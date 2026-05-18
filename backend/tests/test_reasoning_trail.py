"""Tests for reasoning trail recorder (Sprint 2 P1 #5)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.reasoning_trail import ReasoningTrailRecorder


@pytest.mark.asyncio
async def test_record_inserts_with_compact_chunks():
    db = MagicMock()
    db.execute = AsyncMock()

    rec = ReasoningTrailRecorder(db=db)
    await rec.record(
        message_id="m1",
        user_id="u1",
        conversation_id="c1",
        rag_chunks=[
            {
                "id": "c1",
                "title": "AEAT Manual",
                "page": 12,
                "trust_level": "official_aeat",
                "similarity": 0.876,
                "text": "long text we should NOT persist verbatim...",
            }
        ],
        tools_called=[{"name": "simulate_irpf", "arguments": {"ingresos": 30000}, "ok": True}],
        security_layer="all_clear",
        fiscal_profile={
            "ccaa_residencia": "Madrid",
            "situacion_laboral": "autonomo",
            "secret_key": "must_not_persist",
        },
        model="gpt-5-mini",
    )

    db.execute.assert_called_once()
    args = db.execute.call_args[0]
    assert "INSERT INTO reasoning_trails" in args[0]
    params = args[1]
    chunks_json = params[4]
    chunks = json.loads(chunks_json)
    assert len(chunks) == 1
    assert chunks[0]["id"] == "c1"
    assert chunks[0]["trust_level"] == "official_aeat"
    assert "text" not in chunks[0]  # full text NOT persisted

    tools_json = params[5]
    tools = json.loads(tools_json)
    assert tools[0]["name"] == "simulate_irpf"
    assert tools[0]["args_keys"] == ["ingresos"]  # only keys, not values
    assert tools[0]["ok"] is True

    profile_json = params[7]
    profile = json.loads(profile_json)
    assert profile["ccaa_residencia"] == "Madrid"
    assert profile["situacion_laboral"] == "autonomo"
    assert "secret_key" not in profile  # only safe-listed keys persist


@pytest.mark.asyncio
async def test_record_handles_none_inputs():
    db = MagicMock()
    db.execute = AsyncMock()

    rec = ReasoningTrailRecorder(db=db)
    rid = await rec.record(
        message_id="m1",
        user_id="u1",
        conversation_id=None,
        rag_chunks=None,
        tools_called=None,
        security_layer=None,
        fiscal_profile=None,
        model=None,
    )
    assert rid is not None
    db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_record_swallows_db_errors_non_blocking():
    db = MagicMock()
    db.execute = AsyncMock(side_effect=Exception("connection lost"))

    rec = ReasoningTrailRecorder(db=db)
    rid = await rec.record(
        message_id="m1",
        user_id="u1",
        conversation_id=None,
    )
    assert rid is None  # Non-blocking — never raises


@pytest.mark.asyncio
async def test_get_for_message_parses_json_back():
    db = MagicMock()
    row = {
        "id": "t1",
        "message_id": "m1",
        "user_id": "u1",
        "conversation_id": "c1",
        "rag_chunks": '[{"id":"c1","trust_level":"official_aeat"}]',
        "tools_called": "[]",
        "security_layers": '{"layer":"all_clear"}',
        "fiscal_profile_snapshot": "{}",
        "model": "gpt-5-mini",
        "created_at": "2026-05-05T00:00:00+00:00",
    }
    res = MagicMock()
    res.rows = [row]
    db.execute = AsyncMock(return_value=res)

    rec = ReasoningTrailRecorder(db=db)
    got = await rec.get_for_message("m1")
    assert got["rag_chunks"][0]["trust_level"] == "official_aeat"
    assert got["security_layers"]["layer"] == "all_clear"


@pytest.mark.asyncio
async def test_get_for_message_returns_none_if_not_found():
    db = MagicMock()
    res = MagicMock()
    res.rows = []
    db.execute = AsyncMock(return_value=res)

    rec = ReasoningTrailRecorder(db=db)
    assert await rec.get_for_message("missing") is None
