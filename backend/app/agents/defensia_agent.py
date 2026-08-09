"""DefensIA Chat Agent (T2B-012).

Agente conversacional para refinar el brief del usuario antes del análisis
jurídico automático. Pasa todo input por el pipeline de guardrails existente
del repo (llamaguard, prompt injection, PII) antes de invocar a OpenAI.

Regla #1 del producto DefensIA: el sistema NO arranca análisis jurídico hasta
que el usuario escriba su brief explícitamente. El chat agent solo ayuda al
usuario a articular su necesidad defensiva — nunca genera citas normativas ni
dictámenes vinculantes (esos los produce el motor de reglas + RAG verificador
aguas abajo).

Contrato:
- Modelo: ``gpt-5-mini`` con ``temperature=1`` y ``max_completion_tokens=1024``
  (únicos valores soportados por gpt-5-mini en el repo).
- Guardrails: ``is_safe=False`` con ``risk_level`` en ``{"high", "critical"}``
  bloquea la llamada a OpenAI y devuelve un mensaje safe-fail determinista.
- Error handling: cualquier excepción de OpenAI se atrapa y yields un mensaje
  técnico en español — nunca crashea el stream.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.config import settings
from app.security import guardrails_system

logger = logging.getLogger(__name__)


# Disclaimer canónico alineado con ``defensia_writer_service`` y
# ``defensia_export_service``. Replicado aquí para evitar import circular
# agent <-> services. Si se modifica, actualizar los 3 sitios.
DISCLAIMER_CANONICO = (
    "DefensIA es una herramienta de asistencia técnica que no constituye "
    "asesoramiento jurídico vinculante. Revisa y adapta el contenido antes "
    "de presentarlo ante cualquier administración."
)


# System prompt — los primeros 100 chars del disclaimer van literal al inicio
# para que el LLM nunca olvide el límite de responsabilidad.
SYSTEM_PROMPT = f"""Eres el asistente de defensa fiscal de {settings.BRAND_NAME}.

Ayudas a contribuyentes que han recibido un requerimiento, propuesta de
liquidación, liquidación firme, propuesta o resolución sancionadora del
AEAT u otra Administración tributaria.

Respondes en español, con tildes correctas, tono profesional y cercano.

Cuando el usuario te plantee una duda concreta (plazos, vías de recurso,
documentación a aportar, motivación, fundamentos), respóndela
directamente y de forma útil. Si la pregunta es vaga, pide los datos
mínimos que necesitas: tributo (IRPF, IVA, ISD, ITP, Plusvalía
Municipal), ejercicio fiscal y qué acto concreto ha recibido.

Cuando cites artículos o jurisprudencia, hazlo solo si estás
razonablemente seguro; en caso de duda, indica que el análisis con
citas verificadas lo produce el motor de reglas + RAG.

Si el usuario pide un juicio vinculante ("¿debo recurrir?", "¿voy a
ganar?"), recuérdale que DefensIA es una herramienta de asistencia y
que para decisiones firmes debe consultar a un letrado o asesor fiscal
colegiado.

Alcance v1: verificación, comprobación limitada, procedimiento
sancionador, recurso de reposición y reclamación al TEAR (abreviado y
general). Si el caso parece de inspección, apremio, TEAC, contencioso
o Impuesto sobre Sociedades, dilo explícitamente.

Cierra siempre con el disclaimer corto: {DISCLAIMER_CANONICO[:100]}
"""


# Mensaje safe-fail determinista cuando guardrails flaggea input como
# high/critical. No revela detalles del motivo (defensa en profundidad).
SAFE_FAIL_MESSAGE = (
    "Lo siento, no puedo procesar esa consulta. Para utilizar DefensIA, "
    "describe tu situación fiscal defensiva con tus propias palabras: qué "
    "tributo, qué ejercicio y qué acto de la Administración has recibido."
)


# Mensaje técnico cuando OpenAI falla. Evita filtrar detalles del error al
# usuario final y nunca crashea el stream SSE aguas arriba.
TECHNICAL_ERROR_MESSAGE = (
    "Ha ocurrido un error técnico procesando tu consulta. Inténtalo de nuevo "
    "en unos momentos. Si el problema persiste, contacta con soporte."
)


class DefensiaAgent:
    """Chat agent conversacional de DefensIA.

    Espeja el patrón de ``TaxAgent`` pero especializado para refinar el brief
    del usuario antes del análisis jurídico. Integra el pipeline de
    guardrails existente y bloquea risk_level high/critical antes de llamar
    a OpenAI.
    """

    # Aligned with TaxAgent (the chat fiscal agent that DOES work end to
    # end in this same backend). Switching MODEL away from gpt-5-mini was
    # a wrong path — TaxAgent uses gpt-5-mini and streams content fine.
    # The DefensIA-specific failure was not the model, it was the
    # restrictive SYSTEM_PROMPT plus the lack of reasoning_effort hint.
    MODEL: str = "gpt-5-mini"
    MAX_COMPLETION_TOKENS: int = 10000
    TEMPERATURE: int = 1  # único valor soportado por gpt-5 family
    OPENAI_TIMEOUT_S: float = 60.0  # match TaxAgent's outer timeout
    REASONING_EFFORT: str = "minimal"  # force visible output, less hidden reasoning

    def __init__(self, api_key: str | None = None):
        """Inicializa el agent con un cliente AsyncOpenAI.

        Args:
            api_key: OpenAI API key. Si es None, usa ``settings.OPENAI_API_KEY``.
        """
        resolved_key = api_key or settings.OPENAI_API_KEY
        if not resolved_key:
            logger.warning(
                "DefensiaAgent inicializado sin OPENAI_API_KEY — llamadas " "al LLM fallarán."
            )
        self._client = AsyncOpenAI(api_key=resolved_key)

    # ------------------------------------------------------------------
    # Guardrails pipeline
    # ------------------------------------------------------------------

    def _check_input_safety(self, user_message: str) -> tuple[bool, str | None]:
        """Ejecuta el pipeline de guardrails sobre el mensaje del usuario.

        Bloquea únicamente risk_level ``high`` y ``critical`` — niveles
        ``medium`` o inferiores se permiten para no ser excesivamente
        restrictivos en un chat de refinamiento de brief.

        Fail-open ante excepción interna del módulo guardrails: no bloqueamos
        al usuario por un bug del detector, solo lo logeamos como warning.
        Esto es consistente con el patrón de ``llama_guard`` (fails open).

        Returns:
            ``(is_safe, reason_or_none)``.
        """
        try:
            result = guardrails_system.validate_input(user_message)
            if not result.is_safe and result.risk_level in ("high", "critical"):
                violation = result.violations[0] if result.violations else "unsafe"
                return False, f"guardrails_{result.risk_level}: {violation}"
        except Exception as exc:  # noqa: BLE001 — fail-open deliberado
            logger.warning("Error en guardrails_system.validate_input — fail-open: %s", exc)
        return True, None

    # ------------------------------------------------------------------
    # Streaming chat
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        message: str,
        chat_history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        """Stream de respuesta del agent — yields chunks de texto.

        Pipeline:
            1. Input safety check (guardrails). Si falla → safe-fail + return.
            2. Construye mensajes (system + historial + user).
            3. Stream de OpenAI chat.completions con parámetros del repo.
            4. Cualquier excepción → mensaje técnico, nunca crash.

        Args:
            message: Texto del usuario.
            chat_history: Lista opcional de mensajes previos con forma
                ``[{"role": "user"|"assistant", "content": str}, ...]``.

        Yields:
            Chunks de texto (str) de la respuesta del modelo.
        """
        # Trace markers (ERROR level so they survive any log filter).
        logger.error("DEFENSIA_AGENT_TRACE step=enter msg_len=%d", len(message or ""))

        # 1. Safety check
        is_safe, reason = self._check_input_safety(message)
        logger.error("DEFENSIA_AGENT_TRACE step=after_safety is_safe=%s", is_safe)
        if not is_safe:
            logger.warning("DefensIA agent rechaza input: %s", reason)
            yield SAFE_FAIL_MESSAGE
            return

        # 2. Construir mensajes
        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": message})
        logger.error("DEFENSIA_AGENT_TRACE step=before_openai model=%s", self.MODEL)

        # 3. Stream desde OpenAI — replicating TaxAgent's pattern exactly:
        #    outer wait_for 60s on create, per-chunk wait_for 30s. We add
        #    reasoning_effort="minimal" because the model otherwise burns
        #    its tokens on hidden reasoning and emits zero content.
        try:
            stream = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                    temperature=self.TEMPERATURE,
                    max_completion_tokens=self.MAX_COMPLETION_TOKENS,
                    stream=True,
                    reasoning_effort=self.REASONING_EFFORT,
                ),
                timeout=self.OPENAI_TIMEOUT_S,
            )
            logger.debug("DEFENSIA_AGENT_TRACE step=stream_obtained")
            chunks_seen = 0
            content_chunks = 0
            last_finish_reason: str | None = None
            async for chunk in stream:
                chunks_seen += 1
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.finish_reason:
                    last_finish_reason = choice.finish_reason
                delta_content = choice.delta.content
                if delta_content:
                    content_chunks += 1
                    yield delta_content
            logger.debug(
                "DEFENSIA_AGENT_TRACE step=stream_done chunks=%d content_chunks=%d "
                "finish_reason=%s model=%s max_tokens=%d",
                chunks_seen,
                content_chunks,
                last_finish_reason,
                self.MODEL,
                self.MAX_COMPLETION_TOKENS,
            )
            if content_chunks == 0:
                logger.warning(
                    "DefensIA emitted zero content chunks. Likely cause: "
                    "model burned the entire token budget on reasoning before "
                    "producing any visible output. Falling back to a generic "
                    "guidance message so the UI is not left blank."
                )
                yield (
                    "No he podido componer una respuesta esta vez. ¿Puedes "
                    "reformular tu consulta indicando: tributo afectado, "
                    "ejercicio fiscal y qué acto de la Administración has "
                    "recibido (requerimiento, propuesta de liquidación, "
                    "sanción, etc.)?"
                )
        except TimeoutError:
            logger.error(
                "DEFENSIA_AGENT_TRACE step=openai_timeout after=%ss model=%s",
                self.OPENAI_TIMEOUT_S,
                self.MODEL,
            )
            yield (
                "El servicio de IA tardó demasiado en responder. Vuelve a "
                "intentarlo en unos segundos; si el problema persiste, "
                "contacta con soporte."
            )
        except Exception as exc:  # noqa: BLE001 — degradación graceful
            logger.error("DefensIA agent OpenAI error: %s", exc, exc_info=True)
            yield TECHNICAL_ERROR_MESSAGE
