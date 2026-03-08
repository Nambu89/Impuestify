"""
Tests for IPSI Calculator (Ceuta/Melilla).

Tests the ModeloIpsiCalculator and calculate_modelo_ipsi_tool.
"""
import pytest

from app.utils.calculators.modelo_ipsi import (
    ModeloIpsiCalculator,
    TIPO_MINIMO,
    TIPO_REDUCIDO,
    TIPO_BONIFICADO,
    TIPO_GENERAL,
    TIPO_INCREMENTADO,
    TIPO_ESPECIAL,
)


@pytest.fixture
def calculator():
    return ModeloIpsiCalculator(repo=None)


class TestIpsiRates:
    """Verify IPSI rate constants are correct."""

    def test_tipo_minimo(self):
        assert TIPO_MINIMO == 0.005

    def test_tipo_reducido(self):
        assert TIPO_REDUCIDO == 0.01

    def test_tipo_bonificado(self):
        assert TIPO_BONIFICADO == 0.02

    def test_tipo_general(self):
        assert TIPO_GENERAL == 0.04

    def test_tipo_incrementado(self):
        assert TIPO_INCREMENTADO == 0.08

    def test_tipo_especial(self):
        assert TIPO_ESPECIAL == 0.10


class TestIpsiCalculatorBasic:
    """Basic IPSI calculation tests."""

    @pytest.mark.asyncio
    async def test_basic_general_rate(self, calculator):
        """Single rate tier (4% general) — most common case."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_4=10000,
            cuota_corrientes_interiores=200,
            quarter=1,
            year=2025,
        )
        assert result["total_devengado"] == 400.0  # 10000 * 0.04
        assert result["total_deducible"] == 200.0
        assert result["resultado_regimen_general"] == 200.0
        assert result["resultado_liquidacion"] == 200.0
        assert result["territorio"] == "Ceuta"
        assert result["quarter"] == 1
        assert result["year"] == 2025

    @pytest.mark.asyncio
    async def test_zero_activity(self, calculator):
        """No activity — all zeros."""
        result = await calculator.calculate(territorio="Melilla", quarter=2)
        assert result["total_devengado"] == 0.0
        assert result["total_deducible"] == 0.0
        assert result["resultado_liquidacion"] == 0.0
        assert result["territorio"] == "Melilla"

    @pytest.mark.asyncio
    async def test_negative_result_compensate(self, calculator):
        """Negative result in Q1-Q3 — to compensate."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_4=5000,
            cuota_corrientes_interiores=500,
            quarter=2,
        )
        # Devengado: 5000 * 0.04 = 200
        # Deducible: 500
        # Resultado: 200 - 500 = -300
        assert result["resultado_liquidacion"] == -300.0

    @pytest.mark.asyncio
    async def test_negative_result_q4_refund(self, calculator):
        """Negative result in Q4 — eligible for refund."""
        result = await calculator.calculate(
            territorio="Melilla",
            base_4=5000,
            cuota_corrientes_interiores=500,
            quarter=4,
        )
        assert result["resultado_liquidacion"] == -300.0
        assert result["quarter"] == 4


class TestIpsiCalculatorMultiRate:
    """Tests with multiple rate tiers."""

    @pytest.mark.asyncio
    async def test_all_rates(self, calculator):
        """All 6 rate tiers used simultaneously."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_0_5=10000,
            base_1=10000,
            base_2=10000,
            base_4=10000,
            base_8=10000,
            base_10=10000,
            quarter=1,
        )
        expected = round(
            10000 * 0.005
            + 10000 * 0.01
            + 10000 * 0.02
            + 10000 * 0.04
            + 10000 * 0.08
            + 10000 * 0.10,
            2,
        )
        assert result["total_devengado"] == expected
        # 50 + 100 + 200 + 400 + 800 + 1000 = 2550
        assert result["total_devengado"] == 2550.0

    @pytest.mark.asyncio
    async def test_two_rates(self, calculator):
        """Mix of general (4%) and incrementado (8%)."""
        result = await calculator.calculate(
            territorio="Melilla",
            base_4=20000,
            base_8=5000,
            cuota_corrientes_interiores=600,
            quarter=3,
        )
        # Devengado: 20000*0.04 + 5000*0.08 = 800 + 400 = 1200
        assert result["total_devengado"] == 1200.0
        assert result["resultado_regimen_general"] == 600.0

    @pytest.mark.asyncio
    async def test_desglose_devengado_structure(self, calculator):
        """Verify desglose has all 6 rate entries plus extras."""
        result = await calculator.calculate(
            territorio="Ceuta", base_4=1000, quarter=1
        )
        desglose = result["desglose_devengado"]
        assert "tipo_minimo_0_5" in desglose
        assert "tipo_reducido_1" in desglose
        assert "tipo_bonificado_2" in desglose
        assert "tipo_general_4" in desglose
        assert "tipo_incrementado_8" in desglose
        assert "tipo_especial_10" in desglose
        assert "importaciones" in desglose
        assert "inversion_sujeto_pasivo" in desglose
        assert desglose["tipo_general_4"]["cuota"] == 40.0


class TestIpsiCalculatorImportaciones:
    """Tests for imports and ISP."""

    @pytest.mark.asyncio
    async def test_importaciones(self, calculator):
        """Imports with custom rate."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_importaciones=15000,
            tipo_importaciones=0.08,
            quarter=1,
        )
        assert result["desglose_devengado"]["importaciones"]["cuota"] == 1200.0
        assert result["total_devengado"] == 1200.0

    @pytest.mark.asyncio
    async def test_inversion_sujeto_pasivo(self, calculator):
        """ISP with general rate."""
        result = await calculator.calculate(
            territorio="Melilla",
            base_inversion_sp=8000,
            tipo_inversion_sp=0.04,
            quarter=2,
        )
        assert result["desglose_devengado"]["inversion_sujeto_pasivo"]["cuota"] == 320.0

    @pytest.mark.asyncio
    async def test_tipo_importaciones_clamped(self, calculator):
        """Import rate should be clamped to 0-1 range."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_importaciones=10000,
            tipo_importaciones=1.5,  # Invalid, should clamp to 1.0
            quarter=1,
        )
        assert result["desglose_devengado"]["importaciones"]["cuota"] == 10000.0


class TestIpsiCalculatorCompensaciones:
    """Tests for compensations and adjustments."""

    @pytest.mark.asyncio
    async def test_compensacion_anterior(self, calculator):
        """Compensation from previous quarters."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_4=10000,
            cuotas_compensar_anteriores=150,
            quarter=2,
        )
        # Devengado: 400, Deducible: 0
        # Resultado RG: 400
        # Compensacion: -150
        # Resultado: 250
        assert result["resultado_liquidacion"] == 250.0
        assert result["cuotas_compensar_anteriores"] == 150.0

    @pytest.mark.asyncio
    async def test_compensacion_negative_ignored(self, calculator):
        """Negative compensation should be floored at 0."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_4=10000,
            cuotas_compensar_anteriores=-500,
            quarter=1,
        )
        assert result["cuotas_compensar_anteriores"] == 0.0
        assert result["resultado_liquidacion"] == 400.0

    @pytest.mark.asyncio
    async def test_regularizacion_anual_only_q4(self, calculator):
        """Annual regularization only applies in Q4."""
        result_q2 = await calculator.calculate(
            territorio="Ceuta",
            base_4=10000,
            regularizacion_anual=500,
            quarter=2,
        )
        assert result_q2["regularizacion_anual"] == 0.0

        result_q4 = await calculator.calculate(
            territorio="Ceuta",
            base_4=10000,
            regularizacion_anual=500,
            quarter=4,
        )
        assert result_q4["regularizacion_anual"] == 500.0
        # 400 + 500 = 900
        assert result_q4["resultado_liquidacion"] == 900.0

    @pytest.mark.asyncio
    async def test_complementaria(self, calculator):
        """Complementary filing."""
        result = await calculator.calculate(
            territorio="Melilla",
            base_4=10000,
            resultado_anterior_complementaria=200,
            quarter=1,
        )
        assert result["resultado_anterior_complementaria"] == 200.0
        assert result["cuota_diferencial_complementaria"] == 200.0  # 400 - 200

    @pytest.mark.asyncio
    async def test_mod_cuotas(self, calculator):
        """Modifications to previous period cuotas."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_4=10000,
            mod_cuotas=-100,
            quarter=3,
        )
        # Devengado: 400 + (-100) = 300
        assert result["total_devengado"] == 300.0


class TestIpsiCalculatorDeducible:
    """Tests for deductible IPSI."""

    @pytest.mark.asyncio
    async def test_all_deducible_concepts(self, calculator):
        """All deductible concepts."""
        result = await calculator.calculate(
            territorio="Ceuta",
            base_4=50000,
            cuota_corrientes_interiores=300,
            cuota_inversion_interiores=200,
            cuota_importaciones_corrientes=100,
            cuota_importaciones_inversion=50,
            rectificacion_deducciones=-30,
            regularizacion_inversion=20,
            regularizacion_prorrata=10,  # ignored, not Q4
            quarter=1,
        )
        # Total deducible: 300 + 200 + 100 + 50 + (-30) + 20 + 10 = 650
        assert result["total_deducible"] == 650.0

    @pytest.mark.asyncio
    async def test_desglose_deducible_structure(self, calculator):
        """Verify desglose deducible has all fields."""
        result = await calculator.calculate(
            territorio="Melilla", base_4=1000, quarter=1
        )
        desglose = result["desglose_deducible"]
        expected_keys = [
            "cuota_corrientes_interiores",
            "cuota_inversion_interiores",
            "cuota_importaciones_corrientes",
            "cuota_importaciones_inversion",
            "rectificacion_deducciones",
            "regularizacion_inversion",
            "regularizacion_prorrata",
        ]
        for key in expected_keys:
            assert key in desglose


class TestIpsiCalculatorMetadata:
    """Tests for metadata in results."""

    @pytest.mark.asyncio
    async def test_ipsi_rates_in_result(self, calculator):
        """Result should include IPSI rates metadata."""
        result = await calculator.calculate(territorio="Ceuta", quarter=1)
        rates = result["ipsi_rates"]
        assert rates["tipo_minimo"] == 0.005
        assert rates["tipo_reducido"] == 0.01
        assert rates["tipo_bonificado"] == 0.02
        assert rates["tipo_general"] == 0.04
        assert rates["tipo_incrementado"] == 0.08
        assert rates["tipo_especial"] == 0.10

    @pytest.mark.asyncio
    async def test_ceuta_vs_melilla_same_calculation(self, calculator):
        """Same inputs should give same results regardless of territory."""
        result_ceuta = await calculator.calculate(
            territorio="Ceuta", base_4=10000, quarter=1
        )
        result_melilla = await calculator.calculate(
            territorio="Melilla", base_4=10000, quarter=1
        )
        assert result_ceuta["total_devengado"] == result_melilla["total_devengado"]
        assert result_ceuta["resultado_liquidacion"] == result_melilla["resultado_liquidacion"]
        assert result_ceuta["territorio"] == "Ceuta"
        assert result_melilla["territorio"] == "Melilla"


class TestIpsiTool:
    """Tests for the IPSI tool function."""

    @pytest.mark.asyncio
    async def test_tool_basic(self):
        from app.tools.modelo_ipsi_tool import calculate_modelo_ipsi_tool

        result = await calculate_modelo_ipsi_tool(
            territorio="Ceuta",
            trimestre=1,
            base_4=10000,
            ipsi_deducible=200,
        )
        assert result["success"] is True
        assert "formatted_response" in result
        assert "IPSI Ceuta" in result["formatted_response"]
        assert result["total_devengado"] == 400.0

    @pytest.mark.asyncio
    async def test_tool_melilla(self):
        from app.tools.modelo_ipsi_tool import calculate_modelo_ipsi_tool

        result = await calculate_modelo_ipsi_tool(
            territorio="Melilla",
            trimestre=3,
            base_4=5000,
            ipsi_deducible=100,
        )
        assert result["success"] is True
        assert "Melilla" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_tool_invalid_trimestre(self):
        from app.tools.modelo_ipsi_tool import calculate_modelo_ipsi_tool

        result = await calculate_modelo_ipsi_tool(
            territorio="Ceuta", trimestre=5, base_4=1000, ipsi_deducible=0
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_tool_invalid_territorio(self):
        from app.tools.modelo_ipsi_tool import calculate_modelo_ipsi_tool

        result = await calculate_modelo_ipsi_tool(
            territorio="Madrid", trimestre=1, base_4=1000, ipsi_deducible=0
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_tool_restricted_mode(self):
        from app.tools.modelo_ipsi_tool import calculate_modelo_ipsi_tool

        result = await calculate_modelo_ipsi_tool(
            territorio="Ceuta",
            trimestre=1,
            base_4=1000,
            ipsi_deducible=0,
            restricted_mode=True,
        )
        assert result["success"] is False
        assert result["error"] == "restricted"

    @pytest.mark.asyncio
    async def test_tool_formatted_response_content(self):
        from app.tools.modelo_ipsi_tool import calculate_modelo_ipsi_tool

        result = await calculate_modelo_ipsi_tool(
            territorio="Ceuta",
            trimestre=2,
            base_4=20000,
            base_8=5000,
            ipsi_deducible=500,
            year=2025,
        )
        resp = result["formatted_response"]
        assert "IPSI Ceuta" in resp
        assert "2T 2025" in resp
        assert "IPSI Devengado" in resp
        assert "IPSI Deducible" in resp
        assert "Resultado" in resp
        assert "ordenanza fiscal" in resp

    @pytest.mark.asyncio
    async def test_tool_default_year(self):
        from app.tools.modelo_ipsi_tool import calculate_modelo_ipsi_tool
        from datetime import datetime

        result = await calculate_modelo_ipsi_tool(
            territorio="Melilla",
            trimestre=1,
            base_4=1000,
            ipsi_deducible=0,
        )
        assert result["success"] is True
        assert result["year"] == datetime.now().year


class TestIpsiToolDefinition:
    """Tests for IPSI tool registration."""

    def test_tool_in_all_tools(self):
        from app.tools import ALL_TOOLS
        names = [t["function"]["name"] for t in ALL_TOOLS]
        assert "calculate_modelo_ipsi" in names

    def test_tool_in_executors(self):
        from app.tools import TOOL_EXECUTORS
        assert "calculate_modelo_ipsi" in TOOL_EXECUTORS
