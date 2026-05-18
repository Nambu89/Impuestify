"""
Modelo 450 (AIEM Canarias) Calculator Tool for TaxIA.

Wrapper LLM sobre Modelo450Calculator. SIEMPRE delega al calculator
canonico — NO reimplementa logica numerica (regla obligatoria
backend/CLAUDE.md "Tool LLM = wrapper del calculator").

Modelo 450 = autoliquidacion AIEM trimestral de productores canarios
con bienes en la lista AIEM (Anexo IV TR Decreto Legislativo 1/2025).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


MODELO_450_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_450",
        "description": (
            "USA ESTA FUNCION cuando el usuario pregunte sobre:\n"
            "- AIEM (Arbitrio sobre Importaciones y Entregas de Mercancias en Canarias)\n"
            "- Modelo 450 (autoliquidacion trimestral AIEM de productores canarios)\n"
            "- 'cuanto AIEM tengo que pagar' siendo productor en Canarias\n"
            "- Liquidacion AIEM por bienes producidos localmente\n\n"
            "OBLIGATORIO si el usuario es productor canario en epigrafes IAE "
            "incluidos en la lista AIEM (Anexo IV TR Decreto Legislativo 1/2025).\n\n"
            "Tipos AIEM vigentes: 5 % (reducido), 10 % (intermedio), "
            "15 % (general), 25 % (tabaco). Periodicidad trimestral en "
            "regimen general (mensual para grandes empresas > 6,01 M EUR).\n\n"
            "AIEM NO se calcula con IPSI (Ceuta/Melilla) ni con IGIC (Modelo 420). "
            "AIEM es un impuesto monofasico aparte: solo lo paga el productor, "
            "no es deducible en la cadena."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "trimestre": {
                    "type": "integer",
                    "description": "Trimestre (1-4). Ignorado si periodicidad='mensual'.",
                },
                "year": {
                    "type": "integer",
                    "description": "Ano fiscal. Por defecto: ano actual.",
                },
                "bienes_producidos": {
                    "type": "array",
                    "description": (
                        "Lista de bienes producidos en el periodo. Cada bien: "
                        "{epigrafe_iae, descripcion, base_imponible, tipo_aiem (opcional)}. "
                        "Si no se indica tipo_aiem, se intenta lookup por epigrafe."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "epigrafe_iae": {
                                "type": "string",
                                "description": "Epigrafe IAE del bien (opcional pero recomendado).",
                            },
                            "descripcion": {
                                "type": "string",
                                "description": "Descripcion breve del bien (opcional).",
                            },
                            "base_imponible": {
                                "type": "number",
                                "description": "Base imponible del bien (importe de la entrega).",
                            },
                            "tipo_aiem": {
                                "type": "number",
                                "description": (
                                    "Tipo AIEM en decimal (0.05 / 0.10 / 0.15 / 0.25). "
                                    "Si se omite y hay epigrafe, se hace lookup."
                                ),
                            },
                        },
                        "required": ["base_imponible"],
                    },
                },
                "cuotas_compensar_anteriores": {
                    "type": "number",
                    "description": (
                        "Cuotas a compensar de periodos anteriores (>= 0). " "Por defecto: 0."
                    ),
                },
                "rectificacion_bases": {
                    "type": "number",
                    "description": "Rectificacion de bases de periodos anteriores. Por defecto: 0.",
                },
                "rectificacion_cuotas": {
                    "type": "number",
                    "description": "Rectificacion de cuotas de periodos anteriores. Por defecto: 0.",
                },
                "regularizacion_anual": {
                    "type": "number",
                    "description": "Regularizacion anual (solo se aplica en T4). Por defecto: 0.",
                },
                "periodicidad": {
                    "type": "string",
                    "enum": ["trimestral", "mensual"],
                    "description": (
                        "trimestral (default) | mensual (grandes empresas, "
                        "volumen > 6.010.121,04 EUR ano anterior)."
                    ),
                },
                "mes": {
                    "type": "integer",
                    "description": "Mes (1-12). Solo si periodicidad='mensual'.",
                },
            },
            "required": ["trimestre", "bienes_producidos"],
        },
    },
}


def _format_for_llm(result: Dict[str, Any]) -> str:
    """Formatea el resultado del calculator para presentacion al usuario."""
    lines: List[str] = []
    periodo = result["periodo_label"]
    year = result["year"]
    plazo = result["plazo_presentacion"]

    if result["periodicidad"] == "trimestral":
        meses_q = {
            "T1": "enero-marzo",
            "T2": "abril-junio",
            "T3": "julio-septiembre",
            "T4": "octubre-diciembre",
        }
        sub = meses_q.get(periodo, "")
        lines.append(f"**AIEM Canarias — Modelo 450 {periodo} {year} ({sub})**")
    else:
        meses = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        mes_idx = result.get("mes") or 1
        lines.append(f"**AIEM Canarias — Modelo 450 {meses[mes_idx-1]} {year} (mensual)**")

    lines.append("")

    # Desglose por bien
    lines.append("**Bienes producidos sujetos a AIEM**")
    bienes = result.get("desglose_bienes", [])
    if not bienes:
        lines.append("- Sin operaciones declaradas.")
    for b in bienes:
        epi = b.get("epigrafe_iae") or "—"
        desc = b.get("descripcion") or "(sin descripcion)"
        base = b.get("base_imponible", 0.0)
        tipo = b.get("tipo_aiem")
        cuota = b.get("cuota_aiem", 0.0)
        if tipo is None:
            lines.append(
                f"- #{b['indice']} {desc} (IAE {epi}): "
                f"base {base:,.2f} EUR — TIPO DESCONOCIDO (revisa)"
            )
        else:
            origen = b.get("origen_tipo", "manual")
            lines.append(
                f"- #{b['indice']} {desc} (IAE {epi}): "
                f"base {base:,.2f} EUR x {tipo*100:.1f} % "
                f"({origen}) = {cuota:,.2f} EUR"
            )

    lines.append("")
    lines.append(f"- **Total base imponible: {result['total_base_imponible']:,.2f} EUR**")
    lines.append(f"- **Cuota AIEM devengada: {result['total_cuota_devengada']:,.2f} EUR**")

    if result.get("rectificacion_cuotas"):
        lines.append(f"- Rectificacion cuotas: {result['rectificacion_cuotas']:,.2f} EUR")
    if result.get("cuotas_compensar_anteriores"):
        lines.append(
            f"- Compensacion periodos anteriores: "
            f"-{result['cuotas_compensar_anteriores']:,.2f} EUR"
        )
    if result.get("regularizacion_anual"):
        lines.append(f"- Regularizacion anual (T4): " f"{result['regularizacion_anual']:,.2f} EUR")

    resultado = result["resultado_liquidacion"]
    if resultado > 0:
        tipo_resultado = "A ingresar"
    elif resultado < 0:
        tipo_resultado = (
            "A devolver" if periodo == "T4" or result["periodicidad"] == "anual" else "A compensar"
        )
    else:
        tipo_resultado = "Sin actividad"

    lines.append("")
    lines.append(f"**Resultado: {resultado:,.2f} EUR — {tipo_resultado}**")

    lines.append("")
    if resultado > 0:
        lines.append(f"Plazo de presentacion: {plazo} (Agencia Tributaria Canaria — ATC).")
    elif resultado < 0 and periodo not in ("T4",) and result["periodicidad"] == "trimestral":
        lines.append(
            f"El resultado negativo de {abs(resultado):,.2f} EUR se compensa "
            "en el siguiente trimestre."
        )
    elif resultado < 0:
        lines.append(f"Puedes solicitar la devolucion de {abs(resultado):,.2f} EUR a la ATC.")

    # Warnings
    warnings = result.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append("**Avisos**")
        for w in warnings:
            lines.append(f"- {w}")

    lines.append("")
    lines.append(
        "Nota: AIEM es un impuesto monofasico — solo lo declara el productor "
        "(no se compensa con AIEM soportado). La asignacion exacta epigrafe IAE "
        "→ tipo AIEM debe verificarse en el Anexo IV TR Decreto Legislativo 1/2025."
    )

    return "\n".join(lines)


async def calculate_modelo_450_tool(
    trimestre: int,
    bienes_producidos: List[Dict[str, Any]],
    year: Optional[int] = None,
    cuotas_compensar_anteriores: float = 0.0,
    rectificacion_bases: float = 0.0,
    rectificacion_cuotas: float = 0.0,
    regularizacion_anual: float = 0.0,
    periodicidad: str = "trimestral",
    mes: Optional[int] = None,
    restricted_mode: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Tool wrapper para Modelo 450 (AIEM productores canarios).

    Args:
        restricted_mode: si True (usuario plan Particular) bloquea — el AIEM
            es operacion exclusiva de productores (autonomos / sociedades).
    """
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_450 called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response(),
        }

    try:
        if year is None:
            year = datetime.now().year

        if periodicidad == "trimestral" and trimestre not in (1, 2, 3, 4):
            return {
                "success": False,
                "error": "trimestre invalido",
                "formatted_response": "El trimestre debe ser 1, 2, 3 o 4.",
            }
        if periodicidad == "mensual":
            if mes is None or mes not in range(1, 13):
                return {
                    "success": False,
                    "error": "mes invalido",
                    "formatted_response": ("Para periodicidad mensual indica el mes (1-12)."),
                }

        if not isinstance(bienes_producidos, list) or not bienes_producidos:
            return {
                "success": False,
                "error": "bienes_producidos vacio",
                "formatted_response": (
                    "Indica al menos un bien producido sujeto a AIEM "
                    "(epigrafe IAE, base imponible y tipo AIEM)."
                ),
            }

        from app.utils.calculators.modelo_450 import Modelo450Calculator

        calc = Modelo450Calculator(None)
        result = await calc.calculate(
            bienes_producidos=bienes_producidos,
            cuotas_compensar_anteriores=max(0.0, float(cuotas_compensar_anteriores)),
            rectificacion_bases=float(rectificacion_bases),
            rectificacion_cuotas=float(rectificacion_cuotas),
            regularizacion_anual=float(regularizacion_anual),
            quarter=int(trimestre),
            year=int(year),
            periodicidad=periodicidad,
            mes=mes,
        )

        formatted = _format_for_llm(result)

        logger.info(
            "Modelo 450 calculated: %s %s, devengado=%s, resultado=%s",
            result["periodo_label"],
            year,
            result["total_cuota_devengada"],
            result["resultado_liquidacion"],
        )

        return {
            "success": True,
            **result,
            "formatted_response": formatted,
        }

    except ValueError as e:
        logger.warning("Modelo 450 validation error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular AIEM (Modelo 450): {e}",
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Modelo 450 calculation error: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular AIEM (Modelo 450): {e}",
        }
