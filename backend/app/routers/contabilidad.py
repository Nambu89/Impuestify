"""
Contabilidad Router for TaxIA (Impuestify)

Provides endpoints for querying accounting books (libro diario, libro mayor,
balance de sumas y saldos, PyG) and exporting them as CSV or Excel.
"""
import io
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.database.turso_client import get_db_client
from app.services.contabilidad_service import ContabilidadService
from app.services.contabilidad_export_service import ContabilidadExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contabilidad", tags=["contabilidad"])

MEDIA_CSV = "text/csv"
MEDIA_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ---------------------------------------------------------------------------
# GET /libro-diario
# ---------------------------------------------------------------------------

@router.get("/libro-diario")
async def get_libro_diario(
    request: Request,
    year: int = Query(default=2026, ge=2020, le=2099),
    trimestre: Optional[int] = Query(default=None, ge=1, le=4),
    current_user: TokenData = Depends(get_current_user),
    _sub=Depends(require_active_subscription),
):
    """Get journal entries (libro diario) for the authenticated user."""
    service = ContabilidadService()
    entries = await service.get_libro_diario(
        user_id=current_user.user_id,
        year=year,
        trimestre=trimestre,
    )
    return {"entries": entries, "year": year, "trimestre": trimestre}


# ---------------------------------------------------------------------------
# GET /libro-mayor
# ---------------------------------------------------------------------------

@router.get("/libro-mayor")
async def get_libro_mayor(
    request: Request,
    year: int = Query(default=2026, ge=2020, le=2099),
    current_user: TokenData = Depends(get_current_user),
    _sub=Depends(require_active_subscription),
):
    """Get general ledger (libro mayor) grouped by account."""
    service = ContabilidadService()
    accounts = await service.get_libro_mayor(
        user_id=current_user.user_id,
        year=year,
    )
    return {"accounts": accounts, "year": year}


# ---------------------------------------------------------------------------
# GET /balance
# ---------------------------------------------------------------------------

@router.get("/balance")
async def get_balance(
    request: Request,
    year: int = Query(default=2026, ge=2020, le=2099),
    current_user: TokenData = Depends(get_current_user),
    _sub=Depends(require_active_subscription),
):
    """Get trial balance (balance de sumas y saldos)."""
    service = ContabilidadService()
    return await service.get_balance_sumas_saldos(
        user_id=current_user.user_id,
        year=year,
    )


# ---------------------------------------------------------------------------
# GET /pyg
# ---------------------------------------------------------------------------

@router.get("/pyg")
async def get_pyg(
    request: Request,
    year: int = Query(default=2026, ge=2020, le=2099),
    current_user: TokenData = Depends(get_current_user),
    _sub=Depends(require_active_subscription),
):
    """Get profit & loss statement (cuenta de perdidas y ganancias)."""
    service = ContabilidadService()
    return await service.get_pyg(
        user_id=current_user.user_id,
        year=year,
    )


# ---------------------------------------------------------------------------
# GET /export/{libro}
# ---------------------------------------------------------------------------

_VALID_LIBROS = {"libro-diario", "libro-mayor", "libro-registro", "pyg"}


@router.get("/export/{libro}")
async def export_libro(
    request: Request,
    libro: str,
    year: int = Query(default=2026, ge=2020, le=2099),
    trimestre: Optional[int] = Query(default=None, ge=1, le=4),
    format: str = Query(default="csv", regex="^(csv|excel)$"),
    current_user: TokenData = Depends(get_current_user),
    _sub=Depends(require_active_subscription),
):
    """Export an accounting book as CSV or Excel."""
    if libro not in _VALID_LIBROS:
        raise HTTPException(
            status_code=400,
            detail=f"Libro no valido: '{libro}'. Opciones: {', '.join(sorted(_VALID_LIBROS))}",
        )

    service = ContabilidadService()
    export = ContabilidadExportService

    # Build filename
    ext = "csv" if format == "csv" else "xlsx"
    filename = f"{libro}_{year}"
    if trimestre is not None:
        filename += f"_T{trimestre}"
    filename += f".{ext}"

    content: bytes

    if libro == "libro-diario":
        entries = await service.get_libro_diario(
            user_id=current_user.user_id, year=year, trimestre=trimestre,
        )
        content = (
            export.libro_diario_to_csv(entries)
            if format == "csv"
            else export.libro_diario_to_excel(entries)
        )

    elif libro == "libro-mayor":
        accounts = await service.get_libro_mayor(
            user_id=current_user.user_id, year=year,
        )
        content = (
            export.libro_mayor_to_csv(accounts)
            if format == "csv"
            else export.libro_mayor_to_excel(accounts)
        )

    elif libro == "libro-registro":
        # Query libro_registro table directly
        db = await get_db_client()
        sql = """
            SELECT fecha_factura, numero_factura, tipo, emisor_nif, emisor_nombre,
                   receptor_nif, receptor_nombre, base_imponible, tipo_iva,
                   cuota_iva, retencion_irpf, total, cuenta_pgc, concepto
            FROM libro_registro
            WHERE user_id = ? AND year = ?
        """
        params = [current_user.user_id, year]
        if trimestre is not None:
            sql += " AND trimestre = ?"
            params.append(trimestre)
        sql += " ORDER BY fecha"

        result = await db.execute(sql, params)
        facturas = list(result.rows) if result.rows else []
        content = export.libro_registro_to_csv(facturas)
        # libro-registro only supports CSV (no Excel exporter defined)

    elif libro == "pyg":
        pyg_data = await service.get_pyg(
            user_id=current_user.user_id, year=year,
        )
        if format == "csv":
            # PyG only has Excel exporter; for CSV, build a simple fallback
            import csv as csv_mod
            buf = io.StringIO()
            writer = csv_mod.writer(buf)
            writer.writerow(["Concepto", "Importe"])
            writer.writerow(["--- INGRESOS ---", ""])
            for item in pyg_data.get("ingresos", []):
                writer.writerow([
                    item.get("cuenta_nombre", ""),
                    item.get("total_haber", 0) - item.get("total_debe", 0),
                ])
            writer.writerow(["Total Ingresos", pyg_data.get("total_ingresos", 0)])
            writer.writerow([])
            writer.writerow(["--- GASTOS ---", ""])
            for item in pyg_data.get("gastos", []):
                writer.writerow([
                    item.get("cuenta_nombre", ""),
                    item.get("total_debe", 0) - item.get("total_haber", 0),
                ])
            writer.writerow(["Total Gastos", pyg_data.get("total_gastos", 0)])
            writer.writerow([])
            writer.writerow(["RESULTADO", pyg_data.get("resultado", 0)])
            content = buf.getvalue().encode("utf-8-sig")
        else:
            content = export.pyg_to_excel(pyg_data)

    media_type = MEDIA_CSV if format == "csv" else MEDIA_EXCEL

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
