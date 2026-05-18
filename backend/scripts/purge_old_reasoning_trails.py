"""
Monthly cron: purge reasoning_trails rows older than 24 months.

EU AI Act Art. 86 right-to-explanation requires retention while the user
might reasonably ask. AEPD/AESIA recommends 24 months for chat logs in
financial advisory unless tax law mandates longer (4 years for fiscal
records). 24m is the conservative default; bump if needed.

Run monthly: '0 4 1 * *' (4 AM on the 1st of each month).
"""

import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta, timezone
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

RETENTION_MONTHS = 24


async def main():
    from app.database.turso_client import get_db_client

    db = await get_db_client()
    cutoff = (datetime.now(UTC) - timedelta(days=RETENTION_MONTHS * 30)).isoformat()

    count_result = await db.execute(
        "SELECT COUNT(*) AS c FROM reasoning_trails WHERE created_at < ?",
        [cutoff],
    )
    pending = (count_result.rows[0]["c"] if count_result.rows else 0) or 0
    logger.info(f"reasoning_trails older than {RETENTION_MONTHS}m: {pending}")

    if pending == 0:
        return

    await db.execute(
        "DELETE FROM reasoning_trails WHERE created_at < ?",
        [cutoff],
    )
    logger.info(f"Deleted {pending} expired reasoning_trails rows")


if __name__ == "__main__":
    asyncio.run(main())
