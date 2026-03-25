"""
Seed ALL 21 official Cantabria autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de Cantabria
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-cantabria.html

Legal basis: Decreto Legislativo 62/2008, de 19 de junio, por el que se aprueba el
Texto Refundido de la Ley de Medidas Fiscales en materia de Tributos cedidos por el Estado
de la Comunidad Autonoma de Cantabria (sucesivas modificaciones por leyes de cantabria de
medidas fiscales y administrativas).

Idempotent: DELETE existing Cantabria deductions for tax_year=2025, then INSERT all 21.

Usage:
    cd backend
    python scripts/seed_deductions_cantabria_2025.py
    python scripts/seed_deductions_cantabria_2025.py --dry-run
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

TERRITORY = "Cantabria"
TAX_YEAR = 2025

# Common income limits
LIMITES_CTB_22_31 = {"individual": 22946, "conjunta": 31485}
LIMITES_CTB_25_35 = {"individual": 25000, "conjunta": 35000}


# =============================================================================
# ALL 21 CANTABRIA DEDUCTIONS — IRPF 2025
# =============================================================================

CANTABRIA_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion de hijos
    # =========================================================================
    {
        "code": "CTB-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por el 1o y 2o hijo, 500 EUR por el 3o y sucesivos. Incremento adicional por hijos con discapacidad >= 33%.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Nacimiento o adopcion durante el periodo impositivo",
                "Convivencia con el hijo a fecha de devengo",
                "300 EUR por 1o y 2o hijo; 500 EUR 3o y sucesivos",
                "Incremento de 100 EUR por hijo con discapacidad >= 33%",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)",
                "Declaracion conjunta: se aplica solo una vez"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_ctb", "label": "Ha tenido un hijo o adoptado en 2025 en Cantabria?", "type": "boolean"},
            {"key": "num_hijo_orden_ctb", "label": "Numero de orden del hijo (1o, 2o, 3o...)", "type": "number"},
            {"key": "hijo_discapacidad_33_ctb", "label": "El hijo tiene discapacidad >= 33%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 2.Uno DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 2. Por cuidado de hijos menores de 3 anos
    # =========================================================================
    {
        "code": "CTB-FAM-002",
        "name": "Por cuidado de hijos menores de 3 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades satisfechas en guarderia o empleada de hogar para cuidado de menores de 3 anos. Max 300 EUR.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Hijos menores de 3 anos a fecha de devengo",
                "Gastos en guarderia autorizada o empleada de hogar dada de alta en la Seguridad Social",
                "Ambos progenitores deben tener rendimientos del trabajo o actividades economicas",
                "Max 300 EUR por declaracion",
                "Gastos netos de becas o subvenciones",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "cuidado_menores_3_ctb", "label": "Tiene gastos de guarderia o empleada de hogar para hijos < 3 anos?", "type": "boolean"},
            {"key": "gasto_cuidado_menores_ctb", "label": "Importe total de gastos", "type": "number"},
            {"key": "num_hijos_menores_3_ctb", "label": "Cuantos hijos menores de 3 anos?", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Dos DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 3. Por familia numerosa
    # =========================================================================
    {
        "code": "CTB-FAM-003",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR familia numerosa general, 600 EUR especial.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Titulo de familia numerosa vigente a fecha de devengo",
                "300 EUR categoria general",
                "600 EUR categoria especial",
                "Declaracion conjunta: una sola deduccion",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_ctb", "label": "Tiene titulo de familia numerosa vigente?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_ctb", "label": "Categoria de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 2.Tres DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 4. Por discapacidad del contribuyente
    # =========================================================================
    {
        "code": "CTB-FAM-004",
        "name": "Por discapacidad del contribuyente",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por discapacidad >= 65% del contribuyente.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Grado de discapacidad >= 65% reconocido oficialmente",
                "Acreditado mediante certificado del IMSERSO o comunidad autonoma",
                "300 EUR por declaracion",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_65_ctb", "label": "Tiene discapacidad reconocida >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 2.Cuatro DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 5. Por discapacidad de familiares a cargo
    # =========================================================================
    {
        "code": "CTB-FAM-005",
        "name": "Por cuidado de familiares con discapacidad",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada ascendiente o descendiente con discapacidad >= 65% que conviva con el contribuyente.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Ascendiente o descendiente con discapacidad >= 65%",
                "Convivencia con el contribuyente",
                "Deben generar derecho al minimo por ascendientes o descendientes",
                "300 EUR por familiar a cargo",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familiar_discapacidad_ctb", "label": "Tiene familiares con discapacidad >= 65% a su cargo?", "type": "boolean"},
            {"key": "num_familiares_discap_ctb", "label": "Cuantos familiares con discapacidad >= 65%?", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Cinco DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 6. Por acogimiento familiar de menores
    # =========================================================================
    {
        "code": "CTB-FAM-006",
        "name": "Por acogimiento familiar de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 240.0,
        "requirements": json.dumps({
            "descripcion": "240 EUR por cada menor en acogimiento familiar no remunerado.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Acogimiento familiar no remunerado de menores",
                "Formalizado ante la autoridad competente",
                "Convivencia durante al menos 183 dias en el periodo impositivo",
                "240 EUR por menor acogido",
                "No aplica si el acogimiento deriva en adopcion en el mismo ejercicio",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_ctb", "label": "Tiene menores en acogimiento familiar no remunerado?", "type": "boolean"},
            {"key": "num_menores_acogidos_ctb", "label": "Cuantos menores tiene en acogimiento?", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Seis DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 7. Por alquiler de vivienda habitual
    # =========================================================================
    {
        "code": "CTB-VIV-001",
        "name": "Por alquiler de vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades satisfechas en alquiler de vivienda habitual. Max 300 EUR. Menores de 35 anos o familia numerosa.",
            "limites_renta": LIMITES_CTB_22_31,
            "condiciones": [
                "Vivienda habitual del contribuyente en Cantabria",
                "Menores de 35 anos O familia numerosa",
                "Contrato de arrendamiento segun LAU",
                "Deposito de fianza en el Gobierno de Cantabria",
                "Max 300 EUR anuales",
                "Base imponible general + ahorro <= 22.946 EUR (individual) o 31.485 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_ctb", "label": "Paga alquiler de vivienda habitual en Cantabria?", "type": "boolean"},
            {"key": "importe_alquiler_ctb", "label": "Importe anual de alquiler", "type": "number"},
            {"key": "menor_35_ctb", "label": "Tiene menos de 35 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 2.Siete DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 8. Por inversion en vivienda en zonas rurales en riesgo de despoblacion
    # =========================================================================
    {
        "code": "CTB-VIV-002",
        "name": "Por inversion en vivienda habitual en zonas rurales despobladas",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en adquisicion o rehabilitacion de vivienda habitual en municipio en riesgo de despoblacion. Max 600 EUR.",
            "limites_renta": {"individual": 35000, "conjunta": 45000},
            "condiciones": [
                "Municipio de Cantabria declarado en riesgo de despoblacion",
                "Adquisicion o rehabilitacion de vivienda habitual",
                "Max 600 EUR anuales",
                "Vivienda debe constituir residencia habitual durante al menos 3 anos",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_despoblacion_ctb", "label": "Ha adquirido vivienda en zona rural despoblada de Cantabria?", "type": "boolean"},
            {"key": "importe_vivienda_despoblacion_ctb", "label": "Importe invertido en vivienda", "type": "number"},
            {"key": "municipio_despoblacion_ctb", "label": "Nombre del municipio", "type": "text"}
        ]),
        "legal_reference": "Art. 2.Ocho DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 9. Por donaciones a fundaciones y asociaciones
    # =========================================================================
    {
        "code": "CTB-DON-001",
        "name": "Por donativos a fundaciones o asociaciones de utilidad publica de Cantabria",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a fundaciones o asociaciones de utilidad publica domiciliadas en Cantabria.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: fundaciones o asociaciones de utilidad publica con domicilio fiscal en Cantabria",
                "Entidades acogidas a Ley 49/2002 o declaradas de utilidad publica",
                "Certificado de la entidad beneficiaria",
                "Transferencia bancaria o justificante de ingreso",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_fundaciones_ctb", "label": "Ha donado a fundaciones o asociaciones de utilidad publica de Cantabria?", "type": "boolean"},
            {"key": "importe_donacion_fundaciones_ctb", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Nueve DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 10. Por donaciones a entidades deportivas
    # =========================================================================
    {
        "code": "CTB-DON-002",
        "name": "Por donaciones a entidades deportivas de Cantabria",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a clubes deportivos de base y federaciones deportivas de Cantabria.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: clubes deportivos de base, federaciones y asociaciones deportivas de Cantabria",
                "Certificado de la entidad beneficiaria",
                "Transferencia bancaria o justificante de ingreso",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_deportiva_ctb", "label": "Ha donado a entidades deportivas de Cantabria?", "type": "boolean"},
            {"key": "importe_donacion_deportiva_ctb", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Diez DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 11. Por donaciones para fines culturales
    # =========================================================================
    {
        "code": "CTB-DON-003",
        "name": "Por donaciones para fines culturales",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones al Gobierno de Cantabria o entidades culturales para la proteccion del patrimonio cultural.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: Gobierno de Cantabria, ayuntamientos, entidades culturales de Cantabria",
                "Finalidad: proteccion y conservacion del patrimonio cultural",
                "Certificado de la entidad beneficiaria",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_cultural_ctb", "label": "Ha donado para fines culturales en Cantabria?", "type": "boolean"},
            {"key": "importe_donacion_cultural_ctb", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Once DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 12. Por gastos de educacion
    # =========================================================================
    {
        "code": "CTB-EDU-001",
        "name": "Por gastos de educacion de los descendientes",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de los gastos en material escolar, uniformes y libros de texto para hijos en ESO. Max 100 EUR por descendiente.",
            "limites_renta": LIMITES_CTB_22_31,
            "condiciones": [
                "Hijos en Educacion Secundaria Obligatoria (ESO)",
                "Gastos en libros de texto, material escolar y uniformes",
                "Max 100 EUR por descendiente",
                "Hijos deben generar derecho al minimo por descendientes",
                "Conservar facturas durante plazo de prescripcion",
                "Base imponible general + ahorro <= 22.946 EUR (individual) o 31.485 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_educacion_ctb", "label": "Ha comprado material escolar/libros para hijos en ESO?", "type": "boolean"},
            {"key": "gasto_educacion_ctb", "label": "Importe total en material escolar", "type": "number"},
            {"key": "num_hijos_edu_ctb", "label": "Cuantos hijos en ESO?", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Doce DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 13. Por vehiculos electricos
    # =========================================================================
    {
        "code": "CTB-MED-001",
        "name": "Por adquisicion de vehiculos electricos",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% del importe satisfecho en adquisicion de vehiculo electrico. Max 1.500 EUR.",
            "limites_renta": {"individual": 40000, "conjunta": 50000},
            "condiciones": [
                "Vehiculo 100% electrico (BEV)",
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
            {"key": "vehiculo_electrico_ctb", "label": "Ha comprado un vehiculo electrico en Cantabria?", "type": "boolean"},
            {"key": "importe_vehiculo_ctb", "label": "Precio del vehiculo", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Trece DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 14. Por arrendamiento de viviendas vacias
    # =========================================================================
    {
        "code": "CTB-VIV-003",
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
                "Fianza depositada en el Gobierno de Cantabria",
                "500 EUR por vivienda arrendada"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_vacia_ctb", "label": "Ha arrendado una vivienda que llevaba mas de 6 meses vacia?", "type": "boolean"},
            {"key": "num_viviendas_vacias_ctb", "label": "Cuantas viviendas ha arrendado en estas condiciones?", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Catorce DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 15. Por residencia habitual en zonas en riesgo de despoblacion
    # =========================================================================
    {
        "code": "CTB-DES-001",
        "name": "Por residencia habitual en zonas en riesgo de despoblacion",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por residir de forma habitual en municipio de Cantabria en riesgo de despoblacion.",
            "limites_renta": {"individual": 35000, "conjunta": 45000},
            "condiciones": [
                "Municipio de Cantabria declarado en riesgo de despoblacion",
                "Residencia habitual efectiva durante todo el periodo impositivo",
                "Empadronamiento en el municipio",
                "500 EUR por declaracion",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "despoblacion_ctb", "label": "Reside en un municipio de Cantabria en riesgo de despoblacion?", "type": "boolean"},
            {"key": "municipio_despoblacion_ctb", "label": "Nombre del municipio", "type": "text"}
        ]),
        "legal_reference": "Art. 2.Quince DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 16. Por obras de mejora en vivienda habitual
    # =========================================================================
    {
        "code": "CTB-VIV-004",
        "name": "Por obras de mejora y accesibilidad en vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades en obras de accesibilidad y adaptacion de vivienda habitual para personas con discapacidad. Max 500 EUR.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Obras de accesibilidad y adaptacion en vivienda habitual",
                "Contribuyente o familiar conviviente con discapacidad >= 33%",
                "Obras certificadas como necesarias para la accesibilidad",
                "Max 500 EUR por declaracion",
                "Conservar facturas y certificados",
                "Base imponible general + ahorro <= 25.000 EUR (individual) o 35.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "obras_accesibilidad_ctb", "label": "Ha realizado obras de accesibilidad en su vivienda?", "type": "boolean"},
            {"key": "importe_obras_ctb", "label": "Importe de las obras", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Dieciseis DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 17. Por gastos de enfermedad
    # =========================================================================
    {
        "code": "CTB-SAL-001",
        "name": "Por gastos de enfermedad",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de los gastos no cubiertos por el sistema publico de salud para enfermedades cronicas. Max 500 EUR.",
            "limites_renta": LIMITES_CTB_22_31,
            "condiciones": [
                "Gastos por enfermedad cronica del contribuyente o familiares a cargo",
                "No cubiertos por la Seguridad Social ni por seguro privado",
                "Requiere prescripcion medica oficial",
                "Conservar facturas",
                "Max 500 EUR por declaracion",
                "Base imponible general + ahorro <= 22.946 EUR (individual) o 31.485 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_enfermedad_ctb", "label": "Tiene gastos por enfermedad no cubiertos por la Seguridad Social?", "type": "boolean"},
            {"key": "importe_enfermedad_ctb", "label": "Importe total de los gastos medicos", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Diecisiete DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 18. Por inversion en instalaciones de energia renovable
    # =========================================================================
    {
        "code": "CTB-MED-002",
        "name": "Por instalacion de sistemas de energia renovable en vivienda",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1000.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades invertidas en instalaciones de autoconsumo energetico en vivienda habitual. Max 1.000 EUR.",
            "limites_renta": {"individual": 40000, "conjunta": 50000},
            "condiciones": [
                "Instalacion en vivienda habitual del contribuyente en Cantabria",
                "Sistemas de energia renovable para autoconsumo (solar fotovoltaica, solar termica, aerotermia, biomasa)",
                "Instalacion realizada por empresa autorizada",
                "Max 1.000 EUR por declaracion",
                "Base imponible general + ahorro <= 40.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "energia_renovable_ctb", "label": "Ha instalado sistemas de energia renovable en su vivienda en Cantabria?", "type": "boolean"},
            {"key": "importe_renovable_ctb", "label": "Importe invertido en la instalacion", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Dieciocho DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 19. Por familia monoparental
    # =========================================================================
    {
        "code": "CTB-FAM-007",
        "name": "Por familia monoparental",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 200.0,
        "requirements": json.dumps({
            "descripcion": "200 EUR para contribuyentes que sean madres o padres de familia monoparental.",
            "limites_renta": LIMITES_CTB_25_35,
            "condiciones": [
                "Familia monoparental: unico progenitor que convive con hijos menores o dependientes",
                "No convivir con otra persona distinta de los descendientes",
                "Hijos deben generar derecho al minimo por descendientes",
                "200 EUR por declaracion",
                "Base imponible general + ahorro <= 25.000 EUR (individual)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "monoparental_ctb", "label": "Es familia monoparental?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 2.Diecinueve DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 20. Por traslado de residencia a zona en riesgo de despoblacion
    # =========================================================================
    {
        "code": "CTB-DES-002",
        "name": "Por traslado de residencia habitual a municipio en riesgo de despoblacion",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por trasladar la residencia habitual a un municipio de Cantabria en riesgo de despoblacion.",
            "limites_renta": {"individual": 35000, "conjunta": 45000},
            "condiciones": [
                "Traslado de residencia habitual a municipio en riesgo de despoblacion",
                "Municipio incluido en lista oficial del Gobierno de Cantabria",
                "Primer periodo impositivo en el nuevo municipio",
                "Residencia previa fuera de municipios en riesgo de despoblacion",
                "Empadronamiento efectivo",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "traslado_despoblacion_ctb", "label": "Se ha trasladado a un municipio en riesgo de despoblacion en Cantabria?", "type": "boolean"},
            {"key": "municipio_traslado_ctb", "label": "Nombre del municipio de destino", "type": "text"}
        ]),
        "legal_reference": "Art. 2.Veinte DLeg 62/2008 Cantabria"
    },

    # =========================================================================
    # 21. Por inversion en entidades de nueva creacion
    # =========================================================================
    {
        "code": "CTB-INV-001",
        "name": "Por inversion en entidades de nueva o reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 4000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en entidades de nueva o reciente creacion domiciliadas en Cantabria. Max 4.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Adquisicion de acciones o participaciones de empresas de nueva/reciente creacion",
                "Entidad constituida en los 3 anos anteriores",
                "Domicilio fiscal en Cantabria",
                "Participacion (+ conyuge/familiares 3er grado) <= 40% del capital",
                "Mantener inversion minimo 3 anos",
                "Entidad debe ejercer actividad economica con al menos 1 empleado en Cantabria",
                "Max 4.000 EUR"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_startup_ctb", "label": "Ha invertido en empresas de nueva creacion en Cantabria?", "type": "boolean"},
            {"key": "importe_inversion_startup_ctb", "label": "Importe invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 2.Veintiuno DLeg 62/2008 Cantabria"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_cantabria(dry_run: bool = False):
    """Delete existing Cantabria 2025 deductions and insert all 21."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(CANTABRIA_2025)} Cantabria deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing Cantabria deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(CANTABRIA_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(CANTABRIA_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in CANTABRIA_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 21 Cantabria IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_cantabria(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
