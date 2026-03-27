"""
Tests for Modelo 720 (Bienes Extranjero) and Modelo 721 (Cripto Extranjero) tools.

Covers:
- Umbral 50.000 EUR por categoria (720) y global (721)
- Incremento >20.000 EUR respecto ultima declaracion
- Edge cases: exactamente 50K, 0 EUR, multiples categorias
- Clasificacion exchanges (extranjero vs espanol)
- Respuestas formateadas
"""
import pytest
from datetime import datetime

# ---------------------------------------------------------------------------
# Modelo 720 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_720_sin_bienes_extranjero():
    """Sin bienes en el extranjero -> no obligado."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=0,
        valores_extranjero=0,
        inmuebles_extranjero=0,
    )

    assert result["success"] is True
    assert result["obligado_720"] is False
    assert result["categorias_obligadas"] == []


@pytest.mark.asyncio
async def test_720_cuentas_supera_umbral():
    """Cuentas bancarias >50K -> obligado en categoria 1."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=75_000,
        valores_extranjero=10_000,
        inmuebles_extranjero=0,
    )

    assert result["success"] is True
    assert result["obligado_720"] is True
    assert "cuentas" in result["categorias_obligadas"]
    assert "valores" not in result["categorias_obligadas"]
    assert "inmuebles" not in result["categorias_obligadas"]


@pytest.mark.asyncio
async def test_720_valores_supera_umbral():
    """Valores/seguros >50K -> obligado en categoria 2."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=0,
        valores_extranjero=60_000,
        inmuebles_extranjero=0,
    )

    assert result["success"] is True
    assert result["obligado_720"] is True
    assert "valores" in result["categorias_obligadas"]


@pytest.mark.asyncio
async def test_720_inmuebles_supera_umbral():
    """Inmuebles >50K -> obligado en categoria 3."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=0,
        valores_extranjero=0,
        inmuebles_extranjero=200_000,
    )

    assert result["success"] is True
    assert result["obligado_720"] is True
    assert "inmuebles" in result["categorias_obligadas"]


@pytest.mark.asyncio
async def test_720_todo_bajo_umbral():
    """Todas las categorias bajo 50K -> no obligado."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=30_000,
        valores_extranjero=40_000,
        inmuebles_extranjero=49_999,
    )

    assert result["success"] is True
    assert result["obligado_720"] is False


@pytest.mark.asyncio
async def test_720_incremento_supera_20k():
    """Incremento >20K respecto ultimo 720 -> obligado."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=45_000,  # Bajo umbral de 50K
        valores_extranjero=0,
        inmuebles_extranjero=0,
        ultimo_720_presentado=2023,
        saldos_ultimo_720_cuentas=20_000,  # Incremento de 25K
        saldos_ultimo_720_valores=0,
        saldos_ultimo_720_inmuebles=0,
    )

    assert result["success"] is True
    assert result["obligado_720"] is True
    assert "cuentas" in result["categorias_por_incremento"]


@pytest.mark.asyncio
async def test_720_incremento_bajo_20k():
    """Incremento <20K -> no obligado (si no supera umbral)."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=35_000,
        valores_extranjero=0,
        inmuebles_extranjero=0,
        ultimo_720_presentado=2023,
        saldos_ultimo_720_cuentas=20_000,  # Incremento de 15K
        saldos_ultimo_720_valores=0,
        saldos_ultimo_720_inmuebles=0,
    )

    assert result["success"] is True
    assert result["obligado_720"] is False


@pytest.mark.asyncio
async def test_720_multiples_categorias():
    """Multiples categorias sobre umbral -> todas obligadas."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=80_000,
        valores_extranjero=60_000,
        inmuebles_extranjero=150_000,
    )

    assert result["success"] is True
    assert result["obligado_720"] is True
    assert "cuentas" in result["categorias_obligadas"]
    assert "valores" in result["categorias_obligadas"]
    assert "inmuebles" in result["categorias_obligadas"]
    assert len(result["categorias_por_umbral"]) == 3


@pytest.mark.asyncio
async def test_720_exactamente_50k():
    """Exactamente 50.000 EUR -> NO obligado (umbral es >50K, no >=)."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=50_000,
        valores_extranjero=0,
        inmuebles_extranjero=0,
    )

    assert result["success"] is True
    assert result["obligado_720"] is False


@pytest.mark.asyncio
async def test_720_tiene_plazo():
    """El resultado incluye el plazo correcto."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(cuentas_extranjero=100_000)
    ejercicio = datetime.now().year - 1

    assert result["plazo"] == f"Del 1 de enero al 31 de marzo de {ejercicio + 1}"


@pytest.mark.asyncio
async def test_720_formatted_response():
    """La respuesta formateada contiene informacion clave."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(cuentas_extranjero=100_000)

    assert "Modelo 720" in result["formatted_response"]
    assert "RESULTADO" in result["formatted_response"]
    assert "Obligado" in result["formatted_response"]


@pytest.mark.asyncio
async def test_720_recomendaciones_cerca_umbral():
    """Si esta cerca del umbral (>80%), advierte."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=45_000,  # 90% del umbral
        valores_extranjero=0,
        inmuebles_extranjero=0,
    )

    assert result["obligado_720"] is False
    # Debe tener recomendacion de vigilar
    recs_text = " ".join(result["recomendaciones"])
    assert "cerca" in recs_text.lower() or "vigila" in recs_text.lower()


# ---------------------------------------------------------------------------
# Modelo 721 tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_721_crypto_supera_umbral():
    """Crypto >50K en exchanges extranjeros -> obligado."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=80_000,
        exchanges_extranjeros=["Binance", "Coinbase"],
    )

    assert result["success"] is True
    assert result["obligado_721"] is True
    assert result["obligado_por_umbral"] is True


@pytest.mark.asyncio
async def test_721_crypto_bajo_umbral():
    """Crypto <50K -> no obligado."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=30_000,
        exchanges_extranjeros=["Binance"],
    )

    assert result["success"] is True
    assert result["obligado_721"] is False


@pytest.mark.asyncio
async def test_721_incremento_supera_20k():
    """Incremento >20K respecto ultimo 721 -> obligado."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=45_000,
        ultimo_721_presentado=2023,
        valor_ultimo_721=20_000,
    )

    assert result["success"] is True
    assert result["obligado_721"] is True
    assert result["obligado_por_incremento"] is True


@pytest.mark.asyncio
async def test_721_incremento_bajo_20k():
    """Incremento <20K -> no obligado."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=35_000,
        ultimo_721_presentado=2023,
        valor_ultimo_721=20_000,  # Incremento 15K
    )

    assert result["success"] is True
    assert result["obligado_721"] is False


@pytest.mark.asyncio
async def test_721_exactamente_50k():
    """Exactamente 50.000 EUR -> NO obligado (umbral es >50K)."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=50_000,
    )

    assert result["success"] is True
    assert result["obligado_721"] is False


@pytest.mark.asyncio
async def test_721_exchanges_clasificacion():
    """Exchanges espanoles se excluyen del 721."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=80_000,
        exchanges_extranjeros=["Binance", "Bit2Me", "Coinbase"],
    )

    assert result["success"] is True
    assert "Binance" in result["exchanges_afectados"]
    assert "Coinbase" in result["exchanges_afectados"]
    assert "Bit2Me" in result["exchanges_espanoles_excluidos"]


@pytest.mark.asyncio
async def test_721_sin_valor():
    """Sin criptomonedas -> no obligado."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=0,
    )

    assert result["success"] is True
    assert result["obligado_721"] is False


@pytest.mark.asyncio
async def test_721_formatted_response():
    """La respuesta formateada contiene informacion clave."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=80_000,
        exchanges_extranjeros=["Kraken"],
    )

    assert "Modelo 721" in result["formatted_response"]
    assert "RESULTADO" in result["formatted_response"]
    assert "Obligado" in result["formatted_response"]
    assert "Kraken" in result["formatted_response"]


@pytest.mark.asyncio
async def test_721_tiene_plazo():
    """El resultado incluye el plazo correcto."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(crypto_extranjero_valor=100_000)
    ejercicio = datetime.now().year - 1

    assert result["plazo"] == f"Del 1 de enero al 31 de marzo de {ejercicio + 1}"


@pytest.mark.asyncio
async def test_721_autocustodia_mencion():
    """Si obligado, recomendaciones mencionan que autocustodia no aplica."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=80_000,
        exchanges_extranjeros=["Binance"],
    )

    recs_text = " ".join(result["recomendaciones"])
    assert "autocustodia" in recs_text.lower() or "hardware" in recs_text.lower()


# ---------------------------------------------------------------------------
# Integration: tool registration
# ---------------------------------------------------------------------------


def test_tools_registered_in_all_tools():
    """Modelo 720 and 721 tools are registered in ALL_TOOLS."""
    from app.tools import ALL_TOOLS, TOOL_EXECUTORS

    tool_names = [t["function"]["name"] for t in ALL_TOOLS]
    assert "check_modelo_720" in tool_names
    assert "check_modelo_721" in tool_names
    assert "check_modelo_720" in TOOL_EXECUTORS
    assert "check_modelo_721" in TOOL_EXECUTORS


def test_720_tool_definition_valid():
    """Modelo 720 tool definition has correct structure."""
    from app.tools.modelo_720_tool import MODELO_720_TOOL

    assert MODELO_720_TOOL["type"] == "function"
    func = MODELO_720_TOOL["function"]
    assert func["name"] == "check_modelo_720"
    assert "720" in func["description"]
    assert "parameters" in func
    props = func["parameters"]["properties"]
    assert "cuentas_extranjero" in props
    assert "valores_extranjero" in props
    assert "inmuebles_extranjero" in props


def test_721_tool_definition_valid():
    """Modelo 721 tool definition has correct structure."""
    from app.tools.modelo_721_tool import MODELO_721_TOOL

    assert MODELO_721_TOOL["type"] == "function"
    func = MODELO_721_TOOL["function"]
    assert func["name"] == "check_modelo_721"
    assert "721" in func["description"]
    assert "parameters" in func
    props = func["parameters"]["properties"]
    assert "crypto_extranjero_valor" in props
    assert "exchanges_extranjeros" in props
