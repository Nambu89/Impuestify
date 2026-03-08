"""
Tests for Sprint 1 — Fiscal Profile Adaptive Backend.

Covers:
1. classify_regime for every CCAA type
2. GET /api/fiscal-profile/fields returns correct sections by CCAA
3. DeductionService.build_answers_from_profile with partial profiles
4. discover_deductions_tool merges profile answers correctly
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.regime_classifier import classify_regime, is_foral


# =============================================================================
# 1. classify_regime
# =============================================================================

class TestClassifyRegime:
    def test_araba_is_foral_vasco(self):
        assert classify_regime("Araba") == "foral_vasco"

    def test_bizkaia_is_foral_vasco(self):
        assert classify_regime("Bizkaia") == "foral_vasco"

    def test_gipuzkoa_is_foral_vasco(self):
        assert classify_regime("Gipuzkoa") == "foral_vasco"

    def test_navarra_is_foral_navarra(self):
        assert classify_regime("Navarra") == "foral_navarra"

    def test_ceuta_is_ceuta_melilla(self):
        assert classify_regime("Ceuta") == "ceuta_melilla"

    def test_melilla_is_ceuta_melilla(self):
        assert classify_regime("Melilla") == "ceuta_melilla"

    def test_canarias_is_canarias(self):
        assert classify_regime("Canarias") == "canarias"

    def test_madrid_is_comun(self):
        assert classify_regime("Madrid") == "comun"

    def test_cataluna_is_comun(self):
        assert classify_regime("Cataluna") == "comun"

    def test_andalucia_is_comun(self):
        assert classify_regime("Andalucia") == "comun"

    def test_aragon_is_comun(self):
        assert classify_regime("Aragon") == "comun"

    def test_unknown_ccaa_is_comun(self):
        assert classify_regime("UnknownCCAA") == "comun"

    def test_empty_string_is_comun(self):
        assert classify_regime("") == "comun"

    def test_is_foral_araba(self):
        assert is_foral("Araba") is True

    def test_is_foral_navarra(self):
        assert is_foral("Navarra") is True

    def test_is_foral_madrid(self):
        assert is_foral("Madrid") is False

    def test_is_foral_canarias(self):
        assert is_foral("Canarias") is False


# =============================================================================
# 2. GET /api/fiscal-profile/fields  — router-level tests (mocked DB)
# =============================================================================

def _make_mock_db(rows=None):
    """Create an async mock DB client that returns empty rows by default."""
    mock_result = MagicMock()
    mock_result.rows = rows or []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


def _make_mock_user(user_id="test-user-1"):
    user = MagicMock()
    user.user_id = user_id
    return user


@pytest.mark.asyncio
class TestFiscalFieldsEndpoint:
    """Tests for the /api/fiscal-profile/fields route logic (no HTTP server needed)."""

    async def _call_endpoint(self, ccaa="", situacion_laboral="", db=None, user_id="u1"):
        from app.routers.fiscal_fields import get_fiscal_profile_fields
        from app.services.workspace_service import workspace_service

        if db is None:
            db = _make_mock_db()

        mock_user = _make_mock_user(user_id)
        # Patch workspace_service to return empty summary
        with patch.object(workspace_service, "get_fiscal_summary_from_workspace", new=AsyncMock(return_value={"has_data": False})):
            return await get_fiscal_profile_fields(
                ccaa=ccaa,
                situacion_laboral=situacion_laboral,
                current_user=mock_user,
                db=db,
            )

    async def test_empty_ccaa_returns_comun(self):
        resp = await self._call_endpoint(ccaa="")
        assert resp["regime"] == "comun"

    async def test_madrid_returns_comun(self):
        resp = await self._call_endpoint(ccaa="Madrid")
        assert resp["regime"] == "comun"

    async def test_araba_returns_foral_vasco(self):
        resp = await self._call_endpoint(ccaa="Araba")
        assert resp["regime"] == "foral_vasco"

    async def test_navarra_returns_foral_navarra(self):
        resp = await self._call_endpoint(ccaa="Navarra")
        assert resp["regime"] == "foral_navarra"

    async def test_ceuta_returns_ceuta_melilla(self):
        resp = await self._call_endpoint(ccaa="Ceuta")
        assert resp["regime"] == "ceuta_melilla"

    async def test_canarias_returns_canarias(self):
        resp = await self._call_endpoint(ccaa="Canarias")
        assert resp["regime"] == "canarias"

    async def test_base_sections_always_present(self):
        resp = await self._call_endpoint(ccaa="Madrid")
        section_ids = [s["id"] for s in resp["sections"]]
        for expected in ("datos_personales", "rendimientos_trabajo", "rendimientos_ahorro",
                         "inmuebles", "familia", "discapacidad", "reducciones",
                         "vivienda", "sostenibilidad", "donaciones", "territorio"):
            assert expected in section_ids, f"Missing section: {expected}"

    async def test_foral_vasco_includes_prevision_section(self):
        resp = await self._call_endpoint(ccaa="Bizkaia")
        section_ids = [s["id"] for s in resp["sections"]]
        assert "prevision_social_foral" in section_ids

    async def test_foral_navarra_includes_prevision_section(self):
        resp = await self._call_endpoint(ccaa="Navarra")
        section_ids = [s["id"] for s in resp["sections"]]
        assert "prevision_social_navarra" in section_ids

    async def test_ceuta_includes_ceuta_melilla_section(self):
        resp = await self._call_endpoint(ccaa="Ceuta")
        section_ids = [s["id"] for s in resp["sections"]]
        assert "ceuta_melilla" in section_ids

    async def test_canarias_includes_canarias_section(self):
        resp = await self._call_endpoint(ccaa="Canarias")
        section_ids = [s["id"] for s in resp["sections"]]
        assert "canarias" in section_ids

    async def test_autonomo_includes_actividad_section(self):
        resp = await self._call_endpoint(ccaa="Madrid", situacion_laboral="autonomo")
        section_ids = [s["id"] for s in resp["sections"]]
        assert "actividad_economica" in section_ids

    async def test_deducciones_autonomicas_built_from_db(self):
        """When DB has deduction rows with questions_json, a section is built."""
        db = _make_mock_db(rows=[
            {
                "name": "Deduccion vivienda",
                "category": "vivienda",
                "requirements_json": '{"alquiler_vivienda_habitual": true}',
                "questions_json": json.dumps([
                    {"key": "alquiler_vivienda_habitual", "text": "Paga alquiler?", "type": "bool"}
                ]),
            }
        ])
        resp = await self._call_endpoint(ccaa="Madrid", db=db)
        section_ids = [s["id"] for s in resp["sections"]]
        assert "deducciones_autonomicas" in section_ids
        ded_section = next(s for s in resp["sections"] if s["id"] == "deducciones_autonomicas")
        assert any(f["key"] == "alquiler_vivienda_habitual" for f in ded_section["fields"])

    async def test_no_deducciones_section_when_db_empty(self):
        db = _make_mock_db(rows=[])
        resp = await self._call_endpoint(ccaa="Madrid", db=db)
        section_ids = [s["id"] for s in resp["sections"]]
        assert "deducciones_autonomicas" not in section_ids

    async def test_workspace_data_key_present(self):
        resp = await self._call_endpoint(ccaa="Madrid")
        assert "workspace_data" in resp
        assert resp["workspace_data"]["has_data"] is False

    async def test_foral_vasco_no_ceuta_section(self):
        resp = await self._call_endpoint(ccaa="Araba")
        section_ids = [s["id"] for s in resp["sections"]]
        assert "ceuta_melilla" not in section_ids

    async def test_ccaa_echoed_in_response(self):
        resp = await self._call_endpoint(ccaa="Andalucia")
        assert resp["ccaa"] == "Andalucia"


# =============================================================================
# 3. build_answers_from_profile
# =============================================================================

class TestBuildAnswersFromProfile:
    """Unit tests for DeductionService.build_answers_from_profile()."""

    def _build(self, profile: dict, ccaa: str = "") -> dict:
        from app.services.deduction_service import DeductionService
        return DeductionService.build_answers_from_profile(profile, ccaa)

    def test_empty_profile_returns_empty_dict(self):
        result = self._build({})
        assert isinstance(result, dict)

    def test_familia_numerosa_mapped(self):
        result = self._build({"familia_numerosa": True})
        assert result.get("familia_numerosa") is True

    def test_ascendientes_65_maps_ascendiente_a_cargo(self):
        result = self._build({"num_ascendientes_65": 1})
        assert result.get("ascendiente_a_cargo") is True

    def test_ascendientes_75_maps_ascendiente_a_cargo(self):
        result = self._build({"num_ascendientes_75": 2})
        assert result.get("ascendiente_a_cargo") is True

    def test_no_ascendientes_no_mapping(self):
        result = self._build({"num_ascendientes_65": 0, "num_ascendientes_75": 0})
        assert "ascendiente_a_cargo" not in result

    def test_discapacidad_33_maps(self):
        result = self._build({"discapacidad_contribuyente": 33})
        assert result.get("discapacidad_reconocida") is True

    def test_discapacidad_below_33_not_mapped(self):
        result = self._build({"discapacidad_contribuyente": 20})
        assert "discapacidad_reconocida" not in result

    def test_hipoteca_pre2013_maps(self):
        result = self._build({"hipoteca_pre2013": True})
        assert result.get("adquisicion_antes_2013") is True
        assert result.get("deducia_antes_2013") is True

    def test_madre_trabajadora_maps(self):
        result = self._build({"madre_trabajadora_ss": True})
        assert result.get("madre_trabajadora") is True

    def test_ceuta_melilla_bool_maps(self):
        result = self._build({"ceuta_melilla": True})
        assert result.get("residente_ceuta_melilla") is True

    def test_ceuta_ccaa_maps_residencia(self):
        result = self._build({}, ccaa="Ceuta")
        assert result.get("residente_ceuta_melilla") is True

    def test_plan_pensiones_amount_maps(self):
        result = self._build({"aportaciones_plan_pensiones": 1500.0})
        assert result.get("aportaciones_planes_pensiones") is True

    def test_zero_plan_pensiones_not_mapped(self):
        result = self._build({"aportaciones_plan_pensiones": 0})
        assert "aportaciones_planes_pensiones" not in result

    def test_donativo_amount_maps(self):
        result = self._build({"donativos_ley_49_2002": 200.0})
        assert result.get("donativo_a_entidad_acogida") is True

    def test_autonomo_directa_maps(self):
        result = self._build({"situacion_laboral": "autonomo", "metodo_estimacion_irpf": "directa_simplificada"})
        assert result.get("autonomo_estimacion_directa") is True

    def test_direct_bool_field_vehiculo_electrico(self):
        result = self._build({"vehiculo_electrico_nuevo": True})
        assert result.get("vehiculo_electrico_nuevo") is True

    def test_direct_bool_field_false_preserved(self):
        result = self._build({"obras_mejora_energetica": False})
        assert result.get("obras_mejora_energetica") is False

    def test_none_fields_not_included(self):
        result = self._build({"alquiler_vivienda_habitual": None})
        # None should not map to True (the field is not set)
        assert result.get("alquiler_vivienda_habitual") is not True

    def test_multiple_fields_together(self):
        profile = {
            "num_ascendientes_65": 1,
            "familia_numerosa": True,
            "vehiculo_electrico_nuevo": True,
            "obras_mejora_energetica": False,
        }
        result = self._build(profile)
        assert result["ascendiente_a_cargo"] is True
        assert result["familia_numerosa"] is True
        assert result["vehiculo_electrico_nuevo"] is True
        assert result["obras_mejora_energetica"] is False


# =============================================================================
# 4. discover_deductions merges profile answers
# =============================================================================

@pytest.mark.asyncio
class TestDiscoverDeductionsProfileMerge:
    """Verify that discover_deductions_tool merges profile-derived answers correctly."""

    async def test_explicit_answers_override_profile(self):
        """
        Caller passes answers={"familia_numerosa": False}.
        Profile has familia_numerosa=True.
        Caller answer must win.
        """
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        mock_profile_row = {
            "ccaa_residencia": "Madrid",
            "situacion_laboral": "empleado",
            "datos_fiscales": json.dumps({
                "familia_numerosa": {"value": True, "_source": "manual", "_updated": "2026-01-01"},
            }),
        }

        mock_db_result = MagicMock()
        mock_db_result.rows = [mock_profile_row]
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_db_result)

        captured_answers: dict = {}

        async def mock_evaluate_eligibility(self_or_tax_year=None, **kwargs):
            # Called as service.evaluate_eligibility(...) so self is the service instance
            captured_answers.update(kwargs.get("answers", {}))
            return {"eligible": [], "maybe_eligible": [], "not_eligible": [], "estimated_savings": 0.0, "total_deductions": 0}

        async def mock_missing(self_or_tax_year=None, **kwargs):
            return []

        # get_db_client is a lazy import inside the function — patch at the DB module level
        with patch("app.database.turso_client.get_db_client", new=AsyncMock(return_value=mock_db)):
            with patch("app.services.deduction_service.DeductionService.evaluate_eligibility", new=mock_evaluate_eligibility):
                with patch("app.services.deduction_service.DeductionService.get_missing_questions", new=mock_missing):
                    await discover_deductions_tool(
                        ccaa="Madrid",
                        answers={"familia_numerosa": False},
                        user_id="test-user-123",
                    )

        # The explicit False should override the profile True
        assert captured_answers.get("familia_numerosa") is False

    async def test_profile_answers_populate_when_no_explicit_answers(self):
        """
        No explicit answers passed. Profile has vehiculo_electrico_nuevo=True.
        Expected: vehiculo_electrico_nuevo=True in the answers used.
        """
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        mock_profile_row = {
            "ccaa_residencia": "Madrid",
            "situacion_laboral": "empleado",
            "datos_fiscales": json.dumps({
                "vehiculo_electrico_nuevo": {"value": True, "_source": "manual", "_updated": "2026-01-01"},
            }),
        }

        mock_db_result = MagicMock()
        mock_db_result.rows = [mock_profile_row]
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_db_result)

        captured_answers: dict = {}

        async def mock_evaluate_eligibility(self_or_tax_year=None, **kwargs):
            captured_answers.update(kwargs.get("answers", {}))
            return {"eligible": [], "maybe_eligible": [], "not_eligible": [], "estimated_savings": 0.0, "total_deductions": 0}

        async def mock_missing(self_or_tax_year=None, **kwargs):
            return []

        with patch("app.database.turso_client.get_db_client", new=AsyncMock(return_value=mock_db)):
            with patch("app.services.deduction_service.DeductionService.evaluate_eligibility", new=mock_evaluate_eligibility):
                with patch("app.services.deduction_service.DeductionService.get_missing_questions", new=mock_missing):
                    await discover_deductions_tool(
                        ccaa="Madrid",
                        answers={},
                        user_id="test-user-456",
                    )

        assert captured_answers.get("vehiculo_electrico_nuevo") is True

    async def test_no_user_id_uses_explicit_answers_only(self):
        """Without user_id, no DB call is made and only explicit answers are used."""
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        captured_answers: dict = {}

        async def mock_evaluate_eligibility(self_or_tax_year=None, **kwargs):
            captured_answers.update(kwargs.get("answers", {}))
            return {"eligible": [], "maybe_eligible": [], "not_eligible": [], "estimated_savings": 0.0, "total_deductions": 0}

        async def mock_missing(self_or_tax_year=None, **kwargs):
            return []

        with patch("app.services.deduction_service.DeductionService.evaluate_eligibility", new=mock_evaluate_eligibility):
            with patch("app.services.deduction_service.DeductionService.get_missing_questions", new=mock_missing):
                await discover_deductions_tool(
                    ccaa="Estatal",
                    answers={"donativo_a_entidad_acogida": True},
                    user_id=None,
                )

        assert captured_answers.get("donativo_a_entidad_acogida") is True
