"""
Seed Plan General Contable (PGC) accounts.
~59 most common accounts for autonomos and PYMEs (groups 1-7).
Idempotent: deletes existing and re-inserts.

Usage:
    cd backend
    python scripts/seed_pgc_accounts.py
"""
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

PGC_ACCOUNTS = [
    # =============================================
    # Grupo 1: Financiacion basica
    # =============================================
    {"code": "100", "name": "Capital social", "group_code": "10", "group_name": "Capital", "type": "balance"},
    {"code": "129", "name": "Resultado del ejercicio", "group_code": "12", "group_name": "Resultados pendientes", "type": "balance"},
    {"code": "170", "name": "Deudas a largo plazo con entidades de credito", "group_code": "17", "group_name": "Deudas LP", "type": "balance"},
    {"code": "171", "name": "Deudas a largo plazo", "group_code": "17", "group_name": "Deudas LP", "type": "balance"},
    {"code": "174", "name": "Acreedores por arrendamiento financiero LP", "group_code": "17", "group_name": "Deudas LP", "type": "balance"},

    # =============================================
    # Grupo 2: Inmovilizado
    # =============================================
    {"code": "206", "name": "Aplicaciones informaticas", "group_code": "20", "group_name": "Inmovilizado intangible", "type": "balance"},
    {"code": "210", "name": "Terrenos y bienes naturales", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "211", "name": "Construcciones", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "213", "name": "Maquinaria", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "214", "name": "Utillaje", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "216", "name": "Mobiliario", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "217", "name": "Equipos para procesos de informacion", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "218", "name": "Elementos de transporte", "group_code": "21", "group_name": "Inmovilizado material", "type": "balance"},
    {"code": "280", "name": "Amortizacion acumulada inmovilizado intangible", "group_code": "28", "group_name": "Amortizaciones", "type": "balance"},
    {"code": "281", "name": "Amortizacion acumulada inmovilizado material", "group_code": "28", "group_name": "Amortizaciones", "type": "balance"},

    # =============================================
    # Grupo 3: Existencias
    # =============================================
    {"code": "300", "name": "Mercaderias", "group_code": "30", "group_name": "Existencias comerciales", "type": "balance"},
    {"code": "310", "name": "Materias primas", "group_code": "31", "group_name": "Materias primas", "type": "balance"},
    {"code": "350", "name": "Productos terminados", "group_code": "35", "group_name": "Productos terminados", "type": "balance"},

    # =============================================
    # Grupo 4: Acreedores y deudores
    # =============================================
    {"code": "400", "name": "Proveedores", "group_code": "40", "group_name": "Proveedores", "type": "balance",
     "keywords": ["proveedor", "compra", "suministro", "mercaderia"]},
    {"code": "410", "name": "Acreedores por prestaciones de servicios", "group_code": "41", "group_name": "Acreedores", "type": "balance",
     "keywords": ["servicio", "asesoria", "consultoria", "profesional"]},
    {"code": "430", "name": "Clientes", "group_code": "43", "group_name": "Clientes", "type": "balance",
     "keywords": ["cliente", "venta", "factura emitida"]},
    {"code": "440", "name": "Deudores", "group_code": "44", "group_name": "Deudores", "type": "balance"},
    {"code": "465", "name": "Remuneraciones pendientes de pago", "group_code": "46", "group_name": "Personal", "type": "balance"},
    {"code": "470", "name": "Hacienda Publica deudora", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "472", "name": "Hacienda Publica IVA soportado", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance",
     "keywords": ["iva", "soportado", "deducible"]},
    {"code": "473", "name": "Hacienda Publica retenciones y pagos a cuenta", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "475", "name": "Hacienda Publica acreedora", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "4751", "name": "HP acreedora por retenciones practicadas", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance",
     "keywords": ["retencion", "irpf", "practicada"]},
    {"code": "476", "name": "Organismos Seguridad Social acreedores", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance"},
    {"code": "477", "name": "Hacienda Publica IVA repercutido", "group_code": "47", "group_name": "Admin. Publicas", "type": "balance",
     "keywords": ["iva", "repercutido", "cobrado"]},

    # =============================================
    # Grupo 5: Cuentas financieras
    # =============================================
    {"code": "520", "name": "Deudas a corto plazo con entidades de credito", "group_code": "52", "group_name": "Deudas CP", "type": "balance"},
    {"code": "523", "name": "Proveedores de inmovilizado CP", "group_code": "52", "group_name": "Deudas CP", "type": "balance"},
    {"code": "570", "name": "Caja", "group_code": "57", "group_name": "Tesoreria", "type": "balance",
     "keywords": ["efectivo", "caja", "metalico"]},
    {"code": "572", "name": "Bancos c/c", "group_code": "57", "group_name": "Tesoreria", "type": "balance",
     "keywords": ["banco", "transferencia", "cuenta corriente"]},

    # =============================================
    # Grupo 6: Gastos
    # =============================================
    {"code": "600", "name": "Compras de mercaderias", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["compra", "mercaderia", "producto", "material", "stock"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "601", "name": "Compras de materias primas", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["materia prima", "componente"]},
    {"code": "602", "name": "Compras de otros aprovisionamientos", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["consumible", "envase", "embalaje", "material oficina"]},
    {"code": "606", "name": "Descuentos sobre compras por pronto pago", "group_code": "60", "group_name": "Compras", "type": "gasto"},
    {"code": "607", "name": "Trabajos realizados por otras empresas", "group_code": "60", "group_name": "Compras", "type": "gasto",
     "keywords": ["subcontrata", "outsourcing", "trabajo externo"]},
    {"code": "610", "name": "Variacion de existencias de mercaderias", "group_code": "61", "group_name": "Variacion existencias", "type": "gasto"},
    {"code": "621", "name": "Arrendamientos y canones", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["alquiler", "arrendamiento", "local", "oficina", "canon", "leasing", "renting"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "622", "name": "Reparaciones y conservacion", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["reparacion", "mantenimiento", "conservacion", "arreglo"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "623", "name": "Servicios de profesionales independientes", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["asesoria", "abogado", "gestor", "consultoria", "auditor", "notario", "profesional"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "624", "name": "Transportes", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["transporte", "mensajeria", "envio", "logistica", "correos"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "625", "name": "Primas de seguros", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["seguro", "poliza", "rc profesional", "responsabilidad civil"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "626", "name": "Servicios bancarios y similares", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["banco", "comision bancaria", "transferencia", "tpv"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "627", "name": "Publicidad, propaganda y relaciones publicas", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["publicidad", "marketing", "anuncio", "propaganda", "google ads", "meta ads"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "628", "name": "Suministros", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["luz", "agua", "gas", "electricidad", "telefono", "internet", "fibra"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "629", "name": "Otros servicios", "group_code": "62", "group_name": "Servicios exteriores", "type": "gasto",
     "keywords": ["servicio", "limpieza", "formacion", "suscripcion", "software", "hosting", "cloud", "saas"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "631", "name": "Otros tributos", "group_code": "63", "group_name": "Tributos", "type": "gasto",
     "keywords": ["ibi", "iae", "impuesto", "tasa", "tributo", "basura"]},
    {"code": "640", "name": "Sueldos y salarios", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["nomina", "salario", "sueldo", "empleado", "trabajador"],
     "common_for": ["sociedad"]},
    {"code": "642", "name": "Seguridad Social a cargo de la empresa", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto",
     "keywords": ["seguridad social", "cotizacion", "ss empresa"]},
    {"code": "649", "name": "Otros gastos sociales", "group_code": "64", "group_name": "Gastos de personal", "type": "gasto"},
    {"code": "662", "name": "Intereses de deudas", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto",
     "keywords": ["interes", "prestamo", "hipoteca", "financiacion"]},
    {"code": "669", "name": "Otros gastos financieros", "group_code": "66", "group_name": "Gastos financieros", "type": "gasto"},
    {"code": "680", "name": "Amortizacion del inmovilizado intangible", "group_code": "68", "group_name": "Dotaciones amortizacion", "type": "gasto"},
    {"code": "681", "name": "Amortizacion del inmovilizado material", "group_code": "68", "group_name": "Dotaciones amortizacion", "type": "gasto",
     "keywords": ["amortizacion", "depreciacion"]},

    # =============================================
    # Grupo 7: Ingresos
    # =============================================
    {"code": "700", "name": "Ventas de mercaderias", "group_code": "70", "group_name": "Ventas", "type": "ingreso",
     "keywords": ["venta", "mercaderia", "producto"],
     "common_for": ["autonomo", "farmacia", "sociedad"]},
    {"code": "705", "name": "Prestaciones de servicios", "group_code": "70", "group_name": "Ventas", "type": "ingreso",
     "keywords": ["servicio", "honorarios", "factura emitida", "prestacion"],
     "common_for": ["autonomo", "sociedad"]},
    {"code": "708", "name": "Devoluciones de ventas", "group_code": "70", "group_name": "Ventas", "type": "ingreso"},
    {"code": "709", "name": "Rappels sobre ventas", "group_code": "70", "group_name": "Ventas", "type": "ingreso"},
    {"code": "740", "name": "Subvenciones a la explotacion", "group_code": "74", "group_name": "Subvenciones", "type": "ingreso",
     "keywords": ["subvencion", "ayuda", "kit digital"]},
    {"code": "752", "name": "Ingresos por arrendamientos", "group_code": "75", "group_name": "Otros ingresos", "type": "ingreso",
     "keywords": ["alquiler cobrado", "arrendamiento ingreso"]},
    {"code": "759", "name": "Ingresos por servicios diversos", "group_code": "75", "group_name": "Otros ingresos", "type": "ingreso"},
    {"code": "769", "name": "Otros ingresos financieros", "group_code": "76", "group_name": "Ingresos financieros", "type": "ingreso",
     "keywords": ["interes cobrado", "dividendo"]},
    {"code": "771", "name": "Beneficios procedentes del inmovilizado material", "group_code": "77", "group_name": "Beneficios activos", "type": "ingreso"},
]


async def seed_pgc_accounts():
    """Delete existing PGC accounts and re-insert all."""
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    # Ensure schema exists
    print("Initializing schema...")
    await db.init_schema()
    print("Schema ready.")

    # Delete existing accounts
    await db.execute("DELETE FROM pgc_accounts")
    print("Cleared existing pgc_accounts.")

    inserted = 0
    for account in PGC_ACCOUNTS:
        account_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT INTO pgc_accounts
                   (id, code, name, group_code, group_name, type, description, keywords, common_for, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                [
                    account_id,
                    account["code"],
                    account["name"],
                    account["group_code"],
                    account["group_name"],
                    account["type"],
                    account.get("description"),
                    json.dumps(account.get("keywords")) if account.get("keywords") else None,
                    json.dumps(account.get("common_for")) if account.get("common_for") else None,
                ],
            )
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {account['code']}: {e}")

    await db.disconnect()
    print(f"\nSeed complete: {inserted} PGC accounts inserted")
    print(f"Total accounts in seed data: {len(PGC_ACCOUNTS)}")


if __name__ == "__main__":
    asyncio.run(seed_pgc_accounts())
