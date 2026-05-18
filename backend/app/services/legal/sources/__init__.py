"""Legal sources — pluggable backends for fetching norm metadata.

Each source implements the `LegalSource` protocol. Adding a new boletín
oficial = adding a new module that registers itself in the dispatcher.

Currently registered:
    - boe   → BoeApiSource     (Estado)
    - bopv  → BopvApiSource    (País Vasco — Euskadi)
    - url   → StaticUrlSource  (fallback: URL only, no vigencia check)
"""

from app.services.legal.sources.base import (
    LegalSource,
    NormaSourceMetadata,
)
from app.services.legal.sources.boe import BoeApiSource
from app.services.legal.sources.bopv import BopvApiSource
from app.services.legal.sources.static_url import StaticUrlSource
from app.services.legal.sources.dispatcher import (
    LegalSourceDispatcher,
    get_legal_source_dispatcher,
    reset_legal_source_dispatcher,
)

__all__ = [
    "LegalSource",
    "NormaSourceMetadata",
    "BoeApiSource",
    "BopvApiSource",
    "StaticUrlSource",
    "LegalSourceDispatcher",
    "get_legal_source_dispatcher",
    "reset_legal_source_dispatcher",
]
