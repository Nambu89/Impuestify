"""
Endpoint autenticado para el Modelo 349 (Declaracion recapitulativa de
operaciones intracomunitarias).

POST /api/modelo-349/calculate
  - Requiere auth (JWT). Solo planes con acceso a autonomo/creator.
  - Rate limit: 60/min por IP.
  - Wrapper directo de `calculate_modelo_349_tool`.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth.jwt_handler import get_current_user
from app.security.rate_limiter import limiter
from app.tools.modelo_349_tool import calculate_modelo_349_tool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modelo-349", tags=["modelo-349"])


class Operacion349Input(BaseModel):
    nif_operador: str = Field(..., description="NIF-IVA del operador (p.ej. IE6388047V)")
    nombre: str = Field(default="", description="Nombre/razon social del operador")
    clave: str = Field(..., description="Clave: E, A, T, S, I, M, H, R, D, C, N")
    importe: float = Field(..., description="Importe en EUR")
    periodo_rectificado: str | None = Field(None, description="Solo clave N/C")
    base_anterior_declarada: float | None = Field(None, description="Solo clave N")


class Modelo349Request(BaseModel):
    operaciones: list[Operacion349Input] = Field(..., min_length=1)
    periodo: str = Field(
        default="1T", description="'01'..'12' mensual, '1T'..'4T' trimestral, 'anual'"
    )
    year: int | None = Field(None, description="Ejercicio fiscal")
    ccaa: str | None = Field(None, description="CCAA del declarante")
    importes_4_trimestres_anteriores: list[float] | None = Field(None)
    casillas_303: dict[str, float] | None = Field(None, description="c60, c36, c38 del 303")
    validar_vies: bool = Field(default=False)
    forzar_anual: bool = Field(default=False)


class Modelo349Response(BaseModel):
    success: bool
    periodo: str
    year: int
    periodicidad: str
    operadores_unicos: int
    total_por_clave: dict[str, float]
    total_general: float
    cuadre_303: dict[str, Any] | None
    avisos: list[str]
    plazo: str
    formatted_response: str


@router.post("/calculate", response_model=Modelo349Response)
@limiter.limit("60/minute")
async def calculate_modelo_349_endpoint(
    request: Request,
    body: Modelo349Request,
    current_user=Depends(get_current_user),
) -> Modelo349Response:
    """
    Calcula el Modelo 349 (declaracion recapitulativa intracomunitaria).
    Requiere autenticacion.
    """
    try:
        raw_ops = [op.model_dump() for op in body.operaciones]
        result = await calculate_modelo_349_tool(
            operaciones=raw_ops,
            periodo=body.periodo,
            year=body.year,
            ccaa=body.ccaa,
            importes_4_trimestres_anteriores=body.importes_4_trimestres_anteriores,
            casillas_303=body.casillas_303,
            validar_vies=body.validar_vies,
            forzar_anual=body.forzar_anual,
            restricted_mode=False,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400, detail=result.get("error") or result.get("formatted_response")
            )

        logger.info(
            "Modelo 349 endpoint: periodo=%s, year=%s, operadores=%s",
            body.periodo,
            body.year,
            result.get("operadores_unicos", 0),
        )

        import datetime as _dt

        year_used = body.year or _dt.datetime.now().year

        return Modelo349Response(
            success=True,
            periodo=body.periodo,
            year=year_used,
            periodicidad=result.get("periodicidad", "trimestral"),
            operadores_unicos=result.get("operadores_unicos", 0),
            total_por_clave=result.get("total_por_clave", {}),
            total_general=result.get("total_general", 0.0),
            cuadre_303=result.get("cuadre_303"),
            avisos=result.get("avisos") or [],
            plazo=result.get("plazo", ""),
            formatted_response=result.get("formatted_response", ""),
        )

    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning("Modelo 349 invalid input: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Modelo 349 endpoint error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al calcular Modelo 349: {e}")
