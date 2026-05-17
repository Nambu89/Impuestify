"""BOE (Estatal) legal source — wraps the existing BoeApiClient.

Norm IDs follow the BOE format `BOE-A-NNNN-NNNN`.
"""
from __future__ import annotations

from typing import Optional

from app.services.legal.boe_client import BoeApiClient
from app.services.legal.sources.base import LegalSource, NormaSourceMetadata


class BoeApiSource(LegalSource):
    """LegalSource implementation backed by the existing `BoeApiClient`."""

    source_id = "boe"

    def __init__(self, client: Optional[BoeApiClient] = None, db=None):
        # The client may be reused across calls; if not provided, we lazily
        # instantiate one per fetch with a one-shot httpx context.
        self._injected_client = client
        self._db = db

    async def fetch_norma(self, norm_id: str) -> Optional[NormaSourceMetadata]:
        if not norm_id:
            return None
        async with self._acquire_client() as client:
            meta = await client.fetch_norma(norm_id)
        if meta is None:
            return None
        return NormaSourceMetadata(
            source_id=self.source_id,
            norm_id=meta.boe_id,
            titulo=meta.titulo,
            is_vigent=meta.is_vigent,
            url_html=meta.url_html_consolidada,
            fecha_disposicion=meta.fecha_disposicion,
            fecha_vigencia=meta.fecha_vigencia,
            extra={"url_eli": meta.url_eli},
        )

    async def is_vigent(self, norm_id: str) -> Optional[bool]:
        async with self._acquire_client() as client:
            return await client.is_vigent(norm_id)

    def get_url_html(self, norm_id: str) -> Optional[str]:
        if not norm_id:
            return None
        return f"https://www.boe.es/buscar/act.php?id={norm_id}"

    # ── Internals ──

    def _acquire_client(self):
        if self._injected_client is not None:
            return _BorrowedClient(self._injected_client)
        return BoeApiClient(db=self._db)


class _BorrowedClient:
    """Async-context wrapper that yields an externally owned client
    without closing it on `__aexit__`."""

    def __init__(self, client: BoeApiClient):
        self._client = client

    async def __aenter__(self) -> BoeApiClient:
        return self._client

    async def __aexit__(self, *exc):
        return False
