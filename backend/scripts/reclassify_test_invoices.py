"""
Reclassify test user (Carlos Martinez) workspace invoices.
Deletes existing libro_registro + asientos entries and recreates them
with correct tipo (emitida/recibida) based on filename.

Usage: cd backend && python scripts/reclassify_test_invoices.py
Requires: TURSO_DATABASE_URL + TURSO_AUTH_TOKEN in .env
"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Invoice ground truth from generate_autonomo_invoices.py
INVOICES = {
    "factura_emitida_001_enero.pdf": {
        "tipo": "emitida", "numero": "2025/001", "fecha": "2025-01-15",
        "emisor_nombre": "Carlos Martinez Lopez", "emisor_nif": "12345678A",
        "receptor_nombre": "TechSolutions Spain SL", "receptor_nif": "B12345678",
        "concepto": "Consultoria desarrollo web + Mantenimiento servidores",
        "base_imponible": 4000.00, "tipo_iva": 21, "cuota_iva": 840.00,
        "retencion_irpf_pct": 15, "retencion_irpf": 600.00,
        "total": 4240.00,  # 4000 + 840 - 600
        "cuenta_pgc": "705", "cuenta_pgc_nombre": "Prestaciones de servicios",
    },
    "factura_emitida_002_enero.pdf": {
        "tipo": "emitida", "numero": "2025/002", "fecha": "2025-01-31",
        "emisor_nombre": "Carlos Martinez Lopez", "emisor_nif": "12345678A",
        "receptor_nombre": "Inversiones Digitales SA", "receptor_nif": "A87654321",
        "concepto": "Auditoria seguridad informatica + Informe vulnerabilidades",
        "base_imponible": 3500.00, "tipo_iva": 21, "cuota_iva": 735.00,
        "retencion_irpf_pct": 15, "retencion_irpf": 525.00,
        "total": 3710.00,
        "cuenta_pgc": "705", "cuenta_pgc_nombre": "Prestaciones de servicios",
    },
    "factura_emitida_003_febrero.pdf": {
        "tipo": "emitida", "numero": "2025/003", "fecha": "2025-02-15",
        "emisor_nombre": "Carlos Martinez Lopez", "emisor_nif": "12345678A",
        "receptor_nombre": "TechSolutions Spain SL", "receptor_nif": "B12345678",
        "concepto": "Consultoria desarrollo web + Migracion cloud AWS",
        "base_imponible": 4700.00, "tipo_iva": 21, "cuota_iva": 987.00,
        "retencion_irpf_pct": 15, "retencion_irpf": 705.00,
        "total": 4982.00,
        "cuenta_pgc": "705", "cuenta_pgc_nombre": "Prestaciones de servicios",
    },
    "factura_emitida_004_marzo.pdf": {
        "tipo": "emitida", "numero": "2025/004", "fecha": "2025-03-15",
        "emisor_nombre": "Carlos Martinez Lopez", "emisor_nif": "12345678A",
        "receptor_nombre": "TechSolutions Spain SL", "receptor_nif": "B12345678",
        "concepto": "Consultoria desarrollo web + Soporte tecnico urgente",
        "base_imponible": 4250.00, "tipo_iva": 21, "cuota_iva": 892.50,
        "retencion_irpf_pct": 15, "retencion_irpf": 637.50,
        "total": 4505.00,
        "cuenta_pgc": "705", "cuenta_pgc_nombre": "Prestaciones de servicios",
    },
    "factura_emitida_005_marzo.pdf": {
        "tipo": "emitida", "numero": "2025/005", "fecha": "2025-03-28",
        "emisor_nombre": "Carlos Martinez Lopez", "emisor_nif": "12345678A",
        "receptor_nombre": "StartupFlow SL", "receptor_nif": "B99887766",
        "concepto": "Desarrollo MVP aplicacion movil",
        "base_imponible": 6000.00, "tipo_iva": 21, "cuota_iva": 1260.00,
        "retencion_irpf_pct": 15, "retencion_irpf": 900.00,
        "total": 6360.00,
        "cuenta_pgc": "705", "cuenta_pgc_nombre": "Prestaciones de servicios",
    },
    "factura_emitida_006_marzo.pdf": {
        "tipo": "emitida", "numero": "2025/006", "fecha": "2025-03-31",
        "emisor_nombre": "Carlos Martinez Lopez", "emisor_nif": "12345678A",
        "receptor_nombre": "Inversiones Digitales SA", "receptor_nif": "A87654321",
        "concepto": "Formacion equipo IT Ciberseguridad + Material formativo",
        "base_imponible": 1800.00, "tipo_iva": 21, "cuota_iva": 378.00,
        "retencion_irpf_pct": 15, "retencion_irpf": 270.00,
        "total": 1908.00,
        "cuenta_pgc": "705", "cuenta_pgc_nombre": "Prestaciones de servicios",
    },
    "factura_recibida_001_coworking.pdf": {
        "tipo": "recibida", "numero": "CW-2025-0142", "fecha": "2025-01-01",
        "emisor_nombre": "CoWork Madrid SL", "emisor_nif": "B11223344",
        "receptor_nombre": "Carlos Martinez Lopez", "receptor_nif": "12345678A",
        "concepto": "Alquiler puesto fijo coworking + Sala reuniones",
        "base_imponible": 475.00, "tipo_iva": 21, "cuota_iva": 99.75,
        "retencion_irpf_pct": 0, "retencion_irpf": 0,
        "total": 574.75,
        "cuenta_pgc": "621", "cuenta_pgc_nombre": "Arrendamientos y canones",
    },
    "factura_recibida_002_hosting.pdf": {
        "tipo": "recibida", "numero": "AWS-ES-2025-001", "fecha": "2025-01-31",
        "emisor_nombre": "Amazon Web Services EMEA SARL", "emisor_nif": "N0013649J",
        "receptor_nombre": "Carlos Martinez Lopez", "receptor_nif": "12345678A",
        "concepto": "EC2 instances + S3 Storage + CloudFront CDN",
        "base_imponible": 110.00, "tipo_iva": 21, "cuota_iva": 23.10,
        "retencion_irpf_pct": 0, "retencion_irpf": 0,
        "total": 133.10,
        "cuenta_pgc": "629", "cuenta_pgc_nombre": "Otros servicios",
    },
    "factura_recibida_003_software.pdf": {
        "tipo": "recibida", "numero": "JB-2025-ES-4521", "fecha": "2025-02-15",
        "emisor_nombre": "JetBrains s.r.o.", "emisor_nif": "EU826000337",
        "receptor_nombre": "Carlos Martinez Lopez", "receptor_nif": "12345678A",
        "concepto": "IntelliJ IDEA Ultimate - Licencia anual",
        "base_imponible": 499.00, "tipo_iva": 21, "cuota_iva": 104.79,
        "retencion_irpf_pct": 0, "retencion_irpf": 0,
        "total": 603.79,
        "cuenta_pgc": "629", "cuenta_pgc_nombre": "Otros servicios",
    },
    "factura_recibida_004_telefono.pdf": {
        "tipo": "recibida", "numero": "MOV-2025-FEB-8834", "fecha": "2025-02-28",
        "emisor_nombre": "Telefonica Moviles Espana SA", "emisor_nif": "A78923125",
        "receptor_nombre": "Carlos Martinez Lopez", "receptor_nif": "12345678A",
        "concepto": "Tarifa Fusion Pro + Datos adicionales 5GB",
        "base_imponible": 75.00, "tipo_iva": 21, "cuota_iva": 15.75,
        "retencion_irpf_pct": 0, "retencion_irpf": 0,
        "total": 90.75,
        "cuenta_pgc": "629", "cuenta_pgc_nombre": "Otros servicios",
    },
    "factura_recibida_005_seguro_rc.pdf": {
        "tipo": "recibida", "numero": "POL-RC-2025-1234", "fecha": "2025-03-01",
        "emisor_nombre": "Mapfre Seguros SA", "emisor_nif": "A28141935",
        "receptor_nombre": "Carlos Martinez Lopez", "receptor_nif": "12345678A",
        "concepto": "Seguro Responsabilidad Civil Profesional Q1 2025",
        "base_imponible": 180.00, "tipo_iva": 0, "cuota_iva": 0,
        "retencion_irpf_pct": 0, "retencion_irpf": 0,
        "total": 180.00,
        "cuenta_pgc": "625", "cuenta_pgc_nombre": "Primas de seguros",
    },
    "factura_recibida_006_material.pdf": {
        "tipo": "recibida", "numero": "PC-2025-0089", "fecha": "2025-03-20",
        "emisor_nombre": "PcComponentes y Multimedia SLU", "emisor_nif": "B73347494",
        "receptor_nombre": "Carlos Martinez Lopez", "receptor_nif": "12345678A",
        "concepto": "Monitor LG 4K + Teclado Logitech + Raton ergonomico",
        "base_imponible": 657.00, "tipo_iva": 21, "cuota_iva": 137.97,
        "retencion_irpf_pct": 0, "retencion_irpf": 0,
        "total": 794.97,
        "cuenta_pgc": "217", "cuenta_pgc_nombre": "Equipos para procesos de informacion",
    },
}


async def main():
    from dotenv import load_dotenv
    load_dotenv()

    from app.database.turso_client import TursoClient
    db = TursoClient()
    await db.connect()

    # Find workspace files for test autonomo user
    ws_files = await db.execute(
        """
        SELECT wf.id, wf.filename
        FROM workspace_files wf
        JOIN workspaces w ON wf.workspace_id = w.id
        WHERE w.user_id = 'test-autonomo-00000002'
          AND wf.file_type = 'factura'
          AND wf.processing_status = 'completed'
        """,
        [],
    )
    rows = ws_files.rows if hasattr(ws_files, "rows") else ws_files

    if not rows:
        print("No workspace invoice files found for test autonomo user")
        return

    print(f"Found {len(rows)} workspace invoice files")

    # Delete existing libro_registro + asientos for these files
    file_ids = []
    for row in rows:
        fid = row.get("id") if hasattr(row, "get") else row[0]
        file_ids.append(fid)

    placeholders = ",".join(["?" for _ in file_ids])

    # Delete asientos linked to these invoices
    await db.execute(
        f"""
        DELETE FROM asientos_contables
        WHERE libro_registro_id IN (
            SELECT id FROM libro_registro WHERE workspace_file_id IN ({placeholders})
        )
        """,
        file_ids,
    )
    print("Deleted old asientos")

    # Delete libro_registro entries
    await db.execute(
        f"DELETE FROM libro_registro WHERE workspace_file_id IN ({placeholders})",
        file_ids,
    )
    print("Deleted old libro_registro entries")

    # Recreate with correct data
    created = 0
    for row in rows:
        fid = row.get("id") if hasattr(row, "get") else row[0]
        fname = row.get("filename") if hasattr(row, "get") else row[1]

        inv = INVOICES.get(fname)
        if not inv:
            print(f"  SKIP: {fname} — no ground truth data")
            continue

        invoice_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        fecha = inv["fecha"]
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        year = fecha_dt.year
        trimestre = (fecha_dt.month - 1) // 3 + 1

        await db.execute(
            """
            INSERT INTO libro_registro
                (id, user_id, workspace_file_id, tipo, numero_factura,
                 fecha_factura, emisor_nif, emisor_nombre,
                 receptor_nif, receptor_nombre, concepto,
                 base_imponible, tipo_iva, cuota_iva,
                 tipo_re, cuota_re, retencion_irpf_pct, retencion_irpf,
                 total, cuenta_pgc, cuenta_pgc_nombre,
                 clasificacion_confianza,
                 year, trimestre, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                invoice_id,
                "test-autonomo-00000002",
                fid,
                inv["tipo"],
                inv["numero"],
                inv["fecha"],
                inv["emisor_nif"],
                inv["emisor_nombre"],
                inv["receptor_nif"],
                inv["receptor_nombre"],
                inv["concepto"],
                inv["base_imponible"],
                inv["tipo_iva"],
                inv["cuota_iva"],
                0, 0,  # tipo_re, cuota_re
                inv["retencion_irpf_pct"],
                inv["retencion_irpf"],
                inv["total"],
                inv["cuenta_pgc"],
                inv["cuenta_pgc_nombre"],
                "confirmada",
                year,
                trimestre,
                now,
            ],
        )

        # Generate asiento contable (simple double entry)
        # Get next numero_asiento
        max_asiento = await db.execute(
            "SELECT COALESCE(MAX(numero_asiento), 0) as max_num FROM asientos_contables WHERE user_id = ? AND year = ?",
            ["test-autonomo-00000002", year],
        )
        max_rows = max_asiento.rows if hasattr(max_asiento, "rows") else max_asiento
        next_num = (max_rows[0].get("max_num", 0) if hasattr(max_rows[0], "get") else max_rows[0][0]) + 1

        asiento_sql = """INSERT INTO asientos_contables
            (id, user_id, libro_registro_id, fecha, numero_asiento, cuenta_code, cuenta_nombre, debe, haber, concepto, year, trimestre, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        if inv["tipo"] == "emitida":
            await db.execute(asiento_sql,
                [str(uuid.uuid4()), "test-autonomo-00000002", invoice_id, inv["fecha"], next_num,
                 "430", "Clientes", inv["total"], 0, inv["concepto"], year, trimestre, now])
            await db.execute(asiento_sql,
                [str(uuid.uuid4()), "test-autonomo-00000002", invoice_id, inv["fecha"], next_num,
                 inv["cuenta_pgc"], inv["cuenta_pgc_nombre"], 0, inv["base_imponible"], inv["concepto"], year, trimestre, now])
            if inv["cuota_iva"] > 0:
                await db.execute(asiento_sql,
                    [str(uuid.uuid4()), "test-autonomo-00000002", invoice_id, inv["fecha"], next_num,
                     "477", "Hacienda Publica, IVA repercutido", 0, inv["cuota_iva"], inv["concepto"], year, trimestre, now])
        else:
            await db.execute(asiento_sql,
                [str(uuid.uuid4()), "test-autonomo-00000002", invoice_id, inv["fecha"], next_num,
                 inv["cuenta_pgc"], inv["cuenta_pgc_nombre"], inv["base_imponible"], 0, inv["concepto"], year, trimestre, now])
            if inv["cuota_iva"] > 0:
                await db.execute(asiento_sql,
                    [str(uuid.uuid4()), "test-autonomo-00000002", invoice_id, inv["fecha"], next_num,
                     "472", "Hacienda Publica, IVA soportado", inv["cuota_iva"], 0, inv["concepto"], year, trimestre, now])
            await db.execute(asiento_sql,
                [str(uuid.uuid4()), "test-autonomo-00000002", invoice_id, inv["fecha"], next_num,
                 "410", "Acreedores por prestaciones de servicios", 0, inv["total"], inv["concepto"], year, trimestre, now])

        tipo_label = "EMITIDA" if inv["tipo"] == "emitida" else "RECIBIDA"
        print(f"  {tipo_label}: {fname} > {inv['cuenta_pgc']} {inv['cuenta_pgc_nombre']} - {inv['base_imponible']:.2f} EUR")
        created += 1

    print(f"\nDone: {created} invoices reclassified with correct data")
    print(f"Expected: Ingresos 24,250 EUR | Gastos 1,996 EUR | Resultado +22,254 EUR")


if __name__ == "__main__":
    asyncio.run(main())
