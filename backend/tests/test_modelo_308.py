"""
Tests for Modelo 308 (Solicitud de Devolucion del Recargo de Equivalencia).

Tests the calculate_modelo_308_tool for pharmacies and other retailers
in the Recargo de Equivalencia (RE) regime.
"""
import pytest
from datetime import datetime

from app.tools.modelo_308_tool import calculate_modelo_308_tool, TIPOS_RE


class TestModelo308BasicCalculation:
    """Basic refund calculation tests."""

    @pytest.mark.asyncio
    async def test_basic_intracomunitaria_21(self):
        """Intra-community acquisition at 21% — IVA + RE devengado and refunded."""
        result = await calculate_modelo_308_tool(
            periodo="1T",
            year=2025,
            base_intracomunitarias_21=10000,
        )
        assert result["success"] is True
        assert result["periodo"] == "1T"
        assert result["year"] == 2025
        assert result["modelo"] == "308"

        intra = result["adquisiciones_intracomunitarias"]
        assert intra["base_total"] == 10000.0
        # IVA 21% of 10000 = 2100
        assert intra["cuota_iva"] == 2100.0
        # RE 5.2% of 10000 = 520
        assert intra["cuota_re"] == 520.0

        # Net result should be 0 (devengado = deducible, no additional)
        assert result["resultado"]["resultado_final"] == 0.0
        assert result["resultado"]["tipo"] == "Sin resultado"

    @pytest.mark.asyncio
    async def test_basic_intracomunitaria_10(self):
        """Intra-community acquisition at 10% reduced rate."""
        result = await calculate_modelo_308_tool(
            periodo="2T",
            base_intracomunitarias_10=5000,
        )
        assert result["success"] is True

        intra = result["adquisiciones_intracomunitarias"]
        # IVA 10% of 5000 = 500
        assert intra["desglose"]["iva_10"] == 500.0
        # RE 1.4% of 5000 = 70
        assert intra["desglose"]["re_10"] == 70.0

    @pytest.mark.asyncio
    async def test_basic_intracomunitaria_4(self):
        """Intra-community acquisition at 4% super-reduced rate."""
        result = await calculate_modelo_308_tool(
            periodo="0A",
            base_intracomunitarias_4=20000,
        )
        assert result["success"] is True

        intra = result["adquisiciones_intracomunitarias"]
        # IVA 4% of 20000 = 800
        assert intra["desglose"]["iva_4"] == 800.0
        # RE 0.5% of 20000 = 100
        assert intra["desglose"]["re_4"] == 100.0


class TestModelo308ZeroRefund:
    """Zero refund scenarios."""

    @pytest.mark.asyncio
    async def test_zero_all_bases(self):
        """No qualifying operations — result is zero."""
        result = await calculate_modelo_308_tool(periodo="1T", year=2025)
        assert result["success"] is True
        assert result["resultado"]["resultado_final"] == 0.0
        assert result["resultado"]["tipo"] == "Sin resultado"
        assert result["adquisiciones_intracomunitarias"]["base_total"] == 0.0
        assert result["inversion_sujeto_pasivo"]["base_total"] == 0.0
        assert result["exportaciones"]["re_soportado"] == 0.0
        assert result["transporte_nuevo"]["iva_re_soportado"] == 0.0

    @pytest.mark.asyncio
    async def test_zero_explicit_zeros(self):
        """Explicitly passing zero values."""
        result = await calculate_modelo_308_tool(
            periodo="3T",
            base_intracomunitarias_21=0,
            base_isp_21=0,
            base_exportaciones=0,
            re_soportado_exportaciones=0,
        )
        assert result["success"] is True
        assert result["resultado"]["resultado_final"] == 0.0


class TestModelo308MultipleOperations:
    """Tests with multiple operation types combined."""

    @pytest.mark.asyncio
    async def test_intra_plus_isp(self):
        """Intra-community + ISP operations combined."""
        result = await calculate_modelo_308_tool(
            periodo="0A",
            year=2025,
            base_intracomunitarias_21=10000,
            base_isp_10=5000,
        )
        assert result["success"] is True

        # Intra: IVA 2100, RE 520
        intra = result["adquisiciones_intracomunitarias"]
        assert intra["cuota_iva"] == 2100.0
        assert intra["cuota_re"] == 520.0

        # ISP: IVA 500, RE 70
        isp = result["inversion_sujeto_pasivo"]
        assert isp["cuota_iva"] == 500.0
        assert isp["cuota_re"] == 70.0

        # Total devengado = 2100 + 500 = 2600
        assert result["resultado"]["iva_devengado"] == 2600.0
        # Total RE devengado = 520 + 70 = 590
        assert result["resultado"]["re_devengado"] == 590.0

        # Net result still 0 (no exports/transport)
        assert result["resultado"]["resultado_final"] == 0.0

    @pytest.mark.asyncio
    async def test_intra_plus_export(self):
        """Intra-community + export with RE recovery."""
        result = await calculate_modelo_308_tool(
            periodo="4T",
            base_intracomunitarias_21=8000,
            base_exportaciones=3000,
            re_soportado_exportaciones=156.0,  # RE paid on exported goods
        )
        assert result["success"] is True

        # Export RE is additional refundable amount
        assert result["exportaciones"]["re_soportado"] == 156.0
        # Result = 156.0 (export RE recovery)
        assert result["resultado"]["resultado_final"] == 156.0
        assert result["resultado"]["tipo"] == "A devolver"

    @pytest.mark.asyncio
    async def test_all_operation_types(self):
        """All four operation types at once."""
        result = await calculate_modelo_308_tool(
            periodo="0A",
            year=2025,
            base_intracomunitarias_21=10000,
            base_intracomunitarias_10=5000,
            base_isp_21=3000,
            base_exportaciones=2000,
            re_soportado_exportaciones=104.0,
            base_transporte_nuevo=15000,
            iva_soportado_transporte=3930.0,
        )
        assert result["success"] is True

        # Intra IVA: 2100 + 500 = 2600
        assert result["adquisiciones_intracomunitarias"]["cuota_iva"] == 2600.0

        # ISP IVA: 630
        assert result["inversion_sujeto_pasivo"]["cuota_iva"] == 630.0

        # Additional: 104 + 3930 = 4034
        assert result["resultado"]["cuotas_adicionales"] == 4034.0
        assert result["resultado"]["resultado_final"] == 4034.0
        assert result["resultado"]["tipo"] == "A devolver"

    @pytest.mark.asyncio
    async def test_multiple_rates_intra(self):
        """Intra-community at all three IVA rates simultaneously."""
        result = await calculate_modelo_308_tool(
            periodo="1T",
            base_intracomunitarias_21=10000,
            base_intracomunitarias_10=10000,
            base_intracomunitarias_4=10000,
        )
        assert result["success"] is True

        intra = result["adquisiciones_intracomunitarias"]
        assert intra["base_total"] == 30000.0
        # IVA: 2100 + 1000 + 400 = 3500
        assert intra["cuota_iva"] == 3500.0
        # RE: 520 + 140 + 50 = 710
        assert intra["cuota_re"] == 710.0


class TestModelo308NegativeValuesRejected:
    """Edge case: negative values must be rejected."""

    @pytest.mark.asyncio
    async def test_negative_base_intra_rejected(self):
        """Negative intra-community base is rejected."""
        result = await calculate_modelo_308_tool(
            periodo="1T",
            base_intracomunitarias_21=-5000,
        )
        assert result["success"] is False
        assert "negativo" in result["formatted_response"].lower() or "negativ" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_negative_base_isp_rejected(self):
        """Negative ISP base is rejected."""
        result = await calculate_modelo_308_tool(
            periodo="2T",
            base_isp_10=-1000,
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_negative_re_soportado_rejected(self):
        """Negative RE soportado exportaciones is rejected."""
        result = await calculate_modelo_308_tool(
            periodo="3T",
            re_soportado_exportaciones=-200,
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_negative_iva_transporte_rejected(self):
        """Negative IVA soportado transporte is rejected."""
        result = await calculate_modelo_308_tool(
            periodo="4T",
            iva_soportado_transporte=-100,
        )
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_negative_compensacion_floored_to_zero(self):
        """Negative compensacion is floored to 0 (not rejected)."""
        result = await calculate_modelo_308_tool(
            periodo="1T",
            base_intracomunitarias_21=10000,
            compensacion_periodos_anteriores=-500,
        )
        assert result["success"] is True
        assert result["resultado"]["compensacion_anterior"] == 0.0


class TestModelo308Validation:
    """Validation and edge case tests."""

    @pytest.mark.asyncio
    async def test_invalid_periodo(self):
        """Invalid periodo is rejected."""
        result = await calculate_modelo_308_tool(periodo="5T")
        assert result["success"] is False
        assert "Periodo" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_periodo_text(self):
        """Random text periodo is rejected."""
        result = await calculate_modelo_308_tool(periodo="anual")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_periodo_case_insensitive(self):
        """Periodo should be case-insensitive."""
        result = await calculate_modelo_308_tool(periodo="1t")
        assert result["success"] is True
        assert result["periodo"] == "1T"

    @pytest.mark.asyncio
    async def test_periodo_annual(self):
        """Annual period (0A) is valid."""
        result = await calculate_modelo_308_tool(periodo="0A", year=2025)
        assert result["success"] is True
        assert result["periodo"] == "0A"
        assert "Anual 2025" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_default_year(self):
        """Default year is current year."""
        result = await calculate_modelo_308_tool(periodo="1T")
        assert result["success"] is True
        assert result["year"] == datetime.now().year

    @pytest.mark.asyncio
    async def test_restricted_mode(self):
        """Restricted mode blocks the tool."""
        result = await calculate_modelo_308_tool(
            periodo="1T",
            base_intracomunitarias_21=10000,
            restricted_mode=True,
        )
        assert result["success"] is False
        assert result["error"] == "restricted"


class TestModelo308Compensacion:
    """Tests for compensacion de periodos anteriores."""

    @pytest.mark.asyncio
    async def test_compensacion_reduces_refund(self):
        """Compensacion reduces the final refundable amount."""
        result = await calculate_modelo_308_tool(
            periodo="0A",
            base_exportaciones=5000,
            re_soportado_exportaciones=260.0,
            compensacion_periodos_anteriores=100.0,
        )
        assert result["success"] is True
        # 260 - 100 = 160
        assert result["resultado"]["resultado_final"] == 160.0
        assert result["resultado"]["tipo"] == "A devolver"

    @pytest.mark.asyncio
    async def test_compensacion_exceeds_refund(self):
        """Compensacion exceeds refund — result becomes negative (a compensar)."""
        result = await calculate_modelo_308_tool(
            periodo="1T",
            re_soportado_exportaciones=100.0,
            compensacion_periodos_anteriores=300.0,
        )
        assert result["success"] is True
        # 100 - 300 = -200
        assert result["resultado"]["resultado_final"] == -200.0
        assert result["resultado"]["tipo"] == "A compensar"


class TestModelo308FormattedResponse:
    """Tests for formatted response content."""

    @pytest.mark.asyncio
    async def test_formatted_response_contains_key_sections(self):
        """Formatted response should contain key information."""
        result = await calculate_modelo_308_tool(
            periodo="2T",
            year=2025,
            base_intracomunitarias_21=10000,
            base_isp_10=5000,
            base_exportaciones=2000,
            re_soportado_exportaciones=104.0,
        )
        resp = result["formatted_response"]
        assert "Modelo 308" in resp
        assert "2T 2025" in resp
        assert "Adquisiciones intracomunitarias" in resp
        assert "Inversion del sujeto pasivo" in resp
        assert "Exportaciones" in resp
        assert "Resultado" in resp
        assert "AEAT" in resp
        assert "Recargo de Equivalencia" in resp

    @pytest.mark.asyncio
    async def test_formatted_response_annual(self):
        """Annual period label appears correctly."""
        result = await calculate_modelo_308_tool(
            periodo="0A",
            year=2025,
            base_intracomunitarias_21=1000,
        )
        resp = result["formatted_response"]
        assert "Anual 2025" in resp

    @pytest.mark.asyncio
    async def test_formatted_response_no_empty_sections(self):
        """Sections with no data should not appear."""
        result = await calculate_modelo_308_tool(
            periodo="1T",
            base_intracomunitarias_21=10000,
        )
        resp = result["formatted_response"]
        assert "Adquisiciones intracomunitarias" in resp
        # ISP not used, should not appear
        assert "Inversion del sujeto pasivo" not in resp
        # Exports not used, should not appear
        assert "Exportaciones" not in resp
        # Transport not used, should not appear
        assert "medios de transporte" not in resp


class TestModelo308PharmacyProfile:
    """Integration tests with pharmacy-like profiles."""

    @pytest.mark.asyncio
    async def test_pharmacy_intra_community_purchase(self):
        """Pharmacy buying medicines from EU supplier (typical use case).

        A pharmacy in RE buys 50,000 EUR of medicines (tipo reducido 10%)
        from an EU supplier. Must self-assess IVA+RE and request refund.
        """
        result = await calculate_modelo_308_tool(
            periodo="0A",
            year=2025,
            base_intracomunitarias_10=50000,
        )
        assert result["success"] is True

        intra = result["adquisiciones_intracomunitarias"]
        # IVA 10% of 50000 = 5000
        assert intra["cuota_iva"] == 5000.0
        # RE 1.4% of 50000 = 700
        assert intra["cuota_re"] == 700.0
        # Net result is 0 (devengado = deducible)
        assert result["resultado"]["resultado_final"] == 0.0

    @pytest.mark.asyncio
    async def test_pharmacy_mixed_purchases_and_export(self):
        """Pharmacy with intra-community purchases at mixed rates + some exports.

        - 30,000 EUR medicines (10%)
        - 5,000 EUR medical devices (21%)
        - 2,000 EUR baby food (4%)
        - 1,000 EUR export with 14 EUR RE soportado
        """
        result = await calculate_modelo_308_tool(
            periodo="0A",
            year=2025,
            base_intracomunitarias_10=30000,
            base_intracomunitarias_21=5000,
            base_intracomunitarias_4=2000,
            base_exportaciones=1000,
            re_soportado_exportaciones=14.0,
        )
        assert result["success"] is True

        intra = result["adquisiciones_intracomunitarias"]
        assert intra["base_total"] == 37000.0
        # IVA: 3000 + 1050 + 80 = 4130
        assert intra["cuota_iva"] == 4130.0
        # RE: 420 + 260 + 10 = 690
        assert intra["cuota_re"] == 690.0

        # Only the export RE generates a refund
        assert result["resultado"]["resultado_final"] == 14.0
        assert result["resultado"]["tipo"] == "A devolver"


class TestModelo308ToolRegistration:
    """Tests for tool registration in the tools module."""

    def test_tool_in_all_tools(self):
        from app.tools import ALL_TOOLS
        names = [t["function"]["name"] for t in ALL_TOOLS]
        assert "calculate_modelo_308" in names

    def test_tool_in_executors(self):
        from app.tools import TOOL_EXECUTORS
        assert "calculate_modelo_308" in TOOL_EXECUTORS

    def test_tool_definition_structure(self):
        """Tool definition should follow the OpenAI function calling schema."""
        from app.tools.modelo_308_tool import MODELO_308_TOOL
        assert MODELO_308_TOOL["type"] == "function"
        func = MODELO_308_TOOL["function"]
        assert func["name"] == "calculate_modelo_308"
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["type"] == "object"
        assert "periodo" in func["parameters"]["properties"]
        assert func["parameters"]["required"] == ["periodo"]


class TestModelo308RErates:
    """Verify the RE rate constants are correct."""

    def test_general_rates(self):
        assert TIPOS_RE["general"] == (0.21, 0.052)

    def test_reducido_rates(self):
        assert TIPOS_RE["reducido"] == (0.10, 0.014)

    def test_superreducido_rates(self):
        assert TIPOS_RE["superreducido"] == (0.04, 0.005)
