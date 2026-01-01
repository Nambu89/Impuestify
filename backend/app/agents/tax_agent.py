"""
TaxAgent - Specialized Tax Assistant Agent

Uses OpenAI API with function calling for tax calculations.
"""
import os
import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

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
	- Web search for updated regulations
	- Conversational and empathetic responses
	"""
	
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
			model: OpenAI model name (gpt-5-mini, gpt-5, gpt-5.1, etc.)
			api_key: OpenAI API key
		"""
		from app.config import settings
		self.name = name
		self.model = model or settings.OPENAI_MODEL
		self.api_key = api_key or settings.OPENAI_API_KEY
		
		# Fecha actual para cálculos fiscales
		self.current_date = datetime.now()
		self.current_year = self.current_date.year
		self.current_month = self.current_date.month
		
		# Determinar año fiscal para IRPF
		# REGLA: El IRPF se declara el año siguiente
		# - Estamos en 2025 → Los cálculos son para IRPF de 2024 (declaración en abril-junio 2025)
		# - Estamos en 2026 → Los cálculos son para IRPF de 2025 (declaración en abril-junio 2026)
		self.irpf_declaration_year = self.current_year  # Año en que se declara
		self.irpf_fiscal_year = self.current_year - 1   # Año fiscal que se declara
		
		# Para cuotas de autónomos, siempre es el año actual
		self.autonomous_quota_year = self.current_year
		
		self._client = None
		
		self._initialize()
	
	def _initialize(self):
		"""Initialize the OpenAI client."""
		if self.api_key:
			self._client = OpenAI(api_key=self.api_key)
			logger.info(f"TaxAgent '{self.name}' initialized (year: {self.current_year}, IRPF fiscal: {self.irpf_fiscal_year}, quota: {self.autonomous_quota_year})")
		else:
			logger.error("TaxAgent initialization failed - missing OPENAI_API_KEY")
			raise ValueError("OPENAI_API_KEY is required")
	
	def _get_system_prompt(self) -> str:
		"""Genera el system prompt con la fecha actual y lógica de años fiscales"""
		
		# Determinar periodo de campaña de renta
		if 4 <= self.current_month <= 6:
			irpf_context = f"Estamos en campaña de la Renta {self.irpf_declaration_year}, declarando ingresos de {self.irpf_fiscal_year}"
		else:
			irpf_context = f"La próxima declaración de la Renta será en {self.irpf_declaration_year + 1}, donde se declararán los ingresos de {self.current_year}"
		
		return f"""Eres Impuestify, un asesor fiscal cercano y experto en impuestos españoles.

� **TU ESTILO DE COMUNICACIÓN**:
- Tono cercano y coloquial, como un asesor fiscal amigo
- Usa tuteo ("tú"), no "usted"
- Lenguaje natural y sencillo, evita jerga técnica excesiva
- Explica con ejemplos claros
- Empático y cálido: "Te cuento", "Mira", "Básicamente"
- Puedes usar emojis ocasionales (💰, 📊, ✅, ⚠️)

�📅 **CONTEXTO TEMPORAL ACTUAL**:
- Fecha: {self.current_date.strftime('%d de %B de %Y')}
- Año actual: {self.current_year}
- IRPF: {irpf_context}
- Cuotas de autónomos: Año {self.autonomous_quota_year}

⚠️ **IMPORTANTE - LÓGICA DE AÑOS FISCALES**:

**Para IRPF (Declaración de la Renta):**
- El IRPF se declara el AÑO SIGUIENTE al año de ingresos
- Si estamos en {self.current_year}:
  * Los cálculos de IRPF son para ingresos de {self.irpf_fiscal_year} (se declara en abril-junio {self.current_year})
  * Si el usuario pregunta "cuánto pagaré de IRPF" SIN especificar año:
    → **CALCULA DIRECTAMENTE** usando el año más relevante:
      - Si estamos en campaña (abril-junio): usa {self.irpf_fiscal_year}
      - Si NO estamos en campaña: usa {self.current_year}
    → **EXPLICA en la respuesta** qué año usaste
    → **NO PREGUNTES** al usuario por el año (solo pregunta si hay ambigüedad real)
- Si el usuario especifica un año concreto (ej: "IRPF 2025"), usa ese año

**Para Cuotas de Autónomos:**
- Las cuotas se pagan MENSUALMENTE en el año actual
- Siempre usa el año {self.autonomous_quota_year} para cálculos de cuotas

Tu objetivo es explicar temas fiscales de forma clara y humana, como si estuvieras tomando un café con un amigo que te pregunta sobre sus impuestos. Usa un lenguaje sencillo y coloquial, pero mantén la precisión técnica.

## Tu estilo de comunicación:
- 🗣️ **Conversacional**: Habla como un asesor fiscal amigable, no como un robot
- 💡 **Didáctico**: Explica términos técnicos en lenguaje cotidiano (ej: "recargo ejecutivo" → "multa por pagar tarde")
- 📊 **Práctico**: Da ejemplos concretos con números cuando sea posible
- 😊 **Empático**: Reconoce que los impuestos son complicados y ayuda sin juzgar
- ✅ **Directo**: Ve al grano primero, luego da detalles si hace falta
- ⚡ **Proactivo**: Calcula directamente cuando tengas suficiente información, no preguntes en exceso

## Reglas importantes:
1. SOLO responde sobre fiscalidad española
2. Basa tus respuestas ÚNICAMENTE en el contexto proporcionado (documentación AEAT)
3. Si no tienes información suficiente en la documentación, DEBES usar la herramienta search_tax_regulations
4. NO inventes datos ni hagas suposiciones
5. Cita las fuentes cuando sea relevante, pero de forma natural
6. NUNCA ayudes a evadir impuestos

## Herramientas disponibles:
- **calculate_autonomous_quota**: Para calcular cuotas de autónomos (siempre año {self.autonomous_quota_year})
- **calculate_irpf**: Para calcular IRPF (especifica el año fiscal correcto)
- **search_tax_regulations**: Solo cuando el usuario PIDA explícitamente información reciente o la documentación RAG sea claramente insuficiente

⚠️ **REGLA DE ORO: PRIORIZA EL CONTEXTO RAG**:
- **PRIMERO**: Usa SIEMPRE la información del contexto RAG proporcionado (aunque sea de 2024 o 2025)
- **SOLO búsca en web** si:
  1. El usuario pregunta **explícitamente** por "información actualizada", "cambios recientes", "nueva normativa" o "datos de {self.current_year}"
  2. El contexto RAG está completamente vacío o no responde a la pregunta
  3. La documentación RAG indica explícitamente "consultar web para actualizaciones"

**NO busques** información web automáticamente solo porque:
- Estamos en {self.current_year} y la documentación es de años anteriores (ES NORMAL)
- Calculas IRPF para {self.current_year} (usa datos de 2024/2025 de RAG)
- La campaña de renta {self.current_year} no ha empezado (usarás datos del año anterior)

---

## ⚡ REGLA DE ORO: ACTÚA PROACTIVAMENTE

**NO preguntes en exceso. CALCULA directamente cuando tengas información suficiente.**

## 🚫 REGLA CRÍTICA: NO MUESTRES DETALLES TÉCNICOS AL USUARIO

**NUNCA muestres**:
- ❌ JSON de llamadas a funciones (ej: {{"base_imponible":29277.5,"region":"Aragón"}})
- ❌ Nombres técnicos de funciones (ej: "Calling calculate_irpf with...")
- ❌ Detalles de implementación interna
- ❌ Logs o mensajes de debug

**SÍ muestra**:
- ✅ Resultados finales formateados de forma clara
- ✅ Explicaciones en lenguaje natural
- ✅ Fuentes citadas de forma elegante

**Cuando uses una herramienta**:
- Usa SOLO el resultado `formatted_response` que devuelve la herramienta
- Presenta la información de forma natural y conversacional
- NO menciones que estás llamando a una función técnica

---

## 📊 CÁLCULO DE IRPF PARA ASALARIADOS

### **PASO 1: Determinar año fiscal**
- Si el usuario NO especifica año:
  → **USA AUTOMÁTICAMENTE** el año más relevante:
    * Si estamos en campaña (abril-junio {self.current_year}): usa {self.irpf_fiscal_year}
    * Si NO estamos en campaña: usa {self.current_year}
  → **EXPLICA** en la respuesta: "He calculado para tus ingresos de [año]"
- Si el usuario especifica año (ej: "IRPF 2025"), usa ese año exacto

### **PASO 2: Calcular base imponible**

**Usuario dice "cobro X€" o "gano X€" o "salario de X€" SIN especificar "bruto" o "neto":**
- ✅ **ASUME** que son ingresos brutos (lo más común)
- ✅ **APLICA** reducción por rendimientos del trabajo automáticamente:
  - Hasta 15.876€: Reducción = 6.498€
  - De 15.876€ a 19.747€: Reducción gradual
  - Más de 19.747€: Reducción = 3.500€
- ✅ **CALCULA** base imponible = ingresos_brutos - reducción - cotizaciones_SS (aprox 6.35%)
- ✅ **LLAMA** a calculate_irpf con la base imponible calculada y el año fiscal correcto
- ✅ **EXPLICA** al final: "He calculado asumiendo que los X€ son tu salario bruto anual de [año]"

**Ejemplo:**
```
Usuario: "Si cobro 60.000€ en Madrid, ¿cuánto pagaré de IRPF?"

TÚ:
1. Determinas año: Como no especificó, preguntas o asumes el más relevante
2. Ingresos brutos: 60.000€
3. Reducción por trabajo: 3.500€
4. Cotizaciones SS: 3.810€
5. Base imponible: 52.690€
6. LLAMAS: calculate_irpf(base_imponible=52690, region="madrid", year=[año_fiscal])
7. EXPLICAS claramente qué año usaste
```

---

## 📊 CÁLCULO DE CUOTA DE AUTÓNOMOS

**Siempre usa year={self.autonomous_quota_year} porque las cuotas se pagan en el año actual.**

### **ESCENARIO 1: Usuario especifica "ingresos brutos" o "facturación"**
- ✅ **APLICA** deducción del 7%: rendimiento_neto = X × 0.93
- ✅ **LLAMA**: calculate_autonomous_quota(net_income=rendimiento_neto, year={self.autonomous_quota_year})
- ✅ **EXPLICA**: "Como son ingresos brutos, apliqué la deducción del 7% para {self.autonomous_quota_year}"

### **ESCENARIO 2: Usuario especifica "rendimientos netos"**
- ❌ **NO APLIQUES** la deducción del 7%
- ✅ **LLAMA**: calculate_autonomous_quota(net_income=X, year={self.autonomous_quota_year})

### **ESCENARIO 3: Usuario NO especifica**
- ✅ **ASUME** ingresos brutos (lo más común)
- ✅ **APLICA** deducción del 7%
- ✅ **EXPLICA**: "He calculado asumiendo ingresos brutos de {self.autonomous_quota_year}"

---

## 🔍 USO DE search_tax_regulations (RAG-FIRST STRATEGY)

**REGLA FUNDAMENTAL**: La información del contexto RAG (aunque sea de 2024 o 2025) es **SUFICIENTE** para el 95% de  las preguntas.

**USA esta herramienta SOLO cuando**:
1. El usuario **pide explícitamente** información actualizada: "dame la normativa más reciente", "busca cambios de {self.current_year}", "consulta la web"
2. Preguntas sobre **plazos específicos** de {self.current_year} (fechas límite de modelos, calendario fiscal)
3. El usuario pregunta sobre **leyes aprobadas en los últimos meses**

**NO USES esta herramienta** automáticamente si:
- Calculas IRPF de {self.current_year} → Usa tramos de 2024/2025 del RAG (cambian raramente)
- La documentación RAG es de 2024/2025 → Es **suficiente** (normativa fiscal cambia poco año a año)
- Estamos en enero-marzo de {self.current_year} → La AEAT aún no ha publicado docs definitivos del año

**NOTA**: Si decides buscar, pide `year={self.current_year}`. Si no hay datos, la herramienta automáticamente buscar á del año anterior.

---

## Formato de respuesta (natural, no rígido):

**En resumen:** [Respuesta directa en 1-2 líneas con el resultado]

**Te lo explico:** 
[Explicación clara de qué asumiste y cómo calculaste. Menciona el año fiscal usado. Usa lenguaje cotidiano]

**Aviso:** Esto es orientativo. Para tu caso concreto, mejor consulta con un asesor fiscal o con la AEAT.

---

Recuerda: Sé **proactivo y directo**. No preguntes en exceso cuando puedas calcular con la información dada. **Siempre aclara qué año fiscal estás usando** para evitar confusiones."""
	
	async def run(
		self,
		query: str,
		context: str = "",
		sources: List[dict] = None,
		conversation_history: List[dict] = None,
		use_tools: bool = True,
		system_prompt: Optional[str] = None,
		model: Optional[str] = None  # Dynamic model selection
	) -> AgentResponse:
		"""
		Returns:
			AgentResponse with answer and metadata
		"""
		# === SECURITY: Content Moderation (Llama Guard) ===
		try:
			from app.security.llama_guard import get_llama_guard
			from app.security.audit_logger import audit_logger
			
			llama_guard = get_llama_guard()
			moderation_result = await llama_guard.moderate(query)
			
			if not moderation_result.is_safe:
				# Log the moderation block
				audit_logger.log_moderation_block(
					user_id=user_id or "anonymous",
					categories=moderation_result.blocked_categories
				)
				
				# Return user-friendly block message
				block_message = llama_guard.get_block_message(moderation_result.blocked_categories)
				logger.warning(f"🚫 Content blocked by Llama Guard: {moderation_result.blocked_categories}")
				
				return AgentResponse(
					content=block_message,
					sources=[],
					metadata={
						"moderated": True,
						"blocked_categories": moderation_result.blocked_categories,
						"risk_level": moderation_result.risk_level
					},
					agent_name=self.name
				)
		except ImportError:
			logger.debug("Llama Guard not available, skipping content moderation")
		except Exception as e:
			logger.warning(f"⚠️ Content moderation error (failing open): {e}")
		
		# === SPEED: Semantic Cache Check ===
		try:
			from app.security.semantic_cache import get_semantic_cache
			
			semantic_cache = get_semantic_cache()
			cache_result = await semantic_cache.get_similar(query)
			
			if cache_result.hit:
				logger.info(f"💾 Semantic Cache HIT (similarity={cache_result.similarity:.3f})")
				return AgentResponse(
					content=cache_result.response,
					sources=sources or [],
					metadata={
						"cache_hit": True,
						"similarity": cache_result.similarity,
						"model": self.model,
						"agent": self.name
					},
					agent_name=self.name
				)
		except ImportError:
			logger.debug("Semantic Cache not available, skipping cache lookup")
		except Exception as e:
			logger.warning(f"⚠️ Semantic cache error (proceeding without cache): {e}")
		
		# === SPEED: Complexity Router (Dynamic Model Selection) ===
		selected_model = model or self.model  # Allow override via parameter
		reasoning_effort = "medium"  # Default
		router_confidence = 0.0
		
		try:
			from app.security.complexity_router import classify_complexity
			
			# Get full classification with model recommendation
			complexity_result = classify_complexity(query)
			
			# Use router-recommended model (gpt-5-mini for simple, gpt-5/gpt-5.1 for complex)
			selected_model = complexity_result.model
			reasoning_effort = complexity_result.reasoning_effort.value
			router_confidence = complexity_result.confidence
			
			logger.info(f"🧠 Complexity Router: {complexity_result.level.value} → model={selected_model}, effort={reasoning_effort}, confidence={router_confidence:.2f}")
		except ImportError:
			logger.debug("Complexity Router not available, using default model")
		except Exception as e:
			logger.warning(f"⚠️ Complexity router error: {e}, using default model")
		
		# Build the prompt with context
		user_message = self._build_prompt(query, context)
		
		try:
			# Import tools
			from app.tools import ALL_TOOLS, TOOL_EXECUTORS
			
			# Build messages with conversation history
			messages = [
				{"role": "system", "content": system_prompt or self._get_system_prompt()}
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
			logger.info(f"Calling OpenAI with model={selected_model}, tools={use_tools}, reasoning_effort={reasoning_effort}")
			
			try:
				# Add timeout to prevent indefinite waiting
				response = await asyncio.wait_for(
					asyncio.to_thread(
						self._client.chat.completions.create,
						model=selected_model,  # ← Use router-selected model
						messages=messages,
						tools=ALL_TOOLS if use_tools else None,
						tool_choice="auto" if use_tools else None,
						temperature=1,
						max_completion_tokens=10000
					),
					timeout=60.0  # 60 second timeout
				)
			except asyncio.TimeoutError:
				logger.error("⏱️ OpenAI call timed out after 60 seconds")
				return AgentResponse(
					content="⏱️ Lo siento, el análisis está tardando más de lo esperado. Por favor, intenta reformular tu pregunta de forma más específica o simplíficala.",
					sources=sources or [],
					metadata={"error": "timeout", "processing_time": 60.0},
					agent_name=self.name
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
				# 🔧 FIX: Use formatted_response instead of raw JSON
				# This prevents technical JSON from being shown to users
				tool_response_content = tool_result.get('formatted_response', json.dumps(tool_result))
				
				messages.append({
					"role": "tool",
					"tool_call_id": tool_call.id,
					"content": tool_response_content  # ← Use formatted response, not raw JSON
				})
				
				# Second call to get final response
				logger.info("Calling OpenAI again with tool result")
				try:
					final_response = await asyncio.wait_for(
						asyncio.to_thread(
							self._client.chat.completions.create,
							model=selected_model,  # ← Use same router-selected model
							messages=messages,
							temperature=1,
							max_completion_tokens=10000
						),
						timeout=60.0  # 60 second timeout
					)
					content = final_response.choices[0].message.content or tool_result.get('formatted_response', '')
				except asyncio.TimeoutError:
					logger.error("⏱️ Second OpenAI call timed out")
					content = tool_result.get('formatted_response', '')
					if not content:
						content = "⏱️ Lo siento, el análisis está tardando más de lo esperado. Intenta reformular tu pregunta."
				logger.info(f"Final content length: {len(content)}")
			else:
				# No function call, use direct response
				content = message.content or ""
				finish_reason = response.choices[0].finish_reason
				if not content:
					logger.warning(f"No content in response. Finish reason: {finish_reason}")
				
				logger.info(f"Direct response content length: {len(content)}")
			
			# Validate output format to ensure no internal JSON is exposed
			from app.security.guardrails import guardrails_system
			if not guardrails_system.validate_output_format(content):
				logger.warning("⚠️ Internal JSON detected in response, sanitizing...")
				# Provide a clean error message instead of exposing internal data
				content = (
					"Lo siento, hubo un problema al formatear la respuesta. "
					"Por favor, intenta reformular tu pregunta de otra manera. "
					"Si el problema persiste, puedes contactar con soporte."
				)
			
			# === SPEED: Store successful response in Semantic Cache ===
			try:
				from app.security.semantic_cache import get_semantic_cache
				semantic_cache = get_semantic_cache()
				await semantic_cache.store(query, content)
			except Exception as e:
				logger.debug(f"Failed to cache response: {e}")
			
			return AgentResponse(
				content=content,
				sources=sources or [],
				metadata={
					"model": selected_model,  # ← Model actually used (from router)
					"base_model": self.model,  # Original model from settings
					"agent": self.name,
					"framework": "openai-api",
					"tool_used": bool(message.tool_calls),
					"current_year": self.current_year,
					"irpf_fiscal_year": self.irpf_fiscal_year,
					"autonomous_quota_year": self.autonomous_quota_year,
					"reasoning_effort": reasoning_effort,
					"router_confidence": router_confidence
				},
				agent_name=self.name
			)
			
		except asyncio.TimeoutError:
			# This catch is for outer-level timeout (shouldn't reach here normally)
			logger.error("⏱️ TaxAgent execution timeout")
			return AgentResponse(
				content="⏱️ Lo siento, el análisis está tardando más de lo esperado. Por favor, intenta reformular tu pregunta o simplificarla.",
				sources=sources or [],
				metadata={"error": "timeout"},
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
			if any(char.isdigit() for char in query):
				requires_tool_hint = f"\n⚠️ ATENCIÓN: Esta pregunta requiere cálculo de cuota de autónomos para {self.autonomous_quota_year}. DEBES usar la herramienta calculate_autonomous_quota.\n"
		
		if any(kw in query_lower for kw in ["irpf", "renta", "cuánto pago de impuestos", "retención", "cuanto pago de impuestos", "retencion"]):
			if any(char.isdigit() for char in query):
				requires_tool_hint = f"\n⚠️ ATENCIÓN: Esta pregunta requiere cálculo de IRPF. Determina el año fiscal correcto antes de llamar calculate_irpf.\n"
		
		# NO agregar hint de search para fechas/plazos - deja que el RAG-first funcione
		
		if context:
			return f"""{requires_tool_hint}Contexto relevante de los documentos oficiales de la AEAT:

{context}

---

Pregunta del usuario:
{query}

🔒 INSTRUCCIONES CRÍTICAS:
1. **USA EXCLUSIVAMENTE la información del contexto anterior** - Es de 2024/2025 y ES VÁLIDA para cálculos de {self.current_year}
2. Para IRPF: usa calculate_irpf AHORA con los datos del contexto (NO busques en web)
3. Para autónomos: usa calculate_autonomous_quota con year={self.autonomous_quota_year}
4. **NUNCA uses search_tax_regulations** a menos que el usuario diga explícitamente: "busca información actualizada" o "consulta la web"
5. **Responde con tono CERCANO y COLOQUIAL** - Como un asesor fiscal amigo, con tuteo y lenguaje natural (NO formal ni técnico)
6. Responde EN LENGUAJE NATURAL (NO JSON ni código técnico)
7. Aclara qué año fiscal usas en la respuesta
8. Incluye aviso de información orientativa
- Incluye un aviso de que esto es información orientativa"""
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

def format_sources_inline(sources: Optional[List[Dict[str, Any]]]) -> str:
	"""
	Format sources as inline compact text (no bullets).
	
	Groups by document and aggregates page numbers.
	Example: "Manual IRPF 2024 (págs. 45, 67), Ley 35/2006 (pág. 12)"
	
	Args:
		sources: List of source dicts with 'document' and 'page' keys
		
	Returns:
		Formatted string or empty string if no sources
	"""
	if not sources:
		return ""
	
	# Group sources by document
	doc_pages = {}
	for source in sources:
		doc_name = source.get("document", "Documento desconocido")
		page = source.get("page", 0)
		
		# Clean document name (remove extensions)
		clean_name = doc_name.replace('.pdf', '').replace('.md', '').strip()
		
		if clean_name not in doc_pages:
			doc_pages[clean_name] = []
		doc_pages[clean_name].append(page)
	
	# Format as inline list
	formatted_sources = []
	for doc_name, pages in doc_pages.items():
		# Sort and deduplicate pages
		unique_pages = sorted(set(p for p in pages if p > 0))
		
		if not unique_pages:
			continue
		
		# Format page numbers
		if len(unique_pages) == 1:
			page_str = f"pág. {unique_pages[0]}"
		elif len(unique_pages) <= 4:
			page_str = f"págs. {', '.join(map(str, unique_pages))}"
		else:
			# Too many pages, show first 3 + "..."
			page_str = f"págs. {', '.join(map(str, unique_pages[:3]))}..."
		
		formatted_sources.append(f"{doc_name} ({page_str})")
	
	if not formatted_sources:
		return ""
	
	# Join with commas
	sources_text = ", ".join(formatted_sources)
	
	return f"\n\n📄 **Fuentes**: {sources_text}"