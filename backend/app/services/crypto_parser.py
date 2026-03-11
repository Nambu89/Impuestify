from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime

import structlog

try:
    import openpyxl

    _OPENPYXL_AVAILABLE = True
except ImportError:
    _OPENPYXL_AVAILABLE = False

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ROWS = 50_000

FIAT_CURRENCIES: frozenset[str] = frozenset(
    {"EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "HKD", "SGD", "USDT", "USDC", "BUSD", "DAI"}
)

_CSV_INJECTION_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@")

# Kraken asset prefix map: raw symbol → canonical symbol
_KRAKEN_ASSET_MAP: dict[str, str] = {
    "XXBT": "BTC",
    "XBT": "BTC",
    "XETH": "ETH",
    "XLTC": "LTC",
    "XXRP": "XRP",
    "XXLM": "XLM",
    "ZEUR": "EUR",
    "ZUSD": "USD",
    "ZGBP": "GBP",
    "ZCAD": "CAD",
    "ZJPY": "JPY",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class CryptoTransaction:
    """Represents a single normalised cryptocurrency transaction."""

    tx_type: str
    """One of: buy, sell, swap, staking_reward, airdrop, mining, fee, transfer."""
    date_utc: str
    """ISO 8601 datetime string (UTC)."""
    asset: str
    """Ticker symbol in uppercase (e.g. BTC, ETH, SOL)."""
    amount: float
    """Quantity of the crypto asset involved (always positive)."""
    price_eur: float | None = None
    """Price per unit in EUR at the time of the transaction."""
    total_eur: float | None = None
    """Total transaction value in EUR (excluding fees)."""
    fee_eur: float = 0.0
    """Transaction fee in EUR."""
    exchange: str = "manual"
    """Source exchange identifier (e.g. binance, coinbase, kraken)."""
    counterpart_asset: str | None = None
    """For swap transactions: the received asset symbol."""
    counterpart_amount: float | None = None
    """For swap transactions: quantity of the received asset."""
    notes: str = ""
    """Free-text notes or description from the source file."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize_str(value: str | None) -> str:
    """Strip CSV formula injection prefixes and surrounding whitespace."""
    if value is None:
        return ""
    value = str(value).strip()
    while value and value[0] in _CSV_INJECTION_PREFIXES:
        value = value[1:].strip()
    return value


def _parse_float(value: str | None, fallback: float | None = None) -> float | None:
    """Convert a string to float, stripping currency symbols and commas."""
    if value is None:
        return fallback
    cleaned = str(value).strip().replace(",", "").replace(" ", "")
    # Strip common currency prefixes
    for prefix in ("EUR", "USD", "GBP", "$", "€", "£"):
        cleaned = cleaned.replace(prefix, "")
    cleaned = cleaned.strip()
    if not cleaned:
        return fallback
    try:
        return float(cleaned)
    except ValueError:
        return fallback


def _parse_date(value: str | None) -> str | None:
    """
    Parse a date/datetime string into ISO 8601 UTC format.

    Tries multiple common formats used by exchanges. Returns None on failure.
    """
    if not value:
        return None
    value = value.strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
    logger.warning("crypto_parser.unrecognised_date", raw_value=value)
    return None


def _normalise_asset(raw: str | None) -> str:
    """Uppercase and strip whitespace from an asset ticker."""
    if not raw:
        return ""
    return raw.strip().upper()


def _kraken_normalise_asset(raw: str | None) -> str:
    """Map Kraken raw symbols (XXBT, XETH, ZEUR …) to canonical tickers."""
    if not raw:
        return ""
    upper = raw.strip().upper()
    if upper in _KRAKEN_ASSET_MAP:
        return _KRAKEN_ASSET_MAP[upper]
    # Strip leading X or Z for unknown assets with length > 3
    if len(upper) > 3 and upper[0] in ("X", "Z"):
        return upper[1:]
    return upper


def _is_fiat(asset: str) -> bool:
    return asset.upper() in FIAT_CURRENCIES


def _sort_by_date(txs: list[CryptoTransaction]) -> list[CryptoTransaction]:
    """Sort transactions by date_utc ascending (None dates go to end)."""
    return sorted(txs, key=lambda t: t.date_utc or "9999")


def _check_row_limit(row_count: int) -> None:
    if row_count > MAX_ROWS:
        raise ValueError(
            f"CSV exceeds maximum allowed rows ({MAX_ROWS}). Got {row_count} rows."
        )


# ---------------------------------------------------------------------------
# Exchange detection
# ---------------------------------------------------------------------------


def detect_exchange(headers: list[str]) -> str:
    """
    Infer the source exchange from column headers.

    Args:
        headers: List of column header strings (case-sensitive).

    Returns:
        One of 'binance', 'coinbase', 'kraken', 'kucoin', 'bitget', or 'unknown'.
    """
    header_set = set(headers)

    # Order matters: more specific checks first
    if {"User_ID", "UTC_Time", "Operation", "Coin"}.issubset(header_set):
        return "binance"
    if {"Timestamp", "Transaction Type", "Asset"}.issubset(header_set):
        return "coinbase"
    if {"txid", "refid", "time", "type"}.issubset(header_set):
        return "kraken"
    # Bitget is more specific than KuCoin (superset of KuCoin columns)
    if {"Time", "Pair", "Side", "Total"}.issubset(header_set):
        return "bitget"
    if {"Time", "Pair", "Side"}.issubset(header_set):
        return "kucoin"

    return "unknown"


# ---------------------------------------------------------------------------
# Exchange-specific parsers
# ---------------------------------------------------------------------------


def _parse_binance(rows: list[dict[str, str]]) -> list[CryptoTransaction]:
    """Parse Binance transaction history CSV rows."""
    _OPERATION_MAP: dict[str, str] = {
        "buy": "buy",
        "sell": "sell",
        "staking rewards": "staking_reward",
        "airdrop": "airdrop",
        "mining": "mining",
        "fee": "fee",
        "transaction related": "transfer",
        "transfer": "transfer",
    }

    results: list[CryptoTransaction] = []

    for row in rows:
        try:
            raw_op = _sanitize_str(row.get("Operation", "")).lower()
            tx_type = _OPERATION_MAP.get(raw_op, "transfer")

            date_utc = _parse_date(_sanitize_str(row.get("UTC_Time")))
            if not date_utc:
                continue

            asset = _normalise_asset(row.get("Coin"))
            if not asset or _is_fiat(asset):
                continue

            raw_change = _parse_float(row.get("Change"))
            if raw_change is None:
                continue

            amount = abs(raw_change)

            results.append(
                CryptoTransaction(
                    tx_type=tx_type,
                    date_utc=date_utc,
                    asset=asset,
                    amount=amount,
                    exchange="binance",
                    notes=_sanitize_str(row.get("Remark", "")),
                )
            )
        except Exception as exc:
            logger.warning("crypto_parser.binance_row_skip", error=str(exc), row=row)
            continue

    return results


def _parse_coinbase(rows: list[dict[str, str]]) -> list[CryptoTransaction]:
    """Parse Coinbase transaction history CSV rows."""
    _TYPE_MAP: dict[str, str] = {
        "buy": "buy",
        "sell": "sell",
        "staking income": "staking_reward",
        "rewards income": "staking_reward",
        "receive": "transfer",
        "send": "transfer",
        "convert": "swap",
        "coinbase earn": "staking_reward",
        "learning reward": "airdrop",
    }

    results: list[CryptoTransaction] = []

    for row in rows:
        try:
            raw_type = _sanitize_str(row.get("Transaction Type", "")).lower()
            tx_type = _TYPE_MAP.get(raw_type, "transfer")

            # Heuristic: Receive with no cost basis → airdrop
            if raw_type == "receive":
                subtotal = _parse_float(row.get("Subtotal"))
                if subtotal is not None and subtotal == 0.0:
                    tx_type = "airdrop"

            date_utc = _parse_date(_sanitize_str(row.get("Timestamp")))
            if not date_utc:
                continue

            asset = _normalise_asset(row.get("Asset"))
            if not asset or _is_fiat(asset):
                continue

            amount = _parse_float(row.get("Quantity Transacted"))
            if amount is None:
                continue
            amount = abs(amount)

            price_eur = _parse_float(row.get("Spot Price at Transaction"))
            total_eur = _parse_float(row.get("Subtotal"))
            fee_eur = _parse_float(row.get("Fees and/or Spread")) or 0.0

            results.append(
                CryptoTransaction(
                    tx_type=tx_type,
                    date_utc=date_utc,
                    asset=asset,
                    amount=amount,
                    price_eur=price_eur,
                    total_eur=total_eur,
                    fee_eur=fee_eur,
                    exchange="coinbase",
                    notes=_sanitize_str(row.get("Notes", "")),
                )
            )
        except Exception as exc:
            logger.warning("crypto_parser.coinbase_row_skip", error=str(exc), row=row)
            continue

    return results


def _parse_kraken(rows: list[dict[str, str]]) -> list[CryptoTransaction]:
    """Parse Kraken ledger CSV rows."""
    _TYPE_MAP: dict[str, str] = {
        "buy": "buy",
        "sell": "sell",
        "staking": "staking_reward",
        "transfer": "transfer",
        "deposit": "transfer",
        "withdrawal": "transfer",
        "trade": "buy",  # refined by amount sign below
        "spend": "sell",
        "receive": "transfer",
        "earn": "staking_reward",
    }

    results: list[CryptoTransaction] = []

    for row in rows:
        try:
            raw_type = _sanitize_str(row.get("type", "")).lower()
            tx_type = _TYPE_MAP.get(raw_type, "transfer")

            date_utc = _parse_date(_sanitize_str(row.get("time")))
            if not date_utc:
                continue

            asset = _kraken_normalise_asset(row.get("asset"))
            if not asset or _is_fiat(asset):
                continue

            raw_amount = _parse_float(row.get("amount"))
            if raw_amount is None:
                continue

            # For trade rows, sign determines direction
            if raw_type == "trade":
                tx_type = "buy" if raw_amount >= 0 else "sell"

            amount = abs(raw_amount)
            fee_eur = _parse_float(row.get("fee")) or 0.0

            results.append(
                CryptoTransaction(
                    tx_type=tx_type,
                    date_utc=date_utc,
                    asset=asset,
                    amount=amount,
                    fee_eur=fee_eur,
                    exchange="kraken",
                    notes=_sanitize_str(row.get("subtype", "")),
                )
            )
        except Exception as exc:
            logger.warning("crypto_parser.kraken_row_skip", error=str(exc), row=row)
            continue

    return results


def _parse_kucoin(rows: list[dict[str, str]], exchange: str = "kucoin") -> list[CryptoTransaction]:
    """Parse KuCoin and Bitget trade history CSV rows (shared structure)."""
    _SIDE_MAP: dict[str, str] = {
        "buy": "buy",
        "sell": "sell",
    }

    results: list[CryptoTransaction] = []

    for row in rows:
        try:
            raw_side = _sanitize_str(row.get("Side", "")).lower()
            tx_type = _SIDE_MAP.get(raw_side, "transfer")

            date_utc = _parse_date(_sanitize_str(row.get("Time")))
            if not date_utc:
                continue

            # Pair is e.g. "BTC-USDT" or "BTC/USDT"
            pair = _sanitize_str(row.get("Pair", ""))
            asset = _normalise_asset(pair.replace("/", "-").split("-")[0])
            if not asset or _is_fiat(asset):
                continue

            amount = _parse_float(row.get("Filled Amount") or row.get("Amount"))
            if amount is None:
                continue
            amount = abs(amount)

            price_eur = _parse_float(row.get("Avg. Filled Price") or row.get("Price"))
            total_eur = _parse_float(row.get("Total") or row.get("Filled Turnover"))
            fee_eur = _parse_float(row.get("Fee")) or 0.0

            results.append(
                CryptoTransaction(
                    tx_type=tx_type,
                    date_utc=date_utc,
                    asset=asset,
                    amount=amount,
                    price_eur=price_eur,
                    total_eur=total_eur,
                    fee_eur=fee_eur,
                    exchange=exchange,
                )
            )
        except Exception as exc:
            logger.warning(
                "crypto_parser.kucoin_row_skip",
                exchange=exchange,
                error=str(exc),
                row=row,
            )
            continue

    return results


def _parse_generic(rows: list[dict[str, str]]) -> list[CryptoTransaction]:
    """
    Best-effort parser for unknown exchange CSV files.

    Expects columns (case-insensitive): date, type, asset, amount, price, fee.
    """
    # Build case-insensitive column map for the first row
    results: list[CryptoTransaction] = []

    def _col(row: dict[str, str], *names: str) -> str | None:
        lower_row = {k.lower(): v for k, v in row.items()}
        for name in names:
            val = lower_row.get(name.lower())
            if val is not None:
                return val
        return None

    for row in rows:
        try:
            date_utc = _parse_date(_sanitize_str(_col(row, "date", "datetime", "timestamp")))
            if not date_utc:
                continue

            asset = _normalise_asset(_col(row, "asset", "coin", "currency", "symbol"))
            if not asset or _is_fiat(asset):
                continue

            raw_type = _sanitize_str(_col(row, "type", "operation", "side") or "").lower()
            _GENERIC_MAP: dict[str, str] = {
                "buy": "buy",
                "sell": "sell",
                "swap": "swap",
                "staking": "staking_reward",
                "staking_reward": "staking_reward",
                "reward": "staking_reward",
                "airdrop": "airdrop",
                "mining": "mining",
                "fee": "fee",
                "transfer": "transfer",
                "deposit": "transfer",
                "withdrawal": "transfer",
            }
            tx_type = _GENERIC_MAP.get(raw_type, "transfer")

            amount = _parse_float(_col(row, "amount", "quantity", "qty"))
            if amount is None:
                continue
            amount = abs(amount)

            price_eur = _parse_float(_col(row, "price", "price_eur", "unit_price"))
            fee_eur = _parse_float(_col(row, "fee", "fee_eur", "fees")) or 0.0
            notes = _sanitize_str(_col(row, "notes", "note", "description", "memo") or "")

            results.append(
                CryptoTransaction(
                    tx_type=tx_type,
                    date_utc=date_utc,
                    asset=asset,
                    amount=amount,
                    price_eur=price_eur,
                    fee_eur=fee_eur,
                    exchange="unknown",
                    notes=notes,
                )
            )
        except Exception as exc:
            logger.warning("crypto_parser.generic_row_skip", error=str(exc), row=row)
            continue

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_csv(
    file_content: bytes,
    exchange: str | None = None,
) -> list[CryptoTransaction]:
    """
    Parse a CSV file containing cryptocurrency transaction history.

    Decodes the bytes (utf-8 → latin-1 fallback), auto-detects the source
    exchange when not provided, delegates to the appropriate parser, then
    returns rows sorted by date_utc ascending.

    Args:
        file_content: Raw CSV bytes.
        exchange: Optional exchange override. If None, auto-detected from headers.

    Returns:
        List of CryptoTransaction sorted ascending by date_utc.

    Raises:
        ValueError: If the file exceeds MAX_ROWS rows.
    """
    # Decode
    try:
        text = file_content.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        try:
            text = file_content.decode("latin-1")
        except UnicodeDecodeError:
            text = file_content.decode("utf-8", errors="replace")

    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, str]] = []

    for row in reader:
        rows.append(dict(row))
        if len(rows) > MAX_ROWS:
            raise ValueError(
                f"CSV exceeds maximum allowed rows ({MAX_ROWS})."
            )

    if not rows:
        logger.info("crypto_parser.empty_file")
        return []

    headers: list[str] = list(rows[0].keys())

    # Resolve exchange
    resolved_exchange = exchange or detect_exchange(headers)
    logger.info(
        "crypto_parser.parse_csv",
        exchange=resolved_exchange,
        row_count=len(rows),
    )

    # Dispatch
    if resolved_exchange == "binance":
        results = _parse_binance(rows)
    elif resolved_exchange == "coinbase":
        results = _parse_coinbase(rows)
    elif resolved_exchange == "kraken":
        results = _parse_kraken(rows)
    elif resolved_exchange in ("kucoin", "bitget"):
        results = _parse_kucoin(rows, exchange=resolved_exchange)
    else:
        results = _parse_generic(rows)

    return _sort_by_date(results)


def parse_excel(
    file_content: bytes,
    exchange: str | None = None,
) -> list[CryptoTransaction]:
    """
    Parse an .xlsx file containing cryptocurrency transaction history.

    Reads the first sheet with openpyxl, converts it to an in-memory CSV,
    then delegates to parse_csv.

    Args:
        file_content: Raw .xlsx bytes.
        exchange: Optional exchange override. If None, auto-detected from headers.

    Returns:
        List of CryptoTransaction sorted ascending by date_utc.

    Raises:
        ImportError: If openpyxl is not installed.
        ValueError: If the file exceeds MAX_ROWS rows.
    """
    if not _OPENPYXL_AVAILABLE:
        raise ImportError(
            "openpyxl is required to parse Excel files. "
            "Install it with: pip install openpyxl"
        )

    workbook = openpyxl.load_workbook(
        io.BytesIO(file_content), read_only=True, data_only=True
    )
    sheet = workbook.active

    output = io.StringIO()
    writer = csv.writer(output)

    row_count = 0
    for row in sheet.iter_rows(values_only=True):
        cells = [("" if cell is None else str(cell)) for cell in row]
        writer.writerow(cells)
        row_count += 1
        if row_count > MAX_ROWS + 1:  # +1 for header
            raise ValueError(
                f"Excel file exceeds maximum allowed rows ({MAX_ROWS})."
            )

    workbook.close()

    csv_bytes = output.getvalue().encode("utf-8")
    logger.info(
        "crypto_parser.parse_excel",
        exchange=exchange or "auto",
        row_count=row_count - 1,
    )
    return parse_csv(csv_bytes, exchange=exchange)
