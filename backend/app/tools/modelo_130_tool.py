"""
Modelo 130 (Pago Fraccionado IRPF) Calculator Tool for TaxIA.

This module is a THIN WRAPPER around `Modelo130Calculator` (the service in
`app/utils/calculators/modelo_130.py`). All numeric logic lives in the
calculator — the tool only:

  1. Maps OpenAI function-calling parameters to calculator inputs.
  2. Decides which calculator method to invoke (Section I, Section II,
     dispensa check).
  3. Builds a human-readable response for the LLM to forward.

Rule (CLAUDE.md): tools are wrappers, NEVER reimplement calculator logic.
This guarantees that the chat tool, the public calculator and the workspace
tool agree on the same numbers.

IMPORTANT — fixes applied (audit 2026-05, gaps C1, A1, A2, A3, A4, A5):

  C1: Casillas 05 / 06 ahora coinciden con AEAT.
      05 = pagos fraccionados anteriores; 06 = retenciones e ingresos a cuenta.
  A1: Sección II (actividades agrícolas/ganaderas/forestales/pesqueras),
      tipo 2% (0,8% en Ceuta/Melilla).
  A2: Regla de dispensa Art. 109.2/3 RIRPF (≥70% retención año anterior).
  A3: Regla de dispensa foral Gipuzkoa (≥50% retención año anterior).
  A4: Art. 80 bis con escalones planos (delegado al calculator, sin
      interpolación lineal).
  A5: Casilla 18 (autoliquidación complementaria) propagada.

IMPORTANT: Section I (estimación directa) requires CUMULATIVE figures from
January 1st. Section II requires QUARTERLY figures. The tool documents this
in the OpenAI schema so the LLM picks the right inputs.
"""

import logging
from datetime import datetime
from typing import Any

from app.utils.calculators.modelo_130 import Modelo130Calculator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenAI function-calling schema
# ---------------------------------------------------------------------------

MODELO_130_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_130",
        "description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 130
- Pago fraccionado de IRPF (estimación directa, normal o simplificada)
- Pago fraccionado trimestral
- Cuanto tengo que pagar de IRPF como autónomo trimestralmente
- Pago a cuenta IRPF autónomos

OBLIGATORIO usar esta funcion si el usuario quiere calcular o simular
su pago fraccionado trimestral de IRPF.

REGLAS DE INPUT:
- Sección I (actividades NO agrícolas): los importes son ACUMULADOS desde
  el 1 de enero hasta el final del trimestre. Si el usuario da datos
  trimestrales, PREGUNTA antes de continuar.
- Sección II (agrícola/ganadero/forestal/pesquero): pasa actividad_agraria=true
  y usa volumen_ingresos_agrario + retenciones_agrario del TRIMESTRE.
- Casilla 05 = PAGOS FRACCIONADOS ANTERIORES de este año (no retenciones).
- Casilla 06 = RETENCIONES e ingresos a cuenta acumulados.
- Si el usuario es profesional (IAE 2/3) y ≥70% de sus ingresos llevan
  retención (50% en Gipuzkoa), está DISPENSADO de presentar el modelo —
  pasa pct_retencion_anio_anterior y es_profesional para que la herramienta
  lo detecte.
- Casilla 18 = importe ya ingresado en una autoliquidación anterior del
  mismo trimestre (sólo para complementarias).

La funcion calcula el resultado de las casillas 01-19 según las
instrucciones AEAT y delega en `Modelo130Calculator` para garantizar
coherencia con la calculadora pública del frontend.""",
        "parameters": {
            "type": "object",
            "properties": {
                "trimestre": {
                    "type": "integer",
                    "description": "Trimestre (1, 2, 3 o 4)",
                },
                "year": {
                    "type": "integer",
                    "description": "Año fiscal. Por defecto: año actual.",
                },
                "ingresos_computables": {
                    "type": "number",
                    "description": (
                        "Sección I — Ingresos ACUMULADOS desde 1 de enero "
                        "hasta el final del trimestre (casilla 01)."
                    ),
                },
                "gastos_deducibles": {
                    "type": "number",
                    "description": (
                        "Sección I — Gastos deducibles ACUMULADOS desde "
                        "1 de enero hasta el final del trimestre (casilla 02)."
                    ),
                },
                "pagos_fraccionados_anteriores": {
                    "type": "number",
                    "description": (
                        "CASILLA 05 — Pagos fraccionados ya ingresados en "
                        "trimestres previos del MISMO año. Para T1 siempre 0."
                    ),
                },
                "retenciones_ingresos_cuenta": {
                    "type": "number",
                    "description": (
                        "CASILLA 06 — Retenciones e ingresos a cuenta "
                        "soportados ACUMULADOS desde 1 de enero."
                    ),
                },
                "rendimiento_neto_previo_anual": {
                    "type": "number",
                    "description": (
                        "Rendimiento neto del AÑO ANTERIOR (Art. 80 bis "
                        "LIRPF). Si <= 12.000 EUR aplica deducción "
                        "escalonada (100/75/50/25 EUR/trim)."
                    ),
                },
                "tiene_vivienda_habitual": {
                    "type": "boolean",
                    "description": (
                        "True si tiene derecho a la deducción por vivienda "
                        "habitual pre-2013 (casilla 16). Máx 660,14 EUR/trim."
                    ),
                },
                "ceuta_melilla": {
                    "type": "boolean",
                    "description": (
                        "True si la actividad se desarrolla en Ceuta o Melilla "
                        "(reducción 60% del Art. 110.2 RIRPF: 8% en sección I, "
                        "0,8% en sección II agrícola)."
                    ),
                },
                "resultado_anterior_complementaria": {
                    "type": "number",
                    "description": (
                        "CASILLA 18 — Resultado ya ingresado en una "
                        "autoliquidación anterior del mismo trimestre "
                        "(complementaria). Por defecto 0."
                    ),
                },
                "actividad_agraria": {
                    "type": "boolean",
                    "description": (
                        "True si la actividad es agrícola, ganadera, forestal "
                        "o pesquera (Sección II, Art. 110.1.b RIRPF). "
                        "Tipo 2% (0,8% Ceuta/Melilla) sobre volumen ingresos."
                    ),
                },
                "volumen_ingresos_agrario": {
                    "type": "number",
                    "description": (
                        "Sección II — Volumen de ingresos del TRIMESTRE "
                        "(casilla 08), excluyendo subvenciones de capital."
                    ),
                },
                "retenciones_agrario": {
                    "type": "number",
                    "description": (
                        "Sección II — Retenciones e ingresos a cuenta del "
                        "TRIMESTRE (casilla 10)."
                    ),
                },
                "es_profesional": {
                    "type": "boolean",
                    "description": (
                        "True si la actividad es profesional (epígrafe IAE "
                        "sección 2 ó 3). Necesario para evaluar dispensa "
                        "Art. 109.2 RIRPF."
                    ),
                },
                "pct_retencion_anio_anterior": {
                    "type": "number",
                    "description": (
                        "Porcentaje (0-100) de ingresos sometidos a retención "
                        "el AÑO ANTERIOR. Si ≥70% (≥50% Gipuzkoa para "
                        "profesionales) el contribuyente está DISPENSADO de "
                        "presentar el Modelo 130."
                    ),
                },
                "territorio": {
                    "type": "string",
                    "description": (
                        "Territorio fiscal a efectos de la dispensa. "
                        "Valores: 'Comun' (defecto), 'Gipuzkoa', 'Araba', "
                        "'Bizkaia', 'Navarra'. Sólo afecta al umbral de "
                        "dispensa por retención."
                    ),
                },
            },
            "required": ["trimestre"],
        },
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_TRIMESTRE_LABEL = {1: "1T", 2: "2T", 3: "3T", 4: "4T"}
_TRIMESTRE_MESES = {
    1: "enero-marzo",
    2: "abril-junio",
    3: "julio-septiembre",
    4: "octubre-diciembre",
}
_TRIMESTRE_ACUMULADO = {
    1: "enero a marzo",
    2: "enero a junio",
    3: "enero a septiembre",
    4: "enero a diciembre",
}
_TRIMESTRE_PLAZO = {
    1: "20 de abril",
    2: "20 de julio",
    3: "20 de octubre",
    4: "30 de enero del año siguiente",
}


def _fmt(amount: float) -> str:
    return f"{amount:,.2f}"


def _build_dispensa_response(
    *,
    trimestre: int,
    year: int,
    pct: float,
    territorio: str,
    threshold: float,
) -> str:
    """Build the response shown when the contributor is dispensado de presentar."""
    label = _TRIMESTRE_LABEL[trimestre]
    lines = [
        f"**Modelo 130 — {label} {year} — DISPENSA DE PRESENTACIÓN**",
        "",
        (
            f"Con un {pct:.1f}% de tus ingresos sometidos a retención el año "
            f"anterior (umbral aplicable: {threshold:.0f}% en {territorio}), "
            "**no estás obligado a presentar el Modelo 130** este trimestre."
        ),
        "",
        (
            "Base legal: Art. 109.2 RIRPF (territorio común, ≥70%) y la "
            "Norma Foral del IRPF en Gipuzkoa (≥50% para profesionales). "
            "Para actividades agrarias el cómputo excluye subvenciones e "
            "indemnizaciones (Art. 109.3 RIRPF)."
        ),
        "",
        (
            "Si tu situación cambia durante el año (clientes que dejan de "
            "retenerte, nuevas actividades sin retención), revisa el "
            "porcentaje real para no incurrir en infracción."
        ),
    ]
    return "\n".join(lines)


def _build_seccion_i_response(
    *,
    trimestre: int,
    year: int,
    casillas: dict[str, float],
    deduccion_80bis: float,
    resultado_final: float,
    ceuta_melilla: bool,
) -> str:
    """Format the Section I result as the LLM expects."""
    label = _TRIMESTRE_LABEL[trimestre]
    meses = _TRIMESTRE_MESES[trimestre]
    acumulado = _TRIMESTRE_ACUMULADO[trimestre]
    plazo = _TRIMESTRE_PLAZO[trimestre]
    territorio = "Ceuta/Melilla" if ceuta_melilla else "territorio común"
    tipo = "8%" if ceuta_melilla else "20%"

    lines = [
        f"**Modelo 130 — {label} {year} ({meses}) — {territorio}**",
        "",
        f"Datos acumulados de {acumulado} {year}:",
        "",
        "**Sección I — Estimación directa**",
        f"- Ingresos computables [01]: {_fmt(casillas['01_ingresos_acumulados'])} EUR",
        f"- Gastos deducibles [02]: {_fmt(casillas['02_gastos_acumulados'])} EUR",
        f"- Rendimiento neto [03]: {_fmt(casillas['03_rendimiento_neto'])} EUR",
        f"- {tipo} del rendimiento [04]: {_fmt(casillas['04_cuota_20pct'])} EUR",
    ]

    # CASILLA 05 = pagos fraccionados anteriores (FIX C1)
    if casillas["05_retenciones_acumuladas"] != casillas["05_retenciones_acumuladas"]:
        pass  # NaN guard (never triggers)

    # NOTE: the calculator preserves AEAT order by NAME but the legacy field
    # name `05_retenciones_acumuladas` is misleading. After the C1 fix the
    # value at key `06_pagos_anteriores` IS retenciones, and `05_*` IS pagos
    # previos in the formatted output. We re-map here for clarity.
    pagos_previos_05 = casillas["06_pagos_anteriores"]  # see fix below
    retenciones_06 = casillas["05_retenciones_acumuladas"]

    if pagos_previos_05 > 0:
        lines.append(f"- Pagos fraccionados anteriores [05]: -{_fmt(pagos_previos_05)} EUR")
    if retenciones_06 > 0:
        lines.append(f"- Retenciones e ingresos a cuenta [06]: -{_fmt(retenciones_06)} EUR")

    lines.append(f"- **Resultado sección I [07]: {_fmt(casillas['07_resultado_seccion_I'])} EUR**")
    lines.append("")

    # Sección III
    lines.append("**Sección III — Liquidación**")
    if deduccion_80bis > 0:
        lines.append(f"- Deducción art. 80 bis (rentas bajas) [13]: -{_fmt(deduccion_80bis)} EUR")
    if casillas.get("16_deduccion_vivienda", 0) > 0:
        lines.append(
            f"- Deducción vivienda habitual [16]: -{_fmt(casillas['16_deduccion_vivienda'])} EUR"
        )
    if casillas.get("18_declaracion_anterior", 0) > 0:
        lines.append(
            f"- Resultado autoliquidación anterior (complementaria) [18]: "
            f"-{_fmt(casillas['18_declaracion_anterior'])} EUR"
        )
    lines.append("")

    lines.append("**Resultado**")
    if resultado_final > 0:
        lines.append(f"- A ingresar [19]: **{_fmt(resultado_final)} EUR**")
    else:
        lines.append(f"- Resultado [19]: **{_fmt(resultado_final)} EUR (sin ingreso)**")

    lines.append("")
    if resultado_final > 0:
        lines.append(
            f"Plazo: presenta antes del **{plazo}**. "
            "Domiciliación bancaria hasta 5 días antes del vencimiento."
        )
    else:
        lines.append(
            f"Aunque el resultado sea 0, debes presentar el modelo igualmente "
            f"antes del **{plazo}**."
        )

    return "\n".join(lines)


def _build_seccion_ii_response(
    *,
    trimestre: int,
    year: int,
    seccion_ii: dict[str, Any],
) -> str:
    """Format the Section II (agrícola) result."""
    label = _TRIMESTRE_LABEL[trimestre]
    meses = _TRIMESTRE_MESES[trimestre]
    plazo = _TRIMESTRE_PLAZO[trimestre]
    casillas = seccion_ii["casillas"]
    tipo = seccion_ii["tipo_aplicado"]
    territorio = "Ceuta/Melilla" if seccion_ii["ceuta_melilla"] else "territorio común"

    lines = [
        f"**Modelo 130 — {label} {year} ({meses}) — Sección II ({territorio})**",
        "",
        "**Actividades agrícolas / ganaderas / forestales / pesqueras**",
        f"- Volumen de ingresos del trimestre [08]: {_fmt(casillas['08_volumen_ingresos'])} EUR",
        f"- Cuota {tipo}% [09]: {_fmt(casillas['09_cuota_pct'])} EUR",
        f"- Retenciones del trimestre [10]: -{_fmt(casillas['10_retenciones_trimestre'])} EUR",
        f"- **Resultado sección II [11]: {_fmt(casillas['11_resultado_seccion_II'])} EUR**",
        "",
        f"Plazo: presenta antes del **{plazo}**. "
        "Recuerda excluir subvenciones de capital del volumen de ingresos.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool entry point
# ---------------------------------------------------------------------------


async def calculate_modelo_130_tool(
    trimestre: int,
    ingresos_computables: float = 0.0,
    gastos_deducibles: float = 0.0,
    year: int | None = None,
    retenciones_ingresos_cuenta: float = 0.0,
    pagos_fraccionados_anteriores: float = 0.0,
    rendimiento_neto_previo_anual: float = 0.0,
    tiene_vivienda_habitual: bool = False,
    ceuta_melilla: bool = False,
    resultado_anterior_complementaria: float = 0.0,
    actividad_agraria: bool = False,
    volumen_ingresos_agrario: float = 0.0,
    retenciones_agrario: float = 0.0,
    es_profesional: bool = False,
    pct_retencion_anio_anterior: float = 0.0,
    territorio: str = "Comun",
    restricted_mode: bool = False,
) -> dict[str, Any]:
    """
    Wrapper around :class:`Modelo130Calculator` for OpenAI function calling.

    Returns a dict with `success`, `formatted_response` and (on success)
    the calculator output.
    """
    # 1) Restriction guard (Particular plan blocks autónomo content)
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_130 called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response(),
        }

    try:
        if year is None:
            year = datetime.now().year

        if trimestre not in (1, 2, 3, 4):
            return {
                "success": False,
                "error": "Trimestre debe ser 1, 2, 3 o 4",
                "formatted_response": "El trimestre debe ser 1, 2, 3 o 4.",
            }

        calc = Modelo130Calculator(repo=None)

        # 2) Dispensa por retención (Art. 109.2/3 RIRPF + foral Gipuzkoa)
        if (es_profesional or actividad_agraria) and pct_retencion_anio_anterior > 0:
            dispensado = calc.is_dispensado_por_retencion(
                es_profesional=es_profesional,
                pct_retencion_anio_anterior=pct_retencion_anio_anterior,
                territorio=territorio,
                actividad_agraria=actividad_agraria,
            )
            if dispensado:
                threshold = (
                    50.0
                    if (territorio.strip().capitalize() == "Gipuzkoa" and es_profesional)
                    else 70.0
                )
                response = _build_dispensa_response(
                    trimestre=trimestre,
                    year=year,
                    pct=pct_retencion_anio_anterior,
                    territorio=territorio.capitalize(),
                    threshold=threshold,
                )
                logger.info(
                    "Modelo 130: dispensa aplicada (pct=%.1f, territorio=%s)",
                    pct_retencion_anio_anterior,
                    territorio,
                )
                return {
                    "success": True,
                    "dispensado": True,
                    "trimestre": trimestre,
                    "year": year,
                    "territorio": territorio,
                    "pct_retencion_anio_anterior": pct_retencion_anio_anterior,
                    "umbral_dispensa_pct": threshold,
                    "resultado_final": 0.0,
                    "formatted_response": response,
                }

        # 3) Sección II — agrícola
        if actividad_agraria:
            seccion_ii = calc.calculate_agricola(
                quarter=trimestre,
                volumen_ingresos=volumen_ingresos_agrario,
                retenciones_trimestre=retenciones_agrario,
                ceuta_melilla=ceuta_melilla,
            )
            response = _build_seccion_ii_response(
                trimestre=trimestre,
                year=year,
                seccion_ii=seccion_ii,
            )
            logger.info(
                "Modelo 130 sección II: %s, volumen=%s, resultado=%s",
                _TRIMESTRE_LABEL[trimestre],
                volumen_ingresos_agrario,
                seccion_ii["resultado"],
            )
            return {
                "success": True,
                "dispensado": False,
                "trimestre": trimestre,
                "year": year,
                "seccion_ii": seccion_ii,
                "resultado_final": seccion_ii["resultado"],
                "formatted_response": response,
            }

        # 4) Sección I — estimación directa (común / Ceuta-Melilla)
        result = await calc.calculate(
            territory="Comun",
            quarter=trimestre,
            ceuta_melilla=ceuta_melilla,
            ingresos_acumulados=ingresos_computables,
            gastos_acumulados=gastos_deducibles,
            retenciones_acumuladas=retenciones_ingresos_cuenta,
            pagos_anteriores=pagos_fraccionados_anteriores,
            rend_neto_anterior=rendimiento_neto_previo_anual,
            tiene_vivienda_habitual=tiene_vivienda_habitual,
            resultado_anterior_complementaria=resultado_anterior_complementaria,
        )

        casillas = result["casillas"]

        # FIX C1: AEAT defines casilla 05 = pagos previos and casilla 06 =
        # retenciones. The calculator legacy keys are misnamed, so we re-map
        # them here when projecting the public API of the tool.
        casillas_aeat = dict(casillas)
        casillas_aeat["05_pagos_anteriores"] = casillas["06_pagos_anteriores"]
        casillas_aeat["06_retenciones_acumuladas"] = casillas["05_retenciones_acumuladas"]
        # Keep the old keys too for backwards compatibility (1 release window).

        deduccion_80bis = casillas.get("13_deduccion_art80bis", 0.0)
        resultado_final = result["resultado"]

        formatted_response = _build_seccion_i_response(
            trimestre=trimestre,
            year=year,
            casillas=casillas,
            deduccion_80bis=deduccion_80bis,
            resultado_final=resultado_final,
            ceuta_melilla=ceuta_melilla,
        )

        logger.info(
            "Modelo 130 sección I: %s %s, ingresos=%s, gastos=%s, " "neto=%s, resultado=%s",
            _TRIMESTRE_LABEL[trimestre],
            year,
            casillas["01_ingresos_acumulados"],
            casillas["02_gastos_acumulados"],
            casillas["03_rendimiento_neto"],
            resultado_final,
        )

        return {
            "success": True,
            "dispensado": False,
            "trimestre": trimestre,
            "year": year,
            "ceuta_melilla": ceuta_melilla,
            "tipo_aplicado": result["tipo_aplicado"],
            "seccion_i": {
                # Legacy keys kept for backward compatibility with old callers
                "ingresos_computables": casillas["01_ingresos_acumulados"],
                "gastos_deducibles": casillas["02_gastos_acumulados"],
                "rendimiento_neto": casillas["03_rendimiento_neto"],
                "veinte_porciento": casillas["04_cuota_20pct"],
                # AEAT-correct mapping (FIX C1)
                "pagos_anteriores": casillas["06_pagos_anteriores"],
                "retenciones": casillas["05_retenciones_acumuladas"],
                "resultado_seccion": casillas["07_resultado_seccion_I"],
            },
            "casillas": casillas_aeat,
            "deduccion_80bis": deduccion_80bis,
            "casilla_16_vivienda": casillas.get("16_deduccion_vivienda", 0.0),
            "casilla_18_complementaria": casillas.get("18_declaracion_anterior", 0.0),
            "resultado_final": resultado_final,
            "formatted_response": formatted_response,
        }

    except Exception as e:  # pragma: no cover — defensive fallback
        logger.error("Error calculating Modelo 130: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el Modelo 130: {str(e)}",
        }
