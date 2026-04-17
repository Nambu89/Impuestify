"""Tests para defensia_rate_limits (T2B-011).

Verifica las constantes de rate limiting definidas para los endpoints
DefensIA y el helper `get_defensia_rate_limit`.

Los limites responden a la decision de producto:
- analyze SSE: 3/min (llama RAG + writer + OpenAI, pesado)
- chat SSE: 10/min
- upload documento: 20/min
- resto CRUD: 60/min (default)
"""
from __future__ import annotations

from app.security.defensia_rate_limits import (
    DEFENSIA_RATE_LIMITS,
    get_defensia_rate_limit,
)


def test_analyze_rate_limit_is_3_per_minute():
    """El endpoint analyze SSE debe tener limite 3/minute."""
    assert get_defensia_rate_limit("analyze") == "3/minute"


def test_chat_rate_limit_is_10_per_minute():
    """El endpoint chat SSE debe tener limite 10/minute."""
    assert get_defensia_rate_limit("chat") == "10/minute"


def test_upload_rate_limit_is_20_per_minute():
    """El endpoint upload documento debe tener limite 20/minute."""
    assert get_defensia_rate_limit("upload_documento") == "20/minute"


def test_default_rate_limit_is_60_per_minute():
    """El default de endpoints CRUD debe ser 60/minute."""
    assert get_defensia_rate_limit("default") == "60/minute"


def test_unknown_endpoint_returns_default():
    """Un endpoint_kind desconocido debe devolver el default 60/minute."""
    assert get_defensia_rate_limit("unknown_kind") == "60/minute"


def test_constants_exported():
    """El dict DEFENSIA_RATE_LIMITS debe exponer las 4 claves esperadas."""
    expected_keys = {"analyze", "chat", "upload_documento", "default"}
    assert set(DEFENSIA_RATE_LIMITS.keys()) == expected_keys
