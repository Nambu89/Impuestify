"""
Seed foral IRPF deductions v2 — 27 deductions for 4 foral territories.

Territories covered:
- Araba     (8 deductions, codes ARA-*)
- Bizkaia   (6 deductions, codes BIZ-*)
- Gipuzkoa  (6 deductions, codes GIP-*)
- Navarra   (7 deductions, codes NAV-*)

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
    {
        "code": "ARA-VIVIENDA",
        "name": "Deduccion por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "territory": "Araba",
        "percentage": 20.0,
        "max_amount": 1600.0,
        "legal_reference": "Art. 86 NF 33/2013 Araba",
        "description": (
            "20% del alquiler pagado, maximo 1.600 EUR/ano. "
            "Solo si la base imponible es inferior a 30.000 EUR."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion",
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
            {"key": "nacimiento_o_adopcion", "text": "Ha nacido o adoptado un hijo este ano?", "type": "bool"},
            {"key": "numero_hijo", "text": "Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "ARA-GUARDERIA",
        "name": "Gastos en guarderia o centro de educacion infantil",
        "type": "deduccion",
        "category": "familia",
        "territory": "Araba",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 79 bis NF 33/2013 Araba",
        "description": "30% de los gastos en guarderia, maximo 900 EUR por hijo menor de 3 anos.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "Tienes hijos menores de 3 anos en guarderia?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "Cuanto has pagado en guarderia este ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-DISCAPACIDAD",
        "name": "Deduccion por discapacidad propia o familiar",
        "type": "deduccion",
        "category": "discapacidad",
        "territory": "Araba",
        "fixed_amount": 800.0,
        "legal_reference": "Art. 82 NF 33/2013 Araba",
        "description": (
            "800 EUR para discapacidad entre 33% y 65%; "
            "1.500 EUR para discapacidad igual o superior al 65%."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "Tienes o tienes a cargo a alguien con discapacidad reconocida?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "El grado es del 33-65% o >= 65%?", "type": "text"},
        ]),
    },
    {
        "code": "ARA-EPSV",
        "name": "Aportaciones a EPSV (Entidad de Prevision Social Voluntaria)",
        "type": "reduccion",
        "category": "prevision",
        "territory": "Araba",
        "max_amount": 5000.0,
        "legal_reference": "Art. 71 NF 33/2013 Araba",
        "description": (
            "Reduccion de la base imponible por aportaciones a EPSV, "
            "maximo 5.000 EUR anuales. "
            "Sustituye a los planes de pensiones del regimen comun."
        ),
        "requirements_json": json.dumps({"tiene_epsv": True}),
        "questions_json": json.dumps([
            {"key": "tiene_epsv", "text": "Tienes una EPSV (Entidad de Prevision Social Voluntaria)?", "type": "bool"},
            {"key": "aportacion_epsv", "text": "Cuanto has aportado a la EPSV este ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-DONACIONES",
        "name": "Donaciones a entidades de interes general (regimen foral)",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Araba",
        "percentage": 30.0,
        "legal_reference": "Art. 89 NF 33/2013 Araba",
        "description": "30% de los donativos realizados a entidades acogidas a la normativa foral.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "Has realizado donativos a entidades sin animo de lucro este ano?", "type": "bool"},
            {"key": "importe_donativos", "text": "Importe total de los donativos (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-CONCILIACION",
        "name": "Deduccion por conciliacion laboral y familiar (hombres)",
        "type": "deduccion",
        "category": "familia",
        "territory": "Araba",
        "fixed_amount": 500.0,
        "legal_reference": "Art. 79 ter NF 33/2013 Araba (novedad 2025)",
        "description": (
            "500 EUR para hombres trabajadores que se hayan acogido a "
            "excedencia o reduccion de jornada por cuidado de hijos. "
            "Medida de fomento de conciliacion incorporada en 2025."
        ),
        "requirements_json": json.dumps({
            "sexo": "hombre",
            "excedencia_o_reduccion_jornada_cuidado": True,
        }),
        "questions_json": json.dumps([
            {"key": "excedencia_o_reduccion_jornada_cuidado", "text": "Te has acogido a excedencia o reduccion de jornada por cuidado de hijos este ano?", "type": "bool"},
        ]),
    },
    {
        "code": "ARA-VIUDEDAD",
        "name": "Deduccion complementaria por pension de viudedad",
        "type": "deduccion",
        "category": "otros",
        "territory": "Araba",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 82 quater NF 33/2013 Araba (novedad 2025)",
        "description": (
            "300 EUR adicionales para contribuyentes que perciban pension de viudedad. "
            "Incorporado en la reforma foral de 2025."
        ),
        "requirements_json": json.dumps({"pension_viudedad": True}),
        "questions_json": json.dumps([
            {"key": "pension_viudedad", "text": "Percibes pension de viudedad?", "type": "bool"},
        ]),
    },
]

# ---------------------------------------------------------------------------
# Bizkaia (Norma Foral 13/2013, actualizada 2025)
# ---------------------------------------------------------------------------
BIZKAIA_FORALES_V2 = [
    {
        "code": "BIZ-VIVIENDA",
        "name": "Deduccion por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "territory": "Bizkaia",
        "percentage": 20.0,
        "max_amount": 1600.0,
        "legal_reference": "Art. 87 NF 13/2013 Bizkaia",
        "description": "20% del alquiler pagado, maximo 1.600 EUR/ano.",
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "BIZ-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion",
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
            {"key": "nacimiento_o_adopcion", "text": "Ha nacido o adoptado un hijo este ano?", "type": "bool"},
            {"key": "numero_hijo", "text": "Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "BIZ-GUARDERIA",
        "name": "Gastos en guarderia o centro de educacion infantil",
        "type": "deduccion",
        "category": "familia",
        "territory": "Bizkaia",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 80 bis NF 13/2013 Bizkaia",
        "description": "30% de los gastos en guarderia, maximo 900 EUR por hijo menor de 3 anos.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "Tienes hijos menores de 3 anos en guarderia?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "Cuanto has pagado en guarderia este ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "BIZ-DISCAPACIDAD",
        "name": "Deduccion por discapacidad propia o familiar",
        "type": "deduccion",
        "category": "discapacidad",
        "territory": "Bizkaia",
        "fixed_amount": 800.0,
        "legal_reference": "Art. 83 NF 13/2013 Bizkaia",
        "description": "800 EUR (33-65%); 1.500 EUR (>= 65%).",
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "Tienes o tienes a cargo a alguien con discapacidad reconocida?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "El grado es del 33-65% o >= 65%?", "type": "text"},
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
        "description": "Reduccion de base imponible por aportaciones a EPSV, limite 5.000 EUR.",
        "requirements_json": json.dumps({"tiene_epsv": True}),
        "questions_json": json.dumps([
            {"key": "tiene_epsv", "text": "Tienes una EPSV?", "type": "bool"},
            {"key": "aportacion_epsv", "text": "Cuanto has aportado a la EPSV este ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "BIZ-DONACIONES",
        "name": "Donaciones a entidades de interes general",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Bizkaia",
        "percentage": 30.0,
        "legal_reference": "Art. 90 NF 13/2013 Bizkaia",
        "description": "30% de los donativos a entidades acogidas a la normativa foral de Bizkaia.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "Has realizado donativos este ano?", "type": "bool"},
            {"key": "importe_donativos", "text": "Importe total (EUR)?", "type": "number"},
        ]),
    },
]

# ---------------------------------------------------------------------------
# Gipuzkoa (Norma Foral 3/2014, actualizada 2025)
# ---------------------------------------------------------------------------
GIPUZKOA_FORALES_V2 = [
    {
        "code": "GIP-VIVIENDA",
        "name": "Deduccion por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "territory": "Gipuzkoa",
        "percentage": 20.0,
        "max_amount": 1600.0,
        "legal_reference": "Art. 89 NF 3/2014 Gipuzkoa",
        "description": "20% del alquiler pagado, maximo 1.600 EUR/ano.",
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "GIP-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion",
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
            {"key": "nacimiento_o_adopcion", "text": "Ha nacido o adoptado un hijo este ano?", "type": "bool"},
            {"key": "numero_hijo", "text": "Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "GIP-GUARDERIA",
        "name": "Gastos en guarderia",
        "type": "deduccion",
        "category": "familia",
        "territory": "Gipuzkoa",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 82 bis NF 3/2014 Gipuzkoa",
        "description": "30% de gastos de guarderia, maximo 900 EUR por hijo menor de 3 anos.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "Tienes hijos menores de 3 anos en guarderia?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "Cuanto has pagado en guarderia (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "GIP-DISCAPACIDAD",
        "name": "Deduccion por discapacidad propia o familiar",
        "type": "deduccion",
        "category": "discapacidad",
        "territory": "Gipuzkoa",
        "fixed_amount": 800.0,
        "legal_reference": "Art. 85 NF 3/2014 Gipuzkoa",
        "description": "800 EUR (33-65%); 1.500 EUR (>= 65%).",
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "Tienes discapacidad reconocida o tienes a cargo a alguien con discapacidad?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "El grado es del 33-65% o >= 65%?", "type": "text"},
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
        "description": "Reduccion de base imponible por aportaciones a EPSV, limite 5.000 EUR.",
        "requirements_json": json.dumps({"tiene_epsv": True}),
        "questions_json": json.dumps([
            {"key": "tiene_epsv", "text": "Tienes una EPSV?", "type": "bool"},
            {"key": "aportacion_epsv", "text": "Cuanto has aportado este ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "GIP-DONACIONES",
        "name": "Donaciones a entidades de interes general",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Gipuzkoa",
        "percentage": 30.0,
        "legal_reference": "Art. 92 NF 3/2014 Gipuzkoa",
        "description": "30% de los donativos a entidades acogidas a la normativa foral de Gipuzkoa.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "Has realizado donativos este ano?", "type": "bool"},
            {"key": "importe_donativos", "text": "Importe total (EUR)?", "type": "number"},
        ]),
    },
]

# ---------------------------------------------------------------------------
# Navarra (Ley Foral 22/1998, DFL 2025)
# ---------------------------------------------------------------------------
NAVARRA_FORALES_V2 = [
    {
        "code": "NAV-VIVIENDA",
        "name": "Deduccion por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "territory": "Navarra",
        "percentage": 15.0,
        "max_amount": 1200.0,
        "legal_reference": "Art. 62 LF 22/1998 Navarra",
        "description": (
            "15% del alquiler pagado, maximo 1.200 EUR/ano. "
            "Solo aplicable si la base imponible es inferior a 30.000 EUR."
        ),
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
            "base_imponible_max": 30000,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion",
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
            {"key": "nacimiento_o_adopcion", "text": "Ha nacido o adoptado un hijo este ano?", "type": "bool"},
            {"key": "numero_hijo", "text": "Es el primero, segundo o tercero (o posterior)?", "type": "text"},
        ]),
    },
    {
        "code": "NAV-GUARDERIA",
        "name": "Gastos en guarderia",
        "type": "deduccion",
        "category": "familia",
        "territory": "Navarra",
        "percentage": 30.0,
        "max_amount": 900.0,
        "legal_reference": "Art. 59 bis LF 22/1998 Navarra",
        "description": "30% de gastos de guarderia, maximo 900 EUR por hijo menor de 3 anos.",
        "requirements_json": json.dumps({"hijos_menores_3": True}),
        "questions_json": json.dumps([
            {"key": "hijos_menores_3", "text": "Tienes hijos menores de 3 anos en guarderia?", "type": "bool"},
            {"key": "gastos_guarderia", "text": "Cuanto has pagado en guarderia (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-DISCAPACIDAD",
        "name": "Deduccion por discapacidad propia o familiar",
        "type": "deduccion",
        "category": "discapacidad",
        "territory": "Navarra",
        "fixed_amount": 900.0,
        "legal_reference": "Art. 61 LF 22/1998 Navarra",
        "description": "900 EUR (33-65%); 1.500 EUR (>= 65%).",
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "Tienes o tienes a cargo a alguien con discapacidad reconocida?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "El grado es del 33-65% o >= 65%?", "type": "text"},
        ]),
    },
    {
        "code": "NAV-PENSIONES",
        "name": "Aportaciones a plan de prevision social (Navarra)",
        "type": "reduccion",
        "category": "prevision",
        "territory": "Navarra",
        "max_amount": 5000.0,
        "legal_reference": "Art. 51 LF 22/1998 Navarra",
        "description": (
            "Reduccion de la base imponible por aportaciones a planes de prevision social, "
            "maximo 5.000 EUR (incluye planes de pensiones y EPSV reconocidas en Navarra)."
        ),
        "requirements_json": json.dumps({"tiene_plan_prevision": True}),
        "questions_json": json.dumps([
            {"key": "tiene_plan_prevision", "text": "Tienes un plan de pensiones o plan de prevision social?", "type": "bool"},
            {"key": "aportacion_plan", "text": "Cuanto has aportado este ano (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-DONACIONES",
        "name": "Donaciones a entidades de interes general",
        "type": "deduccion",
        "category": "donaciones",
        "territory": "Navarra",
        "percentage": 25.0,
        "legal_reference": "Art. 65 LF 22/1998 Navarra",
        "description": "25% de los donativos a entidades acogidas a la normativa foral de Navarra.",
        "requirements_json": json.dumps({"donativos_forales": True}),
        "questions_json": json.dumps([
            {"key": "donativos_forales", "text": "Has realizado donativos este ano?", "type": "bool"},
            {"key": "importe_donativos", "text": "Importe total (EUR)?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-BICICLETA",
        "name": "Deduccion por adquisicion de bicicleta de uso urbano sostenible",
        "type": "deduccion",
        "category": "sostenibilidad",
        "territory": "Navarra",
        "max_amount": 200.0,
        "legal_reference": "Art. 62 quater LF 22/1998 Navarra (novedad 2025)",
        "description": (
            "Maximo 200 EUR por la adquisicion de bicicletas convencionales o electricas "
            "destinadas al desplazamiento urbano habitual. Incorporado en DFL 2025."
        ),
        "requirements_json": json.dumps({"bicicleta_urbana_adquirida": True}),
        "questions_json": json.dumps([
            {"key": "bicicleta_urbana_adquirida", "text": "Has comprado una bicicleta para desplazarte habitualmente este ano?", "type": "bool"},
            {"key": "precio_bicicleta", "text": "Cuanto costo la bicicleta (EUR)?", "type": "number"},
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


async def seed_deductions_forales_v2() -> None:
    """Insert foral deductions v2 (INSERT OR IGNORE for idempotency)."""
    print("=" * 60)
    print("SEED: Deducciones Forales v2 (Araba, Bizkaia, Gipuzkoa, Navarra)")
    print("=" * 60)

    db = TursoClient()
    await db.connect()

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
