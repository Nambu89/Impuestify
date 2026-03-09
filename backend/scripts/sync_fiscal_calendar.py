"""
Sync Fiscal Calendar from AEAT iCal

Downloads and parses AEAT iCalendar files for the current or specified year.
Maps VEVENT records to fiscal_deadlines rows with deterministic IDs.

Usage:
    python -m backend.scripts.sync_fiscal_calendar [--year 2026] [--dry-run]
"""
import sys
import os
import re
import uuid
import asyncio
import argparse
import logging
from datetime import date, datetime
from typing import Optional

# Resolve paths so imports work when run as script
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))
sys.path.insert(0, BACKEND_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import httpx
try:
    from icalendar import Calendar
    ICALENDAR_AVAILABLE = True
except ImportError:
    ICALENDAR_AVAILABLE = False

from app.database.turso_client import TursoClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# -----------------------------------------------------------------
# AEAT iCal URLs
# Base URL pattern for AEAT calendar files
# -----------------------------------------------------------------
AEAT_ICAL_URLS = [
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Calendario/calendariofiscal{year}.ics",
    "https://sede.agenciatributaria.gob.es/static_files/Sede/Calendario/CalendarioFiscal{year}.ics",
]

# -----------------------------------------------------------------
# Model mapping: regex patterns -> (model_code, model_name, applies_to)
# -----------------------------------------------------------------
MODEL_PATTERNS = [
    # IRPF pagos fraccionados (MUST be before generic IRPF to avoid false match on \birpf\b)
    (r"modelo\s*130\b|pago.*fraccionado.*irpf|irpf.*pago.*fraccionado", "130", "IRPF pagos fraccionados", "autonomos"),
    (r"modelo\s*131\b", "131", "IRPF estimacion objetiva", "autonomos"),
    # IRPF / Renta (generic — after specific IRPF models)
    (r"\brenta\b|modelo\s*100\b|campa[nñ]a.*irpf|irpf.*anual|declaracion.*irpf", "100", "IRPF Renta anual", "todos"),
    # IVA
    (r"modelo\s*303\b|iva.*trimest|trimest.*iva", "303", "IVA trimestral", "autonomos"),
    (r"modelo\s*390\b|iva.*anual|resumen.*iva", "390", "IVA resumen anual", "autonomos"),
    (r"modelo\s*349\b|declaracion.*recapitulativa|operaciones.*intracom", "349", "IVA operaciones intracomunitarias", "autonomos"),
    # Retenciones
    (r"modelo\s*111\b|retenciones.*trabajo|trabajo.*retenciones", "111", "Retenciones rendimientos trabajo", "autonomos"),
    (r"modelo\s*115\b|retenciones.*arrendamiento|arrendamiento.*retenciones", "115", "Retenciones arrendamientos", "autonomos"),
    (r"modelo\s*123\b", "123", "Retenciones capital mobiliario", "autonomos"),
    # Declaraciones informativas
    (r"modelo\s*347\b|operaciones.*terceros|terceros.*operaciones", "347", "Operaciones con terceros", "autonomos"),
    (r"modelo\s*180\b", "180", "Resumen anual retenciones arrendamientos", "autonomos"),
    (r"modelo\s*190\b", "190", "Resumen anual retenciones trabajo", "autonomos"),
    (r"modelo\s*200\b|impuesto.*sociedades", "200", "Impuesto sobre Sociedades", "autonomos"),
    # Patrimonio
    (r"modelo\s*714\b|impuesto.*patrimonio", "714", "Impuesto Patrimonio", "particulares"),
    # Sucesiones (informativo)
    (r"modelo\s*720\b|bienes.*extranjero", "720", "Bienes en el extranjero", "todos"),
]

# Period patterns
PERIOD_PATTERNS = [
    (r"\b1[eE][rR]?\s*trimest|\b1[tT]\b|primer.*trimest|enero.*marzo|ene.*mar", "1T"),
    (r"\b2[oO]\s*trimest|\b2[tT]\b|segundo.*trimest|abril.*junio|abr.*jun", "2T"),
    (r"\b3[eE][rR]?\s*trimest|\b3[tT]\b|tercer.*trimest|julio.*septiembre|jul.*sep", "3T"),
    (r"\b4[oO]\s*trimest|\b4[tT]\b|cuarto.*trimest|octubre.*diciembre|oct.*dic", "4T"),
    (r"\banual\b|resumen.*anual|declaracion.*anual", "anual"),
]


def _infer_model(summary: str, description: str) -> tuple[str, str, str]:
    """Infer model code, name, and applies_to from event summary/description."""
    text = f"{summary} {description}".lower()
    for pattern, code, name, applies_to in MODEL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return code, name, applies_to
    # Generic fallback
    return "misc", summary[:80], "todos"


def _infer_period(summary: str, description: str) -> str:
    """Infer fiscal period from event text."""
    text = f"{summary} {description}".lower()
    for pattern, period in PERIOD_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return period
    return "anual"


def _make_id(model: str, territory: str, period: str, tax_year: int) -> str:
    """Build deterministic ID: {model}_{territory}_{period}_{tax_year}."""
    territory_slug = re.sub(r"[^a-z0-9]", "_", territory.lower()).strip("_")
    period_slug = period.lower().replace(" ", "_")
    model_slug = model.lower().replace(" ", "_")
    return f"{model_slug}_{territory_slug}_{period_slug}_{tax_year}"


def _date_to_str(dt) -> Optional[str]:
    """Convert icalendar date/datetime to ISO string."""
    if dt is None:
        return None
    if hasattr(dt, "dt"):
        dt = dt.dt
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    if isinstance(dt, date):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def parse_ical_content(ical_bytes: bytes, tax_year: int, dry_run: bool = False) -> list[dict]:
    """
    Parse iCal bytes and return list of fiscal_deadline dicts.

    Args:
        ical_bytes: Raw .ics file content
        tax_year: The fiscal year being processed
        dry_run: If True, just parse without writing

    Returns:
        List of deadline dicts ready for upsert
    """
    if not ICALENDAR_AVAILABLE:
        raise ImportError("icalendar package is required. Run: pip install icalendar")

    cal = Calendar.from_ical(ical_bytes)
    deadlines = []
    seen_ids: set[str] = set()

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("SUMMARY", "")).strip()
        description = str(component.get("DESCRIPTION", "")).strip()
        url = str(component.get("URL", "")).strip()

        if not summary:
            continue

        dtstart = _date_to_str(component.get("DTSTART"))
        dtend = _date_to_str(component.get("DTEND"))

        if not dtstart or not dtend:
            logger.warning(f"Skipping event without dates: {summary}")
            continue

        model, model_name, applies_to = _infer_model(summary, description)
        period = _infer_period(summary, description)
        territory = "Estatal"

        deadline_id = _make_id(model, territory, period, tax_year)

        # Deduplicate within this batch (multiple events can map to same ID)
        if deadline_id in seen_ids:
            # Suffix with a short hash to avoid collision
            suffix = uuid.uuid4().hex[:4]
            deadline_id = f"{deadline_id}_{suffix}"
        seen_ids.add(deadline_id)

        deadline = {
            "id": deadline_id,
            "model": model,
            "model_name": model_name,
            "territory": territory,
            "period": period,
            "tax_year": tax_year,
            "start_date": dtstart,
            "end_date": dtend,
            "domiciliation_date": None,
            "applies_to": applies_to,
            "description": description[:500] if description else None,
            "source_url": url or None,
            "is_active": 1,
        }
        deadlines.append(deadline)

        if dry_run:
            logger.info(f"[DRY-RUN] Would upsert: {deadline_id} | {model_name} | {period} | {dtend}")

    return deadlines


async def download_ical(year: int) -> Optional[bytes]:
    """Download iCal file from AEAT, trying known URL patterns."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for url_template in AEAT_ICAL_URLS:
            url = url_template.format(year=year)
            try:
                logger.info(f"Trying: {url}")
                response = await client.get(url)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text" in content_type or "calendar" in content_type or len(response.content) > 500:
                        logger.info(f"Downloaded {len(response.content)} bytes from {url}")
                        return response.content
                    logger.warning(f"Unexpected content-type {content_type} from {url}")
                else:
                    logger.warning(f"HTTP {response.status_code} from {url}")
            except Exception as e:
                logger.warning(f"Failed to download {url}: {e}")
    return None


async def upsert_deadlines(db: TursoClient, deadlines: list[dict]) -> int:
    """Upsert deadlines into fiscal_deadlines table. Returns count of upserted rows."""
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
    """Main entry point for the sync script."""
    logger.info(f"Syncing AEAT fiscal calendar for year {year} (dry_run={dry_run})")

    if not ICALENDAR_AVAILABLE:
        logger.error("icalendar package not installed. Run: pip install icalendar>=6.0.0")
        sys.exit(1)

    ical_bytes = await download_ical(year)

    if ical_bytes is None:
        logger.error("Could not download iCal from AEAT. Check network or URL pattern.")
        sys.exit(1)

    deadlines = parse_ical_content(ical_bytes, year, dry_run=dry_run)
    logger.info(f"Parsed {len(deadlines)} fiscal deadlines from iCal")

    if dry_run:
        logger.info("[DRY-RUN] Skipping database writes")
        return

    db = TursoClient()
    try:
        await db.connect()
        count = await upsert_deadlines(db, deadlines)
        logger.info(f"Upserted {count} deadlines into fiscal_deadlines")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync AEAT fiscal calendar")
    parser.add_argument("--year", type=int, default=datetime.now().year, help="Tax year to sync")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, no DB writes")
    args = parser.parse_args()

    asyncio.run(main(args.year, args.dry_run))
