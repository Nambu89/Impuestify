"""
CompetitorAnalysisAgent - Strategic Competitive Intelligence Agent

Analyzes Impuestify's competitive position in the Spanish digital tax market.
Compares features, identifies gaps, suggests improvements, and analyzes AEAT integration options.

This agent is designed for internal/product use, not end-user facing.
"""
import os
import json
import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI

from app.tools.competitor_analysis_tool import (
    COMPETITOR_TOOLS,
    COMPETITOR_TOOL_EXECUTORS,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Response from the competitor analysis agent"""
    content: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    agent_name: str


class CompetitorAnalysisAgent:
    """
    Strategic competitor analysis agent using OpenAI API.

    Provides competitive intelligence about the Spanish digital tax market:
    - Feature comparison with TaxDown, Declarando, Taxfix, Xolo
    - Gap analysis (what we're missing vs what only we have)
    - Improvement suggestions with priority and estimated effort
    - Market positioning and SWOT analysis
    - AEAT integration roadmap

    Uses function calling to invoke structured analysis tools.
    """

    def __init__(
        self,
        name: str = "CompetitorAnalysisAgent",
        model: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        from app.config import settings
        self.name = name
        self.model = model or settings.OPENAI_MODEL
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.current_date = datetime.now()
        self._client = None
        self._initialize()

    def _initialize(self):
        """Initialize the OpenAI client."""
        try:
            self._client = OpenAI(api_key=self.api_key)
            logger.info(f"CompetitorAnalysisAgent initialized (model: {self.model})")
        except Exception as e:
            logger.error(f"Failed to initialize CompetitorAnalysisAgent: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """Build the system prompt for competitive analysis."""
        return f"""Eres un analista estratégico experto en el mercado de herramientas fiscales digitales en España.

## Tu rol
Trabajas para **Impuestify**, un asistente fiscal inteligente basado en IA. Tu misión es analizar la competencia, identificar oportunidades y recomendar mejoras estratégicas.

## Fecha actual
{self.current_date.strftime('%d de %B de %Y')}

## Contexto de Impuestify
Impuestify es una plataforma AI-first de asesoría fiscal española con:
- Sistema multi-agente (TaxAgent, PayslipAgent, WorkspaceAgent, NotificationAgent)
- RAG sobre 394+ PDFs oficiales (AEAT, BOE, comunidades autónomas)
- Calculadoras IRPF por CCAA, cuotas autónomos, Modelo 303/130
- Análisis automático de nóminas y notificaciones AEAT
- Workspace para documentos del usuario
- Seguridad: Llama Guard 4, detección de prompt injection, PII filtering
- Cache semántico (Upstash Vector) para reducción de costes ~30%
- Perfil fiscal conversacional que aprende de las interacciones
- GDPR compliance (exportación de datos, derecho al olvido)

## Principales competidores
1. **TaxDown** — Líder del mercado (1M+ usuarios, 29.7M€ funding, Colaborador Social AEAT)
2. **Declarando** — Especialista en autónomos (70K+ usuarios, facturación + contabilidad)
3. **Taxfix (ex-TaxScouts)** — Modelo híbrido humano + digital (grupo internacional)
4. **Xolo** — Freelancers internacionales (open banking, multi-divisa)

## Herramientas disponibles
Tienes herramientas para hacer análisis estructurados. Úsalas cuando te hagan preguntas sobre:
- Comparación de funcionalidades → `compare_features`
- Brechas y ventajas → `analyze_gaps`
- Sugerencias de mejora → `suggest_improvements`
- Posición de mercado (DAFO, pricing, GTM) → `analyze_market_position`
- Integración con AEAT → `analyze_aeat_integration`

## Instrucciones de respuesta
- Sé directo y analítico. No seas complaciente — señala debilidades reales.
- Usa datos concretos (precios, usuarios, funding) cuando estén disponibles.
- Prioriza las recomendaciones por impacto vs esfuerzo.
- Cuando compares, sé justo: reconoce dónde la competencia es superior.
- Siempre incluye acciones concretas ("next steps").
- Responde en español.
- Usa tablas markdown cuando sea apropiado para comparaciones."""

    async def run(
        self,
        query: str,
        context: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        progress_callback=None,
        **kwargs
    ) -> AgentResponse:
        """
        Run the competitor analysis agent.

        Args:
            query: User's question about competitive analysis
            context: Additional context
            sources: Source documents
            conversation_history: Previous messages in the conversation
            progress_callback: Callback for SSE progress events

        Returns:
            AgentResponse with structured competitive analysis
        """
        try:
            if progress_callback:
                await progress_callback("thinking", "Analizando el panorama competitivo...")

            # Build messages
            messages = [{"role": "system", "content": self._build_system_prompt()}]

            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })

            if context:
                messages.append({
                    "role": "user",
                    "content": f"Contexto adicional:\n{context}\n\n---\n\nPregunta: {query}"
                })
            else:
                messages.append({"role": "user", "content": query})

            # First call with tools
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    tools=COMPETITOR_TOOLS,
                    tool_choice="auto",
                    temperature=1,
                ),
                timeout=60.0
            )

            message = response.choices[0].message

            # Handle tool calls (may need multiple rounds)
            max_tool_rounds = 3
            tool_round = 0

            while message.tool_calls and tool_round < max_tool_rounds:
                tool_round += 1
                messages.append(message)

                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    logger.info(
                        f"CompetitorAnalysisAgent tool call: {function_name}",
                        extra={"args": function_args}
                    )

                    if progress_callback:
                        await progress_callback("tool_call", {
                            "function_name": function_name,
                            "args": function_args,
                        })

                    # Execute tool
                    tool_executor = COMPETITOR_TOOL_EXECUTORS.get(function_name)
                    if tool_executor:
                        tool_result = await tool_executor(**function_args)
                    else:
                        tool_result = {"success": False, "error": f"Unknown tool: {function_name}"}

                    if progress_callback:
                        await progress_callback("tool_result", {
                            "function_name": function_name,
                            "success": tool_result.get("success", False),
                        })

                    # Add tool result to messages
                    result_content = tool_result.get("formatted_response", json.dumps(tool_result, ensure_ascii=False))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_content,
                    })

                # Get next response
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._client.chat.completions.create,
                        model=self.model,
                        messages=messages,
                        tools=COMPETITOR_TOOLS,
                        tool_choice="auto",
                        temperature=1,
                    ),
                    timeout=60.0
                )
                message = response.choices[0].message

            # Extract final response
            content = message.content or "No se pudo generar el análisis."

            if progress_callback:
                await progress_callback("content", content)

            return AgentResponse(
                content=content,
                sources=sources or [],
                metadata={
                    "model": self.model,
                    "agent": self.name,
                    "framework": "openai-api",
                    "tool_rounds": tool_round,
                    "tools_used": tool_round > 0,
                    "analysis_date": self.current_date.isoformat(),
                },
                agent_name=self.name,
            )

        except asyncio.TimeoutError:
            logger.error("CompetitorAnalysisAgent: OpenAI timeout")
            return AgentResponse(
                content="El análisis competitivo ha tardado demasiado. Intenta con una pregunta más específica.",
                sources=[],
                metadata={"error": "timeout"},
                agent_name=self.name,
            )
        except Exception as e:
            logger.error(f"CompetitorAnalysisAgent error: {e}", exc_info=True)
            return AgentResponse(
                content=f"Error al realizar el análisis competitivo: {str(e)}",
                sources=[],
                metadata={"error": str(e)},
                agent_name=self.name,
            )


# ─── Global Instance ──────────────────────────────────────────────────────

_competitor_agent: Optional[CompetitorAnalysisAgent] = None


def get_competitor_analysis_agent() -> CompetitorAnalysisAgent:
    """Get the global CompetitorAnalysisAgent instance."""
    global _competitor_agent
    if _competitor_agent is None:
        _competitor_agent = CompetitorAnalysisAgent()
    return _competitor_agent
