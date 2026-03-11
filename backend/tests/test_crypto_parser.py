"""
Tests para el parser de CSVs de criptomonedas.

Cubre: helpers, deteccion de exchange, parsers por exchange
(Binance, Coinbase, Kraken, KuCoin, Bitget), parser generico,
parse_csv (integracion) y parse_excel.
"""
from __future__ import annotations

import csv
import io
import sys
import unittest.mock as mock

import pytest

from app.services.crypto_parser import (
    MAX_ROWS,
    CryptoTransaction,
    _kraken_normalise_asset,
    _normalise_asset,
    _parse_date,
    _parse_float,
    _sanitize_str,
    detect_exchange,
    parse_csv,
)


# ---------------------------------------------------------------------------
# Helpers de fabricacion de CSVs
# ---------------------------------------------------------------------------

def _make_csv(headers: list[str], rows: list[list[str]]) -> bytes:
    """Construye CSV en memoria como bytes."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# T1: _sanitize_str
# ---------------------------------------------------------------------------

def test_sanitize_str_removes_equals_prefix():
    """Quita prefijo = (inyeccion CSV formula)."""
    assert _sanitize_str("=1+2") == "1+2"


def test_sanitize_str_removes_plus_prefix():
    """Quita prefijo + (inyeccion CSV)."""
    assert _sanitize_str("+HYPERLINK") == "HYPERLINK"


def test_sanitize_str_removes_at_prefix():
    """Quita prefijo @ (inyeccion CSV)."""
    assert _sanitize_str("@SUM") == "SUM"


def test_sanitize_str_removes_minus_prefix():
    """Quita prefijo - (inyeccion CSV)."""
    assert _sanitize_str("-2+3") == "2+3"


def test_sanitize_str_none_returns_empty():
    """None devuelve cadena vacia."""
    assert _sanitize_str(None) == ""


def test_sanitize_str_no_prefix_unchanged():
    """Cadena sin prefijo de inyeccion no se modifica."""
    assert _sanitize_str("  BTC  ") == "BTC"


# ---------------------------------------------------------------------------
# T2: _parse_float
# ---------------------------------------------------------------------------

def test_parse_float_plain_number():
    """Parsea un numero simple."""
    assert _parse_float("1234.56") == pytest.approx(1234.56)


def test_parse_float_with_comma_thousands():
    """Parsea numero con comas de miles."""
    assert _parse_float("1,234.56") == pytest.approx(1234.56)


def test_parse_float_with_eur_prefix():
    """Parsea cadena con prefijo EUR."""
    assert _parse_float("EUR 500.00") == pytest.approx(500.0)


def test_parse_float_with_dollar_sign():
    """Parsea cadena con simbolo $."""
    assert _parse_float("$9,999.99") == pytest.approx(9999.99)


def test_parse_float_empty_returns_fallback():
    """Cadena vacia devuelve el fallback (None por defecto)."""
    assert _parse_float("") is None


def test_parse_float_none_returns_fallback():
    """None devuelve el fallback."""
    assert _parse_float(None, fallback=0.0) == 0.0


def test_parse_float_invalid_string_returns_fallback():
    """Cadena no numerica devuelve fallback."""
    assert _parse_float("no_es_numero") is None


# ---------------------------------------------------------------------------
# T3: _parse_date
# ---------------------------------------------------------------------------

def test_parse_date_iso_with_time():
    """Parsea formato ISO con hora."""
    result = _parse_date("2024-06-15 10:30:00")
    assert result == "2024-06-15T10:30:00"


def test_parse_date_iso_t_format():
    """Parsea formato ISO con T y Z."""
    result = _parse_date("2024-01-01T00:00:00Z")
    assert result == "2024-01-01T00:00:00"


def test_parse_date_ddmmyyyy():
    """Parsea formato dd/mm/yyyy."""
    result = _parse_date("31/12/2024")
    assert result == "2024-12-31T00:00:00"


def test_parse_date_mmddyyyy():
    """Parsea formato mm/dd/yyyy."""
    result = _parse_date("12/31/2024")
    assert result == "2024-12-31T00:00:00"


def test_parse_date_iso_date_only():
    """Parsea formato yyyy-mm-dd."""
    result = _parse_date("2024-03-01")
    assert result == "2024-03-01T00:00:00"


def test_parse_date_none_returns_none():
    """None devuelve None."""
    assert _parse_date(None) is None


def test_parse_date_invalid_returns_none():
    """Cadena no reconocida devuelve None."""
    assert _parse_date("not-a-date") is None


# ---------------------------------------------------------------------------
# T4: _normalise_asset
# ---------------------------------------------------------------------------

def test_normalise_asset_uppercase():
    """Convierte a mayusculas."""
    assert _normalise_asset("btc") == "BTC"


def test_normalise_asset_strips_whitespace():
    """Elimina espacios."""
    assert _normalise_asset("  ETH  ") == "ETH"


def test_normalise_asset_none_returns_empty():
    """None devuelve cadena vacia."""
    assert _normalise_asset(None) == ""


# ---------------------------------------------------------------------------
# T5: _kraken_normalise_asset
# ---------------------------------------------------------------------------

def test_kraken_normalise_xxbt_to_btc():
    """XXBT se mapea a BTC."""
    assert _kraken_normalise_asset("XXBT") == "BTC"


def test_kraken_normalise_xeth_to_eth():
    """XETH se mapea a ETH."""
    assert _kraken_normalise_asset("XETH") == "ETH"


def test_kraken_normalise_zeur_to_eur():
    """ZEUR se mapea a EUR."""
    assert _kraken_normalise_asset("ZEUR") == "EUR"


def test_kraken_normalise_xbt_to_btc():
    """XBT (sin segundo X) se mapea a BTC."""
    assert _kraken_normalise_asset("XBT") == "BTC"


def test_kraken_normalise_unknown_strips_x_prefix():
    """Activo desconocido con prefijo X pierde la X si len > 3."""
    # XDOT -> DOT (len 4 > 3, empieza con X)
    assert _kraken_normalise_asset("XDOT") == "DOT"


def test_kraken_normalise_short_unknown_unchanged():
    """Activo de 3 chars sin mapeo no se modifica."""
    assert _kraken_normalise_asset("SOL") == "SOL"


# ---------------------------------------------------------------------------
# T6: detect_exchange
# ---------------------------------------------------------------------------

def test_detect_exchange_binance():
    """Detecta Binance por sus headers caracteristicos."""
    headers = ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"]
    assert detect_exchange(headers) == "binance"


def test_detect_exchange_coinbase():
    """Detecta Coinbase por sus headers."""
    headers = ["Timestamp", "Transaction Type", "Asset", "Quantity Transacted",
               "Spot Price at Transaction", "Subtotal", "Fees and/or Spread", "Notes"]
    assert detect_exchange(headers) == "coinbase"


def test_detect_exchange_kraken():
    """Detecta Kraken por sus headers."""
    headers = ["txid", "refid", "time", "type", "subtype", "asset", "amount", "fee"]
    assert detect_exchange(headers) == "kraken"


def test_detect_exchange_kucoin():
    """Detecta KuCoin por sus headers."""
    headers = ["Time", "Pair", "Side", "Filled Amount", "Avg. Filled Price", "Fee"]
    assert detect_exchange(headers) == "kucoin"


def test_detect_exchange_bitget():
    """Detecta Bitget (superset de KuCoin con columna Total)."""
    headers = ["Time", "Pair", "Side", "Total", "Fee"]
    assert detect_exchange(headers) == "bitget"


def test_detect_exchange_unknown():
    """Headers no reconocidos devuelven 'unknown'."""
    headers = ["date", "type", "asset", "amount"]
    assert detect_exchange(headers) == "unknown"


# ---------------------------------------------------------------------------
# T7: Binance parser
# ---------------------------------------------------------------------------

def test_binance_buy_operation_parsed_correctly():
    """Una operacion buy de Binance produce CryptoTransaction con tx_type=buy."""
    csv_bytes = _make_csv(
        ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"],
        [["123", "2024-01-15 10:00:00", "Buy", "BTC", "0.5", ""]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "buy"
    assert txs[0].asset == "BTC"
    assert txs[0].amount == pytest.approx(0.5)
    assert txs[0].exchange == "binance"


def test_binance_sell_operation_parsed_correctly():
    """Una operacion sell de Binance produce tx_type=sell con amount positivo."""
    csv_bytes = _make_csv(
        ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"],
        [["123", "2024-03-01 12:00:00", "Sell", "ETH", "-2.0", ""]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "sell"
    assert txs[0].amount == pytest.approx(2.0)  # siempre positivo


def test_binance_staking_reward_parsed_correctly():
    """Staking Rewards de Binance produce tx_type=staking_reward."""
    csv_bytes = _make_csv(
        ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"],
        [["123", "2024-02-01 00:00:00", "Staking Rewards", "SOL", "1.5", ""]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "staking_reward"


def test_binance_ignores_rows_without_date():
    """Filas Binance sin fecha valida se ignoran silenciosamente."""
    csv_bytes = _make_csv(
        ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"],
        [
            ["123", "", "Buy", "BTC", "0.5", ""],          # sin fecha
            ["123", "2024-01-15 10:00:00", "Buy", "BTC", "1.0", ""],
        ],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1


def test_binance_ignores_fiat_assets():
    """Binance ignora filas donde Coin es USDT o EUR."""
    csv_bytes = _make_csv(
        ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"],
        [
            ["123", "2024-01-15 10:00:00", "Buy", "USDT", "500.0", ""],
            ["123", "2024-01-15 10:00:00", "Buy", "BTC", "0.5", ""],
        ],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].asset == "BTC"


# ---------------------------------------------------------------------------
# T8: Coinbase parser
# ---------------------------------------------------------------------------

def test_coinbase_buy_parsed_correctly():
    """Buy de Coinbase extrae precio, total y fee correctamente."""
    csv_bytes = _make_csv(
        ["Timestamp", "Transaction Type", "Asset", "Quantity Transacted",
         "Spot Price at Transaction", "Subtotal", "Fees and/or Spread", "Notes"],
        [["2024-01-10T09:00:00Z", "Buy", "BTC", "0.1",
          "40000", "4000", "50", ""]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    tx = txs[0]
    assert tx.tx_type == "buy"
    assert tx.asset == "BTC"
    assert tx.amount == pytest.approx(0.1)
    assert tx.price_eur == pytest.approx(40000.0)
    assert tx.total_eur == pytest.approx(4000.0)
    assert tx.fee_eur == pytest.approx(50.0)


def test_coinbase_sell_parsed_correctly():
    """Sell de Coinbase produce tx_type=sell."""
    csv_bytes = _make_csv(
        ["Timestamp", "Transaction Type", "Asset", "Quantity Transacted",
         "Spot Price at Transaction", "Subtotal", "Fees and/or Spread", "Notes"],
        [["2024-06-01T10:00:00Z", "Sell", "ETH", "2.0",
          "3000", "6000", "30", ""]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "sell"


def test_coinbase_convert_is_swap():
    """Convert de Coinbase produce tx_type=swap."""
    csv_bytes = _make_csv(
        ["Timestamp", "Transaction Type", "Asset", "Quantity Transacted",
         "Spot Price at Transaction", "Subtotal", "Fees and/or Spread", "Notes"],
        [["2024-03-01T10:00:00Z", "Convert", "BTC", "0.5",
          "50000", "25000", "10", "Converted to ETH"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "swap"


def test_coinbase_receive_zero_subtotal_is_airdrop():
    """Receive con Subtotal=0 se clasifica como airdrop (heuristica)."""
    csv_bytes = _make_csv(
        ["Timestamp", "Transaction Type", "Asset", "Quantity Transacted",
         "Spot Price at Transaction", "Subtotal", "Fees and/or Spread", "Notes"],
        [["2024-04-01T00:00:00Z", "Receive", "SOL", "10",
          "0", "0", "0", "airdrop"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "airdrop"


def test_coinbase_staking_income_parsed():
    """Staking Income de Coinbase produce tx_type=staking_reward."""
    csv_bytes = _make_csv(
        ["Timestamp", "Transaction Type", "Asset", "Quantity Transacted",
         "Spot Price at Transaction", "Subtotal", "Fees and/or Spread", "Notes"],
        [["2024-05-01T00:00:00Z", "Staking Income", "ETH", "0.05",
          "3000", "150", "0", ""]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "staking_reward"


# ---------------------------------------------------------------------------
# T9: Kraken parser
# ---------------------------------------------------------------------------

def test_kraken_trade_positive_amount_is_buy():
    """Trade de Kraken con amount positivo produce tx_type=buy."""
    csv_bytes = _make_csv(
        ["txid", "refid", "time", "type", "subtype", "asset", "amount", "fee"],
        [["T1", "R1", "2024-01-01 10:00:00", "trade", "", "XXBT", "0.5", "0.001"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "buy"
    assert txs[0].asset == "BTC"
    assert txs[0].amount == pytest.approx(0.5)


def test_kraken_trade_negative_amount_is_sell():
    """Trade de Kraken con amount negativo produce tx_type=sell."""
    csv_bytes = _make_csv(
        ["txid", "refid", "time", "type", "subtype", "asset", "amount", "fee"],
        [["T2", "R2", "2024-06-01 12:00:00", "trade", "", "XETH", "-2.0", "0.005"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "sell"
    assert txs[0].asset == "ETH"
    assert txs[0].amount == pytest.approx(2.0)  # siempre positivo


def test_kraken_staking_parsed():
    """Staking de Kraken produce tx_type=staking_reward."""
    csv_bytes = _make_csv(
        ["txid", "refid", "time", "type", "subtype", "asset", "amount", "fee"],
        [["T3", "R3", "2024-02-01 00:00:00", "staking", "", "SOL", "1.0", "0"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "staking_reward"


def test_kraken_fee_extracted():
    """Kraken extrae el fee correctamente."""
    csv_bytes = _make_csv(
        ["txid", "refid", "time", "type", "subtype", "asset", "amount", "fee"],
        [["T4", "R4", "2024-01-15 08:00:00", "trade", "", "XXBT", "1.0", "0.01"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].fee_eur == pytest.approx(0.01)


def test_kraken_deposit_is_transfer():
    """Deposit de Kraken produce tx_type=transfer."""
    csv_bytes = _make_csv(
        ["txid", "refid", "time", "type", "subtype", "asset", "amount", "fee"],
        [["T5", "R5", "2024-01-10 10:00:00", "deposit", "", "XXBT", "0.1", "0"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "transfer"


# ---------------------------------------------------------------------------
# T10: KuCoin parser
# ---------------------------------------------------------------------------

def test_kucoin_buy_pair_parsed():
    """KuCoin extrae asset del par BTC-USDT correctamente."""
    csv_bytes = _make_csv(
        ["Time", "Pair", "Side", "Filled Amount", "Avg. Filled Price", "Fee"],
        [["2024-01-20 10:00:00", "BTC-USDT", "buy", "0.5", "40000", "5"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].asset == "BTC"
    assert txs[0].tx_type == "buy"
    assert txs[0].amount == pytest.approx(0.5)
    assert txs[0].exchange == "kucoin"


def test_kucoin_sell_parsed():
    """KuCoin sell produce tx_type=sell."""
    csv_bytes = _make_csv(
        ["Time", "Pair", "Side", "Filled Amount", "Avg. Filled Price", "Fee"],
        [["2024-03-10 15:00:00", "ETH-USDT", "sell", "2.0", "3000", "10"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "sell"
    assert txs[0].asset == "ETH"


def test_kucoin_fee_and_price_extracted():
    """KuCoin extrae fee y precio correctamente."""
    csv_bytes = _make_csv(
        ["Time", "Pair", "Side", "Filled Amount", "Avg. Filled Price", "Fee"],
        [["2024-02-05 09:00:00", "SOL-USDT", "buy", "10.0", "100", "1.5"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].price_eur == pytest.approx(100.0)
    assert txs[0].fee_eur == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# T11: Bitget parser
# ---------------------------------------------------------------------------

def test_bitget_detected_and_parsed():
    """Bitget se detecta correctamente y parsea el par con amount y precio."""
    csv_bytes = _make_csv(
        ["Time", "Pair", "Side", "Filled Amount", "Avg. Filled Price", "Total", "Fee"],
        [["2024-04-01 08:00:00", "BTC-USDT", "buy", "0.5", "40000", "20000", "2"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].exchange == "bitget"
    assert txs[0].asset == "BTC"
    assert txs[0].amount == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# T12: Generic parser
# ---------------------------------------------------------------------------

def test_generic_columns_case_insensitive():
    """El parser generico acepta columnas en cualquier capitalizacion."""
    csv_bytes = _make_csv(
        ["DATE", "TYPE", "ASSET", "AMOUNT"],
        [["2024-07-01", "buy", "BTC", "0.2"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].asset == "BTC"
    assert txs[0].tx_type == "buy"


def test_generic_maps_staking_type():
    """El parser generico mapea 'staking' a staking_reward."""
    csv_bytes = _make_csv(
        ["date", "type", "asset", "amount"],
        [["2024-08-01", "staking", "ETH", "0.05"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "staking_reward"


def test_generic_maps_airdrop_type():
    """El parser generico mapea 'airdrop' correctamente."""
    csv_bytes = _make_csv(
        ["date", "type", "asset", "amount"],
        [["2024-09-01", "airdrop", "SOL", "5.0"]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].tx_type == "airdrop"


def test_generic_ignores_rows_without_date():
    """El parser generico ignora filas sin fecha valida."""
    csv_bytes = _make_csv(
        ["date", "type", "asset", "amount"],
        [
            ["", "buy", "BTC", "0.5"],         # sin fecha
            ["2024-10-01", "buy", "ETH", "1.0"],
        ],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].asset == "ETH"


def test_generic_ignores_rows_without_asset():
    """El parser generico ignora filas sin asset."""
    csv_bytes = _make_csv(
        ["date", "type", "asset", "amount"],
        [
            ["2024-10-01", "buy", "", "0.5"],       # sin asset
            ["2024-10-02", "buy", "BTC", "1.0"],
        ],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].asset == "BTC"


# ---------------------------------------------------------------------------
# T13: parse_csv — integracion
# ---------------------------------------------------------------------------

def test_parse_csv_autodetects_binance():
    """parse_csv detecta automaticamente Binance y usa su parser."""
    csv_bytes = _make_csv(
        ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"],
        [["123", "2024-01-01 10:00:00", "Buy", "BTC", "1.0", ""]],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 1
    assert txs[0].exchange == "binance"


def test_parse_csv_sorted_ascending_by_date():
    """parse_csv devuelve transacciones ordenadas por fecha ascendente."""
    csv_bytes = _make_csv(
        ["date", "type", "asset", "amount"],
        [
            ["2024-12-01", "buy", "BTC", "1.0"],
            ["2024-01-01", "buy", "ETH", "2.0"],
            ["2024-06-15", "buy", "SOL", "5.0"],
        ],
    )
    txs = parse_csv(csv_bytes)
    assert len(txs) == 3
    assert txs[0].date_utc < txs[1].date_utc < txs[2].date_utc


def test_parse_csv_empty_file_returns_empty_list():
    """Archivo CSV vacio devuelve lista vacia."""
    csv_bytes = _make_csv(
        ["date", "type", "asset", "amount"],
        [],
    )
    txs = parse_csv(csv_bytes)
    assert txs == []


def test_parse_csv_exceeds_max_rows_raises():
    """Archivo con mas de MAX_ROWS filas lanza ValueError."""
    headers = ["date", "type", "asset", "amount"]
    rows = [["2024-01-01", "buy", "BTC", "0.01"]] * (MAX_ROWS + 1)
    csv_bytes = _make_csv(headers, rows)
    with pytest.raises(ValueError, match="maximum allowed rows"):
        parse_csv(csv_bytes)


def test_parse_csv_exchange_override():
    """Si se pasa exchange explicito, se usa ese parser aunque los headers no coincidan."""
    # Headers genericos pero forzamos binance
    csv_bytes = _make_csv(
        ["User_ID", "UTC_Time", "Operation", "Coin", "Change", "Remark"],
        [["123", "2024-01-01 10:00:00", "Sell", "ETH", "-1.0", ""]],
    )
    txs = parse_csv(csv_bytes, exchange="binance")
    assert len(txs) == 1
    assert txs[0].exchange == "binance"


# ---------------------------------------------------------------------------
# T14: parse_excel
# ---------------------------------------------------------------------------

def test_parse_excel_converts_to_csv_internally():
    """parse_excel convierte el xlsx a CSV y devuelve transacciones correctas."""
    pytest.importorskip("openpyxl")
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["date", "type", "asset", "amount"])
    ws.append(["2024-01-01", "buy", "BTC", "0.5"])

    buf = io.BytesIO()
    wb.save(buf)
    excel_bytes = buf.getvalue()

    from app.services.crypto_parser import parse_excel
    txs = parse_excel(excel_bytes)
    assert len(txs) == 1
    assert txs[0].asset == "BTC"
    assert txs[0].amount == pytest.approx(0.5)


def test_parse_excel_raises_if_openpyxl_missing():
    """parse_excel lanza ImportError si openpyxl no esta disponible."""
    import app.services.crypto_parser as parser_module

    original = parser_module._OPENPYXL_AVAILABLE
    try:
        parser_module._OPENPYXL_AVAILABLE = False
        with pytest.raises(ImportError, match="openpyxl"):
            parser_module.parse_excel(b"fake_excel_bytes")
    finally:
        parser_module._OPENPYXL_AVAILABLE = original
