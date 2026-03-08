"""
Seed autonomous_quotas table with 2026 data.

2026 is the final year of the transitional RETA quota system (RD-l 13/2022).
Tramos are updated from the Seguridad Social official schedule.
Source: https://www.seg-social.es/wps/portal/wss/internet/Trabajadores/CotizacionRecaudacionTrabajadores/36537

Usage:
    cd backend
    python scripts/seed_autonomous_quotas_2026.py
"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

# 2026 Autonomous Quotas Data (15 tramos)
# Source: Seguridad Social — Tabla definitiva 2026 (RD-l 13/2022)
# Cuotas ligeramente superiores a 2025 (ultimo ano transitorio)
TRAMOS_2026 = [
    # Tramo, Rend Min, Rend Max, Base Min, Base Max, Cuota Min, Cuota Max
    (1,     0,    670,  653.59,  718.94,  200.00,  226.00),
    (2,   670,    900,  718.94, 1018.82,  226.00,  320.00),
    (3,   900, 1166.70, 849.67, 1018.82,  267.00,  320.00),
    (4, 1166.70, 1300,  950.98, 1018.82,  299.00,  320.00),
    (5,  1300,   1500,  960.78, 1018.82,  302.00,  320.00),
    (6,  1500,   1700,  960.78, 1018.82,  302.00,  320.00),
    (7,  1700,   1850, 1045.75, 1143.79,  329.00,  360.00),
    (8,  1850,   2030, 1062.09, 1209.15,  334.00,  380.00),
    (9,  2030,   2330, 1078.43, 1274.51,  339.00,  401.00),
    (10, 2330,   2760, 1143.79, 1372.55,  360.00,  431.00),
    (11, 2760,   3190, 1209.15, 1471.24,  380.00,  462.00),
    (12, 3190,   3620, 1274.51, 1569.93,  401.00,  494.00),
    (13, 3620,   4050, 1372.55, 1700.65,  431.00,  534.00),
    (14, 4050,   6000, 1438.24, 1928.10,  452.00,  606.00),
    (15, 6000,   None, 1633.99, 4909.50,  514.00, 1543.00),
]


async def seed_2026():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")

    if not turso_url or not turso_token:
        print("Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN")
        return

    db = TursoClient(turso_url, turso_token)
    await db.connect()
    print("Connected to Turso")

    # Idempotent: clear existing 2026 data
    await db.execute("DELETE FROM autonomous_quotas WHERE year = 2026")
    print("Cleared existing 2026 data")

    regions = [
        ("general", 0),
        ("ceuta", 50),
        ("melilla", 50),
    ]

    total = 0
    for region, bonif_pct in regions:
        print(f"\nInserting 15 tramos for {region} (bonif {bonif_pct}%)...")
        for t in TRAMOS_2026:
            tramo_num, rend_min, rend_max, base_min, base_max, cuota_min, cuota_max = t

            if bonif_pct > 0:
                cuota_min_bonif = round(base_min * 0.1725, 2)
                cuota_max_bonif = round(base_max * 0.1725, 2)
            else:
                cuota_min_bonif = None
                cuota_max_bonif = None

            await db.execute(
                """INSERT INTO autonomous_quotas (
                    year, tramo_number,
                    rendimientos_netos_min, rendimientos_netos_max,
                    base_cotizacion_min, base_cotizacion_max,
                    cuota_min, cuota_max,
                    region, bonificacion_percent,
                    cuota_min_bonificada, cuota_max_bonificada
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    2026, tramo_num,
                    rend_min, rend_max,
                    base_min, base_max,
                    cuota_min, cuota_max,
                    region, bonif_pct,
                    cuota_min_bonif, cuota_max_bonif,
                ],
            )
            total += 1
            print(f"  Tramo {tramo_num}: {rend_min}-{rend_max or 'inf'} -> {cuota_min}-{cuota_max} EUR")

    result = await db.execute("SELECT COUNT(*) as count FROM autonomous_quotas WHERE year = 2026")
    count = result.rows[0]["count"]
    print(f"\nInserted {count} records (expected {total})")

    # Verify query
    test = await db.execute(
        """SELECT tramo_number, cuota_min, cuota_max FROM autonomous_quotas
           WHERE year = 2026 AND region = 'general'
           AND rendimientos_netos_min <= 2500
           AND (rendimientos_netos_max >= 2500 OR rendimientos_netos_max IS NULL)""",
    )
    if test.rows:
        r = test.rows[0]
        print(f"Test: 2500 EUR/mes -> Tramo {r['tramo_number']}, cuota {r['cuota_min']}-{r['cuota_max']} EUR")

    await db.disconnect()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(seed_2026())
