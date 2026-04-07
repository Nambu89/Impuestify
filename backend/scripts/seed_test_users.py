"""
Seed script for QA test users.

Creates 3 test users with complete fiscal profiles for E2E testing:
  1. test.particular@impuestify.es — Asalariada en Madrid
  2. test.autonomo@impuestify.es  — Autonomo disenador en Cataluna
  3. test.creator@impuestify.es   — Creador de contenido en Andalucia

All users: password = Test2026!
All users: subscription active (fake Stripe IDs)

Idempotent: deletes existing test users first, then re-inserts.

Usage:
    cd backend
    python scripts/seed_test_users.py
"""
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.auth.password import hash_password
from app.database.turso_client import TursoClient

# ──────────────────────────────────────────────
# Test user definitions
# ──────────────────────────────────────────────

PASSWORD = "Test2026!"
PASSWORD_HASH = hash_password(PASSWORD)

USER_PARTICULAR = {
    "id": "test-particular-00000001",
    "email": "test.particular@impuestify.es",
    "name": "Maria Garcia Lopez",
    "is_active": 1,
    "is_admin": 0,
    "is_owner": 0,
}

PROFILE_PARTICULAR = {
    "ccaa_residencia": "Comunidad de Madrid",
    "situacion_laboral": "asalariado",
    "tiene_vivienda": 1,
    "primera_vivienda": 0,
    "fecha_nacimiento": "1988-06-15",
    "datos_fiscales": json.dumps({
        "ingresos_trabajo": 35000.0,
        "ss_empleado": 2205.0,
        "num_descendientes": 1,
        "anios_nacimiento_desc": [2019],
        "custodia_compartida": False,
        "num_ascendientes_65": 0,
        "num_ascendientes_75": 0,
        "discapacidad_contribuyente": None,
        "intereses": 150.0,
        "dividendos": 300.0,
        "ganancias_fondos": 0.0,
        "ingresos_alquiler": 0.0,
        "valor_adquisicion_inmueble": 220000.0,
    }),
}

SUB_PARTICULAR = {
    "stripe_customer_id": "cus_test_particular_001",
    "stripe_subscription_id": "sub_test_particular_001",
    "plan_type": "particular",
    "status": "active",
    "current_period_start": "2026-04-01T00:00:00",
    "current_period_end": "2026-12-31T23:59:59",
}

USER_AUTONOMO = {
    "id": "test-autonomo-00000002",
    "email": "test.autonomo@impuestify.es",
    "name": "Carlos Martinez Ruiz",
    "is_active": 1,
    "is_admin": 0,
    "is_owner": 0,
}

PROFILE_AUTONOMO = {
    "ccaa_residencia": "Cataluna",
    "situacion_laboral": "autonomo",
    "tiene_vivienda": 1,
    "primera_vivienda": 1,
    "fecha_nacimiento": "1992-11-03",
    "datos_fiscales": json.dumps({
        "ingresos_trabajo": 0.0,
        "ss_empleado": 0.0,
        "num_descendientes": 0,
        "anios_nacimiento_desc": [],
        "custodia_compartida": False,
        "num_ascendientes_65": 1,
        "num_ascendientes_75": 0,
        "discapacidad_contribuyente": None,
        "intereses": 50.0,
        "dividendos": 0.0,
        "ganancias_fondos": 0.0,
        "ingresos_alquiler": 0.0,
        "valor_adquisicion_inmueble": 180000.0,
        "epigrafe_iae": "844",
        "tipo_actividad": "profesional",
        "fecha_alta_autonomo": "2023-01-10",
        "metodo_estimacion_irpf": "directa_simplificada",
        "regimen_iva": "general",
        "rendimientos_netos_mensuales": 3500.0,
        "base_cotizacion_reta": 1200.0,
        "territorio_foral": False,
        "territorio_historico": None,
        "tipo_retencion_facturas": 15.0,
        "tarifa_plana": False,
        "pluriactividad": False,
        "ceuta_melilla": False,
    }),
}

SUB_AUTONOMO = {
    "stripe_customer_id": "cus_test_autonomo_002",
    "stripe_subscription_id": "sub_test_autonomo_002",
    "plan_type": "autonomo",
    "status": "active",
    "current_period_start": "2026-04-01T00:00:00",
    "current_period_end": "2026-12-31T23:59:59",
}

USER_CREATOR = {
    "id": "test-creator-00000003",
    "email": "test.creator@impuestify.es",
    "name": "Laura Sanchez Torres",
    "is_active": 1,
    "is_admin": 0,
    "is_owner": 0,
}

PROFILE_CREATOR = {
    "ccaa_residencia": "Andalucia",
    "situacion_laboral": "autonomo",
    "tiene_vivienda": 0,
    "primera_vivienda": 0,
    "fecha_nacimiento": "1996-04-22",
    "datos_fiscales": json.dumps({
        "ingresos_trabajo": 0.0,
        "ss_empleado": 0.0,
        "num_descendientes": 0,
        "anios_nacimiento_desc": [],
        "custodia_compartida": False,
        "num_ascendientes_65": 0,
        "num_ascendientes_75": 0,
        "discapacidad_contribuyente": None,
        "intereses": 0.0,
        "dividendos": 0.0,
        "ganancias_fondos": 0.0,
        "ingresos_alquiler": 0.0,
        "valor_adquisicion_inmueble": 0.0,
        "epigrafe_iae": "8690",
        "tipo_actividad": "profesional",
        "fecha_alta_autonomo": "2025-06-01",
        "metodo_estimacion_irpf": "directa_simplificada",
        "regimen_iva": "general",
        "rendimientos_netos_mensuales": 4200.0,
        "base_cotizacion_reta": 960.0,
        "territorio_foral": False,
        "territorio_historico": None,
        "tipo_retencion_facturas": 7.0,
        "tarifa_plana": True,
        "pluriactividad": False,
        "ceuta_melilla": False,
        "plataformas": ["instagram", "youtube", "tiktok"],
        "cnae": "6039",
    }),
}

SUB_CREATOR = {
    "stripe_customer_id": "cus_test_creator_003",
    "stripe_subscription_id": "sub_test_creator_003",
    "plan_type": "creator",
    "status": "active",
    "current_period_start": "2026-04-01T00:00:00",
    "current_period_end": "2026-12-31T23:59:59",
}


async def seed_test_users():
    db = TursoClient()
    await db.connect()
    await db.init_schema()

    test_emails = [USER_PARTICULAR["email"], USER_AUTONOMO["email"], USER_CREATOR["email"]]

    # Clean up existing test users (cascade deletes profiles, subscriptions, etc.)
    for email in test_emails:
        result = await db.execute("SELECT id FROM users WHERE email = ?", [email])
        if result and result.rows:
            user_id = result.rows[0]["id"]
            # Delete in dependency order
            for table in [
                "subscriptions", "user_profiles", "messages",
                "conversations", "payslips", "reports",
                "workspace_file_embeddings", "workspace_files",
                "workspaces", "sessions", "usage_metrics",
            ]:
                try:
                    await db.execute(f"DELETE FROM {table} WHERE user_id = ?", [user_id])
                except Exception:
                    pass
            await db.execute("DELETE FROM users WHERE id = ?", [user_id])
            print(f"  Cleaned up existing user: {email}")

    # Insert users
    for user_data in [USER_PARTICULAR, USER_AUTONOMO, USER_CREATOR]:
        await db.execute(
            """INSERT INTO users (id, email, password_hash, name, is_active, is_admin, is_owner)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                user_data["id"],
                user_data["email"],
                PASSWORD_HASH,
                user_data["name"],
                user_data["is_active"],
                user_data["is_admin"],
                user_data["is_owner"],
            ],
        )
        print(f"  Created user: {user_data['email']}")

    # Insert profiles
    for user_data, profile in [
        (USER_PARTICULAR, PROFILE_PARTICULAR),
        (USER_AUTONOMO, PROFILE_AUTONOMO),
        (USER_CREATOR, PROFILE_CREATOR),
    ]:
        await db.execute(
            """INSERT INTO user_profiles
               (id, user_id, ccaa_residencia, situacion_laboral, tiene_vivienda,
                primera_vivienda, fecha_nacimiento, datos_fiscales)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                str(uuid.uuid4()),
                user_data["id"],
                profile["ccaa_residencia"],
                profile["situacion_laboral"],
                profile["tiene_vivienda"],
                profile["primera_vivienda"],
                profile.get("fecha_nacimiento"),
                profile["datos_fiscales"],
            ],
        )
        print(f"  Created profile: {user_data['email']} ({profile['situacion_laboral']}, {profile['ccaa_residencia']})")

    # Insert subscriptions
    for user_data, sub in [
        (USER_PARTICULAR, SUB_PARTICULAR),
        (USER_AUTONOMO, SUB_AUTONOMO),
        (USER_CREATOR, SUB_CREATOR),
    ]:
        await db.execute(
            """INSERT INTO subscriptions
               (id, user_id, stripe_customer_id, stripe_subscription_id,
                plan_type, status, current_period_start, current_period_end)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                str(uuid.uuid4()),
                user_data["id"],
                sub["stripe_customer_id"],
                sub["stripe_subscription_id"],
                sub["plan_type"],
                sub["status"],
                sub["current_period_start"],
                sub["current_period_end"],
            ],
        )
        print(f"  Created subscription: {user_data['email']} (plan={sub['plan_type']}, status={sub['status']})")

    await db.disconnect()
    print("\nDone! Test users ready for QA.")
    print(f"\n  Particular: {USER_PARTICULAR['email']} / {PASSWORD}")
    print(f"  Autonomo:   {USER_AUTONOMO['email']} / {PASSWORD}")
    print(f"  Creator:    {USER_CREATOR['email']} / {PASSWORD}")


if __name__ == "__main__":
    print("=== Seeding QA Test Users ===\n")
    asyncio.run(seed_test_users())
