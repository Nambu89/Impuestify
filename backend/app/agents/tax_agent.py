"""
TaxAgent - Specialized Tax Assistant Agent

Uses Microsoft Agent Framework with Azure AI Foundry.
Designed for extensibility to multi-agent scenarios.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# Microsoft Agent Framework imports
try:
    from agent_framework import ChatAgent
    from agent_framework.azure import AzureOpenAIChatClient
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Agent Framework import failed: {e}")
    AGENT_FRAMEWORK_AVAILABLE = False
    ChatAgent = None
    AzureOpenAIChatClient = None

# Fallback to direct Azure OpenAI
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
    Tax specialist agent using Microsoft Agent Framework.
    
    Provides intelligent responses about Spanish tax regulations
    based on AEAT documentation.
    
    Features:
    - RAG integration for document retrieval
    - Guardrails for safe responses
    - Multi-agent ready architecture
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
            model: OpenAI model name (gpt-5-mini, gpt-5, gpt-4o, gpt-4o-mini, etc.)
            api_key: OpenAI API key
        """
        self.name = name
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        self._agent = None
        self._fallback_client = None
        # TODO: Integrate IRPFCalculator and RegionDetector in future
        # self.irpf_calculator = IRPFCalculator()
        # self.region_detector = RegionDetector()
        
        self._initialize()
    
    def _initialize(self):
        """Initialize the agent with OpenAI client."""
        if self.api_key:
            self._fallback_client = OpenAI(
                api_key=self.api_key
            )
            logger.info(f"TaxAgent '{self.name}' initialized with OpenAI (model: {self.model})")
        else:
            logger.warning("TaxAgent not fully configured - missing OpenAI API key")
    
    async def run(
        self,
        query: str,
        context: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        use_tools: bool = True,
        system_prompt: Optional[str] = None
    ) -> AgentResponse:
        """
        Run the agent with a user query.
        
        Args:
            query: User's question
            context: Retrieved context from RAG
            sources: Source documents for citations
            use_tools: Whether to enable function calling tools (default: True)
            system_prompt: Optional override for system prompt
            
        Returns:
            AgentResponse with answer and metadata
        """
        # Build the prompt with context
        user_message = self._build_prompt(query, context)
        
        try:
            # Force use of fallback client with function calling (Agent Framework doesn't support tools yet)
            if False and self._agent:  # Disabled Agent Framework for function calling
                # Use Microsoft Agent Framework
                response = await self._agent.run(user_message)
                content = response.text or "" # AgentRunResponse has .text property
            elif self._fallback_client:
                # Use fallback Azure OpenAI with function calling
                from app.tools.irpf_calculator_tool import IRPF_CALCULATOR_TOOL, calculate_irpf_tool
                
                messages = [
                    {"role": "system", "content": system_prompt or self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
                
                # First call with tools (if enabled)
                response = self._fallback_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=[IRPF_CALCULATOR_TOOL] if use_tools else None,
                    tool_choice="auto" if use_tools else None,
                    temperature=1,
                    max_completion_tokens=4000
                )
                
                # Check if model wants to call a function
                message = response.choices[0].message
                
                logger.info(f"Azure OpenAI response - has tool_calls: {bool(message.tool_calls)}")
                logger.info(f"Azure OpenAI response - content length: {len(message.content) if message.content else 0}")
                
                if message.tool_calls:
                    # Model wants to use IRPF calculator
                    tool_call = message.tool_calls[0]
                    function_name = tool_call.function.name
                    
                    logger.info(f"Tool called: {function_name}")
                    
                    if function_name == "calculate_irpf":
                        import json
                        function_args = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"Calculating IRPF with args: {function_args}")
                        
                        # Execute the tool
                        tool_result = await calculate_irpf_tool(**function_args)
                        
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
                        final_response = self._fallback_client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            temperature=1,
                            max_completion_tokens=4000
                        )
                        content = final_response.choices[0].message.content or tool_result.get('formatted_response', '')
                        logger.info(f"Final content length: {len(content)}")
                    else:
                        content = message.content or ""
                else:
                    # No function call, use direct response
                    content = message.content or ""
                    finish_reason = response.choices[0].finish_reason
                    if not content:
                        logger.warning(f"No content in response. Finish reason: {finish_reason}")
                    
                    logger.info(f"Direct response content length: {len(content)}")
            else:
                # No fallback client available
                content = "Error: El agente no está configurado correctamente. Verifica las credenciales de Azure."
            
            return AgentResponse(
                content=content,
                sources=sources or [],
                metadata={
                    "model": self.model,
                    "agent": self.name,
                    "framework": "agent-framework" if self._agent else "azure-openai-fallback"
                },
                agent_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            return AgentResponse(
                content=f"Error al procesar la consulta: {str(e)}",
                sources=[],
                metadata={"error": str(e)},
                agent_name=self.name
            )
    
    def _build_prompt(self, query: str, context: Optional[str] = None) -> str:
        """Build the user prompt with optional context."""
        if context:
            return f"""Contexto relevante de los documentos oficiales de la AEAT:

{context}

---

Pregunta del usuario:
{query}

Instrucciones:
- Si la pregunta requiere un cálculo IRPF específico (con cantidad y ubicación), usa la herramienta de cálculo disponible.
- Para otras consultas, responde basándote en el contexto proporcionado.
- Siempre incluye un aviso de que esto es información orientativa."""
        else:
            return query
    
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
