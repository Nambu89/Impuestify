"""
Token budget per user — defends against LLM cost runaway (OWASP LLM10:2025
Unbounded Consumption).

Each user has a daily cap on the total LLM tokens (prompt + completion) they
can consume across all chat calls. Owners are unlimited. The cap is per
subscription plan.

Storage: Upstash Redis. Key pattern:
    tokens:daily:{user_id}:{YYYY-MM-DD}
TTL: 48h (>24h to survive timezone shifts and stragglers).

Fail-open policy: if Redis is unreachable we ALLOW the request and only log a
warning. Cost protection is best-effort — we never block legitimate traffic
because of an infrastructure blip. (The audit trail in `usage_metrics` is the
authoritative record for billing/alerts.)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ── Plan limits (tokens per UTC day) ─────────────────────────────────────────
# Numbers chosen so that a heavy day fits inside the cap but botted abuse hits
# the wall fast. Adjust based on production metrics.
DAILY_LIMITS = {
    "particular": 50_000,
    "creator": 200_000,
    "autonomo": 150_000,
    # owner has no cap (handled separately)
}

# Soft warn threshold: warn user when they cross this fraction of the cap.
WARN_FRACTION = 0.80

# Redis TTL for daily counters (48h to be timezone-safe).
COUNTER_TTL_SECONDS = 48 * 3600


@dataclass
class BudgetStatus:
    allowed: bool
    used: int
    limit: int
    plan_type: str
    is_owner: bool
    reset_at: str  # ISO date for next daily reset (UTC)
    over_limit: bool
    near_limit: bool


def _utc_today_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def _next_utc_midnight_iso() -> str:
    now = datetime.now(timezone.utc)
    next_midnight = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # if already past midnight, move to tomorrow
    if next_midnight <= now:
        from datetime import timedelta

        next_midnight = next_midnight + timedelta(days=1)
    return next_midnight.isoformat()


def _key(user_id: str, when: Optional[str] = None) -> str:
    return f"tokens:daily:{user_id}:{when or _utc_today_str()}"


class TokenBudgetTracker:
    """Daily token-usage tracker backed by Upstash Redis."""

    def __init__(self, redis_client=None):
        self.redis = redis_client

    def _ensure_redis(self, request=None):
        """Resolve a Redis client. Prefer the explicit one, fall back to app state."""
        if self.redis is not None:
            return self.redis
        # FastAPI app state fallback
        if request is not None:
            client = getattr(request.app.state, "upstash_client", None)
            if client is not None:
                return client
        return None

    # ── Read ────────────────────────────────────────────────────────────────

    async def check(
        self, user_id: str, plan_type: Optional[str], is_owner: bool = False, request=None
    ) -> BudgetStatus:
        """
        Read current usage and decide whether the user is allowed another call.
        Does NOT increment.

        Async because the Upstash Redis client (`upstash_redis.asyncio.Redis`)
        is async — calling `.get()` without await previously returned a
        coroutine and broke the int() cast (fail-open silently). Bug B fix.
        """
        plan = (plan_type or "particular").lower()
        limit = DAILY_LIMITS.get(plan, DAILY_LIMITS["particular"])
        reset_at = _next_utc_midnight_iso()

        if is_owner:
            return BudgetStatus(
                allowed=True,
                used=0,
                limit=10**9,
                plan_type="owner",
                is_owner=True,
                reset_at=reset_at,
                over_limit=False,
                near_limit=False,
            )

        used = 0
        redis = self._ensure_redis(request)
        if redis is None:
            logger.warning("Token budget check: no Redis client available — failing open (allow)")
            return BudgetStatus(
                allowed=True,
                used=0,
                limit=limit,
                plan_type=plan,
                is_owner=False,
                reset_at=reset_at,
                over_limit=False,
                near_limit=False,
            )

        try:
            raw = redis.get(_key(user_id))
            # Support both async and sync Redis clients (tests may inject sync mocks)
            if hasattr(raw, "__await__"):
                raw = await raw
            if raw is not None:
                # Upstash returns str/bytes/int depending on client version
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="ignore")
                used = int(raw) if raw else 0
        except Exception as e:
            logger.warning(f"Token budget read failed (fail-open): {e}")
            return BudgetStatus(
                allowed=True,
                used=0,
                limit=limit,
                plan_type=plan,
                is_owner=False,
                reset_at=reset_at,
                over_limit=False,
                near_limit=False,
            )

        over = used >= limit
        near = (used / limit) >= WARN_FRACTION if limit > 0 else False
        return BudgetStatus(
            allowed=not over,
            used=used,
            limit=limit,
            plan_type=plan,
            is_owner=False,
            reset_at=reset_at,
            over_limit=over,
            near_limit=near,
        )

    # ── Write ───────────────────────────────────────────────────────────────

    async def record(self, user_id: str, tokens: int, request=None) -> int:
        """
        Record `tokens` against today's counter. Returns the new total or -1 on
        failure (we never raise — billing is best-effort).

        Async for the same reason as ``check`` — AsyncRedis client.
        """
        if tokens <= 0:
            return -1
        redis = self._ensure_redis(request)
        if redis is None:
            return -1
        try:
            key = _key(user_id)
            new_total = None
            if hasattr(redis, "incrby"):
                new_total = redis.incrby(key, tokens)
            elif hasattr(redis, "incr_by"):
                new_total = redis.incr_by(key, tokens)
            else:
                # Fallback: call incr `tokens` times (avoid in prod; only for tiny burst)
                for _ in range(min(tokens, 50)):
                    new_total = redis.incr(key)
                    if hasattr(new_total, "__await__"):
                        new_total = await new_total
            if hasattr(new_total, "__await__"):
                new_total = await new_total
            # Normalize return type
            try:
                new_total = int(new_total) if new_total is not None else -1
            except (TypeError, ValueError):
                new_total = -1
            try:
                exp_result = redis.expire(key, COUNTER_TTL_SECONDS)
                if hasattr(exp_result, "__await__"):
                    await exp_result
            except Exception:
                pass
            return new_total
        except Exception as e:
            logger.warning(f"Token budget record failed (non-blocking): {e}")
            return -1


# Module-level singleton; tests can monkey-patch this.
token_budget_tracker = TokenBudgetTracker()
