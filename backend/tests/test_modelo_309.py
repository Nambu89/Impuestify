"""
Tests for Modelo 309 (Declaracion-Liquidacion No Periodica del IVA).

Cover the cases the tool handles:
1. Adquisiciones intracomunitarias en Recargo de Equivalencia (general / reducido /
   superreducido / tabaco).
2. Inversion del sujeto pasivo (Art. 84.uno.2.o LIVA) en RE y sin RE.
3. Plazos por trimestre.
4. Sin RE (autoliquidacion IVA solo).
5. Validaciones (periodo invalido, base negativa).
6. Tool registration.
"""
import pytest


# ---------------------------------------------------------------------------
# Caso 1 — Farmacia/comercio en RE compra intracomunitaria
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_309_farmacia_re_intracomunitaria_general():
    """Farmacia en RE: compra UE 1.000 EUR al 21% -> IVA 210 + RE 52 = 262 EUR."""
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(
        periodo="1T",
        base_intracomunitarias_21=1000,
    )

    assert result["success"] is True
    assert result["resultado"]["iva_devengado"] == 210.0
    assert result["resultado"]["re_devengado"] == 52.0
    assert result["resultado"]["total_a_ingresar"] == 262.0


@pytest.mark.asyncio
async def test_309_estanco_tabaco_re_175():
    """Estanco RE: tabaco 1.000 EUR -> IVA 210 + RE 17,5 = 227,5 EUR."""
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(
        periodo="2T",
        base_intracomunitarias_tabaco=1000,
    )

    assert result["success"] is True
    assert result["adquisiciones_intracomunitarias"]["desglose"]["iva_tabaco"] == 210.0
    assert result["adquisiciones_intracomunitarias"]["desglose"]["re_tabaco"] == 17.5


# ---------------------------------------------------------------------------
# Caso 2 — Inversion del sujeto pasivo (ISP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_309_isp_general_re():
    """ISP en RE: 500 EUR al 21% -> IVA 105 + RE 26 = 131 EUR."""
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(
        periodo="3T",
        base_isp_21=500,
    )

    assert result["success"] is True
    assert result["inversion_sujeto_pasivo"]["desglose"]["iva_21"] == 105.0
    assert result["inversion_sujeto_pasivo"]["desglose"]["re_21"] == 26.0


@pytest.mark.asyncio
async def test_309_isp_sin_re():
    """ISP sin RE: solo IVA, sin recargo."""
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(
        periodo="4T",
        base_isp_21=1000,
        aplica_re=False,
    )

    assert result["success"] is True
    assert result["inversion_sujeto_pasivo"]["desglose"]["iva_21"] == 210.0
    assert result["inversion_sujeto_pasivo"]["desglose"]["re_21"] == 0.0
    assert result["resultado"]["re_devengado"] == 0.0


# ---------------------------------------------------------------------------
# Caso 3 — Plazos por trimestre
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_309_plazo_1t():
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(
        periodo="1T", base_intracomunitarias_21=100,
    )
    assert "20 de abril" in result["plazo"]


@pytest.mark.asyncio
async def test_309_plazo_4t_30_enero():
    """4T plazo es 30 enero (NO 20 enero)."""
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(
        periodo="4T", base_intracomunitarias_21=100,
    )
    assert "30 de enero" in result["plazo"]


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_309_periodo_invalido_rechazado():
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(periodo="0A")

    assert result["success"] is False
    assert "trimestre" in result["formatted_response"].lower()


@pytest.mark.asyncio
async def test_309_base_negativa_rechazada():
    from app.tools.modelo_309_tool import calculate_modelo_309_tool

    result = await calculate_modelo_309_tool(
        periodo="1T",
        base_intracomunitarias_21=-100,
    )

    assert result["success"] is False
    assert "negativ" in result["formatted_response"].lower()


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def test_309_tool_registered():
    from app.tools import ALL_TOOLS, TOOL_EXECUTORS

    tool_names = [t["function"]["name"] for t in ALL_TOOLS]
    assert "calculate_modelo_309" in tool_names
    assert "calculate_modelo_309" in TOOL_EXECUTORS


def test_309_tool_definition_valid():
    from app.tools.modelo_309_tool import MODELO_309_TOOL

    assert MODELO_309_TOOL["type"] == "function"
    func = MODELO_309_TOOL["function"]
    assert func["name"] == "calculate_modelo_309"
    assert "309" in func["description"]
    props = func["parameters"]["properties"]
    assert "periodo" in props
    assert "base_intracomunitarias_21" in props
    assert "base_isp_21" in props
    assert "aplica_re" in props
