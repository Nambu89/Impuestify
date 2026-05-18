"""Tests for velocity check (Sprint 3 P2 #6).

Migrated to async after Bug B fix (sesion 38): VelocityChecker.check is now a
coroutine. Sync mock works because production code only awaits return values
that expose `__await__`.
"""

import pytest

from app.security.velocity_check import MAX_REPEATS, VelocityChecker, _hash, _normalize


class _MockRedis:
    def __init__(self):
        self.store = {}
        self.expiries = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        self.expiries[key] = ttl


def test_normalize_collapses_whitespace_and_lowercases():
    assert _normalize("Hola, ¿qué tal?") == _normalize("HOLA  ¿qué   tal?")


def test_hash_stable_across_punctuation_only_diffs():
    assert _hash("Cuánto IRPF pago?") == _hash("Cuánto IRPF pago.")


@pytest.mark.asyncio
async def test_first_call_allowed():
    v = VelocityChecker(redis=_MockRedis())
    r = await v.check("u1", "Cuánto IRPF pago?")
    assert r.allowed
    assert r.repeat_count == 1


@pytest.mark.asyncio
async def test_under_threshold_allowed():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS):
        r = await v.check("u1", "same question")
    assert r.allowed
    assert r.repeat_count == MAX_REPEATS


@pytest.mark.asyncio
async def test_over_threshold_blocked():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS + 1):
        r = await v.check("u1", "spam prompt")
    assert not r.allowed
    assert r.repeat_count == MAX_REPEATS + 1
    assert "varias veces" in r.reason.lower()


@pytest.mark.asyncio
async def test_different_users_isolated():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS + 1):
        await v.check("u1", "spam")
    r2 = await v.check("u2", "spam")
    assert r2.allowed
    assert r2.repeat_count == 1


@pytest.mark.asyncio
async def test_different_questions_isolated():
    redis = _MockRedis()
    v = VelocityChecker(redis=redis)
    for _ in range(MAX_REPEATS + 1):
        await v.check("u1", "first question")
    r = await v.check("u1", "completely different question")
    assert r.allowed
    assert r.repeat_count == 1


@pytest.mark.asyncio
async def test_no_redis_fail_open():
    v = VelocityChecker(redis=None)
    r = await v.check("u1", "anything")
    assert r.allowed
    assert r.reason in ("redis_unavailable", None)


@pytest.mark.asyncio
async def test_empty_input_allowed():
    v = VelocityChecker(redis=_MockRedis())
    assert (await v.check("", "x")).allowed
    assert (await v.check("u1", "")).allowed


@pytest.mark.asyncio
async def test_works_with_async_redis_mock():
    """Regression for Bug B: AsyncRedis returns coroutines from incr/expire.

    The production code awaits them via `hasattr(x, '__await__')` checks.
    """
    from unittest.mock import AsyncMock, MagicMock

    redis = MagicMock()
    counter = {"n": 0}

    async def _incr(key):
        counter["n"] += 1
        return counter["n"]

    redis.incr = _incr
    redis.expire = AsyncMock(return_value=True)

    v = VelocityChecker(redis=redis)
    for i in range(MAX_REPEATS + 1):
        r = await v.check("u1", "spam from async client")
    assert not r.allowed
    assert r.repeat_count == MAX_REPEATS + 1
