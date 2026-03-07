"""
Tests for seed_deductions_territorial_v2.py data integrity.

Validates the 11 new CCAA territorial deductions before DB insertion.
Does NOT require a live database connection — all tests work against
the in-memory Python data structures.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path setup and dependency mocks (same pattern as test_deductions.py)
# ---------------------------------------------------------------------------
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(backend_dir / "scripts"))

sys.modules.setdefault("jose", MagicMock())
sys.modules.setdefault("jose.jwt", MagicMock())
sys.modules.setdefault("passlib", MagicMock())
sys.modules.setdefault("passlib.context", MagicMock())
sys.modules.setdefault("bcrypt", MagicMock())
sys.modules.setdefault("slowapi", MagicMock())
sys.modules.setdefault("slowapi.util", MagicMock())
sys.modules.setdefault("slowapi.errors", MagicMock())

# Import the module under test
from seed_deductions_territorial_v2 import (
    ALL_TERRITORIAL_V2,
    VALID_CATEGORIES,
    VALID_TERRITORIES,
    validate_deductions,
)

# ---------------------------------------------------------------------------
# Constants derived from the seed data
# ---------------------------------------------------------------------------
ALL_DEDUCTIONS: list[dict] = [
    d for deductions in ALL_TERRITORIAL_V2.values() for d in deductions
]

REQUIRED_FIELDS = ("code", "name", "type", "category", "description",
                   "legal_reference", "requirements_json", "questions_json")

EXPECTED_MIN_DEDUCTIONS_PER_TERRITORY = 4

EXPECTED_CCAA = {
    "Galicia",
    "Asturias",
    "Cantabria",
    "La Rioja",
    "Aragon",
    "Castilla y Leon",
    "Castilla-La Mancha",
    "Extremadura",
    "Murcia",
    "Baleares",
    "Canarias",
}


# ===========================================================================
# Structural / cardinality tests
# ===========================================================================

class TestCoverage:
    """Tests that verify the expected CCAA and minimum deduction counts."""

    def test_all_expected_ccaa_present(self):
        """ALL_TERRITORIAL_V2 must contain exactly the 11 expected CCAA."""
        covered = set(ALL_TERRITORIAL_V2.keys())
        missing = EXPECTED_CCAA - covered
        assert not missing, f"Missing CCAA: {missing}"

    def test_no_unexpected_territories(self):
        """No extra territories should be present (avoids duplicate with v1)."""
        v1_territories = {
            "Araba", "Bizkaia", "Gipuzkoa", "Navarra",
            "Madrid", "Catalunia", "Andalucia", "Valencia",
        }
        unexpected = set(ALL_TERRITORIAL_V2.keys()) & v1_territories
        assert not unexpected, (
            f"Territories already in v1 seed found in v2: {unexpected}"
        )

    def test_minimum_deductions_per_territory(self):
        """Every CCAA must have at least 4 deductions."""
        insufficient = {
            territory: len(deductions)
            for territory, deductions in ALL_TERRITORIAL_V2.items()
            if len(deductions) < EXPECTED_MIN_DEDUCTIONS_PER_TERRITORY
        }
        assert not insufficient, (
            f"CCAA with fewer than {EXPECTED_MIN_DEDUCTIONS_PER_TERRITORY} deductions: "
            f"{insufficient}"
        )

    def test_total_deductions_at_least_55(self):
        """The batch must contribute at least 55 deductions in total."""
        total = len(ALL_DEDUCTIONS)
        assert total >= 55, f"Only {total} deductions — expected at least 55"


# ===========================================================================
# Uniqueness tests
# ===========================================================================

class TestUniqueness:
    """Tests that verify there are no duplicate entries."""

    def test_no_duplicate_codes_within_territory(self):
        """Within each territory, codes must be unique."""
        for territory, deductions in ALL_TERRITORIAL_V2.items():
            codes = [d["code"] for d in deductions]
            duplicates = [c for c in codes if codes.count(c) > 1]
            assert not duplicates, (
                f"Duplicate codes in {territory}: {list(set(duplicates))}"
            )

    def test_no_duplicate_code_territory_pairs(self):
        """The (code, territory) combination must be globally unique."""
        seen: set[tuple[str, str]] = set()
        duplicates = []
        for territory, deductions in ALL_TERRITORIAL_V2.items():
            for d in deductions:
                key = (d["code"], territory)
                if key in seen:
                    duplicates.append(key)
                seen.add(key)
        assert not duplicates, f"Duplicate (code, territory) pairs: {duplicates}"

    def test_all_codes_globally_unique(self):
        """All codes must be globally unique (no code repeated across CCAA)."""
        all_codes = [d["code"] for d in ALL_DEDUCTIONS]
        duplicates = list({c for c in all_codes if all_codes.count(c) > 1})
        assert not duplicates, (
            f"Codes appear in multiple CCAA (likely copy-paste error): {duplicates}"
        )

    def test_no_duplicate_names_within_territory(self):
        """Within each territory, deduction names must be unique."""
        for territory, deductions in ALL_TERRITORIAL_V2.items():
            names = [d["name"] for d in deductions]
            duplicates = [n for n in names if names.count(n) > 1]
            assert not duplicates, (
                f"Duplicate names in {territory}: {list(set(duplicates))}"
            )


# ===========================================================================
# Required fields tests
# ===========================================================================

class TestRequiredFields:
    """Tests that verify all required fields are present and non-empty."""

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_all_deductions_have_required_field(self, field: str):
        """Every deduction must have each required field populated."""
        missing = [
            f"{d.get('code', '??')} ({territory})"
            for territory, deductions in ALL_TERRITORIAL_V2.items()
            for d in deductions
            if not d.get(field)
        ]
        assert not missing, f"Deductions missing '{field}': {missing}"

    def test_all_codes_non_empty(self):
        """Codes must be non-empty strings."""
        bad = [d for d in ALL_DEDUCTIONS if not isinstance(d.get("code"), str) or not d["code"].strip()]
        assert not bad, f"Deductions with empty/invalid code: {[d.get('name') for d in bad]}"

    def test_all_types_are_valid(self):
        """'type' must be 'deduccion' or 'reduccion'."""
        valid_types = {"deduccion", "reduccion"}
        bad = [
            f"{d['code']}: {d.get('type')}"
            for d in ALL_DEDUCTIONS
            if d.get("type") not in valid_types
        ]
        assert not bad, f"Deductions with invalid 'type': {bad}"


# ===========================================================================
# Category tests
# ===========================================================================

class TestCategories:
    """Tests that verify category values are valid."""

    def test_all_categories_valid(self):
        """All deductions must use a recognised category value."""
        bad = [
            f"{d['code']}: '{d.get('category')}'"
            for d in ALL_DEDUCTIONS
            if d.get("category") not in VALID_CATEGORIES
        ]
        assert not bad, f"Deductions with invalid category: {bad}"

    def test_category_distribution_reasonable(self):
        """No single category should account for more than 60% of all deductions.

        This guards against accidental category monotony in the data.
        """
        from collections import Counter
        counts = Counter(d["category"] for d in ALL_DEDUCTIONS)
        total = len(ALL_DEDUCTIONS)
        overrepresented = [
            (cat, count)
            for cat, count in counts.items()
            if count / total > 0.60
        ]
        assert not overrepresented, (
            f"Category(ies) account for >60% of all deductions: {overrepresented}"
        )


# ===========================================================================
# Territory name tests
# ===========================================================================

class TestTerritories:
    """Tests that verify territory names are valid Spanish CCAA names."""

    def test_all_territories_in_valid_set(self):
        """Every key in ALL_TERRITORIAL_V2 must be in VALID_TERRITORIES."""
        invalid = set(ALL_TERRITORIAL_V2.keys()) - VALID_TERRITORIES
        assert not invalid, f"Unknown territory names: {invalid}"

    def test_territory_names_are_strings(self):
        """Territory keys must be non-empty strings."""
        bad = [t for t in ALL_TERRITORIAL_V2 if not isinstance(t, str) or not t.strip()]
        assert not bad, f"Invalid territory keys: {bad}"


# ===========================================================================
# JSON field tests
# ===========================================================================

class TestJsonFields:
    """Tests that verify JSON fields parse correctly and have the right shape."""

    def test_requirements_json_is_valid_dict(self):
        """requirements_json must parse to a dict."""
        bad = []
        for d in ALL_DEDUCTIONS:
            raw = d.get("requirements_json")
            if raw:
                try:
                    parsed = json.loads(raw)
                    if not isinstance(parsed, dict):
                        bad.append(f"{d['code']}: not a dict (got {type(parsed).__name__})")
                except json.JSONDecodeError as exc:
                    bad.append(f"{d['code']}: invalid JSON — {exc}")
        assert not bad, f"requirements_json errors: {bad}"

    def test_questions_json_is_valid_list(self):
        """questions_json must parse to a list."""
        bad = []
        for d in ALL_DEDUCTIONS:
            raw = d.get("questions_json")
            if raw:
                try:
                    parsed = json.loads(raw)
                    if not isinstance(parsed, list):
                        bad.append(f"{d['code']}: not a list (got {type(parsed).__name__})")
                except json.JSONDecodeError as exc:
                    bad.append(f"{d['code']}: invalid JSON — {exc}")
        assert not bad, f"questions_json errors: {bad}"

    def test_questions_have_key_and_text(self):
        """Every question in questions_json must have 'key' and 'text' fields."""
        bad = []
        for d in ALL_DEDUCTIONS:
            raw = d.get("questions_json")
            if raw:
                try:
                    questions = json.loads(raw)
                    for i, q in enumerate(questions):
                        if "key" not in q:
                            bad.append(f"{d['code']} q[{i}]: missing 'key'")
                        if "text" not in q:
                            bad.append(f"{d['code']} q[{i}]: missing 'text'")
                except json.JSONDecodeError:
                    pass  # Already caught by test_questions_json_is_valid_list
        assert not bad, f"Question field errors: {bad}"

    def test_questions_have_type_field(self):
        """Questions should declare a 'type' (bool/number/text)."""
        valid_question_types = {"bool", "number", "text", "select"}
        bad = []
        for d in ALL_DEDUCTIONS:
            raw = d.get("questions_json")
            if raw:
                try:
                    questions = json.loads(raw)
                    for i, q in enumerate(questions):
                        q_type = q.get("type")
                        if q_type and q_type not in valid_question_types:
                            bad.append(
                                f"{d['code']} q[{i}] '{q.get('key')}': "
                                f"unknown type '{q_type}'"
                            )
                except json.JSONDecodeError:
                    pass
        assert not bad, f"Question type errors: {bad}"


# ===========================================================================
# Amount / percentage consistency tests
# ===========================================================================

class TestAmounts:
    """Tests that verify financial fields are consistent."""

    def test_each_deduction_has_amount_or_percentage(self):
        """Each deduction must specify at least one of: fixed_amount, max_amount, percentage."""
        bad = [
            d["code"]
            for d in ALL_DEDUCTIONS
            if not any([
                d.get("fixed_amount"),
                d.get("max_amount"),
                d.get("percentage"),
            ])
        ]
        assert not bad, (
            f"Deductions with no amount/percentage specified: {bad}. "
            "Add fixed_amount, max_amount or percentage."
        )

    def test_percentage_in_valid_range(self):
        """Percentages must be between 0 and 100 (inclusive)."""
        bad = [
            f"{d['code']}: {d['percentage']}"
            for d in ALL_DEDUCTIONS
            if d.get("percentage") is not None
            and not (0 < d["percentage"] <= 100)
        ]
        assert not bad, f"Deductions with percentage out of 0-100 range: {bad}"

    def test_fixed_amounts_positive(self):
        """fixed_amount must be a positive number when present."""
        bad = [
            f"{d['code']}: {d['fixed_amount']}"
            for d in ALL_DEDUCTIONS
            if d.get("fixed_amount") is not None and d["fixed_amount"] <= 0
        ]
        assert not bad, f"Deductions with non-positive fixed_amount: {bad}"

    def test_max_amounts_positive_when_present(self):
        """max_amount must be positive when specified."""
        bad = [
            f"{d['code']}: {d['max_amount']}"
            for d in ALL_DEDUCTIONS
            if d.get("max_amount") is not None and d["max_amount"] <= 0
        ]
        assert not bad, f"Deductions with non-positive max_amount: {bad}"


# ===========================================================================
# validate_deductions() function tests
# ===========================================================================

class TestValidateFunction:
    """Tests for the built-in validation helper."""

    def test_validate_returns_no_errors_for_valid_data(self):
        """validate_deductions() must return an empty error list for the current data."""
        errors = validate_deductions(dry_run=False)
        assert errors == [], (
            f"validate_deductions() found {len(errors)} error(s):\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    def test_dry_run_does_not_raise(self, capsys):
        """dry_run=True must print output without raising exceptions."""
        errors = validate_deductions(dry_run=True)
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
        assert errors == []

    def test_validate_detects_missing_code(self):
        """validate_deductions() must flag a deduction with a missing code."""
        # Temporarily inject a broken deduction
        broken = {
            "code": "",
            "name": "Test",
            "type": "deduccion",
            "category": "familia",
            "description": "Test",
            "legal_reference": "Test",
            "requirements_json": json.dumps({"x": True}),
            "questions_json": json.dumps([{"key": "x", "text": "Test?", "type": "bool"}]),
        }
        original = ALL_TERRITORIAL_V2.get("Canarias", []).copy()
        ALL_TERRITORIAL_V2["Canarias"] = original + [broken]
        try:
            errors = validate_deductions(dry_run=False)
            assert any("MISSING code" in e for e in errors), (
                f"Expected MISSING code error. Got: {errors}"
            )
        finally:
            ALL_TERRITORIAL_V2["Canarias"] = original

    def test_validate_detects_invalid_category(self):
        """validate_deductions() must flag a deduction with an invalid category."""
        broken = {
            "code": "TEST-INVALID-CAT",
            "name": "Test Invalid Category",
            "type": "deduccion",
            "category": "not_a_real_category",
            "description": "Test",
            "legal_reference": "Art. X",
            "requirements_json": json.dumps({"x": True}),
            "questions_json": json.dumps([{"key": "x", "text": "Test?", "type": "bool"}]),
            "fixed_amount": 100.0,
        }
        original = ALL_TERRITORIAL_V2.get("Canarias", []).copy()
        ALL_TERRITORIAL_V2["Canarias"] = original + [broken]
        try:
            errors = validate_deductions(dry_run=False)
            assert any("INVALID category" in e for e in errors), (
                f"Expected INVALID category error. Got: {errors}"
            )
        finally:
            ALL_TERRITORIAL_V2["Canarias"] = original
