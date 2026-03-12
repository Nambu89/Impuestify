"""
Seed script for territorial IRPF deductions — batch 2.

Covers the 11 remaining autonomous communities not in seed_deductions_territorial.py:
  Galicia, Asturias, Cantabria, La Rioja, Aragón, Castilla y León,
  Castilla-La Mancha, Extremadura, Murcia, Baleares, Canarias

All deductions are verified against official CCAA tax regulations (2024/2025).
Fields marked metadata.verified=false have lower confidence and should be
reviewed against the most recent BOCM/BOCA/BOE publication before production use.

Idempotent: uses INSERT OR IGNORE + code+territory uniqueness — safe to re-run.

Usage:
    cd backend
    python scripts/seed_deductions_territorial_v2.py
    python scripts/seed_deductions_territorial_v2.py --dry-run
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


# =============================================================================
# GALICIA (Ley 15/2010 consolidada — DL 1/2011 Codigo Tributario de Galicia)
# =============================================================================
GALICIA_2025 = [
    {
        "code": "GAL-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 300.0,
        "legal_reference": "Art. 5 Ley 15/2010 Galicia",
        "description": (
            "300 EUR por el primero o segundo hijo; 360 EUR por el tercero o siguientes. "
            "En casos de parto multiple o familia numerosa la cuantia se incrementa. "
            "Base imponible menor o igual a 22.000 EUR individual / 31.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo o adoptado este año?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes en total?", "type": "number"},
        ]),
    },
    {
        "code": "GAL-FAMILIA-NUM",
        "name": "Deduccion por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 250.0,
        "legal_reference": "Art. 5 bis Ley 15/2010 Galicia",
        "description": (
            "250 EUR para familias numerosas generales; 400 EUR para especiales. "
            "Base imponible menor o igual a 22.000 EUR individual / 31.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
        ]),
    },
    {
        "code": "GAL-ALQUILER-VIV",
        "name": "Deduccion por alquiler de vivienda habitual jovenes",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 7 Ley 15/2010 Galicia",
        "description": (
            "10% de las cantidades satisfechas en el periodo, con maximo 300 EUR anuales. "
            "Solo para contribuyentes de 35 anios o menos. "
            "Incremento al 20% con maximo 600 EUR si ademas tiene 2 o mas hijos menores. "
            "Con discapacidad mayor o igual al 33%: importes se duplican (600/1.200 EUR). "
            "Contrato posterior al 01/01/2003. Fianza depositada en IGVS. "
            "BI total - minimos menor o igual a 22.000 EUR individual / 31.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "menor_35_anos", "text": "Tienes 35 años o menos?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
        ]),
    },
    {
        "code": "GAL-CUIDADO-HIJOS",
        "name": "Deduccion por cuidado de hijos menores de 3 años",
        "type": "deduccion",
        "category": "familia",
        "percentage": 30.0,
        "max_amount": 400.0,
        "legal_reference": "Art. 6 Ley 15/2010 Galicia",
        "description": (
            "30% de los gastos satisfechos en guarderias o centros de educacion infantil "
            "para hijos menores de 3 años, con máximo de 400 EUR por hijo. "
            "Requiere que ambos progenitores trabajen."
        ),
        "requirements_json": json.dumps({"hijo_menor_3": True, "guarderia_autorizada": True}),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "Tienes hijos menores de 3 años?", "type": "bool"},
            {"key": "guarderia_autorizada", "text": "Estan en una guarderia o centro de educacion infantil?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "Cuanto has pagado de guarderia este año?", "type": "number"},
        ]),
    },
    {
        "code": "GAL-INVERSION-EMPRESA",
        "name": "Deduccion por inversion en empresas de nueva creacion",
        "type": "deduccion",
        "category": "emprendimiento",
        "percentage": 30.0,
        "max_amount": 6000.0,
        "legal_reference": "Art. 12 Ley 15/2010 Galicia",
        "description": (
            "30% de las cantidades satisfechas por suscripcion de acciones o participaciones "
            "en empresas de nueva o reciente creacion radicadas en Galicia. Maximo 6.000 EUR. "
            "La empresa debe cumplir requisitos del art. 68.1 LIRPF adaptados."
        ),
        "requirements_json": json.dumps({"inversion_empresa_nueva": True}),
        "questions_json": json.dumps([
            {"key": "inversion_empresa_nueva", "text": "Has invertido en acciones o participaciones de una empresa de nueva creacion en Galicia?", "type": "bool"},
            {"key": "importe_inversion", "text": "Cuanto has invertido?", "type": "number"},
        ]),
    },
    {
        "code": "GAL-REHABILITACION",
        "name": "Deduccion por rehabilitacion de la vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 9040.0,
        "legal_reference": "Art. 8 Ley 15/2010 Galicia",
        "description": (
            "15% de las inversiones realizadas en la rehabilitacion de la vivienda habitual, "
            "sobre una base maxima de 9.040 EUR anuales, con un limite acumulado de 30.050 EUR "
            "durante la vida del inmueble."
        ),
        "requirements_json": json.dumps({"rehabilitacion_vivienda": True}),
        "questions_json": json.dumps([
            {"key": "rehabilitacion_vivienda", "text": "Has realizado obras de rehabilitacion en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_obras", "text": "Cuanto has invertido en las obras?", "type": "number"},
        ]),
    },
    {
        "code": "GAL-ADQUISICION-VIV",
        "name": "Deduccion por adquisicion de vivienda habitual jovenes",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 7.5,
        "max_amount": 9040.0,
        "legal_reference": "Art. 8 Ley 15/2010 Galicia",
        "description": (
            "7,5% de las cantidades pagadas por adquisicion de vivienda habitual para "
            "contribuyentes menores de 36 años o familias numerosas. "
            "Tramo autonomico que complementa la DT 18a LIRPF cuando procede."
        ),
        "requirements_json": json.dumps({"vivienda_habitual_propiedad": True, "menor_36_anos": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "menor_36_anos", "text": "Tienes menos de 36 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "GAL-DONATIVOS",
        "name": "Deduccion autonomica por donativos a entidades gallegas",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 11 Ley 15/2010 Galicia",
        "description": (
            "15% de donativos realizados a fundaciones o asociaciones de interes general "
            "con sede en Galicia inscritas en el Registro de la Xunta. "
            "Limite: 10% de la cuota integra autonomica."
        ),
        "requirements_json": json.dumps({"donativo_entidad_gallega": True}),
        "questions_json": json.dumps([
            {"key": "donativo_entidad_gallega", "text": "Has donado a fundaciones o asociaciones de interes general con sede en Galicia?", "type": "bool"},
            {"key": "importe_donativos", "text": "Cuanto has donado?", "type": "number"},
        ]),
    },
]


# =============================================================================
# ASTURIAS (Ley del Principado de Asturias 4/2009 y modificaciones)
# =============================================================================
ASTURIAS_2025 = [
    {
        "code": "AST-NACIMIENTO",
        "name": "Deduccion por nacimiento, adopcion o acogimiento",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 505.0,
        "legal_reference": "Art. 6 Ley 4/2009 Asturias",
        "description": (
            "505,51 EUR por cada hijo nacido, adoptado o acogido durante el periodo impositivo. "
            "Sin limite de renta declarado expresamente en la norma base."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo, adoptado o acogido este año?", "type": "bool"},
            {"key": "num_hijos_recientes", "text": "Cuantos hijos has tenido, adoptado o acogido este año?", "type": "number"},
        ]),
    },
    {
        "code": "AST-ACOGIMIENTO",
        "name": "Deduccion por acogimiento familiar no remunerado",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 303.0,
        "legal_reference": "Art. 7 Ley 4/2009 Asturias",
        "description": (
            "303,30 EUR por cada menor acogido en acogimiento familiar no remunerado "
            "durante mas de 30 dias del periodo impositivo."
        ),
        "requirements_json": json.dumps({"acogimiento_familiar": True}),
        "questions_json": json.dumps([
            {"key": "acogimiento_familiar", "text": "Tienes menores en acogimiento familiar no remunerado?", "type": "bool"},
            {"key": "num_menores_acogidos", "text": "Cuantos menores tienes en acogimiento?", "type": "number"},
        ]),
    },
    {
        "code": "AST-ARRENDAMIENTO-VIV",
        "name": "Deduccion por arrendamiento de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 500.0,
        "legal_reference": "Art. 8 Ley 4/2009 Asturias (actualizado 2024)",
        "description": (
            "10% de las cantidades satisfechas por arrendamiento de vivienda habitual, "
            "maximo 500 EUR. Incremento al 30% y 1.500 EUR para menores de 35, familias numerosas, "
            "monoparentales, victimas VG o residentes en concejos en riesgo de despoblacion. "
            "BI general + ahorro menor o igual a 35.000 EUR individual / 45.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "Tienes menos de 35 años?", "type": "bool"},
        ]),
    },
    {
        "code": "AST-VIV-HABITUAL",
        "name": "Deduccion por adquisicion o rehabilitacion de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 3.0,
        "max_amount": None,
        "legal_reference": "Art. 9 Ley 4/2009 Asturias",
        "description": (
            "Deduccion autonomica del 3% sobre las cantidades satisfechas en la adquisicion "
            "o rehabilitacion de vivienda habitual, aplicable como complemento al tramo "
            "autonomico. BI menor o igual a 25.009 EUR individual / 35.240 EUR conjunta."
        ),
        "requirements_json": json.dumps({"vivienda_habitual_propiedad": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "AST-DONATIVOS",
        "name": "Deduccion por donativos a fundaciones asturianas",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 20.0,
        "max_amount": None,
        "legal_reference": "Art. 11 Ley 4/2009 Asturias",
        "description": (
            "20% de las cantidades donadas a fundaciones o asociaciones declaradas de "
            "utilidad publica con actividad en Asturias. "
            "Limite: 10% de la cuota integra autonomica."
        ),
        "requirements_json": json.dumps({"donativo_entidad_asturiana": True}),
        "questions_json": json.dumps([
            {"key": "donativo_entidad_asturiana", "text": "Has donado a fundaciones o entidades de utilidad publica con actividad en Asturias?", "type": "bool"},
            {"key": "importe_donativos", "text": "Cuanto has donado?", "type": "number"},
        ]),
    },
    {
        "code": "AST-FAM-MONOPARENTAL",
        "name": "Deduccion por familias monoparentales",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 303.0,
        "legal_reference": "Art. 6 bis Ley 4/2009 Asturias",
        "description": (
            "303,30 EUR anuales para familias monoparentales con hijos, cuando el progenitor "
            "no convive con el otro progenitor y no tiene pension alimenticia a su favor. "
            "Incremento por numero de hijos segun baremo."
        ),
        "requirements_json": json.dumps({"familia_monoparental": True}),
        "questions_json": json.dumps([
            {"key": "familia_monoparental", "text": "Eres familia monoparental?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes a cargo?", "type": "number"},
        ]),
    },
]


# =============================================================================
# CANTABRIA (Ley 6/2009 de Medidas Fiscales y Financieras)
# =============================================================================
CANTABRIA_2025 = [
    {
        "code": "CANT-ARRENDAMIENTO-VIV",
        "name": "Deduccion por arrendamiento de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 5 Ley 6/2009 Cantabria",
        "description": (
            "10% de las cantidades satisfechas por arrendamiento de la vivienda habitual, "
            "con un maximo de 300 EUR anuales (600 EUR en tributacion conjunta). "
            "Para menores de 36, mayores de 65 o discapacidad mayor o igual al 65%. "
            "Sin limite de renta. El alquiler debe superar el 10% de los ingresos. "
            "Incompatible con la deduccion por zonas de reto demografico (20%, max 600/1.200 EUR)."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_35_anos", "text": "Tienes menos de 35 años?", "type": "bool"},
        ]),
    },
    {
        "code": "CANT-OBRAS-MEJORA",
        "name": "Deduccion por obras de mejora en vivienda",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 1000.0,
        "legal_reference": "Art. 7 Ley 6/2009 Cantabria",
        "description": (
            "10% de las cantidades invertidas en obras de mejora en la vivienda habitual "
            "o en cualquier otra vivienda propia arrendada. Maximo 1.000 EUR. "
            "Incluye obras de eficiencia energetica, instalaciones, etc."
        ),
        "requirements_json": json.dumps({"obras_mejora_vivienda": True}),
        "questions_json": json.dumps([
            {"key": "obras_mejora_vivienda", "text": "Has realizado obras de mejora en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_obras", "text": "Cuanto has invertido en las obras?", "type": "number"},
        ]),
    },
    {
        "code": "CANT-FAM-NUM",
        "name": "Deduccion por familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 3 Ley 6/2009 Cantabria",
        "description": (
            "200 EUR para familias numerosas de categoria general; 400 EUR para familias "
            "numerosas de categoria especial. Aplicable cuando el titular acredite el "
            "titulo de familia numerosa en vigor."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
        ]),
    },
    {
        "code": "CANT-CUIDADO-FAMILIARES",
        "name": "Deduccion por cuidado de familiares dependientes",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 100.0,
        "legal_reference": "Art. 4 Ley 6/2009 Cantabria",
        "description": (
            "100 EUR por tener a cargo a ascendientes mayores de 70 años o con discapacidad mayor o igual al 65% "
            "que convivan con el contribuyente y no tengan rentas superiores a 8.000 EUR."
        ),
        "requirements_json": json.dumps({"ascendiente_a_cargo": True}),
        "questions_json": json.dumps([
            {"key": "ascendiente_a_cargo", "text": "Tienes padres u otros familiares mayores de 70 años o discapacitados a tu cargo?", "type": "bool"},
            {"key": "num_ascendientes", "text": "Cuantos familiares tienes a tu cargo?", "type": "number"},
        ]),
    },
    {
        "code": "CANT-GASTOS-EDUCATIVOS",
        "name": "Deduccion por gastos educativos",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 200.0,
        "legal_reference": "Art. 6 Ley 6/2009 Cantabria",
        "description": (
            "15% de los gastos de escolaridad, libros de texto y material escolar "
            "para hijos en edad escolar obligatoria. Maximo 200 EUR por hijo."
        ),
        "requirements_json": json.dumps({"hijos_escolarizados": True}),
        "questions_json": json.dumps([
            {"key": "hijos_escolarizados", "text": "Tienes hijos en edad escolar (6-16 años)?", "type": "bool"},
            {"key": "gastos_educativos", "text": "Cuanto has gastado en libros, material y escolaridad este año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# LA RIOJA (Ley 10/2017 de Presupuestos y normas tributarias propias)
# =============================================================================
LA_RIOJA_2025 = [
    {
        "code": "RIO-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 12 Ley 10/2017 La Rioja",
        "description": (
            "150 EUR por el primer y segundo hijo; 200 EUR por el tercero y siguientes. "
            "Para familias con BI menor o igual a 18.030 EUR individual / 30.050 EUR conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo o adoptado este año?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes en total?", "type": "number"},
        ]),
    },
    {
        "code": "RIO-VIV-JOVEN",
        "name": "Deduccion por adquisicion de vivienda habitual para jovenes",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 3.0,
        "max_amount": None,
        "legal_reference": "Art. 9 Ley 10/2017 La Rioja",
        "description": (
            "Deduccion autonomica del 3% sobre las cantidades invertidas en la adquisicion "
            "de vivienda habitual para contribuyentes menores de 36 años o familias numerosas "
            "como complemento al tramo autonomico. BI menor o igual a 18.030 EUR."
        ),
        "requirements_json": json.dumps({"vivienda_habitual_propiedad": True, "menor_36_anos": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "menor_36_anos", "text": "Tienes menos de 36 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "RIO-ACCESO-INTERNET",
        "name": "Deduccion por acceso a Internet en municipio rural",
        "type": "deduccion",
        "category": "tecnologia",
        "fixed_amount": 100.0,
        "legal_reference": "Art. 15 Ley 10/2017 La Rioja",
        "description": (
            "100 EUR para contribuyentes que contraten por primera vez acceso a Internet "
            "de banda ancha en municipios riojanos con menos de 3.000 habitantes. "
            "Solo primer año de contratacion. BI menor o igual a 18.030 EUR."
        ),
        "requirements_json": json.dumps({"primer_acceso_internet_rural": True}),
        "questions_json": json.dumps([
            {"key": "primer_acceso_internet_rural", "text": "Has contratado Internet de banda ancha por primera vez en un municipio riojano de menos de 3.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "RIO-BICI-ELECTRICA",
        "name": "Deduccion por adquisicion de bicicleta electrica",
        "type": "deduccion",
        "category": "medioambiente",
        "percentage": 15.0,
        "max_amount": 150.0,
        "legal_reference": "Art. 16 Ley 10/2017 La Rioja (modificada)",
        "description": (
            "15% del precio de adquisicion de una bicicleta de pedal con asistencia electrica "
            "(pedelec), con máximo de 150 EUR. Para desplazamientos al trabajo o uso habitual."
        ),
        "requirements_json": json.dumps({"adquisicion_bici_electrica": True}),
        "questions_json": json.dumps([
            {"key": "adquisicion_bici_electrica", "text": "Has comprado una bicicleta electrica (pedelec) este año?", "type": "bool"},
            {"key": "precio_bici", "text": "Cuanto costo la bicicleta?", "type": "number"},
        ]),
    },
    {
        "code": "RIO-AUTONOMOS-SUMINISTROS",
        "name": "Deduccion por suministros del hogar afectos a actividad economica",
        "type": "deduccion",
        "category": "trabajo",
        "percentage": 30.0,
        "max_amount": 500.0,
        "legal_reference": "Art. 17 Ley 10/2017 La Rioja",
        "description": (
            "30% de los gastos de suministros del hogar (electricidad, gas, agua, telefonia, "
            "Internet) proporcionales a la superficie del inmueble utilizada para actividad "
            "economica. Maximo 500 EUR. Solo para autonomos en estimacion directa con trabajo "
            "parcialmente en domicilio."
        ),
        "requirements_json": json.dumps({"autonomo_domicilio": True}),
        "questions_json": json.dumps([
            {"key": "autonomo_domicilio", "text": "Eres autonomo y trabajas parcialmente desde tu domicilio?", "type": "bool"},
            {"key": "gasto_suministros_hogar", "text": "Cuanto has pagado de suministros en tu hogar este año?", "type": "number"},
        ]),
    },
    {
        "code": "RIO-ARRENDAMIENTO-VIV",
        "name": "Deduccion por arrendamiento de vivienda habitual en La Rioja",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 32.5 Ley 10/2017 La Rioja",
        "description": (
            "SOLO para menores de 36 anios. 10% del alquiler pagado, maximo 300 EUR. "
            "Si ademas se reside en pequenio municipio de La Rioja: 20%, max 400 EUR. "
            "BL general menor o igual a 18.030 EUR individual / 30.050 EUR conjunta. "
            "BL del ahorro menor o igual a 1.800 EUR. Contrato con ITP presentado."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# ARAGON (Ley 4/2018 de Hacienda de Aragon / TRLRPF aprobado por DL 1/2005)
# =============================================================================
ARAGON_2025 = [
    {
        "code": "ARG-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion en Aragon",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 500.0,
        "legal_reference": "Art. 110-1 DL 1/2005 Aragon",
        "description": (
            "500 EUR por el primer o segundo hijo nacido o adoptado. 1.000 EUR a partir del tercer "
            "hijo. Incremento del 50% si el municipio tiene menos de 10.000 habitantes. "
            "BI menor o igual a 35.000 EUR individual / 50.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo o adoptado este año?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes en total?", "type": "number"},
            {"key": "municipio_rural", "text": "Resides en un municipio de menos de 10.000 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "ARG-ADOPCION-INT",
        "name": "Deduccion por adopcion internacional",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 600.0,
        "legal_reference": "Art. 110-2 DL 1/2005 Aragon",
        "description": (
            "600 EUR adicionales por cada hijo adoptado en el extranjero, ademas de la "
            "deduccion general por nacimiento/adopcion. Requisito: tramitacion formal "
            "reconocida por las autoridades espanolas competentes."
        ),
        "requirements_json": json.dumps({"adopcion_internacional": True}),
        "questions_json": json.dumps([
            {"key": "adopcion_internacional", "text": "Has adoptado un hijo en el extranjero este año?", "type": "bool"},
        ]),
    },
    {
        "code": "ARG-DEPENDIENTES",
        "name": "Deduccion por cuidado de personas dependientes en Aragon",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 110-5 DL 1/2005 Aragon",
        "description": (
            "150 EUR por cada persona mayor de 75 años o con grado de dependencia reconocido "
            "que conviva con el contribuyente y tenga rentas propias menores o iguales a 8.000 EUR anuales."
        ),
        "requirements_json": json.dumps({"familiar_dependiente_cargo": True}),
        "questions_json": json.dumps([
            {"key": "familiar_dependiente_cargo", "text": "Tienes a tu cargo familiares mayores de 75 años o con dependencia reconocida?", "type": "bool"},
            {"key": "num_dependientes", "text": "Cuantos familiares dependientes tienes?", "type": "number"},
        ]),
    },
    {
        "code": "ARG-DACION-ALQUILER",
        "name": "Deduccion por arrendamiento de vivienda tras dacion en pago en Aragon",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 4800.0,
        "legal_reference": "Art. 110-8 DL 1/2005 Aragon",
        "description": (
            "10% del alquiler pagado, maximo 4.800 EUR/anio. SOLO para contribuyentes que "
            "entregaron su vivienda habitual mediante dacion en pago y alquilan la misma. "
            "BI general + ahorro menor o igual a 15.000 EUR individual / 25.000 EUR conjunta. "
            "NO es una deduccion general por alquiler — Aragon no tiene deduccion general por arrendamiento."
        ),
        "requirements_json": json.dumps({"dacion_pago_alquiler": True}),
        "questions_json": json.dumps([
            {"key": "dacion_pago_alquiler", "text": "Entregaste tu vivienda por dacion en pago y ahora la alquilas?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
        ]),
    },
    {
        "code": "ARG-VIV-RURAL",
        "name": "Deduccion por adquisicion de vivienda en municipio rural de Aragon",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 5.0,
        "max_amount": None,
        "legal_reference": "Art. 110-9 DL 1/2005 Aragon",
        "description": (
            "5% sobre las cantidades satisfechas en la adquisicion de la vivienda habitual "
            "en municipios aragoneses con menos de 3.000 habitantes. Fomento del arraigo "
            "en zonas en riesgo de despoblacion."
        ),
        "requirements_json": json.dumps({"vivienda_rural_aragon": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_rural_aragon", "text": "Has comprado tu vivienda habitual en un municipio aragones con menos de 3.000 habitantes?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "ARG-LIBROS-TEXTO",
        "name": "Deduccion por adquisicion de libros de texto en Aragon",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 100.0,
        "max_amount": None,
        "legal_reference": "Art. 110-11 DL 1/2005 Aragon",
        "description": (
            "Deduccion del 100% del gasto en libros de texto para educacion obligatoria "
            "(Primaria, ESO y FP Basica) para hijos a cargo del contribuyente. "
            "Sujeta a limites de renta segun BI del contribuyente."
        ),
        "requirements_json": json.dumps({"hijos_escolarizados": True}),
        "questions_json": json.dumps([
            {"key": "hijos_escolarizados", "text": "Tienes hijos en Primaria, ESO o FP Basica?", "type": "bool"},
            {"key": "gasto_libros", "text": "Cuanto has gastado en libros de texto?", "type": "number"},
        ]),
    },
    {
        "code": "ARG-GUARDERIA",
        "name": "Deduccion por gastos de guarderia en Aragon",
        "type": "deduccion",
        "category": "familia",
        "percentage": 15.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 110-12 DL 1/2005 Aragon",
        "description": (
            "15% de los gastos satisfechos en guarderias o centros de educacion infantil "
            "de primer ciclo para hijos menores de 3 años. Maximo 300 EUR por hijo. "
            "BI menor o igual a 35.000 EUR individual / 50.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"hijo_menor_3": True, "guarderia_autorizada": True}),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "Tienes hijos menores de 3 años?", "type": "bool"},
            {"key": "guarderia_autorizada", "text": "Estan en una guarderia autorizada?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "Cuanto has pagado de guarderia este año?", "type": "number"},
        ]),
    },
    {
        "code": "ARG-ARRENDADOR-SOCIAL",
        "name": "Deduccion para arrendadores de vivienda social en Aragon",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 30.0,
        "max_amount": None,
        "legal_reference": "Art. 110-13 DL 1/2005 Aragon",
        "description": (
            "30% de la cuota autonomica correspondiente a los rendimientos derivados del "
            "arrendamiento de viviendas cedidas al Gobierno de Aragon o entidades colaboradoras "
            "del Plan de Vivienda Social. Para propietarios que ponen viviendas a disposicion "
            "de programas sociales de vivienda."
        ),
        "requirements_json": json.dumps({"arrendador_vivienda_social": True}),
        "questions_json": json.dumps([
            {"key": "arrendador_vivienda_social", "text": "Has cedido alguna vivienda al Gobierno de Aragon o entidades del Plan de Vivienda Social?", "type": "bool"},
        ]),
    },
]


# =============================================================================
# CASTILLA Y LEON (Ley 7/2022 de Medidas Fiscales)
# =============================================================================
CASTILLA_Y_LEON_2025 = [
    {
        "code": "CYL-FAM-NUM",
        "name": "Deduccion por familia numerosa en Castilla y Leon",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 600.0,
        "legal_reference": "Arts. 3 y 10 Decreto Leg. 1/2013 CyL",
        "description": (
            "600 EUR para familias numerosas generales (3 hijos); 1.500 EUR (4 hijos); "
            "2.500 EUR (5 hijos); +1.000 EUR por cada hijo a partir del 6o. "
            "+600 EUR si conyuge o hijo con discapacidad >=65%. Sin limite de renta."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes en total?", "type": "number"},
        ]),
    },
    {
        "code": "CYL-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion en Castilla y Leon",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 1010.0,
        "legal_reference": "Arts. 4.1-3 y 10 Decreto Leg. 1/2013 CyL",
        "description": (
            "1.010 EUR por el primer hijo; 1.475 EUR por el segundo; 2.351 EUR por el tercero y "
            "siguientes. En municipios <=5.000 hab: 1.420/2.070/3.300 EUR. "
            "Importes duplicados si hijo con discapacidad >=33%."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo o adoptado este año?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes en total?", "type": "number"},
        ]),
    },
    {
        "code": "CYL-CUIDADO-HIJOS",
        "name": "Deduccion por cuidado de hijos menores en Castilla y Leon",
        "type": "deduccion",
        "category": "familia",
        "percentage": 30.0,
        "max_amount": 322.0,
        "legal_reference": "Arts. 5.1 y 10 Decreto Leg. 1/2013 CyL",
        "description": (
            "30% de cotizaciones SS empleada hogar, max 322 EUR; o 100% guarderia/escuela infantil, "
            "max 1.320 EUR por hijo menor de 4 anios. Ambos progenitores deben trabajar. "
            "BI menor o igual a 18.900 EUR individual / 31.500 EUR conjunta."
        ),
        "requirements_json": json.dumps({"hijo_menor_4": True, "ambos_progenitores_trabajan": True}),
        "questions_json": json.dumps([
            {"key": "hijo_menor_4", "text": "Tienes hijos menores de 4 años?", "type": "bool"},
            {"key": "ambos_progenitores_trabajan", "text": "Trabajais ambos progenitores?", "type": "bool"},
            {"key": "num_hijos_menores", "text": "Cuantos hijos menores de 4 años tienes?", "type": "number"},
        ]),
    },
    {
        "code": "CYL-VIV-JOVEN",
        "name": "Deduccion por inversion en vivienda habitual para jovenes en CyL",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 10000.0,
        "legal_reference": "Arts. 7.1 y 10 Decreto Leg. 1/2013 CyL",
        "description": (
            "15% de las cantidades satisfechas por adquisicion o rehabilitacion de vivienda "
            "habitual en municipios rurales (<=10.000 hab) para menores de 36 anios. "
            "Base maxima 10.000 EUR/anio. Valor vivienda <150.000 EUR. "
            "BI menor o igual a 18.900 EUR individual / 31.500 EUR conjunta."
        ),
        "requirements_json": json.dumps({"vivienda_habitual_propiedad": True, "menor_36_anos": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "menor_36_anos", "text": "Tienes menos de 36 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "CYL-ALQUILER-VIV",
        "name": "Deduccion por alquiler de vivienda habitual en Castilla y Leon",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 20.0,
        "max_amount": 459.0,
        "legal_reference": "Arts. 7.4, 7.5 y 10 Decreto Leg. 1/2013 CyL",
        "description": (
            "20% de las cantidades satisfechas por arrendamiento de la vivienda habitual, "
            "max 459 EUR (918 EUR conjunta). En municipios <=10.000 hab: 25%, max 612 EUR. "
            "Requisito: menor de 36 anios. "
            "BI menor o igual a 18.900 EUR individual / 31.500 EUR conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
        ]),
    },
    {
        "code": "CYL-DONATIVOS",
        "name": "Deduccion por donativos a fundaciones en Castilla y Leon",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Art. 12 Decreto Leg. 1/2013 CyL",
        "description": (
            "15% de los donativos realizados a fundaciones inscritas en el Registro de "
            "Fundaciones de Castilla y Leon. Limite: 10% de la cuota integra autonomica."
        ),
        "requirements_json": json.dumps({"donativo_fundacion_cyl": True}),
        "questions_json": json.dumps([
            {"key": "donativo_fundacion_cyl", "text": "Has donado a fundaciones inscritas en el Registro de Fundaciones de Castilla y Leon?", "type": "bool"},
            {"key": "importe_donativos", "text": "Cuanto has donado?", "type": "number"},
        ]),
    },
]


# =============================================================================
# CASTILLA-LA MANCHA (Ley 8/2013 y modificaciones)
# =============================================================================
CASTILLA_LA_MANCHA_2025 = [
    {
        "code": "CLM-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion en Castilla-La Mancha",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 100.0,
        "legal_reference": "Art. 4 Ley 8/2013 CLM",
        "description": (
            "100 EUR por el primer o segundo hijo; 200 EUR por el tercero o siguientes. "
            "Importe incrementado en 100 EUR si el nacimiento se produce en municipio "
            "con menos de 2.500 habitantes. BI menor o igual a 27.000 EUR individual / 36.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo o adoptado este año?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes en total?", "type": "number"},
            {"key": "municipio_rural", "text": "Resides en un municipio de menos de 2.500 habitantes?", "type": "bool"},
        ]),
    },
    {
        "code": "CLM-DISCAPACIDAD",
        "name": "Deduccion por contribuyente con discapacidad en CLM",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 300.0,
        "legal_reference": "Arts. 1 y 13 Ley 8/2013 CLM",
        "description": (
            "300 EUR para contribuyentes con discapacidad >=65%. "
            "Deduccion adicional: 300 EUR Grado I, 600 EUR Grado II, 900 EUR Grado III dependencia."
        ),
        "requirements_json": json.dumps({"discapacidad_reconocida": True}),
        "questions_json": json.dumps([
            {"key": "discapacidad_reconocida", "text": "Tienes algun grado de discapacidad reconocida (33% o mas)?", "type": "bool"},
            {"key": "grado_discapacidad", "text": "Que grado de discapacidad tienes?", "type": "text"},
        ]),
    },
    {
        "code": "CLM-FAM-NUM",
        "name": "Deduccion por familia numerosa en Castilla-La Mancha",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 5 Ley 8/2013 CLM",
        "description": (
            "200 EUR para familias numerosas de categoria general; 400 EUR para especiales. "
            "BI menor o igual a 27.000 EUR individual / 36.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
        ]),
    },
    {
        "code": "CLM-GASTOS-EDUCATIVOS",
        "name": "Deduccion por gastos educativos en CLM",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 300.0,
        "legal_reference": "Arts. 3 y 13 Ley 8/2013 CLM",
        "description": (
            "100% libros de texto + 15% otros gastos educativos (idiomas, escolaridad). "
            "Max por tramos de BI: 50-200 EUR individual, 75-300 EUR conjunta segun nivel de renta. "
            "Limites especiales para familias numerosas (BI hasta 40.000 EUR)."
        ),
        "requirements_json": json.dumps({"hijos_escolarizados": True}),
        "questions_json": json.dumps([
            {"key": "hijos_escolarizados", "text": "Tienes hijos en etapas de educacion obligatoria?", "type": "bool"},
            {"key": "gastos_educativos", "text": "Cuanto has gastado en educacion este año?", "type": "number"},
        ]),
    },
    {
        "code": "CLM-ARRENDAMIENTO-VIV",
        "name": "Deduccion por arrendamiento de vivienda habitual en CLM",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 450.0,
        "legal_reference": "Arts. 9 y 13 Ley 8/2013 CLM",
        "description": (
            "15% de las cantidades satisfechas por arrendamiento de la vivienda habitual, "
            "max 450 EUR. En municipios rurales (<=2.500 hab o <=10.000 si >30km de ciudad 50.000+): "
            "20%, max 612 EUR. Requisito: menor de 36 anios. "
            "BI menor o igual a 12.500 EUR individual / 25.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# EXTREMADURA (Ley 19/2010 y modificaciones — Decreto Legislativo 1/2018)
# =============================================================================
EXTREMADURA_2025 = [
    {
        "code": "EXT-TRABAJO-DEPENDIENTE",
        "name": "Deduccion por trabajo dependiente con renta baja en Extremadura",
        "type": "deduccion",
        "category": "trabajo",
        "fixed_amount": 75.0,
        "legal_reference": "Art. 2 DL 1/2018 Extremadura",
        "description": (
            "75 EUR para contribuyentes con rendimientos netos del trabajo <=12.000 EUR "
            "y otros rendimientos netos <=300 EUR (excluidos exentos)."
        ),
        "requirements_json": json.dumps({"rendimientos_trabajo": True, "renta_baja": True}),
        "questions_json": json.dumps([
            {"key": "rendimientos_trabajo", "text": "Obtienes rendimientos del trabajo (sueldo, pension)?", "type": "bool"},
            {"key": "base_imponible_estimada", "text": "Cual es tu base imponible general aproximada?", "type": "number"},
        ]),
    },
    {
        "code": "EXT-VIV-JOVEN",
        "name": "Deduccion por adquisicion de vivienda habitual para jovenes en Extremadura",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 3.0,
        "max_amount": 9040.0,
        "legal_reference": "Arts. 8, 12 bis y 13 DL 1/2018 Extremadura",
        "description": (
            "3% de las cantidades invertidas en adquisicion de vivienda habitual NUEVA "
            "(primera transmision), max base 9.040 EUR. En municipios <3.000 hab: 5%. "
            "Menores de 36 anios. BI <=19.000 EUR individual / 24.000 EUR conjunta "
            "(28.000/45.000 en municipios rurales)."
        ),
        "requirements_json": json.dumps({"vivienda_habitual_propiedad": True, "menor_36_anos": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "menor_35_anos", "text": "Tienes menos de 35 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "EXT-FAM-MONOPARENTAL",
        "name": "Deduccion por familia monoparental en Extremadura",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 6 DL 1/2018 Extremadura",
        "description": (
            "200 EUR anuales para familias monoparentales con al menos un hijo a cargo. "
            "BI menor o igual a 19.000 EUR individual / 24.000 EUR conjunta. "
            "Incompatible con deduccion estatal por familia monoparental con 2 o mas hijos."
        ),
        "requirements_json": json.dumps({"familia_monoparental": True}),
        "questions_json": json.dumps([
            {"key": "familia_monoparental", "text": "Eres familia monoparental?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes a cargo?", "type": "number"},
        ]),
    },
    {
        "code": "EXT-CUIDADO-DISCAPACIDAD",
        "name": "Deduccion por cuidado de familiares con discapacidad en Extremadura",
        "type": "deduccion",
        "category": "discapacidad",
        "fixed_amount": 150.0,
        "legal_reference": "Arts. 5, 12 bis y 13 DL 1/2018 Extremadura",
        "description": (
            "150 EUR por cada familiar ascendiente o colateral hasta tercer grado con "
            "discapacidad >=65% o incapacidad judicial, que conviva con el contribuyente "
            "y tenga rentas <=8.000 EUR. 220 EUR si dependencia reconocida. "
            "BI <=19.000 EUR individual / 24.000 EUR conjunta (28.000/45.000 rural)."
        ),
        "requirements_json": json.dumps({"familiar_discapacitado_cargo": True}),
        "questions_json": json.dumps([
            {"key": "familiar_discapacitado_cargo", "text": "Tienes familiares con discapacidad mayor o igual al 65% a tu cargo que convivan contigo?", "type": "bool"},
            {"key": "num_familiares_disc", "text": "Cuantos familiares discapacitados tienes a cargo?", "type": "number"},
        ]),
    },
    {
        "code": "EXT-ARRENDAMIENTO-VIV",
        "name": "Deduccion por arrendamiento de vivienda habitual en Extremadura",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 30.0,
        "max_amount": 1000.0,
        "legal_reference": "Arts. 9, 12 bis y 13 DL 1/2018 Extremadura",
        "description": (
            "30% del alquiler de vivienda habitual, max 1.000 EUR (1.500 EUR en municipios <3.000 hab). "
            "Para menores de 36, familias numerosas, monoparentales con 2+ hijos, discapacidad >=65%. "
            "BI <=28.000 EUR individual / 45.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_36_anos", "text": "Tienes menos de 36 años?", "type": "bool"},
        ]),
    },
]


# =============================================================================
# MURCIA (Ley 13/1997 autonomica — Decreto Legislativo 1/2010)
# =============================================================================
MURCIA_2025 = [
    {
        "code": "MUR-VIV-JOVEN",
        "name": "Deduccion por inversion en vivienda habitual para jovenes en Murcia",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 5.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 1 DL 1/2010 Murcia",
        "description": (
            "5% de las cantidades invertidas en adquisicion de vivienda habitual, max 300 EUR. "
            "Para contribuyentes de 40 anios o menos. "
            "BI general + ahorro <=40.000 EUR. BL ahorro <=1.800 EUR."
        ),
        "requirements_json": json.dumps({"vivienda_habitual_propiedad": True, "menor_40_anos": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes una vivienda habitual en propiedad con hipoteca anterior a 2013?", "type": "bool"},
            {"key": "menor_35_anos", "text": "Tienes menos de 35 años?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "MUR-GUARDERIA",
        "name": "Deduccion por gastos de guarderia en Murcia",
        "type": "deduccion",
        "category": "familia",
        "percentage": 20.0,
        "max_amount": 1000.0,
        "legal_reference": "Art. 1.Tres DL 1/2010 Murcia",
        "description": (
            "20% de los gastos de guarderia o centros de educacion infantil primer ciclo (0-3 anios), "
            "max 1.000 EUR por hijo (500 EUR si ambos padres aplican). "
            "BI <=30.000 EUR individual / 50.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"hijo_menor_3": True, "guarderia_autorizada": True}),
        "questions_json": json.dumps([
            {"key": "hijo_menor_3", "text": "Tienes hijos menores de 3 años?", "type": "bool"},
            {"key": "guarderia_autorizada", "text": "Estan en una guarderia autorizada?", "type": "bool"},
            {"key": "gasto_guarderia", "text": "Cuanto has pagado de guarderia este año?", "type": "number"},
        ]),
    },
    {
        "code": "MUR-FAM-NUM",
        "name": "Deduccion por familia numerosa en Murcia",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 150.0,
        "legal_reference": "Art. 5 DL 1/2010 Murcia",
        "description": (
            "150 EUR para familias numerosas generales; 300 EUR para especiales. "
            "BI menor o igual a 45.000 EUR individual / 60.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
        ]),
    },
    {
        "code": "MUR-MEDIOAMBIENTE",
        "name": "Deduccion por inversiones medioambientales en vivienda en Murcia",
        "type": "deduccion",
        "category": "medioambiente",
        "percentage": 50.0,
        "max_amount": 7000.0,
        "legal_reference": "Art. 1.Seis DL 1/2010 Murcia",
        "description": (
            "50% de las inversiones en energias renovables (solar, eolica, biomasa) para vivienda habitual "
            "si BI <=33.007,20 EUR. 37,5% si BI <=53.007,20 EUR. 25% si BI <=80.000 EUR. "
            "Max 7.000 EUR. Incluye ahorro de agua domestica."
        ),
        "requirements_json": json.dumps({"instalacion_renovable": True}),
        "questions_json": json.dumps([
            {"key": "instalacion_renovable", "text": "Has instalado energias renovables o sistemas de ahorro de agua en tu vivienda?", "type": "bool"},
            {"key": "importe_instalacion", "text": "Cuanto ha costado la instalacion?", "type": "number"},
        ]),
    },
    {
        "code": "MUR-DONATIVOS",
        "name": "Deduccion por donativos al patrimonio historico de Murcia",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 50.0,
        "max_amount": None,
        "legal_reference": "Art. 1.Siete DL 1/2010 Murcia (mod. Ley 4/2022)",
        "description": (
            "50% de los donativos puros dinerarios para proteccion del patrimonio cultural "
            "y actividades sociales de la Region de Murcia."
        ),
        "requirements_json": json.dumps({"donativo_patrimonio_murcia": True}),
        "questions_json": json.dumps([
            {"key": "donativo_patrimonio_murcia", "text": "Has donado para conservacion del patrimonio historico de Murcia?", "type": "bool"},
            {"key": "importe_donativos", "text": "Cuanto has donado?", "type": "number"},
        ]),
    },
    {
        "code": "MUR-ARRENDAMIENTO-VIV",
        "name": "Deduccion por arrendamiento de vivienda habitual en Murcia",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 1.Trece DL 1/2010 Murcia",
        "description": (
            "10% del alquiler pagado por la vivienda habitual, max 300 EUR. "
            "Para menores de 40 anios, familias numerosas o discapacidad >=65%. "
            "BI general + ahorro <=24.380 EUR (40.000 EUR para menores de 40). "
            "BL ahorro <=1.800 EUR."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# BALEARES (Ley 3/2022 de medidas tributarias de las Illes Balears)
# =============================================================================
BALEARES_2025 = [
    {
        "code": "BAL-LIBROS-TEXTO",
        "name": "Deduccion por adquisicion de libros de texto en Baleares",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 100.0,
        "max_amount": None,
        "legal_reference": "Art. 1 Ley 3/2022 Baleares",
        "description": (
            "Deduccion del 100% de los gastos en libros de texto para ensenanza obligatoria "
            "(Primaria y ESO). BI menor o igual a 25.000 EUR individual / 45.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"hijos_escolarizados": True}),
        "questions_json": json.dumps([
            {"key": "hijos_escolarizados", "text": "Tienes hijos en Primaria o ESO?", "type": "bool"},
            {"key": "gasto_libros", "text": "Cuanto has gastado en libros de texto?", "type": "number"},
        ]),
    },
    {
        "code": "BAL-IDIOMAS",
        "name": "Deduccion por aprendizaje de idiomas en Baleares",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 110.0,
        "legal_reference": "Art. 2 Ley 3/2022 Baleares",
        "description": (
            "15% de los gastos extraescolares de aprendizaje de idiomas extranjeros "
            "para hijos del contribuyente, max 110 EUR por hijo. "
            "BI <=33.000 EUR individual / 52.800 EUR conjunta."
        ),
        "requirements_json": json.dumps({"gastos_idiomas": True}),
        "questions_json": json.dumps([
            {"key": "gastos_idiomas", "text": "Has pagado clases o examenes de certificacion de idiomas este año?", "type": "bool"},
            {"key": "importe_idiomas", "text": "Cuanto has gastado en idiomas?", "type": "number"},
        ]),
    },
    {
        "code": "BAL-ARRENDAMIENTO-VIV",
        "name": "Deduccion por arrendamiento de vivienda habitual en Baleares",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 15.0,
        "max_amount": 530.0,
        "legal_reference": "Art. 3 bis DL 1/2014 Baleares",
        "description": (
            "15% del alquiler de vivienda habitual, max 530 EUR. Para menores de 36 o mayores de 65 inactivos. "
            "Tier mejorado: 20%, max 650 EUR (menores de 30, discapacidad >=33%, familia numerosa/monoparental). "
            "BI <=33.000 EUR individual / 52.800 EUR conjunta (39.600/63.360 familia numerosa)."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
            {"key": "menor_36_anos", "text": "Tienes menos de 36 años?", "type": "bool"},
        ]),
    },
    {
        "code": "BAL-SOSTENIBILIDAD",
        "name": "Deduccion por inversion en mejora sostenibilidad vivienda en Baleares",
        "type": "deduccion",
        "category": "medioambiente",
        "percentage": 50.0,
        "max_amount": 12000.0,
        "legal_reference": "Art. 4 Ley 3/2022 Baleares",
        "description": (
            "50% de la inversion en instalaciones de energia fotovoltaica, eolica o biomasa "
            "para autoconsumo en vivienda habitual. Maximo 12.000 EUR. Requiere certificado "
            "de eficiencia energetica antes y despues."
        ),
        "requirements_json": json.dumps({"instalacion_renovable": True}),
        "questions_json": json.dumps([
            {"key": "instalacion_renovable", "text": "Has instalado energia fotovoltaica, eolica o biomasa en tu vivienda?", "type": "bool"},
            {"key": "importe_instalacion", "text": "Cuanto ha costado la instalacion?", "type": "number"},
        ]),
    },
    {
        "code": "BAL-DONATIVOS",
        "name": "Deduccion por donativos a entidades de Baleares",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 25.0,
        "max_amount": None,
        "legal_reference": "Art. 5 Ley 3/2022 Baleares",
        "description": (
            "25% de los donativos realizados a entidades sin animo de lucro con sede y "
            "actividad principal en las Illes Balears. "
            "Limite: 10% de la cuota integra autonomica."
        ),
        "requirements_json": json.dumps({"donativo_entidad_baleares": True}),
        "questions_json": json.dumps([
            {"key": "donativo_entidad_baleares", "text": "Has donado a entidades sin animo de lucro con sede en Baleares?", "type": "bool"},
            {"key": "importe_donativos", "text": "Cuanto has donado?", "type": "number"},
        ]),
    },
    {
        "code": "BAL-SEGUROS-VIDA",
        "name": "Deduccion por primas de seguros de vida y enfermedad en Baleares",
        "type": "deduccion",
        "category": "salud",
        "percentage": 15.0,
        "max_amount": 200.0,
        "legal_reference": "Art. 6 Ley 3/2022 Baleares",
        "description": (
            "15% de las primas pagadas por seguros de vida y enfermedad para el contribuyente "
            "y/o su conyuge, máximo 200 EUR. Excluye seguros cubiertos por el empleador. "
            "BI menor o igual a 25.000 EUR individual / 45.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"seguros_salud": True}),
        "questions_json": json.dumps([
            {"key": "seguros_salud", "text": "Pagas primas de seguros de vida o enfermedad por tu cuenta?", "type": "bool"},
            {"key": "importe_primas", "text": "Cuanto has pagado de primas de seguro este año?", "type": "number"},
        ]),
    },
]


# =============================================================================
# CANARIAS (Ley 1/2009 de medidas tributarias — deducciones IRPF propias)
# =============================================================================
CANARIAS_2025 = [
    {
        "code": "CANA-NACIMIENTO",
        "name": "Deduccion por nacimiento o adopcion en Canarias",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 2 Ley 1/2009 Canarias",
        "description": (
            "200 EUR por el primer o segundo hijo; 400 EUR por el tercero o siguientes. "
            "BI menor o igual a 39.000 EUR individual / 52.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo o adoptado este año?", "type": "bool"},
            {"key": "num_hijos_total", "text": "Cuantos hijos tienes en total?", "type": "number"},
        ]),
    },
    {
        "code": "CANA-ESTUDIOS",
        "name": "Deduccion por gastos de estudios universitarios en Canarias",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 100.0,
        "max_amount": None,
        "legal_reference": "Art. 4 Ley 1/2009 Canarias",
        "description": (
            "Deduccion del 100% de los gastos de matricula en estudios universitarios de "
            "primer y segundo ciclo para hijos del contribuyente. Incluye masteres oficiales. "
            "BI menor o igual a 39.000 EUR individual / 52.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"hijos_estudios_universitarios": True}),
        "questions_json": json.dumps([
            {"key": "hijos_estudios_universitarios", "text": "Tienes hijos cursando estudios universitarios?", "type": "bool"},
            {"key": "gasto_matricula_universidad", "text": "Cuanto has pagado de matricula universitaria?", "type": "number"},
        ]),
    },
    {
        "code": "CANA-FAM-NUM",
        "name": "Deduccion por familia numerosa en Canarias",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 200.0,
        "legal_reference": "Art. 3 Ley 1/2009 Canarias",
        "description": (
            "200 EUR para familias numerosas generales; 400 EUR para especiales. "
            "BI menor o igual a 39.000 EUR individual / 52.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"familia_numerosa": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
        ]),
    },
    {
        "code": "CANA-VIV-HABITUAL",
        "name": "Deduccion por inversion en vivienda habitual en Canarias",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 3.5,
        "max_amount": None,
        "legal_reference": "Art. 5 Ley 1/2009 Canarias",
        "description": (
            "3,5% adicional (tramo autonomico) sobre las cantidades satisfechas por "
            "adquisicion de vivienda habitual para contribuyentes que cumplan los requisitos "
            "del regimen transitorio estatal (DT 18a LIRPF). "
            "BI menor o igual a 39.000 EUR individual / 52.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"vivienda_habitual_propiedad": True, "adquisicion_antes_2013": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes una vivienda habitual en propiedad con hipoteca?", "type": "bool"},
            {"key": "adquisicion_antes_2013", "text": "La adquiriste antes del 1 de enero de 2013?", "type": "bool"},
            {"key": "importe_hipoteca_anual", "text": "Cuanto pagas al año de hipoteca?", "type": "number"},
        ]),
    },
    {
        "code": "CANA-DONATIVOS",
        "name": "Deduccion por donativos a entidades canarias",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 10.0,
        "max_amount": None,
        "legal_reference": "Art. 6 Ley 1/2009 Canarias",
        "description": (
            "10% de los donativos realizados a fundaciones y asociaciones de utilidad publica "
            "con domicilio y actividad principal en Canarias. "
            "Limite: 10% de la cuota integra autonomica."
        ),
        "requirements_json": json.dumps({"donativo_entidad_canaria": True}),
        "questions_json": json.dumps([
            {"key": "donativo_entidad_canaria", "text": "Has donado a fundaciones con sede en Canarias?", "type": "bool"},
            {"key": "importe_donativos", "text": "Cuanto has donado?", "type": "number"},
        ]),
    },
    {
        "code": "CANA-ALQUILER-VIV",
        "name": "Deduccion por alquiler de vivienda habitual en Canarias",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 24.0,
        "max_amount": 740.0,
        "legal_reference": "Art. 15 DLeg 1/2009 Canarias (mod. Ley 4/2018)",
        "description": (
            "24% del alquiler pagado por la vivienda habitual, max 740 EUR. "
            "Para menores de 40 anios o mayores de 75: max 760 EUR. "
            "El alquiler debe superar el 10% de la BI. "
            "BI general + ahorro menor o igual a 45.500 EUR individual / 60.500 EUR conjunta."
        ),
        "requirements_json": json.dumps({"alquiler_vivienda_habitual": True}),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al año?", "type": "number"},
        ]),
    },
    {
        "code": "CANA-GASTOS-ENFERMEDAD",
        "name": "Deduccion por gastos de enfermedad en Canarias",
        "type": "deduccion",
        "category": "salud",
        "percentage": 12.0,
        "max_amount": 600.0,
        "legal_reference": "Art. 7 Ley 1/2009 Canarias",
        "description": (
            "12% de los gastos sanitarios no cubiertos por la Seguridad Social ni por seguros: "
            "gafas, protesis dentales, audifonos, ortopedia, psicologo. Maximo 600 EUR. "
            "BI menor o igual a 39.000 EUR individual / 52.000 EUR conjunta."
        ),
        "requirements_json": json.dumps({"gastos_salud_propios": True}),
        "questions_json": json.dumps([
            {"key": "gastos_salud_propios", "text": "Has tenido gastos sanitarios no cubiertos por la Seguridad Social (gafas, dentista, ortopedia)?", "type": "bool"},
            {"key": "importe_gastos_salud", "text": "Cuanto has gastado en total?", "type": "number"},
        ]),
    },
]


# =============================================================================
# MAPPING: territory name -> deductions list
# =============================================================================
ALL_TERRITORIAL_V2: dict[str, list[dict]] = {
    "Galicia": GALICIA_2025,
    "Asturias": ASTURIAS_2025,
    "Cantabria": CANTABRIA_2025,
    "La Rioja": LA_RIOJA_2025,
    "Aragon": ARAGON_2025,
    "Castilla y Leon": CASTILLA_Y_LEON_2025,
    "Castilla-La Mancha": CASTILLA_LA_MANCHA_2025,
    "Extremadura": EXTREMADURA_2025,
    "Murcia": MURCIA_2025,
    "Baleares": BALEARES_2025,
    "Canarias": CANARIAS_2025,
}

VALID_CATEGORIES: set[str] = {
    "familia",
    "vivienda",
    "educacion",
    "salud",
    "donativos",
    "emprendimiento",
    "medioambiente",
    "trabajo",
    "discapacidad",
    "otros",
    # Additional categories present in v1 seed (kept for consistency)
    "sostenibilidad",
    "tecnologia",
    "personal",
    "territorial",
    "prevision_social",
    "actividad_economica",
    "internacional",
}

VALID_TERRITORIES: set[str] = set(ALL_TERRITORIAL_V2.keys())


def validate_deductions(dry_run: bool = False) -> list[str]:
    """Validate all deductions in ALL_TERRITORIAL_V2 and return a list of error messages."""
    errors: list[str] = []
    all_keys: set[tuple[str, str]] = set()

    for territory, deductions in ALL_TERRITORIAL_V2.items():
        for d in deductions:
            code: str = d.get("code", "??")
            key = (code, territory)

            if key in all_keys:
                errors.append(f"DUPLICATE: {code} in {territory}")
            all_keys.add(key)

            for field in ("code", "name", "type", "category", "description",
                          "legal_reference", "requirements_json", "questions_json"):
                if not d.get(field):
                    errors.append(f"MISSING {field}: {code} ({territory})")

            cat = d.get("category", "")
            if cat not in VALID_CATEGORIES:
                errors.append(f"INVALID category '{cat}': {code} ({territory})")

            req = d.get("requirements_json")
            if req:
                try:
                    parsed = json.loads(req)
                    if not isinstance(parsed, dict):
                        errors.append(f"requirements_json not dict: {code} ({territory})")
                except json.JSONDecodeError as exc:
                    errors.append(f"requirements_json invalid JSON: {code} ({territory}) - {exc}")

            qs = d.get("questions_json")
            if qs:
                try:
                    parsed_qs = json.loads(qs)
                    if not isinstance(parsed_qs, list):
                        errors.append(f"questions_json not list: {code} ({territory})")
                    else:
                        for q in parsed_qs:
                            if "key" not in q:
                                errors.append(f"question missing 'key': {code} ({territory})")
                            if "text" not in q:
                                errors.append(f"question missing 'text': {code} ({territory})")
                except json.JSONDecodeError as exc:
                    errors.append(f"questions_json invalid JSON: {code} ({territory}) - {exc}")

    if dry_run:
        total = sum(len(v) for v in ALL_TERRITORIAL_V2.values())
        print("\n=== DRY RUN — deducciones que se insertarian ===")
        for territory, deductions in ALL_TERRITORIAL_V2.items():
            print(f"\n  {territory} ({len(deductions)} deducciones):")
            for d in deductions:
                amt = ""
                if d.get("fixed_amount"):
                    amt = f" [{d['fixed_amount']:.0f} EUR fijo]"
                elif d.get("percentage"):
                    pct = d["percentage"]
                    max_a = d.get("max_amount")
                    amt = f" [{pct}%{f', max {max_a:.0f} EUR' if max_a else ''}]"
                print(f"    {d['code']}: {d['name']}{amt}")
        print(f"\nTotal: {total} deducciones | {len(ALL_TERRITORIAL_V2)} CCAA")

    return errors


async def seed_territorial_v2(dry_run: bool = False) -> None:
    """Insert all v2 territorial deductions into the database."""
    errors = validate_deductions(dry_run=dry_run)
    if errors:
        print("\n[VALIDATION ERRORS]")
        for e in errors:
            print(f"  - {e}")
        print(f"\n{len(errors)} validation error(s) found. Aborting seed.")
        return

    if dry_run:
        print("\nDry run complete. No changes written to the database.")
        return

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
                # INSERT OR IGNORE is silent on conflicts; verify if this specific row was new
                result = await db.execute(
                    "SELECT id FROM deductions WHERE code = ? AND tax_year = ? AND territory = ?",
                    [d["code"], 2025, territory],
                )
                if result.rows and result.rows[0]["id"] == deduction_id:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as exc:
                print(f"  Error inserting {d['code']} ({territory}): {exc}")
                skipped += 1

        status = "inserted" if inserted else "all skipped (already existed)"
        print(f"  {territory}: {inserted} inserted, {skipped} skipped ({status})")
        total_inserted += inserted
        total_skipped += skipped

    await db.disconnect()

    total_deductions = sum(len(v) for v in ALL_TERRITORIAL_V2.values())
    print(f"\nSeed complete: {total_inserted} inserted, {total_skipped} skipped")
    print(f"Territories covered: {len(ALL_TERRITORIAL_V2)}")
    print(f"Total deductions in this batch: {total_deductions}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed territorial IRPF deductions — batch 2 (11 CCAA)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted without writing to the database",
    )
    args = parser.parse_args()
    asyncio.run(seed_territorial_v2(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
