"""
Plusvalia Municipal (IIVTNU) REST endpoint.

Public lead-magnet calculator — no auth required.
Rate limited to prevent abuse.

POST /api/calculadoras/plusvalia-municipal
"""
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request

from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/calculadoras", tags=["calculadoras"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class PlusvaliaMunicipalRequest(BaseModel):
    """Datos de entrada para el calculo de plusvalia municipal."""
    precio_venta: float = Field(
        ..., ge=0, description="Precio de transmision del inmueble en euros."
    )
    precio_adquisicion: float = Field(
        ..., ge=0, description="Precio de adquisicion del inmueble en euros."
    )
    valor_catastral_total: float = Field(
        ..., ge=0,
        description="Valor catastral total del inmueble (suelo + construccion)."
    )
    valor_catastral_suelo: float = Field(
        ..., ge=0,
        description="Valor catastral del suelo (aparece en el recibo del IBI)."
    )
    anos_tenencia: int = Field(
        ..., ge=0,
        description="Anos completos de tenencia del inmueble."
    )
    tipo_impositivo_municipal: float = Field(
        default=30.0, ge=0, le=30,
        description="Tipo impositivo del municipio (maximo legal: 30%)."
    )
    es_vivienda_habitual_dacion: bool = Field(
        default=False,
        description="True si es dacion en pago de vivienda habitual."
    )
    es_divorcio: bool = Field(
        default=False,
        description="True si es transmision entre conyuges por divorcio."
    )


class MetodoObjetivoResponse(BaseModel):
    """Desglose del metodo objetivo."""
    metodo: str = "objetivo"
    valor_catastral_suelo: float
    coeficiente: float
    anos_tenencia: int
    base_imponible: float
    tipo_impositivo: float
    cuota: float


class MetodoRealResponse(BaseModel):
    """Desglose del metodo real."""
    metodo: str = "real"
    precio_venta: Optional[float] = None
    precio_adquisicion: Optional[float] = None
    plusvalia_total: Optional[float] = None
    porcentaje_suelo: Optional[float] = None
    base_imponible: float
    tipo_impositivo: float
    cuota: float
    hay_plusvalia: Optional[bool] = None


class PlusvaliaMunicipalResponse(BaseModel):
    """Respuesta completa del calculo de plusvalia municipal."""
    success: bool
    error: Optional[str] = None
    exento: bool = False
    motivo_exencion: Optional[str] = None
    cuota_final: float = 0.0
    metodo_objetivo: Optional[MetodoObjetivoResponse] = None
    metodo_real: Optional[MetodoRealResponse] = None
    metodo_elegido: Optional[str] = None
    disclaimer: str = (
        "Este calculo es orientativo. Los coeficientes y tipos impositivos "
        "pueden variar segun la ordenanza fiscal de cada municipio. "
        "Consulte con su ayuntamiento para el calculo definitivo."
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/plusvalia-municipal",
    response_model=PlusvaliaMunicipalResponse,
    summary="Calcular plusvalia municipal (IIVTNU)",
    description=(
        "Calcula el Impuesto sobre el Incremento de Valor de los Terrenos "
        "de Naturaleza Urbana por ambos metodos (objetivo y real) y devuelve "
        "el mas favorable para el contribuyente. "
        "Endpoint publico (lead magnet), sin autenticacion."
    ),
)
@limiter.limit("60/minute")
async def calculate_plusvalia_municipal(
    request: Request,
    body: PlusvaliaMunicipalRequest,
):
    """Calcula la plusvalia municipal por ambos metodos."""
    try:
        from app.utils.calculators.plusvalia_municipal import (
            PlusvaliaMunicipalCalculator,
        )

        calculator = PlusvaliaMunicipalCalculator()
        result = await calculator.calculate(
            precio_venta=body.precio_venta,
            precio_adquisicion=body.precio_adquisicion,
            valor_catastral_total=body.valor_catastral_total,
            valor_catastral_suelo=body.valor_catastral_suelo,
            anos_tenencia=body.anos_tenencia,
            tipo_impositivo_municipal=body.tipo_impositivo_municipal,
            es_vivienda_habitual_dacion=body.es_vivienda_habitual_dacion,
            es_divorcio=body.es_divorcio,
        )

        if not result.get("success", False):
            return PlusvaliaMunicipalResponse(
                success=False,
                error=result.get("error", "Error desconocido"),
            )

        return PlusvaliaMunicipalResponse(
            success=True,
            exento=result.get("exento", False),
            motivo_exencion=result.get("motivo_exencion"),
            cuota_final=result.get("cuota_final", 0.0),
            metodo_objetivo=result.get("metodo_objetivo"),
            metodo_real=result.get("metodo_real"),
            metodo_elegido=result.get("metodo_elegido"),
        )

    except Exception as e:
        logger.error("Error in plusvalia municipal endpoint: %s", str(e))
        return PlusvaliaMunicipalResponse(
            success=False,
            error="Error interno del servidor. Intente de nuevo.",
        )
