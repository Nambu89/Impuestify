"""
Tests for ImputedIncomeCalculator — Renta imputada de inmuebles (Art. 85 LIRPF).

Covers:
1. Single property with revision catastral (1.1%)
2. Single property without revision (2%)
3. Property without valor catastral (50% of valor_adquisicion)
4. Prorrateo by days (306/365)
5. Prorrateo by titularidad (50%)
6. Nudo propietario returns 0
7. Multiple properties (3 different scenarios)
8. Legacy path (valor_catastral_total without inmuebles list)
9. Mixed: vivienda_habitual + disposicion (only disposicion imputes)
10. Edge case: 0 valor catastral AND 0 valor adquisicion -> 0
"""
import pytest

from app.utils.calculators.imputed_income import ImputedIncomeCalculator


@pytest.fixture
def calc():
    return ImputedIncomeCalculator()


# ---------------------------------------------------------------------------
# 1. Single property with revision catastral (1.1%)
# ---------------------------------------------------------------------------
def test_single_property_with_revision(calc):
    """200,000 EUR catastral revisado -> 200000 * 0.011 = 2,200 EUR."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 200_000,
            "revision_catastral": True,
            "uso": "disposicion",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 2200.0
    assert result["num_inmuebles_imputados"] == 1
    assert len(result["detalle_inmuebles"]) == 1
    detail = result["detalle_inmuebles"][0]
    assert detail["porcentaje_aplicado"] == 1.1
    assert detail["renta_imputada"] == 2200.0


# ---------------------------------------------------------------------------
# 2. Single property without revision (2%)
# ---------------------------------------------------------------------------
def test_single_property_without_revision(calc):
    """150,000 EUR catastral no revisado -> 150000 * 0.02 = 3,000 EUR."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 150_000,
            "revision_catastral": False,
            "uso": "disposicion",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 3000.0
    detail = result["detalle_inmuebles"][0]
    assert detail["porcentaje_aplicado"] == 2.0


# ---------------------------------------------------------------------------
# 3. Property without valor catastral (50% of valor_adquisicion, 1.1%)
# ---------------------------------------------------------------------------
def test_no_valor_catastral_uses_adquisicion(calc):
    """No catastral, adquisicion 300,000 -> 50% * 300000 * 0.011 = 1,650 EUR."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 0,
            "valor_adquisicion": 300_000,
            "uso": "disposicion",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 1650.0
    detail = result["detalle_inmuebles"][0]
    assert detail["porcentaje_aplicado"] == 1.1


# ---------------------------------------------------------------------------
# 4. Prorrateo by days (306/365)
# ---------------------------------------------------------------------------
def test_prorrateo_by_days(calc):
    """100,000 * 0.011 * (306/365) = 921.86 EUR (rounded)."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 100_000,
            "revision_catastral": True,
            "dias_disposicion": 306,
            "uso": "disposicion",
        }],
        year=2025,  # 2025 is not a leap year, 365 days
    )
    expected = round(100_000 * 0.011 * (306 / 365), 2)
    assert result["renta_imputada_total"] == expected
    assert result["detalle_inmuebles"][0]["dias_disposicion"] == 306


# ---------------------------------------------------------------------------
# 5. Prorrateo by titularidad (50%)
# ---------------------------------------------------------------------------
def test_prorrateo_by_titularidad(calc):
    """200,000 * 0.011 * 50% = 1,100 EUR."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 200_000,
            "revision_catastral": True,
            "porcentaje_titularidad": 50,
            "uso": "disposicion",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 1100.0


# ---------------------------------------------------------------------------
# 6. Nudo propietario returns 0
# ---------------------------------------------------------------------------
def test_nudo_propietario_no_imputation(calc):
    """Nudo propietario (es_usufructuario=False) should NOT impute."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 200_000,
            "revision_catastral": True,
            "es_usufructuario": False,
            "uso": "disposicion",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 0.0
    assert result["num_inmuebles_imputados"] == 0


# ---------------------------------------------------------------------------
# 7. Multiple properties (3 different scenarios)
# ---------------------------------------------------------------------------
def test_multiple_properties(calc):
    """Three properties: revisado, no revisado, and sin catastral."""
    inmuebles = [
        {
            "valor_catastral": 100_000,
            "revision_catastral": True,
            "uso": "disposicion",
        },
        {
            "valor_catastral": 80_000,
            "revision_catastral": False,
            "uso": "disposicion",
        },
        {
            "valor_catastral": 0,
            "valor_adquisicion": 200_000,
            "uso": "disposicion",
        },
    ]
    result = calc.calculate(inmuebles=inmuebles, year=2024)

    # Property 1: 100000 * 0.011 = 1100
    # Property 2: 80000 * 0.02 = 1600
    # Property 3: 50% * 200000 * 0.011 = 1100
    # Total = 3800
    assert result["renta_imputada_total"] == 3800.0
    assert result["num_inmuebles_imputados"] == 3
    assert len(result["detalle_inmuebles"]) == 3


# ---------------------------------------------------------------------------
# 8. Legacy path (valor_catastral_total without inmuebles list)
# ---------------------------------------------------------------------------
def test_legacy_path_aggregate(calc):
    """Legacy: valor_catastral_total=200000, revisado=True -> 2200 EUR."""
    result = calc.calculate(
        valor_catastral_total=200_000,
        valor_catastral_revisado=True,
        year=2024,
    )
    assert result["renta_imputada_total"] == 2200.0
    assert result["num_inmuebles_imputados"] == 1


def test_legacy_path_not_revised(calc):
    """Legacy: valor_catastral_total=100000, revisado=False -> 2000 EUR."""
    result = calc.calculate(
        valor_catastral_total=100_000,
        valor_catastral_revisado=False,
        year=2024,
    )
    assert result["renta_imputada_total"] == 2000.0


# ---------------------------------------------------------------------------
# 9. Mixed: vivienda_habitual + disposicion (only disposicion imputes)
# ---------------------------------------------------------------------------
def test_mixed_uso_only_disposicion_imputes(calc):
    """vivienda_habitual should be skipped, only disposicion imputes."""
    inmuebles = [
        {
            "valor_catastral": 300_000,
            "revision_catastral": True,
            "uso": "vivienda_habitual",
        },
        {
            "valor_catastral": 100_000,
            "revision_catastral": True,
            "uso": "disposicion",
        },
    ]
    result = calc.calculate(inmuebles=inmuebles, year=2024)
    # Only second property: 100000 * 0.011 = 1100
    assert result["renta_imputada_total"] == 1100.0
    assert result["num_inmuebles_imputados"] == 1


def test_arrendado_does_not_impute(calc):
    """Rented property should not generate imputed income."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 200_000,
            "revision_catastral": True,
            "uso": "arrendado",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 0.0
    assert result["num_inmuebles_imputados"] == 0


def test_afecto_does_not_impute(calc):
    """Property used in economic activity should not impute."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 200_000,
            "uso": "afecto",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 0.0


def test_en_construccion_does_not_impute(calc):
    """Property under construction should not impute."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 200_000,
            "uso": "en_construccion",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 0.0


# ---------------------------------------------------------------------------
# 10. Edge case: 0 valor catastral AND 0 valor adquisicion -> 0
# ---------------------------------------------------------------------------
def test_zero_catastral_and_zero_adquisicion(calc):
    """Both values zero -> base is 0, renta is 0."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 0,
            "valor_adquisicion": 0,
            "uso": "disposicion",
        }],
        year=2024,
    )
    assert result["renta_imputada_total"] == 0.0
    # Still counted as an imputed property (just with 0 amount)
    assert result["num_inmuebles_imputados"] == 1


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------
def test_empty_inmuebles_and_no_legacy(calc):
    """No properties and no legacy value -> 0."""
    result = calc.calculate(year=2024)
    assert result["renta_imputada_total"] == 0.0
    assert result["num_inmuebles_imputados"] == 0


def test_leap_year_affects_day_prorrateo(calc):
    """2024 is a leap year (366 days), prorrateo should use 366."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 100_000,
            "revision_catastral": True,
            "dias_disposicion": 183,
            "uso": "disposicion",
        }],
        year=2024,
    )
    expected = round(100_000 * 0.011 * (183 / 366), 2)
    assert result["renta_imputada_total"] == expected


def test_inmuebles_takes_priority_over_legacy(calc):
    """If inmuebles is provided, legacy valor_catastral_total is ignored."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 50_000,
            "revision_catastral": True,
            "uso": "disposicion",
        }],
        valor_catastral_total=999_999,
        year=2024,
    )
    # Should use inmuebles path: 50000 * 0.011 = 550
    assert result["renta_imputada_total"] == 550.0


def test_combined_prorrateo_days_and_titularidad(calc):
    """200,000 * 0.011 * (183/366) * (25/100) = 137.50."""
    result = calc.calculate(
        inmuebles=[{
            "valor_catastral": 200_000,
            "revision_catastral": True,
            "dias_disposicion": 183,
            "porcentaje_titularidad": 25,
            "uso": "disposicion",
        }],
        year=2024,  # leap year
    )
    expected = round(200_000 * 0.011 * (183 / 366) * (25 / 100), 2)
    assert result["renta_imputada_total"] == expected
