"""HTTP client for the BOE Datos Abiertos REST API.

API official: https://www.boe.es/datosabiertos/api/
Authentication: none (public).
Format: XML only (the API rejects `Accept: application/json` with 400 —
verified with curl 2026-05-17).

Used to verify the vigence (`estatus_derogacion`, `vigencia_agotada`) of
laws referenced in our `data/legal/norms.yaml` and to obtain the
canonical URL of the consolidated text.

Caching: results are persisted in Turso `boe_cache` table for 30 days.
The vigence of a law rarely changes, so this drastically reduces external
calls. Cache write uses `INSERT ... ON CONFLICT(boe_id) DO UPDATE`
(SQLite UPSERT) for race-condition safety under multi-worker scenarios.

Graceful degradation: any network or parsing error returns `None` to
callers. The chat pipeline assumes "vigente" on missing data — better to
ship an unverified-but-likely-correct citation than to break the chat.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

logger = logging.getLogger(__name__)


BOE_API_BASE = "https://www.boe.es/datosabiertos/api"
HEADERS = {"Accept": "application/xml", "User-Agent": "Impuestify/1.0"}
DEFAULT_TIMEOUT_S = 1.5
DEFAULT_CACHE_TTL_DAYS = 30


# ── Domain model ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class NormaBoeMetadata:
    """Subset of the metadata returned by `/legislacion-consolidada/id/{id}`.

    Mapped from XML fields under `<response><data><metadatos>`. Only the
    fields the verifier and enricher need; the API returns many more.
    """

    boe_id: str                          # `<identificador>`
    titulo: str                          # `<titulo>`
    fecha_disposicion: Optional[date]    # `<fecha_disposicion>` YYYYMMDD
    fecha_vigencia: Optional[date]       # `<fecha_vigencia>` YYYYMMDD
    estatus_derogacion: bool             # `<estatus_derogacion>` (S/N) → bool
    vigencia_agotada: bool               # `<vigencia_agotada>` (S/N) → bool
    url_html_consolidada: Optional[str]  # `<url_html_consolidada>`
    url_eli: Optional[str]               # `<url_eli>` (European Legislation Id.)

    @property
    def is_vigent(self) -> bool:
        """True if the law is currently in force (not derogated nor
        consumed)."""
        return not self.estatus_derogacion and not self.vigencia_agotada


# ── XML parsing ──────────────────────────────────────────────────────────


def _parse_date(text: Optional[str]) -> Optional[date]:
    """BOE dates come as `YYYYMMDD` (no separators). Returns None on bad input."""
    if not text:
        return None
    try:
        return datetime.strptime(text.strip(), "%Y%m%d").date()
    except ValueError:
        return None


def _parse_bool_sn(text: Optional[str]) -> bool:
    """BOE booleans are encoded as `S` (sí) / `N` (no)."""
    return (text or "").strip().upper() == "S"


def parse_norma_xml(xml_text: str) -> Optional[NormaBoeMetadata]:
    """Parse a `<response><data><metadatos>` payload into NormaBoeMetadata.

    Returns None if the response status is not 200 or the structure is
    unexpected. Tolerant to missing fields (the API has many evolving
    sub-elements we don't care about).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("BOE API returned invalid XML: %s", exc)
        return None

    status_code = root.findtext("./status/code")
    if status_code != "200":
        logger.debug("BOE API non-200 status in body: %s", status_code)
        return None

    meta = root.find("./data/metadatos")
    if meta is None:
        return None

    return NormaBoeMetadata(
        boe_id=(meta.findtext("identificador") or "").strip(),
        titulo=(meta.findtext("titulo") or "").strip(),
        fecha_disposicion=_parse_date(meta.findtext("fecha_disposicion")),
        fecha_vigencia=_parse_date(meta.findtext("fecha_vigencia")),
        estatus_derogacion=_parse_bool_sn(meta.findtext("estatus_derogacion")),
        vigencia_agotada=_parse_bool_sn(meta.findtext("vigencia_agotada")),
        url_html_consolidada=(meta.findtext("url_html_consolidada") or None),
        url_eli=(meta.findtext("url_eli") or None),
    )


# ── Cache (Turso `boe_cache` table) ──────────────────────────────────────


@dataclass
class _CacheEntry:
    metadata: NormaBoeMetadata
    expires_at: datetime


def _metadata_to_json(meta: NormaBoeMetadata) -> str:
    return json.dumps({
        "boe_id": meta.boe_id,
        "titulo": meta.titulo,
        "fecha_disposicion": meta.fecha_disposicion.isoformat() if meta.fecha_disposicion else None,
        "fecha_vigencia": meta.fecha_vigencia.isoformat() if meta.fecha_vigencia else None,
        "estatus_derogacion": meta.estatus_derogacion,
        "vigencia_agotada": meta.vigencia_agotada,
        "url_html_consolidada": meta.url_html_consolidada,
        "url_eli": meta.url_eli,
    })


def _metadata_from_json(blob: str) -> NormaBoeMetadata:
    d = json.loads(blob)
    return NormaBoeMetadata(
        boe_id=d["boe_id"],
        titulo=d["titulo"],
        fecha_disposicion=date.fromisoformat(d["fecha_disposicion"]) if d.get("fecha_disposicion") else None,
        fecha_vigencia=date.fromisoformat(d["fecha_vigencia"]) if d.get("fecha_vigencia") else None,
        estatus_derogacion=bool(d.get("estatus_derogacion", False)),
        vigencia_agotada=bool(d.get("vigencia_agotada", False)),
        url_html_consolidada=d.get("url_html_consolidada"),
        url_eli=d.get("url_eli"),
    )


# ── Client ───────────────────────────────────────────────────────────────


class BoeApiClient:
    """Async HTTP client for the BOE consolidated-legislation API.

    Usage:
        async with BoeApiClient(db=turso) as client:
            meta = await client.fetch_norma("BOE-A-1992-28740")
            if meta and meta.is_vigent:
                ...
    """

    def __init__(
        self,
        db=None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        cache_ttl_days: int = DEFAULT_CACHE_TTL_DAYS,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._db = db
        self._timeout = httpx.Timeout(timeout_s)
        self._cache_ttl = timedelta(days=cache_ttl_days)
        # Optional injection for tests (mock httpx).
        self._http: Optional[httpx.AsyncClient] = http_client
        self._owns_http = http_client is None

    async def __aenter__(self) -> "BoeApiClient":
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self._timeout, headers=HEADERS)
        return self

    async def __aexit__(self, *exc):
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    # ── Public API ──

    async def fetch_norma(self, boe_id: str) -> Optional[NormaBoeMetadata]:
        """Get metadata for a BOE norm. Uses cache first; on miss/expiry
        consults the API; on any error returns None (graceful degradation)."""
        if not boe_id:
            return None

        cached = await self._read_cache(boe_id)
        if cached is not None:
            return cached

        meta = await self._fetch_from_api(boe_id)
        if meta is not None:
            await self._write_cache(meta)
        return meta

    async def is_vigent(self, boe_id: str) -> Optional[bool]:
        """True / False / None (unknown). Callers should treat None as
        "assume vigente" to avoid false-positive derogation warnings."""
        meta = await self.fetch_norma(boe_id)
        if meta is None:
            return None
        return meta.is_vigent

    async def get_url_html(self, boe_id: str) -> Optional[str]:
        """URL HTML consolidada. Falls back to the well-known pattern if the
        API is unreachable (we know the BOE URL scheme is stable since 2010)."""
        meta = await self.fetch_norma(boe_id)
        if meta and meta.url_html_consolidada:
            return meta.url_html_consolidada
        # Conservative fallback — the pattern is stable in practice.
        if boe_id:
            return f"https://www.boe.es/buscar/act.php?id={boe_id}"
        return None

    # ── Internals ──

    async def _fetch_from_api(self, boe_id: str) -> Optional[NormaBoeMetadata]:
        if self._http is None:
            # Caller used the client without async-context. Open a one-shot.
            async with httpx.AsyncClient(timeout=self._timeout, headers=HEADERS) as http:
                return await self._do_fetch(http, boe_id)
        return await self._do_fetch(self._http, boe_id)

    async def _do_fetch(self, http: httpx.AsyncClient, boe_id: str) -> Optional[NormaBoeMetadata]:
        url = f"{BOE_API_BASE}/legislacion-consolidada/id/{boe_id}"
        try:
            resp = await http.get(url)
        except httpx.HTTPError as exc:
            logger.warning("BOE API request failed for %s: %s", boe_id, exc)
            return None
        if resp.status_code != 200:
            logger.warning("BOE API returned HTTP %s for %s", resp.status_code, boe_id)
            return None
        return parse_norma_xml(resp.text)

    async def _read_cache(self, boe_id: str) -> Optional[NormaBoeMetadata]:
        if self._db is None:
            return None
        try:
            result = await self._db.execute(
                "SELECT metadata_json, expires_at FROM boe_cache WHERE boe_id = ?",
                [boe_id],
            )
            if not result.rows:
                return None
            row = result.rows[0]
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return None  # expired
            return _metadata_from_json(row["metadata_json"])
        except Exception as exc:
            logger.debug("boe_cache read failed for %s: %s", boe_id, exc)
            return None

    async def _write_cache(self, meta: NormaBoeMetadata) -> None:
        if self._db is None:
            return
        now = datetime.now(timezone.utc)
        expires_at = now + self._cache_ttl
        try:
            # UPSERT — race-condition safe under multi-worker. Even with
            # 1 worker on Railway today, future-proofs against tests in
            # parallel or migration to N workers.
            await self._db.execute(
                """
                INSERT INTO boe_cache (boe_id, metadata_json, fetched_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(boe_id) DO UPDATE SET
                    metadata_json = excluded.metadata_json,
                    fetched_at    = excluded.fetched_at,
                    expires_at    = excluded.expires_at
                """,
                [meta.boe_id, _metadata_to_json(meta), now.isoformat(), expires_at.isoformat()],
            )
        except Exception as exc:
            logger.warning("boe_cache write failed for %s: %s", meta.boe_id, exc)
