"""
PII (Personally Identifiable Information) Detector for TaxIA

Detects and masks sensitive personal information in user inputs
to protect privacy and comply with data protection regulations.
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass

from app.config import settings  # ← FIX: Import settings at module level

logger = logging.getLogger(__name__)

# Texts longer than this skip the Groq call entirely and go straight to the
# deterministic regex scanner. Reasons:
#   1. Groq `gpt-oss-safeguard-20b` rejects requests over its context window
#      with HTTP 413 (observed in prod logs 2026-05-07).
#   2. Long inputs are usually pasted documents — the regex catches the
#      high-value PII (DNI, IBAN, email, phone) without spending Groq quota.
#   3. Latency: avoids a 2-3s LLM call when the user is just pasting their
#      payslip into chat.
_REGEX_FALLBACK_THRESHOLD = 3000


@dataclass
class PIIDetectionResult:
    """Result of PII detection"""

    has_pii: bool
    detected_types: list[str]
    masked_text: str
    original_text: str
    detections: dict[str, list[str]]


class PIIDetector:
    """
    Detector for Spanish PII patterns.

    Detects:
    - DNI (Documento Nacional de Identidad)
    - NIE (Número de Identidad de Extranjero)
    - Phone numbers (Spanish format)
    - Email addresses
    - IBAN (Spanish bank accounts)
    - Credit/debit card numbers
    - Social Security numbers
    - Postal codes
    """

    # PII patterns for Spanish context
    PII_PATTERNS = {
        "dni": {
            "pattern": r"\b\d{8}\s*[-]?\s*[A-Za-z]\b",
            "mask": "[DNI_OCULTO]",
            "description": "DNI español",
        },
        "nie": {
            "pattern": r"\b[XYZxyz]\s*[-]?\s*\d{7}\s*[-]?\s*[A-Za-z]\b",
            "mask": "[NIE_OCULTO]",
            "description": "NIE extranjero",
        },
        "phone": {
            "pattern": r"\b(?:\+34|0034)?\s*[6789]\d{2}\s*\d{3}\s*\d{3}\b",
            "mask": "[TELEFONO_OCULTO]",
            "description": "Teléfono español",
        },
        "email": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "mask": "[EMAIL_OCULTO]",
            "description": "Correo electrónico",
        },
        "iban": {
            "pattern": r"\b[A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",
            "mask": "[IBAN_OCULTO]",
            "description": "Cuenta bancaria IBAN",
        },
        "spanish_iban": {
            "pattern": r"\bES\s*\d{2}\s*\d{4}\s*\d{4}\s*\d{2}\s*\d{10}\b",
            "mask": "[IBAN_OCULTO]",
            "description": "IBAN español",
        },
        "credit_card": {
            "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "mask": "[TARJETA_OCULTA]",
            "description": "Tarjeta de crédito/débito",
        },
        "social_security": {
            "pattern": r"\b\d{2}/?\d{8}/?\d{2}\b",
            "mask": "[NSS_OCULTO]",
            "description": "Número Seguridad Social",
        },
        "postal_code": {
            "pattern": r"\b(?:0[1-9]|[1-4]\d|5[0-2])\d{3}\b",
            "mask": "[CP_OCULTO]",
            "description": "Código Postal",
        },
        "passport": {
            "pattern": r"\b[A-Z]{2,3}\d{6,9}\b",
            "mask": "[PASAPORTE_OCULTO]",
            "description": "Número de pasaporte",
        },
        "cif": {
            "pattern": r"\b[A-HJNP-SUVW]\d{7}[0-9A-J]\b",
            "mask": "[CIF_OCULTO]",
            "description": "CIF empresa",
        },
    }

    # Per-instance cache cap. Reached → cache cleared. Simple LRU-ish.
    _CACHE_MAX = 2048

    def __init__(self, mask_pii: bool = True, log_detections: bool = True):
        """
        Initialize the PII detector with Groq client.
        """
        from groq import Groq

        self.mask_pii = mask_pii
        self.log_detections = log_detections
        self.client = None
        # Per-instance cache so tests with monkey-patched clients keep their
        # own state (Bug C fix). Hash → result.
        self._cache: dict[str, PIIDetectionResult] = {}

        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(
                    f"PII Detector initialized with Groq model: {settings.GROQ_MODEL_SAFETY}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Groq client for PII Detector: {e}")
        else:
            logger.warning("GROQ_API_KEY not found. PII Detection Logic will fail.")

    def _cache_clear(self) -> None:
        """Clear the per-instance cache (used by tests)."""
        self._cache.clear()

    def detect(self, text: str) -> PIIDetectionResult:
        """
        Detect PII in text. Uses Llama Guard / gpt-oss-safeguard for general
        privacy reasoning, deterministic regex for long inputs / fallback,
        and an LRU cache to avoid hammering Groq with repeat traffic.

        Behaviour (Bug C fix, sesion 38):
        - Empty / very short input → fast path, no call.
        - >_REGEX_FALLBACK_THRESHOLD chars → regex-only (avoids 413).
        - Otherwise: cache hit → return cached. Cache miss → call Groq.
        - On 429 (rate limit) → sleep 0.5 s, retry once. On any other error
          or repeat 429 → fall back to regex (so we still catch high-value
          PII instead of failing fully open).
        """
        if not text:
            return PIIDetectionResult(
                has_pii=False,
                detected_types=[],
                masked_text="",
                original_text="",
                detections={},
            )

        # Long inputs: skip Groq, deterministic only.
        if len(text) > _REGEX_FALLBACK_THRESHOLD:
            return self._regex_only(text)

        # Per-instance cache: avoids repeat Groq calls on identical inputs.
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        cached = self._cache.get(text_hash)
        if cached is not None:
            return cached

        result = self._detect_uncached(text)

        if len(self._cache) >= self._CACHE_MAX:
            # Simple LRU-ish: drop the oldest half. Avoids unbounded growth
            # without the overhead of an OrderedDict / functools wrapper.
            for k in list(self._cache.keys())[: self._CACHE_MAX // 2]:
                self._cache.pop(k, None)
        self._cache[text_hash] = result
        return result

    def _detect_uncached(self, text: str) -> PIIDetectionResult:
        """The Groq-backed path, separated from caching."""
        if not self.client:
            return PIIDetectionResult(
                has_pii=False,
                detected_types=["GROQ_CLIENT_MISSING"],
                masked_text=text,
                original_text=text,
                detections={},
            )

        try:
            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_SAFETY,
                messages=[{"role": "user", "content": text}],
                temperature=0.0,
            )
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                # Free-tier shared with LlamaGuard. One sync retry buys us
                # the difference; if it fails again we fall back to regex
                # so we still catch DNI / IBAN / email instead of fail-open.
                time.sleep(0.5)
                try:
                    completion = self.client.chat.completions.create(
                        model=settings.GROQ_MODEL_SAFETY,
                        messages=[{"role": "user", "content": text}],
                        temperature=0.0,
                    )
                except Exception as e2:
                    logger.warning(f"PII Detector 429 retry failed, regex fallback: {e2}")
                    return self._regex_only(text)
            else:
                # Includes 413 request-too-large from gpt-oss-safeguard-20b
                # when the input is just under the threshold but still big.
                logger.warning(f"PII Detector API error, regex fallback: {e}")
                return self._regex_only(text)

        try:
            response = completion.choices[0].message.content.strip()

            # Support both Llama Guard format ("unsafe\nS7") and
            # gpt-oss-safeguard-20b format (empty = safe, refusal text = unsafe)
            response_lower = response.lower()
            if not response:
                # Empty response = safe (gpt-oss-safeguard-20b)
                is_unsafe = False
            elif response_lower.startswith("unsafe") and "S7" in response:
                # Llama Guard format with specific S7 category
                is_unsafe = True
            elif response_lower.startswith("safe"):
                is_unsafe = False
            else:
                # Natural language refusal = model considers content unsafe
                refusal_indicators = [
                    "i'm sorry",
                    "i cannot",
                    "i can't",
                    "cannot help",
                    "can't help",
                    "unable to",
                ]
                is_unsafe = any(ind in response_lower for ind in refusal_indicators)

            detected_types = ["PII (Privacy Violation S7)"] if is_unsafe else []

            if is_unsafe and self.log_detections:
                logger.warning(f"PII detected by moderation model: {response}")

            return PIIDetectionResult(
                has_pii=is_unsafe,
                detected_types=detected_types,
                masked_text="[PII REMOVED BY AI]" if (is_unsafe and self.mask_pii) else text,
                original_text=text,
                detections={"S7": ["[Content Blocked]"]} if is_unsafe else {},
            )

        except Exception as e:
            logger.warning(f"PII Detector parse error, regex fallback: {e}")
            return self._regex_only(text)

    def _regex_only(self, text: str) -> PIIDetectionResult:
        """Deterministic-only PII scan using ``self.PII_PATTERNS``.

        Used when:
        - Input exceeds Groq context window (length guard).
        - Groq returns 413 / 429 (after retry) / any other API error.

        Catches the high-value Spanish PII (DNI, NIE, IBAN, email, phone, CIF)
        which is what the prompt-injection regex layer also relies on. Not
        as nuanced as the LLM but never fails open silently.
        """
        detected: dict[str, list[str]] = {}
        masked = text
        detected_types: list[str] = []

        for pii_type, cfg in self.PII_PATTERNS.items():
            try:
                matches = re.findall(cfg["pattern"], text)
            except re.error:
                continue
            if matches:
                detected[pii_type] = (
                    matches if isinstance(matches[0], str) else [str(m) for m in matches]
                )
                detected_types.append(cfg["description"])
                if self.mask_pii:
                    masked = re.sub(cfg["pattern"], cfg["mask"], masked)

        return PIIDetectionResult(
            has_pii=bool(detected),
            detected_types=detected_types,
            masked_text=masked if self.mask_pii else text,
            original_text=text,
            detections=detected,
        )

    def mask(self, text: str) -> str:
        """
        Mask all PII in text.

        Args:
            text: Text to mask

        Returns:
            Text with PII masked
        """
        result = self.detect(text)
        return result.masked_text

    def validate(self, text: str) -> tuple[bool, str, list[str]]:
        """
        Validate text for PII presence.

        Args:
            text: Text to validate

        Returns:
            Tuple of (has_pii, masked_text, detected_types)
        """
        result = self.detect(text)
        return result.has_pii, result.masked_text, result.detected_types


# Global instance
pii_detector = PIIDetector(mask_pii=True, log_detections=True)
