"""
Export Router for TaxIA.

Provides endpoints for generating IRPF reports and sharing them with advisors.
"""
import json
import logging
import secrets
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, EmailStr

from app.auth.jwt_handler import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


# === Request/Response Models ===

class IRPFReportRequest(BaseModel):
    """Request for IRPF report generation."""
    ccaa: str = Field(..., description="Comunidad autonoma")
    ingresos_trabajo: float = Field(0, description="Ingresos brutos anuales del trabajo")
    year: int = Field(2025, description="Ano fiscal")
    answers: Optional[Dict[str, Any]] = Field(default=None, description="Respuestas para deducciones")


class ShareWithAdvisorRequest(BaseModel):
    """Request to share a report with an advisor."""
    report_id: str = Field(..., description="ID del informe generado")
    advisor_email: EmailStr = Field(..., description="Email del asesor")
    message: Optional[str] = Field(default=None, description="Mensaje opcional")


class ReportResponse(BaseModel):
    """Response after report generation."""
    report_id: str
    share_token: str
    message: str


# === Endpoints ===

@router.post("/irpf-report", response_class=Response)
async def generate_irpf_report(
    request: Request,
    body: IRPFReportRequest,
    current_user=Depends(get_current_user),
):
    """
    Generate an IRPF report PDF.

    Runs simulate_irpf + discover_deductions, generates PDF, saves to DB.
    Returns PDF as download.
    """
    db = getattr(request.app.state, "db_client", None)
    if not db:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    user_id = current_user.user_id
    user_name = current_user.email or "Usuario"

    # Get fiscal profile
    fiscal_profile = {}
    try:
        profile_result = await db.execute(
            "SELECT datos_fiscales, ccaa_residencia, situacion_laboral FROM user_profiles WHERE user_id = ?",
            [user_id],
        )
        if profile_result.rows:
            row = profile_result.rows[0]
            if row.get("datos_fiscales"):
                fiscal_profile = json.loads(row["datos_fiscales"])
            if row.get("ccaa_residencia"):
                fiscal_profile["ccaa_residencia"] = row["ccaa_residencia"]
            if row.get("situacion_laboral"):
                fiscal_profile["situacion_laboral"] = row["situacion_laboral"]
    except Exception as e:
        logger.warning(f"Could not load fiscal profile: {e}")

    # Run IRPF simulation
    simulation_data = None
    if body.ingresos_trabajo > 0:
        try:
            from app.tools.irpf_simulator_tool import simulate_irpf_tool
            sim_result = await simulate_irpf_tool(
                comunidad_autonoma=body.ccaa,
                ingresos_trabajo=body.ingresos_trabajo,
                year=body.year,
            )
            if sim_result.get("success"):
                simulation_data = sim_result
        except Exception as e:
            logger.warning(f"IRPF simulation error: {e}")

    # Discover deductions
    deductions = []
    estimated_savings = 0.0
    try:
        from app.tools.deduction_discovery_tool import discover_deductions_tool
        ded_result = await discover_deductions_tool(
            ccaa=body.ccaa,
            tax_year=body.year,
            answers=body.answers or {},
        )
        if ded_result.get("success"):
            deductions = ded_result.get("eligible", [])
            estimated_savings = ded_result.get("estimated_savings", 0.0)
    except Exception as e:
        logger.warning(f"Deduction discovery error: {e}")

    # Generate PDF
    from app.services.report_generator import generate_irpf_report as gen_pdf
    pdf_bytes = gen_pdf(
        user_name=user_name,
        simulation_data=simulation_data,
        deductions=deductions,
        fiscal_profile=fiscal_profile,
        estimated_savings=estimated_savings,
    )

    # Save report to DB
    report_id = str(uuid.uuid4())
    share_token = secrets.token_urlsafe(32)

    report_data = json.dumps({
        "ccaa": body.ccaa,
        "year": body.year,
        "ingresos_trabajo": body.ingresos_trabajo,
        "simulation": simulation_data,
        "deductions_count": len(deductions),
        "estimated_savings": estimated_savings,
    })

    try:
        await db.execute(
            """INSERT INTO reports (id, user_id, report_type, title, report_data, pdf_bytes, share_token)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                report_id,
                user_id,
                "irpf",
                f"Informe IRPF {body.year} - {body.ccaa}",
                report_data,
                pdf_bytes,
                share_token,
            ],
        )
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
        # Still return the PDF even if DB save fails

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="informe_irpf_{body.year}.pdf"',
            "X-Report-Id": report_id,
            "X-Share-Token": share_token,
        },
    )


@router.post("/share-with-advisor")
async def share_with_advisor(
    request: Request,
    body: ShareWithAdvisorRequest,
    current_user=Depends(get_current_user),
):
    """
    Share a previously generated report with a tax advisor via email.
    """
    from app.config import settings

    if not settings.is_resend_configured:
        raise HTTPException(
            status_code=503,
            detail="El servicio de email no esta configurado. Contacta con soporte.",
        )

    db = getattr(request.app.state, "db_client", None)
    if not db:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    user_id = current_user.user_id
    user_name = current_user.email or "Usuario"

    # Verify report ownership
    result = await db.execute(
        "SELECT id, title, pdf_bytes FROM reports WHERE id = ? AND user_id = ?",
        [body.report_id, user_id],
    )
    if not result.rows:
        raise HTTPException(status_code=404, detail="Informe no encontrado")

    row = result.rows[0]
    pdf_bytes = row.get("pdf_bytes")
    report_title = row.get("title", "Informe fiscal")

    if not pdf_bytes:
        raise HTTPException(status_code=404, detail="El PDF del informe no esta disponible")

    # Send email
    from app.services.email_service import get_email_service
    email_service = get_email_service()

    send_result = await email_service.send_report_to_advisor(
        advisor_email=body.advisor_email,
        user_name=user_name,
        report_title=report_title,
        pdf_bytes=pdf_bytes if isinstance(pdf_bytes, bytes) else bytes(pdf_bytes),
    )

    if not send_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Error al enviar el email: {send_result.get('error', 'desconocido')}",
        )

    # Record the share
    try:
        await db.execute(
            "UPDATE reports SET shared_with_email = ?, shared_at = datetime('now') WHERE id = ?",
            [body.advisor_email, body.report_id],
        )
    except Exception as e:
        logger.warning(f"Failed to record share: {e}")

    return {
        "success": True,
        "message": f"Informe enviado a {body.advisor_email}",
        "email_id": send_result.get("id"),
    }
