"""Tests for the BOE API client.

Network calls are mocked with `httpx.MockTransport` — no real BOE
requests. Real-API fixtures captured from `curl` 2026-05-17.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.legal.boe_client import (
    BOE_API_BASE,
    BoeApiClient,
    NormaBoeMetadata,
    parse_norma_xml,
)

# ── Fixtures de respuesta XML BOE real (capturadas con curl) ─────────────


LIVA_XML_VIGENT = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <status><code>200</code><text>ok</text></status>
  <data>
    <metadatos>
      <identificador>BOE-A-1992-28740</identificador>
      <titulo>Ley 37/1992, de 28 de diciembre, del IVA.</titulo>
      <fecha_disposicion>19921228</fecha_disposicion>
      <fecha_vigencia>19930101</fecha_vigencia>
      <estatus_derogacion>N</estatus_derogacion>
      <vigencia_agotada>N</vigencia_agotada>
      <url_eli>https://www.boe.es/eli/es/l/1992/12/28/37</url_eli>
      <url_html_consolidada>https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740</url_html_consolidada>
    </metadatos>
  </data>
</response>"""


DEROGATED_XML = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <status><code>200</code><text>ok</text></status>
  <data>
    <metadatos>
      <identificador>BOE-A-1985-12345</identificador>
      <titulo>Norma derogada de prueba</titulo>
      <fecha_disposicion>19850101</fecha_disposicion>
      <fecha_vigencia>19850201</fecha_vigencia>
      <estatus_derogacion>S</estatus_derogacion>
      <vigencia_agotada>N</vigencia_agotada>
    </metadatos>
  </data>
</response>"""


ERROR_400_XML = """<?xml version="1.0" encoding="utf-8"?>
<response>
  <status><code>400</code><text>Bad request</text></status>
  <data/>
</response>"""


# ── parse_norma_xml ──────────────────────────────────────────────────────


def test_parse_xml_vigent_norm():
    meta = parse_norma_xml(LIVA_XML_VIGENT)
    assert meta is not None
    assert meta.boe_id == "BOE-A-1992-28740"
    assert "Ley 37/1992" in meta.titulo
    assert meta.fecha_vigencia == date(1993, 1, 1)
    assert meta.estatus_derogacion is False
    assert meta.vigencia_agotada is False
    assert meta.is_vigent is True
    assert meta.url_html_consolidada == "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740"


def test_parse_xml_derogated_norm():
    meta = parse_norma_xml(DEROGATED_XML)
    assert meta is not None
    assert meta.estatus_derogacion is True
    assert meta.is_vigent is False


def test_parse_xml_400_returns_none():
    assert parse_norma_xml(ERROR_400_XML) is None


def test_parse_xml_malformed_returns_none():
    assert parse_norma_xml("<not></valid>") is None
    assert parse_norma_xml("") is None


# ── Cliente HTTP con mock transport ──────────────────────────────────────


def _mock_transport(routes: dict[str, tuple[int, str]]) -> httpx.MockTransport:
    """Build a MockTransport routing exact URL paths to (status, body)."""

    def handler(request: httpx.Request) -> httpx.Response:
        full = str(request.url)
        for path, (status, body) in routes.items():
            if path in full:
                return httpx.Response(
                    status, text=body, headers={"content-type": "application/xml"}
                )
        return httpx.Response(404, text="not in mock")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_fetch_norma_success_no_db():
    transport = _mock_transport({"BOE-A-1992-28740": (200, LIVA_XML_VIGENT)})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        meta = await client.fetch_norma("BOE-A-1992-28740")
    assert meta is not None
    assert meta.is_vigent is True


@pytest.mark.asyncio
async def test_fetch_norma_http_error_returns_none():
    transport = _mock_transport({"BOE-A-1992-28740": (500, "internal error")})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        meta = await client.fetch_norma("BOE-A-1992-28740")
    assert meta is None  # degradación graceful


@pytest.mark.asyncio
async def test_fetch_norma_timeout_returns_none():
    def handler(request):
        raise httpx.TimeoutException("simulated timeout")

    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        meta = await client.fetch_norma("BOE-A-1992-28740")
    assert meta is None  # no crash — caller asume vigente


@pytest.mark.asyncio
async def test_is_vigent_returns_true_for_vigent():
    transport = _mock_transport({"BOE-A-1992-28740": (200, LIVA_XML_VIGENT)})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        assert await client.is_vigent("BOE-A-1992-28740") is True


@pytest.mark.asyncio
async def test_is_vigent_returns_false_for_derogated():
    transport = _mock_transport({"BOE-A-1985-12345": (200, DEROGATED_XML)})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        assert await client.is_vigent("BOE-A-1985-12345") is False


@pytest.mark.asyncio
async def test_is_vigent_returns_none_on_api_error():
    transport = _mock_transport({"BOE-A-XXX": (500, "")})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        assert await client.is_vigent("BOE-A-XXX") is None


@pytest.mark.asyncio
async def test_get_url_html_uses_response_url():
    transport = _mock_transport({"BOE-A-1992-28740": (200, LIVA_XML_VIGENT)})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        url = await client.get_url_html("BOE-A-1992-28740")
    assert url == "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740"


@pytest.mark.asyncio
async def test_get_url_html_falls_back_when_api_down():
    """Si API no responde, usa el patrón estable conocido."""
    transport = _mock_transport({})  # 404 to anything
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=None, http_client=http) as client:
        url = await client.get_url_html("BOE-A-1992-28740")
    # Falla la API pero el cliente construye URL desde el patrón conocido.
    assert url == "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740"


@pytest.mark.asyncio
async def test_empty_boe_id_returns_none():
    async with BoeApiClient(db=None) as client:
        assert await client.fetch_norma("") is None
        assert await client.fetch_norma(None) is None  # type: ignore


# ── Cache (Turso) ────────────────────────────────────────────────────────


class _FakeRow(dict):
    """Minimal dict-like wrapper that supports both ['key'] and .get()."""


class _FakeResult:
    def __init__(self, rows: list[dict]):
        self.rows = [_FakeRow(r) for r in rows]


class _FakeDB:
    """In-memory stand-in for TursoClient.execute(). Captures all writes
    and answers reads from an internal dict."""

    def __init__(self):
        self._store: dict[str, dict] = {}
        self.writes: list[tuple[str, list]] = []

    async def execute(self, sql: str, params: list | None = None):
        params = params or []
        sql_norm = " ".join(sql.split()).upper()

        if sql_norm.startswith("SELECT METADATA_JSON, EXPIRES_AT FROM BOE_CACHE WHERE BOE_ID"):
            row = self._store.get(params[0])
            if row is None:
                return _FakeResult([])
            return _FakeResult([row])

        if "INSERT INTO BOE_CACHE" in sql_norm:
            self.writes.append((sql, params))
            boe_id, metadata_json, fetched_at, expires_at = params
            self._store[boe_id] = {
                "metadata_json": metadata_json,
                "fetched_at": fetched_at,
                "expires_at": expires_at,
            }
            return _FakeResult([])

        raise AssertionError(f"Unexpected SQL: {sql}")


@pytest.mark.asyncio
async def test_cache_hit_does_not_call_api():
    """If a fresh entry exists in cache, no HTTP request is made."""
    db = _FakeDB()
    # Seed cache with a non-expired entry.
    now = datetime.now(UTC)
    db._store["BOE-A-1992-28740"] = {
        "metadata_json": '{"boe_id":"BOE-A-1992-28740","titulo":"Cached","fecha_disposicion":null,'
        '"fecha_vigencia":null,"estatus_derogacion":false,"vigencia_agotada":false,'
        '"url_html_consolidada":null,"url_eli":null}',
        "fetched_at": now.isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat(),
    }

    # Mock transport that would FAIL if called.
    def boom(request):
        pytest.fail("API was called despite fresh cache hit")

    http = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    async with BoeApiClient(db=db, http_client=http) as client:
        meta = await client.fetch_norma("BOE-A-1992-28740")

    assert meta is not None
    assert meta.titulo == "Cached"


@pytest.mark.asyncio
async def test_cache_expired_triggers_api_call():
    db = _FakeDB()
    now = datetime.now(UTC)
    db._store["BOE-A-1992-28740"] = {
        "metadata_json": '{"boe_id":"BOE-A-1992-28740","titulo":"Stale","fecha_disposicion":null,'
        '"fecha_vigencia":null,"estatus_derogacion":false,"vigencia_agotada":false,'
        '"url_html_consolidada":null,"url_eli":null}',
        "fetched_at": (now - timedelta(days=60)).isoformat(),
        "expires_at": (now - timedelta(days=30)).isoformat(),  # ya expirado
    }

    transport = _mock_transport({"BOE-A-1992-28740": (200, LIVA_XML_VIGENT)})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=db, http_client=http) as client:
        meta = await client.fetch_norma("BOE-A-1992-28740")

    assert meta is not None
    # Debe haber actualizado el cache con datos frescos.
    assert "Ley 37/1992" in db._store["BOE-A-1992-28740"]["metadata_json"]


@pytest.mark.asyncio
async def test_upsert_does_not_create_duplicates():
    """Re-writing the same boe_id replaces the row, doesn't append."""
    db = _FakeDB()
    transport = _mock_transport({"BOE-A-1992-28740": (200, LIVA_XML_VIGENT)})
    http = httpx.AsyncClient(transport=transport)
    async with BoeApiClient(db=db, http_client=http) as client:
        await client.fetch_norma("BOE-A-1992-28740")
        # Forcing a write again (bypass cache by calling internal). Simulate
        # second worker writing concurrently.
        meta = parse_norma_xml(LIVA_XML_VIGENT)
        await client._write_cache(meta)
    # Single entry in store.
    assert len(db._store) == 1
    # Both INSERTs invoked (UPSERT semantics).
    assert len(db.writes) == 2
