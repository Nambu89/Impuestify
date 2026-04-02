"""
Seed pharmacy-specific IRPF deductions into the deductions table.

6 deductions with scope='sectorial', territory='Estatal'.
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

PHARMACY_DEDUCTIONS = [
    {
        "code": "FARM-01",
        "name": "Cuota Colegio de Farmaceuticos",
        "category": "profesional",
        "scope": "sectorial",
        "ccaa": None,
        "max_amount": None,
        "percentage": 100.0,
        "requirements": json.dumps({
            "situacion_laboral": "farmaceutico",
            "description": "Cuota colegial obligatoria para el ejercicio de la profesion farmaceutica",
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "legal_reference": "Art. 28.1 LIRPF — gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-02",
        "name": "Seguro de Responsabilidad Civil profesional",
        "category": "profesional",
        "scope": "sectorial",
        "ccaa": None,
        "max_amount": None,
        "percentage": 100.0,
        "requirements": json.dumps({
            "situacion_laboral": "farmaceutico",
            "description": "Seguro RC obligatorio para farmacias",
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "legal_reference": "Art. 28.1 LIRPF — gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-03",
        "name": "Formacion continua farmaceutica",
        "category": "formacion",
        "scope": "sectorial",
        "ccaa": None,
        "max_amount": None,
        "percentage": 100.0,
        "requirements": json.dumps({
            "situacion_laboral": "farmaceutico",
            "description": "Cursos, congresos y formacion continua relacionada con la actividad farmaceutica",
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "legal_reference": "Art. 28.1 LIRPF — gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-04",
        "name": "Amortizacion fondo de comercio (compra farmacia)",
        "category": "amortizacion",
        "scope": "sectorial",
        "ccaa": None,
        "max_amount": None,
        "percentage": 5.0,
        "requirements": json.dumps({
            "situacion_laboral": "farmaceutico",
            "description": "Amortizacion del fondo de comercio adquirido en la compra de la farmacia. "
                           "Maximo 5% anual (20 anos)",
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "legal_reference": "Art. 12.6 LIS (aplicable via art. 28 LIRPF) — amortizacion fondo de comercio",
    },
    {
        "code": "FARM-05",
        "name": "Local comercial (alquiler o amortizacion)",
        "category": "local",
        "scope": "sectorial",
        "ccaa": None,
        "max_amount": None,
        "percentage": 100.0,
        "requirements": json.dumps({
            "situacion_laboral": "farmaceutico",
            "description": "Alquiler del local o amortizacion si es en propiedad. Proporcional al uso afecto",
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "legal_reference": "Art. 28.1 LIRPF — gastos deducibles de rendimientos de actividades economicas",
    },
    {
        "code": "FARM-06",
        "name": "Vehiculo (reparto domiciliario)",
        "category": "vehiculo",
        "scope": "sectorial",
        "ccaa": None,
        "max_amount": None,
        "percentage": 50.0,
        "requirements": json.dumps({
            "situacion_laboral": "farmaceutico",
            "description": "Gastos de vehiculo utilizado para reparto domiciliario. "
                           "Presuncion del 50% de afectacion a la actividad",
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "legal_reference": "Art. 22.4 RIRPF — presuncion de afectacion parcial de vehiculos",
    },
]


async def seed(dry_run: bool = False):
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.initialize()

    # Delete existing pharmacy deductions
    if not dry_run:
        await db.execute(
            "DELETE FROM deductions WHERE code LIKE 'FARM-%'",
            [],
        )
        print(f"Deleted existing FARM-% deductions")

    inserted = 0
    for d in PHARMACY_DEDUCTIONS:
        row_id = str(uuid.uuid4())
        if dry_run:
            print(f"  [DRY-RUN] Would insert: {d['code']} — {d['name']}")
        else:
            await db.execute(
                """INSERT INTO deductions
                   (id, code, name, category, scope, ccaa, max_amount, percentage,
                    requirements, tax_year, is_active, legal_reference)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    row_id,
                    d["code"],
                    d["name"],
                    d["category"],
                    d["scope"],
                    d["ccaa"],
                    d["max_amount"],
                    d["percentage"],
                    d["requirements"],
                    d["tax_year"],
                    1 if d["is_active"] else 0,
                    d["legal_reference"],
                ],
            )
            print(f"  Inserted: {d['code']} — {d['name']}")
        inserted += 1

    print(f"\nTotal: {inserted} pharmacy deductions {'would be ' if dry_run else ''}seeded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed pharmacy deductions")
    parser.add_argument("--dry-run", action="store_true", help="Preview without inserting")
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run))
