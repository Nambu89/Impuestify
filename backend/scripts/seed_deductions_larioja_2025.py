"""
Seed ALL 24 official La Rioja autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de La Rioja
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-rioja.html

Legal basis: Ley 10/2017, de 27 de octubre, por la que se consolidan las disposiciones legales
de la Comunidad Autonoma de La Rioja en materia de impuestos propios y tributos cedidos.

Idempotent: DELETE existing La Rioja deductions for tax_year=2025, then INSERT all 24.

Usage:
    cd backend
    python scripts/seed_deductions_larioja_2025.py
    python scripts/seed_deductions_larioja_2025.py --dry-run
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

TERRITORY = "La Rioja"
TAX_YEAR = 2025

# Common income limits
LIMITES_LRI_18_30 = {"individual": 18030, "conjunta": 30050}
LIMITES_LRI_30_50 = {"individual": 30000, "conjunta": 50000}


# =============================================================================
# ALL 24 LA RIOJA DEDUCTIONS — IRPF 2025
# =============================================================================

LARIOJA_2025 = [
    # =========================================================================
    # 1. Por nacimiento y adopcion de hijos (primer hijo)
    # =========================================================================
    {
        "code": "LRI-FAM-001",
        "name": "Por nacimiento y adopcion del primer hijo",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": None,
        "fixed_amount": 150.0,
        "requirements": json.dumps({
            "descripcion": "150 EUR por nacimiento o adopcion del primer hijo en el periodo impositivo.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Nacimiento o adopcion del primer hijo en el periodo impositivo",
                "El hijo debe convivir con el contribuyente",
                "150 EUR por el primer hijo",
                "Si ambos progenitores: prorrateo a partes iguales",
                "Base imponible general + ahorro <= 30.000 EUR individual / 50.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_primer_hijo_larioja", "label": "Ha tenido su primer hijo (nacimiento o adopcion) en 2025?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 32.1 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 2. Por nacimiento y adopcion de hijos (segundo hijo)
    # =========================================================================
    {
        "code": "LRI-FAM-002",
        "name": "Por nacimiento y adopcion del segundo hijo",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 180.0,
        "percentage": None,
        "fixed_amount": 180.0,
        "requirements": json.dumps({
            "descripcion": "180 EUR por nacimiento o adopcion del segundo hijo en el periodo impositivo.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Nacimiento o adopcion del segundo hijo en el periodo impositivo",
                "El hijo debe convivir con el contribuyente",
                "180 EUR por el segundo hijo",
                "Si ambos progenitores: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_segundo_hijo_larioja", "label": "Ha tenido su segundo hijo (nacimiento o adopcion) en 2025?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 32.2 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 3. Por nacimiento y adopcion de hijos (tercero y sucesivos)
    # =========================================================================
    {
        "code": "LRI-FAM-003",
        "name": "Por nacimiento y adopcion del tercer hijo y sucesivos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 180.0,
        "percentage": None,
        "fixed_amount": 180.0,
        "requirements": json.dumps({
            "descripcion": "180 EUR por nacimiento o adopcion del tercer hijo y sucesivos.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Nacimiento o adopcion del tercer hijo o sucesivos",
                "El hijo debe convivir con el contribuyente",
                "180 EUR por cada hijo a partir del tercero",
                "Si ambos progenitores: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_tercer_hijo_larioja", "label": "Ha tenido un tercer hijo o sucesivo en 2025?", "type": "boolean"},
            {"key": "num_hijos_tercero_larioja", "label": "Cuantos hijos nacidos/adoptados (3ro y siguientes)?", "type": "number"}
        ]),
        "legal_reference": "Art. 32.3 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 4. Por gastos en escuelas infantiles o centros de educacion infantil
    # =========================================================================
    {
        "code": "LRI-EDU-001",
        "name": "Por gastos en escuelas infantiles o centros de educacion infantil autorizados",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades satisfechas en escuelas infantiles (0-3 anos). Max 600 EUR por menor.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Hijos menores de 3 anos",
                "Centro de educacion infantil autorizado por la Consejeria competente",
                "30% de los gastos de custodia, matricula y alimentacion",
                "Max 600 EUR por menor",
                "Si ambos progenitores declaran: prorrateo a partes iguales",
                "Conservar facturas y justificantes de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "escuela_infantil_larioja", "label": "Tiene hijos menores de 3 anos en escuela infantil autorizada?", "type": "boolean"},
            {"key": "gasto_escuela_infantil_larioja", "label": "Importe total de gastos en escuela infantil", "type": "number"},
            {"key": "num_hijos_escuela_larioja", "label": "Cuantos hijos asisten a escuela infantil?", "type": "number"}
        ]),
        "legal_reference": "Art. 33 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 5. Por familia numerosa general
    # =========================================================================
    {
        "code": "LRI-FAM-004",
        "name": "Por familia numerosa de categoria general",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": None,
        "fixed_amount": 100.0,
        "requirements": json.dumps({
            "descripcion": "100 EUR por familia numerosa de categoria general.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Titulo de familia numerosa de categoria general vigente a 31 de diciembre",
                "100 EUR por declaracion",
                "Si ambos progenitores: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_general_larioja", "label": "Tiene titulo de familia numerosa general?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 34.1 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 6. Por familia numerosa especial
    # =========================================================================
    {
        "code": "LRI-FAM-005",
        "name": "Por familia numerosa de categoria especial",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 200.0,
        "percentage": None,
        "fixed_amount": 200.0,
        "requirements": json.dumps({
            "descripcion": "200 EUR por familia numerosa de categoria especial.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Titulo de familia numerosa de categoria especial vigente a 31 de diciembre",
                "200 EUR por declaracion",
                "Si ambos progenitores: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_especial_larioja", "label": "Tiene titulo de familia numerosa especial?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 34.2 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 7. Por discapacidad del contribuyente
    # =========================================================================
    {
        "code": "LRI-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por contribuyente con grado de discapacidad >= 33%.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Grado de discapacidad >= 33% reconocido oficialmente",
                "300 EUR fijos por declaracion",
                "Certificado oficial de discapacidad vigente a 31 de diciembre",
                "Base imponible general + ahorro <= 30.000 EUR individual / 50.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_larioja", "label": "Tiene reconocido un grado de discapacidad >= 33%?", "type": "boolean"},
            {"key": "grado_discapacidad_larioja", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 35 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 8. Por discapacidad de ascendientes o descendientes
    # =========================================================================
    {
        "code": "LRI-DIS-002",
        "name": "Por discapacidad de ascendientes o descendientes",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por ascendiente o descendiente con grado de discapacidad >= 33% que conviva con el contribuyente.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Ascendiente o descendiente con grado de discapacidad >= 33%",
                "Convivencia con el contribuyente",
                "El familiar debe generar derecho a minimos por ascendientes/descendientes",
                "300 EUR por persona discapacitada",
                "Certificado oficial de discapacidad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_familiar_larioja", "label": "Convive con ascendientes o descendientes con discapacidad >= 33%?", "type": "boolean"},
            {"key": "num_familiares_discapacidad_larioja", "label": "Cuantos familiares con discapacidad conviven con usted?", "type": "number"}
        ]),
        "legal_reference": "Art. 35.bis Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 9. Por jovenes emancipados menores de 36 anos
    # =========================================================================
    {
        "code": "LRI-VIV-001",
        "name": "Por jovenes emancipados menores de 36 anos",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": None,
        "fixed_amount": 150.0,
        "requirements": json.dumps({
            "descripcion": "150 EUR para jovenes menores de 36 anos emancipados que hayan constituido vivienda habitual independiente.",
            "limites_renta": LIMITES_LRI_18_30,
            "condiciones": [
                "Edad < 36 anos a 31 de diciembre",
                "Emancipado y viviendo de forma independiente",
                "Residencia fiscal en La Rioja",
                "150 EUR fijos",
                "Base imponible general <= 18.030 EUR individual / 30.050 EUR conjunta",
                "No aplica si ya se beneficia de deduccion estatal por vivienda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "joven_emancipado_larioja", "label": "Es menor de 36 anos y vive emancipado de forma independiente?", "type": "boolean"},
            {"key": "menor_36_larioja", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 36 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 10. Por alquiler de vivienda habitual
    # =========================================================================
    {
        "code": "LRI-VIV-002",
        "name": "Por arrendamiento de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades satisfechas por alquiler de vivienda habitual. Max 300 EUR.",
            "limites_renta": LIMITES_LRI_18_30,
            "condiciones": [
                "Arrendamiento de la vivienda habitual",
                "10% de las cantidades pagadas en concepto de alquiler",
                "Max 300 EUR anuales",
                "Contrato de arrendamiento registrado",
                "Fianza depositada en el organismo competente",
                "Base imponible general <= 18.030 EUR individual / 30.050 EUR conjunta",
                "No ser propietario de otra vivienda en La Rioja"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_larioja", "label": "Paga alquiler por su vivienda habitual en La Rioja?", "type": "boolean"},
            {"key": "importe_alquiler_larioja", "label": "Importe anual de alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 37 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 11. Por adquisicion de vehiculos electricos o hibridos enchufables
    # =========================================================================
    {
        "code": "LRI-MED-001",
        "name": "Por adquisicion de vehiculos electricos o hibridos enchufables",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculos electricos o hibridos enchufables nuevos. Max 1.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Vehiculo 100% electrico o hibrido enchufable (categoria M1 o L)",
                "Vehiculo nuevo matriculado por primera vez",
                "No destinado a actividad economica",
                "Mantener propiedad minimo 3 anos",
                "Max 1.000 EUR de deduccion",
                "Un vehiculo por contribuyente y periodo impositivo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_larioja", "label": "Ha comprado un vehiculo electrico o hibrido enchufable nuevo en 2025?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico_larioja", "label": "Precio de adquisicion del vehiculo", "type": "number"},
            {"key": "tipo_vehiculo_larioja", "label": "Tipo de vehiculo", "type": "select", "options": ["electrico", "hibrido_enchufable"]}
        ]),
        "legal_reference": "Art. 38 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 12. Por ELA (Esclerosis Lateral Amiotrofica)
    # =========================================================================
    {
        "code": "LRI-SAL-001",
        "name": "Por gastos asociados a la Esclerosis Lateral Amiotrofica (ELA)",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por contribuyente, conyuge o familiar conviviente diagnosticado de ELA.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Diagnostico de Esclerosis Lateral Amiotrofica (ELA)",
                "Contribuyente, conyuge o descendientes/ascendientes que generen derecho a minimo",
                "500 EUR por persona afectada",
                "Certificado medico oficial",
                "Compatible con otras deducciones por discapacidad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ela_larioja", "label": "Tiene usted o algun familiar conviviente diagnosticado de ELA?", "type": "boolean"},
            {"key": "num_afectados_ela_larioja", "label": "Numero de personas afectadas por ELA", "type": "number"}
        ]),
        "legal_reference": "Art. 38.bis Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 13. Por practica deportiva de menores de 18 anos
    # =========================================================================
    {
        "code": "LRI-EDU-002",
        "name": "Por gastos en actividades deportivas de hijos menores de 18 anos",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos en actividades deportivas organizadas de hijos menores de 18 anos. Max 300 EUR por hijo.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Hijos menores de 18 anos a 31 de diciembre",
                "Actividades deportivas organizadas y federadas",
                "Incluye: inscripciones, licencias federativas, cuotas de clubs deportivos",
                "30% de los gastos",
                "Max 300 EUR por hijo",
                "Conservar facturas y justificantes de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "deporte_hijos_larioja", "label": "Tiene hijos menores de 18 anos que practican deporte organizado?", "type": "boolean"},
            {"key": "gasto_deporte_larioja", "label": "Importe total de gastos deportivos", "type": "number"},
            {"key": "num_hijos_deporte_larioja", "label": "Cuantos hijos practican deporte organizado?", "type": "number"}
        ]),
        "legal_reference": "Art. 39 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 14. Por enfermedad celiaca
    # =========================================================================
    {
        "code": "LRI-SAL-002",
        "name": "Por gastos de personas con enfermedad celiaca",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por contribuyente o familiar conviviente diagnosticado de enfermedad celiaca.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Diagnostico medico de enfermedad celiaca",
                "Contribuyente, conyuge o hijos que generen derecho a minimo por descendientes",
                "300 EUR por persona celiaca",
                "Certificado medico oficial del diagnostico",
                "Compatible con otras deducciones por salud"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "celiaca_larioja", "label": "Tiene usted o algun familiar conviviente diagnosticado de enfermedad celiaca?", "type": "boolean"},
            {"key": "num_celiacos_larioja", "label": "Numero de personas celiacas", "type": "number"}
        ]),
        "legal_reference": "Art. 39.bis Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 15. Por donaciones a entidades sin animo de lucro
    # =========================================================================
    {
        "code": "LRI-DON-001",
        "name": "Por donaciones a entidades sin animo de lucro de La Rioja",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "25% de las donaciones dinerarias a entidades sin animo de lucro con sede en La Rioja.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras e irrevocables",
                "Entidades sin animo de lucro con sede o actividad en La Rioja",
                "Entidades acogidas a la Ley 49/2002 o normativa autonomica",
                "Transferencia bancaria obligatoria",
                "Certificado de la entidad beneficiaria",
                "Deduccion no puede superar el 15% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_entidades_larioja", "label": "Ha realizado donaciones a entidades sin animo de lucro en La Rioja?", "type": "boolean"},
            {"key": "importe_donaciones_larioja", "label": "Importe total de donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 40 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 16. Por donaciones al patrimonio cultural
    # =========================================================================
    {
        "code": "LRI-DON-002",
        "name": "Por donaciones al patrimonio cultural de La Rioja",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del valor de las donaciones de bienes del patrimonio cultural e historico de La Rioja.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones de bienes integrantes del patrimonio cultural de La Rioja",
                "Incluye bienes del Inventario General del Patrimonio Cultural",
                "Requiere valoracion pericial y certificado de la entidad receptora",
                "Transferencia bancaria para donaciones dinerarias"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_patrimonio_larioja", "label": "Ha donado bienes del patrimonio cultural de La Rioja?", "type": "boolean"},
            {"key": "valor_donacion_patrimonio_larioja", "label": "Valor de las donaciones al patrimonio cultural", "type": "number"}
        ]),
        "legal_reference": "Art. 40.bis Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 17. Por adquisicion de vivienda habitual para jovenes
    # =========================================================================
    {
        "code": "LRI-VIV-003",
        "name": "Por inversion en vivienda habitual para jovenes menores de 36 anos",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades invertidas en adquisicion de vivienda habitual por menores de 36 anos. Max 400 EUR.",
            "limites_renta": LIMITES_LRI_18_30,
            "condiciones": [
                "Edad < 36 anos a 31 de diciembre",
                "Adquisicion de vivienda habitual en La Rioja",
                "5% de las cantidades invertidas",
                "Max 400 EUR anuales",
                "Vivienda de nueva construccion o segunda mano",
                "Base imponible general <= 18.030 EUR individual / 30.050 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_joven_larioja", "label": "Ha adquirido vivienda habitual en La Rioja siendo menor de 36 anos?", "type": "boolean"},
            {"key": "importe_inversion_vivienda_larioja", "label": "Importe invertido en vivienda", "type": "number"},
            {"key": "menor_36_larioja", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 41 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 18. Por obras de mejora de eficiencia energetica
    # =========================================================================
    {
        "code": "LRI-MED-002",
        "name": "Por obras de mejora de la eficiencia energetica de la vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las inversiones en mejora de eficiencia energetica de la vivienda habitual. Max 1.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras que mejoren la calificacion energetica de la vivienda habitual",
                "Certificado de eficiencia energetica previo y posterior a la obra",
                "Mejora de al menos una letra en la calificacion",
                "Vivienda habitual del contribuyente en La Rioja",
                "Max 1.000 EUR de deduccion",
                "Conservar facturas y certificados"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_larioja", "label": "Ha realizado obras de mejora de eficiencia energetica en su vivienda?", "type": "boolean"},
            {"key": "importe_eficiencia_larioja", "label": "Importe total invertido en eficiencia energetica", "type": "number"}
        ]),
        "legal_reference": "Art. 42 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 19. Por residencia habitual en municipios en riesgo de despoblacion
    # =========================================================================
    {
        "code": "LRI-DES-001",
        "name": "Por residencia habitual en municipios en riesgo de despoblacion",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por contribuyente con residencia habitual en municipio de La Rioja en riesgo de despoblacion. 600 EUR si traslada su residencia a dicho municipio.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Residencia habitual en municipio riojano en riesgo de despoblacion",
                "Lista de municipios definida por la Comunidad Autonoma",
                "300 EUR si ya residia en el municipio",
                "600 EUR si se traslada al municipio durante el periodo impositivo",
                "Empadronamiento en el municipio durante todo el ejercicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "despoblacion_larioja", "label": "Reside en un municipio de La Rioja en riesgo de despoblacion?", "type": "boolean"},
            {"key": "traslado_despoblacion_larioja", "label": "Se ha trasladado a dicho municipio en 2025?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 43 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 20. Por acogimiento familiar de menores
    # =========================================================================
    {
        "code": "LRI-FAM-006",
        "name": "Por acogimiento familiar de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada menor en regimen de acogimiento familiar no preadoptivo.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Acogimiento familiar no preadoptivo de menores",
                "Convivencia minima de 183 dias durante el periodo impositivo",
                "Resolucion administrativa o judicial",
                "300 EUR por menor acogido",
                "Si varios contribuyentes: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_familiar_larioja", "label": "Tiene menores en acogimiento familiar?", "type": "boolean"},
            {"key": "num_menores_acogidos_larioja", "label": "Numero de menores acogidos", "type": "number"}
        ]),
        "legal_reference": "Art. 44 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 21. Por inversion en entidades nuevas o de reciente creacion
    # =========================================================================
    {
        "code": "LRI-INV-001",
        "name": "Por inversion en entidades nuevas o de reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades invertidas en entidades de nueva creacion con sede en La Rioja. Max 4.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Entidad constituida en los 3 anos anteriores a la inversion",
                "Sede social y domicilio fiscal en La Rioja",
                "Participacion del contribuyente (+ conyuge/familiares) <= 40% del capital",
                "Mantenimiento minimo 3 anos",
                "Al menos 1 empleado a jornada completa",
                "No ser entidad patrimonial"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_startups_larioja", "label": "Ha invertido en entidades nuevas o de reciente creacion en La Rioja?", "type": "boolean"},
            {"key": "importe_inversion_startups_larioja", "label": "Importe total invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 45 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 22. Por gastos de material escolar
    # =========================================================================
    {
        "code": "LRI-EDU-003",
        "name": "Por gastos de material escolar",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos de material escolar de Educacion Basica. Max 100 EUR por descendiente.",
            "limites_renta": LIMITES_LRI_18_30,
            "condiciones": [
                "Descendientes en niveles de Educacion Basica (Primaria y ESO)",
                "Material escolar: libros de texto, cuadernos, mochilas, material de papeleria",
                "Max 100 EUR por descendiente",
                "Conservar facturas con detalle de material",
                "Base imponible general <= 18.030 EUR individual / 30.050 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "material_escolar_larioja", "label": "Tiene hijos en educacion basica (Primaria/ESO)?", "type": "boolean"},
            {"key": "gasto_material_escolar_larioja", "label": "Importe total de gastos de material escolar", "type": "number"},
            {"key": "num_hijos_escolar_larioja", "label": "Cuantos hijos cursan educacion basica?", "type": "number"}
        ]),
        "legal_reference": "Art. 46 Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 23. Por suministros de luz y gas de la vivienda habitual
    # =========================================================================
    {
        "code": "LRI-VIV-004",
        "name": "Por suministros de luz y gas de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 200.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de los gastos de suministros de luz y gas de la vivienda habitual. Max 200 EUR.",
            "limites_renta": LIMITES_LRI_18_30,
            "condiciones": [
                "Gastos de suministro electrico y gas natural de la vivienda habitual",
                "Vivienda habitual en La Rioja",
                "15% de las cantidades pagadas",
                "Max 200 EUR anuales",
                "Conservar facturas de las companias suministradoras",
                "Base imponible general <= 18.030 EUR individual / 30.050 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "suministros_larioja", "label": "Quiere deducir gastos de luz y gas de su vivienda habitual?", "type": "boolean"},
            {"key": "gasto_suministros_larioja", "label": "Importe total anual de luz y gas", "type": "number"}
        ]),
        "legal_reference": "Art. 46.bis Ley 10/2017 La Rioja"
    },

    # =========================================================================
    # 24. Por nacimiento o adopcion en municipios en riesgo de despoblacion
    # =========================================================================
    {
        "code": "LRI-DES-002",
        "name": "Por nacimiento o adopcion en municipio en riesgo de despoblacion",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 750.0,
        "percentage": None,
        "fixed_amount": 750.0,
        "requirements": json.dumps({
            "descripcion": "750 EUR adicional por nacimiento o adopcion cuando el contribuyente reside en municipio en riesgo de despoblacion.",
            "limites_renta": LIMITES_LRI_30_50,
            "condiciones": [
                "Nacimiento o adopcion en el periodo impositivo",
                "Residencia habitual en municipio en riesgo de despoblacion de La Rioja",
                "Complementaria a la deduccion general por nacimiento/adopcion",
                "750 EUR por hijo nacido/adoptado",
                "Empadronamiento en el municipio a fecha de devengo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_despoblacion_larioja", "label": "Ha tenido un nacimiento/adopcion residiendo en municipio en riesgo de despoblacion?", "type": "boolean"},
            {"key": "num_hijos_despoblacion_larioja", "label": "Numero de hijos nacidos/adoptados en zona de despoblacion", "type": "number"}
        ]),
        "legal_reference": "Art. 47 Ley 10/2017 La Rioja"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_larioja(dry_run: bool = False):
    """Delete existing La Rioja 2025 deductions and insert all 24."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(LARIOJA_2025)} La Rioja deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing La Rioja deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(LARIOJA_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(LARIOJA_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in LARIOJA_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 24 La Rioja IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_larioja(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
