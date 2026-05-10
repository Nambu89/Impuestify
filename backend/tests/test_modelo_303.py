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


# =====================================================================
# REGRESSION TESTS — Audit 2026-05 (BUG-303-01..03 P0 fixes)
# =====================================================================
# Estos tests cubren los 3 bugs P0 detectados en
# docs/audits/modelo_303_validation_2026-05.md y validan que el TOOL
# (no solo el calculator) respeta la numeracion oficial de casillas
# AEAT y los plazos correctos.


@pytest.mark.asyncio
async def test_303_casilla_78_compensacion_no_71():
    """BUG-303-01: cuotas a compensar de periodos anteriores van a la
    casilla 78, no a la 71. La 71 es el resultado liquidacion."""
    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=2,
        year=2025,
        base_21=10000,
        iva_deducible_bienes_corrientes=500,
        compensacion_periodos_anteriores=300,
    )
    assert result["success"]
    casillas = result["casillas"]
    assert casillas["casilla_78_compensacion_anterior"] == 300.0
    # casilla 71 NO debe ser la compensacion (300); debe ser el resultado liquidacion
    assert casillas["casilla_71_resultado_liquidacion"] != 300.0
    # La compensacion debe quedar referenciada como casilla 78 en el dict resultado
    assert result["resultado"]["compensacion_anterior"] == 300.0


@pytest.mark.asyncio
async def test_303_casilla_71_resultado_liquidacion():
    """BUG-303-01: casilla 71 = resultado liquidacion final
    (= 69 - 70). En este caso simple (sin atribucion parcial, sin
    aduana, sin complementaria, sin regularizacion):
    71 = devengado - deducible - compensacion."""
    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=2,
        year=2025,
        base_21=10000,                            # devengado = 2100
        iva_deducible_bienes_corrientes=500,      # deducible = 500
        compensacion_periodos_anteriores=300,     # casilla 78
    )
    # Resultado regimen general = 2100 - 500 = 1600
    # Casilla 69 = 66 + 77 - 78 + 68 = 1600 + 0 - 300 + 0 = 1300
    # Casilla 71 = 69 - 70 = 1300 - 0 = 1300
    casillas = result["casillas"]
    assert casillas["casilla_46_regimen_general"] == 1600.0
    assert casillas["casilla_69_resultado_previo"] == 1300.0
    assert casillas["casilla_71_resultado_liquidacion"] == 1300.0
    assert result["resultado"]["resultado_final"] == 1300.0


@pytest.mark.asyncio
async def test_303_plazo_t4_30_enero_y_domiciliacion_dia_25():
    """BUG-303-02: plazo T4 SIEMPRE 30 enero (no 20 ni alternativo).
    Domiciliacion 5 dias antes (dia 25). Debe mencionar festivos."""
    from app.tools.modelo_303_tool import calculate_modelo_303_tool, _format_plazo

    # Helper directo
    plazo_t4 = _format_plazo(4, 2025)
    assert "30 de enero" in plazo_t4
    assert "25 de enero" in plazo_t4  # domiciliacion
    assert "20 de enero" not in plazo_t4
    assert "festivo" in plazo_t4.lower()

    # T1, T2, T3 mantienen 20 + domiciliacion 15
    plazo_t1 = _format_plazo(1, 2025)
    assert "20 de abril" in plazo_t1
    assert "15 de abril" in plazo_t1

    plazo_t2 = _format_plazo(2, 2025)
    assert "20 de julio" in plazo_t2
    assert "15 de julio" in plazo_t2

    plazo_t3 = _format_plazo(3, 2025)
    assert "20 de octubre" in plazo_t3
    assert "15 de octubre" in plazo_t3

    # Verificacion end-to-end: plazo aparece en formatted_response del tool
    result = await calculate_modelo_303_tool(
        trimestre=4,
        year=2025,
        base_21=10000,
        iva_deducible_bienes_corrientes=500,
    )
    assert result["success"]
    assert "30 de enero" in result["formatted_response"]
    assert "25 de enero" in result["formatted_response"]
    assert result["plazo_presentacion"] == plazo_t4


@pytest.mark.asyncio
async def test_303_casilla_45_total_deducible_suma_10_casillas():
    """BUG-303-03: casilla 45 = 29 + 31 + 33 + 35 + 37 + 39 + 41 + 42 + 43 + 44.
    El tool debe delegar al calculator para obtener la suma completa de las
    10 casillas (no las 5 que sumaba el tool reimplementado)."""
    calc = Modelo303Calculator(None)
    r = await calc.calculate(
        cuota_corrientes_interiores=100,        # casilla 29
        cuota_inversion_interiores=200,          # casilla 31
        cuota_importaciones_corrientes=50,       # casilla 33
        cuota_importaciones_inversion=25,        # casilla 35
        cuota_intracom_corrientes=75,            # casilla 37
        cuota_intracom_inversion=30,             # casilla 39
        rectificacion_deducciones=10,            # casilla 41
        compensacion_agricultura=15,             # casilla 42
        regularizacion_inversion=-5,             # casilla 43
        regularizacion_prorrata=20,              # casilla 44
    )
    expected_45 = 100 + 200 + 50 + 25 + 75 + 30 + 10 + 15 + (-5) + 20  # 520
    assert r["casilla_45"] == expected_45
    # Confirmar que las 10 casillas estan incluidas (no las 5 viejas del tool)
    assert r["casilla_35"] == 25
    assert r["casilla_39"] == 30
    assert r["casilla_42"] == 15
    assert r["casilla_43"] == -5
    assert r["casilla_44"] == 20
