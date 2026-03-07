"""
Quarterly Declarations REST API — Modelos 303, 130, 420.

Lightweight endpoints that calculate and persist quarterly tax declarations.
No LLM involved — direct calculator calls for fast (~50ms) responses.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from app.auth.jwt_handler import get_current_user, TokenData
from app.security.rate_limiter import limiter

router = APIRouter(prefix="/api/declarations", tags=["declarations"])


# === Request/Response Models ===

class Calculate303Request(BaseModel):
    # IVA devengado
    base_4: float = 0
    base_10: float = 0
    base_21: float = 0
    base_intracomunitarias: float = 0
    tipo_intracomunitarias: float = 0
    base_inversion_sp: float = 0
    tipo_inversion_sp: float = 21.0
    mod_bases: float = 0
    mod_cuotas: float = 0
    # IVA deducible
    base_corrientes_interiores: float = 0
    cuota_corrientes_interiores: float = 0
    base_inversion_interiores: float = 0
    cuota_inversion_interiores: float = 0
    base_importaciones_corrientes: float = 0
    cuota_importaciones_corrientes: float = 0
    base_importaciones_inversion: float = 0
    cuota_importaciones_inversion: float = 0
    base_intracom_corrientes: float = 0
    cuota_intracom_corrientes: float = 0
    base_intracom_inversion: float = 0
    cuota_intracom_inversion: float = 0
    base_rectificacion_deducciones: float = 0
    rectificacion_deducciones: float = 0
    compensacion_agricultura: float = 0
    regularizacion_inversion: float = 0
    regularizacion_prorrata: float = 0
    # Resultado
    pct_atribucion_estado: float = 100.0
    iva_aduana_pendiente: float = 0
    cuotas_compensar_anteriores: float = 0
    regularizacion_anual: float = 0
    resultado_anterior_complementaria: float = 0
    # Metadata
    quarter: int = 1
    year: int = 2025
    territory: str = "comun"


class Calculate130Request(BaseModel):
    territory: str = "Comun"
    quarter: int = 1
    ceuta_melilla: bool = False
    # Comun
    ingresos_acumulados: float = 0
    gastos_acumulados: float = 0
    retenciones_acumuladas: float = 0
    pagos_anteriores: float = 0
    rend_neto_anterior: float = 0
    tiene_vivienda_habitual: bool = False
    resultado_anterior_complementaria: float = 0
    # Araba
    ingresos_trimestre: float = 0
    gastos_trimestre: float = 0
    retenciones_trimestre: float = 0
    # Gipuzkoa / Bizkaia
    regimen: str = "general"
    rend_neto_penultimo: float = 0
    retenciones_penultimo: float = 0
    volumen_operaciones_trimestre: float = 0
    retenciones_trimestre_gipuzkoa: float = 0
    # Bizkaia
    anos_actividad: int = 3
    volumen_ventas_penultimo: float = 0
    # Navarra
    modalidad: str = "segunda"
    retenciones_acumuladas_navarra: float = 0
    pagos_anteriores_navarra: float = 0


class Calculate420Request(BaseModel):
    base_0: float = 0
    base_3: float = 0
    base_7: float = 0
    base_9_5: float = 0
    base_13_5: float = 0
    base_20: float = 0
    base_35: float = 0
    base_extracanarias: float = 0
    tipo_extracanarias: float = 0.07
    base_inversion_sp: float = 0
    mod_bases: float = 0
    mod_cuotas: float = 0
    cuota_corrientes_interiores: float = 0
    cuota_inversion_interiores: float = 0
    cuota_importaciones_corrientes: float = 0
    cuota_importaciones_inversion: float = 0
    cuota_extracanarias_corrientes: float = 0
    cuota_extracanarias_inversion: float = 0
    rectificacion_deducciones: float = 0
    compensacion_agricultura: float = 0
    regularizacion_inversion: float = 0
    regularizacion_prorrata: float = 0
    cuotas_compensar_anteriores: float = 0
    regularizacion_anual: float = 0
    resultado_anterior_complementaria: float = 0
    quarter: int = 1


class SaveDeclarationRequest(BaseModel):
    declaration_type: str  # "303", "130", "420"
    territory: str
    year: int
    quarter: int
    form_data: Dict[str, Any]
    calculated_result: Dict[str, Any]


class CalculationResponse(BaseModel):
    success: bool = True
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ProjectionRequest(BaseModel):
    jurisdiction: str = "Madrid"
    year: int = 2025
    # Family
    edad_contribuyente: int = 35
    num_descendientes: int = 0
    anios_nacimiento_desc: Optional[List[int]] = None
    custodia_compartida: bool = False
    num_ascendientes_65: int = 0
    num_ascendientes_75: int = 0
    discapacidad_contribuyente: int = 0
    ceuta_melilla: bool = False
    estimacion_actividad: str = "directa_simplificada"
    inicio_actividad: bool = False
    un_solo_cliente: bool = False
    # Deductions
    aportaciones_plan_pensiones: float = 0
    hipoteca_pre2013: bool = False
    capital_amortizado_hipoteca: float = 0
    intereses_hipoteca: float = 0
    madre_trabajadora_ss: bool = False
    gastos_guarderia_anual: float = 0
    familia_numerosa: bool = False
    tipo_familia_numerosa: str = "general"
    donativos_ley_49_2002: float = 0
    donativo_recurrente: bool = False
    tributacion_conjunta: bool = False
    tipo_unidad_familiar: str = "matrimonio"
    # Additional income not in quarterly declarations
    ingresos_trabajo: float = 0
    ss_empleado: float = 0
    intereses: float = 0
    dividendos: float = 0
    ganancias_fondos: float = 0
    ingresos_alquiler: float = 0
    gastos_alquiler_total: float = 0
    retenciones_alquiler: float = 0
    retenciones_ahorro: float = 0


class DeclarationListResponse(BaseModel):
    success: bool = True
    declarations: List[Dict[str, Any]] = Field(default_factory=list)


class DeclarationDetailResponse(BaseModel):
    success: bool = True
    declaration: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# === Endpoints ===

@router.post("/303/calculate", response_model=CalculationResponse)
@limiter.limit("30/minute")
async def calculate_303(
    body: Calculate303Request,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Calculate Modelo 303 (IVA) — no LLM, direct calculator."""
    try:
        from app.utils.calculators.modelo_303 import Modelo303Calculator
        calc = Modelo303Calculator(None)
        result = await calc.calculate(**body.model_dump())
        return CalculationResponse(result=result)
    except Exception as e:
        return CalculationResponse(success=False, error=str(e))


@router.post("/130/calculate", response_model=CalculationResponse)
@limiter.limit("30/minute")
async def calculate_130(
    body: Calculate130Request,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Calculate Modelo 130 (Pago Fraccionado IRPF) — no LLM, direct calculator."""
    try:
        from app.utils.calculators.modelo_130 import Modelo130Calculator
        calc = Modelo130Calculator(None)
        result = await calc.calculate(**body.model_dump())
        return CalculationResponse(result=result)
    except Exception as e:
        return CalculationResponse(success=False, error=str(e))


@router.post("/420/calculate", response_model=CalculationResponse)
@limiter.limit("30/minute")
async def calculate_420(
    body: Calculate420Request,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Calculate Modelo 420 (IGIC Canarias) — no LLM, direct calculator."""
    try:
        from app.utils.calculators.modelo_420 import Modelo420Calculator
        calc = Modelo420Calculator(None)
        result = await calc.calculate(**body.model_dump())
        return CalculationResponse(result=result)
    except Exception as e:
        return CalculationResponse(success=False, error=str(e))


@router.post("/save", response_model=CalculationResponse)
@limiter.limit("20/minute")
async def save_declaration(
    body: SaveDeclarationRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Save a calculated declaration to the database."""
    try:
        from app.database.turso_client import get_db_client
        from app.services.declaration_service import DeclarationService

        db = await get_db_client()
        service = DeclarationService(db)
        result = await service.save(
            user_id=current_user.user_id,
            declaration_type=body.declaration_type,
            territory=body.territory,
            year=body.year,
            quarter=body.quarter,
            form_data=body.form_data,
            calculated_result=body.calculated_result,
        )
        return CalculationResponse(result=result)
    except Exception as e:
        return CalculationResponse(success=False, error=str(e))


@router.post("/projection", response_model=CalculationResponse)
@limiter.limit("10/minute")
async def project_annual_irpf(
    body: ProjectionRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Project annual IRPF from quarterly declarations."""
    try:
        from app.database.turso_client import get_db_client
        from app.utils.calculators.irpf_projector import IRPFProjector

        db = await get_db_client()
        projector = IRPFProjector(db)
        result = await projector.project(
            user_id=current_user.user_id,
            **body.model_dump(),
        )
        return CalculationResponse(result=result)
    except Exception as e:
        return CalculationResponse(success=False, error=str(e))


@router.get("/detail/{declaration_id}", response_model=DeclarationDetailResponse)
@limiter.limit("30/minute")
async def get_declaration_detail(
    declaration_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Get full declaration detail."""
    try:
        from app.database.turso_client import get_db_client
        from app.services.declaration_service import DeclarationService

        db = await get_db_client()
        service = DeclarationService(db)
        declaration = await service.get_detail(current_user.user_id, declaration_id)
        if not declaration:
            raise HTTPException(status_code=404, detail="Declaration not found")
        return DeclarationDetailResponse(declaration=declaration)
    except HTTPException:
        raise
    except Exception as e:
        return DeclarationDetailResponse(success=False, error=str(e))


@router.get("/{year}", response_model=DeclarationListResponse)
@limiter.limit("30/minute")
async def list_declarations(
    year: int,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """List all declarations for a year."""
    try:
        from app.database.turso_client import get_db_client
        from app.services.declaration_service import DeclarationService

        db = await get_db_client()
        service = DeclarationService(db)
        declarations = await service.get_by_year(current_user.user_id, year)
        return DeclarationListResponse(declarations=declarations)
    except Exception as e:
        return DeclarationListResponse(success=False)


@router.get("/{year}/{quarter}", response_model=DeclarationListResponse)
@limiter.limit("30/minute")
async def get_quarter_declarations(
    year: int,
    quarter: int,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Get all declarations for a specific quarter."""
    try:
        from app.database.turso_client import get_db_client
        from app.services.declaration_service import DeclarationService

        db = await get_db_client()
        service = DeclarationService(db)
        declarations = await service.get_quarter(current_user.user_id, year, quarter)
        return DeclarationListResponse(declarations=declarations)
    except Exception as e:
        return DeclarationListResponse(success=False)


@router.delete("/{declaration_id}")
@limiter.limit("10/minute")
async def delete_declaration(
    declaration_id: str,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    """Delete a draft declaration."""
    try:
        from app.database.turso_client import get_db_client
        from app.services.declaration_service import DeclarationService

        db = await get_db_client()
        service = DeclarationService(db)
        deleted = await service.delete(current_user.user_id, declaration_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Declaration not found or already presented")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        return {"success": False, "error": str(e)}
