"""StaticUrlSource — fallback for boletines without a public API.

When a norm lives in a gazette that has no REST endpoint (BOB Bizkaia,
BOG Gipuzkoa, BOTHA Álava, BOCCE Ceuta, BOME Melilla, …) but the URL of
the consolidated text is stable, we use this source. It cannot verify
vigencia (returns `None`), but the citation enricher can still link to
the official text.

The URL itself is supplied by the registry (from `norms.yaml::url_html_consolidada`),
NOT hardcoded here. This source is just an adapter; the URLs themselves
remain data-driven.
"""

from __future__ import annotations

from typing import Optional

from app.services.legal.sources.base import LegalSource, NormaSourceMetadata


class StaticUrlSource(LegalSource):
    """Inert source: returns whatever URL the registry holds, no API."""

    source_id = "static_url"

    async def fetch_norma(self, norm_id: str) -> Optional[NormaSourceMetadata]:
        # No backing API → can't fetch dynamic metadata.
        return None

    async def is_vigent(self, norm_id: str) -> Optional[bool]:
        # No vigencia endpoint → unknown. Callers treat as "assume vigent".
        return None

    def get_url_html(self, norm_id: str) -> Optional[str]:
        # The norm_id IS the URL for this source — the registry passes
        # the configured `url_html_consolidada` here directly.
        if not norm_id:
            return None
        if norm_id.startswith("http://") or norm_id.startswith("https://"):
            return norm_id
        return None
