"""
Azure AI Foundry LLM Client for TaxIA

Provides integration with Azure OpenAI Service (GPT-5 mini and other models).
Uses the openai library with Azure endpoints.

DEPRECATED: Prefer using app.agents.TaxAgent for new implementations.
The TaxAgent class uses Microsoft Agent Framework with multi-agent support.
"""
import os
import logging
import warnings
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from openai import AzureOpenAI

logger = logging.getLogger(__name__)

# Deprecation warning
warnings.warn(
    "AzureLLMClient is deprecated. Use app.agents.TaxAgent instead.",
    DeprecationWarning,
    stacklevel=2
)


@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class AzureLLMClient:
    """
    Client for Azure AI Foundry (Azure OpenAI Service).
    
    Supports GPT-5 mini, GPT-4o, and other Azure-hosted models.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: Optional[str] = None
    ):
        """
        Initialize Azure LLM client.
        
        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            deployment: Model deployment name
            api_version: API version
        """
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self.endpoint = endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.deployment = deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
        self.api_version = api_version or os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
        
        self._client: Optional[AzureOpenAI] = None
        
        if not all([self.api_key, self.endpoint]):
            logger.warning("Azure OpenAI credentials not fully configured")
    
    def _get_client(self) -> AzureOpenAI:
        """Get or create the Azure OpenAI client."""
        if self._client is None:
            if not all([self.api_key, self.endpoint]):
                raise ValueError("Azure OpenAI API key and endpoint are required")
            
            self._client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint
            )
            logger.info(f"Azure OpenAI client initialized with deployment: {self.deployment}")
        
        return self._client
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1200,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API
            
        Returns:
            LLMResponse with generated content
        """
        client = self._get_client()
        
        try:
            response = client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            choice = response.choices[0]
            
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                finish_reason=choice.finish_reason or "stop"
            )
            
        except Exception as e:
            logger.error(f"Azure OpenAI API error: {e}")
            raise
    
    def generate_with_context(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1200
    ) -> LLMResponse:
        """
        Generate a response with RAG context.
        
        Args:
            query: User's question
            context: Retrieved context from documents
            system_prompt: Optional system prompt override
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            LLMResponse with generated content
        """
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""Contexto relevante de los documentos:
{context}

Pregunta del usuario:
{query}

Responde basándote únicamente en el contexto proporcionado. Si la información no está disponible en el contexto, indícalo claramente."""}
        ]
        
        return self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for TaxIA."""
        return """Eres TaxIA, un asistente fiscal especializado en normativa tributaria española.

Tu rol es ayudar a los usuarios a entender sus obligaciones fiscales basándote ÚNICAMENTE en la documentación oficial de la AEAT (Agencia Estatal de Administración Tributaria).

Reglas estrictas:
1. SOLO responde preguntas sobre fiscalidad española
2. Basa tus respuestas ÚNICAMENTE en el contexto proporcionado
3. Si no tienes información suficiente, indícalo claramente
4. NO inventes información ni hagas suposiciones
5. Cita las fuentes (documento y página) cuando sea posible
6. Usa un lenguaje claro y accesible
7. NUNCA proporciones asesoramiento para evadir impuestos

Formato de respuesta:
**Veredicto corto:** [Sí/No/Depende] - [Resumen en una línea]
**Explicación:** [Explicación detallada basada en el contexto]
**Fuentes:** [Documentos citados]
**Aviso:** Esto es información orientativa. Consulta con un asesor fiscal para tu caso particular."""


# Global client instance
_llm_client: Optional[AzureLLMClient] = None


def get_llm_client() -> AzureLLMClient:
    """
    Get the global LLM client instance.
    
    Returns:
        AzureLLMClient instance
    """
    global _llm_client
    
    if _llm_client is None:
        _llm_client = AzureLLMClient()
    
    return _llm_client
