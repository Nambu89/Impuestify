"""
Seed script for ALL 17 Andalucia IRPF deductions (2025).

Replaces the 5 deductions from seed_deductions_territorial.py with a complete set
of 17 deductions verified against the AEAT manual and Ley 5/2021, de 20 de octubre,
de Tributos Cedidos de la Comunidad Autonoma de Andalucia.

Idempotent: DELETE existing Andalucia deductions for tax_year 2025, then INSERT.

Usage:
    cd backend
    python scripts/seed_deductions_andalucia_2025.py
    python scripts/seed_deductions_andalucia_2025.py --dry-run
"""
import argparse
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

TERRITORY = "Andalucía"
TAX_YEAR = 2025

# =============================================================================
# ANDALUCIA — 17 deducciones autonomicas IRPF 2025
# Fuente: Ley 5/2021, de 20 de octubre + AEAT Manual Renta 2025
# =============================================================================

ANDALUCIA_2025: list[dict] = [
    # -------------------------------------------------------------------------
    # 1. Inversion en vivienda habitual protegida / jovenes (Art. 9)
    # -------------------------------------------------------------------------
    {
        "code": "AND-VIV-001",
        "name": "Deduccion por inversion en vivienda habitual protegida o para jovenes",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 5.0,
        "max_amount": 9040.0,
        "legal_reference": "Arts. 9 y 5 Ley 5/2021 Andalucia",
        "description": (
            "5% de las cantidades satisfechas en adquisicion o rehabilitacion de "
            "vivienda protegida, o vivienda habitual por menores de 35 anos. "
            "Base maxima de inversion: 9.040 EUR anuales. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta. "
            "Solo desde 01/01/2003 si es vivienda protegida."
        ),
        "requirements_json": json.dumps({
            "vivienda_habitual_propiedad": True,
        }),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes vivienda protegida o eres menor de 35 con hipoteca?", "type": "bool"},
            {"key": "menor_35_anos", "text": "Tienes menos de 35 anos?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto has pagado de hipoteca este ano?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 2. Alquiler de vivienda habitual (Art. 10)
    # -------------------------------------------------------------------------
    {
        "code": "AND-VIV-002",
        "name": "Deduccion por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 600.0,
        "legal_reference": "Arts. 10 y 5 Ley 5/2021 Andalucia",
        "description": (
            "15% del alquiler de la vivienda habitual, maximo 600 EUR (900 EUR si "
            "el contribuyente tiene discapacidad >= 33%). "
            "Requisitos: menor de 35, mayor de 65, victima de violencia de genero "
            "o terrorismo. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al ano?", "type": "number"},
            {"key": "menor_35_anos", "text": "Tienes menos de 35 anos?", "type": "bool"},
            {"key": "mayor_65_anos", "text": "Tienes 65 o mas anos?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 3. Nacimiento, adopcion o acogimiento familiar de menores (Art. 11)
    # -------------------------------------------------------------------------
    {
        "code": "AND-FAM-001",
        "name": "Deduccion por nacimiento, adopcion o acogimiento familiar de menores",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Arts. 11 y 5 Ley 5/2021 Andalucia",
        "description": (
            "200 EUR por cada hijo nacido, adoptado o acogido. "
            "400 EUR si el nacimiento/adopcion/acogimiento se produce en un municipio "
            "de menos de 3.000 habitantes. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta. "
            "Incompatible con la deduccion por familia numerosa."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo, adoptado o acogido este ano?", "type": "bool"},
            {"key": "municipio_pequeno", "text": "Resides en un municipio de menos de 3.000 habitantes?", "type": "bool"},
            {"key": "num_hijos_recientes", "text": "Cuantos hijos/acogidos este ano?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 4. Adopcion internacional (Art. 12)
    # -------------------------------------------------------------------------
    {
        "code": "AND-FAM-002",
        "name": "Deduccion por adopcion internacional",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 600.0,
        "legal_reference": "Arts. 12 y 5 Ley 5/2021 Andalucia",
        "description": (
            "600 EUR por cada hijo adoptado internacionalmente, siempre que la "
            "adopcion tenga caracter internacional conforme a la legislacion vigente. "
            "Compatible con la deduccion por nacimiento/adopcion (Art. 11). "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"adopcion_internacional": True}),
        "questions_json": json.dumps([
            {"key": "adopcion_internacional", "text": "Has realizado una adopcion internacional este ano?", "type": "bool"},
            {"key": "num_adopciones_internacionales", "text": "Cuantas adopciones internacionales?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 5. Familia monoparental y ascendientes mayores de 75 anos (Art. 13)
    # -------------------------------------------------------------------------
    {
        "code": "AND-FAM-003",
        "name": "Deduccion por familia monoparental y ascendientes mayores de 75 anos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 100.0,
        "legal_reference": "Arts. 13 y 5 Ley 5/2021 Andalucia",
        "description": (
            "100 EUR para familias monoparentales (contribuyente soltero/a, viudo/a, "
            "separado/a o divorciado/a con hijos menores a cargo que den derecho al "
            "minimo por descendientes). "
            "Tambien 100 EUR por cada ascendiente mayor de 75 anos que conviva con "
            "el contribuyente y que genere derecho al minimo por ascendientes. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"familia_monoparental_o_ascendiente_75": True}),
        "questions_json": json.dumps([
            {"key": "familia_monoparental", "text": "Eres familia monoparental (soltero/a, viudo/a, separado/a con hijos a cargo)?", "type": "bool"},
            {"key": "ascendiente_mayor_75", "text": "Convives con ascendientes mayores de 75 anos?", "type": "bool"},
            {"key": "num_ascendientes_75", "text": "Cuantos ascendientes mayores de 75 conviven contigo?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 6. Familia numerosa (Art. 14)
    # -------------------------------------------------------------------------
    {
        "code": "AND-FAM-004",
        "name": "Deduccion por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Arts. 14 y 5 Ley 5/2021 Andalucia",
        "description": (
            "200 EUR para familia numerosa de categoria general. "
            "400 EUR para familia numerosa de categoria especial. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta. "
            "Incompatible con la deduccion por nacimiento/adopcion/acogimiento (Art. 11)."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 7. Gastos educativos (Art. 15)
    # -------------------------------------------------------------------------
    {
        "code": "AND-EDU-001",
        "name": "Deduccion por gastos educativos",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 150.0,
        "legal_reference": "Arts. 15 y 60 Ley 5/2021 Andalucia",
        "description": (
            "15% de los gastos en ensenanza de idiomas o informatica (escolares o "
            "extraescolares) de los hijos que generen derecho al minimo por "
            "descendientes. Maximo 150 EUR por descendiente al ano. "
            "Incluye academias, escuelas oficiales de idiomas y profesores "
            "particulares dados de alta en IAE. "
            "BI general + ahorro <= 80.000 EUR individual / 100.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"gastos_educativos_idiomas_informatica": True}),
        "questions_json": json.dumps([
            {"key": "gastos_educativos_idiomas_informatica", "text": "Has pagado clases de idiomas o informatica para tus hijos?", "type": "bool"},
            {"key": "importe_gastos_educativos", "text": "Cuanto has gastado en idiomas o informatica este ano?", "type": "number"},
            {"key": "num_hijos_beneficiarios", "text": "Cuantos hijos se benefician de estas clases?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 8. Discapacidad del contribuyente (Art. 16)
    # -------------------------------------------------------------------------
    {
        "code": "AND-DIS-001",
        "name": "Deduccion por discapacidad del contribuyente",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 150.0,
        "legal_reference": "Arts. 16 y 5 Ley 5/2021 Andalucia",
        "description": (
            "150 EUR para contribuyentes con grado de discapacidad >= 33%. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "Tienes un grado de discapacidad reconocida >= 33%?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "Que grado de discapacidad tienes?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 9. Discapacidad del conyuge o pareja de hecho (Art. 17)
    # -------------------------------------------------------------------------
    {
        "code": "AND-DIS-002",
        "name": "Deduccion por discapacidad del conyuge o pareja de hecho",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 150.0,
        "legal_reference": "Arts. 17 y 5 Ley 5/2021 Andalucia",
        "description": (
            "150 EUR si el conyuge o pareja de hecho inscrita tiene discapacidad "
            ">= 33% y no tiene rentas anuales superiores a 8.000 EUR (excluidas "
            "las exentas). "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"discapacidad_conyuge": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_conyuge", "text": "Tu conyuge o pareja de hecho tiene discapacidad >= 33%?", "type": "bool"},
            {"key": "rentas_conyuge_max_8000", "text": "Las rentas anuales de tu conyuge son inferiores a 8.000 EUR?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 10. Asistencia a personas con discapacidad (Art. 18)
    # -------------------------------------------------------------------------
    {
        "code": "AND-DIS-003",
        "name": "Deduccion por asistencia a personas con discapacidad",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 100.0,
        "legal_reference": "Arts. 18, 3 y DA 2a Ley 5/2021 Andalucia",
        "description": (
            "100 EUR por cada persona con discapacidad que genere derecho al minimo "
            "por descendientes o ascendientes del IRPF. "
            "Incremento: 20% de las cotizaciones SS del empleado del hogar (max "
            "500 EUR) cuando la persona discapacitada necesite ayuda de terceros. "
            "BI general + ahorro <= 80.000 EUR individual / 100.000 EUR conjunta. "
            "Incompatible con la deduccion por ayuda domestica para el mismo empleado."
        ),
        "requirements_json": json.dumps({"persona_discapacitada_a_cargo": True}),
        "questions_json": json.dumps([
            {"key": "persona_discapacitada_a_cargo", "text": "Tienes personas con discapacidad a tu cargo (descendientes o ascendientes)?", "type": "bool"},
            {"key": "num_personas_discapacitadas", "text": "Cuantas personas con discapacidad tienes a tu cargo?", "type": "number"},
            {"key": "necesita_ayuda_terceros", "text": "Alguna necesita ayuda de terceros y tienes empleado del hogar para ello?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 11. Enfermedad celiaca (Art. 18 bis)
    # -------------------------------------------------------------------------
    {
        "code": "AND-SAL-001",
        "name": "Deduccion por gastos de enfermedad celiaca",
        "type": "deduccion",
        "category": "salud",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 18 bis Ley 5/2021 Andalucia",
        "description": (
            "300 EUR por cada contribuyente o descendiente que genere derecho al "
            "minimo por descendientes y que tenga diagnostico de enfermedad celiaca "
            "acreditado medicamente. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"enfermedad_celiaca": True}),
        "questions_json": json.dumps([
            {"key": "enfermedad_celiaca", "text": "Tu o alguno de tus hijos a cargo tiene diagnostico de enfermedad celiaca?", "type": "bool"},
            {"key": "num_celiacos", "text": "Cuantas personas celiacas hay en tu unidad familiar?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 12. Ayuda domestica (Art. 19)
    # -------------------------------------------------------------------------
    {
        "code": "AND-LAB-001",
        "name": "Deduccion por ayuda domestica",
        "type": "deduccion",
        "category": "trabajo",
        "percentage": 20.0,
        "max_amount": 500.0,
        "legal_reference": "Arts. 19 y 4 Ley 5/2021 Andalucia",
        "description": (
            "20% de las cotizaciones a la Seguridad Social del empleado del hogar, "
            "maximo 500 EUR. Requisitos: a) progenitor con hijos a cargo y ambos "
            "progenitores con rentas del trabajo/actividades economicas, o "
            "b) contribuyente de 75 o mas anos. "
            "El empleado debe estar dado de alta en el Sistema Especial de "
            "Empleados del Hogar de Andalucia. "
            "Incompatible con la deduccion por asistencia a discapacitados por "
            "el mismo empleado."
        ),
        "requirements_json": json.dumps({"empleada_hogar_cuidado": True}),
        "questions_json": json.dumps([
            {"key": "empleada_hogar_cuidado", "text": "Tienes contratada a una persona empleada del hogar?", "type": "bool"},
            {"key": "cotizaciones_ss_hogar", "text": "Cuanto pagas en cotizaciones SS del empleado del hogar al ano?", "type": "number"},
            {"key": "ambos_progenitores_trabajan", "text": "Ambos progenitores trabajan o tienen actividad economica?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 13. Inversion en acciones y participaciones de entidades nuevas (Art. 20)
    # -------------------------------------------------------------------------
    {
        "code": "AND-INV-001",
        "name": "Deduccion por inversion en acciones o participaciones de entidades de nueva creacion",
        "type": "deduccion",
        "category": "emprendimiento",
        "percentage": 20.0,
        "max_amount": 4000.0,
        "legal_reference": "Art. 20 Ley 5/2021 Andalucia",
        "description": (
            "20% de las cantidades invertidas en la suscripcion de acciones o "
            "participaciones de sociedades anonimas, limitadas, anonimas laborales "
            "o limitadas laborales, con domicilio social y fiscal en Andalucia. "
            "Maximo 4.000 EUR anuales. Participacion maxima 40%. "
            "Mantenimiento minimo 3 anos. La sociedad debe ser de nueva o reciente "
            "creacion (< 5 anos)."
        ),
        "requirements_json": json.dumps({"inversion_empresa_nueva": True}),
        "questions_json": json.dumps([
            {"key": "inversion_empresa_nueva", "text": "Has invertido en acciones o participaciones de una empresa nueva en Andalucia?", "type": "bool"},
            {"key": "importe_inversion", "text": "Cuanto has invertido?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 14. Defensa juridica de la relacion laboral (Art. 21)
    # -------------------------------------------------------------------------
    {
        "code": "AND-LAB-002",
        "name": "Deduccion por gastos de defensa juridica de la relacion laboral",
        "type": "deduccion",
        "category": "trabajo",
        "percentage": 10.0,
        "max_amount": 200.0,
        "legal_reference": "Art. 21 Ley 5/2021 Andalucia",
        "description": (
            "10% de los gastos satisfechos por la defensa juridica en procedimientos "
            "judiciales de la relacion laboral (despido, reclamacion de cantidad, "
            "etc.). Maximo 200 EUR. "
            "Solo gastos de abogado y procurador no cubiertos por justicia gratuita. "
            "BI general + ahorro <= 25.000 EUR individual / 30.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"gastos_defensa_laboral": True}),
        "questions_json": json.dumps([
            {"key": "gastos_defensa_laboral", "text": "Has tenido gastos de abogado por un procedimiento laboral?", "type": "bool"},
            {"key": "importe_defensa_laboral", "text": "Cuanto has gastado en defensa juridica laboral?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 15. Donativos con finalidad ecologica (Art. 22)
    # -------------------------------------------------------------------------
    {
        "code": "AND-DON-001",
        "name": "Deduccion por donativos con finalidad ecologica",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 10.0,
        "max_amount": 150.0,
        "legal_reference": "Art. 22 Ley 5/2021 Andalucia",
        "description": (
            "10% de las donaciones a entidades que tengan como fin la defensa y "
            "conservacion del medio ambiente y que esten reconocidas por la Junta "
            "de Andalucia. Maximo 150 EUR. "
            "Limite: 10% de la cuota integra autonomica."
        ),
        "requirements_json": json.dumps({"donativo_ecologico": True}),
        "questions_json": json.dumps([
            {"key": "donativo_ecologico", "text": "Has hecho donativos a entidades ecologicas reconocidas en Andalucia?", "type": "bool"},
            {"key": "importe_donativo_ecologico", "text": "Cuanto has donado?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 16. Fomento del ejercicio fisico y la practica deportiva (Art. 22 bis)
    # -------------------------------------------------------------------------
    {
        "code": "AND-SAL-002",
        "name": "Deduccion por fomento del ejercicio fisico y practica deportiva",
        "type": "deduccion",
        "category": "salud",
        "percentage": 5.0,
        "max_amount": 150.0,
        "legal_reference": "Art. 22 bis Ley 5/2021 Andalucia",
        "description": (
            "5% de los gastos satisfechos en cuotas de gimnasios, centros "
            "deportivos, actividades deportivas organizadas por federaciones, "
            "clubs o entidades deportivas. Maximo 150 EUR por contribuyente. "
            "BI general + ahorro <= 80.000 EUR individual / 100.000 EUR conjunta. "
            "Aplicable desde 01/01/2023."
        ),
        "requirements_json": json.dumps({"gastos_deporte": True}),
        "questions_json": json.dumps([
            {"key": "gastos_deporte", "text": "Has pagado cuotas de gimnasio o actividades deportivas?", "type": "bool"},
            {"key": "importe_gastos_deporte", "text": "Cuanto has gastado en total en actividades deportivas?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 17. Gastos veterinarios de animales de compania (Art. 22 ter)
    # -------------------------------------------------------------------------
    {
        "code": "AND-SAL-003",
        "name": "Deduccion por gastos veterinarios de animales de compania",
        "type": "deduccion",
        "category": "salud",
        "percentage": 10.0,
        "max_amount": 100.0,
        "legal_reference": "Art. 22 ter Ley 5/2021 Andalucia",
        "description": (
            "10% de los gastos veterinarios de animales de compania (perros, gatos "
            "y animales de asistencia). Maximo 100 EUR por contribuyente. "
            "Solo gastos de veterinario (consultas, vacunas, tratamientos). "
            "No incluye alimentacion, accesorios ni peluqueria. "
            "BI general + ahorro <= 80.000 EUR individual / 100.000 EUR conjunta. "
            "Aplicable desde 01/01/2023."
        ),
        "requirements_json": json.dumps({"gastos_veterinarios": True}),
        "questions_json": json.dumps([
            {"key": "gastos_veterinarios", "text": "Has tenido gastos veterinarios por animales de compania?", "type": "bool"},
            {"key": "importe_gastos_veterinarios", "text": "Cuanto has gastado en veterinario este ano?", "type": "number"},
        ]),
    },
]


# =============================================================================
# Validation
# =============================================================================
VALID_CATEGORIES: set[str] = {
    "familia", "vivienda", "educacion", "donativos", "emprendimiento",
    "trabajo", "discapacidad", "salud", "otros",
}


def validate_deductions(dry_run: bool = False) -> list[str]:
    """Validate all deductions and return a list of error messages."""
    errors: list[str] = []
    seen_codes: set[str] = set()

    for d in ANDALUCIA_2025:
        code: str = d.get("code", "??")

        if code in seen_codes:
            errors.append(f"DUPLICATE code: {code}")
        seen_codes.add(code)

        for field in ("code", "name", "type", "category", "description",
                      "legal_reference", "requirements_json", "questions_json"):
            if not d.get(field):
                errors.append(f"MISSING {field}: {code}")

        cat = d.get("category", "")
        if cat not in VALID_CATEGORIES:
            errors.append(f"INVALID category '{cat}': {code}")

        req = d.get("requirements_json")
        if req:
            try:
                parsed = json.loads(req)
                if not isinstance(parsed, dict):
                    errors.append(f"requirements_json not dict: {code}")
            except json.JSONDecodeError as exc:
                errors.append(f"requirements_json invalid JSON: {code} - {exc}")

        qs = d.get("questions_json")
        if qs:
            try:
                parsed_qs = json.loads(qs)
                if not isinstance(parsed_qs, list):
                    errors.append(f"questions_json not list: {code}")
                else:
                    for q in parsed_qs:
                        if "key" not in q:
                            errors.append(f"question missing 'key': {code}")
                        if "text" not in q:
                            errors.append(f"question missing 'text': {code}")
            except json.JSONDecodeError as exc:
                errors.append(f"questions_json invalid JSON: {code} - {exc}")

    if dry_run:
        print(f"\n=== DRY RUN — {TERRITORY} deducciones que se insertarian ===\n")
        print(f"  {TERRITORY} ({len(ANDALUCIA_2025)} deducciones):")
        for d in ANDALUCIA_2025:
            amt = ""
            if d.get("fixed_amount"):
                amt = f" [{d['fixed_amount']:.2f} EUR fijo]"
            elif d.get("percentage"):
                pct = d["percentage"]
                max_a = d.get("max_amount")
                amt = f" [{pct}%{f', max {max_a:.2f} EUR' if max_a else ''}]"
            print(f"    {d['code']}: {d['name']}{amt}")
        print(f"\nTotal: {len(ANDALUCIA_2025)} deducciones | Territorio: {TERRITORY}")

    return errors


# =============================================================================
# Seed function
# =============================================================================
async def seed_andalucia(dry_run: bool = False) -> None:
    """Delete existing Andalucia 2025 deductions and insert the full set of 17."""
    errors = validate_deductions(dry_run=dry_run)
    if errors:
        print("\n[VALIDATION ERRORS]")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} validation error(s) found. Aborting seed.")
        return

    if dry_run:
        print("\nDry run complete. No changes written to the database.")
        return

    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    print("Initializing schema...")
    await db.init_schema()
    print("Schema ready.\n")

    # Delete existing Andalucia deductions for this tax year (idempotent)
    result = await db.execute(
        "SELECT COUNT(*) as cnt FROM deductions WHERE territory = ? AND tax_year = ?",
        [TERRITORY, TAX_YEAR],
    )
    existing_count = result.rows[0]["cnt"] if result.rows else 0
    print(f"Existing {TERRITORY} deductions for {TAX_YEAR}: {existing_count}")

    if existing_count > 0:
        await db.execute(
            "DELETE FROM deductions WHERE territory = ? AND tax_year = ?",
            [TERRITORY, TAX_YEAR],
        )
        print(f"Deleted {existing_count} existing deductions.")

    # Insert all 17 deductions
    inserted = 0
    for d in ANDALUCIA_2025:
        deduction_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT INTO deductions
                   (id, code, tax_year, territory, name, type, category,
                    percentage, max_amount, fixed_amount, legal_reference,
                    description, requirements_json, questions_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    deduction_id,
                    d["code"],
                    TAX_YEAR,
                    TERRITORY,
                    d["name"],
                    d["type"],
                    d["category"],
                    d.get("percentage"),
                    d.get("max_amount"),
                    d.get("fixed_amount"),
                    d.get("legal_reference"),
                    d.get("description"),
                    d.get("requirements_json"),
                    d.get("questions_json"),
                ],
            )
            inserted += 1
        except Exception as exc:
            print(f"  Error inserting {d['code']}: {exc}")

    await db.disconnect()

    print(f"\n{TERRITORY} seed complete: {inserted}/{len(ANDALUCIA_2025)} inserted")
    print(f"Deductions: {', '.join(d['code'] for d in ANDALUCIA_2025)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Seed ALL {len(ANDALUCIA_2025)} {TERRITORY} IRPF deductions for {TAX_YEAR}"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted without writing to the database",
    )
    args = parser.parse_args()
    asyncio.run(seed_andalucia(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
