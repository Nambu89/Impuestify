"""BOPV (Boletín Oficial del País Vasco) legal source.

Base URL verified 2026-05-17 with curl:
    GET https://api.euskadi.eus/bopv/administrative-acts
        → paginated list, 200 OK, application/json
    GET https://api.euskadi.eus/bopv/administrative-acts/{YYYY}/{MM}/{numOrder}
        → single norm, 200 OK, application/json

Norm IDs use the path format `YYYY/MM/numOrder` (e.g. "2008/09/5380").
This is what the BOPV uses internally and is what we store in
`norms.yaml::boe_id`-equivalent field. The model field is named
`source_norm_id` to stay source-neutral.

Public HTML URL (stable pattern, verifiable with curl):
    https://www.euskadi.eus/y22-bopv/es/p43aBOPVWebWar/VerParalelo.do?...
    NOTE: not a clean pattern — varies. We use the api.euskadi.eus link
    instead, which is also human-readable and always works.

Field mapping (BOPV JSON → NormaSourceMetadata):
    id              → norm_id
    name            → titulo
    state           → is_vigent  ("Vigente" → True, otherwise False)
    publishDate     → fecha_vigencia (publication date is closest)
    disposalDate    → fecha_disposicion

Authentication: none. Rate limits: not documented; cache aggressively.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx

from app.services.legal.sources.base import LegalSource, NormaSourceMetadata

logger = logging.getLogger(__name__)


BOPV_API_BASE = "https://api.euskadi.eus/bopv"
HEADERS = {"Accept": "application/json", "User-Agent": "Impuestify/1.0"}
DEFAULT_TIMEOUT_S = 1.5
DEFAULT_CACHE_TTL_DAYS = 30


def _parse_iso_date(text: Optional[str]) -> Optional[date]:
    """BOPV uses ISO 8601 with timezone: "2008-09-23T22:00:00Z"."""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_bopv_norma(payload: dict) -> NormaSourceMetadata:
    """Map BOPV JSON payload to NormaSourceMetadata. Tolerant to missing
    keys — the API may evolve. Returns a record even with partial data."""
    state = (payload.get("state") or "").strip().lower()
    is_vigent: Optional[bool]
    if state == "vigente":
        is_vigent = True
    elif state in {"derogada", "anulada"}:
        is_vigent = False
    else:
        is_vigent = None  # unknown state — assume vigent in caller
    norm_id = payload.get("id") or ""
    return NormaSourceMetadata(
        source_id="bopv",
        norm_id=norm_id,
        titulo=(payload.get("name") or "").strip(),
        is_vigent=is_vigent,
        url_html=_build_url_html(norm_id),
        fecha_disposicion=_parse_iso_date(payload.get("disposalDate")),
        fecha_vigencia=_parse_iso_date(payload.get("publishDate")),
        extra={
            "normativeRange": payload.get("normativeRange"),
            "issuingBody": payload.get("issuingBody"),
            "numBulletin": payload.get("numBulletin"),
            "section": payload.get("section"),
        },
    )


def _build_url_html(norm_id: str) -> Optional[str]:
    """Construct the human-readable URL for a BOPV norm. We point to the
    same api.euskadi.eus endpoint that serves the JSON — it also renders
    a friendly HTML page in browsers and is guaranteed to work."""
    if not norm_id:
        return None
    return f"{BOPV_API_BASE}/administrative-acts/{norm_id}"


# ── Source ───────────────────────────────────────────────────────────────


class BopvApiSource(LegalSource):
    """LegalSource backed by api.euskadi.eus BOPV REST endpoint."""

    source_id = "bopv"

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
        self._http = http_client

    async def fetch_norma(self, norm_id: str) -> Optional[NormaSourceMetadata]:
        if not norm_id:
            return None

        cached = await self._read_cache(norm_id)
        if cached is not None:
            return cached

        meta = await self._fetch_from_api(norm_id)
        if meta is not None:
            await self._write_cache(meta)
        return meta

    async def is_vigent(self, norm_id: str) -> Optional[bool]:
        meta = await self.fetch_norma(norm_id)
        if meta is None:
            return None
        return meta.is_vigent

    def get_url_html(self, norm_id: str) -> Optional[str]:
        return _build_url_html(norm_id)

    # ── Internals ──

    async def _fetch_from_api(self, norm_id: str) -> Optional[NormaSourceMetadata]:
        url = f"{BOPV_API_BASE}/administrative-acts/{norm_id}"
        try:
            if self._http is not None:
                resp = await self._http.get(url, headers=HEADERS)
            else:
                async with httpx.AsyncClient(timeout=self._timeout, headers=HEADERS) as http:
                    resp = await http.get(url)
        except httpx.HTTPError as exc:
            logger.warning("BOPV API request failed for %s: %s", norm_id, exc)
            return None
        if resp.status_code != 200:
            logger.warning("BOPV API returned HTTP %s for %s", resp.status_code, norm_id)
            return None
        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("BOPV API returned invalid JSON for %s: %s", norm_id, exc)
            return None
        return parse_bopv_norma(payload)

    async def _read_cache(self, norm_id: str) -> Optional[NormaSourceMetadata]:
        if self._db is None:
            return None
        try:
            cache_key = f"bopv:{norm_id}"
            result = await self._db.execute(
                "SELECT metadata_json, expires_at FROM boe_cache WHERE boe_id = ?",
                [cache_key],
            )
            if not result.rows:
                return None
            row = result.rows[0]
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return None
            return _metadata_from_json(row["metadata_json"])
        except Exception as exc:
            logger.debug("bopv cache read failed for %s: %s", norm_id, exc)
            return None

    async def _write_cache(self, meta: NormaSourceMetadata) -> None:
        if self._db is None:
            return
        cache_key = f"bopv:{meta.norm_id}"
        now = datetime.now(timezone.utc)
        expires_at = now + self._cache_ttl
        try:
            await self._db.execute(
                """
                INSERT INTO boe_cache (boe_id, metadata_json, fetched_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(boe_id) DO UPDATE SET
                    metadata_json = excluded.metadata_json,
                    fetched_at    = excluded.fetched_at,
                    expires_at    = excluded.expires_at
                """,
                [cache_key, _metadata_to_json(meta), now.isoformat(), expires_at.isoformat()],
            )
        except Exception as exc:
            logger.warning("bopv cache write failed for %s: %s", meta.norm_id, exc)


# ── Serialization helpers ────────────────────────────────────────────────


def _metadata_to_json(meta: NormaSourceMetadata) -> str:
    return json.dumps({
        "source_id": meta.source_id,
        "norm_id": meta.norm_id,
        "titulo": meta.titulo,
        "is_vigent": meta.is_vigent,
        "url_html": meta.url_html,
        "fecha_disposicion": meta.fecha_disposicion.isoformat() if meta.fecha_disposicion else None,
        "fecha_vigencia": meta.fecha_vigencia.isoformat() if meta.fecha_vigencia else None,
        "extra": meta.extra or {},
    })


def _metadata_from_json(blob: str) -> NormaSourceMetadata:
    d = json.loads(blob)
    return NormaSourceMetadata(
        source_id=d.get("source_id", "bopv"),
        norm_id=d["norm_id"],
        titulo=d.get("titulo", ""),
        is_vigent=d.get("is_vigent"),
        url_html=d.get("url_html"),
        fecha_disposicion=date.fromisoformat(d["fecha_disposicion"]) if d.get("fecha_disposicion") else None,
        fecha_vigencia=date.fromisoformat(d["fecha_vigencia"]) if d.get("fecha_vigencia") else None,
        extra=d.get("extra"),
    )
