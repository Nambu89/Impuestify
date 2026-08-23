"""
Modelo 130 Foral Tool — wrapper único para los modelos 130 propios de los
territorios forales (Bizkaia, Gipuzkoa, Araba/Álava, Navarra).

Detecta el territorio del input y delega en el calculator foral correspondiente.
NO reimplementa lógica numérica (regla CLAUDE.md: tools = wrappers).

Casos de uso:
  - Autónomo en Bilbao quiere calcular pago fraccionado del 1T → Bizkaia.
  - Profesional en Donostia con dispensa por retención ≥ 50 % → Gipuzkoa
    (devuelve dispensa).
  - Autónomo en Vitoria con datos trimestrales → Araba.
  - Autónomo en Pamplona modalidad segunda con datos acumulados → Navarra.

NOTE: el Modelo 130 estatal (territorio común + Ceuta/Melilla) sigue
disponible en `modelo_130_tool.py`. Este wrapper foral NO lo reemplaza.
"""

import logging
from datetime import datetime
from typing import Any

from app.utils.calculators.modelo_130_araba import Modelo130ArabaCalculator
from app.utils.calculators.modelo_130_bizkaia import Modelo130BizkaiaCalculator
from app.utils.calculators.modelo_130_gipuzkoa import Modelo130GipuzkoaCalculator
from app.utils.calculators.modelo_130_navarra import Modelo130NavarraCalculator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenAI function-calling schema
# ---------------------------------------------------------------------------

MODELO_130_FORAL_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_130_foral",
        "description": (
            "SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario es autónomo en "
            "un territorio FORAL (Bizkaia, Gipuzkoa, Araba/Álava o Navarra) y "
            "pregunta por su pago fraccionado de IRPF / Modelo 130. Cada "
            "territorio foral tiene su propio Modelo 130 con casillas y reglas "
            "distintas del Modelo 130 estatal (territorio común). Esta "
            "herramienta detecta el territorio y delega en el calculator "
            "correcto. NO usar para territorio común — usa "
            "`calculate_modelo_130` en su lugar."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "territorio": {
                    "type": "string",
                    "description": (
                        "Territorio foral. Valores admitidos: 'Bizkaia', "
                        "'Gipuzkoa', 'Araba' (alias 'Alava'), 'Navarra'."
                    ),
                },
                "trimestre": {
                    "type": "integer",
                    "description": "Trimestre (1, 2, 3 o 4).",
                },
                "year": {
                    "type": "integer",
                    "description": "Año fiscal. Por defecto: año actual.",
                },
                # Bizkaia / Gipuzkoa
                "regimen": {
                    "type": "string",
                    "description": (
                        "Bizkaia / Gipuzkoa: 'general' (≥ 3.er año, rend. "
                        "penúltimo > 0) o 'excepcional' (años 1-2 o rend. "
                        "penúltimo ≤ 0). Por defecto: 'general'."
                    ),
                },
                "anos_actividad": {
                    "type": "integer",
                    "description": (
                        "Bizkaia: años completos de actividad. <3 → reglas de "
                        "los primeros 2 años (datos acumulados, 20%)."
                    ),
                },
                # Datos del penúltimo año (Bizkaia general, Gipuzkoa general,
                # Navarra modalidad primera)
                "rend_neto_penultimo": {
                    "type": "number",
                    "description": (
                        "Rendimiento neto del PENÚLTIMO año. Necesario en "
                        "Bizkaia/Gipuzkoa régimen general y Navarra modalidad "
                        "primera."
                    ),
                },
                "retenciones_penultimo": {
                    "type": "number",
                    "description": (
                        "Retenciones e ingresos a cuenta del penúltimo año. "
                        "Necesario en Bizkaia/Gipuzkoa general y Navarra primera."
                    ),
                },
                "volumen_ventas_penultimo": {
                    "type": "number",
                    "description": (
                        "Bizkaia régimen excepcional: volumen de ventas del "
                        "penúltimo año (cuando rend. neto fue ≤ 0)."
                    ),
                },
                # Datos trimestrales (Gipuzkoa excepcional)
                "volumen_operaciones_trimestre": {
                    "type": "number",
                    "description": (
                        "Gipuzkoa régimen excepcional: volumen de operaciones del trimestre."
                    ),
                },
                "retenciones_trimestre": {
                    "type": "number",
                    "description": (
                        "Retenciones del TRIMESTRE. Necesario en Gipuzkoa excepcional y Araba."
                    ),
                },
                # Araba (datos trimestrales)
                "ingresos_trimestre": {
                    "type": "number",
                    "description": "Araba: ingresos del trimestre.",
                },
                "gastos_trimestre": {
                    "type": "number",
                    "description": "Araba: gastos deducibles del trimestre.",
                },
                "pagos_anteriores": {
                    "type": "number",
                    "description": (
                        "Pagos fraccionados ya ingresados en trimestres "
                        "anteriores del mismo ejercicio. Aplicable en Araba, "
                        "Bizkaia primeros 2 años y Navarra segunda."
                    ),
                },
                # Datos acumulados (Bizkaia primeros 2 años, Navarra segunda)
                "ingresos_acumulados": {
                    "type": "number",
                    "description": (
                        "Ingresos acumulados desde 1 enero. Bizkaia primeros 2 "
                        "años y Navarra modalidad segunda."
                    ),
                },
                "gastos_acumulados": {
                    "type": "number",
                    "description": (
                        "Gastos acumulados desde 1 enero. Bizkaia primeros 2 "
                        "años y Navarra modalidad segunda."
                    ),
                },
                "retenciones_acumuladas": {
                    "type": "number",
                    "description": (
                        "Retenciones acumuladas desde 1 enero. Bizkaia "
                        "primeros 2 años y Navarra modalidad segunda."
                    ),
                },
                # Navarra
                "modalidad": {
                    "type": "string",
                    "description": (
                        "Navarra: 'primera' (penúltimo año + tabla progresiva, "
                        "÷4) o 'segunda' (acumulado del ejercicio). Por "
                        "defecto: 'segunda'."
                    ),
                },
                # Dispensa Gipuzkoa
                "es_profesional": {
                    "type": "boolean",
                    "description": (
                        "Gipuzkoa: True si actividad profesional (IAE 2/3). "
                        "Necesario para evaluar dispensa ≥ 50 %."
                    ),
                },
                "actividad_agraria": {
                    "type": "boolean",
                    "description": (
                        "Gipuzkoa: True si actividad agrícola/ganadera. Dispensa ≥ 70 %."
                    ),
                },
                "pct_retencion_anio_anterior": {
                    "type": "number",
                    "description": (
                        "Gipuzkoa: % (0-100) de ingresos sometidos a retención "
                        "el año anterior. ≥ 50 % (profesionales) o ≥ 70 % "
                        "(agrarios) → DISPENSADO de presentar."
                    ),
                },
            },
            "required": ["territorio", "trimestre"],
        },
    },
}


# ---------------------------------------------------------------------------
# Territory normalisation
# ---------------------------------------------------------------------------

_TERRITORY_ALIASES = {
    "bizkaia": "bizkaia",
    "vizcaya": "bizkaia",
    "biscay": "bizkaia",
    "gipuzkoa": "gipuzkoa",
    "guipuzcoa": "gipuzkoa",
    "guipuzkoa": "gipuzkoa",
    "araba": "araba",
    "alava": "araba",
    "alaba": "araba",
    "navarra": "navarra",
    "nafarroa": "navarra",
}

_FORAL_TERRITORIES = {"bizkaia", "gipuzkoa", "araba", "navarra"}


def _normalize_territory(territory: str) -> str:
    """Normalise foral territory name to canonical lowercase key."""
    if not territory:
        raise ValueError("territorio es obligatorio")
    key = territory.strip().lower()
    # Strip accents (Álava → alava, etc.)
    import unicodedata

    key = "".join(c for c in unicodedata.normalize("NFD", key) if unicodedata.category(c) != "Mn")
    if key not in _TERRITORY_ALIASES:
        raise ValueError(
            f"Territorio '{territory}' no soportado por el wrapper foral. "
            f"Valores: Bizkaia, Gipuzkoa, Araba/Álava, Navarra. "
            f"Para territorio común usa `calculate_modelo_130`."
        )
    return _TERRITORY_ALIASES[key]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_TRIMESTRE_LABEL = {1: "1T", 2: "2T", 3: "3T", 4: "4T"}


def _fmt(amount: float) -> str:
    """Formatea en estilo español: 1.234,56 (no 1,234.56).

    La respuesta va directa al usuario en castellano: el punto es el separador
    de millares y la coma el decimal. Mismo helper que en `modelo_131_tool`.
    """
    formatted = f"{abs(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-{formatted}" if amount < 0 else formatted


def _build_dispensa_response(
    *,
    trimestre: int,
    year: int,
    pct: float,
    threshold: float,
    territorio_label: str,
) -> str:
    label = _TRIMESTRE_LABEL[trimestre]
    return (
        f"**Modelo 130 — {territorio_label} — {label} {year} — DISPENSA**\n\n"
        f"Con un {pct:.1f}% de tus ingresos sometidos a retención el año "
        f"anterior (umbral aplicable {threshold:.0f}% en {territorio_label}), "
        f"**no estás obligado a presentar el Modelo 130** este trimestre.\n\n"
        f"Base legal: Norma Foral del IRPF de Gipuzkoa. Si tu situación cambia "
        f"durante el año, revisa el porcentaje real para no incurrir en "
        f"infracción."
    )


def _build_response(
    *,
    territorio_label: str,
    trimestre: int,
    year: int,
    result: dict[str, Any],
) -> str:
    label = _TRIMESTRE_LABEL[trimestre]
    plazo = result.get("plazo", "")
    resultado = result["resultado"]
    tipo = result.get("tipo_aplicado", 0)

    lines = [
        f"**Modelo 130 — {territorio_label} — {label} {year}**",
        "",
        f"Tipo aplicado: {tipo}%.",
    ]
    if "regimen" in result:
        lines.append(f"Régimen: {result['regimen']}.")
    if "modalidad" in result:
        lines.append(f"Modalidad: {result['modalidad']}.")
    if result.get("anos_actividad") is not None:
        lines.append(f"Años de actividad: {result['anos_actividad']}.")

    lines.append("")
    lines.append("**Casillas**")
    for k, v in result.get("casillas", {}).items():
        if isinstance(v, (int, float)):
            lines.append(f"- {k}: {_fmt(v)} EUR")
        else:
            lines.append(f"- {k}: {v}")

    lines.append("")
    if resultado > 0:
        lines.append(f"**Resultado a ingresar: {_fmt(resultado)} EUR**")
    else:
        lines.append("**Resultado: 0,00 EUR (sin ingreso)**")

    if plazo:
        lines.append("")
        lines.append(f"Plazo de presentación: **{plazo}**.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool entry point
# ---------------------------------------------------------------------------


async def calculate_modelo_130_foral_tool(
    territorio: str,
    trimestre: int,
    year: int | None = None,
    # Bizkaia / Gipuzkoa
    regimen: str = "general",
    anos_actividad: int = 3,
    rend_neto_penultimo: float = 0.0,
    retenciones_penultimo: float = 0.0,
    volumen_ventas_penultimo: float = 0.0,
    volumen_operaciones_trimestre: float = 0.0,
    retenciones_trimestre: float = 0.0,
    # Araba
    ingresos_trimestre: float = 0.0,
    gastos_trimestre: float = 0.0,
    pagos_anteriores: float = 0.0,
    # Bizkaia primeros 2 años / Navarra segunda
    ingresos_acumulados: float = 0.0,
    gastos_acumulados: float = 0.0,
    retenciones_acumuladas: float = 0.0,
    # Navarra
    modalidad: str = "segunda",
    # Dispensa Gipuzkoa
    es_profesional: bool = False,
    actividad_agraria: bool = False,
    pct_retencion_anio_anterior: float = 0.0,
    restricted_mode: bool = False,
) -> dict[str, Any]:
    """
    Wrapper único para los 4 calculadores forales del Modelo 130.

    Returns dict con `success`, `formatted_response` y (si success) los datos
    devueltos por el calculator concreto.
    """
    # Restriction guard (planes Particular bloquean autónomo)
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_130_foral called in restricted_mode — blocking")
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
                "error": "trimestre_invalido",
                "formatted_response": "El trimestre debe ser 1, 2, 3 o 4.",
            }

        territory_key = _normalize_territory(territorio)
        territorio_label = {
            "bizkaia": "Bizkaia",
            "gipuzkoa": "Gipuzkoa",
            "araba": "Araba/Álava",
            "navarra": "Navarra",
        }[territory_key]

        # ---------------------------------------------------------------
        # Gipuzkoa: dispensa por retención (Norma Foral)
        # ---------------------------------------------------------------
        if (
            territory_key == "gipuzkoa"
            and (es_profesional or actividad_agraria)
            and pct_retencion_anio_anterior > 0
        ):
            dispensado = Modelo130GipuzkoaCalculator.is_dispensado_por_retencion(
                es_profesional=es_profesional,
                actividad_agraria=actividad_agraria,
                pct_retencion_anio_anterior=pct_retencion_anio_anterior,
            )
            if dispensado:
                threshold = 50.0 if es_profesional and not actividad_agraria else 70.0
                response = _build_dispensa_response(
                    trimestre=trimestre,
                    year=year,
                    pct=pct_retencion_anio_anterior,
                    threshold=threshold,
                    territorio_label=territorio_label,
                )
                logger.info(
                    "Modelo 130 Gipuzkoa: dispensa aplicada (pct=%.1f)",
                    pct_retencion_anio_anterior,
                )
                return {
                    "success": True,
                    "dispensado": True,
                    "territorio": territorio_label,
                    "trimestre": trimestre,
                    "year": year,
                    "pct_retencion_anio_anterior": pct_retencion_anio_anterior,
                    "umbral_dispensa_pct": threshold,
                    "resultado_final": 0.0,
                    "formatted_response": response,
                }

        # ---------------------------------------------------------------
        # Delegación al calculator foral correspondiente
        # ---------------------------------------------------------------
        if territory_key == "bizkaia":
            calc = Modelo130BizkaiaCalculator(repo=None)
            result = await calc.calculate(
                quarter=trimestre,
                anos_actividad=anos_actividad,
                regimen=regimen,
                rend_neto_penultimo=rend_neto_penultimo,
                retenciones_penultimo=retenciones_penultimo,
                volumen_ventas_penultimo=volumen_ventas_penultimo,
                ingresos_acumulados=ingresos_acumulados,
                gastos_acumulados=gastos_acumulados,
                retenciones_acumuladas=retenciones_acumuladas,
                pagos_anteriores=pagos_anteriores,
            )
        elif territory_key == "gipuzkoa":
            calc = Modelo130GipuzkoaCalculator(repo=None)
            result = await calc.calculate(
                quarter=trimestre,
                regimen=regimen,
                rend_neto_penultimo=rend_neto_penultimo,
                retenciones_penultimo=retenciones_penultimo,
                volumen_operaciones_trimestre=volumen_operaciones_trimestre,
                retenciones_trimestre=retenciones_trimestre,
            )
        elif territory_key == "araba":
            calc = Modelo130ArabaCalculator(repo=None)
            result = await calc.calculate(
                quarter=trimestre,
                ingresos_trimestre=ingresos_trimestre,
                gastos_trimestre=gastos_trimestre,
                retenciones_trimestre=retenciones_trimestre,
                pagos_anteriores=pagos_anteriores,
            )
        else:  # navarra
            calc = Modelo130NavarraCalculator(repo=None)
            result = await calc.calculate(
                quarter=trimestre,
                modalidad=modalidad,
                rend_neto_penultimo=rend_neto_penultimo,
                retenciones_penultimo=retenciones_penultimo,
                ingresos_acumulados=ingresos_acumulados,
                gastos_acumulados=gastos_acumulados,
                retenciones_acumuladas=retenciones_acumuladas,
                pagos_anteriores=pagos_anteriores,
            )

        formatted = _build_response(
            territorio_label=territorio_label,
            trimestre=trimestre,
            year=year,
            result=result,
        )

        logger.info(
            "Modelo 130 foral: territorio=%s, %s %s, resultado=%s",
            territorio_label,
            _TRIMESTRE_LABEL[trimestre],
            year,
            result["resultado"],
        )

        return {
            "success": True,
            "dispensado": False,
            "territorio": territorio_label,
            "territorio_key": territory_key,
            "trimestre": trimestre,
            "year": year,
            "tipo_aplicado": result.get("tipo_aplicado"),
            "regimen": result.get("regimen"),
            "modalidad": result.get("modalidad"),
            "casillas": result.get("casillas", {}),
            "desglose": result.get("desglose", {}),
            "plazo": result.get("plazo"),
            "resultado_final": result["resultado"],
            "formatted_response": formatted,
        }

    except ValueError as e:
        logger.warning("Modelo 130 foral input error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error en los datos del Modelo 130 foral: {e}",
        }
    except Exception as e:  # pragma: no cover — defensive
        logger.error("Error calculating Modelo 130 foral: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el Modelo 130 foral: {e}",
        }
