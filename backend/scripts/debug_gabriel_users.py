"""Diagnostic: list all users in DB to confirm we're connected to prod."""
import sys
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
env_path = backend_dir.parent / ".env"
load_dotenv(env_path)

from app.database.turso_client import TursoClient


async def main():
    print(f"TURSO_DATABASE_URL: {os.getenv('TURSO_DATABASE_URL', '<none>')[:60]}")
    print(f"TURSO_AUTH_TOKEN set: {bool(os.getenv('TURSO_AUTH_TOKEN'))}")
    print()

    client = TursoClient()
    await client.connect()

    total = await client.execute("SELECT COUNT(*) AS c FROM users")
    print(f"Total users in DB: {total.rows[0]['c']}")
    print()

    print("=== Users with 'gabriel' or 'demacedo' or '@gmail' (last 20) ===")
    res = await client.execute(
        "SELECT id, email, name, created_at FROM users "
        "WHERE LOWER(email) LIKE '%gabriel%' OR LOWER(email) LIKE '%demacedo%' "
        "OR LOWER(email) LIKE '%@gmail%' "
        "ORDER BY created_at DESC LIMIT 20"
    )
    for r in res.rows:
        print(f"  {r['id'][:8]} | {r['email']} | {r.get('name')} | {r['created_at']}")

    print()
    print("=== Latest 10 users by created_at ===")
    res2 = await client.execute(
        "SELECT id, email, created_at FROM users ORDER BY created_at DESC LIMIT 10"
    )
    for r in res2.rows:
        print(f"  {r['created_at']} | {r['email']}")

    print()
    print("=== Subscriptions for cus_UR72Qf0IRWWDWV (Gabriel's Stripe customer) ===")
    res3 = await client.execute(
        "SELECT * FROM subscriptions WHERE stripe_customer_id = ?",
        ["cus_UR72Qf0IRWWDWV"],
    )
    if res3.rows:
        for k, v in res3.rows[0].items():
            print(f"  {k}: {v}")
    else:
        print("  (no subscription row found)")


if __name__ == "__main__":
    asyncio.run(main())
