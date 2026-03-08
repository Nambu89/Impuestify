"""
Seed script for IRPF autonomous community deductions from AEAT XSD (Modelo 100, Renta 2024).

Parses docs/AEAT/Renta-2025/diccionarioXSD_2024.properties to extract all P102 entries
under DeduccionAutonomicaRes, then seeds the 'deductions' table with canonical codes,
categories, casilla AEAT numbers, and basic eligibility requirements inferred from
the description text.

Idempotent: DELETEs existing rows with scope='xsd_autonomica' then INSERTs fresh ones.

Usage:
    cd backend
    python scripts/seed_deductions_xsd.py
"""

import asyncio
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# CCAA mapping: XSD node name -> canonical territory name used in DB
# ---------------------------------------------------------------------------
CCAA_MAP: dict[str, str] = {
    "AndaluciaRes": "Andalucia",
    "AragonRes": "Aragon",
    "AsturiasRes": "Asturias",
    "IBalearesRes": "Baleares",
    "CanariasRes": "Canarias",
    "CantabriaRes": "Cantabria",
    "CastillaLaManchaRes": "Castilla-La Mancha",
    "CastillaYLeonRes": "Castilla y Leon",
    "CatalunyaRes": "Cataluna",
    "ExtremaduraRes": "Extremadura",
    "GaliciaRes": "Galicia",
    "LaRiojaRes": "La Rioja",
    "MadridRes": "Madrid",
    "MurciaRes": "Murcia",
    "CValencianaRes": "Comunidad Valenciana",
}

# Short prefix for code generation
CCAA_CODE_PREFIX: dict[str, str] = {
    "Andalucia": "AND",
    "Aragon": "ARA",
    "Asturias": "AST",
    "Baleares": "BAL",
    "Canarias": "CAN",
    "Cantabria": "CBR",
    "Castilla-La Mancha": "CLM",
    "Castilla y Leon": "CYL",
    "Cataluna": "CAT",
    "Extremadura": "EXT",
    "Galicia": "GAL",
    "La Rioja": "LRJ",
    "Madrid": "MAD",
    "Murcia": "MUR",
    "Comunidad Valenciana": "VAL",
}


# ---------------------------------------------------------------------------
# Exclusion patterns for non-deduction P102 entries within DeduccionAutonomicaRes
# ---------------------------------------------------------------------------
EXCLUDE_PATTERNS: list[str] = [
    # Totals
    r"^DEDAUT",
    # Pending amounts
    r"^PDTE",
    r"PDTEEAM",
    r"PDTEM",
    # NIFs / CCCs
    r"^NIF",
    r"^NONIF",
    r"^CCC",
    r"CC[A-Z]",
    r"^CIOVI",
    r"^GAOD$",
    r"^EXTROD$",
    r"^LROD$",
    r"^NIFCHIEA",
    # Auxiliary carry-forward amounts (CANT?EA*)
    r"CANT\dEA",
    r"CANT\dEEA",
    r"CANTG\d",
    # Matriculas, refs catastrales, municipios
    r"^NUMMAT",
    r"^RC",
    r"^NORCP",
    r"^MUN",
    # Date/year fields
    r"^FECHA",
    r"^ANADQ",
    # Abono anticipado (advance payment, not the deduction itself)
    r"^PAGO",
    # NIF fields and similar identifiers embedded in deduction blocks
    r"NIF\dCAN\d",
    r"NIF\dIB\d",
    r"NIF[A-Z]",
]

_EXCL_RE = re.compile("|".join(EXCLUDE_PATTERNS))


# ---------------------------------------------------------------------------
# Category inference rules (checked in order — first match wins)
# ---------------------------------------------------------------------------
CATEGORY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"nacimiento|adopci[oó]n|parto|acogimiento familiar|acogimiento de menores|hijo", re.IGNORECASE), "familia"),
    (re.compile(r"familia numerosa|familia monoparental|monoparental|numerosa", re.IGNORECASE), "familia"),
    (re.compile(r"discapacidad|minusval[ií]a", re.IGNORECASE), "discapacidad"),
    (re.compile(r"alquiler|arrendamiento|arrendador|arrendat", re.IGNORECASE), "vivienda"),
    (re.compile(r"vivienda|inmueble|rehabilitaci[oó]n.*vivienda|adquisici[oó]n.*vivienda|habitua", re.IGNORECASE), "vivienda"),
    (re.compile(r"sostenibilidad|energ[eé]t|renovable|eficiencia|autoconsumo|solar", re.IGNORECASE), "sostenibilidad"),
    (re.compile(r"guarder[ií]a|educaci[oó]n|escolar|libros de texto|idiomas|estudios|formaci[oó]n|m[aá]ster|doctorado", re.IGNORECASE), "educacion"),
    (re.compile(r"donaci[oó]n|donativo|donaciones", re.IGNORECASE), "donaciones"),
    (re.compile(r"inversi[oó]n.*acciones|acciones.*participaciones|entidades.*nuevas|creaci[oó]n.*reciente|[aá]ngel inversor|MAB|econom[ií]a social", re.IGNORECASE), "inversion"),
    (re.compile(r"despoblaci[oó]n|rural|municipio.*peque[ñn]|traslado.*residencia", re.IGNORECASE), "territorial"),
    (re.compile(r"transporte|bicicleta|veh[ií]culo", re.IGNORECASE), "movilidad"),
    (re.compile(r"cuidado.*familiar|cuidado.*ascendiente|cuidado.*descendiente|conciliaci[oó]n|emplead.* hogar", re.IGNORECASE), "familia"),
    (re.compile(r"emprendimiento|autoempleo|aut[oó]nomo|cuenta propia", re.IGNORECASE), "actividad_economica"),
    (re.compile(r"ELA|esclerosis|enfermedad|salud|sanitari", re.IGNORECASE), "salud"),
    (re.compile(r"patrimonio hist[oó]rico|patrimonio cultural|rehabilitaci[oó]n.*bien|bien.*interes cultural", re.IGNORECASE), "donaciones"),
    (re.compile(r"investigaci[oó]n|desarrollo|innovaci[oó]n|tecnol[oó]g", re.IGNORECASE), "donaciones"),
    (re.compile(r"trabajo|laboral", re.IGNORECASE), "trabajo"),
]


def infer_category(description: str) -> str:
    """Infer deduction category from Spanish description text."""
    for pattern, category in CATEGORY_RULES:
        if pattern.search(description):
            return category
    return "general"


# ---------------------------------------------------------------------------
# Requirements inference
# ---------------------------------------------------------------------------
def infer_requirements(description: str, category: str) -> dict[str, Any]:
    """Build a minimal requirements dict from description keywords."""
    reqs: dict[str, Any] = {}
    desc_lower = description.lower()

    if any(w in desc_lower for w in ["nacimiento", "adopci"]):
        reqs["nacimiento_adopcion_reciente"] = True
    if "hijo" in desc_lower:
        reqs["tiene_hijos"] = True
    if "familia numerosa" in desc_lower:
        reqs["familia_numerosa"] = True
    if "monoparental" in desc_lower:
        reqs["familia_monoparental"] = True
    if "discapacidad" in desc_lower:
        reqs["discapacidad_reconocida"] = True
    if any(w in desc_lower for w in ["alquiler", "arrendamiento"]) and "vivienda habitual" in desc_lower:
        reqs["alquila_vivienda_habitual"] = True
    if any(w in desc_lower for w in ["compra", "adquisici", "vivienda habitual"]) and category == "vivienda":
        reqs["vivienda_habitual"] = True
    if any(w in desc_lower for w in ["donaci", "donativo"]):
        reqs["realiza_donativos"] = True
    if "guarder" in desc_lower:
        reqs["hijos_en_guarderia"] = True
    if any(w in desc_lower for w in ["libros de texto", "material escolar"]):
        reqs["gastos_educacion_hijos"] = True
    if any(w in desc_lower for w in ["j[oó]ven", "j[oo]venes", "menores de 3", "menores de 36", "menores de 35", "menor"]):
        reqs["edad_limite_aplicable"] = True
    if "energ" in desc_lower and any(w in desc_lower for w in ["renovable", "autoconsumo", "eficiencia"]):
        reqs["obras_mejora_energetica"] = True
    if any(w in desc_lower for w in ["rural", "despoblaci", "municipio peque"]):
        reqs["reside_zona_rural"] = True
    if "investigaci" in desc_lower and "inversi" not in desc_lower:
        reqs["donativo_investigacion"] = True
    if any(w in desc_lower for w in ["acciones", "participaciones", "nuevas entidades", "reciente creaci"]):
        reqs["inversion_empresa_nueva"] = True
    if "autónomos" in desc_lower or "cuenta propia" in desc_lower:
        reqs["autonomo"] = True

    return reqs


# ---------------------------------------------------------------------------
# Question generation
# ---------------------------------------------------------------------------
def build_questions(description: str, category: str, territory: str) -> list[dict[str, Any]]:
    """Build minimal eligibility questions from description + category."""
    questions: list[dict[str, Any]] = []
    desc_lower = description.lower()

    # Primary boolean gate — always present
    short_desc = description[:100].rstrip()
    questions.append({
        "key": "aplica_deduccion",
        "text": f"¿Cumples los requisitos para la deduccion de {territory}: {short_desc}?",
        "type": "bool",
    })

    # Supplementary amount question
    if category in ("vivienda", "educacion", "donaciones", "inversion", "sostenibilidad"):
        questions.append({
            "key": "importe_pagado",
            "text": "¿Cual es el importe total pagado o invertido este año con derecho a esta deduccion?",
            "type": "number",
        })
    elif category == "familia":
        if any(w in desc_lower for w in ["nacimiento", "adopci"]):
            questions.append({
                "key": "num_hijos_nacidos",
                "text": "¿Cuantos hijos han nacido o han sido adoptados este año?",
                "type": "number",
            })
    elif category == "discapacidad":
        questions.append({
            "key": "grado_discapacidad",
            "text": "¿Cual es el grado de discapacidad reconocido (porcentaje)?",
            "type": "number",
        })

    return questions


# ---------------------------------------------------------------------------
# Code slug generation (ASCII-safe)
# ---------------------------------------------------------------------------
_SLUG_SUBS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"[áàä]", re.IGNORECASE), "A"),
    (re.compile(r"[éèë]", re.IGNORECASE), "E"),
    (re.compile(r"[íìï]", re.IGNORECASE), "I"),
    (re.compile(r"[óòö]", re.IGNORECASE), "O"),
    (re.compile(r"[úùü]", re.IGNORECASE), "U"),
    (re.compile(r"[ñ]", re.IGNORECASE), "N"),
    (re.compile(r"[^A-Z0-9]", re.IGNORECASE), "_"),
    (re.compile(r"_+"), "_"),
]


def _slugify(text: str, max_len: int = 25) -> str:
    result = text.upper()
    for pattern, replacement in _SLUG_SUBS:
        result = pattern.sub(replacement, result)
    return result.strip("_")[:max_len]


def build_code(prefix: str, xsd_key: str, description: str) -> str:
    """Build a unique-ish code like AND-A1-NACIMIENTO."""
    slug = _slugify(description)
    # Remove leading Por_ / Para_ etc.
    slug = re.sub(r"^(POR_|PARA_|DEDUCCION_)", "", slug).strip("_")
    slug = slug[:20].strip("_")
    return f"{prefix}-{xsd_key.upper()}-{slug}"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def parse_properties(path: Path) -> list[dict[str, Any]]:
    """
    Parse diccionarioXSD_2024.properties and return list of deduction dicts.

    Each dict has:
        xsd_key, xsd_path, ccaa_node, territory, casilla, description,
        category, code, requirements_json, questions_json
    """
    results: list[dict[str, Any]] = []

    with open(path, encoding="latin-1") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            # Format: KEY=[/Path][TYPE][CASILLA][Description]
            eq = line.find("=")
            if eq < 0:
                continue
            xsd_key = line[:eq].strip()
            rest = line[eq + 1 :].strip()

            # Must be inside DeduccionAutonomicaRes
            if "DeduccionAutonomicaRes" not in rest:
                continue

            # Parse bracketed segments
            segments = re.findall(r"\[([^\]]*)\]", rest)
            if len(segments) < 4:
                continue

            xsd_path = segments[0]   # /DatosEconomicos/Resultados/DeduccionAutonomicaRes/...
            field_type = segments[1]  # P102, X, LGC, FEC, ...
            casilla = segments[2]     # numeric or ### or *NNN
            description = segments[3]

            # Only keep monetary deduction fields
            if field_type != "P102":
                continue

            # Casilla must be a numeric code (not ### or *NNN)
            if not re.match(r"^\d{4}$", casilla):
                continue

            # Exclude non-deduction entries by key pattern
            if _EXCL_RE.match(xsd_key):
                continue

            # Determine CCAA from path
            ccaa_node: str | None = None
            for node in CCAA_MAP:
                if f"/{node}/" in xsd_path:
                    ccaa_node = node
                    break

            if ccaa_node is None:
                continue

            territory = CCAA_MAP[ccaa_node]
            prefix = CCAA_CODE_PREFIX[territory]
            category = infer_category(description)
            code = build_code(prefix, xsd_key, description)
            reqs = infer_requirements(description, category)
            questions = build_questions(description, category, territory)

            results.append({
                "xsd_key": xsd_key,
                "xsd_path": xsd_path,
                "ccaa_node": ccaa_node,
                "territory": territory,
                "casilla": casilla,
                "description": description,
                "category": category,
                "code": code,
                "requirements_json": json.dumps(reqs, ensure_ascii=False),
                "questions_json": json.dumps(questions, ensure_ascii=False),
            })

    return results


# ---------------------------------------------------------------------------
# Stats helper
# ---------------------------------------------------------------------------
def print_stats(deductions: list[dict[str, Any]]) -> None:
    from collections import Counter

    by_ccaa: Counter[str] = Counter()
    for d in deductions:
        by_ccaa[d["territory"]] += 1

    print("\nDeducciones por CCAA:")
    print("-" * 45)
    total = 0
    for territory, count in sorted(by_ccaa.items()):
        print(f"  {territory:<30} {count:>3}")
        total += count
    print("-" * 45)
    print(f"  {'TOTAL':<30} {total:>3}")


# ---------------------------------------------------------------------------
# JSON reference output
# ---------------------------------------------------------------------------
def save_reference_json(deductions: list[dict[str, Any]], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    output = []
    for d in deductions:
        output.append({
            "xsd_key": d["xsd_key"],
            "xsd_path": d["xsd_path"],
            "territory": d["territory"],
            "casilla_aeat": d["casilla"],
            "description": d["description"],
            "category": d["category"],
            "code": d["code"],
            "requirements": json.loads(d["requirements_json"]),
            "questions": json.loads(d["questions_json"]),
        })
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nJSON de referencia guardado: {dest}")


# ---------------------------------------------------------------------------
# DB seeding
# ---------------------------------------------------------------------------
async def seed_deductions_xsd(deductions: list[dict[str, Any]]) -> None:
    """Delete all XSD-sourced autonomous community deductions and re-insert.

    Idempotency strategy: deductions inserted by this script have
    legal_reference values starting with "Modelo 100 IRPF 2024" and
    tax_year = 2024.  We delete those rows before re-inserting.
    """
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    print("Initializing schema...")
    await db.init_schema()
    print("Schema ready.")

    # --- Idempotent: remove existing rows from this seed ---
    try:
        await db.execute(
            "DELETE FROM deductions WHERE tax_year = ? AND legal_reference LIKE ?",
            [2024, "Modelo 100 IRPF 2024%"],
        )
        print("Deleted existing 'Modelo 100 IRPF 2024' rows.")
    except Exception as exc:
        print(f"Warning during DELETE: {exc}")

    inserted = 0
    errors = 0

    for d in deductions:
        deduction_id = str(uuid.uuid4())
        name = d["description"]
        # Truncate to reasonable length for the name column
        if len(name) > 255:
            name = name[:252] + "..."

        try:
            await db.execute(
                """
                INSERT INTO deductions
                    (id, code, tax_year, territory, name, type, category,
                     percentage, max_amount, fixed_amount, legal_reference,
                     description, requirements_json, questions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    deduction_id,
                    d["code"],
                    2024,                       # tax year from XSD
                    d["territory"],
                    name,
                    "deduccion",
                    d["category"],
                    None,                        # percentage unknown from XSD
                    None,                        # max_amount unknown from XSD
                    None,                        # fixed_amount unknown from XSD
                    f"Modelo 100 IRPF 2024 — Casilla {d['casilla']}",
                    d["description"],
                    d["requirements_json"],
                    d["questions_json"],
                ],
            )
            inserted += 1
        except Exception as exc:
            print(f"  ERROR inserting {d['code']}: {exc}")
            errors += 1

    await db.disconnect()
    print(f"\nSeed complete: {inserted} inserted, {errors} errors.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
async def main() -> None:
    properties_path = PROJECT_ROOT / "docs" / "AEAT" / "Renta-2025" / "diccionarioXSD_2024.properties"

    if not properties_path.exists():
        print(f"ERROR: Archivo no encontrado: {properties_path}")
        sys.exit(1)

    print(f"Parseando: {properties_path}")
    deductions = parse_properties(properties_path)
    print(f"Deducciones extraidas: {len(deductions)}")

    # Save reference JSON regardless of DB operation
    ref_path = PROJECT_ROOT / "data" / "reference" / "deducciones_autonomicas_xsd.json"
    save_reference_json(deductions, ref_path)

    print_stats(deductions)

    # Seed DB
    await seed_deductions_xsd(deductions)


if __name__ == "__main__":
    asyncio.run(main())
