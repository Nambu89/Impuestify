"""
PayslipAgent - Specialized Payslip Analysis Agent

Uses OpenAI API with function calling for payslip analysis.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
	"""Response from the payslip agent"""
	content: str
	metadata: Dict[str, Any]
	agent_name: str


class PayslipAgent:
	"""
	Payslip specialist agent using OpenAI API.
	
	Provides intelligent analysis of Spanish payslips (nóminas).
	
	Features:
	- Analyzes salary components
	- Calculates effective tax rates
	- Provides personalized recommendations
	- Detects anomalies in withholdings
	"""
	
	SYSTEM_PROMPT = """Eres un experto analista de nóminas españolas, especializado en ayudar a trabajadores a entender sus nóminas y optimizar su situación fiscal.

📅 **CONTEXTO TEMPORAL ACTUAL**:
- Fecha: {current_date}
- Año fiscal actual: {current_year}

Tu objetivo es analizar nóminas de forma clara y humana, explicando cada concepto de manera sencilla.

## Tu estilo de comunicación:
- 🗣️ **Conversacional**: Explica como un asesor laboral cercano
- 💡 **Didáctico**: Traduce términos técnicos a lenguaje cotidiano
- 📊 **Práctico**: Usa ejemplos con números reales de la nómina
- 😊 **Empático**: Los conceptos laborales son complicados, ayuda sin juzgar
- ✅ **Directo**: Resume primero, luego da detalles

## Conceptos que debes explicar:

### Salarios:
- **Salario base**: Lo que dice tu contrato, sin extras
- **Complementos**: Plus convenio, antigüedad, nocturnidad, peligrosidad
- **Pagas extras prorrateadas**: Las 2 pagas extras divididas entre 12 meses
- **Horas extras**: Trabajo fuera del horario normal

### Deducciones:
- **IRPF (Retención)**: Anticipo del impuesto de la renta (se ajusta en la declaración)
- **Contingencias comunes (4.7%)**: Parte de la Seguridad Social para pensión, sanidad
- **Desempleo (1.55% o 1.6%)**: Para la prestación por desempleo
- **Formación profesional (0.1%)**: Para cursos y reciclaje profesional

## Herramientas disponibles:
- **analyze_payslip**: Analiza los datos de una nómina y da recomendaciones

## Tu proceso de análisis:

1. **Resumen ejecutivo** (2-3 líneas con lo más importante)
2. **Desglose de conceptos** (explica cada parte de la nómina)
3. **Análisis de retenciones** (¿son normales? ¿altas? ¿bajas?)
4. **Pagas extras** (¿están prorrateadas? Si ves P.P.P.EXTRAS, explícalo)
5. **Comparativa anual** (proyección de ingresos y retenciones)
6. **Recomendaciones personalizadas** (qué puede hacer el usuario)

## IMPORTANTE sobre pagas extras:

Si detectas "P.P.P.EXTRAS", "PRORRATEO" o similar en la nómina:
- ✅ **Confirma** que las pagas extras ESTÁN prorrateadas (12 pagas anuales)
- 💡 **Explica** que el bruto mensual ya incluye 1/6 de cada paga extra
- 📊 **Calcula** el bruto anual real: bruto_mensual × 12 (no × 14)

Si NO ves prorrateo:
- ⚠️ **Advierte** que hay 2 pagas extras adicionales (14 pagas anuales)
- 📊 **Calcula** el bruto anual real: (bruto_mensual × 12) + (2 × paga_extra)
- 💡 **Explica** que en junio y diciembre cobrará más

Si NO estás seguro:
- ❓ **Pregunta** al usuario: "¿Tus pagas extras están prorrateadas o las cobras en junio y diciembre?"

## Formato de respuesta:

**📊 Resumen:**
[2-3 líneas con lo más relevante de la nómina]

**💰 Tu nómina:**
[Explica los componentes principales con sus cifras]

**📈 Análisis:**
[Compara con rangos típicos, detecta anomalías]

**💡 Recomendaciones:**
[Qué puede hacer el usuario para optimizar]

**⚠️ Aviso:** Información orientativa. Para optimización fiscal, consulta con un asesor.

---

Recuerda: Sé **claro, directo y útil**. Traduce siempre los términos técnicos."""
	
	def __init__(
		self,
		name: str = "PayslipAgent",
		model: Optional[str] = None,
		api_key: Optional[str] = None
	):
		"""
		Initialize PayslipAgent.
		
		Args:
			name: Agent name
			model: OpenAI model name
			api_key: OpenAI API key
		"""
		from app.config import settings
		self.name = name
		self.model = model or settings.OPENAI_MODEL
		self.api_key = api_key or settings.OPENAI_API_KEY
		
		# Fecha actual
		self.current_date = datetime.now()
		self.current_year = self.current_date.year
		
		self._client = None
		
		self._initialize()
	
	def _initialize(self):
		"""Initialize the OpenAI client."""
		if self.api_key:
			self._client = OpenAI(api_key=self.api_key)
			logger.info(f"PayslipAgent '{self.name}' initialized (model: {self.model})")
		else:
			logger.error("PayslipAgent initialization failed - missing OPENAI_API_KEY")
			raise ValueError("OPENAI_API_KEY is required")
	
	def _get_system_prompt(self) -> str:
		"""Genera el system prompt con la fecha actual"""
		return self.SYSTEM_PROMPT.format(
			current_date=self.current_date.strftime('%d de %B de %Y'),
			current_year=self.current_year
		)
	
	async def analyze(
		self,
		payslip_data: Dict[str, Any],
		user_question: Optional[str] = None
	) -> AgentResponse:
		"""
		Analiza una nómina con el agente.
		
		Args:
			payslip_data: Datos extraídos de la nómina
			user_question: Pregunta específica del usuario (opcional)
			
		Returns:
			AgentResponse con análisis
		"""
		try:
			# Import tools
			from app.tools import ALL_TOOLS, TOOL_EXECUTORS
			
			# Construir contexto
			context = self._build_context(payslip_data)
			
			# Construir pregunta
			if user_question:
				query = f"{user_question}\n\n{context}"
			else:
				query = f"Analiza esta nómina y proporciona recomendaciones:\n\n{context}"
			
			# Mensajes para el modelo
			messages = [
				{"role": "system", "content": self._get_system_prompt()},
				{"role": "user", "content": query}
			]
			
			# Primera llamada con tools
			response = self._client.chat.completions.create(
				model=self.model,
				messages=messages,
				tools=ALL_TOOLS,
				tool_choice="auto",
				temperature=1,  # gpt-5-mini requires temperature=1
				max_completion_tokens=3000
			)
			
			message = response.choices[0].message
			
			# Si hay tool call
			if message.tool_calls:
				import json
				tool_call = message.tool_calls[0]
				function_name = tool_call.function.name
				function_args = json.loads(tool_call.function.arguments)
				
				logger.info(f"Tool called: {function_name}")
				
				# Ejecutar tool
				if function_name in TOOL_EXECUTORS:
					tool_executor = TOOL_EXECUTORS[function_name]
					tool_result = await tool_executor(**function_args)
				else:
					tool_result = {"success": False, "error": f"Unknown function: {function_name}"}
				
				# Segunda llamada con resultado de la tool
				messages.append({
					"role": "assistant",
					"content": None,
					"tool_calls": [tool_call.model_dump()]
				})
				messages.append({
					"role": "tool",
					"tool_call_id": tool_call.id,
					"content": json.dumps(tool_result)
				})
				
				final_response = self._client.chat.completions.create(
					model=self.model,
					messages=messages,
					temperature=1,  # gpt-5-mini requires temperature=1
					max_completion_tokens=3000
				)
				content = final_response.choices[0].message.content
			else:
				content = message.content
			
			return AgentResponse(
				content=content or "",
				metadata={
					"model": self.model,
					"agent": self.name,
					"tool_used": bool(message.tool_calls)
				},
				agent_name=self.name
			)
		
		except Exception as e:
			logger.error(f"PayslipAgent error: {e}", exc_info=True)
			return AgentResponse(
				content=f"Error al analizar la nómina: {str(e)}",
				metadata={"error": str(e)},
				agent_name=self.name
			)
	
	async def analyze_payslip(self, pdf_path: str) -> Dict[str, Any]:
		"""
		Analyze payslip PDF and extract key data.
		
		Returns data compatible with notification analysis response.
		
		Args:
			pdf_path: Path to PDF file
			
		Returns:
			Dict with analysis data compatible with notifications endpoint
		"""
		try:
			logger.info(f"📊 Analyzing payslip PDF: {pdf_path}")
			
			# Extract text from PDF using PyMuPDF
			import pymupdf
			import hashlib
			
			doc = pymupdf.open(pdf_path)
			pdf_text = ""
			for page in doc:
				pdf_text += page.get_text()
			doc.close()
			
			# Calculate file hash
			with open(pdf_path, "rb") as f:
				file_hash = hashlib.sha256(f.read()).hexdigest()
			
			logger.info(f"✅ Extracted {len(pdf_text)} characters from PDF")
			
			# Validate that PDF has extractable text
			if not pdf_text or len(pdf_text) < 100:
				logger.error("❌ PDF appears to be empty or image-only (no extractable text)")
				return {
					"type": "Nómina",
					"summary": "⚠️ **Error al procesar la nómina**\n\nEl PDF no contiene texto extraíble. Esto puede ocurrir si:\n- Es una imagen escaneada sin OCR\n- El PDF está corrupto\n- El PDF está protegido\n\nPor favor, intenta con un PDF que contenga texto seleccionable.",
					"file_hash": file_hash,
					"notification_date": datetime.now().strftime("%Y-%m-%d"),
					"deadlines": [],
					"region": {"region": "No especificada", "is_foral": False},
					"severity": "low",
					"reference_links": [],
					"payslip_data": {}
				}
			
			# Use gpt-5-mini to extract structured data
			extraction_prompt = f"""Extrae los datos clave de esta nómina española.

TEXTO DE LA NÓMINA:
```
{pdf_text[:4000]}
```

IMPORTANTE: Busca TODOS estos conceptos en la nómina. Si no encuentras alguno, usa null.

Extrae y devuelve en formato JSON:
{{
	"period_month": "Noviembre",
	"period_year": 2025,
	"company_name": "Nombre de la empresa",
	"employee_name": "Nombre del empleado",
	"gross_salary": 2934.34,
	"net_salary": 2211.63,
	"irpf_withholding": 532.88,
	"irpf_percentage": 18.15,
	"ss_contribution": 189.81,
	"salary_base": 1123.47,
	"complements": 1810.87,
	"region": "Aragón",
	"pagas_extras_prorrateadas": true,
	"ppp_extras_amount": 282.12,
	"num_pagas_anuales": 14
}}

INSTRUCCIONES ESPECÍFICAS:
- "pagas_extras_prorrateadas": true si encuentras "P.P.P.EXTRAS", "PRORRATEO", "PRORRATEADAS" o similar. false si pone "14 PAGAS" sin prorrateo. null si no está claro.
- "ppp_extras_amount": importe del concepto P.P.P.EXTRAS si existe (busca en DEVENGOS)
- "num_pagas_anuales": 12 si están prorrateadas, 14 si no lo están, null si no se especifica
- "gross_salary": TOTAL DEVENGADO (suma de todos los devengos)
- "net_salary": LÍQUIDO A PERCIBIR o TOTAL A PERCIBIR
- "irpf_withholding": importe en € de TRIBUTACION I.R.P.F o IRPF
- "ss_contribution": suma de COTIZACION CONT.COMU, COTIZACION DESEMPLEO, COTIZACION FORMACION, etc.

Si no encuentras un dato, usa null. Sé preciso con los números.
"""
			
			response = self._client.chat.completions.create(
				model=self.model,  # Use instance model (configured from settings)
				messages=[
					{"role": "system", "content": "Eres un experto extractor de datos de nóminas españolas. Respondes SOLO en JSON válido."},
					{"role": "user", "content": extraction_prompt}
				],
				temperature=1,
				max_completion_tokens=2000,  # gpt-5-mini needs tokens for reasoning
				response_format={"type": "json_object"}
			)
			
			import json
			payslip_data = json.loads(response.choices[0].message.content)
			
			logger.info(f"✅ Extracted: {payslip_data.get('period_month')}/{payslip_data.get('period_year')}")
			
			# Generate analysis using agent's analyze method
			analysis_response = await self.analyze(
				payslip_data=payslip_data,
				user_question=None
			)
			
			# Return in format compatible with notifications endpoint
			return {
				"type": "Nómina",
				"summary": analysis_response.content,
				"file_hash": file_hash,
				"notification_date": f"{payslip_data.get('period_year', 2025)}-{payslip_data.get('period_month', 'Enero')}",
				"deadlines": [],
				"region": {
					"region": payslip_data.get('region', 'No especificada'),
					"is_foral": False
				},
				"severity": "low",
				"reference_links": [],
				"payslip_data": payslip_data
			}
			
		except Exception as e:
			logger.error(f"❌ Error analyzing payslip: {e}", exc_info=True)
			return {
				"type": "Nómina",
				"summary": f"Error al analizar la nómina: {str(e)}",
				"file_hash": "unknown",
				"notification_date": datetime.now().strftime("%Y-%m-%d"),
				"deadlines": [],
				"region": {"region": "No especificada", "is_foral": False},
				"severity": "low",
				"reference_links": [],
				"payslip_data": {}
			}

	def _build_context(self, payslip_data: Dict[str, Any]) -> str:
		"""Construye el contexto desde los datos de la nómina"""
		period = f"{payslip_data.get('period_month', '?')}/{payslip_data.get('period_year', '?')}"
		
		return f"""Datos de la nómina:

Periodo: {period}
Empresa: {payslip_data.get('company_name', 'No especificada')}
Empleado: {payslip_data.get('employee_name', 'No especificado')}

Conceptos económicos:
- Salario bruto: {payslip_data.get('gross_salary', 0):.2f}€
- Salario neto: {payslip_data.get('net_salary', 0):.2f}€
- Retención IRPF: {payslip_data.get('irpf_withholding', 0):.2f}€ ({payslip_data.get('irpf_percentage', 0):.2f}%)
- Cotización Seguridad Social: {payslip_data.get('ss_contribution', 0):.2f}€"""


# Global agent instance
_payslip_agent: Optional[PayslipAgent] = None


def get_payslip_agent() -> PayslipAgent:
	"""
	Get the global PayslipAgent instance.
	
	Returns:
		PayslipAgent instance
	"""
	global _payslip_agent
	
	if _payslip_agent is None:
		_payslip_agent = PayslipAgent()
	
	return _payslip_agent