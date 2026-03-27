"""
Tool para evaluar la obligacion de presentar el Modelo 721 (Declaracion Informativa
sobre Monedas Virtuales situadas en el Extranjero).

Normativa aplicable:
- Real Decreto 249/2023, de 4 de abril (aprueba el Modelo 721)
- Disposicion adicional decimoctava de la LGT (introducida por Ley 11/2021)
- Orden HFP/886/2023 (aprueba modelo y condiciones de presentacion)
- Vigente desde ejercicio 2023

Umbrales:
- Obligacion si a 31/dic se supera 50.000 EUR en monedas virtuales custodiadas
  por personas o entidades en el extranjero (exchanges, custodios, wallets gestionados).
- Incremento >20.000 EUR respecto la ultima declaracion presentada obliga a
  presentar de nuevo.
- NO aplica a monedas virtuales en wallets de autocustodia (hardware wallets,
  software wallets donde el usuario controla las claves privadas).

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

# Exchanges considerados extranjeros (no exhaustiva, orientativa)
EXCHANGES_EXTRANJEROS_CONOCIDOS = {
    "binance", "coinbase", "kraken", "bybit", "okx", "kucoin",
    "gate.io", "bitfinex", "huobi", "htx", "crypto.com", "gemini",
    "bitstamp", "bitget", "mexc", "phemex", "deribit",
}

# Exchanges con sede en Espana (NO extranjeros)
EXCHANGES_ESPANOLES = {
    "bit2me", "bitnovo",
}

# ---------------------------------------------------------------------------
# Tool definition (OpenAI function calling)
# ---------------------------------------------------------------------------

MODELO_721_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "check_modelo_721",
        "description": (
            "Evalua si el usuario esta obligado a presentar el Modelo 721 "
            "(Declaracion Informativa sobre Monedas Virtuales en el Extranjero). "
            "Usa esta funcion cuando el usuario pregunte sobre el Modelo 721, "
            "declarar criptomonedas en el extranjero, si debe informar de sus "
            "cripto en exchanges como Binance, Coinbase, Kraken, etc. "
            "Tambien cuando pregunte si tiene que declarar Bitcoin, Ethereum u "
            "otras criptomonedas que tenga fuera de Espana. "
            "Evalua si se supera el umbral de 50.000 EUR y si hay incremento "
            ">20.000 EUR respecto a la ultima declaracion."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "crypto_extranjero_valor": {
                    "type": "number",
                    "description": (
                        "Valor de mercado total en euros de las criptomonedas "
                        "custodiadas en exchanges o entidades extranjeras a 31 de "
                        "diciembre del ejercicio."
                    ),
                },
                "exchanges_extranjeros": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Lista de nombres de exchanges extranjeros donde tiene "
                        "cripto (ej: ['Binance', 'Coinbase', 'Kraken'])."
                    ),
                },
                "ultimo_721_presentado": {
                    "type": "integer",
                    "description": (
                        "Ano del ultimo Modelo 721 presentado (ej: 2023). "
                        "Null si nunca se ha presentado."
                    ),
                },
                "valor_ultimo_721": {
                    "type": "number",
                    "description": (
                        "Valor total declarado en el ultimo Modelo 721 presentado, "
                        "en euros. Solo relevante si se presento un 721 anterior."
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


async def check_modelo_721_tool(
    crypto_extranjero_valor: float = 0,
    exchanges_extranjeros: Optional[List[str]] = None,
    ultimo_721_presentado: Optional[int] = None,
    valor_ultimo_721: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Evalua la obligacion de presentar el Modelo 721 (criptomonedas en el extranjero).

    El Modelo 721 (RD 249/2023) obliga a informar sobre monedas virtuales
    custodiadas en el extranjero cuando el saldo a 31/dic supere 50.000 EUR,
    o cuando haya un incremento superior a 20.000 EUR respecto al ultimo 721
    presentado.

    Importante: NO se declaran criptos en wallets de autocustodia (hardware
    wallets, claves privadas propias). Solo cripto en exchanges/custodios
    extranjeros.

    Returns:
        Dict con obligado_721 (bool), plazo, exchanges afectados, recomendaciones
        y formatted_response para el usuario.
    """
    try:
        current_year = datetime.now().year
        ejercicio = current_year - 1

        valor = float(crypto_extranjero_valor or 0)
        exchanges = exchanges_extranjeros or []

        # Clasificar exchanges
        exchanges_afectados: List[str] = []
        exchanges_espanoles: List[str] = []
        for ex in exchanges:
            ex_lower = ex.strip().lower()
            if ex_lower in EXCHANGES_ESPANOLES:
                exchanges_espanoles.append(ex.strip())
            else:
                exchanges_afectados.append(ex.strip())

        # Evaluar obligacion por umbral
        obligado_umbral = valor > UMBRAL_OBLIGACION_EUR

        # Evaluar obligacion por incremento
        obligado_incremento = False
        incremento = 0.0
        if ultimo_721_presentado is not None and not obligado_umbral:
            valor_previo = float(valor_ultimo_721 or 0)
            incremento = valor - valor_previo
            if incremento > UMBRAL_INCREMENTO_EUR:
                obligado_incremento = True

        obligado = obligado_umbral or obligado_incremento

        plazo = f"Del 1 de enero al 31 de marzo de {ejercicio + 1}"

        recomendaciones = _generar_recomendaciones_721(
            obligado, obligado_umbral, obligado_incremento,
            valor, incremento, exchanges_afectados, exchanges_espanoles,
            ejercicio
        )

        formatted = _format_721_response(
            obligado, obligado_umbral, obligado_incremento,
            valor, incremento, exchanges_afectados, exchanges_espanoles,
            plazo, recomendaciones, ejercicio, ultimo_721_presentado
        )

        return {
            "success": True,
            "modelo": "721",
            "ejercicio": ejercicio,
            "obligado_721": obligado,
            "obligado_por_umbral": obligado_umbral,
            "obligado_por_incremento": obligado_incremento,
            "valor_crypto_extranjero": valor,
            "incremento_vs_ultimo_721": round(incremento, 2) if ultimo_721_presentado else None,
            "exchanges_afectados": exchanges_afectados,
            "exchanges_espanoles_excluidos": exchanges_espanoles,
            "plazo": plazo,
            "recomendaciones": recomendaciones,
            "formatted_response": formatted,
        }

    except Exception as exc:
        logger.error("check_modelo_721 error: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                f"Error al evaluar la obligacion del Modelo 721: {exc}. "
                "Por favor, revisa los datos introducidos."
            ),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generar_recomendaciones_721(
    obligado: bool,
    por_umbral: bool,
    por_incremento: bool,
    valor: float,
    incremento: float,
    exchanges_afectados: List[str],
    exchanges_espanoles: List[str],
    ejercicio: int,
) -> List[str]:
    """Genera recomendaciones personalizadas para el Modelo 721."""
    recs: List[str] = []

    if not obligado:
        recs.append(
            f"No estas obligado a presentar el Modelo 721 del ejercicio {ejercicio} "
            "con los datos facilitados."
        )
        if valor > UMBRAL_OBLIGACION_EUR * 0.8:
            recs.append(
                f"Tu saldo en cripto en exchanges extranjeros ({valor:,.2f} EUR) "
                f"esta cerca del umbral de {UMBRAL_OBLIGACION_EUR:,.0f} EUR. "
                "Vigila la evolucion del mercado y tus posiciones a cierre de ejercicio."
            )
        return recs

    recs.append(
        f"Estas obligado a presentar el Modelo 721 del ejercicio {ejercicio}."
    )

    if por_umbral:
        recs.append(
            f"Tu saldo ({valor:,.2f} EUR) supera el umbral de "
            f"{UMBRAL_OBLIGACION_EUR:,.0f} EUR."
        )
    elif por_incremento:
        recs.append(
            f"El incremento ({incremento:,.2f} EUR) supera los "
            f"{UMBRAL_INCREMENTO_EUR:,.0f} EUR respecto al ultimo 721 presentado."
        )

    if exchanges_afectados:
        recs.append(
            f"Exchanges extranjeros afectados: {', '.join(exchanges_afectados)}."
        )

    if exchanges_espanoles:
        recs.append(
            f"Exchanges con sede en Espana (excluidos del 721): "
            f"{', '.join(exchanges_espanoles)}. "
            "Las cripto en plataformas espanolas no se declaran en el 721 "
            "(la plataforma ya informa a la AEAT via Modelo 172/173)."
        )

    recs.append(
        f"Plazo de presentacion: del 1 de enero al 31 de marzo de {ejercicio + 1}."
    )
    recs.append(
        "Se presenta telematicamente ante la AEAT. Debes informar por cada "
        "moneda virtual: tipo (BTC, ETH...), saldo a 31/dic en unidades y euros, "
        "nombre del exchange/custodio y pais."
    )
    recs.append(
        "Recuerda que las criptomonedas en wallets de autocustodia (hardware "
        "wallets como Ledger, Trezor, o software wallets donde controlas las "
        "claves privadas) NO se declaran en el Modelo 721."
    )
    recs.append(
        "El Modelo 721 es solo informativo. Las ganancias o perdidas por "
        "transmision de criptomonedas se declaran aparte en el IRPF "
        "(casillas 1813/1814 del Modelo 100)."
    )

    return recs


def _format_721_response(
    obligado: bool,
    por_umbral: bool,
    por_incremento: bool,
    valor: float,
    incremento: float,
    exchanges_afectados: List[str],
    exchanges_espanoles: List[str],
    plazo: str,
    recomendaciones: List[str],
    ejercicio: int,
    ultimo_presentado: Optional[int],
) -> str:
    """Formatea la respuesta del Modelo 721 para el usuario."""
    lines: List[str] = []
    lines.append(f"Modelo 721 — Monedas Virtuales en el Extranjero (Ejercicio {ejercicio})")
    lines.append("")

    if obligado:
        lines.append("RESULTADO: Obligado a presentar el Modelo 721.")
    else:
        lines.append("RESULTADO: No obligado a presentar el Modelo 721.")
    lines.append("")

    lines.append(f"Valor cripto en exchanges extranjeros: {valor:,.2f} EUR")
    lines.append(f"Umbral de obligacion: {UMBRAL_OBLIGACION_EUR:,.0f} EUR")

    if por_umbral:
        lines.append("Supera el umbral de 50.000 EUR.")
    elif por_incremento:
        lines.append(
            f"Incremento de {incremento:,.2f} EUR respecto al ultimo 721 "
            f"(supera {UMBRAL_INCREMENTO_EUR:,.0f} EUR)."
        )

    if exchanges_afectados:
        lines.append(f"\nExchanges extranjeros: {', '.join(exchanges_afectados)}")

    if exchanges_espanoles:
        lines.append(
            f"Exchanges espanoles (excluidos): {', '.join(exchanges_espanoles)}"
        )

    if ultimo_presentado:
        lines.append(f"\nUltimo Modelo 721 presentado: ejercicio {ultimo_presentado}")

    lines.append(f"\nPlazo: {plazo}")
    lines.append("")

    for rec in recomendaciones:
        lines.append(f"- {rec}")

    return "\n".join(lines)
