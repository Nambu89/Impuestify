"""
Modelo 131 (Pago Fraccionado IRPF Estimación Objetiva — Módulos) Tool.

Thin wrapper around `Modelo131Calculator` (in `app/utils/calculators/modelo_131.py`).
All numeric logic lives in the calculator — the tool only:

  1. Maps OpenAI function-calling parameters to calculator inputs.
  2. Routes to the right apartado (I empresarial, II sin datos-base, III agraria).
  3. Builds a human-readable response for the LLM to forward.

Rule (CLAUDE.md): tools are wrappers, NEVER reimplement calculator logic. This
guarantees that the chat tool, public calculator and PDF generator agree on the
same numbers.

Cobertura:
  - Apartado I  — actividades empresariales en módulos (4/3/2% según asalariados).
  - Apartado II — sin datos-base (2% sobre ingresos del trimestre).
  - Apartado III — actividades agrarias (2% sobre ingresos del trimestre).
  - Reducción 60% Ceuta/Melilla (Art. 110.2 RIRPF).
  - Reducción 60% La Palma (caller debe verificar vigencia anual).
  - Minoración rendimientos bajos (escalonada plana 100/75/50/25 EUR/trim).
  - Plazos AEAT (4T = 1-30 enero, NO 1-20 como erróneamente seedeado).

OUT OF SCOPE en esta versión:
  - Forales (Araba, Bizkaia, Gipuzkoa, Navarra) — usan modelos propios.
  - Cálculo automático del rendimiento neto módulos a partir de los datos-base
    (signos, índices) — el caller debe pasarlo ya calculado vía
    `ModularIncomeCalculator` o input del usuario.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import logging

from app.utils.calculators.modelo_131 import Modelo131Calculator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenAI function-calling schema
# ---------------------------------------------------------------------------

MODELO_131_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_131",
        "description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 131
- Pago fraccionado de IRPF en estimación objetiva (módulos)
- Pago fraccionado trimestral para autónomos en módulos
- Cuanto tengo que pagar de IRPF como autónomo en módulos

NO confundir con Modelo 130 (estimación directa). Si el usuario tributa en
estimación DIRECTA → Modelo 130. Si tributa en estimación OBJETIVA (módulos)
→ Modelo 131.

REGLAS DE INPUT:
- Apartado I (empresarial con datos-base): pasa actividad_tipo='empresarial',
  rendimiento_neto_modulos_anual y num_asalariados (a 1 de enero).
- Apartado II (sin datos-base): actividad_tipo='sin_datos_base' +
  volumen_ingresos_trimestre.
- Apartado III (agrario/ganadero/forestal/pesquero): actividad_tipo='agraria'
  + volumen_ingresos_trimestre.
- num_asalariados a 1 de enero determina el tipo: 0 → 2%, 1 → 3%, ≥2 → 4%.
- Ceuta/Melilla aplica reducción 60% sobre la cuota.
- La Palma aplica reducción 60% (caller debe verificar vigencia anual).
- Si el usuario tributa en estimación directa, NO uses esta función — usa
  calculate_modelo_130 en su lugar.

La función devuelve casillas 01-12 según las instrucciones AEAT y delega en
`Modelo131Calculator` para garantizar coherencia con la calculadora pública
del frontend.""",
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
                "actividad_tipo": {
                    "type": "string",
                    "enum": ["empresarial", "sin_datos_base", "agraria"],
                    "description": (
                        "Apartado del Modelo 131. 'empresarial' = apartado I "
                        "(con datos-base, 4/3/2% según asalariados). "
                        "'sin_datos_base' = apartado II (2% sobre ingresos "
                        "trimestre). 'agraria' = apartado III (agrícola/"
                        "ganadero/forestal/pesquero, 2% sobre ingresos)."
                    ),
                },
                "rendimiento_neto_modulos_anual": {
                    "type": "number",
                    "description": (
                        "Apartado I — Rendimiento neto previo módulos "
                        "ANUALIZADO calculado a partir de los datos-base "
                        "vigentes a 1 de enero (signos, índices). Casilla 01."
                    ),
                },
                "num_asalariados": {
                    "type": "integer",
                    "description": (
                        "Apartado I — Número de personas asalariadas a 1 de "
                        "enero. 0 → tipo 2%; 1 → tipo 3%; ≥2 → tipo 4%."
                    ),
                },
                "volumen_ingresos_trimestre": {
                    "type": "number",
                    "description": (
                        "Apartados II y III — Volumen de ingresos del "
                        "TRIMESTRE, excluyendo subvenciones de capital. "
                        "Casilla 04 (apartado III) o casilla 01 (apartado II)."
                    ),
                },
                "rendimiento_neto_anterior": {
                    "type": "number",
                    "description": (
                        "Rendimiento neto del AÑO ANTERIOR para minoración "
                        "por rendimientos bajos (sólo apartado I). "
                        "Tabla escalonada: ≤9k=100, 9-10k=75, 10-11k=50, "
                        "11-12k=25, >12k=0 EUR/trim."
                    ),
                },
                "retenciones_trimestre": {
                    "type": "number",
                    "description": (
                        "CASILLA 09 — Retenciones e ingresos a cuenta del " "TRIMESTRE."
                    ),
                },
                "pagos_anteriores": {
                    "type": "number",
                    "description": (
                        "CASILLA 10 — Pagos fraccionados ya ingresados en "
                        "trimestres previos del MISMO año. Para 1T siempre 0."
                    ),
                },
                "resultado_anterior_complementaria": {
                    "type": "number",
                    "description": (
                        "CASILLA 11 — Resultado ya ingresado en una "
                        "autoliquidación anterior del mismo trimestre "
                        "(complementaria). Por defecto 0."
                    ),
                },
                "ceuta_melilla": {
                    "type": "boolean",
                    "description": (
                        "True si la actividad se desarrolla en Ceuta o "
                        "Melilla (reducción 60% Art. 110.2 RIRPF)."
                    ),
                },
                "la_palma": {
                    "type": "boolean",
                    "description": (
                        "True si aplica la reducción 60% La Palma. El caller "
                        "debe verificar la vigencia con la Orden anual de "
                        "módulos correspondiente."
                    ),
                },
            },
            "required": ["trimestre", "actividad_tipo"],
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


def _fmt(amount: float) -> str:
    return f"{amount:,.2f}"


def _territorio_label(territory: str) -> str:
    if territory == "Ceuta/Melilla":
        return "Ceuta/Melilla"
    if territory == "La Palma":
        return "La Palma"
    return "territorio común"


def _build_response(
    *,
    trimestre: int,
    year: int,
    apartado: str,
    casillas: Dict[str, float],
    desglose: Dict[str, Any],
    plazo: str,
    territory: str,
    resultado: float,
) -> str:
    """Format the Modelo 131 result as a human-readable response."""
    label = _TRIMESTRE_LABEL[trimestre]
    meses = _TRIMESTRE_MESES[trimestre]
    territorio = _territorio_label(territory)

    lines = [
        f"**Modelo 131 — {label} {year} ({meses}) — {territorio}**",
        "",
    ]

    if apartado == "I":
        criterio = desglose.get("criterio_tipo", "")
        lines.extend(
            [
                "**Apartado I — Actividades empresariales en módulos**",
                f"- Rendimiento neto previo módulos anual [01]: "
                f"{_fmt(casillas['01_rendimiento_neto_modulos'])} EUR",
                f"- Tipo aplicable [02]: {casillas['02_tipo_aplicable']:.1f}% " f"({criterio})",
                f"- Resultado actividades empresariales [03]: "
                f"{_fmt(casillas['03_resultado_empresarial'])} EUR",
            ]
        )
    elif apartado == "III":
        lines.extend(
            [
                "**Apartado III — Actividades agrícolas / ganaderas / forestales / pesqueras**",
                f"- Volumen de ingresos del trimestre [04]: "
                f"{_fmt(casillas['04_volumen_ingresos_agrario'])} EUR",
                f"- Cuota 2% [05]: {_fmt(casillas['05_cuota_agraria'])} EUR",
            ]
        )
    else:  # apartado II
        lines.extend(
            [
                "**Apartado II — Actividad empresarial sin datos-base**",
                f"- Volumen de ingresos del trimestre [01]: "
                f"{_fmt(casillas['01_rendimiento_neto_modulos'])} EUR",
                f"- Tipo aplicable [02]: {casillas['02_tipo_aplicable']:.1f}%",
                f"- Resultado [03]: {_fmt(casillas['03_resultado_empresarial'])} EUR",
            ]
        )

    lines.append("")
    lines.append(f"**Total cuotas [06]: {_fmt(casillas['06_total_cuotas'])} EUR**")

    # Reducciones
    if casillas["07_reducciones"] > 0:
        lines.append(
            f"- Reducciones {desglose['reduccion_concepto']} [07]: "
            f"-{_fmt(casillas['07_reducciones'])} EUR"
        )
        lines.append(
            f"- Resultado tras reducciones [08]: "
            f"{_fmt(casillas['08_resultado_tras_reducciones'])} EUR"
        )

    # Minoraciones
    if casillas["09_retenciones_trimestre"] > 0:
        lines.append(
            f"- Retenciones del trimestre [09]: "
            f"-{_fmt(casillas['09_retenciones_trimestre'])} EUR"
        )
    if casillas["10_pagos_anteriores"] > 0:
        lines.append(
            f"- Pagos fraccionados anteriores [10]: "
            f"-{_fmt(casillas['10_pagos_anteriores'])} EUR"
        )
    if casillas["11_complementaria"] > 0:
        lines.append(
            f"- Resultado autoliquidación anterior [11]: "
            f"-{_fmt(casillas['11_complementaria'])} EUR"
        )

    # Minoración rendimientos bajos (sólo apartado I)
    if apartado == "I" and desglose.get("minoracion_rendimientos_bajos", 0) > 0:
        lines.append(
            f"- Minoración rendimientos bajos: "
            f"-{_fmt(desglose['minoracion_rendimientos_bajos'])} EUR"
        )

    lines.append("")
    lines.append("**Resultado**")
    if resultado > 0:
        lines.append(f"- A ingresar [12]: **{_fmt(resultado)} EUR**")
        lines.append("")
        lines.append(
            f"Plazo: presenta antes del **{plazo}**. "
            "Domiciliación bancaria hasta 5 días antes del vencimiento."
        )
    else:
        lines.append(f"- Resultado [12]: **{_fmt(resultado)} EUR (sin ingreso)**")
        lines.append("")
        lines.append(
            f"Aunque el resultado sea 0, debes presentar el modelo igualmente "
            f"antes del **{plazo}**."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool entry point
# ---------------------------------------------------------------------------


async def calculate_modelo_131_tool(
    trimestre: int,
    actividad_tipo: str = "empresarial",
    year: Optional[int] = None,
    rendimiento_neto_modulos_anual: float = 0.0,
    num_asalariados: int = 0,
    volumen_ingresos_trimestre: float = 0.0,
    rendimiento_neto_anterior: float = 0.0,
    retenciones_trimestre: float = 0.0,
    pagos_anteriores: float = 0.0,
    resultado_anterior_complementaria: float = 0.0,
    ceuta_melilla: bool = False,
    la_palma: bool = False,
    restricted_mode: bool = False,
) -> Dict[str, Any]:
    """
    Wrapper around :class:`Modelo131Calculator` for OpenAI function calling.

    Returns a dict with `success`, `formatted_response` and (on success) the
    calculator output.
    """
    # 1) Restriction guard (Particular plan blocks autónomo content)
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_131 called in restricted_mode — blocking")
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

        if actividad_tipo not in {"empresarial", "sin_datos_base", "agraria"}:
            return {
                "success": False,
                "error": (
                    f"actividad_tipo '{actividad_tipo}' inválido. "
                    "Valores: 'empresarial', 'sin_datos_base', 'agraria'."
                ),
                "formatted_response": (
                    "El tipo de actividad debe ser 'empresarial', " "'sin_datos_base' o 'agraria'."
                ),
            }

        calc = Modelo131Calculator(repo=None)

        result = await calc.calculate(
            quarter=trimestre,
            actividad_tipo=actividad_tipo,
            rendimiento_neto_modulos_anual=rendimiento_neto_modulos_anual,
            num_asalariados=num_asalariados,
            volumen_ingresos_trimestre=volumen_ingresos_trimestre,
            rendimiento_neto_anterior=rendimiento_neto_anterior,
            retenciones_trimestre=retenciones_trimestre,
            pagos_anteriores=pagos_anteriores,
            resultado_anterior_complementaria=resultado_anterior_complementaria,
            ceuta_melilla=ceuta_melilla,
            la_palma=la_palma,
        )

        formatted_response = _build_response(
            trimestre=trimestre,
            year=year,
            apartado=result["apartado"],
            casillas=result["casillas"],
            desglose=result["desglose"],
            plazo=result["plazo"],
            territory=result["territory"],
            resultado=result["resultado"],
        )

        logger.info(
            "Modelo 131 apartado %s: %s %s, actividad=%s, resultado=%s",
            result["apartado"],
            _TRIMESTRE_LABEL[trimestre],
            year,
            actividad_tipo,
            result["resultado"],
        )

        return {
            "success": True,
            "trimestre": trimestre,
            "year": year,
            "apartado": result["apartado"],
            "actividad_tipo": result["actividad_tipo"],
            "territory": result["territory"],
            "tipo_aplicado": result["tipo_aplicado"],
            "casillas": result["casillas"],
            "desglose": result["desglose"],
            "resultado_final": result["resultado"],
            "plazo": result["plazo"],
            "formatted_response": formatted_response,
        }

    except ValueError as ve:
        logger.warning("Modelo 131 input error: %s", ve)
        return {
            "success": False,
            "error": str(ve),
            "formatted_response": f"Error en los datos: {str(ve)}",
        }
    except Exception as e:  # pragma: no cover — defensive fallback
        logger.error("Error calculating Modelo 131: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el Modelo 131: {str(e)}",
        }
