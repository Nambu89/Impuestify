"""
Seed ALL 26 official Principado de Asturias autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Principado de Asturias
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/principado-asturias.html

Legal basis: Decreto Legislativo 2/2014, de 22 de octubre, por el que se aprueba el
Texto Refundido de las disposiciones legales del Principado de Asturias en materia de
tributos cedidos por el Estado.

Idempotent: DELETE existing Asturias deductions for tax_year=2025, then INSERT all 26.

Usage:
    cd backend
    python scripts/seed_deductions_asturias_2025.py
    python scripts/seed_deductions_asturias_2025.py --dry-run
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

TERRITORY = "Asturias"
TAX_YEAR = 2025

# Common income limits
LIMITES_AST_25_35 = {"individual": 25000, "conjunta": 35000}
LIMITES_AST_35_45 = {"individual": 35000, "conjunta": 45000}


# =============================================================================
# ALL 26 ASTURIAS DEDUCTIONS — IRPF 2025
# =============================================================================

ASTURIAS_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion de hijos
    # =========================================================================
    {
        "code": "AST-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por el 1o hijo, 600 EUR por el 2o, 1.000 EUR por el 3o y sucesivos. Incremento del 25% si residencia en concejo de < 3.000 hab.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Nacimiento o adopcion durante el periodo impositivo",
                "Convivencia con el hijo a la fecha de devengo",
                "300 EUR por 1o hijo; 600 EUR por 2o; 1.000 EUR 3o y sucesivos",
                "Incremento del 25% si residencia en concejo < 3.000 habitantes",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)",
                "Declaracion conjunta: se aplica solo una vez"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_ast", "label": "Ha tenido un hijo o adoptado en 2025 en Asturias?", "type": "boolean"},
            {"key": "num_hijo_orden_ast", "label": "Numero de orden del hijo (1o, 2o, 3o...)", "type": "number"},
            {"key": "concejo_3000_ast", "label": "Reside en un concejo de < 3.000 habitantes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 14.Uno DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 2. Por adopcion internacional
    # =========================================================================
    {
        "code": "AST-FAM-002",
        "name": "Por adopcion internacional",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 1000.0,
        "requirements": json.dumps({
            "descripcion": "1.000 EUR por cada adopcion internacional constituida conforme a la legislacion vigente.",
            "limites_renta": {},
            "condiciones": [
                "Adopcion internacional constituida segun legislacion vigente e inscrita en el Registro Civil",
                "Adopcion durante el periodo impositivo",
                "1.000 EUR por cada adopcion",
                "Compatible con deduccion por nacimiento/adopcion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "adopcion_internacional_ast", "label": "Ha realizado una adopcion internacional en 2025?", "type": "boolean"},
            {"key": "num_adopciones_int_ast", "label": "Numero de adopciones internacionales", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Dos DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 3. Por partos multiples o dos o mas adopciones
    # =========================================================================
    {
        "code": "AST-FAM-003",
        "name": "Por partos multiples o dos o mas adopciones constituidas en el mismo ejercicio",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por partos multiples o cuando se constituyan dos o mas adopciones en el mismo periodo impositivo.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Parto multiple (2 o mas hijos en un parto)",
                "O dos o mas adopciones constituidas en el mismo ejercicio",
                "Compatible con deducciones por nacimiento y adopcion",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "parto_multiple_ast", "label": "Ha tenido un parto multiple o 2+ adopciones en el mismo ejercicio?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 14.Tres DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 4. Por familia numerosa
    # =========================================================================
    {
        "code": "AST-FAM-004",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 505.0,
        "requirements": json.dumps({
            "descripcion": "505 EUR familia numerosa general, 1.010 EUR especial.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Titulo de familia numerosa vigente a fecha de devengo",
                "505 EUR categoria general",
                "1.010 EUR categoria especial",
                "Declaracion conjunta: una sola deduccion",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_ast", "label": "Tiene titulo de familia numerosa vigente?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_ast", "label": "Categoria de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 14.Cuatro DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 5. Por familias monoparentales
    # =========================================================================
    {
        "code": "AST-FAM-005",
        "name": "Por familias monoparentales",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR para contribuyentes que sean madres o padres de familia monoparental con hijos a cargo.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Familia monoparental: unico progenitor que convive con hijos menores",
                "No convivir con otra persona distinta de los descendientes",
                "Hijos deben generar derecho al minimo por descendientes",
                "300 EUR por declaracion",
                "Base imponible general + ahorro <= 35.000 EUR (individual)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "monoparental_ast", "label": "Es familia monoparental?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 14.Cinco DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 6. Por acogimiento familiar de menores
    # =========================================================================
    {
        "code": "AST-FAM-006",
        "name": "Por acogimiento familiar de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada menor en regimen de acogimiento familiar no remunerado.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Acogimiento familiar no remunerado de menores",
                "Formalizado ante la autoridad competente",
                "Convivencia durante al menos 183 dias en el periodo impositivo",
                "No aplica si el acogimiento deriva en adopcion en el mismo ejercicio",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_ast", "label": "Tiene menores en acogimiento familiar no remunerado?", "type": "boolean"},
            {"key": "num_menores_acogidos_ast", "label": "Cuantos menores tiene en acogimiento?", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Seis DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 7. Por gastos de descendientes en centros de 0-3 anos
    # =========================================================================
    {
        "code": "AST-FAM-007",
        "name": "Por gastos de descendientes en centros de 0 a 3 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades satisfechas en centros de primer ciclo de educacion infantil (0-3 anos). Max 500 EUR por descendiente.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Primer ciclo de educacion infantil (0-3 anos)",
                "Centro autorizado por la Consejeria de Educacion del Principado de Asturias",
                "Max 500 EUR por descendiente",
                "Convivencia con el descendiente",
                "Gastos netos de becas o subvenciones",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_ast", "label": "Tiene hijos en centros 0-3 anos en Asturias?", "type": "boolean"},
            {"key": "gasto_guarderia_ast", "label": "Importe total pagado en centros 0-3", "type": "number"},
            {"key": "num_hijos_guarderia_ast", "label": "Cuantos hijos asisten a centros 0-3?", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Siete DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 8. Por alquiler de vivienda habitual
    # =========================================================================
    {
        "code": "AST-VIV-001",
        "name": "Por alquiler de vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 455.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades de alquiler de vivienda habitual. Max 455 EUR. Incremento si concejo < 3.000 hab.",
            "limites_renta": LIMITES_AST_25_35,
            "condiciones": [
                "Vivienda habitual del contribuyente en Asturias",
                "Contrato de arrendamiento segun LAU",
                "Fianza depositada en el Principado de Asturias",
                "Max 455 EUR anuales",
                "Incremento adicional por residir en concejo < 3.000 habitantes",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_ast", "label": "Paga alquiler de vivienda habitual en Asturias?", "type": "boolean"},
            {"key": "importe_alquiler_ast", "label": "Importe anual de alquiler", "type": "number"},
            {"key": "concejo_3000_alquiler_ast", "label": "El concejo tiene < 3.000 habitantes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 14.Ocho DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 9. Por inversion en vivienda habitual en concejos de < 3.000 hab.
    # =========================================================================
    {
        "code": "AST-VIV-002",
        "name": "Por inversion en vivienda habitual en concejos con poblacion inferior a 3.000 habitantes",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 700.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades invertidas en adquisicion o rehabilitacion de vivienda habitual en concejo de < 3.000 hab. Max 700 EUR.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Concejo del Principado de Asturias con poblacion < 3.000 habitantes",
                "Adquisicion o rehabilitacion de vivienda habitual",
                "Max 700 EUR anuales",
                "Vivienda debe constituir residencia habitual durante al menos 3 anos",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_concejo_3000_ast", "label": "Ha adquirido vivienda habitual en concejo de Asturias con < 3.000 hab.?", "type": "boolean"},
            {"key": "importe_vivienda_concejo_ast", "label": "Importe invertido en vivienda", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Nueve DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 10. Por adquisicion de vehiculos electricos, hibridos enchufables o de pila de combustible
    # =========================================================================
    {
        "code": "AST-MED-001",
        "name": "Por adquisicion de vehiculos electricos, hibridos enchufables o de pila de combustible",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del importe satisfecho en adquisicion de vehiculo electrico, hibrido enchufable o pila de combustible. Max 1.500 EUR.",
            "limites_renta": {"individual": 40000, "conjunta": 50000},
            "condiciones": [
                "Vehiculo electrico (BEV), hibrido enchufable (PHEV) o de pila de combustible (FCEV)",
                "Vehiculo nuevo, primera matriculacion en Espana",
                "No destinado a actividad economica",
                "Mantener propiedad minimo 3 anos",
                "Max 1.500 EUR",
                "Base imponible general + ahorro <= 40.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_ast", "label": "Ha comprado un vehiculo electrico/hibrido enchufable en Asturias?", "type": "boolean"},
            {"key": "importe_vehiculo_ast", "label": "Precio del vehiculo", "type": "number"},
            {"key": "tipo_vehiculo_ast", "label": "Tipo de vehiculo", "type": "select", "options": ["electrico_bev", "hibrido_enchufable_phev", "pila_combustible_fcev"]}
        ]),
        "legal_reference": "Art. 14.Diez DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 11. Por gastos en tratamiento de ELA y otras enfermedades raras
    # =========================================================================
    {
        "code": "AST-SAL-001",
        "name": "Por gastos derivados de enfermedades raras y ELA",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR para contribuyentes diagnosticados con ELA u otra enfermedad rara, o que tengan a su cargo familiares con dicho diagnostico.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Diagnostico de ELA (Esclerosis Lateral Amiotrofica) u otra enfermedad rara",
                "Enfermedad rara incluida en el listado oficial del Ministerio de Sanidad",
                "Aplica al contribuyente, conyuge o descendientes a cargo",
                "Requiere certificado medico oficial",
                "300 EUR por declaracion",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "enfermedad_rara_ast", "label": "Tiene usted o un familiar a cargo diagnostico de ELA o enfermedad rara?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 14.Once DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 12. Por obras de mejora de eficiencia energetica en vivienda habitual
    # =========================================================================
    {
        "code": "AST-MED-002",
        "name": "Por obras de mejora de la eficiencia energetica en vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades invertidas en obras de mejora de la eficiencia energetica de la vivienda habitual. Max 500 EUR.",
            "limites_renta": {"individual": 40000, "conjunta": 50000},
            "condiciones": [
                "Obras en vivienda habitual del contribuyente en Asturias",
                "Mejora certificada de la calificacion energetica (al menos 1 letra)",
                "Certificado de eficiencia energetica antes y despues de la obra",
                "Realizadas por empresa autorizada",
                "Max 500 EUR por declaracion",
                "Base imponible general + ahorro <= 40.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_ast", "label": "Ha realizado obras de mejora energetica en su vivienda habitual en Asturias?", "type": "boolean"},
            {"key": "importe_eficiencia_ast", "label": "Importe invertido en las obras", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Doce DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 13. Por arrendamiento de viviendas vacias
    # =========================================================================
    {
        "code": "AST-VIV-003",
        "name": "Por arrendamiento de viviendas vacias",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por arrendar como vivienda habitual una vivienda que hubiera estado desocupada mas de 6 meses.",
            "limites_renta": {},
            "condiciones": [
                "Vivienda que hubiera estado desocupada al menos 6 meses",
                "Arrendada como vivienda habitual del arrendatario",
                "Contrato segun LAU con duracion minima 1 ano",
                "500 EUR por vivienda arrendada",
                "Fianza depositada en el Principado de Asturias"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_vacia_ast", "label": "Ha arrendado una vivienda que llevaba mas de 6 meses vacia?", "type": "boolean"},
            {"key": "num_viviendas_vacias_ast", "label": "Cuantas viviendas ha arrendado en estas condiciones?", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Trece DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 14. Por donaciones a fundaciones y ONGs
    # =========================================================================
    {
        "code": "AST-DON-001",
        "name": "Por donativos a fundaciones del Principado de Asturias",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las donaciones a fundaciones domiciliadas en Asturias acogidas a la Ley 49/2002.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: fundaciones acogidas a Ley 49/2002 con domicilio fiscal en Asturias",
                "Certificado de la entidad beneficiaria",
                "Transferencia bancaria o justificante de ingreso",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_fundaciones_ast", "label": "Ha donado a fundaciones del Principado de Asturias?", "type": "boolean"},
            {"key": "importe_donacion_fundaciones_ast", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Catorce DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 15. Por donaciones para fines culturales, investigacion y deporte
    # =========================================================================
    {
        "code": "AST-DON-002",
        "name": "Por donaciones para fines culturales, de investigacion y deportivos",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones para actividades culturales, de investigacion cientifica y deportivas en Asturias.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Finalidad: cultura, investigacion cientifica o deporte",
                "Destinatario: Principado de Asturias, entidades publicas, universidades, entidades sin animo de lucro de Asturias",
                "Certificado de la entidad beneficiaria",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_cultural_ast", "label": "Ha donado para fines culturales, investigacion o deporte en Asturias?", "type": "boolean"},
            {"key": "importe_donacion_cultural_ast", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Quince DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 16. Por donaciones a entidades de economia social
    # =========================================================================
    {
        "code": "AST-DON-003",
        "name": "Por donaciones a entidades de economia social",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a cooperativas y sociedades laborales domiciliadas en Asturias.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: cooperativas y sociedades laborales con domicilio en Asturias",
                "Entidades reguladas por Ley 5/2011 de economia social",
                "Certificado de la entidad beneficiaria",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_eco_social_ast", "label": "Ha donado a cooperativas o sociedades laborales de Asturias?", "type": "boolean"},
            {"key": "importe_donacion_eco_social_ast", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Dieciseis DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 17. Por emprendimiento — inicio de actividad economica
    # =========================================================================
    {
        "code": "AST-EMP-001",
        "name": "Por inicio de actividad economica como trabajador autonomo",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por darse de alta como trabajador autonomo y desarrollar actividad economica en Asturias.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Alta en IAE por actividad economica por cuenta propia",
                "Residencia fiscal en Asturias",
                "Alta en RETA (Seguridad Social)",
                "No haber estado de alta en la misma actividad en los 2 anos anteriores",
                "Primer periodo impositivo o siguiente de inicio de actividad",
                "Mantener actividad minimo 2 anos",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "emprendimiento_ast", "label": "Se ha dado de alta como autonomo por primera vez en Asturias?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 14.Diecisiete DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 18. Por gastos de transporte publico
    # =========================================================================
    {
        "code": "AST-MED-003",
        "name": "Por gastos de transporte publico",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 200.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades satisfechas en abono transporte publico colectivo. Max 200 EUR.",
            "limites_renta": LIMITES_AST_25_35,
            "condiciones": [
                "Abono transporte o titulo multiviaje de transporte publico colectivo",
                "Transporte publico regular en el Principado de Asturias",
                "Max 200 EUR por declaracion",
                "Conservar justificantes de compra",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "transporte_publico_ast", "label": "Ha pagado abono o titulo de transporte publico en Asturias?", "type": "boolean"},
            {"key": "gasto_transporte_ast", "label": "Importe total en transporte publico", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Dieciocho DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 19. Por residencia en concejos en riesgo de despoblacion
    # =========================================================================
    {
        "code": "AST-DES-001",
        "name": "Por residencia en concejos en riesgo de despoblacion",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por fijar residencia habitual en un concejo de Asturias en riesgo de despoblacion.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Concejo incluido en la lista oficial de riesgo de despoblacion del Principado",
                "Residencia habitual efectiva durante todo el periodo impositivo",
                "Empadronamiento en el concejo",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "despoblacion_ast", "label": "Reside en un concejo de Asturias en riesgo de despoblacion?", "type": "boolean"},
            {"key": "concejo_despoblacion_ast", "label": "Nombre del concejo", "type": "text"}
        ]),
        "legal_reference": "Art. 14.Diecinueve DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 20. Por gastos en seguros de salud
    # =========================================================================
    {
        "code": "AST-SAL-002",
        "name": "Por primas de seguros individuales de salud",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las primas de seguros individuales de salud. Max 500 EUR.",
            "limites_renta": LIMITES_AST_25_35,
            "condiciones": [
                "Seguros individuales de asistencia sanitaria",
                "Contratados con entidades aseguradoras autorizadas",
                "Cobertura del contribuyente, conyuge y/o descendientes a cargo",
                "Max 500 EUR por declaracion",
                "Conservar recibos de primas",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "seguro_salud_ast", "label": "Paga un seguro de salud privado?", "type": "boolean"},
            {"key": "prima_seguro_salud_ast", "label": "Importe anual de las primas", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Veinte DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 21. Por gastos en material escolar
    # =========================================================================
    {
        "code": "AST-EDU-001",
        "name": "Por gastos en material escolar",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos en libros de texto y material escolar para Primaria y ESO. Max 150 EUR por descendiente.",
            "limites_renta": LIMITES_AST_25_35,
            "condiciones": [
                "Gastos en libros de texto y material escolar obligatorio",
                "Hijos en Educacion Primaria o ESO",
                "Max 150 EUR por descendiente",
                "Hijos deben generar derecho al minimo por descendientes",
                "Conservar facturas durante plazo de prescripcion",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "material_escolar_ast", "label": "Ha comprado material escolar para hijos en Primaria o ESO?", "type": "boolean"},
            {"key": "gasto_material_escolar_ast", "label": "Importe total en material escolar", "type": "number"},
            {"key": "num_hijos_edu_ast", "label": "Cuantos hijos en Primaria o ESO?", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Veintiuno DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 22. Por instalacion de sistemas de energia renovable
    # =========================================================================
    {
        "code": "AST-MED-004",
        "name": "Por instalacion de sistemas de energia renovable en vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades invertidas en instalaciones de energia renovable para autoconsumo en vivienda habitual. Max 1.000 EUR.",
            "limites_renta": {"individual": 40000, "conjunta": 50000},
            "condiciones": [
                "Instalacion en vivienda habitual del contribuyente en Asturias",
                "Sistemas de energia renovable para autoconsumo (solar, eolica, biomasa, geotermia)",
                "Instalacion realizada por empresa autorizada",
                "Max 1.000 EUR por declaracion",
                "Base imponible general + ahorro <= 40.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "energia_renovable_ast", "label": "Ha instalado sistemas de energia renovable en su vivienda en Asturias?", "type": "boolean"},
            {"key": "importe_renovable_ast", "label": "Importe invertido en la instalacion", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Veintidos DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 23. Por gastos de acceso a internet en zonas rurales
    # =========================================================================
    {
        "code": "AST-TEC-001",
        "name": "Por gastos de acceso a internet en zonas rurales",
        "category": "tecnologia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 200.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de los gastos de contratacion y cuotas de internet en concejos < 5.000 hab. Max 200 EUR.",
            "limites_renta": LIMITES_AST_25_35,
            "condiciones": [
                "Residencia habitual en concejo de Asturias con < 5.000 habitantes",
                "Contratacion de servicio de internet de alta velocidad",
                "Solo en el primer ano de contratacion",
                "Max 200 EUR",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "internet_rural_ast", "label": "Ha contratado internet en un concejo de < 5.000 hab. de Asturias?", "type": "boolean"},
            {"key": "gasto_internet_ast", "label": "Importe de gastos de internet", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Veintitres DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 24. Por cuidado de personas dependientes
    # =========================================================================
    {
        "code": "AST-FAM-008",
        "name": "Por cuidado de personas dependientes",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de los gastos en cuidado de personas dependientes a cargo del contribuyente. Max 500 EUR.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Persona dependiente reconocida (Grado II o III de dependencia)",
                "Convivencia con el contribuyente o gastos justificados de cuidado",
                "Gastos en asistencia personal, centros de dia o residencias",
                "Max 500 EUR por declaracion",
                "Conservar facturas y certificado de dependencia",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "dependientes_ast", "label": "Tiene a cargo personas dependientes reconocidas?", "type": "boolean"},
            {"key": "gasto_dependientes_ast", "label": "Importe total de gastos en cuidado de dependientes", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Veinticuatro DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 25. Por inversion en entidades de nueva o reciente creacion
    # =========================================================================
    {
        "code": "AST-INV-001",
        "name": "Por inversion en entidades de nueva o reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 5000.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades invertidas en entidades de nueva o reciente creacion domiciliadas en Asturias. Max 5.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Adquisicion de acciones o participaciones de empresas de nueva/reciente creacion",
                "Entidad constituida en los 3 anos anteriores",
                "Domicilio fiscal en Asturias",
                "Participacion (+ conyuge/familiares 3er grado) <= 40% del capital",
                "Mantener inversion minimo 3 anos",
                "Entidad debe ejercer actividad economica con al menos 1 empleado en Asturias",
                "Max 5.000 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_startup_ast", "label": "Ha invertido en empresas de nueva creacion en Asturias?", "type": "boolean"},
            {"key": "importe_inversion_startup_ast", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 14.Veinticinco DLeg 2/2014 Asturias"
    },

    # =========================================================================
    # 26. Por traslado de residencia a concejo en riesgo de despoblacion
    # =========================================================================
    {
        "code": "AST-DES-002",
        "name": "Por traslado de residencia habitual a concejo en riesgo de despoblacion",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por trasladar la residencia habitual a un concejo de Asturias en riesgo de despoblacion.",
            "limites_renta": LIMITES_AST_35_45,
            "condiciones": [
                "Traslado de residencia habitual a concejo en riesgo de despoblacion",
                "Concejo incluido en lista oficial del Principado de Asturias",
                "Primer periodo impositivo en el nuevo concejo",
                "Residencia previa fuera de concejos en riesgo de despoblacion",
                "Empadronamiento efectivo",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "traslado_despoblacion_ast", "label": "Se ha trasladado a un concejo en riesgo de despoblacion en Asturias?", "type": "boolean"},
            {"key": "concejo_traslado_ast", "label": "Nombre del concejo de destino", "type": "text"}
        ]),
        "legal_reference": "Art. 14.Veintiseis DLeg 2/2014 Asturias"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_asturias(dry_run: bool = False):
    """Delete existing Asturias 2025 deductions and insert all 26."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(ASTURIAS_2025)} Asturias deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing Asturias deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(ASTURIAS_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(ASTURIAS_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in ASTURIAS_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 26 Asturias IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_asturias(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
