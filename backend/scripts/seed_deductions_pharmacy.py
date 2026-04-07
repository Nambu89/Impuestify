"""
Seed pharmacy-specific IRPF deductions into the deductions table.

6 deductions for IAE 652.1 (Farmacias), territory='Estatal'.
Idempotent: DELETE existing pharmacy deductions (code LIKE 'FARM-%'), then INSERT all 6.

Usage:
    cd backend
    python scripts/seed_deductions_pharmacy.py
    python scripts/seed_deductions_pharmacy.py --dry-run
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

TAX_YEAR = 2025

# Schema matches production: id, code, tax_year, territory, name, type, category,
# percentage, max_amount, fixed_amount, legal_reference, description,
# requirements_json, questions_json, is_active
PHARMACY_DEDUCTIONS = [
    {
        "code": "FARM-01",
        "name": "Cuota Colegio de Farmaceuticos",
        "type": "deduccion",
        "category": "profesional",
        "territory": "Estatal",
        "max_amount": None,
        "fixed_amount": None,
        "percentage": 100.0,
        "description": "Cuota colegial obligatoria para el ejercicio de la profesion farmaceutica (IAE 652.1)",
        "requirements_json": json.dumps({
            "situacion_laboral": "farmaceutico",
            "iae": "652.1",
        }),
        "questions_json": json.dumps([
            {"key": "es_farmaceutico_colegiado", "text": "Estas colegiado en un Colegio Oficial de Farmaceuticos?", "type": "boolean"},
        ]),
        "legal_reference": "Art. 28.1 LIRPF - gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-02",
        "name": "Seguro de Responsabilidad Civil profesional",
        "type": "deduccion",
        "category": "profesional",
        "territory": "Estatal",
        "max_amount": None,
        "fixed_amount": None,
        "percentage": 100.0,
        "description": "Seguro RC obligatorio para el ejercicio de la actividad farmaceutica",
        "requirements_json": json.dumps({
            "situacion_laboral": "farmaceutico",
            "iae": "652.1",
        }),
        "questions_json": json.dumps([
            {"key": "tiene_seguro_rc", "text": "Tienes contratado un seguro de responsabilidad civil profesional?", "type": "boolean"},
        ]),
        "legal_reference": "Art. 28.1 LIRPF - gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-03",
        "name": "Formacion continua farmaceutica",
        "type": "deduccion",
        "category": "formacion",
        "territory": "Estatal",
        "max_amount": None,
        "fixed_amount": None,
        "percentage": 100.0,
        "description": "Cursos, congresos y formacion continua relacionada con la actividad farmaceutica",
        "requirements_json": json.dumps({
            "situacion_laboral": "farmaceutico",
            "iae": "652.1",
        }),
        "questions_json": json.dumps([
            {"key": "gastos_formacion", "text": "Has realizado gastos en formacion continua relacionada con la farmacia?", "type": "boolean"},
        ]),
        "legal_reference": "Art. 28.1 LIRPF - gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-04",
        "name": "Amortizacion fondo de comercio (compra farmacia)",
        "type": "deduccion",
        "category": "amortizacion",
        "territory": "Estatal",
        "max_amount": None,
        "fixed_amount": None,
        "percentage": 5.0,
        "description": "Amortizacion del fondo de comercio adquirido en la compra de la farmacia. Maximo 5% anual (20 anos)",
        "requirements_json": json.dumps({
            "situacion_laboral": "farmaceutico",
            "iae": "652.1",
            "tiene_fondo_comercio": True,
        }),
        "questions_json": json.dumps([
            {"key": "compro_farmacia", "text": "Adquiriste la farmacia mediante compra (con fondo de comercio)?", "type": "boolean"},
            {"key": "importe_fondo_comercio", "text": "Importe del fondo de comercio de la compra", "type": "number"},
        ]),
        "legal_reference": "Art. 12.6 LIS (aplicable via art. 28 LIRPF) - amortizacion fondo de comercio",
    },
    {
        "code": "FARM-05",
        "name": "Local comercial (alquiler o amortizacion)",
        "type": "deduccion",
        "category": "local",
        "territory": "Estatal",
        "max_amount": None,
        "fixed_amount": None,
        "percentage": 100.0,
        "description": "Alquiler del local o amortizacion si es en propiedad. Proporcional al uso afecto a la actividad",
        "requirements_json": json.dumps({
            "situacion_laboral": "farmaceutico",
            "iae": "652.1",
        }),
        "questions_json": json.dumps([
            {"key": "tipo_local", "text": "El local de la farmacia es alquilado o en propiedad?", "type": "select", "options": ["alquilado", "propiedad"]},
        ]),
        "legal_reference": "Art. 28.1 LIRPF - gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-06",
        "name": "Vehiculo (reparto domiciliario)",
        "type": "deduccion",
        "category": "vehiculo",
        "territory": "Estatal",
        "max_amount": None,
        "fixed_amount": None,
        "percentage": 50.0,
        "description": "Gastos de vehiculo utilizado para reparto domiciliario. Presuncion del 50% de afectacion a la actividad",
        "requirements_json": json.dumps({
            "situacion_laboral": "farmaceutico",
            "iae": "652.1",
            "reparto_domiciliario": True,
        }),
        "questions_json": json.dumps([
            {"key": "hace_reparto", "text": "Realizas reparto domiciliario de medicamentos?", "type": "boolean"},
        ]),
        "legal_reference": "Art. 22.4 RIRPF - presuncion de afectacion parcial de vehiculos",
    },
]


async def seed(dry_run: bool = False):
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()
    await db.init_schema()

    # Delete existing pharmacy deductions (idempotent)
    if not dry_run:
        await db.execute(
            "DELETE FROM deductions WHERE code LIKE 'FARM-%'",
            [],
        )
        print("Deleted existing FARM-% deductions")

    inserted = 0
    for d in PHARMACY_DEDUCTIONS:
        row_id = str(uuid.uuid4())
        if dry_run:
            print(f"  [DRY-RUN] Would insert: {d['code']} - {d['name']}")
        else:
            await db.execute(
                """INSERT INTO deductions
                   (id, code, tax_year, territory, name, type, category,
                    percentage, max_amount, fixed_amount, legal_reference,
                    description, requirements_json, questions_json, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    row_id,
                    d["code"],
                    TAX_YEAR,
                    d["territory"],
                    d["name"],
                    d["type"],
                    d["category"],
                    d["percentage"],
                    d["max_amount"],
                    d["fixed_amount"],
                    d["legal_reference"],
                    d["description"],
                    d["requirements_json"],
                    d["questions_json"],
                    1,
                ],
            )
            print(f"  Inserted: {d['code']} - {d['name']}")
        inserted += 1

    print(f"\nTotal: {inserted} pharmacy deductions {'would be ' if dry_run else ''}seeded.")

    await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed pharmacy deductions")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run))
