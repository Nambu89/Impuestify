"""
Cron entry point for cost anomaly detection.

Run hourly via Railway cron (or manually). Checks usage_metrics for users
whose today's spend is 10x their 7-day baseline and emails the owner.

Configure as Railway service "cron" with schedule '0 * * * *' (top of hour).
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT.parent / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    from app.services.cost_anomaly_detector import CostAnomalyDetector

    owner_email = os.getenv("OWNER_EMAIL") or os.getenv("ALERT_EMAIL")
    if not owner_email:
        logger.error("OWNER_EMAIL or ALERT_EMAIL not set — refusing to run.")
        sys.exit(1)

    redis_client = None
    try:
        from app.upstash_init import upstash_client as _client  # type: ignore

        redis_client = _client
    except Exception:
        try:
            from app.utils.upstash import get_upstash_client

            redis_client = get_upstash_client()
        except Exception as e:
            logger.warning(f"Upstash client unavailable, dedupe disabled: {e}")

    detector = CostAnomalyDetector(redis_client=redis_client)
    hits = await detector.find_anomalies()
    if not hits:
        logger.info("No cost anomalies detected.")
        return

    logger.warning("Detected %d cost anomalies", len(hits))
    for h in hits:
        logger.warning(
            "  user=%s plan=%s today=$%.4f baseline=$%.4f/d ratio=%.2fx",
            h.email or h.user_id,
            h.plan,
            h.today_cost_usd,
            h.baseline_avg_usd,
            h.multiplier,
        )

    sent = await detector.alert_owner(hits, owner_email=owner_email)
    logger.info("Sent alerts for %d users (deduped within 24h)", sent)


if __name__ == "__main__":
    asyncio.run(main())
