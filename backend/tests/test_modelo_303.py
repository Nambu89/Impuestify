"""Tests for Modelo 303 (IVA) calculator."""
import pytest
from app.utils.calculators.modelo_303 import Modelo303Calculator


@pytest.fixture
def calc():
    return Modelo303Calculator(None)


@pytest.mark.asyncio
async def test_basic_21pct(calc):
    """Freelancer factura 10.000 EUR al 21%."""
    r = await calc.calculate(base_21=10000)
    assert r["casilla_07"] == 10000
    assert r["casilla_09"] == 2100  # 10000 * 0.21
    assert r["total_devengado"] == 2100
    assert r["total_deducible"] == 0
    assert r["resultado_liquidacion"] == 2100


@pytest.mark.asyncio
async def test_basic_with_deducible(calc):
    """Factura 10.000 al 21%, soporta 3.000 de cuota corrientes."""
    r = await calc.calculate(base_21=10000, cuota_corrientes_interiores=3000)
    assert r["total_devengado"] == 2100
    assert r["total_deducible"] == 3000
    assert r["resultado_regimen_general"] == -900  # a compensar
    assert r["resultado_liquidacion"] == -900


@pytest.mark.asyncio
async def test_three_rates(calc):
    """Operaciones a los 3 tipos."""
    r = await calc.calculate(base_4=5000, base_10=3000, base_21=2000)
    cuota_4 = 5000 * 0.04  # 200
    cuota_10 = 3000 * 0.10  # 300
    cuota_21 = 2000 * 0.21  # 420
    assert r["casilla_03"] == cuota_4
    assert r["casilla_06"] == cuota_10
    assert r["casilla_09"] == cuota_21
    assert r["total_devengado"] == cuota_4 + cuota_10 + cuota_21


@pytest.mark.asyncio
async def test_intracomunitarias(calc):
    """Adquisicion intracomunitaria al 21%."""
    r = await calc.calculate(base_intracomunitarias=5000, tipo_intracomunitarias=21.0)
    assert r["casilla_10"] == 5000
    assert r["casilla_12"] == 1050  # 5000 * 0.21
    assert r["total_devengado"] == 1050


@pytest.mark.asyncio
async def test_inversion_sujeto_pasivo(calc):
    """ISP al tipo por defecto (21%)."""
    r = await calc.calculate(base_inversion_sp=8000)
    assert r["casilla_13"] == 8000
    assert r["casilla_14"] == 1680  # 8000 * 0.21
    assert r["total_devengado"] == 1680


@pytest.mark.asyncio
async def test_compensar_anteriores(calc):
    """Cuotas a compensar de periodos anteriores."""
    r = await calc.calculate(base_21=10000, cuotas_compensar_anteriores=500)
    assert r["casilla_78"] == 500
    assert r["resultado_liquidacion"] == 2100 - 500  # 1600


@pytest.mark.asyncio
async def test_compensar_negativa_clamped(calc):
    """Cuotas a compensar negativas se clampean a 0."""
    r = await calc.calculate(base_21=1000, cuotas_compensar_anteriores=-100)
    assert r["casilla_78"] == 0


@pytest.mark.asyncio
async def test_regularizacion_anual_4t(calc):
    """Regularizacion anual solo aplica en 4T."""
    r4 = await calc.calculate(base_21=1000, regularizacion_anual=200, quarter=4)
    assert r4["casilla_68"] == 200
    assert r4["resultado_liquidacion"] == 210 + 200  # devengado + regularizacion

    r1 = await calc.calculate(base_21=1000, regularizacion_anual=200, quarter=1)
    assert r1["casilla_68"] == 0
    assert r1["resultado_liquidacion"] == 210


@pytest.mark.asyncio
async def test_complementaria(calc):
    """Declaracion complementaria resta resultado anterior."""
    r = await calc.calculate(base_21=10000, resultado_anterior_complementaria=1500)
    assert r["casilla_70"] == 1500
    assert r["resultado_liquidacion"] == 2100 - 1500  # 600


@pytest.mark.asyncio
async def test_atribucion_parcial(calc):
    """Atribucion al Estado < 100% (opera en territorio foral tambien)."""
    r = await calc.calculate(base_21=10000, pct_atribucion_estado=60.0)
    assert r["casilla_65"] == 60.0
    assert r["casilla_66"] == 2100 * 0.60  # 1260
    assert r["resultado_liquidacion"] == 1260


@pytest.mark.asyncio
async def test_all_deducible_fields(calc):
    """All deducible fields sum correctly."""
    r = await calc.calculate(
        cuota_corrientes_interiores=100,
        cuota_inversion_interiores=200,
        cuota_importaciones_corrientes=50,
        cuota_importaciones_inversion=25,
        cuota_intracom_corrientes=75,
        cuota_intracom_inversion=30,
        rectificacion_deducciones=10,
        compensacion_agricultura=15,
        regularizacion_inversion=-5,
        regularizacion_prorrata=0,
    )
    expected = 100 + 200 + 50 + 25 + 75 + 30 + 10 + 15 + (-5) + 0
    assert r["total_deducible"] == expected
    assert r["casilla_45"] == expected


@pytest.mark.asyncio
async def test_modificacion_bases_cuotas(calc):
    """Modificacion de bases/cuotas afecta devengado."""
    r = await calc.calculate(base_21=1000, mod_cuotas=-50)
    assert r["casilla_16"] == -50
    assert r["total_devengado"] == 210 + (-50)  # 160


@pytest.mark.asyncio
async def test_zero_inputs(calc):
    """All zeros produces zero result."""
    r = await calc.calculate()
    assert r["resultado_liquidacion"] == 0
    assert r["total_devengado"] == 0
    assert r["total_deducible"] == 0


@pytest.mark.asyncio
async def test_desglose_structure(calc):
    """Desglose dicts have expected keys."""
    r = await calc.calculate(base_21=1000)
    assert "superreducido_4pct" in r["desglose_devengado"]
    assert "reducido_10pct" in r["desglose_devengado"]
    assert "general_21pct" in r["desglose_devengado"]
    assert "corrientes_interiores" in r["desglose_deducible"]


@pytest.mark.asyncio
async def test_metadata(calc):
    """Territory, quarter, year are returned."""
    r = await calc.calculate(territory="navarra", quarter=3, year=2026)
    assert r["territory"] == "navarra"
    assert r["quarter"] == 3
    assert r["year"] == 2026
