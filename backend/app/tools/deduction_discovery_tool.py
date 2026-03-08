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
                    "description": """Comunidad autónoma del contribuyente.
- 'Estatal': solo deducciones estatales (default si no se conoce la CCAA)
- Territorios forales (Araba, Bizkaia, Gipuzkoa, Navarra): devuelve SOLO deducciones forales (sistema IRPF propio)
- Cualquier otra CCAA: devuelve deducciones Estatal + autonómicas combinadas
Usar el nombre tal como aparece en el perfil fiscal del usuario (ej: 'Aragon', 'Castilla y Leon')."""
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
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute deduction discovery.

    If user_id is provided, the user's stored fiscal profile is loaded and its
    fields are automatically mapped to deduction requirement keys. These
    auto-generated answers are then merged with any explicit `answers` supplied
    by the caller (caller values take precedence).

    Args:
        ccaa: Comunidad Autonoma (or 'Estatal' for state-level only)
        tax_year: Fiscal year
        answers: Explicit user answers for eligibility evaluation
        user_id: Optional user ID — if given, profile is auto-loaded from DB

    Returns:
        Dict with success, deductions found, savings, and formatted response
    """
    answers = answers or {}

    # --- Auto-populate answers from stored fiscal profile ---
    if user_id:
        try:
            from app.database.turso_client import get_db_client
            from app.services.deduction_service import get_deduction_service as _get_svc
            import json as _json

            _db = await get_db_client()
            _prof_result = await _db.execute(
                "SELECT ccaa_residencia, situacion_laboral, datos_fiscales "
                "FROM user_profiles WHERE user_id = ?",
                [user_id],
            )
            if _prof_result.rows:
                _row = _prof_result.rows[0]
                _datos_raw = _row.get("datos_fiscales")
                _datos: Dict[str, Any] = {}
                if _datos_raw:
                    try:
                        _parsed = _json.loads(_datos_raw) if isinstance(_datos_raw, str) else _datos_raw
                        # datos_fiscales stores entries as {value: X, _source: ...} or plain values
                        for _k, _v in _parsed.items():
                            if isinstance(_v, dict) and "value" in _v:
                                _datos[_k] = _v["value"]
                            else:
                                _datos[_k] = _v
                    except (TypeError, ValueError):
                        pass

                # Merge top-level profile columns into _datos for the mapper
                _datos["ccaa_residencia"] = _row.get("ccaa_residencia")
                _datos["situacion_laboral"] = _row.get("situacion_laboral")

                # If ccaa not passed explicitly, infer from profile
                _profile_ccaa = _row.get("ccaa_residencia") or ""
                if ccaa == "Estatal" and _profile_ccaa:
                    ccaa = _profile_ccaa

                from app.services.deduction_service import DeductionService
                _auto_answers = DeductionService.build_answers_from_profile(_datos, ccaa)
                # Merge: explicit answers passed by caller override auto-generated ones
                merged = {**_auto_answers, **answers}
                answers = merged
        except Exception as _e:
            logger.warning("Could not auto-load profile for user %s: %s", user_id, _e)

    try:
        from app.services.deduction_service import get_deduction_service

        service = get_deduction_service()

        # Pass CCAA directly to the service layer, which handles:
        # - Foral territories: returns only foral deductions
        # - Régimen común: returns Estatal + CCAA combined
        # - Unknown CCAA: returns Estatal only (no CCAA rows found)
        # No allowlist needed — the service queries the DB dynamically
        result = await service.evaluate_eligibility(
            tax_year=tax_year, answers=answers, ccaa=ccaa if ccaa != "Estatal" else None,
        )
        missing = await service.get_missing_questions(
            tax_year=tax_year, answers=answers, ccaa=ccaa if ccaa != "Estatal" else None,
        )

        # Build formatted response
        lines = []
        territory_label = ccaa
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
