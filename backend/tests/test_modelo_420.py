"""Tests for Modelo 420 (IGIC Canarias) calculator.

Refactor 2026-05-10 — Decreto Legislativo 1/2025 (TR IGIC + AIEM).
Eliminados tipos derogados 13.5% y 35%. Anadidos 1% energeticos, 5% reducido,
15% incrementado, 20% especial unificado tabaco. Parametrizado por ejercicio.
REPEP (umbral 30.000 EUR) gestionado en plugin Canarias, no en calculator.

Audit: docs/audits/modelo_420_validation_2026-05.md
Fuente normativa: BOC nº 207 (2025-10-20), vigor 2025-10-21.
"""

import pytest

from app.utils.calculators.modelo_420 import (
    DEROGATED_RATES_2024,
    # Tabla parametrica por ejercicio
    IGIC_RATES_BY_YEAR,
    PLAZOS_MODELO_420,
    REPEP_THRESHOLD_EUR,
    # Tipos vigentes 2025+
    TIPO_CERO,
    TIPO_ENERGETICOS,
    TIPO_ESPECIAL,
    TIPO_GENERAL,
    TIPO_INCREMENTADO_1,
    TIPO_INCREMENTADO_2,
    TIPO_REDUCIDO,
    TIPO_SUPERREDUCIDO,
    Modelo420Calculator,
)


@pytest.fixture
def calc():
    return Modelo420Calculator(None)


# ────────────────────────────────────────────────────────────────────
# 1. Tipos vigentes 2025+ (Decreto Legislativo 1/2025)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_basic_general_7pct(calc):
    """Autonomo canario factura 10.000 al tipo general (7%)."""
    r = await calc.calculate(base_general=10000)
    assert r["total_devengado"] == 700  # 10.000 * 0.07
    assert r["total_deducible"] == 0
    assert r["resultado_liquidacion"] == 700


@pytest.mark.asyncio
async def test_tipo_cero(calc):
    """Tipo cero (0%) genera cuota 0."""
    r = await calc.calculate(base_cero=50000)
    assert r["desglose_devengado"]["tipo_cero"]["cuota"] == 0
    assert r["total_devengado"] == 0


@pytest.mark.asyncio
async def test_tipo_energeticos_1pct(calc):
    """Tipo especifico energeticos (1%, Art. 33 bis TR) — NUEVO 2025."""
    r = await calc.calculate(base_energeticos=10000)
    assert r["desglose_devengado"]["tipo_energeticos"]["cuota"] == 100
    assert r["desglose_devengado"]["tipo_energeticos"]["tipo"] == 0.01
    assert r["total_devengado"] == 100


@pytest.mark.asyncio
async def test_tipo_superreducido_3pct(calc):
    """Tipo superreducido (3%, Art. 34 TR) — antes 'reducido'."""
    r = await calc.calculate(base_superreducido=10000)
    assert r["desglose_devengado"]["tipo_superreducido"]["cuota"] == 300
    assert r["desglose_devengado"]["tipo_superreducido"]["tipo"] == 0.03


@pytest.mark.asyncio
async def test_tipo_reducido_5pct(calc):
    """Tipo reducido (5%, Art. 35 TR) — NUEVO 2025."""
    r = await calc.calculate(base_reducido=10000)
    assert r["desglose_devengado"]["tipo_reducido"]["cuota"] == 500
    assert r["desglose_devengado"]["tipo_reducido"]["tipo"] == 0.05


@pytest.mark.asyncio
async def test_tipo_incrementado_9_5pct(calc):
    """Tipo incrementado 9.5% — vehiculos, embarcaciones, joyeria."""
    r = await calc.calculate(base_incrementado_1=10000)
    assert r["desglose_devengado"]["tipo_incrementado_1"]["cuota"] == 950
    assert r["desglose_devengado"]["tipo_incrementado_1"]["tipo"] == 0.095


@pytest.mark.asyncio
async def test_tipo_incrementado_15pct(calc):
    """Tipo incrementado 15% — perfumeria, peleteria (sustituye 13.5% derogado)."""
    r = await calc.calculate(base_incrementado_2=10000)
    assert r["desglose_devengado"]["tipo_incrementado_2"]["cuota"] == 1500
    assert r["desglose_devengado"]["tipo_incrementado_2"]["tipo"] == 0.15


@pytest.mark.asyncio
async def test_tipo_especial_20pct_tabaco(calc):
    """Tipo especial 20% — labores del tabaco (unificado, antes 20/35)."""
    r = await calc.calculate(base_especial=10000)
    assert r["desglose_devengado"]["tipo_especial"]["cuota"] == 2000
    assert r["desglose_devengado"]["tipo_especial"]["tipo"] == 0.20


@pytest.mark.asyncio
async def test_all_8_rates_2025(calc):
    """Las 8 escalas vigentes 2025 (TR Decreto Legislativo 1/2025)."""
    r = await calc.calculate(
        base_cero=1000,
        base_energeticos=1000,
        base_superreducido=1000,
        base_reducido=1000,
        base_general=1000,
        base_incrementado_1=1000,
        base_incrementado_2=1000,
        base_especial=1000,
    )
    expected = (
        1000 * TIPO_CERO
        + 1000 * TIPO_ENERGETICOS
        + 1000 * TIPO_SUPERREDUCIDO
        + 1000 * TIPO_REDUCIDO
        + 1000 * TIPO_GENERAL
        + 1000 * TIPO_INCREMENTADO_1
        + 1000 * TIPO_INCREMENTADO_2
        + 1000 * TIPO_ESPECIAL
    )
    assert r["total_devengado"] == round(expected, 2)


# ────────────────────────────────────────────────────────────────────
# 2. Constantes derogadas y referencias legales
# ────────────────────────────────────────────────────────────────────


def test_constantes_modulo_no_exponen_tipos_derogados():
    """13.5% y 35% NO deben existir como constantes publicas en 2025+."""
    import app.utils.calculators.modelo_420 as mod

    publics = {name for name in dir(mod) if not name.startswith("_")}
    # Nombres del esquema antiguo Ley 4/2012
    assert "TIPO_INCREMENTADO_2_OLD" not in publics
    # Si existen helpers historicos, deben ir en DEROGATED_RATES_2024
    assert 0.135 not in IGIC_RATES_BY_YEAR.get(2025, {}).values()
    assert 0.35 not in IGIC_RATES_BY_YEAR.get(2025, {}).values()


def test_derogated_rates_disponibles_para_2024():
    """Los tipos historicos 13.5% y 35% deben quedar accesibles para ejercicios <2025."""
    assert 0.135 in DEROGATED_RATES_2024.values()
    assert 0.35 in DEROGATED_RATES_2024.values()


def test_igic_rates_by_year_estructura():
    """IGIC_RATES_BY_YEAR debe tener entradas para 2024 (antiguo) y 2025+ (nuevo)."""
    assert 2024 in IGIC_RATES_BY_YEAR
    assert 2025 in IGIC_RATES_BY_YEAR
    assert 2026 in IGIC_RATES_BY_YEAR
    # 2025 trae los nuevos tipos
    rates_2025 = IGIC_RATES_BY_YEAR[2025]
    assert rates_2025["energeticos"] == 0.01
    assert rates_2025["reducido"] == 0.05
    assert rates_2025["incrementado_2"] == 0.15
    assert rates_2025["especial"] == 0.20


def test_docstring_referencia_decreto_legislativo_1_2025():
    """El docstring del modulo NO debe citar 'Ley 4/2012, art. 27' (norma derogada)."""
    import app.utils.calculators.modelo_420 as mod

    doc = mod.__doc__ or ""
    # La referencia falsa NO debe aparecer
    assert "Ley 4/2012, art. 27" not in doc
    assert "Ley 4/2012 art. 27" not in doc
    # La nueva norma SI debe aparecer
    assert "Decreto Legislativo 1/2025" in doc


# ────────────────────────────────────────────────────────────────────
# 3. Parametrizacion por ejercicio
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_year_2024_acepta_tipo_13_5_legacy(calc):
    """Ejercicio 2024 (antes del TR) sigue admitiendo el 13.5% historico."""
    r = await calc.calculate(base_incrementado_2=10000, year=2024)
    # 2024 → tipo derogado 13.5%
    assert r["desglose_devengado"]["tipo_incrementado_2"]["tipo"] == 0.135
    assert r["desglose_devengado"]["tipo_incrementado_2"]["cuota"] == 1350


@pytest.mark.asyncio
async def test_year_2025_aplica_15pct_no_13_5(calc):
    """Ejercicio 2025+: el campo `base_incrementado_2` se grava al 15%, no al 13.5%."""
    r = await calc.calculate(base_incrementado_2=10000, year=2025)
    assert r["desglose_devengado"]["tipo_incrementado_2"]["tipo"] == 0.15
    assert r["desglose_devengado"]["tipo_incrementado_2"]["cuota"] == 1500


@pytest.mark.asyncio
async def test_year_2024_tabaco_rubio_35pct_legacy(calc):
    """Ejercicio 2024: tabaco rubio mantiene 35% (esquema derogado)."""
    r = await calc.calculate(base_especial=10000, year=2024, tabaco_rubio_legacy=True)
    # legacy 35% solo accesible bajo year<2025 + flag explicito
    assert r["desglose_devengado"]["tipo_especial"]["tipo"] == 0.35
    assert r["desglose_devengado"]["tipo_especial"]["cuota"] == 3500


@pytest.mark.asyncio
async def test_year_2025_tabaco_unificado_20pct(calc):
    """Ejercicio 2025+: tabaco unificado al 20% (TR Art. 37)."""
    r = await calc.calculate(base_especial=10000, year=2025, tabaco_rubio_legacy=True)
    # En 2025+ el flag legacy se ignora — tabaco unificado al 20%
    assert r["desglose_devengado"]["tipo_especial"]["tipo"] == 0.20
    assert r["desglose_devengado"]["tipo_especial"]["cuota"] == 2000


@pytest.mark.asyncio
async def test_year_default_es_actual_o_posterior(calc):
    """Default sin especificar year → debe aplicar el esquema vigente (>=2025)."""
    r = await calc.calculate(base_incrementado_2=1000)
    assert r["desglose_devengado"]["tipo_incrementado_2"]["tipo"] == 0.15


# ────────────────────────────────────────────────────────────────────
# 4. Estructura calculo (preservada)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_devengado_minus_deducible(calc):
    """Resultado = devengado - deducible."""
    r = await calc.calculate(base_general=10000, cuota_corrientes_interiores=400)
    assert r["total_devengado"] == 700
    assert r["total_deducible"] == 400
    assert r["resultado_regimen_general"] == 300
    assert r["resultado_liquidacion"] == 300


@pytest.mark.asyncio
async def test_compensar_anteriores(calc):
    """Cuotas a compensar de periodos anteriores."""
    r = await calc.calculate(base_general=10000, cuotas_compensar_anteriores=200)
    assert r["resultado_liquidacion"] == 700 - 200  # 500


@pytest.mark.asyncio
async def test_compensar_negativa_clamped(calc):
    """Cuotas a compensar negativas se clampean a 0."""
    r = await calc.calculate(base_general=1000, cuotas_compensar_anteriores=-50)
    assert r["cuotas_compensar_anteriores"] == 0
    assert r["resultado_liquidacion"] == 70  # 1000 * 0.07


@pytest.mark.asyncio
async def test_regularizacion_anual_4t(calc):
    """Regularizacion anual solo en 4T."""
    r4 = await calc.calculate(base_general=1000, regularizacion_anual=100, quarter=4)
    assert r4["regularizacion_anual"] == 100
    assert r4["resultado_liquidacion"] == 70 + 100  # 170

    r2 = await calc.calculate(base_general=1000, regularizacion_anual=100, quarter=2)
    assert r2["regularizacion_anual"] == 0
    assert r2["resultado_liquidacion"] == 70


@pytest.mark.asyncio
async def test_complementaria(calc):
    """Complementaria: diferencia con resultado anterior."""
    r = await calc.calculate(base_general=10000, resultado_anterior_complementaria=500)
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
async def test_igic_rates_exposed_2025(calc):
    """IGIC rates devueltas en el resultado deben reflejar el esquema 2025."""
    r = await calc.calculate(base_general=100, year=2025)
    rates = r["igic_rates"]
    assert rates["tipo_cero"] == 0.0
    assert rates["tipo_energeticos"] == 0.01
    assert rates["tipo_superreducido"] == 0.03
    assert rates["tipo_reducido"] == 0.05
    assert rates["tipo_general"] == 0.07
    assert rates["tipo_incrementado_1"] == 0.095
    assert rates["tipo_incrementado_2"] == 0.15
    assert rates["tipo_especial"] == 0.20
    # Los tipos derogados NO deben aparecer en el output 2025
    assert "tipo_especial_2" not in rates
    assert 0.135 not in rates.values()
    assert 0.35 not in rates.values()


@pytest.mark.asyncio
async def test_negative_result(calc):
    """More deducible than devengado → negative resultado."""
    r = await calc.calculate(base_general=1000, cuota_corrientes_interiores=500)
    assert r["resultado_regimen_general"] == 70 - 500  # -430
    assert r["resultado_liquidacion"] == -430


# ────────────────────────────────────────────────────────────────────
# 5. Tests negativos — bases y tipos invalidos
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rechaza_base_negativa(calc):
    """Una base imponible negativa debe rechazarse con ValueError."""
    with pytest.raises(ValueError, match="base"):
        await calc.calculate(base_general=-1000)


@pytest.mark.asyncio
async def test_rechaza_year_invalido(calc):
    """Years <2010 o >2099 deben rechazarse."""
    with pytest.raises(ValueError, match="year"):
        await calc.calculate(base_general=1000, year=2009)
    with pytest.raises(ValueError, match="year"):
        await calc.calculate(base_general=1000, year=2100)


@pytest.mark.asyncio
async def test_rechaza_quarter_invalido(calc):
    """Quarters fuera de 1-4 deben rechazarse."""
    with pytest.raises(ValueError, match="quarter"):
        await calc.calculate(base_general=1000, quarter=5)
    with pytest.raises(ValueError, match="quarter"):
        await calc.calculate(base_general=1000, quarter=0)


# ────────────────────────────────────────────────────────────────────
# 6. Plazos Modelo 420 (PLAZOS_MODELO_420)
# ────────────────────────────────────────────────────────────────────


def test_plazos_modelo_420_estructura():
    """PLAZOS_MODELO_420 debe tener 4 trimestres."""
    assert 1 in PLAZOS_MODELO_420
    assert 2 in PLAZOS_MODELO_420
    assert 3 in PLAZOS_MODELO_420
    assert 4 in PLAZOS_MODELO_420


def test_plazo_t1_20_abril():
    """Plazo T1: 1-20 abril (mes 4, dia 20)."""
    plazo = PLAZOS_MODELO_420[1]
    assert plazo["mes_fin"] == 4
    assert plazo["dia_fin"] == 20


def test_plazo_t2_20_julio():
    """Plazo T2: 1-20 julio."""
    plazo = PLAZOS_MODELO_420[2]
    assert plazo["mes_fin"] == 7
    assert plazo["dia_fin"] == 20


def test_plazo_t3_20_octubre():
    """Plazo T3: 1-20 octubre."""
    plazo = PLAZOS_MODELO_420[3]
    assert plazo["mes_fin"] == 10
    assert plazo["dia_fin"] == 20


def test_plazo_t4_30_enero():
    """Plazo T4: 1-30 enero ano siguiente."""
    plazo = PLAZOS_MODELO_420[4]
    assert plazo["mes_fin"] == 1
    assert plazo["dia_fin"] == 30
    assert plazo["anio_siguiente"] is True


# ────────────────────────────────────────────────────────────────────
# 7. REPEP — umbral exencion
# ────────────────────────────────────────────────────────────────────


def test_repep_threshold_30000():
    """REPEP umbral 30.000 EUR (Art. correspondiente TR Decreto Legislativo 1/2025)."""
    assert REPEP_THRESHOLD_EUR == 30000.0


# ────────────────────────────────────────────────────────────────────
# 8. Casos practicos audit
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_caso_C_perfumeria_15pct(calc):
    """Caso C audit: venta perfumeria/electronica antes 13.5% → ahora 15%."""
    r = await calc.calculate(base_incrementado_2=2000, year=2025)
    assert r["desglose_devengado"]["tipo_incrementado_2"]["cuota"] == 300  # 2000*0.15


@pytest.mark.asyncio
async def test_caso_D_tabaco_rubio_20pct(calc):
    """Caso D audit: tabaco rubio antes 35% → ahora 20% unificado."""
    r = await calc.calculate(base_especial=1000, year=2025)
    assert r["desglose_devengado"]["tipo_especial"]["cuota"] == 200  # 1000*0.20


@pytest.mark.asyncio
async def test_caso_E_gas_residencial_1pct(calc):
    """Caso E audit: suministro gas residencial al 1% (Art. 33 bis TR)."""
    r = await calc.calculate(base_energeticos=500, year=2025)
    assert r["desglose_devengado"]["tipo_energeticos"]["cuota"] == 5  # 500*0.01
