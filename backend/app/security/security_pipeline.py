"""
Security Pipeline — Defense-in-depth gate BEFORE the LLM.

Single entry point: SecurityPipeline.check(question, user_id) -> PipelineResult

Layers (in order, short-circuit on first reject):
  1. Sanitization (control chars, zero-width, normalize)
  2. Regex pattern guard (ES + EN: jailbreak, role-inject, SQLi, code, shell)
  3. Llama Prompt Guard 2 (Groq, jailbreak/injection)
  4. PII detector (Llama Guard 4 / gpt-oss-safeguard, S7 privacy)
  5. SQL injection validator (existing)
  6. Topic classifier (llama-3.1-8b-instant, fiscal whitelist)

ANY layer reject -> short-circuit + audit log + canned rejection message.
FAIL CLOSED: if any classifier is unreachable, treat as suspicious where
the layer's nature requires it (topic classifier especially).
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from app.security.audit_logger import AuditEventType, audit_logger
from app.security.pii_detector import pii_detector
from app.security.prompt_injection import prompt_injection_filter
from app.security.sql_injection import sql_validator
from app.security.topic_classifier import TopicContext, check_fiscal_topic

logger = logging.getLogger(__name__)


def _rejection_message() -> str:
    from app.config import settings

    return (
        f"Soy {settings.BRAND_NAME}, tu asistente de fiscalidad española. Solo puedo "
        "responder preguntas sobre IRPF, IVA, modelos AEAT, deducciones, autónomos y "
        "otros temas tributarios españoles. Reformula tu pregunta dentro de este ámbito."
    )


# Backward-compat alias (some tests import REJECTION_MESSAGE)
REJECTION_MESSAGE = _rejection_message()


@dataclass
class PipelineResult:
    is_safe: bool
    layer: str  # which layer rejected (or 'all_clear')
    reason: str  # human-readable reason
    matched_patterns: list[str] = field(default_factory=list)
    rejection_message: str | None = None
    sanitized_text: str = ""


# Strict greetings allowed without classifier (avoid blocking "hola")
_GREETING_PATTERNS = [
    re.compile(
        r"^\s*(hola|buenas|buenos\s+días|buenas\s+tardes|buenas\s+noches|qué\s+tal|hey|hi|hello)\s*[!.?¿¡]?\s*$",
        re.IGNORECASE,
    ),
]

# Hard size limits for user input. RAG chunks use sanitize_text(no cap).
MAX_LENGTH = 4000  # chars
MIN_LENGTH = 2  # chars (we already short-circuit on greetings)


# Pre-compiled regexes for sanitization (zero-width + bidi + control).
# Using \uXXXX escapes (not raw chars) so the file stays ASCII-safe.
_ZERO_WIDTH_RE = re.compile("[​-‏ -‮⁠-⁯]")
_CONTROL_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _is_greeting(text: str) -> bool:
    return any(p.match(text.strip()) for p in _GREETING_PATTERNS)


def sanitize_text(text: str, max_length: int | None = None) -> str:
    """
    Strip zero-width and control chars, normalize unicode (NFKC).

    Public helper used by both:
      - User input via the security pipeline (cap = MAX_LENGTH).
      - RAG document chunks at ingestion (no cap — chunks may legitimately
        run thousands of characters; pass max_length=None).
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = _ZERO_WIDTH_RE.sub("", text)
    text = _CONTROL_RE.sub("", text)
    text = text.strip()
    if max_length is not None and len(text) > max_length:
        text = text[:max_length]
    return text


def _sanitize(text: str) -> str:
    """User-input sanitizer: enforces the pipeline hard length cap."""
    return sanitize_text(text, max_length=MAX_LENGTH)


class SecurityPipeline:
    """
    Multi-layer security pipeline. All layers run BEFORE the LLM is called.

    Layers can be skipped via constructor flags for tests. By default
    everything is on.
    """

    def __init__(
        self,
        enable_prompt_injection: bool = True,
        enable_pii: bool = True,
        enable_sqli: bool = True,
        enable_topic_classifier: bool = True,
    ):
        self.enable_prompt_injection = enable_prompt_injection
        self.enable_pii = enable_pii
        self.enable_sqli = enable_sqli
        self.enable_topic_classifier = enable_topic_classifier

    def check(
        self,
        question: str,
        user_id: str | None = None,
        context: TopicContext | None = None,
    ) -> PipelineResult:
        """
        Run all enabled layers in order. Short-circuit on first reject.

        Returns PipelineResult with is_safe=False on any reject. The caller
        should NOT invoke the LLM if is_safe is False.

        ``context`` is forwarded only to the topic classifier (layer 6).
        Layers 1-5 (sanitization, prompt injection, SQLi, PII) are immune
        to any context the caller supplies — keeping the security posture
        identical regardless of workspace state.
        """
        # ── Layer 1: Sanitization & length ──
        sanitized = _sanitize(question or "")
        if len(sanitized) < MIN_LENGTH:
            return self._reject(
                layer="sanitization",
                reason="Pregunta vacía o demasiado corta",
                sanitized=sanitized,
                user_id=user_id,
            )
        if len(sanitized) >= MAX_LENGTH:
            # We truncated above; truncation itself is suspicious for a chat
            return self._reject(
                layer="sanitization",
                reason="Pregunta excede el límite máximo de caracteres",
                sanitized=sanitized,
                user_id=user_id,
            )

        # Greetings bypass classifier and prompt injection — they're harmless
        # and the agent will respond with a system tour.
        if _is_greeting(sanitized):
            return PipelineResult(
                is_safe=True,
                layer="greeting_bypass",
                reason="Saludo permitido",
                sanitized_text=sanitized,
            )

        # ── Layer 2 & 3: Prompt injection (regex + Llama Prompt Guard) ──
        if self.enable_prompt_injection:
            inj = prompt_injection_filter.check(sanitized)
            if not inj.is_safe:
                return self._reject(
                    layer="prompt_injection",
                    reason=f"Intento de inyección o cambio de rol: {', '.join(inj.matched_patterns[:3])}",
                    matched=inj.matched_patterns,
                    sanitized=sanitized,
                    user_id=user_id,
                )

        # ── Layer 4: SQL injection (deterministic regex) ──
        if self.enable_sqli:
            try:
                sqli_result = sql_validator.validate_user_input(sanitized)
                if not sqli_result.is_safe and sqli_result.risk_level in ("high", "critical"):
                    return self._reject(
                        layer="sql_injection",
                        reason=f"Patrón SQL injection detectado (risk={sqli_result.risk_level})",
                        sanitized=sanitized,
                        user_id=user_id,
                    )
            except Exception as e:
                logger.warning(f"SQL validator error (non-blocking): {e}")

        # ── Layer 5: PII detection ──
        if self.enable_pii:
            try:
                pii_result = pii_detector.detect(sanitized)
                if pii_result.has_pii:
                    return self._reject(
                        layer="pii",
                        reason="La pregunta contiene datos personales sensibles. Por favor, no incluyas DNI, IBAN, números de teléfono u otros datos identificativos en el chat.",
                        matched=pii_result.detected_types,
                        sanitized=sanitized,
                        user_id=user_id,
                    )
            except Exception as e:
                logger.warning(f"PII detector error (non-blocking): {e}")

        # ── Layer 6: Topic classifier (HARD whitelist) ──
        # In DEMO_MODE we skip this layer: demo deploys often run without a
        # working Groq key and the classifier fails closed (rejects everything).
        # Demo content is bounded by RAG_TERRITORY_LOCK + restricted Stripe gate.
        from app.config import settings as _settings

        if self.enable_topic_classifier and not _settings.DEMO_MODE:
            topic = check_fiscal_topic(sanitized, context=context)
            if not topic.is_fiscal:
                return self._reject(
                    layer="topic_classifier",
                    reason=f"Pregunta fuera del ámbito fiscal español: {topic.reason}",
                    matched=[topic.classifier],
                    sanitized=sanitized,
                    user_id=user_id,
                )

        # All layers passed
        return PipelineResult(
            is_safe=True,
            layer="all_clear",
            reason="OK",
            sanitized_text=sanitized,
        )

    def _reject(
        self,
        layer: str,
        reason: str,
        sanitized: str = "",
        matched: list[str] | None = None,
        user_id: str | None = None,
    ) -> PipelineResult:
        # Audit log — map pipeline layer to existing audit event types
        try:
            event_type = (
                AuditEventType.SECURITY_PII_DETECTED
                if layer == "pii"
                else AuditEventType.SECURITY_INJECTION_ATTEMPT
            )
            audit_logger.log(
                event_type=event_type,
                user_id=user_id,
                details={
                    "layer": layer,
                    "reason": reason,
                    "matched": matched or [],
                    "question_len": len(sanitized),
                },
                severity="warning",
            )
        except Exception as e:
            logger.error(f"Audit log failed (non-blocking): {e}")

        logger.warning(f"SECURITY BLOCK [{layer}]: {reason}")
        return PipelineResult(
            is_safe=False,
            layer=layer,
            reason=reason,
            matched_patterns=matched or [],
            rejection_message=_rejection_message(),
            sanitized_text=sanitized,
        )


# Global instance
security_pipeline = SecurityPipeline()
