"""
GDPR User Rights Endpoints + User Profile

Implements user rights according to GDPR/RGPD:
- Art. 15: Right to Access (Data Export)
- Art. 16: Right to Rectification (Profile Update)
- Art. 17: Right to Erasure (Account Deletion)

Also provides:
- Password change
- Fiscal profile management (voluntary IRPF data)
"""

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth.jwt_handler import TokenData, get_current_user
from app.auth.password import hash_password, verify_password
from app.database.turso_client import TursoClient, get_db_client
from app.services.subscription_service import (
    get_subscription_service,
    validate_plan_role_compatibility,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users/me", tags=["user-rights"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================


class UserUpdateRequest(BaseModel):
    """Request model for updating user profile"""

    name: str | None = None
    email: EmailStr | None = None


class PasswordChangeRequest(BaseModel):
    """Request model for changing password"""

    current_password: str
    new_password: str = Field(min_length=8, description="Min 8 characters")


class FiscalProfileRequest(BaseModel):
    """Request model for updating fiscal profile (all fields optional)"""

    ccaa_residencia: str | None = None
    fecha_nacimiento: str | None = None
    situacion_laboral: str | None = None
    estado_civil: str | None = None  # soltero|casado|divorciado|viudo|pareja_de_hecho
    ingresos_trabajo: float | None = None
    ss_empleado: float | None = None
    num_descendientes: int | None = None
    anios_nacimiento_desc: list[int] | None = None
    custodia_compartida: bool | None = None
    num_ascendientes_65: int | None = None
    num_ascendientes_75: int | None = None
    discapacidad_contribuyente: int | None = None
    intereses: float | None = None
    dividendos: float | None = None
    ganancias_fondos: float | None = None
    ingresos_alquiler: float | None = None
    valor_adquisicion_inmueble: float | None = None
    # --- Autonomo-specific fields ---
    epigrafe_iae: str | None = None
    tipo_actividad: str | None = None  # "profesional" | "empresarial" | "artistica"
    fecha_alta_autonomo: str | None = None  # ISO date "2024-03-15"
    metodo_estimacion_irpf: str | None = (
        None  # "directa_normal" | "directa_simplificada" | "objetiva"
    )
    regimen_iva: str | None = (
        None  # "general" | "simplificado" | "recargo_equivalencia" | "exento" | "ipsi"
    )
    rendimientos_netos_mensuales: float | None = None
    base_cotizacion_reta: float | None = None
    territorio_foral: bool | None = None
    territorio_historico: str | None = None  # "bizkaia" | "gipuzkoa" | "araba" | "navarra"
    tipo_retencion_facturas: float | None = None  # 15.0 or 7.0
    tarifa_plana: bool | None = None
    pluriactividad: bool | None = None
    ceuta_melilla: bool | None = (
        None  # Resident in Ceuta/Melilla (60% IRPF deduction + 50% SS bonus + IPSI)
    )
    # --- Phase 1: IRPF deductions / reductions ---
    aportaciones_plan_pensiones: float | None = None
    aportaciones_plan_pensiones_empresa: float | None = None
    hipoteca_pre2013: bool | None = None
    capital_amortizado_hipoteca: float | None = None
    intereses_hipoteca: float | None = None
    madre_trabajadora_ss: bool | None = None
    gastos_guarderia_anual: float | None = None
    familia_numerosa: bool | None = None
    tipo_familia_numerosa: str | None = None  # "general" | "especial"
    donativos_ley_49_2002: float | None = None
    donativo_recurrente: bool | None = None
    retenciones_trabajo: float | None = None
    retenciones_alquiler: float | None = None
    retenciones_ahorro: float | None = None
    # --- Phase 3: Payslip/salary fields ---
    num_pagas_anuales: int | None = None  # 12 | 14
    salario_base_mensual: float | None = None
    complementos_salariales: float | None = None
    irpf_retenido_porcentaje: float | None = None
    # --- Sprint 1: Vivienda ---
    alquiler_vivienda_habitual: bool | None = None
    importe_alquiler_anual: float | None = None
    vivienda_habitual_propiedad: bool | None = None
    rehabilitacion_vivienda: bool | None = None
    vivienda_rural: bool | None = None
    dacion_pago_alquiler: bool | None = None
    arrendador_vivienda_social: bool | None = None
    # --- Sprint 1: Familia ---
    nacimiento_adopcion_reciente: bool | None = None
    adopcion_internacional: bool | None = None
    acogimiento_familiar: bool | None = None
    familia_monoparental: bool | None = None
    hijos_escolarizados: bool | None = None
    gastos_guarderia: bool | None = None
    ambos_progenitores_trabajan: bool | None = None
    hijos_estudios_universitarios: bool | None = None
    # --- Sprint 1: Discapacidad ---
    descendiente_discapacidad: bool | None = None
    ascendiente_discapacidad: bool | None = None
    ascendiente_a_cargo: bool | None = None
    familiar_discapacitado_cargo: bool | None = None
    empleada_hogar_cuidado: bool | None = None
    # --- Sprint 1: Donaciones ---
    donativo_entidad_autonomica: bool | None = None
    donativo_investigacion: bool | None = None
    donativo_patrimonio: bool | None = None
    donativo_fundacion_local: bool | None = None
    # --- Sprint 1: Sostenibilidad ---
    vehiculo_electrico_nuevo: bool | None = None
    obras_mejora_energetica: bool | None = None
    instalacion_renovable: bool | None = None
    # --- Sprint 1: Territorio ---
    municipio_despoblado: bool | None = None
    inversion_empresa_nueva: bool | None = None
    # --- Sprint 1: Foral (solo si CCAA foral) ---
    epsv_aportaciones: float | None = None
    pension_viudedad: bool | None = None
    reduccion_jornada_cuidado: bool | None = None
    cuenta_vivienda_aportaciones: float | None = None
    # --- Activity income (autonomo IRPF fields used by tax guide) ---
    ingresos_actividad: float | None = None
    gastos_actividad: float | None = None
    cuota_autonomo_anual: float | None = None
    amortizaciones_actividad: float | None = None
    provisiones_actividad: float | None = None
    otros_gastos_actividad: float | None = None
    estimacion_actividad: str | None = (
        None  # "directa_simplificada" | "directa_normal" | "objetiva"
    )
    inicio_actividad: bool | None = None
    un_solo_cliente: bool | None = None
    retenciones_actividad: float | None = None
    pagos_fraccionados_130: float | None = None
    # --- Phase 2: Tributación conjunta + alquiler pre-2015 + rentas imputadas ---
    tributacion_conjunta: bool | None = None
    tipo_unidad_familiar: str | None = None  # "matrimonio" | "monoparental"
    alquiler_habitual_pre2015: bool | None = None
    alquiler_pagado_anual: float | None = None
    valor_catastral_segundas_viviendas: float | None = None
    valor_catastral_revisado_post1994: bool | None = None
    gastos_alquiler_total: float | None = None
    # --- Criptomonedas (casillas 1800-1814 Modelo 100) ---
    tiene_criptomonedas: bool | None = None
    cripto_denominaciones: str | None = None
    cripto_clave_contraprestacion: str | None = None  # F | N | O | B
    cripto_valor_transmision_total: float | None = None
    cripto_valor_adquisicion_total: float | None = None
    cripto_ganancia_neta: float | None = None
    cripto_perdida_neta: float | None = None
    cripto_en_extranjero_50k: bool | None = None
    tiene_staking_defi: bool | None = None
    exchanges_utilizados: str | None = None
    # --- Apuestas y juegos — juegos privados (casillas 0281-0290) ---
    tiene_ganancias_juegos_privados: bool | None = None
    premios_metalico_privados: float | None = None
    premios_especie_privados: float | None = None
    perdidas_juegos_privados: float | None = None
    # --- Apuestas y juegos — loterías públicas (casillas 0291-0297) ---
    tiene_premios_loterias: bool | None = None
    premios_metalico_publicos: float | None = None
    premios_especie_publicos: float | None = None
    # --- Ganancias patrimoniales financieras (casillas 0316-0354) ---
    tiene_fondos_inversion: bool | None = None
    ganancias_reembolso_fondos: float | None = None
    perdidas_reembolso_fondos: float | None = None
    tiene_acciones: bool | None = None
    ganancias_acciones: float | None = None  # ya existía, se mantiene
    perdidas_acciones: float | None = None  # ya existía, se mantiene
    tiene_derivados: bool | None = None
    ganancias_derivados: float | None = None
    perdidas_derivados: float | None = None
    # --- Multi-pagador (AEAT Datos Fiscales) ---
    pagadores: list[dict] | None = None  # List of PagadorItem-compatible dicts
    num_pagadores: int | None = None


class UserDataExport(BaseModel):
    """Complete user data export (GDPR Art. 15)"""

    export_date: str
    user: dict[str, Any]
    conversations: list[dict[str, Any]]
    total_conversations: int
    total_messages: int
    account_created: str


class DeleteAccountResponse(BaseModel):
    """Response after account deletion"""

    message: str
    user_id: str
    deleted_at: str
    data_purged: dict[str, int]


# ============================================
# GDPR ART. 15: RIGHT TO ACCESS (DATA EXPORT)
# ============================================


@router.get("/data", response_model=UserDataExport)
async def export_user_data(
    current_user: TokenData = Depends(get_current_user), db: TursoClient = Depends(get_db_client)
):
    """
    Export all user data in JSON format.

    **GDPR Art. 15 - Right to Access**
    """
    user_id = current_user.user_id

    # 1. Get user account data
    user_result = await db.execute(
        "SELECT id, email, name, is_admin, created_at, updated_at FROM users WHERE id = ?",
        [user_id],
    )

    if not user_result.rows:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = user_result.rows[0]

    # 2. Get all conversations
    conversations_result = await db.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at,
               COUNT(m.id) as message_count
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.created_at DESC
        """,
        [user_id],
    )

    conversations_list = []
    total_messages = 0

    for conv in conversations_result.rows:
        # Get messages for this conversation
        messages_result = await db.execute(
            """
            SELECT id, role, content, created_at, metadata
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            [conv["id"]],
        )

        messages = [
            {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "metadata": json.loads(msg["metadata"]) if msg.get("metadata") else None,
                "created_at": msg["created_at"],
            }
            for msg in messages_result.rows
        ]

        conversations_list.append(
            {
                "id": conv["id"],
                "title": conv["title"],
                "created_at": conv["created_at"],
                "updated_at": conv["updated_at"],
                "message_count": conv["message_count"] or 0,
                "messages": messages,
            }
        )

        total_messages += len(messages)

    # 3. Build export
    export = UserDataExport(
        export_date=datetime.now(UTC).isoformat() + "Z",
        user={
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "is_admin": bool(user_data["is_admin"]),
            "created_at": user_data["created_at"],
            "updated_at": user_data["updated_at"],
        },
        conversations=conversations_list,
        total_conversations=len(conversations_list),
        total_messages=total_messages,
        account_created=user_data["created_at"],
    )

    return export


# ============================================
# GDPR ART. 16: RIGHT TO RECTIFICATION
# ============================================


@router.patch("", response_model=dict)
async def update_user_profile(
    updates: UserUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """
    Update user profile information.

    **GDPR Art. 16 - Right to Rectification**
    """
    user_id = current_user.user_id

    # Check if there's anything to update
    if not updates.name and not updates.email:
        raise HTTPException(status_code=400, detail="No data provided for update")

    # Check email uniqueness if email is being updated
    if updates.email:
        existing_user = await db.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?", [updates.email, user_id]
        )

        if existing_user.rows:
            raise HTTPException(status_code=409, detail="Email already in use")

    # Build UPDATE query dynamically
    update_fields = []
    params = []

    if updates.name is not None:
        update_fields.append("name = ?")
        params.append(updates.name)

    if updates.email is not None:
        update_fields.append("email = ?")
        params.append(updates.email)

    # Always update updated_at
    update_fields.append("updated_at = datetime('now')")

    # Execute update
    params.append(user_id)

    await db.execute(f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?", params)

    # Fetch updated user
    updated_user = await db.execute(
        "SELECT id, email, name, is_admin, created_at, updated_at FROM users WHERE id = ?",
        [user_id],
    )

    if not updated_user.rows:
        raise HTTPException(status_code=404, detail="User not found after update")

    user_data = updated_user.rows[0]

    return {
        "message": "Profile updated successfully",
        "user": {
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "is_admin": bool(user_data["is_admin"]),
            "created_at": user_data["created_at"],
            "updated_at": user_data["updated_at"],
        },
    }


# ============================================
# PASSWORD CHANGE
# ============================================


@router.put("/password")
async def change_password(
    body: PasswordChangeRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """
    Change user password.

    Requires current password verification.
    Invalidates all other sessions after change.
    """
    user_id = current_user.user_id

    # 1. Get current password hash
    user_result = await db.execute("SELECT password_hash FROM users WHERE id = ?", [user_id])

    if not user_result.rows:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    current_hash = user_result.rows[0]["password_hash"]

    # 2. Verify current password
    if not verify_password(body.current_password, current_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")

    # 3. Hash new password and update
    new_hash = hash_password(body.new_password)
    await db.execute(
        "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
        [new_hash, user_id],
    )

    # 4. Invalidate all sessions (force re-login on other devices)
    await db.execute("DELETE FROM sessions WHERE user_id = ?", [user_id])

    logger.info("Password changed for user %s", user_id)

    return {"message": "Contraseña actualizada correctamente"}


# ============================================
# FISCAL PROFILE
# ============================================

# Fields stored as top-level columns in user_profiles
_PROFILE_COLUMNS = {"ccaa_residencia", "fecha_nacimiento", "situacion_laboral"}
# All other FiscalProfileRequest fields go into datos_fiscales JSON
_DATOS_FISCALES_KEYS = {
    "estado_civil",
    "ingresos_trabajo",
    "ss_empleado",
    "num_descendientes",
    "anios_nacimiento_desc",
    "custodia_compartida",
    "num_ascendientes_65",
    "num_ascendientes_75",
    "discapacidad_contribuyente",
    "intereses",
    "dividendos",
    "ganancias_fondos",
    "ingresos_alquiler",
    "valor_adquisicion_inmueble",
    # Autonomo-specific
    "epigrafe_iae",
    "tipo_actividad",
    "fecha_alta_autonomo",
    "metodo_estimacion_irpf",
    "regimen_iva",
    "rendimientos_netos_mensuales",
    "base_cotizacion_reta",
    "territorio_foral",
    "territorio_historico",
    "tipo_retencion_facturas",
    "tarifa_plana",
    "pluriactividad",
    "ceuta_melilla",
    # Phase 1: IRPF deductions / reductions
    "aportaciones_plan_pensiones",
    "aportaciones_plan_pensiones_empresa",
    "hipoteca_pre2013",
    "capital_amortizado_hipoteca",
    "intereses_hipoteca",
    "madre_trabajadora_ss",
    "gastos_guarderia_anual",
    "familia_numerosa",
    "tipo_familia_numerosa",
    "donativos_ley_49_2002",
    "donativo_recurrente",
    "retenciones_trabajo",
    "retenciones_alquiler",
    "retenciones_ahorro",
    # Phase 3: Payslip/salary fields
    "num_pagas_anuales",
    "salario_base_mensual",
    "complementos_salariales",
    "irpf_retenido_porcentaje",
    # Sprint 1: Vivienda
    "alquiler_vivienda_habitual",
    "importe_alquiler_anual",
    "vivienda_habitual_propiedad",
    "rehabilitacion_vivienda",
    "vivienda_rural",
    "dacion_pago_alquiler",
    "arrendador_vivienda_social",
    # Sprint 1: Familia
    "nacimiento_adopcion_reciente",
    "adopcion_internacional",
    "acogimiento_familiar",
    "familia_monoparental",
    "hijos_escolarizados",
    "gastos_guarderia",
    "ambos_progenitores_trabajan",
    "hijos_estudios_universitarios",
    # Sprint 1: Discapacidad
    "descendiente_discapacidad",
    "ascendiente_discapacidad",
    "ascendiente_a_cargo",
    "familiar_discapacitado_cargo",
    "empleada_hogar_cuidado",
    # Sprint 1: Donaciones
    "donativo_entidad_autonomica",
    "donativo_investigacion",
    "donativo_patrimonio",
    "donativo_fundacion_local",
    # Sprint 1: Sostenibilidad
    "vehiculo_electrico_nuevo",
    "obras_mejora_energetica",
    "instalacion_renovable",
    # Sprint 1: Territorio
    "municipio_despoblado",
    "inversion_empresa_nueva",
    # Sprint 1: Foral
    "epsv_aportaciones",
    "pension_viudedad",
    "reduccion_jornada_cuidado",
    "cuenta_vivienda_aportaciones",
    # Activity income (autonomo IRPF)
    "ingresos_actividad",
    "gastos_actividad",
    "cuota_autonomo_anual",
    "amortizaciones_actividad",
    "provisiones_actividad",
    "otros_gastos_actividad",
    "estimacion_actividad",
    "inicio_actividad",
    "un_solo_cliente",
    "retenciones_actividad",
    "pagos_fraccionados_130",
    # Phase 2: Tributación conjunta + alquiler pre-2015 + rentas imputadas
    "tributacion_conjunta",
    "tipo_unidad_familiar",
    "alquiler_habitual_pre2015",
    "alquiler_pagado_anual",
    "valor_catastral_segundas_viviendas",
    "valor_catastral_revisado_post1994",
    "gastos_alquiler_total",
    # Criptomonedas (casillas 1800-1814 Modelo 100)
    "tiene_criptomonedas",
    "cripto_denominaciones",
    "cripto_clave_contraprestacion",
    "cripto_valor_transmision_total",
    "cripto_valor_adquisicion_total",
    "cripto_ganancia_neta",
    "cripto_perdida_neta",
    "cripto_en_extranjero_50k",
    "tiene_staking_defi",
    "exchanges_utilizados",
    # Apuestas y juegos — privados (casillas 0281-0290)
    "tiene_ganancias_juegos_privados",
    "premios_metalico_privados",
    "premios_especie_privados",
    "perdidas_juegos_privados",
    # Apuestas y juegos — loterías públicas (casillas 0291-0297)
    "tiene_premios_loterias",
    "premios_metalico_publicos",
    "premios_especie_publicos",
    # Ganancias patrimoniales financieras (casillas 0316-0354)
    "tiene_fondos_inversion",
    "ganancias_reembolso_fondos",
    "perdidas_reembolso_fondos",
    "tiene_acciones",
    "ganancias_acciones",
    "perdidas_acciones",
    "tiene_derivados",
    "ganancias_derivados",
    "perdidas_derivados",
    # Fase 5: Datos para deducciones autonómicas
    "donativos_autonomicos",
    "gastos_educativos",
    "inversion_vivienda",
    "instalacion_renovable_importe",
    "vehiculo_electrico_importe",
    "obras_mejora_importe",
    "cotizaciones_empleada_hogar",
    # Multi-pagador (AEAT Datos Fiscales)
    "pagadores",
    "num_pagadores",
}


@router.get("/fiscal-profile")
async def get_fiscal_profile(
    current_user: TokenData = Depends(get_current_user), db: TursoClient = Depends(get_db_client)
):
    """
    Get user's fiscal profile for IRPF calculation.

    Returns profile fields + datos_fiscales with source metadata.
    """
    user_id = current_user.user_id

    result = await db.execute(
        "SELECT ccaa_residencia, situacion_laboral, fecha_nacimiento, datos_fiscales "
        "FROM user_profiles WHERE user_id = ?",
        [user_id],
    )

    if not result.rows:
        return {
            "ccaa_residencia": None,
            "situacion_laboral": None,
            "fecha_nacimiento": None,
            "fields": {},
            "field_meta": {},
        }

    row = result.rows[0]

    # Parse datos_fiscales JSON
    datos_raw = row.get("datos_fiscales")
    datos = {}
    if datos_raw:
        try:
            datos = json.loads(datos_raw) if isinstance(datos_raw, str) else datos_raw
        except (json.JSONDecodeError, TypeError):
            datos = {}

    # Separate values from metadata
    # Skip keys that are already top-level columns to avoid frontend merge conflicts
    fields = {}
    field_meta = {}
    for key, entry in datos.items():
        if key.startswith("_"):
            continue
        if key in _PROFILE_COLUMNS:
            continue  # Already returned as top-level; don't duplicate in fields
        if isinstance(entry, dict) and "value" in entry:
            fields[key] = entry["value"]
            field_meta[key] = {
                "source": entry.get("_source", "unknown"),
                "updated": entry.get("_updated", ""),
            }
        else:
            # Legacy format (plain value, no metadata)
            fields[key] = entry
            field_meta[key] = {"source": "conversation", "updated": ""}

    return {
        "ccaa_residencia": row.get("ccaa_residencia"),
        "situacion_laboral": row.get("situacion_laboral"),
        "fecha_nacimiento": row.get("fecha_nacimiento"),
        "fields": fields,
        "field_meta": field_meta,
    }


@router.put("/fiscal-profile")
async def update_fiscal_profile(
    body: FiscalProfileRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """
    Save user's fiscal profile (manual entry).

    Fields marked with _source='manual' will NOT be overwritten by
    conversation-extracted data.
    """
    user_id = current_user.user_id
    now = datetime.now(UTC).isoformat()

    # Check if profile exists
    existing = await db.execute(
        "SELECT id, datos_fiscales FROM user_profiles WHERE user_id = ?", [user_id]
    )

    # Parse existing datos_fiscales
    datos_fiscales = {}
    if existing.rows:
        raw = existing.rows[0].get("datos_fiscales")
        if raw:
            try:
                datos_fiscales = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                datos_fiscales = {}

    # Merge new values into datos_fiscales with source="manual"
    request_data = body.model_dump(exclude_none=True)

    # --- Plan-role compatibility check ---
    situacion = request_data.get("situacion_laboral")
    if situacion:
        sub_service = await get_subscription_service()
        access = await sub_service.check_access(user_id, current_user.email)
        incompatible = validate_plan_role_compatibility(
            access.plan_type, situacion, access.is_owner
        )
        if incompatible:
            raise HTTPException(
                status_code=403,
                detail={
                    "detail": "plan_incompatible",
                    "message": (
                        f"Tu plan {incompatible['current_plan'].capitalize()} "
                        f"no incluye el perfil de {situacion}"
                    ),
                    "required_plan": incompatible["required_plan"],
                    "current_plan": incompatible["current_plan"],
                    "upgrade_url": "/subscribe",
                },
            )

    for key in _DATOS_FISCALES_KEYS:
        if key in request_data:
            datos_fiscales[key] = {
                "value": request_data[key],
                "_source": "manual",
                "_updated": now,
            }

    datos_json = json.dumps(datos_fiscales)

    # Extract top-level column values
    ccaa = request_data.get("ccaa_residencia")
    fecha = request_data.get("fecha_nacimiento")
    situacion = request_data.get("situacion_laboral")

    if existing.rows:
        # Build dynamic UPDATE
        update_fields = ["datos_fiscales = ?", "updated_at = ?"]
        params: list = [datos_json, now]

        if ccaa is not None:
            update_fields.append("ccaa_residencia = ?")
            params.append(ccaa)
        if fecha is not None:
            update_fields.append("fecha_nacimiento = ?")
            params.append(fecha)
        if situacion is not None:
            update_fields.append("situacion_laboral = ?")
            params.append(situacion)

        params.append(user_id)
        await db.execute(
            f"UPDATE user_profiles SET {', '.join(update_fields)} WHERE user_id = ?", params
        )
    else:
        # INSERT new profile
        profile_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO user_profiles
               (id, user_id, ccaa_residencia, situacion_laboral, fecha_nacimiento,
                datos_fiscales, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [profile_id, user_id, ccaa, situacion, fecha, datos_json, now, now],
        )

    logger.info("Fiscal profile updated (manual) for user %s", user_id)

    return {"message": "Perfil fiscal guardado correctamente"}


# ============================================
# GDPR ART. 17: RIGHT TO ERASURE
# ============================================


@router.delete("", response_model=DeleteAccountResponse)
async def delete_user_account(
    current_user: TokenData = Depends(get_current_user), db: TursoClient = Depends(get_db_client)
):
    """
    Permanently delete user account and all associated data.

    **GDPR Art. 17 - Right to Erasure ("Right to be Forgotten")**

    WARNING: This action is IRREVERSIBLE.
    """
    user_id = current_user.user_id

    # Count data before deletion (for confirmation)
    conversations_count_result = await db.execute(
        "SELECT COUNT(*) as count FROM conversations WHERE user_id = ?", [user_id]
    )
    conversations_count = conversations_count_result.rows[0]["count"]

    messages_count_result = await db.execute(
        """
        SELECT COUNT(m.id) as count
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.user_id = ?
        """,
        [user_id],
    )
    messages_count = messages_count_result.rows[0]["count"]

    sessions_count_result = await db.execute(
        "SELECT COUNT(*) as count FROM sessions WHERE user_id = ?", [user_id]
    )
    sessions_count = sessions_count_result.rows[0]["count"]

    # Delete all user data explicitly (defense-in-depth, in case CASCADE not active)
    # Order: deepest children first

    # Messages (child of conversations)
    await db.execute(
        """DELETE FROM messages WHERE conversation_id IN
           (SELECT id FROM conversations WHERE user_id = ?)""",
        [user_id],
    )

    # Conversations
    await db.execute("DELETE FROM conversations WHERE user_id = ?", [user_id])

    # User profiles
    await db.execute("DELETE FROM user_profiles WHERE user_id = ?", [user_id])

    # Workspace embeddings → workspace files → workspaces
    await db.execute(
        """DELETE FROM workspace_file_embeddings WHERE workspace_id IN
           (SELECT id FROM workspaces WHERE user_id = ?)""",
        [user_id],
    )
    await db.execute(
        """DELETE FROM workspace_files WHERE workspace_id IN
           (SELECT id FROM workspaces WHERE user_id = ?)""",
        [user_id],
    )
    await db.execute("DELETE FROM workspaces WHERE user_id = ?", [user_id])

    # Crypto tables (GDPR: delete before user row due to FK constraints)
    await db.execute("DELETE FROM crypto_gains WHERE user_id = ?", [user_id])
    await db.execute("DELETE FROM crypto_holdings WHERE user_id = ?", [user_id])
    await db.execute("DELETE FROM crypto_transactions WHERE user_id = ?", [user_id])

    # Feedback & chat ratings (GDPR Art.17 — defense-in-depth, tables have ON DELETE CASCADE)
    await db.execute("DELETE FROM feedback WHERE user_id = ?", [user_id])
    await db.execute("DELETE FROM chat_ratings WHERE user_id = ?", [user_id])

    # DefensIA (T3-003 GDPR cascade): eliminamos explicitamente las 7 tablas
    # defensia_* aunque la migracion declara FK con ON DELETE CASCADE. Es
    # defensa en profundidad por si el pragma foreign_keys no esta activo o
    # si Turso libSQL no aplica el cascade en todos los caminos. El orden
    # respeta las FK internas: rag_log -> escritos -> dictamenes -> briefs
    # -> documentos -> expedientes -> cuotas.
    #
    # Este cliente/wrapper ejecuta cada DELETE de forma independiente
    # (autocommit). Sin API transaccional expuesta, cada DELETE es
    # best-effort: un fallo en una tabla no impide borrar las demas ni
    # aborta el DELETE final sobre users. ON DELETE CASCADE en las
    # migraciones es la primera linea de defensa; estos deletes son la
    # segunda. Si alguno falla, se loggea warning y se continua.
    _defensia_deletes = [
        (
            "defensia_rag_log",
            """DELETE FROM defensia_rag_log WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        ),
        (
            "defensia_escritos",
            """DELETE FROM defensia_escritos WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        ),
        (
            "defensia_dictamenes",
            """DELETE FROM defensia_dictamenes WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        ),
        (
            "defensia_briefs",
            """DELETE FROM defensia_briefs WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        ),
        (
            "defensia_documentos",
            """DELETE FROM defensia_documentos WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        ),
        ("defensia_expedientes", "DELETE FROM defensia_expedientes WHERE user_id = ?"),
        ("defensia_cuotas_mensuales", "DELETE FROM defensia_cuotas_mensuales WHERE user_id = ?"),
    ]
    for table_name, sql in _defensia_deletes:
        try:
            await db.execute(sql, [user_id])
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning(
                "GDPR cascade: fallo DELETE %s para user %s: %s",
                table_name,
                user_id,
                exc,
            )

    # Sessions
    await db.execute("DELETE FROM sessions WHERE user_id = ?", [user_id])

    # Finally, the user
    await db.execute("DELETE FROM users WHERE id = ?", [user_id])

    logger.info("Account deleted (GDPR Art.17) for user %s", user_id)

    return DeleteAccountResponse(
        message="Account deleted successfully. All data has been permanently removed.",
        user_id=user_id,
        deleted_at=datetime.now(UTC).isoformat() + "Z",
        data_purged={
            "conversations": conversations_count,
            "messages": messages_count,
            "sessions": sessions_count,
            "user_account": 1,
        },
    )
