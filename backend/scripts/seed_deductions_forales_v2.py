"""
Seed foral IRPF deductions v2 — 19 deductions for 4 foral territories.

NOTE: Vivienda and Discapacidad deductions are in seed_deductions_territorial.py
      (ARA/BIZ/GIP/NAV-ALQUILER-VIV and -DISCAPACIDAD). Not duplicated here.

Territories covered:
- Araba     (6 deductions, codes ARA-*)
- Bizkaia   (4 deductions, codes BIZ-*)
- Gipuzkoa  (4 deductions, codes GIP-*)
- Navarra   (5 deductions, codes NAV-*)

Idempotent: uses INSERT OR IGNORE on the UNIQUE code column.

Usage:
    cd backend
    PYTHONUTF8=1 python scripts/seed_deductions_forales_v2.py
"""
import asyncio
import json
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
# Araba (Norma Foral 33/2013, actualizada 2025)
# ---------------------------------------------------------------------------
ARABA_FORALES_V2 = [
    # ARA-VIVIENDA removed — duplicate of ARA-ALQUILER-VIV in seed_deductions_territorial.py
    # ARA-DISCAPACIDAD removed — duplicate of ARA-DISCAPACIDAD in seed_deductions_territorial.py
    {
        "code": "ARA-NACIMIENTO",
        "name": "Deducción por nacimiento o adopción",
        "type": "deduccion",
        "category": "familia",
        "territory": "Araba",
        "fixed_amount": 1500.0,
        "legal_reference": "Art. 79 NF 33/2013 Araba",
        "description": (
            "1.500 EUR por el primer hijo, 1.900 EUR por el segundo, "
            "2.300 EUR por el tercero o posteriores."
        ),
        "requirements_json": json.dumps({"nacimiento_o_adopcion": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_o_adopcion", "text": "¿Ha nacido o adoptado un hijo este año?", "type": "bool"},
            {"key": "numero_hijo", "text": "¿Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "ARA-GUARDERIA",
        "name": "Gastos en guardería o centro de educación infantil",
        "type": "deduccion",
        "category": "familia",
        "territory": "Araba",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 79 bis NF 33/2013 Araba",
        "description": "30% de los gastos en guardería, máximo 900 EUR por hijo menor de 3 años.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "¿Tienes hijos menores de 3 años en guardería?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "¿Cuánto has pagado en guardería este año (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-EPSV",
        "name": "Aportaciones a EPSV (Entidad de Previsión Social Voluntaria)",
        "type": "reduccion",
        "category": "prevision",
        "territory": "Araba",
        "max_amount": 5000.0,
        "legal_reference": "Art. 71 NF 33/2013 Araba",
        "description": (
            "Reducción de la base imponible por aportaciones a EPSV, "
            "máximo 5.000 EUR anuales. "
            "Sustituye a los planes de pensiones del régimen común."
        ),
        "requirements_json": json.dumps({"tiene_epsv": True}),
        "questions_json": json.dumps([
            {"key": "tiene_epsv", "text": "¿Tienes una EPSV (Entidad de Previsión Social Voluntaria)?", "type": "bool"},
            {"key": "aportacion_epsv", "text": "¿Cuánto has aportado a la EPSV este año (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-DONACIONES",
        "name": "Donaciones a entidades de interés general (régimen foral)",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Araba",
        "percentage": 30.0,
        "legal_reference": "Art. 89 NF 33/2013 Araba",
        "description": "30% de los donativos realizados a entidades acogidas a la normativa foral.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "¿Has realizado donativos a entidades sin ánimo de lucro este año?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Importe total de los donativos (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-CONCILIACION",
        "name": "Deducción por conciliación laboral y familiar (hombres)",
        "type": "deduccion",
        "category": "familia",
        "territory": "Araba",
        "fixed_amount": 500.0,
        "legal_reference": "Art. 79 ter NF 33/2013 Araba (novedad 2025)",
        "description": (
            "500 EUR para hombres trabajadores que se hayan acogido a "
            "excedencia o reducción de jornada por cuidado de hijos. "
            "Medida de fomento de conciliación incorporada en 2025."
        ),
        "requirements_json": json.dumps({
            "sexo": "hombre",
            "excedencia_o_reduccion_jornada_cuidado": True,
        }),
        "questions_json": json.dumps([
            {"key": "excedencia_o_reduccion_jornada_cuidado", "text": "¿Te has acogido a excedencia o reducción de jornada por cuidado de hijos este año?", "type": "bool"},
        ]),
    },
    {
        "code": "ARA-VIUDEDAD",
        "name": "Deducción complementaria por pensión de viudedad",
        "type": "deduccion",
        "category": "otros",
        "territory": "Araba",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 82 quater NF 33/2013 Araba (novedad 2025)",
        "description": (
            "300 EUR adicionales para contribuyentes que perciban pensión de viudedad. "
            "Incorporado en la reforma foral de 2025."
        ),
        "requirements_json": json.dumps({"pension_viudedad": True}),
        "questions_json": json.dumps([
            {"key": "pension_viudedad", "text": "¿Percibes pensión de viudedad?", "type": "bool"},
        ]),
    },
]

# ---------------------------------------------------------------------------
# Bizkaia (Norma Foral 13/2013, actualizada 2025)
# ---------------------------------------------------------------------------
BIZKAIA_FORALES_V2 = [
    # BIZ-VIVIENDA removed — duplicate of BIZ-ALQUILER-VIV in seed_deductions_territorial.py
    # BIZ-DISCAPACIDAD removed — duplicate of BIZ-DISCAPACIDAD in seed_deductions_territorial.py
    {
        "code": "BIZ-NACIMIENTO",
        "name": "Deducción por nacimiento o adopción",
        "type": "deduccion",
        "category": "familia",
        "territory": "Bizkaia",
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 80 NF 13/2013 Bizkaia",
        "description": (
            "1.200 EUR por el primer hijo, 1.500 EUR por el segundo, "
            "1.800 EUR por el tercero o posteriores."
        ),
        "requirements_json": json.dumps({"nacimiento_o_adopcion": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_o_adopcion", "text": "¿Ha nacido o adoptado un hijo este año?", "type": "bool"},
            {"key": "numero_hijo", "text": "¿Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "BIZ-GUARDERIA",
        "name": "Gastos en guardería o centro de educación infantil",
        "type": "deduccion",
        "category": "familia",
        "territory": "Bizkaia",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 80 bis NF 13/2013 Bizkaia",
        "description": "30% de los gastos en guardería, máximo 900 EUR por hijo menor de 3 años.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "¿Tienes hijos menores de 3 años en guardería?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "¿Cuánto has pagado en guardería este año (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "BIZ-EPSV",
        "name": "Aportaciones a EPSV",
        "type": "reduccion",
        "category": "prevision",
        "territory": "Bizkaia",
        "max_amount": 5000.0,
        "legal_reference": "Art. 72 NF 13/2013 Bizkaia",
        "description": "Reducción de base imponible por aportaciones a EPSV, límite 5.000 EUR.",
        "requirements_json": json.dumps({"tiene_epsv": True}),
        "questions_json": json.dumps([
            {"key": "tiene_epsv", "text": "¿Tienes una EPSV?", "type": "bool"},
            {"key": "aportacion_epsv", "text": "¿Cuánto has aportado a la EPSV este año (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "BIZ-DONACIONES",
        "name": "Donaciones a entidades de interés general",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Bizkaia",
        "percentage": 30.0,
        "legal_reference": "Art. 90 NF 13/2013 Bizkaia",
        "description": "30% de los donativos a entidades acogidas a la normativa foral de Bizkaia.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "¿Has realizado donativos este año?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Importe total (EUR)?", "type": "number"},
        ]),
    },
]

# ---------------------------------------------------------------------------
# Gipuzkoa (Norma Foral 3/2014, actualizada 2025)
# ---------------------------------------------------------------------------
GIPUZKOA_FORALES_V2 = [
    # GIP-VIVIENDA removed — duplicate of GIP-ALQUILER-VIV in seed_deductions_territorial.py
    # GIP-DISCAPACIDAD removed — duplicate of GIP-DISCAPACIDAD in seed_deductions_territorial.py
    {
        "code": "GIP-NACIMIENTO",
        "name": "Deducción por nacimiento o adopción",
        "type": "deduccion",
        "category": "familia",
        "territory": "Gipuzkoa",
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 82 NF 3/2014 Gipuzkoa",
        "description": (
            "1.200 EUR por el primer hijo, 1.500 EUR por el segundo, "
            "1.800 EUR por el tercero o posteriores."
        ),
        "requirements_json": json.dumps({"nacimiento_o_adopcion": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_o_adopcion", "text": "¿Ha nacido o adoptado un hijo este año?", "type": "bool"},
            {"key": "numero_hijo", "text": "¿Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "GIP-GUARDERIA",
        "name": "Gastos en guardería",
        "type": "deduccion",
        "category": "familia",
        "territory": "Gipuzkoa",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 82 bis NF 3/2014 Gipuzkoa",
        "description": "30% de gastos de guardería, máximo 900 EUR por hijo menor de 3 años.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "¿Tienes hijos menores de 3 años en guardería?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "¿Cuánto has pagado en guardería (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "GIP-EPSV",
        "name": "Aportaciones a EPSV",
        "type": "reduccion",
        "category": "prevision",
        "territory": "Gipuzkoa",
        "max_amount": 5000.0,
        "legal_reference": "Art. 74 NF 3/2014 Gipuzkoa",
        "description": "Reducción de base imponible por aportaciones a EPSV, límite 5.000 EUR.",
        "requirements_json": json.dumps({"tiene_epsv": True}),
        "questions_json": json.dumps([
            {"key": "tiene_epsv", "text": "¿Tienes una EPSV?", "type": "bool"},
            {"key": "aportacion_epsv", "text": "¿Cuánto has aportado este año (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "GIP-DONACIONES",
        "name": "Donaciones a entidades de interés general",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Gipuzkoa",
        "percentage": 30.0,
        "legal_reference": "Art. 92 NF 3/2014 Gipuzkoa",
        "description": "30% de los donativos a entidades acogidas a la normativa foral de Gipuzkoa.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "¿Has realizado donativos este año?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Importe total (EUR)?", "type": "number"},
        ]),
    },
]

# ---------------------------------------------------------------------------
# Navarra (Ley Foral 22/1998, DFL 2025)
# ---------------------------------------------------------------------------
NAVARRA_FORALES_V2 = [
    # NAV-VIVIENDA removed — duplicate of NAV-ALQUILER-VIV in seed_deductions_territorial.py
    # NAV-DISCAPACIDAD removed — duplicate of NAV-DISCAPACIDAD in seed_deductions_territorial.py
    {
        "code": "NAV-NACIMIENTO",
        "name": "Deducción por nacimiento o adopción",
        "type": "deduccion",
        "category": "familia",
        "territory": "Navarra",
        "fixed_amount": 1000.0,
        "legal_reference": "Art. 59 LF 22/1998 Navarra",
        "description": (
            "1.000 EUR por el primer hijo, 1.200 EUR por el segundo, "
            "1.400 EUR por el tercero o posteriores."
        ),
        "requirements_json": json.dumps({"nacimiento_o_adopcion": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_o_adopcion", "text": "¿Ha nacido o adoptado un hijo este año?", "type": "bool"},
            {"key": "numero_hijo", "text": "¿Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "NAV-GUARDERIA",
        "name": "Gastos en guardería",
        "type": "deduccion",
        "category": "familia",
        "territory": "Navarra",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 59 bis LF 22/1998 Navarra",
        "description": "30% de gastos de guardería, máximo 900 EUR por hijo menor de 3 años.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "¿Tienes hijos menores de 3 años en guardería?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "¿Cuánto has pagado en guardería (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-PENSIONES",
        "name": "Aportaciones a plan de previsión social (Navarra)",
        "type": "reduccion",
        "category": "prevision",
        "territory": "Navarra",
        "max_amount": 5000.0,
        "legal_reference": "Art. 51 LF 22/1998 Navarra",
        "description": (
            "Reducción de la base imponible por aportaciones a planes de previsión social, "
            "máximo 5.000 EUR (incluye planes de pensiones y EPSV reconocidas en Navarra)."
        ),
        "requirements_json": json.dumps({"tiene_plan_prevision": True}),
        "questions_json": json.dumps([
            {"key": "tiene_plan_prevision", "text": "¿Tienes un plan de pensiones o plan de previsión social?", "type": "bool"},
            {"key": "aportacion_plan", "text": "¿Cuánto has aportado este año (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-DONACIONES",
        "name": "Donaciones a entidades de interés general",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Navarra",
        "percentage": 25.0,
        "legal_reference": "Art. 65 LF 22/1998 Navarra",
        "description": "25% de los donativos a entidades acogidas a la normativa foral de Navarra.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "¿Has realizado donativos este año?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Importe total (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-BICICLETA",
        "name": "Deducción por adquisición de bicicleta de uso urbano sostenible",
        "type": "deduccion",
        "category": "sostenibilidad",
        "territory": "Navarra",
        "max_amount": 200.0,
        "legal_reference": "Art. 62 quater LF 22/1998 Navarra (novedad 2025)",
        "description": (
            "Máximo 200 EUR por la adquisición de bicicletas convencionales o eléctricas "
            "destinadas al desplazamiento urbano habitual. Incorporado en DFL 2025."
        ),
        "requirements_json": json.dumps({"bicicleta_urbana_adquirida": True}),
        "questions_json": json.dumps([
            {"key": "bicicleta_urbana_adquirida", "text": "¿Has comprado una bicicleta para desplazarte habitualmente este año?", "type": "bool"},
            {"key": "precio_bicicleta", "text": "¿Cuánto costó la bicicleta (EUR)?", "type": "number"},
        ]),
    },
]

# ---------------------------------------------------------------------------
# Master list
# ---------------------------------------------------------------------------
ALL_FORAL_V2 = (
    ARABA_FORALES_V2
    + BIZKAIA_FORALES_V2
    + GIPUZKOA_FORALES_V2
    + NAVARRA_FORALES_V2
)

TAX_YEAR = 2025


DEPRECATED_DUPLICATE_CODES = [
    "ARA-VIVIENDA",   # duplicate of ARA-ALQUILER-VIV
    "BIZ-VIVIENDA",   # duplicate of BIZ-ALQUILER-VIV
    "GIP-VIVIENDA",   # duplicate of GIP-ALQUILER-VIV
    "NAV-VIVIENDA",   # duplicate of NAV-ALQUILER-VIV
]


async def seed_deductions_forales_v2() -> None:
    """Insert foral deductions v2 (INSERT OR IGNORE for idempotency)."""
    print("=" * 60)
    print("SEED: Deducciones Forales v2 (Araba, Bizkaia, Gipuzkoa, Navarra)")
    print("=" * 60)

    db = TursoClient()
    await db.connect()

    # Clean up deprecated duplicate codes from previous runs
    for code in DEPRECATED_DUPLICATE_CODES:
        check = await db.execute("SELECT id FROM deductions WHERE code = ?", [code])
        if check.rows:
            await db.execute("DELETE FROM deductions WHERE code = ?", [code])
            print(f"  [CLEANUP] Removed deprecated duplicate: {code}")

    inserted = 0
    skipped = 0

    for ded in ALL_FORAL_V2:
        row_id = str(uuid.uuid4())
        result = await db.execute(
            """INSERT OR IGNORE INTO deductions
               (id, code, name, type, category, territory,
                max_amount, percentage, fixed_amount,
                requirements_json, questions_json,
                tax_year, is_active, legal_reference, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            [
                row_id,
                ded["code"],
                ded["name"],
                ded.get("type", "deduccion"),
                ded["category"],
                ded.get("territory"),
                ded.get("max_amount"),
                ded.get("percentage"),
                ded.get("fixed_amount"),
                ded.get("requirements_json"),
                ded.get("questions_json"),
                TAX_YEAR,
                ded.get("legal_reference"),
                ded.get("description"),
            ],
        )
        # Verify whether it was actually inserted (INSERT OR IGNORE is silent on conflict)
        check = await db.execute(
            "SELECT id FROM deductions WHERE code = ?", [ded["code"]]
        )
        if check.rows and check.rows[0]["id"] == row_id:
            inserted += 1
            print(f"  [INSERT] {ded['code']} — {ded['name']}")
        else:
            skipped += 1
            print(f"  [SKIP]   {ded['code']} (ya existe)")

    print(f"\nResultado: {inserted} insertadas, {skipped} omitidas (ya existian)")

    # Summary by territory
    print("\nResumen por territorio:")
    for territory in ["Araba", "Bizkaia", "Gipuzkoa", "Navarra"]:
        res = await db.execute(
            "SELECT COUNT(*) as cnt FROM deductions WHERE territory = ? AND is_active = 1",
            [territory],
        )
        cnt = res.rows[0]["cnt"] if res.rows else 0
        print(f"  {territory}: {cnt} deducciones activas")

    await db.disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(seed_deductions_forales_v2())
