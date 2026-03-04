"""
Deduction Discovery Tool for TaxIA.

Allows the TaxAgent to discover IRPF deductions the user may be eligible for,
evaluate eligibility based on collected answers, and identify missing information.
"""
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
DISCOVER_DEDUCTIONS_TOOL = {
    "type": "function",
    "function": {
        "name": "discover_deductions",
        "description": """Descubre deducciones IRPF a las que el contribuyente puede tener derecho.

Usa esta herramienta cuando el usuario pregunte sobre:
- Deducciones, desgravaciones o beneficios fiscales
- Cómo ahorrar en la declaración de la renta
- Si puede deducirse algo (vivienda, donativos, hijos, etc.)
- Optimización fiscal

La herramienta evalúa la elegibilidad según las respuestas del usuario y devuelve:
- Deducciones a las que SÍ tiene derecho (con ahorro estimado)
- Deducciones POSIBLES (faltan datos para confirmar)
- Preguntas pendientes para determinar más deducciones

IMPORTANTE: Pasa en 'answers' toda la información que ya conozcas del usuario
(hijos, vivienda, donativos, etc.) para obtener resultados más precisos.""",
        "parameters": {
            "type": "object",
            "properties": {
                "ccaa": {
                    "type": "string",
                    "description": """Comunidad autónoma del contribuyente. Valores válidos:
- 'Estatal': solo deducciones estatales (default si no se conoce la CCAA)
- Territorios forales (sistema propio): 'Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra'
- Régimen común: 'Madrid', 'Cataluña', 'Andalucía', 'Valencia'
Si se indica una CCAA de régimen común, devuelve deducciones Estatal + autonómicas combinadas.
Si es territorio foral, devuelve SOLO las deducciones forales (tienen sistema IRPF propio)."""
                },
                "tax_year": {
                    "type": "integer",
                    "description": "Año fiscal. Default: 2025."
                },
                "answers": {
                    "type": "object",
                    "description": """Respuestas del usuario para evaluar elegibilidad. Claves comunes:
- adquisicion_antes_2013 (bool): Compró vivienda antes de 2013
- deducia_antes_2013 (bool): Deducía por vivienda antes de 2013
- donativo_a_entidad_acogida (bool): Dona a ONGs/fundaciones
- madre_trabajadora (bool): Madre trabajadora dada de alta en SS
- hijo_menor_3 (bool): Tiene hijos menores de 3 años
- familia_numerosa (bool): Título de familia numerosa
- familia_monoparental (bool): Familia monoparental
- descendiente_discapacidad (bool): Hijos con discapacidad ≥33%
- ascendiente_discapacidad (bool): Padres/abuelos con discapacidad
- aportaciones_planes_pensiones (bool): Aporta a plan de pensiones
- contrato_antes_2015 (bool): Contrato alquiler antes de 2015
- autonomo_estimacion_directa (bool): Autónomo en estimación directa
- residente_ceuta_melilla (bool): Reside en Ceuta/Melilla
- vehiculo_electrico_nuevo (bool): Compró vehículo eléctrico
- obras_mejora_energetica (bool): Hizo obras de eficiencia energética
- rentas_extranjero (bool): Tiene rentas del extranjero""",
                    "additionalProperties": True
                }
            },
            "required": []
        }
    }
}


async def discover_deductions_tool(
    ccaa: str = "Estatal",
    tax_year: int = 2025,
    answers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute deduction discovery.

    Args:
        ccaa: Community (currently only 'Estatal' supported)
        tax_year: Fiscal year
        answers: User answers for eligibility evaluation

    Returns:
        Dict with success, deductions found, savings, and formatted response
    """
    answers = answers or {}

    try:
        from app.services.deduction_service import get_deduction_service

        service = get_deduction_service()

        # Determine if we should use combined Estatal+CCAA queries
        supported_ccaa = {
            "Araba", "Bizkaia", "Gipuzkoa", "Navarra",
            "Madrid", "Cataluña", "Andalucía", "Valencia",
        }

        if ccaa in supported_ccaa:
            # Combined query: Estatal + CCAA (or foral-only for foral territories)
            result = await service.evaluate_eligibility(
                tax_year=tax_year, answers=answers, ccaa=ccaa,
            )
            missing = await service.get_missing_questions(
                tax_year=tax_year, answers=answers, ccaa=ccaa,
            )
        else:
            # Fallback: only state-level deductions
            result = await service.evaluate_eligibility("Estatal", tax_year, answers)
            missing = await service.get_missing_questions("Estatal", tax_year, answers)

        # Build formatted response
        lines = []
        territory_label = ccaa if ccaa in supported_ccaa else "Estatal"
        lines.append(f"## Deducciones IRPF {tax_year} ({territory_label}) — Análisis personalizado\n")

        if result["eligible"]:
            lines.append(f"### ✅ Deducciones a las que tienes derecho ({len(result['eligible'])})\n")
            for d in result["eligible"]:
                amount_str = ""
                if d.get("fixed_amount"):
                    amount_str = f" — Hasta {d['fixed_amount']:,.0f}€"
                elif d.get("max_amount") and d.get("percentage"):
                    amount_str = f" — {d['percentage']}% (máx. {d['max_amount']:,.0f}€)"
                elif d.get("percentage"):
                    amount_str = f" — {d['percentage']}%"
                lines.append(f"- **{d['name']}**{amount_str}")
                lines.append(f"  _{d.get('description', '')}_")
                if d.get("legal_reference"):
                    lines.append(f"  Ref: {d['legal_reference']}")
                lines.append("")

            lines.append(f"**💰 Ahorro estimado: {result['estimated_savings']:,.0f}€**\n")

        if result["maybe_eligible"]:
            lines.append(f"### 🔍 Deducciones posibles — necesito más datos ({len(result['maybe_eligible'])})\n")
            for d in result["maybe_eligible"]:
                lines.append(f"- **{d['name']}**: {d.get('description', '')}")
            lines.append("")

        if missing:
            # Group by priority (max 5 questions to avoid overwhelming)
            top_questions = missing[:5]
            lines.append("### ❓ Preguntas para descubrir más deducciones\n")
            for q in top_questions:
                lines.append(f"- {q['text']}")
            if len(missing) > 5:
                lines.append(f"\n_(y {len(missing) - 5} preguntas más)_")
            lines.append("")

        if not result["eligible"] and not result["maybe_eligible"]:
            lines.append("No se han encontrado deducciones aplicables con la información proporcionada.")
            lines.append("Responde a las preguntas anteriores para que pueda buscar más opciones de ahorro.")

        formatted = "\n".join(lines)

        return {
            "success": True,
            "deductions_found": len(result["eligible"]),
            "maybe_eligible": len(result["maybe_eligible"]),
            "estimated_savings": result["estimated_savings"],
            "total_available": result["total_deductions"],
            "questions_pending": len(missing),
            "eligible": result["eligible"],
            "formatted_response": formatted,
        }

    except Exception as e:
        logger.error(f"Error in discover_deductions_tool: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al buscar deducciones: {str(e)}",
        }
