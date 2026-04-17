"""
Impuesto sobre Sociedades (IS) estimation endpoints.

Lightweight endpoints for Modelo 200 (IS annual) and Modelo 202 (pagos fraccionados).
Does NOT go through the LLM agent — directly calls ISSimulator for fast estimates.
"""
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/irpf", tags=["is"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ISEstimateRequest(BaseModel):
    """Datos de entrada para la liquidacion IS (Modelo 200)."""
    resultado_contable: float = 0.0
    territorio: str = "Madrid"
    tipo_entidad: str = "sl"  # sl, slp, sa, nueva_creacion
    facturacion_anual: float = 0.0
    ejercicios_con_bi_positiva: int = 10

    # Ajustes
    gastos_no_deducibles: float = 0.0
    ajustes_negativos: float = 0.0
    amortizacion_contable: float = 0.0
    amortizacion_fiscal: Optional[float] = None

    # BINs
    bins_pendientes: float = 0.0

    # Deducciones
    gasto_id: float = 0.0
    gasto_it: float = 0.0
    incremento_ffpp: float = 0.0
    donativos: float = 0.0
    empleados_discapacidad_33: int = 0
    empleados_discapacidad_65: int = 0
    dotacion_ric: float = 0.0

    # Bonificaciones
    es_zec: bool = False
    rentas_ceuta_melilla: float = 0.0

    # Retenciones y pagos previos
    retenciones_ingresos_cuenta: float = 0.0
    pagos_fraccionados_realizados: float = 0.0

    # Alternativa: ingresos - gastos
    ingresos_explotacion: Optional[float] = None
    gastos_explotacion: Optional[float] = None


class ISEstimateResponse(BaseModel):
    """Resultado completo de la liquidacion IS."""
    resultado_contable: float = 0.0
    ajustes_positivos: float = 0.0
    ajustes_negativos: float = 0.0
    reserva_capitalizacion: float = 0.0
    base_imponible_previa: float = 0.0
    compensacion_bins: float = 0.0
    base_imponible: float = 0.0
    bin_generada: float = 0.0

    tipo_gravamen_aplicado: str = ""
    cuota_integra: float = 0.0

    deducciones_detalle: Dict[str, float] = Field(default_factory=dict)
    deducciones_total: float = 0.0
    bonificaciones_total: float = 0.0
    cuota_liquida: float = 0.0

    retenciones: float = 0.0
    pagos_fraccionados: float = 0.0
    resultado_liquidacion: float = 0.0
    tipo: str = "a_ingresar"
    tipo_efectivo: float = 0.0

    regimen: str = ""
    territorio: str = ""

    # Modelo 202 precalculado en ambas modalidades
    pago_202_art40_2: float = 0.0
    pago_202_art40_3: float = 0.0

    disclaimer: str = "Este cálculo es orientativo y no sustituye asesoramiento profesional."


class IS202Request(BaseModel):
    """Datos de entrada para el pago fraccionado (Modelo 202)."""
    modalidad: str = "art40_2"  # art40_2 | art40_3
    cuota_integra_ultimo: float = 0.0
    deducciones_bonificaciones_ultimo: float = 0.0
    retenciones_ultimo: float = 0.0
    base_imponible_periodo: float = 0.0
    facturacion_anual: float = 0.0
    territorio: str = "Madrid"


class IS202Response(BaseModel):
    """Resultado del pago fraccionado (Modelo 202)."""
    pago_trimestral: float = 0.0
    modalidad: str = ""
    base_calculo: float = 0.0
    porcentaje_aplicado: float = 0.0
    calendario: List[str] = Field(default_factory=lambda: [
        "Abril: del 1 al 20",
        "Octubre: del 1 al 20",
        "Diciembre: del 1 al 20",
    ])
    disclaimer: str = "Este cálculo es orientativo y no sustituye asesoramiento profesional."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/is-estimate", response_model=ISEstimateResponse)
async def is_estimate(request: Request, body: ISEstimateRequest):
    """Calcula la liquidación del Impuesto sobre Sociedades (Modelo 200).

    Endpoint público (no requiere autenticación).
    """
    try:
        from app.utils.is_simulator import ISSimulator, ISInput

        inp = ISInput(
            resultado_contable=body.resultado_contable,
            territorio=body.territorio,
            tipo_entidad=body.tipo_entidad,
            facturacion_anual=body.facturacion_anual,
            ejercicios_con_bi_positiva=body.ejercicios_con_bi_positiva,
            gastos_no_deducibles=body.gastos_no_deducibles,
            ajustes_negativos=body.ajustes_negativos,
            amortizacion_contable=body.amortizacion_contable,
            amortizacion_fiscal=body.amortizacion_fiscal,
            bins_pendientes=body.bins_pendientes,
            gasto_id=body.gasto_id,
            gasto_it=body.gasto_it,
            incremento_ffpp=body.incremento_ffpp,
            donativos=body.donativos,
            empleados_discapacidad_33=body.empleados_discapacidad_33,
            empleados_discapacidad_65=body.empleados_discapacidad_65,
            dotacion_ric=body.dotacion_ric,
            es_zec=body.es_zec,
            rentas_ceuta_melilla=body.rentas_ceuta_melilla,
            retenciones_ingresos_cuenta=body.retenciones_ingresos_cuenta,
            pagos_fraccionados_realizados=body.pagos_fraccionados_realizados,
            ingresos_explotacion=body.ingresos_explotacion,
            gastos_explotacion=body.gastos_explotacion,
        )

        result = ISSimulator.calculate(inp)

        # Also calculate 202 in both modalities
        r202_art40_2 = ISSimulator.calcular_202(
            modalidad="art40_2",
            cuota_integra_ultimo=result.cuota_integra,
            deducciones_bonificaciones_ultimo=result.deducciones_total + result.bonificaciones_total,
            retenciones_ultimo=result.retenciones,
        )
        r202_art40_3 = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=result.base_imponible,
            facturacion_anual=body.facturacion_anual,
            territorio=body.territorio,
        )

        return ISEstimateResponse(
            resultado_contable=result.resultado_contable,
            ajustes_positivos=result.ajustes_positivos,
            ajustes_negativos=result.ajustes_negativos,
            reserva_capitalizacion=result.reserva_capitalizacion,
            base_imponible_previa=result.base_imponible_previa,
            compensacion_bins=result.compensacion_bins,
            base_imponible=result.base_imponible,
            bin_generada=result.bin_generada,
            tipo_gravamen_aplicado=result.tipo_gravamen_aplicado,
            cuota_integra=result.cuota_integra,
            deducciones_detalle=result.deducciones_detalle,
            deducciones_total=result.deducciones_total,
            bonificaciones_total=result.bonificaciones_total,
            cuota_liquida=result.cuota_liquida,
            retenciones=result.retenciones,
            pagos_fraccionados=result.pagos_fraccionados,
            resultado_liquidacion=result.resultado_liquidacion,
            tipo=result.tipo,
            tipo_efectivo=result.tipo_efectivo,
            regimen=result.regimen,
            territorio=result.territorio,
            pago_202_art40_2=r202_art40_2.pago_trimestral,
            pago_202_art40_3=r202_art40_3.pago_trimestral,
        )

    except Exception as e:
        logger.error("Error en IS estimate: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/is-202", response_model=IS202Response)
async def is_202(request: Request, body: IS202Request):
    """Calcula el pago fraccionado trimestral (Modelo 202).

    Endpoint público (no requiere autenticación).
    """
    try:
        from app.utils.is_simulator import ISSimulator

        result = ISSimulator.calcular_202(
            modalidad=body.modalidad,
            cuota_integra_ultimo=body.cuota_integra_ultimo,
            deducciones_bonificaciones_ultimo=body.deducciones_bonificaciones_ultimo,
            retenciones_ultimo=body.retenciones_ultimo,
            base_imponible_periodo=body.base_imponible_periodo,
            facturacion_anual=body.facturacion_anual,
            territorio=body.territorio,
        )

        return IS202Response(
            pago_trimestral=result.pago_trimestral,
            modalidad=result.modalidad,
            base_calculo=result.base_calculo,
            porcentaje_aplicado=result.porcentaje_aplicado,
        )

    except Exception as e:
        logger.error("Error en IS 202: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
