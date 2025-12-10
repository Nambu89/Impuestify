"""
TaxAgent - Specialized Tax Assistant Agent

Uses OpenAI API with function calling for tax calculations.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
	"""Response from the tax agent"""
	content: str
	sources: List[Dict[str, Any]]
	metadata: Dict[str, Any]
	agent_name: str


class TaxAgent:
	"""
	Tax specialist agent using OpenAI API.
	
	Provides intelligent responses about Spanish tax regulations
	based on AEAT documentation.
	
	Features:
	- RAG integration for document retrieval
	- Function calling for tax calculations
	- Conversational and empathetic responses
	"""
	
	SYSTEM_PROMPT = """Eres TaxIA, un asesor fiscal cercano y experto en impuestos españoles.

Tu objetivo es explicar temas fiscales de forma clara y humana, como si estuvieras tomando un café con un amigo que te pregunta sobre sus impuestos. Usa un lenguaje sencillo y coloquial, pero mantén la precisión técnica.

## Tu estilo de comunicación:
- 🗣️ **Conversacional**: Habla como un asesor fiscal amigable, no como un robot
- 💡 **Didáctico**: Explica términos técnicos en lenguaje cotidiano (ej: "recargo ejecutivo" → "multa por pagar tarde")
- 📊 **Práctico**: Da ejemplos concretos con números cuando sea posible
- 😊 **Empático**: Reconoce que los impuestos son complicados y ayuda sin juzgar
- ✅ **Directo**: Ve al grano primero, luego da detalles si hace falta

## Reglas importantes:
1. SOLO responde sobre fiscalidad española
2. Basa tus respuestas ÚNICAMENTE en el contexto proporcionado (documentación AEAT)
3. Si no tienes información suficiente, dilo claramente: "No tengo esa info en la documentación"
4. NO inventes datos ni hagas suposiciones
5. Cita las fuentes cuando sea relevante, pero de forma natural
6. NUNCA ayudes a evadir impuestos

## Herramientas disponibles:
- **calculate_autonomous_quota**: OBLIGATORIO usarla cuando el usuario mencione cuotas de autónomos con ingresos específicos
- **calculate_irpf**: OBLIGATORIO usarla cuando el usuario mencione IRPF con ingresos y región específicos

⚠️ IMPORTANTE: Si el usuario pregunta sobre cuotas de autónomos con cifras concretas, DEBES usar la herramienta calculate_autonomous_quota SIEMPRE, incluso si tienes información aproximada en el contexto. Las herramientas proporcionan cálculos exactos actualizados a 2025.

## Formato de respuesta (natural, no rígido):

**En resumen:** [Respuesta directa en 1-2 líneas, como si hablaras]

**Te lo explico:** 
[Explicación clara usando lenguaje cotidiano. Traduce términos técnicos. Usa ejemplos con números si ayuda]

**Fuentes:** [Solo si es relevante mencionar de dónde sale la info]

**Aviso:** Esto es orientativo. Para tu caso concreto, mejor consulta con un asesor fiscal o con la AEAT directamente.

## Ejemplos de lenguaje coloquial:
- "Recargo ejecutivo" → "multa por pagar tarde" o "recargo por demora"
- "Liquidación provisional" → "lo que te reclama Hacienda de momento"
- "Deuda tributaria" → "lo que debes de impuestos"
- "Sede Electrónica" → "la web de la AEAT donde puedes pagar"
- "Aplazamiento/fraccionamiento" → "pagar a plazos"

Recuerda: Eres un asesor cercano y profesional, no un chatbot formal."""

	def __init__(
		self,
		name: str = "TaxAgent",
		model: Optional[str] = None,
		api_key: Optional[str] = None
	):
		"""
		Initialize TaxAgent.
		
		Args:
			name: Agent name
			model: OpenAI model name (gpt-5-mini, gpt-5, gpt-4o, etc.)
			api_key: OpenAI API key
		"""
		self.name = name
		self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
		self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
		
		self._client = None
		
		self._initialize()
	
	def _initialize(self):
		"""Initialize the OpenAI client."""
		if self.api_key:
			self._client = OpenAI(api_key=self.api_key)
			logger.info(f"TaxAgent '{self.name}' initialized with OpenAI API (model: {self.model})")
		else:
			logger.error("TaxAgent initialization failed - missing OPENAI_API_KEY")
			raise ValueError("OPENAI_API_KEY is required")
	
	async def run(
		self,
		query: str,
		context: Optional[str] = None,
		sources: Optional[List[Dict[str, Any]]] = None,
		conversation_history: Optional[List[Dict[str, str]]] = None,
		use_tools: bool = True,
		system_prompt: Optional[str] = None
	) -> AgentResponse:
		"""
		Run the agent with a user query.
		
		Args:
			query: User's question
			context: Retrieved context from RAG
			sources: Source documents for citations
			conversation_history: Previous messages in conversation
			use_tools: Whether to enable function calling tools (default: True)
			system_prompt: Optional override for system prompt
			
		Returns:
			AgentResponse with answer and metadata
		"""
		# Build the prompt with context
		user_message = self._build_prompt(query, context)
		
		try:
			# Import tools
			from app.tools import ALL_TOOLS, TOOL_EXECUTORS
			
			# Build messages with conversation history
			messages = [
				{"role": "system", "content": system_prompt or self.SYSTEM_PROMPT}
			]
			
			# Add conversation history if provided
			if conversation_history:
				for msg in conversation_history:
					messages.append({
						"role": msg.get("role"),
						"content": msg.get("content")
					})
				logger.info(f"Added {len(conversation_history)} messages from conversation history")
			
			# Add current user message
			messages.append({"role": "user", "content": user_message})
			
			# First call with tools (if enabled)
			logger.info(f"Calling OpenAI with tools enabled: {use_tools}")
			response = self._client.chat.completions.create(
				model=self.model,
				messages=messages,
				tools=ALL_TOOLS if use_tools else None,
				tool_choice="auto" if use_tools else None,
				temperature=1,
				max_completion_tokens=4000
			)
			
			# Check if model wants to call a function
			message = response.choices[0].message
			
			logger.info(f"OpenAI response - has tool_calls: {bool(message.tool_calls)}")
			logger.info(f"OpenAI response - content length: {len(message.content) if message.content else 0}")
			
			if message.tool_calls:
				import json
				tool_call = message.tool_calls[0]
				function_name = tool_call.function.name
				function_args = json.loads(tool_call.function.arguments)
				
				logger.info(f"Tool called: {function_name} with args: {function_args}")
				
				# Execute the appropriate tool dynamically
				if function_name in TOOL_EXECUTORS:
					tool_executor = TOOL_EXECUTORS[function_name]
					tool_result = await tool_executor(**function_args)
				else:
					logger.warning(f"Unknown function: {function_name}")
					tool_result = {"success": False, "error": f"Unknown function: {function_name}"}
				
				logger.info(f"Tool result success: {tool_result.get('success')}")
				
				# Add assistant message and tool result to conversation
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
				
				# Second call to get final response
				logger.info("Calling OpenAI again with tool result")
				final_response = self._client.chat.completions.create(
					model=self.model,
					messages=messages,
					temperature=1,
					max_completion_tokens=4000
				)
				content = final_response.choices[0].message.content or tool_result.get('formatted_response', '')
				logger.info(f"Final content length: {len(content)}")
			else:
				# No function call, use direct response
				content = message.content or ""
				finish_reason = response.choices[0].finish_reason
				if not content:
					logger.warning(f"No content in response. Finish reason: {finish_reason}")
				
				logger.info(f"Direct response content length: {len(content)}")
			
			return AgentResponse(
				content=content,
				sources=sources or [],
				metadata={
					"model": self.model,
					"agent": self.name,
					"framework": "openai-api",
					"tool_used": bool(message.tool_calls)
				},
				agent_name=self.name
			)
			
		except Exception as e:
			logger.error(f"Agent execution error: {e}", exc_info=True)
			return AgentResponse(
				content=f"Error al procesar la consulta: {str(e)}",
				sources=[],
				metadata={"error": str(e)},
				agent_name=self.name
			)
	
	def _build_prompt(self, query: str, context: Optional[str] = None) -> str:
		"""Build the user prompt with optional context."""
		
		# Detect if query requires tool usage
		query_lower = query.lower()
		requires_tool_hint = ""
		
		if any(kw in query_lower for kw in ["cuota", "cotiza", "autónomo", "autonomo", "pago como", "cuánto pago", "cuanto pago"]):
			if any(char.isdigit() for char in query):  # Check if query contains numbers
				requires_tool_hint = "\n⚠️ ATENCIÓN: Esta pregunta requiere cálculo de cuota de autónomos. DEBES usar la herramienta calculate_autonomous_quota.\n"
		
		if any(kw in query_lower for kw in ["irpf", "renta", "cuánto pago de impuestos", "retención", "cuanto pago de impuestos", "retencion"]):
			if any(char.isdigit() for char in query):  # Check if query contains numbers
				requires_tool_hint = "\n⚠️ ATENCIÓN: Esta pregunta requiere cálculo de IRPF. DEBES usar la herramienta calculate_irpf.\n"
		
		if context:
			return f"""{requires_tool_hint}Contexto relevante de los documentos oficiales de la AEAT:

{context}

---

Pregunta del usuario:
{query}

Instrucciones:
- Si la pregunta menciona cuotas de autónomos con ingresos específicos, DEBES usar calculate_autonomous_quota
- Si la pregunta menciona IRPF con ingresos específicos, DEBES usar calculate_irpf
- Para otras consultas, responde basándote en el contexto proporcionado
- Siempre incluye un aviso de que esto es información orientativa"""
		else:
			return requires_tool_hint + query
	
	async def ask(self, question: str, context: Optional[str] = None) -> str:
		"""
		Convenience method for asking questions.
		
		Args:
			question: User's question  
			context: Retrieved context from RAG
			
		Returns:
			str: Answer text
		"""
		response = await self.run(query=question, context=context)
		return response.content
	
	def run_sync(
		self,
		query: str,
		context: Optional[str] = None,
		sources: Optional[List[Dict[str, Any]]] = None
	) -> AgentResponse:
		"""
		Synchronous version of run() for non-async contexts.
		"""
		import asyncio
		
		try:
			loop = asyncio.get_event_loop()
		except RuntimeError:
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
		
		return loop.run_until_complete(self.run(query, context, sources))


# Global agent instance
_tax_agent: Optional[TaxAgent] = None


def get_tax_agent() -> TaxAgent:
	"""
	Get the global TaxAgent instance.
	
	Returns:
		TaxAgent instance
	"""
	global _tax_agent
	
	if _tax_agent is None:
		_tax_agent = TaxAgent()
	
	return _tax_agent