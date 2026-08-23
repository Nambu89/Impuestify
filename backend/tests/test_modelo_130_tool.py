"""
Tests for Modelo 130 LLM tool wrapper (`calculate_modelo_130_tool`).

These tests cover the gaps documented in the audit
`docs/audits/modelo_130_validation_2026-05.md`:

- C1: casillas 05/06 correctly labeled (05 = pagos previos, 06 = retenciones).
- A1: Sección II (actividades agrícolas/ganaderas/forestales) — 2% rate.
- A2: regla del 70% (Art. 109.2/3 RIRPF) — dispensa por retención.
- A3: regla del 50% para Gipuzkoa (Norma Foral).
- A4: Art. 80 bis con escalones planos (NO interpolación lineal).
- A5: casilla 18 (autoliquidación complementaria).

The tool is now a thin wrapper around `Modelo130Calculator` so the numeric
results match exactly the (already tested) calculator service.
"""

import pytest

from app.tools.modelo_130_tool import calculate_modelo_130_tool

# ===========================================================================
# AEAT cases — Casos 1-5 del audit (validación con normativa)
# ===========================================================================


@pytest.mark.asyncio
async def test_caso_aeat_1_basico():
    """Caso 1: Profesional Madrid 2T, sin retenciones ni pagos previos.

    Esperado AEAT: rendimiento neto 20.000 → 20% → 4.000 EUR.
    """
    result = await calculate_modelo_130_tool(
        trimestre=2,
        ingresos_computables=30000,
        gastos_deducibles=10000,
        rendimiento_neto_previo_anual=25000,  # > 12.000 → sin art 80 bis
    )
    assert result["success"] is True
    assert result["resultado_final"] == 4000.0
    assert result["seccion_i"]["rendimiento_neto"] == 20000.0


@pytest.mark.asyncio
async def test_caso_aeat_2_retenciones_y_pagos():
    """Caso 2: Profesional con retenciones y pagos previos (3T).

    Esperado: 30.000 × 20% − 2.000 − 3.000 = 1.000 EUR.
    """
    result = await calculate_modelo_130_tool(
        trimestre=3,
        ingresos_computables=45000,
        gastos_deducibles=15000,
        retenciones_ingresos_cuenta=2000,
        pagos_fraccionados_anteriores=3000,
        rendimiento_neto_previo_anual=30000,
    )
    assert result["success"] is True
    assert result["resultado_final"] == 1000.0


@pytest.mark.asyncio
async def test_caso_aeat_3_art_80bis_8000():
    """Caso 3: Aplicación art. 80 bis (rend prev 8.000 EUR).

    Esperado: cuota 2.000 − minoración 100 = 1.900 EUR.
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=20000,
        gastos_deducibles=10000,
        rendimiento_neto_previo_anual=8000,
    )
    assert result["success"] is True
    assert result["deduccion_80bis"] == 100.0
    assert result["resultado_final"] == 1900.0


@pytest.mark.asyncio
async def test_caso_aeat_4_vivienda_habitual():
    """Caso 4: Vivienda habitual (Madrid).

    Esperado: rendimiento neto 40.000 × 2% = 800 → cap 660,14 EUR/trim.
    Resultado: 8.000 (cuota) − 660,14 = 7.339,86.
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=50000,
        gastos_deducibles=10000,
        tiene_vivienda_habitual=True,
        rendimiento_neto_previo_anual=25000,
    )
    assert result["success"] is True
    # 40.000 × 20% = 8.000; vivienda cap 660,14 → 8.000 − 660,14 = 7.339,86
    assert result["casilla_16_vivienda"] == 660.14
    assert result["resultado_final"] == 7339.86


@pytest.mark.asyncio
async def test_caso_aeat_5_ceuta_melilla_8pct():
    """Caso 5: Ceuta/Melilla 1T → 8% en lugar del 20%.

    Esperado: rend neto 10.000 × 8% = 800 EUR.
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=20000,
        gastos_deducibles=10000,
        ceuta_melilla=True,
        rendimiento_neto_previo_anual=15000,
    )
    assert result["success"] is True
    assert result["resultado_final"] == 800.0
    assert (
        "Ceuta" in result["formatted_response"] or "ceuta" in result["formatted_response"].lower()
    )


# ===========================================================================
# C1: Casillas 05 (pagos previos) y 06 (retenciones) correctamente etiquetadas
# ===========================================================================


@pytest.mark.asyncio
async def test_c1_casilla_05_es_pagos_previos():
    """Casilla 05 = PAGOS FRACCIONADOS ANTERIORES (no retenciones)."""
    result = await calculate_modelo_130_tool(
        trimestre=3,
        ingresos_computables=20000,
        gastos_deducibles=5000,
        pagos_fraccionados_anteriores=750,
        retenciones_ingresos_cuenta=0,
    )
    assert result["success"] is True
    # Output canonical name + value match
    assert result["seccion_i"]["pagos_anteriores"] == 750.0
    # Formatted response must label casilla 05 = pagos previos
    txt = result["formatted_response"].lower()
    assert "[05]" in txt or "05]" in txt
    # Pagos previos line includes the 750 value next to "05"
    assert "pagos fraccionados" in txt
    assert "750" in result["formatted_response"]


@pytest.mark.asyncio
async def test_c1_casilla_06_es_retenciones():
    """Casilla 06 = RETENCIONES E INGRESOS A CUENTA (no pagos previos)."""
    result = await calculate_modelo_130_tool(
        trimestre=2,
        ingresos_computables=20000,
        gastos_deducibles=5000,
        retenciones_ingresos_cuenta=425,
        pagos_fraccionados_anteriores=0,
    )
    assert result["success"] is True
    assert result["seccion_i"]["retenciones"] == 425.0
    txt = result["formatted_response"].lower()
    assert "[06]" in txt or "06]" in txt
    assert "retenciones" in txt
    assert "425" in result["formatted_response"]


# ===========================================================================
# A4: Art. 80 bis con ESCALONES PLANOS (no interpolación)
# ===========================================================================


@pytest.mark.asyncio
async def test_a4_art_80bis_escalonado_9500():
    """Art. 80 bis con rend prev 9.500 → 75 EUR (escalón plano), NO 62,50."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=20000,
        gastos_deducibles=10000,
        rendimiento_neto_previo_anual=9500,
    )
    assert result["success"] is True
    # Antes el tool devolvía 62.5 por interpolación lineal (BUG A4)
    # La normativa fija escalón plano: 9.001-10.000 → 75 EUR
    assert result["deduccion_80bis"] == 75.0


@pytest.mark.asyncio
async def test_a4_art_80bis_escalonado_10500():
    """Art. 80 bis con rend prev 10.500 → 50 EUR (escalón plano)."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=20000,
        gastos_deducibles=10000,
        rendimiento_neto_previo_anual=10500,
    )
    assert result["success"] is True
    assert result["deduccion_80bis"] == 50.0


@pytest.mark.asyncio
async def test_a4_art_80bis_escalonado_11500():
    """Art. 80 bis con rend prev 11.500 → 25 EUR (escalón plano)."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=20000,
        gastos_deducibles=10000,
        rendimiento_neto_previo_anual=11500,
    )
    assert result["success"] is True
    assert result["deduccion_80bis"] == 25.0


# ===========================================================================
# A5: Casilla 18 (autoliquidación complementaria)
# ===========================================================================


@pytest.mark.asyncio
async def test_a5_complementaria_resta_resultado_anterior():
    """Casilla 18: complementaria resta el resultado de la auto anterior.

    Caso: cuota 2.000, complementaria previa 1.500 → resultado 500.
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=20000,
        gastos_deducibles=10000,
        rendimiento_neto_previo_anual=20000,
        resultado_anterior_complementaria=1500,
    )
    assert result["success"] is True
    assert result["casilla_18_complementaria"] == 1500.0
    assert result["resultado_final"] == 500.0


@pytest.mark.asyncio
async def test_a5_sin_complementaria_no_afecta():
    """Si no hay complementaria, casilla 18 = 0 y resultado igual al normal."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=20000,
        gastos_deducibles=10000,
        rendimiento_neto_previo_anual=20000,
    )
    assert result["success"] is True
    assert result["casilla_18_complementaria"] == 0.0
    assert result["resultado_final"] == 2000.0


# ===========================================================================
# A1: Sección II — actividades agrícolas/ganaderas/forestales (2%)
# ===========================================================================


@pytest.mark.asyncio
async def test_a1_agricola_2pct_basico():
    """Agricultor: 2% sobre volumen ingresos − retenciones del trimestre.

    Volumen 30.000 × 2% = 600; retenciones 50 → resultado 550.
    """
    result = await calculate_modelo_130_tool(
        trimestre=2,
        actividad_agraria=True,
        volumen_ingresos_agrario=30000,
        retenciones_agrario=50,
        # ingresos/gastos no aplican en sección II
        ingresos_computables=0,
        gastos_deducibles=0,
    )
    assert result["success"] is True
    assert result.get("seccion_ii") is not None
    assert result["seccion_ii"]["tipo_aplicado"] == 2.0
    assert result["seccion_ii"]["casillas"]["09_cuota_pct"] == 600.0
    assert result["resultado_final"] == 550.0


@pytest.mark.asyncio
async def test_a1_agricola_ceuta_melilla_0_8pct():
    """Agricultor en Ceuta/Melilla: 2% × 0,40 = 0,8% (Art. 110.2 RIRPF)."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        actividad_agraria=True,
        ceuta_melilla=True,
        volumen_ingresos_agrario=10000,
        retenciones_agrario=0,
        ingresos_computables=0,
        gastos_deducibles=0,
    )
    assert result["success"] is True
    # 10.000 × 0,8% = 80
    assert result["seccion_ii"]["tipo_aplicado"] == 0.8
    assert result["resultado_final"] == 80.0


# ===========================================================================
# A2/A3: Dispensa 70% (común) / 50% (Gipuzkoa) por retención
# ===========================================================================


@pytest.mark.asyncio
async def test_a2_dispensa_70pct_comun():
    """Profesional con ≥70% retención año anterior NO está obligado (Art. 109.2)."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=50000,
        gastos_deducibles=10000,
        es_profesional=True,
        pct_retencion_anio_anterior=85.0,  # ≥ 70 → dispensa
    )
    # Tool debe alertar y NO devolver "a ingresar" como cifra principal
    assert result["success"] is True
    assert result.get("dispensado") is True
    assert (
        "no obligado" in result["formatted_response"].lower()
        or "no estás obligado" in result["formatted_response"].lower()
        or "dispensa" in result["formatted_response"].lower()
    )


@pytest.mark.asyncio
async def test_a2_no_dispensa_si_pct_bajo():
    """Profesional con <70% retención SIGUE obligado a presentar."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=50000,
        gastos_deducibles=10000,
        es_profesional=True,
        pct_retencion_anio_anterior=40.0,  # < 70 → obligado
        rendimiento_neto_previo_anual=30000,
    )
    assert result["success"] is True
    assert result.get("dispensado") is False
    assert result["resultado_final"] > 0


@pytest.mark.asyncio
async def test_a3_dispensa_50pct_gipuzkoa():
    """En Gipuzkoa la dispensa profesional se activa con ≥ 50% (no 70%)."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=50000,
        gastos_deducibles=10000,
        es_profesional=True,
        pct_retencion_anio_anterior=55.0,  # ≥ 50% → dispensa en Gipuzkoa
        territorio="Gipuzkoa",
    )
    assert result["success"] is True
    assert result.get("dispensado") is True


@pytest.mark.asyncio
async def test_a3_gipuzkoa_no_dispensa_si_pct_bajo():
    """En Gipuzkoa con <50% retención, sigue obligado."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=50000,
        gastos_deducibles=10000,
        es_profesional=True,
        pct_retencion_anio_anterior=40.0,
        territorio="Gipuzkoa",
    )
    assert result["success"] is True
    assert result.get("dispensado") is False


# ===========================================================================
# Edge cases / regresion
# ===========================================================================


@pytest.mark.asyncio
async def test_restricted_mode_blocks():
    """restricted_mode=True devuelve bloqueo."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=15000,
        gastos_deducibles=5000,
        restricted_mode=True,
    )
    assert result["success"] is False
    assert result["error"] == "restricted"


@pytest.mark.asyncio
async def test_trimestre_invalido():
    """Trimestre fuera de 1-4 devuelve error."""
    result = await calculate_modelo_130_tool(
        trimestre=5,
        ingresos_computables=10000,
        gastos_deducibles=2000,
    )
    assert result["success"] is False


@pytest.mark.asyncio
async def test_rendimiento_neto_negativo_floor_zero():
    """Rendimiento neto negativo → resultado 0 (no se ingresa)."""
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=3000,
        gastos_deducibles=5000,
    )
    assert result["success"] is True
    assert result["resultado_final"] == 0.0


@pytest.mark.asyncio
async def test_casilla_03_negativa_conserva_signo():
    """Casilla 03 en pérdidas conserva el signo; la 04 se topa en 0.

    El diseño de registro oficial de la AEAT
    (docs/AEAT/modelo-130-2026/DR130e15v12.xls) declara "[03] Rendimiento neto
    ([01] - [02])" como campo de tipo "N" (numérico CON signo), mientras que
    "[04] 20 por 100 del importe de la casilla [03]" es de tipo "Num" (sin
    signo). Topar la casilla 03 en 0 borraría la pérdida del trimestre: como la
    sección I es acumulada desde el 1 de enero (art. 110.1.a RIRPF), ese
    negativo es justo lo que rebaja el rendimiento neto del trimestre
    siguiente.
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=3000,
        gastos_deducibles=5000,
    )
    assert result["success"] is True
    assert result["seccion_i"]["rendimiento_neto"] == -2000.0
    assert result["seccion_i"]["veinte_porciento"] == 0.0
    assert result["casillas"]["03_rendimiento_neto"] == -2000.0


# ===========================================================================
# Casilla 13 — la minoración NO se regala cuando no consta el ejercicio
# anterior (art. 110.3.c RIRPF)
# ===========================================================================


@pytest.mark.asyncio
async def test_casilla_13_sin_dato_ejercicio_anterior_no_minora():
    """Si NO se facilita el rendimiento del ejercicio anterior → minoración 0.

    Regresión. Antes, `rendimiento_neto_previo_anual` tenía por defecto 0.0 y
    el calculador lo leía como el hecho "el año pasado gané 0 EUR", que cae en
    el primer tramo del art. 110.3.c) RIRPF y regalaba los 100 EUR/trimestre a
    CUALQUIER usuario que no rellenara el dato — hasta 400 EUR/año de menos
    ingresados, en los tres frentes (chat, API y PDF).
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=15000,
        gastos_deducibles=5000,
    )
    assert result["success"] is True
    assert result["deduccion_80bis"] == 0.0
    # 20% de 10.000 = 2.000, sin minoración.
    assert result["resultado_final"] == 2000.0


@pytest.mark.asyncio
async def test_casilla_13_cero_explicito_si_minora():
    """Un 0 EXPLÍCITO sí es un dato: 0 <= 9.000 → 100 EUR de minoración.

    Art. 110.3.c) RIRPF, primer tramo ("Igual o inferior a 9.000 → 100").
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=15000,
        gastos_deducibles=5000,
        rendimiento_neto_previo_anual=0.0,
    )
    assert result["success"] is True
    assert result["deduccion_80bis"] == 100.0
    assert result["resultado_final"] == 1900.0


@pytest.mark.asyncio
async def test_importes_en_formato_espanol():
    """Los importes se escriben 30.000,00 y no 30,000.00.

    La respuesta va directa al usuario en castellano: el punto es el separador
    de millares y la coma el decimal. Mismo criterio que el tool del 131.
    """
    result = await calculate_modelo_130_tool(
        trimestre=1,
        ingresos_computables=30000,
        gastos_deducibles=0,
    )
    assert result["success"] is True
    txt = result["formatted_response"]
    assert "30.000,00 EUR" in txt
    assert "30,000.00" not in txt
