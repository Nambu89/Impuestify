"""
Seed the QA red-team user used by the Promptfoo nightly workflow.

Creates `qa-redteam@impuestify.es` with a long random password (read from the
QA_REDTEAM_PASSWORD env var, OR auto-generated and printed to stdout once).

Run-once / idempotent: if the user already exists, the password is rotated
to whatever QA_REDTEAM_PASSWORD says. If the env var is not set we keep the
existing user untouched.

Why a dedicated user (not test.particular):
- Activity from the red-team suite stays out of QA-functional metrics.
- Easier to revoke if the credentials leak (delete user / change password
  without affecting other QA flows).
- Tracks failed-login telemetry separate from real users.

The user is created with subscription_status='active' (owner-bypassed plan
for fiscal questions) and is_active=1. NO is_admin and NO is_owner.
"""

import asyncio
import logging
import os
import secrets
import sys
import uuid
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

REDTEAM_EMAIL = "qa-redteam@impuestify.es"


async def _ensure_active_subscription(db, user_id: str) -> None:
    """Make sure the redteam user has one active 'autonomo' subscription row."""
    existing = await db.execute(
        "SELECT id FROM subscriptions WHERE user_id = ? LIMIT 1",
        [user_id],
    )
    if existing.rows:
        await db.execute(
            "UPDATE subscriptions SET status = 'active', plan_type = 'autonomo', "
            "updated_at = datetime('now') WHERE user_id = ?",
            [user_id],
        )
        logger.info("Subscription already present — refreshed to active autonomo")
        return

    sub_id = str(uuid.uuid4())
    fake_stripe_customer = f"cus_redteam_{user_id[:8]}"
    await db.execute(
        """
        INSERT INTO subscriptions
            (id, user_id, plan_type, status, stripe_customer_id, created_at, updated_at)
        VALUES (?, ?, 'autonomo', 'active', ?, datetime('now'), datetime('now'))
        """,
        [sub_id, user_id, fake_stripe_customer],
    )
    logger.info("Created active autonomo subscription for redteam user")


async def main():
    from app.database.turso_client import get_db_client
    from app.auth.password import hash_password as _hash_password

    db = await get_db_client()

    password = os.getenv("QA_REDTEAM_PASSWORD")
    rotate_only = bool(password)
    if not password:
        # Generate one if user is creating fresh
        password = secrets.token_urlsafe(24)

    existing = await db.execute(
        "SELECT id, email FROM users WHERE email = ? LIMIT 1",
        [REDTEAM_EMAIL],
    )

    if existing.rows:
        user_id = existing.rows[0]["id"]
        if os.getenv("QA_REDTEAM_PASSWORD"):
            await db.execute(
                "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
                [_hash_password(password), user_id],
            )
            logger.info(f"Password rotated for {REDTEAM_EMAIL}")
        else:
            logger.info(f"User {REDTEAM_EMAIL} already exists. Use QA_REDTEAM_PASSWORD to rotate.")
        # Ensure subscription exists even if previous run left a partial state
        await _ensure_active_subscription(db, user_id)
        if os.getenv("QA_REDTEAM_PASSWORD") and not rotate_only:
            print(f"\nNEW PASSWORD: {password}\n(Store as GitHub secret PROMPTFOO_AUTH_PASSWORD)\n")
        return

    # Create new user
    user_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO users
            (id, email, password_hash, name, is_admin, is_owner, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, 0, 1, datetime('now'), datetime('now'))
        """,
        [user_id, REDTEAM_EMAIL, _hash_password(password), "QA Red Team Bot"],
    )

    await _ensure_active_subscription(db, user_id)

    logger.info(f"Created user {REDTEAM_EMAIL} with active 'autonomo' subscription.")
    if not rotate_only:
        print()
        print("=" * 70)
        print(f"REDTEAM USER CREATED")
        print(f"  email:    {REDTEAM_EMAIL}")
        print(f"  password: {password}")
        print()
        print("Add as GitHub repository secrets:")
        print(f"  PROMPTFOO_AUTH_EMAIL    = {REDTEAM_EMAIL}")
        print(f"  PROMPTFOO_AUTH_PASSWORD = {password}")
        print("=" * 70)
        print()


if __name__ == "__main__":
    asyncio.run(main())
