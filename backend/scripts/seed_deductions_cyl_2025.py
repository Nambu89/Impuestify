"""
Seed ALL 17 official Castilla y Leon autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad de Castilla y Leon
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-castilla-leon.html

Legal basis: Decreto Legislativo 1/2013, de 12 de septiembre, por el que se aprueba el
texto refundido de las disposiciones legales de la Comunidad de Castilla y Leon en materia
de tributos propios y cedidos.

Idempotent: DELETE existing Castilla y Leon deductions for tax_year=2025, then INSERT all 17.

Usage:
    cd backend
    python scripts/seed_deductions_cyl_2025.py
    python scripts/seed_deductions_cyl_2025.py --dry-run
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

TERRITORY = "Castilla y Leon"
TAX_YEAR = 2025

# Common income limits
LIMITES_CYL_18_30 = {"individual": 18900, "conjunta": 31500}
LIMITES_CYL_25_40 = {"individual": 25000, "conjunta": 40000}


# =============================================================================
# ALL 17 CASTILLA Y LEON DEDUCTIONS — IRPF 2025
# =============================================================================

CYL_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion de hijos
    # =========================================================================
    {
        "code": "CYL-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1635.0,
        "percentage": None,
        "fixed_amount": 750.0,
        "requirements": json.dumps({
            "descripcion": "750 EUR por el primer hijo, 900 EUR por el segundo y 1.635 EUR por el tercero y sucesivos. Importes incrementados en 15% si residencia en municipio < 5.000 hab.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Nacimiento o adopcion durante el periodo impositivo",
                "Residencia habitual en Castilla y Leon",
                "750 EUR primer hijo, 900 EUR segundo, 1.635 EUR tercero y sucesivos",
                "Incremento del 15% si residencia en municipio < 5.000 habitantes",
                "En declaracion conjunta: deduccion unica",
                "En declaraciones individuales: deduccion a partes iguales",
                "Base imponible general + ahorro <= 18.900 EUR (individual) o 31.500 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_hijo_cyl", "label": "Ha tenido o adoptado hijos en Castilla y Leon?", "type": "boolean"},
            {"key": "num_orden_hijo_cyl", "label": "Numero de orden del hijo (1o, 2o, 3o...)", "type": "number"},
            {"key": "municipio_pequeno_cyl", "label": "Reside en un municipio de menos de 5.000 habitantes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 7.1 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 2. Por partos multiples o adopciones simultaneas
    # =========================================================================
    {
        "code": "CYL-FAM-002",
        "name": "Por partos multiples o adopciones simultaneas",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 901.0,
        "requirements": json.dumps({
            "descripcion": "901 EUR por parto multiple o adopcion simultanea de dos o mas hijos.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Parto multiple o adopcion simultanea de 2 o mas hijos",
                "Residencia habitual en Castilla y Leon",
                "En declaracion conjunta: deduccion unica",
                "En individuales: a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "parto_multiple_cyl", "label": "Ha tenido un parto multiple o adopcion simultanea?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 7.2 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 3. Por familia numerosa
    # =========================================================================
    {
        "code": "CYL-FAM-003",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por familia numerosa general o 1.000 EUR por familia numerosa especial.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Titulo de familia numerosa vigente a 31 de diciembre",
                "500 EUR categoria general, 1.000 EUR categoria especial",
                "Residencia habitual en Castilla y Leon",
                "Si ambos progenitores declaran: deduccion a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_cyl", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_cyl", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 7.3 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 4. Por cuidado de hijos menores de 4 anos
    # =========================================================================
    {
        "code": "CYL-FAM-004",
        "name": "Por gastos de cuidado de hijos menores de 4 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 322.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades satisfechas a personas empleadas del hogar o guarderias para cuidado de hijos menores de 4 anos. Max 322 EUR.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Hijos menores de 4 anos a 31 de diciembre",
                "Gastos en empleada de hogar (contrato y alta en SS) o guarderia autorizada",
                "Ambos progenitores deben percibir rendimientos del trabajo o actividades economicas",
                "Max 322 EUR por contribuyente",
                "En declaraciones individuales: cada progenitor deduce sus gastos hasta el maximo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "cuidado_menores_cyl", "label": "Tiene gastos de cuidado de hijos menores de 4 anos?", "type": "boolean"},
            {"key": "gasto_cuidado_menores_cyl", "label": "Importe total de gastos de cuidado", "type": "number"},
            {"key": "num_hijos_menores4_cyl", "label": "Numero de hijos menores de 4 anos", "type": "number"}
        ]),
        "legal_reference": "Art. 7.4 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 5. Por jovenes emancipados
    # =========================================================================
    {
        "code": "CYL-JOV-001",
        "name": "Por contribuyentes jovenes emancipados",
        "category": "jovenes",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": None,
        "fixed_amount": 150.0,
        "requirements": json.dumps({
            "descripcion": "150 EUR para contribuyentes menores de 36 anos emancipados que constituyan su unidad familiar independiente.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Edad < 36 anos a 31 de diciembre",
                "Emancipado y con unidad familiar independiente",
                "Residencia habitual en Castilla y Leon",
                "No convivir con ascendientes",
                "Base imponible general + ahorro <= 18.900 EUR (individual) o 31.500 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "joven_emancipado_cyl", "label": "Es menor de 36 anos y esta emancipado en Castilla y Leon?", "type": "boolean"},
            {"key": "menor_36_cyl", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 7.5 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 6. Por discapacidad del contribuyente
    # =========================================================================
    {
        "code": "CYL-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 656.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por discapacidad >= 33% y < 65%. 656 EUR por discapacidad >= 65%.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Grado de discapacidad reconocido >= 33%",
                "300 EUR si grado >= 33% y < 65%",
                "656 EUR si grado >= 65%",
                "Certificado de discapacidad vigente",
                "Residencia habitual en Castilla y Leon"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_contribuyente_cyl", "label": "Tiene un grado de discapacidad >= 33%?", "type": "boolean"},
            {"key": "grado_discapacidad_cyl", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 7.6 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 7. Por alquiler de vivienda habitual para jovenes
    # =========================================================================
    {
        "code": "CYL-VIV-001",
        "name": "Por alquiler de vivienda habitual para jovenes",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 459.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades satisfechas por alquiler de vivienda habitual para menores de 36 anos. Max 459 EUR.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Edad < 36 anos a 31 de diciembre",
                "Contrato de arrendamiento de vivienda habitual en Castilla y Leon",
                "Deposito de fianza en el organo competente de la Junta de Castilla y Leon",
                "Max 459 EUR",
                "Incompatible con deduccion estatal por alquiler de vivienda habitual"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_joven_cyl", "label": "Alquila vivienda habitual en Castilla y Leon siendo menor de 36 anos?", "type": "boolean"},
            {"key": "importe_alquiler_cyl", "label": "Importe anual del alquiler", "type": "number"},
            {"key": "menor_36_cyl_alquiler", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 8.1 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 8. Por rehabilitacion de vivienda habitual
    # =========================================================================
    {
        "code": "CYL-VIV-002",
        "name": "Por rehabilitacion de vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 10000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en rehabilitacion de vivienda habitual en Castilla y Leon. Max 10.000 EUR de base de deduccion.",
            "limites_renta": {},
            "condiciones": [
                "Obras de rehabilitacion de vivienda habitual",
                "La vivienda debe estar en Castilla y Leon",
                "Obras calificadas como actuacion protegida por la Junta de Castilla y Leon",
                "Max base de deduccion 10.000 EUR (resultado: max 1.500 EUR de deduccion)",
                "Conservar facturas y licencia de obras"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "rehabilitacion_vivienda_cyl", "label": "Ha realizado obras de rehabilitacion en su vivienda habitual en Castilla y Leon?", "type": "boolean"},
            {"key": "importe_rehabilitacion_cyl", "label": "Importe de las obras de rehabilitacion", "type": "number"}
        ]),
        "legal_reference": "Art. 8.2 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 9. Por donaciones a fundaciones de Castilla y Leon
    # =========================================================================
    {
        "code": "CYL-DON-001",
        "name": "Por donaciones a fundaciones de Castilla y Leon",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones dinerarias a fundaciones inscritas en el Registro de Fundaciones de Castilla y Leon que persigan fines culturales, asistenciales, educativos, ecologicos, deportivos, sanitarios o de investigacion.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras, simples e irrevocables",
                "Fundaciones inscritas en el Registro de Fundaciones de Castilla y Leon",
                "Fines: culturales, asistenciales, educativos, ecologicos, deportivos, sanitarios o I+D",
                "Requiere certificacion de la fundacion beneficiaria",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_fundaciones_cyl", "label": "Ha donado a fundaciones de Castilla y Leon?", "type": "boolean"},
            {"key": "importe_donativo_fundaciones_cyl", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 9.1 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 10. Por cantidades donadas para la recuperacion del patrimonio cultural y natural
    # =========================================================================
    {
        "code": "CYL-DON-002",
        "name": "Por donaciones para la recuperacion del patrimonio cultural y natural",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades donadas para la conservacion, reparacion y restauracion de bienes del patrimonio cultural o natural de Castilla y Leon.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones para conservacion, reparacion o restauracion",
                "Bienes del patrimonio historico, cultural o natural de Castilla y Leon",
                "Incluidos bienes inscritos en el Registro de Bienes de Interes Cultural",
                "Requiere certificacion del organo competente",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_patrimonio_cyl", "label": "Ha donado para la recuperacion del patrimonio cultural o natural de Castilla y Leon?", "type": "boolean"},
            {"key": "importe_donativo_patrimonio_cyl", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 9.2 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 11. Por residencia habitual en municipios en riesgo de despoblacion
    # =========================================================================
    {
        "code": "CYL-RUR-001",
        "name": "Por residencia habitual en municipios en riesgo de despoblacion",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por residencia habitual y efectiva en municipios de Castilla y Leon con poblacion inferior a 5.000 habitantes.",
            "limites_renta": LIMITES_CYL_25_40,
            "condiciones": [
                "Residencia habitual y efectiva en municipio de CyL < 5.000 habitantes",
                "Figurar en el padron municipal durante todo el periodo impositivo",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 40.000 EUR (conjunta)",
                "Residencia habitual en Castilla y Leon"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "residencia_rural_cyl", "label": "Reside en un municipio de menos de 5.000 habitantes de Castilla y Leon?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 10.1 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 12. Por inicio de actividad de trabajadores por cuenta propia o autonomos
    # =========================================================================
    {
        "code": "CYL-EMP-001",
        "name": "Por fomento del autoempleo de jovenes",
        "category": "emprendimiento",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por alta inicial como trabajador autonomo en Castilla y Leon siendo menor de 36 anos.",
            "limites_renta": LIMITES_CYL_25_40,
            "condiciones": [
                "Edad < 36 anos a 31 de diciembre",
                "Alta inicial en el RETA o sin actividad en los 2 anos anteriores",
                "Actividad economica desarrollada principalmente en Castilla y Leon",
                "Mantenimiento de la actividad al menos 2 anos",
                "Residencia habitual en Castilla y Leon"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "autoempleo_joven_cyl", "label": "Se ha dado de alta como autonomo siendo menor de 36 anos en Castilla y Leon?", "type": "boolean"},
            {"key": "menor_36_cyl_autoempleo", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 10.2 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 13. Por inversion en entidades de nueva o reciente creacion
    # =========================================================================
    {
        "code": "CYL-EMP-002",
        "name": "Por inversion en entidades de nueva o reciente creacion",
        "category": "emprendimiento",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en acciones o participaciones de entidades de nueva o reciente creacion con sede en Castilla y Leon. Max 4.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Entidad constituida en los 3 anos anteriores a la inversion",
                "Domicilio social y fiscal en Castilla y Leon",
                "Actividad economica con al menos 1 empleado con contrato laboral y centro de trabajo en CyL",
                "Participacion contribuyente + familiares <= 40% del capital",
                "Mantenimiento de la inversion al menos 3 anos",
                "Formalizado en escritura publica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_emprendimiento_cyl", "label": "Ha invertido en entidades de nueva creacion en Castilla y Leon?", "type": "boolean"},
            {"key": "importe_inversion_emprendimiento_cyl", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 10.3 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 14. Por obras de mejora de eficiencia energetica
    # =========================================================================
    {
        "code": "CYL-MED-001",
        "name": "Por obras de mejora de eficiencia energetica en vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en obras de mejora de la eficiencia energetica de la vivienda habitual. Max 1.500 EUR.",
            "limites_renta": LIMITES_CYL_25_40,
            "condiciones": [
                "Obras que mejoren la eficiencia energetica de la vivienda habitual",
                "Certificado de eficiencia energetica antes y despues de las obras",
                "Mejora de al menos una letra en la calificacion energetica",
                "Vivienda habitual en Castilla y Leon",
                "Conservar facturas y justificantes de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_cyl", "label": "Ha realizado obras de eficiencia energetica en su vivienda habitual en Castilla y Leon?", "type": "boolean"},
            {"key": "importe_eficiencia_cyl", "label": "Importe de las obras", "type": "number"}
        ]),
        "legal_reference": "Art. 10.4 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 15. Por adquisicion de vehiculos electricos
    # =========================================================================
    {
        "code": "CYL-MED-002",
        "name": "Por adquisicion de vehiculos electricos",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculo electrico nuevo. Max 4.000 EUR.",
            "limites_renta": LIMITES_CYL_25_40,
            "condiciones": [
                "Vehiculo electrico nuevo (BEV, categoria M1 o L)",
                "Primera matriculacion en Espana a nombre del contribuyente",
                "No destinado a actividad economica",
                "Mantener la propiedad al menos 3 anos",
                "Residencia habitual en Castilla y Leon",
                "Un vehiculo por contribuyente y periodo impositivo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_cyl", "label": "Ha comprado un vehiculo electrico nuevo en Castilla y Leon?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico_cyl", "label": "Precio del vehiculo electrico", "type": "number"}
        ]),
        "legal_reference": "Art. 10.5 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 16. Por traslado de residencia habitual a zonas rurales con riesgo de despoblacion
    # =========================================================================
    {
        "code": "CYL-RUR-002",
        "name": "Por traslado de residencia habitual a zonas rurales",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": None,
        "fixed_amount": 1000.0,
        "requirements": json.dumps({
            "descripcion": "1.000 EUR por traslado de la residencia habitual a un municipio de Castilla y Leon con menos de 5.000 habitantes, durante los dos periodos impositivos siguientes al traslado.",
            "limites_renta": LIMITES_CYL_25_40,
            "condiciones": [
                "Traslado de residencia habitual a municipio de CyL < 5.000 habitantes",
                "Residencia previa en municipio distinto de CyL o fuera de CyL",
                "Deduccion aplicable en el periodo del traslado y los 2 siguientes",
                "Mantener residencia habitual durante al menos 3 anos",
                "Inscripcion en el padron del nuevo municipio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "traslado_rural_cyl", "label": "Se ha trasladado a un municipio < 5.000 hab. de Castilla y Leon?", "type": "boolean"},
            {"key": "ano_traslado_cyl", "label": "Ano del traslado", "type": "number"}
        ]),
        "legal_reference": "Art. 10.6 DLeg 1/2013 Castilla y Leon"
    },

    # =========================================================================
    # 17. Por acogimiento familiar de menores
    # =========================================================================
    {
        "code": "CYL-FAM-005",
        "name": "Por acogimiento familiar de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 784.0,
        "percentage": None,
        "fixed_amount": 784.0,
        "requirements": json.dumps({
            "descripcion": "784 EUR por cada menor en regimen de acogimiento familiar. Aplica tanto acogimiento temporal como permanente.",
            "limites_renta": LIMITES_CYL_18_30,
            "condiciones": [
                "Acogimiento familiar no preadoptivo de menores",
                "Formalizado por la entidad publica competente de Castilla y Leon",
                "Convivencia minima de 183 dias durante el periodo impositivo",
                "Si inferior a 183 dias: 300 EUR",
                "Si ambos acogedores declaran: a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_menores_cyl", "label": "Tiene menores en acogimiento familiar en Castilla y Leon?", "type": "boolean"},
            {"key": "num_menores_acogidos_cyl", "label": "Numero de menores acogidos", "type": "number"},
            {"key": "dias_acogimiento_cyl", "label": "Dias de convivencia durante el periodo impositivo", "type": "number"}
        ]),
        "legal_reference": "Art. 7.7 DLeg 1/2013 Castilla y Leon"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_cyl(dry_run: bool = False):
    """Delete existing Castilla y Leon 2025 deductions and insert all 17."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(CYL_2025)} Castilla y Leon deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing Castilla y Leon deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(CYL_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(CYL_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in CYL_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 17 Castilla y Leon IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_cyl(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
