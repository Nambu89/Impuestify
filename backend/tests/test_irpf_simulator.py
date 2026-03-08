"""
Tests for the IRPF Simulator system.

Tests the complete data-driven IRPF simulation pipeline:
- TaxParameterRepository (with cache + fallback)
- WorkIncomeCalculator
- MPYFCalculator
- SavingsIncomeCalculator
- RentalIncomeCalculator
- IRPFSimulator orchestrator
- No hardcoded values in calculators

All tests use mocked DB responses — no live Turso connection required.
"""
import pytest
import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Dict, Any

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# ─────────────────────────────────────────────────────────────
# Mock DB helper
# ─────────────────────────────────────────────────────────────

@dataclass
class MockRow:
    """Simulates a Turso result row (dict-like access, supports dict() conversion)."""
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
    """Simulates a Turso execute() result."""
    rows: List[MockRow]


# Tax parameters as they would be in the DB (Estatal, 2024)
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

MOCK_MPYF_VALENCIA = {
    "contribuyente": 6105,
    "contribuyente_65": 7370,
    "contribuyente_75": 8910,
    "descendiente_1": 2640,
    "descendiente_2": 2970,
    "descendiente_3": 4400,
    "descendiente_4_plus": 4950,
    "descendiente_menor_3": 3080,
    "ascendiente_65": 1265,
    "ascendiente_75": 2805,
    "discapacidad_33_65": 3300,
    "discapacidad_65_plus": 9900,
    "gastos_asistencia": 3300,
}

MOCK_TRABAJO_PARAMS = {
    "otros_gastos": 2000,
    "reduccion_max": 6498,
    "reduccion_rend_min": 14852,
    "reduccion_rend_max": 19747.5,
    "cuotas_colegio_max": 500,
    "defensa_juridica_max": 300,
    "ss_empleado_pct": 6.35,
}

MOCK_INMUEBLES_PARAMS = {
    "reduccion_alquiler_vivienda": 60,
    "amortizacion_pct": 3,
}

# Ahorro scale (estatal)
MOCK_AHORRO_SCALE = [
    {"tramo_num": 1, "base_hasta": 6000, "cuota_integra": 0, "resto_base": 6000, "tipo_aplicable": 9.5},
    {"tramo_num": 2, "base_hasta": 50000, "cuota_integra": 570, "resto_base": 44000, "tipo_aplicable": 10.5},
    {"tramo_num": 3, "base_hasta": 200000, "cuota_integra": 5190, "resto_base": 150000, "tipo_aplicable": 11.5},
    {"tramo_num": 4, "base_hasta": 300000, "cuota_integra": 22440, "resto_base": 100000, "tipo_aplicable": 13.5},
    {"tramo_num": 5, "base_hasta": 999999, "cuota_integra": 35940, "resto_base": 699999, "tipo_aplicable": 14},
]

# General IRPF scale (estatal, 2024)
MOCK_GENERAL_SCALE_ESTATAL = [
    {"tramo_num": 1, "base_hasta": 12450, "cuota_integra": 0, "resto_base": 12450, "tipo_aplicable": 9.5},
    {"tramo_num": 2, "base_hasta": 20200, "cuota_integra": 1182.75, "resto_base": 7750, "tipo_aplicable": 12},
    {"tramo_num": 3, "base_hasta": 35200, "cuota_integra": 2112.75, "resto_base": 15000, "tipo_aplicable": 15},
    {"tramo_num": 4, "base_hasta": 60000, "cuota_integra": 4362.75, "resto_base": 24800, "tipo_aplicable": 18.5},
    {"tramo_num": 5, "base_hasta": 300000, "cuota_integra": 8952.75, "resto_base": 240000, "tipo_aplicable": 22.5},
    {"tramo_num": 6, "base_hasta": 999999, "cuota_integra": 62952.75, "resto_base": 699999, "tipo_aplicable": 24.5},
]

MOCK_GENERAL_SCALE_MADRID = [
    {"tramo_num": 1, "base_hasta": 12961.49, "cuota_integra": 0, "resto_base": 12961.49, "tipo_aplicable": 8.5},
    {"tramo_num": 2, "base_hasta": 18612.43, "cuota_integra": 1101.73, "resto_base": 5650.94, "tipo_aplicable": 10.7},
    {"tramo_num": 3, "base_hasta": 35200.42, "cuota_integra": 1706.38, "resto_base": 16588.00, "tipo_aplicable": 12.8},
    {"tramo_num": 4, "base_hasta": 55000.42, "cuota_integra": 3829.64, "resto_base": 19800.00, "tipo_aplicable": 17.4},
    {"tramo_num": 5, "base_hasta": 999999, "cuota_integra": 7274.84, "resto_base": 944998.58, "tipo_aplicable": 20.5},
]


def build_mock_db():
    """Build a mock DB that responds to tax_parameters and irpf_scales queries."""
    db = AsyncMock()

    async def mock_execute(query, params=None):
        query_lower = query.lower().strip()
        params = params or []

        # tax_parameters queries
        if "tax_parameters" in query_lower and "select" in query_lower:
            category = params[0] if len(params) > 0 else ""
            year = params[1] if len(params) > 1 else 2024
            jurisdiction = params[2] if len(params) > 2 else "Estatal"

            data = {}
            if category == "mpyf":
                if jurisdiction == "Comunitat Valenciana":
                    data = MOCK_MPYF_VALENCIA
                elif jurisdiction == "Estatal":
                    data = MOCK_MPYF_ESTATAL
                # Other CCAAs return empty → fallback to Estatal
            elif category == "trabajo":
                data = MOCK_TRABAJO_PARAMS
            elif category == "inmuebles":
                data = MOCK_INMUEBLES_PARAMS

            rows = [MockRow({"param_key": k, "value": v}) for k, v in data.items()]
            return MockResult(rows=rows)

        # irpf_scales ahorro queries
        if "irpf_scales" in query_lower and "ahorro" in query_lower:
            rows = [MockRow(row) for row in MOCK_AHORRO_SCALE]
            return MockResult(rows=rows)

        # irpf_scales general queries (for IRPFCalculator._get_scale)
        if "irpf_scales" in query_lower and "select" in query_lower:
            jurisdiction = params[0] if len(params) > 0 else "Estatal"
            if jurisdiction == "Estatal":
                rows = [MockRow(row) for row in MOCK_GENERAL_SCALE_ESTATAL]
            elif jurisdiction == "Comunidad de Madrid":
                rows = [MockRow(row) for row in MOCK_GENERAL_SCALE_MADRID]
            else:
                # Default: use estatal as fallback for unknown CCAAs
                rows = [MockRow(row) for row in MOCK_GENERAL_SCALE_ESTATAL]
            return MockResult(rows=rows)

        return MockResult(rows=[])

    db.execute = mock_execute
    return db


# ─────────────────────────────────────────────────────────────
# Tests: TaxParameterRepository
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_repo_get_params():
    """TaxParameterRepository.get_params returns correct values."""
    from app.utils.tax_parameter_repository import TaxParameterRepository

    db = build_mock_db()
    repo = TaxParameterRepository(db)

    params = await repo.get_params("mpyf", 2024, "Estatal")
    assert params["contribuyente"] == 5550
    assert params["descendiente_1"] == 2400
    assert params["discapacidad_65_plus"] == 9000


@pytest.mark.asyncio
async def test_repo_cache():
    """TaxParameterRepository caches results after first fetch."""
    from app.utils.tax_parameter_repository import TaxParameterRepository

    db = build_mock_db()
    repo = TaxParameterRepository(db)

    # First call → DB fetch
    await repo.get_params("trabajo", 2024, "Estatal")
    # Second call → should use cache (no second DB call)
    params = await repo.get_params("trabajo", 2024, "Estatal")

    assert params["otros_gastos"] == 2000
    assert params["reduccion_max"] == 6498


@pytest.mark.asyncio
async def test_repo_fallback_to_estatal():
    """get_with_fallback falls back to Estatal when CCAA has no overrides."""
    from app.utils.tax_parameter_repository import TaxParameterRepository

    db = build_mock_db()
    repo = TaxParameterRepository(db)

    # "Comunidad de Madrid" has no MPYF overrides → should fallback to Estatal
    params = await repo.get_with_fallback("mpyf", 2024, "Comunidad de Madrid")
    assert params["contribuyente"] == 5550  # Estatal value


@pytest.mark.asyncio
async def test_repo_ccaa_override():
    """CCAA-specific overrides are returned when available."""
    from app.utils.tax_parameter_repository import TaxParameterRepository

    db = build_mock_db()
    repo = TaxParameterRepository(db)

    params = await repo.get_with_fallback("mpyf", 2024, "Comunitat Valenciana")
    assert params["contribuyente"] == 6105  # Valencia override


# ─────────────────────────────────────────────────────────────
# Tests: WorkIncomeCalculator
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_work_income_basic():
    """WorkIncomeCalculator computes net work income correctly."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.work_income import WorkIncomeCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = WorkIncomeCalculator(repo)

    result = await calc.calculate(ingresos_brutos=30000, year=2024)

    assert result["ingresos_brutos"] == 30000
    # SS auto-estimated: 30000 * 6.35% = 1905
    assert result["desglose_gastos"]["ss_empleado"] == pytest.approx(1905, abs=1)
    # Otros gastos: 2000
    assert result["desglose_gastos"]["otros_gastos"] == 2000
    # Total deducibles: 1905 + 2000 = 3905
    assert result["gastos_deducibles"] == pytest.approx(3905, abs=1)
    # Rendimiento neto: 30000 - 3905 = 26095
    assert result["rendimiento_neto"] == pytest.approx(26095, abs=1)
    # Rendimiento neto > 19747.5 → no reduction
    assert result["reduccion_trabajo"] == 0
    assert result["rendimiento_neto_reducido"] == pytest.approx(26095, abs=1)


@pytest.mark.asyncio
async def test_work_income_low_salary_full_reduction():
    """Low salary gets full work income reduction."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.work_income import WorkIncomeCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = WorkIncomeCalculator(repo)

    result = await calc.calculate(ingresos_brutos=15000, year=2024)

    # SS: 15000 * 6.35% = 952.5
    # Otros: 2000
    # Rendimiento neto: 15000 - 2952.5 = 12047.5
    # 12047.5 < 14852 → full reduction of 6498
    assert result["rendimiento_neto"] == pytest.approx(12047.5, abs=1)
    assert result["reduccion_trabajo"] == pytest.approx(6498, abs=1)
    expected_reduced = max(0, 12047.5 - 6498)
    assert result["rendimiento_neto_reducido"] == pytest.approx(expected_reduced, abs=1)


@pytest.mark.asyncio
async def test_work_income_with_explicit_ss():
    """Explicit SS contribution is used instead of auto-estimate."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.work_income import WorkIncomeCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = WorkIncomeCalculator(repo)

    result = await calc.calculate(ingresos_brutos=30000, ss_empleado=2000, year=2024)

    assert result["desglose_gastos"]["ss_empleado"] == 2000


# ─────────────────────────────────────────────────────────────
# Tests: MPYFCalculator
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mpyf_single_taxpayer():
    """Single taxpayer, 35 years, no dependents → minimum personal."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.mpyf import MPYFCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = MPYFCalculator(repo)

    result = await calc.calculate(jurisdiction="Estatal", year=2024)

    assert result["mpyf_estatal"] == 5550
    assert result["mpyf_autonomico"] == 5550


@pytest.mark.asyncio
async def test_mpyf_over_65():
    """Taxpayer >65 years gets increased minimum."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.mpyf import MPYFCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = MPYFCalculator(repo)

    result = await calc.calculate(
        jurisdiction="Estatal", year=2024, edad_contribuyente=68
    )
    assert result["mpyf_estatal"] == 6700


@pytest.mark.asyncio
async def test_mpyf_over_75():
    """Taxpayer >75 years gets maximum personal minimum."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.mpyf import MPYFCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = MPYFCalculator(repo)

    result = await calc.calculate(
        jurisdiction="Estatal", year=2024, edad_contribuyente=78
    )
    assert result["mpyf_estatal"] == 8100


@pytest.mark.asyncio
async def test_mpyf_with_children():
    """MPYF with 2 children, one under 3 years."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.mpyf import MPYFCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = MPYFCalculator(repo)

    result = await calc.calculate(
        jurisdiction="Estatal",
        year=2024,
        edad_contribuyente=35,
        num_descendientes=2,
        anios_nacimiento_desc=[2022, 2019],
    )

    # 5550 (contribuyente) + 2400 (1st child) + 2800 (child <3: 2024-2022=2) + 2700 (2nd child)
    expected = 5550 + 2400 + 2800 + 2700
    assert result["mpyf_estatal"] == expected


@pytest.mark.asyncio
async def test_mpyf_shared_custody():
    """Shared custody halves children minimums."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.mpyf import MPYFCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = MPYFCalculator(repo)

    result = await calc.calculate(
        jurisdiction="Estatal",
        year=2024,
        edad_contribuyente=35,
        num_descendientes=1,
        anios_nacimiento_desc=[2022],
        custodia_compartida=True,
    )

    # 5550 + (2400 + 2800) / 2 = 5550 + 2600 = 8150
    assert result["mpyf_estatal"] == 8150


@pytest.mark.asyncio
async def test_mpyf_valencia_override():
    """Valencia has autonomous MPYF overrides."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.mpyf import MPYFCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = MPYFCalculator(repo)

    result = await calc.calculate(
        jurisdiction="Comunitat Valenciana", year=2024
    )

    assert result["mpyf_estatal"] == 5550
    assert result["mpyf_autonomico"] == 6105  # Valencia override


@pytest.mark.asyncio
async def test_mpyf_disability():
    """Disability percentage adds to MPYF."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.mpyf import MPYFCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = MPYFCalculator(repo)

    # 33% disability
    result = await calc.calculate(
        jurisdiction="Estatal", year=2024, discapacidad_contribuyente=33
    )
    assert result["mpyf_estatal"] == 5550 + 3000  # +discapacidad_33_65

    # 65% disability
    result = await calc.calculate(
        jurisdiction="Estatal", year=2024, discapacidad_contribuyente=65
    )
    assert result["mpyf_estatal"] == 5550 + 9000 + 3000  # +discapacidad_65_plus + gastos_asistencia


# ─────────────────────────────────────────────────────────────
# Tests: SavingsIncomeCalculator
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_savings_basic():
    """Basic savings income calculation."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.savings_income import SavingsIncomeCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = SavingsIncomeCalculator(repo, db)

    result = await calc.calculate(
        intereses=500, dividendos=1200, year=2024, jurisdiction="Estatal"
    )

    assert result["base_ahorro"] == 1700
    # 1700 in first tramo (0-6000) at 9.5% = 161.5 per scale (estatal + autonomico)
    assert result["cuota_ahorro_estatal"] == pytest.approx(161.5, abs=0.1)
    assert result["cuota_ahorro_autonomica"] == pytest.approx(161.5, abs=0.1)
    assert result["cuota_ahorro_total"] == pytest.approx(323.0, abs=0.1)


@pytest.mark.asyncio
async def test_savings_zero():
    """No savings income → zero tax."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.savings_income import SavingsIncomeCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = SavingsIncomeCalculator(repo, db)

    result = await calc.calculate(year=2024, jurisdiction="Estatal")
    assert result["base_ahorro"] == 0
    assert result["cuota_ahorro_total"] == 0


# ─────────────────────────────────────────────────────────────
# Tests: RentalIncomeCalculator
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rental_basic():
    """Basic rental income with housing reduction."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.rental_income import RentalIncomeCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = RentalIncomeCalculator(repo)

    result = await calc.calculate(
        ingresos_alquiler=12000,
        valor_adquisicion=200000,
        year=2024,
    )

    # Amortization: 200000 * 3% = 6000
    assert result["desglose_gastos"]["amortizacion"] == 6000
    # Net: 12000 - 6000 = 6000
    assert result["rendimiento_neto"] == 6000
    # 60% reduction: 6000 * 0.6 = 3600
    assert result["reduccion_vivienda"] == 3600
    # Net reduced: 6000 - 3600 = 2400
    assert result["rendimiento_neto_reducido"] == 2400


@pytest.mark.asyncio
async def test_rental_expenses_capped():
    """Deductible expenses cannot exceed rental income."""
    from app.utils.tax_parameter_repository import TaxParameterRepository
    from app.utils.calculators.rental_income import RentalIncomeCalculator

    db = build_mock_db()
    repo = TaxParameterRepository(db)
    calc = RentalIncomeCalculator(repo)

    result = await calc.calculate(
        ingresos_alquiler=5000,
        gastos_comunidad=3000,
        valor_adquisicion=200000,  # amortization = 6000
        year=2024,
    )

    # Total expenses = 3000 + 6000 = 9000, but capped at 5000 (income)
    assert result["total_gastos"] == 5000
    assert result["rendimiento_neto"] == 0
    assert result["reduccion_vivienda"] == 0


# ─────────────────────────────────────────────────────────────
# Tests: IRPFSimulator (orchestrator)
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_simulator_basic():
    """Full simulation: 30,000€ salary, Madrid, single."""
    from app.utils.irpf_simulator import IRPFSimulator

    db = build_mock_db()
    sim = IRPFSimulator(db)

    result = await sim.simulate(
        jurisdiction="Comunidad de Madrid",
        year=2024,
        ingresos_trabajo=30000,
    )

    assert result["success"] is True
    assert result["year"] == 2024
    assert result["jurisdiction"] == "Comunidad de Madrid"
    # Work income calculated
    assert result["trabajo"]["ingresos_brutos"] == 30000
    assert result["trabajo"]["rendimiento_neto_reducido"] > 0
    # MPYF applied
    assert result["mpyf"]["mpyf_estatal"] == 5550
    # Cuota total > 0
    assert result["cuota_total"] > 0
    # Cuota líquida < cuota íntegra (MPYF reduces tax)
    assert result["cuota_liquida_general"] < result["cuota_integra_general"]
    # Tipo medio is reasonable (5-25% range for 30k)
    assert 5 < result["tipo_medio"] < 25


@pytest.mark.asyncio
async def test_simulator_with_family():
    """Simulation with family: 1 child under 3, shared custody."""
    from app.utils.irpf_simulator import IRPFSimulator

    db = build_mock_db()
    sim = IRPFSimulator(db)

    result_single = await sim.simulate(
        jurisdiction="Comunidad de Madrid",
        year=2024,
        ingresos_trabajo=40000,
    )

    result_family = await sim.simulate(
        jurisdiction="Comunidad de Madrid",
        year=2024,
        ingresos_trabajo=40000,
        num_descendientes=1,
        anios_nacimiento_desc=[2022],
        custodia_compartida=True,
    )

    # Family MPYF should be higher
    assert result_family["mpyf"]["mpyf_estatal"] > result_single["mpyf"]["mpyf_estatal"]
    # Family tax should be lower
    assert result_family["cuota_total"] < result_single["cuota_total"]


@pytest.mark.asyncio
async def test_simulator_with_savings():
    """Simulation with savings income."""
    from app.utils.irpf_simulator import IRPFSimulator

    db = build_mock_db()
    sim = IRPFSimulator(db)

    result = await sim.simulate(
        jurisdiction="Comunidad de Madrid",
        year=2024,
        ingresos_trabajo=30000,
        intereses=500,
        dividendos=1200,
    )

    assert result["base_imponible_ahorro"] == 1700
    assert result["cuota_ahorro"] > 0
    assert result["ahorro"] is not None


@pytest.mark.asyncio
async def test_simulator_with_rental():
    """Simulation with rental income."""
    from app.utils.irpf_simulator import IRPFSimulator

    db = build_mock_db()
    sim = IRPFSimulator(db)

    result = await sim.simulate(
        jurisdiction="Comunidad de Madrid",
        year=2024,
        ingresos_trabajo=30000,
        ingresos_alquiler=12000,
        valor_adquisicion_inmueble=200000,
    )

    assert result["inmuebles"] is not None
    assert result["inmuebles"]["reduccion_vivienda"] > 0
    # BI general includes both work and rental
    assert result["base_imponible_general"] > result["trabajo"]["rendimiento_neto_reducido"]


@pytest.mark.asyncio
async def test_simulator_zero_income():
    """Zero income produces zero tax."""
    from app.utils.irpf_simulator import IRPFSimulator

    db = build_mock_db()
    sim = IRPFSimulator(db)

    result = await sim.simulate(
        jurisdiction="Comunidad de Madrid",
        year=2024,
        ingresos_trabajo=0,
    )

    assert result["success"] is True
    assert result["cuota_total"] == 0
    assert result["tipo_medio"] == 0


# ─────────────────────────────────────────────────────────────
# Tests: Tool definition and formatting
# ─────────────────────────────────────────────────────────────

def test_tool_definition_valid():
    """IRPF_SIMULATOR_TOOL has valid OpenAI function calling schema."""
    from app.tools.irpf_simulator_tool import IRPF_SIMULATOR_TOOL

    assert IRPF_SIMULATOR_TOOL["type"] == "function"
    func = IRPF_SIMULATOR_TOOL["function"]
    assert func["name"] == "simulate_irpf"
    assert "parameters" in func
    assert "comunidad_autonoma" in func["parameters"]["properties"]
    assert "ingresos_trabajo" in func["parameters"]["properties"]
    assert func["parameters"]["required"] == ["comunidad_autonoma"]


def test_tool_registered():
    """simulate_irpf is registered in ALL_TOOLS and TOOL_EXECUTORS."""
    from app.tools import ALL_TOOLS, TOOL_EXECUTORS

    tool_names = [t["function"]["name"] for t in ALL_TOOLS]
    assert "simulate_irpf" in tool_names
    assert "simulate_irpf" in TOOL_EXECUTORS


def test_format_simulation_result():
    """_format_simulation_result produces readable text."""
    from app.tools.irpf_simulator_tool import _format_simulation_result

    mock_result = {
        "year": 2024,
        "trabajo": {
            "ingresos_brutos": 30000,
            "rendimiento_neto_reducido": 26095,
            "gastos_deducibles": 3905,
            "reduccion_trabajo": 0,
        },
        "inmuebles": None,
        "base_imponible_general": 26095,
        "base_imponible_ahorro": 0,
        "cuota_integra_general": 6000,
        "cuota_integra_estatal": 3000,
        "cuota_integra_autonomica": 3000,
        "mpyf": {"mpyf_estatal": 5550, "mpyf_autonomico": 5550},
        "cuota_mpyf_estatal": 800,
        "cuota_mpyf_autonomica": 800,
        "cuota_liquida_general": 4400,
        "cuota_ahorro": 0,
        "cuota_total": 4400,
        "tipo_medio": 16.86,
    }

    text = _format_simulation_result(mock_result, "Comunidad de Madrid")
    assert "Simulación IRPF 2024" in text
    assert "30,000.00" in text
    assert "4,400.00" in text


# ─────────────────────────────────────────────────────────────
# Tests: Activity Income Calculator (Autonomos)
# ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_activity_income_basic():
    """Basic activity income: ingresos - gastos - SS = rendimiento neto."""
    from app.utils.calculators.activity_income import ActivityIncomeCalculator

    calc = ActivityIncomeCalculator(None)

    result = await calc.calculate(
        ingresos_actividad=60000,
        gastos_actividad=15000,
        cuota_autonomo_anual=4200,  # 350/mes
        amortizaciones=2000,
    )

    assert result["ingresos_actividad"] == 60000
    total_gastos = 15000 + 4200 + 2000
    assert result["total_gastos_deducibles"] == total_gastos
    assert result["rendimiento_neto_previo"] == 60000 - total_gastos
    # ED simplificada: 5% de rendimiento neto previo (max 2000)
    rn_previo = 60000 - total_gastos  # 38800
    gdj = min(rn_previo * 0.05, 2000)
    assert result["gastos_dificil_justificacion"] == round(gdj, 2)
    assert result["rendimiento_neto"] == round(rn_previo - gdj, 2)


@pytest.mark.asyncio
async def test_activity_income_simplificada_cap():
    """ED simplificada: gastos dificil justificacion capped at 2000 EUR."""
    from app.utils.calculators.activity_income import ActivityIncomeCalculator

    calc = ActivityIncomeCalculator(None)

    result = await calc.calculate(
        ingresos_actividad=100000,
        gastos_actividad=10000,
        cuota_autonomo_anual=5000,
        estimacion="directa_simplificada",
    )

    # 5% of 85000 = 4250, but capped at 2000
    assert result["gastos_dificil_justificacion"] == 2000


@pytest.mark.asyncio
async def test_activity_income_normal_no_gdj():
    """ED normal: no gastos dificil justificacion, but allows provisiones."""
    from app.utils.calculators.activity_income import ActivityIncomeCalculator

    calc = ActivityIncomeCalculator(None)

    result = await calc.calculate(
        ingresos_actividad=60000,
        gastos_actividad=20000,
        cuota_autonomo_anual=4200,
        provisiones=3000,
        estimacion="directa_normal",
    )

    assert result["gastos_dificil_justificacion"] == 0
    assert result["desglose_gastos"]["provisiones"] == 3000
    assert result["total_gastos_deducibles"] == 20000 + 4200 + 3000


@pytest.mark.asyncio
async def test_activity_income_inicio_actividad():
    """New autonomo: 20% reduction on positive net income (Art. 32.3)."""
    from app.utils.calculators.activity_income import ActivityIncomeCalculator

    calc = ActivityIncomeCalculator(None)

    result = await calc.calculate(
        ingresos_actividad=30000,
        gastos_actividad=10000,
        cuota_autonomo_anual=3600,
        inicio_actividad=True,
        estimacion="directa_normal",
    )

    rn = 30000 - 10000 - 3600  # 16400
    reduccion = round(rn * 0.20, 2)
    assert result["reduccion_aplicada"] == reduccion
    assert result["tipo_reduccion"] == "inicio_actividad_art32_3"
    assert result["rendimiento_neto_reducido"] == round(rn - reduccion, 2)


@pytest.mark.asyncio
async def test_activity_income_dependiente():
    """TRADE autonomo (>75% from 1 client): Art. 32.2 reduction."""
    from app.utils.calculators.activity_income import ActivityIncomeCalculator

    calc = ActivityIncomeCalculator(None)

    # Low income case: should get full 6498 reduction
    result = await calc.calculate(
        ingresos_actividad=20000,
        gastos_actividad=5000,
        cuota_autonomo_anual=3600,
        un_solo_cliente=True,
        estimacion="directa_normal",
    )

    rn = 20000 - 5000 - 3600  # 11400 < 14852
    assert result["reduccion_aplicada"] == 6498
    assert result["tipo_reduccion"] == "dependiente_art32_2"


@pytest.mark.asyncio
async def test_activity_income_negative():
    """Negative net income: no reductions, no GDJ, rendimiento = 0."""
    from app.utils.calculators.activity_income import ActivityIncomeCalculator

    calc = ActivityIncomeCalculator(None)

    result = await calc.calculate(
        ingresos_actividad=10000,
        gastos_actividad=15000,
        cuota_autonomo_anual=4200,
    )

    assert result["rendimiento_neto_previo"] < 0
    assert result["gastos_dificil_justificacion"] == 0
    assert result["rendimiento_neto_reducido"] == 0


# ─────────────────────────────────────────────────────────────
# Tests: No hardcoded values in calculators
# ─────────────────────────────────────────────────────────────

def test_no_hardcoded_values_in_calculators():
    """Verify calculators don't contain hardcoded fiscal values."""
    import importlib
    import inspect

    modules_to_check = [
        "app.utils.calculators.work_income",
        "app.utils.calculators.mpyf",
        "app.utils.calculators.rental_income",
        "app.utils.calculators.savings_income",
    ]

    # Fiscal values that should NOT appear hardcoded
    forbidden_values = [
        "5550",   # MPYF contribuyente
        "6700",   # MPYF 65+
        "8100",   # MPYF 75+
        "2400",   # descendiente 1
        "2700",   # descendiente 2
        "2800",   # descendiente <3
        "6498",   # reduccion max trabajo
        "14852",  # rend_min for reduction
    ]

    for mod_name in modules_to_check:
        mod = importlib.import_module(mod_name)
        source = inspect.getsource(mod)

        for val in forbidden_values:
            # Allow the value in comments and docstrings, but not as literals
            # Simple heuristic: check if the value appears as a standalone number assignment
            lines = source.split('\n')
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                # Skip comments, docstrings, and imports
                if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if stripped.startswith('from ') or stripped.startswith('import '):
                    continue
                # Check for hardcoded assignment like `= 5550` or `= 6498`
                if f"= {val}" in stripped and "params" not in stripped and "default" not in stripped:
                    pytest.fail(
                        f"Hardcoded value {val} found in {mod_name} line {line_num}: {stripped}"
                    )


# ─────────────────────────────────────────────────────────────
# Tests: Backward compatibility
# ─────────────────────────────────────────────────────────────

def test_old_calculator_still_importable():
    """IRPFCalculator and calculate_irpf_tool still exist (backward compat)."""
    from app.utils.irpf_calculator import IRPFCalculator
    from app.tools.irpf_calculator_tool import IRPF_CALCULATOR_TOOL, calculate_irpf_tool

    assert IRPFCalculator is not None
    assert IRPF_CALCULATOR_TOOL["function"]["name"] == "calculate_irpf"
    assert callable(calculate_irpf_tool)


def test_both_tools_in_registry():
    """Both simulate_irpf and calculate_irpf are in the tool registry."""
    from app.tools import ALL_TOOLS, TOOL_EXECUTORS

    tool_names = [t["function"]["name"] for t in ALL_TOOLS]
    assert "simulate_irpf" in tool_names
    assert "calculate_irpf" in tool_names
    assert "simulate_irpf" in TOOL_EXECUTORS
    assert "calculate_irpf" in TOOL_EXECUTORS
