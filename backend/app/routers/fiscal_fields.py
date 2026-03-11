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
# Text cleanup for DB-sourced question labels (fixes seed spelling errors)
# ---------------------------------------------------------------------------

_TEXT_REPLACEMENTS = [
    # "anyo" / "ano" → "año"
    ("anyo", "año"),
    ("ano ", "año "),
    ("ano?", "año?"),
    ("anos", "años"),
    # Missing accents
    ("Cuanto ", "¿Cuánto "),
    ("Cuantos ", "¿Cuántos "),
    ("Estan ", "¿Están "),
    ("Basica", "Básica"),
    ("maximo", "máximo"),
    ("Maximo", "Máximo"),
    ("animo", "ánimo"),
    ("costo ", "costó "),
    ("Deduccion ", "Deducción "),
    ("deduccion ", "deducción "),
    ("adopcion", "adopción"),
    ("Adopcion", "Adopción"),
    ("educacion", "educación"),
    ("reduccion", "reducción"),
    ("Reduccion", "Reducción"),
    ("Prevision", "Previsión"),
    ("prevision", "previsión"),
    ("pension ", "pensión "),
    ("Codigo", "Código"),
    ("guarderia", "guardería"),
    ("regimen ", "régimen "),
    ("comun", "común"),
    ("adquisicion", "adquisición"),
]


def _fix_text(text: str) -> str:
    """Fix common spelling errors in DB-sourced question labels."""
    if not text:
        return text
    # Add missing opening ¿ if text starts with a question word and ends with ?
    for old, new in _TEXT_REPLACEMENTS:
        text = text.replace(old, new)
    # Ensure questions have opening ¿
    if text.endswith("?") and "¿" not in text:
        text = "¿" + text
    return text


# ---------------------------------------------------------------------------
# Base sections — always present regardless of CCAA
# ---------------------------------------------------------------------------

_BASE_SECTIONS: List[Dict[str, Any]] = [
    {
        "id": "datos_personales",
        "title": "Datos personales",
        "fields": [
            {"key": "fecha_nacimiento", "label": "Fecha de nacimiento", "type": "date", "required": False},
            {"key": "situacion_laboral", "label": "Situación laboral", "type": "select",
             "options": ["empleado", "autonomo", "desempleado", "pensionista", "estudiante"],
             "option_labels": ["Empleado/a", "Autónomo/a", "Desempleado/a", "Pensionista", "Estudiante"],
             "required": False},
            {"key": "estado_civil", "label": "Estado civil", "type": "select",
             "options": ["soltero", "casado", "divorciado", "viudo", "pareja_de_hecho"],
             "option_labels": ["Soltero/a", "Casado/a", "Divorciado/a", "Viudo/a", "Pareja de hecho"],
             "required": False},
        ]
    },
    {
        "id": "rendimientos_trabajo",
        "title": "Rendimientos del trabajo",
        "fields": [
            {"key": "ingresos_trabajo", "label": "Ingresos brutos del trabajo (EUR/año)", "type": "float", "required": False},
            {"key": "ss_empleado", "label": "Cotización SS empleado (EUR/año)", "type": "float", "required": False},
            {"key": "retenciones_trabajo", "label": "Retenciones IRPF trabajo (EUR/año)", "type": "float", "required": False},
        ]
    },
    {
        "id": "rendimientos_ahorro",
        "title": "Rendimientos del ahorro e inversiones",
        "fields": [
            {"key": "intereses", "label": "Intereses cuentas/depósitos (EUR)", "type": "float", "required": False},
            {"key": "dividendos", "label": "Dividendos (EUR)", "type": "float", "required": False},
            {"key": "ganancias_fondos", "label": "Ganancias patrimoniales fondos/acciones (EUR)", "type": "float", "required": False},
            {"key": "retenciones_ahorro", "label": "Retenciones sobre ahorro (EUR)", "type": "float", "required": False},
        ]
    },
    {
        "id": "inmuebles",
        "title": "Inmuebles",
        "fields": [
            {"key": "ingresos_alquiler", "label": "Ingresos por alquiler (EUR/año)", "type": "float", "required": False},
            {"key": "valor_adquisicion_inmueble", "label": "Valor de adquisición del inmueble (EUR)", "type": "float", "required": False},
            {"key": "retenciones_alquiler", "label": "Retenciones sobre alquiler (EUR)", "type": "float", "required": False},
        ]
    },
    {
        "id": "familia",
        "title": "Situación familiar y descendientes",
        "fields": [
            {"key": "num_descendientes", "label": "Número de descendientes a cargo", "type": "int", "required": False},
            {"key": "anios_nacimiento_desc", "label": "Años de nacimiento de los descendientes", "type": "list_int", "required": False},
            {"key": "custodia_compartida", "label": "Custodia compartida", "type": "bool", "required": False},
            {"key": "num_ascendientes_65", "label": "Ascendientes mayores de 65 años a cargo", "type": "int", "required": False},
            {"key": "num_ascendientes_75", "label": "Ascendientes mayores de 75 años a cargo", "type": "int", "required": False},
            {"key": "discapacidad_contribuyente", "label": "Grado de discapacidad del contribuyente (%)", "type": "int", "required": False},
            {"key": "familia_numerosa", "label": "Familia numerosa", "type": "bool", "required": False},
            {"key": "tipo_familia_numerosa", "label": "Tipo de familia numerosa", "type": "select",
             "options": ["general", "especial"],
             "option_labels": ["General (3-4 hijos)", "Especial (5+ hijos)"],
             "required": False},
            {"key": "nacimiento_adopcion_reciente", "label": "Nacimiento o adopción en el último año", "type": "bool", "required": False},
            {"key": "adopcion_internacional", "label": "Adopción internacional", "type": "bool", "required": False},
            {"key": "acogimiento_familiar", "label": "Acogimiento familiar", "type": "bool", "required": False},
            {"key": "familia_monoparental", "label": "Familia monoparental", "type": "bool", "required": False},
            {"key": "hijos_escolarizados", "label": "Hijos en edad escolar (3-16 años)", "type": "bool", "required": False},
            {"key": "gastos_guarderia", "label": "Gastos de guardería o centro de educación infantil", "type": "bool", "required": False},
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
        "title": "Reducciones y deducciones básicas",
        "fields": [
            {"key": "aportaciones_plan_pensiones", "label": "Aportaciones propias a plan de pensiones (EUR/año)", "type": "float", "required": False},
            {"key": "aportaciones_plan_pensiones_empresa", "label": "Aportaciones empresa a plan de pensiones (EUR/año)", "type": "float", "required": False},
            {"key": "hipoteca_pre2013", "label": "Hipoteca sobre vivienda habitual adquirida antes de 2013", "type": "bool", "required": False},
            {"key": "capital_amortizado_hipoteca", "label": "Capital amortizado hipoteca (EUR/año)", "type": "float", "required": False},
            {"key": "intereses_hipoteca", "label": "Intereses hipoteca pagados (EUR/año)", "type": "float", "required": False},
            {"key": "madre_trabajadora_ss", "label": "Madre trabajadora dada de alta en SS", "type": "bool", "required": False},
            {"key": "gastos_guarderia_anual", "label": "Gastos guardería o educación infantil (EUR/año)", "type": "float", "required": False},
            {"key": "donativos_ley_49_2002", "label": "Donativos a entidades Ley 49/2002 (EUR/año)", "type": "float", "required": False},
            {"key": "donativo_recurrente", "label": "Donativo recurrente (mismo organismo 3+ años)", "type": "bool", "required": False},
        ]
    },
    {
        "id": "vivienda",
        "title": "Vivienda",
        "fields": [
            {"key": "alquiler_vivienda_habitual", "label": "Paga alquiler por vivienda habitual", "type": "bool", "required": False},
            {"key": "importe_alquiler_anual", "label": "Importe anual del alquiler (EUR)", "type": "float", "required": False},
            {"key": "vivienda_habitual_propiedad", "label": "Vivienda habitual en propiedad", "type": "bool", "required": False},
            {"key": "rehabilitacion_vivienda", "label": "Obras de rehabilitación de vivienda habitual", "type": "bool", "required": False},
            {"key": "vivienda_rural", "label": "Vivienda en municipio rural o en riesgo de despoblación", "type": "bool", "required": False},
            {"key": "dacion_pago_alquiler", "label": "Dación en pago o alquiler social por impago hipoteca", "type": "bool", "required": False},
            {"key": "arrendador_vivienda_social", "label": "Arrendador de vivienda social o a precio reducido", "type": "bool", "required": False},
        ]
    },
    {
        "id": "sostenibilidad",
        "title": "Sostenibilidad y movilidad",
        "fields": [
            {"key": "vehiculo_electrico_nuevo", "label": "Adquisición de vehículo eléctrico nuevo", "type": "bool", "required": False},
            {"key": "obras_mejora_energetica", "label": "Obras de mejora de eficiencia energética en vivienda", "type": "bool", "required": False},
            {"key": "instalacion_renovable", "label": "Instalación de paneles solares u otras energías renovables", "type": "bool", "required": False},
        ]
    },
    {
        "id": "donaciones",
        "title": "Donaciones",
        "fields": [
            {"key": "donativo_entidad_autonomica", "label": "Donativo a entidad declarada de interés autonómico", "type": "bool", "required": False},
            {"key": "donativo_investigacion", "label": "Donativo a entidades de investigación o innovación", "type": "bool", "required": False},
            {"key": "donativo_patrimonio", "label": "Donativo de bienes al patrimonio histórico artístico", "type": "bool", "required": False},
            {"key": "donativo_fundacion_local", "label": "Donativo a fundación o asociación local declarada de interés general", "type": "bool", "required": False},
        ]
    },
    {
        "id": "territorio",
        "title": "Situación territorial especial",
        "fields": [
            {"key": "municipio_despoblado", "label": "Reside en municipio en riesgo de despoblación", "type": "bool", "required": False},
            {"key": "inversion_empresa_nueva", "label": "Ha invertido en empresa de nueva creación", "type": "bool", "required": False},
        ]
    },
    {
        "id": "criptomonedas",
        "title": "Criptomonedas y monedas virtuales",
        "description": "Casillas 1800-1814 del Modelo 100",
        "fields": [
            {"key": "tiene_criptomonedas", "label": "¿Has transmitido monedas virtuales en el ejercicio?", "type": "bool", "required": False},
            {"key": "cripto_denominaciones", "label": "Monedas virtuales transmitidas (BTC, ETH, SOL...)", "type": "str", "required": False,
             "hint": "Casilla 1802 — Denominación de la moneda virtual"},
            {"key": "cripto_clave_contraprestacion", "label": "Tipo de contraprestación recibida", "type": "select",
             "options": ["F", "N", "O", "B"],
             "option_labels": ["Moneda de curso legal (EUR, USD...)", "Otra moneda virtual (cripto a cripto)", "Otro activo virtual (NFT, token)", "Bienes o servicios"],
             "required": False,
             "hint": "Casilla 1803"},
            {"key": "cripto_valor_transmision_total", "label": "Valor total de transmisión (EUR)", "type": "float", "required": False,
             "hint": "Suma casilla 1804"},
            {"key": "cripto_valor_adquisicion_total", "label": "Valor total de adquisición (EUR)", "type": "float", "required": False,
             "hint": "Suma casilla 1806"},
            {"key": "cripto_ganancia_neta", "label": "Ganancia patrimonial neta por criptomonedas (EUR)", "type": "float", "required": False,
             "hint": "Casilla 1814 — suma ganancias"},
            {"key": "cripto_perdida_neta", "label": "Pérdida patrimonial neta por criptomonedas (EUR)", "type": "float", "required": False,
             "hint": "Casilla 1813 — suma pérdidas"},
            {"key": "cripto_en_extranjero_50k", "label": "¿Tienes saldo en exchanges extranjeros > 50.000 EUR al 31/dic?", "type": "bool", "required": False,
             "hint": "Obligación Modelo 721"},
            {"key": "tiene_staking_defi", "label": "¿Tienes ingresos por staking, DeFi, lending o minería?", "type": "bool", "required": False,
             "hint": "Sin casilla propia — tributa como rendimiento de capital mobiliario o actividad económica"},
            {"key": "exchanges_utilizados", "label": "Exchanges utilizados (Binance, Coinbase...)", "type": "str", "required": False},
        ]
    },
    {
        "id": "apuestas_juegos",
        "title": "Premios, apuestas y juegos",
        "description": "Casillas 0281-0297 del Modelo 100",
        "fields": [
            # --- Juegos privados (casillas 0281-0290) ---
            {"key": "tiene_ganancias_juegos_privados", "label": "¿Has tenido premios en juegos, apuestas o concursos?", "type": "bool", "required": False,
             "hint": "Casillas 0281-0290 — Juegos no organizados por el Estado"},
            {"key": "premios_metalico_privados", "label": "Premios en metálico de juegos/apuestas (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0282"},
            {"key": "premios_especie_privados", "label": "Premios en especie — valoración (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0283"},
            {"key": "perdidas_juegos_privados", "label": "Pérdidas patrimoniales en juegos/apuestas (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0287 — compensan las ganancias del mismo tipo"},
            # --- Loterías y juegos públicos (casillas 0291-0297) ---
            {"key": "tiene_premios_loterias", "label": "¿Has tenido premios de loterías del Estado, ONCE o Cruz Roja?", "type": "bool", "required": False,
             "hint": "Casillas 0291-0297 — Juegos organizados por organismos públicos"},
            {"key": "premios_metalico_publicos", "label": "Premios en metálico de loterías públicas (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0292 — exentos los primeros 40.000 EUR"},
            {"key": "premios_especie_publicos", "label": "Premios en especie de loterías públicas — valoración (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0293"},
        ]
    },
    {
        "id": "ganancias_patrimoniales_financieras",
        "title": "Ganancias patrimoniales por inversiones financieras",
        "description": "Casillas 0316-0354 del Modelo 100",
        "fields": [
            # --- Fondos de inversión (GPFondos, casillas 0316-0320) ---
            {"key": "tiene_fondos_inversion", "label": "¿Has reembolsado participaciones en fondos de inversión?", "type": "bool", "required": False,
             "hint": "Casillas 0316-0320"},
            {"key": "ganancias_reembolso_fondos", "label": "Ganancias por reembolso de fondos (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0320 — ganancia patrimonial"},
            {"key": "perdidas_reembolso_fondos", "label": "Pérdidas por reembolso de fondos (EUR)", "type": "float", "required": False},
            # --- Acciones y participaciones (GPAcciones, casillas 0332-0339) ---
            {"key": "tiene_acciones", "label": "¿Has vendido acciones o participaciones?", "type": "bool", "required": False,
             "hint": "Casillas 0332-0339"},
            {"key": "ganancias_acciones", "label": "Ganancias por venta de acciones (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0338"},
            {"key": "perdidas_acciones", "label": "Pérdidas por venta de acciones (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0339"},
            # --- Derivados/CFDs/Forex (GPDerechos, casillas 0347-0354) ---
            {"key": "tiene_derivados", "label": "¿Has operado con derivados, CFDs o Forex?", "type": "bool", "required": False,
             "hint": "Casillas 0347-0354 — Derechos y participaciones"},
            {"key": "ganancias_derivados", "label": "Ganancias por derivados/CFDs/Forex (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0353"},
            {"key": "perdidas_derivados", "label": "Pérdidas por derivados/CFDs/Forex (EUR)", "type": "float", "required": False,
             "hint": "Casilla 0354"},
        ]
    },
]

# ---------------------------------------------------------------------------
# Conditional section builders
# ---------------------------------------------------------------------------

def _section_actividad_economica() -> Dict[str, Any]:
    return {
        "id": "actividad_economica",
        "title": "Actividad económica (Autónomo)",
        "condition": "situacion_laboral=autonomo",
        "fields": [
            {"key": "epigrafe_iae", "label": "Epígrafe IAE de la actividad", "type": "str", "required": False},
            {"key": "tipo_actividad", "label": "Tipo de actividad", "type": "select",
             "options": ["profesional", "empresarial", "artistica"],
             "option_labels": ["Profesional", "Empresarial", "Artística"],
             "required": False},
            {"key": "fecha_alta_autonomo", "label": "Fecha de alta como autónomo", "type": "date", "required": False},
            {"key": "metodo_estimacion_irpf", "label": "Método de estimación IRPF", "type": "select",
             "options": ["directa_normal", "directa_simplificada", "objetiva"],
             "option_labels": ["Directa normal", "Directa simplificada", "Objetiva (módulos)"],
             "required": False},
            {"key": "regimen_iva", "label": "Régimen de IVA", "type": "select",
             "options": ["general", "simplificado", "recargo_equivalencia", "exento", "ipsi"],
             "option_labels": ["General", "Simplificado", "Recargo de equivalencia", "Exento", "IPSI (Ceuta/Melilla)"],
             "required": False},
            {"key": "rendimientos_netos_mensuales", "label": "Rendimientos netos mensuales estimados (EUR)", "type": "float", "required": False},
            {"key": "base_cotizacion_reta", "label": "Base de cotización RETA (EUR/mes)", "type": "float", "required": False},
            {"key": "tipo_retencion_facturas", "label": "Tipo de retención en facturas (%)", "type": "select",
             "options": ["15", "7", "1", "2"],
             "option_labels": ["15% (general)", "7% (primeros 3 años)", "1% (módulos)", "2% (actividades artísticas)"],
             "required": False},
            {"key": "tarifa_plana", "label": "Acogido a tarifa plana de autónomos", "type": "bool", "required": False},
            {"key": "pluriactividad", "label": "Pluriactividad (autónomo + por cuenta ajena)", "type": "bool", "required": False},
        ]
    }


def _section_foral_vasco() -> Dict[str, Any]:
    return {
        "id": "prevision_social_foral",
        "title": "Previsión social foral (País Vasco)",
        "condition": "ccaa=Araba|Bizkaia|Gipuzkoa",
        "fields": [
            {"key": "epsv_aportaciones", "label": "Aportaciones a EPSV (EUR/año)", "type": "float", "required": False},
            {"key": "pension_viudedad", "label": "Percibe pensión de viudedad", "type": "bool", "required": False},
            {"key": "reduccion_jornada_cuidado", "label": "Reducción de jornada por cuidado de familiar", "type": "bool", "required": False},
            {"key": "cuenta_vivienda_aportaciones", "label": "Aportaciones a cuenta vivienda foral (EUR/año)", "type": "float", "required": False},
        ]
    }


def _section_foral_navarra() -> Dict[str, Any]:
    return {
        "id": "prevision_social_navarra",
        "title": "Previsión social foral (Navarra)",
        "condition": "ccaa=Navarra",
        "fields": [
            {"key": "epsv_aportaciones", "label": "Aportaciones a planes de previsión social navarros (EUR/año)", "type": "float", "required": False},
            {"key": "pension_viudedad", "label": "Percibe pensión de viudedad", "type": "bool", "required": False},
            {"key": "reduccion_jornada_cuidado", "label": "Reducción de jornada por cuidado (Art. 64 TRIRPFN)", "type": "bool", "required": False},
        ]
    }


def _section_ceuta_melilla() -> Dict[str, Any]:
    return {
        "id": "ceuta_melilla",
        "title": "Régimen especial Ceuta / Melilla",
        "condition": "ccaa=Ceuta|Melilla",
        "fields": [
            {"key": "ceuta_melilla", "label": "Residente fiscal en Ceuta o Melilla (deducción 60% cuota IRPF)", "type": "bool", "required": False},
            {"key": "regimen_iva", "label": "Tipo impositivo IPSI aplicable", "type": "select",
             "options": ["0.5", "1.0", "2.0", "4.0", "8.0", "10.0"],
             "option_labels": ["0,5%", "1%", "2%", "4%", "8%", "10%"],
             "required": False},
        ]
    }


def _section_canarias() -> Dict[str, Any]:
    return {
        "id": "canarias",
        "title": "Régimen especial Canarias",
        "condition": "ccaa=Canarias",
        "fields": [
            {"key": "regimen_iva", "label": "Régimen IGIC", "type": "select",
             "options": ["general", "simplificado", "exento"],
             "option_labels": ["General (7%)", "Simplificado", "Exento"],
             "required": False},
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
                "label": _fix_text(q.get("text", key)),
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
        "title": f"Deducciones autonómicas ({ccaa})",
        "condition": f"ccaa={ccaa}",
        "fields": all_fields,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/fields")
async def get_fiscal_profile_fields(
    ccaa: str = Query(default="", description="Comunidad Autónoma del contribuyente"),
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
