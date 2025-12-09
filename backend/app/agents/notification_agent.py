"""
Notification Agent for analyzing AEAT notifications.

Specialized agent that:
- Extracts content from notification PDFs
- Calculates exact deadlines
- Detects taxpayer's region
- Generates user-friendly explanations
- Retrieves relevant context from RAG
"""
import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from app.utils.deadline_calculator import DeadlineCalculator
from app.utils.region_detector import RegionDetector
from app.agents.tax_agent import get_tax_agent


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

Tu misión es ayudar a ciudadanos que han recibido notificaciones de Hacienda, explicándoles de forma CLARA y COLOQUIAL qué significa y qué deben hacer.

REGLAS FUNDAMENTALES:
1. **Lenguaje sencillo** - Evita jerga técnica. Habla como si explicaras a un amigo.
2. **Fechas exactas** - Nunca digas "10 días hábiles", di la fecha concreta (ej: "20 de diciembre de 2024")
3. **Prioriza lo urgente** - Destaca plazos críticos con emojis
4. **Sé empático** - Reconoce que puede ser estresante, pero tranquiliza al usuario
5. **Pasos concretos** - Instrucciones accionables, no teoría

ESTRUCTURA DE TU RESPUESTA:

## 📋 ¿Qué es esto?
[Explica en 2-3 frases qué tipo de notificación es y por qué la recibieron, de forma tranquilizadora]

## ⏰ Plazos Importantes  
**[URGENTE si falta <5 días]**
- **[Acción requerida]**: Fecha límite [DD de mes de AAAA]  
  ([X días restantes])

## 📍 Tu situación fiscal
- **Comunidad Autónoma**: [Detectada del documento]
- **Normativa aplicable**: [Territorio común AEAT / Hacienda Foral de X]

## ✅ Qué tienes que hacer (paso a paso)
1. [Primer paso concreto y específico]
2. [Segundo paso]
3. [etc]

## 🔗 Enlaces útiles
- [Enlaces mencionados en la notificación o recursos de la AEAT]

## 💡 Consejos
[1-2 tips útiles para evitar problemas o agilizar el proceso]

---
**Aviso**: Esta es información orientativa. Para casos complejos, consulta con un asesor fiscal profesional.
"""
    
    def __init__(self):
        self.deadline_calc = DeadlineCalculator()
        self.region_detector = RegionDetector()
        self.tax_agent = None  # Lazy init
        self._azure_client = None
    
    def _get_tax_agent(self):
        """Lazy initialization of tax agent."""
        if self.tax_agent is None:
            self.tax_agent = get_tax_agent()
        return self.tax_agent
    
    def _init_azure_client(self):
        """Initialize Azure Document Intelligence client."""
        if self._azure_client is None:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
            endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
            
            if not endpoint or not key:
                raise ValueError("Azure Document Intelligence not configured")
            
            self._azure_client = DocumentIntelligenceClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(key)
            )
        
        return self._azure_client
    
    async def extract_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract content from notification PDF.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            {
                'text': str,  # Full extracted text
                'pages': int,  # Number of pages
                'file_hash': str  # MD5 hash for dedup
            }
        """
        import base64
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        
        client = self._init_azure_client()
        
        # Read PDF
        with open(pdf_path, "rb") as f:
            file_content = f.read()
        
        # Calculate hash for deduplication
        file_hash = hashlib.md5(file_content).hexdigest()
        
        # Encode for API
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Analyze with prebuilt-layout
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=AnalyzeDocumentRequest(bytes_source=base64_content)
        )
        
        result = poller.result()
        
        # Extract text from all pages
        full_text = ""
        for page in result.pages:
            if page.lines:
                page_text = "\n".join([line.content for line in page.lines])
                full_text += page_text + "\n\n"
        
        return {
            'text': full_text.strip(),
            'pages': len(result.pages) if hasattr(result, 'pages') else 1,
            'file_hash': file_hash
        }
    
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
                'file_hash': str
            }
        """
        # Step 1: Extract PDF
        extracted = await self.extract_pdf(pdf_path)
        text = extracted['text']
        
        # Log extracted text length
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Extracted PDF text length: {len(text)}")
        if not text:
            logger.warning("Extracted PDF text is empty!")
        
        # Step 2: Detect region
        region_info = self.region_detector.detect_from_text(text)
        
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
        
        # Step 4: Detect notification type
        notif_type = self._classify_notification(text)
        
        # Step 5: Determine severity
        severity = self._calculate_severity(text, deadlines, notif_type)
        
        # Step 6: Get relevant RAG context
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
        
        # Get response (without tool calling for notification analysis)
        response = await agent.run(
            query=analysis_prompt,
            context=rag_context,
            use_tools=False,  # Disable tools for notification analysis
            system_prompt=self.SYSTEM_PROMPT  # Use specialized notification agent prompt
        )
        
        # Step 8: Extract references/links from text
        references = self._extract_references(text, region_info)
        
        # Step 9: Structure response
        return {
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
    
    def _classify_notification(self, text: str) -> str:
        """
        Classify notification type.
        
        Returns:
            Type string (e.g., 'Requerimiento', 'Liquidación', etc)
        """
        text_lower = text.lower()
        
        if "requerimiento" in text_lower:
            return "Requerimiento de documentación"
        elif "liquidación provisional" in text_lower or "liquidación" in text_lower:
            return "Liquidación provisional"
        elif "comprobación limitada" in text_lower:
            return "Comprobación limitada"
        elif "sanción" in text_lower or "multa" in text_lower:
            return "Propuesta de sanción"
        elif "devolución" in text_lower:
            return "Devolución de impuestos"
        elif "embargo" in text_lower or "apremio" in text_lower:
            return "Procedimiento de apremio"
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
        if "sanción" in text.lower() or "apremio" in text.lower() or "embargo" in text.lower():
            return "high"
        
        # Urgent deadlines
        if any(d.get('is_urgent') or d.get('is_overdue') for d in deadlines):
            return "high"
        
        # Medium severity
        if notif_type in ["Liquidación provisional", "Comprobación limitada"]:
            return "medium"
        
        # Low severity
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
        
        # TODO: Call chat.fts_search here
        # For now, return empty - will integrate after testing
        return ""
    
    def _extract_key_terms(self, text: str) -> str:
        """Extract key tax-related terms from notification."""
        # Simple keyword extraction
        keywords = []
        
        tax_terms = [
            "IRPF", "IVA", "IS", "Impuesto Sociedades",
            "retenciones", "declaración", "modelo",
            "ejercicio", "liquidación"
        ]
        
        for term in tax_terms:
            if term in text:
                keywords.append(term)
        
        return " ".join(keywords[:5])  # Top 5
    
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
        
        prompt = f"""
Analiza esta notificación de la Agencia Tributaria y explícala de forma clara al usuario.

**Tipo de notificación**: {notification_type}

**Región del contribuyente**: {region.get('region', 'No detectada')}
**Normativa**: {"Hacienda Foral" if region.get('is_foral') else "Territorio común (AEAT)"}

**Plazos detectados**:
{deadline_info if deadline_info else "No se detectaron plazos específicos"}

**Contenido de la notificación**:
{notification_text[:2000]}  # Limit to avoid token overflow

**Contexto normativo relevante**:
{context if context else "No disponible"}

Genera una explicación siguiendo EXACTAMENTE la estructura del SYSTEM_PROMPT.
Usa las fechas exactas calculadas arriba.
Sé empático y claro.
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
            List of {'title': str, 'url': str}
        """
        references = []
        
        # Extract URLs from text
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        
        for url in urls:
            references.append({
                'title': 'Enlace mencionado en la notificación',
                'url': url
            })
        
        # Add standard AEAT references
        if not region_info.get('is_foral'):
            references.append({
                'title': 'Sede Electrónica de la AEAT',
                'url': 'https://sede.agenciatributaria.gob.es'
            })
            references.append({
                'title': 'Atención telefónica: 91 535 73 26',
                'url': 'tel:+34915357326'
            })
        else:
            # Foral references
            authority_url = self.region_detector.get_tax_authority_url(
                region_info['region'],
                True
            )
            references.append({
                'title': f'Sede de {self.region_detector.get_tax_authority_name(region_info["region"], True)}',
                'url': authority_url
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
