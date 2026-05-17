"""Tests for the LegalSource plugin architecture.

Covers the BOPV plugin (api.euskadi.eus), the static_url fallback, and
the dispatcher routing.
"""
from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.services.legal.sources import (
    BopvApiSource,
    LegalSourceDispatcher,
    StaticUrlSource,
)
from app.services.legal.sources.bopv import parse_bopv_norma


# ── Fixtures ─────────────────────────────────────────────────────────────


BOPV_JSON_VIGENT = {
    "id": "2024/12/5380",
    "name": "DECRETO 200/2024 EJEMPLO",
    "publishDate": "2024-12-15T22:00:00Z",
    "isErrorCorrection": False,
    "normativeRange": "DECRETO AUTONOMICO",
    "state": "Vigente",
    "territorialScope": "Autonómico",
    "numBulletin": "242",
    "numOrder": "5380",
    "disposalDate": "2024-12-01T22:00:00Z",
    "issuingBody": "Gobierno Vasco",
    "department": "Hacienda",
    "section": "DISPOSICIONES",
}


BOPV_JSON_DEROGATED = {
    **BOPV_JSON_VIGENT,
    "id": "1995/01/12345",
    "state": "Derogada",
}


# ── parse_bopv_norma ─────────────────────────────────────────────────────


def test_parse_bopv_vigent():
    meta = parse_bopv_norma(BOPV_JSON_VIGENT)
    assert meta.source_id == "bopv"
    assert meta.norm_id == "2024/12/5380"
    assert "DECRETO 200/2024" in meta.titulo
    assert meta.is_vigent is True
    assert meta.fecha_disposicion == date(2024, 12, 1)
    assert meta.fecha_vigencia == date(2024, 12, 15)
    assert meta.url_html and "2024/12/5380" in meta.url_html


def test_parse_bopv_derogated():
    meta = parse_bopv_norma(BOPV_JSON_DEROGATED)
    assert meta.is_vigent is False


def test_parse_bopv_unknown_state_returns_none_vigent():
    """Unknown state ('En tramite', etc.) → is_vigent=None (caller asume vigente)."""
    payload = {**BOPV_JSON_VIGENT, "state": "En revisión"}
    meta = parse_bopv_norma(payload)
    assert meta.is_vigent is None


# ── BopvApiSource (mock httpx) ───────────────────────────────────────────


def _mock_transport(routes: dict[str, tuple[int, dict | str]]) -> httpx.MockTransport:
    import json as _json

    def handler(request: httpx.Request) -> httpx.Response:
        full = str(request.url)
        for path, (status, body) in routes.items():
            if path in full:
                if isinstance(body, dict):
                    return httpx.Response(status, text=_json.dumps(body),
                                          headers={"content-type": "application/json"})
                return httpx.Response(status, text=body)
        return httpx.Response(404, text="not in mock")

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_bopv_source_fetch_norma_success():
    transport = _mock_transport({"2024/12/5380": (200, BOPV_JSON_VIGENT)})
    http = httpx.AsyncClient(transport=transport)
    source = BopvApiSource(db=None, http_client=http)
    meta = await source.fetch_norma("2024/12/5380")
    await http.aclose()
    assert meta is not None
    assert meta.is_vigent is True
    assert meta.source_id == "bopv"


@pytest.mark.asyncio
async def test_bopv_source_404_returns_none():
    transport = _mock_transport({"missing": (404, "not found")})
    http = httpx.AsyncClient(transport=transport)
    source = BopvApiSource(db=None, http_client=http)
    meta = await source.fetch_norma("nope/00/0")
    await http.aclose()
    assert meta is None


@pytest.mark.asyncio
async def test_bopv_source_get_url_html_constant():
    """No network needed — URL pattern is stable."""
    source = BopvApiSource(db=None)
    url = source.get_url_html("2024/12/5380")
    assert url == "https://api.euskadi.eus/bopv/administrative-acts/2024/12/5380"


# ── StaticUrlSource ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_static_url_source_returns_url_unchanged():
    source = StaticUrlSource()
    url = source.get_url_html("https://www.bizkaia.eus/.../doc.pdf")
    assert url == "https://www.bizkaia.eus/.../doc.pdf"


@pytest.mark.asyncio
async def test_static_url_source_rejects_non_url():
    source = StaticUrlSource()
    assert source.get_url_html("not a url") is None
    assert source.get_url_html("") is None


@pytest.mark.asyncio
async def test_static_url_source_cannot_check_vigencia():
    source = StaticUrlSource()
    assert await source.is_vigent("https://anything") is None
    assert await source.fetch_norma("https://anything") is None


# ── Dispatcher ───────────────────────────────────────────────────────────


def test_dispatcher_routes_by_source_id():
    dispatcher = LegalSourceDispatcher()
    assert dispatcher.get_source("boe") is not None
    assert dispatcher.get_source("bopv") is not None
    assert dispatcher.get_source("static_url") is not None
    assert dispatcher.get_source("unknown") is None


def test_dispatcher_get_url_html_static():
    """static_url plugin: the dispatcher returns whatever URL we feed."""
    dispatcher = LegalSourceDispatcher()
    url = dispatcher.get_url_html("static_url", "https://example.com/norma.pdf")
    assert url == "https://example.com/norma.pdf"


def test_dispatcher_get_url_html_boe_pattern():
    """BOE plugin: the dispatcher builds the URL from the boe_id pattern."""
    dispatcher = LegalSourceDispatcher()
    url = dispatcher.get_url_html("boe", "BOE-A-1992-28740")
    assert url == "https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740"


def test_dispatcher_unknown_source_returns_none():
    dispatcher = LegalSourceDispatcher()
    assert dispatcher.get_url_html("alien", "X") is None


# ── Registry + dispatcher integration ────────────────────────────────────


def test_registry_get_url_html_for_static_url_norm():
    """A norm with source_id=static_url must resolve via the dispatcher."""
    from app.services.legal.registry import YamlLegalNormsRegistry
    reg = YamlLegalNormsRegistry.from_directory()
    norm = reg.get_norm("NF 13/2013")
    assert norm is not None
    assert norm.effective_source_id() == "static_url"
    url = reg.get_url_html(norm)
    assert url and url.startswith("https://www.bizkaia.eus/")


def test_registry_get_url_html_for_boe_norm():
    """A norm with implicit source_id=boe still resolves correctly."""
    from app.services.legal.registry import YamlLegalNormsRegistry
    reg = YamlLegalNormsRegistry.from_directory()
    norm = reg.get_norm("Ley 37/1992")
    assert norm is not None
    assert norm.effective_source_id() == "boe"
    url = reg.get_url_html(norm)
    assert url and "BOE-A-1992-28740" in url
