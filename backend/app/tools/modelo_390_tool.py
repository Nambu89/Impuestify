"""
Modelo 390 (Resumen Anual IVA) Tool for TaxIA.

Wrapper LLM sobre `Modelo390Calculator`. Responsabilidades:
    - Detectar exoneracion por SII / REDEME / grupo IVA / RE / simplificado
      (Art. 71.7 RIVA).
    - Detectar variante territorial (390 / 391 / F-66 / 425) o no-aplicacion
      (Ceuta/Melilla — IPSI).
    - Sumar 4 modelos 303 trimestrales en un resumen anual.
    - Devolver respuesta amigable al usuario con plazo de presentacion.

Norma:
    Orden EHA/3111/2009 + modificaciones (Orden HFP/417/2017, etc.).
    Art. 71.7 RIVA — exoneracion.
    Plazo: 1 al 30 de enero del año siguiente.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.calculators.modelo_390 import (
    Modelo390Calculator,
    UMBRAL_SII_EUR,
)

logger = logging.getLogger(__name__)


MODELO_390_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_390",
        "description": """USA ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 390 / Modelo 391 (Bizkaia, Araba, Gipuzkoa) / Modelo F-66 (Navarra) / Modelo 425 (Canarias)
- Resumen anual de IVA
- Declaracion-resumen anual de IVA
- Si tiene que presentar 390 estando en SII / REDEME / grupo IVA / RE
- Sumatorio anual de los 4 modelos 303 trimestrales
- Exoneracion del 390 por volumen de facturacion

OBLIGATORIO usar esta funcion si el usuario quiere:
- Saber si esta obligado al 390 segun su situacion (SII, REDEME, RE, simplificado).
- Calcular el resumen anual sumando sus 4 trimestres del 303.
- Conocer el modelo correcto segun su territorio (390/391/F-66/425).

PASA SIEMPRE la ccaa del usuario. La funcion adapta automaticamente:
- Canarias        → Modelo 425 (resumen IGIC, Gobierno de Canarias)
- Bizkaia/Araba/Gipuzkoa → Modelo 391 foral
- Navarra         → Modelo F-66 foral
- Ceuta/Melilla   → No aplica (IPSI, no IVA)
- Resto           → Modelo 390 AEAT

Detecta automaticamente exoneraciones (Art. 71.7 RIVA):
- volumen_operaciones_ano_anterior > 6.010.121,04 EUR → SII obligatorio → exonerado
- en_redeme=True → exonerado
- en_grupo_iva=True → exonerado
- regimen_especial='simplificado' o 'recargo_equivalencia' → exonerado
""",
        "parameters": {
            "type": "object",
            "properties": {
                "ccaa": {
                    "type": "string",
                    "description": (
                        "CCAA o territorio del usuario. Ejemplos: 'Madrid', "
                        "'Canarias', 'Gipuzkoa', 'Navarra', 'Bizkaia', 'Araba', "
                        "'Ceuta', 'Melilla'. Si no se indica se asume regimen "
                        "comun (Modelo 390 AEAT)."
                    ),
                },
                "year": {
                    "type": "integer",
                    "description": (
                        "Ejercicio del resumen anual (ej. 2025 → se presenta "
                        "en enero 2026). Por defecto: año actual - 1."
                    ),
                },
                "volumen_operaciones_ano_anterior": {
                    "type": "number",
                    "description": (
                        "Volumen de operaciones del año anterior (EUR). Si supera "
                        "6.010.121,04 EUR el sujeto esta obligado a SII y exonerado "
                        "del 390 (Art. 121 LIVA + Art. 71.7 RIVA). Por defecto: 0."
                    ),
                },
                "en_redeme": {
                    "type": "boolean",
                    "description": (
                        "True si el sujeto esta inscrito en REDEME (Registro de "
                        "Devolucion Mensual del IVA) — exonerado del 390. "
                        "Por defecto: False."
                    ),
                },
                "en_grupo_iva": {
                    "type": "boolean",
                    "description": (
                        "True si el sujeto pertenece a un grupo de IVA "
                        "(Cap. IX Tit. IX LIVA) — exonerado del 390. "
                        "Por defecto: False."
                    ),
                },
                "sii_voluntario": {
                    "type": "boolean",
                    "description": (
                        "True si el sujeto se ha acogido voluntariamente a SII "
                        "aunque no supere el umbral. Por defecto: False."
                    ),
                },
                "regimen_especial": {
                    "type": "string",
                    "enum": ["simplificado", "recargo_equivalencia", "general"],
                    "description": (
                        "Regimen IVA del sujeto. 'simplificado' (modulos) o "
                        "'recargo_equivalencia' exoneran del 390. 'general' "
                        "= regimen general (puede estar obligado). Por defecto: "
                        "'general'."
                    ),
                },
                "trimestres_303": {
                    "type": "array",
                    "description": (
                        "Lista de 4 resultados de Modelo 303 trimestrales "
                        "(salida de calculate_modelo_303). Necesario solo si el "
                        "sujeto esta obligado y se quiere el sumatorio anual. "
                        "Cada elemento debe contener al menos las claves "
                        "'iva_devengado' e 'iva_deducible' o las casillas "
                        "individuales (casilla_03, casilla_06, casilla_09, "
                        "casilla_27, casilla_45, etc.)."
                    ),
                    "items": {"type": "object"},
                },
            },
            "required": [],
        },
    },
}


async def calculate_modelo_390_tool(
    ccaa: Optional[str] = None,
    year: Optional[int] = None,
    volumen_operaciones_ano_anterior: float = 0.0,
    en_redeme: bool = False,
    en_grupo_iva: bool = False,
    sii_voluntario: bool = False,
    regimen_especial: Optional[str] = "general",
    trimestres_303: Optional[List[Dict[str, Any]]] = None,
    restricted_mode: bool = False,
) -> Dict[str, Any]:
    """
    Wrapper LLM sobre Modelo390Calculator.

    Returns:
        Dict con success, obligado, modelo, formatted_response, etc.
    """
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_390 called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response(),
        }

    try:
        if year is None:
            # Por defecto, ejercicio anterior al año actual
            year = datetime.now().year - 1

        regimen_norm = (regimen_especial or "general").strip().lower()
        if regimen_norm == "general":
            regimen_for_check = None
        else:
            regimen_for_check = regimen_norm

        if volumen_operaciones_ano_anterior < 0:
            return {
                "success": False,
                "error": "volumen_operaciones_ano_anterior no puede ser negativo",
                "formatted_response": (
                    "El volumen de operaciones del año anterior no puede ser negativo."
                ),
            }

        if trimestres_303 is not None and not isinstance(trimestres_303, list):
            return {
                "success": False,
                "error": "trimestres_303 debe ser una lista",
                "formatted_response": (
                    "El parametro trimestres_303 debe ser una lista de 4 "
                    "resultados de Modelo 303 trimestrales."
                ),
            }

        if trimestres_303 is not None and len(trimestres_303) not in (0, 4):
            return {
                "success": False,
                "error": (
                    f"trimestres_303 debe contener 4 trimestres (recibidos: "
                    f"{len(trimestres_303)})"
                ),
                "formatted_response": (
                    f"Para calcular el resumen anual del 390 necesito los 4 "
                    f"trimestres del Modelo 303. Has pasado {len(trimestres_303)}. "
                    f"Si solo quieres saber si estas obligado puedes omitir "
                    f"trimestres_303."
                ),
            }

        # Si la lista esta vacia, tratar como ausente
        if trimestres_303 is not None and len(trimestres_303) == 0:
            trimestres_303 = None

        calc = Modelo390Calculator(None)
        result = await calc.calculate(
            trimestres_303=trimestres_303,
            territory=ccaa,
            volumen_operaciones_ano_anterior=volumen_operaciones_ano_anterior,
            en_redeme=en_redeme,
            en_grupo_iva=en_grupo_iva,
            sii_voluntario=sii_voluntario,
            regimen_especial=regimen_for_check,
            year=year,
        )

        formatted = _format_response(
            result=result,
            volumen_operaciones_ano_anterior=volumen_operaciones_ano_anterior,
            en_redeme=en_redeme,
            en_grupo_iva=en_grupo_iva,
            regimen_especial=regimen_norm,
            trimestres_303=trimestres_303,
        )

        logger.info(
            "Modelo 390 calculated: ccaa=%s modelo=%s obligado=%s year=%s",
            ccaa,
            result["modelo"],
            result["obligado"],
            year,
        )

        return {
            "success": True,
            "obligado": result["obligado"],
            "modelo": result["modelo"],
            "ccaa": ccaa,
            "year": year,
            "plazo": result["plazo"],
            "hacienda": result["hacienda"],
            "motivo_exoneracion": result["motivo_exoneracion"],
            "territory_info": result["territory_info"],
            "exoneraciones_aplicables": result["exoneraciones_aplicables"],
            "resumen_anual": result["resumen_anual"],
            "umbral_sii": UMBRAL_SII_EUR,
            "formatted_response": formatted,
        }

    except ValueError as ve:
        logger.warning("Modelo 390 validation error: %s", ve)
        return {
            "success": False,
            "error": str(ve),
            "formatted_response": f"Error de validacion: {ve}",
        }
    except Exception as e:
        logger.error("Error calculating Modelo 390: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el Modelo 390: {e}",
        }


# ---------------------------------------------------------------------- #
# Helpers de formateo
# ---------------------------------------------------------------------- #


def _format_response(
    *,
    result: Dict[str, Any],
    volumen_operaciones_ano_anterior: float,
    en_redeme: bool,
    en_grupo_iva: bool,
    regimen_especial: str,
    trimestres_303: Optional[List[Dict[str, Any]]],
) -> str:
    """Construye la respuesta amigable para el usuario."""
    territory_info = result["territory_info"]
    territory_name = territory_info.get("territory") or "regimen comun"
    modelo = result["modelo"]
    year = result["year"]
    plazo = result["plazo"]
    hacienda = result["hacienda"]

    lines: List[str] = []

    # Caso 1: Ceuta/Melilla — no aplica
    if modelo is None:
        lines.append(f"**Resumen anual IVA — {territory_name} — Ejercicio {year}**")
        lines.append("")
        lines.append(territory_info["nota"])
        lines.append("")
        lines.append(
            "No tienes que presentar Modelo 390 ni equivalente — IPSI no tiene "
            "resumen anual obligatorio."
        )
        return "\n".join(lines)

    # Caso 2: Canarias — sustituido por 425
    if modelo == "425":
        lines.append(f"**Modelo 425 — Resumen anual IGIC Canarias — Ejercicio {year}**")
        lines.append(f"Presentacion: {hacienda}")
        lines.append(f"Plazo: {plazo}")
        lines.append("")
        lines.append(territory_info["nota"])
        lines.append("")
        lines.append(
            "En Canarias NO se presenta Modelo 390 (es IVA). El resumen anual "
            "equivalente es el Modelo 425 (IGIC). Para el calculo trimestral de "
            "IGIC usa Modelo 420."
        )
        return "\n".join(lines)

    # Caso 3: foral o comun, exonerado
    if not result["obligado"]:
        modelo_label = f"Modelo {modelo}"
        lines.append(f"**EXONERADO — {modelo_label} (resumen anual IVA) — Ejercicio {year}**")
        lines.append(f"Hacienda: {hacienda}")
        lines.append("")
        lines.append("**No tienes que presentar el Modelo 390 (ni equivalente).**")
        lines.append("")
        lines.append("**Motivo(s):**")
        for chk in result["exoneraciones_aplicables"]:
            lines.append(f"- {chk['chequeo']}: {chk['motivo']}")
        lines.append("")
        lines.append(
            "Base legal: Art. 71.7 RIVA (RD 1624/1992) + Disp. Adicional unica "
            "Orden HFP/417/2017."
        )
        return "\n".join(lines)

    # Caso 4: obligado — formatear cabecera y, si hay 303, sumatorio
    modelo_label = f"Modelo {modelo}"
    lines.append(f"**{modelo_label} — Resumen anual IVA — Ejercicio {year}**")
    lines.append(f"Presentacion: {hacienda}")
    lines.append(f"Plazo: {plazo}")
    if territory_info.get("nota") and modelo != "390":
        lines.append("")
        lines.append(territory_info["nota"])
    lines.append("")
    lines.append("**Estas OBLIGADO a presentar el resumen anual.**")
    lines.append("")
    lines.append(
        f"- Volumen operaciones año anterior: {volumen_operaciones_ano_anterior:,.2f} EUR (umbral SII: {UMBRAL_SII_EUR:,.2f} EUR)"
    )
    lines.append(f"- En REDEME: {'Si' if en_redeme else 'No'}")
    lines.append(f"- En grupo IVA: {'Si' if en_grupo_iva else 'No'}")
    lines.append(f"- Regimen IVA: {regimen_especial}")
    lines.append("")

    resumen = result.get("resumen_anual")
    if resumen:
        lines.append("**Sumatorio anual (4 trimestres del Modelo 303)**")
        lines.append("")
        lines.append("**IVA devengado anual**")
        if resumen["cuota_devengada_4"]:
            lines.append(f"- Cuota 4% anual: {resumen['cuota_devengada_4']:,.2f} EUR")
        if resumen["cuota_devengada_10"]:
            lines.append(f"- Cuota 10% anual: {resumen['cuota_devengada_10']:,.2f} EUR")
        if resumen["cuota_devengada_21"]:
            lines.append(f"- Cuota 21% anual: {resumen['cuota_devengada_21']:,.2f} EUR")
        if resumen["cuota_devengada_intra"]:
            lines.append(
                f"- Cuota adq. intracomunitarias: " f"{resumen['cuota_devengada_intra']:,.2f} EUR"
            )
        if resumen["cuota_devengada_isp"]:
            lines.append(
                f"- Cuota inversion sujeto pasivo: " f"{resumen['cuota_devengada_isp']:,.2f} EUR"
            )
        lines.append(
            f"- **Total devengado anual: " f"{resumen['total_devengado_anual']:,.2f} EUR**"
        )
        lines.append("")
        lines.append("**IVA deducible anual**")
        if resumen["cuota_deducible_corrientes"]:
            lines.append(
                f"- Bienes y servicios corrientes: "
                f"{resumen['cuota_deducible_corrientes']:,.2f} EUR"
            )
        if resumen["cuota_deducible_inversion"]:
            lines.append(
                f"- Bienes de inversion: " f"{resumen['cuota_deducible_inversion']:,.2f} EUR"
            )
        if resumen["cuota_deducible_importaciones"]:
            lines.append(
                f"- Importaciones: " f"{resumen['cuota_deducible_importaciones']:,.2f} EUR"
            )
        if resumen["cuota_deducible_intra"]:
            lines.append(
                f"- Adquisiciones intracomunitarias: "
                f"{resumen['cuota_deducible_intra']:,.2f} EUR"
            )
        lines.append(
            f"- **Total deducible anual: " f"{resumen['total_deducible_anual']:,.2f} EUR**"
        )
        lines.append("")
        lines.append(
            f"**Resultado liquidacion anual: "
            f"{resumen['resultado_liquidacion_anual']:,.2f} EUR**"
        )
    else:
        lines.append(
            "Para obtener el sumatorio anual, llamame de nuevo pasando los 4 "
            "resultados del Modelo 303 trimestral en el parametro `trimestres_303`."
        )

    lines.append("")
    lines.append(
        "Este calculo cubre solo el regimen general. Apartados informativos "
        "detallados (volumen de operaciones por epigrafe IAE, exenciones, "
        "exportaciones agregadas) requieren introducirse manualmente al "
        "presentar el modelo en sede."
    )
    return "\n".join(lines)
