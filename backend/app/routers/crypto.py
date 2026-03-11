"""
Crypto REST API — Gestion de transacciones de criptomonedas.

Permite subir historiales CSV/XLSX de exchanges, listar transacciones,
consultar el portfolio actual y calcular ganancias/perdidas FIFO para IRPF.

Endpoints:
  POST /api/crypto/upload          — Subir CSV/XLSX de exchange
  GET  /api/crypto/transactions    — Listar transacciones (paginado)
  GET  /api/crypto/holdings        — Portfolio actual agregado por activo
  GET  /api/crypto/gains           — Ganancias/perdidas FIFO por ejercicio
  DELETE /api/crypto/transactions/{id} — Eliminar transaccion (ownership check)
"""
import io
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field
from starlette.requests import Request

from app.auth.jwt_handler import get_current_user, TokenData
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crypto", tags=["crypto"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
_XLSX_MAGIC = b"PK"  # ZIP/XLSX magic bytes
_VALID_EXCHANGES = {"binance", "coinbase", "kraken", "kucoin", "bitget"}


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class UploadResponse(BaseModel):
    success: bool = True
    imported: int = 0
    duplicates_skipped: int = 0
    exchange_detected: str = ""
    date_range: Dict[str, str] = Field(default_factory=dict)
    error: Optional[str] = None


class TransactionItem(BaseModel):
    id: str
    exchange: str
    tx_type: str
    date_utc: str
    asset: str
    amount: float
    price_eur: Optional[float]
    total_eur: Optional[float]
    fee_eur: Optional[float]
    counterpart_asset: Optional[str]
    counterpart_amount: Optional[float]
    notes: Optional[str]


class TransactionsResponse(BaseModel):
    success: bool = True
    transactions: List[TransactionItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    per_page: int = 50
    error: Optional[str] = None


class HoldingItem(BaseModel):
    asset: str
    total_units: float
    avg_cost_eur: float
    total_invested_eur: float


class HoldingsResponse(BaseModel):
    success: bool = True
    holdings: List[HoldingItem] = Field(default_factory=list)
    total_invested_eur: float = 0.0
    error: Optional[str] = None


class GainItem(BaseModel):
    asset: str
    tx_type: str
    clave_contraprestacion: str
    date_acquisition: str
    date_transmission: str
    acquisition_value_eur: float
    acquisition_fees_eur: float
    transmission_value_eur: float
    transmission_fees_eur: float
    gain_loss_eur: float
    anti_aplicacion: bool


class GainsSummary(BaseModel):
    casilla_1813: float  # perdidas patrimoniales cripto
    casilla_1814: float  # ganancias patrimoniales cripto
    net: float
    total_transactions: int


class GainsResponse(BaseModel):
    success: bool = True
    tax_year: int
    gains: List[GainItem] = Field(default_factory=list)
    summary: GainsSummary = Field(
        default_factory=lambda: GainsSummary(
            casilla_1813=0.0, casilla_1814=0.0, net=0.0, total_transactions=0
        )
    )
    error: Optional[str] = None


class DeleteResponse(BaseModel):
    deleted: bool = True


# ---------------------------------------------------------------------------
# Helper: file validation
# ---------------------------------------------------------------------------


def _validate_upload(file_bytes: bytes, filename: str) -> str:
    """
    Valida el archivo subido y devuelve el formato detectado ('csv' o 'xlsx').

    Raises:
        HTTPException 413: si el archivo supera 10 MB.
        HTTPException 415: si el tipo MIME no es CSV ni XLSX.
    """
    if len(file_bytes) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail="El archivo supera el limite de 10 MB. Divide el historial en periodos mas cortos.",
        )

    # Detectar formato por magic bytes
    if file_bytes[:2] == _XLSX_MAGIC:
        return "xlsx"

    # CSV: texto plano (sin magic bytes binarios en los primeros bytes)
    # Verificar que no es un binario desconocido
    try:
        file_bytes[:512].decode("utf-8", errors="strict")
        return "csv"
    except UnicodeDecodeError:
        # Intentar latin-1 (algunos CSV de exchanges usan esta codificacion)
        try:
            file_bytes[:512].decode("latin-1", errors="strict")
            return "csv"
        except Exception:
            pass

    name_lower = filename.lower()
    if name_lower.endswith(".csv"):
        return "csv"
    if name_lower.endswith(".xlsx") or name_lower.endswith(".xls"):
        return "xlsx"

    raise HTTPException(
        status_code=415,
        detail=(
            "Formato de archivo no soportado. Sube un archivo CSV o XLSX "
            "exportado desde tu exchange."
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("5/minute")
async def upload_crypto_csv(
    request: Request,
    file: UploadFile = File(...),
    exchange: Optional[str] = Query(
        default=None,
        description="Exchange de origen (opcional, auto-detectado). Valores: binance, coinbase, kraken, kucoin, bitget.",
    ),
    current_user: TokenData = Depends(get_current_user),
) -> UploadResponse:
    """
    Sube un archivo CSV o XLSX con el historial de transacciones de un exchange.

    - Detecta automaticamente el formato (CSV/XLSX) por magic bytes.
    - Detecta el exchange por las cabeceras del archivo si no se indica.
    - Deduplicacion: omite transacciones ya existentes (misma fecha, activo, cantidad, tipo y exchange).
    - Limite: 10 MB por archivo, 5 subidas por minuto y usuario.
    """
    if exchange and exchange.lower() not in _VALID_EXCHANGES:
        raise HTTPException(
            status_code=422,
            detail=f"Exchange no valido: {exchange!r}. Valores permitidos: {', '.join(sorted(_VALID_EXCHANGES))}.",
        )

    file_bytes = await file.read()
    filename = file.filename or "upload"
    file_format = _validate_upload(file_bytes, filename)

    # Parsear con crypto_parser
    try:
        from app.services.crypto_parser import parse_csv, parse_excel

        if file_format == "xlsx":
            transactions = parse_excel(file_bytes, exchange=exchange)
        else:
            transactions = parse_csv(file_bytes, exchange=exchange)
    except ValueError as exc:
        return UploadResponse(
            success=False,
            error=f"El archivo tiene demasiadas filas: {exc}. Divide el historial en periodos mas cortos.",
        )
    except ImportError:
        return UploadResponse(
            success=False,
            error="Para procesar archivos Excel se necesita openpyxl. Exporta tu historial en formato CSV.",
        )
    except Exception as exc:
        logger.error("crypto upload: error al parsear: %s", exc, exc_info=True)
        return UploadResponse(
            success=False,
            error=f"No se pudo procesar el archivo: {exc}. Comprueba que el formato sea correcto para tu exchange.",
        )

    if not transactions:
        return UploadResponse(
            success=True,
            imported=0,
            duplicates_skipped=0,
            exchange_detected=exchange or "desconocido",
            date_range={"from": "", "to": ""},
        )

    detected_exchange = transactions[0].exchange if transactions else (exchange or "desconocido")

    # Guardar en BD con deduplicacion
    try:
        from app.database.turso_client import get_db_client

        db = await get_db_client()
        imported_count = 0
        skipped_count = 0

        for tx in transactions:
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
                    current_user.user_id,
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
                    current_user.user_id,
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
        logger.error("crypto upload: error guardando en BD: %s", exc, exc_info=True)
        return UploadResponse(
            success=False,
            error=f"Las transacciones se parsearon pero no se pudieron guardar: {exc}.",
        )

    dates = [tx.date_utc for tx in transactions if tx.date_utc]
    date_from = min(dates)[:10] if dates else ""
    date_to = max(dates)[:10] if dates else ""

    return UploadResponse(
        success=True,
        imported=imported_count,
        duplicates_skipped=skipped_count,
        exchange_detected=detected_exchange,
        date_range={"from": date_from, "to": date_to},
    )


@router.get("/transactions", response_model=TransactionsResponse)
@limiter.limit("30/minute")
async def list_transactions(
    request: Request,
    page: int = Query(default=1, ge=1, description="Numero de pagina"),
    per_page: int = Query(default=50, ge=1, le=200, description="Resultados por pagina (max 200)"),
    asset: Optional[str] = Query(default=None, description="Filtrar por activo (BTC, ETH...)"),
    tx_type: Optional[str] = Query(
        default=None,
        description="Filtrar por tipo: buy, sell, swap, staking_reward, airdrop, mining, transfer, fee",
    ),
    current_user: TokenData = Depends(get_current_user),
) -> TransactionsResponse:
    """
    Lista las transacciones de criptomonedas del usuario con paginacion.

    Filtra opcionalmente por activo y tipo de transaccion.
    Devuelve un maximo de 200 transacciones por pagina.
    """
    try:
        from app.database.turso_client import get_db_client

        db = await get_db_client()

        # Construir filtros dinamicos (siempre con parametros para evitar inyeccion SQL)
        filters = ["user_id = ?"]
        params: list[Any] = [current_user.user_id]

        if asset:
            filters.append("asset = ?")
            params.append(asset.upper())

        if tx_type:
            filters.append("tx_type = ?")
            params.append(tx_type.lower())

        where_clause = " AND ".join(filters)

        # Contar total
        count_result = await db.execute(
            f"SELECT COUNT(*) as cnt FROM crypto_transactions WHERE {where_clause}",
            params,
        )
        total = count_result.rows[0]["cnt"] if count_result.rows else 0

        # Paginar
        offset = (page - 1) * per_page
        rows_result = await db.execute(
            f"""
            SELECT id, exchange, tx_type, date_utc,
                   asset, amount, price_eur, total_eur, fee_eur,
                   counterpart_asset, counterpart_amount, notes
            FROM crypto_transactions
            WHERE {where_clause}
            ORDER BY date_utc DESC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        )

        rows = rows_result.rows or []
        items = [
            TransactionItem(
                id=row["id"],
                exchange=row["exchange"] or "",
                tx_type=row["tx_type"] or "",
                date_utc=row["date_utc"] or "",
                asset=row["asset"] or "",
                amount=float(row["amount"] or 0),
                price_eur=float(row["price_eur"]) if row["price_eur"] is not None else None,
                total_eur=float(row["total_eur"]) if row["total_eur"] is not None else None,
                fee_eur=float(row["fee_eur"]) if row["fee_eur"] is not None else None,
                counterpart_asset=row["counterpart_asset"],
                counterpart_amount=(
                    float(row["counterpart_amount"])
                    if row["counterpart_amount"] is not None
                    else None
                ),
                notes=row["notes"],
            )
            for row in rows
        ]

        return TransactionsResponse(
            success=True,
            transactions=items,
            total=total,
            page=page,
            per_page=per_page,
        )

    except Exception as exc:
        logger.error("crypto list_transactions error: %s", exc, exc_info=True)
        return TransactionsResponse(success=False, error=str(exc))


@router.get("/holdings", response_model=HoldingsResponse)
@limiter.limit("20/minute")
async def get_holdings(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
) -> HoldingsResponse:
    """
    Devuelve el portfolio actual del usuario agregado por activo.

    Calcula el coste medio ponderado y la inversion total en EUR
    a partir de las transacciones de compra registradas.
    """
    try:
        from app.database.turso_client import get_db_client

        db = await get_db_client()

        # Intentar leer del cache (crypto_holdings)
        cache_result = await db.execute(
            """
            SELECT asset, total_units, avg_cost_eur, total_invested_eur
            FROM crypto_holdings
            WHERE user_id = ?
            ORDER BY total_invested_eur DESC
            """,
            [current_user.user_id],
        )

        if cache_result.rows:
            items = [
                HoldingItem(
                    asset=row["asset"],
                    total_units=float(row["total_units"] or 0),
                    avg_cost_eur=float(row["avg_cost_eur"] or 0),
                    total_invested_eur=float(row["total_invested_eur"] or 0),
                )
                for row in cache_result.rows
            ]
            total_invested = sum(h.total_invested_eur for h in items)
            return HoldingsResponse(
                success=True,
                holdings=items,
                total_invested_eur=round(total_invested, 2),
            )

        # Si no hay cache: calcular desde transacciones
        tx_result = await db.execute(
            """
            SELECT asset, tx_type, amount, total_eur, price_eur, fee_eur
            FROM crypto_transactions
            WHERE user_id = ?
              AND tx_type IN ('buy', 'staking_reward', 'airdrop', 'mining')
            ORDER BY date_utc ASC
            """,
            [current_user.user_id],
        )

        rows = tx_result.rows or []
        if not rows:
            return HoldingsResponse(success=True, holdings=[], total_invested_eur=0.0)

        # Calcular coste medio ponderado por activo
        holdings_data: dict[str, dict[str, float]] = {}
        for row in rows:
            asset = row["asset"] or ""
            if not asset:
                continue
            amount = float(row["amount"] or 0)
            fee_eur = float(row["fee_eur"] or 0)

            # Calcular coste total de la operacion en EUR
            if row["total_eur"] is not None:
                cost_eur = float(row["total_eur"]) + fee_eur
            elif row["price_eur"] is not None and amount:
                cost_eur = float(row["price_eur"]) * amount + fee_eur
            else:
                # Sin precio: no podemos calcular el coste; omitir del calculo medio
                cost_eur = 0.0

            if asset not in holdings_data:
                holdings_data[asset] = {"total_units": 0.0, "total_cost_eur": 0.0}

            holdings_data[asset]["total_units"] += amount
            holdings_data[asset]["total_cost_eur"] += cost_eur

        # Descontar ventas/swaps para obtener saldo neto
        sell_result = await db.execute(
            """
            SELECT asset, amount
            FROM crypto_transactions
            WHERE user_id = ?
              AND tx_type IN ('sell', 'swap')
            """,
            [current_user.user_id],
        )
        for row in sell_result.rows or []:
            asset = row["asset"] or ""
            if asset in holdings_data:
                holdings_data[asset]["total_units"] -= float(row["amount"] or 0)

        items = []
        total_invested = 0.0
        for asset, data in holdings_data.items():
            units = max(0.0, data["total_units"])
            if units < 1e-10:
                continue  # Activo completamente vendido
            cost_eur = data["total_cost_eur"]
            avg_cost = cost_eur / (data["total_units"] or 1.0)
            invested = avg_cost * units
            items.append(
                HoldingItem(
                    asset=asset,
                    total_units=round(units, 8),
                    avg_cost_eur=round(avg_cost, 4),
                    total_invested_eur=round(invested, 2),
                )
            )
            total_invested += invested

        # Ordenar por inversion total descendente
        items.sort(key=lambda h: h.total_invested_eur, reverse=True)

        return HoldingsResponse(
            success=True,
            holdings=items,
            total_invested_eur=round(total_invested, 2),
        )

    except Exception as exc:
        logger.error("crypto get_holdings error: %s", exc, exc_info=True)
        return HoldingsResponse(success=False, error=str(exc))


@router.get("/gains", response_model=GainsResponse)
@limiter.limit("20/minute")
async def get_gains(
    request: Request,
    tax_year: int = Query(
        default=0,
        description="Ejercicio fiscal (ej: 2024, 2025). Por defecto el ano anterior al actual.",
    ),
    current_user: TokenData = Depends(get_current_user),
) -> GainsResponse:
    """
    Calcula las ganancias y perdidas patrimoniales FIFO del usuario por ejercicio fiscal.

    Usa el metodo FIFO obligatorio (Art. 37.1.Undecies LIRPF) y devuelve:
    - Lista detallada de ganancias/perdidas por operacion
    - Resumen con casillas 1813 (perdidas) y 1814 (ganancias) del Modelo 100
    """
    if tax_year == 0:
        tax_year = datetime.now().year - 1

    try:
        from app.database.turso_client import get_db_client
        from app.utils.calculators.crypto_fifo import calculate_fifo_gains
        from app.services.crypto_parser import CryptoTransaction

        db = await get_db_client()

        # Leer todas las transacciones del usuario (FIFO necesita el historial completo)
        tx_result = await db.execute(
            """
            SELECT tx_type, date_utc, asset, amount,
                   price_eur, total_eur, fee_eur, exchange,
                   counterpart_asset, counterpart_amount, notes
            FROM crypto_transactions
            WHERE user_id = ?
            ORDER BY date_utc ASC
            """,
            [current_user.user_id],
        )

        rows = tx_result.rows or []
        if not rows:
            return GainsResponse(
                success=True,
                tax_year=tax_year,
                gains=[],
                summary=GainsSummary(
                    casilla_1813=0.0, casilla_1814=0.0, net=0.0, total_transactions=0
                ),
            )

        transactions = [
            CryptoTransaction(
                tx_type=row["tx_type"] or "transfer",
                date_utc=row["date_utc"] or "",
                asset=row["asset"] or "",
                amount=float(row["amount"] or 0),
                price_eur=float(row["price_eur"]) if row["price_eur"] is not None else None,
                total_eur=float(row["total_eur"]) if row["total_eur"] is not None else None,
                fee_eur=float(row["fee_eur"] or 0),
                exchange=row["exchange"] or "manual",
                counterpart_asset=row["counterpart_asset"],
                counterpart_amount=(
                    float(row["counterpart_amount"])
                    if row["counterpart_amount"] is not None
                    else None
                ),
                notes=row["notes"] or "",
            )
            for row in rows
        ]

        fifo_result = calculate_fifo_gains(transactions, tax_year=tax_year)
        summary_data = fifo_result.summary

        gain_items = [
            GainItem(
                asset=g.asset,
                tx_type=g.tx_type,
                clave_contraprestacion=g.clave_contraprestacion,
                date_acquisition=g.date_acquisition,
                date_transmission=g.date_transmission,
                acquisition_value_eur=g.acquisition_value_eur,
                acquisition_fees_eur=g.acquisition_fees_eur,
                transmission_value_eur=g.transmission_value_eur,
                transmission_fees_eur=g.transmission_fees_eur,
                gain_loss_eur=g.gain_loss_eur,
                anti_aplicacion=g.anti_aplicacion,
            )
            for g in fifo_result.gains
        ]

        summary = GainsSummary(
            casilla_1813=summary_data.get("casilla_1813", 0.0),
            casilla_1814=summary_data.get("casilla_1814", 0.0),
            net=summary_data.get("net_result_eur", 0.0),
            total_transactions=len(rows),
        )

        return GainsResponse(
            success=True,
            tax_year=tax_year,
            gains=gain_items,
            summary=summary,
        )

    except Exception as exc:
        logger.error("crypto get_gains error: %s", exc, exc_info=True)
        return GainsResponse(
            success=False,
            tax_year=tax_year,
            error=str(exc),
        )


@router.delete("/transactions/{transaction_id}", response_model=DeleteResponse)
@limiter.limit("20/minute")
async def delete_transaction(
    transaction_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
) -> DeleteResponse:
    """
    Elimina una transaccion de criptomonedas del usuario.

    Verifica que la transaccion pertenece al usuario autenticado antes de borrarla.
    Devuelve 404 si no existe o pertenece a otro usuario.
    """
    try:
        from app.database.turso_client import get_db_client

        db = await get_db_client()

        # Ownership check: verificar que la transaccion pertenece al usuario
        check_result = await db.execute(
            "SELECT id FROM crypto_transactions WHERE id = ? AND user_id = ?",
            [transaction_id, current_user.user_id],
        )

        if not check_result.rows:
            raise HTTPException(
                status_code=404,
                detail="Transaccion no encontrada o no tienes permiso para eliminarla.",
            )

        await db.execute(
            "DELETE FROM crypto_transactions WHERE id = ? AND user_id = ?",
            [transaction_id, current_user.user_id],
        )

        return DeleteResponse(deleted=True)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("crypto delete_transaction error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la transaccion: {exc}",
        )
