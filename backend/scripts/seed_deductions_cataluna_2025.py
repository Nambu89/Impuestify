"""
Seed ALL 13 official Cataluna autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunitat Autonoma de Catalunya
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-cataluna.html

Legal basis: Ley 31/2002, de 30 de diciembre, de medidas fiscales y administrativas
(modificada por leyes de acompanamiento presupuestario sucesivas).

Idempotent: DELETE existing Cataluna deductions for tax_year=2025, then INSERT all 13.

Usage:
    cd backend
    python scripts/seed_deductions_cataluna_2025.py
    python scripts/seed_deductions_cataluna_2025.py --dry-run
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

TERRITORY = "Cataluna"
TAX_YEAR = 2025

# Common income limits
LIMITES_CATALUNA_30_50 = {"individual": 30000, "conjunta": 50000}


# =============================================================================
# ALL 13 CATALUNA DEDUCTIONS — IRPF 2025
# =============================================================================

CATALUNA_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion de un hijo
    # =========================================================================
    {
        "code": "CAT-FAM-001",
        "name": "Por nacimiento o adopcion de un hijo",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por nacimiento o adopcion de un hijo durante el periodo impositivo.",
            "limites_renta": LIMITES_CATALUNA_30_50,
            "condiciones": [
                "Nacimiento o adopcion durante el periodo impositivo",
                "Residencia habitual en Cataluna",
                "Base imponible general + ahorro <= 30.000 EUR (individual) o 50.000 EUR (conjunta)",
                "En tributacion conjunta: deduccion unica de 300 EUR",
                "En individuales: deduccion a partes iguales (150 EUR cada progenitor)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_hijo_cataluna", "label": "Ha tenido o adoptado un hijo en Cataluna?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.1 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 2. Por alquiler de la vivienda habitual
    # =========================================================================
    {
        "code": "CAT-VIV-001",
        "name": "Por alquiler de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades satisfechas por alquiler de la vivienda habitual. Max 300 EUR (600 EUR para familias numerosas).",
            "limites_renta": {"individual": 20000, "conjunta": 30000},
            "condiciones": [
                "Contrato de arrendamiento de vivienda habitual en Cataluna",
                "Edad del contribuyente <= 32 anos, o en paro > 183 dias, o discapacidad >= 65%, o viudo/a >= 65 anos",
                "Base imponible general + ahorro <= 20.000 EUR (individual) o 30.000 EUR (conjunta)",
                "Max 300 EUR (600 EUR si familia numerosa)",
                "Incompatible con deduccion estatal por alquiler",
                "Las cantidades pagadas deben superar el 10% de la renta neta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_cataluna", "label": "Alquila su vivienda habitual en Cataluna?", "type": "boolean"},
            {"key": "importe_alquiler_cataluna", "label": "Importe anual del alquiler", "type": "number"},
            {"key": "cumple_requisitos_alquiler_cat", "label": "Cumple alguno: menor 32 anos, parado > 183 dias, discapacidad >= 65%, viudo/a >= 65?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.2 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 3. Por rehabilitacion de la vivienda habitual
    # =========================================================================
    {
        "code": "CAT-VIV-002",
        "name": "Por rehabilitacion de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 1.5,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "1,5% de las cantidades satisfechas en la rehabilitacion de la vivienda habitual.",
            "limites_renta": {},
            "condiciones": [
                "Obras de rehabilitacion de la vivienda habitual en Cataluna",
                "Calificadas como actuacion protegida segun Plan de Vivienda",
                "Conservar facturas y licencia de obras",
                "La deduccion se aplica sobre las cantidades invertidas en rehabilitacion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "rehabilitacion_vivienda_cataluna", "label": "Ha realizado obras de rehabilitacion de su vivienda habitual en Cataluna?", "type": "boolean"},
            {"key": "importe_rehabilitacion_cataluna", "label": "Importe de las obras de rehabilitacion", "type": "number"}
        ]),
        "legal_reference": "Art. 1.3 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 4. Por donativos a entidades que fomentan el uso de la lengua catalana
    # =========================================================================
    {
        "code": "CAT-DON-001",
        "name": "Por donativos a entidades que fomentan el uso de la lengua catalana",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a entidades que fomenten el uso de la lengua catalana o del occitano (aranense).",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias a entidades que tengan como finalidad el fomento de la lengua catalana",
                "Incluye lengua occitana (aranense)",
                "Entidades sin animo de lucro con sede en Cataluna",
                "Requiere certificacion de la entidad receptora",
                "Limite: 10% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_lengua_catalana", "label": "Ha donado a entidades de fomento de la lengua catalana?", "type": "boolean"},
            {"key": "importe_donativo_lengua_cat", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 1.4 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 5. Por donativos a entidades de fomento de la investigacion cientifica y el desarrollo
    # =========================================================================
    {
        "code": "CAT-DON-002",
        "name": "Por donativos a entidades de investigacion cientifica y desarrollo",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de las donaciones a centros de investigacion adscritos a universidades catalanas y a fundaciones o asociaciones de investigacion.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias a centros de investigacion de universidades catalanas",
                "O a fundaciones/asociaciones inscritas con finalidad de fomento I+D+i",
                "Requiere certificacion de la entidad receptora",
                "Limite: 10% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_investigacion_cataluna", "label": "Ha donado a entidades de investigacion o I+D en Cataluna?", "type": "boolean"},
            {"key": "importe_donativo_investigacion_cat", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 1.5 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 6. Por donativos a entidades de fomento del medio ambiente
    # =========================================================================
    {
        "code": "CAT-DON-003",
        "name": "Por donativos a entidades medioambientales",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a entidades que tengan como finalidad la defensa del medio ambiente en Cataluna.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias a entidades con finalidad medioambiental",
                "Entidades sin animo de lucro con sede social en Cataluna",
                "Que tengan como objeto social la defensa del medio ambiente",
                "Requiere certificacion de la entidad receptora",
                "Limite: 5% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_medioambiente_cataluna", "label": "Ha donado a entidades medioambientales en Cataluna?", "type": "boolean"},
            {"key": "importe_donativo_medioambiente_cat", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 1.6 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 7. Por donativos a fundaciones y asociaciones culturales, asistenciales, educativas y sanitarias
    # =========================================================================
    {
        "code": "CAT-DON-004",
        "name": "Por donativos a fundaciones y asociaciones culturales y asistenciales",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a fundaciones y asociaciones inscritas que persigan fines culturales, asistenciales, educativos o sanitarios.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras, simples e irrevocables",
                "Fundaciones o asociaciones declaradas de utilidad publica",
                "Inscritas en los registros correspondientes de la Generalitat",
                "Fines: culturales, asistenciales, educativos, sanitarios",
                "Requiere certificacion de la entidad receptora",
                "Limite: 10% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_fundaciones_cataluna", "label": "Ha donado a fundaciones o asociaciones culturales/asistenciales en Cataluna?", "type": "boolean"},
            {"key": "importe_donativo_fundaciones_cat", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 1.7 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 8. Por inversiones en acciones de entidades del Mercado Alternativo Bursatil (MAB)
    # =========================================================================
    {
        "code": "CAT-INV-001",
        "name": "Por inversiones en entidades cotizadas en el mercado alternativo bursatil",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 10000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en la adquisicion de acciones de entidades cotizadas en el segmento de empresas en expansion del Mercado Alternativo Bursatil (BME Growth). Max 10.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Acciones adquiridas en el mercado alternativo bursatil (BME Growth / segmento empresas en expansion)",
                "La entidad debe tener domicilio social y fiscal en Cataluna",
                "Participacion contribuyente + familiares <= 10% del capital",
                "Mantenimiento de las acciones al menos 2 anos",
                "Max 10.000 EUR de base de deduccion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_mab_cataluna", "label": "Ha invertido en entidades del Mercado Alternativo Bursatil con sede en Cataluna?", "type": "boolean"},
            {"key": "importe_inversion_mab_cataluna", "label": "Importe total invertido en acciones MAB/BME Growth", "type": "number"}
        ]),
        "legal_reference": "Art. 1.8 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 9. Por discapacidad del contribuyente
    # =========================================================================
    {
        "code": "CAT-DIS-001",
        "name": "Por discapacidad del contribuyente o de familiares a cargo",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR si el contribuyente tiene discapacidad >= 33% y < 65%. 600 EUR si >= 65%. Tambien aplicable por conyuge o descendientes discapacitados a cargo.",
            "limites_renta": LIMITES_CATALUNA_30_50,
            "condiciones": [
                "Grado de discapacidad reconocido >= 33%",
                "300 EUR si grado >= 33% y < 65%",
                "600 EUR si grado >= 65%",
                "Tambien por conyuge o descendientes con discapacidad que dependan del contribuyente",
                "Rentas de la persona discapacitada <= 8.000 EUR anuales (excluido contribuyente)",
                "Residencia habitual en Cataluna"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_contribuyente_cataluna", "label": "Tiene usted o algun familiar a cargo discapacidad >= 33%?", "type": "boolean"},
            {"key": "grado_discapacidad_cataluna", "label": "Grado de discapacidad (%)", "type": "number"},
            {"key": "persona_discapacitada_cataluna", "label": "Quien tiene la discapacidad?", "type": "select", "options": ["contribuyente", "conyuge", "descendiente"]}
        ]),
        "legal_reference": "Art. 1.9 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 10. Por intereses de prestamos para estudios de master y doctorado
    # =========================================================================
    {
        "code": "CAT-EDU-001",
        "name": "Por intereses de prestamos para estudios de master y doctorado",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion del 100% de los intereses pagados por prestamos destinados a financiar estudios de master y doctorado.",
            "limites_renta": LIMITES_CATALUNA_30_50,
            "condiciones": [
                "Intereses satisfechos de prestamos concedidos a traves de la AGAUR",
                "O prestamos para financiacion de master y doctorado",
                "Estudios en universidades catalanas o del Espacio Europeo de Educacion Superior",
                "Base de deduccion: intereses efectivamente pagados en el periodo",
                "Conservar certificado bancario de intereses pagados"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "prestamo_estudios_cataluna", "label": "Ha pagado intereses de prestamos para master o doctorado?", "type": "boolean"},
            {"key": "importe_intereses_estudios_cat", "label": "Importe de intereses pagados", "type": "number"}
        ]),
        "legal_reference": "Art. 1.10 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 11. Por contribuyentes que queden viudos/as
    # =========================================================================
    {
        "code": "CAT-FAM-002",
        "name": "Por contribuyentes que queden viudos/as",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": None,
        "fixed_amount": 150.0,
        "requirements": json.dumps({
            "descripcion": "150 EUR para contribuyentes que hayan quedado viudos/as y tengan hijos dependientes.",
            "limites_renta": LIMITES_CATALUNA_30_50,
            "condiciones": [
                "Contribuyente que haya enviudado",
                "Con hijos que formen parte de la unidad familiar",
                "Hijos que generen derecho al minimo por descendientes",
                "Residencia habitual en Cataluna"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "viudedad_cataluna", "label": "Ha enviudado y tiene hijos a cargo?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.11 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 12. Por inversion en acciones de entidades de nueva o reciente creacion
    # =========================================================================
    {
        "code": "CAT-EMP-001",
        "name": "Por inversion en entidades de nueva o reciente creacion",
        "category": "emprendimiento",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 6000.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades invertidas en acciones o participaciones de entidades de nueva o reciente creacion con sede en Cataluna. Max 6.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Entidad constituida en los 3 anos anteriores a la inversion",
                "Domicilio social y fiscal en Cataluna",
                "Actividad economica con al menos 1 persona empleada con contrato laboral",
                "Capital social de la entidad <= 200.000 EUR en el momento de la inversion",
                "Participacion del contribuyente + familiares <= 35% del capital",
                "Mantenimiento de la inversion al menos 3 anos",
                "Max 6.000 EUR de base de deduccion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_startups_cataluna", "label": "Ha invertido en entidades de nueva creacion en Cataluna?", "type": "boolean"},
            {"key": "importe_inversion_startups_cat", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 1.12 Ley 31/2002 Catalunya"
    },

    # =========================================================================
    # 13. Por donaciones a determinadas entidades en beneficio del medio ambiente, la conservacion del patrimonio natural y de la custodia del territorio
    # =========================================================================
    {
        "code": "CAT-DON-005",
        "name": "Por donaciones para conservacion del patrimonio natural y custodia del territorio",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a entidades de custodia del territorio y conservacion del patrimonio natural catalan.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias a entidades de custodia del territorio",
                "Entidades inscritas en el Registro de entidades de custodia del territorio de Cataluna",
                "O donaciones para la conservacion del patrimonio natural catalan",
                "Requiere certificacion de la entidad receptora",
                "Limite: 5% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_custodia_territorio_cat", "label": "Ha donado a entidades de custodia del territorio o conservacion del patrimonio natural catalan?", "type": "boolean"},
            {"key": "importe_donativo_custodia_cat", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 1.13 Ley 31/2002 Catalunya"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_cataluna(dry_run: bool = False):
    """Delete existing Cataluna 2025 deductions and insert all 13."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(CATALUNA_2025)} Cataluna deductions for IRPF {TAX_YEAR}")
    print("=" * 70)

    if not dry_run:
        from app.database.turso_client import TursoClient
        db = TursoClient()
        await db.connect()
        print("Connected to database.\n")

        for col_name in ("ccaa", "territory"):
            try:
                result = await db.execute(
                    f"DELETE FROM deductions WHERE {col_name} = ? AND tax_year = ?",
                    [TERRITORY, TAX_YEAR],
                )
                if hasattr(result, "rows_affected") and result.rows_affected:
                    print(f"  Deleted {result.rows_affected} existing Cataluna deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(CATALUNA_2025, 1):
        code = d["code"]
        name = d["name"]
        category = d["category"]

        if dry_run:
            fa = d.get("fixed_amount")
            pct = d.get("percentage")
            mx = d.get("max_amount")
            amount_str = ""
            if fa:
                amount_str = f"{fa} EUR fijo"
            elif pct:
                amount_str = f"{pct}%"
                if mx:
                    amount_str += f" (max {mx} EUR)"
            else:
                amount_str = "variable"
            print(f"  {i:2d}. [{code}] {name}")
            print(f"      Categoria: {category} | Importe: {amount_str}")
            print(f"      Ref: {d.get('legal_reference', 'N/A')}")
            print()
            inserted += 1
            continue

        deduction_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT INTO deductions
                   (id, code, name, category, scope, ccaa,
                    max_amount, percentage, tax_year, is_active,
                    requirements, questions, legal_reference)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    deduction_id,
                    code,
                    name,
                    category,
                    d["scope"],
                    d["ccaa"],
                    d.get("max_amount"),
                    d.get("percentage"),
                    d["tax_year"],
                    1 if d.get("is_active", True) else 0,
                    d.get("requirements"),
                    d.get("questions"),
                    d.get("legal_reference"),
                ],
            )
            inserted += 1
            print(f"  {i:2d}. [OK] {code} — {name}")
        except Exception as e:
            try:
                deduction_id = str(uuid.uuid4())
                await db.execute(
                    """INSERT INTO deductions
                       (id, code, tax_year, territory, name, type, category,
                        percentage, max_amount, fixed_amount, legal_reference,
                        description, requirements_json, questions_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        deduction_id,
                        code,
                        d["tax_year"],
                        d["ccaa"],
                        name,
                        "deduccion",
                        category,
                        d.get("percentage"),
                        d.get("max_amount"),
                        d.get("fixed_amount"),
                        d.get("legal_reference"),
                        json.loads(d.get("requirements", "{}")).get("descripcion", ""),
                        d.get("requirements"),
                        d.get("questions"),
                    ],
                )
                inserted += 1
                print(f"  {i:2d}. [OK-fallback] {code} — {name}")
            except Exception as e2:
                print(f"  {i:2d}. [ERROR] {code} — {e2}")

    print()
    print("=" * 70)
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(CATALUNA_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in CATALUNA_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 13 Cataluna IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_cataluna(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
