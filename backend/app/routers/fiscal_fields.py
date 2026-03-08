"""
Fiscal Profile Fields Endpoint.

GET /api/fiscal-profile/fields?ccaa={ccaa}

Returns the structured list of sections and fields needed for the fiscal profile
of a given CCAA. Sections adapt dynamically:
- Base sections: always present (datos_personales, rendimientos, familia, etc.)
- Conditional sections: foral_vasco, foral_navarra, ceuta_melilla, canarias, autonomo
- deducciones_autonomicas: queried live from the deductions DB for the given CCAA
"""
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from app.auth.jwt_handler import get_current_user, TokenData
from app.database.turso_client import get_db_client, TursoClient
from app.utils.regime_classifier import classify_regime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fiscal-profile", tags=["fiscal-profile"])


# ---------------------------------------------------------------------------
# Base sections — always present regardless of CCAA
# ---------------------------------------------------------------------------

_BASE_SECTIONS: List[Dict[str, Any]] = [
    {
        "id": "datos_personales",
        "title": "Datos personales",
        "fields": [
            {"key": "fecha_nacimiento", "label": "Fecha de nacimiento", "type": "date", "required": False},
            {"key": "situacion_laboral", "label": "Situacion laboral", "type": "select",
             "options": ["empleado", "autonomo", "desempleado", "pensionista", "estudiante"], "required": False},
            {"key": "estado_civil", "label": "Estado civil", "type": "select",
             "options": ["soltero", "casado", "divorciado", "viudo", "pareja_de_hecho"], "required": False},
        ]
    },
    {
        "id": "rendimientos_trabajo",
        "title": "Rendimientos del trabajo",
        "fields": [
            {"key": "ingresos_trabajo", "label": "Ingresos brutos del trabajo (EUR/ano)", "type": "float", "required": False},
            {"key": "ss_empleado", "label": "Cotizacion SS empleado (EUR/ano)", "type": "float", "required": False},
            {"key": "retenciones_trabajo", "label": "Retenciones IRPF trabajo (EUR/ano)", "type": "float", "required": False},
        ]
    },
    {
        "id": "rendimientos_ahorro",
        "title": "Rendimientos del ahorro e inversiones",
        "fields": [
            {"key": "intereses", "label": "Intereses cuentas/depositos (EUR)", "type": "float", "required": False},
            {"key": "dividendos", "label": "Dividendos (EUR)", "type": "float", "required": False},
            {"key": "ganancias_fondos", "label": "Ganancias patrimoniales fondos/acciones (EUR)", "type": "float", "required": False},
            {"key": "retenciones_ahorro", "label": "Retenciones sobre ahorro (EUR)", "type": "float", "required": False},
        ]
    },
    {
        "id": "inmuebles",
        "title": "Inmuebles",
        "fields": [
            {"key": "ingresos_alquiler", "label": "Ingresos por alquiler (EUR/ano)", "type": "float", "required": False},
            {"key": "valor_adquisicion_inmueble", "label": "Valor de adquisicion del inmueble (EUR)", "type": "float", "required": False},
            {"key": "retenciones_alquiler", "label": "Retenciones sobre alquiler (EUR)", "type": "float", "required": False},
        ]
    },
    {
        "id": "familia",
        "title": "Situacion familiar y descendientes",
        "fields": [
            {"key": "num_descendientes", "label": "Numero de descendientes a cargo", "type": "int", "required": False},
            {"key": "anios_nacimiento_desc", "label": "Anos de nacimiento de los descendientes", "type": "list_int", "required": False},
            {"key": "custodia_compartida", "label": "Custodia compartida", "type": "bool", "required": False},
            {"key": "num_ascendientes_65", "label": "Ascendientes mayores de 65 anos a cargo", "type": "int", "required": False},
            {"key": "num_ascendientes_75", "label": "Ascendientes mayores de 75 anos a cargo", "type": "int", "required": False},
            {"key": "discapacidad_contribuyente", "label": "Grado de discapacidad del contribuyente (%)", "type": "int", "required": False},
            {"key": "familia_numerosa", "label": "Familia numerosa", "type": "bool", "required": False},
            {"key": "tipo_familia_numerosa", "label": "Tipo de familia numerosa", "type": "select",
             "options": ["general", "especial"], "required": False},
            # New family fields (Sprint 1)
            {"key": "nacimiento_adopcion_reciente", "label": "Nacimiento o adopcion en el ultimo ano", "type": "bool", "required": False},
            {"key": "adopcion_internacional", "label": "Adopcion internacional", "type": "bool", "required": False},
            {"key": "acogimiento_familiar", "label": "Acogimiento familiar", "type": "bool", "required": False},
            {"key": "familia_monoparental", "label": "Familia monoparental", "type": "bool", "required": False},
            {"key": "hijos_escolarizados", "label": "Hijos en edad escolar (3-16 anos)", "type": "bool", "required": False},
            {"key": "gastos_guarderia", "label": "Gastos de guarderia o centro de educacion infantil", "type": "bool", "required": False},
            {"key": "ambos_progenitores_trabajan", "label": "Ambos progenitores trabajan y cotizan a SS", "type": "bool", "required": False},
            {"key": "hijos_estudios_universitarios", "label": "Hijos cursando estudios universitarios", "type": "bool", "required": False},
        ]
    },
    {
        "id": "discapacidad",
        "title": "Discapacidad de familiares",
        "fields": [
            {"key": "descendiente_discapacidad", "label": "Descendiente con discapacidad >= 33%", "type": "bool", "required": False},
            {"key": "ascendiente_discapacidad", "label": "Ascendiente con discapacidad >= 33%", "type": "bool", "required": False},
            {"key": "ascendiente_a_cargo", "label": "Ascendiente a cargo del contribuyente", "type": "bool", "required": False},
            {"key": "familiar_discapacitado_cargo", "label": "Familiar discapacitado a cargo (no descendiente/ascendiente)", "type": "bool", "required": False},
            {"key": "empleada_hogar_cuidado", "label": "Empleada del hogar para cuidado de familiar", "type": "bool", "required": False},
        ]
    },
    {
        "id": "reducciones",
        "title": "Reducciones y deducciones basicas",
        "fields": [
            {"key": "aportaciones_plan_pensiones", "label": "Aportaciones propias a plan de pensiones (EUR/ano)", "type": "float", "required": False},
            {"key": "aportaciones_plan_pensiones_empresa", "label": "Aportaciones empresa a plan de pensiones (EUR/ano)", "type": "float", "required": False},
            {"key": "hipoteca_pre2013", "label": "Hipoteca sobre vivienda habitual adquirida antes de 2013", "type": "bool", "required": False},
            {"key": "capital_amortizado_hipoteca", "label": "Capital amortizado hipoteca (EUR/ano)", "type": "float", "required": False},
            {"key": "intereses_hipoteca", "label": "Intereses hipoteca pagados (EUR/ano)", "type": "float", "required": False},
            {"key": "madre_trabajadora_ss", "label": "Madre trabajadora dada de alta en SS", "type": "bool", "required": False},
            {"key": "gastos_guarderia_anual", "label": "Gastos guarderia o educacion infantil (EUR/ano)", "type": "float", "required": False},
            {"key": "donativos_ley_49_2002", "label": "Donativos a entidades Ley 49/2002 (EUR/ano)", "type": "float", "required": False},
            {"key": "donativo_recurrente", "label": "Donativo recurrente (mismo organismo 3+ anos)", "type": "bool", "required": False},
        ]
    },
    {
        "id": "vivienda",
        "title": "Vivienda",
        "fields": [
            {"key": "alquiler_vivienda_habitual", "label": "Paga alquiler por vivienda habitual", "type": "bool", "required": False},
            {"key": "importe_alquiler_anual", "label": "Importe anual del alquiler (EUR)", "type": "float", "required": False},
            {"key": "vivienda_habitual_propiedad", "label": "Vivienda habitual en propiedad", "type": "bool", "required": False},
            {"key": "rehabilitacion_vivienda", "label": "Obras de rehabilitacion de vivienda habitual", "type": "bool", "required": False},
            {"key": "vivienda_rural", "label": "Vivienda en municipio rural o en riesgo de despoblacion", "type": "bool", "required": False},
            {"key": "dacion_pago_alquiler", "label": "Dacion en pago o alquiler social por impago hipoteca", "type": "bool", "required": False},
            {"key": "arrendador_vivienda_social", "label": "Arrendador de vivienda social o a precio reducido", "type": "bool", "required": False},
        ]
    },
    {
        "id": "sostenibilidad",
        "title": "Sostenibilidad y movilidad",
        "fields": [
            {"key": "vehiculo_electrico_nuevo", "label": "Adquisicion de vehiculo electrico nuevo", "type": "bool", "required": False},
            {"key": "obras_mejora_energetica", "label": "Obras de mejora de eficiencia energetica en vivienda", "type": "bool", "required": False},
            {"key": "instalacion_renovable", "label": "Instalacion de paneles solares u otras energias renovables", "type": "bool", "required": False},
        ]
    },
    {
        "id": "donaciones",
        "title": "Donaciones",
        "fields": [
            {"key": "donativo_entidad_autonomica", "label": "Donativo a entidad declarada de interes autonómico", "type": "bool", "required": False},
            {"key": "donativo_investigacion", "label": "Donativo a entidades de investigacion o innovacion", "type": "bool", "required": False},
            {"key": "donativo_patrimonio", "label": "Donativo de bienes al patrimonio historico artistico", "type": "bool", "required": False},
            {"key": "donativo_fundacion_local", "label": "Donativo a fundacion o asociacion local declarada de interes general", "type": "bool", "required": False},
        ]
    },
    {
        "id": "territorio",
        "title": "Situacion territorial especial",
        "fields": [
            {"key": "municipio_despoblado", "label": "Reside en municipio en riesgo de despoblacion", "type": "bool", "required": False},
            {"key": "inversion_empresa_nueva", "label": "Ha invertido en empresa de nueva creacion", "type": "bool", "required": False},
        ]
    },
]

# ---------------------------------------------------------------------------
# Conditional section builders
# ---------------------------------------------------------------------------

def _section_actividad_economica() -> Dict[str, Any]:
    return {
        "id": "actividad_economica",
        "title": "Actividad economica (Autonomo)",
        "condition": "situacion_laboral=autonomo",
        "fields": [
            {"key": "epigrafe_iae", "label": "Epigrafe IAE de la actividad", "type": "str", "required": False},
            {"key": "tipo_actividad", "label": "Tipo de actividad", "type": "select",
             "options": ["profesional", "empresarial", "artistica"], "required": False},
            {"key": "fecha_alta_autonomo", "label": "Fecha de alta como autonomo", "type": "date", "required": False},
            {"key": "metodo_estimacion_irpf", "label": "Metodo de estimacion IRPF", "type": "select",
             "options": ["directa_normal", "directa_simplificada", "objetiva"], "required": False},
            {"key": "regimen_iva", "label": "Regimen de IVA", "type": "select",
             "options": ["general", "simplificado", "recargo_equivalencia", "exento", "ipsi"], "required": False},
            {"key": "rendimientos_netos_mensuales", "label": "Rendimientos netos mensuales estimados (EUR)", "type": "float", "required": False},
            {"key": "base_cotizacion_reta", "label": "Base de cotizacion RETA (EUR/mes)", "type": "float", "required": False},
            {"key": "tipo_retencion_facturas", "label": "Tipo de retencion en facturas (%)", "type": "float", "required": False},
            {"key": "tarifa_plana", "label": "Acogido a tarifa plana de autónomos", "type": "bool", "required": False},
            {"key": "pluriactividad", "label": "Pluriactividad (autonomo + por cuenta ajena)", "type": "bool", "required": False},
        ]
    }


def _section_foral_vasco() -> Dict[str, Any]:
    return {
        "id": "prevision_social_foral",
        "title": "Prevision social foral (Pais Vasco)",
        "condition": "ccaa=Araba|Bizkaia|Gipuzkoa",
        "fields": [
            {"key": "epsv_aportaciones", "label": "Aportaciones a EPSV (EUR/ano)", "type": "float", "required": False},
            {"key": "pension_viudedad", "label": "Percibe pension de viudedad", "type": "bool", "required": False},
            {"key": "reduccion_jornada_cuidado", "label": "Reduccion de jornada por cuidado de familiar", "type": "bool", "required": False},
            {"key": "cuenta_vivienda_aportaciones", "label": "Aportaciones a cuenta vivienda foral (EUR/ano)", "type": "float", "required": False},
        ]
    }


def _section_foral_navarra() -> Dict[str, Any]:
    return {
        "id": "prevision_social_navarra",
        "title": "Prevision social foral (Navarra)",
        "condition": "ccaa=Navarra",
        "fields": [
            {"key": "epsv_aportaciones", "label": "Aportaciones a planes de prevision social navarros (EUR/ano)", "type": "float", "required": False},
            {"key": "pension_viudedad", "label": "Percibe pension de viudedad", "type": "bool", "required": False},
            {"key": "reduccion_jornada_cuidado", "label": "Reduccion de jornada por cuidado (Art. 64 TRIRPFN)", "type": "bool", "required": False},
        ]
    }


def _section_ceuta_melilla() -> Dict[str, Any]:
    return {
        "id": "ceuta_melilla",
        "title": "Regimen especial Ceuta / Melilla",
        "condition": "ccaa=Ceuta|Melilla",
        "fields": [
            {"key": "ceuta_melilla", "label": "Residente fiscal en Ceuta o Melilla (deduccion 60% cuota IRPF)", "type": "bool", "required": False},
            {"key": "regimen_iva", "label": "Tipo impositivo IPSI aplicable", "type": "select",
             "options": ["0.5", "1.0", "2.0", "4.0", "8.0", "10.0"], "required": False},
        ]
    }


def _section_canarias() -> Dict[str, Any]:
    return {
        "id": "canarias",
        "title": "Regimen especial Canarias",
        "condition": "ccaa=Canarias",
        "fields": [
            {"key": "regimen_iva", "label": "Regimen IGIC", "type": "select",
             "options": ["general", "simplificado", "exento"], "required": False},
        ]
    }


# ---------------------------------------------------------------------------
# DB-backed deducciones_autonomicas section
# ---------------------------------------------------------------------------

async def _build_deducciones_section(ccaa: str, db: TursoClient) -> Optional[Dict[str, Any]]:
    """
    Build the deducciones_autonomicas section by reading unique requirement keys
    from the deductions table for this CCAA, grouped by category.

    Returns None if there are no territorial deductions for this CCAA.
    """
    try:
        result = await db.execute(
            """SELECT name, category, requirements_json, questions_json
               FROM deductions
               WHERE territory = ? AND is_active = 1 AND tax_year = 2025
               ORDER BY category, name""",
            [ccaa],
        )
    except Exception:
        # If deductions table unavailable, skip silently
        return None

    if not result.rows:
        return None

    # Collect unique question keys (from questions_json) grouped by category
    category_fields: Dict[str, List[Dict[str, Any]]] = {}
    seen_keys: set = set()

    for row in result.rows:
        category = row.get("category") or "general"
        questions_raw = row.get("questions_json")
        questions = []
        if questions_raw:
            try:
                questions = json.loads(questions_raw) if isinstance(questions_raw, str) else questions_raw
            except (json.JSONDecodeError, TypeError):
                questions = []

        for q in questions:
            key = q.get("key")
            if not key or key in seen_keys:
                continue
            seen_keys.add(key)

            field = {
                "key": key,
                "label": q.get("text", key),
                "type": q.get("type", "bool"),
                "required": False,
                "_source_ccaa": ccaa,
            }
            if q.get("type") == "select" and q.get("options"):
                field["options"] = q["options"]

            category_fields.setdefault(category, []).append(field)

    if not category_fields:
        return None

    # Flatten into a single list with category metadata
    all_fields: List[Dict[str, Any]] = []
    for cat, fields in category_fields.items():
        for f in fields:
            f["_category"] = cat
            all_fields.append(f)

    return {
        "id": "deducciones_autonomicas",
        "title": f"Deducciones autonomicas ({ccaa})",
        "condition": f"ccaa={ccaa}",
        "fields": all_fields,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/fields")
async def get_fiscal_profile_fields(
    ccaa: str = Query(default="", description="Comunidad Autonoma del contribuyente"),
    situacion_laboral: str = Query(default="", description="situacion_laboral del perfil: empleado|autonomo|..."),
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> Dict[str, Any]:
    """
    Return the structured list of fiscal-profile sections and fields for a given CCAA.

    The response adapts dynamically:
    - `regime`: fiscal regime classification
    - `sections`: ordered list of section objects, each with `id`, `title`, `fields`

    Conditional sections are included when applicable (foral, Ceuta/Melilla, autonomo, etc.).
    The `deducciones_autonomicas` section is built live from the deductions DB.
    """
    regime = classify_regime(ccaa) if ccaa else "comun"

    sections: List[Dict[str, Any]] = list(_BASE_SECTIONS)

    # --- Conditional: actividad_economica (autonomo) ---
    if situacion_laboral == "autonomo" or situacion_laboral == "":
        # Always include so frontend can show/hide based on profile
        sections.append(_section_actividad_economica())

    # --- Regime-specific sections ---
    if regime == "foral_vasco":
        sections.append(_section_foral_vasco())
    elif regime == "foral_navarra":
        sections.append(_section_foral_navarra())
    elif regime == "ceuta_melilla":
        sections.append(_section_ceuta_melilla())
    elif regime == "canarias":
        sections.append(_section_canarias())

    # --- deducciones_autonomicas from DB ---
    if ccaa:
        ded_section = await _build_deducciones_section(ccaa, db)
        if ded_section:
            sections.append(ded_section)

    # --- Workspace data hint ---
    try:
        from app.services.workspace_service import workspace_service
        ws_summary = await workspace_service.get_fiscal_summary_from_workspace(current_user.user_id)
    except Exception:
        ws_summary = {"has_data": False}

    return {
        "ccaa": ccaa or None,
        "regime": regime,
        "sections": sections,
        "workspace_data": ws_summary,
    }
