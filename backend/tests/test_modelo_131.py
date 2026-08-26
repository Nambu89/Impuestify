"""
Tests for Modelo 131 (Pago Fraccionado IRPF Estimación Objetiva — Módulos).

Cobertura:
  - Apartado I (empresarial): tipos 4/3/2% según asalariados.
  - Apartado II (sin datos-base): 2% sobre ingresos trimestre.
  - Apartado III (agraria): 2% sobre ingresos trimestre.
  - Reducción Ceuta/Melilla 60%.
  - Reducción La Palma 60%.
  - Minoración rendimientos bajos (escalonada plana).
  - Edge cases: rend negativo, num_asalariados negativo, quarter inválido.
  - Casos AEAT verificados (A-G del audit modelo_131_validation_2026-05.md).
"""

import pytest

from app.utils.calculators.modelo_131 import Modelo131Calculator


@pytest.fixture
def calc():
    return Modelo131Calculator(repo=None)


# ===========================================================================
# Apartado I — Empresarial con datos-base
# ===========================================================================


@pytest.mark.asyncio
async def test_apartado_i_sin_asalariados_2pct(calc):
    """Bar pequeño sin asalariados → tipo 2%."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=15000,  # > 12.000 → sin minoración
    )
    # 18.000 × 2% = 360
    assert r["apartado"] == "I"
    assert r["tipo_aplicado"] == 2.0
    assert r["casillas"]["03_resultado_empresarial"] == 360.0
    assert r["casillas"]["12_resultado_final"] == 360.0
    assert r["resultado"] == 360.0
    assert r["territory"] == "Comun"


@pytest.mark.asyncio
async def test_apartado_i_un_asalariado_3pct(calc):
    """Bar con 1 asalariado → tipo 3%."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=1,
        rendimiento_neto_anterior=15000,
    )
    # 18.000 × 3% = 540
    assert r["tipo_aplicado"] == 3.0
    assert r["casillas"]["03_resultado_empresarial"] == 540.0
    assert r["resultado"] == 540.0


@pytest.mark.asyncio
async def test_apartado_i_dos_asalariados_4pct(calc):
    """Bar con 2 asalariados → tipo 4%."""
    r = await calc.calculate(
        quarter=2,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=2,
        rendimiento_neto_anterior=15000,
    )
    # 18.000 × 4% = 720
    assert r["tipo_aplicado"] == 4.0
    assert r["casillas"]["03_resultado_empresarial"] == 720.0


@pytest.mark.asyncio
async def test_apartado_i_muchos_asalariados_4pct(calc):
    """Más de 2 asalariados sigue siendo 4% (no escala)."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=10,
        rendimiento_neto_anterior=15000,
    )
    assert r["tipo_aplicado"] == 4.0


# ===========================================================================
# Casos AEAT del audit (A-G)
# ===========================================================================


@pytest.mark.asyncio
async def test_caso_a_bar_pequeno_madrid(calc):
    """Caso A audit: bar sin asalariados, Madrid, 1T 2026.

    Datos-base: 18.000 €. Asalariados: 0 → 2%.
    Cuota = 360 €. Minoración rendimiento previo 11.500 → 25 €.
    Resultado = 335 €.
    """
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=11500,  # tramo 11.001-12.000 → 25 EUR
    )
    assert r["casillas"]["03_resultado_empresarial"] == 360.0
    assert r["desglose"]["minoracion_rendimientos_bajos"] == 25.0
    assert r["resultado"] == 335.0
    assert r["plazo"] == "1 al 20 de abril"


@pytest.mark.asyncio
async def test_caso_b_bar_un_asalariado_andalucia(calc):
    """Caso B audit: bar 1 asalariado, Andalucía. 18.000 × 3% = 540 €."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=1,
        rendimiento_neto_anterior=15000,  # > 12.000 → sin minoración
    )
    assert r["resultado"] == 540.0


@pytest.mark.asyncio
async def test_caso_c_taxi_sevilla(calc):
    """Caso C audit: taxi 12.000 datos-base, 0 asalariados, Sevilla.

    Cuota 240. Minoración rendimiento previo 9.500 → 75 EUR. Resultado = 165.
    """
    r = await calc.calculate(
        quarter=2,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=12000,
        num_asalariados=0,
        rendimiento_neto_anterior=9500,  # tramo 9.001-10.000 → 75 EUR
    )
    assert r["casillas"]["03_resultado_empresarial"] == 240.0
    assert r["desglose"]["minoracion_rendimientos_bajos"] == 75.0
    assert r["resultado"] == 165.0


@pytest.mark.asyncio
async def test_caso_d_agricultor_galicia(calc):
    """Caso D audit: agricultor Galicia, ingresos 25.000, apartado III.

    25.000 × 2% = 500 €. Sin minoración rendimientos bajos (no aplica a III).
    """
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=25000,
    )
    assert r["apartado"] == "III"
    assert r["casillas"]["04_volumen_ingresos_agrario"] == 25000.0
    assert r["casillas"]["05_cuota_agraria"] == 500.0
    assert r["resultado"] == 500.0


@pytest.mark.asyncio
async def test_caso_e_bar_ceuta(calc):
    """Caso E audit: bar Ceuta, mismos datos que A.

    Cuota 360. Reducción 60% Ceuta → 144. Sin minoración a este resultado
    porque el rendimiento previo del caso E es 11.500 (igual que A).
    Aplicando minoración 25 al resultado tras reducción → 144 - 25 = 119.
    """
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=11500,
        ceuta_melilla=True,
    )
    assert r["territory"] == "Ceuta/Melilla"
    assert r["casillas"]["06_total_cuotas"] == 360.0
    # Reducción 60% sobre 360 = 216
    assert r["casillas"]["07_reducciones"] == 216.0
    # Resultado tras reducción = 144
    assert r["casillas"]["08_resultado_tras_reducciones"] == 144.0
    # Minoración 25 → 144 - 25 = 119
    assert r["resultado"] == 119.0


@pytest.mark.asyncio
async def test_caso_g_sin_datos_base(calc):
    """Caso G audit: alta nueva sin datos-base, ingresos 1T 5.000.

    5.000 × 2% = 100 €.
    """
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="sin_datos_base",
        volumen_ingresos_trimestre=5000,
    )
    assert r["apartado"] == "II"
    assert r["resultado"] == 100.0


# ===========================================================================
# Minoración rendimientos bajos (tabla escalonada plana)
# ===========================================================================


@pytest.mark.parametrize(
    "rend_anterior,esperada",
    [
        (5000.0, 100.0),  # tramo ≤ 9.000 → 100
        (9000.0, 100.0),  # límite inferior tramo 100
        (9001.0, 75.0),  # tramo 9.001-10.000 → 75
        (10000.0, 75.0),  # límite tramo 75
        (10500.0, 50.0),  # tramo 10.001-11.000 → 50
        (11500.0, 25.0),  # tramo 11.001-12.000 → 25
        (12000.0, 25.0),  # límite tramo 25
        (12001.0, 0.0),  # > 12.000 → 0
        (50000.0, 0.0),  # > 12.000 → 0
        # 0 EXPLÍCITO = "el ejercicio anterior gané 0 EUR". El art. 110.3.c)
        # RIRPF dice "igual o inferior a 9.000 euros" y no excluye el cero, así
        # que sí da derecho al primer tramo.
        (0.0, 100.0),
        # None = dato NO facilitado → sin minoración.
        (None, 0.0),
    ],
)
def test_minoracion_rendimientos_bajos(calc, rend_anterior, esperada):
    """La tabla es escalonada PLANA, no interpolación lineal."""
    assert calc._minoracion_rendimientos_bajos(rend_anterior) == esperada


# ---------------------------------------------------------------------------
# Regresión: dato ausente vs cero explícito (casilla [09], art. 110.3.c RIRPF)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_minoracion_no_se_aplica_si_falta_el_dato(calc):
    """Sin `rendimiento_neto_anterior` NO hay minoración de la casilla [09].

    Art. 110.3.c) RIRPF (RD 439/2007): "Cuando la cuantía de los rendimientos
    netos de actividades económicas del ejercicio anterior sea igual o inferior
    a 12.000 euros, [se deducirá] el importe que resulte del siguiente cuadro".
    La deducción está condicionada a que CONSTE esa cuantía; si el llamante no
    la facilita no se puede afirmar que se cumpla el supuesto, y aplicarla por
    defecto rebajaría el pago fraccionado de cualquiera que no rellene el dato.
    """
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        # rendimiento_neto_anterior omitido a propósito
    )
    assert r["desglose"]["minoracion_rendimientos_bajos"] == 0.0
    assert r["desglose"]["rendimiento_neto_anterior"] is None
    # 18.000 × 2% = 360, sin minoración
    assert r["resultado"] == 360.0


@pytest.mark.asyncio
async def test_minoracion_se_aplica_con_cero_explicito(calc):
    """Un 0 EXPLÍCITO sí es un dato y sí aplica los 100 EUR del primer tramo.

    Art. 110.3.c) RIRPF: primer tramo "Igual o inferior a 9.000 euros ... 100".
    Cero es igual o inferior a 9.000 y la norma no lo excluye, así que el
    contribuyente que declara haber tenido un ejercicio anterior a cero tiene
    derecho a la minoración. Tratar el 0 como "sin dato" —que es lo que hacía
    esta calculadora— le hacía ingresar 100 EUR de más cada trimestre.
    """
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=0.0,
    )
    assert r["desglose"]["minoracion_rendimientos_bajos"] == 100.0
    assert r["desglose"]["rendimiento_neto_anterior"] == 0.0
    # 360 − 100 = 260
    assert r["resultado"] == 260.0


# ===========================================================================
# Apartado III — Agraria + Ceuta/Melilla
# ===========================================================================


@pytest.mark.asyncio
async def test_agraria_ceuta_melilla(calc):
    """Agraria Ceuta: 10.000 × 2% = 200. Reducción 60% → 80."""
    r = await calc.calculate(
        quarter=2,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=10000,
        ceuta_melilla=True,
    )
    assert r["casillas"]["05_cuota_agraria"] == 200.0
    assert r["casillas"]["07_reducciones"] == 120.0
    assert r["resultado"] == 80.0


@pytest.mark.asyncio
async def test_agraria_con_retenciones(calc):
    """Agraria con retenciones de 100.

    Cuota 200, sin reducción → 200 - 100 = 100.
    """
    r = await calc.calculate(
        quarter=3,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=10000,
        retenciones_trimestre=100,
    )
    assert r["resultado"] == 100.0


# ===========================================================================
# Reducción La Palma
# ===========================================================================


@pytest.mark.asyncio
async def test_la_palma_reduccion_60pct(calc):
    """La Palma: bar sin asalariados con datos del caso A. Reducción 60%."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=18000,
        num_asalariados=0,
        rendimiento_neto_anterior=15000,
        la_palma=True,
    )
    # 360 - 60% = 144
    assert r["territory"] == "La Palma"
    assert r["casillas"]["07_reducciones"] == 216.0
    assert r["resultado"] == 144.0


@pytest.mark.asyncio
async def test_ceuta_prevalece_sobre_la_palma(calc):
    """Si ambas flags activas, prevalece Ceuta/Melilla (no son acumulables)."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
        num_asalariados=0,
        rendimiento_neto_anterior=15000,
        ceuta_melilla=True,
        la_palma=True,
    )
    assert r["territory"] == "Ceuta/Melilla"
    assert r["desglose"]["reduccion_concepto"] == "Ceuta/Melilla 60%"


# ===========================================================================
# Edge cases
# ===========================================================================


@pytest.mark.asyncio
async def test_rendimiento_negativo_no_da_resultado_negativo(calc):
    """Rendimiento neto módulos negativo se trata como 0."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=-5000,
        num_asalariados=0,
    )
    assert r["resultado"] == 0
    assert r["casillas"]["01_rendimiento_neto_modulos"] == 0.0


@pytest.mark.asyncio
async def test_volumen_ingresos_negativo_se_clipa(calc):
    """Volumen de ingresos negativo se trata como 0."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="agraria",
        volumen_ingresos_trimestre=-1000,
    )
    assert r["resultado"] == 0


@pytest.mark.asyncio
async def test_quarter_invalido_raise(calc):
    with pytest.raises(ValueError, match="Quarter"):
        await calc.calculate(
            quarter=5,
            actividad_tipo="empresarial",
            rendimiento_neto_modulos_anual=10000,
        )


@pytest.mark.asyncio
async def test_actividad_tipo_invalido_raise(calc):
    with pytest.raises(ValueError, match="actividad_tipo"):
        await calc.calculate(
            quarter=1,
            actividad_tipo="otra",
            rendimiento_neto_modulos_anual=10000,
        )


def test_num_asalariados_negativo_raise(calc):
    with pytest.raises(ValueError, match="negativo"):
        calc._tipo_segun_asalariados(-1)


# ===========================================================================
# Plazos AEAT (incluido fix 4T = 1-30 enero, no 1-20)
# ===========================================================================


@pytest.mark.asyncio
async def test_plazo_4t_correcto_30_enero(calc):
    """Plazo 4T es 1-30 enero (NO 1-20 como erróneamente seedeado)."""
    r = await calc.calculate(
        quarter=4,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
    )
    assert r["plazo"] == "1 al 30 de enero del año siguiente"


@pytest.mark.asyncio
async def test_plazos_trimestres(calc):
    """Verifica plazos de los 4 trimestres."""
    plazos_esperados = {
        1: "1 al 20 de abril",
        2: "1 al 20 de julio",
        3: "1 al 20 de octubre",
        4: "1 al 30 de enero del año siguiente",
    }
    for q, plazo in plazos_esperados.items():
        r = await calc.calculate(
            quarter=q,
            actividad_tipo="sin_datos_base",
            volumen_ingresos_trimestre=1000,
        )
        assert r["plazo"] == plazo


# ===========================================================================
# Complementaria (casilla 11)
# ===========================================================================


@pytest.mark.asyncio
async def test_complementaria_resta_resultado_anterior(calc):
    """Casilla 11 (complementaria) resta del resultado a ingresar."""
    r = await calc.calculate(
        quarter=4,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=20000,
        num_asalariados=0,
        rendimiento_neto_anterior=20000,  # > 12.000 → sin minoración
        resultado_anterior_complementaria=200,
    )
    # 20.000 × 2% = 400. 400 - 200 = 200
    assert r["casillas"]["03_resultado_empresarial"] == 400.0
    assert r["casillas"]["11_complementaria"] == 200.0
    assert r["resultado"] == 200.0


@pytest.mark.asyncio
async def test_resultado_negativo_se_clipa_a_cero(calc):
    """Si las retenciones superan la cuota, resultado = 0 (no negativo)."""
    r = await calc.calculate(
        quarter=2,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=10000,
        num_asalariados=0,
        retenciones_trimestre=500,
    )
    # cuota 200, retenciones 500 → max(0, 200-500) = 0
    assert r["resultado"] == 0


# ===========================================================================
# Sin datos-base (apartado II)
# ===========================================================================


@pytest.mark.asyncio
async def test_apartado_ii_basico(calc):
    """Apartado II: 8.000 × 2% = 160."""
    r = await calc.calculate(
        quarter=2,
        actividad_tipo="sin_datos_base",
        volumen_ingresos_trimestre=8000,
    )
    assert r["apartado"] == "II"
    assert r["tipo_aplicado"] == 2.0
    assert r["resultado"] == 160.0


@pytest.mark.asyncio
async def test_apartado_ii_ceuta_reduccion(calc):
    """Apartado II en Ceuta: 8.000 × 2% × 40% = 64."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="sin_datos_base",
        volumen_ingresos_trimestre=8000,
        ceuta_melilla=True,
    )
    assert r["resultado"] == 64.0


# ===========================================================================
# Estructura de respuesta
# ===========================================================================


@pytest.mark.asyncio
async def test_estructura_respuesta_completa(calc):
    """La respuesta contiene todas las casillas y el desglose."""
    r = await calc.calculate(
        quarter=1,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=20000,
        num_asalariados=1,
    )
    expected_keys = {
        "01_rendimiento_neto_modulos",
        "02_tipo_aplicable",
        "03_resultado_empresarial",
        "04_volumen_ingresos_agrario",
        "05_cuota_agraria",
        "06_total_cuotas",
        "07_reducciones",
        "08_resultado_tras_reducciones",
        "09_retenciones_trimestre",
        # No hay "10_...": los pagos fraccionados de trimestres anteriores no
        # se deducen en el 131 (ver el bloque de regresión al final). El hueco
        # es deliberado — renumerar 11 y 12 rompería a los consumidores de la
        # API sin ganar nada, porque el prefijo ya es arbitrario.
        "11_complementaria",
        "12_resultado_final",
    }
    assert set(r["casillas"].keys()) == expected_keys
    assert "tipo_pct" in r["desglose"]
    assert "criterio_tipo" in r["desglose"]
    assert "plazo" in r


# ===========================================================================
# REGRESIÓN — el 131 NO deduce los pagos fraccionados de trimestres anteriores
# ===========================================================================
#
# La calculadora aceptó durante un tiempo un parámetro `pagos_anteriores` y lo
# restaba del resultado. Era un error de bulto: hacía que el contribuyente
# ingresara MENOS de lo debido, y se agravaba trimestre a trimestre.
#
# Fundamento (art. 110 RIRPF, RD 439/2007, texto consolidado del BOE):
#
#   - Letra 1.a) — estimación DIRECTA, que es el Modelo 130 y NO este:
#     "el 20 por ciento del rendimiento neto correspondiente al período de
#     tiempo transcurrido desde el primer día del año hasta el último día del
#     trimestre" — base ACUMULADA. Y sólo por eso añade: "De la cantidad
#     resultante por aplicación de lo dispuesto EN ESTA LETRA se deducirán los
#     pagos fraccionados que [...] habría correspondido ingresar en los
#     trimestres anteriores del mismo año". El mandato está literalmente
#     acotado a la letra a). Es la casilla [05] del DR130 ("A deducir: De los
#     trim. anteriores, suma de los importes").
#
#   - Letra 1.b) — estimación OBJETIVA, apartados I y II de ESTE modelo: el
#     4/3/2 % se aplica sobre "los rendimientos netos resultantes de la
#     aplicación de dicho método EN FUNCIÓN DE LOS DATOS-BASE DEL PRIMER DÍA
#     DEL AÑO". La base es idéntica en los cuatro trimestres: no acumula nada,
#     luego no hay nada que descontar.
#
#   - Letra 1.c) — agrarias, apartado III: "el 2 por ciento del volumen de
#     ingresos DEL TRIMESTRE". Tampoco acumula.
#
#   - Apartado 3 — lista CERRADA de lo deducible: a) y b) retenciones e
#     ingresos a cuenta, c) minoración por rendimientos ≤ 12.000 €, d)
#     deducción por vivienda habitual. Ninguna letra menciona los pagos
#     fraccionados previos.
#
# Y el diseño de registro DR131_2026, apartado "IV. Total liquidación", no
# tiene casilla para ese concepto: [07] suma de los pagos fraccionados previos
# DEL TRIMESTRE, [08] retenciones, [09] minoración, [10] Diferencia, [11]
# resultados NEGATIVOS de trimestres anteriores, [12] préstamos vivienda,
# [13] Total, [14] resultado a ingresar de las anteriores declaraciones
# (complementaria), [15] resultado.


@pytest.mark.asyncio
@pytest.mark.parametrize("quarter", [1, 2, 3, 4])
async def test_ningun_trimestre_resta_pagos_de_trimestres_anteriores(calc, quarter):
    """El resultado del 3T es el mismo que el del 1T: el 131 no acumula.

    Art. 110.1.b) RIRPF — la base son los datos-base del primer día del año,
    la misma en los cuatro trimestres.
    """
    r = await calc.calculate(
        quarter=quarter,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=20000,
        num_asalariados=0,
    )
    # 20.000 × 2 % = 400 EUR en CADA trimestre, sin descontar los previos.
    assert r["resultado"] == 400.0
    assert "10_pagos_anteriores" not in r["casillas"]


@pytest.mark.asyncio
async def test_pagos_anteriores_se_ignora_y_no_altera_el_resultado(calc):
    """Un caller antiguo que aún mande `pagos_anteriores` no rompe ni desvía.

    Se absorbe en `**kwargs` y el resultado es idéntico al de no mandarlo. Se
    ignora en silencio a propósito: rechazarlo rompería a los clientes ya
    desplegados sin ganar nada, porque el resultado correcto es calculable sin
    ese dato.
    """
    comun = dict(
        quarter=3,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=20000,
        num_asalariados=0,
        retenciones_trimestre=50,
    )
    sin_parametro = await calc.calculate(**comun)
    con_parametro = await calc.calculate(**comun, pagos_anteriores=300)

    assert con_parametro["casillas"] == sin_parametro["casillas"]
    assert con_parametro["resultado"] == sin_parametro["resultado"] == 350.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("actividad_tipo", "kwargs", "esperado"),
    [
        ("empresarial", {"rendimiento_neto_modulos_anual": 20000, "num_asalariados": 0}, 400.0),
        ("sin_datos_base", {"volumen_ingresos_trimestre": 8000}, 160.0),
        ("agraria", {"volumen_ingresos_trimestre": 10000}, 200.0),
    ],
)
async def test_los_tres_apartados_ignoran_los_pagos_previos(calc, actividad_tipo, kwargs, esperado):
    """Ni el I (110.1.b), ni el II (110.1.b in fine), ni el III (110.1.c)."""
    r = await calc.calculate(
        quarter=4,
        actividad_tipo=actividad_tipo,
        pagos_anteriores=999,
        **kwargs,
    )
    assert r["resultado"] == esperado


@pytest.mark.asyncio
async def test_la_casilla_14_de_la_complementaria_sigue_deduciendose(calc):
    """[14] NO es lo mismo que los pagos previos: no se retira con ellos.

    "A deducir: resultado a ingresar de las anteriores declaraciones" [14] va
    emparejada en el DR131 con el indicador "Declaración complementaria" y el
    número de justificante de la anterior: es lo ingresado en otra
    autoliquidación DEL MISMO trimestre.
    """
    r = await calc.calculate(
        quarter=2,
        actividad_tipo="empresarial",
        rendimiento_neto_modulos_anual=20000,
        num_asalariados=0,
        resultado_anterior_complementaria=150,
    )
    assert r["casillas"]["11_complementaria"] == 150.0
    assert r["resultado"] == 250.0


def test_pagos_anteriores_no_es_un_parametro_de_la_calculadora():
    """La firma no debe volver a declararlo, ni siquiera inerte.

    Los tests de arriba comprueban la aritmética, pero pasarían igual si
    alguien repusiera el parámetro sin usarlo. Y un parámetro formal vuelve a
    salir en la firma pública, en el schema del tool y en el formulario: es el
    camino por el que el campo regresaría.
    """
    import inspect

    params = inspect.signature(Modelo131Calculator.calculate).parameters
    assert "pagos_anteriores" not in params
    # Y sigue habiendo un **kwargs que lo absorba si un caller viejo lo manda.
    assert any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
