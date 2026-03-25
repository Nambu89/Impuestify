"""
Seed ALL 24 official Illes Balears autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunitat Autonoma de les Illes Balears
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-illes-balears.html

Legal basis: Decreto Legislativo 1/2014, de 6 de junio, por el que se aprueba el
Texto Refundido de las disposiciones legales de la Comunidad Autonoma de las Illes Balears
en materia de tributos cedidos por el Estado.

Idempotent: DELETE existing Baleares deductions for tax_year=2025, then INSERT all 24.

Usage:
    cd backend
    python scripts/seed_deductions_baleares_2025.py
    python scripts/seed_deductions_baleares_2025.py --dry-run
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

TERRITORY = "Baleares"
TAX_YEAR = 2025

# Common income limits
LIMITES_BAL_33_52 = {"individual": 33000, "conjunta": 52000}
LIMITES_BAL_30_48 = {"individual": 30000, "conjunta": 48000}


# =============================================================================
# ALL 24 BALEARES DEDUCTIONS — IRPF 2025
# =============================================================================

BALEARES_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion
    # =========================================================================
    {
        "code": "BAL-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 800.0,
        "percentage": None,
        "fixed_amount": 800.0,
        "requirements": json.dumps({
            "descripcion": "800 EUR por nacimiento o adopcion de hijos en el periodo impositivo. 900 EUR si el municipio tiene menos de 10.000 habitantes.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Nacimiento o adopcion en el periodo impositivo",
                "Hijo conviviendo con el contribuyente a fecha de devengo",
                "800 EUR por hijo (900 EUR si municipio < 10.000 hab.)",
                "Si ambos progenitores cumplen requisitos: prorrateo a partes iguales",
                "Base imponible general + ahorro <= 33.000 EUR individual / 52.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_baleares", "label": "Ha tenido un nacimiento o adopcion en 2025?", "type": "boolean"},
            {"key": "num_hijos_nacidos_baleares", "label": "Numero de hijos nacidos/adoptados", "type": "number"},
            {"key": "municipio_menor_10000_baleares", "label": "Reside en un municipio de menos de 10.000 habitantes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 3.Uno DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 2. Por adopcion internacional
    # =========================================================================
    {
        "code": "BAL-FAM-002",
        "name": "Por adopcion internacional de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 800.0,
        "percentage": None,
        "fixed_amount": 800.0,
        "requirements": json.dumps({
            "descripcion": "800 EUR por adopcion internacional constituida en el periodo impositivo. Complementaria a la deduccion por adopcion.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Adopcion constituida segun legislacion vigente e inscrita en Registro Civil",
                "Adopcion de caracter internacional",
                "Compatible con deduccion general por adopcion",
                "Si ambos progenitores cumplen requisitos: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "adopcion_internacional_baleares", "label": "Ha realizado una adopcion internacional en 2025?", "type": "boolean"},
            {"key": "num_adopciones_internacionales", "label": "Numero de adopciones internacionales", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Dos DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 3. Por discapacidad fisica o sensorial del contribuyente
    # =========================================================================
    {
        "code": "BAL-DIS-001",
        "name": "Por discapacidad fisica o sensorial del contribuyente",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": None,
        "fixed_amount": 80.0,
        "requirements": json.dumps({
            "descripcion": "80 EUR por discapacidad fisica o sensorial >= 33%. 150 EUR si >= 65%.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Grado de discapacidad fisica o sensorial >= 33%",
                "80 EUR si grado >= 33% y < 65%",
                "150 EUR si grado >= 65%",
                "Certificado oficial de discapacidad",
                "Base imponible general + ahorro <= 33.000 EUR individual / 52.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_fisica_baleares", "label": "Tiene discapacidad fisica o sensorial reconocida >= 33%?", "type": "boolean"},
            {"key": "grado_discapacidad_fisica_baleares", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Tres DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 4. Por discapacidad psiquica del contribuyente
    # =========================================================================
    {
        "code": "BAL-DIS-002",
        "name": "Por discapacidad psiquica del contribuyente",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": None,
        "fixed_amount": 150.0,
        "requirements": json.dumps({
            "descripcion": "150 EUR por discapacidad psiquica >= 33% del contribuyente.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Grado de discapacidad psiquica >= 33%",
                "150 EUR fijos",
                "Certificado oficial de discapacidad",
                "Base imponible general + ahorro <= 33.000 EUR individual / 52.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_psiquica_baleares", "label": "Tiene discapacidad psiquica reconocida >= 33%?", "type": "boolean"},
            {"key": "grado_discapacidad_psiquica_baleares", "label": "Grado de discapacidad psiquica (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Cuatro DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 5. Por familia numerosa
    # =========================================================================
    {
        "code": "BAL-FAM-003",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": None,
        "fixed_amount": 200.0,
        "requirements": json.dumps({
            "descripcion": "200 EUR por familia numerosa general, 400 EUR por familia numerosa especial.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Titulo de familia numerosa vigente a 31 de diciembre",
                "200 EUR familia numerosa general (3 hijos)",
                "400 EUR familia numerosa especial (4+ hijos o especiales)",
                "Si ambos progenitores: prorrateo a partes iguales",
                "Base imponible general + ahorro <= 33.000 EUR individual / 52.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_baleares", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_baleares", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 3.Cinco DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 6. Por gastos de estudios de educacion superior (grado)
    # =========================================================================
    {
        "code": "BAL-EDU-001",
        "name": "Por gastos de estudios de educacion superior — grado",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1500.0,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos en estudios de grado universitario de los descendientes. Max 1.500 EUR por hijo.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Estudios de grado universitario (primera titulacion)",
                "Descendientes con derecho a minimo por descendientes",
                "Max 1.500 EUR por hijo y ano",
                "Gastos de matricula y tasas oficiales",
                "Conservar justificantes de matricula y pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "estudios_grado_baleares", "label": "Tiene hijos cursando estudios de grado universitario?", "type": "boolean"},
            {"key": "gasto_grado_baleares", "label": "Importe total de gastos de grado", "type": "number"},
            {"key": "num_hijos_grado_baleares", "label": "Cuantos hijos cursan grado?", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Seis DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 7. Por gastos de estudios de educacion superior (master fuera de isla)
    # =========================================================================
    {
        "code": "BAL-EDU-002",
        "name": "Por gastos de estudios de master fuera de la isla de residencia",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1500.0,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos en estudios de master oficial cursados fuera de la isla de residencia. Max 1.500 EUR por hijo.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Estudios de master universitario oficial",
                "Cursados fuera de la isla de residencia habitual del contribuyente",
                "Descendientes con derecho a minimo por descendientes",
                "Incluye gastos de matricula y transporte interinsular/peninsula",
                "Max 1.500 EUR por hijo y ano",
                "La isla de residencia no debe ofrecer estudios equivalentes"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "master_fuera_isla_baleares", "label": "Tiene hijos cursando master fuera de su isla de residencia?", "type": "boolean"},
            {"key": "gasto_master_fuera_baleares", "label": "Importe total de gastos de master fuera de isla", "type": "number"},
            {"key": "num_hijos_master_fuera", "label": "Cuantos hijos cursan master fuera de isla?", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Siete DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 8. Por mejora de la sostenibilidad de la vivienda habitual
    # =========================================================================
    {
        "code": "BAL-VIV-001",
        "name": "Por mejora de la sostenibilidad de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 10000.0,
        "percentage": 50.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "50% de las inversiones en mejora de la sostenibilidad de la vivienda habitual. Max 10.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Inversiones en mejora de sostenibilidad de vivienda habitual",
                "Incluye: instalaciones de autoconsumo electrico, energia solar termica, biomasa, geotermia",
                "Instalacion de sistemas de recarga de vehiculos electricos",
                "Mejoras de eficiencia energetica (aislamiento, ventanas, calderas eficientes)",
                "Vivienda construida hace mas de 10 anos",
                "La vivienda debe ser de uso residencial",
                "Conservar facturas y certificados de instalacion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "sostenibilidad_vivienda_baleares", "label": "Ha realizado inversiones en sostenibilidad en su vivienda habitual?", "type": "boolean"},
            {"key": "importe_sostenibilidad_baleares", "label": "Importe total invertido en sostenibilidad", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Ocho DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 9. Por alquiler de vivienda habitual
    # =========================================================================
    {
        "code": "BAL-VIV-002",
        "name": "Por arrendamiento de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 530.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades satisfechas por el alquiler de la vivienda habitual. Max 530 EUR.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Arrendamiento de la vivienda habitual del contribuyente",
                "15% de las cantidades pagadas en concepto de alquiler",
                "Max 530 EUR anuales",
                "Contrato de arrendamiento registrado y deposito de fianza en organismo competente",
                "El contribuyente no puede ser propietario de otra vivienda en Baleares",
                "Base imponible general + ahorro <= 33.000 EUR individual / 52.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_baleares", "label": "Paga alquiler por su vivienda habitual en Baleares?", "type": "boolean"},
            {"key": "importe_alquiler_baleares", "label": "Importe anual de alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Nueve DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 10. Por alquiler de vivienda habitual en favor de colectivos especiales
    # =========================================================================
    {
        "code": "BAL-VIV-003",
        "name": "Por arrendamiento de vivienda habitual en favor de colectivos especiales",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 650.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades de alquiler para discapacitados, familias numerosas, monoparentales o menores de 36. Max 650 EUR.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Discapacitados con grado >= 65%",
                "Familias numerosas",
                "Familias monoparentales",
                "Menores de 36 anos a fecha de devengo",
                "Contrato de arrendamiento registrado",
                "Max 650 EUR anuales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_colectivo_especial_baleares", "label": "Pertenece a colectivo especial (discapacidad >= 65%, familia numerosa, monoparental, < 36 anos)?", "type": "boolean"},
            {"key": "importe_alquiler_especial_baleares", "label": "Importe anual de alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Diez DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 11. Por donaciones a entidades del tercer sector
    # =========================================================================
    {
        "code": "BAL-DON-001",
        "name": "Por donaciones a entidades sin animo de lucro",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de las donaciones dinerarias a entidades sin animo de lucro que cumplan con la Ley 49/2002.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras e irrevocables",
                "Entidades beneficiarias segun Ley 49/2002 y normativa autonomica",
                "Entidades con sede en Baleares o que desarrollen actividad en el territorio",
                "Transferencia bancaria obligatoria",
                "Certificado de la entidad beneficiaria",
                "Deduccion no puede superar el 15% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_entidades_baleares", "label": "Ha realizado donaciones a entidades sin animo de lucro en Baleares?", "type": "boolean"},
            {"key": "importe_donaciones_baleares", "label": "Importe total de donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Once DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 12. Por donaciones a la investigacion, desarrollo e innovacion
    # =========================================================================
    {
        "code": "BAL-DON-002",
        "name": "Por donaciones a la investigacion, desarrollo e innovacion",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de las donaciones destinadas a I+D+i realizadas en Baleares.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias a entidades dedicadas a I+D+i",
                "Incluye universidades publicas, centros de investigacion, parques tecnologicos",
                "Entidades con actividad en Baleares",
                "Transferencia bancaria obligatoria",
                "Certificado de la entidad beneficiaria"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_idi_baleares", "label": "Ha realizado donaciones para I+D+i en Baleares?", "type": "boolean"},
            {"key": "importe_donaciones_idi_baleares", "label": "Importe total donado a I+D+i", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Doce DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 13. Por donaciones relativas al patrimonio cultural y artistico
    # =========================================================================
    {
        "code": "BAL-DON-003",
        "name": "Por donaciones relativas al patrimonio cultural y artistico",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del valor de las donaciones de bienes del patrimonio cultural e historico de las Illes Balears.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones de bienes integrantes del patrimonio historico de Baleares",
                "Donaciones a instituciones culturales publicas",
                "Requiere valoracion pericial del bien donado",
                "Certificado de la entidad receptora"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_patrimonio_baleares", "label": "Ha donado bienes del patrimonio cultural o artistico?", "type": "boolean"},
            {"key": "valor_donacion_patrimonio_baleares", "label": "Valor de las donaciones al patrimonio cultural", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Trece DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 14. Por ELA (Esclerosis Lateral Amiotrofica)
    # =========================================================================
    {
        "code": "BAL-SAL-001",
        "name": "Por gastos relacionados con la Esclerosis Lateral Amiotrofica (ELA)",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por contribuyente o familiar con ELA diagnosticada.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Diagnostico de Esclerosis Lateral Amiotrofica (ELA)",
                "Contribuyente, conyuge o descendientes/ascendientes con derecho a minimos",
                "300 EUR por persona afectada",
                "Certificado medico oficial de la enfermedad",
                "Compatible con otras deducciones por discapacidad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ela_baleares", "label": "Tiene usted o algun familiar conviviente diagnosticado de ELA?", "type": "boolean"},
            {"key": "num_afectados_ela_baleares", "label": "Numero de personas afectadas por ELA", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Catorce DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 15. Por cuidado de ascendientes mayores de 65 anos
    # =========================================================================
    {
        "code": "BAL-FAM-004",
        "name": "Por gastos relativos a los ascendientes mayores de 65 anos o discapacitados",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por ascendiente mayor de 65 anos o discapacitado que conviva con el contribuyente. 600 EUR si mayor de 75 anos.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Ascendiente mayor de 65 anos o con discapacidad >= 33%",
                "Convivencia con el contribuyente al menos 6 meses al ano",
                "300 EUR si mayor de 65 anos o discapacitado",
                "600 EUR si mayor de 75 anos",
                "El ascendiente no debe tener rentas anuales > 8.000 EUR",
                "Si varios contribuyentes tienen derecho: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ascendientes_mayores_baleares", "label": "Convive con ascendientes mayores de 65 anos o discapacitados?", "type": "boolean"},
            {"key": "num_ascendientes_65_baleares", "label": "Numero de ascendientes mayores de 65 anos", "type": "number"},
            {"key": "num_ascendientes_75_baleares", "label": "De ellos, cuantos son mayores de 75 anos?", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Quince DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 16. Por vehiculos electricos
    # =========================================================================
    {
        "code": "BAL-MED-001",
        "name": "Por adquisicion de vehiculos electricos",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 6000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculos electricos nuevos. Max 6.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Vehiculo electrico nuevo (100% electrico o pila de combustible de hidrogeno)",
                "Matriculado por primera vez a nombre del contribuyente",
                "No destinado a actividad economica",
                "Mantener propiedad minimo 3 anos",
                "Base maxima: 40.000 EUR del vehiculo",
                "Un vehiculo por contribuyente y periodo impositivo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_baleares", "label": "Ha comprado un vehiculo electrico nuevo en 2025?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico_baleares", "label": "Precio de adquisicion del vehiculo electrico", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Dieciseis DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 17. Por emprendimiento
    # =========================================================================
    {
        "code": "BAL-INV-001",
        "name": "Por inversiones y gastos en favor del emprendimiento",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por inicio de actividad economica como emprendedor en Baleares.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Alta en actividad economica por primera vez en el ano fiscal",
                "Residencia fiscal en Baleares",
                "Mantenimiento de la actividad durante al menos 2 anos",
                "No haber ejercido la misma actividad economica en los 3 anos anteriores",
                "500 EUR para el ano de inicio de actividad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "emprendimiento_baleares", "label": "Ha iniciado una actividad economica como emprendedor en 2025?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 3.Diecisiete DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 18. Por eficiencia energetica de la vivienda habitual
    # =========================================================================
    {
        "code": "BAL-MED-002",
        "name": "Por obras de mejora de eficiencia energetica de la vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 10000.0,
        "percentage": 50.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "50% de las inversiones en mejora de eficiencia energetica. Max 10.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras que mejoren la calificacion energetica de la vivienda",
                "Certificado de eficiencia energetica antes y despues de la obra",
                "Mejora de al menos una letra en la calificacion energetica",
                "Vivienda habitual del contribuyente",
                "Facturas y certificados de instalacion",
                "Incompatible con la deduccion por sostenibilidad si mismo concepto"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_baleares", "label": "Ha realizado obras de mejora de eficiencia energetica en su vivienda?", "type": "boolean"},
            {"key": "importe_eficiencia_energetica_baleares", "label": "Importe total invertido en eficiencia energetica", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Dieciocho DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 19. Por gastos en primas de seguros de credito
    # =========================================================================
    {
        "code": "BAL-VIV-004",
        "name": "Por primas de seguros de credito para cubrir impagos de alquileres",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 440.0,
        "percentage": 75.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "75% de las primas de seguros de credito que cubran total o parcialmente impagos de rentas de alquiler. Max 440 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Arrendador de vivienda ubicada en Baleares",
                "Seguro que cubra impago de rentas de alquiler",
                "El alquiler debe constituir vivienda habitual del inquilino",
                "Contrato de arrendamiento registrado",
                "Max 440 EUR por vivienda arrendada"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "seguro_impago_baleares", "label": "Es arrendador con seguro de impago de alquileres?", "type": "boolean"},
            {"key": "prima_seguro_impago_baleares", "label": "Importe de la prima del seguro", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Diecinueve DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 20. Por gastos de aprendizaje extraescolar de idiomas
    # =========================================================================
    {
        "code": "BAL-EDU-003",
        "name": "Por gastos de aprendizaje extraescolar de idiomas extranjeros",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 200.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de los gastos de aprendizaje extraescolar de idiomas extranjeros de los hijos. Max 200 EUR por hijo.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Hijos menores de 25 anos con derecho a minimo por descendientes",
                "Clases de idiomas extranjeros en centros oficiales o academias",
                "Actividades extraescolares (no incluidas en curriculo obligatorio)",
                "Max 200 EUR por hijo",
                "Conservar facturas y justificantes de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "idiomas_hijos_baleares", "label": "Tiene hijos que reciben clases de idiomas extranjeros?", "type": "boolean"},
            {"key": "gasto_idiomas_baleares", "label": "Importe total de gastos en idiomas", "type": "number"},
            {"key": "num_hijos_idiomas_baleares", "label": "Cuantos hijos reciben clases de idiomas?", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Veinte DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 21. Por acogimiento familiar
    # =========================================================================
    {
        "code": "BAL-FAM-005",
        "name": "Por acogimiento familiar de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por cada menor en regimen de acogimiento familiar.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Acogimiento familiar segun legislacion civil vigente",
                "El menor debe convivir con el contribuyente minimo 183 dias al ano",
                "600 EUR por menor acogido",
                "Resolucion administrativa o judicial de acogimiento",
                "Si varios contribuyentes: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_familiar_baleares", "label": "Tiene menores en regimen de acogimiento familiar?", "type": "boolean"},
            {"key": "num_menores_acogidos_baleares", "label": "Numero de menores acogidos", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Veintiuno DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 22. Por gastos de guarderia de menores de 3 anos
    # =========================================================================
    {
        "code": "BAL-FAM-006",
        "name": "Por gastos de guarderia de hijos menores de 3 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 40.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "40% de los gastos de guarderia o centros de primer ciclo de educacion infantil (0-3 anos). Max 600 EUR por hijo.",
            "limites_renta": LIMITES_BAL_33_52,
            "condiciones": [
                "Hijos menores de 3 anos",
                "Centro de educacion infantil autorizado",
                "Ambos progenitores deben trabajar (por cuenta propia o ajena)",
                "Max 600 EUR por hijo",
                "Si ambos progenitores: prorrateo a partes iguales",
                "Conservar facturas y justificantes"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_baleares", "label": "Tiene hijos menores de 3 anos en guarderia?", "type": "boolean"},
            {"key": "gasto_guarderia_baleares", "label": "Importe total de gastos de guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_baleares", "label": "Cuantos hijos menores de 3 anos asisten a guarderia?", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Veintidos DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 23. Por inversion en entidades nuevas o de reciente creacion
    # =========================================================================
    {
        "code": "BAL-INV-002",
        "name": "Por inversion en entidades nuevas o de reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 6000.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades invertidas en acciones/participaciones de entidades nuevas o de reciente creacion. Max 6.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Entidad constituida en los 5 anos anteriores a la inversion",
                "Sede social y domicilio fiscal en Baleares",
                "Participacion del contribuyente (+ conyuge/familiares) <= 40% del capital",
                "La entidad debe tener al menos 1 empleado a tiempo completo",
                "Mantenimiento de la inversion durante 4 anos",
                "No tratarse de entidad patrimonial",
                "Capital social entre 3.000 y 400.000 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_startups_baleares", "label": "Ha invertido en entidades nuevas o de reciente creacion en Baleares?", "type": "boolean"},
            {"key": "importe_inversion_startups_baleares", "label": "Importe total invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Veintitres DLeg 1/2014 Baleares"
    },

    # =========================================================================
    # 24. Por donaciones a actividades deportivas
    # =========================================================================
    {
        "code": "BAL-DON-004",
        "name": "Por donaciones a entidades que fomenten la practica deportiva",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de las donaciones a entidades sin animo de lucro dedicadas al fomento de la practica deportiva.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias a entidades deportivas sin animo de lucro",
                "Entidades inscritas en el registro de entidades deportivas de Baleares",
                "Transferencia bancaria obligatoria",
                "Certificado de la entidad beneficiaria",
                "Deduccion no puede superar 15% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_deportivas_baleares", "label": "Ha donado a entidades deportivas sin animo de lucro en Baleares?", "type": "boolean"},
            {"key": "importe_donaciones_deportivas_baleares", "label": "Importe total donado a entidades deportivas", "type": "number"}
        ]),
        "legal_reference": "Art. 3.Veinticuatro DLeg 1/2014 Baleares"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_baleares(dry_run: bool = False):
    """Delete existing Baleares 2025 deductions and insert all 24."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(BALEARES_2025)} Baleares deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing Baleares deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(BALEARES_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(BALEARES_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in BALEARES_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 24 Baleares IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_baleares(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
