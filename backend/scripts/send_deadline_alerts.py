"""
Send Fiscal Deadline Push Alerts

Cron script that sends push notifications for upcoming fiscal deadlines.
Run daily via Railway scheduled job or GitHub Actions.

Features:
- Rate limit: max 3 notifications per user per day
- Idempotent: notification_log prevents duplicate alerts
- Dry-run mode for testing

Usage:
    python -m backend.scripts.send_deadline_alerts [--dry-run]
"""
import sys
import os
import asyncio
import argparse
import logging

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))
sys.path.insert(0, BACKEND_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.database.turso_client import TursoClient
from app.services.push_service import send_deadline_alerts, send_deadline_email_alerts

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def main(dry_run: bool) -> None:
    """Main entry point for the alerts cron job."""
    logger.info(f"Starting deadline alert job (dry_run={dry_run})")

    if dry_run:
        logger.info("[DRY-RUN] Would run send_deadline_alerts() — skipping actual sends")
        logger.info("[DRY-RUN] Configure VAPID_PUBLIC_KEY + VAPID_PRIVATE_KEY in .env to enable push")
        logger.info("[DRY-RUN] Would run send_deadline_email_alerts() — skipping email sends")
        logger.info("[DRY-RUN] Configure RESEND_API_KEY in .env to enable email alerts")
        return

    db = TursoClient()
    try:
        await db.connect()

        # --- Web Push alerts (15d / 5d / 1d) ---
        push_stats = await send_deadline_alerts(db=db)
        logger.info(f"Push alert job completed: {push_stats}")

        # --- Email alerts (30d, autonomo opt-in only) ---
        email_stats = await send_deadline_email_alerts(db=db)
        logger.info(f"Email alert job completed: {email_stats}")

        logger.info(
            f"Combined stats — "
            f"push_sent={push_stats.get('notifications_sent', 0)}, "
            f"emails_sent={email_stats.get('emails_sent', 0)}, "
            f"errors={push_stats.get('errors', 0) + email_stats.get('errors', 0)}"
        )
    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send fiscal deadline push notifications")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual sends, just log")
    args = parser.parse_args()

    asyncio.run(main(args.dry_run))
