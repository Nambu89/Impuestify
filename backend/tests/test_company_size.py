"""
Tests for the Company Size Calculator (Phase 1B).

Covers:
- Micro, small, medium, large classification
- 2-year consecutive rule (1 year exceeds, 1 doesn't)
- Audit obligation
- Balance abreviado / PyG abreviada eligibility
- 2025 vs 2026 thresholds
- Edge cases
"""
import pytest
from app.utils.calculators.company_size import (
    classify_company,
    YearData,
    _count_exceeded,
    _fits_category,
    THRESHOLDS_2025,
    THRESHOLDS_2026,
    AUDIT_THRESHOLDS_2025,
    AUDIT_THRESHOLDS_2026,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def make_year(activo: float, negocios: float, empleados: int) -> YearData:
    return YearData(activo=activo, negocios=negocios, empleados=empleados)


# ---------------------------------------------------------------------------
# Classification tests (2025 thresholds)
# ---------------------------------------------------------------------------

class TestMicroCompany:
    """Micro: activo <= 350K, negocios <= 700K, empleados <= 10."""

    def test_micro_both_years(self):
        y1 = make_year(200_000, 500_000, 5)
        y2 = make_year(250_000, 600_000, 7)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "micro"
        assert result.clasificacion_label == "Microempresa"
        assert "PYMES" in result.pgc_aplicable

    def test_micro_exactly_at_threshold(self):
        y1 = make_year(350_000, 700_000, 10)
        y2 = make_year(350_000, 700_000, 10)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "micro"

    def test_micro_zero_values(self):
        y1 = make_year(0, 0, 0)
        y2 = make_year(0, 0, 0)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "micro"


class TestSmallCompany:
    """Small: exceeds micro but fits pequena thresholds."""

    def test_small_typical(self):
        y1 = make_year(2_000_000, 5_000_000, 30)
        y2 = make_year(2_500_000, 6_000_000, 35)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "pequena"
        assert result.clasificacion_label == "Pequena empresa"
        assert "PYMES" in result.pgc_aplicable

    def test_small_at_upper_boundary(self):
        y1 = make_year(4_000_000, 8_000_000, 50)
        y2 = make_year(4_000_000, 8_000_000, 50)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "pequena"


class TestMediumCompany:
    """Medium: exceeds pequena but fits mediana thresholds."""

    def test_medium_typical(self):
        y1 = make_year(10_000_000, 25_000_000, 150)
        y2 = make_year(12_000_000, 30_000_000, 180)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "mediana"
        assert result.clasificacion_label == "Mediana empresa"
        assert "Normal" in result.pgc_aplicable


class TestLargeCompany:
    """Large: exceeds all mediana thresholds in both years."""

    def test_large_typical(self):
        y1 = make_year(50_000_000, 100_000_000, 500)
        y2 = make_year(60_000_000, 120_000_000, 600)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "grande"
        assert result.clasificacion_label == "Gran empresa"
        assert "Normal" in result.pgc_aplicable

    def test_large_has_required_notes(self):
        y1 = make_year(50_000_000, 100_000_000, 500)
        y2 = make_year(60_000_000, 120_000_000, 600)
        result = classify_company(y1, y2, ejercicio=2025)
        notes_text = " ".join(result.notas)
        assert "informe de gestion" in notes_text
        assert "flujos de efectivo" in notes_text


# ---------------------------------------------------------------------------
# 2-year consecutive rule
# ---------------------------------------------------------------------------

class TestTwoYearRule:
    """The company only loses its category if it exceeds 2/3 in BOTH years."""

    def test_one_year_exceeds_micro_one_doesnt(self):
        """Year 1 exceeds micro (2 of 3), year 2 does not. Still micro."""
        y1 = make_year(500_000, 900_000, 5)  # exceeds activo + negocios (2 of 3)
        y2 = make_year(200_000, 400_000, 5)  # within micro
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "micro"

    def test_both_years_exceed_micro_but_only_one_criteria(self):
        """Both years exceed 1 of 3 micro thresholds — still micro."""
        y1 = make_year(500_000, 600_000, 8)  # only activo exceeds (1 of 3)
        y2 = make_year(400_000, 600_000, 8)  # only activo exceeds (1 of 3)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "micro"

    def test_both_years_exceed_two_micro_thresholds(self):
        """Both years exceed 2 of 3 micro thresholds — not micro anymore."""
        y1 = make_year(500_000, 900_000, 8)  # activo + negocios exceed
        y2 = make_year(400_000, 800_000, 8)  # activo + negocios exceed
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion != "micro"

    def test_year2_exceeds_year1_doesnt_still_lower(self):
        """Year 2 exceeds pequena, year 1 does not. Still pequena."""
        y1 = make_year(3_000_000, 7_000_000, 40)  # within pequena
        y2 = make_year(5_000_000, 9_000_000, 60)  # exceeds 3 of 3 pequena
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "pequena"


# ---------------------------------------------------------------------------
# Audit obligation
# ---------------------------------------------------------------------------

class TestAuditObligation:
    """Art. 263 LSC: audit if exceeds 2 of 3 audit thresholds in both years."""

    def test_no_audit_small_company(self):
        y1 = make_year(1_000_000, 2_000_000, 20)
        y2 = make_year(1_200_000, 2_500_000, 25)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.auditoria_obligatoria is False

    def test_audit_required_large(self):
        y1 = make_year(3_000_000, 6_000_000, 60)  # exceeds all 3 audit thresholds
        y2 = make_year(3_500_000, 7_000_000, 55)  # exceeds all 3
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.auditoria_obligatoria is True

    def test_audit_exactly_two_of_three_both_years(self):
        """Exceeds activo + negocios but not empleados in both years."""
        y1 = make_year(3_000_000, 6_000_000, 30)  # activo + negocios exceed
        y2 = make_year(3_200_000, 6_500_000, 35)  # activo + negocios exceed
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.auditoria_obligatoria is True

    def test_audit_one_year_only(self):
        """Exceeds audit thresholds in only 1 year — no audit."""
        y1 = make_year(3_000_000, 6_000_000, 60)  # exceeds
        y2 = make_year(1_000_000, 2_000_000, 20)  # does not
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.auditoria_obligatoria is False

    def test_audit_note_present(self):
        y1 = make_year(3_000_000, 6_000_000, 60)
        y2 = make_year(3_500_000, 7_000_000, 55)
        result = classify_company(y1, y2, ejercicio=2025)
        assert any("auditoria" in n.lower() or "auditar" in n.lower() for n in result.notas)


# ---------------------------------------------------------------------------
# Balance abreviado / PyG abreviada
# ---------------------------------------------------------------------------

class TestAbbreviatedAccounts:

    def test_small_company_gets_all_abbreviated(self):
        y1 = make_year(2_000_000, 4_000_000, 30)
        y2 = make_year(2_500_000, 5_000_000, 35)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.balance_abreviado is True
        assert result.memoria_abreviada is True
        assert result.pyg_abreviada is True

    def test_large_company_no_abbreviated(self):
        y1 = make_year(50_000_000, 100_000_000, 500)
        y2 = make_year(60_000_000, 120_000_000, 600)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.balance_abreviado is False
        assert result.memoria_abreviada is False
        assert result.pyg_abreviada is False

    def test_medium_can_have_pyg_abreviada(self):
        """Medium company under PyG threshold still gets PyG abreviada."""
        y1 = make_year(10_000_000, 20_000_000, 200)
        y2 = make_year(10_500_000, 21_000_000, 210)
        result = classify_company(y1, y2, ejercicio=2025)
        assert result.clasificacion == "mediana"
        assert result.pyg_abreviada is True


# ---------------------------------------------------------------------------
# 2026 thresholds
# ---------------------------------------------------------------------------

class TestThresholds2026:
    """Verify that 2026 thresholds (EU Directive) are higher."""

    def test_micro_2025_becomes_micro_2026_too(self):
        """Under 2025 micro thresholds → definitely micro under 2026."""
        y1 = make_year(300_000, 600_000, 8)
        y2 = make_year(320_000, 650_000, 9)
        r25 = classify_company(y1, y2, ejercicio=2025)
        r26 = classify_company(y1, y2, ejercicio=2026)
        assert r25.clasificacion == "micro"
        assert r26.clasificacion == "micro"

    def test_small_2025_becomes_micro_2026(self):
        """Between 2025 micro and 2026 micro thresholds → micro under 2026."""
        y1 = make_year(400_000, 800_000, 8)  # exceeds 2025 micro (2 of 3)
        y2 = make_year(420_000, 850_000, 9)  # exceeds 2025 micro (2 of 3)
        r25 = classify_company(y1, y2, ejercicio=2025)
        r26 = classify_company(y1, y2, ejercicio=2026)
        assert r25.clasificacion == "pequena"
        assert r26.clasificacion == "micro"

    def test_2026_has_directive_note(self):
        y1 = make_year(200_000, 400_000, 5)
        y2 = make_year(200_000, 400_000, 5)
        result = classify_company(y1, y2, ejercicio=2026)
        assert any("Directiva UE 2023/2775" in n for n in result.notas)

    def test_audit_2026_higher_thresholds(self):
        """Just above 2025 audit thresholds but below 2026 → no audit in 2026."""
        y1 = make_year(3_000_000, 6_000_000, 55)  # exceeds 2025 audit (3/3)
        y2 = make_year(3_200_000, 6_500_000, 52)  # exceeds 2025 audit (3/3)
        r25 = classify_company(y1, y2, ejercicio=2025)
        r26 = classify_company(y1, y2, ejercicio=2026)
        assert r25.auditoria_obligatoria is True
        assert r26.auditoria_obligatoria is False


# ---------------------------------------------------------------------------
# Threshold detail / progress bars
# ---------------------------------------------------------------------------

class TestThresholdDetails:

    def test_umbrales_contain_all_keys(self):
        y1 = make_year(1_000_000, 3_000_000, 20)
        y2 = make_year(1_500_000, 3_500_000, 25)
        result = classify_company(y1, y2, ejercicio=2025)
        for key in ("activo", "negocios", "empleados"):
            assert key in result.umbrales_auditoria
            detail = result.umbrales_auditoria[key]
            assert "valor" in detail
            assert "limite" in detail
            assert "supera" in detail
            assert "porcentaje" in detail

    def test_porcentaje_calculation(self):
        y1 = make_year(1_425_000, 2_850_000, 25)
        y2 = make_year(1_425_000, 2_850_000, 25)
        result = classify_company(y1, y2, ejercicio=2025)
        # Avg activo = 1_425_000, audit limit = 2_850_000 → 50%
        assert result.umbrales_auditoria["activo"]["porcentaje"] == 50.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestInternalHelpers:

    def test_count_exceeded_zero(self):
        data = make_year(100_000, 200_000, 5)
        assert _count_exceeded(data, THRESHOLDS_2025["micro"]) == 0

    def test_count_exceeded_all_three(self):
        data = make_year(500_000, 900_000, 15)
        assert _count_exceeded(data, THRESHOLDS_2025["micro"]) == 3

    def test_count_exceeded_two(self):
        data = make_year(500_000, 900_000, 5)  # activo + negocios exceed
        assert _count_exceeded(data, THRESHOLDS_2025["micro"]) == 2

    def test_fits_category_true(self):
        y1 = make_year(200_000, 400_000, 5)
        y2 = make_year(200_000, 400_000, 5)
        assert _fits_category(y1, y2, THRESHOLDS_2025["micro"]) is True

    def test_fits_category_false(self):
        y1 = make_year(500_000, 900_000, 15)  # exceeds all 3
        y2 = make_year(500_000, 900_000, 15)  # exceeds all 3
        assert _fits_category(y1, y2, THRESHOLDS_2025["micro"]) is False


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

class TestDisclaimer:

    def test_disclaimer_present(self):
        y1 = make_year(200_000, 400_000, 5)
        y2 = make_year(200_000, 400_000, 5)
        result = classify_company(y1, y2, ejercicio=2025)
        assert "LSC" in result.disclaimer
        assert "Directiva UE 2023/2775" in result.disclaimer
