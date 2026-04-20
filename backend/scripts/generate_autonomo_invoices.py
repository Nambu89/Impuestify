"""
Generate realistic test invoices for an autonomous worker (consultoria IT).

Creates:
- 6 emitted invoices (services rendered to clients)
- 6 received invoices (deductible expenses)
- Spanning Q1 2025 (Jan-Mar) for quarterly IVA/IRPF testing

Output: tests/e2e/fixtures/invoices_prueba/autonomo_test/
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

OUTPUT_DIR = Path(__file__).parent.parent.parent / "tests" / "e2e" / "fixtures" / "invoices_prueba" / "autonomo_test"


def create_invoice_pdf(filename: str, data: dict):
    """Create a realistic Spanish invoice PDF."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = OUTPUT_DIR / filename

    doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'],
                                  fontSize=16, textColor=colors.HexColor('#1a56db'),
                                  alignment=TA_CENTER)
    header_style = ParagraphStyle('Header', parent=styles['Normal'],
                                   fontSize=9, leading=12)
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'],
                                 fontSize=9, leading=12)
    right_style = ParagraphStyle('Right', parent=styles['Normal'],
                                  fontSize=9, alignment=TA_RIGHT)
    small_style = ParagraphStyle('Small', parent=styles['Normal'],
                                  fontSize=7, textColor=colors.gray)

    elements = []

    # Title
    tipo = data.get("tipo", "FACTURA")
    elements.append(Paragraph(f"{tipo} N.º {data['numero']}", title_style))
    elements.append(Spacer(1, 5*mm))

    # Emisor + Receptor side by side
    emisor_text = (
        f"<b>EMISOR</b><br/>"
        f"{data['emisor']['nombre']}<br/>"
        f"NIF: {data['emisor']['nif']}<br/>"
        f"{data['emisor']['direccion']}<br/>"
        f"{data['emisor'].get('email', '')}"
    )
    receptor_text = (
        f"<b>RECEPTOR</b><br/>"
        f"{data['receptor']['nombre']}<br/>"
        f"NIF: {data['receptor']['nif']}<br/>"
        f"{data['receptor']['direccion']}<br/>"
        f"{data['receptor'].get('email', '')}"
    )

    header_table = Table([
        [Paragraph(emisor_text, header_style), Paragraph(receptor_text, header_style)]
    ], colWidths=[85*mm, 85*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f4ff')),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3*mm))

    # Date
    elements.append(Paragraph(f"<b>Fecha:</b> {data['fecha']}    <b>Vencimiento:</b> {data.get('vencimiento', 'A 30 dias')}", header_style))
    elements.append(Spacer(1, 5*mm))

    # Line items
    table_data = [["Concepto", "Cantidad", "Precio Unit.", "Importe"]]
    for item in data['lineas']:
        table_data.append([
            item['concepto'],
            str(item['cantidad']),
            f"{item['precio']:.2f} EUR",
            f"{item['cantidad'] * item['precio']:.2f} EUR"
        ])

    items_table = Table(table_data, colWidths=[90*mm, 20*mm, 30*mm, 30*mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a56db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 5*mm))

    # Totals
    base = data['base_imponible']
    iva_pct = data.get('iva_pct', 21)
    iva = round(base * iva_pct / 100, 2)
    irpf_pct = data.get('irpf_pct', 0)
    irpf = round(base * irpf_pct / 100, 2)
    total = base + iva - irpf

    totals_data = [
        ["Base imponible", f"{base:.2f} EUR"],
        [f"IVA ({iva_pct}%)", f"{iva:.2f} EUR"],
    ]
    if irpf_pct > 0:
        totals_data.append([f"Retención IRPF (-{irpf_pct}%)", f"-{irpf:.2f} EUR"])
    totals_data.append(["TOTAL", f"{total:.2f} EUR"])

    totals_table = Table(totals_data, colWidths=[130*mm, 40*mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 5*mm))

    # Payment method
    if data.get('forma_pago'):
        elements.append(Paragraph(f"<b>Forma de pago:</b> {data['forma_pago']}", header_style))

    if data.get('iban'):
        elements.append(Paragraph(f"<b>IBAN:</b> {data['iban']}", header_style))

    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("Este documento sirve como factura a efectos del Real Decreto 1619/2012.", small_style))

    doc.build(elements)
    print(f"  Created: {filepath.name}")
    return filepath


# ============================================================
# AUTONOMO: Carlos Martinez, Consultor IT, Madrid
# ============================================================

AUTONOMO = {
    "nombre": "Carlos Martinez Lopez",
    "nif": "12345678A",
    "direccion": "C/ Gran Via 45, 3D, 28013 Madrid",
    "email": "carlos@martinez-consulting.es",
}

# --- EMITTED INVOICES (services rendered) ---

EMITTED = [
    {
        "filename": "factura_emitida_001_enero.pdf",
        "numero": "2025/001",
        "fecha": "15/01/2025",
        "tipo": "FACTURA",
        "emisor": AUTONOMO,
        "receptor": {
            "nombre": "TechSolutions Spain SL",
            "nif": "B12345678",
            "direccion": "Paseo de la Castellana 100, 28046 Madrid",
            "email": "admin@techsolutions.es",
        },
        "lineas": [
            {"concepto": "Consultoria desarrollo web - Enero 2025", "cantidad": 1, "precio": 3500.00},
            {"concepto": "Mantenimiento servidores", "cantidad": 1, "precio": 500.00},
        ],
        "base_imponible": 4000.00,
        "iva_pct": 21,
        "irpf_pct": 15,
        "forma_pago": "Transferencia bancaria",
        "iban": "ES12 1234 5678 9012 3456 7890",
    },
    {
        "filename": "factura_emitida_002_enero.pdf",
        "numero": "2025/002",
        "fecha": "31/01/2025",
        "tipo": "FACTURA",
        "emisor": AUTONOMO,
        "receptor": {
            "nombre": "Inversiones Digitales SA",
            "nif": "A87654321",
            "direccion": "Av. de America 32, 28028 Madrid",
            "email": "facturacion@invdig.com",
        },
        "lineas": [
            {"concepto": "Auditoria de seguridad informatica", "cantidad": 1, "precio": 2800.00},
            {"concepto": "Informe de vulnerabilidades", "cantidad": 1, "precio": 700.00},
        ],
        "base_imponible": 3500.00,
        "iva_pct": 21,
        "irpf_pct": 15,
        "forma_pago": "Transferencia bancaria",
        "iban": "ES12 1234 5678 9012 3456 7890",
    },
    {
        "filename": "factura_emitida_003_febrero.pdf",
        "numero": "2025/003",
        "fecha": "15/02/2025",
        "tipo": "FACTURA",
        "emisor": AUTONOMO,
        "receptor": {
            "nombre": "TechSolutions Spain SL",
            "nif": "B12345678",
            "direccion": "Paseo de la Castellana 100, 28046 Madrid",
            "email": "admin@techsolutions.es",
        },
        "lineas": [
            {"concepto": "Consultoria desarrollo web - Febrero 2025", "cantidad": 1, "precio": 3500.00},
            {"concepto": "Migracion cloud AWS", "cantidad": 1, "precio": 1200.00},
        ],
        "base_imponible": 4700.00,
        "iva_pct": 21,
        "irpf_pct": 15,
        "forma_pago": "Transferencia bancaria",
        "iban": "ES12 1234 5678 9012 3456 7890",
    },
    {
        "filename": "factura_emitida_004_marzo.pdf",
        "numero": "2025/004",
        "fecha": "15/03/2025",
        "tipo": "FACTURA",
        "emisor": AUTONOMO,
        "receptor": {
            "nombre": "TechSolutions Spain SL",
            "nif": "B12345678",
            "direccion": "Paseo de la Castellana 100, 28046 Madrid",
            "email": "admin@techsolutions.es",
        },
        "lineas": [
            {"concepto": "Consultoria desarrollo web - Marzo 2025", "cantidad": 1, "precio": 3500.00},
            {"concepto": "Soporte tecnico urgente", "cantidad": 5, "precio": 150.00},
        ],
        "base_imponible": 4250.00,
        "iva_pct": 21,
        "irpf_pct": 15,
        "forma_pago": "Transferencia bancaria",
        "iban": "ES12 1234 5678 9012 3456 7890",
    },
    {
        "filename": "factura_emitida_005_marzo.pdf",
        "numero": "2025/005",
        "fecha": "28/03/2025",
        "tipo": "FACTURA",
        "emisor": AUTONOMO,
        "receptor": {
            "nombre": "StartupFlow SL",
            "nif": "B99887766",
            "direccion": "C/ Serrano 55, 28006 Madrid",
            "email": "pagos@startupflow.io",
        },
        "lineas": [
            {"concepto": "Desarrollo MVP aplicacion movil", "cantidad": 1, "precio": 6000.00},
        ],
        "base_imponible": 6000.00,
        "iva_pct": 21,
        "irpf_pct": 15,
        "forma_pago": "Transferencia bancaria",
        "iban": "ES12 1234 5678 9012 3456 7890",
    },
    {
        "filename": "factura_emitida_006_marzo.pdf",
        "numero": "2025/006",
        "fecha": "31/03/2025",
        "tipo": "FACTURA",
        "emisor": AUTONOMO,
        "receptor": {
            "nombre": "Inversiones Digitales SA",
            "nif": "A87654321",
            "direccion": "Av. de America 32, 28028 Madrid",
            "email": "facturacion@invdig.com",
        },
        "lineas": [
            {"concepto": "Formacion equipo IT - Ciberseguridad", "cantidad": 2, "precio": 800.00},
            {"concepto": "Material formativo", "cantidad": 1, "precio": 200.00},
        ],
        "base_imponible": 1800.00,
        "iva_pct": 21,
        "irpf_pct": 15,
        "forma_pago": "Transferencia bancaria",
        "iban": "ES12 1234 5678 9012 3456 7890",
    },
]

# --- RECEIVED INVOICES (deductible expenses) ---

RECEIVED = [
    {
        "filename": "factura_recibida_001_coworking.pdf",
        "numero": "CW-2025-0142",
        "fecha": "01/01/2025",
        "tipo": "FACTURA",
        "emisor": {
            "nombre": "CoWork Madrid SL",
            "nif": "B11223344",
            "direccion": "C/ Alcala 200, 28028 Madrid",
            "email": "admin@coworkmadrid.es",
        },
        "receptor": AUTONOMO,
        "lineas": [
            {"concepto": "Alquiler puesto fijo coworking - Enero 2025", "cantidad": 1, "precio": 350.00},
            {"concepto": "Sala reuniones (5 horas)", "cantidad": 5, "precio": 25.00},
        ],
        "base_imponible": 475.00,
        "iva_pct": 21,
        "irpf_pct": 0,
        "forma_pago": "Domiciliacion bancaria",
    },
    {
        "filename": "factura_recibida_002_hosting.pdf",
        "numero": "AWS-ES-2025-001",
        "fecha": "31/01/2025",
        "tipo": "FACTURA",
        "emisor": {
            "nombre": "Amazon Web Services EMEA SARL",
            "nif": "N0013649J",
            "direccion": "38 Avenue John F. Kennedy, L-1855 Luxembourg",
            "email": "aws-billing@amazon.com",
        },
        "receptor": AUTONOMO,
        "lineas": [
            {"concepto": "EC2 instances - Enero 2025", "cantidad": 1, "precio": 89.50},
            {"concepto": "S3 Storage", "cantidad": 1, "precio": 12.30},
            {"concepto": "CloudFront CDN", "cantidad": 1, "precio": 8.20},
        ],
        "base_imponible": 110.00,
        "iva_pct": 21,
        "irpf_pct": 0,
        "forma_pago": "Tarjeta de credito",
    },
    {
        "filename": "factura_recibida_003_software.pdf",
        "numero": "JB-2025-ES-4521",
        "fecha": "15/02/2025",
        "tipo": "FACTURA",
        "emisor": {
            "nombre": "JetBrains s.r.o.",
            "nif": "EU826000337",
            "direccion": "Na Hrebenech II 1718/10, 140 00 Prague, Czech Republic",
            "email": "sales@jetbrains.com",
        },
        "receptor": AUTONOMO,
        "lineas": [
            {"concepto": "IntelliJ IDEA Ultimate - Licencia anual", "cantidad": 1, "precio": 499.00},
        ],
        "base_imponible": 499.00,
        "iva_pct": 21,
        "irpf_pct": 0,
        "forma_pago": "Tarjeta de credito",
    },
    {
        "filename": "factura_recibida_004_telefono.pdf",
        "numero": "MOV-2025-FEB-8834",
        "fecha": "28/02/2025",
        "tipo": "FACTURA",
        "emisor": {
            "nombre": "Telefonica Moviles Espana SA",
            "nif": "A78923125",
            "direccion": "Ronda de la Comunicacion s/n, 28050 Madrid",
            "email": "facturacion@movistar.es",
        },
        "receptor": AUTONOMO,
        "lineas": [
            {"concepto": "Tarifa Fusion Pro - Febrero 2025", "cantidad": 1, "precio": 65.00},
            {"concepto": "Datos adicionales 5GB", "cantidad": 1, "precio": 10.00},
        ],
        "base_imponible": 75.00,
        "iva_pct": 21,
        "irpf_pct": 0,
        "forma_pago": "Domiciliacion bancaria",
    },
    {
        "filename": "factura_recibida_005_seguro_rc.pdf",
        "numero": "POL-RC-2025-1234",
        "fecha": "01/03/2025",
        "tipo": "FACTURA",
        "emisor": {
            "nombre": "Mapfre Seguros SA",
            "nif": "A28141935",
            "direccion": "Paseo de Recoletos 25, 28004 Madrid",
            "email": "empresas@mapfre.com",
        },
        "receptor": AUTONOMO,
        "lineas": [
            {"concepto": "Seguro Responsabilidad Civil Profesional - Trimestre Q1 2025", "cantidad": 1, "precio": 180.00},
        ],
        "base_imponible": 180.00,
        "iva_pct": 0,
        "irpf_pct": 0,
        "forma_pago": "Domiciliacion bancaria",
    },
    {
        "filename": "factura_recibida_006_material.pdf",
        "numero": "PC-2025-0089",
        "fecha": "20/03/2025",
        "tipo": "FACTURA",
        "emisor": {
            "nombre": "PcComponentes y Multimedia SLU",
            "nif": "B73347494",
            "direccion": "Av. Europa 2, 30007 Murcia",
            "email": "facturacion@pccomponentes.com",
        },
        "receptor": AUTONOMO,
        "lineas": [
            {"concepto": "Monitor LG 27\" 4K UltraFine", "cantidad": 1, "precio": 449.00},
            {"concepto": "Teclado mecanico Logitech MX Keys", "cantidad": 1, "precio": 119.00},
            {"concepto": "Raton ergonomico Logitech MX Master 3S", "cantidad": 1, "precio": 89.00},
        ],
        "base_imponible": 657.00,
        "iva_pct": 21,
        "irpf_pct": 0,
        "forma_pago": "Tarjeta de credito",
    },
]


def main():
    print(f"Generating invoices in: {OUTPUT_DIR}")
    print(f"\n--- EMITTED (services rendered) ---")

    total_base_emitida = 0
    total_iva_repercutido = 0
    total_irpf_retenido = 0
    for inv in EMITTED:
        create_invoice_pdf(inv["filename"], inv)
        total_base_emitida += inv["base_imponible"]
        total_iva_repercutido += round(inv["base_imponible"] * inv.get("iva_pct", 21) / 100, 2)
        total_irpf_retenido += round(inv["base_imponible"] * inv.get("irpf_pct", 0) / 100, 2)

    print(f"\n--- RECEIVED (deductible expenses) ---")
    total_base_recibida = 0
    total_iva_soportado = 0
    for inv in RECEIVED:
        create_invoice_pdf(inv["filename"], inv)
        total_base_recibida += inv["base_imponible"]
        total_iva_soportado += round(inv["base_imponible"] * inv.get("iva_pct", 21) / 100, 2)

    print(f"\n{'='*50}")
    print(f"Q1 2025 Summary (Carlos Martinez, Consultor IT)")
    print(f"{'='*50}")
    print(f"Ingresos (base): {total_base_emitida:,.2f} EUR")
    print(f"IVA repercutido: {total_iva_repercutido:,.2f} EUR")
    print(f"IRPF retenido:   {total_irpf_retenido:,.2f} EUR")
    print(f"Gastos (base):   {total_base_recibida:,.2f} EUR")
    print(f"IVA soportado:   {total_iva_soportado:,.2f} EUR")
    print(f"IVA a ingresar:  {total_iva_repercutido - total_iva_soportado:,.2f} EUR")
    print(f"Beneficio neto:  {total_base_emitida - total_base_recibida:,.2f} EUR")


if __name__ == "__main__":
    main()
