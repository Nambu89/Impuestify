"""Tests for token budget tracker (Sprint 1 P0 #5)."""

import pytest

from app.security.token_budget import (
    TokenBudgetTracker,
    DAILY_LIMITS,
    WARN_FRACTION,
)


class _MockRedis:
    """In-memory stand-in for Upstash Redis client used in tests."""

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


def test_owner_always_allowed(tracker):
    status = tracker.check(user_id="owner", plan_type="particular", is_owner=True)
    assert status.allowed
    assert status.is_owner
    assert status.plan_type == "owner"


def test_owner_record_does_not_block(tracker):
    tracker.record(user_id="owner", tokens=10**9)
    status = tracker.check(user_id="owner", plan_type=None, is_owner=True)
    assert status.allowed


# ── Fail-open when Redis missing ────────────────────────────────────────────


def test_no_redis_fails_open():
    t = TokenBudgetTracker(redis_client=None)
    status = t.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.allowed, "Must fail open when Redis is unavailable"
    assert status.used == 0


def test_no_redis_record_returns_minus_one():
    t = TokenBudgetTracker(redis_client=None)
    assert t.record(user_id="u1", tokens=1000) == -1


# ── Plan limits ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("plan,expected", [
    ("particular", 50_000),
    ("creator", 200_000),
    ("autonomo", 150_000),
    ("unknown_plan", 50_000),  # falls back to particular
])
def test_plan_limits(tracker, plan, expected):
    status = tracker.check(user_id="u1", plan_type=plan, is_owner=False)
    assert status.limit == expected


# ── Increment + block at threshold ──────────────────────────────────────────


def test_fresh_user_allowed(tracker):
    status = tracker.check(user_id="fresh", plan_type="particular", is_owner=False)
    assert status.allowed
    assert status.used == 0
    assert not status.over_limit
    assert not status.near_limit


def test_record_increments_counter(tracker):
    tracker.record(user_id="u1", tokens=1000)
    status = tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.used == 1000
    assert status.allowed


def test_warning_when_near_limit(tracker):
    # Particular = 50k, warn at 80% = 40k
    tracker.record(user_id="u1", tokens=int(50_000 * WARN_FRACTION) + 100)
    status = tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.near_limit
    assert status.allowed  # still allowed, just warned


def test_blocked_when_over_limit(tracker):
    tracker.record(user_id="u1", tokens=50_001)
    status = tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert not status.allowed
    assert status.over_limit
    assert status.used == 50_001


def test_creator_higher_limit(tracker):
    tracker.record(user_id="u1", tokens=60_000)
    # would block particular...
    status_p = tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert not status_p.allowed
    # ...but creator has 200k cap so still allowed
    status_c = tracker.check(user_id="u1", plan_type="creator", is_owner=False)
    assert status_c.allowed


# ── Multiple users isolated ─────────────────────────────────────────────────


def test_users_isolated(tracker):
    tracker.record(user_id="u1", tokens=60_000)
    status_u2 = tracker.check(user_id="u2", plan_type="particular", is_owner=False)
    assert status_u2.allowed
    assert status_u2.used == 0


# ── Reset_at is a valid ISO date in the future ──────────────────────────────


def test_reset_at_iso_format(tracker):
    from datetime import datetime
    status = tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    parsed = datetime.fromisoformat(status.reset_at)
    assert parsed > datetime.now(parsed.tzinfo)


# ── Negative or zero token records are ignored ──────────────────────────────


def test_record_zero_tokens_noop(tracker):
    tracker.record(user_id="u1", tokens=0)
    tracker.record(user_id="u1", tokens=-5)
    status = tracker.check(user_id="u1", plan_type="particular", is_owner=False)
    assert status.used == 0
