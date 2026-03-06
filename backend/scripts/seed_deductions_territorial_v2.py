"""
Seed script for territorial IRPF deductions — v2 (expansion).

Adds deducciones for the 11 CCAA missing from v1:
  Galicia, Asturias, Cantabria, La Rioja, Aragón,
  Castilla y León, Castilla-La Mancha, Extremadura,
  Murcia, Islas Baleares, Islas Canarias.

Sources: legislation in force for fiscal year 2025.
- Galicia: DL 1/2011 Código Tributario Galicia (CTRG)
- Asturias: DL 2/2014 Código Tributario Asturias
- Cantabria: DL 62/2008 Ley IRPF Cantabria (texto refundido 2024)
- La Rioja: Ley 10/2017 Texto Refundido IRPF Rioja
- Aragón: DL 1/2005 Texto Refundido Tributos Aragón
- Castilla y León: DL 1/2013 Texto Refundido IRPF CyL
- Castilla-La Mancha: Ley 8/2013 Medidas Tributarias CLM
- Extremadura: DL 1/2013 Texto Refundido Ext.
- Murcia: DL 1/2010 Texto Refundido Murcia
- Islas Baleares: DL 1/2014 Texto Refundido IB
- Islas Canarias: DL 1/2009 Texto Refundido IC

Idempotent: uses INSERT OR IGNORE — safe to run multiple times.

Usage:
    cd backend
    PYTHONUTF8=1 python scripts/seed_deductions_territorial_v2.py
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
# GALICIA (DL 1/2011 Código Tributario de Galicia — CTRG)
# =============================================================================
GALICIA_2025 = [
    {
        "code": "GAL-NAC-ADOP",
        "name": "Deducción por nacimiento o adopción de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 5.1 CTRG / DL 1/2011 Galicia",
        "description": (
            "300€ por el 1º hijo, 360€ por el 2º, 1.200€ por el 3º y posteriores. "
            "El importe se triplica si el municipio tiene menos de 5.000 habitantes. "
            "La base liquidable no puede superar 22.000€ individual o 31.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año fiscal?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes en total (incluido el nuevo)?", "type": "number"},
            {"key": "municipio_rural", "text": "¿Vives en un municipio de menos de 5.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "GAL-ALQ-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 5.6 CTRG / DL 1/2011 Galicia",
        "description": (
            "10% de las cantidades satisfechas por alquiler de la vivienda habitual, "
            "con un máximo de 300€ (600€ en declaración conjunta). "
            "Base liquidable ≤22.000€ individual o ≤31.000€ conjunta. "
            "Para menores de 35 años o mayores de 65, el límite sube a 600€ (1.200€ conjunta)."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Galicia?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
        ]),
    },
    {
        "code": "GAL-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 250.0,
        "legal_reference": "Art. 5.4 CTRG / DL 1/2011 Galicia",
        "description": (
            "250€ para familias numerosas de categoría general y 400€ para especial. "
            "La deducción se incrementa en 100€ por cada descendiente con discapacidad."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial (5 o más hijos, o 4 con discapacidad)?", "type": "bool"},
        ]),
    },
    {
        "code": "GAL-CUID-MAYORES",
        "name": "Deducción por cuidado de hijos menores y otros dependientes",
        "type": "deduccion",
        "category": "familia",
        "percentage": 30.0,
        "max_amount": 400.0,
        "legal_reference": "Art. 5.7 CTRG / DL 1/2011 Galicia",
        "description": (
            "30% de los gastos satisfechos en guarderías o centros de 0-3 años, "
            "máximo 400€ por hijo. También aplicable a cuidado de ascendientes o "
            "personas con discapacidad. Ambos cónyuges deben tener rentas del trabajo."
        ),
        "requirements_json": json.dumps({"hijo_menor_3": True}),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "¿Tienes hijos menores de 3 años en guardería o centro autorizado?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "¿Cuánto has pagado de guardería o cuidados este año?", "type": "number"},
        ]),
    },
    {
        "code": "GAL-DISCAPACIDAD",
        "name": "Deducción por discapacidad del contribuyente",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 100.0,
        "legal_reference": "Art. 5.8 CTRG / DL 1/2011 Galicia",
        "description": (
            "100€ para contribuyentes con discapacidad de grado igual o superior al 33%. "
            "200€ para grado igual o superior al 65%."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es tu grado de discapacidad? (33-65% o ≥65%)", "type": "text"},
        ]),
    },
    {
        "code": "GAL-DONATIVO",
        "name": "Deducción por donativos a entidades gallegas",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 25.0,
        "max_amount": None,
        "legal_reference": "Art. 5.9 CTRG / DL 1/2011 Galicia",
        "description": (
            "25% de los donativos realizados a fundaciones gallegas o entidades "
            "declaradas de utilidad pública en Galicia. Límite: 10% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has hecho donativos a fundaciones o entidades de utilidad pública gallegas?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
]


# =============================================================================
# ASTURIAS (DL 2/2014 Código Tributario Asturias)
# =============================================================================
ASTURIAS_2025 = [
    {
        "code": "AST-NAC-ADOP",
        "name": "Deducción por adopción internacional de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 1010.0,
        "legal_reference": "Art. 7 DL 2/2014 Asturias",
        "description": (
            "1.010€ por cada hijo adoptado en el extranjero mediante procedimiento "
            "de adopción internacional reconocido. Deducción aplicable en el ejercicio "
            "en que se produce la adopción."
        ),
        "requirements_json": json.dumps({"adopcion_internacional": True}),
        "questions_json": json.dumps([
            {"key": "adopcion_internacional", "text": "¿Has adoptado un hijo en el extranjero este año?", "type": "bool"},
        ]),
    },
    {
        "code": "AST-ALQ-JOV",
        "name": "Deducción por alquiler de vivienda habitual (jóvenes y familia monoparental)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 4000.0,
        "legal_reference": "Art. 12 DL 2/2014 Asturias",
        "description": (
            "10% de las cantidades satisfechas por arrendamiento de la vivienda habitual, "
            "máximo 4.000€ (cuotas de SS excluidas). Para contribuyentes menores de 35 años, "
            "familias monoparentales o víctimas de violencia de género. "
            "Base liquidable ≤25.009€ individual o ≤35.240€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Asturias?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
            {"key": "familia_monoparental", "text": "¿Tienes una familia monoparental?", "type": "bool"},
        ]),
    },
    {
        "code": "AST-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 505.0,
        "legal_reference": "Art. 6 DL 2/2014 Asturias",
        "description": (
            "505€ para familia numerosa de categoría general. "
            "1.010€ para familia numerosa de categoría especial. "
            "La deducción es compatible con las deducciones estatales."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
        ]),
    },
    {
        "code": "AST-DISCAPACIDAD",
        "name": "Deducción por discapacidad del contribuyente o ascendientes/descendientes",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 14 DL 2/2014 Asturias",
        "description": (
            "300€ por contribuyente con discapacidad ≥33% y base liquidable ≤25.009€. "
            "También 300€ por cada descendiente/ascendiente con discapacidad ≥65% en el mismo umbral de renta."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes o tienes a tu cargo personas con discapacidad reconocida ≥33%?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es el grado de discapacidad?", "type": "text"},
        ]),
    },
    {
        "code": "AST-GASTOS-ENSENANZA",
        "name": "Deducción por gastos de estudios en centros de enseñanza reglada no universitaria",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 5.0,
        "max_amount": 1000.0,
        "legal_reference": "Art. 13 DL 2/2014 Asturias",
        "description": (
            "5% de los gastos en escolaridad, libros de texto, material escolar y uniforme "
            "en centros de enseñanza reglada no universitaria, máx. 1.000€ por declaración. "
            "Base liquidable ≤25.009€ individual o ≤35.240€ conjunta."
        ),
        "requirements_json": json.dumps({"gastos_educativos": True}),
        "questions_json": json.dumps([
            {"key": "gastos_educativos", "text": "¿Tienes hijos con gastos de material escolar, libros o uniformes?", "type": "bool"},
            {"key": "importe_gastos_educacion", "text": "¿Cuánto has gastado en material y gastos escolares este año?", "type": "number"},
        ]),
    },
    {
        "code": "AST-VIV-HABITUAL",
        "name": "Deducción por inversión en vivienda habitual (adquisición antes 2013)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 3.0,
        "max_amount": 9040.0,
        "legal_reference": "Art. 11 DL 2/2014 Asturias",
        "description": (
            "Tramo autonómico del 3% para la deducción por adquisición de vivienda habitual. "
            "Solo para contribuyentes que adquirieron antes del 1/1/2013 y venían deduciendo. "
            "El tramo estatal es del 7,5% — este es el complemento autonómico de Asturias."
        ),
        "requirements_json": json.dumps({
            "adquisicion_antes_2013": True,
            "deducia_antes_2013": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_antes_2013", "text": "¿Adquiriste tu vivienda habitual antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "deducia_antes_2013", "text": "¿Aplicabas la deducción por vivienda habitual en la declaración de 2012 o anteriores?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca este año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# CANTABRIA (DL 62/2008 — Texto Refundido Ley IRPF Cantabria)
# =============================================================================
CANTABRIA_2025 = [
    {
        "code": "CAN-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 1127.0,
        "legal_reference": "Art. 2 DL 62/2008 Cantabria",
        "description": (
            "1.127€ para familia numerosa de categoría general. "
            "2.112€ para familia numerosa de categoría especial."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
        ]),
    },
    {
        "code": "CAN-ALQ-JOV",
        "name": "Deducción por alquiler de vivienda habitual (jóvenes)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 6 DL 62/2008 Cantabria",
        "description": (
            "10% de las cuotas satisfechas por arrendamiento de la vivienda habitual, "
            "máx. 300€. Para contribuyentes menores de 35 años o mayores de 65. "
            "Base liquidable ≤22.000€ individual o ≤31.000€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Cantabria?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años o más de 65?", "type": "bool"},
        ]),
    },
    {
        "code": "CAN-GASTOS-ENFERMEDAD",
        "name": "Deducción por gastos de enfermedad",
        "type": "deduccion",
        "category": "social",
        "percentage": 10.0,
        "max_amount": 500.0,
        "legal_reference": "Art. 8 DL 62/2008 Cantabria",
        "description": (
            "10% de los gastos médicos, hospitalarios, odontológicos, ópticos y "
            "farmacéuticos no cubiertos por la Seguridad Social o seguro privado, "
            "máx. 500€. Aplicable también a los satisfechos por el cónyuge, "
            "descendientes y ascendientes."
        ),
        "requirements_json": json.dumps({"gastos_enfermedad": True}),
        "questions_json": json.dumps([
            {"key": "gastos_enfermedad", "text": "¿Has tenido gastos médicos, dentales, de óptica o farmacia no cubiertos por la SS ni seguro?", "type": "bool"},
            {"key": "importe_gastos_medicos", "text": "¿Cuánto has gastado en total en gastos médicos no cubiertos?", "type": "number"},
        ]),
    },
    {
        "code": "CAN-DISCAPACIDAD",
        "name": "Deducción por discapacidad del contribuyente",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 100.0,
        "legal_reference": "Art. 9 DL 62/2008 Cantabria",
        "description": (
            "100€ para contribuyentes con discapacidad de grado igual o superior al 33%. "
            "300€ para discapacidad de grado igual o superior al 65%."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es tu grado de discapacidad? (33-65% o ≥65%)", "type": "text"},
        ]),
    },
    {
        "code": "CAN-NAC-ADOP",
        "name": "Deducción por nacimiento, adopción o acogimiento",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 240.0,
        "legal_reference": "Art. 4 DL 62/2008 Cantabria",
        "description": (
            "240€ por cada hijo nacido o adoptado. La deducción se duplica si el "
            "municipio tiene menos de 2.000 habitantes. Base liquidable ≤31.000€ "
            "individual o ≤43.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo, adoptado o acogido este año?", "type": "bool"},
            {"key": "municipio_rural", "text": "¿Vives en un municipio de menos de 2.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "CAN-VIV-HABITUAL",
        "name": "Deducción por inversión en vivienda habitual (adquisición antes 2013)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 2.5,
        "max_amount": 9.040,
        "legal_reference": "Art. 3 DL 62/2008 Cantabria",
        "description": (
            "Tramo autonómico del 2,5% adicional por adquisición de vivienda habitual "
            "para contribuyentes que adquirieron antes del 1/1/2013 y venían deduciendo. "
            "Aplica sobre la misma base máxima de 9.040€."
        ),
        "requirements_json": json.dumps({
            "adquisicion_antes_2013": True,
            "deducia_antes_2013": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_antes_2013", "text": "¿Adquiriste tu vivienda habitual antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "deducia_antes_2013", "text": "¿Aplicabas ya la deducción por vivienda antes de 2013?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca este año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# LA RIOJA (Ley 10/2017 — Texto Refundido IRPF La Rioja)
# =============================================================================
LA_RIOJA_2025 = [
    {
        "code": "RIO-NAC-ADOP",
        "name": "Deducción por nacimiento o adopción de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 10 Ley 10/2017 La Rioja",
        "description": (
            "150€ por el primer hijo, 180€ por el segundo, 720€ a partir del tercero. "
            "Si el hijo tiene discapacidad ≥65%: 414€ (1º), 582€ (2º), 1.164€ (3º y ss). "
            "Base liquidable ≤31.000€ individual o ≤43.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año en La Rioja?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes en total?", "type": "number"},
            {"key": "descendiente_discapacidad", "text": "¿El hijo tiene discapacidad reconocida ≥65%?", "type": "bool"},
        ]),
    },
    {
        "code": "RIO-VIV-JOV",
        "name": "Deducción por adquisición de vivienda habitual (jóvenes menores de 36)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 5.0,
        "max_amount": 9.040,
        "legal_reference": "Art. 14 Ley 10/2017 La Rioja",
        "description": (
            "3% de las cantidades satisfechas por adquisición de vivienda habitual "
            "financiada mediante crédito hipotecario (tramo autonómico). "
            "Para menores de 36 años el porcentaje es del 5%. "
            "Aplica únicamente a viviendas adquiridas antes del 1/1/2013."
        ),
        "requirements_json": json.dumps({
            "adquisicion_antes_2013": True,
            "deducia_antes_2013": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_antes_2013", "text": "¿Adquiriste tu vivienda habitual antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "deducia_antes_2013", "text": "¿Aplicabas ya la deducción por vivienda antes de 2013?", "type": "bool"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca este año?", "type": "number"},
        ]),
    },
    {
        "code": "RIO-ALQ-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 15 Ley 10/2017 La Rioja",
        "description": (
            "10% de las cantidades satisfechas por alquiler de la vivienda habitual, "
            "máx. 300€. Para menores de 36 años o personas con discapacidad ≥65%. "
            "Base liquidable ≤18.030€ individual o ≤30.050€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en La Rioja?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años?", "type": "bool"},
        ]),
    },
    {
        "code": "RIO-CONCILIACION",
        "name": "Deducción por conciliación (gastos guardería)",
        "type": "deduccion",
        "category": "familia",
        "percentage": 30.0,
        "max_amount": 200.0,
        "legal_reference": "Art. 11 Ley 10/2017 La Rioja",
        "description": (
            "30% de los gastos de guardería o cuidado de hijos menores de 4 años, "
            "máx. 200€ por hijo. La madre debe tener rentas del trabajo o de actividades "
            "económicas. Incompatible con la deducción estatal por maternidad."
        ),
        "requirements_json": json.dumps({"hijo_menor_3": True}),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "¿Tienes hijos menores de 4 años en guardería autorizada?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "¿Cuánto has gastado en guardería este año?", "type": "number"},
        ]),
    },
    {
        "code": "RIO-DONATIVO",
        "name": "Deducción por donativos a fundaciones riojanas",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 16 Ley 10/2017 La Rioja",
        "description": (
            "15% de los donativos efectuados a fundaciones inscritas en el Registro de "
            "Fundaciones de La Rioja que persigan fines culturales, asistenciales, "
            "deportivos o de naturaleza análoga. Límite: 10% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has donado a fundaciones o entidades de utilidad pública riojanas?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
    {
        "code": "RIO-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 12 Ley 10/2017 La Rioja",
        "description": (
            "150€ para familias numerosas de categoría general. "
            "300€ para familias numerosas de categoría especial."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
        ]),
    },
]


# =============================================================================
# ARAGÓN (DL 1/2005 — Texto Refundido Tributos Aragón, mod. Ley 10/2022)
# =============================================================================
ARAGON_2025 = [
    {
        "code": "ARA-NAC-ADOP",
        "name": "Deducción por nacimiento o adopción del tercer hijo o sucesivos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 500.0,
        "legal_reference": "Art. 110-1 DL 1/2005 Aragón",
        "description": (
            "500€ por el tercer hijo o sucesivos nacidos o adoptados (100€ por 1º y 2º). "
            "El importe se eleva a 600€ (300€ 1º y 2º) si el municipio tiene menos de 2.000 habitantes. "
            "Para familias monoparentales: importe duplicado. BI ≤35.000€ individual / 55.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año en Aragón?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes en total?", "type": "number"},
            {"key": "municipio_rural", "text": "¿Vives en un municipio de menos de 2.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "ARA-CUID-DEP",
        "name": "Deducción por cuidado de personas dependientes",
        "type": "deduccion",
        "category": "social",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 110-3 DL 1/2005 Aragón",
        "description": (
            "150€ por cada ascendiente o descendiente con discapacidad ≥65% o dependencia "
            "reconocida que conviva con el contribuyente. BI ≤35.000€ individual / ≤55.000€ conjunta."
        ),
        "requirements_json": json.dumps({"ascendiente_discapacidad": True}),
        "questions_json": json.dumps([
            {"key": "ascendiente_discapacidad", "text": "¿Tienes familiares a cargo con discapacidad ≥65% o dependencia reconocida?", "type": "bool"},
            {"key": "num_dependientes", "text": "¿Cuántas personas con discapacidad o dependencia tienes a tu cargo?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-VIV-RURAL",
        "name": "Deducción por adquisición de vivienda habitual en municipios en riesgo de despoblación",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 5.0,
        "max_amount": 9.040,
        "legal_reference": "Art. 110-5 DL 1/2005 Aragón",
        "description": (
            "5% de las cantidades invertidas en adquisición de vivienda habitual en municipios "
            "en riesgo de despoblación de Aragón (menos de 1.000 habitantes). "
            "Base máxima: 9.040€."
        ),
        "requirements_json": json.dumps({"vivienda_zona_rural_aragon": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_zona_rural_aragon", "text": "¿Has adquirido tu vivienda habitual en un municipio aragonés con menos de 1.000 habitantes?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca o inversión en la vivienda este año?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-DONAT-INVESTIG",
        "name": "Deducción por donaciones a I+D+i en Aragón",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 20.0,
        "max_amount": None,
        "legal_reference": "Art. 110-8 DL 1/2005 Aragón",
        "description": (
            "20% de los donativos a centros de investigación adscritos a universidades aragonesas "
            "o al CSIC en Aragón. Límite: 15% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_investigacion_aragon": True}),
        "questions_json": json.dumps([
            {"key": "donativo_investigacion_aragon", "text": "¿Has donado a centros de investigación o universidades aragonesas?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado?", "type": "number"},
        ]),
    },
    {
        "code": "ARA-ALQ-VIV",
        "name": "Deducción por arrendamiento de vivienda habitual (jóvenes y zona rural)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 1.000,
        "legal_reference": "Art. 110-4 DL 1/2005 Aragón",
        "description": (
            "10% de las cantidades satisfechas por arrendamiento de vivienda habitual, "
            "máx. 1.000€ (2.000€ si el municipio tiene menos de 1.000 habitantes). "
            "Para menores de 35 años o mayores de 65. BI ≤35.000€ individual / ≤55.000€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Aragón?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años o más de 65?", "type": "bool"},
        ]),
    },
    {
        "code": "ARA-DISCAPACIDAD",
        "name": "Deducción por nacimiento o adopción de hijo con discapacidad",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 110-2 DL 1/2005 Aragón",
        "description": (
            "200€ adicionales por cada hijo nacido o adoptado con discapacidad reconocida "
            "igual o superior al 33%, compatible con la deducción por nacimiento. "
            "BI ≤35.000€ individual o ≤55.000€ conjunta."
        ),
        "requirements_json": json.dumps({
            "nacimiento_adopcion_reciente": True,
            "descendiente_discapacidad": True,
        }),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo nacido o adoptado este año?", "type": "bool"},
            {"key": "descendiente_discapacidad", "text": "¿El hijo tiene discapacidad reconocida ≥33%?", "type": "bool"},
        ]),
    },
]


# =============================================================================
# CASTILLA Y LEÓN (DL 1/2013 — Texto Refundido Tributos propios CyL)
# =============================================================================
CASTILLA_LEON_2025 = [
    {
        "code": "CYL-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 246.0,
        "legal_reference": "Art. 8 DL 1/2013 Castilla y León",
        "description": (
            "246€ para familia numerosa de categoría general. "
            "492€ para familia numerosa de categoría especial. "
            "Ambos cónyuges deben residir en Castilla y León."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido en Castilla y León?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
        ]),
    },
    {
        "code": "CYL-NAC-ADOP",
        "name": "Deducción por nacimiento o adopción de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 1.010,
        "legal_reference": "Art. 9 DL 1/2013 Castilla y León",
        "description": (
            "1.010€ por cada hijo nacido o adoptado durante el período impositivo. "
            "El importe se duplica si el municipio tiene menos de 10.000 habitantes. "
            "BI ≤31.500€ individual o ≤47.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año en Castilla y León?", "type": "bool"},
            {"key": "municipio_rural", "text": "¿Vives en un municipio de menos de 10.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "CYL-CUID-HIJOS-4",
        "name": "Deducción por cuidado de hijos menores de 4 años",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 1.000,
        "legal_reference": "Art. 10 DL 1/2013 Castilla y León",
        "description": (
            "Hasta 1.000€ por los gastos satisfechos en guarderías o centros de educación "
            "infantil de primer ciclo para hijos menores de 4 años. "
            "Los dos progenitores deben trabajar y cotizar a la Seguridad Social."
        ),
        "requirements_json": json.dumps({"hijo_menor_3": True}),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "¿Tienes hijos menores de 4 años en guardería o centro de primer ciclo?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "¿Cuánto has gastado en guardería o cuidados este año?", "type": "number"},
        ]),
    },
    {
        "code": "CYL-ALQ-VIV",
        "name": "Deducción por alquiler de vivienda habitual (jóvenes y mayores)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 459.0,
        "legal_reference": "Art. 6 DL 1/2013 Castilla y León",
        "description": (
            "15% de las cantidades satisfechas por alquiler de la vivienda habitual, "
            "máx. 459€. Para menores de 36 años o mayores de 65. "
            "BI ≤18.900€ individual o ≤31.500€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Castilla y León?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años o más de 65?", "type": "bool"},
        ]),
    },
    {
        "code": "CYL-DISCAPACIDAD",
        "name": "Deducción por discapacidad del contribuyente o familiares",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 12 DL 1/2013 Castilla y León",
        "description": (
            "300€ por contribuyente o familiar con discapacidad reconocida ≥33% "
            "(500€ si es ≥65%). Se puede aplicar también por cada ascendiente/descendiente "
            "con discapacidad ≥33% que dependa económicamente del contribuyente."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes o tienes a cargo personas con discapacidad reconocida ≥33%?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es el grado de discapacidad?", "type": "text"},
        ]),
    },
    {
        "code": "CYL-INVERSION-VIV",
        "name": "Deducción por inversión en vivienda habitual en municipios en riesgo de despoblación",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 7.5,
        "max_amount": 9.040,
        "legal_reference": "Art. 7 DL 1/2013 Castilla y León",
        "description": (
            "7,5% de las cantidades invertidas en adquisición de vivienda habitual en "
            "municipios de menos de 10.000 habitantes declarados en riesgo de despoblación. "
            "Aplica sobre una base máxima de 9.040€ (incluyendo intereses de hipoteca)."
        ),
        "requirements_json": json.dumps({"vivienda_zona_rural_cyl": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_zona_rural_cyl", "text": "¿Has comprado una vivienda habitual en un municipio de CyL de menos de 10.000 habitantes?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca o inversión en vivienda este año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# CASTILLA-LA MANCHA (Ley 8/2013 y modificaciones posteriores)
# =============================================================================
CASTILLA_LA_MANCHA_2025 = [
    {
        "code": "CLM-NAC-ADOP",
        "name": "Deducción por nacimiento, adopción o acogimiento familiar",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 100.0,
        "legal_reference": "Art. 1 Ley 8/2013 Castilla-La Mancha",
        "description": (
            "100€ por el primer hijo, 500€ por el segundo, 900€ por el tercer hijo y "
            "siguientes. Importes aumentados para familias en municipios de menos de 2.500 hab. "
            "BI ≤27.000€ individual o ≤36.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo, adoptado o acogido este año en Castilla-La Mancha?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes en total?", "type": "number"},
            {"key": "municipio_rural", "text": "¿Vives en un municipio de menos de 2.500 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "CLM-DISCAPACIDAD",
        "name": "Deducción por discapacidad reconocida",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 4 Ley 8/2013 Castilla-La Mancha",
        "description": (
            "300€ para contribuyentes con discapacidad reconocida ≥33%. "
            "600€ para contribuyentes con discapacidad reconocida ≥65%. "
            "BI ≤27.000€ individual o ≤36.000€ conjunta."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es tu grado de discapacidad? (33-65% o ≥65%)", "type": "text"},
        ]),
    },
    {
        "code": "CLM-GASTOS-EDUC",
        "name": "Deducción por gastos educativos",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 1.000,
        "legal_reference": "Art. 3 Ley 8/2013 Castilla-La Mancha",
        "description": (
            "15% de los gastos de escolaridad, libros de texto y material escolar en "
            "enseñanza obligatoria (Primaria, ESO), máx. 1.000€ por hijo. "
            "Compatible con la deducción por nacimiento."
        ),
        "requirements_json": json.dumps({"gastos_educativos": True}),
        "questions_json": json.dumps([
            {"key": "gastos_educativos", "text": "¿Tienes hijos con gastos de escolaridad, libros o material escolar obligatorio?", "type": "bool"},
            {"key": "importe_gastos_educacion", "text": "¿Cuánto has gastado en material y escolaridad este año?", "type": "number"},
        ]),
    },
    {
        "code": "CLM-ALQ-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 450.0,
        "legal_reference": "Art. 5 Ley 8/2013 Castilla-La Mancha",
        "description": (
            "15% de las cantidades satisfechas por alquiler de vivienda habitual, "
            "máx. 450€. Para menores de 36 años o mayores de 65 años. "
            "BI ≤27.000€ individual o ≤36.000€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Castilla-La Mancha?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años o más de 65?", "type": "bool"},
        ]),
    },
    {
        "code": "CLM-DONATIVO",
        "name": "Deducción por donativos y mecenazgo en Castilla-La Mancha",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 6 Ley 8/2013 Castilla-La Mancha",
        "description": (
            "15% de los donativos efectuados a fundaciones y entidades declaradas de "
            "utilidad pública con domicilio en Castilla-La Mancha. "
            "Límite: 10% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has donado a fundaciones o entidades de utilidad pública de Castilla-La Mancha?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
    {
        "code": "CLM-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 2 Ley 8/2013 Castilla-La Mancha",
        "description": (
            "200€ para familia numerosa de categoría general. "
            "400€ para familia numerosa de categoría especial. "
            "BI ≤36.000€ conjunta."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
        ]),
    },
]


# =============================================================================
# EXTREMADURA (DL 1/2013 — Texto Refundido disposiciones legales Extremadura)
# =============================================================================
EXTREMADURA_2025 = [
    {
        "code": "EXT-VIV-JOV",
        "name": "Deducción por adquisición de vivienda habitual (jóvenes)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 5.0,
        "max_amount": 9.040,
        "legal_reference": "Art. 8 DL 1/2013 Extremadura",
        "description": (
            "3% general / 5% para menores de 36 años del precio de adquisición de "
            "vivienda habitual. Aplica solo a viviendas adquiridas antes del 1/1/2013 "
            "que venían siendo objeto de deducción. Base máxima: 9.040€."
        ),
        "requirements_json": json.dumps({
            "adquisicion_antes_2013": True,
            "deducia_antes_2013": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_antes_2013", "text": "¿Adquiriste tu vivienda habitual antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "deducia_antes_2013", "text": "¿Aplicabas ya la deducción por vivienda antes de 2013?", "type": "bool"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca este año?", "type": "number"},
        ]),
    },
    {
        "code": "EXT-ALQ-VIV",
        "name": "Deducción por alquiler de vivienda habitual (jóvenes extremeños)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 9 DL 1/2013 Extremadura",
        "description": (
            "10% de las cantidades pagadas por alquiler de vivienda habitual, "
            "máx. 300€. Solo para menores de 35 años con BI ≤19.000€ individual "
            "o ≤24.000€ conjunta."
        ),
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
            "menor_35_anos": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Extremadura?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
        ]),
    },
    {
        "code": "EXT-TRAB-DEPEND",
        "name": "Deducción para trabajadores dependientes con discapacidad",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 600.0,
        "legal_reference": "Art. 10 DL 1/2013 Extremadura",
        "description": (
            "600€ para contribuyentes con discapacidad ≥33% con rentas del trabajo "
            "o de actividades económicas. 1.200€ para discapacidad ≥65%. "
            "BI ≤19.000€ individual o ≤24.000€ conjunta."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes discapacidad reconocida ≥33% y trabajas por cuenta ajena o propia?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es tu grado de discapacidad? (33-65% o ≥65%)", "type": "text"},
        ]),
    },
    {
        "code": "EXT-ACOGIMIENTO",
        "name": "Deducción por acogimiento familiar de menores",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 250.0,
        "legal_reference": "Art. 6 DL 1/2013 Extremadura",
        "description": (
            "250€ por cada menor acogido en régimen de acogimiento familiar "
            "durante al menos 183 días del período impositivo. "
            "BI ≤19.000€ individual o ≤24.000€ conjunta."
        ),
        "requirements_json": json.dumps({"acogimiento_familiar": True}),
        "questions_json": json.dumps([
            {"key": "acogimiento_familiar", "text": "¿Tienes menores acogidos en régimen de acogimiento familiar?", "type": "bool"},
            {"key": "num_acogidos", "text": "¿Cuántos menores tienes acogidos?", "type": "number"},
        ]),
    },
    {
        "code": "EXT-FAM-NUM",
        "name": "Deducción por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 7 DL 1/2013 Extremadura",
        "description": (
            "200€ para familia numerosa de categoría general. "
            "300€ para familia numerosa de categoría especial. "
            "BI ≤24.000€ conjunta."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
        ]),
    },
    {
        "code": "EXT-DONATIVO",
        "name": "Deducción por donaciones para la conservación del patrimonio extremeño",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 12 DL 1/2013 Extremadura",
        "description": (
            "15% de los donativos a la Junta de Extremadura, ayuntamientos o entidades "
            "sin ánimo de lucro dedicadas a la conservación del patrimonio natural y cultural "
            "extremeño. Límite: 10% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has donado a entidades extremeñas para conservación del patrimonio?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
]


# =============================================================================
# MURCIA (DL 1/2010 — Texto Refundido Ley de Hacienda Murcia, mod. Ley 4/2024)
# =============================================================================
MURCIA_2025 = [
    {
        "code": "MUR-GUARDERIA",
        "name": "Deducción por gastos de guardería y primer ciclo de educación infantil",
        "type": "deduccion",
        "category": "familia",
        "percentage": 15.0,
        "max_amount": 1.000,
        "legal_reference": "Art. 5 DL 1/2010 Murcia",
        "description": (
            "15% de los gastos de guardería y primer ciclo de educación infantil "
            "para hijos menores de 3 años, máx. 1.000€ por hijo. "
            "Ambos progenitores deben tener ingresos del trabajo. "
            "BI ≤30.000€ individual o ≤45.000€ conjunta."
        ),
        "requirements_json": json.dumps({
            "hijo_menor_3": True,
            "guarderia_autorizada": True,
        }),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "¿Tienes hijos menores de 3 años en guardería o centro de educación infantil?", "type": "bool"},
            {"key": "guarderia_autorizada", "text": "¿La guardería está autorizada por la Consejería de Educación?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "¿Cuánto has pagado de guardería este año?", "type": "number"},
        ]),
    },
    {
        "code": "MUR-VIV-JOV",
        "name": "Deducción por inversión en vivienda habitual (jóvenes)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 3.0,
        "max_amount": 9.040,
        "legal_reference": "Art. 3 DL 1/2010 Murcia",
        "description": (
            "3% de tramo autonómico por adquisición de vivienda habitual, ampliado a "
            "3,5% para menores de 35 años o discapacitados ≥65%. "
            "Solo aplicable a adquisiciones anteriores a 1/1/2013 con deducción previa."
        ),
        "requirements_json": json.dumps({
            "adquisicion_antes_2013": True,
            "deducia_antes_2013": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_antes_2013", "text": "¿Adquiriste tu vivienda habitual antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "deducia_antes_2013", "text": "¿Aplicabas ya la deducción por vivienda antes de 2013?", "type": "bool"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca este año?", "type": "number"},
        ]),
    },
    {
        "code": "MUR-MEDIOAMBIENTAL",
        "name": "Deducción por inversiones en instalaciones medioambientales",
        "type": "deduccion",
        "category": "medioambiental",
        "percentage": 30.0,
        "max_amount": 1.000,
        "legal_reference": "Art. 7 DL 1/2010 Murcia",
        "description": (
            "30% de las inversiones en instalaciones de depuración, almacenamiento y "
            "aprovechamiento de agua o en paneles solares para autoconsumo en la vivienda "
            "habitual, máx. 1.000€ por período impositivo."
        ),
        "requirements_json": json.dumps({"instalacion_renovable": True}),
        "questions_json": json.dumps([
            {"key": "instalacion_renovable", "text": "¿Has instalado paneles solares, sistemas de depuración de agua u otras instalaciones medioambientales?", "type": "bool"},
            {"key": "importe_instalacion", "text": "¿Cuánto ha costado la instalación?", "type": "number"},
        ]),
    },
    {
        "code": "MUR-NAC-ADOP",
        "name": "Deducción por nacimiento o adopción de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 4 DL 1/2010 Murcia",
        "description": (
            "100€ por el primer hijo nacido o adoptado, 200€ por el segundo, "
            "300€ por el tercero y siguientes. La deducción se incrementa en un 50% "
            "para familias monoparentales. BI ≤30.000€ individual o ≤45.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año en Murcia?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes en total?", "type": "number"},
            {"key": "familia_monoparental", "text": "¿Eres familia monoparental?", "type": "bool"},
        ]),
    },
    {
        "code": "MUR-DISCAPACIDAD",
        "name": "Deducción por discapacidad del contribuyente",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 100.0,
        "legal_reference": "Art. 6 DL 1/2010 Murcia",
        "description": (
            "100€ para contribuyentes con discapacidad ≥33%. "
            "300€ para contribuyentes con discapacidad ≥65%."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es tu grado de discapacidad? (33-65% o ≥65%)", "type": "text"},
        ]),
    },
    {
        "code": "MUR-DONATIVOS",
        "name": "Deducción por donativos para fines culturales, deportivos y de investigación",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 30.0,
        "max_amount": None,
        "legal_reference": "Art. 8 DL 1/2010 Murcia",
        "description": (
            "30% de los donativos a entidades de la Región de Murcia para fines culturales, "
            "deportivos, de investigación o asistenciales. Límite: 15% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has donado a entidades de la Región de Murcia para fines culturales, deportivos o de investigación?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
]


# =============================================================================
# ISLAS BALEARES (DL 1/2014 — Texto Refundido disposiciones legales Baleares)
# =============================================================================
BALEARES_2025 = [
    {
        "code": "BAL-GASTOS-ESTUDIOS",
        "name": "Deducción por gastos de estudios en educación no universitaria",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 100.0,
        "legal_reference": "Art. 4 DL 1/2014 Baleares",
        "description": (
            "15% de los gastos de escolaridad en centros concertados o privados de "
            "enseñanza no universitaria, máx. 100€ por hijo. "
            "Compatible con otras deducciones por hijos."
        ),
        "requirements_json": json.dumps({"gastos_educativos": True}),
        "questions_json": json.dumps([
            {"key": "gastos_educativos", "text": "¿Tienes hijos en centros de enseñanza concertados o privados?", "type": "bool"},
            {"key": "importe_gastos_educacion", "text": "¿Cuánto has pagado de escolaridad en centros privados o concertados?", "type": "number"},
        ]),
    },
    {
        "code": "BAL-MEJORA-SOSTENIB",
        "name": "Deducción por mejoras de sostenibilidad en la vivienda habitual",
        "type": "deduccion",
        "category": "medioambiental",
        "percentage": 50.0,
        "max_amount": 600.0,
        "legal_reference": "Art. 6 DL 1/2014 Baleares",
        "description": (
            "50% de las cantidades invertidas en mejoras de sostenibilidad de la vivienda "
            "habitual (eficiencia energética, energías renovables), máx. 600€ por año. "
            "Debe acreditarse mejora en calificación energética."
        ),
        "requirements_json": json.dumps({"obras_mejora_energetica": True}),
        "questions_json": json.dumps([
            {"key": "obras_mejora_energetica", "text": "¿Has realizado obras de mejora de eficiencia energética o instalado renovables en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_obras", "text": "¿Cuánto has invertido en las mejoras de sostenibilidad?", "type": "number"},
        ]),
    },
    {
        "code": "BAL-ALQ-VIV",
        "name": "Deducción por alquiler de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 500.0,
        "legal_reference": "Art. 3 DL 1/2014 Baleares",
        "description": (
            "15% de las cantidades satisfechas por arrendamiento de la vivienda habitual, "
            "máx. 500€ (700€ para menores de 36 años o discapacitados). "
            "BI ≤24.000€ individual o ≤38.000€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Baleares?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_36_anos", "text": "¿Tienes menos de 36 años?", "type": "bool"},
        ]),
    },
    {
        "code": "BAL-NAC-ADOP",
        "name": "Deducción por nacimiento o adopción (familias numerosas y monoparentales)",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 500.0,
        "legal_reference": "Art. 5 DL 1/2014 Baleares",
        "description": (
            "500€ por tercer hijo o posteriores (general). "
            "Para familias numerosas de categoría especial o monoparentales: "
            "800€ por cada hijo nacido o adoptado."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año en Baleares?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes en total?", "type": "number"},
            {"key": "familia_numerosa_especial", "text": "¿Eres familia numerosa de categoría especial o familia monoparental?", "type": "bool"},
        ]),
    },
    {
        "code": "BAL-DISCAPACIDAD",
        "name": "Deducción por discapacidad del contribuyente",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 80.0,
        "legal_reference": "Art. 7 DL 1/2014 Baleares",
        "description": (
            "80€ para contribuyentes con discapacidad reconocida ≥33%. "
            "150€ para discapacidad ≥65%."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "¿Tienes algún grado de discapacidad reconocida (≥33%)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "¿Cuál es tu grado de discapacidad? (33-65% o ≥65%)", "type": "text"},
        ]),
    },
    {
        "code": "BAL-DONATIVOS",
        "name": "Deducción por donativos a entidades de las Islas Baleares",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 25.0,
        "max_amount": None,
        "legal_reference": "Art. 8 DL 1/2014 Baleares",
        "description": (
            "25% de los donativos realizados a fundaciones o entidades de las Islas Baleares "
            "declaradas de utilidad pública que desarrollen actividades culturales, "
            "asistenciales, deportivas o similares. Límite: 10% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has donado a fundaciones o entidades declaradas de utilidad pública en Baleares?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
]


# =============================================================================
# ISLAS CANARIAS (DL 1/2009 — Texto Refundido, mod. Ley 4/2024 Canarias)
# =============================================================================
CANARIAS_2025 = [
    {
        "code": "IC-NAC-ADOP",
        "name": "Deducción por nacimiento o adopción de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 6 DL 1/2009 Canarias",
        "description": (
            "200€ por primer hijo; 400€ por segundo; 600€ por tercero y siguientes. "
            "Si el municipio tiene menos de 5.000 habitantes, los importes se duplican. "
            "BI ≤39.000€ individual o ≤52.000€ conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "¿Has tenido un hijo o adoptado este año en Canarias?", "type": "bool"},
            {"key": "num_hijos_total", "text": "¿Cuántos hijos tienes en total?", "type": "number"},
            {"key": "municipio_rural", "text": "¿Vives en un municipio de menos de 5.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "IC-GASTOS-ESTUDIOS",
        "name": "Deducción por gastos de estudios (enseñanza no universitaria y universitaria)",
        "type": "deduccion",
        "category": "educacion",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 8 DL 1/2009 Canarias",
        "description": (
            "Hasta 300€ por descendiente para gastos de libros, material escolar, transporte "
            "y uniformes en enseñanza no universitaria. Hasta 1.800€ por descendiente "
            "en gastos de estudios universitarios fuera de la isla de residencia. "
            "BI ≤39.000€ individual o ≤52.000€ conjunta."
        ),
        "requirements_json": json.dumps({"gastos_educativos": True}),
        "questions_json": json.dumps([
            {"key": "gastos_educativos", "text": "¿Tienes hijos con gastos de libros, material, transporte escolar o estudios fuera de la isla?", "type": "bool"},
            {"key": "importe_gastos_educacion", "text": "¿Cuánto has gastado en total en educación?", "type": "number"},
            {"key": "estudios_fuera_isla", "text": "¿Algún hijo estudia en otra isla o en la Península?", "type": "bool"},
        ]),
    },
    {
        "code": "IC-VIV-HABITUAL",
        "name": "Deducción por inversión en vivienda habitual (jóvenes y régimen especial)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 2.5,
        "max_amount": 9.040,
        "legal_reference": "Art. 5 DL 1/2009 Canarias",
        "description": (
            "Tramo autonómico del 2,5% por inversión en vivienda habitual adquirida "
            "antes del 1/1/2013. Para menores de 35 años: porcentaje ampliado al 3,5%. "
            "Base máxima: 9.040€."
        ),
        "requirements_json": json.dumps({
            "adquisicion_antes_2013": True,
            "deducia_antes_2013": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_antes_2013", "text": "¿Adquiriste tu vivienda habitual antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "deducia_antes_2013", "text": "¿Aplicabas ya la deducción por vivienda antes de 2013?", "type": "bool"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "¿Cuánto has pagado de hipoteca este año?", "type": "number"},
        ]),
    },
    {
        "code": "IC-DONATIVOS",
        "name": "Deducción por donaciones a instituciones canarias",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 20.0,
        "max_amount": None,
        "legal_reference": "Art. 10 DL 1/2009 Canarias",
        "description": (
            "20% de los donativos y aportaciones a fundaciones canarias registradas "
            "y a programas de apoyo a la cultura, ciencia y medio ambiente declarados "
            "de interés social por el Gobierno de Canarias. Límite: 10% de la base liquidable."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "¿Has donado a fundaciones o entidades canarias de interés social?", "type": "bool"},
            {"key": "importe_donativos", "text": "¿Cuánto has donado en total?", "type": "number"},
        ]),
    },
    {
        "code": "IC-ALQ-VIV",
        "name": "Deducción por alquiler de vivienda habitual (Canarias)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 20.0,
        "max_amount": 1.500,
        "legal_reference": "Art. 7 DL 1/2009 Canarias",
        "description": (
            "20% de las cantidades satisfechas por arrendamiento de vivienda habitual, "
            "máx. 1.500€ (2.000€ para menores de 35 años o discapacitados ≥65%). "
            "BI ≤39.000€ individual o ≤52.000€ conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "¿Vives de alquiler en tu vivienda habitual en Canarias?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "¿Cuánto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "¿Tienes menos de 35 años?", "type": "bool"},
        ]),
    },
    {
        "code": "IC-FAM-NUM",
        "name": "Deducción por familia numerosa (Canarias)",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 9 DL 1/2009 Canarias",
        "description": (
            "200€ para familias numerosas de categoría general. "
            "400€ para familias numerosas de categoría especial. "
            "Deducción adicional de 200€ si algún miembro de la unidad familiar tiene discapacidad."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "¿Tienes título de familia numerosa reconocido en Canarias?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "¿Es de categoría especial?", "type": "bool"},
            {"key": "descendiente_discapacidad", "text": "¿Algún miembro de la unidad familiar tiene discapacidad reconocida?", "type": "bool"},
        ]),
    },
]


# =============================================================================
# MAPPING: territory name -> deductions list
# =============================================================================
ALL_TERRITORIAL_V2 = {
    "Galicia": GALICIA_2025,
    "Asturias": ASTURIAS_2025,
    "Cantabria": CANTABRIA_2025,
    "La Rioja": LA_RIOJA_2025,
    "Aragón": ARAGON_2025,
    "Castilla y León": CASTILLA_LEON_2025,
    "Castilla-La Mancha": CASTILLA_LA_MANCHA_2025,
    "Extremadura": EXTREMADURA_2025,
    "Murcia": MURCIA_2025,
    "Islas Baleares": BALEARES_2025,
    "Islas Canarias": CANARIAS_2025,
}


async def seed_territorial_v2():
    """Insert all v2 territorial deductions into the database."""
    from app.database.turso_client import TursoClient

    db = TursoClient()
    await db.connect()

    print("Initializing schema...")
    await db.init_schema()
    print("Schema ready.\n")

    total_inserted = 0
    total_skipped = 0

    for territory, deductions in ALL_TERRITORIAL_V2.items():
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
                # Verify actual insertion (vs IGNORE due to duplicate code)
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

    total_deductions = sum(len(d) for d in ALL_TERRITORIAL_V2.values())
    print(f"\nSeed v2 complete: {total_inserted} inserted, {total_skipped} skipped")
    print(f"Territories covered in this run: {len(ALL_TERRITORIAL_V2)}")
    print(f"Total deductions defined in this script: {total_deductions}")


if __name__ == "__main__":
    asyncio.run(seed_territorial_v2())
