"""
Lightweight IRPF estimation endpoint for the Tax Guide live estimator.

Does NOT go through the LLM agent — directly calls IRPFSimulator for
fast (~50-100ms) real-time estimates as users fill in the wizard.
"""
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth.jwt_handler import get_current_user, TokenData
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

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
    # Fase 4: Ganancias patrimoniales del ahorro (acciones, fondos, derivados, cripto)
    ganancias_acciones: float = 0
    perdidas_acciones: float = 0
    ganancias_reembolso_fondos: float = 0
    perdidas_reembolso_fondos: float = 0
    ganancias_derivados: float = 0
    perdidas_derivados: float = 0
    cripto_ganancia_neta: float = 0
    cripto_perdida_neta: float = 0
    # Fase 4: Juegos y apuestas privados (base general, casillas 0281-0290)
    premios_metalico_privados: float = 0
    premios_especie_privados: float = 0
    perdidas_juegos_privados: float = 0
    # Fase 4: Loterías públicas (gravamen especial 20%, exentos primeros 40.000 EUR)
    premios_metalico_publicos: float = 0
    premios_especie_publicos: float = 0
    # Fase 5: Datos para deducciones autonómicas (from DynamicFiscalForm)
    deducciones_answers: dict = Field(default_factory=dict)
    # User data for computing CCAA deduction amounts
    donativos_autonomicos: float = 0
    gastos_educativos: float = 0
    inversion_vivienda: float = 0
    instalacion_renovable_importe: float = 0
    vehiculo_electrico_importe: float = 0
    obras_mejora_importe: float = 0
    cotizaciones_empleada_hogar: float = 0
    # Creator-specific fields
    plataformas_ingresos: Optional[dict] = None  # {"youtube": 5000, "twitch": 2000, ...}
    epigrafe_iae: Optional[str] = None  # "8690", "9020", "6010.1"
    tiene_ingresos_intracomunitarios: Optional[bool] = False
    ingresos_intracomunitarios: Optional[float] = 0
    withholding_tax_pagado: Optional[float] = 0
    gastos_equipo: Optional[float] = 0
    gastos_software: Optional[float] = 0
    gastos_coworking: Optional[float] = 0
    gastos_transporte: Optional[float] = 0
    gastos_formacion: Optional[float] = 0


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
    # Fase 4
    ganancias_juegos_netas: float = 0
    gravamen_especial_loterias: float = 0
    # Fase 5: Deducciones autonómicas
    deducciones_autonomicas: List[dict] = Field(default_factory=list)
    total_deducciones_autonomicas: float = 0
    trabajo: Optional[IRPFBreakdown] = None
    actividad: Optional[ActivityBreakdown] = None
    # Creator-specific response fields
    plataformas_desglose: Optional[dict] = None
    modelo_349_requerido: Optional[bool] = None
    iae_seleccionado: Optional[str] = None
    error: Optional[str] = None


@router.post("/estimate", response_model=IRPFEstimateResponse)
@limiter.limit("60/minute")
async def estimate_irpf(
    request: Request,
    body: IRPFEstimateRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Fast IRPF estimate for the interactive tax guide. No LLM involved."""
    try:
        from app.utils.irpf_simulator import IRPFSimulator
        from app.utils.ccaa_constants import normalize_ccaa
        from app.database.turso_client import get_db_client

        db = await get_db_client()
        ccaa = normalize_ccaa(body.comunidad_autonoma)

        ceuta_melilla = body.ceuta_melilla
        if not ceuta_melilla and ccaa.lower() in ("ceuta", "melilla"):
            ceuta_melilla = True

        # Auto-calculate annual gross from monthly salary if provided
        ingresos_trabajo = body.ingresos_trabajo
        if body.salario_base_mensual > 0 and ingresos_trabajo == 0:
            mensual_total = body.salario_base_mensual + body.complementos_salariales
            ingresos_trabajo = mensual_total * body.num_pagas_anuales

        # Auto-calculate retenciones from percentage if provided
        retenciones_trabajo = body.retenciones_trabajo
        if body.irpf_retenido_porcentaje > 0 and retenciones_trabajo == 0 and ingresos_trabajo > 0:
            retenciones_trabajo = ingresos_trabajo * body.irpf_retenido_porcentaje / 100

        # Creator: override ingresos_actividad from platform breakdown if provided
        ingresos_actividad = body.ingresos_actividad
        if body.plataformas_ingresos:
            platform_total = sum(
                v for v in body.plataformas_ingresos.values()
                if isinstance(v, (int, float)) and v > 0
            )
            if platform_total > 0:
                ingresos_actividad = platform_total

        # Creator: override gastos_actividad from granular expense fields if provided
        gastos_actividad = body.gastos_actividad
        gastos_creator = (
            (body.gastos_equipo or 0)
            + (body.gastos_software or 0)
            + (body.gastos_coworking or 0)
            + (body.gastos_transporte or 0)
            + (body.gastos_formacion or 0)
        )
        if gastos_creator > 0:
            gastos_actividad = gastos_creator

        # Creator: add foreign withholding tax to activity retenciones
        retenciones_actividad = body.retenciones_actividad
        if body.withholding_tax_pagado and body.withholding_tax_pagado > 0:
            retenciones_actividad += body.withholding_tax_pagado

        simulator = IRPFSimulator(db)

        # --- Compute CCAA deductions before simulation ---
        from app.services.deduction_service import get_deduction_service, DeductionService

        deduction_service = get_deduction_service()
        ccaa_deductions_list = []
        total_ccaa_deductions = 0.0

        try:
            # Build answers: merge profile-derived booleans + explicit answers from frontend
            profile_for_answers = {
                "num_descendientes": body.num_descendientes,
                "num_ascendientes_65": body.num_ascendientes_65,
                "num_ascendientes_75": body.num_ascendientes_75,
                "discapacidad_contribuyente": body.discapacidad_contribuyente,
                "familia_numerosa": body.familia_numerosa,
                "madre_trabajadora_ss": body.madre_trabajadora_ss,
                "ceuta_melilla": ceuta_melilla,
                "hipoteca_pre2013": body.hipoteca_pre2013,
                "aportaciones_plan_pensiones": body.aportaciones_plan_pensiones,
                "donativos_ley_49_2002": body.donativos_ley_49_2002,
                "alquiler_vivienda_habitual": body.alquiler_pagado_anual > 0,
                "edad_contribuyente": body.edad_contribuyente,
            }
            answers = DeductionService.build_answers_from_profile(profile_for_answers, ccaa)
            # Merge explicit answers from frontend DynamicFiscalForm
            answers.update(body.deducciones_answers)

            # Evaluate eligibility
            eval_result = await deduction_service.evaluate_eligibility(
                ccaa=ccaa,
                tax_year=body.year,
                answers=answers,
            )

            # Compute exact amounts for eligible CCAA deductions
            user_data = {
                "alquiler_pagado_anual": body.alquiler_pagado_anual,
                "edad_contribuyente": body.edad_contribuyente,
                "num_descendientes": body.num_descendientes,
                "anios_nacimiento_desc": body.anios_nacimiento_desc,
                "donativos_autonomicos": body.donativos_autonomicos,
                "gastos_guarderia_anual": body.gastos_guarderia_anual,
                "gastos_educativos": body.gastos_educativos,
                "base_imponible": ingresos_trabajo + ingresos_actividad,
                "inversion_vivienda": body.inversion_vivienda,
                "instalacion_renovable_importe": body.instalacion_renovable_importe,
                "vehiculo_electrico_importe": body.vehiculo_electrico_importe,
                "obras_mejora_importe": body.obras_mejora_importe,
                "cotizaciones_empleada_hogar": body.cotizaciones_empleada_hogar,
                "year": body.year,
            }
            ccaa_deductions_list = deduction_service.compute_ccaa_deduction_amounts(
                eligible=eval_result.get("eligible", []),
                user_data=user_data,
            )
            total_ccaa_deductions = sum(d["amount"] for d in ccaa_deductions_list)
        except Exception as e:
            logger.warning("CCAA deduction computation failed (non-fatal): %s", e)
            # Non-fatal: continue simulation without CCAA deductions

        # Build common simulation kwargs
        sim_kwargs = dict(
            jurisdiction=ccaa,
            ingresos_trabajo=ingresos_trabajo,
            ss_empleado=body.ss_empleado,
            intereses=body.intereses,
            dividendos=body.dividendos,
            ganancias_fondos=body.ganancias_fondos,
            ingresos_alquiler=body.ingresos_alquiler,
            gastos_alquiler_total=body.gastos_alquiler_total,
            valor_adquisicion_inmueble=body.valor_adquisicion_inmueble,
            edad_contribuyente=body.edad_contribuyente,
            num_descendientes=body.num_descendientes,
            anios_nacimiento_desc=body.anios_nacimiento_desc or None,
            custodia_compartida=body.custodia_compartida,
            num_ascendientes_65=body.num_ascendientes_65,
            num_ascendientes_75=body.num_ascendientes_75,
            discapacidad_contribuyente=body.discapacidad_contribuyente,
            ceuta_melilla=ceuta_melilla,
            # Activity income (autonomos / creators)
            ingresos_actividad=ingresos_actividad,
            gastos_actividad=gastos_actividad,
            cuota_autonomo_anual=body.cuota_autonomo_anual,
            amortizaciones_actividad=body.amortizaciones_actividad,
            provisiones_actividad=body.provisiones_actividad,
            otros_gastos_actividad=body.otros_gastos_actividad,
            estimacion_actividad=body.estimacion_actividad,
            inicio_actividad=body.inicio_actividad,
            un_solo_cliente=body.un_solo_cliente,
            retenciones_actividad=retenciones_actividad,
            pagos_fraccionados_130=body.pagos_fraccionados_130,
            # Phase 1
            aportaciones_plan_pensiones=body.aportaciones_plan_pensiones,
            aportaciones_plan_pensiones_empresa=body.aportaciones_plan_pensiones_empresa,
            hipoteca_pre2013=body.hipoteca_pre2013,
            capital_amortizado_hipoteca=body.capital_amortizado_hipoteca,
            intereses_hipoteca=body.intereses_hipoteca,
            madre_trabajadora_ss=body.madre_trabajadora_ss,
            gastos_guarderia_anual=body.gastos_guarderia_anual,
            familia_numerosa=body.familia_numerosa,
            tipo_familia_numerosa=body.tipo_familia_numerosa,
            donativos_ley_49_2002=body.donativos_ley_49_2002,
            donativo_recurrente=body.donativo_recurrente,
            retenciones_alquiler=body.retenciones_alquiler,
            retenciones_ahorro=body.retenciones_ahorro,
            # Phase 2
            tributacion_conjunta=body.tributacion_conjunta,
            tipo_unidad_familiar=body.tipo_unidad_familiar,
            alquiler_habitual_pre2015=body.alquiler_habitual_pre2015,
            alquiler_pagado_anual=body.alquiler_pagado_anual,
            valor_catastral_segundas_viviendas=body.valor_catastral_segundas_viviendas,
            valor_catastral_revisado_post1994=body.valor_catastral_revisado_post1994,
            # Fase 4: ganancias patrimoniales del ahorro
            ganancias_acciones=body.ganancias_acciones,
            perdidas_acciones=body.perdidas_acciones,
            ganancias_reembolso_fondos=body.ganancias_reembolso_fondos,
            perdidas_reembolso_fondos=body.perdidas_reembolso_fondos,
            ganancias_derivados=body.ganancias_derivados,
            perdidas_derivados=body.perdidas_derivados,
            cripto_ganancia_neta=body.cripto_ganancia_neta,
            cripto_perdida_neta=body.cripto_perdida_neta,
            # Fase 4: juegos privados y loterías
            premios_metalico_privados=body.premios_metalico_privados,
            premios_especie_privados=body.premios_especie_privados,
            perdidas_juegos_privados=body.perdidas_juegos_privados,
            premios_metalico_publicos=body.premios_metalico_publicos,
            premios_especie_publicos=body.premios_especie_publicos,
            # Retenciones del trabajo (calculadas arriba desde % o valor directo)
            retenciones_trabajo=retenciones_trabajo,
            # Fase 5: deducciones autonómicas pre-computed
            deducciones_autonomicas_total=total_ccaa_deductions,
        )

        # Try requested year, fallback to year-1
        try:
            result = await simulator.simulate(year=body.year, **sim_kwargs)
        except ValueError:
            result = await simulator.simulate(year=body.year - 1, **sim_kwargs)

        # cuota_diferencial now includes ALL retenciones (trabajo + alquiler + ahorro + actividad + 130)
        cuota_total = result.get("cuota_total", 0)
        resultado = result.get("cuota_diferencial", 0)
        retenciones = result.get("total_retenciones", 0)

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
            ganancias_juegos_netas=round(result.get("ganancias_juegos_netas", 0), 2),
            gravamen_especial_loterias=round(result.get("gravamen_especial_loterias", 0), 2),
            deducciones_autonomicas=ccaa_deductions_list,
            total_deducciones_autonomicas=round(result.get("deducciones_autonomicas_total", 0), 2),
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
            # Creator-specific response fields
            plataformas_desglose=body.plataformas_ingresos if body.plataformas_ingresos else None,
            modelo_349_requerido=(
                True
                if body.tiene_ingresos_intracomunitarios and (body.ingresos_intracomunitarios or 0) > 0
                else False
            ),
            iae_seleccionado=body.epigrafe_iae if body.epigrafe_iae else None,
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
    request: Request,
    body: DeductionDiscoverRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Discover eligible deductions for a CCAA. No LLM — direct DB query."""
    try:
        from app.services.deduction_service import get_deduction_service
        from app.utils.ccaa_constants import normalize_ccaa

        ccaa = normalize_ccaa(body.ccaa)
        service = get_deduction_service()

        result = await service.evaluate_eligibility(
            ccaa=ccaa,
            tax_year=body.tax_year,
            answers=body.answers,
        )

        questions = await service.get_missing_questions(
            ccaa=ccaa,
            tax_year=body.tax_year,
            answers=body.answers,
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
