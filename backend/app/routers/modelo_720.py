"""
REST endpoints for Modelo 720 (Bienes Extranjero) and Modelo 721 (Cripto Extranjero).

Public endpoints (no auth required) — designed as lead magnet / free tool.
Rate limited to prevent abuse.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modelos", tags=["modelos"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class Check720Request(BaseModel):
    """Body para evaluar obligacion Modelo 720."""
    cuentas_extranjero: float = Field(
        default=0,
        ge=0,
        description="Saldo cuentas bancarias en el extranjero a 31/dic (EUR)",
    )
    valores_extranjero: float = Field(
        default=0,
        ge=0,
        description="Valor mercado valores/seguros en entidades extranjeras (EUR)",
    )
    inmuebles_extranjero: float = Field(
        default=0,
        ge=0,
        description="Valor adquisicion inmuebles en el extranjero (EUR)",
    )
    ultimo_720_presentado: Optional[int] = Field(
        default=None,
        description="Ano del ultimo Modelo 720 presentado (o null)",
    )
    saldos_ultimo_720_cuentas: Optional[float] = Field(
        default=None,
        ge=0,
        description="Saldo cuentas declarado en ultimo 720 (EUR)",
    )
    saldos_ultimo_720_valores: Optional[float] = Field(
        default=None,
        ge=0,
        description="Valor valores declarado en ultimo 720 (EUR)",
    )
    saldos_ultimo_720_inmuebles: Optional[float] = Field(
        default=None,
        ge=0,
        description="Valor inmuebles declarado en ultimo 720 (EUR)",
    )


class Check721Request(BaseModel):
    """Body para evaluar obligacion Modelo 721."""
    crypto_extranjero_valor: float = Field(
        default=0,
        ge=0,
        description="Valor mercado cripto en exchanges extranjeros a 31/dic (EUR)",
    )
    exchanges_extranjeros: Optional[List[str]] = Field(
        default=None,
        description="Lista de exchanges extranjeros (ej: ['Binance', 'Coinbase'])",
    )
    ultimo_721_presentado: Optional[int] = Field(
        default=None,
        description="Ano del ultimo Modelo 721 presentado (o null)",
    )
    valor_ultimo_721: Optional[float] = Field(
        default=None,
        ge=0,
        description="Valor total declarado en ultimo 721 (EUR)",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/check-720")
@limiter.limit("20/minute")
async def check_720(request: Request, body: Check720Request):
    """
    Evalua si el contribuyente esta obligado a presentar el Modelo 720
    (Declaracion Informativa de Bienes y Derechos en el Extranjero).

    Endpoint publico (no requiere autenticacion) — herramienta gratuita / lead magnet.

    Evalua tres categorias independientes con umbral de 50.000 EUR cada una:
    1. Cuentas bancarias en el extranjero
    2. Valores, derechos, seguros y rentas en entidades extranjeras
    3. Bienes inmuebles en el extranjero

    Si se presento un 720 anterior, tambien evalua incremento >20.000 EUR.
    """
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=body.cuentas_extranjero,
        valores_extranjero=body.valores_extranjero,
        inmuebles_extranjero=body.inmuebles_extranjero,
        ultimo_720_presentado=body.ultimo_720_presentado,
        saldos_ultimo_720_cuentas=body.saldos_ultimo_720_cuentas,
        saldos_ultimo_720_valores=body.saldos_ultimo_720_valores,
        saldos_ultimo_720_inmuebles=body.saldos_ultimo_720_inmuebles,
    )

    return result


@router.post("/check-721")
@limiter.limit("20/minute")
async def check_721(request: Request, body: Check721Request):
    """
    Evalua si el contribuyente esta obligado a presentar el Modelo 721
    (Declaracion Informativa sobre Monedas Virtuales en el Extranjero).

    Endpoint publico (no requiere autenticacion) — herramienta gratuita / lead magnet.

    Evalua si el saldo en criptomonedas en exchanges extranjeros supera
    50.000 EUR a 31/dic, o si hay incremento >20.000 EUR vs ultimo 721.
    """
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=body.crypto_extranjero_valor,
        exchanges_extranjeros=body.exchanges_extranjeros,
        ultimo_721_presentado=body.ultimo_721_presentado,
        valor_ultimo_721=body.valor_ultimo_721,
    )

    return result
