"""
Velocity check — defense against prompt-flooding low-cost DoS.

If a user submits N near-identical prompts within a short window we throttle.
Cheap deterministic signal: SHA-256 of the normalized prompt. Real
semantic similarity (cosine on embeddings) is overkill given our
per-user rate limits already exist; the SHA approach catches the
common bot pattern (same prompt repeated) without an extra embedding
call per request.

Storage: Upstash Redis. Key:
  velocity:{user_id}:{sha} -> count, TTL 60s.

If count >= MAX_REPEATS within the window -> throttle (return False).
Fail-open if Redis is unreachable.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


WINDOW_SECONDS = 60
MAX_REPEATS = 3  # 4th identical-ish prompt in 60s -> throttle


_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Lowercase + collapse whitespace + strip punctuation that varies between bot retries."""
    if not text:
        return ""
    cleaned = text.lower()
    cleaned = re.sub(r"[^\w\s]", "", cleaned, flags=re.UNICODE)
    return _WS_RE.sub(" ", cleaned).strip()


def _hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()[:24]


@dataclass
class VelocityResult:
    allowed: bool
    repeat_count: int
    reason: str | None = None


class VelocityChecker:
    def __init__(self, redis=None):
        self.redis = redis

    def _get_redis(self, request=None):
        if self.redis is not None:
            return self.redis
        if request is not None:
            return getattr(request.app.state, "upstash_client", None)
        return None

    async def check(self, user_id: str, question: str, request=None) -> VelocityResult:
        """Async because the Upstash Redis client is async (Bug B fix)."""
        if not user_id or not question:
            return VelocityResult(allowed=True, repeat_count=0)

        redis = self._get_redis(request)
        if redis is None:
            return VelocityResult(allowed=True, repeat_count=0, reason="redis_unavailable")

        key = f"velocity:{user_id}:{_hash(question)}"
        try:
            if hasattr(redis, "incr"):
                count = redis.incr(key)
                if hasattr(count, "__await__"):
                    count = await count
            else:
                set_result = redis.set(key, "1")
                if hasattr(set_result, "__await__"):
                    await set_result
                count = 1
            if count == 1:
                # First hit -> set TTL
                if hasattr(redis, "expire"):
                    exp_result = redis.expire(key, WINDOW_SECONDS)
                    if hasattr(exp_result, "__await__"):
                        await exp_result
            count = int(count) if count is not None else 0
        except Exception as e:
            logger.warning(f"Velocity check Redis error (fail-open): {e}")
            return VelocityResult(allowed=True, repeat_count=0, reason="redis_error")

        if count > MAX_REPEATS:
            logger.warning(
                f"Velocity throttle: user={user_id} count={count} hash={_hash(question)}"
            )
            return VelocityResult(
                allowed=False,
                repeat_count=count,
                reason=(
                    "Has enviado la misma pregunta varias veces seguidas. "
                    "Espera unos segundos antes de reintentarla."
                ),
            )

        return VelocityResult(allowed=True, repeat_count=count)


velocity_checker = VelocityChecker()
