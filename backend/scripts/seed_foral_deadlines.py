"""
Seed Foral Fiscal Deadlines 2026

Hardcoded fiscal deadlines for the four foral territories:
- Gipuzkoa (Hacienda Foral de Gipuzkoa)
- Bizkaia (Hacienda Foral de Bizkaia)
- Araba (Hacienda Foral de Araba)
- Navarra (Hacienda Foral de Navarra)

Run once per year (January) to populate foral deadlines for the new year.
Idempotent via INSERT ... ON CONFLICT(id) DO UPDATE.

Usage:
    python -m backend.scripts.seed_foral_deadlines [--year 2026] [--dry-run]
"""
import sys
import os
import asyncio
import argparse
import logging
from datetime import datetime

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))
sys.path.insert(0, BACKEND_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.database.turso_client import TursoClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _make_id(model: str, territory: str, period: str, tax_year: int) -> str:
    """Build deterministic ID matching the pattern used in sync_fiscal_calendar."""
    import re
    territory_slug = re.sub(r"[^a-z0-9]", "_", territory.lower()).strip("_")
    period_slug = period.lower().replace(" ", "_")
    model_slug = model.lower().replace(" ", "_")
    return f"{model_slug}_{territory_slug}_{period_slug}_{tax_year}"


def build_foral_deadlines_2026(tax_year: int = 2026) -> list[dict]:
    """
    Return hardcoded foral fiscal deadlines for the given year.

    Sources:
    - Gipuzkoa: https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal
    - Bizkaia: https://www.bizkaia.eus/eu/home/ogasun/fiskalitate/tributu-egutegi
    - Araba: https://www.araba.eus/es/web/ogasuna/calendario-fiscal
    - Navarra: https://hacienda.navarra.es/es/calendario-fiscal

    Dates follow the foral haciendas calendar for 2026.
    Run seed_foral_deadlines.py each January to update for the new year.
    """
    y = tax_year

    deadlines = [
        # =============================================
        # GIPUZKOA
        # =============================================
        # Modelo 100 (IRPF) - anual
        {
            "id": _make_id("100", "Gipuzkoa", "anual", y),
            "model": "100",
            "model_name": "IRPF Renta (Gipuzkoa)",
            "territory": "Gipuzkoa",
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-04-06",
            "end_date": f"{y}-06-30",
            "domiciliation_date": f"{y}-06-25",
            "applies_to": "todos",
            "description": "Declaracion anual IRPF Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 300 (IVA - equivalente al 303 estatal) - 1T
        {
            "id": _make_id("300", "Gipuzkoa", "1T", y),
            "model": "300",
            "model_name": "IVA trimestral (Gipuzkoa Modelo 300)",
            "territory": "Gipuzkoa",
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 1T Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 300 - 2T
        {
            "id": _make_id("300", "Gipuzkoa", "2T", y),
            "model": "300",
            "model_name": "IVA trimestral (Gipuzkoa Modelo 300)",
            "territory": "Gipuzkoa",
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 2T Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 300 - 3T
        {
            "id": _make_id("300", "Gipuzkoa", "3T", y),
            "model": "300",
            "model_name": "IVA trimestral (Gipuzkoa Modelo 300)",
            "territory": "Gipuzkoa",
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 3T Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 300 - 4T (anual IVA)
        {
            "id": _make_id("300", "Gipuzkoa", "4T", y),
            "model": "300",
            "model_name": "IVA trimestral (Gipuzkoa Modelo 300)",
            "territory": "Gipuzkoa",
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-12-26",
            "end_date": f"{y + 1}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 4T Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 109 (pagos fraccionados IRPF) - 1T
        {
            "id": _make_id("109", "Gipuzkoa", "1T", y),
            "model": "109",
            "model_name": "IRPF pagos fraccionados (Gipuzkoa Modelo 109)",
            "territory": "Gipuzkoa",
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Pago fraccionado IRPF 1T Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 109 - 2T
        {
            "id": _make_id("109", "Gipuzkoa", "2T", y),
            "model": "109",
            "model_name": "IRPF pagos fraccionados (Gipuzkoa Modelo 109)",
            "territory": "Gipuzkoa",
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Pago fraccionado IRPF 2T Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 109 - 3T
        {
            "id": _make_id("109", "Gipuzkoa", "3T", y),
            "model": "109",
            "model_name": "IRPF pagos fraccionados (Gipuzkoa Modelo 109)",
            "territory": "Gipuzkoa",
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Pago fraccionado IRPF 3T Hacienda Foral de Gipuzkoa",
            "source_url": "https://www.gipuzkoa.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },

        # =============================================
        # BIZKAIA
        # =============================================
        # Modelo 100 (IRPF) - anual
        {
            "id": _make_id("100", "Bizkaia", "anual", y),
            "model": "100",
            "model_name": "IRPF Renta (Bizkaia)",
            "territory": "Bizkaia",
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-04-06",
            "end_date": f"{y}-06-30",
            "domiciliation_date": f"{y}-06-25",
            "applies_to": "todos",
            "description": "Declaracion anual IRPF Hacienda Foral de Bizkaia",
            "source_url": "https://www.bizkaia.eus/eu/home/ogasun/fiskalitate/tributu-egutegi",
            "is_active": 1,
        },
        # Modelo 303 IVA Bizkaia - 1T
        {
            "id": _make_id("303", "Bizkaia", "1T", y),
            "model": "303",
            "model_name": "IVA trimestral (Bizkaia Modelo 303)",
            "territory": "Bizkaia",
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 1T Hacienda Foral de Bizkaia",
            "source_url": "https://www.bizkaia.eus/eu/home/ogasun/fiskalitate/tributu-egutegi",
            "is_active": 1,
        },
        # Modelo 303 IVA Bizkaia - 2T
        {
            "id": _make_id("303", "Bizkaia", "2T", y),
            "model": "303",
            "model_name": "IVA trimestral (Bizkaia Modelo 303)",
            "territory": "Bizkaia",
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 2T Hacienda Foral de Bizkaia",
            "source_url": "https://www.bizkaia.eus/eu/home/ogasun/fiskalitate/tributu-egutegi",
            "is_active": 1,
        },
        # Modelo 303 IVA Bizkaia - 3T
        {
            "id": _make_id("303", "Bizkaia", "3T", y),
            "model": "303",
            "model_name": "IVA trimestral (Bizkaia Modelo 303)",
            "territory": "Bizkaia",
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 3T Hacienda Foral de Bizkaia",
            "source_url": "https://www.bizkaia.eus/eu/home/ogasun/fiskalitate/tributu-egutegi",
            "is_active": 1,
        },
        # Modelo 303 IVA Bizkaia - 4T
        {
            "id": _make_id("303", "Bizkaia", "4T", y),
            "model": "303",
            "model_name": "IVA trimestral (Bizkaia Modelo 303)",
            "territory": "Bizkaia",
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-12-26",
            "end_date": f"{y + 1}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 4T Hacienda Foral de Bizkaia",
            "source_url": "https://www.bizkaia.eus/eu/home/ogasun/fiskalitate/tributu-egutegi",
            "is_active": 1,
        },

        # =============================================
        # ARABA
        # =============================================
        # Modelo 100 (IRPF) - anual
        {
            "id": _make_id("100", "Araba", "anual", y),
            "model": "100",
            "model_name": "IRPF Renta (Araba)",
            "territory": "Araba",
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-04-06",
            "end_date": f"{y}-06-30",
            "domiciliation_date": f"{y}-06-25",
            "applies_to": "todos",
            "description": "Declaracion anual IRPF Hacienda Foral de Araba",
            "source_url": "https://www.araba.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 303 IVA Araba - 1T
        {
            "id": _make_id("303", "Araba", "1T", y),
            "model": "303",
            "model_name": "IVA trimestral (Araba Modelo 303)",
            "territory": "Araba",
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 1T Hacienda Foral de Araba",
            "source_url": "https://www.araba.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 303 IVA Araba - 2T
        {
            "id": _make_id("303", "Araba", "2T", y),
            "model": "303",
            "model_name": "IVA trimestral (Araba Modelo 303)",
            "territory": "Araba",
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 2T Hacienda Foral de Araba",
            "source_url": "https://www.araba.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 303 IVA Araba - 3T
        {
            "id": _make_id("303", "Araba", "3T", y),
            "model": "303",
            "model_name": "IVA trimestral (Araba Modelo 303)",
            "territory": "Araba",
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 3T Hacienda Foral de Araba",
            "source_url": "https://www.araba.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo 303 IVA Araba - 4T
        {
            "id": _make_id("303", "Araba", "4T", y),
            "model": "303",
            "model_name": "IVA trimestral (Araba Modelo 303)",
            "territory": "Araba",
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-12-26",
            "end_date": f"{y + 1}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 4T Hacienda Foral de Araba",
            "source_url": "https://www.araba.eus/es/web/ogasuna/calendario-fiscal",
            "is_active": 1,
        },

        # =============================================
        # NAVARRA
        # =============================================
        # Modelo S90 (IRPF anual Navarra)
        {
            "id": _make_id("S90", "Navarra", "anual", y),
            "model": "S90",
            "model_name": "IRPF Renta (Navarra Modelo S90)",
            "territory": "Navarra",
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-04-06",
            "end_date": f"{y}-06-30",
            "domiciliation_date": f"{y}-06-25",
            "applies_to": "todos",
            "description": "Declaracion anual IRPF Hacienda Foral de Navarra (Modelo S90)",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo F-65 (IVA trimestral Navarra - equivalente al 303) - 1T
        {
            "id": _make_id("F-65", "Navarra", "1T", y),
            "model": "F-65",
            "model_name": "IVA trimestral (Navarra Modelo F-65)",
            "territory": "Navarra",
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 1T Hacienda Foral de Navarra (Modelo F-65)",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo F-65 - 2T
        {
            "id": _make_id("F-65", "Navarra", "2T", y),
            "model": "F-65",
            "model_name": "IVA trimestral (Navarra Modelo F-65)",
            "territory": "Navarra",
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 2T Hacienda Foral de Navarra (Modelo F-65)",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo F-65 - 3T
        {
            "id": _make_id("F-65", "Navarra", "3T", y),
            "model": "F-65",
            "model_name": "IVA trimestral (Navarra Modelo F-65)",
            "territory": "Navarra",
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 3T Hacienda Foral de Navarra (Modelo F-65)",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo F-65 - 4T
        {
            "id": _make_id("F-65", "Navarra", "4T", y),
            "model": "F-65",
            "model_name": "IVA trimestral (Navarra Modelo F-65)",
            "territory": "Navarra",
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-12-26",
            "end_date": f"{y + 1}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Autoliquidacion IVA 4T Hacienda Foral de Navarra (Modelo F-65)",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo F-69 (pagos fraccionados IRPF Navarra) - 1T
        {
            "id": _make_id("F-69", "Navarra", "1T", y),
            "model": "F-69",
            "model_name": "IRPF pagos fraccionados (Navarra Modelo F-69)",
            "territory": "Navarra",
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Pago fraccionado IRPF 1T Hacienda Foral de Navarra",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo F-69 - 2T
        {
            "id": _make_id("F-69", "Navarra", "2T", y),
            "model": "F-69",
            "model_name": "IRPF pagos fraccionados (Navarra Modelo F-69)",
            "territory": "Navarra",
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Pago fraccionado IRPF 2T Hacienda Foral de Navarra",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
        # Modelo F-69 - 3T
        {
            "id": _make_id("F-69", "Navarra", "3T", y),
            "model": "F-69",
            "model_name": "IRPF pagos fraccionados (Navarra Modelo F-69)",
            "territory": "Navarra",
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": "Pago fraccionado IRPF 3T Hacienda Foral de Navarra",
            "source_url": "https://hacienda.navarra.es/es/calendario-fiscal",
            "is_active": 1,
        },
    ]
    return deadlines


async def upsert_deadlines(db: TursoClient, deadlines: list[dict]) -> int:
    """Upsert foral deadlines. Returns count of upserted rows."""
    count = 0
    for d in deadlines:
        await db.execute(
            """
            INSERT INTO fiscal_deadlines (
                id, model, model_name, territory, period, tax_year,
                start_date, end_date, domiciliation_date, applies_to,
                description, source_url, is_active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                model = excluded.model,
                model_name = excluded.model_name,
                territory = excluded.territory,
                period = excluded.period,
                tax_year = excluded.tax_year,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                domiciliation_date = excluded.domiciliation_date,
                applies_to = excluded.applies_to,
                description = excluded.description,
                source_url = excluded.source_url,
                is_active = excluded.is_active,
                updated_at = datetime('now')
            """,
            [
                d["id"], d["model"], d["model_name"], d["territory"],
                d["period"], d["tax_year"], d["start_date"], d["end_date"],
                d["domiciliation_date"], d["applies_to"], d["description"],
                d["source_url"], d["is_active"],
            ],
        )
        count += 1
    return count


async def main(year: int, dry_run: bool) -> None:
    """Main entry point for the foral seed script."""
    deadlines = build_foral_deadlines_2026(tax_year=year)
    logger.info(f"Prepared {len(deadlines)} foral deadlines for year {year}")

    if dry_run:
        for d in deadlines:
            logger.info(f"[DRY-RUN] {d['id']} | {d['model_name']} | {d['period']} | {d['end_date']}")
        logger.info("[DRY-RUN] No database writes performed")
        return

    db = TursoClient()
    try:
        await db.connect()
        count = await upsert_deadlines(db, deadlines)
        logger.info(f"Upserted {count} foral deadlines into fiscal_deadlines")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed foral fiscal deadlines")
    parser.add_argument("--year", type=int, default=2026, help="Tax year to seed (default: 2026)")
    parser.add_argument("--dry-run", action="store_true", help="Print deadlines without writing to DB")
    args = parser.parse_args()

    asyncio.run(main(args.year, args.dry_run))
