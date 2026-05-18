"""Legal norms registry — data-driven citation verification.

Substitutes the previous hardcoded whitelists in citation_verifier.py.
The registry loads norms + canonical articles + invoice templates from
YAML files in `backend/data/legal/`, validates them with pydantic, and
exposes lookup methods.

Public API:
    from app.services.legal import get_legal_registry

    registry = get_legal_registry()
    if registry.is_known_norm("ley 37/1992"):
        ...
    if registry.is_known_article("LIVA", "69", "Dos.d"):
        ...

See `models.py`, `loader.py`, `registry.py`, `citation_parser.py`.
"""

from app.services.legal.registry import (
    LegalNormsRegistry,
    YamlLegalNormsRegistry,
    get_legal_registry,
)

__all__ = [
    "LegalNormsRegistry",
    "YamlLegalNormsRegistry",
    "get_legal_registry",
]
