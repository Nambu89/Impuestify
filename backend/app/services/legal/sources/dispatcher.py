"""LegalSourceDispatcher — routes a norm to the right `LegalSource`.

`norms.yaml` declares each norm's `source_id` (e.g. `boe`, `bopv`,
`static_url`). The dispatcher holds a registry of source instances and
delegates calls. Singleton via `lru_cache` for app-lifetime reuse.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Dict, Optional

from app.services.legal.sources.base import LegalSource, NormaSourceMetadata
from app.services.legal.sources.boe import BoeApiSource
from app.services.legal.sources.bopv import BopvApiSource
from app.services.legal.sources.static_url import StaticUrlSource

logger = logging.getLogger(__name__)


class LegalSourceDispatcher:
    """Holds a `source_id → LegalSource` map and forwards calls."""

    def __init__(self, sources: Optional[Dict[str, LegalSource]] = None):
        if sources is None:
            sources = self._default_sources()
        self._sources: Dict[str, LegalSource] = sources

    @staticmethod
    def _default_sources() -> Dict[str, LegalSource]:
        """Build the canonical set of sources for production use."""
        return {
            "boe": BoeApiSource(),
            "bopv": BopvApiSource(),
            "static_url": StaticUrlSource(),
        }

    # ── Public API ──

    def get_source(self, source_id: str) -> Optional[LegalSource]:
        return self._sources.get(source_id)

    def register(self, source: LegalSource) -> None:
        """Add or override a source (used in tests)."""
        self._sources[source.source_id] = source

    async def fetch_norma(self, source_id: str, norm_id: str) -> Optional[NormaSourceMetadata]:
        src = self.get_source(source_id)
        if src is None:
            logger.warning("Unknown legal source_id: %s", source_id)
            return None
        return await src.fetch_norma(norm_id)

    async def is_vigent(self, source_id: str, norm_id: str) -> Optional[bool]:
        src = self.get_source(source_id)
        if src is None:
            return None
        return await src.is_vigent(norm_id)

    def get_url_html(self, source_id: str, norm_id: str) -> Optional[str]:
        src = self.get_source(source_id)
        if src is None:
            return None
        return src.get_url_html(norm_id)


# ── Singleton ────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_legal_source_dispatcher() -> LegalSourceDispatcher:
    return LegalSourceDispatcher()


def reset_legal_source_dispatcher() -> None:
    get_legal_source_dispatcher.cache_clear()
