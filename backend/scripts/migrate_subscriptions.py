"""
Subscription Migration Script for TaxIA/Impuestify

One-time script that:
1. Adds is_owner column to users table (idempotent)
2. Marks the owner (fernando.prada@proton.me) as is_owner=True
3. Creates Stripe customers for all existing users
4. Grants grace_period (until 2026-12-31) to all existing users
5. Owner gets status='active' with no expiration

Usage:
    cd backend
    python -m scripts.migrate_subscriptions
"""
import asyncio
import os
import sys
import uuid
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "fernando.prada@proton.me")
GRACE_PERIOD_END = "2026-12-31T23:59:59"


async def migrate():
    from app.database.turso_client import get_db_client
    from app.config import settings

    db = await get_db_client()

    # ------------------------------------------------------------------
    # Step 1: Add is_owner column (idempotent)
    # ------------------------------------------------------------------
    logger.info("Step 1: Ensuring is_owner column exists on users table...")
    try:
        await db.execute("ALTER TABLE users ADD COLUMN is_owner BOOLEAN DEFAULT 0")
        logger.info("  -> is_owner column added")
    except Exception:
        logger.info("  -> is_owner column already exists (OK)")

    # ------------------------------------------------------------------
    # Step 2: Mark owner
    # ------------------------------------------------------------------
    logger.info(f"Step 2: Marking {OWNER_EMAIL} as owner...")
    result = await db.execute(
        "UPDATE users SET is_owner = 1 WHERE LOWER(email) = LOWER(?)",
        [OWNER_EMAIL],
    )
    logger.info(f"  -> Rows affected: {getattr(result, 'rowcount', '?')}")

    # ------------------------------------------------------------------
    # Step 3: Ensure subscriptions table exists
    # ------------------------------------------------------------------
    logger.info("Step 3: Ensuring subscriptions table exists...")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            stripe_customer_id TEXT NOT NULL,
            stripe_subscription_id TEXT,
            plan_type TEXT NOT NULL DEFAULT 'particular',
            status TEXT NOT NULL DEFAULT 'inactive',
            current_period_start TEXT,
            current_period_end TEXT,
            cancel_at_period_end BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    logger.info("  -> subscriptions table ready")

    # ------------------------------------------------------------------
    # Step 4: Get all existing users
    # ------------------------------------------------------------------
    logger.info("Step 4: Fetching all existing users...")
    users_result = await db.execute("SELECT id, email, name FROM users")
    users = users_result.rows
    logger.info(f"  -> Found {len(users)} users")

    # ------------------------------------------------------------------
    # Step 5: Create Stripe customers + subscription records
    # ------------------------------------------------------------------
    stripe_available = settings.is_stripe_configured
    if stripe_available:
        import stripe as _stripe
        _stripe.api_key = settings.STRIPE_SECRET_KEY
        logger.info("Step 5: Stripe configured — will create real customers")
    else:
        logger.info("Step 5: Stripe NOT configured — using placeholder customer IDs")

    migrated = 0
    skipped = 0
    upgraded = 0

    for user in users:
        user_id = user["id"]
        email = user["email"]
        name = user.get("name", "")
        is_owner_user = email.lower() == OWNER_EMAIL.lower()

        # Check if subscription record already exists
        existing = await db.execute(
            "SELECT id, stripe_customer_id FROM subscriptions WHERE user_id = ?", [user_id]
        )
        if existing.rows:
            existing_cid = existing.rows[0]["stripe_customer_id"]
            # If placeholder, upgrade to real Stripe customer
            if stripe_available and existing_cid and existing_cid.startswith("placeholder_"):
                try:
                    customer = _stripe.Customer.create(
                        email=email,
                        name=name,
                        metadata={"user_id": user_id, "migrated": "true"},
                    )
                    await db.execute(
                        "UPDATE subscriptions SET stripe_customer_id = ?, updated_at = datetime('now') WHERE user_id = ?",
                        [customer.id, user_id],
                    )
                    upgraded += 1
                    logger.info(f"  -> UPGRADED {email}: {existing_cid} -> {customer.id}")
                except Exception as e:
                    logger.error(f"  -> FAILED to upgrade Stripe customer for {email}: {e}")
                    skipped += 1
            else:
                skipped += 1
                logger.info(f"  -> SKIP {email} (already has real Stripe customer: {existing_cid})")
            continue

        # Create Stripe customer
        if stripe_available:
            try:
                customer = _stripe.Customer.create(
                    email=email,
                    name=name,
                    metadata={"user_id": user_id, "migrated": "true"},
                )
                stripe_customer_id = customer.id
                logger.info(f"  -> Stripe customer created: {stripe_customer_id} for {email}")
            except Exception as e:
                logger.error(f"  -> FAILED to create Stripe customer for {email}: {e}")
                stripe_customer_id = f"placeholder_{user_id}"
        else:
            stripe_customer_id = f"placeholder_{user_id}"

        # Insert subscription record
        sub_id = str(uuid.uuid4())

        if is_owner_user:
            # Owner: active subscription, no expiration
            await db.execute(
                """
                INSERT INTO subscriptions (id, user_id, stripe_customer_id, plan_type, status)
                VALUES (?, ?, ?, 'owner', 'active')
                """,
                [sub_id, user_id, stripe_customer_id],
            )
            logger.info(f"  -> OWNER {email}: active subscription (no expiration)")
        else:
            # Regular user: grace period until 2026-12-31
            await db.execute(
                """
                INSERT INTO subscriptions (id, user_id, stripe_customer_id, plan_type, status, current_period_end)
                VALUES (?, ?, ?, 'particular', 'grace_period', ?)
                """,
                [sub_id, user_id, stripe_customer_id, GRACE_PERIOD_END],
            )
            logger.info(f"  -> {email}: grace_period until {GRACE_PERIOD_END}")

        migrated += 1

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("MIGRATION COMPLETE")
    logger.info(f"  Total users:    {len(users)}")
    logger.info(f"  Migrated:       {migrated}")
    logger.info(f"  Upgraded:       {upgraded} (placeholder -> real Stripe customer)")
    logger.info(f"  Skipped:        {skipped}")
    logger.info(f"  Owner email:    {OWNER_EMAIL}")
    logger.info(f"  Grace period:   until {GRACE_PERIOD_END}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(migrate())
