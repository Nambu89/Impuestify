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
from app.services.push_service import send_deadline_alerts

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


async def main(dry_run: bool) -> None:
    """Main entry point for the alerts cron job."""
    logger.info(f"Starting deadline alert job (dry_run={dry_run})")

    if dry_run:
        logger.info("[DRY-RUN] Would run send_deadline_alerts() — skipping actual sends")
        logger.info("[DRY-RUN] Configure VAPID_PUBLIC_KEY + VAPID_PRIVATE_KEY in .env to enable push")
        return

    db = TursoClient()
    try:
        await db.connect()
        stats = await send_deadline_alerts(db=db)
        logger.info(f"Alert job completed: {stats}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send fiscal deadline push notifications")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual sends, just log")
    args = parser.parse_args()

    asyncio.run(main(args.dry_run))
