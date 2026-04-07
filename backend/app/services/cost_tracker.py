"""
Lightweight cost tracking service for Impuestify.

Tracks token usage and estimated costs per user/endpoint in the usage_metrics table.
Replaces Prometheus with simple DB-based tracking for admin dashboard.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# USD per 1M tokens (updated 2026)
MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-5": {"input": 5.00, "output": 15.00},
    "gpt-5-mini": {"input": 0.30, "output": 1.20},
    "text-embedding-3-large": {"input": 0.13, "output": 0},
}

# EUR/USD exchange rate (approximate, update periodically)
EUR_USD_RATE = 0.92


class CostTracker:
    """Track token usage and costs in usage_metrics table."""

    def __init__(self, db=None):
        self._db = db

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client
        self._db = await get_db_client()
        return self._db

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost for a given model and token counts."""
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            return 0.0
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    async def track(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        endpoint: str,
        processing_time: float = 0.0,
        cached: bool = False,
    ) -> None:
        """Record a usage event in the database."""
        try:
            db = await self._get_db()
            cost_usd = self.calculate_cost(model, input_tokens, output_tokens)
            total_tokens = input_tokens + output_tokens

            await db.execute(
                """INSERT INTO usage_metrics
                   (id, user_id, endpoint, tokens_used, processing_time, cached,
                    model, input_tokens, output_tokens, cost_usd, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    str(uuid.uuid4()), user_id, endpoint, total_tokens,
                    processing_time, int(cached), model, input_tokens,
                    output_tokens, cost_usd, datetime.now(timezone.utc).isoformat(),
                ],
            )
        except Exception as e:
            # Never let cost tracking break the main request flow
            logger.error("CostTracker.track failed: %s", e)

    async def get_user_summary(
        self, user_id: str, period: str = "month"
    ) -> Dict[str, Any]:
        """Get usage summary for a specific user."""
        db = await self._get_db()
        since = self._period_start(period)

        result = await db.execute(
            """SELECT
                 COUNT(*) as total_requests,
                 COALESCE(SUM(tokens_used), 0) as total_tokens,
                 COALESCE(SUM(cost_usd), 0) as total_cost_usd,
                 model,
                 COALESCE(SUM(input_tokens), 0) as model_input,
                 COALESCE(SUM(output_tokens), 0) as model_output
               FROM usage_metrics
               WHERE user_id = ? AND created_at >= ?
               GROUP BY model""",
            [user_id, since],
        )

        by_model: Dict[str, Any] = {}
        total_cost = 0.0
        total_tokens = 0
        total_requests = 0

        for row in result.rows or []:
            row_dict = dict(row) if not isinstance(row, dict) else row
            model_name = row_dict.get("model", "unknown")
            cost = row_dict.get("total_cost_usd", 0) or 0
            by_model[model_name] = {
                "input_tokens": row_dict.get("model_input", 0),
                "output_tokens": row_dict.get("model_output", 0),
                "cost_usd": cost,
            }
            total_cost += cost
            total_tokens += row_dict.get("total_tokens", 0) or 0
            total_requests += row_dict.get("total_requests", 0) or 0

        return {
            "user_id": user_id,
            "period": period,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "total_cost_eur": round(total_cost * EUR_USD_RATE, 4),
            "by_model": by_model,
        }

    async def get_global_summary(
        self, period: str = "month"
    ) -> Dict[str, Any]:
        """Get global usage summary for admin dashboard."""
        db = await self._get_db()
        since = self._period_start(period)

        # Total costs
        result = await db.execute(
            """SELECT
                 COUNT(*) as total_requests,
                 COALESCE(SUM(tokens_used), 0) as total_tokens,
                 COALESCE(SUM(cost_usd), 0) as total_cost_usd
               FROM usage_metrics
               WHERE created_at >= ?""",
            [since],
        )
        totals = dict(result.rows[0]) if result.rows else {}

        # Top 10 users by cost
        top_result = await db.execute(
            """SELECT
                 um.user_id,
                 u.email,
                 u.subscription_plan,
                 COALESCE(SUM(um.cost_usd), 0) as user_cost_usd,
                 COUNT(*) as request_count
               FROM usage_metrics um
               LEFT JOIN users u ON um.user_id = u.id
               WHERE um.created_at >= ?
               GROUP BY um.user_id
               ORDER BY user_cost_usd DESC
               LIMIT 10""",
            [since],
        )
        top_users = [dict(row) for row in top_result.rows or []]

        # Cost by plan
        plan_result = await db.execute(
            """SELECT
                 COALESCE(u.subscription_plan, 'none') as plan,
                 COALESCE(SUM(um.cost_usd), 0) as plan_cost_usd,
                 COUNT(DISTINCT um.user_id) as user_count
               FROM usage_metrics um
               LEFT JOIN users u ON um.user_id = u.id
               WHERE um.created_at >= ?
               GROUP BY u.subscription_plan""",
            [since],
        )
        by_plan = {dict(row)["plan"]: dict(row) for row in plan_result.rows or []}

        total_cost = totals.get("total_cost_usd", 0) or 0

        return {
            "period": period,
            "total_requests": totals.get("total_requests", 0),
            "total_tokens": totals.get("total_tokens", 0),
            "total_cost_usd": round(total_cost, 4),
            "total_cost_eur": round(total_cost * EUR_USD_RATE, 4),
            "top_users": top_users,
            "by_plan": by_plan,
        }

    def _period_start(self, period: str) -> str:
        """Return ISO date string for the start of the period."""
        now = datetime.now(timezone.utc)
        if period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        elif period == "year":
            start = now - timedelta(days=365)
        else:
            start = now - timedelta(days=30)
        return start.isoformat()
