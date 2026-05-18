"""Tests for PII detector resilience (Bug C fix, sesion 38).

Covers:
- LRU-style per-instance cache (no double Groq call for same input).
- Length guard: inputs > 3000 chars skip Groq, use deterministic regex.
- Retry sync on 429 from Groq, fall back to regex on second failure.
- Fallback to regex on 413 / generic API errors (instead of fail-open).
"""

from unittest.mock import MagicMock

import pytest

from app.security.pii_detector import PIIDetector, _REGEX_FALLBACK_THRESHOLD


def _mock_completion(content: str = "safe"):
    """Build a Groq-shaped completion result."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# ── Length guard: long inputs go straight to regex ──────────────────────────


def test_long_input_skips_groq_uses_regex():
    detector = PIIDetector()
    detector.client = MagicMock()
    text = "padding " * 500 + " mi DNI es 12345678Z y mi correo a@b.com"
    assert len(text) > _REGEX_FALLBACK_THRESHOLD

    result = detector.detect(text)

    detector.client.chat.completions.create.assert_not_called()
    assert result.has_pii is True
    assert "DNI español" in result.detected_types
    assert "Correo electrónico" in result.detected_types
    assert "[DNI_OCULTO]" in result.masked_text
    assert "[EMAIL_OCULTO]" in result.masked_text


def test_long_input_clean_returns_no_pii():
    detector = PIIDetector()
    detector.client = MagicMock()
    text = "x" * (_REGEX_FALLBACK_THRESHOLD + 100)

    result = detector.detect(text)

    detector.client.chat.completions.create.assert_not_called()
    assert result.has_pii is False
    assert result.detected_types == []


# ── Cache: identical input only hits Groq once ──────────────────────────────


def test_cache_avoids_repeat_groq_calls():
    detector = PIIDetector()
    detector.client = MagicMock()
    detector.client.chat.completions.create.return_value = _mock_completion("safe")

    detector.detect("hola, una pregunta sobre IRPF")
    detector.detect("hola, una pregunta sobre IRPF")
    detector.detect("hola, una pregunta sobre IRPF")

    # Only one real call despite 3 detect() invocations
    assert detector.client.chat.completions.create.call_count == 1


def test_cache_different_inputs_call_groq_separately():
    detector = PIIDetector()
    detector.client = MagicMock()
    detector.client.chat.completions.create.return_value = _mock_completion("safe")

    detector.detect("primera pregunta")
    detector.detect("segunda pregunta")

    assert detector.client.chat.completions.create.call_count == 2


def test_cache_clear_resets():
    detector = PIIDetector()
    detector.client = MagicMock()
    detector.client.chat.completions.create.return_value = _mock_completion("safe")

    detector.detect("pregunta")
    detector._cache_clear()
    detector.detect("pregunta")

    assert detector.client.chat.completions.create.call_count == 2


# ── 429 retry: sleeps once, retries, then fallback ──────────────────────────


def test_429_retried_once_then_fallback_to_regex():
    detector = PIIDetector()
    detector.client = MagicMock()

    # Both calls raise 429-like exception
    detector.client.chat.completions.create.side_effect = Exception("Error code: 429 - rate limit")

    text = "mi correo es test@example.com"
    result = detector.detect(text)

    # Called exactly twice (initial + retry)
    assert detector.client.chat.completions.create.call_count == 2
    # Regex fallback caught the email
    assert result.has_pii is True
    assert "Correo electrónico" in result.detected_types


def test_429_retry_succeeds_no_fallback():
    detector = PIIDetector()
    detector.client = MagicMock()

    # First call 429, second call returns "unsafe\nS7"
    detector.client.chat.completions.create.side_effect = [
        Exception("Error code: 429 - rate limit"),
        _mock_completion("unsafe\nS7"),
    ]

    result = detector.detect("contiene PII")
    assert detector.client.chat.completions.create.call_count == 2
    assert result.has_pii is True
    assert "S7" in result.detections


# ── 413 / generic error: fallback to regex (no retry) ───────────────────────


def test_413_falls_back_to_regex_no_retry():
    detector = PIIDetector()
    detector.client = MagicMock()
    detector.client.chat.completions.create.side_effect = Exception(
        "Error code: 413 - request too large"
    )

    text = "mi IBAN es ES7620770024003102575766"
    result = detector.detect(text)

    # Single call, no retry on 413
    assert detector.client.chat.completions.create.call_count == 1
    # Regex fallback caught the IBAN
    assert result.has_pii is True


def test_generic_api_error_falls_back_to_regex():
    detector = PIIDetector()
    detector.client = MagicMock()
    detector.client.chat.completions.create.side_effect = RuntimeError("network down")

    text = "tengo el DNI 12345678Z"
    result = detector.detect(text)

    assert detector.client.chat.completions.create.call_count == 1
    assert result.has_pii is True
    assert "DNI español" in result.detected_types


# ── No client: graceful degradation ─────────────────────────────────────────


def test_no_client_returns_groq_missing_short_input():
    detector = PIIDetector()
    detector.client = None
    result = detector.detect("hola")
    assert result.has_pii is False
    assert "GROQ_CLIENT_MISSING" in result.detected_types


def test_no_client_long_input_still_uses_regex():
    detector = PIIDetector()
    detector.client = None
    text = "padding " * 500 + " contacto: usuario@correo.es"
    result = detector.detect(text)
    assert result.has_pii is True
    assert "Correo electrónico" in result.detected_types
