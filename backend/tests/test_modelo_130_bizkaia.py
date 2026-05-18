"""Tests for Modelo 130 Bizkaia (Pago Fraccionado IRPF foral)."""

import pytest

from app.utils.calculators.modelo_130_bizkaia import Modelo130BizkaiaCalculator


@pytest.fixture
def calc():
    return Modelo130BizkaiaCalculator(repo=None)


# ===========================================================================
# Régimen general (≥ 3.er año, rend. neto penúltimo > 0)
# ===========================================================================


@pytest.mark.asyncio
async def test_general_basico(calc):
    """Régimen general: 30.000 × 5% = 1.500. Sin minoración → 1.500."""
    r = await calc.calculate(
        quarter=1,
        anos_actividad=5,
        regimen="general",
        rend_neto_penultimo=30000,
    )
    assert r["territory"] == "Bizkaia"
    assert r["regimen"] == "general"
    assert r["tipo_aplicado"] == 5.0
    assert r["casillas"]["03_cuota_base"] == 1500.0
    assert r["resultado"] == 1500.0
    assert r["plazo"] == "1 al 25 de abril"


@pytest.mark.asyncio
async def test_general_con_retenciones(calc):
    """Régimen general: 30.000 × 5% − 4.000 × 25% = 1.500 − 1.000 = 500."""
    r = await calc.calculate(
        quarter=2,
        anos_actividad=5,
        regimen="general",
        rend_neto_penultimo=30000,
        retenciones_penultimo=4000,
    )
    assert r["casillas"]["05_minoracion_25pct_retenciones"] == 1000.0
    assert r["resultado"] == 500.0


@pytest.mark.asyncio
async def test_general_minoracion_supera_cuota_se_clipa_a_cero(calc):
    """Si la minoración del 25% supera la cuota → resultado 0 (no negativo)."""
    r = await calc.calculate(
        quarter=3,
        anos_actividad=10,
        regimen="general",
        rend_neto_penultimo=10000,  # cuota = 500
        retenciones_penultimo=10000,  # 25% = 2.500 > 500
    )
    assert r["resultado"] == 0


@pytest.mark.asyncio
async def test_general_rend_negativo_clipa_base_a_cero(calc):
    """rend_neto_penultimo negativo → base 0 → resultado 0."""
    r = await calc.calculate(
        quarter=1,
        anos_actividad=5,
        regimen="general",
        rend_neto_penultimo=-1000,
    )
    assert r["casillas"]["01_base_calculo"] == 0.0
    assert r["resultado"] == 0


# ===========================================================================
# Régimen excepcional (rend. neto penúltimo ≤ 0 → usa volumen ventas)
# ===========================================================================


@pytest.mark.asyncio
async def test_excepcional_basico(calc):
    """Excepcional: 100.000 ventas × 5% = 5.000. Sin retenciones → 5.000."""
    r = await calc.calculate(
        quarter=2,
        anos_actividad=4,
        regimen="excepcional",
        volumen_ventas_penultimo=100000,
    )
    assert r["regimen"] == "excepcional"
    assert r["resultado"] == 5000.0
    assert r["desglose"]["base_label"] == "volumen_ventas_penultimo"


@pytest.mark.asyncio
async def test_excepcional_con_retenciones(calc):
    """Excepcional: 100.000 × 5% − 8.000 × 25% = 5.000 − 2.000 = 3.000."""
    r = await calc.calculate(
        quarter=3,
        anos_actividad=4,
        regimen="excepcional",
        volumen_ventas_penultimo=100000,
        retenciones_penultimo=8000,
    )
    assert r["resultado"] == 3000.0


# ===========================================================================
# Primeros 2 años de actividad (anos_actividad < 3 → reglas Estatal)
# ===========================================================================


@pytest.mark.asyncio
async def test_primeros_anos_basico(calc):
    """1er año: 20.000 − 5.000 = 15.000 × 20% = 3.000."""
    r = await calc.calculate(
        quarter=2,
        anos_actividad=1,
        ingresos_acumulados=20000,
        gastos_acumulados=5000,
    )
    assert r["regimen"] == "primeros_anos"
    assert r["tipo_aplicado"] == 20.0
    assert r["casillas"]["04_cuota_20pct"] == 3000.0
    assert r["resultado"] == 3000.0


@pytest.mark.asyncio
async def test_primeros_anos_con_retenciones_y_pagos(calc):
    """2.º año: 30.000 × 20% − 1.000 retenciones − 500 pagos = 4.500."""
    r = await calc.calculate(
        quarter=3,
        anos_actividad=2,
        ingresos_acumulados=45000,
        gastos_acumulados=15000,
        retenciones_acumuladas=1000,
        pagos_anteriores=500,
    )
    # rn = 30.000, cuota = 6.000 → 6.000 − 1.000 − 500 = 4.500
    assert r["resultado"] == 4500.0


@pytest.mark.asyncio
async def test_primeros_anos_rend_negativo_resultado_cero(calc):
    """Rend. neto acumulado negativo → resultado 0 (no negativo)."""
    r = await calc.calculate(
        quarter=1,
        anos_actividad=1,
        ingresos_acumulados=5000,
        gastos_acumulados=8000,
    )
    assert r["resultado"] == 0


@pytest.mark.asyncio
async def test_primeros_anos_year_3_pasa_a_general(calc):
    """anos_actividad = 3 → ya régimen general (ya no primeros años)."""
    r = await calc.calculate(
        quarter=1,
        anos_actividad=3,
        regimen="general",
        rend_neto_penultimo=20000,
    )
    assert r["regimen"] == "general"
    assert r["tipo_aplicado"] == 5.0


# ===========================================================================
# Plazos (verificar los 4 trimestres)
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
            anos_actividad=5,
            regimen="general",
            rend_neto_penultimo=10000,
        )
        assert r["plazo"] == plazo


# ===========================================================================
# Edge cases / validaciones
# ===========================================================================


@pytest.mark.asyncio
async def test_quarter_invalido_raise(calc):
    with pytest.raises(ValueError, match="Quarter"):
        await calc.calculate(
            quarter=5,
            anos_actividad=5,
            regimen="general",
            rend_neto_penultimo=10000,
        )


@pytest.mark.asyncio
async def test_anos_actividad_negativo_raise(calc):
    with pytest.raises(ValueError, match="anos_actividad"):
        await calc.calculate(
            quarter=1,
            anos_actividad=-1,
            regimen="general",
            rend_neto_penultimo=10000,
        )


@pytest.mark.asyncio
async def test_regimen_invalido_raise(calc):
    with pytest.raises(ValueError, match="regimen"):
        await calc.calculate(
            quarter=1,
            anos_actividad=5,
            regimen="otro",
            rend_neto_penultimo=10000,
        )


@pytest.mark.asyncio
async def test_estructura_respuesta_general(calc):
    """Estructura completa de la respuesta del régimen general."""
    r = await calc.calculate(
        quarter=1,
        anos_actividad=5,
        regimen="general",
        rend_neto_penultimo=20000,
        retenciones_penultimo=2000,
    )
    assert set(r["casillas"].keys()) == {
        "01_base_calculo",
        "02_tipo_aplicable_pct",
        "03_cuota_base",
        "04_retenciones_penultimo",
        "05_minoracion_25pct_retenciones",
        "06_resultado_pago_fraccionado",
    }
    assert "concepto" in r["desglose"]
    assert r["plazo"]


@pytest.mark.asyncio
async def test_estructura_respuesta_primeros_anos(calc):
    """Estructura completa de la respuesta de los primeros 2 años."""
    r = await calc.calculate(
        quarter=2,
        anos_actividad=1,
        ingresos_acumulados=10000,
        gastos_acumulados=2000,
    )
    assert set(r["casillas"].keys()) == {
        "01_ingresos_acumulados",
        "02_gastos_acumulados",
        "03_rendimiento_neto_acumulado",
        "04_cuota_20pct",
        "05_retenciones_acumuladas",
        "06_pagos_anteriores",
        "07_resultado_pago_fraccionado",
    }


@pytest.mark.asyncio
async def test_redondeo_dos_decimales(calc):
    """Todos los importes se redondean a 2 decimales."""
    r = await calc.calculate(
        quarter=1,
        anos_actividad=5,
        regimen="general",
        rend_neto_penultimo=12345.678,  # cuota = 617.2839 → 617.28
        retenciones_penultimo=100.123,  # 25% = 25.03075 → 25.03
    )
    assert r["casillas"]["03_cuota_base"] == 617.28
    assert r["casillas"]["05_minoracion_25pct_retenciones"] == 25.03
    # 617.28 - 25.03 = 592.25
    assert r["resultado"] == 592.25


# ===========================================================================
# Smoke test PDF render foral
# ===========================================================================


@pytest.mark.asyncio
async def test_pdf_render_foral_bizkaia_smoke(calc):
    """Genera el PDF foral Bizkaia y comprueba que devuelve bytes válidos."""
    from app.services.modelo_pdf_generator import ModeloPDFGenerator

    r = await calc.calculate(
        quarter=2,
        anos_actividad=5,
        regimen="general",
        rend_neto_penultimo=30000,
        retenciones_penultimo=4000,
    )

    pdf_data = {
        "variante_foral": "130-bizkaia",
        "casillas": r["casillas"],
        "regimen": r["regimen"],
        "tipo_aplicado": r["tipo_aplicado"],
        "plazo": r["plazo"],
        "resultado_final": r["resultado"],
        "dispensado": False,
    }

    pdf_bytes = ModeloPDFGenerator().generate(
        modelo_type="130",
        data=pdf_data,
        user_info={"nombre": "Aitor", "nif": "12345678Z", "variante_foral": "130-bizkaia"},
        trimestre="2T",
        ejercicio=2026,
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000  # PDF mínimamente formado
