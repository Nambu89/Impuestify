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
4. **Comparativa anual** (proyección de ingresos y retenciones)
5. **Recomendaciones personalizadas** (qué puede hacer el usuario)

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
		self.name = name
		self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
		self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
		
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
				temperature=0.7,
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
					temperature=0.7,
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