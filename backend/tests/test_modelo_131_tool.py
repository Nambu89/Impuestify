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
# Casilla [09] — minoración art. 110.3.c RIRPF: dato ausente vs cero explícito
# ===========================================================================


@pytest.mark.asyncio
async def test_tool_sin_rendimiento_anterior_no_aplica_minoracion():
    """Si el LLM no facilita el dato, NO se aplica la minoración [09].

    Art. 110.3.c) RIRPF (RD 439/2007): "Cuando la cuantía de los rendimientos
    netos de actividades económicas del ejercicio anterior sea igual o inferior
    a 12.000 euros, [se deducirá] el importe que resulte del siguiente cuadro".
    La deducción exige que CONSTE la cuantía del ejercicio anterior. Si el tool
    la asumiera a 0 por defecto, todo usuario que no la mencione en el chat se
    llevaría 100 EUR/trimestre de minoración que no le corresponde.
    """
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        # rendimiento_neto_anterior omitido a propósito
    )
    assert result["success"] is True
    assert result["desglose"]["minoracion_rendimientos_bajos"] == 0.0
    assert result["desglose"]["rendimiento_neto_anterior"] is None
    assert result["resultado_final"] == 360.0
    assert "[09]" not in result["formatted_response"]


@pytest.mark.asyncio
async def test_tool_cero_explicito_si_aplica_minoracion():
    """Un 0 explícito es un dato: aplica los 100 EUR del primer tramo.

    Art. 110.3.c) RIRPF, primer tramo: "Igual o inferior a 9.000 euros ...
    100". Cero es igual o inferior a 9.000 y la norma no lo excluye, así que
    el autónomo que declara un ejercicio anterior a cero tiene derecho a la
    minoración. La versión anterior lo trataba como "sin dato" y le hacía
    ingresar 100 EUR de más cada trimestre.
    """
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=0.0,
    )
    assert result["success"] is True
    assert result["desglose"]["minoracion_rendimientos_bajos"] == 100.0
    assert result["desglose"]["rendimiento_neto_anterior"] == 0.0
    # 18.000 × 2% = 360 − 100 = 260
    assert result["resultado_final"] == 260.0
    # La minoración se etiqueta como casilla [09] y cita la norma vigente
    assert "[09]" in result["formatted_response"]
    assert "110.3.c" in result["formatted_response"]


@pytest.mark.asyncio
async def test_complementaria_es_la_casilla_14_y_pagos_previos_no_se_mencionan():
    """[14] = "A deducir: resultado a ingresar de las anteriores declaraciones".

    En el diseño de registro DR131_2026 la única deducción por declaraciones
    previas es la [14], la de la complementaria. Los pagos fraccionados de
    trimestres anteriores NO se deducen en el 131 ni tienen casilla: el modelo
    no es acumulativo (art. 110.1.b RIRPF — la base son "los datos-base del
    primer día del año"; el mandato de descontar lo ingresado en trimestres
    previos vive en la letra a), acotado a "lo dispuesto EN ESTA LETRA", que es
    la estimación directa del Modelo 130).

    La respuesta al usuario no debe ni nombrarlos: hacerlo invitaba a rellenar
    un dato que le hacía ingresar de menos. Y no pueden etiquetarse con ninguna
    casilla: [10] es "Diferencia" y [11] "Resultados negativos de trimestres
    anteriores", que es otra cosa.
    """
    result = await calculate_modelo_131_tool(
        trimestre=4,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        resultado_anterior_complementaria=40,
    )
    assert result["success"] is True
    txt = result["formatted_response"]
    assert "anteriores declaraciones [14]" in txt
    assert "Pagos fraccionados de trimestres anteriores" not in txt
    assert "[10]" not in txt
    assert "[11]" not in txt


@pytest.mark.asyncio
async def test_el_tool_ignora_pagos_anteriores_y_no_lo_ofrece_en_el_schema():
    """Un `pagos_anteriores` arrastrado de una conversación vieja no rompe.

    El despachador invoca el ejecutor con `**function_args` sin filtrar, así
    que un argumento retirado del schema provocaría un `TypeError` en vez de
    una respuesta. Se absorbe y se ignora: el resultado es el mismo que sin él.
    """
    from app.tools.modelo_131_tool import MODELO_131_TOOL

    props = MODELO_131_TOOL["function"]["parameters"]["properties"]
    assert "pagos_anteriores" not in props

    comun = dict(
        trimestre=3,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
    )
    limpio = await calculate_modelo_131_tool(**comun)
    heredado = await calculate_modelo_131_tool(**comun, pagos_anteriores=250)

    assert heredado["success"] is True
    assert heredado["formatted_response"] == limpio["formatted_response"]


@pytest.mark.asyncio
async def test_importes_en_formato_espanol():
    """Los importes se escriben 18.000,00 y no 18,000.00.

    La respuesta va directa al usuario en castellano: el punto es el separador
    de millares y la coma el decimal.
    """
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
    )
    assert result["success"] is True
    txt = result["formatted_response"]
    assert "18.000,00 EUR" in txt
    assert "18,000.00" not in txt


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("num_asalariados", "esperado"),
    [(0, "2%"), (1, "3%"), (2, "4%")],
)
async def test_porcentaje_sin_decimales_ni_euros(num_asalariados, esperado):
    """El tipo es un porcentaje entero, no un importe ni un 2,0%.

    La misma cifra viaja a tres superficies (chat, PDF y la calculadora
    publica) y las tres deben decir lo mismo: `2%`, `3%` o `4%`.
    """
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=num_asalariados,
    )
    assert result["success"] is True
    txt = result["formatted_response"]
    assert f"Porcentaje aplicable: {esperado}" in txt
    assert "Porcentaje aplicable: 2,00 EUR" not in txt
    assert f"{esperado[0]}.0%" not in txt


@pytest.mark.asyncio
async def test_apartado_ii_tambien_muestra_el_porcentaje_entero():
    result = await calculate_modelo_131_tool(
        trimestre=2,
        actividad_tipo="sin_datos_base",
        volumen_ingresos_trimestre=9000,
    )
    assert result["success"] is True
    assert "Porcentaje aplicable: 2%" in result["formatted_response"]


def test_schema_rendimiento_anterior_prohibe_rellenar_con_cero():
    """El schema debe decirle al LLM que OMITA el dato en vez de poner 0."""
    props = MODELO_131_TOOL["function"]["parameters"]["properties"]
    desc = props["rendimiento_neto_anterior"]["description"]
    assert "110.3.c" in desc
    assert "OMITE" in desc
    assert "rendimiento_neto_anterior" not in MODELO_131_TOOL["function"]["parameters"]["required"]


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
    """formatted_response debe mencionar las casillas OFICIALES del modelo.

    Numeración del diseño de registro DR131_2026 de la AEAT
    (docs/AEAT/modelo-130-2026/DR131_2026.xlsx), apartado I:
      [01] Suma de rendimientos netos
      [02] Pago fraccionado previo: suma de resultados
      [07] Suma de los pagos fraccionados previos del trimestre
      [15] Resultado de la declaración

    OJO: [12] es "Pago de préstamos para la adquisición de vivienda habitual",
    NO el resultado; el "Porcentaje aplicable" no tiene casilla numerada.
    """
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
    assert "[07]" in txt
    assert "[15]" in txt
    # El resultado NUNCA debe etiquetarse como [12]
    assert "[12]" not in txt
    # Plazo
    assert "20 de julio" in txt


@pytest.mark.asyncio
async def test_formatted_response_apartado_iii_menciona_agraria():
    """Apartado III según DR131_2026: [05] volumen de ingresos del trimestre,
    [06] pago fraccionado previo del trimestre."""
    result = await calculate_modelo_131_tool(
        trimestre=1,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=10000,
    )
    assert result["success"] is True
    txt = result["formatted_response"].lower()
    assert "agr" in txt  # agrícolas, agrarias, etc.
    assert "[05]" in result["formatted_response"]
    assert "[06]" in result["formatted_response"]


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


def test_pagos_anteriores_no_es_un_parametro_del_tool():
    """Ni en la firma ni en el schema: el LLM no debe poder ofrecerlo."""
    import inspect

    params = inspect.signature(calculate_modelo_131_tool).parameters
    assert "pagos_anteriores" not in params
    # El **_ignored tiene que seguir ahí: el despachador pasa `**function_args`
    # sin filtrar y un argumento arrastrado no puede reventar la herramienta.
    assert any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
