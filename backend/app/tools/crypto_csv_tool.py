"""
Tool para importar y parsear CSV/Excel de exchanges de criptomonedas.

Permite al usuario importar su historial de transacciones desde Binance,
Coinbase, Kraken, KuCoin o Bitget directamente desde el chat, enviando
el archivo en base64.
"""
from __future__ import annotations

import base64
import binascii
import logging
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definition (OpenAI function calling)
# ---------------------------------------------------------------------------

CRYPTO_CSV_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "parse_crypto_csv",
        "description": (
            "Importa y procesa un archivo CSV o Excel de transacciones de "
            "criptomonedas de un exchange (Binance, Coinbase, Kraken, KuCoin, "
            "Bitget). Detecta el formato automaticamente. Guarda las transacciones "
            "en la base de datos del usuario para su posterior calculo FIFO. "
            "Usa esta funcion cuando el usuario suba o pegue un CSV de su exchange "
            "o diga que quiere importar su historial de criptomonedas."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_content_base64": {
                    "type": "string",
                    "description": (
                        "Contenido del archivo CSV o Excel codificado en base64."
                    ),
                },
                "exchange": {
                    "type": "string",
                    "description": (
                        "Exchange de origen (opcional, se auto-detecta si no se indica): "
                        "binance, coinbase, kraken, kucoin, bitget."
                    ),
                    "enum": ["binance", "coinbase", "kraken", "kucoin", "bitget"],
                },
                "file_format": {
                    "type": "string",
                    "description": (
                        "Formato del archivo: 'csv' (por defecto) o 'xlsx' (Excel)."
                    ),
                    "enum": ["csv", "xlsx"],
                },
            },
            "required": ["file_content_base64"],
        },
    },
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

_MAX_BASE64_BYTES = 70_000_000  # ~52 MB en base64 → ~40 MB raw → margen sobre 10 MB real


async def parse_crypto_csv_tool(
    file_content_base64: str,
    exchange: Optional[str] = None,
    file_format: str = "csv",
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Decodifica, parsea y guarda transacciones de criptomonedas desde un CSV/Excel.

    Flujo:
    1. Decodifica base64 → bytes.
    2. Llama a parse_csv() o parse_excel() segun el formato.
    3. Guarda transacciones en crypto_transactions con deduplicacion por hash.
    4. Devuelve resumen: N transacciones importadas, exchange detectado, rango fechas.

    Args:
        file_content_base64: Contenido del fichero en base64.
        exchange: Exchange opcional (auto-detectado si None).
        file_format: 'csv' (defecto) o 'xlsx'.
        user_id: ID del usuario autenticado (inyectado por el agente).

    Returns:
        Diccionario con 'success', 'formatted_response' y estadisticas.
    """
    if not user_id:
        return {
            "success": False,
            "error": "usuario_no_identificado",
            "formatted_response": (
                "No puedo importar el CSV porque no tengo tu identificador de "
                "usuario. Asegurate de estar autenticado."
            ),
        }

    # Validar tamano del base64 para evitar ataques de memoria
    if len(file_content_base64) > _MAX_BASE64_BYTES:
        return {
            "success": False,
            "error": "archivo_demasiado_grande",
            "formatted_response": (
                "El archivo es demasiado grande. El limite es 10 MB. "
                "Prueba a dividir el historial en periodos mas cortos."
            ),
        }

    # --- 1. Decodificar base64 ---
    try:
        file_bytes = base64.b64decode(file_content_base64)
    except (binascii.Error, ValueError) as exc:
        return {
            "success": False,
            "error": f"base64_invalido: {exc}",
            "formatted_response": (
                "El contenido del archivo no es base64 valido. "
                "Asegurate de enviar el archivo correctamente codificado."
            ),
        }

    # --- 2. Parsear segun formato ---
    try:
        from app.services.crypto_parser import parse_csv, parse_excel

        if file_format == "xlsx":
            transactions = parse_excel(file_bytes, exchange=exchange)
        else:
            transactions = parse_csv(file_bytes, exchange=exchange)

    except ValueError as exc:
        # parse_csv lanza ValueError si supera MAX_ROWS
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                f"Error al procesar el archivo: {exc}. "
                "El archivo tiene demasiadas filas (maximo 50.000). "
                "Por favor, divide el historial en periodos mas cortos."
            ),
        }
    except ImportError as exc:
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                "Para procesar archivos Excel se necesita openpyxl. "
                "Prueba a exportar tu historial en formato CSV desde el exchange."
            ),
        }
    except Exception as exc:
        logger.error("parse_crypto_csv: error al parsear archivo: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                f"No pude procesar el archivo. Error: {exc}. "
                "Comprueba que el formato sea el correcto para tu exchange."
            ),
        }

    if not transactions:
        return {
            "success": True,
            "imported": 0,
            "exchange_detected": exchange or "desconocido",
            "formatted_response": (
                "El archivo esta vacio o no contiene transacciones reconocibles. "
                "Asegurate de exportar el historial completo desde tu exchange."
            ),
        }

    # Determinar exchange detectado
    detected_exchange = transactions[0].exchange if transactions else (exchange or "desconocido")

    # --- 3. Guardar en BD con deduplicacion ---
    try:
        from app.database.turso_client import get_db_client

        db = await get_db_client()

        imported_count = 0
        skipped_count = 0

        for tx in transactions:
            # Clave de deduplicacion: combinacion de campos que identifican de forma
            # unica una transaccion (no hay hash disponible, usamos campos clave)
            dup_check = await db.execute(
                """
                SELECT id FROM crypto_transactions
                WHERE user_id = ?
                  AND date_utc = ?
                  AND asset = ?
                  AND amount = ?
                  AND tx_type = ?
                  AND exchange = ?
                LIMIT 1
                """,
                [
                    user_id,
                    tx.date_utc or "",
                    tx.asset,
                    tx.amount,
                    tx.tx_type,
                    tx.exchange,
                ],
            )

            if dup_check.rows:
                skipped_count += 1
                continue

            tx_id = str(uuid.uuid4())
            await db.execute(
                """
                INSERT INTO crypto_transactions (
                    id, user_id, exchange, tx_type, date_utc,
                    asset, amount, price_eur, total_eur, fee_eur,
                    counterpart_asset, counterpart_amount, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    tx_id,
                    user_id,
                    tx.exchange,
                    tx.tx_type,
                    tx.date_utc or "",
                    tx.asset,
                    tx.amount,
                    tx.price_eur,
                    tx.total_eur,
                    tx.fee_eur,
                    tx.counterpart_asset,
                    tx.counterpart_amount,
                    tx.notes,
                ],
            )
            imported_count += 1

    except Exception as exc:
        logger.error("parse_crypto_csv: error guardando en BD: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                f"Las transacciones se parsearon correctamente pero no se pudieron "
                f"guardar en la base de datos: {exc}."
            ),
        }

    # --- 4. Calcular rango de fechas ---
    dates = [tx.date_utc for tx in transactions if tx.date_utc]
    date_from = min(dates) if dates else "desconocido"
    date_to = max(dates) if dates else "desconocido"

    # Contar tipos de operacion
    type_counts: dict[str, int] = {}
    for tx in transactions:
        type_counts[tx.tx_type] = type_counts.get(tx.tx_type, 0) + 1

    formatted = _format_import_response(
        imported=imported_count,
        skipped=skipped_count,
        total_parsed=len(transactions),
        exchange=detected_exchange,
        date_from=date_from,
        date_to=date_to,
        type_counts=type_counts,
    )

    return {
        "success": True,
        "imported": imported_count,
        "skipped_duplicates": skipped_count,
        "total_parsed": len(transactions),
        "exchange_detected": detected_exchange,
        "date_from": date_from,
        "date_to": date_to,
        "transaction_types": type_counts,
        "formatted_response": formatted,
    }


def _format_import_response(
    imported: int,
    skipped: int,
    total_parsed: int,
    exchange: str,
    date_from: str,
    date_to: str,
    type_counts: dict[str, int],
) -> str:
    """Formatea el resumen de importacion para el usuario."""
    lines = [
        f"Importacion CSV criptomonedas — {exchange.capitalize()}",
        f"Transacciones parseadas: {total_parsed}",
        f"Nuevas importadas: {imported}",
    ]

    if skipped > 0:
        lines.append(f"Duplicados omitidos: {skipped}")

    if date_from and date_to and date_from != "desconocido":
        # Acortar fechas a solo la parte de fecha
        from_short = date_from[:10] if len(date_from) >= 10 else date_from
        to_short = date_to[:10] if len(date_to) >= 10 else date_to
        lines.append(f"Periodo: {from_short} — {to_short}")

    if type_counts:
        lines.append("")
        lines.append("Tipos de transaccion:")
        type_labels = {
            "buy": "Compras",
            "sell": "Ventas",
            "swap": "Intercambios (swap)",
            "staking_reward": "Recompensas staking",
            "airdrop": "Airdrops",
            "mining": "Mineria",
            "transfer": "Transferencias",
            "fee": "Comisiones",
        }
        for tx_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            label = type_labels.get(tx_type, tx_type)
            lines.append(f"  {label}: {count}")

    if imported > 0:
        lines.append("")
        lines.append(
            "Ya puedes calcular tus ganancias y perdidas patrimoniales del ejercicio "
            "usando el calculo FIFO. Preguntame por tus ganancias de criptomonedas "
            "para la declaracion de la renta."
        )
    elif skipped == total_parsed:
        lines.append("")
        lines.append(
            "Todas las transacciones ya estaban importadas previamente. "
            "No hay nuevas transacciones que anadir."
        )

    return "\n".join(lines)
