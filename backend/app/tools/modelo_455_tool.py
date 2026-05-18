"""
Modelo 455 (AIEM ZEC) Calculator Tool for TaxIA.

Wrapper LLM sobre Modelo455Calculator. SIEMPRE delega al calculator
canonico — NO reimplementa logica numerica.

Modelo 455 = autoliquidacion AIEM de operadores ZEC (Zona Especial
Canaria) que producen / entregan mercancias en Canarias. Periodicidad
ANUAL por defecto (1-30 enero ano siguiente).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


MODELO_455_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_455",
        "description": (
            "USA ESTA FUNCION cuando el usuario sea un operador ZEC "
            "(Zona Especial Canaria) y pregunte sobre:\n"
            "- AIEM aplicable a entidades ZEC con autorizacion para producir / "
            "entregar mercancias en Canarias\n"
            "- Modelo 455 (autoliquidacion ANUAL AIEM ZEC)\n"
            "- Liquidacion AIEM consolidada del ejercicio para entidad ZEC\n\n"
            "Periodicidad ANUAL (1-30 enero del ano siguiente). En supuestos "
            "concretos definidos por la ATC puede ser trimestral.\n\n"
            "NO confundir con Modelo 450 (productores 'ordinarios' fuera ZEC, "
            "trimestral) ni con Modelo 420 (IGIC, otro impuesto). AIEM es "
            "monofasico — solo lo paga el productor / entidad ZEC, no es "
            "deducible en cadena."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "epigrafe_zec": {
                    "type": "string",
                    "description": "Epigrafe / actividad ZEC autorizada (informativo).",
                },
                "year": {
                    "type": "integer",
                    "description": "Ejercicio fiscal declarado. Por defecto: ano actual.",
                },
                "bienes_anuales": {
                    "type": "array",
                    "description": (
                        "Lista de bienes producidos / entregados durante todo "
                        "el ejercicio (agregado anual). Cada bien: "
                        "{epigrafe_iae, descripcion, base_imponible, tipo_aiem (opcional)}."
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
                                "description": "Base imponible anual agregada del bien.",
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
                    "description": "Cuotas a compensar de ejercicios anteriores (>= 0).",
                },
                "rectificacion_bases": {
                    "type": "number",
                    "description": "Rectificacion de bases. Por defecto: 0.",
                },
                "rectificacion_cuotas": {
                    "type": "number",
                    "description": "Rectificacion de cuotas. Por defecto: 0.",
                },
                "regularizacion_anual": {
                    "type": "number",
                    "description": "Regularizacion anual final. Por defecto: 0.",
                },
                "periodicidad": {
                    "type": "string",
                    "enum": ["anual", "trimestral"],
                    "description": "anual (default) | trimestral (excepcional).",
                },
                "trimestre": {
                    "type": "integer",
                    "description": "Trimestre (1-4). Solo si periodicidad='trimestral'.",
                },
            },
            "required": ["bienes_anuales"],
        },
    },
}


def _format_for_llm(result: Dict[str, Any]) -> str:
    """Formatea el resultado del calculator para presentacion al usuario."""
    lines: List[str] = []
    year = result["year"]
    plazo = result["plazo_presentacion"]
    epigrafe_zec = result.get("epigrafe_zec")

    if result["periodicidad"] == "anual":
        lines.append(f"**AIEM ZEC Canarias — Modelo 455 ANUAL {year}**")
    else:
        lines.append(f"**AIEM ZEC Canarias — Modelo 455 {result['periodo_label']} {year}**")

    if epigrafe_zec:
        lines.append(f"Autorizacion ZEC: {epigrafe_zec}")
    lines.append("")

    # Desglose por bien
    lines.append("**Bienes ZEC sujetos a AIEM**")
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
            f"- Compensacion ejercicios anteriores: "
            f"-{result['cuotas_compensar_anteriores']:,.2f} EUR"
        )
    if result.get("regularizacion_anual"):
        lines.append(f"- Regularizacion anual: {result['regularizacion_anual']:,.2f} EUR")

    resultado = result["resultado_liquidacion"]
    if resultado > 0:
        tipo_resultado = "A ingresar"
    elif resultado < 0:
        tipo_resultado = "A devolver / compensar"
    else:
        tipo_resultado = "Sin actividad"

    lines.append("")
    lines.append(f"**Resultado: {resultado:,.2f} EUR — {tipo_resultado}**")
    lines.append("")
    lines.append(f"Plazo de presentacion: {plazo} (Agencia Tributaria Canaria — ATC).")

    warnings = result.get("warnings") or []
    if warnings:
        lines.append("")
        lines.append("**Avisos**")
        for w in warnings:
            lines.append(f"- {w}")

    lines.append("")
    lines.append(
        "Nota: el regimen ZEC requiere autorizacion previa del Consorcio ZEC. "
        "AIEM es monofasico — no se compensa con AIEM soportado. "
        "Verifica la asignacion epigrafe IAE → tipo AIEM en el "
        "Anexo IV TR Decreto Legislativo 1/2025."
    )

    return "\n".join(lines)


async def calculate_modelo_455_tool(
    bienes_anuales: List[Dict[str, Any]],
    epigrafe_zec: Optional[str] = None,
    year: Optional[int] = None,
    cuotas_compensar_anteriores: float = 0.0,
    rectificacion_bases: float = 0.0,
    rectificacion_cuotas: float = 0.0,
    regularizacion_anual: float = 0.0,
    periodicidad: str = "anual",
    trimestre: Optional[int] = None,
    restricted_mode: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Tool wrapper para Modelo 455 (AIEM ZEC).

    Args:
        restricted_mode: si True (usuario plan Particular) bloquea — el AIEM
            ZEC requiere ser entidad ZEC (sociedad autorizada).
    """
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_455 called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response(),
        }

    try:
        if year is None:
            year = datetime.now().year

        if periodicidad not in ("anual", "trimestral"):
            return {
                "success": False,
                "error": "periodicidad invalida",
                "formatted_response": (
                    "La periodicidad del Modelo 455 debe ser 'anual' (default) "
                    "o 'trimestral' (casos especificos)."
                ),
            }
        if periodicidad == "trimestral" and trimestre not in (1, 2, 3, 4):
            return {
                "success": False,
                "error": "trimestre invalido",
                "formatted_response": ("Para periodicidad trimestral, el trimestre debe ser 1-4."),
            }

        if not isinstance(bienes_anuales, list) or not bienes_anuales:
            return {
                "success": False,
                "error": "bienes_anuales vacio",
                "formatted_response": (
                    "Indica al menos un bien ZEC sujeto a AIEM "
                    "(epigrafe IAE, base imponible anual y tipo AIEM)."
                ),
            }

        from app.utils.calculators.modelo_455 import Modelo455Calculator

        calc = Modelo455Calculator(None)
        result = await calc.calculate(
            bienes_anuales=bienes_anuales,
            epigrafe_zec=epigrafe_zec,
            cuotas_compensar_anteriores=max(0.0, float(cuotas_compensar_anteriores)),
            rectificacion_bases=float(rectificacion_bases),
            rectificacion_cuotas=float(rectificacion_cuotas),
            regularizacion_anual=float(regularizacion_anual),
            year=int(year),
            periodicidad=periodicidad,
            quarter=trimestre,
        )

        formatted = _format_for_llm(result)

        logger.info(
            "Modelo 455 calculated: %s %s, devengado=%s, resultado=%s",
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
        logger.warning("Modelo 455 validation error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular AIEM ZEC (Modelo 455): {e}",
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Modelo 455 calculation error: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular AIEM ZEC (Modelo 455): {e}",
        }
