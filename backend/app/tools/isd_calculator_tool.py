"""
ISD Calculator Tool for TaxIA

Provides function calling capability for the LLM to calculate the
Impuesto sobre Sucesiones y Donaciones (ISD) with CCAA-specific rules.

Covers:
- Donaciones (inter-vivos gifts)
- Sucesiones (inheritances)
- Tarifa estatal (Art. 21 Ley 29/1987)
- Coeficientes multiplicadores por patrimonio preexistente
- Reducciones estatales por parentesco (Arts. 20 y 22 Ley 29/1987)
- Bonificaciones autonómicas: Madrid, Andalucia, Cataluna, Valencia,
  Aragon, Pais Vasco (Araba/Bizkaia/Gipuzkoa), Navarra, Galicia,
  Castilla y Leon, Castilla-La Mancha, Extremadura, Murcia, Canarias,
  Asturias, Cantabria, La Rioja, Baleares, Ceuta, Melilla
"""
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI tool definition
# ---------------------------------------------------------------------------

ISD_CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_isd",
        "description": """SIEMPRE DEBES USAR ESTA FUNCIÓN cuando el usuario pregunte sobre:
- ISD, Impuesto sobre Sucesiones y Donaciones
- Herencia, heredad, recibir una herencia, cuánto se paga por heredar
- Donación, recibir dinero en donación, cuánto se paga por una donación
- "¿Tengo que pagar impuestos si mis padres me dan dinero?"
- "¿Cuánto debo pagar si heredo la casa?"
- Sucesiones, donaciones, plusvalía mortis causa

OBLIGATORIO usar esta función si el usuario menciona:
- Un importe de donación o herencia
- Una CCAA receptora
- Grado de parentesco (padres, hijos, hermanos, etc.)

La función calcula el ISD (estatal + bonificaciones autonómicas) para donaciones
y sucesiones en España, según la Ley 29/1987 y la normativa de cada CCAA.""",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {
                    "type": "number",
                    "description": "Importe de la donación o herencia en euros."
                },
                "operation_type": {
                    "type": "string",
                    "enum": ["donacion", "sucesion"],
                    "description": "Tipo de operación: 'donacion' (inter-vivos) o 'sucesion' (mortis causa)."
                },
                "relationship": {
                    "type": "string",
                    "enum": ["grupo_i", "grupo_ii", "grupo_iii", "grupo_iv"],
                    "description": (
                        "Grupo de parentesco del receptor respecto al donante/causante: "
                        "'grupo_i' = descendientes menores de 21 años; "
                        "'grupo_ii' = descendientes >= 21 años, cónyuge, ascendientes; "
                        "'grupo_iii' = colaterales de 2.º y 3.º grado (hermanos, tíos, sobrinos) y afines; "
                        "'grupo_iv' = colaterales de 4.º grado o más, y extraños."
                    )
                },
                "ccaa": {
                    "type": "string",
                    "description": (
                        "CCAA de residencia del receptor (para sucesiones) "
                        "o CCAA donde radican los bienes inmuebles (para donaciones). "
                        "Ejemplos: 'Madrid', 'Cataluña', 'Andalucía', 'Valencia', 'Aragón', "
                        "'Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra', 'Galicia', "
                        "'Castilla y León', 'Castilla-La Mancha', 'Extremadura', "
                        "'Murcia', 'Canarias', 'Asturias', 'Cantabria', 'La Rioja', "
                        "'Baleares', 'Ceuta', 'Melilla'."
                    )
                },
                "recipient_age": {
                    "type": "integer",
                    "description": "Edad del receptor en años. Necesario para calcular la reducción del Grupo I."
                },
                "donor_age": {
                    "type": "integer",
                    "description": "Edad del donante/causante. Relevante para algunos coeficientes autonómicos."
                },
                "destination": {
                    "type": "string",
                    "enum": ["ninguno", "vivienda_habitual", "empresa_familiar", "explotacion_agraria"],
                    "description": (
                        "Destino del bien heredado/donado: "
                        "'vivienda_habitual' = reducción 95% hasta 122.606,47€ (sucesiones); "
                        "'empresa_familiar' = reducción 95% del valor de la empresa; "
                        "'explotacion_agraria' = reducción 90-100% según normativa."
                    )
                },
                "previous_wealth": {
                    "type": "number",
                    "description": (
                        "Patrimonio preexistente del receptor en euros "
                        "(para determinar el coeficiente multiplicador). "
                        "Si no se conoce, omitir (se aplica el coeficiente más bajo)."
                    )
                },
                "disability": {
                    "type": "integer",
                    "enum": [0, 33, 65],
                    "description": (
                        "Grado de discapacidad del receptor en porcentaje: "
                        "0 = sin discapacidad; 33 = >= 33%; 65 = >= 65%. "
                        "Genera reducciones adicionales."
                    )
                }
            },
            "required": ["amount", "operation_type", "relationship", "ccaa"]
        }
    }
}


# ---------------------------------------------------------------------------
# Tarifa estatal ISD — Art. 21 Ley 29/1987
# (base_hasta, cuota_integra_previa, resto_base_hasta, tipo_pct)
# ---------------------------------------------------------------------------

TARIFA_ESTATAL: List[tuple] = [
    (7_993.46,       0.00,          7_993.46,   7.65),
    (15_980.91,      611.50,        7_987.45,   8.50),
    (23_968.36,    1_290.43,        7_987.45,   9.35),
    (31_955.81,    2_037.26,        7_987.45,  10.20),
    (39_943.26,    2_851.98,        7_987.45,  11.05),
    (47_930.72,    3_734.59,        7_987.45,  11.90),
    (55_918.17,    4_685.10,        7_987.45,  12.75),
    (63_905.62,    5_703.50,        7_987.45,  13.60),
    (71_893.07,    6_789.79,        7_987.45,  14.45),
    (79_880.52,    7_943.98,        7_987.45,  15.30),
    (119_757.67,   9_166.06,       39_877.15,  16.15),
    (159_634.83,  15_606.22,       39_877.16,  18.70),
    (239_389.13,  23_063.25,       79_754.30,  21.25),
    (398_777.54,  40_011.04,      159_388.41,  25.50),
    (797_555.08,  80_655.08,      398_777.54,  29.75),
    (float("inf"), 199_291.40,    float("inf"), 34.00),
]

# Coeficientes multiplicadores (Art. 22 Ley 29/1987)
# (patrimonio_hasta, coef_grupos_i_ii, coef_grupo_iii, coef_grupo_iv)
COEFICIENTES_MULTIPLICADORES: List[tuple] = [
    (402_678.11,         1.0000, 1.5882, 2.0000),
    (2_007_380.43,       1.0500, 1.6676, 2.1000),
    (4_020_770.98,       1.1000, 1.7471, 2.2000),
    (float("inf"),       1.2000, 1.9059, 2.4000),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_tarifa_estatal(base_liquidable: float) -> float:
    """Apply the state ISD tariff and return cuota integra."""
    if base_liquidable <= 0:
        return 0.0

    for base_hasta, cuota_previa, _resto, tipo_pct in TARIFA_ESTATAL:
        if base_liquidable <= base_hasta:
            # Find the previous bracket's base to know the excess
            # We need the lower bound of the current bracket
            break

    # Walk the table properly
    cuota = 0.0
    remaining = base_liquidable
    previous_base = 0.0

    for base_hasta, cuota_en_base, tramo_size, tipo_pct in TARIFA_ESTATAL:
        if remaining <= 0:
            break
        if base_liquidable <= base_hasta:
            # We are in this bracket — apply type to the excess over previous_base
            excess = base_liquidable - previous_base
            cuota = cuota_en_base + excess * (tipo_pct / 100.0)
            break
        previous_base = base_hasta

    return round(cuota, 2)


def _get_coeficiente(relationship: str, previous_wealth: float) -> float:
    """Return the multiplier coefficient for patrimony and group."""
    wealth = previous_wealth if previous_wealth is not None else 0.0

    for patrim_hasta, coef_i_ii, coef_iii, coef_iv in COEFICIENTES_MULTIPLICADORES:
        if wealth <= patrim_hasta:
            if relationship in ("grupo_i", "grupo_ii"):
                return coef_i_ii
            elif relationship == "grupo_iii":
                return coef_iii
            else:
                return coef_iv

    # Fallback — should never reach here
    if relationship in ("grupo_i", "grupo_ii"):
        return 1.2000
    elif relationship == "grupo_iii":
        return 1.9059
    return 2.4000


def _reduccion_parentesco_estatal(
    relationship: str,
    recipient_age: Optional[int]
) -> Dict[str, Any]:
    """
    Compute the kinship reduction (Arts. 20.2 a) Ley 29/1987).
    Returns dict with importe and base_legal.
    """
    BASE_GRUPO_I = 15_956.87
    INCREMENTO_GRUPO_I = 3_990.72
    MAX_GRUPO_I = 47_858.59
    BASE_GRUPO_II = 15_956.87
    BASE_GRUPO_III = 7_993.46

    if relationship == "grupo_i":
        age = recipient_age if recipient_age is not None else 20
        years_under_21 = max(0, 21 - age)
        importe = BASE_GRUPO_I + INCREMENTO_GRUPO_I * years_under_21
        importe = min(importe, MAX_GRUPO_I)
        return {
            "nombre": "Reducción por parentesco (Grupo I)",
            "importe": round(importe, 2),
            "base_legal": "Art. 20.2.a) Ley 29/1987 — descendientes < 21 años",
        }
    elif relationship == "grupo_ii":
        return {
            "nombre": "Reducción por parentesco (Grupo II)",
            "importe": BASE_GRUPO_II,
            "base_legal": "Art. 20.2.a) Ley 29/1987 — descendientes >= 21, cónyuge, ascendientes",
        }
    elif relationship == "grupo_iii":
        return {
            "nombre": "Reducción por parentesco (Grupo III)",
            "importe": BASE_GRUPO_III,
            "base_legal": "Art. 20.2.a) Ley 29/1987 — colaterales 2.º-3.º grado",
        }
    else:
        return {
            "nombre": "Reducción por parentesco (Grupo IV)",
            "importe": 0.0,
            "base_legal": "Art. 20.2.a) Ley 29/1987 — sin reducción para extraños",
        }


def _reduccion_discapacidad(disability: Optional[int]) -> Optional[Dict[str, Any]]:
    """Return disability reduction if applicable (Art. 20.2.a) Ley 29/1987)."""
    if not disability or disability == 0:
        return None
    if disability >= 65:
        return {
            "nombre": "Reducción por discapacidad >= 65%",
            "importe": 47_858.59,
            "base_legal": "Art. 20.2.a) Ley 29/1987",
        }
    elif disability >= 33:
        return {
            "nombre": "Reducción por discapacidad >= 33%",
            "importe": 15_956.87,
            "base_legal": "Art. 20.2.a) Ley 29/1987",
        }
    return None


def _reduccion_vivienda_habitual(
    amount: float,
    operation_type: str,
    relationship: str
) -> Optional[Dict[str, Any]]:
    """
    Reduccion 95% vivienda habitual en sucesiones (Art. 20.2.c) Ley 29/1987).
    Max 122.606,47 EUR per receptor.
    Only Grupos I, II and III (colaterales 2.º-3.º grado).
    """
    if operation_type != "sucesion":
        return None
    if relationship == "grupo_iv":
        return None
    reduccion = min(amount * 0.95, 122_606.47)
    return {
        "nombre": "Reducción vivienda habitual (95%)",
        "importe": round(reduccion, 2),
        "base_legal": "Art. 20.2.c) Ley 29/1987 — límite 122.606,47€",
    }


def _reduccion_empresa_familiar(
    amount: float,
    operation_type: str
) -> Optional[Dict[str, Any]]:
    """Reduccion 95% empresa familiar (Art. 20.2.c) Ley 29/1987)."""
    reduccion = amount * 0.95
    context = "sucesiones y donaciones" if operation_type == "donacion" else "sucesiones"
    return {
        "nombre": "Reducción empresa o negocio familiar (95%)",
        "importe": round(reduccion, 2),
        "base_legal": f"Art. 20.2.c) Ley 29/1987 — {context}",
    }


# ---------------------------------------------------------------------------
# CCAA-specific rules
# ---------------------------------------------------------------------------

def _bonificaciones_ccaa(
    ccaa_norm: str,
    operation_type: str,
    relationship: str,
    base_liquidable: float,
    cuota_tributaria: float,
    amount: float,
) -> List[Dict[str, Any]]:
    """
    Return list of autonomous-community bonifications.
    Each entry: {nombre, porcentaje, importe, normativa}.
    """
    bonificaciones: List[Dict[str, Any]] = []

    # ---- Madrid -------------------------------------------------------
    if ccaa_norm == "madrid":
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Madrid (99%)",
                "porcentaje": 99.0,
                "importe": round(cuota_tributaria * 0.99, 2),
                "normativa": "Decreto Legislativo 1/2010, Art. 22",
            })

    # ---- Andalucia ----------------------------------------------------
    elif ccaa_norm == "andalucia":
        if relationship in ("grupo_i", "grupo_ii") and base_liquidable < 1_000_000:
            bonificaciones.append({
                "nombre": "Bonificación autonómica Andalucía (99%)",
                "porcentaje": 99.0,
                "importe": round(cuota_tributaria * 0.99, 2),
                "normativa": "Decreto Legislativo 1/2018 Andalucía, Art. 22 quinquies",
            })

    # ---- Valencia -----------------------------------------------------
    elif ccaa_norm == "valencia":
        if operation_type == "sucesion" and relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Valencia (75%) — sucesiones",
                "porcentaje": 75.0,
                "importe": round(cuota_tributaria * 0.75, 2),
                "normativa": "Ley 13/1997 Valencia (modificada Ley 8/2022)",
            })
        elif operation_type == "donacion" and relationship == "grupo_i":
            bonificaciones.append({
                "nombre": "Bonificación autonómica Valencia (75%) — donaciones Grupo I",
                "porcentaje": 75.0,
                "importe": round(cuota_tributaria * 0.75, 2),
                "normativa": "Ley 13/1997 Valencia (modificada Ley 8/2022)",
            })

    # ---- Aragon -------------------------------------------------------
    elif ccaa_norm == "aragon":
        if (
            operation_type == "sucesion"
            and relationship in ("grupo_i", "grupo_ii")
            and amount <= 500_000
        ):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Aragón (99%) — sucesiones ≤ 500.000€",
                "porcentaje": 99.0,
                "importe": round(cuota_tributaria * 0.99, 2),
                "normativa": "Decreto Legislativo 1/2005 Aragón, modificado Ley 10/2021",
            })

    # ---- Cataluna -----------------------------------------------------
    elif ccaa_norm == "cataluna":
        # Cataluña applies a progressive discount on quota based on base liquidable
        # (coeficient ranges from 0.99 to 0.01 per Ley 19/2010)
        if relationship in ("grupo_i", "grupo_ii"):
            # Simplified: flat 99% up to 100k, then decreasing
            if base_liquidable <= 100_000:
                pct = 99.0
            elif base_liquidable <= 500_000:
                pct = 50.0
            else:
                pct = 20.0
            bonificaciones.append({
                "nombre": f"Bonificación autonómica Cataluña ({pct:.0f}%)",
                "porcentaje": pct,
                "importe": round(cuota_tributaria * pct / 100.0, 2),
                "normativa": "Ley 19/2010 Cataluña — sistema de coeficientes reductores",
            })

    # ---- Pais Vasco: Araba, Bizkaia, Gipuzkoa ------------------------
    elif ccaa_norm in ("araba", "bizkaia", "gipuzkoa", "pais_vasco"):
        # Each territorio historico has its own foral normative.
        # Grupos I and II are almost fully exempt.
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Exención cuasi-total territorio foral (Grupo I/II)",
                "porcentaje": 100.0,
                "importe": round(cuota_tributaria, 2),
                "normativa": (
                    "Normas Forales ISD: NF 4/2015 Araba / NF 4/2015 Bizkaia "
                    "/ NF 3/1990 Gipuzkoa — exención sucesiones y donaciones Grupos I-II"
                ),
            })
        elif relationship == "grupo_iii":
            # Partial reduction ~50% (simplified)
            bonificaciones.append({
                "nombre": "Reducción foral Grupo III (~50%)",
                "porcentaje": 50.0,
                "importe": round(cuota_tributaria * 0.50, 2),
                "normativa": "Normativa foral País Vasco — reducción colaterales 2.º-3.º grado",
            })

    # ---- Navarra ------------------------------------------------------
    elif ccaa_norm == "navarra":
        # Navarra has its own tariff (much lower) and full exemption for
        # spouse and direct descendants in sucesiones.
        if operation_type == "sucesion" and relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Exención Navarra — cónyuge y descendientes (sucesiones)",
                "porcentaje": 100.0,
                "importe": round(cuota_tributaria, 2),
                "normativa": "Ley Foral 11/2022 Navarra — exención cónyuge y línea directa",
            })
        elif operation_type == "donacion" and relationship in ("grupo_i", "grupo_ii"):
            # Navarra applies its own lower tariff — 50% approx. reduction vs state
            bonificaciones.append({
                "nombre": "Tarifa reducida Navarra — donaciones Grupos I/II",
                "porcentaje": 50.0,
                "importe": round(cuota_tributaria * 0.50, 2),
                "normativa": "Ley Foral 11/2022 Navarra — tarifa propia donaciones",
            })

    # ---- Galicia -------------------------------------------------------
    elif ccaa_norm == "galicia":
        # Ley 2/2023 Galicia: 99% bonificación sucesiones Grupos I-II
        # si base imponible individual <= 400.000 €
        if relationship in ("grupo_i", "grupo_ii"):
            if operation_type == "sucesion" and amount <= 400_000:
                bonificaciones.append({
                    "nombre": "Bonificación autonómica Galicia (99%) — sucesiones ≤ 400.000€",
                    "porcentaje": 99.0,
                    "importe": round(cuota_tributaria * 0.99, 2),
                    "normativa": "DL 1/2011 Galicia, modificado Ley 2/2023 — Art. 6 bonificación Grupos I-II",
                })
            elif operation_type == "donacion":
                # Galicia: reducción 99% donaciones padres→hijos si < 200.000 €
                if amount <= 200_000:
                    bonificaciones.append({
                        "nombre": "Bonificación autonómica Galicia (99%) — donaciones ≤ 200.000€",
                        "porcentaje": 99.0,
                        "importe": round(cuota_tributaria * 0.99, 2),
                        "normativa": "DL 1/2011 Galicia, modificado Ley 2/2023 — Art. 8 donaciones Grupos I-II",
                    })

    # ---- Castilla y Leon -----------------------------------------------
    elif ccaa_norm == "castilla_y_leon":
        # DL 1/2013 Castilla y León: 99% bonificación sucesiones y donaciones
        # Grupos I-II sin límite de base
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Castilla y León (99%)",
                "porcentaje": 99.0,
                "importe": round(cuota_tributaria * 0.99, 2),
                "normativa": "DL 1/2013 Castilla y León, Art. 14.1 — bonificación 99% Grupos I-II",
            })

    # ---- Castilla-La Mancha --------------------------------------------
    elif ccaa_norm == "castilla_la_mancha":
        # Ley 8/2013 CLM modificada por Ley 3/2023: 100% bonificación
        # sucesiones y donaciones Grupos I-II desde 2024
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Castilla-La Mancha (100%)",
                "porcentaje": 100.0,
                "importe": round(cuota_tributaria, 2),
                "normativa": "Ley 8/2013 CLM, modificada Ley 3/2023 — bonificación 100% Grupos I-II (2024+)",
            })

    # ---- Extremadura ---------------------------------------------------
    elif ccaa_norm == "extremadura":
        # DL 1/2018 Extremadura, Art. 15: 99% bonificación sucesiones Y
        # donaciones Grupos I-II con límites por grupo.
        # Grupo I (descendientes < 21): límite 175.000 €
        # Grupo II (cónyuge/ascendientes/descendientes >= 21): límite 325.000 €
        if relationship in ("grupo_i", "grupo_ii"):
            limite = 175_000 if relationship == "grupo_i" else 325_000
            op_label = "sucesiones" if operation_type == "sucesion" else "donaciones"
            if amount <= limite:
                bonificaciones.append({
                    "nombre": f"Bonificación autonómica Extremadura (99%) — {op_label} ≤ {limite:,.0f}€",
                    "porcentaje": 99.0,
                    "importe": round(cuota_tributaria * 0.99, 2),
                    "normativa": "DL 1/2018 Extremadura, Art. 15 — bonificación 99% Grupos I-II con límites",
                })

    # ---- Murcia --------------------------------------------------------
    elif ccaa_norm == "murcia":
        # DL 1/2010 Murcia: 99% bonificación sucesiones y donaciones Grupos I-II
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Murcia (99%)",
                "porcentaje": 99.0,
                "importe": round(cuota_tributaria * 0.99, 2),
                "normativa": "DL 1/2010 Región de Murcia, Art. 3 — bonificación 99% Grupos I-II",
            })

    # ---- Canarias ------------------------------------------------------
    elif ccaa_norm == "canarias":
        # Ley 4/2012 Canarias modificada por DL 1/2023: 99.9% bonificación
        # sucesiones y donaciones Grupos I-II
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Canarias (99,9%)",
                "porcentaje": 99.9,
                "importe": round(cuota_tributaria * 0.999, 2),
                "normativa": "DL 1/2023 Canarias — bonificación 99,9% Grupos I-II sucesiones y donaciones",
            })

    # ---- Asturias ------------------------------------------------------
    elif ccaa_norm == "asturias":
        # DL 2/2014 Asturias modificado por Ley de Presupuestos 2024:
        # Bonificación escalonada sucesiones Grupo II según base liquidable.
        # Grupo I: 100% bonificación.
        if relationship == "grupo_i":
            bonificaciones.append({
                "nombre": "Bonificación autonómica Asturias (100%) — Grupo I",
                "porcentaje": 100.0,
                "importe": round(cuota_tributaria, 2),
                "normativa": "DL 2/2014 Asturias — bonificación 100% Grupo I",
            })
        elif relationship == "grupo_ii" and operation_type == "sucesion":
            # Escalonada: 100% hasta 300K, 95% hasta 450K, 90% hasta 600K
            if base_liquidable <= 300_000:
                pct = 100.0
            elif base_liquidable <= 450_000:
                pct = 95.0
            elif base_liquidable <= 600_000:
                pct = 90.0
            else:
                pct = 0.0  # Sin bonificación por encima de 600K
            if pct > 0:
                bonificaciones.append({
                    "nombre": f"Bonificación autonómica Asturias ({pct:.0f}%) — sucesiones Grupo II",
                    "porcentaje": pct,
                    "importe": round(cuota_tributaria * pct / 100.0, 2),
                    "normativa": "DL 2/2014 Asturias, Art. 18 — bonificación escalonada Grupo II",
                })
        elif relationship == "grupo_ii" and operation_type == "donacion":
            # DL 2/2014 Asturias: donaciones Grupo II — 95% bonificación.
            # NOTE: conservative 95% flat rate; verify exact rate against
            # latest Asturias budget law if higher precision is needed.
            bonificaciones.append({
                "nombre": "Bonificación autonómica Asturias (95%) — donaciones Grupo II",
                "porcentaje": 95.0,
                "importe": round(cuota_tributaria * 0.95, 2),
                "normativa": "DL 2/2014 Asturias — bonificación donaciones Grupo II",
            })

    # ---- Cantabria -----------------------------------------------------
    elif ccaa_norm == "cantabria":
        # Ley de Cantabria 5/2023: 100% bonificación sucesiones y donaciones
        # Grupos I-II desde 2024
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica Cantabria (100%)",
                "porcentaje": 100.0,
                "importe": round(cuota_tributaria, 2),
                "normativa": "Ley 5/2023 Cantabria — bonificación 100% Grupos I-II (2024+)",
            })

    # ---- La Rioja ------------------------------------------------------
    elif ccaa_norm == "la_rioja":
        # Ley 10/2017 La Rioja modificada: 99% bonificación sucesiones
        # y donaciones Grupos I-II
        if relationship in ("grupo_i", "grupo_ii"):
            bonificaciones.append({
                "nombre": "Bonificación autonómica La Rioja (99%)",
                "porcentaje": 99.0,
                "importe": round(cuota_tributaria * 0.99, 2),
                "normativa": "Ley 10/2017 La Rioja — bonificación 99% Grupos I-II",
            })

    # ---- Baleares ------------------------------------------------------
    elif ccaa_norm == "baleares":
        # DL 1/2014 Baleares: 99% bonificación sucesiones Grupos I-II
        # si base imponible <= 3.000.000 €
        if relationship in ("grupo_i", "grupo_ii"):
            if operation_type == "sucesion" and amount <= 3_000_000:
                bonificaciones.append({
                    "nombre": "Bonificación autonómica Baleares (99%) — sucesiones ≤ 3M€",
                    "porcentaje": 99.0,
                    "importe": round(cuota_tributaria * 0.99, 2),
                    "normativa": "DL 1/2014 Baleares, Art. 36 — bonificación 99% Grupos I-II (base ≤ 3M€)",
                })
            elif operation_type == "donacion":
                # Baleares: 75% bonificación donaciones padres→hijos
                bonificaciones.append({
                    "nombre": "Bonificación autonómica Baleares (75%) — donaciones Grupos I-II",
                    "porcentaje": 75.0,
                    "importe": round(cuota_tributaria * 0.75, 2),
                    "normativa": "DL 1/2014 Baleares, Art. 37 — bonificación 75% donaciones Grupos I-II",
                })

    # ---- Ceuta ---------------------------------------------------------
    elif ccaa_norm == "ceuta":
        # Art. 23 bis Ley 29/1987: bonificación 50% para residentes en Ceuta
        # Aplica a todos los grupos y tipos de operación
        bonificaciones.append({
            "nombre": "Bonificación estatal Ceuta (50%)",
            "porcentaje": 50.0,
            "importe": round(cuota_tributaria * 0.50, 2),
            "normativa": "Art. 23 bis Ley 29/1987 — bonificación 50% residentes Ceuta",
        })

    # ---- Melilla -------------------------------------------------------
    elif ccaa_norm == "melilla":
        # Art. 23 bis Ley 29/1987: bonificación 50% para residentes en Melilla
        # Aplica a todos los grupos y tipos de operación
        bonificaciones.append({
            "nombre": "Bonificación estatal Melilla (50%)",
            "porcentaje": 50.0,
            "importe": round(cuota_tributaria * 0.50, 2),
            "normativa": "Art. 23 bis Ley 29/1987 — bonificación 50% residentes Melilla",
        })

    return bonificaciones


def _normalize_ccaa(ccaa: str) -> str:
    """Normalize CCAA name to a lowercase key."""
    mapping = {
        "madrid": "madrid",
        "comunidad de madrid": "madrid",
        "andalucia": "andalucia",
        "andalucía": "andalucia",
        "cataluna": "cataluna",
        "cataluña": "cataluna",
        "catalunya": "cataluna",
        "valencia": "valencia",
        "valenciana": "valencia",
        "comunitat valenciana": "valencia",
        "comunidad valenciana": "valencia",
        "aragon": "aragon",
        "aragón": "aragon",
        "araba": "araba",
        "alava": "araba",
        "álava": "araba",
        "bizkaia": "bizkaia",
        "vizcaya": "bizkaia",
        "gipuzkoa": "gipuzkoa",
        "guipuzcoa": "gipuzkoa",
        "guipúzcoa": "gipuzkoa",
        "pais vasco": "pais_vasco",
        "país vasco": "pais_vasco",
        "euskadi": "pais_vasco",
        "navarra": "navarra",
        "nafarroa": "navarra",
        "asturias": "asturias",
        "cantabria": "cantabria",
        "la rioja": "la_rioja",
        "rioja": "la_rioja",
        "murcia": "murcia",
        "region de murcia": "murcia",
        "castilla y leon": "castilla_y_leon",
        "castilla y león": "castilla_y_leon",
        "castilla la mancha": "castilla_la_mancha",
        "castilla-la mancha": "castilla_la_mancha",
        "extremadura": "extremadura",
        "galicia": "galicia",
        "baleares": "baleares",
        "illes balears": "baleares",
        "canarias": "canarias",
        "ceuta": "ceuta",
        "melilla": "melilla",
    }
    key = ccaa.lower().strip()
    return mapping.get(key, key)


def _get_plazo_presentacion(operation_type: str) -> str:
    """Return the statutory filing deadline."""
    if operation_type == "sucesion":
        return (
            "6 meses desde el fallecimiento del causante "
            "(prorrogable otros 6 meses — Arts. 67 y 68 RISD)"
        )
    else:
        return (
            "30 días hábiles desde la fecha de la donación "
            "(Art. 67 RISD)"
        )


def _get_normativa(ccaa_norm: str, operation_type: str) -> str:
    """Return the applicable legal framework string."""
    base = "Ley 29/1987, de 18 de diciembre, del Impuesto sobre Sucesiones y Donaciones"
    foral_map = {
        "araba": "Norma Foral 11/2005 de las Juntas Generales de Álava",
        "bizkaia": "Norma Foral 4/2015 de las Juntas Generales de Bizkaia",
        "gipuzkoa": "Norma Foral 3/1990 de las Juntas Generales de Gipuzkoa",
        "pais_vasco": "Normativa foral del País Vasco (NF 11/2005 Álava / NF 4/2015 Bizkaia / NF 3/1990 Gipuzkoa)",
        "navarra": "Ley Foral 11/2022, de 23 de diciembre (Navarra)",
    }
    ccaa_extra = {
        "madrid": "Decreto Legislativo 1/2010, de 21 de octubre (Madrid)",
        "andalucia": "Decreto Legislativo 1/2018, de 19 de junio (Andalucía)",
        "cataluna": "Ley 19/2010, de 7 de junio (Cataluña)",
        "valencia": "Ley 13/1997, de 23 de diciembre (Valencia), modificada Ley 8/2022",
        "aragon": "Decreto Legislativo 1/2005, de 26 de septiembre (Aragón), modificado Ley 10/2021",
        "galicia": "Decreto Legislativo 1/2011, de 28 de julio (Galicia), modificado Ley 2/2023",
        "castilla_y_leon": "Decreto Legislativo 1/2013, de 12 de septiembre (Castilla y León)",
        "castilla_la_mancha": "Ley 8/2013, de 21 de noviembre (Castilla-La Mancha), modificada Ley 3/2023",
        "extremadura": "Decreto Legislativo 1/2018, de 10 de abril (Extremadura)",
        "murcia": "Decreto Legislativo 1/2010, de 5 de noviembre (Región de Murcia)",
        "canarias": "Decreto Ley 1/2023, de 10 de julio (Canarias)",
        "asturias": "Decreto Legislativo 2/2014, de 22 de octubre (Asturias)",
        "cantabria": "Ley 5/2023, de 26 de diciembre (Cantabria)",
        "la_rioja": "Ley 10/2017, de 27 de octubre (La Rioja)",
        "baleares": "Decreto Legislativo 1/2014, de 6 de junio (Illes Balears)",
        "ceuta": "Art. 23 bis Ley 29/1987 — bonificación residentes Ceuta",
        "melilla": "Art. 23 bis Ley 29/1987 — bonificación residentes Melilla",
    }
    if ccaa_norm in foral_map:
        return foral_map[ccaa_norm]
    normativa = base
    if ccaa_norm in ccaa_extra:
        normativa += f"; {ccaa_extra[ccaa_norm]}"
    return normativa


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

async def calculate_isd(
    amount: float,
    operation_type: str,
    relationship: str,
    ccaa: str,
    donor_age: Optional[int] = None,
    recipient_age: Optional[int] = None,
    destination: Optional[str] = None,
    previous_wealth: Optional[float] = None,
    disability: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate Spanish ISD (Impuesto sobre Sucesiones y Donaciones).

    Args:
        amount: Value of the donation or inheritance in euros.
        operation_type: "donacion" or "sucesion".
        relationship: Kinship group ("grupo_i" … "grupo_iv").
        ccaa: Autonomous community of the recipient.
        donor_age: Age of the donor/deceased (optional).
        recipient_age: Age of the recipient (required for grupo_i reductions).
        destination: Special purpose of asset ("vivienda_habitual", etc.).
        previous_wealth: Pre-existing wealth of recipient (euros).
        disability: Disability grade of recipient (0, 33, or 65 pct).

    Returns:
        Full calculation breakdown as a dict with formatted_response.
    """
    try:
        # --- Input validation ---
        if amount <= 0:
            return {
                "success": False,
                "error": "El importe debe ser positivo.",
                "formatted_response": "El importe de la donación/herencia debe ser mayor que 0.",
            }
        if operation_type not in ("donacion", "sucesion"):
            return {
                "success": False,
                "error": f"operation_type inválido: {operation_type}",
                "formatted_response": "El tipo de operación debe ser 'donacion' o 'sucesion'.",
            }
        if relationship not in ("grupo_i", "grupo_ii", "grupo_iii", "grupo_iv"):
            return {
                "success": False,
                "error": f"relationship inválido: {relationship}",
                "formatted_response": "El grupo de parentesco debe ser grupo_i, grupo_ii, grupo_iii o grupo_iv.",
            }

        ccaa_norm = _normalize_ccaa(ccaa)
        logger.info(
            "Calculating ISD: amount=%.2f, type=%s, relationship=%s, ccaa=%s",
            amount, operation_type, relationship, ccaa_norm,
        )

        # ----------------------------------------------------------------
        # 1. Reducciones
        # ----------------------------------------------------------------
        reducciones: List[Dict[str, Any]] = []

        # 1a. Reduccion parentesco estatal
        red_parentesco = _reduccion_parentesco_estatal(relationship, recipient_age)
        reducciones.append(red_parentesco)

        # 1b. Discapacidad
        red_discapacidad = _reduccion_discapacidad(disability)
        if red_discapacidad:
            reducciones.append(red_discapacidad)

        # 1c. Destino especial
        if destination == "vivienda_habitual":
            red_vivienda = _reduccion_vivienda_habitual(amount, operation_type, relationship)
            if red_vivienda:
                reducciones.append(red_vivienda)
        elif destination == "empresa_familiar":
            red_empresa = _reduccion_empresa_familiar(amount, operation_type)
            reducciones.append(red_empresa)
        elif destination == "explotacion_agraria":
            red_agraria = {
                "nombre": "Reducción explotación agraria (90%)",
                "importe": round(amount * 0.90, 2),
                "base_legal": "Art. 20.2.e) Ley 29/1987 — explotaciones agrarias",
            }
            reducciones.append(red_agraria)

        # 1d. Navarra & forales: add extra reductions on top
        if ccaa_norm in ("araba", "bizkaia", "gipuzkoa", "pais_vasco"):
            if relationship in ("grupo_i", "grupo_ii"):
                # Foral territories grant much larger kinship reductions
                extra = {
                    "nombre": "Reducción foral adicional Grupos I/II (90% base)",
                    "importe": round(amount * 0.90, 2),
                    "base_legal": "Normativa Foral País Vasco — reducción adicional",
                }
                reducciones.append(extra)

        # ----------------------------------------------------------------
        # 2. Base liquidable
        # ----------------------------------------------------------------
        base_imponible = round(amount, 2)
        total_reducciones = sum(r["importe"] for r in reducciones)
        base_liquidable = max(0.0, round(base_imponible - total_reducciones, 2))

        # ----------------------------------------------------------------
        # 3. Cuota integra (tarifa estatal)
        # ----------------------------------------------------------------
        cuota_integra = _apply_tarifa_estatal(base_liquidable)

        # ----------------------------------------------------------------
        # 4. Coeficiente multiplicador
        # ----------------------------------------------------------------
        coef = _get_coeficiente(relationship, previous_wealth or 0.0)
        cuota_tributaria = round(cuota_integra * coef, 2)

        # ----------------------------------------------------------------
        # 5. Bonificaciones autonómicas
        # ----------------------------------------------------------------
        bonificaciones = _bonificaciones_ccaa(
            ccaa_norm, operation_type, relationship,
            base_liquidable, cuota_tributaria, amount,
        )

        total_bonificaciones = sum(b["importe"] for b in bonificaciones)
        cuota_a_pagar = max(0.0, round(cuota_tributaria - total_bonificaciones, 2))

        # ----------------------------------------------------------------
        # 6. Notes and warnings
        # ----------------------------------------------------------------
        notas: List[str] = []

        if ccaa_norm in ("araba", "bizkaia", "gipuzkoa", "pais_vasco", "navarra"):
            notas.append(
                "Territorio foral: este cálculo es una aproximación. "
                "Los territorios forales tienen normativa propia que puede diferir "
                "significativamente de la estatal. Se recomienda consultar con un "
                "gestor local o la Hacienda Foral correspondiente."
            )
        if operation_type == "donacion" and ccaa_norm not in (
            "madrid", "andalucia", "araba", "bizkaia", "gipuzkoa", "pais_vasco", "navarra",
            "castilla_y_leon", "castilla_la_mancha", "murcia", "canarias", "cantabria",
            "la_rioja", "galicia", "baleares", "ceuta", "melilla",
            "extremadura", "asturias",
        ):
            notas.append(
                "En donaciones, el impuesto se liquida en la CCAA donde estén situados "
                "los bienes inmuebles, o en la CCAA de residencia del donatario para bienes muebles."
            )
        if destination in ("empresa_familiar", "explotacion_agraria"):
            notas.append(
                "La reducción por empresa familiar o explotación agraria requiere el "
                "cumplimiento de requisitos específicos (actividad principal, mantenimiento "
                "10 años, etc.). Verificar con asesor fiscal."
            )
        if base_liquidable == 0:
            notas.append(
                "La base liquidable es cero porque las reducciones superan la base imponible. "
                "No se genera cuota."
            )
        if recipient_age is None and relationship == "grupo_i":
            notas.append(
                "No se indicó la edad del receptor. Se asumió 20 años para calcular la "
                "reducción del Grupo I. Proporcione la edad exacta para un cálculo preciso."
            )

        # ----------------------------------------------------------------
        # 7. Formatted response
        # ----------------------------------------------------------------
        op_label = "Donación" if operation_type == "donacion" else "Sucesión/Herencia"
        group_labels = {
            "grupo_i": "Grupo I (descendientes < 21 años)",
            "grupo_ii": "Grupo II (descendientes >= 21, cónyuge, ascendientes)",
            "grupo_iii": "Grupo III (colaterales 2.º-3.º grado, afines)",
            "grupo_iv": "Grupo IV (colaterales 4.º+ grado y extraños)",
        }
        group_label = group_labels.get(relationship, relationship)

        lines = [
            f"**Cálculo ISD — {op_label}**",
            f"CCAA: {ccaa} | Parentesco: {group_label}",
            "",
            f"**Base imponible**: {base_imponible:,.2f} €",
        ]

        if reducciones:
            lines.append("**Reducciones aplicadas**:")
            for r in reducciones:
                lines.append(f"  - {r['nombre']}: -{r['importe']:,.2f} € ({r['base_legal']})")

        lines += [
            f"**Base liquidable**: {base_liquidable:,.2f} €",
            "",
            f"**Cuota íntegra** (tarifa estatal Art. 21 Ley 29/1987): {cuota_integra:,.2f} €",
            f"**Coeficiente multiplicador** (patrimonio preexistente + grupo): x{coef:.4f}",
            f"**Cuota tributaria**: {cuota_tributaria:,.2f} €",
        ]

        if bonificaciones:
            lines.append("**Bonificaciones autonómicas**:")
            for b in bonificaciones:
                lines.append(f"  - {b['nombre']}: -{b['importe']:,.2f} € ({b['porcentaje']:.0f}%)")

        lines += [
            "",
            f"**Cuota a pagar: {cuota_a_pagar:,.2f} €**",
            "",
            f"Plazo de presentación: {_get_plazo_presentacion(operation_type)}",
            "",
            f"Normativa: {_get_normativa(ccaa_norm, operation_type)}",
        ]

        if notas:
            lines.append("")
            lines.append("**Notas importantes**:")
            for nota in notas:
                lines.append(f"  - {nota}")

        lines.append("")
        lines.append(
            "_Este cálculo es orientativo. La liquidación definitiva puede variar según "
            "circunstancias personales, valoraciones y posibles comprobaciones de valor. "
            "Se recomienda consultar con un asesor fiscal o gestoría._"
        )

        formatted_response = "\n".join(lines)

        return {
            "success": True,
            "base_imponible": base_imponible,
            "reducciones": reducciones,
            "base_liquidable": base_liquidable,
            "cuota_integra": cuota_integra,
            "coeficiente_multiplicador": coef,
            "cuota_tributaria": cuota_tributaria,
            "bonificaciones_ccaa": bonificaciones,
            "cuota_a_pagar": cuota_a_pagar,
            "plazo_presentacion": _get_plazo_presentacion(operation_type),
            "notas": notas,
            "normativa_aplicable": _get_normativa(ccaa_norm, operation_type),
            "formatted_response": formatted_response,
        }

    except Exception as exc:
        logger.error("Error calculating ISD: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": f"Error al calcular el ISD: {exc}",
        }
