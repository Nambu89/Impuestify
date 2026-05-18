"""
Endpoint publico para el Modelo 309 (Declaracion-Liquidacion No Periodica del IVA).

POST /api/modelo-309/calculate
  - Sin auth (lead magnet SEO, igual que modelo-131).
  - Body: bases imponibles intracomunitarias e ISP, aplica_re, trimestre, year.
  - Devuelve: cuotas IVA + RE + resultado + plazo (~50ms, sin LLM).

Wrapper directo de `calculate_modelo_309_tool` — coherente con el tool LLM.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.security.rate_limiter import limiter
from app.tools.modelo_309_tool import calculate_modelo_309_tool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modelo-309", tags=["modelo-309"])


class Modelo309Request(BaseModel):
    """Parametros del calculo del Modelo 309."""

    periodo: str = Field(..., description="Trimestre: '1T', '2T', '3T' o '4T'")
    year: int | None = Field(None, description="Ejercicio fiscal")

    # Adquisiciones intracomunitarias
    base_intracomunitarias_21: float = Field(
        default=0.0, ge=0, description="Base adq. intracom. tipo general 21%"
    )
    base_intracomunitarias_10: float = Field(
        default=0.0, ge=0, description="Base adq. intracom. tipo reducido 10%"
    )
    base_intracomunitarias_4: float = Field(
        default=0.0, ge=0, description="Base adq. intracom. tipo superreducido 4%"
    )
    base_intracomunitarias_tabaco: float = Field(
        default=0.0, ge=0, description="Base adq. intracom. labores del tabaco (21% + RE 1,75%)"
    )

    # Inversion del sujeto pasivo
    base_isp_21: float = Field(default=0.0, ge=0, description="Base ISP tipo general 21%")
    base_isp_10: float = Field(default=0.0, ge=0, description="Base ISP tipo reducido 10%")
    base_isp_4: float = Field(default=0.0, ge=0, description="Base ISP tipo superreducido 4%")

    aplica_re: bool = Field(default=True, description="Sujeto en Recargo de Equivalencia")


class Modelo309Response(BaseModel):
    """Respuesta del calculo."""

    success: bool
    periodo: str
    year: int
    aplica_re: bool
    desglose: dict
    total_iva: float
    total_re: float
    resultado: float
    plazo: str
    formatted_response: str


@router.post("/calculate", response_model=Modelo309Response)
@limiter.limit("60/minute")
async def calculate_modelo_309_endpoint(
    request: Request,
    body: Modelo309Request,
) -> Modelo309Response:
    """
    Calcula el Modelo 309 (autoliquidacion no periodica IVA/RE).

    Endpoint publico (lead magnet SEO).
    Rate limit: 60/min por IP.
    """
    try:
        result = await calculate_modelo_309_tool(
            periodo=body.periodo,
            year=body.year,
            base_intracomunitarias_21=body.base_intracomunitarias_21,
            base_intracomunitarias_10=body.base_intracomunitarias_10,
            base_intracomunitarias_4=body.base_intracomunitarias_4,
            base_intracomunitarias_tabaco=body.base_intracomunitarias_tabaco,
            base_isp_21=body.base_isp_21,
            base_isp_10=body.base_isp_10,
            base_isp_4=body.base_isp_4,
            aplica_re=body.aplica_re,
            restricted_mode=False,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error") or result.get("formatted_response"),
            )

        import datetime as _dt

        year_used = body.year or _dt.datetime.now().year

        logger.info(
            "Modelo 309 endpoint: periodo=%s, year=%s, resultado=%s",
            body.periodo,
            year_used,
            result.get("resultado", 0),
        )

        return Modelo309Response(
            success=True,
            periodo=body.periodo,
            year=year_used,
            aplica_re=body.aplica_re,
            desglose=result.get("desglose", {}),
            total_iva=result.get("total_iva", 0.0),
            total_re=result.get("total_re", 0.0),
            resultado=result.get("resultado", 0.0),
            plazo=result.get("plazo", ""),
            formatted_response=result.get("formatted_response", ""),
        )

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning("Modelo 309 invalid input: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Modelo 309 endpoint error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular Modelo 309: {e}",
        )
