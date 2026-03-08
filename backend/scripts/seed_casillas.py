"""
Seed script for IRPF casillas (Model 100 field dictionary).

Parses two AEAT .properties files and populates the irpf_casillas table:
  - diccionarioXSD_2024.properties        (~2383 entries, standard format)
  - diccionarioDlgXSD_2024.properties     (~3712 entries, toma-de-datos extended format)

Format — diccionarioXSD_2024.properties:
    FIELD_KEY=[/XSD/Path][TYPE][*NNNN][Description text]
    FIELD_KEY=[/XSD/Path][TYPE][###][Description text]   <- no casilla num

Format — diccionarioDlgXSD_2024.properties:
    FIELD_KEY=[/XSD/Path][TYPE][*NNNN]{Section context}[Description text]
    FIELD_KEY=[/XSD/Path][TYPE][###]{Section context}[Description text]

Strategy:
  - Only entries with a real casilla number ([*NNNN]) are inserted.
  - When the same casilla appears in both files, the Dlg version wins (richer section context).
  - Section is extracted from the XSD path (e.g. "Pagina06" -> human label).
  - Idempotent: DELETE existing rows for year=2024 then re-insert.

Usage:
    cd backend
    ../venv/Scripts/python.exe scripts/seed_casillas.py
    ../venv/Scripts/python.exe scripts/seed_casillas.py --dry-run
"""
import argparse
import asyncio
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

AEAT_DIR = Path(PROJECT_ROOT) / "docs" / "aeat" / "renta-2025"
XSD_FILE = AEAT_DIR / "diccionarioXSD_2024.properties"
DLG_FILE = AEAT_DIR / "diccionarioDlgXSD_2024.properties"

# ---------------------------------------------------------------------------
# XSD-path to section mapping
# ---------------------------------------------------------------------------

_SECTION_MAP = {
    "DatosIdentificativos": "Datos identificativos",
    "DatosPersonales": "Datos personales",
    "OtraDeclaracion": "Otra declaracion",
    "DatosIngresoDevolucion": "Ingreso / devolucion",
    "DatosEconomicos": "Datos economicos",
    "TomaDatosAmpliada": "Toma de datos ampliada",
    "CalculoImpuesto": "Calculo del impuesto",
    "RendimientosDelTrabajo": "Rendimientos del trabajo",
    "RendimientosTrabajo": "Rendimientos del trabajo",
    "RendimientosCapitalInmobiliario": "Rendimientos capital inmobiliario",
    "RendimientosCapitalMobiliario": "Rendimientos capital mobiliario",
    "RendimientosActividadesEconomicas": "Rendimientos actividades economicas",
    "GananciasPatrimoniales": "Ganancias y perdidas patrimoniales",
    "PerdidaPatrimonial": "Ganancias y perdidas patrimoniales",
    "GananciaPatrimonial": "Ganancias y perdidas patrimoniales",
    "RendimientosImputados": "Rendimientos imputados",
    "BaseImponibleGeneral": "Base imponible general",
    "BaseImponibleAhorro": "Base imponible del ahorro",
    "CuotaIntegra": "Cuota integra",
    "Deducciones": "Deducciones",
    "CuotaLiquida": "Cuota liquida",
    "CuotaDiferencial": "Cuota diferencial",
    "Pagina01": "Pagina 1 — Datos personales",
    "Pagina02": "Pagina 2 — Datos personales",
    "Pagina03": "Pagina 3 — Rendimientos trabajo",
    "Pagina04": "Pagina 4 — Rendimientos trabajo (cont.)",
    "Pagina05": "Pagina 5 — Rendimientos capital mobiliario",
    "Pagina06": "Pagina 6 — Rendimientos capital inmobiliario",
    "Pagina07": "Pagina 7 — Rendimientos actividades economicas",
    "Pagina08": "Pagina 8 — Ganancias y perdidas patrimoniales",
    "Pagina09": "Pagina 9 — Ganancias y perdidas patrimoniales (cont.)",
    "Pagina10": "Pagina 10 — Rentas imputadas",
    "Pagina11": "Pagina 11 — Base imponible",
    "Pagina12": "Pagina 12 — Cuota integra",
    "Pagina13": "Pagina 13 — Deducciones",
    "Pagina14": "Pagina 14 — Cuota diferencial",
    "Pagina15": "Pagina 15 — Resultado final",
    "Pagina16": "Pagina 16 — Datos bancarios",
    "AutoliquidacionRectificativa": "Autoliquidacion rectificativa / complementaria",
    "Complementaria": "Complementaria",
    "CotizacionesTIT": "Cotizaciones Seguridad Social",
    "CotizacionesCedente": "Cotizaciones cedente",
    "Ascendientes": "Minimos por ascendientes",
    "Descendientes": "Minimos por descendientes",
    "Hijos": "Datos de hijos",
    "DAFAS": "Deducciones por familia / discapacidad",
}


def _path_to_section(xsd_path: str) -> str:
    """
    Convert an XSD path like '/DatosEconomicos/Pagina12/...' to a human section label.
    Returns the most specific matching segment found in _SECTION_MAP.
    """
    parts = [p for p in xsd_path.split("/") if p and p not in ("Declaracion",)]
    for part in reversed(parts):
        # Strip array indices like [0]
        clean = re.sub(r"\[.*\]", "", part)
        if clean in _SECTION_MAP:
            return _SECTION_MAP[clean]
    # Fallback: return the second-level path element
    return parts[0] if parts else "General"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

# Pattern for XSD dictionary:
# FIELD_KEY=[/XSD/Path][TYPE][*NNNN][Description]
# or
# FIELD_KEY=[/XSD/Path][TYPE][###][Description]
_XSD_PATTERN = re.compile(
    r"^[^=]+=\[([^\]]+)\]\[[^\]]+\]\[(\*?[\d\-]+|###)\]\[([^\]]+)\]",
    re.IGNORECASE,
)

# Pattern for DlgXSD dictionary:
# FIELD_KEY=[/XSD/Path][TYPE][*NNNN]{Context}[Description]
# or
# FIELD_KEY=[/XSD/Path][TYPE][###]{Context}[Description]
_DLG_PATTERN = re.compile(
    r"^[^=]+=\[([^\]]+)\]\[[^\]]+\]\[(\*?[\d\-]+|###)\](?:\{[^}]*\})?\[([^\]]+)\]",
    re.IGNORECASE,
)

# Pattern for DlgXSD dictionary — extract section from {Context}
_DLG_SECTION_PATTERN = re.compile(
    r"^[^=]+=\[[^\]]+\]\[[^\]]+\]\[[^\]]+\]\{([^}]*)\}\[([^\]]+)\]",
    re.IGNORECASE,
)


def _parse_casilla_num(raw: str) -> Optional[str]:
    """
    Extract a clean casilla number from raw token like '*0505', '0505', or '*06-09'.
    Returns None for '###' (no casilla number).
    """
    if raw == "###":
        return None
    # Remove leading '*' if present, normalise to zero-padded 4-digit
    num = raw.lstrip("*")
    if re.match(r"^\d+$", num):
        return num.zfill(4)
    # Range like '06-09' — return first number
    m = re.match(r"^(\d+)", num)
    if m:
        return m.group(1).zfill(4)
    return num


def parse_xsd_file(filepath: Path, encoding: str = "iso-8859-1") -> dict[str, dict]:
    """
    Parse diccionarioXSD_2024.properties.
    Returns dict keyed by casilla_num -> {casilla_num, description, xsd_path, section}.
    Only entries with a real casilla number are included.
    """
    entries: dict[str, dict] = {}
    if not filepath.exists():
        print(f"[WARN] File not found: {filepath}")
        return entries

    with filepath.open(encoding=encoding, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _XSD_PATTERN.match(line)
            if not m:
                continue
            xsd_path, casilla_raw, description = m.group(1), m.group(2), m.group(3)
            casilla_num = _parse_casilla_num(casilla_raw)
            if casilla_num is None:
                continue
            section = _path_to_section(xsd_path)
            # Only keep first occurrence per casilla_num (XSD file can have duplicates)
            if casilla_num not in entries:
                entries[casilla_num] = {
                    "casilla_num": casilla_num,
                    "description": description.strip(),
                    "xsd_path": xsd_path,
                    "section": section,
                    "source": "xsd",
                }
    return entries


def parse_dlg_file(filepath: Path, encoding: str = "iso-8859-1") -> dict[str, dict]:
    """
    Parse diccionarioDlgXSD_2024.properties.
    Returns dict keyed by casilla_num -> {...}. Entries with {Context} use context as section.
    """
    entries: dict[str, dict] = {}
    if not filepath.exists():
        print(f"[WARN] File not found: {filepath}")
        return entries

    with filepath.open(encoding=encoding, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = _DLG_PATTERN.match(line)
            if not m:
                continue
            xsd_path, casilla_raw, description = m.group(1), m.group(2), m.group(3)
            casilla_num = _parse_casilla_num(casilla_raw)
            if casilla_num is None:
                continue

            # Try to extract section from {Context} block
            m_ctx = _DLG_SECTION_PATTERN.match(line)
            if m_ctx:
                ctx_raw = m_ctx.group(1).strip()
                # Context can have multiple sentences separated by spaces — take first ~60 chars
                section = ctx_raw[:80].strip() if ctx_raw else _path_to_section(xsd_path)
            else:
                section = _path_to_section(xsd_path)

            if casilla_num not in entries:
                entries[casilla_num] = {
                    "casilla_num": casilla_num,
                    "description": description.strip(),
                    "xsd_path": xsd_path,
                    "section": section,
                    "source": "dlg",
                }
    return entries


def merge_entries(
    xsd_entries: dict[str, dict],
    dlg_entries: dict[str, dict],
) -> list[dict]:
    """
    Merge both dictionaries. Dlg entries take priority over XSD for the same casilla_num.
    """
    merged = dict(xsd_entries)  # start with XSD
    for casilla_num, entry in dlg_entries.items():
        merged[casilla_num] = entry  # Dlg wins
    return list(merged.values())


# ---------------------------------------------------------------------------
# DB seeding
# ---------------------------------------------------------------------------

async def seed(dry_run: bool = False) -> None:
    from app.database.turso_client import TursoClient

    print(f"Parsing {XSD_FILE.name} ...")
    xsd_entries = parse_xsd_file(XSD_FILE)
    print(f"  -> {len(xsd_entries)} casillas found")

    print(f"Parsing {DLG_FILE.name} ...")
    dlg_entries = parse_dlg_file(DLG_FILE)
    print(f"  -> {len(dlg_entries)} casillas found")

    rows = merge_entries(xsd_entries, dlg_entries)
    print(f"Merged total: {len(rows)} unique casillas")

    if dry_run:
        print("\n[DRY RUN] First 10 entries:")
        for row in sorted(rows, key=lambda r: r["casilla_num"])[:10]:
            print(
                f"  [{row['casilla_num']}] {row['description'][:60]}"
                f"  | section={row['section'][:40]}"
                f"  | source={row['source']}"
            )
        print(f"\n[DRY RUN] Would insert {len(rows)} rows into irpf_casillas. No changes made.")
        return

    db = TursoClient()
    await db.connect()

    try:
        # Ensure table exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS irpf_casillas (
                id TEXT PRIMARY KEY,
                casilla_num TEXT NOT NULL,
                description TEXT NOT NULL,
                xsd_path TEXT,
                section TEXT,
                source TEXT DEFAULT 'xsd',
                year INTEGER DEFAULT 2024
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_casillas_num ON irpf_casillas(casilla_num)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_casillas_desc ON irpf_casillas(description)")

        # Idempotent: delete existing rows for year=2024 then re-insert
        print("Deleting existing rows for year=2024 ...")
        await db.execute("DELETE FROM irpf_casillas WHERE year = ?", [2024])

        print(f"Inserting {len(rows)} rows ...")
        sql = """
            INSERT INTO irpf_casillas (id, casilla_num, description, xsd_path, section, source, year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        for row in rows:
            await db.execute(sql, [
                str(uuid.uuid4()),
                row["casilla_num"],
                row["description"],
                row.get("xsd_path"),
                row.get("section"),
                row["source"],
                2024,
            ])

        # Verify
        result = await db.execute(
            "SELECT COUNT(*) as cnt FROM irpf_casillas WHERE year = ?", [2024]
        )
        count = result.rows[0]["cnt"] if result.rows else 0
        print(f"Verification: {count} rows in irpf_casillas for year=2024")

    finally:
        await db.disconnect()

    print("Done.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed IRPF casillas from AEAT .properties files")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse files and print summary without modifying the database",
    )
    args = parser.parse_args()

    asyncio.run(seed(dry_run=args.dry_run))
