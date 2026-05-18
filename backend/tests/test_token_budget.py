"""Tests for token budget tracker (Sprint 1 P0 #5).

Migrated to async after Bug B fix (sesion 38): TokenBudgetTracker.check/record
are now coroutines because the production Redis client is AsyncRedis. The
tests still use a sync in-memory mock — the production code detects coroutine
returns via `hasattr(x, '__await__')` and only awaits when needed.
"""

import pytest

from app.security.token_budget import (
    DAILY_LIMITS,
    WARN_FRACTION,
    TokenBudgetTracker,
)


class _MockRedis:
    """In-memory stand-in for Upstash Redis client used in tests.

    Stays synchronous: production code awaits only when the return value is
    a coroutine. This keeps the test surface minimal.
    """

    def __init__(self):
        self.store: dict = {}
        self.expiries: dict = {}

    def get(self, key):
        return self.store.get(key)

    def incrby(self, key, n):
        self.store[key] = int(self.store.get(key, 0)) + int(n)
        return self.store[key]

    def expire(self, key, ttl):
        self.expiries[key] = ttl


@pytest.fixture
def mock_redis():
    return _MockRedis()


@pytest.fixture
def tracker(mock_redis):
    return TokenBudgetTracker(redis_client=mock_redis)


# ── Owner is unlimited ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_owner_always_allowed(tracker):
    status = await tracker.check(user_id="owner", plan_type="particular", is_owner=True)
    assert status.allowed
    assert status.is_owner
    assert status.plan_type == "owner"


@pytest.mark.asyncio
async def test_owner_record_does_not_block(tracker):
    await tracker.record(user_id="owner", tokens=10**9)
    status = await tracker.check(user_id="owner", plan_type=None, is_owner=True)
    assert status.allowed


# ── Fail-open when Redis missing ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_redis_fails_open():
    t = TokenBudgetTracker(redis_client=None)
    status = await t.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.allowed, "Must fail open when Redis is unavailable"
    assert status.used == 0


@pytest.mark.asyncio
async def test_no_redis_record_returns_minus_one():
    t = TokenBudgetTracker(redis_client=None)
    assert await t.record(user_id="u1", tokens=1000) == -1


# ── Plan limits ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plan,expected",
    [
        ("particular", 50_000),
        ("creator", 200_000),
        ("autonomo", 150_000),
        ("unknown_plan", 50_000),  # falls back to particular
    ],
)
async def test_plan_limits(tracker, plan, expected):
    status = await tracker.check(user_id="u1", plan_type=plan, is_owner=False)
    assert status.limit == expected


# ── Increment + block at threshold ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_fresh_user_allowed(tracker):
    status = await tracker.check(user_id="fresh", plan_type="particular", is_owner=False)
    assert status.allowed
    assert status.used == 0
    assert not status.over_limit
    assert not status.near_limit


@pytest.mark.asyncio
async def test_record_increments_counter(tracker):
    await tracker.record(user_id="u1", tokens=1000)
    status = await tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.used == 1000
    assert status.allowed


@pytest.mark.asyncio
async def test_warning_when_near_limit(tracker):
    # Particular = 50k, warn at 80% = 40k
    await tracker.record(user_id="u1", tokens=int(50_000 * WARN_FRACTION) + 100)
    status = await tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.near_limit
    assert status.allowed  # still allowed, just warned


@pytest.mark.asyncio
async def test_blocked_when_over_limit(tracker):
    await tracker.record(user_id="u1", tokens=50_001)
    status = await tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert not status.allowed
    assert status.over_limit
    assert status.used == 50_001


@pytest.mark.asyncio
async def test_creator_higher_limit(tracker):
    await tracker.record(user_id="u1", tokens=60_000)
    # would block particular...
    status_p = await tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert not status_p.allowed
    # ...but creator has 200k cap so still allowed
    status_c = await tracker.check(user_id="u1", plan_type="creator", is_owner=False)
    assert status_c.allowed


# ── Multiple users isolated ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_users_isolated(tracker):
    await tracker.record(user_id="u1", tokens=60_000)
    status_u2 = await tracker.check(user_id="u2", plan_type="particular", is_owner=False)
    assert status_u2.allowed
    assert status_u2.used == 0


# ── Reset_at is a valid ISO date in the future ──────────────────────────────


@pytest.mark.asyncio
async def test_reset_at_iso_format(tracker):
    from datetime import datetime

    status = await tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    parsed = datetime.fromisoformat(status.reset_at)
    assert parsed > datetime.now(parsed.tzinfo)


# ── Negative or zero token records are ignored ──────────────────────────────


@pytest.mark.asyncio
async def test_record_zero_tokens_noop(tracker):
    await tracker.record(user_id="u1", tokens=0)
    await tracker.record(user_id="u1", tokens=-5)
    status = await tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.used == 0


# ── New: works with AsyncMock-style coroutine-returning Redis ───────────────


@pytest.mark.asyncio
async def test_works_with_async_redis_mock():
    """Regression for Bug B (sesion 37 sprint 3): when Redis returns
    coroutines (real AsyncRedis client), tracker.check must await them
    instead of int()-casting a coroutine.
    """
    from unittest.mock import AsyncMock, MagicMock

    redis = MagicMock()
    redis.get = AsyncMock(return_value=b"5000")
    redis.incrby = AsyncMock(return_value=6000)
    redis.expire = AsyncMock(return_value=True)

    t = TokenBudgetTracker(redis_client=redis)
    status = await t.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.used == 5000  # awaited correctly, not coroutine
    assert status.allowed

    new_total = await t.record(user_id="u1", tokens=1000)
    assert new_total == 6000
    redis.expire.assert_awaited_once()
