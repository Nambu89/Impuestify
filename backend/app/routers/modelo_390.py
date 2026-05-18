"""
Endpoint autenticado para el Modelo 390 (Resumen anual IVA).

POST /api/modelo-390/calculate
  - Requiere auth (JWT).
  - Rate limit: 60/min por IP.
  - Wrapper directo de `calculate_modelo_390_tool`.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.jwt_handler import get_current_user
from app.security.rate_limiter import limiter
from app.tools.modelo_390_tool import calculate_modelo_390_tool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modelo-390", tags=["modelo-390"])


class Trimestre303Input(BaseModel):
    """Datos minimos de un trimestre 303 para el resumen anual."""

    casilla_03: float = Field(default=0.0, description="Cuota IVA devengado 4%")
    casilla_06: float = Field(default=0.0, description="Cuota IVA devengado 10%")
    casilla_09: float = Field(default=0.0, description="Cuota IVA devengado 21%")
    casilla_27: float = Field(default=0.0, description="Total IVA devengado")
    casilla_29: float = Field(default=0.0, description="Cuotas bienes corrientes deducibles")
    casilla_31: float = Field(default=0.0, description="Cuotas bienes inversion deducibles")
    casilla_33: float = Field(default=0.0, description="Cuotas importaciones deducibles")
    casilla_37: float = Field(default=0.0, description="Cuotas intracomunitarias deducibles")
    casilla_45: float = Field(default=0.0, description="Total IVA deducible")
    resultado_liquidacion: float = Field(default=0.0, description="Resultado del trimestre")


class Modelo390Request(BaseModel):
    year: Optional[int] = Field(None, description="Ejercicio (ej. 2025 -> presentar enero 2026)")
    ccaa: Optional[str] = Field(None, description="CCAA o territorio")
    volumen_operaciones_ano_anterior: float = Field(default=0.0, ge=0)
    en_redeme: bool = Field(default=False)
    en_grupo_iva: bool = Field(default=False)
    sii_voluntario: bool = Field(default=False)
    regimen_especial: Optional[str] = Field(
        None, description="simplificado | recargo_equivalencia | general"
    )
    trimestres_303: Optional[List[Trimestre303Input]] = Field(
        None,
        description="Exactamente 4 trimestres del 303 para calcular resumen anual",
    )


class Modelo390Response(BaseModel):
    success: bool
    year: int
    obligado: bool
    modelo: Optional[str]
    ccaa: Optional[str]
    motivo_exoneracion: Optional[str]
    variante_territorial: Optional[str]
    resumen_anual: Optional[Dict[str, Any]]
    plazo: str
    formatted_response: str


@router.post("/calculate", response_model=Modelo390Response)
@limiter.limit("60/minute")
async def calculate_modelo_390_endpoint(
    request: Request,
    body: Modelo390Request,
    current_user=Depends(get_current_user),
) -> Modelo390Response:
    """
    Calcula / verifica el Modelo 390 (resumen anual IVA).
    Requiere autenticacion.
    """
    try:
        trimestres_raw = None
        if body.trimestres_303:
            trimestres_raw = [t.model_dump() for t in body.trimestres_303]

        result = await calculate_modelo_390_tool(
            year=body.year,
            ccaa=body.ccaa,
            volumen_operaciones_ano_anterior=body.volumen_operaciones_ano_anterior,
            en_redeme=body.en_redeme,
            en_grupo_iva=body.en_grupo_iva,
            sii_voluntario=body.sii_voluntario,
            regimen_especial=body.regimen_especial,
            trimestres_303=trimestres_raw,
            restricted_mode=False,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400, detail=result.get("error") or result.get("formatted_response")
            )

        import datetime as _dt

        year_used = body.year if body.year else (_dt.datetime.now().year - 1)

        logger.info(
            "Modelo 390 endpoint: year=%s, obligado=%s, modelo=%s",
            year_used,
            result.get("obligado"),
            result.get("modelo"),
        )

        return Modelo390Response(
            success=True,
            year=year_used,
            obligado=result.get("obligado", True),
            modelo=result.get("modelo"),
            ccaa=body.ccaa,
            motivo_exoneracion=result.get("motivo_exoneracion"),
            variante_territorial=result.get("variante_territorial"),
            resumen_anual=result.get("resumen_anual"),
            plazo=result.get("plazo", "1 al 30 de enero"),
            formatted_response=result.get("formatted_response", ""),
        )

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning("Modelo 390 invalid input: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Modelo 390 endpoint error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al calcular Modelo 390: {e}")
