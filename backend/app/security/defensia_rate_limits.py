"""DefensIA rate limits config (T2B-011).

Constantes de rate limiting para los endpoints DefensIA. Aplicar en los
decoradores de los endpoints cuando se creen en Batch 3.

Limites (decision producto):
- analyze: 3/min (mas pesado, llama RAG + writer + OpenAI)
- chat: 10/min
- upload documentos: 20/min
- resto CRUD: 60/min default
"""
from __future__ import annotations


DEFENSIA_RATE_LIMITS: dict[str, str] = {
    "analyze": "3/minute",
    "chat": "10/minute",
    "upload_documento": "20/minute",
    "default": "60/minute",
}


def get_defensia_rate_limit(endpoint_kind: str) -> str:
    """Devuelve el rate limit para un tipo de endpoint DefensIA.

    Args:
        endpoint_kind: uno de "analyze", "chat", "upload_documento", "default".

    Returns:
        Rate limit string compatible con slowapi (ej: "3/minute").
    """
    return DEFENSIA_RATE_LIMITS.get(endpoint_kind, DEFENSIA_RATE_LIMITS["default"])
