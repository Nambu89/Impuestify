"""
Tests para extensiones P1/P2 del Modelo 303 (audit 2026-05, sesion 40).

Cubre:
- RECC (Regimen Especial Criterio de Caja, Art. 163 decies-sexies LIVA)
- SII (Suministro Inmediato Informacion, Art. 62.6 RIVA)
- ISP por supuesto (Art. 84.uno.2 LIVA)
- Modificaciones de bases (Art. 80 + 89 LIVA)
- Tipos transitorios alimentacion / aceites (RDL 4/2022, RDL 9/2024)
- Recargo Equivalencia detector ampliado (Art. 154-163 LIVA)

NO sustituye a `test_modelo_303.py` — es un suite paralelo que valida solo
los nuevos parametros sin afectar a la regresion existente.
"""

import pytest
from app.utils.calculators.modelo_303 import (
    Modelo303Calculator,
    ISP_SUPUESTOS,
    RE_RATES_FULL,
)


@pytest.fixture
def calc():
    return Modelo303Calculator(None)


# =====================================================================
# RECC — Regimen Especial Criterio de Caja
# =====================================================================


@pytest.mark.asyncio
async def test_recc_eligible_under_threshold(calc):
    """RECC elegible si volumen ano anterior <= 2.000.000 EUR."""
    r = await calc.calculate(
        base_21=10000,
        regimen_recc=True,
        volumen_ano_anterior=1_500_000.0,
    )
    assert r["regimen_recc"]["regimen_aplicado"] is True
    assert r["regimen_recc"]["elegible"] is True
    assert r["regimen_recc"]["warning"] is None
    assert r["regimen_recc"]["umbral_volumen"] == 2_000_000.0


@pytest.mark.asyncio
async def test_recc_not_eligible_over_threshold(calc):
    """RECC NO elegible si volumen > 2M EUR — warning generado."""
    r = await calc.calculate(
        base_21=10000,
        regimen_recc=True,
        volumen_ano_anterior=2_500_000.0,
    )
    assert r["regimen_recc"]["regimen_aplicado"] is False
    assert r["regimen_recc"]["elegible"] is False
    assert r["regimen_recc"]["warning"] is not None
    assert "umbral RECC" in r["regimen_recc"]["warning"]
    assert any("umbral" in w.lower() or "rec" in w.lower() for w in r["warnings"])


@pytest.mark.asyncio
async def test_recc_devengado_diferido_se_suma(calc):
    """Cobros materializados de devengo anterior suman al casilla 27."""
    r = await calc.calculate(
        base_21=10000,  # devengado periodo = 2100
        regimen_recc=True,
        volumen_ano_anterior=500_000,
        cobros_pendientes_recc=420,  # cobro de venta T anterior
    )
    # casilla 27 = 2100 (corriente) + 420 (RECC diferido) = 2520
    assert r["casilla_27"] == 2520.0


@pytest.mark.asyncio
async def test_recc_deducible_diferido_se_suma(calc):
    """Pagos materializados de deducciones anteriores suman al casilla 45."""
    r = await calc.calculate(
        cuota_corrientes_interiores=100,  # deducible periodo
        regimen_recc=True,
        volumen_ano_anterior=500_000,
        pagos_pendientes_recc=300,  # pago de compra T anterior
    )
    # casilla 45 = 100 + 300 (RECC) = 400
    assert r["casilla_45"] == 400.0


@pytest.mark.asyncio
async def test_recc_limite_temporal_year_plus_one(calc):
    """Limite temporal RECC: 31 dic ano siguiente al devengo."""
    r = await calc.calculate(
        base_21=1000,
        regimen_recc=True,
        volumen_ano_anterior=100_000,
        year=2025,
    )
    assert r["regimen_recc"]["limite_temporal_year"] == 2026


@pytest.mark.asyncio
async def test_recc_disabled_no_extra_devengo(calc):
    """Si RECC desactivado, cobros pendientes NO se suman."""
    r = await calc.calculate(
        base_21=10000,
        cobros_pendientes_recc=420,  # se ignora porque regimen_recc=False
    )
    assert r["casilla_27"] == 2100.0
    assert r["regimen_recc"]["regimen_aplicado"] is False


@pytest.mark.asyncio
async def test_recc_helper_es_elegible(calc):
    """Helper estatico es_elegible_recc()."""
    assert calc.es_elegible_recc(0) is True
    assert calc.es_elegible_recc(1_999_999) is True
    assert calc.es_elegible_recc(2_000_000) is True
    assert calc.es_elegible_recc(2_000_001) is False
    assert calc.es_elegible_recc(-100) is False  # negativo invalido


# =====================================================================
# SII — Suministro Inmediato Informacion
# =====================================================================


@pytest.mark.asyncio
async def test_sii_obligatorio_por_volumen(calc):
    """Volumen > 6.010.121,04 EUR -> SII obligatorio."""
    r = await calc.calculate(
        base_21=100,
        volumen_ano_anterior=10_000_000,
    )
    assert r["sii"]["obligatorio"] is True
    assert r["sii"]["aplicado"] is True
    assert r["sii"]["periodicidad"] == "mensual"
    assert "mensual" in r["sii"]["warning"].lower()


@pytest.mark.asyncio
async def test_sii_obligatorio_por_redeme(calc):
    """REDEME -> SII obligatorio aunque volumen sea bajo."""
    r = await calc.calculate(base_21=100, redeme=True)
    assert r["sii"]["obligatorio"] is True
    assert r["sii"]["aplicado"] is True


@pytest.mark.asyncio
async def test_sii_obligatorio_por_grupo_iva(calc):
    """Grupo IVA Art. 163 quinquies -> SII obligatorio."""
    r = await calc.calculate(base_21=100, grupo_iva=True)
    assert r["sii"]["obligatorio"] is True


@pytest.mark.asyncio
async def test_sii_voluntario(calc):
    """En SII voluntariamente sin obligacion -> aplicado pero no obligatorio."""
    r = await calc.calculate(base_21=100, en_sii=True, volumen_ano_anterior=500_000)
    assert r["sii"]["obligatorio"] is False
    assert r["sii"]["aplicado"] is True
    assert r["sii"]["periodicidad"] == "mensual"


@pytest.mark.asyncio
async def test_sii_no_aplicado_default(calc):
    """Sin SII -> trimestral, sin warning."""
    r = await calc.calculate(base_21=100)
    assert r["sii"]["obligatorio"] is False
    assert r["sii"]["aplicado"] is False
    assert r["sii"]["periodicidad"] == "trimestral"
    assert r["sii"]["warning"] is None


@pytest.mark.asyncio
async def test_sii_helper_requiere_sii(calc):
    """Helper estatico requiere_sii()."""
    assert calc.requiere_sii(7_000_000) is True
    assert calc.requiere_sii(6_010_121.04) is False  # boundary inclusive
    assert calc.requiere_sii(6_010_121.05) is True
    assert calc.requiere_sii(100, redeme=True) is True
    assert calc.requiere_sii(100, grupo_iva=True) is True
    assert calc.requiere_sii(100) is False


# =====================================================================
# ISP — Inversion Sujeto Pasivo Art. 84.uno.2 LIVA
# =====================================================================


@pytest.mark.asyncio
async def test_isp_construccion_devengado_y_deducible(calc):
    """ISP construccion: cuota devengada y deducible simultaneas (neto 0)."""
    r = await calc.calculate(
        bases_isp={"construccion": {"base": 10000, "tipo": 21}},
    )
    assert r["isp_desglose"]["total_base_isp"] == 10000.0
    assert r["isp_desglose"]["total_cuota_isp"] == 2100.0
    # devengado y deducible se compensan (neto 0)
    assert r["casilla_27"] == 2100.0
    assert r["casilla_45"] == 2100.0
    assert r["resultado_liquidacion"] == 0.0


@pytest.mark.asyncio
async def test_isp_no_deducible(calc):
    """ISP no deducible (actividad exenta): solo suma a devengado."""
    r = await calc.calculate(
        bases_isp={"moviles": {"base": 5000, "tipo": 21}},
        isp_es_deducible=False,
    )
    assert r["casilla_27"] == 1050.0  # devengado +1050
    assert r["casilla_45"] == 0.0  # NO se suma a deducible
    assert r["resultado_liquidacion"] == 1050.0


@pytest.mark.asyncio
async def test_isp_multiples_supuestos(calc):
    """Varios supuestos ISP simultaneos."""
    r = await calc.calculate(
        bases_isp={
            "construccion": {"base": 10000, "tipo": 21},
            "moviles": {"base": 2000, "tipo": 21},
            "inmuebles": {"base": 50000, "tipo": 10},
        },
    )
    desg = r["isp_desglose"]["desglose_supuestos"]
    assert "construccion" in desg
    assert "moviles" in desg
    assert "inmuebles" in desg
    # base total = 62000, cuota total = 2100 + 420 + 5000 = 7520
    assert r["isp_desglose"]["total_cuota_isp"] == 7520.0


@pytest.mark.asyncio
async def test_isp_supuestos_constantes_disponibles():
    """ISP_SUPUESTOS expone las descripciones legales."""
    assert "construccion" in ISP_SUPUESTOS
    assert "Art. 84.uno.2.f" in ISP_SUPUESTOS["construccion"]
    assert "moviles" in ISP_SUPUESTOS
    assert "Art. 84.uno.2.g" in ISP_SUPUESTOS["moviles"]


# =====================================================================
# Modificaciones de bases (Art. 80 + 89 LIVA)
# =====================================================================


@pytest.mark.asyncio
async def test_mod_bases_envases_concurso(calc):
    """Modificaciones por devolucion envases + concurso acreedores."""
    r = await calc.calculate(
        mods_bases={
            "envases": {"base": 1000, "tipo": 21},
            "concurso": {"base": 5000, "tipo": 21},
        },
    )
    info = r["modificaciones_bases"]
    assert info["total_base_modificaciones"] == 6000.0
    assert info["total_cuota_modificaciones"] == 1260.0  # 6000 * 0.21
    assert "envases" in info["desglose_modificaciones"]
    assert "concurso" in info["desglose_modificaciones"]


@pytest.mark.asyncio
async def test_mod_bases_se_suma_devengado(calc):
    """Cuota de modificaciones se suma al devengado total."""
    r = await calc.calculate(
        base_21=10000,  # devengado base = 2100
        mods_bases={"incobrables": {"base": 1000, "tipo": 21}},  # +210
    )
    assert r["casilla_27"] == 2310.0


@pytest.mark.asyncio
async def test_mod_bases_signed_negative(calc):
    """Modificaciones con base negativa (rectificacion en favor)."""
    r = await calc.calculate(
        mods_bases={"rappels_descuentos": {"base": -2000, "tipo": 21}},
    )
    info = r["modificaciones_bases"]
    assert info["total_cuota_modificaciones"] == -420.0


# =====================================================================
# Tipos transitorios 0% / 5% / 2% / 7.5%
# =====================================================================


@pytest.mark.asyncio
async def test_transitorios_2024_basicos_0(calc):
    """2024: productos basicos al 0% sigue vigente."""
    r = await calc.calculate(
        bases_transitorias={"base_0": 5000},
        year=2024,
        mes_inicio_periodo=3,
    )
    assert r["tipos_transitorios"]["cuota_0"] == 0.0
    assert r["tipos_transitorios"]["vigencia"]["tipo_0_vigente"] is True
    assert r["tipos_transitorios"]["warnings"] == []


@pytest.mark.asyncio
async def test_transitorios_2024_aceites_5_h1(calc):
    """2024 1er semestre: aceites/pasta al 5%."""
    r = await calc.calculate(
        bases_transitorias={"base_5": 2000},
        year=2024,
        mes_inicio_periodo=4,
    )
    assert r["tipos_transitorios"]["cuota_5"] == 100.0  # 2000 * 0.05
    assert r["tipos_transitorios"]["vigencia"]["tipo_5_vigente"] is True


@pytest.mark.asyncio
async def test_transitorios_2024_aceites_75_h2(calc):
    """2024 2do semestre: aceites al 7.5% (subida progresiva)."""
    r = await calc.calculate(
        bases_transitorias={"base_75": 2000},
        year=2024,
        mes_inicio_periodo=10,
    )
    assert r["tipos_transitorios"]["cuota_75"] == 150.0  # 2000 * 0.075
    assert r["tipos_transitorios"]["vigencia"]["tipo_75_vigente"] is True


@pytest.mark.asyncio
async def test_transitorios_2025_basicos_2(calc):
    """2025 ene-sept: basicos al 2%."""
    r = await calc.calculate(
        bases_transitorias={"base_2": 3000},
        year=2025,
        mes_inicio_periodo=4,
    )
    assert r["tipos_transitorios"]["cuota_2"] == 60.0  # 3000 * 0.02


@pytest.mark.asyncio
async def test_transitorios_2025_q4_no_vigente(calc):
    """2025 Q4 (oct+): tipos transitorios expirados, warning generado."""
    r = await calc.calculate(
        bases_transitorias={"base_2": 3000, "base_75": 2000},
        year=2025,
        mes_inicio_periodo=10,
    )
    assert r["tipos_transitorios"]["vigencia"]["tipo_2_vigente"] is False
    assert r["tipos_transitorios"]["vigencia"]["tipo_75_vigente"] is False
    assert len(r["tipos_transitorios"]["warnings"]) >= 2
    # cuotas calculan igual (informativo) pero hay warning
    assert any("2%" in w for w in r["tipos_transitorios"]["warnings"])


@pytest.mark.asyncio
async def test_transitorios_2026_todo_expirado(calc):
    """2026: ningun tipo transitorio vigente."""
    r = await calc.calculate(
        bases_transitorias={"base_0": 1000, "base_5": 500},
        year=2026,
    )
    vig = r["tipos_transitorios"]["vigencia"]
    assert vig["tipo_0_vigente"] is False
    assert vig["tipo_5_vigente"] is False
    assert vig["tipo_2_vigente"] is False
    assert vig["tipo_75_vigente"] is False


@pytest.mark.asyncio
async def test_transitorios_se_suman_devengado(calc):
    """Cuotas transitorias se suman a casilla 27."""
    r = await calc.calculate(
        base_21=10000,  # +2100
        bases_transitorias={"base_5": 2000},  # +100
        year=2024,
        mes_inicio_periodo=3,
    )
    assert r["casilla_27"] == 2200.0


# =====================================================================
# RE — Recargo Equivalencia detector ampliado
# =====================================================================


@pytest.mark.asyncio
async def test_re_detector_farmaceutico(calc):
    """Caso canonico farmaceutico (legacy)."""
    assert calc.is_recargo_equivalencia(situacion_laboral="farmaceutico") is True


@pytest.mark.asyncio
async def test_re_detector_cnae_minorista(calc):
    """CNAE 47.x persona fisica -> RE."""
    assert calc.is_recargo_equivalencia(cnae="47.71", es_persona_fisica=True) is True
    assert calc.is_recargo_equivalencia(cnae="47.21", es_persona_fisica=True) is True


@pytest.mark.asyncio
async def test_re_detector_cnae_vehiculos_excluido(calc):
    """CNAE 47.3 (vehiculos motor) NO esta en RE."""
    assert calc.is_recargo_equivalencia(cnae="47.30", es_persona_fisica=True) is False


@pytest.mark.asyncio
async def test_re_detector_iae_minorista(calc):
    """IAE 641-659 -> RE."""
    assert calc.is_recargo_equivalencia(iae="652.1", es_persona_fisica=True) is True
    assert calc.is_recargo_equivalencia(iae="641", es_persona_fisica=True) is True


@pytest.mark.asyncio
async def test_re_detector_persona_juridica_no(calc):
    """SL/SA nunca esta en RE."""
    assert calc.is_recargo_equivalencia(cnae="47.71", es_persona_fisica=False) is False


@pytest.mark.asyncio
async def test_re_strict_block_devuelve_bloqueo(calc):
    """Si re_strict_block=True y RE detectado -> respuesta de bloqueo."""
    r = await calc.calculate(
        base_21=10000,
        re_situacion_laboral="farmaceutico",
        re_strict_block=True,
    )
    assert r["bloqueo_re"] is True
    assert r["presenta_303"] is False
    assert "Recargo de Equivalencia" in r["mensaje"]
    assert "proveedor" in r["mensaje"].lower()
    # No deben existir casillas en respuesta de bloqueo
    assert "casilla_27" not in r


@pytest.mark.asyncio
async def test_re_sin_strict_block_calcula_pero_anota(calc):
    """Sin strict_block, calcula 303 normal pero anota detector RE."""
    r = await calc.calculate(
        base_21=10000,
        re_situacion_laboral="farmaceutico",
        re_strict_block=False,
    )
    assert "casilla_27" in r  # calcula normal
    assert r["recargo_equivalencia"]["detectado"] is True
    assert r["recargo_equivalencia"]["presenta_303"] is False


@pytest.mark.asyncio
async def test_re_rates_full_constants():
    """RE_RATES_FULL expone los tipos vigentes incluido 1.75% tabaco."""
    assert RE_RATES_FULL[21.0] == 5.2
    assert RE_RATES_FULL[10.0] == 1.4
    assert RE_RATES_FULL[4.0] == 0.5
    assert RE_RATES_FULL[1.75] == 1.75  # tabaco


# =====================================================================
# Integracion — combinaciones realistas
# =====================================================================


@pytest.mark.asyncio
async def test_integracion_recc_isp_mods(calc):
    """Caso real: RECC + ISP construccion + modificaciones."""
    r = await calc.calculate(
        base_21=20000,  # devengado base 4200
        cuota_corrientes_interiores=500,  # deducible base 500
        regimen_recc=True,
        volumen_ano_anterior=800_000,
        cobros_pendientes_recc=210,  # +210 devengado
        pagos_pendientes_recc=100,  # +100 deducible
        bases_isp={"construccion": {"base": 5000, "tipo": 21}},  # +1050 dev +1050 ded
        mods_bases={"envases": {"base": -500, "tipo": 21}},  # -105 devengado
    )
    # devengado = 4200 + 1050 (ISP) + (-105 mods) + 210 (RECC) = 5355
    assert r["casilla_27"] == 5355.0
    # deducible = 500 + 1050 (ISP ded) + 100 (RECC ded) = 1650
    assert r["casilla_45"] == 1650.0
    # neto = 5355 - 1650 = 3705
    assert r["resultado_liquidacion"] == 3705.0
    assert r["regimen_recc"]["regimen_aplicado"] is True


@pytest.mark.asyncio
async def test_integracion_warnings_aggregated(calc):
    """Warnings de RECC + SII + transitorios se agregan en r['warnings']."""
    r = await calc.calculate(
        base_21=1000,
        regimen_recc=True,
        volumen_ano_anterior=10_000_000,  # supera RECC y dispara SII
        bases_transitorias={"base_2": 100},
        year=2026,  # transitorios expirados
    )
    # Esperamos al menos 3 warnings: RECC inelegible + SII obligatorio + tipo 2% expirado
    assert len(r["warnings"]) >= 3


@pytest.mark.asyncio
async def test_backwards_compat_sin_nuevos_params(calc):
    """Sin nuevos parametros, output coincide con regresion previa."""
    r = await calc.calculate(base_21=10000, cuota_corrientes_interiores=500)
    # Mismo resultado que sesion 40 wave B4
    assert r["casilla_27"] == 2100.0
    assert r["casilla_45"] == 500.0
    assert r["resultado_liquidacion"] == 1600.0
    # Nuevas claves existen pero con defaults vacios
    assert r["regimen_recc"]["regimen_aplicado"] is False
    assert r["sii"]["aplicado"] is False
    assert r["isp_desglose"]["total_cuota_isp"] == 0.0
    assert r["modificaciones_bases"]["total_cuota_modificaciones"] == 0.0
    assert r["tipos_transitorios"]["cuota_total_transitorios"] == 0.0
    assert r["recargo_equivalencia"]["detectado"] is False
    assert r["warnings"] == []
