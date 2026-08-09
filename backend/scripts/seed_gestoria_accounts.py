"""Alta idempotente de cuentas gestoría seleccionadas (acceso full + account_type='gestoria').

Uso:
    cd backend && python scripts/seed_gestoria_accounts.py

Edita GESTORIAS abajo con (email, nombre, password) de cada gestoría seleccionada.
Un live run requiere credenciales Turso reales (TURSO_DATABASE_URL + TURSO_AUTH_TOKEN).
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT.parent / ".env")
except ImportError:
    pass

from app.auth.password import hash_password
from app.database.turso_client import get_db_client

# ──────────────────────────────────────────────────────────────────────────────
# Rellena esta lista antes de ejecutar en producción.
# Formato: (email, nombre_visible, password_inicial)
# ──────────────────────────────────────────────────────────────────────────────
GESTORIAS: list[tuple[str, str, str]] = [
    # ("gestoria1@example.com", "Gestoría Uno", "CambiarEsto123!"),
]

# Fecha de fin de suscripción activa (autonomo)
SUBSCRIPTION_END = "2026-12-31T23:59:59"


async def seed() -> None:
    if not GESTORIAS:
        print("GESTORIAS vacío — nada que hacer. Hecho.")
        return

    db = await get_db_client()
    now = datetime.now(UTC).isoformat()

    for email, name, password in GESTORIAS:
        # ── Comprobar si el usuario ya existe ──────────────────────────────
        existing = await db.execute(
            "SELECT id FROM users WHERE email = ?",
            [email],
        )
        if existing.rows:
            user_id = existing.rows[0]["id"]
            print(f"= ya existe: {email} ({user_id})")
        else:
            user_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO users
                   (id, email, password_hash, name, is_active, is_admin, is_owner,
                    account_type, created_at, updated_at)
                   VALUES (?, ?, ?, ?, 1, 0, 0, 'gestoria', ?, ?)""",
                [user_id, email, hash_password(password), name, now, now],
            )
            print(f"+ creada gestoría: {email} ({user_id})")

        # ── Garantizar account_type='gestoria' (idempotente) ──────────────
        await db.execute(
            "UPDATE users SET account_type = 'gestoria', updated_at = ? WHERE id = ?",
            [now, user_id],
        )

        # ── Suscripción autonomo activa hasta SUBSCRIPTION_END ─────────────
        sub = await db.execute(
            "SELECT id FROM subscriptions WHERE user_id = ?",
            [user_id],
        )
        if sub.rows:
            await db.execute(
                """UPDATE subscriptions
                   SET plan_type = 'autonomo', status = 'active',
                       current_period_start = ?, current_period_end = ?,
                       updated_at = ?
                   WHERE user_id = ?""",
                [now, SUBSCRIPTION_END, now, user_id],
            )
            print(f"  ~ suscripción actualizada: {email}")
        else:
            fake_customer_id = f"gestoria_{user_id[:8]}"
            await db.execute(
                """INSERT INTO subscriptions
                   (id, user_id, stripe_customer_id, plan_type, status,
                    current_period_start, current_period_end, created_at, updated_at)
                   VALUES (?, ?, ?, 'autonomo', 'active', ?, ?, ?, ?)""",
                [str(uuid.uuid4()), user_id, fake_customer_id, now, SUBSCRIPTION_END, now, now],
            )
            print(f"  + suscripción creada: {email}")

    print("\nHecho.")


if __name__ == "__main__":
    asyncio.run(seed())
