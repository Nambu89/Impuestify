"""
Cost anomaly detector — alerts the owner when a user's spending today is
abnormally high vs their own 7-day baseline.

Designed to be run as a Railway cron (hourly). Sends a Resend email with
the offending user and amount delta. Idempotent within a 24h window per
user via Upstash Redis flag.

Trigger heuristic (default):
  today_cost > max(LOWER_FLOOR_USD, 10 * baseline_avg_per_day)

LOWER_FLOOR_USD avoids spamming when both numbers are tiny (e.g. user
spent $0.01 average, today spent $0.15 — 15x but irrelevant).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Tuning ───────────────────────────────────────────────────────────────────
DEFAULT_MULTIPLIER = float(os.getenv("COST_ANOMALY_MULTIPLIER", "10.0"))
LOWER_FLOOR_USD = float(os.getenv("COST_ANOMALY_FLOOR_USD", "0.50"))
ALERT_DEDUPE_TTL = 24 * 3600  # one alert per user per 24h


@dataclass
class AnomalyHit:
    user_id: str
    email: Optional[str]
    plan: Optional[str]
    today_cost_usd: float
    baseline_avg_usd: float
    multiplier: float
    today_requests: int


class CostAnomalyDetector:
    """Detect users whose today's spend is N× their 7-day average."""

    def __init__(self, db=None, redis_client=None):
        self._db = db
        self.redis = redis_client

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client

        self._db = await get_db_client()
        return self._db

    async def find_anomalies(self, multiplier: float = DEFAULT_MULTIPLIER) -> List[AnomalyHit]:
        db = await self._get_db()
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        seven_days_ago = (now - timedelta(days=7)).isoformat()
        yesterday_start = (
            (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        )

        # Today's cost per user
        today_result = await db.execute(
            """SELECT user_id,
                      COALESCE(SUM(cost_usd), 0) AS today_cost,
                      COUNT(*) AS today_requests
                 FROM usage_metrics
                WHERE created_at >= ?
             GROUP BY user_id
            """,
            [today_start],
        )
        today_rows = today_result.rows or []
        if not today_rows:
            return []

        # 7-day baseline EXCLUDING today (so a single bad day doesn't dilute itself)
        # avg_daily = total_7d_cost_excluding_today / 7
        baseline_result = await db.execute(
            """SELECT user_id,
                      COALESCE(SUM(cost_usd), 0) / 7.0 AS baseline_avg
                 FROM usage_metrics
                WHERE created_at >= ?
                  AND created_at <  ?
             GROUP BY user_id
            """,
            [seven_days_ago, today_start],
        )
        baseline_map = {
            (row["user_id"] if "user_id" in row.keys() else row[0]): float(
                row["baseline_avg"] if "baseline_avg" in row.keys() else row[1]
            )
            for row in baseline_result.rows or []
        }

        # User metadata for the report
        user_ids = [row["user_id"] for row in today_rows]
        if not user_ids:
            return []
        placeholders = ",".join("?" for _ in user_ids)
        meta_result = await db.execute(
            f"""SELECT u.id, u.email, s.plan_type
                  FROM users u
                  LEFT JOIN subscriptions s ON s.user_id = u.id
                 WHERE u.id IN ({placeholders})
            """,
            user_ids,
        )
        meta_map = {
            row["id"]: {"email": row["email"], "plan": row.get("plan_type")}
            for row in meta_result.rows or []
        }

        hits: List[AnomalyHit] = []
        for row in today_rows:
            uid = row["user_id"]
            today_cost = float(row["today_cost"])
            today_reqs = int(row["today_requests"])
            baseline = baseline_map.get(uid, 0.0)

            threshold = max(LOWER_FLOOR_USD, multiplier * baseline)
            if today_cost <= threshold:
                continue
            # New users (no baseline) trigger only if they cross the floor by 5x
            if baseline == 0.0 and today_cost < (LOWER_FLOOR_USD * 5):
                continue

            ratio = (today_cost / baseline) if baseline > 0 else float("inf")
            meta = meta_map.get(uid, {})
            hits.append(
                AnomalyHit(
                    user_id=uid,
                    email=meta.get("email"),
                    plan=meta.get("plan"),
                    today_cost_usd=round(today_cost, 4),
                    baseline_avg_usd=round(baseline, 4),
                    multiplier=round(ratio, 2) if ratio != float("inf") else -1,
                    today_requests=today_reqs,
                )
            )
        return hits

    async def alert_owner(self, hits: List[AnomalyHit], owner_email: str) -> int:
        """Send a single grouped email if there are unalerted hits. Returns count emailed."""
        if not hits:
            return 0

        # Deduplicate via Redis flag (one alert per user per 24h)
        new_hits: List[AnomalyHit] = []
        if self.redis is not None:
            for hit in hits:
                key = f"cost_alert_sent:{hit.user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
                try:
                    existed = self.redis.get(key)
                    if existed:
                        continue
                    self.redis.setex(key, ALERT_DEDUPE_TTL, "1") if hasattr(
                        self.redis, "setex"
                    ) else self.redis.set(key, "1", ex=ALERT_DEDUPE_TTL)
                except Exception:
                    pass
                new_hits.append(hit)
        else:
            new_hits = hits

        if not new_hits:
            return 0

        from app.services.email_service import EmailService

        email = EmailService()

        rows_html = "".join(
            f"<tr>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{h.email or h.user_id}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{h.plan or '—'}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>${h.today_cost_usd}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>${h.baseline_avg_usd}/día</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{h.multiplier}×</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{h.today_requests}</td>"
            f"</tr>"
            for h in new_hits
        )
        subject = f"[Impuestify] Anomalía coste detectada: {len(new_hits)} usuario(s)"
        body = (
            "<h2>Anomalía de coste detectada</h2>"
            "<p>Los siguientes usuarios han gastado hoy más de lo habitual respecto a su media de los últimos 7 días.</p>"
            "<table style='border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px'>"
            "<thead><tr style='background:#f3f4f6'>"
            "<th style='padding:8px 10px;text-align:left'>Usuario</th>"
            "<th style='padding:8px 10px;text-align:left'>Plan</th>"
            "<th style='padding:8px 10px;text-align:right'>Hoy</th>"
            "<th style='padding:8px 10px;text-align:right'>Media 7d</th>"
            "<th style='padding:8px 10px;text-align:right'>Ratio</th>"
            "<th style='padding:8px 10px;text-align:right'>Requests</th>"
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table>"
            "<p style='color:#666;font-size:12px;margin-top:16px'>"
            "Esta alerta no se repetirá en las próximas 24h para los mismos usuarios."
            "</p>"
        )
        try:
            await email.send_email(to=owner_email, subject=subject, html=body)
            logger.info("Cost anomaly alert sent for %d users", len(new_hits))
            return len(new_hits)
        except Exception as e:
            logger.error("Failed to send anomaly alert: %s", e)
            return 0
