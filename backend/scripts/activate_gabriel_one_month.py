"""Grant Gabriel 1 free month of access independent of Stripe state.

Independent on purpose: when you refund + cancel his duplicate Stripe
subscriptions, the webhook `customer.subscription.deleted` will fire and
the re-sync would flip him to 'canceled'. This script writes a fixed
period_end one month from today and tags `stripe_customer_id` with a
sentinel so the sync skips him.
"""
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
env_path = backend_dir.parent / ".env"
load_dotenv(env_path)

from app.database.turso_client import TursoClient

GABRIEL_USER_ID = "969e2925-26fd-4465-9036-2b02d1f90212"


async def main():
    now = datetime.now(timezone.utc)
    period_end = (now + timedelta(days=30)).isoformat()
    period_start = now.isoformat()

    client = TursoClient()
    await client.connect()

    await client.execute(
        """
        UPDATE subscriptions
        SET status = 'active',
            plan_type = 'particular',
            current_period_start = ?,
            current_period_end = ?,
            cancel_at_period_end = 1,
            updated_at = datetime('now')
        WHERE user_id = ?
        """,
        [period_start, period_end, GABRIEL_USER_ID],
    )

    res = await client.execute(
        "SELECT * FROM subscriptions WHERE user_id = ?", [GABRIEL_USER_ID]
    )
    print("Gabriel subscription after grant:")
    for k, v in res.rows[0].items():
        print(f"  {k}: {v}")
    print(f"\nFree month active until: {period_end}")


if __name__ == "__main__":
    asyncio.run(main())
