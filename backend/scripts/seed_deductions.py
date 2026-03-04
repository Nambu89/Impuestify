"""
Seed script for IRPF deductions registry.

Inserts the 16 main state-level IRPF deductions for 2025.
Idempotent: uses INSERT OR IGNORE so it can be run multiple times safely.

Usage:
    cd backend
    python scripts/seed_deductions.py
"""
import asyncio
import json
import os
import sys
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


DEDUCTIONS_2025 = [
    {
        "code": "EST-VIV-HAB",
        "name": "Deducción por inversión en vivienda habitual (régimen transitorio)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 9040.0,
        "legal_reference": "DT 18ª LIRPF",
        "description": "Para contribuyentes que adquirieron su vivienda habitual antes del 1/1/2013 y venían deduciendo.",
        "requirements_json": json.dumps({
            "adquisicion_antes_2013": True,
            "deducia_antes_2013": True,
            "vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_antes_2013", "text": "¿Compraste tu vivienda habitual antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "deducia_antes_2013", "text": "¿Venías aplicando la deducción por vivienda en declaraciones anteriores a 2013?", "type": "bool"},
            {"key": "importe_inversion", "text": "¿Cuánto has pagado este año en hipoteca (capital + intereses + seguros vinculados)?", "type": "number"},
        ]),
    },
    {
        "code": "EST-DONAT-GEN",
        "name": "Deducción por donativos a entidades sin ánimo de lucro",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 80.0,
        "max_amount": 250.0,
        "legal_reference": "Art. 68.3 LIRPF + Ley 49/2002",
        "description": "80% sobre los primeros 250€ donados. El exceso al 40% (o 45% si es recurrente 3+ años).",
        "requirements_json": json.dumps({
            "donativo_a_entidad_acogida": True,
        }),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has hecho donativos a ONGs, fundaciones o entidades acogidas a la Ley 49/2002?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total este año?", "type": "number"},
            {"key": "donativo_recurrente", "text": "¿Llevas donando a la misma entidad al menos 3 años consecutivos?", "type": "bool"},
        ]),
    },
    {
        "code": "EST-DONAT-EXC",
        "name": "Deducción por donativos (exceso sobre 250€)",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 40.0,
        "max_amount": None,
        "legal_reference": "Art. 68.3 LIRPF + Ley 49/2002",
        "description": "40% sobre el importe que exceda de 250€ (45% si es recurrente 3+ años a la misma entidad).",
        "requirements_json": json.dumps({
            "donativo_a_entidad_acogida": True,
            "importe_superior_250": True,
        }),
        "questions_json": json.dumps([
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total este año?", "type": "number"},
        ]),
    },
    {
        "code": "EST-MAT-GUARD",
        "name": "Deducción por maternidad (guardería 0-3 años)",
        "type": "deduccion",
        "category": "familia",
        "percentage": None,
        "max_amount": 1000.0,
        "fixed_amount": 1000.0,
        "legal_reference": "Art. 81 LIRPF",
        "description": "Hasta 1.000€ adicionales por gastos de guardería o centro de educación infantil autorizado para hijos menores de 3 años.",
        "requirements_json": json.dumps({
            "madre_trabajadora": True,
            "hijo_menor_3": True,
            "guarderia_autorizada": True,
        }),
        "questions_json": json.dumps([
            {"key": "madre_trabajadora", "text": "¿La madre trabaja por cuenta ajena o propia y está dada de alta en la SS?", "type": "bool"},
            {"key": "hijo_menor_3", "text": "¿Tienes hijos menores de 3 años?", "type": "bool"},
            {"key": "guarderia_autorizada", "text": "¿Están en una guardería o centro de educación infantil autorizado?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "¿Cuánto has pagado de guardería este año?", "type": "number"},
        ]),
    },
    {
        "code": "EST-MAT-1200",
        "name": "Deducción por maternidad (madres trabajadoras)",
        "type": "deduccion",
        "category": "familia",
        "percentage": None,
        "max_amount": 1200.0,
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 81 LIRPF",
        "description": "1.200€ anuales (100€/mes) por cada hijo menor de 3 años para madres trabajadoras dadas de alta en SS/mutualidad.",
        "requirements_json": json.dumps({
            "madre_trabajadora": True,
            "hijo_menor_3": True,
        }),
        "questions_json": json.dumps([
            {"key": "madre_trabajadora", "text": "¿La madre trabaja y cotiza a la Seguridad Social o mutualidad?", "type": "bool"},
            {"key": "num_hijos_menor_3", "text": "¿Cuántos hijos menores de 3 años tienes?", "type": "number"},
        ]),
    },
    {
        "code": "EST-FAM-DISC",
        "name": "Deducción por descendiente con discapacidad",
        "type": "deduccion",
        "category": "familia",
        "percentage": None,
        "max_amount": 1200.0,
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 81 bis LIRPF",
        "description": "1.200€ anuales por cada descendiente con discapacidad que dé derecho al MPYF.",
        "requirements_json": json.dumps({
            "descendiente_discapacidad": True,
            "alta_ss": True,
        }),
        "questions_json": json.dumps([
            {"key": "descendiente_discapacidad", "text": "¿Tienes hijos o descendientes con discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "num_descendientes_disc", "text": "¿Cuántos descendientes con discapacidad tienes?", "type": "number"},
        ]),
    },
    {
        "code": "EST-FAM-ASC-DISC",
        "name": "Deducción por ascendiente con discapacidad",
        "type": "deduccion",
        "category": "familia",
        "percentage": None,
        "max_amount": 1200.0,
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 81 bis LIRPF",
        "description": "1.200€ anuales por cada ascendiente con discapacidad que dé derecho al MPYF.",
        "requirements_json": json.dumps({
            "ascendiente_discapacidad": True,
            "alta_ss": True,
        }),
        "questions_json": json.dumps([
            {"key": "ascendiente_discapacidad", "text": "¿Tienes padres o abuelos a tu cargo con discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "num_ascendientes_disc", "text": "¿Cuántos ascendientes con discapacidad tienes a tu cargo?", "type": "number"},
        ]),
    },
    {
        "code": "EST-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "percentage": None,
        "max_amount": 2400.0,
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 81 bis LIRPF",
        "description": "1.200€ por familia numerosa general, 2.400€ por especial. +600€ por cada hijo a partir del 4º.",
        "requirements_json": json.dumps({
            "familia_numerosa": True,
            "alta_ss": True,
        }),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es familia numerosa de categoría especial (5+ hijos)?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos en total?", "type": "number"},
        ]),
    },
    {
        "code": "EST-FAM-MONO",
        "name": "Deducción por familia monoparental con 2+ hijos",
        "type": "deduccion",
        "category": "familia",
        "percentage": None,
        "max_amount": 1200.0,
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 81 bis LIRPF",
        "description": "1.200€ anuales para familias monoparentales con dos o más hijos sin derecho a pensión alimenticia.",
        "requirements_json": json.dumps({
            "familia_monoparental": True,
            "dos_o_mas_hijos": True,
            "alta_ss": True,
        }),
        "questions_json": json.dumps([
            {"key": "familia_monoparental", "text": "¿Eres familia monoparental (un solo progenitor)?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes?", "type": "number"},
        ]),
    },
    {
        "code": "EST-PLAN-PENS",
        "name": "Reducción por aportaciones a planes de pensiones",
        "type": "reduccion",
        "category": "prevision_social",
        "percentage": None,
        "max_amount": 1500.0,
        "legal_reference": "Art. 51-52 LIRPF",
        "description": "Reducción de hasta 1.500€/año por aportaciones individuales a planes de pensiones (hasta 8.500€ si incluye aportaciones de empresa).",
        "requirements_json": json.dumps({
            "aportaciones_planes_pensiones": True,
        }),
        "questions_json": json.dumps([
            {"key": "aportaciones_planes_pensiones", "text": "¿Has aportado dinero a un plan de pensiones este año?", "type": "bool"},
            {"key": "importe_aportacion_individual", "text": "¿Cuánto has aportado tú personalmente?", "type": "number"},
            {"key": "aportacion_empresa", "text": "¿Tu empresa también aporta a tu plan de pensiones? ¿Cuánto?", "type": "number"},
        ]),
    },
    {
        "code": "EST-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual (régimen transitorio)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.05,
        "max_amount": 9040.0,
        "legal_reference": "DT 18ª.2 LIRPF",
        "description": "10,05% sobre el alquiler pagado (máx. base 9.040€) para contratos anteriores a 1/1/2015 y base imponible < 24.107,20€.",
        "requirements_json": json.dumps({
            "contrato_antes_2015": True,
            "base_imponible_inferior_24107": True,
        }),
        "questions_json": json.dumps([
            {"key": "contrato_antes_2015", "text": "¿Tu contrato de alquiler es anterior al 1 de enero de 2015?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
        ]),
    },
    {
        "code": "EST-ACT-ECON",
        "name": "Incentivos fiscales actividades económicas (autónomos)",
        "type": "deduccion",
        "category": "actividad_economica",
        "percentage": None,
        "max_amount": None,
        "legal_reference": "Art. 68.2 LIRPF + LIS",
        "description": "Autónomos en estimación directa pueden aplicar incentivos del Impuesto de Sociedades: libertad de amortización, I+D+i, etc.",
        "requirements_json": json.dumps({
            "autonomo_estimacion_directa": True,
        }),
        "questions_json": json.dumps([
            {"key": "autonomo_estimacion_directa", "text": "¿Eres autónomo en régimen de estimación directa?", "type": "bool"},
            {"key": "inversiones_activos", "text": "¿Has invertido en activos nuevos para tu actividad (equipos, vehículos, etc.)?", "type": "bool"},
        ]),
    },
    {
        "code": "EST-CEUTA-MELILLA",
        "name": "Deducción por rentas obtenidas en Ceuta o Melilla",
        "type": "deduccion",
        "category": "territorial",
        "percentage": 60.0,
        "max_amount": None,
        "legal_reference": "Art. 68.4 LIRPF",
        "description": "Deducción del 60% de la cuota íntegra para residentes en Ceuta o Melilla, sobre rentas obtenidas en dichos territorios.",
        "requirements_json": json.dumps({
            "residente_ceuta_melilla": True,
        }),
        "questions_json": json.dumps([
            {"key": "residente_ceuta_melilla", "text": "¿Resides en Ceuta o Melilla?", "type": "bool"},
        ]),
    },
    {
        "code": "EST-DOUBLE-INT",
        "name": "Deducción por doble imposición internacional",
        "type": "deduccion",
        "category": "internacional",
        "percentage": None,
        "max_amount": None,
        "legal_reference": "Art. 80 LIRPF",
        "description": "Deducción por impuestos pagados en el extranjero sobre rentas incluidas en la base imponible, con el límite de la cuota correspondiente en España.",
        "requirements_json": json.dumps({
            "rentas_extranjero": True,
            "impuestos_pagados_extranjero": True,
        }),
        "questions_json": json.dumps([
            {"key": "rentas_extranjero", "text": "¿Has obtenido rentas en el extranjero (dividendos, trabajo, etc.)?", "type": "bool"},
            {"key": "impuestos_pagados_extranjero", "text": "¿Has pagado impuestos en el país de origen de esas rentas? ¿Cuánto?", "type": "number"},
        ]),
    },
    {
        "code": "EST-VEH-ELEC",
        "name": "Deducción por adquisición de vehículo eléctrico",
        "type": "deduccion",
        "category": "sostenibilidad",
        "percentage": 15.0,
        "max_amount": 20000.0,
        "legal_reference": "DA 58ª LIRPF (RDL 5/2023)",
        "description": "15% sobre el precio de adquisición de un vehículo eléctrico nuevo (máximo 20.000€ de base). Vigente para adquisiciones hasta 31/12/2024 (prorrogado a 2025 pendiente confirmación).",
        "requirements_json": json.dumps({
            "vehiculo_electrico_nuevo": True,
            "precio_inferior_base": True,
        }),
        "questions_json": json.dumps([
            {"key": "vehiculo_electrico_nuevo", "text": "¿Has comprado un vehículo eléctrico nuevo (BEV o PHEV) este año?", "type": "bool"},
            {"key": "precio_vehiculo", "text": "¿Cuánto costó el vehículo (sin IVA)?", "type": "number"},
        ]),
    },
    {
        "code": "EST-REHAB-ENERG",
        "name": "Deducción por obras de mejora energética en vivienda",
        "type": "deduccion",
        "category": "sostenibilidad",
        "percentage": 20.0,
        "max_amount": 5000.0,
        "legal_reference": "DA 50ª LIRPF (RDL 19/2021)",
        "description": "20% de las obras que reduzcan demanda de calefacción/refrigeración ≥7%. 40% si reducen consumo energía primaria ≥30%. 60% para rehabilitación energética de edificios.",
        "requirements_json": json.dumps({
            "obras_mejora_energetica": True,
            "certificado_eficiencia": True,
        }),
        "questions_json": json.dumps([
            {"key": "obras_mejora_energetica", "text": "¿Has hecho obras de mejora energética en tu vivienda (aislamiento, ventanas, caldera, etc.)?", "type": "bool"},
            {"key": "importe_obras", "text": "¿Cuánto has invertido en las obras?", "type": "number"},
            {"key": "certificado_eficiencia", "text": "¿Tienes certificado de eficiencia energética antes y después de las obras?", "type": "bool"},
        ]),
    },
]


async def seed_deductions():
    """Insert all deductions into the database."""
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    # Ensure schema exists (creates tables if missing)
    print("Initializing schema...")
    await db.init_schema()
    print("Schema ready.")

    inserted = 0
    skipped = 0

    for d in DEDUCTIONS_2025:
        deduction_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT OR IGNORE INTO deductions
                   (id, code, tax_year, territory, name, type, category,
                    percentage, max_amount, fixed_amount, legal_reference,
                    description, requirements_json, questions_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    deduction_id,
                    d["code"],
                    2025,
                    "Estatal",
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
            # Check if row was actually inserted
            result = await db.execute(
                "SELECT id FROM deductions WHERE code = ? AND tax_year = ? AND territory = ?",
                [d["code"], 2025, "Estatal"],
            )
            if result.rows and result.rows[0]["id"] == deduction_id:
                inserted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  Error inserting {d['code']}: {e}")
            skipped += 1

    await db.disconnect()
    print(f"\nSeed complete: {inserted} inserted, {skipped} skipped (already existed)")
    print(f"Total deductions in seed: {len(DEDUCTIONS_2025)}")


if __name__ == "__main__":
    asyncio.run(seed_deductions())
