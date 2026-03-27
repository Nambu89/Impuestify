"""
Tool para evaluar la obligacion de presentar el Modelo 720 (Declaracion Informativa
de Bienes y Derechos en el Extranjero).

Normativa aplicable:
- Ley 7/2012, de 29 de octubre (introduccion del Modelo 720)
- Real Decreto 1065/2007, Arts. 42 bis, 42 ter y 54 bis
- Sentencia TJUE C-788/19 de 27/01/2022 (anulacion sanciones desproporcionadas)
- Ley 5/2022 de 9 de marzo (reforma regimen sancionador — regimen general LGT)

Umbrales:
- Obligacion si a 31/dic se supera 50.000 EUR en CUALQUIERA de las 3 categorias:
  1. Cuentas bancarias en entidades financieras del extranjero
  2. Valores, derechos, seguros y rentas en entidades del extranjero
  3. Bienes inmuebles y derechos sobre inmuebles en el extranjero
- Incremento >20.000 EUR respecto la ultima declaracion presentada obliga a
  presentar de nuevo (aunque no se supere el umbral de 50K si ya se presento antes).

Plazo: 1 de enero a 31 de marzo del ejercicio siguiente.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

UMBRAL_OBLIGACION_EUR = 50_000
UMBRAL_INCREMENTO_EUR = 20_000

CATEGORIAS = {
    "cuentas": "Cuentas bancarias en el extranjero",
    "valores": "Valores, derechos, seguros y rentas en el extranjero",
    "inmuebles": "Bienes inmuebles en el extranjero",
}

# ---------------------------------------------------------------------------
# Tool definition (OpenAI function calling)
# ---------------------------------------------------------------------------

MODELO_720_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "check_modelo_720",
        "description": (
            "Evalua si el usuario esta obligado a presentar el Modelo 720 "
            "(Declaracion Informativa de Bienes y Derechos en el Extranjero). "
            "Usa esta funcion cuando el usuario pregunte sobre el Modelo 720, "
            "bienes en el extranjero, cuentas bancarias fuera de Espana, "
            "inmuebles en otro pais, valores o seguros en entidades extranjeras, "
            "o si debe declarar activos en el exterior. "
            "Evalua por cada categoria (cuentas, valores, inmuebles) si se supera "
            "el umbral de 50.000 EUR y si hay incremento >20.000 EUR respecto "
            "a la ultima declaracion presentada."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cuentas_extranjero": {
                    "type": "number",
                    "description": (
                        "Saldo total en cuentas bancarias en el extranjero a 31 de "
                        "diciembre del ejercicio, en euros."
                    ),
                },
                "valores_extranjero": {
                    "type": "number",
                    "description": (
                        "Valor de mercado de valores, derechos, seguros y rentas "
                        "depositados en entidades extranjeras a 31 de diciembre, en euros."
                    ),
                },
                "inmuebles_extranjero": {
                    "type": "number",
                    "description": (
                        "Valor de adquisicion de bienes inmuebles situados en el "
                        "extranjero, en euros."
                    ),
                },
                "ultimo_720_presentado": {
                    "type": "integer",
                    "description": (
                        "Ano del ultimo Modelo 720 presentado (ej: 2023). "
                        "Null si nunca se ha presentado."
                    ),
                },
                "saldos_ultimo_720_cuentas": {
                    "type": "number",
                    "description": (
                        "Saldo de cuentas declarado en el ultimo 720 presentado, en euros. "
                        "Solo relevante si se presento un 720 anterior."
                    ),
                },
                "saldos_ultimo_720_valores": {
                    "type": "number",
                    "description": (
                        "Valor de valores/seguros declarado en el ultimo 720 presentado, en euros."
                    ),
                },
                "saldos_ultimo_720_inmuebles": {
                    "type": "number",
                    "description": (
                        "Valor de inmuebles declarado en el ultimo 720 presentado, en euros."
                    ),
                },
            },
            "required": [],
        },
    },
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


async def check_modelo_720_tool(
    cuentas_extranjero: float = 0,
    valores_extranjero: float = 0,
    inmuebles_extranjero: float = 0,
    ultimo_720_presentado: Optional[int] = None,
    saldos_ultimo_720_cuentas: Optional[float] = None,
    saldos_ultimo_720_valores: Optional[float] = None,
    saldos_ultimo_720_inmuebles: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Evalua la obligacion de presentar el Modelo 720.

    Analiza tres categorias independientes:
    1. Cuentas bancarias en el extranjero (umbral 50.000 EUR)
    2. Valores, derechos, seguros y rentas en entidades extranjeras (umbral 50.000 EUR)
    3. Bienes inmuebles en el extranjero (umbral 50.000 EUR)

    Si ya se presento un 720 anterior, se evalua ademas si hay incremento >20.000 EUR
    en alguna categoria respecto a los saldos declarados.

    Post-reforma 2022 (Ley 5/2022): las sanciones se rigen por el regimen general
    de la LGT (no las sanciones desproporcionadas que anulo el TJUE en C-788/19).

    Returns:
        Dict con obligado_720 (bool), categorias_obligadas, plazo, recomendaciones
        y formatted_response para el usuario.
    """
    try:
        current_year = datetime.now().year
        ejercicio = current_year - 1  # Se declara el ejercicio anterior

        saldos_actuales = {
            "cuentas": float(cuentas_extranjero or 0),
            "valores": float(valores_extranjero or 0),
            "inmuebles": float(inmuebles_extranjero or 0),
        }

        saldos_previos: Optional[Dict[str, float]] = None
        if ultimo_720_presentado is not None:
            saldos_previos = {
                "cuentas": float(saldos_ultimo_720_cuentas or 0),
                "valores": float(saldos_ultimo_720_valores or 0),
                "inmuebles": float(saldos_ultimo_720_inmuebles or 0),
            }

        categorias_obligadas: List[str] = []
        categorias_por_incremento: List[str] = []
        detalles: List[Dict[str, Any]] = []

        for cat_key, cat_label in CATEGORIAS.items():
            valor = saldos_actuales[cat_key]
            obligado_umbral = valor > UMBRAL_OBLIGACION_EUR
            obligado_incremento = False
            incremento = 0.0

            if saldos_previos is not None and not obligado_umbral:
                incremento = valor - saldos_previos[cat_key]
                if incremento > UMBRAL_INCREMENTO_EUR:
                    obligado_incremento = True

            if obligado_umbral:
                categorias_obligadas.append(cat_key)
            elif obligado_incremento:
                categorias_por_incremento.append(cat_key)

            detalles.append({
                "categoria": cat_key,
                "descripcion": cat_label,
                "valor_actual": valor,
                "supera_umbral_50k": obligado_umbral,
                "incremento_vs_ultimo_720": round(incremento, 2) if saldos_previos else None,
                "supera_incremento_20k": obligado_incremento,
                "obligado": obligado_umbral or obligado_incremento,
            })

        todas_obligadas = categorias_obligadas + categorias_por_incremento
        obligado = len(todas_obligadas) > 0

        plazo = f"Del 1 de enero al 31 de marzo de {ejercicio + 1}"

        recomendaciones = _generar_recomendaciones_720(
            obligado, categorias_obligadas, categorias_por_incremento,
            saldos_actuales, ejercicio
        )

        formatted = _format_720_response(
            obligado, detalles, plazo, recomendaciones, ejercicio,
            ultimo_720_presentado
        )

        return {
            "success": True,
            "modelo": "720",
            "ejercicio": ejercicio,
            "obligado_720": obligado,
            "categorias_obligadas": todas_obligadas,
            "categorias_por_umbral": categorias_obligadas,
            "categorias_por_incremento": categorias_por_incremento,
            "plazo": plazo,
            "detalles": detalles,
            "recomendaciones": recomendaciones,
            "formatted_response": formatted,
        }

    except Exception as exc:
        logger.error("check_modelo_720 error: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                f"Error al evaluar la obligacion del Modelo 720: {exc}. "
                "Por favor, revisa los datos introducidos."
            ),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generar_recomendaciones_720(
    obligado: bool,
    por_umbral: List[str],
    por_incremento: List[str],
    saldos: Dict[str, float],
    ejercicio: int,
) -> List[str]:
    """Genera recomendaciones personalizadas."""
    recs: List[str] = []

    if not obligado:
        recs.append(
            f"No estas obligado a presentar el Modelo 720 del ejercicio {ejercicio} "
            "con los datos facilitados."
        )
        # Avisar si esta cerca del umbral
        for cat_key, cat_label in CATEGORIAS.items():
            if saldos[cat_key] > UMBRAL_OBLIGACION_EUR * 0.8:
                recs.append(
                    f"Tu saldo en {cat_label.lower()} ({saldos[cat_key]:,.2f} EUR) "
                    f"esta cerca del umbral de {UMBRAL_OBLIGACION_EUR:,.0f} EUR. "
                    "Vigila la evolucion a cierre del ejercicio."
                )
        return recs

    recs.append(
        f"Estas obligado a presentar el Modelo 720 del ejercicio {ejercicio}."
    )

    if por_umbral:
        nombres = [CATEGORIAS[c] for c in por_umbral]
        recs.append(
            f"Superas el umbral de {UMBRAL_OBLIGACION_EUR:,.0f} EUR en: "
            + ", ".join(nombres) + "."
        )

    if por_incremento:
        nombres = [CATEGORIAS[c] for c in por_incremento]
        recs.append(
            f"Hay incremento superior a {UMBRAL_INCREMENTO_EUR:,.0f} EUR respecto "
            f"al ultimo Modelo 720 presentado en: " + ", ".join(nombres) + "."
        )

    recs.append(
        f"Plazo de presentacion: del 1 de enero al 31 de marzo de {ejercicio + 1}."
    )
    recs.append(
        "Desde la reforma de 2022 (Ley 5/2022, tras la sentencia TJUE C-788/19), "
        "las sanciones se rigen por el regimen general de la LGT. Ya no se aplican "
        "las sanciones desproporcionadas de 5.000 EUR por dato."
    )
    recs.append(
        "Se presenta telematicamente ante la AEAT (Sede Electronica, apartado "
        "Modelo 720). Necesitas certificado digital o Cl@ve PIN."
    )

    return recs


def _format_720_response(
    obligado: bool,
    detalles: List[Dict],
    plazo: str,
    recomendaciones: List[str],
    ejercicio: int,
    ultimo_presentado: Optional[int],
) -> str:
    """Formatea la respuesta del Modelo 720 para el usuario."""
    lines: List[str] = []
    lines.append(f"Modelo 720 — Bienes y Derechos en el Extranjero (Ejercicio {ejercicio})")
    lines.append("")

    if obligado:
        lines.append("RESULTADO: Obligado a presentar el Modelo 720.")
    else:
        lines.append("RESULTADO: No obligado a presentar el Modelo 720.")
    lines.append("")

    lines.append("Detalle por categorias:")
    for d in detalles:
        estado = "OBLIGADO" if d["obligado"] else "No obligado"
        lines.append(f"  {d['descripcion']}: {d['valor_actual']:,.2f} EUR — {estado}")
        if d["supera_umbral_50k"]:
            lines.append(f"    Supera umbral de 50.000 EUR")
        if d["supera_incremento_20k"]:
            lines.append(f"    Incremento >{UMBRAL_INCREMENTO_EUR:,.0f} EUR vs ultimo 720")

    if ultimo_presentado:
        lines.append(f"\nUltimo Modelo 720 presentado: ejercicio {ultimo_presentado}")

    lines.append(f"\nPlazo: {plazo}")
    lines.append("")

    for rec in recomendaciones:
        lines.append(f"- {rec}")

    return "\n".join(lines)
