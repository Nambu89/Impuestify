"""Tests for Modelo 130 Navarra (Pago Fraccionado IRPF foral)."""

import pytest

from app.utils.calculators.modelo_130_navarra import Modelo130NavarraCalculator


@pytest.fixture
def calc():
    return Modelo130NavarraCalculator(repo=None)


# ===========================================================================
# Modalidad primera (penúltimo año + tabla progresiva, ÷4)
# ===========================================================================


@pytest.mark.asyncio
async def test_primera_tramo_6pct(calc):
    """Rend 5.000 ≤ 6.500 → 6%. Cuota anual 300, ÷4 = 75."""
    r = await calc.calculate(
        quarter=1,
        modalidad="primera",
        rend_neto_penultimo=5000,
    )
    assert r["territory"] == "Navarra"
    assert r["modalidad"] == "primera"
    assert r["tipo_aplicado"] == 6.0
    assert r["casillas"]["133_cuota_anual"] == 300.0
    assert r["resultado"] == 75.0


@pytest.mark.asyncio
async def test_primera_tramo_12pct(calc):
    """Rend 10.000 ≤ 12.000 → 12%. Cuota 1.200, ÷4 = 300."""
    r = await calc.calculate(
        quarter=2,
        modalidad="primera",
        rend_neto_penultimo=10000,
    )
    assert r["tipo_aplicado"] == 12.0
    assert r["resultado"] == 300.0


@pytest.mark.asyncio
async def test_primera_tramo_18pct(calc):
    """Rend 20.000 ≤ 24.000 → 18%. Cuota 3.600, ÷4 = 900."""
    r = await calc.calculate(
        quarter=3,
        modalidad="primera",
        rend_neto_penultimo=20000,
    )
    assert r["tipo_aplicado"] == 18.0
    assert r["resultado"] == 900.0


@pytest.mark.asyncio
async def test_primera_tramo_24pct(calc):
    """Rend 50.000 > 24.000 → 24%. Cuota 12.000, ÷4 = 3.000."""
    r = await calc.calculate(
        quarter=4,
        modalidad="primera",
        rend_neto_penultimo=50000,
    )
    assert r["tipo_aplicado"] == 24.0
    assert r["resultado"] == 3000.0


@pytest.mark.asyncio
async def test_primera_con_retenciones(calc):
    """Rend 20.000 → 18% × 20.000 = 3.600. − 800 retenciones = 2.800. ÷4 = 700."""
    r = await calc.calculate(
        quarter=1,
        modalidad="primera",
        rend_neto_penultimo=20000,
        retenciones_penultimo=800,
    )
    assert r["casillas"]["135_cuota_neta_anual"] == 2800.0
    assert r["resultado"] == 700.0


@pytest.mark.asyncio
async def test_primera_retenciones_superan_cuota_clipa(calc):
    """Si retenciones > cuota anual → resultado 0."""
    r = await calc.calculate(
        quarter=1,
        modalidad="primera",
        rend_neto_penultimo=5000,  # cuota anual 300
        retenciones_penultimo=1000,  # > 300
    )
    assert r["resultado"] == 0


@pytest.mark.asyncio
async def test_primera_obligado_presentar_cuota_alta(calc):
    """Rend 20.000 → cuota trim 900 ≥ 100 y rend > 6.500 → obligado."""
    r = await calc.calculate(
        quarter=1,
        modalidad="primera",
        rend_neto_penultimo=20000,
    )
    assert r["obligado_presentar"] is True


@pytest.mark.asyncio
async def test_primera_no_obligado_rend_bajo(calc):
    """Rend 5.000 ≤ 6.500 → no obligado a presentar."""
    r = await calc.calculate(
        quarter=1,
        modalidad="primera",
        rend_neto_penultimo=5000,
    )
    assert r["obligado_presentar"] is False


@pytest.mark.asyncio
async def test_primera_no_obligado_cuota_baja(calc):
    """Rend 6.700 (≤ 12.000 → 12%): cuota anual 804, − 410 retenciones =
    394, ÷4 = 98,50 < 100 → no obligado a presentar."""
    r = await calc.calculate(
        quarter=1,
        modalidad="primera",
        rend_neto_penultimo=6700,
        retenciones_penultimo=410,
    )
    # 6700 × 12% = 804; 804 - 410 = 394; 394 / 4 = 98,50
    assert r["resultado"] == 98.50
    assert r["obligado_presentar"] is False


# ===========================================================================
# Modalidad segunda (acumulado del ejercicio, anualización)
# ===========================================================================


@pytest.mark.asyncio
async def test_segunda_q1_anualizacion_x4(calc):
    """Q1: rend acumulado 3.000, anualizado ×4 = 12.000 → 12%. Cuota 360."""
    r = await calc.calculate(
        quarter=1,
        modalidad="segunda",
        ingresos_acumulados=5000,
        gastos_acumulados=2000,
    )
    assert r["modalidad"] == "segunda"
    # rend_neto_acum = 3.000, anualizado = 12.000 → 12%
    assert r["casillas"]["04_factor_anualizacion"] == 4.0
    assert r["casillas"]["05_rendimiento_neto_anualizado"] == 12000.0
    assert r["tipo_aplicado"] == 12.0
    # cuota = 3.000 × 12% = 360
    assert r["resultado"] == 360.0


@pytest.mark.asyncio
async def test_segunda_q4_anualizacion_x1(calc):
    """Q4: rend acumulado 25.000, anualizado ×1 = 25.000 → 24%. Cuota 6.000."""
    r = await calc.calculate(
        quarter=4,
        modalidad="segunda",
        ingresos_acumulados=40000,
        gastos_acumulados=15000,
    )
    assert r["casillas"]["04_factor_anualizacion"] == 1.0
    assert r["tipo_aplicado"] == 24.0
    # cuota = 25.000 × 24% = 6.000
    assert r["resultado"] == 6000.0


@pytest.mark.asyncio
async def test_segunda_con_retenciones_y_pagos(calc):
    """Q2 anualizado ×2: rend 5.000 ×2 = 10.000 → 12%. Cuota 600.
    − 100 retenciones − 50 pagos = 450."""
    r = await calc.calculate(
        quarter=2,
        modalidad="segunda",
        ingresos_acumulados=8000,
        gastos_acumulados=3000,
        retenciones_acumuladas=100,
        pagos_anteriores=50,
    )
    assert r["resultado"] == 450.0


@pytest.mark.asyncio
async def test_segunda_rend_negativo_resultado_cero(calc):
    """Rend acumulado negativo → resultado 0."""
    r = await calc.calculate(
        quarter=1,
        modalidad="segunda",
        ingresos_acumulados=2000,
        gastos_acumulados=5000,
    )
    assert r["resultado"] == 0


# ===========================================================================
# Plazos
# ===========================================================================


@pytest.mark.asyncio
async def test_plazos_los_cuatro_trimestres(calc):
    plazos_esperados = {
        1: "1 al 20 de abril",
        2: "1 al 5 de agosto",
        3: "1 al 20 de octubre",
        4: "1 al 31 de enero del año siguiente",
    }
    for q, plazo in plazos_esperados.items():
        r = await calc.calculate(
            quarter=q,
            modalidad="segunda",
            ingresos_acumulados=1000,
            gastos_acumulados=0,
        )
        assert r["plazo"] == plazo


# ===========================================================================
# Validaciones / edge cases
# ===========================================================================


@pytest.mark.asyncio
async def test_quarter_invalido_raise(calc):
    with pytest.raises(ValueError, match="Quarter"):
        await calc.calculate(
            quarter=5,
            modalidad="primera",
            rend_neto_penultimo=10000,
        )


@pytest.mark.asyncio
async def test_modalidad_invalida_raise(calc):
    with pytest.raises(ValueError, match="modalidad"):
        await calc.calculate(
            quarter=1,
            modalidad="otra",
            rend_neto_penultimo=10000,
        )


@pytest.mark.asyncio
async def test_estructura_respuesta_primera(calc):
    r = await calc.calculate(
        quarter=1,
        modalidad="primera",
        rend_neto_penultimo=10000,
    )
    assert set(r["casillas"].keys()) == {
        "131_rend_neto_penultimo",
        "132_porcentaje_tabla",
        "133_cuota_anual",
        "134_retenciones_penultimo",
        "135_cuota_neta_anual",
        "140_pago_trimestral",
    }
    assert r["plazo"]


@pytest.mark.asyncio
async def test_estructura_respuesta_segunda(calc):
    r = await calc.calculate(
        quarter=2,
        modalidad="segunda",
        ingresos_acumulados=10000,
        gastos_acumulados=2000,
    )
    expected = {
        "01_ingresos_acumulados",
        "02_gastos_acumulados",
        "03_rendimiento_neto_acumulado",
        "04_factor_anualizacion",
        "05_rendimiento_neto_anualizado",
        "06_porcentaje_tabla",
        "07_retenciones_acumuladas",
        "08_pagos_anteriores",
        "10_cuota_sobre_rend_real",
        "15_resultado_pago_fraccionado",
    }
    assert set(r["casillas"].keys()) == expected


@pytest.mark.asyncio
async def test_tabla_progresiva_limites(calc):
    """Verifica los límites exactos de la tabla progresiva."""
    casos = [
        (6500, 6.0),  # límite ≤ 6.500
        (6501, 12.0),  # > 6.500 → 12%
        (12000, 12.0),  # límite ≤ 12.000
        (12001, 18.0),  # > 12.000 → 18%
        (24000, 18.0),  # límite ≤ 24.000
        (24001, 24.0),  # > 24.000 → 24%
    ]
    for rend, esperado in casos:
        r = await calc.calculate(
            quarter=1,
            modalidad="primera",
            rend_neto_penultimo=rend,
        )
        assert (
            r["tipo_aplicado"] == esperado
        ), f"rend={rend} esperaba {esperado}, got {r['tipo_aplicado']}"
