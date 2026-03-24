"""
Seed script for ALL 23 Madrid IRPF deductions (2025).

Replaces the 7 deductions from seed_deductions_territorial.py with a complete set
of 23 deductions verified against the AEAT manual and DL 1/2010 (Texto Refundido
de las disposiciones legales de la Comunidad de Madrid en materia de tributos
cedidos por el Estado).

Idempotent: DELETE existing Madrid deductions for tax_year 2025, then INSERT.

Usage:
    cd backend
    python scripts/seed_deductions_madrid_2025.py
    python scripts/seed_deductions_madrid_2025.py --dry-run
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

TERRITORY = "Madrid"
TAX_YEAR = 2025

# =============================================================================
# COMUNIDAD DE MADRID — 23 deducciones autonomicas IRPF 2025
# Fuente: DL 1/2010 (Texto Refundido) + AEAT Manual Renta 2025
# =============================================================================

MADRID_2025: list[dict] = [
    # -------------------------------------------------------------------------
    # 1. Nacimiento o adopcion de hijos (Art. 4)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-001",
        "name": "Deduccion por nacimiento o adopcion de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 721.70,
        "legal_reference": "Arts. 4 y 18.1 DL 1/2010 Madrid",
        "description": (
            "721,70 EUR por cada hijo nacido o adoptado (desde 01/01/2023; 600 EUR para "
            "anteriores). Se aplica en el periodo del nacimiento/adopcion y en los dos "
            "siguientes. En parto/adopcion multiple, la cuantia se incrementa en 721,70 EUR "
            "por cada hijo adicional en el primer periodo. "
            "BI general + ahorro <= 30.930 EUR individual / 37.322,20 EUR conjunta; "
            "BI unidad familiar <= 61.860 EUR."
        ),
        "requirements_json": json.dumps({"nacimiento_adopcion_reciente": True}),
        "questions_json": json.dumps([
            {"key": "nacimiento_adopcion_reciente", "text": "Has tenido un hijo o adoptado en los ultimos 3 anos?", "type": "bool"},
            {"key": "num_hijos_recientes", "text": "Cuantos hijos has tenido o adoptado en los ultimos 3 anos?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 2. Adopcion internacional (Art. 5)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-002",
        "name": "Deduccion por adopcion internacional de hijos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 721.70,
        "legal_reference": "Arts. 5 y 18.1 DL 1/2010 Madrid",
        "description": (
            "721,70 EUR por cada hijo adoptado internacionalmente. Compatible con la "
            "deduccion por nacimiento/adopcion. Mismo periodo de aplicacion (ano de "
            "adopcion + 2 siguientes). "
            "BI general + ahorro <= 30.930 EUR individual / 37.322,20 EUR conjunta; "
            "BI unidad familiar <= 61.860 EUR."
        ),
        "requirements_json": json.dumps({"adopcion_internacional": True}),
        "questions_json": json.dumps([
            {"key": "adopcion_internacional", "text": "Has realizado una adopcion internacional en los ultimos 3 anos?", "type": "bool"},
            {"key": "num_adopciones_internacionales", "text": "Cuantas adopciones internacionales has realizado?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 3. Acogimiento familiar de menores (Art. 6)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-003",
        "name": "Deduccion por acogimiento familiar de menores",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 618.60,
        "legal_reference": "Arts. 6 y 18.1, 4.a) DL 1/2010 Madrid",
        "description": (
            "618,60 EUR por el primer menor en acogimiento familiar; 773,25 EUR por el "
            "segundo; 927,90 EUR por el tercero y siguientes. Incluye acogimiento de "
            "urgencia, temporal, permanente y delegacion de guarda preadoptiva. "
            "El menor debe convivir mas de 183 dias en el periodo. "
            "BI <= 26.414,22 EUR individual / 37.322,20 EUR conjunta."
        ),
        "requirements_json": json.dumps({"acogimiento_menores": True}),
        "questions_json": json.dumps([
            {"key": "acogimiento_menores", "text": "Tienes menores en acogimiento familiar?", "type": "bool"},
            {"key": "num_menores_acogidos", "text": "Cuantos menores tienes en acogimiento?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 4. Acogimiento no remunerado de mayores de 65 y/o discapacitados (Art. 7)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-004",
        "name": "Deduccion por acogimiento no remunerado de mayores de 65 o discapacitados",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 1546.50,
        "legal_reference": "Arts. 7 y 18.1, 4.b) DL 1/2010 Madrid",
        "description": (
            "1.546,50 EUR por cada persona mayor de 65 anos y/o con discapacidad >= 33% "
            "acogida sin contraprestacion. Convivencia minima 183 dias. "
            "No aplicable a parentesco hasta 4o grado (consanguinidad o afinidad). "
            "BI <= 26.414,22 EUR individual / 37.322,20 EUR conjunta."
        ),
        "requirements_json": json.dumps({"acogimiento_no_remunerado_65": True}),
        "questions_json": json.dumps([
            {"key": "acogimiento_no_remunerado_65", "text": "Acoges sin contraprestacion a personas mayores de 65 o con discapacidad?", "type": "bool"},
            {"key": "num_personas_acogidas", "text": "Cuantas personas acoges?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 5. Cuidado de ascendientes (Art. 7 bis)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-005",
        "name": "Deduccion por cuidado de ascendientes",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 515.50,
        "legal_reference": "Arts. 7 bis y 18.1 DL 1/2010 Madrid",
        "description": (
            "515,50 EUR por cada ascendiente mayor de 65 anos o con discapacidad >= 33% "
            "que genere derecho al minimo por ascendientes del IRPF."
        ),
        "requirements_json": json.dumps({"ascendiente_a_cargo": True}),
        "questions_json": json.dumps([
            {"key": "ascendiente_a_cargo", "text": "Tienes padres o abuelos a tu cargo mayores de 65 o con discapacidad?", "type": "bool"},
            {"key": "num_ascendientes", "text": "Cuantos ascendientes tienes a tu cargo?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 6. Familias con 2+ descendientes e ingresos reducidos (Art. 7 ter)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-006",
        "name": "Deduccion para familias con 2 o mas descendientes e ingresos reducidos",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 618.60,
        "legal_reference": "Art. 7 ter DL 1/2010 Madrid",
        "description": (
            "10% de la cuota integra autonomica para contribuyentes con 2 o mas "
            "descendientes que generen derecho al minimo por descendientes. "
            "Rendimientos netos del trabajo del contribuyente (casilla [0022]) "
            "no superiores a 24.000 EUR. "
            "BI general + ahorro <= 26.414,22 EUR individual / 37.322,20 EUR conjunta."
        ),
        "percentage": 10.0,
        "requirements_json": json.dumps({
            "dos_o_mas_descendientes": True,
            "rendimientos_trabajo_max_24000": True,
        }),
        "questions_json": json.dumps([
            {"key": "dos_o_mas_descendientes", "text": "Tienes 2 o mas hijos que generen derecho al minimo por descendientes?", "type": "bool"},
            {"key": "rendimientos_netos_trabajo", "text": "Cuales son tus rendimientos netos del trabajo (casilla 0022)?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 7. Obtencion de la condicion de familia numerosa (Art. 7 quater)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-007",
        "name": "Deduccion por obtencion de la condicion de familia numerosa",
        "type": "deduccion",
        "category": "familia",
        "fixed_amount": 618.60,
        "legal_reference": "Art. 7 quater DL 1/2010 Madrid",
        "description": (
            "618,60 EUR para familia numerosa de categoria general; 927,90 EUR para "
            "categoria especial. Solo aplicable en el periodo en que se obtiene "
            "el titulo de familia numerosa (no en periodos posteriores). "
            "BI general + ahorro <= 30.930 EUR individual / 37.322,20 EUR conjunta; "
            "BI unidad familiar <= 61.860 EUR."
        ),
        "requirements_json": json.dumps({"familia_numerosa_nueva": True}),
        "questions_json": json.dumps([
            {"key": "familia_numerosa_nueva", "text": "Has obtenido el titulo de familia numerosa este ano?", "type": "bool"},
            {"key": "familia_numerosa_especial", "text": "Es de categoria especial?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 8. Arrendamiento de vivienda habitual — inquilino (Art. 8)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-001",
        "name": "Deduccion por arrendamiento de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 30.0,
        "max_amount": 1237.20,
        "legal_reference": "Arts. 8 y 18.1, 4.c) DL 1/2010 Madrid",
        "description": (
            "30% del alquiler de la vivienda habitual, maximo 1.237,20 EUR. "
            "Solo para menores de 40 anos a fecha de devengo. "
            "El alquiler debe superar el 20% de la BI general + ahorro. "
            "BI <= 26.414,22 EUR individual / 37.322,20 EUR conjunta; "
            "BI unidad familiar <= 61.860 EUR. "
            "Requiere copia del deposito de fianza en IVIMA."
        ),
        "requirements_json": json.dumps({
            "alquiler_vivienda_habitual": True,
            "menor_40_anos": True,
        }),
        "questions_json": json.dumps([
            {"key": "alquiler_vivienda_habitual", "text": "Vives de alquiler en tu vivienda habitual?", "type": "bool"},
            {"key": "menor_40_anos", "text": "Tienes menos de 40 anos?", "type": "bool"},
            {"key": "importe_alquiler_anual", "text": "Cuanto pagas de alquiler al ano?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 9. Gastos derivados del arrendamiento de viviendas — arrendador (Art. 8 bis)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-002",
        "name": "Deduccion por gastos derivados del arrendamiento de viviendas",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 154.65,
        "legal_reference": "Arts. 8 bis y 18.4.c) DL 1/2010 Madrid",
        "description": (
            "10% de los gastos de conservacion/reparacion, formalizacion del contrato, "
            "seguros de danos e impagos, y certificacion energetica de viviendas "
            "arrendadas como vivienda. Maximo 154,65 EUR. "
            "Compatible con la deduccion por arrendamiento de viviendas desocupadas. "
            "Requiere deposito de fianza en IVIMA."
        ),
        "requirements_json": json.dumps({"arrendador_vivienda": True}),
        "questions_json": json.dumps([
            {"key": "arrendador_vivienda", "text": "Eres propietario de una vivienda que tienes alquilada como vivienda?", "type": "bool"},
            {"key": "gastos_arrendamiento", "text": "Cuanto has gastado en conservacion, seguros y certificacion energetica?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 10. Arrendamiento de viviendas vacias (Art. 8 ter)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-003",
        "name": "Deduccion por arrendamiento de viviendas desocupadas",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": None,
        "fixed_amount": 154.65,
        "legal_reference": "Art. 8 ter DL 1/2010 Madrid",
        "description": (
            "154,65 EUR por poner en alquiler una vivienda que llevaba al menos "
            "1 ano desocupada. Requiere certificado IVIMA de fianza y vigencia "
            "minima del contrato de 1 ano. Compatible con la deduccion Art. 8 bis."
        ),
        "requirements_json": json.dumps({"vivienda_desocupada_alquilada": True}),
        "questions_json": json.dumps([
            {"key": "vivienda_desocupada_alquilada", "text": "Has puesto en alquiler una vivienda que llevaba mas de 1 ano vacia?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 11. Incremento de costes de financiacion por subida de tipos (Art. 8 quater)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-004",
        "name": "Deduccion por incremento de costes de financiacion de vivienda habitual",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 25.0,
        "max_amount": 300.0,
        "legal_reference": "Art. 8 quater DL 1/2010 Madrid",
        "description": (
            "25% del incremento de intereses de prestamo hipotecario a tipo variable "
            "para vivienda habitual respecto al periodo anterior, maximo 300 EUR. "
            "Prestamo constituido antes del 01/01/2024. "
            "BI general + ahorro <= 30.930 EUR individual / 37.322,20 EUR conjunta."
        ),
        "requirements_json": json.dumps({"hipoteca_variable_vivienda": True}),
        "questions_json": json.dumps([
            {"key": "hipoteca_variable_vivienda", "text": "Tienes hipoteca a tipo variable sobre tu vivienda habitual?", "type": "bool"},
            {"key": "incremento_intereses", "text": "Cuanto han aumentado tus intereses hipotecarios respecto al ano anterior?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 12. Cambio de residencia a municipio en riesgo de despoblamiento (Art. 10 bis)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-005",
        "name": "Deduccion por cambio de residencia a municipio en riesgo de despoblamiento",
        "type": "deduccion",
        "category": "vivienda",
        "fixed_amount": 1031.0,
        "legal_reference": "Art. 10 bis DL 1/2010 Madrid",
        "description": (
            "1.031 EUR en el periodo del cambio de residencia y en los dos siguientes. "
            "El municipio debe estar en la lista oficial de municipios en riesgo de "
            "despoblamiento de la Comunidad de Madrid. "
            "No haber residido en dicho municipio en los 5 anos anteriores. "
            "BI general + ahorro <= 26.414,22 EUR individual / 37.322,20 EUR conjunta."
        ),
        "requirements_json": json.dumps({"cambio_residencia_despoblamiento": True}),
        "questions_json": json.dumps([
            {"key": "cambio_residencia_despoblamiento", "text": "Te has trasladado a un municipio en riesgo de despoblamiento de Madrid?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 13. Adquisicion de vivienda habitual en municipio despoblamiento (Art. 10 ter)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-006",
        "name": "Deduccion por adquisicion de vivienda en municipio en riesgo de despoblamiento",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 1546.50,
        "legal_reference": "Art. 10 ter DL 1/2010 Madrid",
        "description": (
            "10% del precio de adquisicion de vivienda habitual en municipio en riesgo "
            "de despoblamiento, maximo 1.546,50 EUR anuales, durante 10 anos (ano de "
            "adquisicion + 9 siguientes). Adquisicion desde 01/01/2021. "
            "Ocupacion efectiva en 12 meses, permanencia minima 3 anos. "
            "BI <= 26.414,22 EUR individual / 37.322,20 EUR conjunta."
        ),
        "requirements_json": json.dumps({"adquisicion_vivienda_despoblamiento": True}),
        "questions_json": json.dumps([
            {"key": "adquisicion_vivienda_despoblamiento", "text": "Has comprado vivienda en un municipio en riesgo de despoblamiento de Madrid?", "type": "bool"},
            {"key": "precio_adquisicion", "text": "Cual fue el precio de adquisicion de la vivienda?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 14. Pago de intereses de prestamos para vivienda habitual jovenes < 30 (Art. 12)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-007",
        "name": "Deduccion por intereses de prestamo para adquisicion de vivienda habitual (menores de 30)",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 25.0,
        "max_amount": 1031.0,
        "legal_reference": "Art. 12 DL 1/2010 Madrid",
        "description": (
            "25% de los intereses satisfechos por prestamos para adquisicion de "
            "vivienda habitual, maximo 1.031 EUR. Solo para menores de 30 anos "
            "a fecha de devengo. Prestamo constituido desde 01/01/2024. "
            "BI general + ahorro <= 26.414,22 EUR individual / 37.322,20 EUR conjunta; "
            "BI unidad familiar <= 61.860 EUR."
        ),
        "requirements_json": json.dumps({
            "vivienda_habitual_propiedad": True,
            "menor_30_anos": True,
        }),
        "questions_json": json.dumps([
            {"key": "vivienda_habitual_propiedad", "text": "Tienes vivienda habitual en propiedad con prestamo?", "type": "bool"},
            {"key": "menor_30_anos", "text": "Tienes menos de 30 anos?", "type": "bool"},
            {"key": "intereses_prestamo_vivienda", "text": "Cuanto has pagado de intereses del prestamo este ano?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 15. Adquisicion de vivienda habitual por nacimiento/adopcion (Art. 13)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-VIV-008",
        "name": "Deduccion por adquisicion de vivienda habitual por nacimiento o adopcion",
        "type": "deduccion",
        "category": "vivienda",
        "percentage": 10.0,
        "max_amount": 1546.50,
        "legal_reference": "Arts. 13 y 18.2 DL 1/2010 Madrid",
        "description": (
            "10% del precio de adquisicion de vivienda habitual adquirida dentro de "
            "los 3 anos siguientes al nacimiento/adopcion de un hijo, maximo "
            "1.546,50 EUR anuales, durante 10 anos. Adquisicion desde 01/01/2023. "
            "Ocupacion efectiva en 12 meses, permanencia minima 3 anos. "
            "BI <= 30.930 EUR x numero de miembros de la unidad familiar."
        ),
        "requirements_json": json.dumps({
            "adquisicion_vivienda_por_hijo": True,
            "nacimiento_adopcion_reciente": True,
        }),
        "questions_json": json.dumps([
            {"key": "adquisicion_vivienda_por_hijo", "text": "Has comprado vivienda tras el nacimiento o adopcion de un hijo (en los ultimos 3 anos)?", "type": "bool"},
            {"key": "precio_adquisicion_vivienda", "text": "Cual fue el precio de adquisicion?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 16. Gastos educativos (Art. 11)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-EDU-001",
        "name": "Deduccion por gastos educativos",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 15.0,
        "max_amount": 927.90,
        "legal_reference": "Arts. 11 y 18.2, 4.d) DL 1/2010 Madrid",
        "description": (
            "15% de escolaridad (max 927,90 EUR/hijo; 1.031 EUR para primer ciclo "
            "infantil 0-3 anos). 15% de ensenanza de idiomas (max 412,40 EUR/hijo). "
            "5% de vestuario escolar (combinado con idiomas max 412,40 EUR). "
            "No incluye comedor, transporte ni libros. "
            "BI general + ahorro <= 30.930 EUR x numero de miembros de la unidad familiar."
        ),
        "requirements_json": json.dumps({"gastos_educativos": True}),
        "questions_json": json.dumps([
            {"key": "gastos_educativos", "text": "Tienes gastos de escolaridad, idiomas o uniformes de tus hijos?", "type": "bool"},
            {"key": "importe_escolaridad", "text": "Cuanto has pagado de escolaridad privada (no concertada)?", "type": "number"},
            {"key": "importe_idiomas", "text": "Cuanto has pagado en ensenanza de idiomas?", "type": "number"},
            {"key": "importe_uniformes", "text": "Cuanto has pagado en uniformes escolares?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 17. Cuidado de hijos < 3, mayores dependientes, discapacitados (Art. 11 bis)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-FAM-008",
        "name": "Deduccion por cuidado de hijos menores de 3 anos, mayores dependientes y discapacitados",
        "type": "deduccion",
        "category": "familia",
        "percentage": 25.0,
        "max_amount": 463.95,
        "legal_reference": "Arts. 11 bis y 18.2, 4.e) DL 1/2010 Madrid",
        "description": (
            "25% de las cotizaciones a la Seguridad Social del empleado del hogar, "
            "maximo 463,95 EUR. Familia numerosa: 40%, maximo 618,60 EUR. "
            "Aplica para cuidado de hijos < 3, ascendientes >= 65 o discapacitados >= 33%."
        ),
        "requirements_json": json.dumps({"empleada_hogar_cuidado": True}),
        "questions_json": json.dumps([
            {"key": "empleada_hogar_cuidado", "text": "Tienes contratada a una persona del hogar para cuidado de hijos < 3 o dependientes?", "type": "bool"},
            {"key": "cotizaciones_ss_hogar", "text": "Cuanto pagas en cotizaciones a la SS por el empleado del hogar al ano?", "type": "number"},
            {"key": "familia_numerosa", "text": "Tienes titulo de familia numerosa?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 18. Pago de intereses de prestamos estudios (Art. 11 ter)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-EDU-002",
        "name": "Deduccion por intereses de prestamos para estudios de grado, master y doctorado",
        "type": "deduccion",
        "category": "educacion",
        "percentage": 25.0,
        "max_amount": 1031.0,
        "legal_reference": "Art. 11 ter DL 1/2010 Madrid",
        "description": (
            "25% de los intereses satisfechos en el periodo por prestamos concedidos "
            "para financiar estudios de Grado, Master o Doctorado, maximo 1.031 EUR. "
            "El prestamo debe haberse formalizado para dicha finalidad. "
            "BI general + ahorro <= 30.930 EUR individual / 37.322,20 EUR conjunta."
        ),
        "requirements_json": json.dumps({"prestamo_estudios": True}),
        "questions_json": json.dumps([
            {"key": "prestamo_estudios", "text": "Tienes un prestamo para financiar estudios de Grado, Master o Doctorado?", "type": "bool"},
            {"key": "intereses_prestamo_estudios", "text": "Cuanto has pagado de intereses del prestamo de estudios este ano?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 19. Donativos a fundaciones y clubes deportivos (Art. 9)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-DON-001",
        "name": "Deduccion por donativos a fundaciones y clubes deportivos",
        "type": "deduccion",
        "category": "donativos",
        "percentage": 15.0,
        "max_amount": None,
        "legal_reference": "Arts. 9 y 18.3 DL 1/2010 Madrid",
        "description": (
            "15% de las donaciones a fundaciones inscritas en el Registro de "
            "Fundaciones de la Comunidad de Madrid y a clubes deportivos elementales "
            "y basicos inscritos en el Registro de Asociaciones Deportivas. "
            "Limite: 10% de la base liquidable (general + ahorro)."
        ),
        "requirements_json": json.dumps({"donativo_a_entidad_acogida": True}),
        "questions_json": json.dumps([
            {"key": "donativo_a_entidad_acogida", "text": "Has hecho donativos a fundaciones o clubes deportivos inscritos en la CM de Madrid?", "type": "bool"},
            {"key": "importe_donativos", "text": "Cuanto has donado en total?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 20. Inversion en entidades de nueva o reciente creacion (Art. 15)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-INV-001",
        "name": "Deduccion por inversion en entidades de nueva o reciente creacion",
        "type": "deduccion",
        "category": "emprendimiento",
        "percentage": 30.0,
        "max_amount": 6000.0,
        "legal_reference": "Art. 15 DL 1/2010 Madrid",
        "description": (
            "30% de las cantidades invertidas en la suscripcion de acciones o "
            "participaciones de entidades de nueva o reciente creacion (menos de "
            "3 anos), maximo 6.000 EUR. La entidad debe tener domicilio social "
            "y fiscal en la CM de Madrid. Participacion maxima del 40%. "
            "Mantenimiento minimo 3 anos."
        ),
        "requirements_json": json.dumps({"inversion_empresa_nueva": True}),
        "questions_json": json.dumps([
            {"key": "inversion_empresa_nueva", "text": "Has invertido en acciones o participaciones de una empresa de nueva creacion en Madrid?", "type": "bool"},
            {"key": "importe_inversion", "text": "Cuanto has invertido?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 21. Inversiones en entidades cotizadas en el MAB (Art. 15 bis)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-INV-002",
        "name": "Deduccion por inversiones en entidades cotizadas en el Mercado Alternativo Bursatil",
        "type": "deduccion",
        "category": "emprendimiento",
        "percentage": 20.0,
        "max_amount": 10000.0,
        "legal_reference": "Art. 15 bis DL 1/2010 Madrid",
        "description": (
            "20% de las cantidades invertidas en la adquisicion de acciones como "
            "consecuencia de acuerdos de ampliacion de capital de empresas cotizadas "
            "en el MAB (ahora BME Growth), maximo 10.000 EUR. "
            "Mantenimiento minimo 2 anos. Participacion maxima 10%. "
            "Solo acciones adquiridas en ampliaciones de capital."
        ),
        "requirements_json": json.dumps({"inversion_mab": True}),
        "questions_json": json.dumps([
            {"key": "inversion_mab", "text": "Has invertido en ampliaciones de capital de empresas del BME Growth (antiguo MAB)?", "type": "bool"},
            {"key": "importe_inversion_mab", "text": "Cuanto has invertido?", "type": "number"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 22. Fomento del autoempleo de jovenes menores de 35 (Art. 16)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-LAB-001",
        "name": "Deduccion por fomento del autoempleo de jovenes menores de 35 anos",
        "type": "deduccion",
        "category": "trabajo",
        "fixed_amount": 1031.0,
        "legal_reference": "Art. 16 DL 1/2010 Madrid",
        "description": (
            "1.031 EUR para contribuyentes menores de 35 anos que se den de alta "
            "por primera vez como autonomos o socios de una entidad en atribucion "
            "de rentas en el Censo de Empresarios. "
            "Actividad principal en la CM de Madrid. "
            "Permanencia minima de 1 ano desde el alta. "
            "Se aplica en el periodo impositivo del alta."
        ),
        "requirements_json": json.dumps({
            "autoempleo_joven": True,
            "menor_35_anos": True,
        }),
        "questions_json": json.dumps([
            {"key": "autoempleo_joven", "text": "Te has dado de alta como autonomo por primera vez este ano?", "type": "bool"},
            {"key": "menor_35_anos", "text": "Tienes menos de 35 anos?", "type": "bool"},
        ]),
    },
    # -------------------------------------------------------------------------
    # 23. Inversiones de nuevos contribuyentes procedentes del extranjero (Art. 17)
    # -------------------------------------------------------------------------
    {
        "code": "MAD-INV-003",
        "name": "Deduccion por inversiones de nuevos contribuyentes procedentes del extranjero",
        "type": "deduccion",
        "category": "emprendimiento",
        "percentage": 20.0,
        "max_amount": 10000.0,
        "legal_reference": "Art. 17 DL 1/2010 Madrid",
        "description": (
            "20% de las cantidades invertidas en acciones o participaciones de "
            "entidades con domicilio social y fiscal en la CM de Madrid, maximo "
            "10.000 EUR. Solo para contribuyentes que adquieran residencia fiscal "
            "en la CM de Madrid procedentes del extranjero (no residentes en "
            "Espana en los 5 anos anteriores). Mantenimiento minimo 6 anos."
        ),
        "requirements_json": json.dumps({"nuevo_contribuyente_extranjero": True}),
        "questions_json": json.dumps([
            {"key": "nuevo_contribuyente_extranjero", "text": "Eres nuevo residente fiscal en Madrid procedente del extranjero?", "type": "bool"},
            {"key": "importe_inversion_extranjero", "text": "Cuanto has invertido en entidades madrilenas?", "type": "number"},
        ]),
    },
]


# =============================================================================
# Validation
# =============================================================================
VALID_CATEGORIES: set[str] = {
    "familia", "vivienda", "educacion", "donativos", "emprendimiento",
    "trabajo", "discapacidad", "salud", "otros",
}


def validate_deductions(dry_run: bool = False) -> list[str]:
    """Validate all deductions and return a list of error messages."""
    errors: list[str] = []
    seen_codes: set[str] = set()

    for d in MADRID_2025:
        code: str = d.get("code", "??")

        if code in seen_codes:
            errors.append(f"DUPLICATE code: {code}")
        seen_codes.add(code)

        for field in ("code", "name", "type", "category", "description",
                      "legal_reference", "requirements_json", "questions_json"):
            if not d.get(field):
                errors.append(f"MISSING {field}: {code}")

        cat = d.get("category", "")
        if cat not in VALID_CATEGORIES:
            errors.append(f"INVALID category '{cat}': {code}")

        req = d.get("requirements_json")
        if req:
            try:
                parsed = json.loads(req)
                if not isinstance(parsed, dict):
                    errors.append(f"requirements_json not dict: {code}")
            except json.JSONDecodeError as exc:
                errors.append(f"requirements_json invalid JSON: {code} - {exc}")

        qs = d.get("questions_json")
        if qs:
            try:
                parsed_qs = json.loads(qs)
                if not isinstance(parsed_qs, list):
                    errors.append(f"questions_json not list: {code}")
                else:
                    for q in parsed_qs:
                        if "key" not in q:
                            errors.append(f"question missing 'key': {code}")
                        if "text" not in q:
                            errors.append(f"question missing 'text': {code}")
            except json.JSONDecodeError as exc:
                errors.append(f"questions_json invalid JSON: {code} - {exc}")

    if dry_run:
        print(f"\n=== DRY RUN — {TERRITORY} deducciones que se insertarian ===\n")
        print(f"  {TERRITORY} ({len(MADRID_2025)} deducciones):")
        for d in MADRID_2025:
            amt = ""
            if d.get("fixed_amount"):
                amt = f" [{d['fixed_amount']:.2f} EUR fijo]"
            elif d.get("percentage"):
                pct = d["percentage"]
                max_a = d.get("max_amount")
                amt = f" [{pct}%{f', max {max_a:.2f} EUR' if max_a else ''}]"
            print(f"    {d['code']}: {d['name']}{amt}")
        print(f"\nTotal: {len(MADRID_2025)} deducciones | Territorio: {TERRITORY}")

    return errors


# =============================================================================
# Seed function
# =============================================================================
async def seed_madrid(dry_run: bool = False) -> None:
    """Delete existing Madrid 2025 deductions and insert the full set of 23."""
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

    # Delete existing Madrid deductions for this tax year (idempotent)
    result = await db.execute(
        "SELECT COUNT(*) as cnt FROM deductions WHERE territory = ? AND tax_year = ?",
        [TERRITORY, TAX_YEAR],
    )
    existing_count = result.rows[0]["cnt"] if result.rows else 0
    print(f"Existing {TERRITORY} deductions for {TAX_YEAR}: {existing_count}")

    if existing_count > 0:
        await db.execute(
            "DELETE FROM deductions WHERE territory = ? AND tax_year = ?",
            [TERRITORY, TAX_YEAR],
        )
        print(f"Deleted {existing_count} existing deductions.")

    # Insert all 23 deductions
    inserted = 0
    for d in MADRID_2025:
        deduction_id = str(uuid.uuid4())
        try:
            await db.execute(
                """INSERT INTO deductions
                   (id, code, tax_year, territory, name, type, category,
                    percentage, max_amount, fixed_amount, legal_reference,
                    description, requirements_json, questions_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    deduction_id,
                    d["code"],
                    TAX_YEAR,
                    TERRITORY,
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
            inserted += 1
        except Exception as exc:
            print(f"  Error inserting {d['code']}: {exc}")

    await db.disconnect()

    print(f"\n{TERRITORY} seed complete: {inserted}/{len(MADRID_2025)} inserted")
    print(f"Deductions: {', '.join(d['code'] for d in MADRID_2025)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"Seed ALL {len(MADRID_2025)} {TERRITORY} IRPF deductions for {TAX_YEAR}"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be inserted without writing to the database",
    )
    args = parser.parse_args()
    asyncio.run(seed_madrid(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
