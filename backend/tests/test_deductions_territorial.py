"""
Tests for territorial (autonomous community) deductions system.

Covers:
- Seed data integrity for all 8 territories
- Combined Estatal + CCAA query logic
- Foral vs régimen común behavior
- Eligibility evaluation with territorial deductions
- Discovery tool with CCAA parameter
"""
import json
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Mock dependencies before importing app modules
sys.modules.setdefault("jose", MagicMock())
sys.modules.setdefault("jose.jwt", MagicMock())
sys.modules.setdefault("passlib", MagicMock())
sys.modules.setdefault("passlib.context", MagicMock())
sys.modules.setdefault("bcrypt", MagicMock())
sys.modules.setdefault("slowapi", MagicMock())
sys.modules.setdefault("slowapi.util", MagicMock())
sys.modules.setdefault("slowapi.errors", MagicMock())


# ============================================================
# SEED DATA INTEGRITY TESTS
# ============================================================

class TestTerritorialSeedData:
    """Tests that seed data is well-formed for all territories."""

    def _get_all_territorial(self):
        from scripts.seed_deductions_territorial import ALL_TERRITORIAL
        return ALL_TERRITORIAL

    def test_all_territories_present(self):
        """Should have exactly 8 territories."""
        territories = self._get_all_territorial()
        expected = {"Araba", "Bizkaia", "Gipuzkoa", "Navarra",
                    "Madrid", "Cataluña", "Andalucía", "Valencia"}
        assert set(territories.keys()) == expected

    def test_foral_territories_have_deductions(self):
        """Foral territories should have 6+ deductions each."""
        territories = self._get_all_territorial()
        for t in ["Araba", "Bizkaia", "Gipuzkoa", "Navarra"]:
            assert len(territories[t]) >= 6, f"{t} has only {len(territories[t])} deductions"

    def test_regimen_comun_territories_have_deductions(self):
        """Régimen común territories should have 5+ deductions each."""
        territories = self._get_all_territorial()
        for t in ["Madrid", "Cataluña", "Andalucía", "Valencia"]:
            assert len(territories[t]) >= 5, f"{t} has only {len(territories[t])} deductions"

    def test_total_deduction_count(self):
        """Should have at least 45 territorial deductions total."""
        territories = self._get_all_territorial()
        total = sum(len(d) for d in territories.values())
        assert total >= 45, f"Only {total} deductions, expected 45+"

    def test_all_codes_unique_per_territory(self):
        """Deduction codes should be unique within each territory."""
        territories = self._get_all_territorial()
        for territory_name, deductions in territories.items():
            codes = [d["code"] for d in deductions]
            assert len(codes) == len(set(codes)), \
                f"Duplicate codes in {territory_name}: {[c for c in codes if codes.count(c) > 1]}"

    def test_all_codes_globally_unique(self):
        """Deduction codes should be globally unique across all territories."""
        territories = self._get_all_territorial()
        all_codes = []
        for deductions in territories.values():
            all_codes.extend(d["code"] for d in deductions)
        assert len(all_codes) == len(set(all_codes)), "Duplicate codes across territories"

    def test_code_prefix_matches_territory(self):
        """Deduction codes should use correct territory prefix."""
        territories = self._get_all_territorial()
        prefix_map = {
            "Araba": "ARA-", "Bizkaia": "BIZ-", "Gipuzkoa": "GIP-",
            "Navarra": "NAV-", "Madrid": "MAD-", "Cataluña": "CAT-",
            "Andalucía": "AND-", "Valencia": "VAL-",
        }
        for territory_name, deductions in territories.items():
            expected_prefix = prefix_map[territory_name]
            for d in deductions:
                assert d["code"].startswith(expected_prefix), \
                    f"{d['code']} doesn't start with {expected_prefix}"

    def test_required_fields_present(self):
        """Every deduction should have all required fields."""
        territories = self._get_all_territorial()
        required = {"code", "name", "type", "category", "legal_reference",
                    "description", "requirements_json", "questions_json"}
        for territory_name, deductions in territories.items():
            for d in deductions:
                for field in required:
                    assert field in d, f"{d['code']} missing field: {field}"

    def test_json_fields_parseable(self):
        """requirements_json and questions_json should be valid JSON."""
        territories = self._get_all_territorial()
        for territory_name, deductions in territories.items():
            for d in deductions:
                reqs = json.loads(d["requirements_json"])
                assert isinstance(reqs, dict), f"{d['code']} requirements not dict"
                qs = json.loads(d["questions_json"])
                assert isinstance(qs, list), f"{d['code']} questions not list"

    def test_questions_have_required_keys(self):
        """Each question should have key, text, and type."""
        territories = self._get_all_territorial()
        for territory_name, deductions in territories.items():
            for d in deductions:
                questions = json.loads(d["questions_json"])
                for q in questions:
                    assert "key" in q, f"{d['code']} question missing 'key'"
                    assert "text" in q, f"{d['code']} question missing 'text'"
                    assert "type" in q, f"{d['code']} question missing 'type'"

    def test_has_amount_info(self):
        """Every deduction should have percentage, max_amount, or fixed_amount."""
        territories = self._get_all_territorial()
        for territory_name, deductions in territories.items():
            for d in deductions:
                has_amount = (
                    d.get("percentage") is not None
                    or d.get("max_amount") is not None
                    or d.get("fixed_amount") is not None
                )
                assert has_amount, f"{d['code']} has no amount info"

    def test_legal_references_not_empty(self):
        """Legal references should reference actual laws."""
        territories = self._get_all_territorial()
        for territory_name, deductions in territories.items():
            for d in deductions:
                ref = d.get("legal_reference", "")
                assert len(ref) > 5, f"{d['code']} has empty legal_reference"


# ============================================================
# FORAL TERRITORY SPECIFIC TESTS
# ============================================================

class TestForalTerritories:
    """Tests specific to Basque Country and Navarra foral deductions."""

    def _get_territory(self, name):
        from scripts.seed_deductions_territorial import ALL_TERRITORIAL
        return ALL_TERRITORIAL[name]

    def test_araba_has_vivienda_compra(self):
        """Araba should have vivienda habitual purchase deduction (unique — still active)."""
        deductions = self._get_territory("Araba")
        codes = [d["code"] for d in deductions]
        assert "ARA-COMPRA-VIV" in codes

    def test_bizkaia_has_vivienda_compra(self):
        """Bizkaia should have vivienda habitual purchase deduction."""
        deductions = self._get_territory("Bizkaia")
        codes = [d["code"] for d in deductions]
        assert "BIZ-COMPRA-VIV" in codes

    def test_gipuzkoa_has_vivienda_compra(self):
        """Gipuzkoa should have vivienda habitual purchase deduction."""
        deductions = self._get_territory("Gipuzkoa")
        codes = [d["code"] for d in deductions]
        assert "GIP-COMPRA-VIV" in codes

    def test_basque_compra_vivienda_18_percent(self):
        """Basque vivienda compra should be 18% general (unique vs state)."""
        for territory in ["Araba", "Bizkaia", "Gipuzkoa"]:
            deductions = self._get_territory(territory)
            compra = next(d for d in deductions if "COMPRA-VIV" in d["code"])
            assert compra.get("percentage") == 18.0
            assert compra.get("max_amount") == 1530.0

    def test_araba_descendientes_higher_than_state(self):
        """Araba descendientes (734.80€) should be higher than state MPYF."""
        deductions = self._get_territory("Araba")
        desc = next(d for d in deductions if d["code"] == "ARA-DESC-HIJOS")
        assert desc["fixed_amount"] == 734.80

    def test_navarra_no_vivienda_compra(self):
        """Navarra should NOT have vivienda compra (eliminated since 2018)."""
        deductions = self._get_territory("Navarra")
        codes = [d["code"] for d in deductions]
        assert not any("COMPRA-VIV" in c for c in codes)

    def test_araba_has_vehiculo_electrico(self):
        """Araba should have EV deduction (unique among Basque territories)."""
        deductions = self._get_territory("Araba")
        codes = [d["code"] for d in deductions]
        assert "ARA-VEH-ELECT" in codes

    def test_araba_has_despoblacion(self):
        """Araba should have depopulation deduction (unique)."""
        deductions = self._get_territory("Araba")
        codes = [d["code"] for d in deductions]
        assert "ARA-DESPOBLACION" in codes

    def test_gipuzkoa_has_cuidado_menores_2025(self):
        """Gipuzkoa should have the new 2025 childcare deduction."""
        deductions = self._get_territory("Gipuzkoa")
        codes = [d["code"] for d in deductions]
        assert "GIP-CUIDADO-MENORES" in codes


# ============================================================
# RÉGIMEN COMÚN SPECIFIC TESTS
# ============================================================

class TestRegimenComun:
    """Tests specific to régimen común CCAA deductions."""

    def _get_territory(self, name):
        from scripts.seed_deductions_territorial import ALL_TERRITORIAL
        return ALL_TERRITORIAL[name]

    def test_madrid_has_gastos_educativos(self):
        """Madrid should have education expenses deduction (unique)."""
        deductions = self._get_territory("Madrid")
        codes = [d["code"] for d in deductions]
        assert "MAD-GASTOS-EDUC" in codes

    def test_madrid_alquiler_jovenes(self):
        """Madrid alquiler should require menor_40_anos."""
        deductions = self._get_territory("Madrid")
        alquiler = next(d for d in deductions if d["code"] == "MAD-ALQUILER-VIV")
        reqs = json.loads(alquiler["requirements_json"])
        assert reqs.get("menor_40_anos") is True

    def test_valencia_has_material_escolar(self):
        """Valencia should have material escolar deduction."""
        deductions = self._get_territory("Valencia")
        codes = [d["code"] for d in deductions]
        assert "VAL-MAT-ESCOLAR" in codes

    def test_valencia_renovables(self):
        """Valencia should have renewable energy deduction at 40%+."""
        deductions = self._get_territory("Valencia")
        renov = next(d for d in deductions if d["code"] == "VAL-RENOVABLES")
        assert renov.get("percentage") == 40.0

    def test_cataluna_donativos_catalan(self):
        """Cataluña should have Catalan language donation deduction."""
        deductions = self._get_territory("Cataluña")
        codes = [d["code"] for d in deductions]
        assert "CAT-DONAT-CATALAN" in codes


# ============================================================
# DEDUCTION SERVICE COMBINED QUERY TESTS
# ============================================================

class TestDeductionServiceCombined:
    """Tests for combined Estatal + CCAA deduction queries."""

    def _make_mock_db(self, rows_by_territory):
        """Create a mock DB that returns different rows per territory."""
        mock_db = AsyncMock()

        async def mock_execute(query, params=None):
            result = MagicMock()
            if params and "territory" in query.lower():
                territory = params[0]
                result.rows = rows_by_territory.get(territory, [])
            else:
                result.rows = []
            return result

        mock_db.execute = mock_execute
        return mock_db

    def _make_row(self, code, territory, category="general", fixed_amount=100.0):
        return {
            "id": f"id-{code}",
            "code": code,
            "tax_year": 2025,
            "territory": territory,
            "name": f"Deducción {code}",
            "type": "deduccion",
            "category": category,
            "percentage": None,
            "max_amount": None,
            "fixed_amount": fixed_amount,
            "legal_reference": "Test",
            "description": "Test deduction",
            "requirements_json": json.dumps({}),
            "questions_json": json.dumps([]),
            "is_active": 1,
        }

    @pytest.mark.asyncio
    async def test_get_all_deductions_regimen_comun(self):
        """Should combine Estatal + CCAA deductions for régimen común."""
        from app.services.deduction_service import DeductionService

        mock_db = self._make_mock_db({
            "Estatal": [self._make_row("EST-1", "Estatal"), self._make_row("EST-2", "Estatal")],
            "Madrid": [self._make_row("MAD-1", "Madrid")],
        })
        service = DeductionService(db_client=mock_db)
        result = await service.get_all_deductions("Madrid")
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_all_deductions_foral_only(self):
        """Foral territories should NOT include Estatal deductions."""
        from app.services.deduction_service import DeductionService

        mock_db = self._make_mock_db({
            "Estatal": [self._make_row("EST-1", "Estatal")],
            "Araba": [self._make_row("ARA-1", "Araba"), self._make_row("ARA-2", "Araba")],
        })
        service = DeductionService(db_client=mock_db)
        result = await service.get_all_deductions("Araba")
        # Should only have Araba deductions, NOT Estatal
        assert len(result) == 2
        assert all(d["code"].startswith("ARA-") for d in result)

    @pytest.mark.asyncio
    async def test_evaluate_eligibility_with_ccaa(self):
        """Should evaluate combined deductions when ccaa is provided."""
        from app.services.deduction_service import DeductionService

        mock_db = self._make_mock_db({
            "Estatal": [self._make_row("EST-1", "Estatal", fixed_amount=200.0)],
            "Madrid": [self._make_row("MAD-1", "Madrid", fixed_amount=300.0)],
        })
        service = DeductionService(db_client=mock_db)
        result = await service.evaluate_eligibility(ccaa="Madrid", answers={})
        # Both should be maybe_eligible (no requirements)
        assert len(result["maybe_eligible"]) == 2
        assert result["total_deductions"] == 2

    @pytest.mark.asyncio
    async def test_get_missing_questions_with_ccaa(self):
        """Should get questions from both Estatal and CCAA deductions."""
        from app.services.deduction_service import DeductionService

        estatal_row = self._make_row("EST-1", "Estatal")
        estatal_row["requirements_json"] = json.dumps({"req_a": True})
        estatal_row["questions_json"] = json.dumps([
            {"key": "req_a", "text": "Question A?", "type": "bool"},
        ])

        ccaa_row = self._make_row("MAD-1", "Madrid")
        ccaa_row["requirements_json"] = json.dumps({"req_b": True})
        ccaa_row["questions_json"] = json.dumps([
            {"key": "req_b", "text": "Question B?", "type": "bool"},
        ])

        mock_db = self._make_mock_db({
            "Estatal": [estatal_row],
            "Madrid": [ccaa_row],
        })
        service = DeductionService(db_client=mock_db)
        missing = await service.get_missing_questions(ccaa="Madrid", answers={})
        keys = [q["key"] for q in missing]
        assert "req_a" in keys
        assert "req_b" in keys

    @pytest.mark.asyncio
    async def test_foral_eligibility_independent(self):
        """Foral eligibility should not include Estatal deductions."""
        from app.services.deduction_service import DeductionService

        estatal_row = self._make_row("EST-1", "Estatal")
        navarra_row = self._make_row("NAV-1", "Navarra", fixed_amount=500.0)

        mock_db = self._make_mock_db({
            "Estatal": [estatal_row],
            "Navarra": [navarra_row],
        })
        service = DeductionService(db_client=mock_db)
        result = await service.evaluate_eligibility(ccaa="Navarra", answers={})
        # Should only have Navarra deductions
        assert result["total_deductions"] == 1
        assert result["maybe_eligible"][0]["code"] == "NAV-1"


# ============================================================
# DISCOVERY TOOL TERRITORIAL TESTS
# ============================================================

class TestDiscoveryToolTerritorial:
    """Tests for deduction discovery tool with territorial support."""

    @pytest.mark.asyncio
    async def test_discover_with_ccaa_madrid(self):
        """Should use combined query when ccaa='Madrid'."""
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        mock_result = {
            "eligible": [{"code": "MAD-1", "name": "Test", "type": "deduccion",
                         "category": "familia", "description": "Test", "legal_reference": "Art. 1",
                         "fixed_amount": 500.0}],
            "maybe_eligible": [],
            "not_eligible": [],
            "estimated_savings": 500.0,
            "total_deductions": 1,
        }

        with patch("app.services.deduction_service.get_deduction_service") as mock_svc:
            svc = MagicMock()
            svc.evaluate_eligibility = AsyncMock(return_value=mock_result)
            svc.get_missing_questions = AsyncMock(return_value=[])
            mock_svc.return_value = svc

            result = await discover_deductions_tool(ccaa="Madrid")

            assert result["success"] is True
            # Should have called with ccaa parameter
            call_kwargs = svc.evaluate_eligibility.call_args
            assert call_kwargs.kwargs.get("ccaa") == "Madrid"

    @pytest.mark.asyncio
    async def test_discover_with_foral_territory(self):
        """Should use combined query when ccaa='Araba'."""
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        mock_result = {
            "eligible": [],
            "maybe_eligible": [],
            "not_eligible": [],
            "estimated_savings": 0.0,
            "total_deductions": 0,
        }

        with patch("app.services.deduction_service.get_deduction_service") as mock_svc:
            svc = MagicMock()
            svc.evaluate_eligibility = AsyncMock(return_value=mock_result)
            svc.get_missing_questions = AsyncMock(return_value=[])
            mock_svc.return_value = svc

            result = await discover_deductions_tool(ccaa="Araba")

            assert result["success"] is True
            call_kwargs = svc.evaluate_eligibility.call_args
            assert call_kwargs.kwargs.get("ccaa") == "Araba"

    @pytest.mark.asyncio
    async def test_discover_with_unknown_ccaa_falls_back(self):
        """Unknown CCAA should fallback to Estatal only."""
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        mock_result = {
            "eligible": [],
            "maybe_eligible": [],
            "not_eligible": [],
            "estimated_savings": 0.0,
            "total_deductions": 0,
        }

        with patch("app.services.deduction_service.get_deduction_service") as mock_svc:
            svc = MagicMock()
            svc.evaluate_eligibility = AsyncMock(return_value=mock_result)
            svc.get_missing_questions = AsyncMock(return_value=[])
            mock_svc.return_value = svc

            result = await discover_deductions_tool(ccaa="Desconocida")

            assert result["success"] is True
            # Should have called with territory="Estatal", not ccaa
            call_args = svc.evaluate_eligibility.call_args
            assert call_args[0][0] == "Estatal"

    @pytest.mark.asyncio
    async def test_formatted_response_shows_territory(self):
        """Formatted response should show the territory name."""
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        mock_result = {
            "eligible": [],
            "maybe_eligible": [],
            "not_eligible": [],
            "estimated_savings": 0.0,
            "total_deductions": 0,
        }

        with patch("app.services.deduction_service.get_deduction_service") as mock_svc:
            svc = MagicMock()
            svc.evaluate_eligibility = AsyncMock(return_value=mock_result)
            svc.get_missing_questions = AsyncMock(return_value=[])
            mock_svc.return_value = svc

            result = await discover_deductions_tool(ccaa="Araba")
            assert "Araba" in result["formatted_response"]

    def test_tool_schema_lists_supported_ccaa(self):
        """Tool schema description should mention supported territories."""
        from app.tools.deduction_discovery_tool import DISCOVER_DEDUCTIONS_TOOL

        schema = DISCOVER_DEDUCTIONS_TOOL["function"]["parameters"]
        ccaa_desc = schema["properties"]["ccaa"]["description"]
        assert "Araba" in ccaa_desc
        assert "Bizkaia" in ccaa_desc
        assert "Navarra" in ccaa_desc
        assert "Madrid" in ccaa_desc


# ============================================================
# CROSS-TERRITORY COMPARISON TESTS
# ============================================================

class TestCrossTerritoryComparison:
    """Tests that verify strategic differences between territories."""

    def _get_territory(self, name):
        from scripts.seed_deductions_territorial import ALL_TERRITORIAL
        return ALL_TERRITORIAL[name]

    def test_basque_alquiler_more_generous_than_common(self):
        """Basque alquiler deductions should be more generous than régimen común."""
        for basque in ["Araba", "Bizkaia", "Gipuzkoa"]:
            basque_deductions = self._get_territory(basque)
            alquiler = next(d for d in basque_deductions if "ALQUILER" in d["code"])
            assert alquiler["max_amount"] >= 1600.0

        # Compare with Andalucía (lower)
        and_deductions = self._get_territory("Andalucía")
        and_alquiler = next(d for d in and_deductions if "ALQUILER" in d["code"])
        assert and_alquiler["max_amount"] <= 600.0

    def test_basque_compra_vivienda_exists(self):
        """Only Basque territories should have active vivienda compra."""
        for basque in ["Araba", "Bizkaia", "Gipuzkoa"]:
            deductions = self._get_territory(basque)
            has_compra = any("COMPRA-VIV" in d["code"] for d in deductions)
            assert has_compra, f"{basque} should have compra vivienda"

        # Navarra eliminated it
        navarra = self._get_territory("Navarra")
        has_compra = any("COMPRA-VIV" in d["code"] for d in navarra)
        assert not has_compra, "Navarra should NOT have compra vivienda"

    def test_every_territory_has_vivienda_category(self):
        """Every territory should have at least one vivienda deduction."""
        from scripts.seed_deductions_territorial import ALL_TERRITORIAL
        for name, deductions in ALL_TERRITORIAL.items():
            has_vivienda = any(d["category"] == "vivienda" for d in deductions)
            assert has_vivienda, f"{name} has no vivienda deduction"

    def test_every_territory_has_familia_category(self):
        """Every territory should have at least one familia deduction."""
        from scripts.seed_deductions_territorial import ALL_TERRITORIAL
        for name, deductions in ALL_TERRITORIAL.items():
            has_familia = any(d["category"] == "familia" for d in deductions)
            assert has_familia, f"{name} has no familia deduction"
