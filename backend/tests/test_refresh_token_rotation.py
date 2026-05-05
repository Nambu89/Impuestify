"""Tests for refresh-token rotation + reuse detection (Sprint 3 P1 #2)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.refresh_token_store import (
    RefreshTokenStore,
    _hash,
)


def _row(**fields):
    class R(dict):
        pass
    return R(fields)


def _result(rows):
    res = MagicMock()
    res.rows = rows
    return res


@pytest.fixture
def db():
    return MagicMock()


@pytest.mark.asyncio
async def test_validate_unknown_jti_revokes_all(db):
    db.execute = AsyncMock(side_effect=[
        _result([]),                       # SELECT (not found)
        _result([_row(c=2)]),              # COUNT for revoke
        _result([]),                       # UPDATE revoke
    ])
    store = RefreshTokenStore(db=db)
    r = await store.validate_and_consume(
        jti="missing-jti", raw_token="t", user_id="u1",
    )
    assert not r.ok
    assert r.reason == "unknown"
    assert r.revoked_count == 2


@pytest.mark.asyncio
async def test_validate_hash_mismatch_revokes(db):
    db.execute = AsyncMock(side_effect=[
        _result([_row(
            id="jti1", user_id="u1",
            refresh_token_hash=_hash("real-token"),
            expires_at="2099-01-01T00:00:00+00:00",
            used_at=None, revoked_at=None,
        )]),
        _result([_row(c=1)]),
        _result([]),
    ])
    store = RefreshTokenStore(db=db)
    r = await store.validate_and_consume(jti="jti1", raw_token="WRONG", user_id="u1")
    assert not r.ok
    assert r.reason == "hash_mismatch"


@pytest.mark.asyncio
async def test_validate_user_mismatch_revokes(db):
    db.execute = AsyncMock(side_effect=[
        _result([_row(
            id="jti1", user_id="u_other",
            refresh_token_hash=_hash("t"),
            expires_at="2099-01-01T00:00:00+00:00",
            used_at=None, revoked_at=None,
        )]),
        _result([_row(c=0)]),
        _result([]),
    ])
    store = RefreshTokenStore(db=db)
    r = await store.validate_and_consume(jti="jti1", raw_token="t", user_id="u1")
    assert not r.ok
    assert r.reason == "user_mismatch"


@pytest.mark.asyncio
async def test_validate_revoked_token_rejected(db):
    db.execute = AsyncMock(return_value=_result([_row(
        id="jti1", user_id="u1",
        refresh_token_hash=_hash("t"),
        expires_at="2099-01-01T00:00:00+00:00",
        used_at=None,
        revoked_at="2026-05-01T00:00:00+00:00",
    )]))
    store = RefreshTokenStore(db=db)
    r = await store.validate_and_consume(jti="jti1", raw_token="t", user_id="u1")
    assert not r.ok
    assert r.reason == "revoked"


@pytest.mark.asyncio
async def test_validate_expired_rejected(db):
    db.execute = AsyncMock(return_value=_result([_row(
        id="jti1", user_id="u1",
        refresh_token_hash=_hash("t"),
        expires_at="2020-01-01T00:00:00+00:00",  # past
        used_at=None, revoked_at=None,
    )]))
    store = RefreshTokenStore(db=db)
    r = await store.validate_and_consume(jti="jti1", raw_token="t", user_id="u1")
    assert not r.ok
    assert r.reason == "expired"


@pytest.mark.asyncio
async def test_validate_first_use_succeeds_and_marks_used(db):
    db.execute = AsyncMock(side_effect=[
        _result([_row(
            id="jti1", user_id="u1",
            refresh_token_hash=_hash("t"),
            expires_at="2099-01-01T00:00:00+00:00",
            used_at=None, revoked_at=None,
        )]),
        _result([]),  # UPDATE used_at
    ])
    store = RefreshTokenStore(db=db)
    r = await store.validate_and_consume(jti="jti1", raw_token="t", user_id="u1")
    assert r.ok
    assert r.reason == "ok"
    # 2nd execute call must be the UPDATE used_at
    assert "UPDATE sessions SET used_at" in db.execute.call_args_list[1][0][0]


@pytest.mark.asyncio
async def test_reuse_detection_triggers_revoke_all_and_email(db):
    # First fetch: row exists with used_at already set -> REUSE
    used_row = _row(
        id="jti1", user_id="u1",
        refresh_token_hash=_hash("t"),
        expires_at="2099-01-01T00:00:00+00:00",
        used_at="2026-05-05T10:00:00+00:00",
        revoked_at=None,
    )
    db.execute = AsyncMock(side_effect=[
        _result([used_row]),                       # SELECT
        _result([_row(c=3)]),                      # COUNT before revoke
        _result([]),                               # UPDATE revoke
        _result([_row(email="u1@x.com", name="Alice")]),  # SELECT user for email
    ])
    store = RefreshTokenStore(db=db)
    with patch("app.services.email_service.EmailService") as MockEmail:
        instance = MockEmail.return_value
        instance.send_email = AsyncMock()
        r = await store.validate_and_consume(jti="jti1", raw_token="t", user_id="u1")
        assert not r.ok
        assert r.reason == "reuse_detected"
        assert r.revoked_count == 3
        # Email to user (and possibly owner) at least once
        assert instance.send_email.await_count >= 1


@pytest.mark.asyncio
async def test_register_inserts_session_row(db):
    db.execute = AsyncMock()
    store = RefreshTokenStore(db=db)
    await store.register(jti="jti1", user_id="u1", raw_token="raw", ttl_days=7)
    db.execute.assert_called_once()
    sql, params = db.execute.call_args[0]
    assert "INSERT INTO sessions" in sql
    assert params[0] == "jti1"
    assert params[1] == "u1"
    assert params[2] == _hash("raw")


@pytest.mark.asyncio
async def test_revoke_all_for_user_returns_count(db):
    db.execute = AsyncMock(side_effect=[
        _result([_row(c=5)]),   # COUNT
        _result([]),             # UPDATE
    ])
    store = RefreshTokenStore(db=db)
    n = await store.revoke_all_for_user("u1", reason="logout")
    assert n == 5
