"""
Seed ALL 19 official Aragon autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de Aragon
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-aragon.html

Legal basis: Decreto Legislativo 1/2005, de 26 de septiembre, del Gobierno de Aragon,
por el que se aprueba el texto refundido de las disposiciones dictadas por la Comunidad
Autonoma de Aragon en materia de tributos cedidos.

Idempotent: DELETE existing Aragon deductions for tax_year=2025, then INSERT all 19.

Usage:
    cd backend
    python scripts/seed_deductions_aragon_2025.py
    python scripts/seed_deductions_aragon_2025.py --dry-run
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

TERRITORY = "Aragon"
TAX_YEAR = 2025

# Common income limits
LIMITES_ARAGON_35_50 = {"individual": 35000, "conjunta": 50000}
LIMITES_ARAGON_21_3535 = {"individual": 21000, "conjunta": 35000}


# =============================================================================
# ALL 19 ARAGON DEDUCTIONS — IRPF 2025
# =============================================================================

ARAGON_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion del primer hijo
    # =========================================================================
    {
        "code": "ARA-FAM-001",
        "name": "Por nacimiento o adopcion del primer hijo",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por nacimiento o adopcion del primer hijo. 700 EUR si la residencia habitual es un municipio de menos de 10.000 habitantes.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Nacimiento o adopcion del primer hijo en el periodo impositivo",
                "Residencia habitual en Aragon",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 50.000 EUR (conjunta)",
                "600 EUR general, 700 EUR si municipio < 10.000 habitantes",
                "En tributacion conjunta: deduccion unica de 600/700 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_primer_hijo_aragon", "label": "Ha tenido o adoptado su primer hijo en Aragon?", "type": "boolean"},
            {"key": "municipio_rural_aragon", "label": "Reside en un municipio de menos de 10.000 habitantes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 110.1 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 2. Por nacimiento o adopcion del segundo hijo
    # =========================================================================
    {
        "code": "ARA-FAM-002",
        "name": "Por nacimiento o adopcion del segundo hijo",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 750.0,
        "percentage": None,
        "fixed_amount": 750.0,
        "requirements": json.dumps({
            "descripcion": "750 EUR por nacimiento o adopcion del segundo hijo. Incremento si municipio rural.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Nacimiento o adopcion del segundo hijo en el periodo impositivo",
                "Residencia habitual en Aragon",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_segundo_hijo_aragon", "label": "Ha tenido o adoptado su segundo hijo en Aragon?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 110.1 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 3. Por nacimiento o adopcion del tercer hijo o sucesivos
    # =========================================================================
    {
        "code": "ARA-FAM-003",
        "name": "Por nacimiento o adopcion del tercer hijo o sucesivos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 900.0,
        "percentage": None,
        "fixed_amount": 900.0,
        "requirements": json.dumps({
            "descripcion": "900 EUR por nacimiento o adopcion del tercer hijo o sucesivos.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Nacimiento o adopcion del tercer hijo o sucesivos en el periodo impositivo",
                "Residencia habitual en Aragon",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_tercer_hijo_aragon", "label": "Ha tenido o adoptado su tercer hijo o mas en Aragon?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 110.1 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 4. Por familia numerosa
    # =========================================================================
    {
        "code": "ARA-FAM-004",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": None,
        "fixed_amount": 200.0,
        "requirements": json.dumps({
            "descripcion": "200 EUR (general) o 400 EUR (especial) por familia numerosa en Aragon.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Titulo de familia numerosa a 31 de diciembre",
                "Residencia habitual en Aragon",
                "200 EUR familia numerosa general, 400 EUR especial",
                "Si ambos progenitores declaran: deduccion a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_aragon", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_aragon", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 110.2 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 5. Por cuidado de personas dependientes
    # =========================================================================
    {
        "code": "ARA-FAM-005",
        "name": "Por cuidado de personas dependientes",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada ascendiente o descendiente con discapacidad >= 65% o dependencia reconocida que conviva con el contribuyente.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Ascendiente mayor de 75 anos o descendiente con discapacidad >= 65%",
                "O persona con dependencia reconocida (Ley 39/2006)",
                "Convivencia durante al menos la mitad del periodo impositivo",
                "Rentas de la persona dependiente <= 8.000 EUR anuales",
                "Residencia habitual en Aragon"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "cuidado_dependientes_aragon", "label": "Convive con personas dependientes o con discapacidad >= 65%?", "type": "boolean"},
            {"key": "num_dependientes_aragon", "label": "Numero de personas dependientes a su cargo", "type": "number"}
        ]),
        "legal_reference": "Art. 110.3 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 6. Por discapacidad del contribuyente
    # =========================================================================
    {
        "code": "ARA-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 200.0,
        "percentage": None,
        "fixed_amount": 200.0,
        "requirements": json.dumps({
            "descripcion": "200 EUR por grado de discapacidad reconocido >= 33% del contribuyente.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Grado de discapacidad reconocido >= 33%",
                "Certificado emitido por organismo competente",
                "Residencia habitual en Aragon"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_contribuyente_aragon", "label": "Tiene un grado de discapacidad >= 33%?", "type": "boolean"},
            {"key": "grado_discapacidad_aragon", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 110.4 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 7. Por gastos de guarderia de hijos menores de 3 anos
    # =========================================================================
    {
        "code": "ARA-FAM-006",
        "name": "Por gastos de guarderia de hijos menores de 3 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 250.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades satisfechas en guarderia para hijos menores de 3 anos. Max 250 EUR por hijo.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Hijos menores de 3 anos a 31 de diciembre",
                "Guarderia o centro de educacion infantil autorizado",
                "Ambos progenitores deben percibir rendimientos del trabajo o de actividades economicas",
                "Max 250 EUR por hijo",
                "Si ambos progenitores declaran: deduccion a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_aragon", "label": "Tiene hijos menores de 3 anos en guarderia?", "type": "boolean"},
            {"key": "gasto_guarderia_aragon", "label": "Importe total de gastos de guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_aragon", "label": "Numero de hijos en guarderia", "type": "number"}
        ]),
        "legal_reference": "Art. 110.5 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 8. Por alquiler de vivienda habitual (jovenes)
    # =========================================================================
    {
        "code": "ARA-VIV-001",
        "name": "Por alquiler de vivienda habitual para jovenes",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% del alquiler de vivienda habitual para menores de 36 anos. Max 400 EUR.",
            "limites_renta": LIMITES_ARAGON_21_35,
            "condiciones": [
                "Edad del contribuyente < 36 anos a 31 de diciembre",
                "Contrato de arrendamiento de vivienda habitual",
                "Base imponible general + ahorro <= 21.000 EUR (individual) o 35.000 EUR (conjunta)",
                "La vivienda debe estar situada en Aragon",
                "Deposito de fianza en el organo competente",
                "Incompatible con deduccion estatal por alquiler"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_joven_aragon", "label": "Alquila vivienda habitual en Aragon siendo menor de 36 anos?", "type": "boolean"},
            {"key": "importe_alquiler_aragon", "label": "Importe anual del alquiler", "type": "number"},
            {"key": "menor_36_aragon", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 110.6 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 9. Por inversion en vivienda habitual en municipio rural < 3.000 hab.
    # =========================================================================
    {
        "code": "ARA-VIV-002",
        "name": "Por inversion en vivienda habitual en municipio rural",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades invertidas en adquisicion o rehabilitacion de vivienda habitual en municipios de menos de 3.000 habitantes. Max 1.000 EUR.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Vivienda habitual en municipio aragones de menos de 3.000 habitantes",
                "Adquisicion, construccion o rehabilitacion de vivienda habitual",
                "Residencia efectiva y continuada durante al menos 3 anos",
                "Max 1.000 EUR",
                "No aplica a segundas residencias"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_rural_aragon", "label": "Ha invertido en vivienda habitual en un municipio < 3.000 hab. de Aragon?", "type": "boolean"},
            {"key": "importe_inversion_vivienda_rural", "label": "Importe invertido en vivienda", "type": "number"}
        ]),
        "legal_reference": "Art. 110.7 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 10. Por donaciones con finalidad ecologica y en investigacion y desarrollo
    # =========================================================================
    {
        "code": "ARA-DON-001",
        "name": "Por donaciones con finalidad ecologica y en investigacion y desarrollo",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones dinerarias puras y simples para fines ecologicos, investigacion y desarrollo cientifico y tecnico.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras, simples e irrevocables",
                "Destinatarios: Gobierno de Aragon y sus organismos publicos para fines ecologicos o de I+D+i",
                "Requiere certificacion del organo receptor",
                "Base de la deduccion: importe del donativo"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_ecologico_aragon", "label": "Ha realizado donaciones ecologicas o de I+D en Aragon?", "type": "boolean"},
            {"key": "importe_donativo_ecologico", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 111 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 11. Por donaciones a entidades sin fines de lucro
    # =========================================================================
    {
        "code": "ARA-DON-002",
        "name": "Por donaciones a entidades sin fines de lucro",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones dinerarias a fundaciones y asociaciones declaradas de utilidad publica en Aragon.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Fundaciones o asociaciones declaradas de utilidad publica",
                "Con domicilio social en Aragon",
                "Que persigan fines de naturaleza cultural, asistencial, deportiva o sanitaria",
                "Requiere certificacion de la entidad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_entidades_aragon", "label": "Ha donado a fundaciones o asociaciones de utilidad publica en Aragon?", "type": "boolean"},
            {"key": "importe_donativo_entidades", "label": "Importe total de las donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 111.2 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 12. Por emprendimiento y creacion de empleo
    # =========================================================================
    {
        "code": "ARA-EMP-001",
        "name": "Por inversion en acciones o participaciones de entidades nuevas o de reciente creacion",
        "category": "emprendimiento",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en acciones o participaciones de entidades nuevas o de reciente creacion. Max 4.000 EUR. 500 EUR adicionales si es empresa innovadora.",
            "limites_renta": {},
            "condiciones": [
                "Entidad constituida en los 3 anos anteriores a la inversion",
                "Domicilio social y fiscal en Aragon",
                "Capital social maximo 200.000 EUR en el periodo de la inversion",
                "La entidad debe ejercer actividad economica con al menos 1 empleado",
                "Participacion del contribuyente + familiares <= 40% del capital",
                "Mantenimiento de la inversion durante al menos 3 anos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_emprendimiento_aragon", "label": "Ha invertido en entidades de nueva creacion en Aragon?", "type": "boolean"},
            {"key": "importe_inversion_emprendimiento", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 110.8 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 13. Por adquisicion de vehiculo electrico
    # =========================================================================
    {
        "code": "ARA-MED-001",
        "name": "Por adquisicion de vehiculo electrico",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del precio de adquisicion de vehiculo electrico nuevo. Max 1.000 EUR.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Vehiculo electrico nuevo (categoria M1 o L)",
                "Primera matriculacion en Espana",
                "No destinado a actividad economica",
                "Mantener la propiedad durante al menos 3 anos",
                "Un vehiculo por contribuyente y periodo impositivo",
                "Residencia habitual en Aragon"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_aragon", "label": "Ha comprado un vehiculo electrico nuevo en Aragon?", "type": "boolean"},
            {"key": "precio_vehiculo_electrico_aragon", "label": "Precio del vehiculo electrico", "type": "number"}
        ]),
        "legal_reference": "Art. 110.9 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 14. Por obras de eficiencia energetica en vivienda habitual
    # =========================================================================
    {
        "code": "ARA-MED-002",
        "name": "Por obras de mejora de eficiencia energetica en vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en obras de mejora de eficiencia energetica de la vivienda habitual. Max 1.500 EUR.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Obras que mejoren la eficiencia energetica de la vivienda habitual",
                "Certificado de eficiencia energetica antes y despues de las obras",
                "Mejora minima de una letra en la calificacion energetica",
                "Vivienda habitual situada en Aragon",
                "Facturas y justificantes de pago obligatorios"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_aragon", "label": "Ha realizado obras de eficiencia energetica en su vivienda habitual en Aragon?", "type": "boolean"},
            {"key": "importe_eficiencia_energetica", "label": "Importe de las obras", "type": "number"}
        ]),
        "legal_reference": "Art. 110.10 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 15. Por trabajo autonomo de nuevos autonomos
    # =========================================================================
    {
        "code": "ARA-EMP-002",
        "name": "Por inicio de actividad de trabajo autonomo",
        "category": "emprendimiento",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por alta inicial en el RETA como trabajador autonomo durante el periodo impositivo.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Alta inicial o sin actividad por cuenta propia en los 2 anos anteriores",
                "Dado de alta en el censo de empresarios y actividad economica",
                "Residencia habitual en Aragon",
                "Actividad economica principal desarrollada en Aragon",
                "Mantenimiento de la actividad durante al menos 2 anos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nuevo_autonomo_aragon", "label": "Se ha dado de alta como autonomo por primera vez en Aragon?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 110.11 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 16. Por gastos en libros de texto y material escolar
    # =========================================================================
    {
        "code": "ARA-EDU-001",
        "name": "Por gastos en libros de texto y material escolar",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": None,
        "fixed_amount": 100.0,
        "requirements": json.dumps({
            "descripcion": "Deduccion por gastos en libros de texto y material escolar: hasta 100 EUR por hijo en educacion basica y obligatoria.",
            "limites_renta": LIMITES_ARAGON_21_35,
            "condiciones": [
                "Hijos que cursen educacion infantil, primaria, ESO o formacion profesional basica",
                "Hijos que generen derecho al minimo por descendientes",
                "Gastos en libros de texto editados para el desarrollo del curriculo",
                "Material escolar segun listado oficial del centro educativo",
                "Conservar justificantes: facturas nominativas",
                "Base imponible general + ahorro <= 21.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "libros_material_escolar_aragon", "label": "Ha tenido gastos en libros de texto o material escolar para sus hijos?", "type": "boolean"},
            {"key": "num_hijos_escolar_aragon", "label": "Numero de hijos en educacion basica u obligatoria", "type": "number"},
            {"key": "gasto_libros_escolar_aragon", "label": "Importe total de gastos en libros y material escolar", "type": "number"}
        ]),
        "legal_reference": "Art. 110.12 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 17. Por residencia habitual en zonas rurales en riesgo de despoblacion
    # =========================================================================
    {
        "code": "ARA-RUR-001",
        "name": "Por residencia habitual en zonas rurales en riesgo de despoblacion",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por residencia habitual y efectiva en municipios aragoneses en riesgo de despoblacion (< 3.000 habitantes).",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Residencia habitual y efectiva en municipio aragones < 3.000 habitantes",
                "Figurar en el padron municipal del municipio durante todo el periodo impositivo",
                "No se aplica si ya se beneficia de la deduccion por vivienda rural (ARA-VIV-002) por la misma vivienda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "residencia_rural_aragon", "label": "Reside en un municipio aragones de menos de 3.000 habitantes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 110.13 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 18. Por adopcion internacional
    # =========================================================================
    {
        "code": "ARA-FAM-007",
        "name": "Por adopcion internacional",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por cada adopcion internacional realizada durante el periodo impositivo.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Adopcion internacional constituida conforme a la legislacion vigente",
                "Inscripcion en el Registro Civil",
                "Residencia habitual en Aragon",
                "Si ambos adoptantes declaran: deduccion a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "adopcion_internacional_aragon", "label": "Ha realizado una adopcion internacional?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 110.14 DLeg 1/2005 Aragon"
    },

    # =========================================================================
    # 19. Por gastos de suministros en vivienda habitual de zonas rurales
    # =========================================================================
    {
        "code": "ARA-RUR-002",
        "name": "Por gastos de suministros en vivienda habitual en zonas rurales",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 200.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de los gastos de suministros (luz, agua, gas, calefaccion, telefono, internet) de vivienda habitual en municipios < 3.000 hab. Max 200 EUR.",
            "limites_renta": LIMITES_ARAGON_35_50,
            "condiciones": [
                "Vivienda habitual en municipio aragones < 3.000 habitantes",
                "Gastos de suministros: electricidad, agua, gas, calefaccion, telefono, internet",
                "Titularidad del contrato a nombre del contribuyente o conyuge",
                "Residencia habitual y efectiva durante todo el periodo impositivo",
                "Conservar facturas y justificantes de pago"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "suministros_rural_aragon", "label": "Tiene gastos de suministros en vivienda habitual en municipio < 3.000 hab. de Aragon?", "type": "boolean"},
            {"key": "gasto_suministros_rural_aragon", "label": "Importe total de gastos de suministros", "type": "number"}
        ]),
        "legal_reference": "Art. 110.15 DLeg 1/2005 Aragon"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_aragon(dry_run: bool = False):
    """Delete existing Aragon 2025 deductions and insert all 19."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(ARAGON_2025)} Aragon deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing Aragon deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(ARAGON_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(ARAGON_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in ARAGON_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 19 Aragon IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_aragon(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
