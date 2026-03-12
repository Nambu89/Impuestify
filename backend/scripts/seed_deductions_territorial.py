"""
Seed script for territorial (autonomous community) IRPF deductions.

Covers 8 territories with their most impactful deductions:
- Foral (unique competitive advantage): Araba, Bizkaia, Gipuzkoa, Navarra
- Régimen común (highest population): Madrid, Cataluña, Andalucía, Valencia

Idempotent: uses INSERT OR IGNORE so it can be run multiple times safely.

Usage:
    cd backend
    python scripts/seed_deductions_territorial.py
"""
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# =============================================================================
# ARABA / ÁLAVA (Norma Foral 33/2013 consolidada)
# =============================================================================
ARABA_2025 = [
    {
        "code": "ARA-DESC-HIJOS",
        "name": "Deducción por descendientes (hijos)",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 668.0,
        "legal_reference": "Art. 79 NF 33/2013 Araba",
        "description": "668€ por el 1º hijo, 827€ el 2º, 1.393€ el 3º, 1.647€ el 4º, 2.151€ del 5º en adelante. Complemento +386€ por menor de 6 años y +62€ por 6-16 años. Municipios <4.000 hab: +15% sobre todas las cantidades.",
        "requirements_json": json.dumps({
            "tiene_hijos": True,
        }),
        "questions_json": json.dumps([
            {"key": "tiene_hijos", "text": "¿Tienes hijos o descendientes a tu cargo?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes?", "type": "number"},
            {"key": "hijos_menores_6", "text": "¿Cuántos son menores de 6 años?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 20.0,
        "max_amount": 1600.0,
        "legal_reference": "Art. 86 NF 33/2013 Araba",
        "description": "20% del alquiler, máx. 1.600€/año. Colectivos especiales (menores de 36, familia numerosa, discapacidad ≥65%, municipios <4.000 hab.): 35%, máx. 2.800€. Base liquidable ≤ 68.000€.",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años?", "type": "bool"},
        ]),
    },
    {
        "code": "ARA-COMPRA-VIV",
        "name": "Deducción por adquisición de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 18.0,
        "max_amount": 1530.0,
        "legal_reference": "Art. 87 NF 33/2013 Araba",
        "description": "18% de la inversión (capital + intereses), máx. 1.530€/año. Menores de 36: 23%, máx. 1.955€. Límite vital: 36.000€. VIGENTE (a diferencia del régimen común que la eliminó en 2013).",
        "requirements_json": json.dumps({
            "vivienda_habitual_propiedad": True,
        }),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "¿Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto pagas al año de hipoteca (capital + intereses)?", "type": "number"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años?", "type": "bool"},
        ]),
    },
    {
        "code": "ARA-DISCAPACIDAD",
        "name": "Deducción por discapacidad",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 932.40,
        "legal_reference": "Art. 82 NF 33/2013 Araba (actualizado NF 3/2025)",
        "description": "932,40€ (33-65%), 1.331,40€ (≥65% o Grado I), 1.597,05€ (Grado II), 1.991,85€ (Grado III). Aplica al contribuyente y/o cónyuge. Importes actualizados por NF 3/2025.",
        "requirements_json": json.dumps({
            "discapacidad_reconocida": True,
        }),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Qué grado de discapacidad tienes? (33-65, ≥65, Grado I, II o III)", "type": "text"},
        ]),
    },
    {
        "code": "ARA-VEH-ELECT",
        "name": "Deducción por vehículo eléctrico",
        "type": "deduccion",
        "category": "sostenibilidad",
        "percentage": 15.0,
        "max_amount": 5000.0,
        "legal_reference": "Art. 87 quáter NF 33/2013 Araba",
        "description": "15% del precio de adquisición de vehículos eléctricos, máx. 5.000€. También 15% por puntos de recarga (máx. 1.500€).",
        "requirements_json": json.dumps({
            "vehiculo_electrico_nuevo": True,
        }),
        "questions_json": json.dumps([
            {"key": "vehiculo_electrico_nuevo", "text": "¿Has comprado un vehículo eléctrico nuevo este año?", "type": "bool"},
            {"key": "precio_vehiculo", "text": "¿Cuánto costó el vehículo?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-EFIC-ENERG",
        "name": "Deducción por eficiencia energética en vivienda",
        "type": "deduccion",
        "category": "sostenibilidad",
        "percentage": 20.0,
        "max_amount": 15000.0,
        "legal_reference": "Art. 87 ter NF 33/2013 Araba",
        "description": "20-35% de obras de eficiencia energética e integración de renovables. Máx. 3.000-15.000€ según tipo de obra.",
        "requirements_json": json.dumps({
            "obras_mejora_energetica": True,
        }),
        "questions_json": json.dumps([
            {"key": "obras_mejora_energetica", "text": "¿Has hecho obras de eficiencia energética en tu vivienda?", "type": "bool"},
            {"key": "importe_obras", "text": "¿Cuánto has invertido en las obras?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-DESPOBLACION",
        "name": "Minoración por residencia en municipio despoblado",
        "type": "deduccion",
        "category": "territorial",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 77.2 NF 33/2013 Araba",
        "description": "200€ adicionales para residentes en núcleos de ≤500 habitantes. Además, +15% en deducciones por descendientes, ascendientes y vivienda para municipios <4.000 hab.",
        "requirements_json": json.dumps({
            "municipio_despoblado": True,
        }),
        "questions_json": json.dumps([
            {"key": "municipio_despoblado", "text": "¿Resides en un municipio de menos de 4.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "ARA-ASCENDIENTES",
        "name": "Deducción por ascendientes a cargo",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 423.72,
        "legal_reference": "Art. 81 NF 33/2013 Araba",
        "description": "423,72€ por cada ascendiente que conviva de forma continua con el contribuyente. +15% si es en municipio <4.000 hab.",
        "requirements_json": json.dumps({
            "ascendiente_a_cargo": True,
        }),
        "questions_json": json.dumps([
            {"key": "ascendiente_a_cargo", "text": "¿Tienes padres o abuelos a tu cargo que convivan contigo?", "type": "bool"},
            {"key": "num_ascendientes", "text": "¿Cuántos ascendientes tienes a tu cargo?", "type": "number"},
        ]),
    },
]


# =============================================================================
# BIZKAIA (Norma Foral 13/2013)
# =============================================================================
BIZKAIA_2025 = [
    {
        "code": "BIZ-DESC-HIJOS",
        "name": "Deducción por descendientes (hijos)",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 668.0,
        "legal_reference": "Art. 79 NF 13/2013 Bizkaia",
        "description": "668€ por el 1º hijo, 827€ el 2º, 1.393€ el 3º, 1.647€ el 4º, 2.151€ del 5º en adelante. Complemento +386€ por menor de 6 años.",
        "requirements_json": json.dumps({
            "tiene_hijos": True,
        }),
        "questions_json": json.dumps([
            {"key": "tiene_hijos", "text": "¿Tienes hijos o descendientes a tu cargo?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes?", "type": "number"},
            {"key": "hijos_menores_6", "text": "¿Cuántos son menores de 6 años?", "type": "number"},
        ]),
    },
    {
        "code": "BIZ-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 20.0,
        "max_amount": 1600.0,
        "legal_reference": "Art. 86 NF 13/2013 Bizkaia",
        "description": "20% del alquiler, máx. 1.600€. Familia numerosa: 25%, máx. 2.000€. Menores de 30: 30%, máx. 2.400€.",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_30_anos", "text": "¿Tienes menos de 30 años?", "type": "bool"},
        ]),
    },
    {
        "code": "BIZ-COMPRA-VIV",
        "name": "Deducción por adquisición de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 18.0,
        "max_amount": 1530.0,
        "legal_reference": "Art. 87 NF 13/2013 Bizkaia",
        "description": "18% de la inversión (capital + intereses), máx. 1.530€/año. Menores de 30 o familia numerosa: 23%, máx. 1.955€. Límite vital: 36.000€. VIGENTE.",
        "requirements_json": json.dumps({
            "vivienda_habitual_propiedad": True,
        }),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "¿Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto pagas al año de hipoteca (capital + intereses)?", "type": "number"},
            {"key": "menor_30_anos", "text": "¿Tienes menos de 30 años?", "type": "bool"},
        ]),
    },
    {
        "code": "BIZ-DISCAPACIDAD",
        "name": "Deducción por discapacidad",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 888.0,
        "legal_reference": "Art. 82 NF 13/2013 Bizkaia",
        "description": "888€ (33-65%), 1.268€ (≥65% o Grado I), 1.521€ (Grado II), 1.897€ (Grado III).",
        "requirements_json": json.dumps({
            "discapacidad_reconocida": True,
        }),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Qué grado de discapacidad tienes?", "type": "text"},
        ]),
    },
    {
        "code": "BIZ-EDAD-65",
        "name": "Deducción por edad (mayores de 65 años)",
        "type": "deduccion",
        "category": "personal",
        "fixed_amount": 385.0,
        "legal_reference": "Art. 83 NF 13/2013 Bizkaia",
        "description": "385€ para mayores de 65 años, 700€ para mayores de 75. Requisito: base imponible ≤ 20.000€ (escala reducida entre 20.000-30.000€).",
        "requirements_json": json.dumps({
            "mayor_65_anos": True,
        }),
        "questions_json": json.dumps([
            {"key": "mayor_65_anos", "text": "¿Tienes 65 años o más?", "type": "bool"},
            {"key": "mayor_75_anos", "text": "¿Tienes 75 años o más?", "type": "bool"},
        ]),
    },
    {
        "code": "BIZ-ASCENDIENTES",
        "name": "Deducción por ascendientes a cargo",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 321.0,
        "legal_reference": "Art. 81 NF 13/2013 Bizkaia",
        "description": "321€ por cada ascendiente que conviva de forma continua con el contribuyente.",
        "requirements_json": json.dumps({
            "ascendiente_a_cargo": True,
        }),
        "questions_json": json.dumps([
            {"key": "ascendiente_a_cargo", "text": "¿Tienes padres o abuelos a tu cargo que convivan contigo?", "type": "bool"},
            {"key": "num_ascendientes", "text": "¿Cuántos ascendientes tienes a tu cargo?", "type": "number"},
        ]),
    },
]


# =============================================================================
# GIPUZKOA (Norma Foral 3/2014 + NF 1/2025 reforma)
# =============================================================================
GIPUZKOA_2025 = [
    {
        "code": "GIP-DESC-HIJOS",
        "name": "Deducción por descendientes (hijos)",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 668.0,
        "legal_reference": "Art. 79 NF 3/2014 Gipuzkoa",
        "description": "668€ por el 1º hijo, 827€ el 2º, 1.393€ el 3º, 1.647€ el 4º, 2.151€ del 5º en adelante. Complemento +386€ por menor de 6 años.",
        "requirements_json": json.dumps({
            "tiene_hijos": True,
        }),
        "questions_json": json.dumps([
            {"key": "tiene_hijos", "text": "¿Tienes hijos o descendientes a tu cargo?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes?", "type": "number"},
            {"key": "hijos_menores_6", "text": "¿Cuántos son menores de 6 años?", "type": "number"},
        ]),
    },
    {
        "code": "GIP-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 20.0,
        "max_amount": 1600.0,
        "legal_reference": "Art. 86 NF 3/2014 Gipuzkoa",
        "description": "20% del alquiler, máx. 1.600€. Familia numerosa: 25%, máx. 2.000€. Menores de 30: 30%, máx. 2.400€.",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_30_anos", "text": "¿Tienes menos de 30 años?", "type": "bool"},
        ]),
    },
    {
        "code": "GIP-COMPRA-VIV",
        "name": "Deducción por adquisición de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 18.0,
        "max_amount": 1530.0,
        "legal_reference": "Art. 87 NF 3/2014 Gipuzkoa",
        "description": "18% de la inversión (capital + intereses), máx. 1.530€/año. Menores de 30 o familia numerosa: 23%, máx. 1.955€. Límite vital: 36.000€. VIGENTE.",
        "requirements_json": json.dumps({
            "vivienda_habitual_propiedad": True,
        }),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "¿Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto pagas al año de hipoteca (capital + intereses)?", "type": "number"},
            {"key": "menor_30_anos", "text": "¿Tienes menos de 30 años?", "type": "bool"},
        ]),
    },
    {
        "code": "GIP-DISCAPACIDAD",
        "name": "Deducción por discapacidad",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 888.0,
        "legal_reference": "Art. 82 NF 3/2014 Gipuzkoa",
        "description": "888€ (33-65%), 1.268€ (≥65% o Grado I), 1.521€ (Grado II), 2.040€ (Grado III gran dependencia).",
        "requirements_json": json.dumps({
            "discapacidad_reconocida": True,
        }),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Qué grado de discapacidad tienes?", "type": "text"},
        ]),
    },
    {
        "code": "GIP-CUIDADO-MENORES",
        "name": "Deducción por cuidado de menores y personas dependientes",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 250.0,
        "legal_reference": "Art. 83 bis NF 3/2014 Gipuzkoa (NF 1/2025)",
        "description": "250€ por contrato indefinido con empleado/a del hogar para cuidado de menores de 12 años o personas con discapacidad ≥65% o dependencia. Nueva deducción desde 2025.",
        "requirements_json": json.dumps({
            "empleada_hogar_cuidado": True,
        }),
        "questions_json": json.dumps([
            {"key": "empleada_hogar_cuidado", "text": "¿Tienes contratada a una persona del hogar para el cuidado de menores o dependientes?", "type": "bool"},
        ]),
    },
    {
        "code": "GIP-ASCENDIENTES",
        "name": "Deducción por ascendientes a cargo",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 321.0,
        "legal_reference": "Art. 81 NF 3/2014 Gipuzkoa",
        "description": "321€ por cada ascendiente que conviva de forma continua con el contribuyente.",
        "requirements_json": json.dumps({
            "ascendiente_a_cargo": True,
        }),
        "questions_json": json.dumps([
            {"key": "ascendiente_a_cargo", "text": "¿Tienes padres o abuelos a tu cargo que convivan contigo?", "type": "bool"},
            {"key": "num_ascendientes", "text": "¿Cuántos ascendientes tienes a tu cargo?", "type": "number"},
        ]),
    },
]


# =============================================================================
# NAVARRA (TRIRPF DFL 4/2008 + Manual IRPF 2024)
# =============================================================================
NAVARRA_2025 = [
    {
        "code": "NAV-DESC-HIJOS",
        "name": "Deducción por descendientes (hijos)",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 483.0,
        "legal_reference": "Art. 62.9 TRIRPF Navarra",
        "description": "483€ por el 1º hijo, 512€ el 2º, 732€ el 3º, 981€ el 4º, 1.111€ del 5º, 1.286€ del 6º. Complemento +644€ por menor de 3 años. +40% si rentas ≤20.000€.",
        "requirements_json": json.dumps({
            "tiene_hijos": True,
        }),
        "questions_json": json.dumps([
            {"key": "tiene_hijos", "text": "¿Tienes hijos o descendientes a tu cargo?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes?", "type": "number"},
            {"key": "hijos_menores_3", "text": "¿Cuántos son menores de 3 años?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 1500.0,
        "legal_reference": "Art. 62.2 TRIRPF Navarra",
        "description": "15% del alquiler, máx. 1.500€. Menores de 30 o familias monoparentales: 20%, máx. 1.600€. Rentas ≤30.000€ individual / 60.000€ conjunta.",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_30_anos", "text": "¿Tienes menos de 30 años?", "type": "bool"},
        ]),
    },
    {
        "code": "NAV-DISCAPACIDAD",
        "name": "Deducción por discapacidad",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 674.0,
        "legal_reference": "Art. 62.9 TRIRPF Navarra",
        "description": "674€ (33-65%), 2.360€ (≥65%). Se aplica al contribuyente y también a descendientes/ascendientes con discapacidad.",
        "requirements_json": json.dumps({
            "discapacidad_reconocida": True,
        }),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Qué grado de discapacidad tienes? (33-65% o ≥65%)", "type": "text"},
        ]),
    },
    {
        "code": "NAV-DONATIVOS",
        "name": "Deducción por donativos (mecenazgo social)",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 80.0,
        "max_amount": 150.0,
        "legal_reference": "DFL 2/2023 Navarra",
        "description": "80% de los primeros 150€ donados + 35% del exceso (mecenazgo social/medioambiental/deportivo). Límite conjunto del 25% de la base liquidable.",
        "requirements_json": json.dumps({
            "donativo_a_entidad_acogida": True,
        }),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has hecho donativos a fundaciones o entidades sin ánimo de lucro navarras?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total este año?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-VEH-ELECT",
        "name": "Deducción por vehículo eléctrico",
        "type": "deduccion",
        "category": "sostenibilidad",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 62.7 TRIRPF Navarra",
        "description": "15% del precio de adquisición de vehículos eléctricos o híbridos enchufables. También 15% por puntos de recarga.",
        "requirements_json": json.dumps({
            "vehiculo_electrico_nuevo": True,
        }),
        "questions_json": json.dumps([
            {"key": "vehiculo_electrico_nuevo", "text": "¿Has comprado un vehículo eléctrico o híbrido enchufable nuevo este año?", "type": "bool"},
            {"key": "precio_vehiculo", "text": "¿Cuánto costó el vehículo?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-RENOVABLES",
        "name": "Deducción por instalación de energías renovables",
        "type": "deduccion",
        "category": "sostenibilidad",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 62.7 TRIRPF Navarra",
        "description": "15% de inversión en instalaciones de autoconsumo con energías renovables (fotovoltaica, eólica, hidráulica, bombas de calor). 20% si es comunidad de vecinos.",
        "requirements_json": json.dumps({
            "instalacion_renovable": True,
        }),
        "questions_json": json.dumps([
            {"key": "instalacion_renovable", "text": "¿Has instalado paneles solares, aerotermia u otra energía renovable en tu vivienda?", "type": "bool"},
            {"key": "importe_instalacion", "text": "¿Cuánto ha costado la instalación?", "type": "number"},
        ]),
    },
    {
        "code": "NAV-ASCENDIENTES",
        "name": "Deducción por ascendientes a cargo",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 264.0,
        "legal_reference": "Art. 62.9 TRIRPF Navarra",
        "description": "264€ por ascendiente ≥65 años, 585€ por ascendiente ≥75 años. Rentas del ascendiente inferiores al IPREM.",
        "requirements_json": json.dumps({
            "ascendiente_a_cargo": True,
        }),
        "questions_json": json.dumps([
            {"key": "ascendiente_a_cargo", "text": "¿Tienes padres o abuelos a tu cargo que convivan contigo?", "type": "bool"},
            {"key": "num_ascendientes", "text": "¿Cuántos ascendientes tienes a tu cargo?", "type": "number"},
        ]),
    },
]


# =============================================================================
# COMUNIDAD DE MADRID (DL 1/2010)
# =============================================================================
MADRID_2025 = [
    {
        "code": "MAD-NACIMIENTO",
        "name": "Deducción por nacimiento o adopción de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 721.70,
        "legal_reference": "Art. 4 DL 1/2010 Madrid",
        "description": "721,70€ por cada hijo nacido o adoptado, durante 3 años. Base imponible ≤30.930€ individual / ≤37.322€ conjunta; base imponible unidad familiar ≤61.860€.",
        "requirements_json": json.dumps({
            "nacimiento_adopcion_reciente": True,
        }),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado en los últimos 3 años?", "type": "bool"},
            {"key": "num_hijos_recientes", "text": "¿Cuántos hijos has tenido o adoptado en los últimos 3 años?", "type": "number"},
        ]),
    },
    {
        "code": "MAD-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual (jóvenes)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 30.0,
        "max_amount": 1237.20,
        "legal_reference": "Art. 8 DL 1/2010 Madrid",
        "description": "30% del alquiler, máx. 1.237,20€. Solo menores de 40 años. Base imponible ≤26.414,22€ individual; base imponible UF ≤61.860€.",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
            "menor_40_anos": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "menor_40_anos", "text": "¿Tienes menos de 40 años?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
        ]),
    },
    {
        "code": "MAD-GASTOS-EDUC",
        "name": "Deducción por gastos educativos",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 927.90,
        "legal_reference": "Art. 11 DL 1/2010 Madrid",
        "description": "15% de escolaridad (máx. 927,90€/hijo, 1.031€ para 0-3 años). 15% de enseñanza de idiomas (máx. 412,40€/hijo). 5% de vestuario escolar (combinado con idiomas máx. 412,40€).",
        "requirements_json": json.dumps({
            "gastos_educativos": True,
        }),
        "questions_json": json.dumps([
            {"key": "gastos_educativos", "text": "¿Tienes gastos de escolaridad, idiomas o uniformes escolares de tus hijos?", "type": "bool"},
            {"key": "importe_escolaridad", "text": "¿Cuánto has pagado de escolaridad privada (no concertada) este año?", "type": "number"},
            {"key": "importe_idiomas", "text": "¿Cuánto has pagado en enseñanza de idiomas?", "type": "number"},
        ]),
    },
    {
        "code": "MAD-CUID-ASC",
        "name": "Deducción por cuidado de ascendientes",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 515.50,
        "legal_reference": "Art. 7 bis DL 1/2010 Madrid",
        "description": "515,50€ por cada ascendiente mayor de 65 años o con discapacidad ≥33% que genere derecho al mínimo por ascendientes.",
        "requirements_json": json.dumps({
            "ascendiente_a_cargo": True,
        }),
        "questions_json": json.dumps([
            {"key": "ascendiente_a_cargo", "text": "¿Tienes padres o abuelos a tu cargo mayores de 65 años o con discapacidad?", "type": "bool"},
            {"key": "num_ascendientes", "text": "¿Cuántos ascendientes tienes a tu cargo?", "type": "number"},
        ]),
    },
    {
        "code": "MAD-DONATIVOS",
        "name": "Deducción por donativos a fundaciones y clubes deportivos",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 9 DL 1/2010 Madrid",
        "description": "15% de las donaciones a fundaciones inscritas en la CM de Madrid. Máximo: 10% de la base liquidable.",
        "requirements_json": json.dumps({
            "donativo_a_entidad_acogida": True,
        }),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has hecho donativos a fundaciones o clubes deportivos inscritos en la Comunidad de Madrid?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
    {
        "code": "MAD-CUIDADO-HIJOS",
        "name": "Deducción por cuidado de hijos menores de 3 años",
        "type": "deduccion",
        "category": "familia",
        "percentage": 25.0,
        "max_amount": 463.95,
        "legal_reference": "Art. 11 bis DL 1/2010 Madrid",
        "description": "25% de las cotizaciones SS por empleado del hogar, máx. 463,95€. Familia numerosa: 40%, máx. 618,60€. Para cuidado de hijos <3 años, mayores dependientes o discapacitados.",
        "requirements_json": json.dumps({
            "empleada_hogar_cuidado": True,
        }),
        "questions_json": json.dumps([
            {"key": "empleada_hogar_cuidado", "text": "¿Tienes contratada a una persona del hogar para cuidado de hijos menores de 3 o dependientes?", "type": "bool"},
            {"key": "cotizaciones_ss_hogar", "text": "¿Cuánto pagas en cotizaciones a la SS por el/la empleado/a del hogar?", "type": "number"},
        ]),
    },
]


# =============================================================================
# CATALUÑA (DL 1/2024 Libro Sexto Código Tributario)
# =============================================================================
CATALUNA_2025 = [
    {
        "code": "CAT-NACIMIENTO",
        "name": "Deducción por nacimiento o adopción",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 612-1 DL 1/2024 Cataluña",
        "description": "150€ en declaración individual, 300€ en conjunta. 300€ para familias monoparentales.",
        "requirements_json": json.dumps({
            "nacimiento_adopcion_reciente": True,
        }),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año?", "type": "bool"},
        ]),
    },
    {
        "code": "CAT-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 612-3 DL 1/2024 Cataluña",
        "description": "10% del alquiler, máx. 300€ (600€ conjunta). Solo para: ≤32 años, desempleados ≥183 días, discapacidad ≥65%, viudos ≥65, o familias numerosas/monoparentales. BI-mínimo ≤20.000€ individual / 30.000€ conjunta.",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_32_anos", "text": "¿Tienes 32 años o menos?", "type": "bool"},
        ]),
    },
    {
        "code": "CAT-DONAT-CATALAN",
        "name": "Deducción por donativos fomento lengua catalana/occitana",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 612-6 DL 1/2024 Cataluña",
        "description": "15% de donativos a entidades que fomentan la lengua catalana u occitana. Máx. 10% de la cuota íntegra autonómica.",
        "requirements_json": json.dumps({
            "donativo_fomento_catalan": True,
        }),
        "questions_json": json.dumps([
            {"key": "donativo_fomento_catalan", "text": "¿Has donado a entidades que fomentan la lengua catalana u occitana?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado?", "type": "number"},
        ]),
    },
    {
        "code": "CAT-DONAT-IDI",
        "name": "Deducción por donativos a investigación científica",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 30.0,
        "max_amount": None,
        "legal_reference": "Art. 612-7 DL 1/2024 Cataluña",
        "description": "30% de donativos a universidades y centros de investigación catalanes para I+D+i. Máx. 10% de la cuota íntegra autonómica.",
        "requirements_json": json.dumps({
            "donativo_investigacion_cat": True,
        }),
        "questions_json": json.dumps([
            {"key": "donativo_investigacion_cat", "text": "¿Has donado a universidades o centros de investigación catalanes?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado?", "type": "number"},
        ]),
    },
    {
        "code": "CAT-REHAB-VIV",
        "name": "Deducción por rehabilitación de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 1.5,
        "max_amount": 9040.0,
        "legal_reference": "Art. 612-4 DL 1/2024 Cataluña",
        "description": "1,5% de las cantidades satisfechas por rehabilitación de la vivienda habitual, máx. base 9.040€.",
        "requirements_json": json.dumps({
            "rehabilitacion_vivienda": True,
        }),
        "questions_json": json.dumps([
            {"key": "rehabilitacion_vivienda", "text": "¿Has realizado obras de rehabilitación en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_obras", "text": "¿Cuánto has invertido en las obras?", "type": "number"},
        ]),
    },
]


# =============================================================================
# ANDALUCÍA (Ley 5/2021)
# =============================================================================
ANDALUCIA_2025 = [
    {
        "code": "AND-VIV-JOVEN",
        "name": "Deducción por inversión en vivienda habitual (jóvenes/protegida)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 5.0,
        "max_amount": 9040.0,
        "legal_reference": "Art. 9 Ley 5/2021 Andalucía",
        "description": "5% de la inversión en vivienda protegida o si el contribuyente es menor de 35 años, máx. base 9.040€. BI ≤25.000€ individual / 30.000€ conjunta.",
        "requirements_json": json.dumps({
            "vivienda_habitual_propiedad": True,
        }),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "¿Tienes una vivienda protegida o eres menor de 35 años con hipoteca?", "type": "bool"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca este año?", "type": "number"},
        ]),
    },
    {
        "code": "AND-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 600.0,
        "legal_reference": "Art. 10 Ley 5/2021 Andalucía",
        "description": "15% del alquiler, máx. 600€ (900€ con discapacidad). Para menores de 35, mayores de 65, víctimas de violencia o terrorismo. BI ≤25.000€ indiv. / 30.000€ conjunta.",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
        ]),
    },
    {
        "code": "AND-NACIMIENTO",
        "name": "Deducción por nacimiento, adopción o acogimiento",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 11 Ley 5/2021 Andalucía",
        "description": "200€ por hijo (400€ si es en municipio de menos de 3.000 habitantes). BI ≤25.000€ individual / 30.000€ conjunta.",
        "requirements_json": json.dumps({
            "nacimiento_adopcion_reciente": True,
        }),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo, adoptado o acogido este año?", "type": "bool"},
        ]),
    },
    {
        "code": "AND-DISCAPACIDAD",
        "name": "Deducción por discapacidad del contribuyente",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 16 Ley 5/2021 Andalucía",
        "description": "150€ para contribuyentes con discapacidad ≥33%. BI ≤25.000€ individual / 30.000€ conjunta.",
        "requirements_json": json.dumps({
            "discapacidad_reconocida": True,
        }),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
        ]),
    },
    {
        "code": "AND-AYUDA-DOMESTICA",
        "name": "Deducción por ayuda doméstica",
        "type": "deduccion",
        "category": "familia",
        "percentage": 20.0,
        "max_amount": 500.0,
        "legal_reference": "Arts. 19, 4 y DT 3a Ley 5/2021 Andalucía",
        "description": "20% de las cotizaciones a la Seguridad Social del empleado/a del hogar, máx. 500€. Requisito: progenitor con hijos dependientes y ambos progenitores con rentas del trabajo/actividades, o contribuyente de 75+ años.",
        "requirements_json": json.dumps({
            "empleada_hogar_cuidado": True,
        }),
        "questions_json": json.dumps([
            {"key": "empleada_hogar_cuidado", "text": "¿Tienes contratada a una persona empleada del hogar?", "type": "bool"},
            {"key": "coste_empleada_hogar", "text": "¿Cuánto has pagado en total por el servicio doméstico este año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# COMUNITAT VALENCIANA (Ley 13/1997)
# =============================================================================
VALENCIA_2025 = [
    {
        "code": "VAL-NACIMIENTO",
        "name": "Deducción por nacimiento, adopción o acogimiento",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 4.Uno.a) Ley 13/1997 Valencia",
        "description": "300€ por cada hijo nacido, adoptado o acogido, durante 3 años. BL ≤30.000€ individual / 47.000€ conjunta.",
        "requirements_json": json.dumps({
            "nacimiento_adopcion_reciente": True,
        }),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo, adoptado o acogido en los últimos 3 años?", "type": "bool"},
            {"key": "num_hijos_recientes", "text": "¿Cuántos hijos has tenido o adoptado en los últimos 3 años?", "type": "number"},
        ]),
    },
    {
        "code": "VAL-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 330.0,
        "legal_reference": "Art. 4.Uno.d) Ley 13/1997 Valencia",
        "description": "330€ familia numerosa general, 660€ especial. También 330/660€ para familias monoparentales. BL ≤30.000€ indiv. / 47.000€ conjunta (especial: 35.000/58.000€).",
        "requirements_json": json.dumps({
            "familia_numerosa": True,
        }),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
        ]),
    },
    {
        "code": "VAL-ALQUILER-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 20.0,
        "max_amount": 800.0,
        "legal_reference": "Art. 4.Uno.n) Ley 13/1997 Valencia",
        "description": "20% del alquiler, máx. 800€. Con 1 condición (≤35 años, discapacidad física ≥65% o psíquica ≥33%, víctima VG): 25%, máx. 950€. Con 2+ condiciones: 30%, máx. 1.100€. BL ≤30.000€ indiv. / 47.000€ conjunta (deducción plena hasta 27.000/44.000€).",
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
        ]),
    },
    {
        "code": "VAL-GUARDERIA",
        "name": "Deducción por guardería (menores de 3 años)",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 298.0,
        "legal_reference": "Art. 4.Uno.e) Ley 13/1997 Valencia",
        "description": "Hasta 298€ por hijo menor de 3 años en guardería o centro de educación infantil de primer ciclo. BL sujeta a límites.",
        "requirements_json": json.dumps({
            "hijo_menor_3": True,
            "guarderia_autorizada": True,
        }),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "¿Tienes hijos menores de 3 años?", "type": "bool"},
            {"key": "guarderia_autorizada", "text": "¿Están en una guardería o centro de educación infantil autorizado?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "¿Cuánto has pagado de guardería este año?", "type": "number"},
        ]),
    },
    {
        "code": "VAL-MAT-ESCOLAR",
        "name": "Deducción por material escolar",
        "type": "deduccion",
        "category": "educacion",
        "fixed_amount": 110.0,
        "legal_reference": "Art. 4.Uno.cc) Ley 13/1997 Valencia",
        "description": "110€ por cada descendiente escolarizado en Educación Primaria, ESO o unidades de educación especial. BL sujeta a límites.",
        "requirements_json": json.dumps({
            "hijos_escolarizados": True,
        }),
        "questions_json": json.dumps([
            {"key": "hijos_escolarizados", "text": "¿Tienes hijos en Educación Primaria, ESO o educación especial?", "type": "bool"},
            {"key": "num_hijos_escolarizados", "text": "¿Cuántos hijos escolarizados tienes?", "type": "number"},
        ]),
    },
    {
        "code": "VAL-RENOVABLES",
        "name": "Deducción por instalaciones de autoconsumo renovable",
        "type": "deduccion",
        "category": "sostenibilidad",
        "percentage": 40.0,
        "max_amount": None,
        "legal_reference": "Art. 4.Uno.p) Ley 13/1997 Valencia",
        "description": "40-65% de inversión en instalaciones de autoconsumo eléctrico con energías renovables, según tipo de instalación.",
        "requirements_json": json.dumps({
            "instalacion_renovable": True,
        }),
        "questions_json": json.dumps([
            {"key": "instalacion_renovable", "text": "¿Has instalado paneles solares u otra energía renovable para autoconsumo?", "type": "bool"},
            {"key": "importe_instalacion", "text": "¿Cuánto ha costado la instalación?", "type": "number"},
        ]),
    },
]


# =============================================================================
# MAPPING: territory name -> deductions list
# =============================================================================
ALL_TERRITORIAL = {
    "Araba": ARABA_2025,
    "Bizkaia": BIZKAIA_2025,
    "Gipuzkoa": GIPUZKOA_2025,
    "Navarra": NAVARRA_2025,
    "Madrid": MADRID_2025,
    "Cataluña": CATALUNA_2025,
    "Andalucía": ANDALUCIA_2025,
    "Valencia": VALENCIA_2025,
}


async def seed_territorial():
    """Insert all territorial deductions into the database."""
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    print("Initializing schema...")
    await db.init_schema()
    print("Schema ready.\n")

    total_inserted = 0
    total_skipped = 0

    for territory, deductions in ALL_TERRITORIAL.items():
        inserted = 0
        skipped = 0

        for d in deductions:
            deduction_id = str(uuid.uuid4())
            try:
                await db.execute(
                    """INSERT OR IGNORE INTO deductions
                       (id, code, tax_year, territory, name, type, category,
                        percentage, max_amount, fixed_amount, legal_reference,
                        description, requirements_json, questions_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        deduction_id,
                        d["code"],
                        2025,
                        territory,
                        d["name"],
                        d["type"],
                        d["category"],
                        d.get("percentage"),
                        d.get("max_amount"),
                        d.get("fixed_amount"),
                        d.get("legal_reference"),
                        d.get("description"),
                        d.get("requirements_json"),
                        d.get("questions_json"),
                    ],
                )
                result = await db.execute(
                    "SELECT id FROM deductions WHERE code = ? AND tax_year = ? AND territory = ?",
                    [d["code"], 2025, territory],
                )
                if result.rows and result.rows[0]["id"] == deduction_id:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  Error inserting {d['code']}: {e}")
                skipped += 1

        print(f"  {territory}: {inserted} inserted, {skipped} skipped")
        total_inserted += inserted
        total_skipped += skipped

    await db.disconnect()

    total_deductions = sum(len(d) for d in ALL_TERRITORIAL.values())
    print(f"\nSeed complete: {total_inserted} inserted, {total_skipped} skipped")
    print(f"Territories covered: {len(ALL_TERRITORIAL)}")
    print(f"Total territorial deductions: {total_deductions}")


if __name__ == "__main__":
    asyncio.run(seed_territorial())
