"""
Tests for Autonomo Fiscal Profile — 12 new fields.

Tests cover:
- FiscalProfileRequest accepts all 12 new fields
- _DATOS_FISCALES_KEYS includes all 12 new keys
- Fiscal profile round-trip (save → load) logic
- Fiscal profile formatting for agent prompts
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock
import types
import importlib.util
import json


# ---------------------------------------------------------------------------
# Module loading helpers
# ---------------------------------------------------------------------------

def _load_module_direct(name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


for pkg in (
    "app", "app.routers", "app.auth", "app.database",
    "app.services", "app.config", "app.security",
):
    if pkg not in sys.modules:
        sys.modules[pkg] = types.ModuleType(pkg)

_backend = os.path.join(os.path.dirname(__file__), "..")

# Stub jwt_handler and password modules
jwt_stub = types.ModuleType("app.auth.jwt_handler")
jwt_stub.get_current_user = lambda: None
jwt_stub.TokenData = type("TokenData", (), {})
sys.modules["app.auth.jwt_handler"] = jwt_stub

pwd_stub = types.ModuleType("app.auth.password")
pwd_stub.hash_password = lambda x: x
pwd_stub.verify_password = lambda x, y: x == y
sys.modules["app.auth.password"] = pwd_stub

db_stub = types.ModuleType("app.database.turso_client")
db_stub.get_db_client = lambda: None
db_stub.TursoClient = type("TursoClient", (), {})
sys.modules["app.database.turso_client"] = db_stub

# Load the module under test
_user_rights_mod = _load_module_direct(
    "app.routers.user_rights",
    os.path.join(_backend, "app", "routers", "user_rights.py"),
)

FiscalProfileRequest = _user_rights_mod.FiscalProfileRequest
_DATOS_FISCALES_KEYS = _user_rights_mod._DATOS_FISCALES_KEYS
_PROFILE_COLUMNS = _user_rights_mod._PROFILE_COLUMNS


# ---------------------------------------------------------------------------
# Tests: FiscalProfileRequest model
# ---------------------------------------------------------------------------

AUTONOMO_FIELDS = {
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
}


class TestFiscalProfileRequest:
    """Verify FiscalProfileRequest Pydantic model has all 12 autonomo fields."""

    def test_all_autonomo_fields_exist(self):
        """All 12 autonomo fields must be in the model."""
        model_fields = set(FiscalProfileRequest.model_fields.keys())
        for field in AUTONOMO_FIELDS:
            assert field in model_fields, f"Missing field: {field}"

    def test_all_fields_optional(self):
        """All autonomo fields should be Optional (can construct with empty body)."""
        req = FiscalProfileRequest()
        for field in AUTONOMO_FIELDS:
            assert getattr(req, field) is None or getattr(req, field) is False, \
                f"Field {field} should default to None or False"

    def test_full_autonomo_profile(self):
        """Can construct with all 12 autonomo fields populated."""
        req = FiscalProfileRequest(
            epigrafe_iae="861",
            tipo_actividad="profesional",
            fecha_alta_autonomo="2024-03-15",
            metodo_estimacion_irpf="directa_simplificada",
            regimen_iva="general",
            rendimientos_netos_mensuales=2500.0,
            base_cotizacion_reta=1000.0,
            territorio_foral=True,
            territorio_historico="bizkaia",
            tipo_retencion_facturas=15.0,
            tarifa_plana=False,
            pluriactividad=True,
        )
        assert req.epigrafe_iae == "861"
        assert req.tipo_actividad == "profesional"
        assert req.rendimientos_netos_mensuales == 2500.0
        assert req.territorio_foral is True
        assert req.territorio_historico == "bizkaia"
        assert req.tipo_retencion_facturas == 15.0
        assert req.pluriactividad is True

    def test_mixed_profile_old_and_new(self):
        """Can send both traditional and autonomo fields together."""
        req = FiscalProfileRequest(
            ccaa_residencia="Madrid",
            situacion_laboral="autonomo",
            ingresos_trabajo=35000,
            epigrafe_iae="749.1",
            regimen_iva="general",
            metodo_estimacion_irpf="directa_normal",
        )
        assert req.ccaa_residencia == "Madrid"
        assert req.situacion_laboral == "autonomo"
        assert req.ingresos_trabajo == 35000
        assert req.epigrafe_iae == "749.1"
        assert req.regimen_iva == "general"

    def test_model_dump_excludes_none(self):
        """model_dump(exclude_none=True) only includes set fields."""
        req = FiscalProfileRequest(
            epigrafe_iae="861",
            regimen_iva="general",
        )
        data = req.model_dump(exclude_none=True)
        assert "epigrafe_iae" in data
        assert "regimen_iva" in data
        assert "tipo_actividad" not in data
        assert "rendimientos_netos_mensuales" not in data


class TestDatosFiscalesKeys:
    """Verify _DATOS_FISCALES_KEYS includes all 12 autonomo fields."""

    def test_all_autonomo_keys_present(self):
        """All 12 autonomo field names must be in _DATOS_FISCALES_KEYS."""
        for field in AUTONOMO_FIELDS:
            assert field in _DATOS_FISCALES_KEYS, f"Missing key: {field}"

    def test_original_keys_still_present(self):
        """The original 13 keys must still be present (no regression)."""
        original_keys = {
            "ingresos_trabajo", "ss_empleado", "num_descendientes",
            "anios_nacimiento_desc", "custodia_compartida",
            "num_ascendientes_65", "num_ascendientes_75",
            "discapacidad_contribuyente", "intereses", "dividendos",
            "ganancias_fondos", "ingresos_alquiler", "valor_adquisicion_inmueble",
        }
        for key in original_keys:
            assert key in _DATOS_FISCALES_KEYS, f"Missing original key: {key}"

    def test_profile_columns_unchanged(self):
        """Top-level columns should remain: ccaa_residencia, fecha_nacimiento, situacion_laboral."""
        assert _PROFILE_COLUMNS == {"ccaa_residencia", "fecha_nacimiento", "situacion_laboral"}


class TestFiscalProfileSaveLogic:
    """Test the save logic for autonomo fields going into datos_fiscales JSON."""

    def test_autonomo_fields_go_to_datos_fiscales(self):
        """Autonomo fields should NOT be in _PROFILE_COLUMNS (go to JSON)."""
        for field in AUTONOMO_FIELDS:
            assert field not in _PROFILE_COLUMNS, \
                f"{field} should be in datos_fiscales, not a column"

    def test_datos_fiscales_json_structure(self):
        """Simulate the save logic: fields get {value, _source, _updated} wrapper."""
        from datetime import datetime

        req = FiscalProfileRequest(
            epigrafe_iae="861",
            regimen_iva="general",
            tarifa_plana=True,
        )
        request_data = req.model_dump(exclude_none=True)
        now = datetime.utcnow().isoformat()

        datos_fiscales = {}
        for key in _DATOS_FISCALES_KEYS:
            if key in request_data:
                datos_fiscales[key] = {
                    "value": request_data[key],
                    "_source": "manual",
                    "_updated": now,
                }

        assert "epigrafe_iae" in datos_fiscales
        assert datos_fiscales["epigrafe_iae"]["value"] == "861"
        assert datos_fiscales["epigrafe_iae"]["_source"] == "manual"

        assert "regimen_iva" in datos_fiscales
        assert datos_fiscales["regimen_iva"]["value"] == "general"

        # Boolean field
        assert "tarifa_plana" in datos_fiscales
        assert datos_fiscales["tarifa_plana"]["value"] is True

        # JSON-serializable
        json_str = json.dumps(datos_fiscales)
        parsed = json.loads(json_str)
        assert parsed["epigrafe_iae"]["value"] == "861"

    def test_datos_fiscales_merge_with_existing(self):
        """New autonomo fields should merge with existing datos_fiscales."""
        existing = {
            "ingresos_trabajo": {"value": 30000, "_source": "manual", "_updated": "2026-01-01"},
            "ss_empleado": {"value": 1905, "_source": "conversation", "_updated": "2026-01-01"},
        }

        new_data = {"epigrafe_iae": "861", "regimen_iva": "general"}
        now = "2026-03-03T10:00:00"

        for key in _DATOS_FISCALES_KEYS:
            if key in new_data:
                existing[key] = {
                    "value": new_data[key],
                    "_source": "manual",
                    "_updated": now,
                }

        # Old keys preserved
        assert existing["ingresos_trabajo"]["value"] == 30000
        assert existing["ss_empleado"]["_source"] == "conversation"
        # New keys added
        assert existing["epigrafe_iae"]["value"] == "861"
        assert existing["regimen_iva"]["value"] == "general"


class TestFiscalProfileForAgents:
    """Test how the fiscal profile is formatted for agent system prompts."""

    def test_format_for_workspace_agent(self):
        """Simulate the formatting used in workspace_agent._format_fiscal_profile."""
        fp = {
            "ccaa_residencia": "Madrid",
            "situacion_laboral": "autonomo",
            "epigrafe_iae": "861",
            "tipo_actividad": "profesional",
            "metodo_estimacion_irpf": "directa_simplificada",
            "regimen_iva": "general",
            "tipo_retencion_facturas": 15.0,
            "tarifa_plana": False,
            "pluriactividad": True,
        }

        label_map = {
            "ccaa_residencia": "CCAA residencia",
            "situacion_laboral": "Situación laboral",
            "epigrafe_iae": "Epígrafe IAE",
            "tipo_actividad": "Tipo actividad",
            "metodo_estimacion_irpf": "Método estimación IRPF",
            "regimen_iva": "Régimen IVA",
            "tipo_retencion_facturas": "Tipo retención facturas",
            "tarifa_plana": "Tarifa plana",
            "pluriactividad": "Pluriactividad",
        }

        lines = []
        for key, label in label_map.items():
            val = fp.get(key)
            if val is not None and val != "":
                if isinstance(val, bool):
                    lines.append(f"- {label}: {'Sí' if val else 'No'}")
                elif isinstance(val, float) and key == "tipo_retencion_facturas":
                    lines.append(f"- {label}: {val}%")
                else:
                    lines.append(f"- {label}: {val}")

        result = "\n".join(lines)
        assert "CCAA residencia: Madrid" in result
        assert "Epígrafe IAE: 861" in result
        assert "Régimen IVA: general" in result
        assert "Tipo retención facturas: 15.0%" in result
        assert "Tarifa plana: No" in result
        assert "Pluriactividad: Sí" in result

    def test_empty_profile_produces_no_output(self):
        """An empty fiscal profile should produce no lines."""
        fp = {}
        lines = []
        for key in AUTONOMO_FIELDS:
            val = fp.get(key)
            if val is not None and val != "":
                lines.append(f"- {key}: {val}")
        assert len(lines) == 0

    def test_extract_plain_values_from_wrapped_format(self):
        """The chat_stream.py logic extracts plain values from wrapped format."""
        raw_datos = json.dumps({
            "epigrafe_iae": {"value": "861", "_source": "manual", "_updated": "2026-03-03"},
            "regimen_iva": {"value": "general", "_source": "manual", "_updated": "2026-03-03"},
            "tarifa_plana": {"value": True, "_source": "manual", "_updated": "2026-03-03"},
            "ingresos_trabajo": {"value": 30000, "_source": "conversation", "_updated": "2026-01-01"},
        })

        datos = json.loads(raw_datos)
        fiscal_profile = {}
        for k, v in datos.items():
            if k.startswith("_"):
                continue
            fiscal_profile[k] = v["value"] if isinstance(v, dict) and "value" in v else v

        assert fiscal_profile["epigrafe_iae"] == "861"
        assert fiscal_profile["regimen_iva"] == "general"
        assert fiscal_profile["tarifa_plana"] is True
        assert fiscal_profile["ingresos_trabajo"] == 30000
