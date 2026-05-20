"""Seed demo user at startup when DEMO_MODE is enabled.

The demo user is a precreated account visitors share, used in white-label
demos (e.g. Coolify deploys). Idempotent: skips if user already exists.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.auth.password import hash_password
from app.config import settings

logger = logging.getLogger(__name__)


async def seed_demo_user(db) -> None:
    """Create the demo user if DEMO_MODE is on and credentials are configured.

    Safe to call on every startup — idempotent.
    """
    if not settings.DEMO_MODE:
        return
    if not settings.DEMO_USER_EMAIL or not settings.DEMO_USER_PASSWORD:
        logger.warning(
            "DEMO_MODE=true but DEMO_USER_EMAIL/DEMO_USER_PASSWORD not set — skipping seed"
        )
        return

    email = settings.DEMO_USER_EMAIL.lower().strip()
    existing = await db.execute("SELECT id FROM users WHERE email = ?", [email])
    if existing.rows:
        logger.info("Demo user %s already exists — skipping seed", email)
        return

    user_id = str(uuid.uuid4())
    pw_hash = hash_password(settings.DEMO_USER_PASSWORD)
    now = datetime.now(UTC).isoformat()

    await db.execute(
        """
        INSERT INTO users (
            id, email, password_hash, name,
            is_admin, is_owner, is_active,
            subscription_status, subscription_plan,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            user_id,
            email,
            pw_hash,
            "Demo",
            False,
            False,
            True,
            "active",  # bypass paywall in demo (also gated by SUBSCRIPTIONS_ENABLED=false)
            "autonomo",  # widest feature set
            now,
            now,
        ],
    )
    logger.info("Seeded demo user: %s", email)
