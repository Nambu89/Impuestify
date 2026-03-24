"""
Tests for XSD gaps implementation:
- Gap 1: Pension compensatoria ex-conyuge (Art. 55 LIRPF, casilla 0475)
- Gap 2: Anualidades por alimentos a hijos (Art. 64 LIRPF, casillas 0476-0478)
- Gap 3: Doble imposicion internacional (Art. 80 LIRPF, casilla 0588)
- Gap 4: Discapacidad descendientes MPYF (Art. 60.2, casilla 0519)
- Gap 5: Discapacidad ascendientes MPYF (Art. 60.3, casilla 0520)

All tests use mocked DB responses -- no live Turso connection required.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock
from dataclasses import dataclass
from typing import List, Dict, Any

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.utils.calculators.mpyf import MPYFCalculator
from app.utils.irpf_simulator import IRPFSimulator


# ─────────────────────────────────────────────────────────────
# Mock DB helper (same pattern as test_irpf_simulator.py)
# ─────────────────────────────────────────────────────────────

@dataclass
class MockRow:
    data: Dict[str, Any]

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, default)

    def keys(self):
        return self.data.keys()

    def values(self):
        return self.data.values()

    def items(self):
        return self.data.items()

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)


@dataclass
class MockResult:
    rows: List[MockRow]


MOCK_MPYF_ESTATAL = {
    "contribuyente": 5550,
    "contribuyente_65": 6700,
    "contribuyente_75": 8100,
    "descendiente_1": 2400,
    "descendiente_2": 2700,
    "descendiente_3": 4000,
    "descendiente_4_plus": 4500,
    "descendiente_menor_3": 2800,
    "ascendiente_65": 1150,
    "ascendiente_75": 2550,
    "discapacidad_33_65": 3000,
    "discapacidad_65_plus": 9000,
    "gastos_asistencia": 3000,
}

MOCK_TRABAJO_PARAMS = {
    "otros_gastos": 2000,
    "reduccion_max": 7302,
    "reduccion_rend_min": 14852,
    "reduccion_rend_mid": 17673.52,
    "reduccion_rend_max": 19747.5,
    "reduccion_factor_1": 1.75,
    "reduccion_factor_2": 1.14,
    "reduccion_mid_value": 2364.34,
    "cuotas_colegio_max": 500,
    "defensa_juridica_max": 300,
    "ss_empleado_pct": 6.35,
}

MOCK_INMUEBLES_PARAMS = {
    "reduccion_alquiler_vivienda": 60,
    "amortizacion_pct": 3,
}

MOCK_GENERAL_SCALE_ESTATAL = [
    {"tramo_num": 1, "base_hasta": 12450, "cuota_integra": 0, "resto_base": 12450, "tipo_aplicable": 9.5},
    {"tramo_num": 2, "base_hasta": 20200, "cuota_integra": 1182.75, "resto_base": 7750, "tipo_aplicable": 12},
    {"tramo_num": 3, "base_hasta": 35200, "cuota_integra": 2112.75, "resto_base": 15000, "tipo_aplicable": 15},
    {"tramo_num": 4, "base_hasta": 60000, "cuota_integra": 4362.75, "resto_base": 24800, "tipo_aplicable": 18.5},
    {"tramo_num": 5, "base_hasta": 300000, "cuota_integra": 8952.75, "resto_base": 240000, "tipo_aplicable": 22.5},
    {"tramo_num": 6, "base_hasta": 999999, "cuota_integra": 62952.75, "resto_base": 699999, "tipo_aplicable": 24.5},
]

MOCK_AHORRO_SCALE = [
    {"tramo_num": 1, "base_hasta": 6000, "cuota_integra": 0, "resto_base": 6000, "tipo_aplicable": 9.5},
    {"tramo_num": 2, "base_hasta": 50000, "cuota_integra": 570, "resto_base": 44000, "tipo_aplicable": 10.5},
]


def build_mock_db():
    """Build a mock DB that responds to tax_parameters and irpf_scales queries."""
    db = AsyncMock()

    async def mock_execute(query, params=None):
        query_lower = query.lower().strip()
        params = params or []

        if "tax_parameters" in query_lower and "select" in query_lower:
            category = params[0] if len(params) > 0 else ""
            jurisdiction = params[2] if len(params) > 2 else "Estatal"

            data = {}
            if category == "mpyf":
                data = MOCK_MPYF_ESTATAL
            elif category == "trabajo":
                data = MOCK_TRABAJO_PARAMS
            elif category == "inmuebles":
                data = MOCK_INMUEBLES_PARAMS

            rows = [MockRow({"param_key": k, "value": v}) for k, v in data.items()]
            return MockResult(rows=rows)

        if "irpf_scales" in query_lower and "ahorro" in query_lower:
            rows = [MockRow(row) for row in MOCK_AHORRO_SCALE]
            return MockResult(rows=rows)

        if "irpf_scales" in query_lower and "select" in query_lower:
            rows = [MockRow(row) for row in MOCK_GENERAL_SCALE_ESTATAL]
            return MockResult(rows=rows)

        return MockResult(rows=[])

    db.execute = mock_execute
    return db


# ─────────────────────────────────────────────────────────────
# Gap 4 & 5: MPYF disability tests (unit tests on MPYFCalculator)
# ─────────────────────────────────────────────────────────────

class TestMPYFDisabilityDescendants:
    """Gap 4: Discapacidad descendientes (Art. 60.2 LIRPF, casilla 0519)."""

    @pytest.mark.asyncio
    async def test_descendant_disability_33_adds_3000(self):
        """A descendant with 33-64% disability adds 3,000 EUR to MPYF."""
        db = build_mock_db()
        calc = MPYFCalculator(db)  # MPYFCalculator takes repo, not db
        # But MPYFCalculator.__init__ takes TaxParameterRepository
        from app.utils.tax_parameter_repository import TaxParameterRepository
        repo = TaxParameterRepository(db)
        calc = MPYFCalculator(repo)

        # Baseline: no disability
        base = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_descendientes=1,
        )
        # With 1 descendant 33% disability
        with_disc = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_descendientes=1,
            num_descendientes_discapacidad_33=1,
        )
        diff_est = with_disc["mpyf_estatal"] - base["mpyf_estatal"]
        assert diff_est == 3000, f"Expected +3000, got +{diff_est}"

    @pytest.mark.asyncio
    async def test_descendant_disability_65_adds_12000(self):
        """A descendant with 65%+ disability adds 9,000 + 3,000 gastos asistencia = 12,000 EUR."""
        from app.utils.tax_parameter_repository import TaxParameterRepository
        db = build_mock_db()
        repo = TaxParameterRepository(db)
        calc = MPYFCalculator(repo)

        base = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_descendientes=1,
        )
        with_disc = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_descendientes=1,
            num_descendientes_discapacidad_65=1,
        )
        diff_est = with_disc["mpyf_estatal"] - base["mpyf_estatal"]
        assert diff_est == 12000, f"Expected +12000, got +{diff_est}"


class TestMPYFDisabilityAscendants:
    """Gap 5: Discapacidad ascendientes (Art. 60.3 LIRPF, casilla 0520)."""

    @pytest.mark.asyncio
    async def test_ascendant_disability_33_adds_3000(self):
        """An ascendant with 33-64% disability adds 3,000 EUR to MPYF."""
        from app.utils.tax_parameter_repository import TaxParameterRepository
        db = build_mock_db()
        repo = TaxParameterRepository(db)
        calc = MPYFCalculator(repo)

        base = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_ascendientes_65=1,
        )
        with_disc = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_ascendientes_65=1,
            num_ascendientes_discapacidad_33=1,
        )
        diff_est = with_disc["mpyf_estatal"] - base["mpyf_estatal"]
        assert diff_est == 3000, f"Expected +3000, got +{diff_est}"

    @pytest.mark.asyncio
    async def test_ascendant_disability_65_adds_12000(self):
        """An ascendant with 65%+ disability adds 12,000 EUR."""
        from app.utils.tax_parameter_repository import TaxParameterRepository
        db = build_mock_db()
        repo = TaxParameterRepository(db)
        calc = MPYFCalculator(repo)

        base = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_ascendientes_65=1,
        )
        with_disc = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_ascendientes_65=1,
            num_ascendientes_discapacidad_65=1,
        )
        diff_est = with_disc["mpyf_estatal"] - base["mpyf_estatal"]
        assert diff_est == 12000, f"Expected +12000, got +{diff_est}"

    @pytest.mark.asyncio
    async def test_both_desc_and_asc_disability(self):
        """Both disabled descendant and ascendant stack correctly."""
        from app.utils.tax_parameter_repository import TaxParameterRepository
        db = build_mock_db()
        repo = TaxParameterRepository(db)
        calc = MPYFCalculator(repo)

        base = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_descendientes=1, num_ascendientes_65=1,
        )
        with_both = await calc.calculate(
            jurisdiction="Estatal", year=2024,
            edad_contribuyente=40, num_descendientes=1, num_ascendientes_65=1,
            num_descendientes_discapacidad_33=1,
            num_ascendientes_discapacidad_65=1,
        )
        diff_est = with_both["mpyf_estatal"] - base["mpyf_estatal"]
        # 3000 (desc 33%) + 12000 (asc 65%) = 15000
        assert diff_est == 15000, f"Expected +15000, got +{diff_est}"


# ─────────────────────────────────────────────────────────────
# Gaps 1-3: Simulator-level tests
# ─────────────────────────────────────────────────────────────

class TestPensionCompensatoria:
    """Gap 1: Pension compensatoria ex-conyuge (Art. 55 LIRPF, casilla 0475)."""

    @pytest.mark.asyncio
    async def test_pension_compensatoria_reduces_bi_general(self):
        """Pension compensatoria reduces base imponible general."""
        db = build_mock_db()
        sim = IRPFSimulator(db)

        base = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
        )
        with_pension = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            pension_compensatoria_exconyuge=6000,
        )
        assert with_pension["reduccion_pension_compensatoria"] == 6000
        assert with_pension["base_imponible_general"] < base["base_imponible_general"]
        assert with_pension["cuota_total"] < base["cuota_total"]

    @pytest.mark.asyncio
    async def test_pension_compensatoria_capped_at_bi_general(self):
        """Pension compensatoria cannot make base imponible go negative."""
        db = build_mock_db()
        sim = IRPFSimulator(db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=5000,
            pension_compensatoria_exconyuge=999999,
        )
        # bi_general should be 0, not negative
        assert result["base_imponible_general"] >= 0
        # The reduction should be capped at the available bi_general
        assert result["reduccion_pension_compensatoria"] <= 5000


class TestAnualidadesAlimentos:
    """Gap 2: Anualidades por alimentos a hijos (Art. 64 LIRPF, casillas 0476-0478)."""

    @pytest.mark.asyncio
    async def test_anualidades_taxed_separately(self):
        """Anualidades alimentos are taxed separately -- more favorable than adding to base."""
        db = build_mock_db()
        sim = IRPFSimulator(db)

        # Scenario A: alimentos taxed separately (correct)
        result_separate = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=50000,
            anualidades_alimentos_hijos=10000,
        )

        # Scenario B: alimentos added to main income (incorrect, higher tax)
        result_combined = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=60000,  # 50000 + 10000
        )

        # Separate taxation should produce lower total cuota
        assert result_separate["cuota_total"] < result_combined["cuota_total"], (
            f"Separate ({result_separate['cuota_total']}) should be less than "
            f"combined ({result_combined['cuota_total']})"
        )
        assert result_separate["cuota_anualidades_alimentos"] > 0


class TestDobleImposicion:
    """Gap 3: Doble imposicion internacional (Art. 80 LIRPF, casilla 0588)."""

    @pytest.mark.asyncio
    async def test_doble_imposicion_reduces_cuota(self):
        """Foreign taxes paid reduce the total cuota."""
        db = build_mock_db()
        sim = IRPFSimulator(db)

        base = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
        )
        with_foreign_tax = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            impuestos_pagados_extranjero=1000,
        )
        assert with_foreign_tax["deduccion_doble_imposicion"] == 1000
        assert with_foreign_tax["cuota_total"] < base["cuota_total"]
        expected_diff = base["cuota_total"] - with_foreign_tax["cuota_total"]
        assert abs(expected_diff - 1000) < 0.01

    @pytest.mark.asyncio
    async def test_doble_imposicion_capped_at_cuota(self):
        """Foreign tax deduction cannot exceed total cuota (no negative cuota)."""
        db = build_mock_db()
        sim = IRPFSimulator(db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=15000,
            impuestos_pagados_extranjero=999999,
        )
        assert result["cuota_total"] >= 0
        assert result["deduccion_doble_imposicion"] <= 999999


class TestAllGapsCombined:
    """Test all 5 gaps working together."""

    @pytest.mark.asyncio
    async def test_all_gaps_combined(self):
        """All 5 XSD gaps work together in a single simulation."""
        db = build_mock_db()
        sim = IRPFSimulator(db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=60000,
            # Gap 1: pension compensatoria
            pension_compensatoria_exconyuge=5000,
            # Gap 2: anualidades alimentos
            anualidades_alimentos_hijos=8000,
            # Gap 3: doble imposicion
            impuestos_pagados_extranjero=500,
            # Gap 4: disabled descendant
            num_descendientes=2,
            num_descendientes_discapacidad_33=1,
            # Gap 5: disabled ascendant
            num_ascendientes_65=1,
            num_ascendientes_discapacidad_65=1,
        )

        assert result["success"] is True
        # Gap 1: pension compensatoria applied
        assert result["reduccion_pension_compensatoria"] == 5000
        # Gap 2: anualidades alimentos taxed separately
        assert result["cuota_anualidades_alimentos"] > 0
        # Gap 3: doble imposicion deducted
        assert result["deduccion_doble_imposicion"] == 500
        # Gap 4 & 5: MPYF includes disability minimums
        # desc 33%: +3000, asc 65%: +12000
        mpyf_est = result["mpyf"]["mpyf_estatal"]
        # Base MPYF for age 40 (5550) + desc1 (2400) + desc2 (2700) + asc65 (1150) = 11800
        # Disability: +3000 (desc 33%) + 12000 (asc 65%) = 15000
        # Total: 11800 + 15000 = 26800
        assert mpyf_est == 26800, f"Expected MPYF 26800, got {mpyf_est}"
        # Overall cuota should be non-negative
        assert result["cuota_total"] >= 0
