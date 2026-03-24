"""
Seed CCAA autonomous IRPF scales (escala autonómica) for all 15 CCAA de régimen común.

Sources:
- AEAT Manual Práctico Renta 2024 - Gravamen Autonómico
- Ministerio de Hacienda - Capítulo IV Tributación Autonómica 2025

Usage:
    python scripts/seed_ccaa_scales.py
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

from app.database.turso_client import TursoClient


# Format: (tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable)

SCALES = {
    # 1. ANDALUCIA — Art. 19 Ley 5/2021
    "Andalucía": [
        (1, 13000, 0, 13000, 9.50),
        (2, 21100, 1235, 8100, 12.00),
        (3, 35200, 2207, 14100, 15.00),
        (4, 60000, 4322, 24800, 18.50),
        (5, 999999, 8910, 999999, 22.50),
    ],
    # 2. ARAGON — Art. 110-1 DLeg 1/2005
    "Aragón": [
        (1, 13072.50, 0, 13072.50, 9.50),
        (2, 21210, 1241.89, 8137.50, 12.00),
        (3, 36960, 2218.39, 15750, 15.00),
        (4, 52500, 4580.89, 15540, 18.50),
        (5, 60000, 7455.79, 7500, 20.50),
        (6, 80000, 8993.29, 20000, 23.00),
        (7, 90000, 13593.29, 10000, 24.00),
        (8, 130000, 15993.29, 40000, 25.00),
        (9, 999999, 25993.29, 999999, 25.50),
    ],
    # 3. ASTURIAS — Art. 2 DLeg 2/2014 (2024 rates)
    "Asturias": [
        (1, 12450, 0, 12450, 10.00),
        (2, 17707.20, 1245, 5257.20, 12.00),
        (3, 33007.20, 1875.86, 15300, 14.00),
        (4, 53407.20, 4017.86, 20400, 18.50),
        (5, 70000, 7791.86, 16592.80, 21.50),
        (6, 90000, 11359.32, 20000, 22.50),
        (7, 175000, 15859.32, 85000, 25.00),
        (8, 999999, 37109.32, 999999, 25.50),
    ],
    # 4. ILLES BALEARS — DLeg 1/2014 art. 2 (mod. Ley 12/2023)
    "Baleares": [
        (1, 10000, 0, 10000, 9.00),
        (2, 18000, 900, 8000, 11.25),
        (3, 30000, 1800, 12000, 14.25),
        (4, 48000, 3510, 18000, 17.50),
        (5, 70000, 6660, 22000, 19.00),
        (6, 90000, 10840, 20000, 21.75),
        (7, 120000, 15190, 30000, 22.75),
        (8, 175000, 22015, 55000, 23.75),
        (9, 999999, 35077.50, 999999, 24.75),
    ],
    # 5. CANARIAS — Art. 18 bis DLeg 1/2009 (mod. Ley 5/2024)
    "Canarias": [
        (1, 13465, 0, 13465, 9.00),
        (2, 19022, 1211.85, 5557, 11.50),
        (3, 35185, 1850.91, 16163, 14.00),
        (4, 56382, 4113.73, 21197, 18.50),
        (5, 91350, 8035.17, 34968, 23.50),
        (6, 121200, 16252.65, 29850, 25.00),
        (7, 999999, 23715.15, 999999, 26.00),
    ],
    # 6. CANTABRIA — Ley 3/2023
    "Cantabria": [
        (1, 13000, 0, 13000, 8.50),
        (2, 21000, 1105, 8000, 11.00),
        (3, 35200, 1985, 14200, 14.50),
        (4, 60000, 4044, 24800, 18.00),
        (5, 90000, 8508, 30000, 22.50),
        (6, 999999, 15258, 999999, 24.50),
    ],
    # 7. CASTILLA Y LEON — DLeg 1/2013 art. 1 (mod. Ley 2/2023)
    "Castilla y León": [
        (1, 12450, 0, 12450, 9.00),
        (2, 20200, 1120.50, 7750, 12.00),
        (3, 35200, 2050.50, 15000, 14.00),
        (4, 53407.20, 4150.50, 18207.20, 18.50),
        (5, 999999, 7518.83, 999999, 21.50),
    ],
    # 8. CASTILLA-LA MANCHA — Art. 13 bis Ley 8/2013 (= supletoria)
    "Castilla-La Mancha": [
        (1, 12450, 0, 12450, 9.50),
        (2, 20200, 1182.75, 7750, 12.00),
        (3, 35200, 2112.75, 15000, 15.00),
        (4, 60000, 4362.75, 24800, 18.50),
        (5, 999999, 8950.75, 999999, 22.50),
    ],
    # 9. CATALUNA — DLeg 1/2024
    "Cataluña": [
        (1, 12450, 0, 12450, 10.50),
        (2, 17707.20, 1307.25, 5257.20, 12.00),
        (3, 21000, 1938.11, 3292.80, 14.00),
        (4, 33007.20, 2399.10, 12007.20, 15.00),
        (5, 53407.20, 4200.18, 20400, 18.80),
        (6, 90000, 8035.38, 36592.80, 21.50),
        (7, 120000, 15902.83, 30000, 23.50),
        (8, 175000, 22952.83, 55000, 24.50),
        (9, 999999, 36427.83, 999999, 25.50),
    ],
    # 10. EXTREMADURA — Art. 1 DLeg 1/2018
    "Extremadura": [
        (1, 12450, 0, 12450, 8.00),
        (2, 20200, 996, 7750, 10.00),
        (3, 24200, 1771, 4000, 16.00),
        (4, 35200, 2411, 11000, 17.50),
        (5, 60000, 4336, 24800, 21.00),
        (6, 80200, 9544, 20200, 23.50),
        (7, 99200, 14291, 19000, 24.00),
        (8, 120200, 18851, 21000, 24.50),
        (9, 999999, 23996, 999999, 25.00),
    ],
    # 11. GALICIA — Art. 4 DLeg 1/2011
    "Galicia": [
        (1, 12985.35, 0, 12985.35, 9.00),
        (2, 21068.60, 1168.68, 8083.25, 11.65),
        (3, 35200, 2110.38, 14131.40, 14.90),
        (4, 60000, 4215.96, 24800, 18.40),
        (5, 999999, 8779.16, 999999, 22.50),
    ],
    # 12. LA RIOJA — Art. 31 Ley 10/2017 (mod. Ley 13/2023)
    "La Rioja": [
        (1, 12450, 0, 12450, 8.00),
        (2, 20200, 996, 7750, 10.60),
        (3, 35200, 1817.50, 15000, 13.60),
        (4, 40000, 3857.50, 4800, 17.80),
        (5, 50000, 4711.90, 10000, 18.30),
        (6, 60000, 6541.90, 10000, 19.00),
        (7, 120000, 8441.90, 60000, 24.50),
        (8, 999999, 23141.90, 999999, 27.00),
    ],
    # 13. MADRID — Art. 1 DLeg 1/2010
    "Madrid": [
        (1, 13362.22, 0, 13362.22, 8.50),
        (2, 19004.63, 1135.79, 5642.41, 10.70),
        (3, 35425.68, 1739.53, 16421.05, 12.80),
        (4, 57320.40, 3841.42, 21894.72, 17.40),
        (5, 999999, 7651.10, 999999, 20.50),
    ],
    # 14. MURCIA — DLeg 1/2010
    "Murcia": [
        (1, 12450, 0, 12450, 9.50),
        (2, 20200, 1182.75, 7750, 11.20),
        (3, 34000, 2050.75, 13800, 13.30),
        (4, 60000, 3886.15, 26000, 17.90),
        (5, 999999, 8540.15, 999999, 22.50),
    ],
    # 15. VALENCIA — Art. 2 Ley 13/1997
    "Valencia": [
        (1, 12000, 0, 12000, 9.00),
        (2, 22000, 1080, 10000, 12.00),
        (3, 32000, 2280, 10000, 15.00),
        (4, 42000, 3780, 10000, 17.50),
        (5, 52000, 5530, 10000, 20.00),
        (6, 62000, 7530, 10000, 22.50),
        (7, 72000, 9780, 10000, 25.00),
        (8, 100000, 12280, 28000, 26.50),
        (9, 150000, 19700, 50000, 27.50),
        (10, 200000, 33450, 50000, 28.50),
        (11, 999999, 47700, 999999, 29.50),
    ],
}


async def main():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    if not turso_url or not turso_token:
        print("Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN")
        return

    db = TursoClient(turso_url, turso_token)
    await db.connect()
    print("Connected to Turso\n")

    for year in [2024, 2025]:
        print(f"{'='*60}")
        print(f"SEEDING CCAA AUTONOMOUS SCALES — YEAR {year}")
        print(f"{'='*60}")

        # Delete existing CCAA general scales (but NOT Estatal or foral)
        ccaa_names = list(SCALES.keys())
        for ccaa in ccaa_names:
            await db.execute(
                "DELETE FROM irpf_scales WHERE jurisdiction = ? AND year = ? AND scale_type = 'general'",
                [ccaa, year],
            )

        total = 0
        for ccaa, tramos in SCALES.items():
            for tramo_num, base_hasta, cuota_integra, resto_base, tipo in tramos:
                await db.execute(
                    "INSERT INTO irpf_scales (id, jurisdiction, year, scale_type, tramo_num, "
                    "base_hasta, cuota_integra, resto_base, tipo_aplicable) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [str(uuid.uuid4()), ccaa, year, "general", tramo_num,
                     base_hasta, cuota_integra, resto_base, tipo],
                )
                total += 1
            print(f"  {ccaa:25s}: {len(tramos)} tramos ({tramos[0][4]}% - {tramos[-1][4]}%)")

        print(f"\n  Total: {total} filas insertadas para {year}")

    # Verification
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")

    result = await db.execute(
        "SELECT jurisdiction, year, COUNT(*) as cnt, MIN(tipo_aplicable) as min_rate, MAX(tipo_aplicable) as max_rate "
        "FROM irpf_scales WHERE scale_type = 'general' AND year = 2025 "
        "GROUP BY jurisdiction, year ORDER BY jurisdiction"
    )
    for row in result.rows:
        print(f"  {row['jurisdiction']:25s}: {row['cnt']:>2d} tramos  ({row['min_rate']:.1f}% - {row['max_rate']:.1f}%)")

    # Quick sanity: Aragon base ~26540 should give ~3200 autonomous
    print("\nSanity check: Aragon base=26540 (Fernando's case)")
    # Tramo 1: 13072.50 × 9.5% = 1241.89
    # Tramo 2: 8137.50 × 12% = 976.50 → acum 2218.39
    # Tramo 3: 26540-21210 = 5330 × 15% = 799.50 → acum 3017.89
    print(f"  Expected autonomous cuota: ~3,018 EUR")

    await db.disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
