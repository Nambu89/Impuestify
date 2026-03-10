"""
Fiscal Profile Update Tool

Allows the AI agent to update the user's fiscal profile with data
extracted from documents (payslips, invoices) or conversation context.
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)

UPDATE_FISCAL_PROFILE_TOOL = {
    "type": "function",
    "function": {
        "name": "update_fiscal_profile",
        "description": (
            "Actualiza el perfil fiscal del usuario en la base de datos. "
            "SOLO usar cuando el usuario EXPLICITAMENTE pida guardar, actualizar o rellenar su perfil fiscal. "
            "Ejemplos: 'rellena mi perfil', 'guarda estos datos en mi perfil', 'actualiza mi perfil fiscal'. "
            "NO usar para responder preguntas sobre deducciones, IRPF, impuestos o analisis de documentos. "
            "Para preguntas fiscales usa las otras herramientas (discover_deductions, simulate_irpf, etc.)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ingresos_trabajo": {
                    "type": "number",
                    "description": "Ingresos brutos anuales del trabajo (EUR/ano)"
                },
                "ss_empleado": {
                    "type": "number",
                    "description": "Cotizacion SS empleado anual (EUR/ano)"
                },
                "retenciones_trabajo": {
                    "type": "number",
                    "description": "Retenciones IRPF anuales sobre trabajo (EUR/ano)"
                },
                "situacion_laboral": {
                    "type": "string",
                    "enum": ["empleado", "autonomo", "desempleado", "pensionista", "estudiante"],
                    "description": "Situacion laboral del contribuyente"
                },
                "estado_civil": {
                    "type": "string",
                    "enum": ["soltero", "casado", "divorciado", "viudo", "pareja_de_hecho"],
                    "description": "Estado civil"
                },
                "num_descendientes": {
                    "type": "integer",
                    "description": "Numero de descendientes a cargo"
                },
                "intereses": {
                    "type": "number",
                    "description": "Intereses de cuentas/depositos (EUR)"
                },
                "dividendos": {
                    "type": "number",
                    "description": "Dividendos recibidos (EUR)"
                },
                "ingresos_alquiler": {
                    "type": "number",
                    "description": "Ingresos por alquiler (EUR/ano)"
                },
                "aportaciones_plan_pensiones": {
                    "type": "number",
                    "description": "Aportaciones a plan de pensiones (EUR/ano)"
                },
                "base_cotizacion_reta": {
                    "type": "number",
                    "description": "Base de cotizacion RETA para autonomos (EUR/mes)"
                },
                "rendimientos_netos_mensuales": {
                    "type": "number",
                    "description": "Rendimientos netos mensuales estimados para autonomos (EUR)"
                },
                "tipo_retencion_facturas": {
                    "type": "number",
                    "description": "Tipo de retencion en facturas para autonomos (%)"
                },
            },
            "required": [],
        },
    },
}


async def update_fiscal_profile_tool(user_id: str, db_client: Any, **kwargs) -> Dict[str, Any]:
    """
    Update the user's fiscal profile with the provided fields.
    Merges with existing data, marks source as 'agent'.
    """
    if not kwargs:
        return {"success": False, "error": "No se proporcionaron campos para actualizar"}

    now = datetime.utcnow().isoformat()

    try:
        # Load existing profile
        existing = await db_client.execute(
            "SELECT id, datos_fiscales, ccaa_residencia, situacion_laboral FROM user_profiles WHERE user_id = ?",
            [user_id]
        )

        datos_fiscales = {}
        profile_exists = bool(existing.rows)

        if profile_exists:
            raw = existing.rows[0].get("datos_fiscales")
            if raw:
                try:
                    datos_fiscales = json.loads(raw) if isinstance(raw, str) else raw
                except (json.JSONDecodeError, TypeError):
                    datos_fiscales = {}

        # Top-level column fields
        top_level_fields = {"situacion_laboral"}

        # Merge new values
        updated_keys = []
        top_level_updates = {}

        for key, value in kwargs.items():
            if value is None:
                continue

            if key in top_level_fields:
                top_level_updates[key] = value

            # All fields also go into datos_fiscales JSON
            datos_fiscales[key] = {
                "value": value,
                "_source": "agent",
                "_updated": now,
            }
            updated_keys.append(key)

        if not updated_keys:
            return {"success": False, "error": "No se proporcionaron campos validos"}

        datos_json = json.dumps(datos_fiscales, ensure_ascii=False)

        if profile_exists:
            # Build dynamic UPDATE
            set_parts = ["datos_fiscales = ?", "updated_at = datetime('now')"]
            params = [datos_json]

            if "situacion_laboral" in top_level_updates:
                set_parts.append("situacion_laboral = ?")
                params.append(top_level_updates["situacion_laboral"])

            params.append(user_id)
            sql = f"UPDATE user_profiles SET {', '.join(set_parts)} WHERE user_id = ?"
            await db_client.execute(sql, params)
        else:
            import uuid
            profile_id = str(uuid.uuid4())
            await db_client.execute(
                """INSERT INTO user_profiles (id, user_id, datos_fiscales, situacion_laboral, created_at, updated_at)
                   VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
                [profile_id, user_id, datos_json, top_level_updates.get("situacion_laboral")]
            )

        logger.info(f"Fiscal profile updated for user {user_id}: {updated_keys}")
        return {
            "success": True,
            "updated_fields": updated_keys,
            "message": f"Perfil fiscal actualizado: {', '.join(updated_keys)}"
        }

    except Exception as e:
        logger.error(f"Error updating fiscal profile: {e}")
        return {"success": False, "error": str(e)}
