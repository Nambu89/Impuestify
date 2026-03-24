"""
Tests for LossCompensationCalculator — Art. 48-49 LIRPF.

Covers:
- compensar_ahorro(): Prior year GP/RCM savings losses
- compensar_general(): Prior year GP general losses
- Integration with SavingsIncomeCalculator
"""
import pytest
from app.utils.calculators.loss_compensation import LossCompensationCalculator


@pytest.fixture
def calc():
    return LossCompensationCalculator()


# ==========================================================================
# Tests for compensar_ahorro()
# ==========================================================================

class TestCompensarAhorro:
    """Tests for savings base prior year loss compensation (Art. 49)."""

    def test_no_prior_losses_no_change(self, calc):
        """1. No prior losses: balances unchanged."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=1200.0,
            gp_ahorro_ejercicio=3500.0,
            year=2024,
        )
        assert result["rcm_final"] == 1200.0
        assert result["gp_ahorro_final"] == 3500.0
        assert result["base_ahorro_compensada"] == 4700.0
        assert result["gp_consumidas_por_ano"] == {}
        assert result["rcm_consumidas_por_ano"] == {}

    def test_gp_losses_fully_compensate_against_gp(self, calc):
        """2. GP losses fully absorbed by GP positivas."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=1000.0,
            gp_ahorro_ejercicio=5000.0,
            perdidas_gp_anteriores={2022: 2000.0},
            year=2024,
        )
        assert result["gp_ahorro_final"] == 3000.0
        assert result["rcm_final"] == 1000.0
        assert result["gp_consumidas_por_ano"] == {2022: 2000.0}
        assert result["gp_remanentes"] == {}

    def test_gp_losses_exceed_gp_cross_at_25_pct(self, calc):
        """3. GP losses exceed GP positivas, cross-compensate at 25% of RCM."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=4000.0,
            gp_ahorro_ejercicio=1000.0,
            perdidas_gp_anteriores={2022: 3000.0},
            year=2024,
        )
        # 1000 absorbed by GP, then 25% of 4000 = 1000 cross
        assert result["gp_ahorro_final"] == 0.0
        assert result["rcm_final"] == 3000.0
        assert result["gp_consumidas_por_ano"] == {2022: 2000.0}
        assert result["gp_remanentes"] == {2022: 1000.0}

    def test_rcm_losses_fully_compensate_against_rcm(self, calc):
        """4. RCM losses fully absorbed by RCM positivas."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=5000.0,
            gp_ahorro_ejercicio=1000.0,
            perdidas_rcm_anteriores={2021: 3000.0},
            year=2024,
        )
        assert result["rcm_final"] == 2000.0
        assert result["gp_ahorro_final"] == 1000.0
        assert result["rcm_consumidas_por_ano"] == {2021: 3000.0}

    def test_rcm_losses_exceed_rcm_cross_at_25_pct_gp(self, calc):
        """5. RCM losses exceed RCM positivas, cross at 25% of GP."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=1000.0,
            gp_ahorro_ejercicio=4000.0,
            perdidas_rcm_anteriores={2023: 3000.0},
            year=2024,
        )
        # 1000 absorbed by RCM, then 25% of 4000 = 1000 cross
        assert result["rcm_final"] == 0.0
        assert result["gp_ahorro_final"] == 3000.0
        assert result["rcm_consumidas_por_ano"] == {2023: 2000.0}
        assert result["rcm_remanentes"] == {2023: 1000.0}

    def test_multiple_years_fifo(self, calc):
        """6. Multiple years: oldest consumed first (FIFO)."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=500.0,
            gp_ahorro_ejercicio=3000.0,
            perdidas_gp_anteriores={2021: 1000.0, 2022: 1500.0, 2023: 800.0},
            year=2024,
        )
        # 2021: 1000 from GP → GP=2000
        # 2022: 1500 from GP → GP=500
        # 2023: 500 from GP → GP=0, then 25% of 500 RCM = 125 → remaining 175
        assert result["gp_ahorro_final"] == 0.0
        assert result["gp_consumidas_por_ano"][2021] == 1000.0
        assert result["gp_consumidas_por_ano"][2022] == 1500.0
        assert result["gp_consumidas_por_ano"][2023] == 625.0
        assert result["gp_remanentes"] == {2023: 175.0}

    def test_losses_beyond_4_years_ignored(self, calc):
        """7. Losses older than 4 years are ignored."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=1000.0,
            gp_ahorro_ejercicio=5000.0,
            perdidas_gp_anteriores={2019: 2000.0, 2020: 500.0},
            year=2024,
        )
        # 2019 is 5 years ago (only 2020-2023 valid), so ignored
        # 2020 is exactly 4 years ago, valid
        assert result["gp_consumidas_por_ano"] == {2020: 500.0}
        assert result["gp_ahorro_final"] == 4500.0

    def test_partial_compensation_track_remanentes(self, calc):
        """8. Partial compensation: remanentes tracked correctly."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=0.0,
            gp_ahorro_ejercicio=200.0,
            perdidas_gp_anteriores={2022: 1000.0},
            year=2024,
        )
        # Only 200 absorbed from GP, no RCM to cross-compensate
        assert result["gp_consumidas_por_ano"] == {2022: 200.0}
        assert result["gp_remanentes"] == {2022: 800.0}
        assert result["gp_ahorro_final"] == 0.0

    def test_research_example_478_69(self, calc):
        """9. Research example: 478.69 EUR losses from 2022, GP=3500, RCM=1200."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=1200.0,
            gp_ahorro_ejercicio=3500.0,
            perdidas_gp_anteriores={2022: 478.69},
            year=2024,
        )
        # 478.69 fully absorbed by GP 3500
        assert result["gp_ahorro_final"] == round(3500.0 - 478.69, 2)
        assert result["rcm_final"] == 1200.0
        assert result["gp_consumidas_por_ano"] == {2022: 478.69}
        assert result["gp_remanentes"] == {}
        expected_base = round(1200.0 + 3500.0 - 478.69, 2)
        assert result["base_ahorro_compensada"] == expected_base

    def test_current_year_negative_carries_forward(self, calc):
        """Current year negative balances tracked for carryforward."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=-500.0,
            gp_ahorro_ejercicio=200.0,
            year=2024,
        )
        assert result["rcm_negativo_ejercicio_pendiente"] == 500.0
        assert result["gp_negativo_ejercicio_pendiente"] == 0.0
        assert result["rcm_final"] == 0.0
        assert result["gp_ahorro_final"] == 200.0

    def test_both_gp_and_rcm_losses_combined(self, calc):
        """Both GP and RCM prior losses applied together."""
        result = calc.compensar_ahorro(
            rcm_ejercicio=2000.0,
            gp_ahorro_ejercicio=2000.0,
            perdidas_gp_anteriores={2022: 500.0},
            perdidas_rcm_anteriores={2023: 300.0},
            year=2024,
        )
        # GP losses: 500 from GP → GP=1500
        # RCM losses: 300 from RCM → RCM=1700
        assert result["gp_ahorro_final"] == 1500.0
        assert result["rcm_final"] == 1700.0
        assert result["gp_consumidas_por_ano"] == {2022: 500.0}
        assert result["rcm_consumidas_por_ano"] == {2023: 300.0}


# ==========================================================================
# Tests for compensar_general()
# ==========================================================================

class TestCompensarGeneral:
    """Tests for general base prior year loss compensation (Art. 48)."""

    def test_no_prior_losses_no_change(self, calc):
        """10. No prior losses: balances unchanged."""
        result = calc.compensar_general(
            rendimientos_netos=30000.0,
            gp_general_ejercicio=2000.0,
            year=2024,
        )
        assert result["base_general_compensada"] == 32000.0
        assert result["gp_consumidas_por_ano"] == {}

    def test_gp_losses_cross_at_25_pct_rendimientos(self, calc):
        """11. GP losses compensate at 25% limit of rendimientos."""
        result = calc.compensar_general(
            rendimientos_netos=20000.0,
            gp_general_ejercicio=0.0,
            perdidas_gp_general_anteriores={2022: 10000.0},
            year=2024,
        )
        # No GP positivas, cross at 25% of 20000 = 5000
        assert result["rendimientos_finales"] == 15000.0
        assert result["gp_general_final"] == 0.0
        assert result["gp_consumidas_por_ano"] == {2022: 5000.0}
        assert result["gp_remanentes"] == {2022: 5000.0}

    def test_gp_losses_fully_against_gp_first(self, calc):
        """12. GP losses fully compensate against GP positivas first."""
        result = calc.compensar_general(
            rendimientos_netos=10000.0,
            gp_general_ejercicio=5000.0,
            perdidas_gp_general_anteriores={2023: 3000.0},
            year=2024,
        )
        # 3000 fully absorbed by GP 5000
        assert result["gp_general_final"] == 2000.0
        assert result["rendimientos_finales"] == 10000.0
        assert result["gp_consumidas_por_ano"] == {2023: 3000.0}
        assert result["gp_remanentes"] == {}

    def test_current_year_gp_negative_plus_prior_losses(self, calc):
        """13. Current year GP negative + prior year losses (combined)."""
        result = calc.compensar_general(
            rendimientos_netos=20000.0,
            gp_general_ejercicio=-3000.0,
            perdidas_gp_general_anteriores={2022: 2000.0},
            year=2024,
        )
        # Phase 1: GP=-3000 compensates at 25% of 20000=5000 → comp=3000, rend=17000, GP=0
        # Phase 2: prior 2022=2000, no GP left, cross at 25% of 17000=4250 → comp=2000
        assert result["rendimientos_finales"] == 15000.0
        assert result["gp_general_final"] == 0.0
        assert result["compensacion_cruzada_ejercicio"] == 3000.0
        assert result["gp_consumidas_por_ano"] == {2022: 2000.0}
        assert result["gp_remanentes"] == {}

    def test_current_year_negative_rendimientos_compensate_gp(self, calc):
        """Negative rendimientos compensate against GP (no % limit)."""
        result = calc.compensar_general(
            rendimientos_netos=-2000.0,
            gp_general_ejercicio=5000.0,
            year=2024,
        )
        # rend=-2000 compensates fully against GP (no limit) → comp=2000
        assert result["rendimientos_finales"] == 0.0
        assert result["gp_general_final"] == 3000.0
        assert result["compensacion_cruzada_ejercicio"] == 2000.0

    def test_losses_older_than_4_years_ignored_general(self, calc):
        """Prior losses from >4 years ago are ignored in general base."""
        result = calc.compensar_general(
            rendimientos_netos=10000.0,
            gp_general_ejercicio=0.0,
            perdidas_gp_general_anteriores={2018: 5000.0, 2021: 1000.0},
            year=2024,
        )
        # 2018 too old (6 years), only 2021 valid
        assert result["gp_consumidas_por_ano"] == {2021: 1000.0}
        assert result["rendimientos_finales"] == 9000.0


# ==========================================================================
# Integration test with SavingsIncomeCalculator
# ==========================================================================

class TestSavingsIntegration:
    """Test that SavingsIncomeCalculator passes through loss compensation."""

    @pytest.fixture
    def mock_db(self):
        """Minimal mock DB that returns an empty savings scale."""
        class MockResult:
            def __init__(self):
                self.rows = []
        class MockDB:
            async def execute(self, query, params=None):
                return MockResult()
        return MockDB()

    @pytest.fixture
    def mock_repo(self):
        class MockRepo:
            pass
        return MockRepo()

    @pytest.mark.asyncio
    async def test_savings_with_prior_losses(self, mock_db, mock_repo):
        """14. savings.calculate() with perdidas_gp_anteriores passes through."""
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        calc = SavingsIncomeCalculator(mock_repo, mock_db)

        result = await calc.calculate(
            intereses=500.0,
            dividendos=200.0,
            ganancias_acciones=3000.0,
            perdidas_acciones=500.0,
            perdidas_gp_anteriores={2022: 400.0},
            year=2024,
        )

        # GP = 3000-500 = 2500. RCM = 700. No Phase 1 cross (both positive).
        # Phase 2: 400 from GP → GP = 2100
        assert result["loss_compensation"] is not None
        loss = result["loss_compensation"]
        assert loss["gp_ahorro_final"] == 2100.0
        assert loss["rcm_final"] == 700.0
        assert loss["gp_consumidas_por_ano"] == {2022: 400.0}

        # base_ahorro = 2100 + 700 = 2800 (no scale applied since mock returns empty)
        assert result["base_ahorro"] == 2800.0

    @pytest.mark.asyncio
    async def test_savings_without_prior_losses(self, mock_db, mock_repo):
        """savings.calculate() without prior losses has loss_compensation=None."""
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        calc = SavingsIncomeCalculator(mock_repo, mock_db)

        result = await calc.calculate(
            intereses=1000.0,
            ganancias_acciones=2000.0,
            year=2024,
        )

        assert result["loss_compensation"] is None
        assert result["base_ahorro"] == 3000.0
