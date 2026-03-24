"""
Seed ALL 40 official Valencia (Comunitat Valenciana) autonomous deductions for IRPF 2025.

Source: AEAT Manual Practico IRPF 2025 — Comunitat Valenciana
https://sede.agenciatributaria.gob.es/Sede/ayuda/manuales-videos-folletos/manuales-practicos/
    irpf-2025-deducciones-autonomicas/comunitat-valenciana.html

Legal basis: Ley 13/1997, de 23 de diciembre, por la que se regula el tramo autonomico
del IRPF y restantes tributos cedidos (Comunitat Valenciana).
Modified by Ley 5/2025, de 30 de mayo.

Idempotent: DELETE existing Valencia deductions for tax_year=2025, then INSERT all 40.

Usage:
    cd backend
    python scripts/seed_deductions_valencia_2025.py
    python scripts/seed_deductions_valencia_2025.py --dry-run
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

TERRITORY = "Valencia"
TAX_YEAR = 2025

# Common income limits for most Valencia deductions
LIMITES_STANDARD = {"individual": 30000, "conjunta": 47000}
LIMITES_STANDARD_PLENA = {"individual": 27000, "conjunta": 44000}


# =============================================================================
# ALL 40 VALENCIA DEDUCTIONS — IRPF 2025
# =============================================================================

VALENCIA_2025 = [
    # =========================================================================
    # 1. Por nacimiento, adopcion, delegacion de guarda o acogimiento familiar
    # =========================================================================
    {
        "code": "VAL-FAM-001",
        "name": "Por nacimiento, adopcion, delegacion de guarda con fines de adopcion o acogimiento familiar",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 300.0,
        "requirements": json.dumps({
            "descripcion": "300 EUR por cada hijo nacido, adoptado o acogido durante el periodo impositivo y los dos siguientes. Hijo debe dar derecho al minimo por descendientes estatal.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Hijo nacido, adoptado, acogido o en delegacion de guarda en el periodo impositivo",
                "Hijo debe dar derecho al minimo por descendientes",
                "Si dos contribuyentes tienen derecho, se prorratea a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "label": "Ha tenido hijos nacidos, adoptados o acogidos en 2025?", "type": "boolean"},
            {"key": "num_hijos_recientes", "label": "Cuantos hijos ha tenido, adoptado o acogido?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.a), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 2. Por nacimiento o adopcion multiples
    # =========================================================================
    {
        "code": "VAL-FAM-002",
        "name": "Por nacimiento o adopcion multiples",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 246.0,
        "requirements": json.dumps({
            "descripcion": "246 EUR por parto multiple o dos o mas adopciones constituidas en la misma fecha durante el periodo impositivo.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Parto multiple o dos o mas adopciones en la misma fecha",
                "Hijos deben dar derecho al minimo por descendientes",
                "Compatible con deduccion por nacimiento/adopcion individual"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "parto_multiple", "label": "Ha tenido un parto multiple o dos o mas adopciones en la misma fecha en 2025?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4.Uno.b), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 3. Por nacimiento, adopcion, acogimiento de personas con discapacidad
    # =========================================================================
    {
        "code": "VAL-FAM-003",
        "name": "Por nacimiento, adopcion, acogimiento o delegacion de guarda de personas con discapacidad",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 246.0,
        "requirements": json.dumps({
            "descripcion": "246 EUR por cada hijo nacido, adoptado o acogido con discapacidad fisica o sensorial >= 65% o psiquica >= 33%.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Hijo con discapacidad fisica/sensorial >= 65% o psiquica >= 33%",
                "Debe dar derecho al minimo por descendientes",
                "Compatible con deduccion por nacimiento/adopcion general"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "hijo_discapacidad", "label": "Tiene hijos nacidos/adoptados en 2025 con discapacidad reconocida?", "type": "boolean"},
            {"key": "grado_discapacidad_hijo", "label": "Que grado de discapacidad tiene el hijo?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.c), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 4. Por familia numerosa o monoparental
    # =========================================================================
    {
        "code": "VAL-FAM-004",
        "name": "Por familia numerosa o monoparental",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 660.0,
        "percentage": None,
        "fixed_amount": 330.0,
        "requirements": json.dumps({
            "descripcion": "330 EUR familia numerosa/monoparental general, 660 EUR especial. Clasificacion segun Ley 40/2003 (familias numerosas) o Decreto 19/2018 (monoparental Valencia).",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "limites_renta_especial": {"individual": 35000, "conjunta": 58000},
            "limites_renta_plena_especial": {"individual": 31000, "conjunta": 54000},
            "condiciones": [
                "Titulo de familia numerosa o monoparental en fecha de devengo",
                "General: 330 EUR; Especial: 660 EUR",
                "Si dos contribuyentes tienen derecho, se prorratea a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "familia_numerosa", "label": "Tiene titulo de familia numerosa o monoparental?", "type": "boolean"},
            {"key": "familia_numerosa_especial", "label": "Es de categoria especial?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4.Uno.d), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 5. Por cantidades destinadas a guarderia y centros 1er ciclo educacion infantil
    # =========================================================================
    {
        "code": "VAL-FAM-005",
        "name": "Por cantidades destinadas a custodia en guarderia y centros de primer ciclo de educacion infantil",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 298.0,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Hasta 298 EUR por hijo menor de 3 anos en guarderia o centro de educacion infantil de primer ciclo autorizado.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Hijo menor de 3 anos (o mayor de 3 que no pueda obtener plaza en centro educativo publico)",
                "Guarderia o centro de primer ciclo de educacion infantil autorizado",
                "Custodia no ocasional",
                "Ambos padres deben percibir rentas del trabajo o actividades economicas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "hijo_menor_3", "label": "Tiene hijos menores de 3 anos?", "type": "boolean"},
            {"key": "guarderia_autorizada", "label": "Estan en una guarderia o centro de educacion infantil autorizado?", "type": "boolean"},
            {"key": "gasto_guarderia", "label": "Cuanto ha pagado de guarderia este ano?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.e), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 6. Por conciliacion del trabajo con la vida familiar
    # =========================================================================
    {
        "code": "VAL-FAM-006",
        "name": "Por conciliacion del trabajo con la vida familiar",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 460.0,
        "requirements": json.dumps({
            "descripcion": "460 EUR por cada hijo o acogido de 3 a 5 anos. Corresponde exclusivamente a la madre (o padre si madre fallecida/sin custodia). Limitada por cotizaciones a Seguridad Social.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Hijo o acogido de 3 a 5 anos",
                "Madre (o padre si corresponde) dada de alta en Seguridad Social o mutualidad",
                "Se calcula proporcionalmente por meses cumpliendo condiciones",
                "Limitada por cotizaciones SS pagadas en el periodo",
                "Incompatible con deduccion por empleada de hogar"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "hijos_3_5_anos", "label": "Tiene hijos de 3 a 5 anos?", "type": "boolean"},
            {"key": "alta_seguridad_social", "label": "Esta dada de alta en la Seguridad Social o mutualidad?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4.Uno.f), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 7. Por contribuyentes con discapacidad >= 33%, >= 65 anos
    # =========================================================================
    {
        "code": "VAL-FAM-007",
        "name": "Por contribuyentes con discapacidad, en grado igual o superior al 33%, de edad igual o superior a 65 anos",
        "category": "discapacidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 197.0,
        "requirements": json.dumps({
            "descripcion": "197 EUR para contribuyentes con discapacidad >= 33% y edad >= 65 anos a 31 de diciembre. No procede si percibe prestaciones exentas de IRPF.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Discapacidad reconocida >= 33%",
                "Edad >= 65 anos a 31 de diciembre",
                "No percibir prestaciones exentas de IRPF por discapacidad"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_reconocida", "label": "Tiene un grado de discapacidad reconocido >= 33%?", "type": "boolean"},
            {"key": "edad_65_o_mas", "label": "Tiene 65 anos o mas?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4.Uno.g), Cuatro, Cinco y DA 6a Ley 13/1997"
    },

    # =========================================================================
    # 8. Por ascendientes mayores de 75 o mayores de 65 con discapacidad
    # =========================================================================
    {
        "code": "VAL-FAM-008",
        "name": "Por ascendientes mayores de 75 anos o mayores de 65 anos con discapacidad",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 197.0,
        "requirements": json.dumps({
            "descripcion": "197 EUR por cada ascendiente mayor de 75 anos, o mayor de 65 anos con discapacidad fisica/sensorial >= 65% o psiquica >= 33%, que conviva con el contribuyente.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Ascendiente mayor de 75 anos, o mayor de 65 con discapacidad >= 65% (fisica) o >= 33% (psiquica)",
                "Debe convivir con el contribuyente al menos la mitad del periodo impositivo",
                "Rentas del ascendiente no superiores a 8.000 EUR (excluidas exentas)",
                "Ascendiente no debe percibir prestaciones exentas de IRPF"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ascendiente_75_o_mas", "label": "Convive con ascendientes mayores de 75 anos o mayores de 65 con discapacidad?", "type": "boolean"},
            {"key": "num_ascendientes", "label": "Cuantos ascendientes cumplen este requisito?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.h), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 9. Por contratar indefinidamente personas empleadas de hogar
    # =========================================================================
    {
        "code": "VAL-FAM-009",
        "name": "Por contratar de manera indefinida a personas afiliadas en el Sistema Especial de Empleados de Hogar",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1100.0,
        "percentage": 50.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "50% de las cotizaciones patronales pagadas por contrato indefinido de empleada de hogar. Max 660 EUR (1 descendiente < 5 anos), 1.100 EUR (2+ desc. o monoparental). Para ascendientes: 330/550 EUR.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Contrato indefinido en Sistema Especial Empleados de Hogar",
                "Descendientes < 5 anos o ascendientes >= 75 (o >= 65 con discapacidad >= 65%)",
                "Contribuyente debe percibir rentas del trabajo o actividades economicas",
                "Incompatible con deducciones de guarderia, conciliacion y ascendientes 75+"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "empleada_hogar_contratada", "label": "Tiene contratada de forma indefinida a una persona empleada de hogar?", "type": "boolean"},
            {"key": "cotizaciones_patronales", "label": "Cuanto ha pagado en cotizaciones patronales a la Seguridad Social por la empleada?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.i), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 10. Por obtencion de rentas derivadas de arrendamientos de vivienda (arrendador)
    # =========================================================================
    {
        "code": "VAL-VIV-001",
        "name": "Por obtencion de rentas derivadas de arrendamientos de vivienda (deduccion del arrendador)",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% del rendimiento integro de arrendamientos de vivienda. Base maxima de deduccion: 3.300 EUR anuales. Renta mensual no puede superar el indice de referencia de precios de alquiler de la Comunitat Valenciana.",
            "limites_renta": None,
            "condiciones": [
                "Contrato de arrendamiento de vivienda iniciado en el periodo impositivo",
                "Vivienda destinada a residencia permanente del arrendatario",
                "Renta no superior al indice de referencia de precios de alquiler",
                "Fianza depositada en la Generalitat",
                "Si contrato anterior < 3 anos, arrendatario debe ser distinto"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "arrendador_vivienda", "label": "Ha arrendado una vivienda como propietario en 2025?", "type": "boolean"},
            {"key": "rendimiento_alquiler", "label": "Cual es el rendimiento integro anual del alquiler?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.j) Ley 13/1997"
    },

    # =========================================================================
    # 11. Por primera adquisicion de vivienda habitual (menores de 35 anos)
    # =========================================================================
    {
        "code": "VAL-VIV-002",
        "name": "Por primera adquisicion de vivienda habitual por contribuyentes de edad igual o inferior a 35 anos",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades satisfechas durante el periodo impositivo por la adquisicion de la primera vivienda habitual (excluidos intereses). Contribuyentes <= 35 anos.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Edad <= 35 anos a 31 de diciembre",
                "Primera vivienda habitual",
                "Se excluyen intereses del prestamo",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "menor_35_anos", "label": "Tiene 35 anos o menos?", "type": "boolean"},
            {"key": "primera_vivienda", "label": "Es su primera vivienda habitual?", "type": "boolean"},
            {"key": "importe_adquisicion_vivienda", "label": "Cuanto ha pagado por la adquisicion de la vivienda en 2025 (sin intereses)?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.k), Cuatro, Cinco y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 12. Por adquisicion de vivienda habitual por personas con discapacidad
    # =========================================================================
    {
        "code": "VAL-VIV-003",
        "name": "Por adquisicion de vivienda habitual por personas con discapacidad",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 5.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "5% de las cantidades satisfechas por adquisicion de vivienda habitual (excluidos intereses) para contribuyentes con discapacidad fisica/sensorial >= 65% o psiquica >= 33%.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Discapacidad fisica o sensorial >= 65%, o psiquica >= 33%",
                "Certificado de organo competente",
                "Se excluyen intereses del prestamo",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta",
                "Compatible con deduccion por primera vivienda joven"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "discapacidad_reconocida", "label": "Tiene discapacidad reconocida >= 65% (fisica) o >= 33% (psiquica)?", "type": "boolean"},
            {"key": "importe_adquisicion_vivienda", "label": "Cuanto ha pagado por la adquisicion de la vivienda en 2025 (sin intereses)?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.l), Cuatro, Cinco y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 13. Por cantidades destinadas a adquisicion o rehabilitacion de vivienda
    #     procedentes de ayudas publicas
    # =========================================================================
    {
        "code": "VAL-VIV-004",
        "name": "Por cantidades destinadas a la adquisicion o rehabilitacion de vivienda habitual, procedentes de ayudas publicas",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 112.0,
        "requirements": json.dumps({
            "descripcion": "112 EUR fijos, o alternativamente el resultado de aplicar el tipo medio autonomico general al importe de la ayuda publica. Subvencion de la Generalitat para adquisicion o rehabilitacion de vivienda habitual.",
            "limites_renta": None,
            "condiciones": [
                "Ayuda publica de la Generalitat Valenciana para adquisicion o rehabilitacion de vivienda habitual",
                "El contribuyente elige entre 112 EUR fijos o el tipo medio general aplicado a la ayuda",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta",
                "Incompatible con deduccion por vivienda joven o discapacidad (mismas cantidades)"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ayuda_publica_vivienda", "label": "Ha recibido una ayuda publica de la Generalitat para adquisicion o rehabilitacion de vivienda?", "type": "boolean"},
            {"key": "importe_ayuda_publica", "label": "Cual es el importe de la ayuda publica recibida?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.m) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 14. Por arrendamiento de vivienda habitual (inquilino)
    # =========================================================================
    {
        "code": "VAL-VIV-005",
        "name": "Por arrendamiento o pago por la cesion en uso de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 1100.0,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% del alquiler, max 800 EUR. Con 1 condicion especial: 25%, max 950 EUR. Con 2+ condiciones: 30%, max 1.100 EUR. Condiciones especiales: <= 35 anos, discapacidad >= 65%/33% psiquica, victima violencia de genero.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "porcentajes_escalonados": {
                "base": {"porcentaje": 20, "max": 800},
                "una_condicion": {"porcentaje": 25, "max": 950},
                "dos_o_mas_condiciones": {"porcentaje": 30, "max": 1100}
            },
            "condiciones_especiales": [
                "Edad <= 35 anos",
                "Discapacidad fisica/sensorial >= 65% o psiquica >= 33%",
                "Victima de violencia de genero"
            ],
            "condiciones": [
                "Contrato de arrendamiento posterior a 23/04/1998, duracion minima 1 ano",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta",
                "No ser propietario de otra vivienda a < 50 km durante >= mitad del periodo",
                "No simultanear con deduccion por inversion en vivienda habitual"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_vivienda_habitual", "label": "Vive de alquiler en su vivienda habitual?", "type": "boolean"},
            {"key": "importe_alquiler_anual", "label": "Cuanto paga de alquiler al ano?", "type": "number"},
            {"key": "menor_35_anos", "label": "Tiene 35 anos o menos?", "type": "boolean"},
            {"key": "discapacidad_reconocida", "label": "Tiene discapacidad reconocida >= 65% (fisica) o >= 33% (psiquica)?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4.Uno.n), Cuatro, Cinco y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 15. Por arrendamiento de vivienda por actividad (por cuenta propia o ajena)
    # =========================================================================
    {
        "code": "VAL-VIV-006",
        "name": "Por arrendamiento de una vivienda, como consecuencia de la realizacion de una actividad, por cuenta propia o ajena",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 550.0,
        "percentage": 10.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "10% del alquiler, max 550 EUR. Para trabajadores por cuenta propia o ajena que necesiten arrendar una vivienda en municipio distinto al de residencia habitual por motivos laborales.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Vivienda arrendada en municipio distinto al de residencia habitual",
                "Motivo: realizacion de actividad por cuenta propia o ajena",
                "Distancia > 50 km entre municipio de residencia y municipio del arrendamiento",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "alquiler_por_trabajo", "label": "Ha alquilado una vivienda en otro municipio por motivos laborales?", "type": "boolean"},
            {"key": "importe_alquiler_trabajo", "label": "Cuanto ha pagado de alquiler por esa vivienda al ano?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.nn), Cuatro, Cinco y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 16. Por cantidades invertidas en instalaciones de autoconsumo o generacion
    #     de energia electrica o termica renovable
    # =========================================================================
    {
        "code": "VAL-SOS-001",
        "name": "Por cantidades invertidas en instalaciones de autoconsumo o de generacion de energia electrica o termica",
        "category": "sostenibilidad",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 40.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "40% de la inversion en instalaciones de autoconsumo electrico con energias renovables o de generacion de energia termica (biomasa, aerotermica, geotermica, solar termica). Porcentaje puede llegar al 65% segun tipo de instalacion.",
            "limites_renta": None,
            "porcentajes_detallados": {
                "autoconsumo_electrico": 40,
                "autoconsumo_electrico_con_bateria": 50,
                "energia_termica_renovable": 40,
                "instalacion_colectiva": 65
            },
            "condiciones": [
                "Instalacion de autoconsumo electrico o generacion termica renovable",
                "Instalacion realizada en vivienda habitual o edificio donde se ubique",
                "Las cantidades no cubiertas por subvenciones son deducibles",
                "Base maxima de deduccion: importe de la inversion no subvencionada"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "instalacion_renovable", "label": "Ha instalado paneles solares u otra energia renovable para autoconsumo?", "type": "boolean"},
            {"key": "importe_instalacion", "label": "Cuanto ha costado la instalacion?", "type": "number"},
            {"key": "tipo_instalacion", "label": "Que tipo de instalacion? (fotovoltaica, termica, con bateria, colectiva)", "type": "text"}
        ]),
        "legal_reference": "Art. 4.Uno.o) Ley 13/1997"
    },

    # =========================================================================
    # 17. Por donaciones con finalidad ecologica
    # =========================================================================
    {
        "code": "VAL-DON-001",
        "name": "Por donaciones con finalidad ecologica",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR donados, 25% sobre el exceso. Donaciones a la Generalitat, entes publicos o entidades sin animo de lucro con fines de defensa y conservacion del medio ambiente.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "Donacion a Generalitat, corporaciones locales o entidades publicas dependientes con fines medioambientales",
                "O a entidades sin animo de lucro (Ley 49/2002) con fines exclusivos de proteccion medioambiental",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_ecologica", "label": "Ha realizado donaciones con fines ecologicos a entidades valencianas?", "type": "boolean"},
            {"key": "importe_donacion_ecologica", "label": "Cuanto ha donado?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.p) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 18. Por donaciones de bienes integrantes del Patrimonio Cultural Valenciano
    # =========================================================================
    {
        "code": "VAL-DON-002",
        "name": "Por donaciones de bienes integrantes del Patrimonio Cultural Valenciano",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR y 25% sobre el exceso. Donaciones de bienes del inventario del Patrimonio Cultural Valenciano a la Generalitat o entidades publicas.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "Donacion de bienes integrantes del Patrimonio Cultural Valenciano",
                "Destinatario: Generalitat, corporaciones locales, universidades, centros de investigacion o formacion artistica de la CV"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_patrimonio_cultural", "label": "Ha donado bienes del Patrimonio Cultural Valenciano?", "type": "boolean"},
            {"key": "importe_donacion_patrimonio", "label": "Cual es el valor de los bienes donados?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.pp) Ley 13/1997"
    },

    # =========================================================================
    # 19. Por donativos para conservacion, reparacion y restauracion del
    #     Patrimonio Cultural Valenciano
    # =========================================================================
    {
        "code": "VAL-DON-003",
        "name": "Por donativos para la conservacion, reparacion y restauracion de bienes integrantes del Patrimonio Cultural Valenciano",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR y 25% sobre el exceso. Donativos dinerarios para conservacion, reparacion y restauracion de bienes del Patrimonio Cultural Valenciano.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "Donativos dinerarios para conservacion/reparacion/restauracion del Patrimonio Cultural Valenciano",
                "Destinatario: entidades sin animo de lucro, administraciones publicas, universidades, centros de investigacion",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donativo_restauracion_patrimonio", "label": "Ha donado dinero para conservacion o restauracion del Patrimonio Cultural Valenciano?", "type": "boolean"},
            {"key": "importe_donativo_restauracion", "label": "Cuanto ha donado?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.q) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 20. Por cantidades destinadas por titulares a conservacion, reparacion y
    #     restauracion del Patrimonio Cultural Valenciano
    # =========================================================================
    {
        "code": "VAL-DON-004",
        "name": "Por cantidades destinadas por sus titulares a la conservacion, reparacion y restauracion de bienes integrantes del Patrimonio Cultural Valenciano",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR y 25% sobre el exceso. Para propietarios de bienes del Patrimonio Cultural Valenciano que destinan cantidades a su conservacion, reparacion o restauracion.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "El contribuyente debe ser titular del bien del Patrimonio Cultural Valenciano",
                "Las cantidades deben destinarse a conservacion, reparacion o restauracion del bien",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "titular_patrimonio_cultural", "label": "Es propietario de un bien del Patrimonio Cultural Valenciano?", "type": "boolean"},
            {"key": "gasto_restauracion_propio", "label": "Cuanto ha gastado en conservacion, reparacion o restauracion?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.qq) Ley 13/1997"
    },

    # =========================================================================
    # 21. Por donaciones destinadas al fomento de la Lengua Valenciana
    # =========================================================================
    {
        "code": "VAL-DON-005",
        "name": "Por donaciones destinadas al fomento de la Lengua Valenciana",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR y 25% sobre el exceso. Donaciones dinerarias para fomento de la Lengua Valenciana.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "Donaciones dinerarias para fomento de la Lengua Valenciana",
                "Destinatario: Generalitat, entes publicos, universidades, centros artisticos, o entidades censadas en el Censo de Fomento del Valenciano",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_lengua_valenciana", "label": "Ha donado dinero para el fomento de la Lengua Valenciana?", "type": "boolean"},
            {"key": "importe_donacion_lengua", "label": "Cuanto ha donado?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.r) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 22. Por donaciones o cesiones de uso para fines culturales, cientificos o deportivos
    # =========================================================================
    {
        "code": "VAL-DON-006",
        "name": "Por donaciones o cesiones de uso o comodatos para otros fines de caracter cultural, cientifico o deportivo",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR y 25% sobre el exceso. Donaciones o cesiones de uso para fines culturales, cientificos o deportivos no profesionales. Ley 20/2018 de mecenazgo.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "Donaciones/cesiones para fines culturales, cientificos o deportivos no profesionales",
                "Destinatario: entidades sin animo de lucro en la CV, administraciones publicas, universidades, centros de investigacion, empresas culturales con domicilio en CV",
                "Proyectos declarados de interes social",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_cultural_cientifica", "label": "Ha donado para fines culturales, cientificos o deportivos en la CV?", "type": "boolean"},
            {"key": "importe_donacion_cultural", "label": "Cuanto ha donado o cual es el valor de la cesion?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.s) y DA 16a Ley 13/1997; Ley 20/2018"
    },

    # =========================================================================
    # 23. Justificacion documental de determinadas deducciones por donativos
    # (no es una deduccion propiamente dicha, sino requisito formal)
    # =========================================================================
    {
        "code": "VAL-DON-007",
        "name": "Justificacion documental de determinadas deducciones autonomicas por donativos o cesiones de uso o comodato",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Requisito formal: las deducciones por donativos requieren certificacion de la entidad receptora con NIF del donante, importe, fecha y destino de la donacion. No es una deduccion cuantitativa sino un requisito procedimental.",
            "limites_renta": None,
            "condiciones": [
                "Certificacion de la entidad receptora del donativo",
                "Debe incluir: NIF del donante, importe, fecha y destino",
                "Aplica a deducciones VAL-DON-001 a VAL-DON-006"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "tiene_certificado_donacion", "label": "Dispone de certificacion de la entidad receptora del donativo?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4.Dos Ley 13/1997"
    },

    # =========================================================================
    # 24. Requisito conjunto para determinadas deducciones por donativos
    # (requisito formal adicional)
    # =========================================================================
    {
        "code": "VAL-DON-008",
        "name": "Requisito conjunto para determinadas deducciones autonomicas por donativos o cesiones de uso o comodato",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Requisito formal conjunto: el total de las bases de las deducciones por donativos no puede exceder el 20% de la base liquidable del contribuyente. No es una deduccion cuantitativa sino un limite global.",
            "limites_renta": None,
            "condiciones": [
                "El conjunto de bases de deducciones por donativos no puede superar el 20% de la base liquidable",
                "Aplica a deducciones VAL-DON-001 a VAL-DON-006"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([]),
        "legal_reference": "Art. 4.Tres Ley 13/1997"
    },

    # =========================================================================
    # 25. Por contribuyentes con dos o mas descendientes
    # =========================================================================
    {
        "code": "VAL-FAM-010",
        "name": "Por contribuyentes con dos o mas descendientes",
        "category": "familia",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 110.0,
        "requirements": json.dumps({
            "descripcion": "110 EUR para contribuyentes con dos o mas descendientes que generen derecho al minimo por descendientes.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Dos o mas descendientes que generen derecho al minimo por descendientes",
                "Si dos contribuyentes tienen derecho, se prorratea a partes iguales"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "dos_o_mas_descendientes", "label": "Tiene dos o mas descendientes que generen minimo por descendientes?", "type": "boolean"},
            {"key": "num_descendientes", "label": "Cuantos descendientes tiene?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.t), Cuatro y Cinco Ley 13/1997"
    },

    # =========================================================================
    # 26. Por el incremento de los costes de la financiacion ajena en inversion
    #     de vivienda habitual
    # =========================================================================
    {
        "code": "VAL-VIV-007",
        "name": "Por el incremento de los costes de la financiacion ajena en la inversion de la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion por el incremento de los intereses de prestamos hipotecarios para vivienda habitual cuando los tipos de interes han subido respecto al ano anterior. Se aplica sobre la diferencia de intereses entre el periodo impositivo y el anterior.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Prestamo hipotecario para adquisicion de vivienda habitual",
                "Los intereses pagados en 2025 deben ser superiores a los de 2024",
                "Se deduce el 50% de la diferencia de intereses entre ambos periodos",
                "Base maxima de deduccion: la diferencia de intereses"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "hipoteca_vivienda_habitual", "label": "Tiene hipoteca para vivienda habitual?", "type": "boolean"},
            {"key": "intereses_2025", "label": "Cuanto ha pagado de intereses hipotecarios en 2025?", "type": "number"},
            {"key": "intereses_2024", "label": "Cuanto pago de intereses hipotecarios en 2024?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.u) Ley 13/1997"
    },

    # =========================================================================
    # 27. Por cantidades destinadas a la adquisicion de material escolar
    # =========================================================================
    {
        "code": "VAL-EDU-001",
        "name": "Por cantidades destinadas a la adquisicion de material escolar",
        "category": "educacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 110.0,
        "requirements": json.dumps({
            "descripcion": "110 EUR por cada descendiente escolarizado en Educacion Primaria, ESO o educacion especial en centros publicos o concertados. Requisito: contribuyente en situacion de desempleo e inscrito como demandante de empleo.",
            "limites_renta": LIMITES_STANDARD,
            "limites_renta_plena": LIMITES_STANDARD_PLENA,
            "condiciones": [
                "Descendientes escolarizados en Primaria, ESO o educacion especial",
                "Centro publico o concertado",
                "Contribuyente en situacion de desempleo e inscrito como demandante de empleo en servicio publico",
                "Deduccion proporcional a los dias en desempleo",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "hijos_escolarizados", "label": "Tiene hijos en Educacion Primaria, ESO o educacion especial?", "type": "boolean"},
            {"key": "num_hijos_escolarizados", "label": "Cuantos hijos escolarizados tiene?", "type": "number"},
            {"key": "situacion_desempleo", "label": "Ha estado en situacion de desempleo en 2025?", "type": "boolean"}
        ]),
        "legal_reference": "Art. 4.Uno.v) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 28. Por obras de conservacion o mejora de calidad, sostenibilidad y
    #     accesibilidad en la vivienda habitual (vigente)
    # =========================================================================
    {
        "code": "VAL-VIV-008",
        "name": "Por obras de conservacion o mejora de la calidad, sostenibilidad y accesibilidad en la vivienda habitual",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% de las cantidades satisfechas en obras de conservacion o mejora de la calidad, sostenibilidad y accesibilidad de la vivienda habitual. Incluye eficiencia energetica, accesibilidad, seguridad estructural.",
            "limites_renta": None,
            "condiciones": [
                "Obras en la vivienda habitual del contribuyente",
                "Obras de conservacion, mejora de calidad, sostenibilidad o accesibilidad",
                "Las obras no pueden ser de ampliacion ni nuevas construcciones",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta",
                "Factura emitida por el profesional que realice las obras"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "obras_conservacion_vivienda", "label": "Ha realizado obras de conservacion, mejora o accesibilidad en su vivienda habitual?", "type": "boolean"},
            {"key": "importe_obras", "label": "Cuanto ha pagado por las obras?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.w) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 29. Por obras de conservacion o mejora en vivienda habitual efectuadas
    #     en 2014 y 2015 (transitoria residual)
    # =========================================================================
    {
        "code": "VAL-VIV-009",
        "name": "Por obras de conservacion o mejora de la calidad, sostenibilidad y accesibilidad en la vivienda habitual efectuadas en 2014 y 2015",
        "category": "vivienda",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 20.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Regimen transitorio: 20% de las cantidades satisfechas en obras de conservacion, sostenibilidad o accesibilidad en vivienda habitual realizadas en 2014-2015, cuyas cantidades pendientes se aplican en periodos posteriores.",
            "limites_renta": None,
            "condiciones": [
                "Obras realizadas en 2014 o 2015",
                "Cantidades pendientes de deduccion de periodos anteriores",
                "Solo aplicable si la base de deduccion excedia el limite anual en el periodo de realizacion"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "obras_2014_2015_pendientes", "label": "Tiene cantidades pendientes de deduccion por obras de vivienda realizadas en 2014-2015?", "type": "boolean"},
            {"key": "importe_pendiente", "label": "Cuanto le queda pendiente de deducir?", "type": "number"}
        ]),
        "legal_reference": "DT 20a Ley 13/1997"
    },

    # =========================================================================
    # 30. Por cantidades destinadas a abonos culturales
    # =========================================================================
    {
        "code": "VAL-CUL-001",
        "name": "Por cantidades destinadas a abonos culturales",
        "category": "cultura",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 21.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "21% de las cantidades satisfechas en abonos culturales, con base maxima de deduccion de 165 EUR. El abono cultural debe ser del programa de Abonos Culturales Valencianos (convenio CulturArts).",
            "limites_renta": {"individual": 50000},
            "base_maxima_deduccion": 165,
            "condiciones": [
                "Abonos culturales del programa de Abonos Culturales Valencianos (CulturArts Generalitat)",
                "Base liquidable general + ahorro < 50.000 EUR",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "abono_cultural", "label": "Ha adquirido abonos culturales del programa de Abonos Culturales Valencianos?", "type": "boolean"},
            {"key": "importe_abono_cultural", "label": "Cuanto ha pagado por los abonos culturales?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.x) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 31. Por adquisicion de vehiculos nuevos (Orden 5/2020)
    # =========================================================================
    {
        "code": "VAL-INV-001",
        "name": "Por adquisicion de vehiculos nuevos pertenecientes a las categorias incluidas en la Orden 5/2020",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion por adquisicion de vehiculos nuevos electricos, hibridos enchufables u otros incluidos en la Orden 5/2020 de la Conselleria. Porcentaje y condiciones segun tipo de vehiculo y categoria.",
            "limites_renta": None,
            "condiciones": [
                "Vehiculo nuevo incluido en las categorias de la Orden 5/2020",
                "Vehiculos electricos puros, hibridos enchufables, pila de combustible",
                "Debe estar matriculado en la Comunitat Valenciana",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "vehiculo_electrico", "label": "Ha adquirido un vehiculo nuevo electrico o hibrido enchufable en 2025?", "type": "boolean"},
            {"key": "importe_vehiculo", "label": "Cual es el precio del vehiculo?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.y) y DA 16a Ley 13/1997; Orden 5/2020"
    },

    # =========================================================================
    # 32. Por inversion en entidades nuevas o de reciente creacion
    # =========================================================================
    {
        "code": "VAL-INV-002",
        "name": "Por inversion en adquisicion de acciones o participaciones sociales en entidades nuevas o de reciente creacion",
        "category": "inversion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades invertidas en la adquisicion de acciones o participaciones sociales de entidades nuevas o de reciente creacion (maximo 3 anos desde constitucion). Deduccion autonomica complementaria a la estatal.",
            "limites_renta": None,
            "condiciones": [
                "Entidad constituida como SA, SL, SAL o SLL",
                "Entidad de reciente creacion (max 3 anos desde constitucion)",
                "Domicilio social y fiscal en la Comunitat Valenciana",
                "Actividad economica real con al menos 1 trabajador con contrato laboral",
                "Participacion del contribuyente no puede superar el 40% del capital",
                "Mantener las acciones un minimo de 3 anos"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "inversion_startup", "label": "Ha invertido en acciones o participaciones de empresas nuevas o de reciente creacion en la CV?", "type": "boolean"},
            {"key": "importe_inversion", "label": "Cuanto ha invertido?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.z) Ley 13/1997"
    },

    # =========================================================================
    # 33. Por residir habitualmente en un municipio en riesgo de despoblamiento
    # =========================================================================
    {
        "code": "VAL-DES-001",
        "name": "Por residir habitualmente en un municipio en riesgo de despoblamiento",
        "category": "despoblacion",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": 330.0,
        "requirements": json.dumps({
            "descripcion": "330 EUR base. Incrementos por descendientes: +132 EUR (1 desc.), +198 EUR (2 desc.), +264 EUR (3+ desc.). Municipio beneficiario del Fondo de Cooperacion Municipal contra despoblacion (Ley 5/2023).",
            "limites_renta": None,
            "incrementos_descendientes": {
                "1_descendiente": 132,
                "2_descendientes": 198,
                "3_o_mas_descendientes": 264
            },
            "condiciones": [
                "Residencia habitual en municipio en riesgo de despoblamiento",
                "Municipio beneficiario del Fondo de Cooperacion Municipal para combatir despoblacion (Ley 5/2023)",
                "Incompatible con deducciones por nacimiento/adopcion/discapacidad de descendientes (suplementos)",
                "Si dos contribuyentes reclaman el mismo descendiente, incremento se prorratea"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "municipio_despoblamiento", "label": "Reside habitualmente en un municipio en riesgo de despoblamiento de la CV?", "type": "boolean"},
            {"key": "num_descendientes", "label": "Cuantos descendientes tiene con derecho a minimo por descendientes?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.aa) y Seis Ley 13/1997; Ley 5/2023"
    },

    # =========================================================================
    # 34. Por cantidades satisfechas en tratamientos de fertilidad
    # =========================================================================
    {
        "code": "VAL-SAL-001",
        "name": "Por cantidades satisfechas en tratamientos de fertilidad realizados en clinicas o centros autorizados",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades satisfechas en tratamientos de fertilidad realizados en clinicas o centros autorizados de la Comunitat Valenciana.",
            "limites_renta": {"individual": 32000, "conjunta": 48000},
            "limites_renta_plena": {"individual": 29000, "conjunta": 45000},
            "condiciones": [
                "Tratamiento de fertilidad en clinica o centro autorizado",
                "No incluye importes reembolsados por Seguridad Social o seguros",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta",
                "Factura del profesional o centro sanitario"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "tratamiento_fertilidad", "label": "Ha pagado por tratamientos de fertilidad en clinicas autorizadas de la CV?", "type": "boolean"},
            {"key": "importe_fertilidad", "label": "Cuanto ha pagado en tratamientos de fertilidad?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.ab) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 35. Por cantidades satisfechas en determinados gastos de salud
    # =========================================================================
    {
        "code": "VAL-SAL-002",
        "name": "Por cantidades satisfechas en determinados gastos de salud",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": 150.0,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Cuatro conceptos: (1) Enfermedades cronicas, raras, dano cerebral/Alzheimer: hasta 100 EUR (150 EUR fam. numerosa/monoparental). (2) Salud dental (no estetica): 30%, max 150 EUR. (3) Salud mental: 30%, max 150 EUR. (4) Gafas/lentillas/soluciones: 30%, max 100 EUR.",
            "limites_renta": {"individual": 32000, "conjunta": 48000},
            "limites_renta_plena": {"individual": 29000, "conjunta": 45000},
            "conceptos": {
                "enfermedades_cronicas_raras": {"max": 100, "max_familia_numerosa": 150},
                "salud_dental": {"porcentaje": 30, "max": 150},
                "salud_mental": {"porcentaje": 30, "max": 150},
                "optica_gafas_lentillas": {"porcentaje": 30, "max": 100}
            },
            "condiciones": [
                "Servicios de profesionales o centros sanitarios registrados",
                "Factura + justificante de pago (tarjeta, transferencia, cheque, ingreso en cuenta)",
                "No incluye primas de seguros ni importes reembolsables por la Seguridad Social"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_salud", "label": "Ha tenido gastos de salud dental, mental, optica o por enfermedades cronicas/raras?", "type": "boolean"},
            {"key": "importe_gastos_salud", "label": "Cuanto ha pagado en total en gastos de salud deducibles?", "type": "number"},
            {"key": "tipo_gasto_salud", "label": "Que tipo de gasto? (dental, mental, optica, enfermedad cronica/rara)", "type": "text"}
        ]),
        "legal_reference": "Art. 4.Uno.ac) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 36. Por cantidades satisfechas en gastos asociados a la practica del
    #     deporte y actividades saludables
    # =========================================================================
    {
        "code": "VAL-SAL-003",
        "name": "Por cantidades satisfechas en gastos asociados a la practica del deporte y actividades saludables",
        "category": "salud",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 30.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "30% de las cantidades satisfechas en gastos asociados a la practica del deporte y actividades saludables (gimnasios, federaciones deportivas, etc.).",
            "limites_renta": {"individual": 32000, "conjunta": 48000},
            "limites_renta_plena": {"individual": 29000, "conjunta": 45000},
            "condiciones": [
                "Gastos en practica deportiva o actividades saludables",
                "Cuotas de gimnasios, federaciones deportivas, actividades deportivas organizadas",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta",
                "Factura del centro o entidad deportiva"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "gastos_deporte", "label": "Ha pagado cuotas de gimnasio, federaciones deportivas u otras actividades saludables?", "type": "boolean"},
            {"key": "importe_gastos_deporte", "label": "Cuanto ha pagado en total?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.ad) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 37. Por cantidades procedentes de ayudas publicas por ERTE y COVID-19
    # (Decreto Ley 3/2020)
    # =========================================================================
    {
        "code": "VAL-COV-001",
        "name": "Por cantidades procedentes de ayudas publicas concedidas por la Generalitat en virtud del Decreto Ley 3/2020 (ERTE y COVID-19)",
        "category": "otros",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion por las cantidades percibidas de ayudas publicas concedidas por la Generalitat en virtud del Decreto Ley 3/2020, de 13 de marzo (ERTE y medidas economicas COVID-19). La deduccion equivale al resultado de aplicar el tipo medio de gravamen autonomico a las ayudas recibidas.",
            "limites_renta": None,
            "condiciones": [
                "Ayudas publicas concedidas por la Generalitat por Decreto Ley 3/2020",
                "Ayudas por ERTE o medidas economicas por COVID-19",
                "Deduccion = tipo medio gravamen autonomico x importe ayuda"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "ayuda_covid_erte", "label": "Ha recibido ayudas de la Generalitat por ERTE o COVID-19 (DL 3/2020)?", "type": "boolean"},
            {"key": "importe_ayuda_covid", "label": "Cual es el importe de las ayudas recibidas?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.ae) Ley 13/1997; DL 3/2020"
    },

    # =========================================================================
    # 38. Por donaciones dinerarias para financiar programas de investigacion
    #     sobre COVID-19
    # =========================================================================
    {
        "code": "VAL-COV-002",
        "name": "Por donaciones dinerarias dirigidas a financiar programas de investigacion sobre COVID-19",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR y 25% sobre el exceso. Donaciones dinerarias para financiar programas de investigacion sobre COVID-19.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "Donaciones dinerarias para programas de investigacion COVID-19",
                "Destinatario: centros de investigacion, universidades, entidades sanitarias de la CV",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_investigacion_covid", "label": "Ha donado para investigacion sobre COVID-19 en la CV?", "type": "boolean"},
            {"key": "importe_donacion_covid", "label": "Cuanto ha donado?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.af) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 39. Por donaciones para financiar gastos por la crisis sanitaria COVID-19
    # =========================================================================
    {
        "code": "VAL-COV-003",
        "name": "Por donaciones para contribuir a la financiacion de los gastos ocasionados por la crisis sanitaria producida por la Covid-19",
        "category": "donativos",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": 25.0,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "20% sobre los primeros 250 EUR y 25% sobre el exceso. Donaciones dinerarias para financiar gastos derivados de la crisis sanitaria COVID-19.",
            "limites_renta": None,
            "porcentajes_escalonados": {
                "primeros_250": 20,
                "exceso_250": 25
            },
            "condiciones": [
                "Donaciones dinerarias para gastos derivados de la crisis sanitaria COVID-19",
                "Destinatario: administraciones publicas, centros sanitarios, entidades sin animo de lucro de la CV",
                "Pago mediante tarjeta, transferencia, cheque nominativo o ingreso en cuenta"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "donacion_gastos_covid", "label": "Ha donado para financiar gastos de la crisis sanitaria COVID-19 en la CV?", "type": "boolean"},
            {"key": "importe_donacion_gastos_covid", "label": "Cuanto ha donado?", "type": "number"}
        ]),
        "legal_reference": "Art. 4.Uno.ag) y DA 16a Ley 13/1997"
    },

    # =========================================================================
    # 40. Dirigidas a personas afectadas por las inundaciones producidas por
    #     la DANA de octubre de 2024
    # =========================================================================
    {
        "code": "VAL-DANA-001",
        "name": "Deducciones dirigidas a las personas afectadas por las inundaciones producidas por la DANA de octubre de 2024",
        "category": "dana",
        "scope": "territorial",
        "ccaa": TERRITORY,
        "max_amount": None,
        "percentage": None,
        "fixed_amount": None,
        "requirements": json.dumps({
            "descripcion": "Deduccion extraordinaria para afectados por la DANA de octubre de 2024. Incluye compensaciones por danos en vivienda habitual, vehiculo, enseres, actividades economicas y otros perjuicios derivados de las inundaciones. Regulacion especifica por Decreto-ley de la Generalitat.",
            "limites_renta": None,
            "condiciones": [
                "Afectado por las inundaciones de la DANA de octubre de 2024",
                "Residente en municipios afectados declarados zona catastrofica",
                "Danos materiales en vivienda habitual, vehiculo, enseres o actividad economica",
                "Regulacion especifica mediante Decreto-ley de la Generalitat Valenciana",
                "Cantidades no cubiertas por seguros u otras ayudas publicas"
            ]
        }),
        "tax_year": TAX_YEAR,
        "is_active": True,
        "questions": json.dumps([
            {"key": "afectado_dana_2024", "label": "Ha sido afectado por las inundaciones de la DANA de octubre de 2024?", "type": "boolean"},
            {"key": "municipio_zona_catastrofica", "label": "Reside en un municipio declarado zona catastrofica?", "type": "boolean"},
            {"key": "tipo_dano_dana", "label": "Que tipo de danos ha sufrido? (vivienda, vehiculo, enseres, actividad economica)", "type": "text"},
            {"key": "importe_danos_no_cubiertos", "label": "Cual es el importe de los danos no cubiertos por seguros?", "type": "number"}
        ]),
        "legal_reference": "DT y DA especificas Ley 13/1997 (incorporadas por DL DANA 2024)"
    },
]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

async def seed_valencia(dry_run: bool = False):
    """Delete existing Valencia 2025 deductions and insert all 40."""

    print(f"{'[DRY RUN] ' if dry_run else ''}Seeding {len(VALENCIA_2025)} Valencia deductions for IRPF {TAX_YEAR}")
    print("=" * 70)

    if not dry_run:
        from app.database.turso_client import TursoClient
        db = TursoClient()
        await db.connect()
        print("Connected to database.\n")

        # Delete existing Valencia deductions for this tax year
        # Check both the new schema (ccaa column) and old schema (territory column)
        for col_name in ("ccaa", "territory"):
            try:
                result = await db.execute(
                    f"DELETE FROM deductions WHERE {col_name} = ? AND tax_year = ?",
                    [TERRITORY, TAX_YEAR],
                )
                if hasattr(result, "rows_affected") and result.rows_affected:
                    print(f"  Deleted {result.rows_affected} existing Valencia deductions (column: {col_name})")
                else:
                    print(f"  No existing deductions found to delete (column: {col_name})")
            except Exception:
                # Column might not exist in the schema variant
                pass

        print()

    inserted = 0
    for i, d in enumerate(VALENCIA_2025, 1):
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
            # Try new schema first (with ccaa, scope columns)
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
            # Fallback: try old schema (territory, type, fixed_amount, etc.)
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
    print(f"{'[DRY RUN] ' if dry_run else ''}Total: {inserted}/{len(VALENCIA_2025)} deductions {'would be ' if dry_run else ''}inserted")
    print()

    # Summary by category
    categories = {}
    for d in VALENCIA_2025:
        cat = d["category"]
        categories[cat] = categories.get(cat, 0) + 1
    print("By category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Seed all 40 Valencia IRPF deductions for 2025")
    parser.add_argument("--dry-run", action="store_true", help="Print deductions without inserting into DB")
    args = parser.parse_args()
    asyncio.run(seed_valencia(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
