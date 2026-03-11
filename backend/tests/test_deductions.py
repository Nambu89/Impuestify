"""
Tests for the Deductions system: DeductionService + discover_deductions tool + seed data.
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
# SEED DATA TESTS
# ============================================================

class TestSeedData:
    """Tests for seed_deductions.py data integrity."""

    def test_seed_file_importable(self):
        """Seed script should be importable."""
        sys.path.insert(0, str(backend_dir / "scripts"))
        from seed_deductions import DEDUCTIONS_2025
        assert len(DEDUCTIONS_2025) == 16

    def test_all_deductions_have_required_fields(self):
        """Every deduction must have code, name, type, category."""
        sys.path.insert(0, str(backend_dir / "scripts"))
        from seed_deductions import DEDUCTIONS_2025

        for d in DEDUCTIONS_2025:
            assert "code" in d, f"Missing code in {d.get('name', '???')}"
            assert "name" in d, f"Missing name in {d.get('code', '???')}"
            assert "type" in d, f"Missing type in {d['code']}"
            assert "category" in d, f"Missing category in {d['code']}"
            assert d["code"].startswith("EST-"), f"State deductions must start with EST-: {d['code']}"

    def test_all_codes_unique(self):
        """All deduction codes must be unique."""
        sys.path.insert(0, str(backend_dir / "scripts"))
        from seed_deductions import DEDUCTIONS_2025

        codes = [d["code"] for d in DEDUCTIONS_2025]
        assert len(codes) == len(set(codes)), f"Duplicate codes found: {[c for c in codes if codes.count(c) > 1]}"

    def test_requirements_json_valid(self):
        """requirements_json must be valid JSON."""
        sys.path.insert(0, str(backend_dir / "scripts"))
        from seed_deductions import DEDUCTIONS_2025

        for d in DEDUCTIONS_2025:
            if d.get("requirements_json"):
                parsed = json.loads(d["requirements_json"])
                assert isinstance(parsed, dict), f"requirements_json must be dict for {d['code']}"

    def test_questions_json_valid(self):
        """questions_json must be valid JSON with key and text."""
        sys.path.insert(0, str(backend_dir / "scripts"))
        from seed_deductions import DEDUCTIONS_2025

        for d in DEDUCTIONS_2025:
            if d.get("questions_json"):
                parsed = json.loads(d["questions_json"])
                assert isinstance(parsed, list), f"questions_json must be list for {d['code']}"
                for q in parsed:
                    assert "key" in q, f"Question missing 'key' in {d['code']}"
                    assert "text" in q, f"Question missing 'text' in {d['code']}"

    def test_categories_valid(self):
        """All categories should be from expected set."""
        sys.path.insert(0, str(backend_dir / "scripts"))
        from seed_deductions import DEDUCTIONS_2025

        valid_categories = {
            "vivienda", "donativos", "familia", "prevision_social",
            "actividad_economica", "territorial", "internacional",
            "sostenibilidad", "general",
        }
        for d in DEDUCTIONS_2025:
            assert d["category"] in valid_categories, f"Unknown category '{d['category']}' in {d['code']}"

    def test_types_valid(self):
        """Types should be 'deduccion' or 'reduccion'."""
        sys.path.insert(0, str(backend_dir / "scripts"))
        from seed_deductions import DEDUCTIONS_2025

        for d in DEDUCTIONS_2025:
            assert d["type"] in ("deduccion", "reduccion"), f"Invalid type '{d['type']}' in {d['code']}"


# ============================================================
# DEDUCTION SERVICE TESTS
# ============================================================

def _make_mock_db(rows):
    """Create a mock DB client that returns given rows."""
    mock_db = AsyncMock()
    result = MagicMock()
    result.rows = rows
    mock_db.execute = AsyncMock(return_value=result)
    return mock_db


def _sample_deduction_row(code="EST-MAT-1200", category="familia", reqs=None, questions=None):
    """Create a sample deduction row dict."""
    return {
        "id": "test-id",
        "code": code,
        "tax_year": 2025,
        "territory": "Estatal",
        "name": f"Deduccion {code}",
        "type": "deduccion",
        "category": category,
        "percentage": None,
        "max_amount": 1200.0,
        "fixed_amount": 1200.0,
        "legal_reference": "Art. 81 LIRPF",
        "description": "Test deduction",
        "requirements_json": json.dumps(reqs or {"madre_trabajadora": True, "hijo_menor_3": True}),
        "questions_json": json.dumps(questions or [
            {"key": "madre_trabajadora", "text": "Es madre trabajadora?", "type": "bool"},
            {"key": "hijo_menor_3", "text": "Tiene hijos <3?", "type": "bool"},
        ]),
        "is_active": 1,
    }


class TestDeductionService:
    """Tests for DeductionService."""

    @pytest.mark.asyncio
    async def test_get_deductions_returns_list(self):
        """get_deductions should return parsed deductions."""
        from app.services.deduction_service import DeductionService

        row = _sample_deduction_row()
        db = _make_mock_db([row])
        service = DeductionService(db)

        deductions = await service.get_deductions("Estatal", 2025)
        assert len(deductions) == 1
        assert deductions[0]["code"] == "EST-MAT-1200"
        assert isinstance(deductions[0]["requirements"], dict)
        assert isinstance(deductions[0]["questions"], list)

    @pytest.mark.asyncio
    async def test_get_deductions_with_category(self):
        """get_deductions should filter by category."""
        from app.services.deduction_service import DeductionService

        db = _make_mock_db([_sample_deduction_row()])
        service = DeductionService(db)

        await service.get_deductions("Estatal", 2025, category="familia")
        # Verify the SQL included category filter
        call_args = db.execute.call_args
        assert "category = ?" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_evaluate_eligibility_all_met(self):
        """Should identify eligible deductions when all requirements met."""
        from app.services.deduction_service import DeductionService

        db = _make_mock_db([_sample_deduction_row()])
        service = DeductionService(db)

        result = await service.evaluate_eligibility(
            "Estatal", 2025,
            answers={"madre_trabajadora": True, "hijo_menor_3": True},
        )
        assert len(result["eligible"]) == 1
        assert len(result["not_eligible"]) == 0
        assert result["estimated_savings"] > 0

    @pytest.mark.asyncio
    async def test_evaluate_eligibility_not_met(self):
        """Should identify not-eligible deductions when requirements fail."""
        from app.services.deduction_service import DeductionService

        db = _make_mock_db([_sample_deduction_row()])
        service = DeductionService(db)

        result = await service.evaluate_eligibility(
            "Estatal", 2025,
            answers={"madre_trabajadora": False, "hijo_menor_3": True},
        )
        assert len(result["eligible"]) == 0
        assert len(result["not_eligible"]) == 1

    @pytest.mark.asyncio
    async def test_evaluate_eligibility_partial_answers(self):
        """Deductions with unanswered requirements should be 'maybe_eligible'."""
        from app.services.deduction_service import DeductionService

        db = _make_mock_db([_sample_deduction_row()])
        service = DeductionService(db)

        result = await service.evaluate_eligibility(
            "Estatal", 2025,
            answers={"madre_trabajadora": True},  # hijo_menor_3 not answered
        )
        assert len(result["maybe_eligible"]) == 1
        assert len(result["eligible"]) == 0

    @pytest.mark.asyncio
    async def test_evaluate_eligibility_no_answers(self):
        """With no answers, all should be maybe_eligible."""
        from app.services.deduction_service import DeductionService

        db = _make_mock_db([_sample_deduction_row()])
        service = DeductionService(db)

        result = await service.evaluate_eligibility("Estatal", 2025, answers={})
        assert len(result["maybe_eligible"]) == 1

    @pytest.mark.asyncio
    async def test_get_missing_questions(self):
        """Should return questions for unanswered requirements."""
        from app.services.deduction_service import DeductionService

        db = _make_mock_db([_sample_deduction_row()])
        service = DeductionService(db)

        missing = await service.get_missing_questions("Estatal", 2025, answers={})
        assert len(missing) == 2
        keys = {q["key"] for q in missing}
        assert "madre_trabajadora" in keys
        assert "hijo_menor_3" in keys

    @pytest.mark.asyncio
    async def test_get_missing_questions_skips_ruled_out(self):
        """Should skip questions for deductions already ruled out."""
        from app.services.deduction_service import DeductionService

        db = _make_mock_db([_sample_deduction_row()])
        service = DeductionService(db)

        # madre_trabajadora=False rules out this deduction
        missing = await service.get_missing_questions(
            "Estatal", 2025,
            answers={"madre_trabajadora": False},
        )
        assert len(missing) == 0

    @pytest.mark.asyncio
    async def test_estimated_savings_percentage_based(self):
        """Should calculate savings for percentage-based deductions."""
        from app.services.deduction_service import DeductionService

        row = _sample_deduction_row()
        row["fixed_amount"] = None
        row["percentage"] = 15.0
        row["max_amount"] = 9040.0
        row["requirements_json"] = json.dumps({"test_req": True})
        row["questions_json"] = json.dumps([])

        db = _make_mock_db([row])
        service = DeductionService(db)

        result = await service.evaluate_eligibility(
            "Estatal", 2025,
            answers={"test_req": True},
        )
        assert result["estimated_savings"] == 9040.0 * 15.0 / 100


# ============================================================
# DISCOVER DEDUCTIONS TOOL TESTS
# ============================================================

class TestDiscoverDeductionsTool:
    """Tests for the discover_deductions tool."""

    def test_tool_schema_valid(self):
        """Tool definition should have correct structure."""
        from app.tools.deduction_discovery_tool import DISCOVER_DEDUCTIONS_TOOL

        assert DISCOVER_DEDUCTIONS_TOOL["type"] == "function"
        func = DISCOVER_DEDUCTIONS_TOOL["function"]
        assert func["name"] == "discover_deductions"
        assert "parameters" in func
        assert "properties" in func["parameters"]

    def test_tool_registered(self):
        """Tool should be registered in ALL_TOOLS and TOOL_EXECUTORS."""
        from app.tools import ALL_TOOLS, TOOL_EXECUTORS

        tool_names = [t["function"]["name"] for t in ALL_TOOLS]
        assert "discover_deductions" in tool_names
        assert "discover_deductions" in TOOL_EXECUTORS

    @pytest.mark.asyncio
    async def test_tool_returns_formatted_response(self):
        """Tool should return formatted_response string."""
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        with patch("app.services.deduction_service.get_deduction_service") as mock_svc:
            svc = AsyncMock()
            svc.evaluate_eligibility = AsyncMock(return_value={
                "eligible": [{"code": "EST-MAT-1200", "name": "Test", "type": "deduccion",
                              "category": "familia", "fixed_amount": 1200}],
                "maybe_eligible": [],
                "not_eligible": [],
                "estimated_savings": 1200.0,
                "total_deductions": 16,
            })
            svc.get_missing_questions = AsyncMock(return_value=[])
            mock_svc.return_value = svc

            result = await discover_deductions_tool(ccaa="Estatal", tax_year=2025, answers={})

            assert result["success"] is True
            assert result["deductions_found"] == 1
            assert result["estimated_savings"] == 1200.0
            assert "formatted_response" in result
            assert "Deducciones IRPF" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_tool_handles_errors(self):
        """Tool should handle errors gracefully."""
        from app.tools.deduction_discovery_tool import discover_deductions_tool

        with patch("app.services.deduction_service.get_deduction_service") as mock_svc:
            mock_svc.side_effect = Exception("DB connection failed")

            result = await discover_deductions_tool()

            assert result["success"] is False
            assert "error" in result
            assert "formatted_response" in result


# ============================================================
# INTEGRATION: SERVICE + TOOL
# ============================================================

class TestDeductionIntegration:
    """Integration tests with multiple deductions."""

    @pytest.mark.asyncio
    async def test_multiple_deductions_mixed_eligibility(self):
        """Test with multiple deductions and various answer states."""
        from app.services.deduction_service import DeductionService

        rows = [
            _sample_deduction_row("EST-MAT-1200", "familia",
                                  {"madre_trabajadora": True, "hijo_menor_3": True}),
            _sample_deduction_row("EST-DONAT-GEN", "donativos",
                                  {"donativo_a_entidad_acogida": True},
                                  [{"key": "donativo_a_entidad_acogida", "text": "Donas?", "type": "bool"}]),
            _sample_deduction_row("EST-VIV-HAB", "vivienda",
                                  {"adquisicion_antes_2013": True, "deducia_antes_2013": True},
                                  [{"key": "adquisicion_antes_2013", "text": "Compra antes 2013?", "type": "bool"}]),
        ]

        db = _make_mock_db(rows)
        service = DeductionService(db)

        result = await service.evaluate_eligibility(
            "Estatal", 2025,
            answers={
                "madre_trabajadora": True,
                "hijo_menor_3": True,       # → eligible for EST-MAT-1200
                "donativo_a_entidad_acogida": False,  # → not eligible for EST-DONAT-GEN
                # adquisicion_antes_2013 not answered → maybe for EST-VIV-HAB
            },
        )

        assert len(result["eligible"]) == 1
        assert result["eligible"][0]["code"] == "EST-MAT-1200"
        assert len(result["not_eligible"]) == 1
        assert result["not_eligible"][0]["code"] == "EST-DONAT-GEN"
        assert len(result["maybe_eligible"]) == 1
        assert result["maybe_eligible"][0]["code"] == "EST-VIV-HAB"

    def test_compute_ccaa_fixed_amount_deduction(self):
        """Fixed-amount CCAA deduction should return the fixed amount."""
        from app.services.deduction_service import DeductionService

        service = DeductionService()
        eligible = [
            {"code": "MAD-NACIMIENTO", "name": "Nacimiento Madrid", "scope": "territorial",
             "fixed_amount": 721.70, "percentage": None, "max_amount": None},
        ]
        result = service.compute_ccaa_deduction_amounts(eligible, {})
        assert len(result) == 1
        assert result[0]["code"] == "MAD-NACIMIENTO"
        assert result[0]["amount"] == 721.70

    def test_compute_ccaa_rent_deduction(self):
        """Percentage-based rent deduction should compute from alquiler_pagado_anual."""
        from app.services.deduction_service import DeductionService

        service = DeductionService()
        eligible = [
            {"code": "MAD-ALQUILER-VIV", "name": "Alquiler Madrid", "scope": "territorial",
             "fixed_amount": None, "percentage": 30.0, "max_amount": 1237.20},
        ]
        user_data = {"alquiler_pagado_anual": 9600}  # 800/month
        result = service.compute_ccaa_deduction_amounts(eligible, user_data)
        assert len(result) == 1
        # 30% of 9600 = 2880, capped at 1237.20
        assert result[0]["amount"] == 1237.20

    def test_compute_ccaa_rent_deduction_below_max(self):
        """Rent deduction below max should not be capped."""
        from app.services.deduction_service import DeductionService

        service = DeductionService()
        eligible = [
            {"code": "AND-ALQUILER-VIV", "name": "Alquiler Andalucia", "scope": "territorial",
             "fixed_amount": None, "percentage": 15.0, "max_amount": 600.0},
        ]
        user_data = {"alquiler_pagado_anual": 3000}  # 250/month
        result = service.compute_ccaa_deduction_amounts(eligible, user_data)
        assert len(result) == 1
        # 15% of 3000 = 450, below max 600
        assert result[0]["amount"] == 450.0

    def test_compute_ccaa_skips_estatal_deductions(self):
        """Should skip estatal deductions (handled by simulator)."""
        from app.services.deduction_service import DeductionService

        service = DeductionService()
        eligible = [
            {"code": "EST-MAT-1200", "name": "Maternidad", "scope": "Estatal",
             "fixed_amount": 1200, "percentage": None, "max_amount": None},
            {"code": "MAD-NACIMIENTO", "name": "Nacimiento Madrid", "scope": "territorial",
             "fixed_amount": 721.70, "percentage": None, "max_amount": None},
        ]
        result = service.compute_ccaa_deduction_amounts(eligible, {})
        assert len(result) == 1
        assert result[0]["code"] == "MAD-NACIMIENTO"

    def test_compute_ccaa_multiple_deductions(self):
        """Should compute multiple CCAA deductions and sum them."""
        from app.services.deduction_service import DeductionService

        service = DeductionService()
        eligible = [
            {"code": "VAL-NACIMIENTO", "name": "Nacimiento Valencia", "scope": "territorial",
             "fixed_amount": 300.0, "percentage": None, "max_amount": None},
            {"code": "VAL-ALQUILER-VIV", "name": "Alquiler Valencia", "scope": "territorial",
             "fixed_amount": None, "percentage": 20.0, "max_amount": 950.0},
            {"code": "VAL-GUARDERIA", "name": "Guarderia Valencia", "scope": "territorial",
             "fixed_amount": 298.0, "percentage": None, "max_amount": None},
        ]
        user_data = {"alquiler_pagado_anual": 7200}
        result = service.compute_ccaa_deduction_amounts(eligible, user_data)
        assert len(result) == 3
        total = sum(d["amount"] for d in result)
        # 300 + min(20%*7200, 950) + 298 = 300 + 950 + 298 = 1548
        assert total == 1548.0

    def test_compute_ccaa_zero_user_data(self):
        """Percentage deductions with no user data should be skipped."""
        from app.services.deduction_service import DeductionService

        service = DeductionService()
        eligible = [
            {"code": "GAL-ALQUILER-VIV", "name": "Alquiler Galicia", "scope": "territorial",
             "fixed_amount": None, "percentage": 10.0, "max_amount": 300.0},
        ]
        result = service.compute_ccaa_deduction_amounts(eligible, {})
        assert len(result) == 0  # No rent data → no deduction

    @pytest.mark.asyncio
    async def test_deduction_no_requirements_is_maybe(self):
        """Deductions without requirements should be 'maybe_eligible'."""
        from app.services.deduction_service import DeductionService

        row = _sample_deduction_row()
        row["requirements_json"] = json.dumps({})
        row["questions_json"] = json.dumps([])

        db = _make_mock_db([row])
        service = DeductionService(db)

        result = await service.evaluate_eligibility("Estatal", 2025, answers={"x": True})
        assert len(result["maybe_eligible"]) == 1
