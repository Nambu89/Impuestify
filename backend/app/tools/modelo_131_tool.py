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

import logging
from datetime import datetime
from typing import Any

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

La función devuelve las casillas del modelo según el diseño de registro
oficial DR131_2026 de la AEAT y delega en `Modelo131Calculator` para
garantizar coherencia con la calculadora pública del frontend.""",
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
                        "Casilla 05 (apartado III) o casilla 03 (apartado II)."
                    ),
                },
                "rendimiento_neto_anterior": {
                    "type": "number",
                    "description": (
                        "Dato de partida de la CASILLA 09 (la [09] es la "
                        "minoración ya calculada) — Rendimiento neto de actividades "
                        "económicas del EJERCICIO ANTERIOR (art. 110.3.c "
                        "RIRPF, sólo apartado I). Si ≤ 12.000 EUR aplica una "
                        "minoración escalonada plana (≤9k=100, 9-10k=75, "
                        "10-11k=50, 11-12k=25 EUR/trim). NO lo inventes ni lo "
                        "pongas a 0: si el usuario no lo ha dicho, OMITE el "
                        "parámetro y no se aplicará minoración alguna."
                    ),
                },
                "retenciones_trimestre": {
                    "type": "number",
                    "description": ("CASILLA 08 — Retenciones e ingresos a cuenta del TRIMESTRE."),
                },
                "resultado_anterior_complementaria": {
                    "type": "number",
                    "description": (
                        "CASILLA 14 — Resultado a ingresar de las anteriores "
                        "declaraciones: lo ya ingresado en una autoliquidación "
                        "anterior del mismo trimestre (complementaria). "
                        "Por defecto 0."
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
    """Formatea en estilo espanol: 1.234,56 (no 1,234.56)."""
    formatted = f"{abs(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{formatted}" if amount < 0 else formatted


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
    casillas: dict[str, float],
    desglose: dict[str, Any],
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

    # Los números entre corchetes son los del diseño de registro oficial
    # DR131_2026 de la AEAT, NO el prefijo de la clave del dict (ver la tabla
    # de equivalencias en el docstring de `Modelo131Calculator`).
    if apartado == "I":
        criterio = desglose.get("criterio_tipo", "")
        lines.extend(
            [
                "**Apartado I — Actividades empresariales en módulos**",
                f"- Suma de rendimientos netos [01]: "
                f"{_fmt(casillas['01_rendimiento_neto_modulos'])} EUR",
                f"- Porcentaje aplicable: {casillas['02_tipo_aplicable']:.0f}% ({criterio})",
                f"- Pago fraccionado previo: suma de resultados [02]: "
                f"{_fmt(casillas['03_resultado_empresarial'])} EUR",
            ]
        )
    elif apartado == "III":
        lines.extend(
            [
                "**Apartado III — Actividades agrícolas / ganaderas / forestales / pesqueras**",
                f"- Volumen de ingresos del trimestre [05]: "
                f"{_fmt(casillas['04_volumen_ingresos_agrario'])} EUR",
                f"- Pago fraccionado previo del trimestre, 2% [06]: "
                f"{_fmt(casillas['05_cuota_agraria'])} EUR",
            ]
        )
    else:  # apartado II
        lines.extend(
            [
                "**Apartado II — Actividad empresarial sin datos-base**",
                f"- Volumen de ventas o ingresos [03]: "
                f"{_fmt(casillas['01_rendimiento_neto_modulos'])} EUR",
                f"- Porcentaje aplicable: {casillas['02_tipo_aplicable']:.0f}%",
                f"- Pago fraccionado previo [04]: {_fmt(casillas['03_resultado_empresarial'])} EUR",
            ]
        )

    lines.append("")
    lines.append(
        f"**Suma de los pagos fraccionados previos del trimestre [07]: "
        f"{_fmt(casillas['06_total_cuotas'])} EUR**"
    )

    # Reducciones territoriales — no tienen casilla propia en el modelo: la
    # AEAT las incorpora al porcentaje aplicable de cada actividad.
    if casillas["07_reducciones"] > 0:
        lines.append(
            f"- Reducciones {desglose['reduccion_concepto']}: "
            f"-{_fmt(casillas['07_reducciones'])} EUR"
        )
        lines.append(
            f"- Resultado tras reducciones: {_fmt(casillas['08_resultado_tras_reducciones'])} EUR"
        )

    # Minoraciones
    if casillas["09_retenciones_trimestre"] > 0:
        lines.append(
            f"- A deducir: retenciones e ingresos a cuenta [08]: "
            f"-{_fmt(casillas['09_retenciones_trimestre'])} EUR"
        )

    # Minoración rendimientos bajos (sólo apartado I) — casilla [09]
    if apartado == "I" and desglose.get("minoracion_rendimientos_bajos", 0) > 0:
        lines.append(
            f"- Minoración por aplicación de la deducción del art. 110.3.c) "
            f"RIRPF [09]: -{_fmt(desglose['minoracion_rendimientos_bajos'])} EUR"
        )

    # Aquí NO va una línea de "pagos fraccionados de trimestres anteriores":
    # el 131 no es acumulativo y no existe tal deducción (art. 110.1.b RIRPF,
    # y no hay casilla en el DR131). Ver el docstring de `modelo_131.py`.
    if casillas["11_complementaria"] > 0:
        lines.append(
            f"- A deducir: resultado a ingresar de las anteriores "
            f"declaraciones [14]: -{_fmt(casillas['11_complementaria'])} EUR"
        )

    lines.append("")
    lines.append("**Resultado**")
    if resultado > 0:
        lines.append(f"- A ingresar [15]: **{_fmt(resultado)} EUR**")
        lines.append("")
        lines.append(
            f"Plazo: presenta antes del **{plazo}**. "
            "Domiciliación bancaria hasta 5 días antes del vencimiento."
        )
    else:
        lines.append(f"- Resultado [15]: **{_fmt(resultado)} EUR (sin ingreso)**")
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
    year: int | None = None,
    rendimiento_neto_modulos_anual: float = 0.0,
    num_asalariados: int = 0,
    volumen_ingresos_trimestre: float = 0.0,
    # None = el usuario NO ha facilitado el dato → sin minoración casilla [09]
    # (art. 110.3.c RIRPF). Un 0.0 explícito sí aplica el primer tramo.
    rendimiento_neto_anterior: float | None = None,
    retenciones_trimestre: float = 0.0,
    resultado_anterior_complementaria: float = 0.0,
    ceuta_melilla: bool = False,
    la_palma: bool = False,
    restricted_mode: bool = False,
    **_ignored: Any,
) -> dict[str, Any]:
    """
    Wrapper around :class:`Modelo131Calculator` for OpenAI function calling.

    Returns a dict with `success`, `formatted_response` and (on success) the
    calculator output.

    `**_ignored` absorbe los argumentos que el modelo pueda inventarse o
    arrastrar de una conversación previa — en particular `pagos_anteriores`,
    retirado por no existir en el 131 (ver el docstring de `modelo_131.py`).
    El despachador llama a este ejecutor con `**function_args` sin filtrar, así
    que un argumento de más provocaría un `TypeError` en vez de una respuesta.
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
                    "El tipo de actividad debe ser 'empresarial', 'sin_datos_base' o 'agraria'."
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
