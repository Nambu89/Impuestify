"""Tests for Modelo 130 Gipuzkoa (Pago Fraccionado IRPF foral)."""

import pytest

from app.utils.calculators.modelo_130_gipuzkoa import Modelo130GipuzkoaCalculator


@pytest.fixture
def calc():
    return Modelo130GipuzkoaCalculator(repo=None)


# ===========================================================================
# Régimen general (rend. neto penúltimo > 0, ≥ 3.er año)
# ===========================================================================


@pytest.mark.asyncio
async def test_general_basico(calc):
    """General: 30.000 × 5% = 1.500. Sin retenciones → 1.500."""
    r = await calc.calculate(
        quarter=1,
        regimen="general",
        rend_neto_penultimo=30000,
    )
    assert r["territory"] == "Gipuzkoa"
    assert r["regimen"] == "general"
    assert r["tipo_aplicado"] == 5.0
    assert r["casillas"]["03_cuota_base"] == 1500.0
    assert r["resultado"] == 1500.0


@pytest.mark.asyncio
async def test_general_con_retenciones(calc):
    """General: 30.000 × 5% − 4.000 × 25% = 1.500 − 1.000 = 500."""
    r = await calc.calculate(
        quarter=2,
        regimen="general",
        rend_neto_penultimo=30000,
        retenciones_penultimo=4000,
    )
    assert r["casillas"]["05_minoracion_25pct_retenciones"] == 1000.0
    assert r["resultado"] == 500.0


@pytest.mark.asyncio
async def test_general_minoracion_supera_cuota_se_clipa(calc):
    """Si minoración > cuota → resultado 0."""
    r = await calc.calculate(
        quarter=1,
        regimen="general",
        rend_neto_penultimo=10000,
        retenciones_penultimo=15000,  # 25% = 3.750 > 500
    )
    assert r["resultado"] == 0


@pytest.mark.asyncio
async def test_general_rend_negativo_clipa(calc):
    """rend negativo → base 0 → resultado 0."""
    r = await calc.calculate(
        quarter=1,
        regimen="general",
        rend_neto_penultimo=-5000,
    )
    assert r["casillas"]["01_rend_neto_penultimo"] == -5000.0  # registrado
    assert r["resultado"] == 0


# ===========================================================================
# Régimen excepcional (años 1-2 o rend. penúltimo ≤ 0)
# ===========================================================================


@pytest.mark.asyncio
async def test_excepcional_basico(calc):
    """Excepcional: 50.000 operaciones × 1% = 500."""
    r = await calc.calculate(
        quarter=2,
        regimen="excepcional",
        volumen_operaciones_trimestre=50000,
    )
    assert r["regimen"] == "excepcional"
    assert r["tipo_aplicado"] == 1.0
    assert r["resultado"] == 500.0


@pytest.mark.asyncio
async def test_excepcional_con_retenciones(calc):
    """Excepcional: 50.000 × 1% − 200 = 300."""
    r = await calc.calculate(
        quarter=3,
        regimen="excepcional",
        volumen_operaciones_trimestre=50000,
        retenciones_trimestre=200,
    )
    assert r["resultado"] == 300.0


@pytest.mark.asyncio
async def test_excepcional_retenciones_superan_cuota(calc):
    """Excepcional: si retenciones > cuota → 0."""
    r = await calc.calculate(
        quarter=1,
        regimen="excepcional",
        volumen_operaciones_trimestre=10000,  # cuota 100
        retenciones_trimestre=500,
    )
    assert r["resultado"] == 0


# ===========================================================================
# Dispensa por retención (Norma Foral Gipuzkoa)
# ===========================================================================


def test_dispensa_profesional_50pct():
    """Profesional con ≥ 50 % → dispensado."""
    assert Modelo130GipuzkoaCalculator.is_dispensado_por_retencion(
        es_profesional=True,
        actividad_agraria=False,
        pct_retencion_anio_anterior=50.0,
    )
    assert Modelo130GipuzkoaCalculator.is_dispensado_por_retencion(
        es_profesional=True,
        actividad_agraria=False,
        pct_retencion_anio_anterior=75.0,
    )


def test_dispensa_profesional_49pct_no_dispensado():
    """Profesional con 49 % NO dispensado."""
    assert not Modelo130GipuzkoaCalculator.is_dispensado_por_retencion(
        es_profesional=True,
        actividad_agraria=False,
        pct_retencion_anio_anterior=49.0,
    )


def test_dispensa_agrario_70pct():
    """Agrario con ≥ 70 % → dispensado."""
    assert Modelo130GipuzkoaCalculator.is_dispensado_por_retencion(
        es_profesional=False,
        actividad_agraria=True,
        pct_retencion_anio_anterior=70.0,
    )


def test_dispensa_agrario_60pct_no_dispensado():
    """Agrario con 60 % NO dispensado (umbral 70 %)."""
    assert not Modelo130GipuzkoaCalculator.is_dispensado_por_retencion(
        es_profesional=False,
        actividad_agraria=True,
        pct_retencion_anio_anterior=60.0,
    )


def test_dispensa_empresarial_no_aplica():
    """Empresarial puro NO tiene dispensa por retención."""
    assert not Modelo130GipuzkoaCalculator.is_dispensado_por_retencion(
        es_profesional=False,
        actividad_agraria=False,
        pct_retencion_anio_anterior=99.0,
    )


# ===========================================================================
# Plazos (verificados en gipuzkoa.eus 2026-05)
# ===========================================================================


@pytest.mark.asyncio
async def test_plazos_los_cuatro_trimestres(calc):
    plazos_esperados = {
        1: "1 de abril al 10 de mayo",
        2: "1 de julio al 10 de agosto",
        3: "1 de octubre al 10 de noviembre",
        4: "1 de enero al 10 de febrero del año siguiente",
    }
    for q, plazo in plazos_esperados.items():
        r = await calc.calculate(
            quarter=q,
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
            quarter=0,
            regimen="general",
            rend_neto_penultimo=10000,
        )


@pytest.mark.asyncio
async def test_regimen_invalido_raise(calc):
    with pytest.raises(ValueError, match="regimen"):
        await calc.calculate(
            quarter=1,
            regimen="otro",
            rend_neto_penultimo=10000,
        )


@pytest.mark.asyncio
async def test_estructura_respuesta_general(calc):
    r = await calc.calculate(
        quarter=1,
        regimen="general",
        rend_neto_penultimo=10000,
    )
    assert set(r["casillas"].keys()) == {
        "01_rend_neto_penultimo",
        "02_tipo_aplicable_pct",
        "03_cuota_base",
        "04_retenciones_penultimo",
        "05_minoracion_25pct_retenciones",
        "06_resultado_pago_fraccionado",
    }


@pytest.mark.asyncio
async def test_estructura_respuesta_excepcional(calc):
    r = await calc.calculate(
        quarter=1,
        regimen="excepcional",
        volumen_operaciones_trimestre=10000,
    )
    assert set(r["casillas"].keys()) == {
        "01_volumen_operaciones_trimestre",
        "02_tipo_aplicable_pct",
        "03_cuota_base",
        "04_retenciones_trimestre",
        "05_resultado_pago_fraccionado",
    }


@pytest.mark.asyncio
async def test_redondeo_dos_decimales(calc):
    """Todos los importes a 2 decimales."""
    r = await calc.calculate(
        quarter=1,
        regimen="general",
        rend_neto_penultimo=12345.678,
        retenciones_penultimo=100.987,
    )
    assert r["casillas"]["03_cuota_base"] == 617.28
    assert r["casillas"]["05_minoracion_25pct_retenciones"] == 25.25


# ===========================================================================
# Wrapper foral tool — routing y dispensa
# ===========================================================================


@pytest.mark.asyncio
async def test_wrapper_routing_gipuzkoa_general():
    """El wrapper foral enruta correctamente a Gipuzkoa con régimen general."""
    from app.tools.modelo_130_foral_tool import calculate_modelo_130_foral_tool

    r = await calculate_modelo_130_foral_tool(
        territorio="Gipuzkoa",
        trimestre=1,
        regimen="general",
        rend_neto_penultimo=20000,
    )
    assert r["success"] is True
    assert r["territorio"] == "Gipuzkoa"
    assert r["regimen"] == "general"
    assert r["tipo_aplicado"] == 5.0
    assert r["resultado_final"] == 1000.0
    assert r["dispensado"] is False
    assert "Modelo 130" in r["formatted_response"]


@pytest.mark.asyncio
async def test_wrapper_dispensa_gipuzkoa_profesional_50pct():
    """Wrapper aplica dispensa Gipuzkoa para profesionales ≥ 50 %."""
    from app.tools.modelo_130_foral_tool import calculate_modelo_130_foral_tool

    r = await calculate_modelo_130_foral_tool(
        territorio="Gipuzkoa",
        trimestre=1,
        es_profesional=True,
        pct_retencion_anio_anterior=55.0,
    )
    assert r["success"] is True
    assert r["dispensado"] is True
    assert r["umbral_dispensa_pct"] == 50.0
    assert r["resultado_final"] == 0.0
    assert "DISPENSA" in r["formatted_response"]


@pytest.mark.asyncio
async def test_wrapper_alias_alava_resuelve_a_araba():
    """Alias 'Alava' (sin tilde) → Araba."""
    from app.tools.modelo_130_foral_tool import calculate_modelo_130_foral_tool

    r = await calculate_modelo_130_foral_tool(
        territorio="Alava",
        trimestre=1,
        ingresos_trimestre=10000,
        gastos_trimestre=5000,
    )
    assert r["success"] is True
    assert r["territorio"] == "Araba/Álava"
    assert r["resultado_final"] == 250.0


@pytest.mark.asyncio
async def test_wrapper_territorio_no_foral_devuelve_error():
    """Territorio común NO está soportado en este wrapper."""
    from app.tools.modelo_130_foral_tool import calculate_modelo_130_foral_tool

    r = await calculate_modelo_130_foral_tool(
        territorio="Madrid",
        trimestre=1,
    )
    assert r["success"] is False
    assert "no soportado" in r["error"].lower()


@pytest.mark.asyncio
async def test_wrapper_restricted_mode_blockea():
    """`restricted_mode=True` bloquea el wrapper (plan Particular)."""
    from app.tools.modelo_130_foral_tool import calculate_modelo_130_foral_tool

    r = await calculate_modelo_130_foral_tool(
        territorio="Bizkaia",
        trimestre=1,
        restricted_mode=True,
    )
    assert r["success"] is False
    assert r["error"] == "restricted"
