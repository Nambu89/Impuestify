"""Generate 20 test invoices for Q2-Q3 2025 (Carlos Martinez, Consultor IT)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
from scripts.generate_autonomo_invoices import create_invoice_pdf
import scripts.generate_autonomo_invoices as gen

OUTPUT = Path(os.path.dirname(__file__)).parent.parent / "Facturas prueba 2"
OUTPUT.mkdir(parents=True, exist_ok=True)
gen.OUTPUT_DIR = OUTPUT

A = {"nombre": "Carlos Martinez Lopez", "nif": "12345678A",
     "direccion": "C/ Gran Via 45, 3D, 28013 Madrid", "email": "carlos@martinez-consulting.es"}

INVOICES = [
    # 10 EMITIDAS (Q2-Q3 2025)
    {"filename": "factura_emitida_007_abril.pdf", "numero": "2025/007", "fecha": "15/04/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "TechSolutions Spain SL", "nif": "B12345678", "direccion": "Paseo de la Castellana 100, Madrid", "email": "admin@techsolutions.es"},
     "lineas": [{"concepto": "Consultoria desarrollo web - Abril 2025", "cantidad": 1, "precio": 3500.00}, {"concepto": "Implementacion CI/CD pipeline", "cantidad": 1, "precio": 1200.00}],
     "base_imponible": 4700.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_008_abril.pdf", "numero": "2025/008", "fecha": "30/04/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "DataVision Analytics SL", "nif": "B55667788", "direccion": "C/ Velazquez 80, Madrid", "email": "contabilidad@datavision.es"},
     "lineas": [{"concepto": "Desarrollo dashboard analitico React", "cantidad": 1, "precio": 5500.00}],
     "base_imponible": 5500.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_009_mayo.pdf", "numero": "2025/009", "fecha": "15/05/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "TechSolutions Spain SL", "nif": "B12345678", "direccion": "Paseo de la Castellana 100, Madrid", "email": "admin@techsolutions.es"},
     "lineas": [{"concepto": "Consultoria desarrollo web - Mayo 2025", "cantidad": 1, "precio": 3500.00}, {"concepto": "Optimizacion rendimiento PostgreSQL", "cantidad": 1, "precio": 800.00}],
     "base_imponible": 4300.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_010_mayo.pdf", "numero": "2025/010", "fecha": "31/05/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "Inversiones Digitales SA", "nif": "A87654321", "direccion": "Av. de America 32, Madrid", "email": "facturacion@invdig.com"},
     "lineas": [{"concepto": "Pentest aplicacion web + informe", "cantidad": 1, "precio": 3200.00}, {"concepto": "Hardening servidores Linux", "cantidad": 1, "precio": 1500.00}],
     "base_imponible": 4700.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_011_junio.pdf", "numero": "2025/011", "fecha": "15/06/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "TechSolutions Spain SL", "nif": "B12345678", "direccion": "Paseo de la Castellana 100, Madrid", "email": "admin@techsolutions.es"},
     "lineas": [{"concepto": "Consultoria desarrollo web - Junio 2025", "cantidad": 1, "precio": 3500.00}],
     "base_imponible": 3500.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_012_junio.pdf", "numero": "2025/012", "fecha": "28/06/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "StartupFlow SL", "nif": "B99887766", "direccion": "C/ Serrano 55, Madrid", "email": "pagos@startupflow.io"},
     "lineas": [{"concepto": "Desarrollo modulo pagos Stripe", "cantidad": 1, "precio": 4000.00}, {"concepto": "Integracion webhooks", "cantidad": 1, "precio": 1500.00}],
     "base_imponible": 5500.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_013_julio.pdf", "numero": "2025/013", "fecha": "15/07/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "MedTech Solutions SA", "nif": "A11223399", "direccion": "C/ Doctor Esquerdo 136, Madrid", "email": "it@medtech.es"},
     "lineas": [{"concepto": "Auditoria RGPD sistemas sanitarios", "cantidad": 1, "precio": 6500.00}],
     "base_imponible": 6500.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_014_agosto.pdf", "numero": "2025/014", "fecha": "31/08/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "DataVision Analytics SL", "nif": "B55667788", "direccion": "C/ Velazquez 80, Madrid", "email": "contabilidad@datavision.es"},
     "lineas": [{"concepto": "Mantenimiento dashboard Q3", "cantidad": 1, "precio": 2000.00}, {"concepto": "Nuevas visualizaciones datos", "cantidad": 1, "precio": 1800.00}],
     "base_imponible": 3800.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_015_septiembre.pdf", "numero": "2025/015", "fecha": "15/09/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "TechSolutions Spain SL", "nif": "B12345678", "direccion": "Paseo de la Castellana 100, Madrid", "email": "admin@techsolutions.es"},
     "lineas": [{"concepto": "Consultoria desarrollo web - Septiembre 2025", "cantidad": 1, "precio": 3500.00}, {"concepto": "Migracion a Kubernetes", "cantidad": 1, "precio": 2500.00}],
     "base_imponible": 6000.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    {"filename": "factura_emitida_016_septiembre.pdf", "numero": "2025/016", "fecha": "30/09/2025", "tipo": "FACTURA",
     "emisor": A, "receptor": {"nombre": "Inversiones Digitales SA", "nif": "A87654321", "direccion": "Av. de America 32, Madrid", "email": "facturacion@invdig.com"},
     "lineas": [{"concepto": "Formacion DevOps equipo desarrollo", "cantidad": 3, "precio": 600.00}, {"concepto": "Documentacion tecnica", "cantidad": 1, "precio": 500.00}],
     "base_imponible": 2300.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria", "iban": "ES12 1234 5678 9012 3456 7890"},

    # 10 RECIBIDAS (Q2-Q3 2025)
    {"filename": "factura_recibida_007_coworking_q2.pdf", "numero": "CW-2025-0298", "fecha": "01/04/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "CoWork Madrid SL", "nif": "B11223344", "direccion": "C/ Alcala 200, Madrid", "email": "admin@coworkmadrid.es"},
     "receptor": A, "lineas": [{"concepto": "Alquiler puesto fijo coworking - Q2 2025", "cantidad": 3, "precio": 350.00}],
     "base_imponible": 1050.00, "iva_pct": 21, "irpf_pct": 0, "forma_pago": "Domiciliacion bancaria"},

    {"filename": "factura_recibida_008_hosting_q2.pdf", "numero": "AWS-ES-2025-002", "fecha": "30/04/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Amazon Web Services EMEA SARL", "nif": "N0013649J", "direccion": "Luxembourg", "email": "aws-billing@amazon.com"},
     "receptor": A, "lineas": [{"concepto": "EC2 + RDS + S3 - Abril 2025", "cantidad": 1, "precio": 156.80}],
     "base_imponible": 156.80, "iva_pct": 21, "irpf_pct": 0, "forma_pago": "Tarjeta de credito"},

    {"filename": "factura_recibida_009_contable.pdf", "numero": "ASE-2025-0234", "fecha": "15/05/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Asesoria Fiscal Martinez SL", "nif": "B33445566", "direccion": "C/ Princesa 25, Madrid", "email": "info@asesoriamartinez.es"},
     "receptor": A, "lineas": [{"concepto": "Asesoria fiscal trimestral Q1", "cantidad": 1, "precio": 250.00}, {"concepto": "Presentacion Modelo 303 + 130", "cantidad": 1, "precio": 80.00}],
     "base_imponible": 330.00, "iva_pct": 21, "irpf_pct": 15, "forma_pago": "Transferencia bancaria"},

    {"filename": "factura_recibida_010_publicidad.pdf", "numero": "GADS-2025-ES-7732", "fecha": "31/05/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Google Ireland Ltd", "nif": "IE6388047V", "direccion": "Dublin 4, Ireland", "email": "billing@google.com"},
     "receptor": A, "lineas": [{"concepto": "Google Ads - Campana Consultoria IT Madrid", "cantidad": 1, "precio": 320.00}],
     "base_imponible": 320.00, "iva_pct": 21, "irpf_pct": 0, "forma_pago": "Tarjeta de credito"},

    {"filename": "factura_recibida_011_telefono_q2.pdf", "numero": "MOV-2025-MAY-9921", "fecha": "31/05/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Telefonica Moviles Espana SA", "nif": "A78923125", "direccion": "Madrid", "email": "facturacion@movistar.es"},
     "receptor": A, "lineas": [{"concepto": "Tarifa Fusion Pro - Abril+Mayo 2025", "cantidad": 2, "precio": 65.00}],
     "base_imponible": 130.00, "iva_pct": 21, "irpf_pct": 0, "forma_pago": "Domiciliacion bancaria"},

    {"filename": "factura_recibida_012_formacion.pdf", "numero": "UD-2025-ES-44521", "fecha": "10/06/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Udemy Inc", "nif": "US460785802", "direccion": "San Francisco, CA, USA", "email": "support@udemy.com"},
     "receptor": A, "lineas": [{"concepto": "Curso AWS Solutions Architect", "cantidad": 1, "precio": 89.99}, {"concepto": "Curso Kubernetes DevOps", "cantidad": 1, "precio": 94.99}],
     "base_imponible": 184.98, "iva_pct": 21, "irpf_pct": 0, "forma_pago": "Tarjeta de credito"},

    {"filename": "factura_recibida_013_viaje.pdf", "numero": "RNF-2025-78234", "fecha": "20/06/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Renfe Viajeros SA", "nif": "A86868189", "direccion": "Madrid", "email": "facturacion@renfe.es"},
     "receptor": A, "lineas": [{"concepto": "AVE Madrid-Barcelona ida+vuelta (reunion cliente)", "cantidad": 1, "precio": 187.50}],
     "base_imponible": 187.50, "iva_pct": 10, "irpf_pct": 0, "forma_pago": "Tarjeta de credito"},

    {"filename": "factura_recibida_014_seguro_q3.pdf", "numero": "POL-RC-2025-5678", "fecha": "01/07/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Mapfre Seguros SA", "nif": "A28141935", "direccion": "Madrid", "email": "empresas@mapfre.com"},
     "receptor": A, "lineas": [{"concepto": "Seguro RC Profesional - Q3 2025", "cantidad": 1, "precio": 180.00}],
     "base_imponible": 180.00, "iva_pct": 0, "irpf_pct": 0, "forma_pago": "Domiciliacion bancaria"},

    {"filename": "factura_recibida_015_hosting_q3.pdf", "numero": "AWS-ES-2025-003", "fecha": "31/07/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "Amazon Web Services EMEA SARL", "nif": "N0013649J", "direccion": "Luxembourg", "email": "aws-billing@amazon.com"},
     "receptor": A, "lineas": [{"concepto": "EC2 + RDS + S3 + Lambda - Julio 2025", "cantidad": 1, "precio": 198.40}],
     "base_imponible": 198.40, "iva_pct": 21, "irpf_pct": 0, "forma_pago": "Tarjeta de credito"},

    {"filename": "factura_recibida_016_mobiliario.pdf", "numero": "IK-2025-ES-90123", "fecha": "15/08/2025", "tipo": "FACTURA",
     "emisor": {"nombre": "IKEA Iberica SA", "nif": "A60731530", "direccion": "Madrid", "email": "empresas@ikea.es"},
     "receptor": A, "lineas": [{"concepto": "Escritorio elevable BEKANT 160x80", "cantidad": 1, "precio": 499.00}, {"concepto": "Silla ergonomica MARKUS", "cantidad": 1, "precio": 229.00}],
     "base_imponible": 728.00, "iva_pct": 21, "irpf_pct": 0, "forma_pago": "Tarjeta de credito"},
]

if __name__ == "__main__":
    total_e, total_r = 0, 0
    for inv in INVOICES:
        create_invoice_pdf(inv["filename"], inv)
        if "emitida" in inv["filename"]:
            total_e += inv["base_imponible"]
        else:
            total_r += inv["base_imponible"]
        print(f"  OK: {inv['filename']}")

    print(f"\n20 facturas generadas en: {OUTPUT}")
    print(f"Emitidas (ingresos): {total_e:,.2f} EUR")
    print(f"Recibidas (gastos):  {total_r:,.2f} EUR")
