"""
Tests de integración para T4.1 — Ganancias cripto/trading/apuestas en el simulador IRPF.

Verifica:
1. Ganancias cripto → base del ahorro (casillas 1813-1814)
2. Ganancias acciones/fondos/derivados → base del ahorro (casillas 0316-0354)
3. Compensación de pérdidas dentro de cada tipo
4. Juegos privados → base general (casillas 0281-0290)
5. Loterías públicas → gravamen especial 20% sobre exceso de 40.000 EUR
6. Backward compatibility: parámetros sin nuevos campos = mismo resultado que antes
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _DictRow(dict):
    """Dict subclass that also supports attribute access — mimics Turso row objects."""
    pass


def _make_scale_result(tramos):
    """Build a mock DB result whose rows behave like Turso row objects."""
    result = MagicMock()
    result.rows = [_DictRow(t) for t in tramos]
    return result


@pytest.fixture
def mock_db():
    db = AsyncMock()

    # IRPF general scale (Estatal/CCAA 2024, simplified 4 tramos)
    estatal_general = [
        {"tramo_num": 1, "base_hasta": 12450.0,  "cuota_integra": 0.0,     "resto_base": 12450.0, "tipo_aplicable": 9.5},
        {"tramo_num": 2, "base_hasta": 20200.0,  "cuota_integra": 1182.75, "resto_base": 7750.0,  "tipo_aplicable": 12.0},
        {"tramo_num": 3, "base_hasta": 35200.0,  "cuota_integra": 2112.75, "resto_base": 15000.0, "tipo_aplicable": 15.0},
        {"tramo_num": 4, "base_hasta": 999999.0, "cuota_integra": 4362.75, "resto_base": 999999.0,"tipo_aplicable": 18.5},
    ]
    # Ahorro scale (Estatal 2024)
    ahorro_scale = [
        {"tramo_num": 1, "base_hasta": 6000.0,   "cuota_integra": 0.0,    "resto_base": 6000.0,  "tipo_aplicable": 19.0},
        {"tramo_num": 2, "base_hasta": 50000.0,  "cuota_integra": 1140.0, "resto_base": 44000.0, "tipo_aplicable": 21.0},
        {"tramo_num": 3, "base_hasta": 200000.0, "cuota_integra": 10380.0,"resto_base": 150000.0,"tipo_aplicable": 23.0},
        {"tramo_num": 4, "base_hasta": 999999.0, "cuota_integra": 44880.0,"resto_base": 999999.0,"tipo_aplicable": 27.0},
    ]

    def db_side_effect(query, params):
        # tax_parameters → empty (calculators use .get() with hardcoded defaults)
        if "tax_parameters" in query:
            empty = MagicMock()
            empty.rows = []
            return empty
        # irpf_scales → select the right scale based on scale_type in query
        if "scale_type = 'ahorro'" in query:
            return _make_scale_result(ahorro_scale)
        # general scale (Estatal + any CCAA — use same simplified scale for tests)
        if "irpf_scales" in query or "scale_type" in query:
            return _make_scale_result(estatal_general)
        # fallback: empty result
        empty = MagicMock()
        empty.rows = []
        return empty

    db.execute = AsyncMock(side_effect=db_side_effect)
    return db


# ---------------------------------------------------------------------------
# SavingsIncomeCalculator unit tests
# ---------------------------------------------------------------------------

class TestSavingsIncomeCalculatorNewParams:
    """Unit tests for SavingsIncomeCalculator with patrimonial gains."""

    @pytest.mark.asyncio
    async def test_cripto_ganancia_suma_a_base_ahorro(self, mock_db):
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            cripto_ganancia_neta=5000.0,
            jurisdiction="Estatal",
            year=2024,
        )

        assert result["base_ahorro"] == 5000.0
        assert result["ganancias_patrimoniales"]["neto_cripto"] == 5000.0
        assert result["cuota_ahorro_total"] > 0

    @pytest.mark.asyncio
    async def test_cripto_perdida_compensa_ganancia(self, mock_db):
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            cripto_ganancia_neta=10000.0,
            cripto_perdida_neta=3000.0,
            jurisdiction="Estatal",
            year=2024,
        )

        assert result["ganancias_patrimoniales"]["neto_cripto"] == 7000.0
        assert result["base_ahorro"] == 7000.0

    @pytest.mark.asyncio
    async def test_perdida_mayor_que_ganancia_da_cero(self, mock_db):
        """Las pérdidas no pueden dejar el neto negativo en cripto."""
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            cripto_ganancia_neta=2000.0,
            cripto_perdida_neta=5000.0,
            jurisdiction="Estatal",
            year=2024,
        )

        assert result["ganancias_patrimoniales"]["neto_cripto"] == 0.0
        assert result["base_ahorro"] == 0.0

    @pytest.mark.asyncio
    async def test_acciones_suma_a_base_ahorro(self, mock_db):
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            ganancias_acciones=8000.0,
            perdidas_acciones=2000.0,
            jurisdiction="Estatal",
            year=2024,
        )

        assert result["ganancias_patrimoniales"]["neto_acciones"] == 6000.0
        assert result["base_ahorro"] == 6000.0

    @pytest.mark.asyncio
    async def test_derivados_suma_a_base_ahorro(self, mock_db):
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            ganancias_derivados=3000.0,
            perdidas_derivados=500.0,
            jurisdiction="Estatal",
            year=2024,
        )

        assert result["ganancias_patrimoniales"]["neto_derivados"] == 2500.0
        assert result["base_ahorro"] == 2500.0

    @pytest.mark.asyncio
    async def test_fondos_reembolso_suma_a_base_ahorro(self, mock_db):
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            ganancias_reembolso_fondos=4000.0,
            perdidas_reembolso_fondos=1000.0,
            jurisdiction="Estatal",
            year=2024,
        )

        assert result["ganancias_patrimoniales"]["neto_reembolso_fondos"] == 3000.0
        assert result["base_ahorro"] == 3000.0

    @pytest.mark.asyncio
    async def test_mix_todas_las_ganancias_patrimoniales(self, mock_db):
        """Cripto + acciones + fondos + derivados se suman a la base del ahorro."""
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            intereses=1000.0,
            cripto_ganancia_neta=5000.0,
            ganancias_acciones=3000.0,
            ganancias_reembolso_fondos=2000.0,
            ganancias_derivados=1000.0,
            jurisdiction="Estatal",
            year=2024,
        )

        # 1000 (intereses) + 5000 (cripto) + 3000 (acciones) + 2000 (fondos) + 1000 (derivados)
        assert result["base_ahorro"] == 12000.0
        assert result["ganancias_patrimoniales"]["total_neto"] == 11000.0

    @pytest.mark.asyncio
    async def test_backward_compatible_sin_nuevos_params(self, mock_db):
        """Sin nuevos parámetros, el resultado es idéntico al anterior."""
        from app.utils.calculators.savings_income import SavingsIncomeCalculator
        from app.utils.tax_parameter_repository import TaxParameterRepository

        repo = TaxParameterRepository(mock_db)
        calc = SavingsIncomeCalculator(repo, mock_db)

        result = await calc.calculate(
            intereses=2000.0,
            dividendos=500.0,
            jurisdiction="Estatal",
            year=2024,
        )

        assert result["base_ahorro"] == 2500.0
        assert result["ganancias_patrimoniales"]["total_neto"] == 0.0


# ---------------------------------------------------------------------------
# IRPFSimulator integration tests
# ---------------------------------------------------------------------------

class TestIRPFSimulatorCryptoIntegration:
    """Integration tests: new params flow through simulate() correctly."""

    def _make_simulator(self, mock_db):
        from app.utils.irpf_simulator import IRPFSimulator
        return IRPFSimulator(mock_db)

    @pytest.mark.asyncio
    async def test_cripto_aumenta_base_ahorro(self, mock_db):
        """Ganancias cripto deben incrementar la base del ahorro."""
        sim = self._make_simulator(mock_db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
            cripto_ganancia_neta=5000.0,
        )

        assert result["success"] is True
        assert result["base_imponible_ahorro"] == 5000.0

    @pytest.mark.asyncio
    async def test_acciones_aumentan_base_ahorro(self, mock_db):
        sim = self._make_simulator(mock_db)

        result = await sim.simulate(
            jurisdiction="Cataluna",
            year=2024,
            ingresos_trabajo=40000.0,
            ganancias_acciones=10000.0,
            perdidas_acciones=2000.0,
        )

        assert result["success"] is True
        assert result["base_imponible_ahorro"] == 8000.0

    @pytest.mark.asyncio
    async def test_juegos_privados_van_a_base_general(self, mock_db):
        """Premios de juegos privados deben sumarse a la base imponible general."""
        sim = self._make_simulator(mock_db)

        # Simulación sin juegos
        result_base = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
        )

        # Simulación con premios juegos
        result_juegos = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
            premios_metalico_privados=5000.0,
            perdidas_juegos_privados=1000.0,
        )

        # Base general debe ser mayor con juegos (neto = 4000)
        diferencia = (
            result_juegos["base_imponible_general"]
            - result_base["base_imponible_general"]
        )
        assert abs(diferencia - 4000.0) < 0.01

        # Base del ahorro no debe verse afectada por juegos
        assert result_juegos["base_imponible_ahorro"] == 0.0
        assert result_juegos.get("ganancias_juegos_netas") == 4000.0

    @pytest.mark.asyncio
    async def test_juegos_privados_perdidas_no_superan_premios(self, mock_db):
        """Las pérdidas de juegos no pueden compensar rentas de otros tipos."""
        sim = self._make_simulator(mock_db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
            premios_metalico_privados=1000.0,
            perdidas_juegos_privados=3000.0,  # más pérdidas que premios
        )

        # El neto de juegos no puede ser negativo
        assert result.get("ganancias_juegos_netas") == 0.0

    @pytest.mark.asyncio
    async def test_loterias_publicas_exencion_40000(self, mock_db):
        """Loterías públicas <= 40.000 EUR: gravamen especial = 0."""
        sim = self._make_simulator(mock_db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
            premios_metalico_publicos=30000.0,
        )

        assert result.get("gravamen_especial_loterias") == 0.0

    @pytest.mark.asyncio
    async def test_loterias_publicas_gravamen_sobre_exceso(self, mock_db):
        """Premio de 60.000 EUR: gravamen = (60000 - 40000) * 20% = 4000 EUR."""
        sim = self._make_simulator(mock_db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
            premios_metalico_publicos=60000.0,
        )

        expected_gravamen = (60000.0 - 40000.0) * 0.20
        assert abs(result.get("gravamen_especial_loterias", 0) - expected_gravamen) < 0.01

    @pytest.mark.asyncio
    async def test_loterias_no_van_a_base_general_ni_ahorro(self, mock_db):
        """Las loterías públicas NO afectan la base general ni la del ahorro."""
        sim = self._make_simulator(mock_db)

        result_sin = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
        )

        result_con = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
            premios_metalico_publicos=100000.0,
        )

        # Las bases no cambian con loterías
        assert result_sin["base_imponible_general"] == result_con["base_imponible_general"]
        assert result_sin["base_imponible_ahorro"] == result_con["base_imponible_ahorro"]

        # Pero el gravamen especial existe
        assert result_con["gravamen_especial_loterias"] == (100000.0 - 40000.0) * 0.20

    @pytest.mark.asyncio
    async def test_backward_compatible_sin_nuevos_campos(self, mock_db):
        """Sin nuevos campos, el resultado debe ser idéntico al de antes de T4.1."""
        sim = self._make_simulator(mock_db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=45000.0,
            intereses=1000.0,
            dividendos=500.0,
        )

        assert result["success"] is True
        # Los nuevos campos tienen valor 0 por defecto
        assert result.get("ganancias_juegos_netas", 0) == 0.0
        assert result.get("gravamen_especial_loterias", 0) == 0.0
        # Base ahorro es solo rendimientos capital mobiliario
        assert result["base_imponible_ahorro"] == 1500.0

    @pytest.mark.asyncio
    async def test_gravamen_loterias_suma_a_cuota_diferencial(self, mock_db):
        """El gravamen especial de loterías se suma al resultado final."""
        sim = self._make_simulator(mock_db)

        result_sin = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
        )

        result_con = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000.0,
            premios_metalico_publicos=60000.0,  # gravamen = 4000
        )

        diferencia = result_con["cuota_diferencial"] - result_sin["cuota_diferencial"]
        assert abs(diferencia - 4000.0) < 0.01

    @pytest.mark.asyncio
    async def test_mix_completo_todas_las_nuevas_rentas(self, mock_db):
        """Caso completo: trabajo + cripto + acciones + juegos + loterías."""
        sim = self._make_simulator(mock_db)

        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=35000.0,
            cripto_ganancia_neta=8000.0,
            cripto_perdida_neta=2000.0,       # neto cripto = 6000
            ganancias_acciones=5000.0,
            perdidas_acciones=1000.0,          # neto acciones = 4000
            premios_metalico_privados=3000.0,
            perdidas_juegos_privados=500.0,    # neto juegos = 2500 → base general
            premios_metalico_publicos=50000.0, # gravamen = (50000-40000)*0.20 = 2000
        )

        assert result["success"] is True
        # Base ahorro = cripto neto + acciones neto = 6000 + 4000 = 10000
        assert result["base_imponible_ahorro"] == 10000.0
        # Ganancias juegos en base general
        assert result.get("ganancias_juegos_netas") == 2500.0
        # Gravamen especial loterías
        assert result.get("gravamen_especial_loterias") == 2000.0
