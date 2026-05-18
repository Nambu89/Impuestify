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
# Modelo 720 — cese de titularidad (Bug 95 P1.1)
# RD 1065/2007 Arts. 42 bis.5, 42 ter.5, 54 bis.7
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_720_cese_cuenta_con_720_previo_obliga():
    """
    Cierre de cuenta declarada en 720 anterior -> obligado a declarar el cese
    aunque el saldo a 31/dic sea 0.
    Caso C11 del audit (Bug 95 P1.1).
    """
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=0,
        valores_extranjero=0,
        inmuebles_extranjero=0,
        ultimo_720_presentado=2023,
        saldos_ultimo_720_cuentas=200_000,
        ceses_titularidad=[
            {
                "categoria": "cuentas",
                "subtipo": "A",
                "descripcion": "Cuenta corriente Andorra ES12 0234 ...",
                "valor_ultima_declaracion": 200_000,
                "fecha_cese": "2025-06-15",
                "motivo": "cierre_cuenta",
            }
        ],
    )

    assert result["success"] is True
    assert result["obligado_720"] is True, "Cese de cuenta con 720 previo debe obligar"
    assert len(result["ceses_obligan_declarar"]) == 1
    assert result["ceses_obligan_declarar"][0]["categoria"] == "cuentas"
    assert result["ceses_obligan_declarar"][0]["subtipo"] == "A"
    assert "cuentas" in result["categorias_por_cese"]
    formatted = result["formatted_response"].lower()
    assert "cese" in formatted


@pytest.mark.asyncio
async def test_720_cese_valores_con_720_previo_obliga():
    """Venta de valores declarados en 720 previo -> obligado a declarar cese."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        valores_extranjero=0,
        ultimo_720_presentado=2024,
        saldos_ultimo_720_valores=120_000,
        ceses_titularidad=[
            {
                "categoria": "valores",
                "subtipo": "A",
                "descripcion": "Acciones Apple Inc.",
                "valor_ultima_declaracion": 120_000,
                "fecha_cese": "2025-09-01",
                "motivo": "venta_valores",
            }
        ],
    )

    assert result["obligado_720"] is True
    assert any(
        c["categoria"] == "valores" and c["subtipo"] == "A"
        for c in result["ceses_obligan_declarar"]
    )


@pytest.mark.asyncio
async def test_720_cese_inmueble_con_720_previo_obliga():
    """Venta de inmueble declarado en 720 previo -> obligado a declarar cese."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        inmuebles_extranjero=0,
        ultimo_720_presentado=2022,
        saldos_ultimo_720_inmuebles=300_000,
        ceses_titularidad=[
            {
                "categoria": "inmuebles",
                "subtipo": "A",  # titularidad plena
                "descripcion": "Vivienda Lisboa, Rua Augusta 12",
                "valor_ultima_declaracion": 300_000,
                "fecha_cese": "2025-04-30",
                "motivo": "venta_inmueble",
            }
        ],
    )

    assert result["obligado_720"] is True
    cese = result["ceses_obligan_declarar"][0]
    assert cese["categoria"] == "inmuebles"
    assert cese["subtipo"] == "A"
    assert cese["subtipo_descripcion"].lower().startswith("titularidad plena")


@pytest.mark.asyncio
async def test_720_cese_sin_720_previo_no_obliga():
    """
    Cese de bien que NUNCA se declaro en un 720 previo -> no obligacion.
    El input ultimo_720_presentado=None debe excluir la obligacion.
    """
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=0,
        ultimo_720_presentado=None,
        ceses_titularidad=[
            {
                "categoria": "cuentas",
                "subtipo": "B",
                "descripcion": "Cuenta de ahorro Suiza",
                "valor_ultima_declaracion": 80_000,
                "fecha_cese": "2025-03-10",
                "motivo": "cierre_cuenta",
            }
        ],
    )

    assert result["success"] is True
    assert result["obligado_720"] is False, "Sin 720 previo, el cese no genera obligacion"
    assert result["ceses_obligan_declarar"] == []
    # El cese se devuelve marcado como no obligatorio + razon
    assert len(result["ceses_titularidad"]) == 1
    assert result["ceses_titularidad"][0]["obliga_declarar"] is False
    assert "no se presento" in result["ceses_titularidad"][0]["motivo_no_obliga"].lower()


@pytest.mark.asyncio
async def test_720_cese_con_720_previo_pero_otra_categoria_no_obliga():
    """
    Hubo 720 previo pero solo declaraba inmuebles. Cese de cuenta no declarada
    previamente en esa categoria -> no obliga (mejor esfuerzo).
    """
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=0,
        ultimo_720_presentado=2023,
        saldos_ultimo_720_cuentas=0,  # nunca tuvo cuentas en 720
        saldos_ultimo_720_inmuebles=300_000,
        ceses_titularidad=[
            {
                "categoria": "cuentas",
                "subtipo": "A",
                "descripcion": "Cuenta corriente nueva, no declarada",
                "valor_ultima_declaracion": 0,
                "fecha_cese": "2025-05-01",
                "motivo": "cierre_cuenta",
            }
        ],
    )

    assert result["obligado_720"] is False
    assert result["ceses_obligan_declarar"] == []


# ---------------------------------------------------------------------------
# Modelo 720 — subtipos por clave DR720 (Bug 95 P1 subtipos)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_720_subtipos_desglose_correcto():
    """Subtipos por categoria que suman el agregado -> validados sin warnings."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=55_000,
        valores_extranjero=0,
        inmuebles_extranjero=0,
        subtipos={
            "cuentas": {"A": 30_000, "B": 25_000},
        },
    )

    assert result["success"] is True
    assert result["obligado_720"] is True
    assert "A" in result["subtipos"]["cuentas"]
    assert "B" in result["subtipos"]["cuentas"]
    assert result["subtipos"]["cuentas"]["A"]["valor"] == 30_000
    assert result["subtipos"]["cuentas"]["A"]["descripcion"].lower().startswith("cuenta corriente")
    assert result["subtipos_warnings"] == []
    formatted = result["formatted_response"]
    assert "Clave A" in formatted
    assert "Clave B" in formatted


@pytest.mark.asyncio
async def test_720_subtipos_suma_no_coincide_warning():
    """Si la suma de subtipos != agregado, devuelve warning."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        cuentas_extranjero=55_000,
        subtipos={
            "cuentas": {"A": 30_000},  # falta 25_000
        },
    )

    assert result["success"] is True
    assert any("no coincide" in w.lower() for w in result["subtipos_warnings"])


@pytest.mark.asyncio
async def test_720_subtipo_clave_invalida_warning():
    """Clave fuera del DR720 (ej: 'Z') -> warning, no rompe ejecucion."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        valores_extranjero=60_000,
        subtipos={
            "valores": {"Z": 60_000},  # Z no existe en valores
        },
    )

    assert result["success"] is True
    assert result["obligado_720"] is True
    assert any("dr720" in w.lower() or "fuera de" in w.lower() for w in result["subtipos_warnings"])
    assert "Z" not in result["subtipos"].get("valores", {})


@pytest.mark.asyncio
async def test_720_subtipos_inmuebles_usufructo():
    """Inmueble en usufructo (clave C) -> categoria correcta y descripcion."""
    from app.tools.modelo_720_tool import check_modelo_720_tool

    result = await check_modelo_720_tool(
        inmuebles_extranjero=80_000,
        subtipos={
            "inmuebles": {"C": 80_000},
        },
    )

    assert result["subtipos"]["inmuebles"]["C"]["valor"] == 80_000
    desc = result["subtipos"]["inmuebles"]["C"]["descripcion"].lower()
    assert "usufructo" in desc


@pytest.mark.asyncio
async def test_720_tool_definition_incluye_ceses_y_subtipos():
    """La definicion OpenAI incluye los nuevos parametros."""
    from app.tools.modelo_720_tool import MODELO_720_TOOL

    props = MODELO_720_TOOL["function"]["parameters"]["properties"]
    assert "ceses_titularidad" in props
    assert "subtipos" in props
    # ceses_titularidad: array de objetos
    assert props["ceses_titularidad"]["type"] == "array"
    item_props = props["ceses_titularidad"]["items"]["properties"]
    assert "categoria" in item_props
    assert "subtipo" in item_props
    assert "valor_ultima_declaracion" in item_props
    assert "motivo" in item_props
    # subtipos: objeto con cuentas/valores/inmuebles
    assert props["subtipos"]["type"] == "object"
    sub_props = props["subtipos"]["properties"]
    assert "cuentas" in sub_props
    assert "valores" in sub_props
    assert "inmuebles" in sub_props


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
    # Bug 96 fix: nuevo parametro para sucursales espanolas
    assert "exchanges_via_sucursal_espanola" in props


# ---------------------------------------------------------------------------
# Modelo 721 — Bug 96: sucursales/filiales espanolas + lista BdE ampliada
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_721_binance_spain_sl_excluido():
    """Si el contrato es con Binance Spain SL (sucursal inscrita en BdE),
    el exchange queda EXCLUIDO del computo del 721.

    Caso real: usuario con 80K en Binance pero contrato firmado con la
    filial espanola. Debe clasificarse como excluido por sucursal.
    """
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=80_000,
        exchanges_extranjeros=["Binance"],
        exchanges_via_sucursal_espanola=["Binance"],
    )

    assert result["success"] is True
    assert "Binance" in result["exchanges_sucursal_espanola_excluidos"]
    assert "Binance" not in result["exchanges_afectados"]


@pytest.mark.asyncio
async def test_721_binance_internacional_incluido():
    """Si el usuario tiene Binance pero NO indica sucursal espanola,
    se considera Binance internacional -> entra en el 721 (>50K).
    """
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=80_000,
        exchanges_extranjeros=["Binance"],
    )

    assert result["success"] is True
    assert result["obligado_721"] is True
    assert "Binance" in result["exchanges_afectados"]
    assert result.get("exchanges_sucursal_espanola_excluidos", []) == []


@pytest.mark.asyncio
async def test_721_onyze_excluido_por_defecto():
    """Onyze esta inscrita en el Registro BdE como exchange espanol —
    debe quedar excluido del 721 sin necesidad de flag adicional.
    """
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=80_000,
        exchanges_extranjeros=["Onyze"],
    )

    assert result["success"] is True
    assert "Onyze" in result["exchanges_espanoles_excluidos"]
    assert "Onyze" not in result["exchanges_afectados"]


@pytest.mark.asyncio
async def test_721_lista_exchanges_espanoles_ampliada():
    """La lista EXCHANGES_ESPANOLES debe incluir todos los exchanges
    inscritos en el Registro BdE (Bug 96 ALTO 2)."""
    from app.tools.modelo_721_tool import EXCHANGES_ESPANOLES

    expected = {"bit2me", "bitnovo", "onyze", "criptan", "vottun", "onyx", "bitbase"}
    assert expected.issubset(EXCHANGES_ESPANOLES)


@pytest.mark.asyncio
async def test_721_mix_internacional_y_sucursal_espanola():
    """Usuario con Binance Spain SL (excluido) + Kraken internacional (incluido).
    Solo Kraken debe contar para la obligacion."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=60_000,
        exchanges_extranjeros=["Binance", "Kraken"],
        exchanges_via_sucursal_espanola=["Binance"],
    )

    assert result["success"] is True
    assert "Binance" in result["exchanges_sucursal_espanola_excluidos"]
    assert "Kraken" in result["exchanges_afectados"]
    assert "Binance" not in result["exchanges_afectados"]


@pytest.mark.asyncio
async def test_721_recomendacion_menciona_binance_spain():
    """Las recomendaciones deben mencionar el caso Binance Spain SL como
    aclaracion para evitar falsos positivos."""
    from app.tools.modelo_721_tool import check_modelo_721_tool

    result = await check_modelo_721_tool(
        crypto_extranjero_valor=30_000,
        exchanges_extranjeros=["Binance"],
    )

    recs_text = " ".join(result["recomendaciones"]).lower()
    assert "binance spain" in recs_text or "sucursal" in recs_text
