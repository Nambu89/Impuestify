"""
Seed ALL foral territory IRPF deductions for 2025 (60 deductions: 15 per territory).

Covers the 4 foral territories:
  - Araba (Alava): Norma Foral 33/2013 de 27 de noviembre, del Impuesto sobre la Renta
    de las Personas Fisicas (NFIRPF Araba)
  - Bizkaia: Norma Foral 13/2013 de 5 de diciembre, del Impuesto sobre la Renta
    de las Personas Fisicas (NFIRPF Bizkaia)
  - Gipuzkoa: Norma Foral 3/2014 de 17 de enero, del Impuesto sobre la Renta
    de las Personas Fisicas (NFIRPF Gipuzkoa)
  - Navarra: Ley Foral 22/1998 de 30 de diciembre, del Impuesto sobre la Renta
    de las Personas Fisicas (LFIRPF Navarra), actualizada por LF 29/2024

Key differences vs regimen comun:
  - EPSV (Entidad de Prevision Social Voluntaria) is unique to Pais Vasco
  - Foral territories have their OWN Normas Forales (not Decreto Legislativo)
  - Generally more generous deduction amounts than regimen comun
  - Each Diputacion Foral has its own tax administration

Idempotent: DELETE existing foral deductions for tax_year=2025, then INSERT all 60.

Usage:
    cd backend
    python scripts/seed_deductions_forales_2025.py
    python scripts/seed_deductions_forales_2025.py --dry-run
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
FORAL_TERRITORIES = ["Araba", "Bizkaia", "Gipuzkoa", "Navarra"]


# =============================================================================
# ARABA (ALAVA) — 15 DEDUCTIONS — IRPF 2025
# Norma Foral 33/2013 de 27 de noviembre
# =============================================================================

ARABA_2025 = [
    # 1. Nacimiento o adopcion de hijos
    {
        "code": "ARB-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 2300.0,
        "percentage": None,
        "fixed_amount": 1500.0,
        "requirements": json.dumps({
            "descripcion": "1.500 EUR por el 1er hijo, 1.900 EUR por el 2o, 2.300 EUR por el 3o y siguientes. Adopcion y acogimiento permanente equiparados.",
            "limites_renta": {},
            "condiciones": [
                "Nacimiento, adopcion o acogimiento permanente durante el ejercicio",
                "1er hijo: 1.500 EUR, 2o hijo: 1.900 EUR, 3er hijo y siguientes: 2.300 EUR",
                "El orden se determina por hijos anteriores del contribuyente",
                "Convivencia con el hijo a fecha de devengo",
                "En declaracion conjunta, deduccion unica (no duplicada)",
                "Acogimiento: solo permanente o preadoptivo, no temporal"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_araba", "label": "Ha tenido un hijo o adoptado en 2025 en Araba?", "type": "boolean"},
            {"key": "orden_hijo_araba", "label": "Que numero de hijo es (1o, 2o, 3o...)?", "type": "number"}
        ]),
        "legal_reference": "Art. 82 NF 33/2013 Araba"
    },

    # 2. Guarderia hijos menores de 3 anos
    {
        "code": "ARB-FAM-002",
        "name": "Por gastos de guarderia de hijos menores de 3 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 900.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos de guarderia de hijos menores de 3 anos. Maximo 900 EUR por hijo.",
            "limites_renta": {},
            "condiciones": [
                "Hijos menores de 3 anos a 31 de diciembre",
                "Centro de educacion infantil autorizado (primer ciclo 0-3)",
                "Solo gastos de custodia, no alimentacion ni actividades extras",
                "Maximo 900 EUR por hijo y ejercicio",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_araba", "label": "Tiene hijos menores de 3 anos en guarderia en Araba?", "type": "boolean"},
            {"key": "gasto_guarderia_araba", "label": "Importe anual pagado en guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_araba", "label": "Numero de hijos en guarderia", "type": "number"}
        ]),
        "legal_reference": "Art. 83 NF 33/2013 Araba"
    },

    # 3. EPSV - Entidad de Prevision Social Voluntaria
    {
        "code": "ARB-AHO-001",
        "name": "Por aportaciones a EPSV y planes de prevision social",
        "category": "ahorro",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 5000.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Reduccion en base imponible por aportaciones a EPSV, planes de pensiones, mutualidades de prevision social. Limite maximo 5.000 EUR anuales.",
            "limites_renta": {},
            "condiciones": [
                "Aportaciones a EPSV (Entidad de Prevision Social Voluntaria) — exclusivo Pais Vasco",
                "Tambien planes de pensiones y mutualidades de prevision social",
                "Limite conjunto: 5.000 EUR anuales",
                "Limite adicional de 8.000 EUR para aportaciones empresariales",
                "Aportaciones a favor del conyuge: max 2.400 EUR (si conyuge rentas < 8.000 EUR)",
                "Aportaciones a favor de personas con discapacidad: max 24.250 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "epsv_araba", "label": "Realiza aportaciones a EPSV o planes de prevision?", "type": "boolean"},
            {"key": "importe_epsv_araba", "label": "Importe anual aportado a EPSV/planes", "type": "number"}
        ]),
        "legal_reference": "Art. 70 NF 33/2013 Araba"
    },

    # 4. Donaciones a entidades de interes general
    {
        "code": "ARB-DON-001",
        "name": "Por donaciones a entidades de interes general",
        "category": "donaciones",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": None,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los donativos a entidades sin animo de lucro, fundaciones, asociaciones de utilidad publica y administraciones publicas.",
            "limites_renta": {},
            "condiciones": [
                "Donativos dinerarios puros y simples",
                "Entidades beneficiarias: Ley 49/2002 de regimen fiscal de entidades sin fines lucrativos",
                "Incluye: fundaciones, asociaciones utilidad publica, administraciones publicas forales",
                "Base: limite 30% de la base liquidable",
                "Requiere certificado de la entidad receptora"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_araba", "label": "Ha realizado donativos a entidades de interes general?", "type": "boolean"},
            {"key": "importe_donaciones_araba", "label": "Importe total de los donativos", "type": "number"}
        ]),
        "legal_reference": "Art. 89 NF 33/2013 Araba"
    },

    # 5. Conciliacion laboral para hombres
    {
        "code": "ARB-FAM-003",
        "name": "Por conciliacion de la vida laboral y familiar (hombres)",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR para hombres que soliciten excedencia o reduccion de jornada por cuidado de hijos o familiares dependientes.",
            "limites_renta": {},
            "condiciones": [
                "Exclusiva para contribuyentes varones",
                "Excedencia por cuidado de hijos menores de 3 anos",
                "O reduccion de jornada laboral por cuidado de familiares dependientes",
                "Duracion minima de la excedencia/reduccion: 3 meses continuados",
                "Compatible con la deduccion por nacimiento/adopcion",
                "500 EUR por ejercicio (proporcional al tiempo de excedencia si < 1 ano)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "conciliacion_hombre_araba", "label": "Es hombre y ha solicitado excedencia o reduccion de jornada por cuidado familiar?", "type": "boolean"},
            {"key": "meses_excedencia_araba", "label": "Meses de excedencia/reduccion en 2025", "type": "number"}
        ]),
        "legal_reference": "Art. 84 NF 33/2013 Araba"
    },

    # 6. Pension de viudedad
    {
        "code": "ARB-PER-001",
        "name": "Por percepcion de pension de viudedad",
        "category": "personal",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por percibir pension de viudedad de la Seguridad Social o regimenes especiales.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Percibir pension de viudedad a 31 de diciembre",
                "Pension de la Seguridad Social, Clases Pasivas o mutualidades alternativas",
                "Base imponible general + ahorro <= 30.000 EUR",
                "No es compatible con pension de jubilacion simultanea"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "pension_viudedad_araba", "label": "Percibe pension de viudedad?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 85 NF 33/2013 Araba"
    },

    # 7. Familia numerosa
    {
        "code": "ARB-FAM-004",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 900.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR para familia numerosa de categoria general, 900 EUR para categoria especial.",
            "limites_renta": {},
            "condiciones": [
                "Titulo de familia numerosa en vigor a 31 de diciembre",
                "General (3-4 hijos): 600 EUR",
                "Especial (5+ hijos o 4 con condiciones especiales): 900 EUR",
                "Titulo expedido por la Diputacion Foral de Araba o CCAA de residencia",
                "En declaracion conjunta, se aplica una sola vez"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_araba", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_araba", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 86 NF 33/2013 Araba"
    },

    # 8. Discapacidad del contribuyente
    {
        "code": "ARB-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 1500.0,
        "percentage": None,
        "fixed_amount": 700.0,
        "requirements": json.dumps({
            "descripcion": "700 EUR para discapacidad 33%-64%, 1.500 EUR para discapacidad 65% o superior.",
            "limites_renta": {},
            "condiciones": [
                "Grado de discapacidad reconocido >= 33%",
                "33%-64%: 700 EUR",
                "65% o superior: 1.500 EUR",
                "Certificado de la Diputacion Foral, IMSERSO o autonomia competente",
                "Grado acreditado a 31 de diciembre del ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_contribuyente_araba", "label": "Tiene reconocido un grado de discapacidad?", "type": "boolean"},
            {"key": "grado_discapacidad_araba", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 87 NF 33/2013 Araba"
    },

    # 9. Alquiler de vivienda habitual
    {
        "code": "ARB-VIV-001",
        "name": "Por alquiler de vivienda habitual",
        "category": "vivienda",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 1600.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades pagadas en alquiler de vivienda habitual. Maximo 1.600 EUR anuales.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Arrendamiento de vivienda habitual en Araba",
                "Contrato de arrendamiento con deposito de fianza en el organismo competente",
                "Base imponible general + ahorro <= 30.000 EUR",
                "No ser propietario de otra vivienda en el territorio",
                "Maximo 1.600 EUR por ejercicio",
                "Si varios contribuyentes comparten vivienda, se divide proporcionalmente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_araba", "label": "Vive de alquiler en Araba?", "type": "boolean"},
            {"key": "importe_alquiler_araba", "label": "Importe anual del alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 88 NF 33/2013 Araba"
    },

    # 10. Vehiculo electrico
    {
        "code": "ARB-SOS-001",
        "name": "Por adquisicion de vehiculo electrico",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculo electrico nuevo. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Vehiculo electrico puro (BEV) — no hibridos enchufables",
                "Vehiculo nuevo, primera matriculacion en el ejercicio",
                "Matriculado a nombre del contribuyente",
                "Maximo 1.500 EUR de deduccion",
                "No aplicable a vehiculos de empresa o actividad economica (solo uso particular)",
                "Precio de adquisicion sin IVA como base de deduccion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_araba", "label": "Ha adquirido un vehiculo electrico nuevo en 2025?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico_araba", "label": "Precio de adquisicion del vehiculo (sin IVA)", "type": "number"}
        ]),
        "legal_reference": "Art. 90 NF 33/2013 Araba"
    },

    # 11. Eficiencia energetica de la vivienda
    {
        "code": "ARB-SOS-002",
        "name": "Por obras de mejora de eficiencia energetica de la vivienda",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 1000.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades invertidas en mejora de eficiencia energetica de vivienda habitual. Maximo 1.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras que mejoren la calificacion energetica de la vivienda habitual",
                "Certificado de eficiencia energetica antes y despues de las obras",
                "Mejora minima de 1 letra en la calificacion energetica",
                "Solo vivienda habitual del contribuyente en Araba",
                "Maximo 1.000 EUR por ejercicio",
                "Obras realizadas por empresas instaladoras autorizadas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_araba", "label": "Ha realizado obras de mejora energetica en su vivienda habitual?", "type": "boolean"},
            {"key": "importe_obras_eficiencia_araba", "label": "Importe invertido en mejora energetica", "type": "number"}
        ]),
        "legal_reference": "Art. 91 NF 33/2013 Araba"
    },

    # 12. Edad mayor de 65 anos
    {
        "code": "ARB-PER-002",
        "name": "Por edad igual o superior a 65 anos",
        "category": "personal",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR para contribuyentes de 65 anos o mas a 31 de diciembre del ejercicio.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Edad >= 65 anos a 31 de diciembre de 2025",
                "Base imponible general + ahorro <= 30.000 EUR",
                "Residencia habitual en Araba"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "mayor_65_araba", "label": "Tiene 65 anos o mas?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 80.1 NF 33/2013 Araba"
    },

    # 13. Cuidado de menores de 6 anos
    {
        "code": "ARB-FAM-005",
        "name": "Por cuidado de hijos menores de 6 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por cada hijo menor de 6 anos que conviva con el contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Hijo menor de 6 anos a 31 de diciembre",
                "Convivencia con el contribuyente",
                "500 EUR por cada hijo",
                "Compatible con deduccion por nacimiento/adopcion",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "menores_6_araba", "label": "Tiene hijos menores de 6 anos conviviendo con usted?", "type": "boolean"},
            {"key": "num_menores_6_araba", "label": "Numero de hijos menores de 6 anos", "type": "number"}
        ]),
        "legal_reference": "Art. 83 bis NF 33/2013 Araba"
    },

    # 14. Inversion en entidades de nueva creacion
    {
        "code": "ARB-INV-001",
        "name": "Por inversion en entidades de nueva o reciente creacion",
        "category": "inversion",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 1500.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en la suscripcion de acciones/participaciones de empresas de nueva creacion. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Adquisicion de acciones o participaciones en entidades de nueva o reciente creacion (< 3 anos)",
                "La entidad debe desarrollar actividad economica real",
                "Participacion del contribuyente no puede superar el 40% del capital",
                "Mantenimiento de la inversion: minimo 3 anos",
                "Entidad domiciliada en Araba o Pais Vasco",
                "Maximo 1.500 EUR por ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_nueva_creacion_araba", "label": "Ha invertido en empresas de nueva creacion en Araba?", "type": "boolean"},
            {"key": "importe_inversion_nueva_araba", "label": "Importe invertido en nuevas empresas", "type": "number"}
        ]),
        "legal_reference": "Art. 90 bis NF 33/2013 Araba"
    },

    # 15. Discapacidad de ascendientes y descendientes
    {
        "code": "ARB-DIS-002",
        "name": "Por discapacidad de ascendientes o descendientes",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Araba",
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por ascendiente/descendiente con discapacidad 33%-64%, 600 EUR si discapacidad >= 65%.",
            "limites_renta": {},
            "condiciones": [
                "Ascendiente o descendiente con grado de discapacidad >= 33%",
                "Convivencia con el contribuyente o dependencia economica",
                "33%-64%: 300 EUR por persona",
                "65% o superior: 600 EUR por persona",
                "Rentas del ascendiente/descendiente no superiores a 8.000 EUR anuales",
                "Certificado de discapacidad en vigor"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_familiar_araba", "label": "Tiene ascendientes o descendientes con discapacidad reconocida?", "type": "boolean"},
            {"key": "grado_discapacidad_familiar_araba", "label": "Grado de discapacidad del familiar (%)", "type": "number"},
            {"key": "num_familiares_discapacidad_araba", "label": "Numero de familiares con discapacidad", "type": "number"}
        ]),
        "legal_reference": "Art. 87 bis NF 33/2013 Araba"
    },
]


# =============================================================================
# BIZKAIA — 15 DEDUCTIONS — IRPF 2025
# Norma Foral 13/2013 de 5 de diciembre
# =============================================================================

BIZKAIA_2025 = [
    # 1. Nacimiento o adopcion de hijos
    {
        "code": "BIZ-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 1800.0,
        "percentage": None,
        "fixed_amount": 1200.0,
        "requirements": json.dumps({
            "descripcion": "1.200 EUR por el 1er hijo, 1.500 EUR por el 2o, 1.800 EUR por el 3o y siguientes. Adopcion y acogimiento permanente equiparados.",
            "limites_renta": {},
            "condiciones": [
                "Nacimiento, adopcion o acogimiento permanente durante el ejercicio",
                "1er hijo: 1.200 EUR, 2o hijo: 1.500 EUR, 3er hijo y siguientes: 1.800 EUR",
                "El orden se determina por hijos anteriores del contribuyente",
                "Convivencia con el hijo a fecha de devengo",
                "En declaracion conjunta, deduccion unica (no duplicada)",
                "Acogimiento: solo permanente o preadoptivo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_bizkaia", "label": "Ha tenido un hijo o adoptado en 2025 en Bizkaia?", "type": "boolean"},
            {"key": "orden_hijo_bizkaia", "label": "Que numero de hijo es (1o, 2o, 3o...)?", "type": "number"}
        ]),
        "legal_reference": "Art. 82 NF 13/2013 Bizkaia"
    },

    # 2. Guarderia hijos menores de 3 anos
    {
        "code": "BIZ-FAM-002",
        "name": "Por gastos de guarderia de hijos menores de 3 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 900.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos de guarderia de hijos menores de 3 anos. Maximo 900 EUR por hijo.",
            "limites_renta": {},
            "condiciones": [
                "Hijos menores de 3 anos a 31 de diciembre",
                "Centro de educacion infantil autorizado (primer ciclo 0-3)",
                "Solo gastos de custodia, no alimentacion ni actividades extras",
                "Maximo 900 EUR por hijo y ejercicio",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_bizkaia", "label": "Tiene hijos menores de 3 anos en guarderia en Bizkaia?", "type": "boolean"},
            {"key": "gasto_guarderia_bizkaia", "label": "Importe anual pagado en guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_bizkaia", "label": "Numero de hijos en guarderia", "type": "number"}
        ]),
        "legal_reference": "Art. 83 NF 13/2013 Bizkaia"
    },

    # 3. EPSV
    {
        "code": "BIZ-AHO-001",
        "name": "Por aportaciones a EPSV y planes de prevision social",
        "category": "ahorro",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 5000.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Reduccion en base imponible por aportaciones a EPSV, planes de pensiones, mutualidades. Limite maximo 5.000 EUR anuales.",
            "limites_renta": {},
            "condiciones": [
                "Aportaciones a EPSV (Entidad de Prevision Social Voluntaria) — exclusivo Pais Vasco",
                "Tambien planes de pensiones y mutualidades de prevision social",
                "Limite conjunto: 5.000 EUR anuales",
                "Limite adicional de 8.000 EUR para aportaciones empresariales",
                "Aportaciones a favor del conyuge: max 2.400 EUR (si conyuge rentas < 8.000 EUR)",
                "Aportaciones a favor de personas con discapacidad: max 24.250 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "epsv_bizkaia", "label": "Realiza aportaciones a EPSV o planes de prevision?", "type": "boolean"},
            {"key": "importe_epsv_bizkaia", "label": "Importe anual aportado a EPSV/planes", "type": "number"}
        ]),
        "legal_reference": "Art. 70 NF 13/2013 Bizkaia"
    },

    # 4. Donaciones
    {
        "code": "BIZ-DON-001",
        "name": "Por donaciones a entidades de interes general",
        "category": "donaciones",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": None,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los donativos a entidades sin animo de lucro, fundaciones, asociaciones de utilidad publica.",
            "limites_renta": {},
            "condiciones": [
                "Donativos dinerarios puros y simples",
                "Entidades beneficiarias segun normativa foral de mecenazgo",
                "Incluye: fundaciones, asociaciones utilidad publica, administraciones publicas forales",
                "Base: limite 30% de la base liquidable",
                "Requiere certificado de la entidad receptora"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_bizkaia", "label": "Ha realizado donativos a entidades de interes general?", "type": "boolean"},
            {"key": "importe_donaciones_bizkaia", "label": "Importe total de los donativos", "type": "number"}
        ]),
        "legal_reference": "Art. 89 NF 13/2013 Bizkaia"
    },

    # 5. Familia numerosa
    {
        "code": "BIZ-FAM-003",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 900.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR para familia numerosa general, 900 EUR para categoria especial.",
            "limites_renta": {},
            "condiciones": [
                "Titulo de familia numerosa en vigor a 31 de diciembre",
                "General (3-4 hijos): 600 EUR",
                "Especial (5+ hijos o 4 con condiciones especiales): 900 EUR",
                "Titulo expedido por la Diputacion Foral de Bizkaia o CCAA de residencia",
                "En declaracion conjunta, se aplica una sola vez"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_bizkaia", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_bizkaia", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 86 NF 13/2013 Bizkaia"
    },

    # 6. Discapacidad del contribuyente
    {
        "code": "BIZ-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 1500.0,
        "percentage": None,
        "fixed_amount": 700.0,
        "requirements": json.dumps({
            "descripcion": "700 EUR para discapacidad 33%-64%, 1.500 EUR para discapacidad 65% o superior.",
            "limites_renta": {},
            "condiciones": [
                "Grado de discapacidad reconocido >= 33%",
                "33%-64%: 700 EUR",
                "65% o superior: 1.500 EUR",
                "Certificado de la Diputacion Foral, IMSERSO o autonomia competente",
                "Grado acreditado a 31 de diciembre del ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_contribuyente_bizkaia", "label": "Tiene reconocido un grado de discapacidad?", "type": "boolean"},
            {"key": "grado_discapacidad_bizkaia", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 87 NF 13/2013 Bizkaia"
    },

    # 7. Alquiler de vivienda habitual
    {
        "code": "BIZ-VIV-001",
        "name": "Por alquiler de vivienda habitual",
        "category": "vivienda",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 1600.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades pagadas en alquiler de vivienda habitual. Maximo 1.600 EUR anuales.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Arrendamiento de vivienda habitual en Bizkaia",
                "Contrato de arrendamiento registrado",
                "Base imponible general + ahorro <= 30.000 EUR",
                "No ser propietario de otra vivienda en el territorio",
                "Maximo 1.600 EUR por ejercicio",
                "Si varios contribuyentes comparten vivienda, se divide proporcionalmente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_bizkaia", "label": "Vive de alquiler en Bizkaia?", "type": "boolean"},
            {"key": "importe_alquiler_bizkaia", "label": "Importe anual del alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 88 NF 13/2013 Bizkaia"
    },

    # 8. Vehiculo electrico
    {
        "code": "BIZ-SOS-001",
        "name": "Por adquisicion de vehiculo electrico",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculo electrico nuevo. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Vehiculo electrico puro (BEV) — no hibridos enchufables",
                "Vehiculo nuevo, primera matriculacion en el ejercicio",
                "Matriculado a nombre del contribuyente",
                "Maximo 1.500 EUR de deduccion",
                "No aplicable a vehiculos de empresa o actividad economica",
                "Precio de adquisicion sin IVA como base de deduccion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_bizkaia", "label": "Ha adquirido un vehiculo electrico nuevo en 2025?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico_bizkaia", "label": "Precio de adquisicion del vehiculo (sin IVA)", "type": "number"}
        ]),
        "legal_reference": "Art. 90 NF 13/2013 Bizkaia"
    },

    # 9. Eficiencia energetica
    {
        "code": "BIZ-SOS-002",
        "name": "Por obras de mejora de eficiencia energetica de la vivienda",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 1000.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades invertidas en mejora de eficiencia energetica de vivienda habitual. Maximo 1.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras que mejoren la calificacion energetica de la vivienda habitual",
                "Certificado de eficiencia energetica antes y despues",
                "Mejora minima de 1 letra en la calificacion energetica",
                "Solo vivienda habitual del contribuyente en Bizkaia",
                "Maximo 1.000 EUR por ejercicio",
                "Obras realizadas por empresas instaladoras autorizadas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_bizkaia", "label": "Ha realizado obras de mejora energetica en su vivienda habitual?", "type": "boolean"},
            {"key": "importe_obras_eficiencia_bizkaia", "label": "Importe invertido en mejora energetica", "type": "number"}
        ]),
        "legal_reference": "Art. 91 NF 13/2013 Bizkaia"
    },

    # 10. Edad mayor de 65 anos
    {
        "code": "BIZ-PER-001",
        "name": "Por edad igual o superior a 65 anos",
        "category": "personal",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR para contribuyentes de 65 anos o mas a 31 de diciembre del ejercicio.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Edad >= 65 anos a 31 de diciembre de 2025",
                "Base imponible general + ahorro <= 30.000 EUR",
                "Residencia habitual en Bizkaia"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "mayor_65_bizkaia", "label": "Tiene 65 anos o mas?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 80.1 NF 13/2013 Bizkaia"
    },

    # 11. Cuidado de menores de 6 anos
    {
        "code": "BIZ-FAM-004",
        "name": "Por cuidado de hijos menores de 6 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por cada hijo menor de 6 anos que conviva con el contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Hijo menor de 6 anos a 31 de diciembre",
                "Convivencia con el contribuyente",
                "500 EUR por cada hijo",
                "Compatible con deduccion por nacimiento/adopcion",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "menores_6_bizkaia", "label": "Tiene hijos menores de 6 anos conviviendo con usted?", "type": "boolean"},
            {"key": "num_menores_6_bizkaia", "label": "Numero de hijos menores de 6 anos", "type": "number"}
        ]),
        "legal_reference": "Art. 83 bis NF 13/2013 Bizkaia"
    },

    # 12. Familia monoparental
    {
        "code": "BIZ-FAM-005",
        "name": "Por familia monoparental",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR para familias monoparentales con hijos a cargo.",
            "limites_renta": {},
            "condiciones": [
                "Familia monoparental: un solo progenitor con hijos menores a cargo",
                "Hijos menores de 18 anos (o mayores con discapacidad) conviviendo con el contribuyente",
                "No convivir con otro progenitor ni con pareja de hecho",
                "500 EUR por ejercicio",
                "No acumulable con deduccion por tributacion conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "monoparental_bizkaia", "label": "Es familia monoparental con hijos menores a cargo?", "type": "boolean"},
            {"key": "num_hijos_monoparental_bizkaia", "label": "Numero de hijos a cargo", "type": "number"}
        ]),
        "legal_reference": "Art. 84 NF 13/2013 Bizkaia"
    },

    # 13. Inversion en empresas de nueva creacion
    {
        "code": "BIZ-INV-001",
        "name": "Por inversion en empresas de nueva o reciente creacion",
        "category": "inversion",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 1500.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en suscripcion de acciones/participaciones de empresas nuevas. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Adquisicion de acciones o participaciones en entidades de nueva creacion (< 3 anos)",
                "La entidad debe desarrollar actividad economica real",
                "Participacion del contribuyente no puede superar el 40% del capital",
                "Mantenimiento de la inversion: minimo 3 anos",
                "Entidad domiciliada en Bizkaia o Pais Vasco",
                "Maximo 1.500 EUR por ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_nueva_creacion_bizkaia", "label": "Ha invertido en empresas de nueva creacion en Bizkaia?", "type": "boolean"},
            {"key": "importe_inversion_nueva_bizkaia", "label": "Importe invertido en nuevas empresas", "type": "number"}
        ]),
        "legal_reference": "Art. 90 bis NF 13/2013 Bizkaia"
    },

    # 14. Discapacidad de descendientes
    {
        "code": "BIZ-DIS-002",
        "name": "Por discapacidad de descendientes",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por descendiente con discapacidad 33%-64%, 600 EUR si discapacidad >= 65%.",
            "limites_renta": {},
            "condiciones": [
                "Descendiente con grado de discapacidad >= 33%",
                "Convivencia con el contribuyente o dependencia economica",
                "33%-64%: 300 EUR por persona",
                "65% o superior: 600 EUR por persona",
                "Rentas del descendiente no superiores a 8.000 EUR anuales",
                "Certificado de discapacidad en vigor"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_descendientes_bizkaia", "label": "Tiene descendientes con discapacidad reconocida?", "type": "boolean"},
            {"key": "grado_discapacidad_desc_bizkaia", "label": "Grado de discapacidad del descendiente (%)", "type": "number"},
            {"key": "num_descendientes_disc_bizkaia", "label": "Numero de descendientes con discapacidad", "type": "number"}
        ]),
        "legal_reference": "Art. 87 bis NF 13/2013 Bizkaia"
    },

    # 15. Participacion en actividades culturales
    {
        "code": "BIZ-CUL-001",
        "name": "Por participacion en actividades culturales",
        "category": "cultura",
        "scope": "foral",
        "ccaa": "Bizkaia",
        "max_amount": 500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de los gastos en actividades culturales reconocidas por la Diputacion Foral. Maximo 500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Gastos en actividades culturales: teatro, musica, danza, cine, museos, exposiciones",
                "Actividades organizadas en Bizkaia o Pais Vasco",
                "Entradas y abonos a espectaculos culturales en vivo",
                "Suscripciones a plataformas culturales vascas reconocidas",
                "Maximo 500 EUR por ejercicio",
                "Requiere factura o justificante de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "actividades_culturales_bizkaia", "label": "Ha tenido gastos en actividades culturales en Bizkaia?", "type": "boolean"},
            {"key": "importe_cultura_bizkaia", "label": "Importe gastado en actividades culturales", "type": "number"}
        ]),
        "legal_reference": "Art. 92 NF 13/2013 Bizkaia"
    },
]


# =============================================================================
# GIPUZKOA — 15 DEDUCTIONS — IRPF 2025
# Norma Foral 3/2014 de 17 de enero
# =============================================================================

GIPUZKOA_2025 = [
    # 1. Nacimiento o adopcion de hijos
    {
        "code": "GIP-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 1800.0,
        "percentage": None,
        "fixed_amount": 1200.0,
        "requirements": json.dumps({
            "descripcion": "1.200 EUR por el 1er hijo, 1.500 EUR por el 2o, 1.800 EUR por el 3o y siguientes.",
            "limites_renta": {},
            "condiciones": [
                "Nacimiento, adopcion o acogimiento permanente durante el ejercicio",
                "1er hijo: 1.200 EUR, 2o hijo: 1.500 EUR, 3er hijo y siguientes: 1.800 EUR",
                "El orden se determina por hijos anteriores del contribuyente",
                "Convivencia con el hijo a fecha de devengo",
                "En declaracion conjunta, deduccion unica (no duplicada)",
                "Acogimiento: solo permanente o preadoptivo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_gipuzkoa", "label": "Ha tenido un hijo o adoptado en 2025 en Gipuzkoa?", "type": "boolean"},
            {"key": "orden_hijo_gipuzkoa", "label": "Que numero de hijo es (1o, 2o, 3o...)?", "type": "number"}
        ]),
        "legal_reference": "Art. 90 NF 3/2014 Gipuzkoa"
    },

    # 2. Guarderia hijos menores de 3 anos
    {
        "code": "GIP-FAM-002",
        "name": "Por gastos de guarderia de hijos menores de 3 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 900.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos de guarderia de hijos menores de 3 anos. Maximo 900 EUR por hijo.",
            "limites_renta": {},
            "condiciones": [
                "Hijos menores de 3 anos a 31 de diciembre",
                "Centro de educacion infantil autorizado (primer ciclo 0-3)",
                "Solo gastos de custodia, no alimentacion ni actividades extras",
                "Maximo 900 EUR por hijo y ejercicio",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_gipuzkoa", "label": "Tiene hijos menores de 3 anos en guarderia en Gipuzkoa?", "type": "boolean"},
            {"key": "gasto_guarderia_gipuzkoa", "label": "Importe anual pagado en guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_gipuzkoa", "label": "Numero de hijos en guarderia", "type": "number"}
        ]),
        "legal_reference": "Art. 91 NF 3/2014 Gipuzkoa"
    },

    # 3. EPSV
    {
        "code": "GIP-AHO-001",
        "name": "Por aportaciones a EPSV y planes de prevision social",
        "category": "ahorro",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 5000.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Reduccion en base imponible por aportaciones a EPSV, planes de pensiones, mutualidades. Limite maximo 5.000 EUR anuales.",
            "limites_renta": {},
            "condiciones": [
                "Aportaciones a EPSV (Entidad de Prevision Social Voluntaria) — exclusivo Pais Vasco",
                "Tambien planes de pensiones y mutualidades de prevision social",
                "Limite conjunto: 5.000 EUR anuales",
                "Limite adicional de 8.000 EUR para aportaciones empresariales",
                "Aportaciones a favor del conyuge: max 2.400 EUR (si conyuge rentas < 8.000 EUR)",
                "Aportaciones a favor de personas con discapacidad: max 24.250 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "epsv_gipuzkoa", "label": "Realiza aportaciones a EPSV o planes de prevision?", "type": "boolean"},
            {"key": "importe_epsv_gipuzkoa", "label": "Importe anual aportado a EPSV/planes", "type": "number"}
        ]),
        "legal_reference": "Art. 70 NF 3/2014 Gipuzkoa"
    },

    # 4. Donaciones
    {
        "code": "GIP-DON-001",
        "name": "Por donaciones a entidades de interes general",
        "category": "donaciones",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": None,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los donativos a entidades sin animo de lucro, fundaciones, asociaciones de utilidad publica.",
            "limites_renta": {},
            "condiciones": [
                "Donativos dinerarios puros y simples",
                "Entidades beneficiarias segun normativa foral de mecenazgo",
                "Incluye: fundaciones, asociaciones utilidad publica, administraciones publicas forales",
                "Base: limite 30% de la base liquidable",
                "Requiere certificado de la entidad receptora"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_gipuzkoa", "label": "Ha realizado donativos a entidades de interes general?", "type": "boolean"},
            {"key": "importe_donaciones_gipuzkoa", "label": "Importe total de los donativos", "type": "number"}
        ]),
        "legal_reference": "Art. 97 NF 3/2014 Gipuzkoa"
    },

    # 5. Familia numerosa
    {
        "code": "GIP-FAM-003",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 900.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR para familia numerosa general, 900 EUR para categoria especial.",
            "limites_renta": {},
            "condiciones": [
                "Titulo de familia numerosa en vigor a 31 de diciembre",
                "General (3-4 hijos): 600 EUR",
                "Especial (5+ hijos o 4 con condiciones especiales): 900 EUR",
                "Titulo expedido por la Diputacion Foral de Gipuzkoa o CCAA de residencia",
                "En declaracion conjunta, se aplica una sola vez"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_gipuzkoa", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_gipuzkoa", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 94 NF 3/2014 Gipuzkoa"
    },

    # 6. Discapacidad del contribuyente
    {
        "code": "GIP-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 1500.0,
        "percentage": None,
        "fixed_amount": 700.0,
        "requirements": json.dumps({
            "descripcion": "700 EUR para discapacidad 33%-64%, 1.500 EUR para discapacidad 65% o superior.",
            "limites_renta": {},
            "condiciones": [
                "Grado de discapacidad reconocido >= 33%",
                "33%-64%: 700 EUR",
                "65% o superior: 1.500 EUR",
                "Certificado de la Diputacion Foral, IMSERSO o autonomia competente",
                "Grado acreditado a 31 de diciembre del ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_contribuyente_gipuzkoa", "label": "Tiene reconocido un grado de discapacidad?", "type": "boolean"},
            {"key": "grado_discapacidad_gipuzkoa", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 95 NF 3/2014 Gipuzkoa"
    },

    # 7. Alquiler de vivienda habitual
    {
        "code": "GIP-VIV-001",
        "name": "Por alquiler de vivienda habitual",
        "category": "vivienda",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 1600.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades pagadas en alquiler de vivienda habitual. Maximo 1.600 EUR anuales.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Arrendamiento de vivienda habitual en Gipuzkoa",
                "Contrato de arrendamiento registrado",
                "Base imponible general + ahorro <= 30.000 EUR",
                "No ser propietario de otra vivienda en el territorio",
                "Maximo 1.600 EUR por ejercicio",
                "Si varios contribuyentes comparten vivienda, se divide proporcionalmente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_gipuzkoa", "label": "Vive de alquiler en Gipuzkoa?", "type": "boolean"},
            {"key": "importe_alquiler_gipuzkoa", "label": "Importe anual del alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 96 NF 3/2014 Gipuzkoa"
    },

    # 8. Vehiculo electrico
    {
        "code": "GIP-SOS-001",
        "name": "Por adquisicion de vehiculo electrico",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculo electrico nuevo. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Vehiculo electrico puro (BEV) — no hibridos enchufables",
                "Vehiculo nuevo, primera matriculacion en el ejercicio",
                "Matriculado a nombre del contribuyente",
                "Maximo 1.500 EUR de deduccion",
                "No aplicable a vehiculos de empresa o actividad economica",
                "Precio de adquisicion sin IVA como base de deduccion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_gipuzkoa", "label": "Ha adquirido un vehiculo electrico nuevo en 2025?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico_gipuzkoa", "label": "Precio de adquisicion del vehiculo (sin IVA)", "type": "number"}
        ]),
        "legal_reference": "Art. 98 NF 3/2014 Gipuzkoa"
    },

    # 9. Eficiencia energetica
    {
        "code": "GIP-SOS-002",
        "name": "Por obras de mejora de eficiencia energetica de la vivienda",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 1000.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades invertidas en mejora de eficiencia energetica de vivienda habitual. Maximo 1.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras que mejoren la calificacion energetica de la vivienda habitual",
                "Certificado de eficiencia energetica antes y despues",
                "Mejora minima de 1 letra en la calificacion energetica",
                "Solo vivienda habitual del contribuyente en Gipuzkoa",
                "Maximo 1.000 EUR por ejercicio",
                "Obras realizadas por empresas instaladoras autorizadas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_gipuzkoa", "label": "Ha realizado obras de mejora energetica en su vivienda habitual?", "type": "boolean"},
            {"key": "importe_obras_eficiencia_gipuzkoa", "label": "Importe invertido en mejora energetica", "type": "number"}
        ]),
        "legal_reference": "Art. 99 NF 3/2014 Gipuzkoa"
    },

    # 10. Edad mayor de 65 anos
    {
        "code": "GIP-PER-001",
        "name": "Por edad igual o superior a 65 anos",
        "category": "personal",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR para contribuyentes de 65 anos o mas a 31 de diciembre del ejercicio.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Edad >= 65 anos a 31 de diciembre de 2025",
                "Base imponible general + ahorro <= 30.000 EUR",
                "Residencia habitual en Gipuzkoa"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "mayor_65_gipuzkoa", "label": "Tiene 65 anos o mas?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 88.1 NF 3/2014 Gipuzkoa"
    },

    # 11. Cuidado de menores de 6 anos
    {
        "code": "GIP-FAM-004",
        "name": "Por cuidado de hijos menores de 6 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por cada hijo menor de 6 anos que conviva con el contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Hijo menor de 6 anos a 31 de diciembre",
                "Convivencia con el contribuyente",
                "500 EUR por cada hijo",
                "Compatible con deduccion por nacimiento/adopcion",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "menores_6_gipuzkoa", "label": "Tiene hijos menores de 6 anos conviviendo con usted?", "type": "boolean"},
            {"key": "num_menores_6_gipuzkoa", "label": "Numero de hijos menores de 6 anos", "type": "number"}
        ]),
        "legal_reference": "Art. 91 bis NF 3/2014 Gipuzkoa"
    },

    # 12. Familia monoparental
    {
        "code": "GIP-FAM-005",
        "name": "Por familia monoparental",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR para familias monoparentales con hijos a cargo.",
            "limites_renta": {},
            "condiciones": [
                "Familia monoparental: un solo progenitor con hijos menores a cargo",
                "Hijos menores de 18 anos (o mayores con discapacidad) conviviendo con el contribuyente",
                "No convivir con otro progenitor ni con pareja de hecho",
                "500 EUR por ejercicio",
                "No acumulable con deduccion por tributacion conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "monoparental_gipuzkoa", "label": "Es familia monoparental con hijos menores a cargo?", "type": "boolean"},
            {"key": "num_hijos_monoparental_gipuzkoa", "label": "Numero de hijos a cargo", "type": "number"}
        ]),
        "legal_reference": "Art. 92 NF 3/2014 Gipuzkoa"
    },

    # 13. Inversion en empresas de nueva creacion
    {
        "code": "GIP-INV-001",
        "name": "Por inversion en empresas de nueva o reciente creacion",
        "category": "inversion",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 1500.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en suscripcion de acciones/participaciones de empresas nuevas. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Adquisicion de acciones o participaciones en entidades de nueva creacion (< 3 anos)",
                "La entidad debe desarrollar actividad economica real",
                "Participacion del contribuyente no puede superar el 40% del capital",
                "Mantenimiento de la inversion: minimo 3 anos",
                "Entidad domiciliada en Gipuzkoa o Pais Vasco",
                "Maximo 1.500 EUR por ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_nueva_creacion_gipuzkoa", "label": "Ha invertido en empresas de nueva creacion en Gipuzkoa?", "type": "boolean"},
            {"key": "importe_inversion_nueva_gipuzkoa", "label": "Importe invertido en nuevas empresas", "type": "number"}
        ]),
        "legal_reference": "Art. 98 bis NF 3/2014 Gipuzkoa"
    },

    # 14. Discapacidad de descendientes
    {
        "code": "GIP-DIS-002",
        "name": "Por discapacidad de descendientes",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por descendiente con discapacidad 33%-64%, 600 EUR si discapacidad >= 65%.",
            "limites_renta": {},
            "condiciones": [
                "Descendiente con grado de discapacidad >= 33%",
                "Convivencia con el contribuyente o dependencia economica",
                "33%-64%: 300 EUR por persona",
                "65% o superior: 600 EUR por persona",
                "Rentas del descendiente no superiores a 8.000 EUR anuales",
                "Certificado de discapacidad en vigor"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_descendientes_gipuzkoa", "label": "Tiene descendientes con discapacidad reconocida?", "type": "boolean"},
            {"key": "grado_discapacidad_desc_gipuzkoa", "label": "Grado de discapacidad del descendiente (%)", "type": "number"},
            {"key": "num_descendientes_disc_gipuzkoa", "label": "Numero de descendientes con discapacidad", "type": "number"}
        ]),
        "legal_reference": "Art. 95 bis NF 3/2014 Gipuzkoa"
    },

    # 15. Insercion laboral
    {
        "code": "GIP-EMP-001",
        "name": "Por insercion laboral de nuevos empleados",
        "category": "empleo",
        "scope": "foral",
        "ccaa": "Gipuzkoa",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por cada nuevo empleado contratado de forma indefinida. Aplicable a contribuyentes con actividad economica.",
            "limites_renta": {},
            "condiciones": [
                "Contribuyente con actividad economica (autonomo o empresario individual)",
                "Contratacion indefinida de nuevos empleados durante el ejercicio",
                "Contrato a tiempo completo (proporcional si tiempo parcial)",
                "Mantenimiento del empleo: minimo 2 anos desde la contratacion",
                "No computar familiares hasta 2o grado como nuevos empleados",
                "500 EUR por cada nuevo empleo neto creado"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "insercion_laboral_gipuzkoa", "label": "Ha contratado nuevos empleados de forma indefinida en 2025?", "type": "boolean"},
            {"key": "num_nuevos_empleados_gipuzkoa", "label": "Numero de nuevos empleados contratados", "type": "number"}
        ]),
        "legal_reference": "Art. 100 NF 3/2014 Gipuzkoa"
    },
]


# =============================================================================
# NAVARRA — 15 DEDUCTIONS — IRPF 2025
# Ley Foral 22/1998 de 30 de diciembre (actualizada LF 29/2024)
# =============================================================================

NAVARRA_2025 = [
    # 1. Nacimiento o adopcion de hijos
    {
        "code": "NAV-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 1400.0,
        "percentage": None,
        "fixed_amount": 1000.0,
        "requirements": json.dumps({
            "descripcion": "1.000 EUR por el 1er hijo, 1.200 EUR por el 2o, 1.400 EUR por el 3o y siguientes. Adopcion equiparada.",
            "limites_renta": {},
            "condiciones": [
                "Nacimiento, adopcion o acogimiento permanente durante el ejercicio",
                "1er hijo: 1.000 EUR, 2o hijo: 1.200 EUR, 3er hijo y siguientes: 1.400 EUR",
                "El orden se determina por hijos anteriores del contribuyente",
                "Convivencia con el hijo a fecha de devengo",
                "En declaracion conjunta, deduccion unica (no duplicada)",
                "Acogimiento: solo permanente o preadoptivo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_navarra", "label": "Ha tenido un hijo o adoptado en 2025 en Navarra?", "type": "boolean"},
            {"key": "orden_hijo_navarra", "label": "Que numero de hijo es (1o, 2o, 3o...)?", "type": "number"}
        ]),
        "legal_reference": "Art. 62.1 LF 22/1998 Navarra"
    },

    # 2. Guarderia hijos menores de 3 anos
    {
        "code": "NAV-FAM-002",
        "name": "Por gastos de guarderia de hijos menores de 3 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 900.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos de guarderia de hijos menores de 3 anos. Maximo 900 EUR por hijo.",
            "limites_renta": {},
            "condiciones": [
                "Hijos menores de 3 anos a 31 de diciembre",
                "Centro de educacion infantil autorizado (primer ciclo 0-3)",
                "Solo gastos de custodia, no alimentacion ni actividades extras",
                "Maximo 900 EUR por hijo y ejercicio",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_navarra", "label": "Tiene hijos menores de 3 anos en guarderia en Navarra?", "type": "boolean"},
            {"key": "gasto_guarderia_navarra", "label": "Importe anual pagado en guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_navarra", "label": "Numero de hijos en guarderia", "type": "number"}
        ]),
        "legal_reference": "Art. 62.8 LF 22/1998 Navarra"
    },

    # 3. Plan de prevision social / EPSV
    {
        "code": "NAV-AHO-001",
        "name": "Por aportaciones a planes de prevision social y EPSV",
        "category": "ahorro",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 5000.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Reduccion en base imponible por aportaciones a planes de pensiones, EPSV, mutualidades. Limite maximo 5.000 EUR anuales.",
            "limites_renta": {},
            "condiciones": [
                "Aportaciones a planes de pensiones regulados por normativa foral navarra",
                "Tambien EPSV y mutualidades de prevision social",
                "Limite conjunto: 5.000 EUR anuales",
                "Limite adicional para aportaciones empresariales",
                "Aportaciones a favor del conyuge: max 2.400 EUR",
                "Aportaciones a favor de personas con discapacidad: limites incrementados"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "prevision_social_navarra", "label": "Realiza aportaciones a planes de prevision social o EPSV?", "type": "boolean"},
            {"key": "importe_prevision_navarra", "label": "Importe anual aportado", "type": "number"}
        ]),
        "legal_reference": "Art. 55 LF 22/1998 Navarra"
    },

    # 4. Donaciones
    {
        "code": "NAV-DON-001",
        "name": "Por donaciones a entidades de interes general",
        "category": "donaciones",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de los donativos a entidades sin animo de lucro, fundaciones, asociaciones de utilidad publica y administraciones publicas navarras.",
            "limites_renta": {},
            "condiciones": [
                "Donativos dinerarios puros y simples",
                "Entidades beneficiarias segun Ley Foral de mecenazgo de Navarra",
                "Incluye: fundaciones, asociaciones utilidad publica, Gobierno de Navarra, entidades locales",
                "Base: limite 30% de la base liquidable",
                "Requiere certificado de la entidad receptora"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_navarra", "label": "Ha realizado donativos a entidades de interes general?", "type": "boolean"},
            {"key": "importe_donaciones_navarra", "label": "Importe total de los donativos", "type": "number"}
        ]),
        "legal_reference": "Art. 62.5 LF 22/1998 Navarra"
    },

    # 5. Bicicleta urbana sostenible
    {
        "code": "NAV-SOS-001",
        "name": "Por adquisicion de bicicleta urbana para movilidad sostenible",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 200.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion por adquisicion de bicicleta urbana para uso cotidiano. Maximo 200 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Adquisicion de bicicleta nueva (convencional o electrica) para desplazamientos urbanos",
                "Factura de compra a nombre del contribuyente",
                "Bicicleta para uso personal y desplazamiento habitual (no deportivo)",
                "Maximo 200 EUR por contribuyente y ejercicio",
                "Compatible con otras deducciones de sostenibilidad",
                "Incluye bicicletas electricas (e-bikes) con pedaleo asistido"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "bicicleta_navarra", "label": "Ha adquirido una bicicleta urbana nueva en 2025?", "type": "boolean"},
            {"key": "importe_bicicleta_navarra", "label": "Precio de la bicicleta", "type": "number"}
        ]),
        "legal_reference": "Art. 62.10 LF 22/1998 Navarra (mod. LF 29/2024)"
    },

    # 6. Familia numerosa
    {
        "code": "NAV-FAM-003",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 800.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR para familia numerosa general, 800 EUR para categoria especial.",
            "limites_renta": {},
            "condiciones": [
                "Titulo de familia numerosa en vigor a 31 de diciembre",
                "General (3-4 hijos): 500 EUR",
                "Especial (5+ hijos o 4 con condiciones especiales): 800 EUR",
                "Titulo expedido por el Gobierno de Navarra o CCAA de residencia",
                "En declaracion conjunta, se aplica una sola vez"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_navarra", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_navarra", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 62.3 LF 22/1998 Navarra"
    },

    # 7. Discapacidad del contribuyente
    {
        "code": "NAV-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 1500.0,
        "percentage": None,
        "fixed_amount": 700.0,
        "requirements": json.dumps({
            "descripcion": "700 EUR para discapacidad 33%-64%, 1.500 EUR para discapacidad 65% o superior.",
            "limites_renta": {},
            "condiciones": [
                "Grado de discapacidad reconocido >= 33%",
                "33%-64%: 700 EUR",
                "65% o superior: 1.500 EUR",
                "Certificado del Gobierno de Navarra (ANADP) o autonomia competente",
                "Grado acreditado a 31 de diciembre del ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_contribuyente_navarra", "label": "Tiene reconocido un grado de discapacidad?", "type": "boolean"},
            {"key": "grado_discapacidad_navarra", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 62.4 LF 22/1998 Navarra"
    },

    # 8. Alquiler de vivienda habitual
    {
        "code": "NAV-VIV-001",
        "name": "Por alquiler de vivienda habitual",
        "category": "vivienda",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 1200.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades pagadas en alquiler de vivienda habitual. Maximo 1.200 EUR anuales.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Arrendamiento de vivienda habitual en Navarra",
                "Contrato de arrendamiento con deposito de fianza en el Gobierno de Navarra",
                "Base imponible general + ahorro <= 30.000 EUR",
                "No ser propietario de otra vivienda en Navarra",
                "Maximo 1.200 EUR por ejercicio",
                "Edad < 30 anos o familia con hijos: limite incrementado a 1.500 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_navarra", "label": "Vive de alquiler en Navarra?", "type": "boolean"},
            {"key": "importe_alquiler_navarra", "label": "Importe anual del alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 62.6 LF 22/1998 Navarra"
    },

    # 9. Vehiculo electrico o hibrido enchufable
    {
        "code": "NAV-SOS-002",
        "name": "Por adquisicion de vehiculo electrico o hibrido enchufable",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 2000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculo electrico o hibrido enchufable. Maximo 2.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Vehiculo electrico puro (BEV) o hibrido enchufable (PHEV)",
                "Vehiculo nuevo, primera matriculacion en el ejercicio",
                "Matriculado a nombre del contribuyente en Navarra",
                "Maximo 2.000 EUR de deduccion",
                "PHEV: autonomia electrica minima 40 km y emisiones < 50 g CO2/km",
                "No aplicable a vehiculos de empresa o actividad economica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_navarra", "label": "Ha adquirido un vehiculo electrico o hibrido enchufable nuevo en 2025?", "type": "boolean"},
            {"key": "precio_vehiculo_navarra", "label": "Precio de adquisicion del vehiculo (sin IVA)", "type": "number"},
            {"key": "tipo_vehiculo_navarra", "label": "Tipo de vehiculo", "type": "select", "options": ["electrico", "hibrido_enchufable"]}
        ]),
        "legal_reference": "Art. 62.9 LF 22/1998 Navarra (mod. LF 29/2024)"
    },

    # 10. Eficiencia energetica
    {
        "code": "NAV-SOS-003",
        "name": "Por obras de mejora de eficiencia energetica de la vivienda",
        "category": "sostenibilidad",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en mejora de eficiencia energetica de vivienda habitual. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras que mejoren la calificacion energetica de la vivienda habitual",
                "Certificado de eficiencia energetica antes y despues de las obras",
                "Mejora minima de 1 letra en la calificacion energetica",
                "Solo vivienda habitual del contribuyente en Navarra",
                "Maximo 1.500 EUR por ejercicio",
                "Obras realizadas por empresas instaladoras autorizadas",
                "Navarra: porcentaje e importe mas generosos que Pais Vasco (15% vs 10%)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_navarra", "label": "Ha realizado obras de mejora energetica en su vivienda habitual?", "type": "boolean"},
            {"key": "importe_obras_eficiencia_navarra", "label": "Importe invertido en mejora energetica", "type": "number"}
        ]),
        "legal_reference": "Art. 62.11 LF 22/1998 Navarra (mod. LF 29/2024)"
    },

    # 11. Edad mayor de 65 anos
    {
        "code": "NAV-PER-001",
        "name": "Por edad igual o superior a 65 anos",
        "category": "personal",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 250.0,
        "requirements": json.dumps({
            "descripcion": "250 EUR para contribuyentes de 65 anos o mas a 31 de diciembre del ejercicio.",
            "limites_renta": {"base_imponible_max": 30000},
            "condiciones": [
                "Edad >= 65 anos a 31 de diciembre de 2025",
                "Base imponible general + ahorro <= 30.000 EUR",
                "Residencia habitual en Navarra"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "mayor_65_navarra", "label": "Tiene 65 anos o mas?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 62.2 LF 22/1998 Navarra"
    },

    # 12. Cuidado de menores de 6 anos
    {
        "code": "NAV-FAM-004",
        "name": "Por cuidado de hijos menores de 6 anos",
        "category": "familia",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por cada hijo menor de 6 anos que conviva con el contribuyente.",
            "limites_renta": {},
            "condiciones": [
                "Hijo menor de 6 anos a 31 de diciembre",
                "Convivencia con el contribuyente",
                "500 EUR por cada hijo",
                "Compatible con deduccion por nacimiento/adopcion",
                "Si ambos progenitores deducen, se reparte por mitades"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "menores_6_navarra", "label": "Tiene hijos menores de 6 anos conviviendo con usted?", "type": "boolean"},
            {"key": "num_menores_6_navarra", "label": "Numero de hijos menores de 6 anos", "type": "number"}
        ]),
        "legal_reference": "Art. 62.8 bis LF 22/1998 Navarra"
    },

    # 13. Inversion en empresas de nueva creacion
    {
        "code": "NAV-INV-001",
        "name": "Por inversion en empresas de nueva o reciente creacion",
        "category": "inversion",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 2000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en suscripcion de acciones/participaciones de empresas nuevas. Maximo 2.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Adquisicion de acciones o participaciones en entidades de nueva creacion (< 3 anos)",
                "La entidad debe desarrollar actividad economica real",
                "Participacion del contribuyente no puede superar el 40% del capital",
                "Mantenimiento de la inversion: minimo 3 anos",
                "Entidad domiciliada en Navarra",
                "Maximo 2.000 EUR por ejercicio (mas generoso que Pais Vasco: 1.500 EUR)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_nueva_creacion_navarra", "label": "Ha invertido en empresas de nueva creacion en Navarra?", "type": "boolean"},
            {"key": "importe_inversion_nueva_navarra", "label": "Importe invertido en nuevas empresas", "type": "number"}
        ]),
        "legal_reference": "Art. 62.12 LF 22/1998 Navarra"
    },

    # 14. Discapacidad de descendientes
    {
        "code": "NAV-DIS-002",
        "name": "Por discapacidad de descendientes",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por descendiente con discapacidad 33%-64%, 600 EUR si discapacidad >= 65%.",
            "limites_renta": {},
            "condiciones": [
                "Descendiente con grado de discapacidad >= 33%",
                "Convivencia con el contribuyente o dependencia economica",
                "33%-64%: 300 EUR por persona",
                "65% o superior: 600 EUR por persona",
                "Rentas del descendiente no superiores a 8.000 EUR anuales",
                "Certificado de discapacidad del Gobierno de Navarra (ANADP) en vigor"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_descendientes_navarra", "label": "Tiene descendientes con discapacidad reconocida?", "type": "boolean"},
            {"key": "grado_discapacidad_desc_navarra", "label": "Grado de discapacidad del descendiente (%)", "type": "number"},
            {"key": "num_descendientes_disc_navarra", "label": "Numero de descendientes con discapacidad", "type": "number"}
        ]),
        "legal_reference": "Art. 62.4 bis LF 22/1998 Navarra"
    },

    # 15. Obras de adaptacion de vivienda para personas con discapacidad
    {
        "code": "NAV-DIS-003",
        "name": "Por obras de adaptacion de vivienda habitual para personas con discapacidad",
        "category": "discapacidad",
        "scope": "foral",
        "ccaa": "Navarra",
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en obras de adaptacion de vivienda habitual para personas con discapacidad. Maximo 1.500 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras de adaptacion para accesibilidad de personas con discapacidad >= 33%",
                "Vivienda habitual del contribuyente o de familiar conviviente con discapacidad",
                "Incluye: rampas, ascensores, ampliacion puertas, banos adaptados, domotica asistencial",
                "Maximo 1.500 EUR por ejercicio",
                "Obras realizadas por empresas autorizadas con certificado de accesibilidad",
                "Compatible con deduccion de eficiencia energetica si las obras tambien mejoran calificacion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "adaptacion_vivienda_discapacidad_navarra", "label": "Ha realizado obras de adaptacion de vivienda para personas con discapacidad?", "type": "boolean"},
            {"key": "importe_adaptacion_navarra", "label": "Importe invertido en obras de adaptacion", "type": "number"}
        ]),
        "legal_reference": "Art. 62.7 LF 22/1998 Navarra"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

ALL_FORAL = ARABA_2025 + BIZKAIA_2025 + GIPUZKOA_2025 + NAVARRA_2025


async def seed_forales(dry_run: bool = False):
    """Delete existing foral 2025 deductions and insert all 60."""

    total = len(ALL_FORAL)
    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {total} foral deductions for IRPF {TAX_YEAR}")
    print(f"  Araba: {len(ARABA_2025)} | Bizkaia: {len(BIZKAIA_2025)} | Gipuzkoa: {len(GIPUZKOA_2025)} | Navarra: {len(NAVARRA_2025)}")
    print("=" * 70)

    if not dry_run:
        from app.database.turso_client import TursoClient
        db = TursoClient()
        await db.connect()
        print("Connected to database.\n")

        # Delete existing foral deductions for 2025 (try both column names for compatibility)
        for col_name in ("ccaa", "territory"):
            try:
                result = await db.execute(
                    f"DELETE FROM deductions WHERE {col_name} IN (?, ?, ?, ?) AND tax_year = ?",
                    ["Araba", "Bizkaia", "Gipuzkoa", "Navarra", TAX_YEAR],
                )
                if hasattr(result, "rows_affected") and result.rows_affected:
                    print(f"  Deleted {result.rows_affected} existing foral deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(ALL_FORAL, 1):
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
            print(f"      Territorio: {d['ccaa']} | Categoria: {category} | Importe: {amount_str}")
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
            # Fallback for older schema
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{total} deductions {'would be ' if dry_run else ''}inserted")
    print()

    # Summary by territory
    print("By territory:")
    for territory in FORAL_TERRITORIES:
        count = sum(1 for d in ALL_FORAL if d["ccaa"] == territory)
        print(f"  {territory}: {count}")

    # Summary by category
    print()
    print("By category:")
    categories = {}
    for d in ALL_FORAL:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 60 foral IRPF deductions for 2025 (Araba, Bizkaia, Gipuzkoa, Navarra)")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_forales(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
