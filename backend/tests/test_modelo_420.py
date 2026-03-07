"""Tests for Modelo 420 (IGIC Canarias) calculator."""
import pytest
from app.utils.calculators.modelo_420 import (
    Modelo420Calculator,
    TIPO_CERO, TIPO_REDUCIDO, TIPO_GENERAL,
    TIPO_INCREMENTADO_1, TIPO_INCREMENTADO_2,
    TIPO_ESPECIAL_1, TIPO_ESPECIAL_2,
)


@pytest.fixture
def calc():
    return Modelo420Calculator(None)


@pytest.mark.asyncio
async def test_basic_general_7pct(calc):
    """Autonomo canario factura 10.000 al tipo general (7%)."""
    r = await calc.calculate(base_7=10000)
    assert r["total_devengado"] == 700  # 10.000 * 0.07
    assert r["total_deducible"] == 0
    assert r["resultado_liquidacion"] == 700


@pytest.mark.asyncio
async def test_tipo_cero(calc):
    """Tipo cero (0%) genera cuota 0."""
    r = await calc.calculate(base_0=50000)
    assert r["desglose_devengado"]["tipo_cero"]["cuota"] == 0
    assert r["total_devengado"] == 0


@pytest.mark.asyncio
async def test_all_rates(calc):
    """All 7 rate tiers."""
    r = await calc.calculate(
        base_0=1000, base_3=1000, base_7=1000,
        base_9_5=1000, base_13_5=1000, base_20=1000, base_35=1000,
    )
    expected = (
        1000 * TIPO_CERO
        + 1000 * TIPO_REDUCIDO
        + 1000 * TIPO_GENERAL
        + 1000 * TIPO_INCREMENTADO_1
        + 1000 * TIPO_INCREMENTADO_2
        + 1000 * TIPO_ESPECIAL_1
        + 1000 * TIPO_ESPECIAL_2
    )
    assert r["total_devengado"] == round(expected, 2)


@pytest.mark.asyncio
async def test_devengado_minus_deducible(calc):
    """Resultado = devengado - deducible."""
    r = await calc.calculate(base_7=10000, cuota_corrientes_interiores=400)
    assert r["total_devengado"] == 700
    assert r["total_deducible"] == 400
    assert r["resultado_regimen_general"] == 300
    assert r["resultado_liquidacion"] == 300


@pytest.mark.asyncio
async def test_compensar_anteriores(calc):
    """Cuotas a compensar de periodos anteriores."""
    r = await calc.calculate(base_7=10000, cuotas_compensar_anteriores=200)
    assert r["resultado_liquidacion"] == 700 - 200  # 500


@pytest.mark.asyncio
async def test_compensar_negativa_clamped(calc):
    """Cuotas a compensar negativas se clampean a 0."""
    r = await calc.calculate(base_7=1000, cuotas_compensar_anteriores=-50)
    assert r["cuotas_compensar_anteriores"] == 0
    assert r["resultado_liquidacion"] == 70  # 1000 * 0.07


@pytest.mark.asyncio
async def test_regularizacion_anual_4t(calc):
    """Regularizacion anual solo en 4T."""
    r4 = await calc.calculate(base_7=1000, regularizacion_anual=100, quarter=4)
    assert r4["regularizacion_anual"] == 100
    assert r4["resultado_liquidacion"] == 70 + 100  # 170

    r2 = await calc.calculate(base_7=1000, regularizacion_anual=100, quarter=2)
    assert r2["regularizacion_anual"] == 0
    assert r2["resultado_liquidacion"] == 70


@pytest.mark.asyncio
async def test_complementaria(calc):
    """Complementaria: diferencia con resultado anterior."""
    r = await calc.calculate(base_7=10000, resultado_anterior_complementaria=500)
    assert r["cuota_diferencial_complementaria"] == 700 - 500  # 200


@pytest.mark.asyncio
async def test_extracanarias(calc):
    """Adquisiciones extracanarias al tipo general."""
    r = await calc.calculate(base_extracanarias=5000, tipo_extracanarias=0.07)
    assert r["desglose_devengado"]["adquisiciones_extracanarias"]["cuota"] == 350
    assert r["total_devengado"] == 350


@pytest.mark.asyncio
async def test_inversion_sp(calc):
    """Inversion sujeto pasivo usa tipo general (7%)."""
    r = await calc.calculate(base_inversion_sp=3000)
    assert r["desglose_devengado"]["inversion_sujeto_pasivo"]["cuota"] == 210
    assert r["total_devengado"] == 210


@pytest.mark.asyncio
async def test_all_deducible_fields(calc):
    """All deducible fields sum correctly."""
    r = await calc.calculate(
        cuota_corrientes_interiores=100,
        cuota_inversion_interiores=200,
        cuota_importaciones_corrientes=50,
        cuota_importaciones_inversion=25,
        cuota_extracanarias_corrientes=75,
        cuota_extracanarias_inversion=30,
        rectificacion_deducciones=10,
        compensacion_agricultura=15,
        regularizacion_inversion=-5,
        regularizacion_prorrata=0,
    )
    expected = 100 + 200 + 50 + 25 + 75 + 30 + 10 + 15 + (-5) + 0
    assert r["total_deducible"] == expected


@pytest.mark.asyncio
async def test_zero_inputs(calc):
    """All zeros → zero result."""
    r = await calc.calculate()
    assert r["resultado_liquidacion"] == 0
    assert r["total_devengado"] == 0
    assert r["total_deducible"] == 0


@pytest.mark.asyncio
async def test_igic_rates_exposed(calc):
    """IGIC rates are returned in the result."""
    r = await calc.calculate(base_7=100)
    rates = r["igic_rates"]
    assert rates["tipo_cero"] == 0.0
    assert rates["tipo_reducido"] == 0.03
    assert rates["tipo_general"] == 0.07
    assert rates["tipo_incrementado_1"] == 0.095
    assert rates["tipo_incrementado_2"] == 0.135
    assert rates["tipo_especial_1"] == 0.20
    assert rates["tipo_especial_2"] == 0.35


@pytest.mark.asyncio
async def test_negative_result(calc):
    """More deducible than devengado → negative resultado."""
    r = await calc.calculate(base_7=1000, cuota_corrientes_interiores=500)
    assert r["resultado_regimen_general"] == 70 - 500  # -430
    assert r["resultado_liquidacion"] == -430
