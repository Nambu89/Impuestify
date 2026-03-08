"""
Seed foral IRPF scales for the 4 foral territories (2025 data).

Covers:
- Araba/Alava  (Norma Foral 33/2013, actualizada 2025)  — 7 tramos
- Bizkaia       (Norma Foral 13/2013, actualizada 2025)  — 7 tramos
- Gipuzkoa     (Norma Foral 3/2014, actualizada 2025)   — 7 tramos
- Navarra       (Ley Foral 22/1998, DFL 2025)             — 11 tramos

Key differences from common-regime scales:
- scale_type = 'foral' (not 'general')
- Single unified scale (not estatal + autonomica split)
- cuota_integra / resto_base follow the same accumulated-bracket format

Usage:
    cd backend
    PYTHONUTF8=1 python scripts/seed_foral_scales.py
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient  # noqa: E402

# ---------------------------------------------------------------------------
# Scale data
# Format: (tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable)
#
# cuota_integra = cumulative quota from all previous brackets
# resto_base    = width of this bracket (base_hasta - prev base_hasta)
# For the last open-ended bracket, base_hasta = 999999.00
# ---------------------------------------------------------------------------

# Araba and Bizkaia share identical 2025 tramos
_ARABA_BIZKAIA_TRAMOS = [
    (1, 17360.00,  0.00,       17360.00, 23.00),
    (2, 33280.00,  3992.80,    15920.00, 28.00),
    (3, 42240.00,  8449.60,     8960.00, 34.00),
    (4, 56760.00, 11496.00,    14520.00, 40.00),
    (5, 76320.00, 17304.00,    19560.00, 45.00),
    (6, 120840.00, 26106.00,   44520.00, 46.00),
    (7, 999999.00, 46585.20,  879159.00, 49.00),
]

FORAL_SCALES = {
    "Araba": _ARABA_BIZKAIA_TRAMOS,
    "Bizkaia": _ARABA_BIZKAIA_TRAMOS,
    "Gipuzkoa": [
        (1, 17030.00,  0.00,       17030.00, 23.00),
        (2, 32650.00,  3916.90,    15620.00, 28.00),
        (3, 41435.00,  8289.50,     8785.00, 34.00),
        (4, 55680.00, 11276.40,    14245.00, 40.00),
        (5, 74880.00, 16974.40,    19200.00, 45.00),
        (6, 118560.00, 25614.40,   43680.00, 46.00),
        (7, 999999.00, 45707.20,  881439.00, 49.00),
    ],
    "Navarra": [
        (1,   4484.00,     0.00,     4484.00, 13.00),
        (2,   8968.00,   582.92,     4484.00, 22.00),
        (3,  13452.00,  1569.40,     4484.00, 25.00),
        (4,  17936.00,  2690.40,     4484.00, 28.00),
        (5,  22420.00,  3945.92,     4484.00, 33.50),
        (6,  33632.00,  5448.56,    11212.00, 37.00),
        (7,  50448.00,  9596.00,    16816.00, 40.50),
        (8,  67264.00, 16406.48,    16816.00, 44.00),
        (9,  92372.00, 23805.52,    25108.00, 46.50),
        (10, 163128.00, 35475.72,   70756.00, 48.00),
        (11, 999999.00, 69438.60,  836871.00, 52.00),
    ],
}

YEARS = [2024, 2025]


async def seed_foral_scales() -> None:
    """Insert foral IRPF scales for all 4 territories and 2 years."""
    print("=" * 60)
    print("SEED: Escalas Forales IRPF (Araba, Bizkaia, Gipuzkoa, Navarra)")
    print("=" * 60)

    db = TursoClient()
    await db.connect()

    for jurisdiction, tramos in FORAL_SCALES.items():
        for year in YEARS:
            existing = await db.execute(
                "SELECT COUNT(*) as cnt FROM irpf_scales "
                "WHERE jurisdiction = ? AND year = ? AND scale_type = 'foral'",
                [jurisdiction, year],
            )
            count = existing.rows[0]["cnt"] if existing.rows else 0

            if count > 0:
                print(
                    f"  {jurisdiction} {year}: {count} tramos existentes. "
                    "Eliminando para re-insertar..."
                )
                await db.execute(
                    "DELETE FROM irpf_scales "
                    "WHERE jurisdiction = ? AND year = ? AND scale_type = 'foral'",
                    [jurisdiction, year],
                )

            for tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable in tramos:
                await db.execute(
                    """INSERT INTO irpf_scales
                       (id, jurisdiction, year, scale_type, tramo_num,
                        base_hasta, cuota_integra, resto_base, tipo_aplicable)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        str(uuid.uuid4()),
                        jurisdiction,
                        year,
                        "foral",
                        tramo_num,
                        base_hasta,
                        cuota_integra,
                        resto_base,
                        tipo_aplicable,
                    ],
                )

            print(f"  {jurisdiction} {year}: Insertados {len(tramos)} tramos")

    # Verification
    print("\nVerificacion:")
    for jurisdiction in FORAL_SCALES:
        for year in YEARS:
            result = await db.execute(
                "SELECT tramo_num, base_hasta, tipo_aplicable "
                "FROM irpf_scales "
                "WHERE jurisdiction = ? AND year = ? AND scale_type = 'foral' "
                "ORDER BY tramo_num",
                [jurisdiction, year],
            )
            n = len(result.rows)
            last = result.rows[-1] if result.rows else {}
            print(
                f"  {jurisdiction} {year}: {n} tramos, "
                f"tipo marginal maximo {last.get('tipo_aplicable', '?')}%"
            )

    await db.disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(seed_foral_scales())
