"""
Tests for Modelo 131 LLM tool wrapper (`calculate_modelo_131_tool`).

The tool is a thin wrapper around `Modelo131Calculator` so the numeric results
match exactly the (already tested) calculator service. These tests verify:

  - Tool returns success + formatted_response.
  - restricted_mode bloquea el cálculo.
  - Validación de inputs (trimestre, actividad_tipo).
  - Routing a apartado correcto (I/II/III).
  - Reducciones territoriales propagadas.
  - Plazo 4T = 1-30 enero (NO 1-20).
  - Schema OpenAI function-calling exporta los campos esperados.
  - Respuesta formateada incluye casillas y plazo.
"""

import pytest

from app.tools.modelo_131_tool import (
    MODELO_131_TOOL,
    calculate_modelo_131_tool,
)

# ===========================================================================
# Casos AEAT del audit
# ===========================================================================


@pytest.mark.asyncio
async def test_caso_a_bar_pequeno_madrid():
    """Caso A: bar Madrid, 1T, 18.000 datos-base, 0 asalariados, prev 11.500.

    Esperado: 360 - 25 (minoración) = 335 EUR.
    """
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=11500,
    )
    assert result["success"] is True
    assert result["resultado_final"] == 335.0
    assert result["apartado"] == "I"
    assert result["tipo_aplicado"] == 2.0


@pytest.mark.asyncio
async def test_caso_d_agricultor_apartado_iii():
    """Caso D: agricultor Galicia, 25.000 ingresos trimestre → 500 EUR."""
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=25000,
    )
    assert result["success"] is True
    assert result["resultado_final"] == 500.0
    assert result["apartado"] == "III"


@pytest.mark.asyncio
async def test_caso_e_bar_ceuta():
    """Caso E: bar Ceuta, 18.000 datos-base, 0 asalariados, prev 11.500.

    360 - 60% reducción = 144. Minoración 25 → 119 EUR.
    """
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=11500,
        ceuta_melilla=True,
    )
    assert result["success"] is True
    assert result["resultado_final"] == 119.0
    assert result["territory"] == "Ceuta/Melilla"


# ===========================================================================
# Restricted mode (bloqueo plan Particular)
# ===========================================================================


@pytest.mark.asyncio
async def test_restricted_mode_bloquea():
    """restricted_mode=True devuelve error y NO calcula."""
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        restricted_mode=True,
    )
    assert result["success"] is False
    assert result["error"] == "restricted"
    # No debe haber resultado calculado
    assert "resultado_final" not in result


# ===========================================================================
# Validación de inputs
# ===========================================================================


@pytest.mark.asyncio
async def test_trimestre_invalido():
    result = await calculate_modelo_131_tool(
        trimestre=5,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
    )
    assert result["success"] is False
    assert "trimestre" in result["error"].lower() or "1, 2, 3 o 4" in result["error"]


@pytest.mark.asyncio
async def test_trimestre_cero():
    result = await calculate_modelo_131_tool(
        trimestre=0,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
    )
    assert result["success"] is False


@pytest.mark.asyncio
async def test_actividad_tipo_invalido():
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="otra",
    )
    assert result["success"] is False
    assert "actividad" in result["error"].lower()


# ===========================================================================
# Plazo 4T (fix audit: 1-30 enero NO 1-20)
# ===========================================================================


@pytest.mark.asyncio
async def test_plazo_4t_es_30_enero():
    """Plazo 4T = 1-30 enero del año siguiente."""
    result = await calculate_modelo_131_tool(
        trimestre=4,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
    )
    assert result["success"] is True
    assert "30 de enero" in result["plazo"]
    assert "30 de enero" in result["formatted_response"]


@pytest.mark.asyncio
async def test_plazo_1t_es_20_abril():
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="sin_datos_base",
        volumen_ingresos_trimestre=1000,
    )
    assert result["success"] is True
    assert "20 de abril" in result["plazo"]


# ===========================================================================
# Schema OpenAI function-calling
# ===========================================================================


def test_schema_tiene_nombre_correcto():
    assert MODELO_131_TOOL["function"]["name"] == "calculate_modelo_131"


def test_schema_required_fields():
    required = MODELO_131_TOOL["function"]["parameters"]["required"]
    assert "trimestre" in required
    assert "actividad_tipo" in required


def test_schema_actividad_tipo_enum():
    """El enum de actividad_tipo debe incluir los 3 apartados."""
    props = MODELO_131_TOOL["function"]["parameters"]["properties"]
    enum = props["actividad_tipo"]["enum"]
    assert set(enum) == {"empresarial", "sin_datos_base", "agraria"}


def test_schema_ceuta_melilla_y_la_palma_disponibles():
    """Las dos reducciones territoriales deben estar en el schema."""
    props = MODELO_131_TOOL["function"]["parameters"]["properties"]
    assert "ceuta_melilla" in props
    assert "la_palma" in props


# ===========================================================================
# Formatted response
# ===========================================================================


@pytest.mark.asyncio
async def test_formatted_response_incluye_casillas():
    """formatted_response debe mencionar las casillas oficiales."""
    result = await calculate_modelo_131_tool(
        trimestre=2,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=20000,
        num_asalariados=1,
    )
    assert result["success"] is True
    txt = result["formatted_response"]
    # Casillas relevantes deben aparecer en el output
    assert "[01]" in txt
    assert "[02]" in txt
    assert "[03]" in txt
    assert "[06]" in txt
    assert "[12]" in txt
    # Plazo
    assert "20 de julio" in txt


@pytest.mark.asyncio
async def test_formatted_response_apartado_iii_menciona_agraria():
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=10000,
    )
    assert result["success"] is True
    txt = result["formatted_response"].lower()
    assert "agr" in txt  # agrícolas, agrarias, etc.
    assert "[04]" in result["formatted_response"]
    assert "[05]" in result["formatted_response"]


@pytest.mark.asyncio
async def test_formatted_response_resultado_cero_indica_presentar():
    """Cuando resultado=0 el mensaje indica que igualmente debe presentarse."""
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=0,
    )
    assert result["success"] is True
    assert result["resultado_final"] == 0
    assert (
        "presentar" in result["formatted_response"].lower()
        or "sin ingreso" in result["formatted_response"].lower()
    )


# ===========================================================================
# La Palma reduction (caller debe verificar vigencia)
# ===========================================================================


@pytest.mark.asyncio
async def test_la_palma_reduccion_aplicada():
    """Si la_palma=True, reducción 60% aplicada."""
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
        num_asalariados=0,
        la_palma=True,
    )
    assert result["success"] is True
    assert result["territory"] == "La Palma"
    # 10.000 × 2% = 200. Reducción 60% = 80
    assert result["resultado_final"] == 80.0


# ===========================================================================
# Routing apartado correcto
# ===========================================================================


@pytest.mark.asyncio
async def test_routing_empresarial_a_apartado_i():
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
    )
    assert result["apartado"] == "I"


@pytest.mark.asyncio
async def test_routing_sin_datos_base_a_apartado_ii():
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="sin_datos_base",
        volumen_ingresos_trimestre=5000,
    )
    assert result["apartado"] == "II"


@pytest.mark.asyncio
async def test_routing_agraria_a_apartado_iii():
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=5000,
    )
    assert result["apartado"] == "III"


# ===========================================================================
# Tipo según asalariados (4/3/2%)
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "num_asalariados,tipo_esperado",
    [
        (0, 2.0),
        (1, 3.0),
        (2, 4.0),
        (5, 4.0),
    ],
)
async def test_tipo_segun_asalariados(num_asalariados, tipo_esperado):
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
        num_asalariados=num_asalariados,
    )
    assert result["success"] is True
    assert result["tipo_aplicado"] == tipo_esperado
