"""
Tool para calcular ganancias/perdidas patrimoniales por criptomonedas (FIFO).

Calcula las ganancias y perdidas patrimoniales derivadas de la transmision de
monedas virtuales del usuario usando el metodo FIFO obligatorio (Art. 37.1.Undecies LIRPF).
Devuelve el resumen fiscal con casillas 1813 y 1814 del Modelo 100.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definition (OpenAI function calling)
# ---------------------------------------------------------------------------

CRYPTO_GAINS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "calculate_crypto_gains",
        "description": (
            "Calcula las ganancias y perdidas patrimoniales por transmision de "
            "criptomonedas del usuario usando el metodo FIFO obligatorio "
            "(Art. 37.1.Undecies LIRPF). Devuelve el resumen fiscal con casillas "
            "1813 (perdidas) y 1814 (ganancias) del Modelo 100. "
            "Usa esta funcion cuando el usuario pregunte cuanto tiene que declarar "
            "por sus cryptos, su resultado de criptomonedas en la renta, o quiera "
            "saber sus ganancias/perdidas de BTC, ETH u otras monedas virtuales."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "tax_year": {
                    "type": "integer",
                    "description": (
                        "Ejercicio fiscal a calcular (ej: 2024, 2025). "
                        "Por defecto el ano anterior al actual."
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


async def calculate_crypto_gains_tool(
    tax_year: Optional[int] = None,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Calcula ganancias/perdidas FIFO de criptomonedas para el usuario.

    Flujo:
    1. Lee transacciones de crypto_transactions desde la BD.
    2. Llama a calculate_fifo_gains() con todas las transacciones del usuario.
    3. Guarda los resultados en crypto_gains (INSERT OR IGNORE por idempotencia).
    4. Devuelve resumen formateado con casillas AEAT.

    Args:
        tax_year: Ejercicio fiscal. Si None, usa el ano anterior al actual.
        user_id: ID del usuario autenticado (inyectado por el agente).

    Returns:
        Diccionario con 'success', 'formatted_response' y datos del calculo.
    """
    if not user_id:
        return {
            "success": False,
            "error": "usuario_no_identificado",
            "formatted_response": (
                "No puedo calcular tus ganancias de criptomonedas porque no "
                "tengo tu identificador de usuario. Asegurate de estar autenticado."
            ),
        }

    # Determinar ejercicio fiscal
    if tax_year is None:
        tax_year = datetime.now().year - 1

    try:
        from app.database.turso_client import get_db_client
        from app.utils.calculators.crypto_fifo import calculate_fifo_gains
        from app.services.crypto_parser import CryptoTransaction

        db = await get_db_client()

        # --- 1. Leer transacciones del usuario ---
        result = await db.execute(
            """
            SELECT tx_type, date_utc, asset, amount,
                   price_eur, total_eur, fee_eur, exchange,
                   counterpart_asset, counterpart_amount, notes, id
            FROM crypto_transactions
            WHERE user_id = ?
            ORDER BY date_utc ASC
            """,
            [user_id],
        )

        rows = result.rows or []
        if not rows:
            return {
                "success": True,
                "tax_year": tax_year,
                "total_transactions": 0,
                "formatted_response": (
                    f"No tengo transacciones de criptomonedas registradas para el "
                    f"ejercicio {tax_year}. Puedes importar tu historial desde "
                    f"Binance, Coinbase, Kraken u otros exchanges usando el "
                    f"comando de importacion de CSV."
                ),
            }

        transactions: list[CryptoTransaction] = []
        tx_id_map: dict[int, str] = {}  # indice -> id original en BD
        for i, row in enumerate(rows):
            tx = CryptoTransaction(
                tx_type=row[0] or "transfer",
                date_utc=row[1] or "",
                asset=row[2] or "",
                amount=float(row[3] or 0),
                price_eur=float(row[4]) if row[4] is not None else None,
                total_eur=float(row[5]) if row[5] is not None else None,
                fee_eur=float(row[6] or 0),
                exchange=row[7] or "manual",
                counterpart_asset=row[8],
                counterpart_amount=float(row[9]) if row[9] is not None else None,
                notes=row[10] or "",
            )
            transactions.append(tx)
            tx_id_map[i] = row[11] or ""

        # --- 2. Calcular FIFO ---
        fifo_result = calculate_fifo_gains(transactions, tax_year=tax_year)

        # --- 3. Guardar en crypto_gains (idempotente: borrar ejercicio y re-insertar) ---
        await db.execute(
            "DELETE FROM crypto_gains WHERE user_id = ? AND tax_year = ?",
            [user_id, tax_year],
        )

        for gain in fifo_result.gains:
            gain_id = str(uuid.uuid4())
            await db.execute(
                """
                INSERT INTO crypto_gains (
                    id, user_id, tax_year, asset, tx_type,
                    clave_contraprestacion, date_acquisition, date_transmission,
                    acquisition_value_eur, acquisition_fees_eur,
                    transmission_value_eur, transmission_fees_eur,
                    gain_loss_eur, anti_aplicacion
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    gain_id,
                    user_id,
                    tax_year,
                    gain.asset,
                    gain.tx_type,
                    gain.clave_contraprestacion,
                    gain.date_acquisition,
                    gain.date_transmission,
                    gain.acquisition_value_eur,
                    gain.acquisition_fees_eur,
                    gain.transmission_value_eur,
                    gain.transmission_fees_eur,
                    gain.gain_loss_eur,
                    1 if gain.anti_aplicacion else 0,
                ],
            )

        summary = fifo_result.summary
        formatted = _format_gains_response(summary, tax_year, len(transactions))

        return {
            "success": True,
            "tax_year": tax_year,
            "total_transactions": len(transactions),
            "operations_analyzed": summary["total_operations"],
            "assets_involved": summary["assets_involved"],
            "total_gains_eur": summary["total_gains_eur"],
            "total_losses_eur": summary["total_losses_eur"],
            "net_result_eur": summary["net_result_eur"],
            "casilla_1813": summary["casilla_1813"],
            "casilla_1814": summary["casilla_1814"],
            "anti_aplicacion_count": summary["anti_aplicacion_count"],
            "formatted_response": formatted,
        }

    except Exception as exc:
        logger.error("calculate_crypto_gains error: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                f"Error al calcular las ganancias de criptomonedas: {exc}. "
                "Por favor, revisa que tus transacciones esten correctamente importadas."
            ),
        }


def _format_gains_response(summary: dict, tax_year: int, total_txs: int) -> str:
    """Formatea el resumen de ganancias cripto para el usuario."""
    lines = [
        f"Calculo FIFO criptomonedas — Ejercicio {tax_year}",
        f"Transacciones importadas: {total_txs}",
        f"Operaciones de transmision analizadas: {summary['total_operations']}",
    ]

    if summary["assets_involved"]:
        lines.append(f"Activos: {', '.join(summary['assets_involved'])}")

    lines.append("")
    lines.append("Resultado fiscal:")
    lines.append(f"  Ganancias patrimoniales: {summary['total_gains_eur']:,.2f} EUR")
    lines.append(f"  Perdidas patrimoniales: {summary['total_losses_eur']:,.2f} EUR")

    if summary["anti_aplicacion_count"] > 0:
        lines.append(
            f"  Perdidas no computables (antiaplicacion Art. 33.5.f LIRPF): "
            f"{summary['anti_aplicacion_count']} operaciones"
        )
        lines.append(
            f"  Perdidas computables: {summary['computable_losses_eur']:,.2f} EUR"
        )

    net = summary["net_result_eur"]
    if net >= 0:
        lines.append(f"  RESULTADO NETO: +{net:,.2f} EUR (ganancia)")
    else:
        lines.append(f"  RESULTADO NETO: {net:,.2f} EUR (perdida)")

    lines.append("")
    lines.append("Casillas Modelo 100:")
    lines.append(
        f"  Casilla 1814 (ganancias patrimoniales cripto): "
        f"{summary['casilla_1814']:,.2f} EUR"
    )
    lines.append(
        f"  Casilla 1813 (perdidas patrimoniales cripto): "
        f"{summary['casilla_1813']:,.2f} EUR"
    )

    if net > 0:
        lines.append("")
        lines.append(
            "Estas ganancias tributan como base del ahorro (Art. 46 LIRPF): "
            "19% hasta 6.000 EUR, 21% de 6.000 a 50.000 EUR, "
            "23% de 50.000 a 200.000 EUR, 27% de 200.000 a 300.000 EUR, "
            "28% a partir de 300.000 EUR."
        )
    elif net < 0:
        lines.append("")
        lines.append(
            "Estas perdidas pueden compensarse con ganancias del ahorro del mismo "
            "ejercicio. El saldo negativo pendiente se puede compensar en los "
            "4 ejercicios siguientes (Art. 49 LIRPF)."
        )

    return "\n".join(lines)
