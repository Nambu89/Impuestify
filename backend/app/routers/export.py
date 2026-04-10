"""
Export Router for TaxIA.

Provides endpoints for generating IRPF reports, modelo PDFs,
and sharing them with advisors.
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
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


# === Request/Response Models ===

class IRPFReportRequest(BaseModel):
    """Request for IRPF report generation."""
    ccaa: str = Field(..., description="Comunidad autonoma")
    ingresos_trabajo: float = Field(0, description="Ingresos brutos anuales del trabajo")
    year: int = Field(2025, description="Ano fiscal")
    answers: Optional[Dict[str, Any]] = Field(default=None, description="Respuestas para deducciones")
    # Extended fields for complete simulation
    retenciones_trabajo: float = Field(0, description="Retenciones IRPF en nómina")
    ss_empleado: float = Field(0, description="Cotización SS empleado anual")
    aportaciones_plan_pensiones: float = Field(0, description="Aportaciones plan pensiones")
    tributacion_conjunta: bool = Field(False, description="Tributación conjunta")
    tipo_unidad_familiar: str = Field("matrimonio", description="Tipo unidad familiar")
    hipoteca_pre2013: bool = Field(False, description="Hipoteca anterior a 2013")
    capital_amortizado_hipoteca: float = Field(0, description="Capital amortizado hipoteca")
    intereses_hipoteca: float = Field(0, description="Intereses hipoteca")
    donativos: float = Field(0, description="Donativos Ley 49/2002")
    donativo_recurrente: bool = Field(False, description="Donativo recurrente 2+ años")
    familia_numerosa: bool = Field(False, description="Familia numerosa")
    tipo_familia_numerosa: str = Field("general", description="Tipo familia numerosa")
    madre_trabajadora_ss: bool = Field(False, description="Madre trabajadora con hijos <3")
    gastos_guarderia_anual: float = Field(0, description="Gastos guardería anual")
    edad_contribuyente: int = Field(35, description="Edad del contribuyente")
    num_descendientes: int = Field(0, description="Número de descendientes")
    num_ascendientes_65: int = Field(0, description="Ascendientes >65")
    num_ascendientes_75: int = Field(0, description="Ascendientes >75")
    discapacidad_contribuyente: int = Field(0, description="Porcentaje discapacidad")
    ceuta_melilla: bool = Field(False, description="Residente Ceuta/Melilla")
    # Activity income
    ingresos_actividad: float = Field(0, description="Ingresos actividad económica")
    gastos_actividad: float = Field(0, description="Gastos actividad económica")
    cuota_autonomo_anual: float = Field(0, description="Cuota autónomo anual")
    retenciones_actividad: float = Field(0, description="Retenciones actividad")
    pagos_fraccionados_130: float = Field(0, description="Pagos fraccionados M130")
    # Savings
    intereses: float = Field(0, description="Intereses cuentas/depósitos")
    dividendos: float = Field(0, description="Dividendos")
    ganancias_fondos: float = Field(0, description="Ganancias fondos")
    # Chat content for personalized analysis
    chat_content: Optional[str] = Field(default=None, description="Contenido markdown del análisis del asistente")


class ModeloPDFRequest(BaseModel):
    """Request for Modelo Tributario PDF generation."""
    modelo: str = Field(..., description="Tipo de modelo: 303, 130, 308, 720, 721, ipsi")
    data: dict = Field(..., description="Datos calculados del modelo (casillas, resultados)")
    trimestre: str = Field("1T", description="Periodo: 1T, 2T, 3T, 4T, anual")
    ejercicio: int = Field(2026, description="Año fiscal")
    contribuyente: Optional[dict] = Field(
        default=None,
        description="Datos del contribuyente: {nombre, nif, variante_foral}",
    )


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
@limiter.limit("5/minute")
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
    has_income = body.ingresos_trabajo > 0 or body.ingresos_actividad > 0
    if has_income:
        try:
            from app.tools.irpf_simulator_tool import simulate_irpf_tool
            sim_result = await simulate_irpf_tool(
                comunidad_autonoma=body.ccaa,
                ingresos_trabajo=body.ingresos_trabajo,
                year=body.year,
                ss_empleado=body.ss_empleado,
                retenciones_trabajo=body.retenciones_trabajo,
                aportaciones_plan_pensiones=body.aportaciones_plan_pensiones,
                tributacion_conjunta=body.tributacion_conjunta,
                tipo_unidad_familiar=body.tipo_unidad_familiar,
                hipoteca_pre2013=body.hipoteca_pre2013,
                capital_amortizado_hipoteca=body.capital_amortizado_hipoteca,
                intereses_hipoteca=body.intereses_hipoteca,
                donativos_ley_49_2002=body.donativos,
                donativo_recurrente=body.donativo_recurrente,
                familia_numerosa=body.familia_numerosa,
                tipo_familia_numerosa=body.tipo_familia_numerosa,
                madre_trabajadora_ss=body.madre_trabajadora_ss,
                gastos_guarderia_anual=body.gastos_guarderia_anual,
                edad_contribuyente=body.edad_contribuyente,
                num_descendientes=body.num_descendientes,
                num_ascendientes_65=body.num_ascendientes_65,
                num_ascendientes_75=body.num_ascendientes_75,
                discapacidad_contribuyente=body.discapacidad_contribuyente,
                ceuta_melilla=body.ceuta_melilla,
                ingresos_actividad=body.ingresos_actividad,
                gastos_actividad=body.gastos_actividad,
                cuota_autonomo_anual=body.cuota_autonomo_anual,
                retenciones_actividad=body.retenciones_actividad,
                pagos_fraccionados_130=body.pagos_fraccionados_130,
                intereses=body.intereses,
                dividendos=body.dividendos,
                ganancias_fondos=body.ganancias_fondos,
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
        chat_content=body.chat_content,
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
@limiter.limit("5/minute")
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


@router.post("/modelo-pdf", response_class=Response)
@limiter.limit("5/minute")
async def export_modelo_pdf(
    request: Request,
    body: ModeloPDFRequest,
    current_user=Depends(get_current_user),
):
    """
    Generate a PDF for a Spanish tax form model (Modelo Tributario).

    Supported modelos: 303, 130, 308, 720, 721, ipsi.
    Returns PDF as download.
    """
    from app.services.modelo_pdf_generator import ModeloPDFGenerator, VALID_MODELOS

    if body.modelo not in VALID_MODELOS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Modelo '{body.modelo}' no soportado. "
                f"Valores válidos: {', '.join(sorted(VALID_MODELOS))}"
            ),
        )

    user_info = body.contribuyente or {}
    # Fallback: use email from token if no name provided
    if not user_info.get("nombre"):
        user_info["nombre"] = current_user.email or ""

    try:
        generator = ModeloPDFGenerator()
        pdf_bytes = generator.generate(
            modelo_type=body.modelo,
            data=body.data,
            user_info=user_info,
            trimestre=body.trimestre,
            ejercicio=body.ejercicio,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error generating modelo PDF: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el PDF del modelo tributario.",
        )

    filename = f"Modelo_{body.modelo.upper()}_{body.trimestre}_{body.ejercicio}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
