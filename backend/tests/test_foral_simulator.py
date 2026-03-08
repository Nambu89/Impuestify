"""
Tests for Foral IRPF Simulator Engine.

Covers:
- Regime dispatch: foral_vasco / foral_navarra vs comun
- Foral scale calculation (single unified scale, not estatal+autonomica split)
- Personal/family minimums as direct quota deductions
- EPSV reduction from base imponible
- Navarra 11-tramo scale
- Edge cases: zero income, very high income, multiple descendientes
- Seed data integrity: FORAL_MINIMOS constants
"""
import sys
import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Patch heavy optional dependencies before importing any app modules
# ---------------------------------------------------------------------------

def _mock(module_name, **attrs):
    if module_name not in sys.modules:
        m = MagicMock()
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[module_name] = m


_mock("jose")
_mock("jose.exceptions")
_mock("bcrypt")
_mock("slowapi")
_mock("slowapi.util")
_mock("slowapi.errors")
_mock("httpx", AsyncClient=MagicMock)
_mock("bs4", BeautifulSoup=MagicMock)
_mock("openai", OpenAI=MagicMock, AsyncOpenAI=MagicMock)
_mock("libsql_client")

# ---------------------------------------------------------------------------
# Imports after mocking
# ---------------------------------------------------------------------------

from app.utils.regime_classifier import classify_regime, is_foral  # noqa: E402
from app.utils.irpf_simulator import IRPFSimulator, FORAL_MINIMOS  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scale_rows(tramos):
    """Convert list of (tramo_num, base_hasta, cuota_integra, resto_base, tipo) to dicts."""
    return [
        {
            "tramo_num": t[0],
            "base_hasta": t[1],
            "cuota_integra": t[2],
            "resto_base": t[3],
            "tipo_aplicable": t[4],
        }
        for t in tramos
    ]


# Araba/Bizkaia 7-tramo foral scale (2025)
ARABA_TRAMOS = _make_scale_rows([
    (1, 17360.00,  0.00,       17360.00, 23.00),
    (2, 33280.00,  3992.80,    15920.00, 28.00),
    (3, 42240.00,  8449.60,     8960.00, 34.00),
    (4, 56760.00, 11496.00,    14520.00, 40.00),
    (5, 76320.00, 17304.00,    19560.00, 45.00),
    (6, 120840.00, 26106.00,   44520.00, 46.00),
    (7, 999999.00, 46585.20,  879159.00, 49.00),
])

# Navarra 11-tramo foral scale (2025)
NAVARRA_TRAMOS = _make_scale_rows([
    (1,   4484.00,     0.00,     4484.00, 13.00),
    (2,   8968.00,   582.92,     4484.00, 22.00),
    (3,  13452.00,  1569.40,     4484.00, 25.00),
    (4,  17936.00,  2690.40,     4484.00, 28.00),
    (5,  22420.00,  3945.92,     4484.00, 33.50),
    (6,  33632.00,  5448.56,    11212.00, 37.00),
    (7,  50448.00,  9596.00,    16816.00, 40.50),
    (8,  67264.00, 16406.48,    16816.00, 44.00),
    (9,  92372.00, 23805.52,    25108.00, 46.50),
    (10, 163128.00, 35475.72,   70756.00, 48.00),
    (11, 999999.00, 69438.60,  836871.00, 52.00),
])


def _make_work_result(rendimiento_neto_reducido: float) -> Dict[str, Any]:
    return {"rendimiento_neto_reducido": rendimiento_neto_reducido}


def _make_savings_result(base_ahorro: float = 0.0, cuota_ahorro_total: float = 0.0):
    return {"base_ahorro": base_ahorro, "cuota_ahorro_total": cuota_ahorro_total}


async def _run_simulate(
    jurisdiction: str,
    scale_rows: list,
    ingresos_trabajo: float = 40000.0,
    num_descendientes: int = 0,
    num_ascendientes_65: int = 0,
    num_ascendientes_75: int = 0,
    custodia_compartida: bool = False,
    aportaciones_epsv: float = 0.0,
    donativos_forales: float = 0.0,
    ingresos_actividad: float = 0.0,
    year: int = 2025,
) -> Dict[str, Any]:
    """
    Build a minimal IRPFSimulator with mocked sub-calculators and run simulate().
    """
    # Mock DB
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.rows = scale_rows
    mock_db.execute = AsyncMock(return_value=mock_result)

    # Build simulator with mocked sub-calculators
    simulator = IRPFSimulator.__new__(IRPFSimulator)
    simulator._db = mock_db

    # Work calculator mock
    simulator.work = MagicMock()
    simulator.work.calculate = AsyncMock(
        return_value=_make_work_result(max(0.0, ingresos_trabajo - ingresos_trabajo * 0.065))
    )

    # Activity calculator mock
    simulator.activity = MagicMock()
    if ingresos_actividad > 0:
        simulator.activity.calculate = AsyncMock(
            return_value={"rendimiento_neto_reducido": ingresos_actividad * 0.8}
        )

    # Other calculators (not needed for basic foral tests)
    simulator.savings = MagicMock()
    simulator.savings.calculate = AsyncMock(return_value=_make_savings_result())
    simulator.rental = MagicMock()
    simulator.rental.calculate = AsyncMock(return_value={"rendimiento_neto_reducido": 0.0})
    simulator.mpyf = MagicMock()
    simulator.mpyf.calculate = AsyncMock(return_value={"mpyf_estatal": 0.0, "mpyf_autonomico": 0.0})

    # IRPFCalculator (used for _apply_scale and common-regime path)
    from app.utils.irpf_calculator import IRPFCalculator
    simulator._irpf_calc = IRPFCalculator()
    simulator._irpf_calc.db = mock_db

    # TaxParameterRepository
    from app.utils.tax_parameter_repository import TaxParameterRepository
    simulator._repo = TaxParameterRepository(mock_db)

    return await simulator.simulate(
        jurisdiction=jurisdiction,
        year=year,
        ingresos_trabajo=ingresos_trabajo,
        num_descendientes=num_descendientes,
        num_ascendientes_65=num_ascendientes_65,
        num_ascendientes_75=num_ascendientes_75,
        custodia_compartida=custodia_compartida,
        aportaciones_epsv=aportaciones_epsv,
        donativos_forales=donativos_forales,
        ingresos_actividad=ingresos_actividad,
    )


# ===========================================================================
# Tests: Regime Classifier
# ===========================================================================

class TestRegimeClassifier:
    """classify_regime must return correct regimes for all foral territories."""

    def test_araba_is_foral_vasco(self):
        assert classify_regime("Araba") == "foral_vasco"

    def test_bizkaia_is_foral_vasco(self):
        assert classify_regime("Bizkaia") == "foral_vasco"

    def test_gipuzkoa_is_foral_vasco(self):
        assert classify_regime("Gipuzkoa") == "foral_vasco"

    def test_navarra_is_foral_navarra(self):
        assert classify_regime("Navarra") == "foral_navarra"

    def test_madrid_is_comun(self):
        assert classify_regime("Madrid") == "comun"

    def test_cataluna_is_comun(self):
        assert classify_regime("Cataluna") == "comun"

    def test_ceuta_regime(self):
        assert classify_regime("Ceuta") == "ceuta_melilla"

    def test_canarias_regime(self):
        assert classify_regime("Canarias") == "canarias"

    def test_is_foral_araba(self):
        assert is_foral("Araba") is True

    def test_is_foral_navarra(self):
        assert is_foral("Navarra") is True

    def test_is_foral_madrid_false(self):
        assert is_foral("Madrid") is False

    def test_unknown_ccaa_defaults_to_comun(self):
        assert classify_regime("UnknownProvince") == "comun"


# ===========================================================================
# Tests: FORAL_MINIMOS constants
# ===========================================================================

class TestForalMinimosConstants:
    """Validate FORAL_MINIMOS data integrity."""

    def test_foral_vasco_contribuyente(self):
        assert FORAL_MINIMOS["foral_vasco"]["contribuyente"] == 5472.00

    def test_foral_navarra_contribuyente(self):
        assert FORAL_MINIMOS["foral_navarra"]["contribuyente"] == 1084.00

    def test_foral_vasco_descendiente_1(self):
        assert FORAL_MINIMOS["foral_vasco"]["descendiente_1"] == 2808.00

    def test_foral_vasco_descendiente_2_greater_than_1(self):
        vasco = FORAL_MINIMOS["foral_vasco"]
        assert vasco["descendiente_2"] > vasco["descendiente_1"]

    def test_foral_navarra_descendiente_4_greater_than_3(self):
        navarra = FORAL_MINIMOS["foral_navarra"]
        assert navarra["descendiente_4_plus"] > navarra["descendiente_3"]

    def test_foral_vasco_ascendiente_75_greater_than_65(self):
        vasco = FORAL_MINIMOS["foral_vasco"]
        assert vasco["ascendiente_75"] > vasco["ascendiente_65"]

    def test_both_regimes_present(self):
        assert "foral_vasco" in FORAL_MINIMOS
        assert "foral_navarra" in FORAL_MINIMOS


# ===========================================================================
# Tests: _compute_foral_minimos
# ===========================================================================

class TestComputeForalMinimos:
    """Unit tests for IRPFSimulator._compute_foral_minimos."""

    def setup_method(self):
        self.sim = IRPFSimulator.__new__(IRPFSimulator)

    def test_no_family_returns_contribuyente_only_vasco(self):
        result = self.sim._compute_foral_minimos(
            regime="foral_vasco",
            num_descendientes=0,
            num_ascendientes_65=0,
            num_ascendientes_75=0,
            custodia_compartida=False,
        )
        assert result == FORAL_MINIMOS["foral_vasco"]["contribuyente"]

    def test_no_family_returns_contribuyente_only_navarra(self):
        result = self.sim._compute_foral_minimos(
            regime="foral_navarra",
            num_descendientes=0,
            num_ascendientes_65=0,
            num_ascendientes_75=0,
            custodia_compartida=False,
        )
        assert result == FORAL_MINIMOS["foral_navarra"]["contribuyente"]

    def test_two_descendientes_vasco(self):
        vasco = FORAL_MINIMOS["foral_vasco"]
        expected = (
            vasco["contribuyente"]
            + vasco["descendiente_1"]
            + vasco["descendiente_2"]
        )
        result = self.sim._compute_foral_minimos(
            regime="foral_vasco",
            num_descendientes=2,
            num_ascendientes_65=0,
            num_ascendientes_75=0,
            custodia_compartida=False,
        )
        assert abs(result - expected) < 0.01

    def test_custodia_compartida_halves_descendientes(self):
        vasco = FORAL_MINIMOS["foral_vasco"]
        full = self.sim._compute_foral_minimos(
            regime="foral_vasco",
            num_descendientes=1,
            num_ascendientes_65=0,
            num_ascendientes_75=0,
            custodia_compartida=False,
        )
        shared = self.sim._compute_foral_minimos(
            regime="foral_vasco",
            num_descendientes=1,
            num_ascendientes_65=0,
            num_ascendientes_75=0,
            custodia_compartida=True,
        )
        # Descendiente portion should be halved; contribuyente portion unchanged
        delta_full = full - vasco["contribuyente"]
        delta_shared = shared - vasco["contribuyente"]
        assert abs(delta_shared - delta_full / 2) < 0.01

    def test_ascendiente_75_larger_than_65(self):
        result_75 = self.sim._compute_foral_minimos(
            regime="foral_vasco",
            num_descendientes=0,
            num_ascendientes_65=0,
            num_ascendientes_75=1,
            custodia_compartida=False,
        )
        result_65 = self.sim._compute_foral_minimos(
            regime="foral_vasco",
            num_descendientes=0,
            num_ascendientes_65=1,
            num_ascendientes_75=0,
            custodia_compartida=False,
        )
        assert result_75 > result_65

    def test_four_or_more_descendientes_uses_4_plus_key(self):
        vasco = FORAL_MINIMOS["foral_vasco"]
        # 4 descendientes: uses keys 1, 2, 3, 4_plus
        result = self.sim._compute_foral_minimos(
            regime="foral_vasco",
            num_descendientes=4,
            num_ascendientes_65=0,
            num_ascendientes_75=0,
            custodia_compartida=False,
        )
        expected = (
            vasco["contribuyente"]
            + vasco["descendiente_1"]
            + vasco["descendiente_2"]
            + vasco["descendiente_3"]
            + vasco["descendiente_4_plus"]
        )
        assert abs(result - expected) < 0.01


# ===========================================================================
# Tests: _get_foral_scale
# ===========================================================================

class TestGetForalScale:
    """Test that _get_foral_scale raises ValueError when scale is missing."""

    @pytest.mark.asyncio
    async def test_raises_when_scale_missing(self):
        mock_db = MagicMock()
        empty_result = MagicMock()
        empty_result.rows = []
        mock_db.execute = AsyncMock(return_value=empty_result)

        sim = IRPFSimulator.__new__(IRPFSimulator)
        sim._db = mock_db

        with pytest.raises(ValueError, match="Escala foral no encontrada"):
            await sim._get_foral_scale("Araba", 2025)

    @pytest.mark.asyncio
    async def test_returns_scale_rows(self):
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.rows = ARABA_TRAMOS
        mock_db.execute = AsyncMock(return_value=mock_result)

        sim = IRPFSimulator.__new__(IRPFSimulator)
        sim._db = mock_db

        scale = await sim._get_foral_scale("Araba", 2025)
        assert len(scale) == 7
        assert scale[0]["tipo_aplicable"] == 23.00
        assert scale[-1]["tipo_aplicable"] == 49.00


# ===========================================================================
# Tests: Foral simulation — Araba (Pais Vasco)
# ===========================================================================

class TestForalVascoSimulation:
    """Integration-level tests for the foral vasco simulation path."""

    @pytest.mark.asyncio
    async def test_araba_returns_regime_key(self):
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        assert result["success"] is True
        assert result["regime"] == "foral_vasco"
        assert result["jurisdiction"] == "Araba"

    @pytest.mark.asyncio
    async def test_araba_cuota_integra_foral_is_positive(self):
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        assert result["cuota_integra_foral"] > 0

    @pytest.mark.asyncio
    async def test_araba_no_estatal_autonomica_split(self):
        """Foral path must NOT produce separate estatal/autonomica cuotas."""
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        assert result["cuota_integra_estatal"] == 0.0
        assert result["cuota_integra_autonomica"] == 0.0

    @pytest.mark.asyncio
    async def test_araba_minimos_reduce_cuota(self):
        """cuota_liquida must equal cuota_integra_foral minus minimos."""
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        expected = max(0.0, result["cuota_integra_foral"] - result["minimos_personales_familiares"])
        assert abs(result["cuota_liquida"] - expected) < 0.01

    @pytest.mark.asyncio
    async def test_araba_contribuyente_minimo_correct(self):
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        # No descendientes, no ascendientes -> minimo == contribuyente
        assert result["minimos_personales_familiares"] == pytest.approx(5472.00, abs=0.01)

    @pytest.mark.asyncio
    async def test_araba_two_descendientes_increases_minimo(self):
        result_no_children = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        result_two_children = await _run_simulate(
            "Araba", ARABA_TRAMOS, ingresos_trabajo=40000, num_descendientes=2
        )
        assert (
            result_two_children["minimos_personales_familiares"]
            > result_no_children["minimos_personales_familiares"]
        )

    @pytest.mark.asyncio
    async def test_araba_epsv_reduces_base(self):
        result_no_epsv = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        result_with_epsv = await _run_simulate(
            "Araba", ARABA_TRAMOS, ingresos_trabajo=40000, aportaciones_epsv=3000
        )
        assert result_with_epsv["base_imponible_general"] < result_no_epsv["base_imponible_general"]
        assert result_with_epsv["reduccion_epsv"] == pytest.approx(3000.0, abs=1.0)

    @pytest.mark.asyncio
    async def test_araba_epsv_capped_at_5000(self):
        result = await _run_simulate(
            "Araba", ARABA_TRAMOS, ingresos_trabajo=80000, aportaciones_epsv=8000
        )
        assert result["reduccion_epsv"] <= 5000.0

    @pytest.mark.asyncio
    async def test_araba_donativos_reduce_cuota_liquida(self):
        result_no_don = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        result_with_don = await _run_simulate(
            "Araba", ARABA_TRAMOS, ingresos_trabajo=40000, donativos_forales=500
        )
        expected_deduccion = round(500 * 0.30, 2)
        assert result_with_don["deduccion_donativos"] == pytest.approx(expected_deduccion, abs=0.01)
        assert result_with_don["cuota_liquida"] < result_no_don["cuota_liquida"]

    @pytest.mark.asyncio
    async def test_araba_zero_income(self):
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=0)
        assert result["success"] is True
        assert result["cuota_total"] >= 0
        assert result["base_imponible_general"] >= 0

    @pytest.mark.asyncio
    async def test_araba_very_high_income_uses_top_bracket(self):
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=500000)
        # At 49% top rate, cuota_integra_foral should be substantial
        assert result["cuota_integra_foral"] > 100000

    @pytest.mark.asyncio
    async def test_araba_cuota_diferencial_computed(self):
        result = await _run_simulate("Araba", ARABA_TRAMOS, ingresos_trabajo=40000)
        assert "cuota_diferencial" in result
        assert "tipo_resultado" in result
        assert result["tipo_resultado"] in ("a_pagar", "a_devolver")

    @pytest.mark.asyncio
    async def test_bizkaia_dispatches_foral_vasco(self):
        result = await _run_simulate("Bizkaia", ARABA_TRAMOS, ingresos_trabajo=35000)
        assert result["regime"] == "foral_vasco"
        assert result["jurisdiction"] == "Bizkaia"

    @pytest.mark.asyncio
    async def test_gipuzkoa_dispatches_foral_vasco(self):
        result = await _run_simulate("Gipuzkoa", ARABA_TRAMOS, ingresos_trabajo=35000)
        assert result["regime"] == "foral_vasco"
        assert result["jurisdiction"] == "Gipuzkoa"


# ===========================================================================
# Tests: Foral simulation — Navarra
# ===========================================================================

class TestForalNavarraSimulation:
    """Integration-level tests for the foral navarra simulation path."""

    @pytest.mark.asyncio
    async def test_navarra_returns_regime_key(self):
        result = await _run_simulate("Navarra", NAVARRA_TRAMOS, ingresos_trabajo=40000)
        assert result["success"] is True
        assert result["regime"] == "foral_navarra"
        assert result["jurisdiction"] == "Navarra"

    @pytest.mark.asyncio
    async def test_navarra_11_tramo_scale_high_income(self):
        """High income (>163.128 EUR) should reach tramo 11 at 52%."""
        result = await _run_simulate("Navarra", NAVARRA_TRAMOS, ingresos_trabajo=500000)
        # cuota_integra_foral should reflect the top rate of 52%
        assert result["cuota_integra_foral"] > 150000

    @pytest.mark.asyncio
    async def test_navarra_minimo_contribuyente_correct(self):
        result = await _run_simulate("Navarra", NAVARRA_TRAMOS, ingresos_trabajo=40000)
        assert result["minimos_personales_familiares"] == pytest.approx(1084.00, abs=0.01)

    @pytest.mark.asyncio
    async def test_navarra_donativos_at_25pct(self):
        result = await _run_simulate(
            "Navarra", NAVARRA_TRAMOS, ingresos_trabajo=40000, donativos_forales=1000
        )
        expected = round(1000 * 0.25, 2)
        assert result["deduccion_donativos"] == pytest.approx(expected, abs=0.01)

    @pytest.mark.asyncio
    async def test_navarra_zero_income(self):
        result = await _run_simulate("Navarra", NAVARRA_TRAMOS, ingresos_trabajo=0)
        assert result["success"] is True
        assert result["cuota_total"] >= 0

    @pytest.mark.asyncio
    async def test_navarra_cuota_integra_positive_for_middle_income(self):
        result = await _run_simulate("Navarra", NAVARRA_TRAMOS, ingresos_trabajo=30000)
        assert result["cuota_integra_foral"] > 0

    @pytest.mark.asyncio
    async def test_navarra_epsv_reduces_base(self):
        result_no = await _run_simulate("Navarra", NAVARRA_TRAMOS, ingresos_trabajo=40000)
        result_yes = await _run_simulate(
            "Navarra", NAVARRA_TRAMOS, ingresos_trabajo=40000, aportaciones_epsv=2000
        )
        assert result_yes["base_imponible_general"] < result_no["base_imponible_general"]


# ===========================================================================
# Tests: Common regime is NOT dispatched to foral path
# ===========================================================================

class TestCommonRegimeNotForal:
    """Verify that common-regime CCAA go through the normal simulate path."""

    @pytest.mark.asyncio
    async def test_madrid_not_foral(self):
        # Simulating Madrid through a mocked common-regime path
        mock_db = MagicMock()

        # For common path, it will try to get Estatal + CCAA scales from DB.
        # Return empty rows to trigger ValueError (common path) not foral ValueError.
        empty_result = MagicMock()
        empty_result.rows = []
        mock_db.execute = AsyncMock(return_value=empty_result)

        sim = IRPFSimulator.__new__(IRPFSimulator)
        sim._db = mock_db

        from app.utils.irpf_calculator import IRPFCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        sim._irpf_calc = IRPFCalculator()
        sim._irpf_calc.db = mock_db
        sim._repo = TaxParameterRepository(mock_db)
        sim.work = MagicMock()
        sim.work.calculate = AsyncMock(return_value={"rendimiento_neto_reducido": 35000.0})
        sim.activity = MagicMock()
        sim.activity.calculate = AsyncMock(return_value={"rendimiento_neto_reducido": 0.0})
        sim.savings = MagicMock()
        sim.savings.calculate = AsyncMock(return_value=_make_savings_result())
        sim.rental = MagicMock()
        sim.rental.calculate = AsyncMock(return_value={"rendimiento_neto_reducido": 0.0})
        sim.mpyf = MagicMock()
        sim.mpyf.calculate = AsyncMock(return_value={"mpyf_estatal": 0.0, "mpyf_autonomico": 0.0})

        # Madrid common path hits IRPFCalculator._get_scale which raises ValueError
        # (because our empty mock DB has no scales).
        # We just verify it does NOT raise the foral-specific error.
        with pytest.raises(Exception) as exc_info:
            await sim.simulate(jurisdiction="Madrid", year=2025, ingresos_trabajo=40000)
        # The error should NOT be about foral scales
        assert "Escala foral no encontrada" not in str(exc_info.value)


# ===========================================================================
# Tests: Foral scale arithmetic (pure unit, no async)
# ===========================================================================

class TestForalScaleArithmetic:
    """Verify that _apply_scale (inherited from IRPFCalculator) is correct for foral scales."""

    def setup_method(self):
        from app.utils.irpf_calculator import IRPFCalculator
        self.calc = IRPFCalculator()

    def test_araba_income_in_first_bracket(self):
        """Income of 10.000 EUR falls in tramo 1 (23%)."""
        cuota, breakdown = self.calc._apply_scale(10000.0, ARABA_TRAMOS)
        expected = 10000.0 * 0.23
        assert abs(cuota - expected) < 0.01
        assert len(breakdown) == 1

    def test_araba_income_at_bracket_boundary(self):
        """Income exactly at 17.360 EUR: all in tramo 1."""
        cuota, _ = self.calc._apply_scale(17360.0, ARABA_TRAMOS)
        expected = 17360.0 * 0.23
        assert abs(cuota - expected) < 0.01

    def test_araba_income_in_second_bracket(self):
        """Income of 25.000 EUR spans tramo 1 + tramo 2."""
        cuota, breakdown = self.calc._apply_scale(25000.0, ARABA_TRAMOS)
        # Tramo 1: 17360 * 0.23 = 3992.80
        # Tramo 2: (25000 - 17360) * 0.28 = 7640 * 0.28 = 2139.20
        expected = 3992.80 + 7640 * 0.28
        assert abs(cuota - expected) < 0.01
        assert len(breakdown) == 2

    def test_navarra_income_in_first_bracket(self):
        """Income of 3.000 EUR in Navarra tramo 1 (13%)."""
        cuota, _ = self.calc._apply_scale(3000.0, NAVARRA_TRAMOS)
        assert abs(cuota - 3000 * 0.13) < 0.01

    def test_navarra_income_spans_multiple_brackets(self):
        """Income of 50.000 EUR in Navarra spans 7 brackets."""
        cuota, breakdown = self.calc._apply_scale(50000.0, NAVARRA_TRAMOS)
        assert cuota > 0
        assert len(breakdown) == 7

    def test_araba_zero_income(self):
        cuota, breakdown = self.calc._apply_scale(0.0, ARABA_TRAMOS)
        assert cuota == 0.0

    def test_navarra_very_high_income_hits_top_bracket(self):
        """Income of 200.000 EUR in Navarra reaches tramo 11 (52%)."""
        cuota, breakdown = self.calc._apply_scale(200000.0, NAVARRA_TRAMOS)
        assert len(breakdown) == 11
        assert breakdown[-1]["tipo"] == 52.00
