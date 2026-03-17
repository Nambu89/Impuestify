"""
Seed Estatal Fiscal Deadlines

Hardcoded AEAT fiscal deadlines for the Spanish common territory (Estatal).
This is the authoritative fallback when the AEAT iCal sync is unavailable or
returns incomplete data.

Covers all standard models for a given fiscal year:
- Modelo 303 (IVA trimestral): 4T prev year + 1T/2T/3T current year
- Modelo 130 (IRPF pagos fraccionados, estimacion directa): 4T + 1T/2T/3T
- Modelo 131 (IRPF pagos fraccionados, estimacion objetiva): 4T + 1T/2T/3T
- Modelo 111 (Retenciones trabajo/actividades): 4T + 1T/2T/3T
- Modelo 115 (Retenciones arrendamientos): 4T + 1T/2T/3T
- Modelo 180 (Resumen anual retenciones arrendamientos): enero, anual
- Modelo 190 (Resumen anual retenciones trabajo): enero, anual
- Modelo 390 (Resumen anual IVA): enero, anual
- Modelo 347 (Operaciones con terceros): febrero, anual
- Modelo 720 (Bienes en el extranjero): marzo, anual
- Modelo 100 (Campaña Renta): abril-junio, anual
- Modelo 200 (Impuesto Sociedades): julio, anual
- Modelo 100 (Segundo plazo Renta): noviembre

Note on 4T deadlines: The 4T period from the previous fiscal year has its
submission deadline in January of the current calendar year. These are seeded
as period="4T" under the current year (the year in which the obligation is due),
not the previous year.

Usage:
    python -m backend.scripts.seed_estatal_deadlines [--year 2026] [--dry-run]

Run once per year (January) to populate estatal deadlines for the new year.
Idempotent via INSERT ... ON CONFLICT(id) DO UPDATE.

Source: https://sede.agenciatributaria.gob.es/Sede/calendario-contribuyente.html
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

SOURCE_URL = "https://sede.agenciatributaria.gob.es/Sede/calendario-contribuyente.html"
TERRITORY = "Estatal"


def _make_id(model: str, territory: str, period: str, tax_year: int) -> str:
    """Build deterministic ID matching the pattern used in sync_fiscal_calendar."""
    import re
    territory_slug = re.sub(r"[^a-z0-9]", "_", territory.lower()).strip("_")
    period_slug = period.lower().replace(" ", "_")
    model_slug = model.lower().replace(" ", "_")
    return f"{model_slug}_{territory_slug}_{period_slug}_{tax_year}"


def build_estatal_deadlines(tax_year: int = 2026) -> list[dict]:
    """
    Return hardcoded AEAT estatal fiscal deadlines for the given year.

    Source: https://sede.agenciatributaria.gob.es/Sede/calendario-contribuyente.html

    The 4T deadlines (303, 130, 131, 111, 115) fall in January of `tax_year`
    because they correspond to the 4th quarter of the previous fiscal year but
    their legal due date is in the current calendar year.

    Run seed_estatal_deadlines.py each January to update for the new year.
    """
    y = tax_year

    deadlines = [

        # =============================================
        # ENERO — 4T del ejercicio anterior
        # Deadline falls in January of `y`; period labelled "4T"
        # =============================================

        # Modelo 303 IVA — 4T
        {
            "id": _make_id("303", TERRITORY, "4T", y),
            "model": "303",
            "model_name": "IVA trimestral Modelo 303 — 4T",
            "territory": TERRITORY,
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                "Autoliquidacion trimestral del IVA correspondiente al 4T "
                f"del ejercicio {y - 1}. Plazo: 1-20 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 130 IRPF pagos fraccionados (estimacion directa) — 4T
        {
            "id": _make_id("130", TERRITORY, "4T", y),
            "model": "130",
            "model_name": "IRPF pagos fraccionados Modelo 130 — 4T",
            "territory": TERRITORY,
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                "Pago fraccionado IRPF (estimacion directa) correspondiente al 4T "
                f"del ejercicio {y - 1}. Plazo: 1-20 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 131 IRPF pagos fraccionados (estimacion objetiva) — 4T
        {
            "id": _make_id("131", TERRITORY, "4T", y),
            "model": "131",
            "model_name": "IRPF pagos fraccionados Modelo 131 — 4T",
            "territory": TERRITORY,
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                "Pago fraccionado IRPF (estimacion objetiva/modulos) correspondiente al 4T "
                f"del ejercicio {y - 1}. Plazo: 1-20 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 111 Retenciones trabajo — 4T
        {
            "id": _make_id("111", TERRITORY, "4T", y),
            "model": "111",
            "model_name": "Retenciones trabajo Modelo 111 — 4T",
            "territory": TERRITORY,
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                "Retenciones e ingresos a cuenta sobre rendimientos del trabajo y "
                "actividades economicas correspondientes al 4T "
                f"del ejercicio {y - 1}. Plazo: 1-20 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 115 Retenciones arrendamientos — 4T
        {
            "id": _make_id("115", TERRITORY, "4T", y),
            "model": "115",
            "model_name": "Retenciones arrendamientos Modelo 115 — 4T",
            "territory": TERRITORY,
            "period": "4T",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                "Retenciones e ingresos a cuenta sobre rendimientos procedentes del "
                "arrendamiento de inmuebles urbanos correspondientes al 4T "
                f"del ejercicio {y - 1}. Plazo: 1-20 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 180 Resumen anual retenciones arrendamientos — anual
        {
            "id": _make_id("180", TERRITORY, "anual", y),
            "model": "180",
            "model_name": "Resumen anual retenciones arrendamientos Modelo 180",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Resumen anual de retenciones sobre arrendamientos del ejercicio {y - 1}. "
                "Plazo: 1-20 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 390 Resumen anual IVA — anual
        {
            "id": _make_id("390", TERRITORY, "anual", y),
            "model": "390",
            "model_name": "Resumen anual IVA Modelo 390",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-30",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Declaracion-resumen anual del IVA del ejercicio {y - 1}. "
                "Plazo: 1-30 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 190 Resumen anual retenciones trabajo — anual
        {
            "id": _make_id("190", TERRITORY, "anual", y),
            "model": "190",
            "model_name": "Resumen anual retenciones trabajo Modelo 190",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-01-31",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                "Resumen anual de retenciones sobre rendimientos del trabajo, "
                f"actividades economicas y premios del ejercicio {y - 1}. "
                "Plazo: 1-31 de enero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # =============================================
        # FEBRERO — Resumen operaciones con terceros
        # =============================================

        # Modelo 347 Operaciones con terceros — anual
        {
            "id": _make_id("347", TERRITORY, "anual", y),
            "model": "347",
            "model_name": "Operaciones con terceros Modelo 347",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-02-01",
            # 28 feb (2026 is not a leap year; adjust manually for leap years if needed)
            "end_date": f"{y}-02-28",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                "Declaracion anual de operaciones con terceras personas superiores a "
                f"3.005,06 EUR del ejercicio {y - 1}. Plazo: hasta el 28 de febrero."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # =============================================
        # MARZO — Bienes en el extranjero
        # =============================================

        # Modelo 720 Bienes en el extranjero — anual
        {
            "id": _make_id("720", TERRITORY, "anual", y),
            "model": "720",
            "model_name": "Bienes en el extranjero Modelo 720",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-03-01",
            "end_date": f"{y}-03-31",
            "domiciliation_date": None,
            "applies_to": "todos",
            "description": (
                "Declaracion informativa sobre bienes y derechos situados en el "
                f"extranjero del ejercicio {y - 1}. Plazo: 1-31 de marzo."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # =============================================
        # ABRIL — 1T + Inicio Campana Renta
        # =============================================

        # Modelo 303 IVA — 1T
        {
            "id": _make_id("303", TERRITORY, "1T", y),
            "model": "303",
            "model_name": "IVA trimestral Modelo 303 — 1T",
            "territory": TERRITORY,
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Autoliquidacion trimestral del IVA correspondiente al 1T {y}. "
                "Plazo: 1-20 de abril."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 130 IRPF pagos fraccionados — 1T
        {
            "id": _make_id("130", TERRITORY, "1T", y),
            "model": "130",
            "model_name": "IRPF pagos fraccionados Modelo 130 — 1T",
            "territory": TERRITORY,
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Pago fraccionado IRPF (estimacion directa) 1T {y}. "
                "Plazo: 1-20 de abril."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 131 IRPF pagos fraccionados (objetiva) — 1T
        {
            "id": _make_id("131", TERRITORY, "1T", y),
            "model": "131",
            "model_name": "IRPF pagos fraccionados Modelo 131 — 1T",
            "territory": TERRITORY,
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Pago fraccionado IRPF (estimacion objetiva/modulos) 1T {y}. "
                "Plazo: 1-20 de abril."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 111 Retenciones trabajo — 1T
        {
            "id": _make_id("111", TERRITORY, "1T", y),
            "model": "111",
            "model_name": "Retenciones trabajo Modelo 111 — 1T",
            "territory": TERRITORY,
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Retenciones sobre rendimientos del trabajo y actividades economicas 1T {y}. "
                "Plazo: 1-20 de abril."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 115 Retenciones arrendamientos — 1T
        {
            "id": _make_id("115", TERRITORY, "1T", y),
            "model": "115",
            "model_name": "Retenciones arrendamientos Modelo 115 — 1T",
            "territory": TERRITORY,
            "period": "1T",
            "tax_year": y,
            "start_date": f"{y}-04-01",
            "end_date": f"{y}-04-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Retenciones sobre arrendamientos de inmuebles urbanos 1T {y}. "
                "Plazo: 1-20 de abril."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 100 Campana Renta — anual (online desde 8 abril, fin 30 junio)
        {
            "id": _make_id("100", TERRITORY, "anual", y),
            "model": "100",
            "model_name": f"Campana de la Renta {y - 1} — Modelo 100",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-04-08",
            "end_date": f"{y}-06-30",
            "domiciliation_date": f"{y}-06-25",
            "applies_to": "todos",
            "description": (
                f"Campana de la Renta {y - 1}. Presentacion online desde el 8 de abril. "
                "Atencion telefonica desde el 9 de mayo (cita previa desde el 9 de abril). "
                "Presentacion presencial desde el 1 de junio (cita previa desde el 29 de mayo). "
                "Domiciliacion bancaria: hasta el 25 de junio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # =============================================
        # JULIO — 2T + Impuesto Sociedades
        # =============================================

        # Modelo 303 IVA — 2T
        {
            "id": _make_id("303", TERRITORY, "2T", y),
            "model": "303",
            "model_name": "IVA trimestral Modelo 303 — 2T",
            "territory": TERRITORY,
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Autoliquidacion trimestral del IVA correspondiente al 2T {y}. "
                "Plazo: 1-20 de julio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 130 IRPF pagos fraccionados — 2T
        {
            "id": _make_id("130", TERRITORY, "2T", y),
            "model": "130",
            "model_name": "IRPF pagos fraccionados Modelo 130 — 2T",
            "territory": TERRITORY,
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Pago fraccionado IRPF (estimacion directa) 2T {y}. "
                "Plazo: 1-20 de julio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 131 IRPF pagos fraccionados (objetiva) — 2T
        {
            "id": _make_id("131", TERRITORY, "2T", y),
            "model": "131",
            "model_name": "IRPF pagos fraccionados Modelo 131 — 2T",
            "territory": TERRITORY,
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Pago fraccionado IRPF (estimacion objetiva/modulos) 2T {y}. "
                "Plazo: 1-20 de julio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 111 Retenciones trabajo — 2T
        {
            "id": _make_id("111", TERRITORY, "2T", y),
            "model": "111",
            "model_name": "Retenciones trabajo Modelo 111 — 2T",
            "territory": TERRITORY,
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Retenciones sobre rendimientos del trabajo y actividades economicas 2T {y}. "
                "Plazo: 1-20 de julio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 115 Retenciones arrendamientos — 2T
        {
            "id": _make_id("115", TERRITORY, "2T", y),
            "model": "115",
            "model_name": "Retenciones arrendamientos Modelo 115 — 2T",
            "territory": TERRITORY,
            "period": "2T",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Retenciones sobre arrendamientos de inmuebles urbanos 2T {y}. "
                "Plazo: 1-20 de julio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 200 Impuesto Sociedades — anual
        {
            "id": _make_id("200", TERRITORY, "anual", y),
            "model": "200",
            "model_name": "Impuesto sobre Sociedades Modelo 200",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-07-01",
            "end_date": f"{y}-07-25",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Declaracion anual del Impuesto sobre Sociedades del ejercicio {y - 1}. "
                "Plazo: 1-25 de julio (para ejercicios cerrados a 31 de diciembre)."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # =============================================
        # OCTUBRE — 3T
        # =============================================

        # Modelo 303 IVA — 3T
        {
            "id": _make_id("303", TERRITORY, "3T", y),
            "model": "303",
            "model_name": "IVA trimestral Modelo 303 — 3T",
            "territory": TERRITORY,
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Autoliquidacion trimestral del IVA correspondiente al 3T {y}. "
                "Plazo: 1-20 de octubre."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 130 IRPF pagos fraccionados — 3T
        {
            "id": _make_id("130", TERRITORY, "3T", y),
            "model": "130",
            "model_name": "IRPF pagos fraccionados Modelo 130 — 3T",
            "territory": TERRITORY,
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Pago fraccionado IRPF (estimacion directa) 3T {y}. "
                "Plazo: 1-20 de octubre."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 131 IRPF pagos fraccionados (objetiva) — 3T
        {
            "id": _make_id("131", TERRITORY, "3T", y),
            "model": "131",
            "model_name": "IRPF pagos fraccionados Modelo 131 — 3T",
            "territory": TERRITORY,
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Pago fraccionado IRPF (estimacion objetiva/modulos) 3T {y}. "
                "Plazo: 1-20 de octubre."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 111 Retenciones trabajo — 3T
        {
            "id": _make_id("111", TERRITORY, "3T", y),
            "model": "111",
            "model_name": "Retenciones trabajo Modelo 111 — 3T",
            "territory": TERRITORY,
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Retenciones sobre rendimientos del trabajo y actividades economicas 3T {y}. "
                "Plazo: 1-20 de octubre."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 115 Retenciones arrendamientos — 3T
        {
            "id": _make_id("115", TERRITORY, "3T", y),
            "model": "115",
            "model_name": "Retenciones arrendamientos Modelo 115 — 3T",
            "territory": TERRITORY,
            "period": "3T",
            "tax_year": y,
            "start_date": f"{y}-10-01",
            "end_date": f"{y}-10-20",
            "domiciliation_date": None,
            "applies_to": "autonomos",
            "description": (
                f"Retenciones sobre arrendamientos de inmuebles urbanos 3T {y}. "
                "Plazo: 1-20 de octubre."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # =============================================
        # NOVIEMBRE — Segundo plazo Renta
        # =============================================

        # Modelo 100 Segundo plazo — fraccionamiento
        {
            "id": _make_id("100", TERRITORY, "segundo_plazo", y),
            "model": "100",
            "model_name": f"Segundo plazo IRPF Renta {y - 1}",
            "territory": TERRITORY,
            "period": "segundo_plazo",
            "tax_year": y,
            "start_date": f"{y}-11-01",
            "end_date": f"{y}-11-05",
            "domiciliation_date": None,
            "applies_to": "todos",
            "description": (
                f"Segundo plazo de pago fraccionado de la declaracion de la Renta {y - 1} "
                "(40% restante si se eligio fraccionamiento en la presentacion). "
                "Plazo: 1-5 de noviembre."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # =============================================
        # INFORMATIVOS PARTICULARES — applies_to = "todos"
        # Plazos reales que afectan a cualquier contribuyente
        # (no solo autonomos), incluyendo asalariados y pensionistas.
        # =============================================

        # Modelo 721 — Monedas virtuales en el extranjero (anual, enero-marzo)
        {
            "id": _make_id("721", TERRITORY, "anual", y),
            "model": "721",
            "model_name": "Monedas virtuales en el extranjero Modelo 721",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-01-01",
            "end_date": f"{y}-03-31",
            "domiciliation_date": None,
            "applies_to": "todos",
            "description": (
                "Declaracion informativa sobre monedas virtuales situadas en el extranjero "
                f"del ejercicio {y - 1}. Obligatorio si el valor total supera los 50.000 EUR "
                "a 31 de diciembre. Plazo: 1 de enero - 31 de marzo."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 714 — Impuesto sobre el Patrimonio (campana Renta, abril-junio)
        {
            "id": _make_id("714", TERRITORY, "anual", y),
            "model": "714",
            "model_name": f"Impuesto sobre el Patrimonio {y - 1} — Modelo 714",
            "territory": TERRITORY,
            "period": "anual",
            "tax_year": y,
            "start_date": f"{y}-04-08",
            "end_date": f"{y}-06-30",
            "domiciliation_date": f"{y}-06-25",
            "applies_to": "todos",
            "description": (
                f"Declaracion del Impuesto sobre el Patrimonio del ejercicio {y - 1}. "
                "Obligatorio si el patrimonio neto supera los 700.000 EUR "
                "(el minimo exento varia por CCAA; en algunas como Madrid la bonificacion es del 100%). "
                "Se presenta junto con la Campana de la Renta: 8 de abril - 30 de junio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 100 — Cita previa atencion telefonica (referencia informativa)
        {
            "id": _make_id("100", TERRITORY, "cita_telefonica", y),
            "model": "100",
            "model_name": "Cita previa atencion telefonica Renta",
            "territory": TERRITORY,
            "period": "cita_telefonica",
            "tax_year": y,
            "start_date": f"{y}-05-09",
            "end_date": f"{y}-05-09",
            "domiciliation_date": None,
            "applies_to": "todos",
            "description": (
                f"Desde el 9 de mayo se puede solicitar cita previa para la confeccion telefonica "
                f"de la declaracion de la Renta {y - 1}. La atencion telefonica comienza el mismo dia."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },

        # Modelo 100 — Atencion presencial en oficinas AEAT (referencia informativa)
        {
            "id": _make_id("100", TERRITORY, "atencion_presencial", y),
            "model": "100",
            "model_name": "Atencion presencial en oficinas AEAT",
            "territory": TERRITORY,
            "period": "atencion_presencial",
            "tax_year": y,
            "start_date": f"{y}-06-01",
            "end_date": f"{y}-06-30",
            "domiciliation_date": None,
            "applies_to": "todos",
            "description": (
                f"Desde el 1 de junio: atencion presencial en oficinas de la AEAT para confeccion "
                f"de la declaracion de la Renta {y - 1} (cita previa desde el 29 de mayo). "
                "Plazo limite de presentacion: 30 de junio."
            ),
            "source_url": SOURCE_URL,
            "is_active": 1,
        },
    ]

    return deadlines


async def upsert_deadlines(db: TursoClient, deadlines: list[dict]) -> int:
    """Upsert estatal deadlines. Returns count of upserted rows."""
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
    """Main entry point for the estatal seed script."""
    deadlines = build_estatal_deadlines(tax_year=year)
    logger.info(f"Prepared {len(deadlines)} estatal deadlines for year {year}")

    if dry_run:
        for d in deadlines:
            logger.info(
                f"[DRY-RUN] {d['id']} | {d['model_name']} | {d['period']} | "
                f"{d['start_date']} -> {d['end_date']}"
            )
        logger.info("[DRY-RUN] No database writes performed")
        return

    db = TursoClient()
    try:
        await db.connect()
        count = await upsert_deadlines(db, deadlines)
        logger.info(f"Upserted {count} estatal deadlines into fiscal_deadlines")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed AEAT estatal fiscal deadlines")
    parser.add_argument("--year", type=int, default=2026, help="Tax year to seed (default: 2026)")
    parser.add_argument("--dry-run", action="store_true", help="Print deadlines without writing to DB")
    args = parser.parse_args()

    asyncio.run(main(args.year, args.dry_run))
