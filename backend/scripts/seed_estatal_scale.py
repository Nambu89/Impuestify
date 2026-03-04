"""
Seed the Estatal (state) general IRPF scale into irpf_scales table.

Source: Art. 63.1 LIRPF (Ley 35/2006, modified by Ley 11/2020).
These values have been stable since 2021 and apply to 2024 and 2025.

Usage:
    cd backend
    python scripts/seed_estatal_scale.py
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

from app.database.turso_client import TursoClient

# Official Estatal general scale (Art. 63.1 LIRPF)
# Unchanged since 2021
ESTATAL_GENERAL_SCALE = [
    # (tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable)
    (1, 12450.00, 0.00, 12450.00, 9.50),
    (2, 20200.00, 1182.75, 7750.00, 12.00),
    (3, 35200.00, 2112.75, 15000.00, 15.00),
    (4, 60000.00, 4362.75, 24800.00, 18.50),
    (5, 300000.00, 8950.75, 240000.00, 22.50),
    (6, 999999.00, 62950.75, 699999.00, 24.50),
]

YEARS = [2024, 2025]


async def seed_estatal_scale():
    """Insert Estatal general IRPF scale for 2024 and 2025."""
    print("=" * 60)
    print("SEED: Escala Estatal General IRPF")
    print("=" * 60)

    db = TursoClient()
    await db.connect()

    for year in YEARS:
        # Check if already exists
        existing = await db.execute(
            "SELECT COUNT(*) as cnt FROM irpf_scales WHERE jurisdiction = 'Estatal' AND year = ? AND scale_type = 'general'",
            [year],
        )
        count = existing.rows[0]["cnt"] if existing.rows else 0

        if count > 0:
            print(f"  {year}: Ya existen {count} tramos. Eliminando para re-insertar...")
            await db.execute(
                "DELETE FROM irpf_scales WHERE jurisdiction = 'Estatal' AND year = ? AND scale_type = 'general'",
                [year],
            )

        for tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable in ESTATAL_GENERAL_SCALE:
            await db.execute(
                """INSERT INTO irpf_scales
                   (id, jurisdiction, year, scale_type, tramo_num,
                    base_hasta, cuota_integra, resto_base, tipo_aplicable)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    str(uuid.uuid4()),
                    "Estatal",
                    year,
                    "general",
                    tramo_num,
                    base_hasta,
                    cuota_integra,
                    resto_base,
                    tipo_aplicable,
                ],
            )

        print(f"  {year}: Insertados {len(ESTATAL_GENERAL_SCALE)} tramos")

    # Verify
    print("\nVerificacion:")
    for year in YEARS:
        result = await db.execute(
            "SELECT tramo_num, base_hasta, tipo_aplicable FROM irpf_scales WHERE jurisdiction = 'Estatal' AND year = ? AND scale_type = 'general' ORDER BY tramo_num",
            [year],
        )
        print(f"  {year}: {len(result.rows)} tramos")
        for row in result.rows:
            print(f"    Tramo {row['tramo_num']}: hasta {row['base_hasta']:,.2f} EUR al {row['tipo_aplicable']}%")

    await db.disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(seed_estatal_scale())
