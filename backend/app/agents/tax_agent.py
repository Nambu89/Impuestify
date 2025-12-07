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
    from agent_framework import Agent, AgentConfig
    from agent_framework.models import AzureOpenAIModel
    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False
    Agent = None
    AgentConfig = None
    AzureOpenAIModel = None

# Fallback to direct Azure OpenAI
from openai import AzureOpenAI

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
    
    SYSTEM_PROMPT = """Eres TaxIA, un asistente fiscal especializado en normativa tributaria española.

Tu rol es ayudar a los usuarios a entender sus obligaciones fiscales basándote ÚNICAMENTE en la documentación oficial de la AEAT (Agencia Estatal de Administración Tributaria).

## Reglas estrictas:
1. SOLO responde preguntas sobre fiscalidad española
2. Basa tus respuestas ÚNICAMENTE en el contexto proporcionado
3. Si no tienes información suficiente, indícalo claramente
4. NO inventes información ni hagas suposiciones
5. Cita las fuentes (documento y página) cuando sea posible
6. Usa un lenguaje claro y accesible
7. NUNCA proporciones asesoramiento para evadir impuestos

## Formato de respuesta:
**Veredicto:** [Sí/No/Depende] - [Resumen en una línea]

**Explicación:** [Explicación detallada basada en el contexto]

**Fuentes:** [Documentos citados]

**Aviso:** Esto es información orientativa. Consulta con un asesor fiscal para tu caso particular."""

    def __init__(
        self,
        name: str = "TaxAgent",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        """
        Initialize TaxAgent.
        
        Args:
            name: Agent name
            model: Azure OpenAI deployment name
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint
            api_version: API version
        """
        self.name = name
        self.model = model or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self.endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
        
        self._agent = None
        self._fallback_client = None
        
        self._initialize()
    
    def _initialize(self):
        """Initialize the agent with Microsoft Agent Framework or fallback."""
        if AGENT_FRAMEWORK_AVAILABLE and self.api_key and self.endpoint:
            try:
                # Configure Azure OpenAI model for Agent Framework
                model_config = AzureOpenAIModel(
                    deployment=self.model,
                    api_key=self.api_key,
                    endpoint=self.endpoint,
                    api_version=self.api_version
                )
                
                # Create agent with configuration
                self._agent = Agent(
                    name=self.name,
                    model=model_config,
                    instructions=self.SYSTEM_PROMPT,
                    config=AgentConfig(
                        temperature=0.2,
                        max_tokens=1200,
                        # Enable tools for future expansion
                        tools=[]
                    )
                )
                
                logger.info(f"TaxAgent '{self.name}' initialized with Microsoft Agent Framework")
                return
                
            except Exception as e:
                logger.warning(f"Agent Framework initialization failed: {e}, using fallback")
        
        # Fallback to direct Azure OpenAI client
        if self.api_key and self.endpoint:
            self._fallback_client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint
            )
            logger.info(f"TaxAgent '{self.name}' initialized with Azure OpenAI fallback")
        else:
            logger.warning("TaxAgent not fully configured - missing Azure credentials")
    
    async def run(
        self,
        query: str,
        context: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> AgentResponse:
        """
        Run the agent with a user query.
        
        Args:
            query: User's question
            context: Retrieved context from RAG
            sources: Source documents for citations
            
        Returns:
            AgentResponse with answer and metadata
        """
        # Build the prompt with context
        user_message = self._build_prompt(query, context)
        
        try:
            if self._agent:
                # Use Microsoft Agent Framework
                response = await self._agent.run(user_message)
                content = response.content
            elif self._fallback_client:
                # Use fallback Azure OpenAI
                response = self._fallback_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.2,
                    max_tokens=1200
                )
                content = response.choices[0].message.content or ""
            else:
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

Responde basándote únicamente en el contexto proporcionado."""
        else:
            return query
    
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
