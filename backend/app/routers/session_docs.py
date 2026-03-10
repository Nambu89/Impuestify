"""
Session Documents Router — Ephemeral document upload for chat context.

Documents are extracted, anonymized, and cached in Redis (2h TTL).
NOT stored in database. Cleared automatically or on browser session end.
"""
import uuid
import json
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from pydantic import BaseModel

from app.auth.jwt_handler import get_current_user, TokenData
from app.services.payslip_extractor import PayslipExtractor
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session-docs", tags=["session-documents"])

ACCEPTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_DOCS_PER_SESSION = 5
SESSION_DOC_TTL = 7200  # 2 hours
MAX_STORED_TEXT = 10_000  # chars stored in Redis per doc


class SessionDocResponse(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    summary: str
    page_count: int


def _classify_file_type(filename: str) -> str:
    """Classify file type from filename (reuses FileProcessingService logic)."""
    lower = filename.lower()
    if any(p in lower for p in ["nomina", "nómina", "payslip", "salario"]):
        return "nomina"
    if any(p in lower for p in ["factura", "invoice", "fra", "fact"]):
        return "factura"
    if any(p in lower for p in ["declaracion", "declaración", "modelo", "303", "130", "420"]):
        return "declaracion"
    if any(p in lower for p in ["notificacion", "notificación", "aeat", "requerimiento", "providencia"]):
        return "notificacion"
    return "otro"


def _build_summary(filename: str, file_type: str, page_count: int, extracted_data: dict) -> str:
    """Build a short human-readable summary."""
    type_labels = {
        "nomina": "Nomina",
        "factura": "Factura",
        "declaracion": "Declaracion fiscal",
        "notificacion": "Notificacion AEAT",
        "otro": "Documento",
    }
    label = type_labels.get(file_type, "Documento")
    parts = [f"{label} — {page_count} pag."]

    if file_type == "nomina":
        gross = extracted_data.get("gross_salary")
        net = extracted_data.get("net_salary")
        period = extracted_data.get("period_month")
        if gross:
            parts.append(f"Bruto: {gross:,.2f}EUR")
        if net:
            parts.append(f"Neto: {net:,.2f}EUR")
        if period:
            parts.append(f"Mes: {period}")
    elif file_type == "factura":
        total = extracted_data.get("total") or extracted_data.get("total_amount")
        if total:
            parts.append(f"Total: {total}EUR")

    return " | ".join(parts)


@router.post("/upload", response_model=SessionDocResponse)
@limiter.limit("10/minute")
async def upload_session_doc(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Upload a document for session-scoped chat context.
    Extracts text, anonymizes PII, caches in Redis. No DB storage.
    """
    # Validate file type
    if file.content_type not in ACCEPTED_MIME_TYPES:
        raise HTTPException(400, f"Tipo de archivo no soportado: {file.content_type}")

    # Read and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, f"Archivo demasiado grande (max {MAX_FILE_SIZE // 1024 // 1024}MB)")

    # Check Redis availability
    upstash = getattr(request.app.state, "upstash_client", None)
    if not upstash:
        raise HTTPException(503, "Servicio de cache no disponible")

    # Check max docs per session
    existing_keys = await upstash.keys(f"session_doc:{current_user.user_id}:*")
    if existing_keys and len(existing_keys) >= MAX_DOCS_PER_SESSION:
        raise HTTPException(400, f"Maximo {MAX_DOCS_PER_SESSION} documentos por sesion")

    # Classify file type
    file_type = _classify_file_type(file.filename or "document.pdf")

    # Extract text
    extracted_text = ""
    page_count = 0
    extracted_data = {}

    if file.content_type == "application/pdf":
        from app.utils.pdf_extractor import extract_pdf_text, extract_pdf_text_plain

        # Use plain text for tabular docs, markdown for others
        if file_type in ("nomina", "factura"):
            result = await extract_pdf_text_plain(content, file.filename)
        else:
            result = await extract_pdf_text(content, file.filename)

        if result.success:
            extracted_text = result.markdown_text
            page_count = result.total_pages

            # Run specialized extractors
            if file_type == "nomina":
                extractor = PayslipExtractor()
                extracted_data = extractor._parse_payslip_data(extracted_text)
            elif file_type == "factura":
                try:
                    from app.services.invoice_extractor import get_invoice_extractor
                    inv_extractor = get_invoice_extractor()
                    extracted_data = await inv_extractor.extract_from_text(extracted_text)
                except Exception as e:
                    logger.warning(f"Invoice extraction failed: {e}")
        else:
            raise HTTPException(422, f"No se pudo extraer texto del PDF: {result.error}")
    else:
        # Image — no text extraction yet, just store reference
        page_count = 1

    # PII anonymization
    anonymized_text = PayslipExtractor.anonymize_text(extracted_text[:MAX_STORED_TEXT])
    safe_data = PayslipExtractor.anonymize_data(extracted_data) if extracted_data else {}

    # Generate doc ID and cache in Redis
    doc_id = str(uuid.uuid4())[:12]
    cache_key = f"session_doc:{current_user.user_id}:{doc_id}"

    cache_payload = {
        "doc_id": doc_id,
        "user_id": current_user.user_id,
        "filename": file.filename,
        "file_type": file_type,
        "extracted_text": anonymized_text,
        "extracted_data": safe_data,
        "page_count": page_count,
    }

    await upstash.set(cache_key, json.dumps(cache_payload, ensure_ascii=False), ex=SESSION_DOC_TTL)
    logger.info(f"Session doc cached: {doc_id} ({file_type}, {page_count} pages, {len(anonymized_text)} chars)")

    summary = _build_summary(file.filename, file_type, page_count, extracted_data)

    return SessionDocResponse(
        doc_id=doc_id,
        filename=file.filename,
        file_type=file_type,
        summary=summary,
        page_count=page_count,
    )


@router.delete("/{doc_id}")
async def delete_session_doc(
    request: Request,
    doc_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a session document from cache."""
    upstash = getattr(request.app.state, "upstash_client", None)
    if not upstash:
        raise HTTPException(503, "Servicio de cache no disponible")

    cache_key = f"session_doc:{current_user.user_id}:{doc_id}"
    deleted = await upstash.delete(cache_key)

    if not deleted:
        raise HTTPException(404, "Documento no encontrado o ya expirado")

    return {"status": "deleted", "doc_id": doc_id}


@router.get("/list", response_model=List[SessionDocResponse])
async def list_session_docs(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """List all session documents for the current user (for session restore)."""
    upstash = getattr(request.app.state, "upstash_client", None)
    if not upstash:
        return []

    keys = await upstash.keys(f"session_doc:{current_user.user_id}:*")
    if not keys:
        return []

    docs = []
    for key in keys[:MAX_DOCS_PER_SESSION]:
        raw = await upstash.get(key)
        if raw:
            data = json.loads(raw)
            docs.append(SessionDocResponse(
                doc_id=data["doc_id"],
                filename=data["filename"],
                file_type=data["file_type"],
                summary=_build_summary(
                    data["filename"], data["file_type"],
                    data.get("page_count", 0), data.get("extracted_data", {})
                ),
                page_count=data.get("page_count", 0),
            ))

    return docs
