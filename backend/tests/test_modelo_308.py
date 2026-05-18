"""
Tests for Modelo 308 (Solicitud de Devolucion — sujetos ocasionales y RE
tax-free) following Orden EHA/3786/2008 Art. 7.

Three legitimate cases ONLY:
1. transporte_ocasional — sujeto ocasional medio de transporte nuevo.
2. transportista_simplificado — transportista regimen simplificado adquiriendo vehiculo.
3. re_viajeros — comerciante en RE que reembolsa IVA a viajeros (tax-free).

NOTE: cases related to RE intra-community acquisitions, ISP or imports were
moved to test_modelo_309.py — those are Modelo 309, not 308.
"""

import pytest
from datetime import datetime

from app.tools.modelo_308_tool import calculate_modelo_308_tool, CASOS_VALIDOS


class TestModelo308CasoTransporteOcasional:
    """Caso 1: sujeto ocasional entrega medio de transporte nuevo."""

    @pytest.mark.asyncio
    async def test_basic_transporte_ocasional(self):
        """Particular vende coche nuevo a Francia, recupera el IVA pagado."""
        result = await calculate_modelo_308_tool(
            caso="transporte_ocasional",
            iva_soportado_transporte_nuevo=4200.0,
            year=2025,
        )
        assert result["success"] is True
        assert result["modelo"] == "308"
        assert result["caso"] == "transporte_ocasional"
        assert result["iva_a_devolver"] == 4200.0
        assert result["resultado"]["tipo"] == "A devolver"
        assert "transporte" in result["formatted_response"].lower()

    @pytest.mark.asyncio
    async def test_transporte_ocasional_plazo_30_dias(self):
        """Plazo: 30 dias naturales desde la fecha de entrega."""
        result = await calculate_modelo_308_tool(
            caso="transporte_ocasional",
            iva_soportado_transporte_nuevo=3000.0,
            fecha_entrega_transporte="2025-06-01",
        )
        assert result["success"] is True
        # 1 jun + 30 dias = 1 julio
        assert "01/07/2025" in result["plazo"]
        assert "01/07/2025" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_transporte_ocasional_negative_rejected(self):
        result = await calculate_modelo_308_tool(
            caso="transporte_ocasional",
            iva_soportado_transporte_nuevo=-100,
        )
        assert result["success"] is False


class TestModelo308CasoTransportistaSimplificado:
    """Caso 2: transportista regimen simplificado adquiere vehiculo."""

    @pytest.mark.asyncio
    async def test_basic_transportista_simplificado(self):
        """Transportista simplificado compra furgoneta 25.000 + 5.250 IVA."""
        result = await calculate_modelo_308_tool(
            caso="transportista_simplificado",
            iva_soportado_vehiculo_simplificado=5250.0,
            year=2025,
        )
        assert result["success"] is True
        assert result["caso"] == "transportista_simplificado"
        assert result["iva_a_devolver"] == 5250.0
        assert result["resultado"]["tipo"] == "A devolver"
        assert "regimen simplificado" in result["formatted_response"].lower()

    @pytest.mark.asyncio
    async def test_transportista_plazo_20_dias_mes_siguiente(self):
        """Plazo: 20 primeros dias del mes siguiente al de la adquisicion."""
        result = await calculate_modelo_308_tool(
            caso="transportista_simplificado",
            iva_soportado_vehiculo_simplificado=4000.0,
            fecha_adquisicion_vehiculo="2025-03-15",
        )
        assert result["success"] is True
        # Marzo 15 → mes siguiente abril → 20 abril
        assert "20/04/2025" in result["plazo"]

    @pytest.mark.asyncio
    async def test_transportista_diciembre_rolls_year(self):
        """Adquisicion en diciembre → plazo 20 enero ano siguiente."""
        result = await calculate_modelo_308_tool(
            caso="transportista_simplificado",
            iva_soportado_vehiculo_simplificado=2000.0,
            fecha_adquisicion_vehiculo="2025-12-10",
        )
        assert result["success"] is True
        assert "20/01/2026" in result["plazo"]


class TestModelo308CasoREViajeros:
    """Caso 3: RE devuelve IVA a viajeros (tax-free Art. 21.2 LIVA)."""

    @pytest.mark.asyncio
    async def test_basic_re_viajeros(self):
        """Farmacia Madrid devuelve 84 EUR a turista japones (compras 500 EUR)."""
        result = await calculate_modelo_308_tool(
            caso="re_viajeros",
            iva_devuelto_a_viajeros=84.0,
            periodo="2T",
            year=2025,
        )
        assert result["success"] is True
        assert result["caso"] == "re_viajeros"
        assert result["periodo"] == "2T"
        assert result["iva_a_devolver"] == 84.0
        assert (
            "tax-free" in result["formatted_response"].lower()
            or "viajeros" in result["formatted_response"].lower()
        )

    @pytest.mark.asyncio
    async def test_re_viajeros_plazo_4t_30_enero(self):
        """4T: plazo 30 enero del ano siguiente."""
        result = await calculate_modelo_308_tool(
            caso="re_viajeros",
            iva_devuelto_a_viajeros=200.0,
            periodo="4T",
            year=2025,
        )
        assert result["success"] is True
        assert "30 de enero" in result["plazo"]

    @pytest.mark.asyncio
    async def test_re_viajeros_requires_periodo(self):
        """Caso re_viajeros sin periodo → error."""
        result = await calculate_modelo_308_tool(
            caso="re_viajeros",
            iva_devuelto_a_viajeros=50.0,
        )
        assert result["success"] is False
        assert (
            "trimestre" in result["formatted_response"].lower()
            or "1T" in result["formatted_response"]
        )


class TestModelo308CasoInvalido:
    """Casos invalidos (no contemplados en Art. 7)."""

    @pytest.mark.asyncio
    async def test_caso_desconocido_rejected(self):
        result = await calculate_modelo_308_tool(caso="adquisicion_intracomunitaria")
        assert result["success"] is False
        # Mensaje debe redirigir a Modelo 309
        assert "309" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_caso_vacio_rejected(self):
        result = await calculate_modelo_308_tool(caso="")
        assert result["success"] is False

    def test_casos_validos_constant(self):
        """Solo 3 casos legitimos (Art. 7 Orden EHA/3786/2008)."""
        assert CASOS_VALIDOS == {
            "transporte_ocasional",
            "transportista_simplificado",
            "re_viajeros",
        }


class TestModelo308RestrictedMode:
    @pytest.mark.asyncio
    async def test_restricted_mode_blocks(self):
        result = await calculate_modelo_308_tool(
            caso="transporte_ocasional",
            iva_soportado_transporte_nuevo=1000,
            restricted_mode=True,
        )
        assert result["success"] is False
        assert result["error"] == "restricted"


class TestModelo308DefaultYear:
    @pytest.mark.asyncio
    async def test_default_year_is_current(self):
        result = await calculate_modelo_308_tool(
            caso="transporte_ocasional",
            iva_soportado_transporte_nuevo=100,
        )
        assert result["success"] is True
        assert result["year"] == datetime.now().year


class TestModelo308ToolRegistration:
    def test_tool_in_all_tools(self):
        from app.tools import ALL_TOOLS

        names = [t["function"]["name"] for t in ALL_TOOLS]
        assert "calculate_modelo_308" in names

    def test_tool_in_executors(self):
        from app.tools import TOOL_EXECUTORS

        assert "calculate_modelo_308" in TOOL_EXECUTORS

    def test_tool_definition_structure(self):
        from app.tools.modelo_308_tool import MODELO_308_TOOL

        assert MODELO_308_TOOL["type"] == "function"
        func = MODELO_308_TOOL["function"]
        assert func["name"] == "calculate_modelo_308"
        assert func["parameters"]["required"] == ["caso"]
        # Enum debe tener exactamente los 3 casos legitimos
        enum = func["parameters"]["properties"]["caso"]["enum"]
        assert set(enum) == {
            "transporte_ocasional",
            "transportista_simplificado",
            "re_viajeros",
        }
