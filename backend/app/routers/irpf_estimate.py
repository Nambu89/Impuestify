"""
Lightweight IRPF estimation endpoint for the Tax Guide live estimator.

Does NOT go through the LLM agent — directly calls IRPFSimulator for
fast (~50-100ms) real-time estimates as users fill in the wizard.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.jwt_handler import get_current_user, TokenData
from app.security.rate_limiter import limiter

router = APIRouter(prefix="/api/irpf", tags=["irpf"])


class IRPFEstimateRequest(BaseModel):
    comunidad_autonoma: str
    year: int = 2025
    ingresos_trabajo: float = 0
    ss_empleado: float = 0
    retenciones_trabajo: float = 0
    intereses: float = 0
    dividendos: float = 0
    ganancias_fondos: float = 0
    ingresos_alquiler: float = 0
    gastos_alquiler_total: float = 0
    valor_adquisicion_inmueble: float = 0
    edad_contribuyente: int = 35
    num_descendientes: int = 0
    anios_nacimiento_desc: List[int] = Field(default_factory=list)
    custodia_compartida: bool = False
    num_ascendientes_65: int = 0
    num_ascendientes_75: int = 0
    discapacidad_contribuyente: int = 0
    ceuta_melilla: bool = False
    # Activity income (autonomos)
    ingresos_actividad: float = 0
    gastos_actividad: float = 0
    cuota_autonomo_anual: float = 0
    amortizaciones_actividad: float = 0
    provisiones_actividad: float = 0
    otros_gastos_actividad: float = 0
    estimacion_actividad: str = "directa_simplificada"
    inicio_actividad: bool = False
    un_solo_cliente: bool = False
    retenciones_actividad: float = 0
    pagos_fraccionados_130: float = 0
    # Phase 1: Reductions & deductions
    aportaciones_plan_pensiones: float = 0
    aportaciones_plan_pensiones_empresa: float = 0
    hipoteca_pre2013: bool = False
    capital_amortizado_hipoteca: float = 0
    intereses_hipoteca: float = 0
    madre_trabajadora_ss: bool = False
    gastos_guarderia_anual: float = 0
    familia_numerosa: bool = False
    tipo_familia_numerosa: str = "general"
    donativos_ley_49_2002: float = 0
    donativo_recurrente: bool = False
    # Additional withholdings
    retenciones_alquiler: float = 0
    retenciones_ahorro: float = 0
    # Phase 2: Tributación conjunta (Art. 84 LIRPF)
    tributacion_conjunta: bool = False
    tipo_unidad_familiar: str = "matrimonio"
    # Phase 2: Alquiler vivienda habitual pre-2015 (DT 15ª LIRPF)
    alquiler_habitual_pre2015: bool = False
    alquiler_pagado_anual: float = 0
    # Phase 2: Rentas imputadas inmuebles (Art. 85 LIRPF)
    valor_catastral_segundas_viviendas: float = 0
    valor_catastral_revisado_post1994: bool = True
    # Phase 3: Payslip/salary fields
    num_pagas_anuales: int = 14
    salario_base_mensual: float = 0
    complementos_salariales: float = 0
    irpf_retenido_porcentaje: float = 0


class IRPFBreakdown(BaseModel):
    ingresos_brutos: float = 0
    gastos_deducibles: float = 0
    reduccion_trabajo: float = 0
    rendimiento_neto: float = 0


class ActivityBreakdown(BaseModel):
    ingresos_actividad: float = 0
    total_gastos_deducibles: float = 0
    gastos_dificil_justificacion: float = 0
    rendimiento_neto: float = 0
    reduccion_aplicada: float = 0
    tipo_reduccion: str = "ninguna"
    rendimiento_neto_reducido: float = 0
    estimacion: str = "directa_simplificada"


class IRPFEstimateResponse(BaseModel):
    success: bool
    resultado_estimado: float  # <0 = refund (green), >0 = payment (red)
    cuota_liquida_total: float = 0
    retenciones_pagadas: float = 0
    base_imponible_general: float = 0
    base_imponible_ahorro: float = 0
    cuota_integra_general: float = 0
    cuota_integra_ahorro: float = 0
    tipo_medio_efectivo: float = 0
    mpyf_estatal: float = 0
    mpyf_autonomico: float = 0
    deduccion_ceuta_melilla: float = 0
    reduccion_planes_pensiones: float = 0
    deduccion_vivienda_pre2013: float = 0
    deduccion_maternidad: float = 0
    deduccion_familia_numerosa: float = 0
    deduccion_donativos: float = 0
    total_deducciones_cuota: float = 0
    # Phase 2
    reduccion_tributacion_conjunta: float = 0
    deduccion_alquiler_pre2015: float = 0
    renta_imputada_inmuebles: float = 0
    trabajo: Optional[IRPFBreakdown] = None
    actividad: Optional[ActivityBreakdown] = None
    error: Optional[str] = None


@router.post("/estimate", response_model=IRPFEstimateResponse)
@limiter.limit("60/minute")
async def estimate_irpf(
    req: Request,
    request: IRPFEstimateRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Fast IRPF estimate for the interactive tax guide. No LLM involved."""
    try:
        from app.utils.irpf_simulator import IRPFSimulator
        from app.tools.web_scraper_tool import normalize_ccaa_name
        from app.database.turso_client import get_db_client

        db = await get_db_client()
        ccaa = normalize_ccaa_name(request.comunidad_autonoma)

        ceuta_melilla = request.ceuta_melilla
        if not ceuta_melilla and ccaa.lower() in ("ceuta", "melilla"):
            ceuta_melilla = True

        # Auto-calculate annual gross from monthly salary if provided
        ingresos_trabajo = request.ingresos_trabajo
        if request.salario_base_mensual > 0 and ingresos_trabajo == 0:
            mensual_total = request.salario_base_mensual + request.complementos_salariales
            ingresos_trabajo = mensual_total * request.num_pagas_anuales

        # Auto-calculate retenciones from percentage if provided
        retenciones_trabajo = request.retenciones_trabajo
        if request.irpf_retenido_porcentaje > 0 and retenciones_trabajo == 0 and ingresos_trabajo > 0:
            retenciones_trabajo = ingresos_trabajo * request.irpf_retenido_porcentaje / 100

        simulator = IRPFSimulator(db)

        # Build common simulation kwargs
        sim_kwargs = dict(
            jurisdiction=ccaa,
            ingresos_trabajo=ingresos_trabajo,
            ss_empleado=request.ss_empleado,
            intereses=request.intereses,
            dividendos=request.dividendos,
            ganancias_fondos=request.ganancias_fondos,
            ingresos_alquiler=request.ingresos_alquiler,
            gastos_alquiler_total=request.gastos_alquiler_total,
            valor_adquisicion_inmueble=request.valor_adquisicion_inmueble,
            edad_contribuyente=request.edad_contribuyente,
            num_descendientes=request.num_descendientes,
            anios_nacimiento_desc=request.anios_nacimiento_desc or None,
            custodia_compartida=request.custodia_compartida,
            num_ascendientes_65=request.num_ascendientes_65,
            num_ascendientes_75=request.num_ascendientes_75,
            discapacidad_contribuyente=request.discapacidad_contribuyente,
            ceuta_melilla=ceuta_melilla,
            # Activity income (autonomos)
            ingresos_actividad=request.ingresos_actividad,
            gastos_actividad=request.gastos_actividad,
            cuota_autonomo_anual=request.cuota_autonomo_anual,
            amortizaciones_actividad=request.amortizaciones_actividad,
            provisiones_actividad=request.provisiones_actividad,
            otros_gastos_actividad=request.otros_gastos_actividad,
            estimacion_actividad=request.estimacion_actividad,
            inicio_actividad=request.inicio_actividad,
            un_solo_cliente=request.un_solo_cliente,
            retenciones_actividad=request.retenciones_actividad,
            pagos_fraccionados_130=request.pagos_fraccionados_130,
            # Phase 1
            aportaciones_plan_pensiones=request.aportaciones_plan_pensiones,
            aportaciones_plan_pensiones_empresa=request.aportaciones_plan_pensiones_empresa,
            hipoteca_pre2013=request.hipoteca_pre2013,
            capital_amortizado_hipoteca=request.capital_amortizado_hipoteca,
            intereses_hipoteca=request.intereses_hipoteca,
            madre_trabajadora_ss=request.madre_trabajadora_ss,
            gastos_guarderia_anual=request.gastos_guarderia_anual,
            familia_numerosa=request.familia_numerosa,
            tipo_familia_numerosa=request.tipo_familia_numerosa,
            donativos_ley_49_2002=request.donativos_ley_49_2002,
            donativo_recurrente=request.donativo_recurrente,
            retenciones_alquiler=request.retenciones_alquiler,
            retenciones_ahorro=request.retenciones_ahorro,
            # Phase 2
            tributacion_conjunta=request.tributacion_conjunta,
            tipo_unidad_familiar=request.tipo_unidad_familiar,
            alquiler_habitual_pre2015=request.alquiler_habitual_pre2015,
            alquiler_pagado_anual=request.alquiler_pagado_anual,
            valor_catastral_segundas_viviendas=request.valor_catastral_segundas_viviendas,
            valor_catastral_revisado_post1994=request.valor_catastral_revisado_post1994,
        )

        # Try requested year, fallback to year-1
        try:
            result = await simulator.simulate(year=request.year, **sim_kwargs)
        except ValueError:
            result = await simulator.simulate(year=request.year - 1, **sim_kwargs)

        # Use cuota_diferencial from simulator if available (includes all retenciones)
        cuota_total = result.get("cuota_total", 0)
        resultado = result.get("cuota_diferencial", cuota_total - retenciones_trabajo)
        retenciones = result.get("total_retenciones", retenciones_trabajo)

        trabajo = result.get("trabajo", {})
        actividad = result.get("actividad", {})
        mpyf = result.get("mpyf", {})

        tipo_medio = 0
        bi_general = result.get("base_imponible_general", 0)
        if bi_general > 0:
            tipo_medio = round((cuota_total / bi_general) * 100, 2)

        return IRPFEstimateResponse(
            success=True,
            resultado_estimado=round(resultado, 2),
            cuota_liquida_total=round(cuota_total, 2),
            retenciones_pagadas=round(retenciones, 2),
            base_imponible_general=round(bi_general, 2),
            base_imponible_ahorro=round(result.get("base_imponible_ahorro", 0), 2),
            cuota_integra_general=round(result.get("cuota_integra_general", 0), 2),
            cuota_integra_ahorro=round(result.get("cuota_integra_ahorro", 0), 2),
            tipo_medio_efectivo=tipo_medio,
            mpyf_estatal=round(mpyf.get("mpyf_estatal", 0), 2),
            mpyf_autonomico=round(mpyf.get("mpyf_autonomico", 0), 2),
            deduccion_ceuta_melilla=round(result.get("deduccion_ceuta_melilla", 0), 2),
            reduccion_planes_pensiones=round(result.get("reduccion_planes_pensiones", 0), 2),
            deduccion_vivienda_pre2013=round(result.get("deduccion_vivienda_pre2013", 0), 2),
            deduccion_maternidad=round(result.get("deduccion_maternidad", 0), 2),
            deduccion_familia_numerosa=round(result.get("deduccion_familia_numerosa", 0), 2),
            deduccion_donativos=round(result.get("deduccion_donativos", 0), 2),
            total_deducciones_cuota=round(result.get("total_deducciones_cuota", 0), 2),
            reduccion_tributacion_conjunta=round(result.get("reduccion_tributacion_conjunta", 0), 2),
            deduccion_alquiler_pre2015=round(result.get("deduccion_alquiler_pre2015", 0), 2),
            renta_imputada_inmuebles=round(result.get("renta_imputada_inmuebles", 0), 2),
            trabajo=IRPFBreakdown(
                ingresos_brutos=trabajo.get("ingresos_brutos", 0),
                gastos_deducibles=trabajo.get("gastos_deducibles", 0),
                reduccion_trabajo=trabajo.get("reduccion_trabajo", 0),
                rendimiento_neto=trabajo.get("rendimiento_neto_reducido", 0),
            ) if trabajo else None,
            actividad=ActivityBreakdown(
                ingresos_actividad=actividad.get("ingresos_actividad", 0),
                total_gastos_deducibles=actividad.get("total_gastos_deducibles", 0),
                gastos_dificil_justificacion=actividad.get("gastos_dificil_justificacion", 0),
                rendimiento_neto=actividad.get("rendimiento_neto", 0),
                reduccion_aplicada=actividad.get("reduccion_aplicada", 0),
                tipo_reduccion=actividad.get("tipo_reduccion", "ninguna"),
                rendimiento_neto_reducido=actividad.get("rendimiento_neto_reducido", 0),
                estimacion=actividad.get("estimacion", "directa_simplificada"),
            ) if actividad else None,
        )

    except Exception as e:
        return IRPFEstimateResponse(
            success=False,
            resultado_estimado=0,
            error=str(e),
        )


# === Phase B: Deduction discovery (lightweight, no LLM) ===

class DeductionDiscoverRequest(BaseModel):
    ccaa: str
    tax_year: int = 2025
    answers: dict = Field(default_factory=dict)


class DeductionItem(BaseModel):
    code: str
    name: str
    category: str
    description: str = ""
    percentage: Optional[float] = None
    max_amount: Optional[float] = None
    fixed_amount: Optional[float] = None
    legal_reference: str = ""


class DeductionDiscoverResponse(BaseModel):
    success: bool = True
    eligible: List[DeductionItem] = []
    maybe_eligible: List[DeductionItem] = []
    estimated_savings: float = 0
    total_deductions: int = 0
    missing_questions: List[dict] = []


@router.post("/deductions/discover", response_model=DeductionDiscoverResponse)
@limiter.limit("30/minute")
async def discover_deductions_endpoint(
    req: Request,
    request: DeductionDiscoverRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Discover eligible deductions for a CCAA. No LLM — direct DB query."""
    try:
        from app.services.deduction_service import get_deduction_service
        from app.tools.web_scraper_tool import normalize_ccaa_name

        ccaa = normalize_ccaa_name(request.ccaa)
        service = get_deduction_service()

        result = await service.evaluate_eligibility(
            ccaa=ccaa,
            tax_year=request.tax_year,
            answers=request.answers,
        )

        questions = await service.get_missing_questions(
            ccaa=ccaa,
            tax_year=request.tax_year,
            answers=request.answers,
        )

        def to_item(d: dict) -> DeductionItem:
            return DeductionItem(
                code=d.get("code", ""),
                name=d.get("name", ""),
                category=d.get("category", ""),
                description=d.get("description", ""),
                percentage=d.get("percentage"),
                max_amount=d.get("max_amount"),
                fixed_amount=d.get("fixed_amount"),
                legal_reference=d.get("legal_reference", ""),
            )

        return DeductionDiscoverResponse(
            eligible=[to_item(d) for d in result.get("eligible", [])],
            maybe_eligible=[to_item(d) for d in result.get("maybe_eligible", [])],
            estimated_savings=result.get("estimated_savings", 0),
            total_deductions=result.get("total_deductions", 0),
            missing_questions=questions[:8],
        )

    except Exception as e:
        return DeductionDiscoverResponse(success=False)
