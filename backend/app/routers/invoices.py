"""
Invoices router — Upload, OCR extraction, PGC classification, and CRUD.

Endpoints:
  POST   /api/invoices/upload          Upload + OCR + classify + journal entry
  GET    /api/invoices                  List user invoices
  GET    /api/invoices/{invoice_id}     Invoice detail + asiento
  PUT    /api/invoices/{id}/reclassify  Manual reclassification
  DELETE /api/invoices/{invoice_id}     Delete invoice + asientos (GDPR)
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query, Request
from pydantic import BaseModel

from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.services.subscription_service import SubscriptionAccess
from app.config import settings
from app.database.turso_client import get_db_client
from app.security.rate_limiter import limiter
from app.services.invoice_ocr_service import InvoiceOCRService
from app.services.invoice_classifier_service import InvoiceClassifierService
from app.services.contabilidad_service import ContabilidadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_MIME_TYPES = {
    "application/pdf": b"%PDF",
    "image/jpeg": b"\xff\xd8",
    "image/png": b"\x89PNG",
}

ALLOWED_PLANS = {"autonomo", "creator"}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ReclassifyRequest(BaseModel):
    cuenta_pgc: str
    cuenta_pgc_nombre: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_trimestre(month: int) -> int:
    """Return trimestre 1-4 from month 1-12."""
    return (month - 1) // 3 + 1


def _validate_file(file_bytes: bytes, content_type: str | None) -> str:
    """Validate file size, MIME type, and magic bytes. Returns resolved MIME type."""
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"El archivo excede el tamaño máximo de {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    if not content_type or content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no soportado: {content_type}. "
                   f"Se aceptan: {', '.join(ALLOWED_MIME_TYPES.keys())}",
        )

    expected_magic = ALLOWED_MIME_TYPES[content_type]
    if not file_bytes[:len(expected_magic)] == expected_magic:
        raise HTTPException(
            status_code=400,
            detail="El contenido del archivo no coincide con el tipo declarado.",
        )

    return content_type


# ---------------------------------------------------------------------------
# POST /upload
# ---------------------------------------------------------------------------

@router.post("/upload")
@limiter.limit("10/minute")
async def upload_invoice(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
):
    """Sube una factura, extrae datos con OCR, clasifica PGC y genera asiento contable."""

    # Plan gate: only autonomo, creator, or owner
    if not access.is_owner and access.plan_type not in ALLOWED_PLANS:
        raise HTTPException(
            status_code=403,
            detail="Esta funcionalidad requiere plan Autónomo o Creator.",
        )

    # Read and validate file
    file_bytes = await file.read()
    mime_type = _validate_file(file_bytes, file.content_type)

    # --- OCR extraction ---
    if not settings.GOOGLE_GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Servicio OCR no configurado.")

    ocr_service = InvoiceOCRService(api_key=settings.GOOGLE_GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    try:
        extraction = await ocr_service.extract_from_bytes(file_bytes, mime_type)
    except Exception as exc:
        logger.error("OCR extraction failed", exc_info=exc)
        raise HTTPException(status_code=422, detail=f"Error extrayendo datos de la factura: {exc}")

    factura = extraction.factura

    # --- PGC classification ---
    db = await get_db_client()
    classifier = InvoiceClassifierService(
        api_key=settings.GOOGLE_GEMINI_API_KEY,
        db=db,
        model=settings.GEMINI_MODEL,
    )

    concepto = ", ".join(l.concepto for l in factura.lineas) if factura.lineas else factura.numero_factura
    try:
        clasificacion = await classifier.classify(
            concepto=concepto,
            emisor_nombre=factura.emisor.nombre,
            tipo=factura.tipo,
            base_imponible=factura.base_imponible_total,
        )
    except Exception as exc:
        logger.error("Classification failed", exc_info=exc)
        raise HTTPException(status_code=422, detail=f"Error clasificando la factura: {exc}")

    # --- Parse date for year / trimestre ---
    try:
        fecha_dt = datetime.strptime(factura.fecha_factura, "%Y-%m-%d")
    except ValueError:
        # Fallback: try other common formats
        try:
            fecha_dt = datetime.strptime(factura.fecha_factura, "%d/%m/%Y")
        except ValueError:
            fecha_dt = datetime.now()

    year = fecha_dt.year
    trimestre = _parse_trimestre(fecha_dt.month)

    # --- Save to libro_registro ---
    invoice_id = str(uuid.uuid4())
    user_id = current_user.user_id

    raw_extraction_json = json.dumps(factura.model_dump(), default=str)
    clasificacion_json = json.dumps(clasificacion.model_dump(), default=str)

    await db.execute(
        """
        INSERT INTO libro_registro
            (id, user_id, tipo, numero_factura, fecha_factura, fecha_operacion,
             emisor_nif, emisor_nombre, receptor_nif, receptor_nombre,
             base_imponible, tipo_iva, cuota_iva,
             tipo_re, cuota_re, retencion_irpf_pct, retencion_irpf,
             total, cuenta_pgc, cuenta_pgc_nombre,
             clasificacion_confianza, raw_extraction,
             year, trimestre, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            invoice_id,
            user_id,
            factura.tipo,
            factura.numero_factura,
            factura.fecha_factura,
            factura.fecha_operacion,
            factura.emisor.nif_cif,
            factura.emisor.nombre,
            factura.receptor.nif_cif,
            factura.receptor.nombre,
            factura.base_imponible_total,
            factura.tipo_iva_pct,
            factura.cuota_iva,
            factura.tipo_re_pct,
            factura.cuota_re,
            factura.retencion_irpf_pct,
            factura.retencion_irpf,
            factura.total,
            clasificacion.cuenta_code,
            clasificacion.cuenta_nombre,
            clasificacion.confianza,
            raw_extraction_json,
            year,
            trimestre,
            datetime.now(timezone.utc).isoformat(),
        ],
    )

    # --- Generate + save asiento contable ---
    contabilidad = ContabilidadService(db=db)
    asiento_lines = ContabilidadService.generate_asiento_lines(
        tipo=factura.tipo,
        cuenta_pgc_code=clasificacion.cuenta_code,
        cuenta_pgc_nombre=clasificacion.cuenta_nombre,
        base_imponible=factura.base_imponible_total,
        cuota_iva=factura.cuota_iva,
        total=factura.total,
        retencion_irpf=factura.retencion_irpf or 0.0,
        concepto=concepto,
    )

    await contabilidad.save_asiento(
        user_id=user_id,
        libro_registro_id=invoice_id,
        fecha=factura.fecha_factura,
        lines=asiento_lines,
        year=year,
        trimestre=trimestre,
    )

    return {
        "id": invoice_id,
        "factura": factura.model_dump(),
        "clasificacion": clasificacion.model_dump(),
        "validacion": {
            "confianza_extraccion": extraction.confianza,
            "nif_emisor_valido": extraction.nif_emisor_valido,
            "nif_receptor_valido": extraction.nif_receptor_valido,
            "errores_validacion": extraction.errores_validacion,
        },
    }


# ---------------------------------------------------------------------------
# GET / — List invoices
# ---------------------------------------------------------------------------

@router.get("")
async def list_invoices(
    request: Request,
    year: int = Query(default=2026, ge=2000, le=2100),
    trimestre: Optional[int] = Query(default=None, ge=1, le=4),
    tipo: Optional[str] = Query(default=None, pattern="^(emitida|recibida)$"),
    current_user: TokenData = Depends(get_current_user),
):
    """Lista las facturas del usuario filtradas por año, trimestre y/o tipo."""
    db = await get_db_client()
    user_id = current_user.user_id

    query = "SELECT * FROM libro_registro WHERE user_id = ? AND year = ?"
    params: list = [user_id, year]

    if trimestre is not None:
        query += " AND trimestre = ?"
        params.append(trimestre)

    if tipo is not None:
        query += " AND tipo = ?"
        params.append(tipo)

    query += " ORDER BY fecha_factura DESC"

    result = await db.execute(query, params)
    invoices = [dict(row) for row in (result.rows or [])]

    return {"invoices": invoices}


# ---------------------------------------------------------------------------
# GET /{invoice_id} — Invoice detail + asiento
# ---------------------------------------------------------------------------

@router.get("/{invoice_id}")
async def get_invoice(
    request: Request,
    invoice_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Obtiene el detalle de una factura y su asiento contable asociado."""
    db = await get_db_client()
    user_id = current_user.user_id

    # Fetch invoice
    result = await db.execute(
        "SELECT * FROM libro_registro WHERE id = ?",
        [invoice_id],
    )
    if not result.rows:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")

    invoice = dict(result.rows[0])

    # Ownership check
    if invoice["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta factura.")

    # Fetch asiento lines
    asiento_result = await db.execute(
        "SELECT * FROM asientos_contables WHERE libro_registro_id = ? ORDER BY id",
        [invoice_id],
    )
    asiento = [dict(row) for row in (asiento_result.rows or [])]

    return {"invoice": invoice, "asiento": asiento}


# ---------------------------------------------------------------------------
# PUT /{invoice_id}/reclassify — Manual reclassification
# ---------------------------------------------------------------------------

@router.put("/{invoice_id}/reclassify")
async def reclassify_invoice(
    request: Request,
    invoice_id: str,
    body: ReclassifyRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Reclasifica manualmente una factura con una nueva cuenta PGC."""
    db = await get_db_client()
    user_id = current_user.user_id

    # Fetch invoice + ownership check
    result = await db.execute(
        "SELECT * FROM libro_registro WHERE id = ? AND user_id = ?",
        [invoice_id, user_id],
    )
    if not result.rows:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")

    invoice = dict(result.rows[0])

    # Update libro_registro with new classification
    await db.execute(
        """
        UPDATE libro_registro
        SET cuenta_pgc = ?, cuenta_pgc_nombre = ?, clasificacion_confianza = 'manual'
        WHERE id = ? AND user_id = ?
        """,
        [body.cuenta_pgc, body.cuenta_pgc_nombre, invoice_id, user_id],
    )

    # Delete old asientos
    await db.execute(
        "DELETE FROM asientos_contables WHERE libro_registro_id = ?",
        [invoice_id],
    )

    # Regenerate asiento with new classification
    concepto = f"Factura {invoice['numero_factura']}"
    asiento_lines = ContabilidadService.generate_asiento_lines(
        tipo=invoice["tipo"],
        cuenta_pgc_code=body.cuenta_pgc,
        cuenta_pgc_nombre=body.cuenta_pgc_nombre,
        base_imponible=invoice["base_imponible"],
        cuota_iva=invoice["cuota_iva"],
        total=invoice["total"],
        retencion_irpf=invoice.get("retencion_irpf") or 0.0,
        concepto=concepto,
    )

    contabilidad = ContabilidadService(db=db)
    year = invoice["year"]
    trimestre = invoice["trimestre"]

    await contabilidad.save_asiento(
        user_id=user_id,
        libro_registro_id=invoice_id,
        fecha=invoice["fecha_factura"],
        lines=asiento_lines,
        year=year,
        trimestre=trimestre,
    )

    return {
        "id": invoice_id,
        "cuenta_pgc": body.cuenta_pgc,
        "cuenta_pgc_nombre": body.cuenta_pgc_nombre,
        "clasificacion_confianza": "manual",
        "message": "Factura reclasificada correctamente.",
    }


# ---------------------------------------------------------------------------
# DELETE /{invoice_id} — Delete invoice + asientos (GDPR cascade)
# ---------------------------------------------------------------------------

@router.delete("/{invoice_id}")
async def delete_invoice(
    request: Request,
    invoice_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Elimina una factura y sus asientos contables asociados (GDPR cascade)."""
    db = await get_db_client()
    user_id = current_user.user_id

    # Verify ownership
    result = await db.execute(
        "SELECT id FROM libro_registro WHERE id = ? AND user_id = ?",
        [invoice_id, user_id],
    )
    if not result.rows:
        raise HTTPException(status_code=404, detail="Factura no encontrada.")

    # Delete asientos first (child records)
    await db.execute(
        "DELETE FROM asientos_contables WHERE libro_registro_id = ?",
        [invoice_id],
    )

    # Delete invoice
    await db.execute(
        "DELETE FROM libro_registro WHERE id = ? AND user_id = ?",
        [invoice_id, user_id],
    )

    logger.info("Invoice %s deleted for user %s (GDPR cascade)", invoice_id, user_id)

    return {"message": "Factura y asientos eliminados correctamente."}
