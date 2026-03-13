"""
Notification Agent for analyzing AEAT notifications.

Specialized agent that:
- Extracts content from notification PDFs using PyMuPDF4LLM (FREE, no API costs)
- Calculates exact deadlines
- Detects taxpayer's region
- Generates user-friendly explanations
- Retrieves relevant context from RAG

MIGRATION NOTE: Replaced Azure Document Intelligence with PyMuPDF4LLM
- ✅ No API costs (100% free)
- ✅ Faster processing (local extraction)
- ✅ Extracts ALL pages for complete context
- ✅ Better Markdown output for LLMs
"""
import os
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import pymupdf4llm

from app.utils.deadline_calculator import DeadlineCalculator
from app.utils.region_detector import RegionDetector
from app.agents.tax_agent import get_tax_agent

logger = logging.getLogger(__name__)


class NotificationAgent:
	"""
	Specialized agent for AEAT notification analysis.
	
	Provides clear, actionable summaries of tax notifications with:
	- Exact deadline calculations
	- Regional tax considerations
	- Step-by-step guidance
	"""
	
	SYSTEM_PROMPT = """
Eres un experto asesor fiscal español especializado en notificaciones de la Agencia Tributaria.

REGLA DE ORO: RESPONDE PRIMERO, EXPLICA SOLO LO NO OBVIO.

Cuando analices una notificación:
1. En 1-2 frases di QUÉ es el documento y QUÉ debe hacer el usuario. Sin preámbulos.
2. Si hay cifras o fechas relevantes, ponlas en tabla markdown.
3. Si hay acciones concretas necesarias, listarlas en pasos numerados breves.
4. NO expliques lo obvio. NO rellenes secciones vacías. NO repitas información ya incluida en los plazos calculados.

TONO: coloquial, directo, empático. Habla como un asesor de confianza, no como un formulario.

SOBRE LOS PLAZOS: el sistema ya calculó las fechas exactas y te las pasará en el contexto. Úsalas. NO recalcules ni repitas "10 días hábiles" — di la fecha concreta.

Avisa solo al final, en una línea: "Para decisiones importantes (recurrir, alegar), consulta con un asesor fiscal."
"""
	
	def __init__(self):
		self.deadline_calc = DeadlineCalculator()
		self.region_detector = RegionDetector()
		self.tax_agent = None  # Lazy init
	
	def _get_tax_agent(self):
		"""Lazy initialization of tax agent."""
		if self.tax_agent is None:
			self.tax_agent = get_tax_agent()
		return self.tax_agent
	
	async def extract_pdf(self, pdf_path: str) -> Dict[str, Any]:
		"""
		Extract content from notification PDF using PyMuPDF4LLM.
		
		Args:
			pdf_path: Path to PDF file
		
		Returns:
			{
				'text': str,  # Full extracted text (Markdown format)
				'pages': int,  # Number of pages
				'file_hash': str  # SHA256 hash for deduplication
			}
		"""
		try:
			# Read file for hash calculation
			with open(pdf_path, "rb") as f:
				file_content = f.read()
			
			# Calculate hash for deduplication
			file_hash = hashlib.sha256(file_content).hexdigest()
			
			# Extract ALL pages as Markdown using PyMuPDF4LLM
			logger.info(f"🔍 Extracting text from {pdf_path} with PyMuPDF4LLM...")
			
			md_text = pymupdf4llm.to_markdown(
				pdf_path,
				# pages=None means ALL pages (default)
				page_chunks=False,  # Single string with all content
				write_images=False,  # We don't need images
				extract_words=False  # Just text, not word-level detail
			)
			
			if not md_text or len(md_text.strip()) < 50:
				logger.error("❌ PDF appears to be empty or text extraction failed")
				raise ValueError("PDF appears to be empty or text extraction failed")
			
			# Count approximate pages (PyMuPDF4LLM doesn't return page count directly)
			# Estimate: typical page has ~500-2000 chars in Markdown
			estimated_pages = max(1, len(md_text) // 1000)
			
			logger.info(f"✅ Extracted {len(md_text)} characters (~{estimated_pages} pages)")
			
			return {
				'text': md_text.strip(),
				'pages': estimated_pages,
				'file_hash': file_hash
			}
			
		except Exception as e:
			logger.error(f"❌ PDF extraction failed: {str(e)}")
			raise ValueError(f"Failed to extract text from PDF: {str(e)}")
	
	async def analyze_notification(
		self,
		pdf_path: str,
		notification_date: Optional[str] = None,
		user_context: Optional[Dict] = None
	) -> Dict[str, Any]:
		"""
		Analyze AEAT notification PDF.
		
		Args:
			pdf_path: Path to uploaded PDF
			notification_date: ISO date when notification was received (defaults to today)
			user_context: Optional user info (region, etc)
		
		Returns:
			{
				'summary': str,  # User-friendly explanation
				'type': str,  # Notification type
				'deadlines': List[dict],  # Calculated deadlines
				'region': dict,  # Detected region info
				'actions': List[str],  # Steps to take
				'references': List[dict],  # Useful links
				'severity': str,  # 'low' | 'medium' | 'high'
				'file_hash': str,
				'notification_date': str,
				'analyzed_at': str
			}
		"""
		logger.info(f"📄 Starting notification analysis: {pdf_path}")
		
		# Step 1: Extract PDF with PyMuPDF4LLM
		extracted = await self.extract_pdf(pdf_path)
		text = extracted['text']
		
		logger.info(f"📝 Extracted text length: {len(text)} chars")
		
		if not text:
			logger.error("❌ Extracted PDF text is empty!")
			raise ValueError("Could not extract text from PDF")
		
		# Step 2: Detect region
		region_info = self.region_detector.detect_from_text(text)
		logger.info(f"📍 Detected region: {region_info.get('region')} (confidence: {region_info.get('confidence')})")
		
		# Override with user context if provided
		if user_context and 'region' in user_context:
			region_info = user_context['region']
		
		# Step 3: Calculate deadlines
		notif_date = notification_date or datetime.now().isoformat()[:10]
		raw_deadlines = self.deadline_calc.extract_deadlines_from_text(text, notif_date)
		
		# Enhance with region-specific calculation
		deadlines = []
		region_name = region_info.get('region', '').lower()
		
		for deadline in raw_deadlines:
			if deadline['type'] == 'business_days':
				# Recalculate with regional holidays
				exact_date = self.deadline_calc.calculate_business_days(
					start_date=notif_date,
					num_days=deadline['value'],
					region=region_name
				)
				deadline['date'] = exact_date
			
			# Add urgency info
			days_left = self.deadline_calc.days_remaining(deadline['date'])
			deadline['days_remaining'] = days_left
			deadline['is_urgent'] = self.deadline_calc.is_urgent(deadline['date'])
			deadline['is_overdue'] = days_left < 0
			
			deadlines.append(deadline)
		
		logger.info(f"⏰ Detected {len(deadlines)} deadlines")
		
		# Step 4: Detect notification type
		notif_type = self._classify_notification(text)
		logger.info(f"📋 Notification type: {notif_type}")
		
		# Step 5: Determine severity
		severity = self._calculate_severity(text, deadlines, notif_type)
		logger.info(f"🔔 Severity: {severity}")
		
		# Step 6: Get relevant RAG context (optional)
		rag_context = await self._get_rag_context(text, region_info)
		
		# Step 7: Generate explanation with LLM
		agent = self._get_tax_agent()
		
		# Build prompt
		analysis_prompt = self._build_analysis_prompt(
			notification_text=text,
			notification_type=notif_type,
			deadlines=deadlines,
			region=region_info,
			context=rag_context
		)
		
		logger.info("🤖 Calling TaxAgent for analysis...")
		
		# Get response (without tool calling for notification analysis)
		response = await agent.run(
			query=analysis_prompt,
			context=rag_context,
			use_tools=False,  # Disable tools for notification analysis
			system_prompt=self.SYSTEM_PROMPT  # Use specialized notification agent prompt
		)
		
		logger.info(f"✅ TaxAgent response length: {len(response.content)}")
		
		# Step 8: Extract references/links from text
		references = self._extract_references(text, region_info)
		
		# Step 9: Structure response
		result = {
			'summary': response.content,
			'type': notif_type,
			'deadlines': deadlines,
			'region': region_info,
			'severity': severity,
			'references': references,
			'file_hash': extracted['file_hash'],
			'notification_date': notif_date,
			'analyzed_at': datetime.now().isoformat()
		}
		
		logger.info(f"✅ Notification analysis complete: {notif_type}")
		return result
	
	def _classify_notification(self, text: str) -> str:
		"""
		Classify notification type based on content.
		
		Returns:
			Type string (e.g., 'Requerimiento', 'Liquidación', etc)
		"""
		text_lower = text.lower()
		
		if "providencia de apremio" in text_lower or "apremio" in text_lower:
			return "Providencia de apremio"
		elif "requerimiento" in text_lower:
			return "Requerimiento de documentación"
		elif "liquidación provisional" in text_lower or "liquidación" in text_lower:
			return "Liquidación provisional"
		elif "comprobación limitada" in text_lower:
			return "Comprobación limitada"
		elif "sanción" in text_lower or "multa" in text_lower:
			return "Propuesta de sanción"
		elif "devolución" in text_lower:
			return "Devolución de impuestos"
		elif "embargo" in text_lower:
			return "Diligencia de embargo"
		else:
			return "Notificación general"
	
	def _calculate_severity(
		self,
		text: str,
		deadlines: List[dict],
		notif_type: str
	) -> str:
		"""
		Calculate notification severity.
		
		Returns:
			'low' | 'medium' | 'high'
		"""
		# High severity indicators
		if any(word in text.lower() for word in ["sanción", "apremio", "embargo", "ejecución"]):
			return "high"
		
		# Urgent deadlines
		if any(d.get('is_urgent') or d.get('is_overdue') for d in deadlines):
			return "high"
		
		# Medium severity
		if notif_type in ["Liquidación provisional", "Comprobación limitada", "Requerimiento de documentación"]:
			return "medium"
		
		# Low severity (informative notifications)
		return "low"
	
	async def _get_rag_context(
		self,
		text: str,
		region_info: Dict
	) -> str:
		"""
		Get relevant context from RAG knowledge base.
		
		Args:
			text: Notification text
			region_info: Detected region
		
		Returns:
			Relevant context string
		"""
		# Extract key terms from notification
		key_terms = self._extract_key_terms(text)
		
		# Build search query
		query = f"{key_terms} {region_info.get('region', '')}"
		
		# TODO: Call fts_search from chat router here for RAG context
		# For now, return empty - agent will work without RAG
		return ""
	
	def _extract_key_terms(self, text: str) -> str:
		"""Extract key tax-related terms from notification."""
		keywords = []
		
		tax_terms = [
			"IRPF", "IVA", "IS", "Impuesto Sociedades",
			"retenciones", "declaración", "modelo",
			"ejercicio", "liquidación", "apremio",
			"recargo", "sanción"
		]
		
		for term in tax_terms:
			if term in text:
				keywords.append(term)
		
		return " ".join(keywords[:5])  # Top 5 terms
	
	def _build_analysis_prompt(
		self,
		notification_text: str,
		notification_type: str,
		deadlines: List[dict],
		region: Dict,
		context: str
	) -> str:
		"""Build prompt for LLM analysis."""
		# Format deadlines for prompt
		deadline_info = ""
		for d in deadlines:
			days_left = d.get('days_remaining', 0)
			urgency = "🚨 URGENTE" if d.get('is_urgent') else ""
			deadline_info += f"- {d['description']}: {d['date']} ({days_left} días) {urgency}\n"
		
		# Limit text to avoid token overflow (keep first 3000 chars)
		truncated_text = notification_text[:3000]
		if len(notification_text) > 3000:
			truncated_text += "\n\n[... documento continúa ...]"
		
		prompt = f"""
Analiza esta notificación de la Agencia Tributaria y explícala de forma clara al usuario.

**Tipo de notificación**: {notification_type}

**Región del contribuyente**: {region.get('region', 'No detectada')}
**Normativa**: {"Hacienda Foral" if region.get('is_foral') else "Territorio común (AEAT)"}

**Plazos detectados**:
{deadline_info if deadline_info else "No se detectaron plazos específicos"}

**Contenido de la notificación**:
{truncated_text}

**Contexto normativo relevante**:
{context if context else "No disponible"}

Responde directamente: qué es este documento y qué debe hacer el usuario.
Usa las fechas exactas calculadas arriba.
Sé breve. Solo detalla lo que NO sea obvio.
"""
		return prompt
	
	def _extract_references(
		self,
		text: str,
		region_info: Dict
	) -> List[Dict[str, str]]:
		"""
		Extract useful links and references.
		
		Returns:
			List of {'title': str, 'url': str, 'description': str}
		"""
		references = []
		
		# Extract URLs from text
		import re
		url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
		urls = re.findall(url_pattern, text)
		
		for url in urls:
			references.append({
				'title': 'Enlace mencionado en la notificación',
				'url': url,
				'description': 'Recurso oficial de la AEAT'
			})
		
		# Add standard AEAT references based on region
		if not region_info.get('is_foral'):
			references.extend([
				{
					'title': 'Sede Electrónica de la AEAT',
					'url': 'https://sede.agenciatributaria.gob.es',
					'description': 'Portal para realizar trámites online'
				},
				{
					'title': 'Pagar deudas (Sede AEAT)',
					'url': 'https://sede.agenciatributaria.gob.es/Sede/deudas-apremios-embargos-subastas/pagar-aplazar-consultar.html',
					'description': 'Sistema de pago electrónico'
				},
				{
					'title': 'Atención telefónica: 91 535 73 26',
					'url': 'tel:+34915357326',
					'description': 'Horario: L-V 9:00-14:00'
				}
			])
		else:
			# Foral references
			authority_name = self.region_detector.get_tax_authority_name(
				region_info['region'],
				True
			)
			authority_url = self.region_detector.get_tax_authority_url(
				region_info['region'],
				True
			)
			references.append({
				'title': f'Sede de {authority_name}',
				'url': authority_url,
				'description': 'Portal de la Hacienda Foral'
			})
		
		return references


# Singleton instance
_notification_agent = None


def get_notification_agent() -> NotificationAgent:
	"""Get singleton instance of notification agent."""
	global _notification_agent
	if _notification_agent is None:
		_notification_agent = NotificationAgent()
	return _notification_agent