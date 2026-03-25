"""
Seed ALL 19 official Extremadura autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de Extremadura
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-extremadura.html

Legal basis: Decreto Legislativo 1/2018, de 10 de abril, por el que se aprueba el
Texto Refundido de las disposiciones legales de la Comunidad Autonoma de Extremadura
en materia de tributos cedidos por el Estado.

Idempotent: DELETE existing Extremadura deductions for tax_year=2025, then INSERT all 19.

Usage:
    cd backend
    python scripts/seed_deductions_extremadura_2025.py
    python scripts/seed_deductions_extremadura_2025.py --dry-run
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

TERRITORY = "Extremadura"
TAX_YEAR = 2025

# Common income limits
LIMITES_EXT_19_24 = {"individual": 19000, "conjunta": 24000}
LIMITES_EXT_28_45 = {"individual": 28000, "conjunta": 45000}


# =============================================================================
# ALL 19 EXTREMADURA DEDUCTIONS — IRPF 2025
# =============================================================================

EXTREMADURA_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion de hijos
    # =========================================================================
    {
        "code": "EXT-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada hijo nacido o adoptado en el periodo impositivo. Importe incrementado en partos/adopciones multiples.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Nacimiento o adopcion en el periodo impositivo",
                "300 EUR por cada hijo",
                "600 EUR si parto o adopcion multiple (por cada hijo a partir del segundo)",
                "El hijo debe convivir con el contribuyente a 31 de diciembre",
                "Si ambos progenitores: prorrateo a partes iguales",
                "Base imponible general + ahorro <= 28.000 EUR individual / 45.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_extremadura", "label": "Ha tenido un nacimiento o adopcion en 2025?", "type": "boolean"},
            {"key": "num_hijos_nacidos_extremadura", "label": "Numero de hijos nacidos/adoptados", "type": "number"},
            {"key": "parto_multiple_extremadura", "label": "Ha sido parto o adopcion multiple?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Uno DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 2. Por discapacidad del contribuyente
    # =========================================================================
    {
        "code": "EXT-DIS-001",
        "name": "Por discapacidad del contribuyente",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por contribuyente con grado de discapacidad >= 33%.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Grado de discapacidad >= 33% reconocido oficialmente",
                "300 EUR fijos",
                "Certificado oficial de discapacidad vigente a 31 de diciembre",
                "Base imponible general + ahorro <= 28.000 EUR individual / 45.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_extremadura", "label": "Tiene reconocido un grado de discapacidad >= 33%?", "type": "boolean"},
            {"key": "grado_discapacidad_extremadura", "label": "Grado de discapacidad (%)", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Dos DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 3. Por familia numerosa
    # =========================================================================
    {
        "code": "EXT-FAM-002",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": None,
        "fixed_amount": 200.0,
        "requirements": json.dumps({
            "descripcion": "200 EUR por familia numerosa de categoria general. 400 EUR por familia numerosa especial.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Titulo de familia numerosa vigente a 31 de diciembre",
                "200 EUR familia numerosa general",
                "400 EUR familia numerosa especial",
                "Si ambos progenitores: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_extremadura", "label": "Tiene titulo de familia numerosa?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_extremadura", "label": "Tipo de familia numerosa", "type": "select", "options": ["general", "especial"]}
        ]),
        "legal_reference": "Art. 5.Tres DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 4. Por cuidado de hijos menores de 6 anos
    # =========================================================================
    {
        "code": "EXT-FAM-003",
        "name": "Por cuidado de hijos menores de 6 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 250.0,
        "percentage": None,
        "fixed_amount": 250.0,
        "requirements": json.dumps({
            "descripcion": "250 EUR por cada hijo menor de 6 anos que conviva con el contribuyente.",
            "limites_renta": LIMITES_EXT_19_24,
            "condiciones": [
                "Hijos menores de 6 anos a 31 de diciembre",
                "Convivencia con el contribuyente",
                "250 EUR por cada hijo menor de 6 anos",
                "Ambos progenitores deben realizar actividad economica por cuenta propia o ajena",
                "Si ambos progenitores: prorrateo a partes iguales",
                "Base imponible general + ahorro <= 19.000 EUR individual / 24.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "hijos_menores_6_extremadura", "label": "Tiene hijos menores de 6 anos?", "type": "boolean"},
            {"key": "num_hijos_menores_6_extremadura", "label": "Cuantos hijos menores de 6 anos?", "type": "number"},
            {"key": "ambos_trabajan_extremadura", "label": "Trabajan ambos progenitores?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Cuatro DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 5. Por acogimiento familiar de menores
    # =========================================================================
    {
        "code": "EXT-FAM-004",
        "name": "Por acogimiento familiar de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 250.0,
        "percentage": None,
        "fixed_amount": 250.0,
        "requirements": json.dumps({
            "descripcion": "250 EUR por cada menor en regimen de acogimiento familiar.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Acogimiento familiar no preadoptivo de menores",
                "Resolucion administrativa o judicial de acogimiento",
                "Convivencia minima de 183 dias en el periodo impositivo",
                "250 EUR por menor acogido",
                "Si varios contribuyentes: prorrateo a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_familiar_extremadura", "label": "Tiene menores en acogimiento familiar?", "type": "boolean"},
            {"key": "num_menores_acogidos_extremadura", "label": "Numero de menores acogidos", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Cinco DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 6. Por adquisicion de vivienda habitual para jovenes
    # =========================================================================
    {
        "code": "EXT-VIV-001",
        "name": "Por adquisicion de vivienda habitual para jovenes y victimas del terrorismo",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades invertidas en adquisicion de vivienda habitual por jovenes (< 36 anos) o victimas del terrorismo. Max 300 EUR.",
            "limites_renta": LIMITES_EXT_19_24,
            "condiciones": [
                "Edad < 36 anos a fecha de devengo, o victima del terrorismo",
                "Adquisicion de vivienda habitual en Extremadura",
                "5% de las cantidades invertidas",
                "Max 300 EUR anuales",
                "La vivienda debe constituir residencia habitual durante al menos 3 anos",
                "Base imponible general + ahorro <= 19.000 EUR individual / 24.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_joven_extremadura", "label": "Ha adquirido vivienda habitual siendo menor de 36 anos o victima del terrorismo?", "type": "boolean"},
            {"key": "importe_inversion_vivienda_extremadura", "label": "Importe invertido en vivienda", "type": "number"},
            {"key": "menor_36_extremadura", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Seis DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 7. Por arrendamiento de vivienda habitual para jovenes
    # =========================================================================
    {
        "code": "EXT-VIV-002",
        "name": "Por arrendamiento de vivienda habitual para menores de 36 anos",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de las cantidades satisfechas por alquiler de vivienda habitual para menores de 36 anos. Max 400 EUR.",
            "limites_renta": LIMITES_EXT_19_24,
            "condiciones": [
                "Edad < 36 anos a fecha de devengo",
                "Arrendamiento de vivienda habitual en Extremadura",
                "10% de las cantidades pagadas en concepto de alquiler",
                "Max 400 EUR anuales",
                "Contrato de arrendamiento inscrito y fianza depositada",
                "No ser propietario de otra vivienda",
                "Base imponible general + ahorro <= 19.000 EUR individual / 24.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_joven_extremadura", "label": "Es menor de 36 anos y paga alquiler por su vivienda habitual?", "type": "boolean"},
            {"key": "importe_alquiler_extremadura", "label": "Importe anual de alquiler", "type": "number"},
            {"key": "menor_36_alquiler_extremadura", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Siete DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 8. Por donaciones a entidades sin animo de lucro
    # =========================================================================
    {
        "code": "EXT-DON-001",
        "name": "Por donaciones a entidades de caracter social, cultural o deportivo",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones dinerarias a entidades sin animo de lucro de Extremadura con fines sociales, culturales o deportivos.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras e irrevocables",
                "Entidades sin animo de lucro con sede o actividad en Extremadura",
                "Fines sociales, culturales, cientificos o deportivos",
                "Transferencia bancaria obligatoria",
                "Certificado de la entidad beneficiaria",
                "Deduccion no puede superar el 10% de la cuota integra autonomica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_entidades_extremadura", "label": "Ha realizado donaciones a entidades sociales/culturales/deportivas en Extremadura?", "type": "boolean"},
            {"key": "importe_donaciones_extremadura", "label": "Importe total de donaciones", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Ocho DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 9. Por ELA (Esclerosis Lateral Amiotrofica)
    # =========================================================================
    {
        "code": "EXT-SAL-001",
        "name": "Por gastos relacionados con la Esclerosis Lateral Amiotrofica (ELA)",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por contribuyente o familiar conviviente diagnosticado de ELA.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Diagnostico de Esclerosis Lateral Amiotrofica (ELA)",
                "Contribuyente, conyuge o descendientes/ascendientes que generen derecho a minimos",
                "300 EUR por persona afectada",
                "Certificado medico oficial del diagnostico",
                "Compatible con otras deducciones por discapacidad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ela_extremadura", "label": "Tiene usted o algun familiar conviviente diagnosticado de ELA?", "type": "boolean"},
            {"key": "num_afectados_ela_extremadura", "label": "Numero de personas afectadas por ELA", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Nueve DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 10. Por arrendamiento de viviendas vacias
    # =========================================================================
    {
        "code": "EXT-VIV-003",
        "name": "Por puesta en el mercado de alquiler de viviendas vacias",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% del precio del arrendamiento de viviendas que estaban vacias y se ponen en alquiler como vivienda habitual. Max 400 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Vivienda que llevaba vacia al menos 1 ano antes del arrendamiento",
                "El arrendamiento debe ser de vivienda habitual del inquilino",
                "Contrato de arrendamiento de duracion minima de 1 ano",
                "5% de las rentas de alquiler obtenidas",
                "Max 400 EUR anuales",
                "Fianza depositada en la Junta de Extremadura"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_vacia_extremadura", "label": "Ha arrendado una vivienda que llevaba vacia mas de un ano?", "type": "boolean"},
            {"key": "renta_alquiler_vivienda_vacia_extremadura", "label": "Importe anual del alquiler obtenido", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Diez DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 11. Por residencia en municipios en riesgo de despoblacion
    # =========================================================================
    {
        "code": "EXT-DES-001",
        "name": "Por residencia habitual en municipios en riesgo de despoblacion",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por contribuyente con residencia habitual en municipio extremeno en riesgo de despoblacion.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Residencia habitual en municipio de Extremadura con menos de 3.000 habitantes",
                "Empadronamiento durante todo el periodo impositivo",
                "500 EUR fijos por contribuyente",
                "El municipio debe estar en la lista oficial de riesgo de despoblacion",
                "Compatible con otras deducciones por vivienda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "despoblacion_extremadura", "label": "Reside en un municipio de Extremadura con menos de 3.000 habitantes?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Once DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 12. Por emprendimiento
    # =========================================================================
    {
        "code": "EXT-INV-001",
        "name": "Por inicio de actividad economica como emprendedor",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por inicio de actividad economica como emprendedor en Extremadura.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Alta en actividad economica por primera vez en el periodo impositivo",
                "Residencia fiscal en Extremadura",
                "Mantenimiento de la actividad durante al menos 2 anos",
                "No haber ejercido la misma actividad en los 3 anos anteriores",
                "500 EUR para el ano de inicio"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "emprendimiento_extremadura", "label": "Ha iniciado una actividad economica como emprendedor en 2025?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 5.Doce DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 13. Por trabajo dependiente
    # =========================================================================
    {
        "code": "EXT-TRA-001",
        "name": "Por rendimientos del trabajo dependiente",
        "category": "trabajo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por contribuyente con rendimientos del trabajo dependiente que cumplan los requisitos de renta.",
            "limites_renta": {"individual": 12000},
            "condiciones": [
                "Rendimientos netos del trabajo como unica fuente de renta",
                "Base imponible general <= 12.000 EUR",
                "300 EUR fijos",
                "Rendimientos del trabajo deben representar al menos el 90% de la base imponible general",
                "No obtener rendimientos de actividades economicas, capital mobiliario o inmobiliario significativos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "trabajo_dependiente_extremadura", "label": "Son sus rendimientos del trabajo su unica fuente de renta significativa?", "type": "boolean"},
            {"key": "base_imponible_extremadura", "label": "Base imponible general estimada", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Trece DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 14. Por gastos de guarderia de menores de 3 anos
    # =========================================================================
    {
        "code": "EXT-FAM-005",
        "name": "Por gastos de guarderia de hijos menores de 4 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 250.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de los gastos de guarderia o centros de primer ciclo de educacion infantil. Max 250 EUR por hijo.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Hijos menores de 4 anos a 31 de diciembre",
                "Centro de educacion infantil autorizado",
                "10% de los gastos de custodia, matricula y alimentacion",
                "Max 250 EUR por hijo",
                "Conservar facturas y justificantes"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_extremadura", "label": "Tiene hijos menores de 4 anos en guarderia?", "type": "boolean"},
            {"key": "gasto_guarderia_extremadura", "label": "Importe total de gastos de guarderia", "type": "number"},
            {"key": "num_hijos_guarderia_extremadura", "label": "Cuantos hijos menores de 4 anos asisten a guarderia?", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Catorce DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 15. Por donaciones a la conservacion del patrimonio natural
    # =========================================================================
    {
        "code": "EXT-DON-002",
        "name": "Por donaciones para la conservacion y difusion del patrimonio natural",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones para la conservacion, reparacion y restauracion del patrimonio natural extremeno.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones destinadas a la conservacion del patrimonio natural de Extremadura",
                "Incluye espacios naturales protegidos, biodiversidad, restauracion de habitats",
                "Entidades sin animo de lucro con actividad medioambiental en Extremadura",
                "Transferencia bancaria obligatoria",
                "Certificado de la entidad beneficiaria"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donaciones_patrimonio_natural_extremadura", "label": "Ha donado para la conservacion del patrimonio natural de Extremadura?", "type": "boolean"},
            {"key": "importe_donaciones_natural_extremadura", "label": "Importe total donado al patrimonio natural", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Quince DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 16. Por adquisicion de material escolar
    # =========================================================================
    {
        "code": "EXT-EDU-001",
        "name": "Por adquisicion de material escolar",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": 100.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos en material escolar de Educacion Primaria y Secundaria. Max 150 EUR por descendiente.",
            "limites_renta": LIMITES_EXT_19_24,
            "condiciones": [
                "Descendientes matriculados en Educacion Primaria o ESO",
                "Material escolar: libros de texto, material de papeleria, mochilas",
                "Max 150 EUR por descendiente",
                "Conservar facturas detalladas",
                "Base imponible general + ahorro <= 19.000 EUR individual / 24.000 EUR conjunta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "material_escolar_extremadura", "label": "Tiene hijos en Educacion Primaria o ESO?", "type": "boolean"},
            {"key": "gasto_material_escolar_extremadura", "label": "Importe total de gastos de material escolar", "type": "number"},
            {"key": "num_hijos_escolar_extremadura", "label": "Cuantos hijos cursan Primaria/ESO?", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Dieciseis DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 17. Por inversion en entidades de economia social
    # =========================================================================
    {
        "code": "EXT-INV-002",
        "name": "Por inversion en entidades de economia social",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 3000.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades invertidas en entidades de economia social domiciliadas en Extremadura. Max 3.000 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Entidad de economia social segun Ley 5/2011",
                "Sede social y domicilio fiscal en Extremadura",
                "Participacion del contribuyente (+ familiares) <= 40% del capital",
                "Al menos 1 empleado a jornada completa",
                "Mantenimiento de la inversion minimo 5 anos",
                "Formalizado en escritura publica"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_economia_social_extremadura", "label": "Ha invertido en entidades de economia social en Extremadura?", "type": "boolean"},
            {"key": "importe_inversion_eco_social_extremadura", "label": "Importe total invertido", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Diecisiete DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 18. Por alquiler de vivienda habitual en zona rural
    # =========================================================================
    {
        "code": "EXT-VIV-004",
        "name": "Por arrendamiento de vivienda habitual en zona rural",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 400.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades pagadas por alquiler de vivienda habitual en municipios de menos de 3.000 habitantes. Max 400 EUR.",
            "limites_renta": LIMITES_EXT_28_45,
            "condiciones": [
                "Arrendamiento de vivienda habitual en municipio de < 3.000 habitantes",
                "15% de las cantidades pagadas en alquiler",
                "Max 400 EUR anuales",
                "Contrato de arrendamiento registrado",
                "Fianza depositada en organismo competente",
                "Compatible con la deduccion por despoblacion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_rural_extremadura", "label": "Paga alquiler en un municipio de menos de 3.000 habitantes?", "type": "boolean"},
            {"key": "importe_alquiler_rural_extremadura", "label": "Importe anual de alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Dieciocho DLeg 1/2018 Extremadura"
    },

    # =========================================================================
    # 19. Por gastos de eficiencia energetica en vivienda habitual
    # =========================================================================
    {
        "code": "EXT-MED-001",
        "name": "Por obras de mejora de eficiencia energetica de la vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las inversiones en mejora de eficiencia energetica de la vivienda habitual. Max 600 EUR.",
            "limites_renta": {},
            "condiciones": [
                "Obras que mejoren la calificacion energetica de la vivienda habitual",
                "Certificado de eficiencia energetica previo y posterior a la obra",
                "Mejora de al menos una letra en la calificacion",
                "Vivienda habitual en Extremadura",
                "Max 600 EUR de deduccion",
                "Conservar facturas y certificados de instalacion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "eficiencia_energetica_extremadura", "label": "Ha realizado obras de mejora de eficiencia energetica en su vivienda?", "type": "boolean"},
            {"key": "importe_eficiencia_extremadura", "label": "Importe total invertido en eficiencia energetica", "type": "number"}
        ]),
        "legal_reference": "Art. 5.Diecinueve DLeg 1/2018 Extremadura"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_extremadura(dry_run: bool = False):
    """Delete existing Extremadura 2025 deductions and insert all 19."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(EXTREMADURA_2025)} Extremadura deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing Extremadura deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(EXTREMADURA_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(EXTREMADURA_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in EXTREMADURA_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 19 Extremadura IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_extremadura(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
