"""
Endpoint público y autenticado para el Modelo 131 (Pago Fraccionado IRPF
Estimación Objetiva — Módulos).

POST /api/modelo-131/calculate
  - Sin auth (lead magnet SEO, igual que `/api/irpf/estimate`).
  - Body: parámetros del cálculo (apartado, datos-base, asalariados, ...).
  - Devuelve: casillas + resultado + plazo (~50ms, sin LLM).

Wrapper directo de `Modelo131Calculator` — coherente con el tool LLM.
"""

import logging
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.security.rate_limiter import limiter
from app.utils.calculators.modelo_131 import Modelo131Calculator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modelo-131", tags=["modelo-131"])


class Modelo131Request(BaseModel):
    """Parámetros del cálculo del Modelo 131."""

    trimestre: int = Field(..., ge=1, le=4, description="Trimestre 1-4")
    actividad_tipo: Literal["empresarial", "sin_datos_base", "agraria"] = "empresarial"

    # Apartado I — empresarial
    rendimiento_neto_modulos_anual: float = 0.0
    num_asalariados: int = Field(0, ge=0)

    # Apartados II y III
    volumen_ingresos_trimestre: float = 0.0

    # Comunes
    rendimiento_neto_anterior: float = 0.0
    retenciones_trimestre: float = 0.0
    pagos_anteriores: float = 0.0
    resultado_anterior_complementaria: float = 0.0

    # Reducciones territoriales
    ceuta_melilla: bool = False
    la_palma: bool = False

    year: Optional[int] = None


class Modelo131Response(BaseModel):
    """Respuesta del cálculo."""

    success: bool
    trimestre: int
    apartado: str
    actividad_tipo: str
    territory: str
    tipo_aplicado: float
    casillas: Dict[str, float]
    desglose: Dict[str, Any]
    resultado_final: float
    plazo: str


@router.post("/calculate", response_model=Modelo131Response)
@limiter.limit("60/minute")
async def calculate_modelo_131_endpoint(
    request: Request,
    body: Modelo131Request,
) -> Modelo131Response:
    """
    Calcula el resultado del Modelo 131 (pago fraccionado IRPF — módulos).

    Endpoint público (lead magnet SEO + calculadora frontend).
    Rate limit: 60/min por IP.
    """
    try:
        calc = Modelo131Calculator(repo=None)
        result = await calc.calculate(
            quarter=body.trimestre,
            actividad_tipo=body.actividad_tipo,
            rendimiento_neto_modulos_anual=body.rendimiento_neto_modulos_anual,
            num_asalariados=body.num_asalariados,
            volumen_ingresos_trimestre=body.volumen_ingresos_trimestre,
            rendimiento_neto_anterior=body.rendimiento_neto_anterior,
            retenciones_trimestre=body.retenciones_trimestre,
            pagos_anteriores=body.pagos_anteriores,
            resultado_anterior_complementaria=body.resultado_anterior_complementaria,
            ceuta_melilla=body.ceuta_melilla,
            la_palma=body.la_palma,
        )

        logger.info(
            "Modelo 131 endpoint: apartado=%s, trimestre=%s, resultado=%s",
            result["apartado"],
            body.trimestre,
            result["resultado"],
        )

        return Modelo131Response(
            success=True,
            trimestre=body.trimestre,
            apartado=result["apartado"],
            actividad_tipo=result["actividad_tipo"],
            territory=result["territory"],
            tipo_aplicado=result["tipo_aplicado"],
            casillas=result["casillas"],
            desglose=result["desglose"],
            resultado_final=result["resultado"],
            plazo=result["plazo"],
        )

    except ValueError as ve:
        logger.warning("Modelo 131 invalid input: %s", ve)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error("Modelo 131 endpoint error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular Modelo 131: {e}",
        )
