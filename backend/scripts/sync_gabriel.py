"""Sync Gabriel's subscription from Stripe and report final state.

Usage: PYTHONUTF8=1 python scripts/sync_gabriel.py
"""
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
env_path = backend_dir.parent / ".env"
load_dotenv(env_path)

from app.database.turso_client import TursoClient
from app.services.subscription_service import get_subscription_service


GABRIEL_USER_ID = "969e2925-26fd-4465-9036-2b02d1f90212"
GABRIEL_EMAIL = "gabriel.demacedo1@gmail.com"


async def main():
    print(f"Sync Stripe → DB for {GABRIEL_EMAIL}")

    service = await get_subscription_service()
    summary = await service.sync_from_stripe(GABRIEL_USER_ID)
    print("\nSync result:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    client = TursoClient()
    await client.connect()
    res = await client.execute(
        "SELECT * FROM subscriptions WHERE user_id = ?", [GABRIEL_USER_ID]
    )
    print("\nDB state after sync:")
    if res.rows:
        for k, v in res.rows[0].items():
            print(f"  {k}: {v}")
    else:
        print("  (no subscription row)")


if __name__ == "__main__":
    asyncio.run(main())
