"""
Seed ALL 25 official Castilla-La Mancha autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunidad Autonoma de Castilla-La Mancha
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunidad-autonoma-castilla-la-mancha.html

Legal basis: Decreto Legislativo 1/2002, de 19 de noviembre, por el que se aprueba el
Texto Refundido de la Ley de Hacienda de Castilla-La Mancha (modificado por sucesivas
leyes de medidas tributarias y administrativas).

Idempotent: DELETE existing CLM deductions for tax_year=2025, then INSERT all 25.

Usage:
    cd backend
    python scripts/seed_deductions_clm_2025.py
    python scripts/seed_deductions_clm_2025.py --dry-run
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

TERRITORY = "Castilla-La Mancha"
TAX_YEAR = 2025

# Common income limits
LIMITES_CLM_27_36 = {"individual": 27000, "conjunta": 36000}
LIMITES_CLM_12_30 = {"individual": 12500, "conjunta": 30000}


# =============================================================================
# ALL 25 CASTILLA-LA MANCHA DEDUCTIONS — IRPF 2025
# =============================================================================

CLM_2025 = [
    # =========================================================================
    # 1. Por nacimiento o adopcion de hijos
    # =========================================================================
    {
        "code": "CLM-FAM-001",
        "name": "Por nacimiento o adopcion de hijos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 770.0,
        "requirements": json.dumps({
            "descripcion": "770 EUR por el 1o y 2o hijo, 900 EUR por el 3o y sucesivos. Si hijo tiene discapacidad >= 33%: 900 EUR siempre.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Nacimiento o adopcion durante el periodo impositivo",
                "Convivencia con el hijo a la fecha de devengo",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)",
                "770 EUR por 1o y 2o hijo; 900 EUR a partir del 3o",
                "900 EUR si el hijo tiene discapacidad >= 33%",
                "Declaracion conjunta: se aplica solo una vez"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_clm", "label": "Ha tenido un hijo o adoptado en 2025 en Castilla-La Mancha?", "type": "boolean"},
            {"key": "num_hijo_orden_clm", "label": "Numero de orden del hijo (1o, 2o, 3o...)", "type": "number"},
            {"key": "hijo_discapacidad_33_clm", "label": "El hijo tiene discapacidad >= 33%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Uno DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 2. Por familia numerosa
    # =========================================================================
    {
        "code": "CLM-FAM-002",
        "name": "Por familia numerosa",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR familia numerosa general, 600 EUR especial, 900 EUR con 6+ hijos o discapacidad >= 65% en uno de los progenitores.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Titulo de familia numerosa vigente a fecha de devengo",
                "300 EUR categoria general (3 hijos)",
                "600 EUR categoria especial (5+ hijos o 4 con condiciones especiales)",
                "900 EUR si 6 o mas hijos o progenitor con discapacidad >= 65%",
                "Declaracion conjunta: una sola deduccion",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa_clm", "label": "Tiene titulo de familia numerosa vigente?", "type": "boolean"},
            {"key": "tipo_familia_numerosa_clm", "label": "Categoria de familia numerosa", "type": "select", "options": ["general", "especial", "6_o_mas"]}
        ]),
        "legal_reference": "Art. 1.Dos DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 3. Por discapacidad del contribuyente
    # =========================================================================
    {
        "code": "CLM-FAM-003",
        "name": "Por discapacidad del contribuyente",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por discapacidad >= 65% del contribuyente.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Grado de discapacidad >= 65% reconocido",
                "Acreditado mediante certificado oficial",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_65_clm", "label": "Tiene discapacidad reconocida >= 65%?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Tres DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 4. Por discapacidad de ascendientes o descendientes
    # =========================================================================
    {
        "code": "CLM-FAM-004",
        "name": "Por discapacidad de ascendientes o descendientes",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada ascendiente o descendiente con discapacidad >= 65% que conviva con el contribuyente.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Ascendiente o descendiente con discapacidad >= 65%",
                "Convivencia con el contribuyente",
                "Deben generar derecho al minimo por ascendientes o descendientes",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familiar_discapacidad_65_clm", "label": "Tiene ascendientes o descendientes con discapacidad >= 65% conviviendo con usted?", "type": "boolean"},
            {"key": "num_familiares_discap_clm", "label": "Cuantos familiares con discapacidad >= 65%?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Cuatro DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 5. Por acogimiento familiar no remunerado de menores
    # =========================================================================
    {
        "code": "CLM-FAM-005",
        "name": "Por acogimiento familiar no remunerado de menores",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por cada menor en regimen de acogimiento familiar permanente o preadoptivo no remunerado.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Acogimiento familiar permanente o preadoptivo",
                "Modalidad no remunerada",
                "Menor de edad a fecha de devengo",
                "Formalizado ante la autoridad competente",
                "Convivencia durante al menos 183 dias en el periodo impositivo",
                "No aplica si el acogimiento deriva en adopcion en el mismo ejercicio",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "acogimiento_clm", "label": "Tiene menores en acogimiento familiar no remunerado?", "type": "boolean"},
            {"key": "num_menores_acogidos_clm", "label": "Cuantos menores tiene en acogimiento?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Cinco DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 6. Por gastos en educacion infantil (guarderia)
    # =========================================================================
    {
        "code": "CLM-EDU-001",
        "name": "Por gastos en educacion infantil (guarderia)",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 100.0,
        "percentage": None,
        "fixed_amount": 100.0,
        "requirements": json.dumps({
            "descripcion": "100 EUR por hijo en el primer ciclo de educacion infantil (0-3 anos) en centro autorizado.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Primer ciclo de educacion infantil (0-3 anos)",
                "Centro autorizado por la Consejeria de Educacion de CLM",
                "100 EUR por cada hijo matriculado",
                "Convivencia con el contribuyente",
                "Gastos netos de becas o subvenciones",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "guarderia_clm", "label": "Tiene hijos en guarderia (0-3 anos) en Castilla-La Mancha?", "type": "boolean"},
            {"key": "num_hijos_guarderia_clm", "label": "Cuantos hijos asisten a guarderia?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Seis DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 7. Por cuidado de ascendientes mayores de 75 anos
    # =========================================================================
    {
        "code": "CLM-FAM-006",
        "name": "Por cuidado de ascendientes mayores de 75 anos",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 200.0,
        "requirements": json.dumps({
            "descripcion": "200 EUR por cada ascendiente mayor de 75 anos que conviva con el contribuyente y genere derecho al minimo por ascendientes.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Ascendiente mayor de 75 anos a fecha de devengo",
                "Convivencia con el contribuyente durante al menos 183 dias",
                "Debe generar derecho al minimo por ascendientes",
                "Rentas del ascendiente <= 8.000 EUR anuales (excluidas exentas)",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ascendiente_75_clm", "label": "Convive con ascendientes mayores de 75 anos?", "type": "boolean"},
            {"key": "num_ascendientes_75_clm", "label": "Cuantos ascendientes mayores de 75 anos conviven con usted?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Siete DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 8. Por alquiler de vivienda habitual (jovenes)
    # =========================================================================
    {
        "code": "CLM-VIV-001",
        "name": "Por alquiler de vivienda habitual por jovenes",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 450.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades satisfechas en alquiler de vivienda habitual. Max 450 EUR. Para menores de 36 anos.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Edad < 36 anos a fecha de devengo",
                "Vivienda habitual en Castilla-La Mancha",
                "Contrato de arrendamiento segun LAU",
                "Fianza depositada en la JCCM",
                "Max 450 EUR anuales",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_joven_clm", "label": "Paga alquiler de vivienda habitual en CLM siendo menor de 36 anos?", "type": "boolean"},
            {"key": "importe_alquiler_clm", "label": "Importe anual de alquiler", "type": "number"},
            {"key": "menor_36_clm", "label": "Tiene menos de 36 anos?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Ocho DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 9. Por alquiler de vivienda habitual en zonas rurales
    # =========================================================================
    {
        "code": "CLM-VIV-002",
        "name": "Por alquiler de vivienda habitual en zonas rurales",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 550.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades de alquiler en municipios <= 5.000 hab. Max 550 EUR.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Vivienda habitual en municipio de CLM con poblacion <= 5.000 habitantes",
                "Contrato de arrendamiento segun LAU",
                "Fianza depositada en la JCCM",
                "Max 550 EUR anuales",
                "Incompatible con deduccion de alquiler jovenes si se aplica por la misma vivienda",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_rural_clm", "label": "Paga alquiler en un municipio de CLM con <= 5.000 habitantes?", "type": "boolean"},
            {"key": "importe_alquiler_rural_clm", "label": "Importe anual de alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Nueve DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 10. Por inversion en vivienda habitual en municipios < 5.000 hab.
    # =========================================================================
    {
        "code": "CLM-VIV-003",
        "name": "Por inversion en vivienda habitual en municipios de menos de 5.000 habitantes",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en adquisicion o rehabilitacion de vivienda habitual en municipio < 5.000 hab. Max 500 EUR.",
            "limites_renta": {"individual": 35000, "conjunta": 45000},
            "condiciones": [
                "Municipio de CLM con poblacion < 5.000 habitantes",
                "Adquisicion o rehabilitacion de vivienda habitual",
                "Max 500 EUR anuales",
                "Vivienda debe constituir residencia habitual durante al menos 3 anos",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_vivienda_rural_clm", "label": "Ha adquirido vivienda habitual en municipio < 5.000 hab. de CLM?", "type": "boolean"},
            {"key": "importe_inversion_vivienda_clm", "label": "Importe invertido en vivienda", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Diez DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 11. Por donaciones con finalidad ecologica
    # =========================================================================
    {
        "code": "CLM-DON-001",
        "name": "Por donaciones con finalidad ecologica",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones dinerarias puras y simples a la JCCM destinadas a medio ambiente.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: Junta de Comunidades de Castilla-La Mancha",
                "Finalidad: defensa y conservacion del medio ambiente",
                "Transferencia bancaria o justificante de ingreso",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_ecologica_clm", "label": "Ha realizado donaciones ecologicas a la JCCM?", "type": "boolean"},
            {"key": "importe_donacion_ecologica_clm", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Once DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 12. Por donaciones para cooperacion internacional
    # =========================================================================
    {
        "code": "CLM-DON-002",
        "name": "Por donaciones para cooperacion internacional al desarrollo",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a ONGs para cooperacion internacional.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: ONGs inscritas en el registro de CLM",
                "Finalidad: cooperacion internacional al desarrollo",
                "Transferencia bancaria o justificante de ingreso",
                "Certificado de la entidad beneficiaria",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_cooperacion_clm", "label": "Ha donado a ONGs de cooperacion internacional inscritas en CLM?", "type": "boolean"},
            {"key": "importe_donacion_cooperacion_clm", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Doce DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 13. Por donaciones a entidades de promocion de investigacion
    # =========================================================================
    {
        "code": "CLM-DON-003",
        "name": "Por donaciones a entidades promotoras de la investigacion",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a la Universidad de CLM u otros centros de investigacion.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: UCLM, centros de investigacion de CLM",
                "Finalidad: investigacion, desarrollo e innovacion",
                "Transferencia bancaria o justificante de ingreso",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_investigacion_clm", "label": "Ha donado a centros de investigacion de CLM?", "type": "boolean"},
            {"key": "importe_donacion_investigacion_clm", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Trece DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 14. Por donaciones al mecenazgo deportivo
    # =========================================================================
    {
        "code": "CLM-DON-004",
        "name": "Por donaciones al mecenazgo deportivo de Castilla-La Mancha",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a clubes deportivos y entidades de promocion del deporte de CLM.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: clubes deportivos elementales y basicos de CLM, Federaciones deportivas de CLM",
                "Certificado de la entidad beneficiaria",
                "Transferencia bancaria o justificante de ingreso",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_deportivo_clm", "label": "Ha donado a clubes o federaciones deportivas de CLM?", "type": "boolean"},
            {"key": "importe_donacion_deportivo_clm", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Catorce DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 15. Por gastos en la adquisicion de libros de texto y ensenanza idiomas
    # =========================================================================
    {
        "code": "CLM-EDU-002",
        "name": "Por gastos en adquisicion de libros de texto y ensenanza de idiomas",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 300.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "100% de los gastos en libros de texto y material escolar, y ensenanza extraescolar de idiomas. Limites segun BI y numero de hijos.",
            "limites_renta": LIMITES_CLM_12_30,
            "condiciones": [
                "Hijos en Educacion Basica (Primaria y ESO)",
                "Libros de texto: limite 100 EUR por hijo (BI < 12.500 EUR) o 50 EUR por hijo (BI 12.500-27.000 EUR individual)",
                "Ensenanza de idiomas extraescolar: limite adicional de 100 EUR por hijo",
                "Hijos deben generar derecho al minimo por descendientes",
                "Conservar facturas durante plazo de prescripcion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "libros_texto_clm", "label": "Ha comprado libros de texto o pagado clases de idiomas para sus hijos?", "type": "boolean"},
            {"key": "gasto_libros_clm", "label": "Importe en libros de texto y material escolar", "type": "number"},
            {"key": "gasto_idiomas_clm", "label": "Importe en ensenanza extraescolar de idiomas", "type": "number"},
            {"key": "num_hijos_edu_clm", "label": "Cuantos hijos en Primaria o ESO?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Quince DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 16. Por residencia habitual en zonas rurales en riesgo de despoblacion
    # =========================================================================
    {
        "code": "CLM-DES-001",
        "name": "Por residencia habitual en zonas rurales en riesgo de despoblacion",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por fijar residencia habitual en municipio de CLM con <= 2.000 habitantes o que figure como zona en riesgo de despoblacion.",
            "limites_renta": {"individual": 35000, "conjunta": 45000},
            "condiciones": [
                "Municipio de CLM con poblacion <= 2.000 habitantes",
                "O municipio declarado en riesgo de despoblacion por la JCCM",
                "Residencia habitual efectiva (no segunda vivienda)",
                "Empadronamiento en el municipio durante todo el periodo impositivo",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "despoblacion_clm", "label": "Reside en un municipio de CLM con <= 2.000 habitantes o en zona de despoblacion?", "type": "boolean"},
            {"key": "municipio_despoblacion_clm", "label": "Nombre del municipio", "type": "text"}
        ]),
        "legal_reference": "Art. 1.Dieciseis DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 17. Por traslado de residencia a zonas rurales en riesgo de despoblacion
    # =========================================================================
    {
        "code": "CLM-DES-002",
        "name": "Por traslado de residencia habitual por motivos laborales a zonas rurales",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por trasladar la residencia habitual por motivos laborales a un municipio de CLM con <= 5.000 hab.",
            "limites_renta": {"individual": 35000, "conjunta": 45000},
            "condiciones": [
                "Traslado de residencia habitual por motivos laborales",
                "Municipio de destino en CLM con poblacion <= 5.000 habitantes",
                "Primer periodo impositivo en el nuevo municipio",
                "Residencia previa en municipio distinto de la zona rural",
                "Empadronamiento efectivo",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "traslado_rural_clm", "label": "Se ha trasladado a un municipio rural de CLM (<= 5.000 hab.) por motivos laborales?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Diecisiete DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 18. Por vehiculo electrico o punto de recarga
    # =========================================================================
    {
        "code": "CLM-MED-001",
        "name": "Por adquisicion de vehiculos electricos o instalacion de puntos de recarga",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 3000.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en adquisicion de vehiculo electrico o punto de recarga. Max 3.000 EUR.",
            "limites_renta": {"individual": 40000, "conjunta": 50000},
            "condiciones": [
                "Vehiculo 100% electrico (BEV) o punto de recarga domestico",
                "Vehiculo nuevo, no destinado a actividad economica",
                "Primera matriculacion en Espana",
                "Max 3.000 EUR por vehiculo o instalacion",
                "Mantener propiedad minimo 3 anos",
                "Base imponible general + ahorro <= 40.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico_clm", "label": "Ha adquirido un vehiculo electrico o punto de recarga en CLM?", "type": "boolean"},
            {"key": "importe_vehiculo_electrico_clm", "label": "Importe de la adquisicion", "type": "number"},
            {"key": "tipo_adquisicion_clm", "label": "Tipo de adquisicion", "type": "select", "options": ["vehiculo_electrico", "punto_recarga"]}
        ]),
        "legal_reference": "Art. 1.Dieciocho DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 19. Por autonomos nuevos en zonas rurales
    # =========================================================================
    {
        "code": "CLM-EMP-001",
        "name": "Por inicio de actividad economica en zonas rurales",
        "category": "empleo",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 500.0,
        "requirements": json.dumps({
            "descripcion": "500 EUR por alta en actividad economica por cuenta propia en municipio de CLM con <= 5.000 hab.",
            "limites_renta": {"individual": 35000, "conjunta": 45000},
            "condiciones": [
                "Alta en IAE por actividad economica por cuenta propia",
                "Municipio de CLM con poblacion <= 5.000 habitantes",
                "Alta en RETA (Seguridad Social)",
                "Primer periodo impositivo o siguiente de inicio de actividad",
                "No haber estado de alta en la misma actividad en los 2 anos anteriores",
                "Mantener actividad minimo 2 anos",
                "Base imponible general + ahorro <= 35.000 EUR (individual) o 45.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "autonomo_rural_clm", "label": "Se ha dado de alta como autonomo en un municipio rural de CLM (<= 5.000 hab.)?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Diecinueve DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 20. Por gastos de enfermedad
    # =========================================================================
    {
        "code": "CLM-SAL-001",
        "name": "Por gastos de enfermedad",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 500.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% de los gastos no cubiertos por seguros, en enfermedad cronica de alta complejidad. Max 500 EUR.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Gastos originados por enfermedad cronica de alta complejidad",
                "No cubiertos por la Seguridad Social ni por seguro privado",
                "Requiere prescripcion medica oficial",
                "Conservar facturas durante plazo de prescripcion",
                "Max 500 EUR por declaracion",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_enfermedad_clm", "label": "Tiene gastos por enfermedad cronica no cubiertos por la Seguridad Social?", "type": "boolean"},
            {"key": "importe_enfermedad_clm", "label": "Importe total de los gastos medicos", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veinte DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 21. Por donaciones a fundaciones y asociaciones de utilidad publica de CLM
    # =========================================================================
    {
        "code": "CLM-DON-005",
        "name": "Por donaciones a fundaciones y asociaciones de utilidad publica",
        "category": "donaciones",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las donaciones a fundaciones y asociaciones declaradas de utilidad publica de CLM.",
            "limites_renta": {},
            "condiciones": [
                "Donaciones dinerarias puras y simples",
                "Destinatario: fundaciones o asociaciones de utilidad publica con domicilio fiscal en CLM",
                "Certificado de la entidad beneficiaria",
                "Transferencia bancaria o justificante de ingreso",
                "Limite: 10% de la base liquidable del contribuyente"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_fundaciones_clm", "label": "Ha donado a fundaciones o asociaciones de utilidad publica de CLM?", "type": "boolean"},
            {"key": "importe_donacion_fundaciones_clm", "label": "Importe total donado", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veintiuno DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 22. Por familia monoparental
    # =========================================================================
    {
        "code": "CLM-FAM-007",
        "name": "Por familia monoparental",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR para contribuyentes que sean madres o padres de familia monoparental.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Familia monoparental: unico progenitor que convive con hijos menores o con discapacidad",
                "No convivir con otra persona distinta de los descendientes",
                "Hijos deben generar derecho al minimo por descendientes",
                "300 EUR por declaracion",
                "Base imponible general + ahorro <= 27.000 EUR (individual)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "monoparental_clm", "label": "Es familia monoparental?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 1.Veintidos DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 23. Por arrendamiento de viviendas vacias a inquilinos
    # =========================================================================
    {
        "code": "CLM-VIV-004",
        "name": "Por arrendamiento de vivienda vacia con fines sociales",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 600.0,
        "percentage": None,
        "fixed_amount": 600.0,
        "requirements": json.dumps({
            "descripcion": "600 EUR por arrendar una vivienda que llevara mas de un ano vacia como vivienda habitual de inquilino.",
            "limites_renta": {},
            "condiciones": [
                "Vivienda que hubiera estado desocupada al menos un ano antes del arrendamiento",
                "Arrendada como vivienda habitual del arrendatario",
                "Contrato de arrendamiento segun LAU",
                "Duracion minima del contrato: 1 ano",
                "Fianza depositada en la JCCM",
                "600 EUR por cada vivienda arrendada que cumpla requisitos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vivienda_vacia_clm", "label": "Ha arrendado una vivienda que llevaba mas de 1 ano vacia?", "type": "boolean"},
            {"key": "num_viviendas_vacias_clm", "label": "Cuantas viviendas ha arrendado en estas condiciones?", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veintitres DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 24. Por instalacion de sistemas de energia renovable en vivienda
    # =========================================================================
    {
        "code": "CLM-MED-002",
        "name": "Por instalacion de sistemas de energia renovable en vivienda habitual",
        "category": "medioambiente",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1500.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades invertidas en instalaciones de autoconsumo energetico (placas solares, aerotermia, etc.) en vivienda habitual. Max 1.500 EUR.",
            "limites_renta": {"individual": 40000, "conjunta": 50000},
            "condiciones": [
                "Instalacion en vivienda habitual del contribuyente en CLM",
                "Sistemas de energia renovable para autoconsumo (solar fotovoltaica, solar termica, aerotermia)",
                "Instalacion realizada por empresa autorizada",
                "Max 1.500 EUR por declaracion",
                "Base imponible general + ahorro <= 40.000 EUR (individual) o 50.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "energia_renovable_clm", "label": "Ha instalado sistemas de energia renovable en su vivienda habitual en CLM?", "type": "boolean"},
            {"key": "importe_renovable_clm", "label": "Importe invertido en la instalacion", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veinticuatro DLeg 1/2002 CLM"
    },

    # =========================================================================
    # 25. Por arrendamiento de vivienda habitual vinculado a operaciones de dacion en pago
    # =========================================================================
    {
        "code": "CLM-VIV-005",
        "name": "Por arrendamiento de vivienda habitual vinculado a dacion en pago",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 450.0,
        "percentage": 15.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "15% de las cantidades de alquiler de vivienda habitual por contribuyentes que hayan perdido la propiedad por dacion en pago o ejecucion hipotecaria. Max 450 EUR.",
            "limites_renta": LIMITES_CLM_27_36,
            "condiciones": [
                "Contribuyente que perdio la propiedad de su vivienda por dacion en pago o ejecucion hipotecaria",
                "Arrendamiento de nueva vivienda habitual en CLM",
                "Contrato de arrendamiento segun LAU",
                "Max 450 EUR anuales",
                "Base imponible general + ahorro <= 27.000 EUR (individual) o 36.000 EUR (conjunta)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "dacion_pago_clm", "label": "Perdio su vivienda por dacion en pago o ejecucion hipotecaria y ahora alquila?", "type": "boolean"},
            {"key": "importe_alquiler_dacion_clm", "label": "Importe anual de alquiler", "type": "number"}
        ]),
        "legal_reference": "Art. 1.Veinticinco DLeg 1/2002 CLM"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_clm(dry_run: bool = False):
    """Delete existing CLM 2025 deductions and insert all 25."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(CLM_2025)} Castilla-La Mancha deductions for IRPF {TAX_YEAR}")
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
                    print(f"  Deleted {result.rows_affected} existing CLM deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                pass

        print()

    inserted = 0
    for i, d in enumerate(CLM_2025, 1):
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(CLM_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    categories = {}
    for d in CLM_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 25 Castilla-La Mancha IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_clm(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
