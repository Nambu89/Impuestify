"""Tests for Modelo 130 Araba/Álava (Pago Fraccionado IRPF foral)."""
import pytest

from app.utils.calculators.modelo_130_araba import Modelo130ArabaCalculator


@pytest.fixture
def calc():
    return Modelo130ArabaCalculator(repo=None)


# ===========================================================================
# Cálculo básico (5 % sobre rendimiento neto trimestral)
# ===========================================================================

@pytest.mark.asyncio
async def test_basico(calc):
    """Araba: 8.000 − 3.000 = 5.000 × 5% = 250."""
    r = await calc.calculate(
        quarter=2,
        ingresos_trimestre=8000,
        gastos_trimestre=3000,
    )
    assert r["territory"] == "Araba"
    assert r["tipo_aplicado"] == 5.0
    assert r["casillas"]["03_rendimiento_neto_trimestral"] == 5000.0
    assert r["casillas"]["04_cuota_5pct"] == 250.0
    assert r["resultado"] == 250.0


@pytest.mark.asyncio
async def test_con_retenciones(calc):
    """Con retenciones 200: 250 − 200 = 50."""
    r = await calc.calculate(
        quarter=3,
        ingresos_trimestre=10000,
        gastos_trimestre=5000,
        retenciones_trimestre=200,
    )
    # rn = 5.000, cuota = 250, − 200 = 50
    assert r["resultado"] == 50.0


@pytest.mark.asyncio
async def test_con_pagos_anteriores(calc):
    """Con pagos anteriores 100: 250 − 100 = 150."""
    r = await calc.calculate(
        quarter=2,
        ingresos_trimestre=10000,
        gastos_trimestre=5000,
        pagos_anteriores=100,
    )
    assert r["resultado"] == 150.0


@pytest.mark.asyncio
async def test_retenciones_y_pagos(calc):
    """250 − 100 − 50 = 100."""
    r = await calc.calculate(
        quarter=4,
        ingresos_trimestre=10000,
        gastos_trimestre=5000,
        retenciones_trimestre=100,
        pagos_anteriores=50,
    )
    assert r["resultado"] == 100.0


@pytest.mark.asyncio
async def test_rendimiento_negativo_resultado_cero(calc):
    """Rend. negativo → resultado 0 (no negativo)."""
    r = await calc.calculate(
        quarter=1,
        ingresos_trimestre=2000,
        gastos_trimestre=5000,
    )
    assert r["casillas"]["03_rendimiento_neto_trimestral"] == -3000.0
    assert r["resultado"] == 0


@pytest.mark.asyncio
async def test_minoraciones_superan_cuota(calc):
    """Si retenciones + pagos > cuota → 0."""
    r = await calc.calculate(
        quarter=2,
        ingresos_trimestre=4000,
        gastos_trimestre=2000,    # rn 2.000, cuota 100
        retenciones_trimestre=200,
        pagos_anteriores=100,
    )
    assert r["resultado"] == 0


# ===========================================================================
# Plazos
# ===========================================================================

@pytest.mark.asyncio
async def test_plazos_los_cuatro_trimestres(calc):
    plazos_esperados = {
        1: "1 al 25 de abril",
        2: "1 al 25 de julio",
        3: "1 al 25 de octubre",
        4: "1 al 30 de enero del año siguiente",
    }
    for q, plazo in plazos_esperados.items():
        r = await calc.calculate(
            quarter=q,
            ingresos_trimestre=1000,
            gastos_trimestre=0,
        )
        assert r["plazo"] == plazo


# ===========================================================================
# Inputs negativos se clipan a 0
# ===========================================================================

@pytest.mark.asyncio
async def test_ingresos_negativos_se_clipan(calc):
    r = await calc.calculate(
        quarter=1,
        ingresos_trimestre=-100,
        gastos_trimestre=0,
    )
    assert r["casillas"]["01_ingresos_trimestre"] == 0.0


@pytest.mark.asyncio
async def test_gastos_negativos_se_clipan(calc):
    r = await calc.calculate(
        quarter=1,
        ingresos_trimestre=1000,
        gastos_trimestre=-50,
    )
    assert r["casillas"]["02_gastos_trimestre"] == 0.0


@pytest.mark.asyncio
async def test_retenciones_negativas_se_clipan(calc):
    r = await calc.calculate(
        quarter=1,
        ingresos_trimestre=10000,
        gastos_trimestre=5000,
        retenciones_trimestre=-200,
    )
    assert r["casillas"]["05_retenciones_trimestre"] == 0.0
    assert r["resultado"] == 250.0


# ===========================================================================
# Validaciones
# ===========================================================================

@pytest.mark.asyncio
async def test_quarter_invalido_raise(calc):
    with pytest.raises(ValueError, match="Quarter"):
        await calc.calculate(quarter=5, ingresos_trimestre=1000)


@pytest.mark.asyncio
async def test_quarter_cero_raise(calc):
    with pytest.raises(ValueError, match="Quarter"):
        await calc.calculate(quarter=0, ingresos_trimestre=1000)


# ===========================================================================
# Estructura
# ===========================================================================

@pytest.mark.asyncio
async def test_estructura_respuesta_completa(calc):
    r = await calc.calculate(
        quarter=2,
        ingresos_trimestre=10000,
        gastos_trimestre=2000,
    )
    assert set(r["casillas"].keys()) == {
        "01_ingresos_trimestre",
        "02_gastos_trimestre",
        "03_rendimiento_neto_trimestral",
        "04_cuota_5pct",
        "05_retenciones_trimestre",
        "06_pagos_anteriores",
        "07_resultado_pago_fraccionado",
    }
    assert r["desglose"]["base_calculo"] == "trimestral"
    assert r["plazo"]


@pytest.mark.asyncio
async def test_redondeo_dos_decimales(calc):
    """Importes redondeados a 2 decimales."""
    r = await calc.calculate(
        quarter=1,
        ingresos_trimestre=12345.678,
        gastos_trimestre=2345.123,
    )
    assert r["casillas"]["01_ingresos_trimestre"] == 12345.68
    assert r["casillas"]["02_gastos_trimestre"] == 2345.12
    # rn = 10000.56, cuota = 500.028 → 500.03
    assert r["casillas"]["04_cuota_5pct"] == 500.03


@pytest.mark.asyncio
async def test_resultado_grande(calc):
    """Caso con cifras grandes."""
    r = await calc.calculate(
        quarter=4,
        ingresos_trimestre=120000,
        gastos_trimestre=20000,
    )
    # rn = 100.000, cuota 5% = 5.000
    assert r["resultado"] == 5000.0
