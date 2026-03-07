"""Tests for Modelo 130 (Pago Fraccionado IRPF) calculator — all territories."""
import pytest
from app.utils.calculators.modelo_130 import Modelo130Calculator


@pytest.fixture
def calc():
    return Modelo130Calculator(None)


# ===========================================================================
# Territorio Comun
# ===========================================================================

@pytest.mark.asyncio
async def test_comun_basic(calc):
    """Autonomo con 30.000 ingresos, 10.000 gastos acumulados al 2T."""
    r = await calc.calculate(
        territory="Comun", quarter=2,
        ingresos_acumulados=30000, gastos_acumulados=10000,
        rend_neto_anterior=20000,  # > 12.000 → art 80bis = 0
    )
    rn = 30000 - 10000  # 20.000
    cuota = rn * 0.20  # 4.000
    assert r["resultado"] == cuota  # sin retenciones ni pagos previos
    assert r["tipo_aplicado"] == 20.0
    assert r["territory"] == "Comun"


@pytest.mark.asyncio
async def test_comun_with_retenciones_and_pagos(calc):
    """Retenciones y pagos anteriores se restan."""
    r = await calc.calculate(
        territory="Comun", quarter=3,
        ingresos_acumulados=45000, gastos_acumulados=15000,
        retenciones_acumuladas=2000, pagos_anteriores=3000,
        rend_neto_anterior=30000,  # > 12.000 → art 80bis = 0
    )
    rn = 45000 - 15000  # 30.000
    cuota = rn * 0.20  # 6.000
    sec1 = max(0, cuota - 2000 - 3000)  # 1.000
    assert r["resultado"] == sec1


@pytest.mark.asyncio
async def test_comun_negative_rend_neto(calc):
    """Rendimiento neto negativo → resultado 0."""
    r = await calc.calculate(
        territory="Comun", quarter=1,
        ingresos_acumulados=5000, gastos_acumulados=8000,
    )
    assert r["resultado"] == 0


@pytest.mark.asyncio
async def test_comun_art_80bis_9000(calc):
    """Art. 80 bis: rend_neto_anterior <= 9.000 → deduccion 100 EUR."""
    r = await calc.calculate(
        territory="Comun", quarter=1,
        ingresos_acumulados=20000, gastos_acumulados=10000,
        rend_neto_anterior=8000,
    )
    # sec I = (10.000 * 20%) = 2.000
    # casilla 13 = 100 (art 80 bis)
    # casilla 14 = 2000 - 100 = 1900
    assert r["casillas"]["13_deduccion_art80bis"] == 100
    assert r["resultado"] == 1900


@pytest.mark.asyncio
async def test_comun_art_80bis_10500(calc):
    """Art. 80 bis: rend_neto_anterior = 10.500 → deduccion 50 EUR."""
    r = await calc.calculate(
        territory="Comun", quarter=1,
        ingresos_acumulados=20000, gastos_acumulados=10000,
        rend_neto_anterior=10500,
    )
    assert r["casillas"]["13_deduccion_art80bis"] == 50


@pytest.mark.asyncio
async def test_comun_art_80bis_above_12000(calc):
    """Art. 80 bis: rend_neto_anterior > 12.000 → deduccion 0."""
    r = await calc.calculate(
        territory="Comun", quarter=1,
        ingresos_acumulados=20000, gastos_acumulados=10000,
        rend_neto_anterior=15000,
    )
    assert r["casillas"]["13_deduccion_art80bis"] == 0


@pytest.mark.asyncio
async def test_comun_vivienda_habitual(calc):
    """Deduccion vivienda habitual: 2% rendimiento neto, max 660.14."""
    r = await calc.calculate(
        territory="Comun", quarter=1,
        ingresos_acumulados=50000, gastos_acumulados=10000,
        tiene_vivienda_habitual=True,
    )
    # rn = 40.000, 2% = 800, pero max 660.14
    assert r["casillas"]["16_deduccion_vivienda"] == 660.14


@pytest.mark.asyncio
async def test_comun_vivienda_habitual_small(calc):
    """Deduccion vivienda < max."""
    r = await calc.calculate(
        territory="Comun", quarter=1,
        ingresos_acumulados=15000, gastos_acumulados=5000,
        tiene_vivienda_habitual=True,
    )
    # rn = 10.000, 2% = 200 < 660.14
    assert r["casillas"]["16_deduccion_vivienda"] == 200


# ===========================================================================
# Ceuta / Melilla
# ===========================================================================

@pytest.mark.asyncio
async def test_ceuta_melilla_8pct(calc):
    """Ceuta/Melilla usa 8% en vez de 20%."""
    r = await calc.calculate(
        territory="Comun", quarter=1, ceuta_melilla=True,
        ingresos_acumulados=20000, gastos_acumulados=10000,
        rend_neto_anterior=15000,  # > 12.000 → art 80bis = 0
    )
    rn = 10000
    cuota = rn * 0.08  # 800
    assert r["tipo_aplicado"] == 8.0
    assert r["resultado"] == cuota
    assert r["territory"] == "Ceuta/Melilla"


# ===========================================================================
# Araba
# ===========================================================================

@pytest.mark.asyncio
async def test_araba_basic(calc):
    """Araba: 5% trimestral."""
    r = await calc.calculate(
        territory="Araba", quarter=2,
        ingresos_trimestre=8000, gastos_trimestre=3000,
    )
    rn = 5000
    cuota = rn * 0.05  # 250
    assert r["resultado"] == cuota
    assert r["tipo_aplicado"] == 5.0


@pytest.mark.asyncio
async def test_araba_with_retenciones(calc):
    """Araba con retenciones y pagos anteriores."""
    r = await calc.calculate(
        territory="Araba", quarter=3,
        ingresos_trimestre=10000, gastos_trimestre=4000,
        retenciones_trimestre=200, pagos_anteriores=50,
    )
    rn = 6000
    cuota = rn * 0.05  # 300
    assert r["resultado"] == max(0, cuota - 200 - 50)  # 50


@pytest.mark.asyncio
async def test_araba_negative(calc):
    """Araba rendimiento negativo → 0."""
    r = await calc.calculate(
        territory="Araba", quarter=1,
        ingresos_trimestre=2000, gastos_trimestre=5000,
    )
    assert r["resultado"] == 0


# ===========================================================================
# Gipuzkoa
# ===========================================================================

@pytest.mark.asyncio
async def test_gipuzkoa_general(calc):
    """Gipuzkoa general: 5% rend_neto_penultimo - 25% retenciones_penultimo."""
    r = await calc.calculate(
        territory="Gipuzkoa", quarter=1, regimen="general",
        rend_neto_penultimo=40000, retenciones_penultimo=4000,
    )
    cuota = 40000 * 0.05  # 2.000
    minorar = 4000 * 0.25  # 1.000
    assert r["resultado"] == cuota - minorar  # 1.000
    assert r["tipo_aplicado"] == 5.0


@pytest.mark.asyncio
async def test_gipuzkoa_excepcional(calc):
    """Gipuzkoa excepcional: 1% volumen operaciones - retenciones."""
    r = await calc.calculate(
        territory="Gipuzkoa", quarter=2, regimen="excepcional",
        volumen_operaciones_trimestre=15000, retenciones_trimestre_gipuzkoa=50,
    )
    cuota = 15000 * 0.01  # 150
    assert r["resultado"] == cuota - 50  # 100
    assert r["tipo_aplicado"] == 1.0


# ===========================================================================
# Bizkaia
# ===========================================================================

@pytest.mark.asyncio
async def test_bizkaia_first_2_years(calc):
    """Bizkaia primeros 2 anos: 20% acumulado (como Comun)."""
    r = await calc.calculate(
        territory="Bizkaia", quarter=1, anos_actividad=1,
        ingresos_acumulados=20000, gastos_acumulados=8000,
    )
    rn = 12000
    cuota = rn * 0.20  # 2.400
    assert r["resultado"] == cuota
    assert r["regimen"] == "primeros_anos"


@pytest.mark.asyncio
async def test_bizkaia_general_3rd_year(calc):
    """Bizkaia desde 3er ano, regimen general."""
    r = await calc.calculate(
        territory="Bizkaia", quarter=2, anos_actividad=5,
        regimen="general",
        rend_neto_penultimo=50000, retenciones_penultimo=6000,
    )
    cuota = 50000 * 0.05  # 2.500
    minorar = 6000 * 0.25  # 1.500
    assert r["resultado"] == cuota - minorar  # 1.000


@pytest.mark.asyncio
async def test_bizkaia_excepcional_3rd_year(calc):
    """Bizkaia excepcional: base = volumen_ventas_penultimo."""
    r = await calc.calculate(
        territory="Bizkaia", quarter=1, anos_actividad=4,
        regimen="excepcional",
        volumen_ventas_penultimo=80000, retenciones_penultimo=2000,
    )
    cuota = 80000 * 0.05  # 4.000
    minorar = 2000 * 0.25  # 500
    assert r["resultado"] == cuota - minorar  # 3.500


# ===========================================================================
# Navarra
# ===========================================================================

@pytest.mark.asyncio
async def test_navarra_primera_6pct(calc):
    """Navarra primera modalidad: rend_neto_penultimo = 5.000 → 6%."""
    r = await calc.calculate(
        territory="Navarra", quarter=1, modalidad="primera",
        rend_neto_penultimo=5000, retenciones_penultimo=0,
    )
    cuota_anual = 5000 * 0.06  # 300
    pago = cuota_anual / 4  # 75
    assert r["resultado"] == pago
    assert r["tipo_aplicado"] == 6.0
    assert r["modalidad"] == "primera"


@pytest.mark.asyncio
async def test_navarra_primera_24pct(calc):
    """Navarra primera: rend_neto_penultimo = 30.000 → 24%."""
    r = await calc.calculate(
        territory="Navarra", quarter=1, modalidad="primera",
        rend_neto_penultimo=30000, retenciones_penultimo=1000,
    )
    cuota_anual = 30000 * 0.24  # 7.200
    cuota_neta = 7200 - 1000  # 6.200
    pago = cuota_neta / 4  # 1.550
    assert r["resultado"] == pago


@pytest.mark.asyncio
async def test_navarra_primera_12pct(calc):
    """Navarra primera: rend_neto_penultimo = 10.000 → 12%."""
    r = await calc.calculate(
        territory="Navarra", quarter=1, modalidad="primera",
        rend_neto_penultimo=10000, retenciones_penultimo=0,
    )
    assert r["tipo_aplicado"] == 12.0
    assert r["resultado"] == (10000 * 0.12) / 4  # 300


@pytest.mark.asyncio
async def test_navarra_segunda_q1(calc):
    """Navarra segunda modalidad T1: anualizacion x4."""
    r = await calc.calculate(
        territory="Navarra", quarter=1, modalidad="segunda",
        ingresos_acumulados=8000, gastos_acumulados=3000,
    )
    rn = 5000
    anualizado = 5000 * 4  # 20.000 → 18%
    cuota = rn * 0.18  # 900
    assert r["tipo_aplicado"] == 18.0
    assert r["resultado"] == cuota  # 900 (no retenciones, no pagos)


@pytest.mark.asyncio
async def test_navarra_segunda_q2(calc):
    """Navarra segunda T2: anualizacion x2."""
    r = await calc.calculate(
        territory="Navarra", quarter=2, modalidad="segunda",
        ingresos_acumulados=16000, gastos_acumulados=6000,
        retenciones_acumuladas_navarra=500, pagos_anteriores_navarra=200,
    )
    rn = 10000
    anualizado = 10000 * 2  # 20.000 → 18%
    cuota = rn * 0.18  # 1.800
    resultado = max(0, cuota - 500 - 200)  # 1.100
    assert r["tipo_aplicado"] == 18.0
    assert r["resultado"] == resultado


# ===========================================================================
# Edge cases
# ===========================================================================

@pytest.mark.asyncio
async def test_invalid_territory(calc):
    """Invalid territory raises ValueError."""
    with pytest.raises(ValueError, match="not supported"):
        await calc.calculate(territory="Canarias_invalid", quarter=1)


@pytest.mark.asyncio
async def test_comun_complementaria(calc):
    """Complementaria resta resultado anterior."""
    r = await calc.calculate(
        territory="Comun", quarter=1,
        ingresos_acumulados=20000, gastos_acumulados=10000,
        rend_neto_anterior=20000,  # > 12.000 → art 80bis = 0
        resultado_anterior_complementaria=1500,
    )
    # sec I = 2.000, minus complementaria 1.500 = 500
    assert r["resultado"] == max(0, 2000 - 1500)
