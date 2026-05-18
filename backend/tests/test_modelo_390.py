"""
Tests para Modelo390Calculator.

Cubre:
    - Sumatorio anual de 4 modelos 303 (T1+T2+T3+T4)
    - Detección automática exoneración (Art. 71.7 RIVA):
        * SII por volumen > 6.010.121,04 EUR
        * SII voluntario
        * REDEME
        * Grupos IVA
        * Régimen simplificado / recargo de equivalencia exclusivos
    - Variantes territoriales (390 / 391 / F-66 / 425 / IPSI)
    - Validación completa (validate_complete)
    - Robustez del lookup en build_from_303_quarterly
"""

import pytest

from app.utils.calculators.modelo_390 import (
    Modelo390Calculator,
    UMBRAL_SII_EUR,
)


@pytest.fixture
def calc():
    return Modelo390Calculator(None)


# ---------------------------------------------------------------------- #
# 1. Variante territorial
# ---------------------------------------------------------------------- #


def test_variante_comun_sin_territorio():
    info = Modelo390Calculator.get_variante_territorial(None)
    assert info["modelo"] == "390"
    assert info["aplica_iva"] is True
    assert "AEAT" in info["hacienda"]


def test_variante_madrid_es_390():
    info = Modelo390Calculator.get_variante_territorial("Madrid")
    assert info["modelo"] == "390"
    assert info["aplica_iva"] is True
    assert info["territory"] == "Madrid"


def test_variante_canarias_es_425():
    info = Modelo390Calculator.get_variante_territorial("Canarias")
    assert info["modelo"] == "425"
    assert info["aplica_iva"] is False
    assert "Canarias" in info["hacienda"] or "canaria" in info["hacienda"].lower()


def test_variante_bizkaia_es_391():
    info = Modelo390Calculator.get_variante_territorial("Bizkaia")
    assert info["modelo"] == "391"
    assert "Bizkaia" in info["hacienda"]
    assert "Norma Foral" in info["nota"]


def test_variante_araba_es_391():
    info = Modelo390Calculator.get_variante_territorial("Araba")
    assert info["modelo"] == "391"
    assert "Araba" in info["hacienda"]


def test_variante_gipuzkoa_es_391():
    info = Modelo390Calculator.get_variante_territorial("Gipuzkoa")
    assert info["modelo"] == "391"
    assert "Gipuzkoa" in info["hacienda"]


def test_variante_navarra_es_f66():
    info = Modelo390Calculator.get_variante_territorial("Navarra")
    assert info["modelo"] == "F-66"
    assert "Navarra" in info["hacienda"]


def test_variante_ceuta_no_aplica():
    info = Modelo390Calculator.get_variante_territorial("Ceuta")
    assert info["modelo"] is None
    assert info["aplica_iva"] is False
    assert "IPSI" in info["nota"]


def test_variante_melilla_no_aplica():
    info = Modelo390Calculator.get_variante_territorial("Melilla")
    assert info["modelo"] is None
    assert info["aplica_iva"] is False
    assert "IPSI" in info["nota"]


def test_variante_normaliza_alias():
    """Frontend puede mandar 'Cataluna' sin tilde — se normaliza."""
    info = Modelo390Calculator.get_variante_territorial("Cataluna")
    assert info["modelo"] == "390"
    assert info["territory"] == "Cataluña"


# ---------------------------------------------------------------------- #
# 2. Exoneración SII (Art. 71.7 RIVA)
# ---------------------------------------------------------------------- #


def test_sii_volumen_supera_umbral():
    res = Modelo390Calculator.check_exoneracion_sii(
        volumen_operaciones_ano_anterior=UMBRAL_SII_EUR + 1
    )
    assert res["exonerado"] is True
    assert "SII" in res["motivo"]
    assert res["umbral"] == UMBRAL_SII_EUR


def test_sii_volumen_justo_por_debajo():
    res = Modelo390Calculator.check_exoneracion_sii(volumen_operaciones_ano_anterior=UMBRAL_SII_EUR)
    # > umbral, no >= → no exonerado en el límite exacto
    assert res["exonerado"] is False


def test_sii_voluntario():
    res = Modelo390Calculator.check_exoneracion_sii(
        volumen_operaciones_ano_anterior=10_000,
        sii_voluntario=True,
    )
    assert res["exonerado"] is True
    assert "voluntariamente" in res["motivo"].lower()


def test_sii_volumen_bajo_no_exonera():
    res = Modelo390Calculator.check_exoneracion_sii(volumen_operaciones_ano_anterior=50_000)
    assert res["exonerado"] is False


# ---------------------------------------------------------------------- #
# 3. Otros chequeos individuales
# ---------------------------------------------------------------------- #


def test_redeme_exonera():
    res = Modelo390Calculator.check_redeme(en_redeme=True)
    assert res["exonerado"] is True
    assert "REDEME" in res["motivo"]


def test_redeme_no_exonera_si_false():
    res = Modelo390Calculator.check_redeme(en_redeme=False)
    assert res["exonerado"] is False


def test_grupo_iva_exonera():
    res = Modelo390Calculator.check_grupo_iva(en_grupo_iva=True)
    assert res["exonerado"] is True
    assert "grupo de IVA" in res["motivo"]


def test_simplificado_exonera():
    res = Modelo390Calculator.check_regimen_especial_exclusivo("simplificado")
    assert res["exonerado"] is True
    assert "simplificado" in res["motivo"]


def test_recargo_equivalencia_exonera():
    res = Modelo390Calculator.check_regimen_especial_exclusivo("recargo_equivalencia")
    assert res["exonerado"] is True
    assert "Recargo de Equivalencia" in res["motivo"]


def test_regimen_general_no_exonera():
    res = Modelo390Calculator.check_regimen_especial_exclusivo("general")
    assert res["exonerado"] is False


def test_regimen_none_no_exonera():
    res = Modelo390Calculator.check_regimen_especial_exclusivo(None)
    assert res["exonerado"] is False


# ---------------------------------------------------------------------- #
# 4. validate_complete — orquestación
# ---------------------------------------------------------------------- #


def test_validate_obligado_madrid_general_pequeno():
    res = Modelo390Calculator.validate_complete(
        territory="Madrid",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["obligado"] is True
    assert res["modelo"] == "390"
    assert res["motivo_exoneracion"] == ""


def test_validate_exonerado_sii():
    res = Modelo390Calculator.validate_complete(
        territory="Madrid",
        volumen_operaciones_ano_anterior=10_000_000,
    )
    assert res["obligado"] is False
    assert res["modelo"] == "390"
    assert "SII" in res["motivo_exoneracion"]
    assert any(c["chequeo"] == "SII" for c in res["exoneraciones_aplicables"])


def test_validate_exonerado_redeme():
    res = Modelo390Calculator.validate_complete(
        territory="Madrid",
        volumen_operaciones_ano_anterior=80_000,
        en_redeme=True,
    )
    assert res["obligado"] is False
    assert "REDEME" in res["motivo_exoneracion"]


def test_validate_exonerado_recargo_equivalencia():
    res = Modelo390Calculator.validate_complete(
        territory="Madrid",
        regimen_especial="recargo_equivalencia",
    )
    assert res["obligado"] is False
    assert "Recargo de Equivalencia" in res["motivo_exoneracion"]


def test_validate_canarias_redirige_a_425():
    res = Modelo390Calculator.validate_complete(
        territory="Canarias",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["modelo"] == "425"
    # Canarias se considera "obligado" pero al 425 no al 390
    assert res["obligado"] is True


def test_validate_ceuta_no_aplica():
    res = Modelo390Calculator.validate_complete(territory="Ceuta")
    assert res["obligado"] is False
    assert res["modelo"] is None
    assert "IPSI" in res["motivo_exoneracion"]


def test_validate_bizkaia_obligado_a_391():
    res = Modelo390Calculator.validate_complete(
        territory="Bizkaia",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["obligado"] is True
    assert res["modelo"] == "391"


def test_validate_navarra_obligado_a_f66():
    res = Modelo390Calculator.validate_complete(
        territory="Navarra",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["obligado"] is True
    assert res["modelo"] == "F-66"


def test_validate_multiples_exoneraciones_se_acumulan():
    """Si SII + REDEME + grupo aplican a la vez, todos se listan."""
    res = Modelo390Calculator.validate_complete(
        territory="Madrid",
        volumen_operaciones_ano_anterior=10_000_000,
        en_redeme=True,
        en_grupo_iva=True,
    )
    assert res["obligado"] is False
    chequeos = [c["chequeo"] for c in res["exoneraciones_aplicables"]]
    assert "SII" in chequeos
    assert "REDEME" in chequeos
    assert "Grupo IVA" in chequeos


# ---------------------------------------------------------------------- #
# 5. Sumatorio anual a partir de 4 modelos 303
# ---------------------------------------------------------------------- #


def _t303(
    cuota_21=0,
    cuota_10=0,
    cuota_4=0,
    intra=0,
    isp=0,
    deducible_corr=0,
    deducible_inv=0,
    deducible_imp=0,
    deducible_intra=0,
    resultado=0,
):
    """Construye un dict simulando salida de Modelo303Calculator (formato plano)."""
    total_dev = cuota_4 + cuota_10 + cuota_21 + intra + isp
    total_ded = deducible_corr + deducible_inv + deducible_imp + deducible_intra
    return {
        "casilla_03": cuota_4,
        "casilla_06": cuota_10,
        "casilla_09": cuota_21,
        "casilla_12": intra,
        "casilla_14": isp,
        "casilla_27": total_dev,
        "casilla_29": deducible_corr,
        "casilla_31": deducible_inv,
        "casilla_33": deducible_imp,
        "casilla_37": deducible_intra,
        "casilla_45": total_ded,
        "resultado_liquidacion": resultado,
    }


def test_build_4_trimestres_iguales():
    """4 trimestres iguales: total = 4× cada concepto."""
    t = _t303(cuota_21=2100, deducible_corr=500, resultado=1600)
    res = Modelo390Calculator.build_from_303_quarterly([t, t, t, t])
    assert res["cuota_devengada_21"] == 8400
    assert res["cuota_deducible_corrientes"] == 2000
    assert res["total_devengado_anual"] == 8400
    assert res["total_deducible_anual"] == 2000
    assert res["resultado_liquidacion_anual"] == 6400
    assert len(res["sumatorio_303"]) == 4


def test_build_trimestres_distintos():
    """Caso real: 4 trimestres con montos distintos."""
    t1 = _t303(cuota_21=1000, deducible_corr=200, resultado=800)
    t2 = _t303(cuota_21=1500, cuota_10=300, deducible_corr=400, resultado=1400)
    t3 = _t303(cuota_21=2000, deducible_corr=600, deducible_inv=500, resultado=900)
    t4 = _t303(cuota_21=2500, cuota_4=80, deducible_corr=800, resultado=1780)
    res = Modelo390Calculator.build_from_303_quarterly([t1, t2, t3, t4])
    assert res["cuota_devengada_21"] == 7000
    assert res["cuota_devengada_10"] == 300
    assert res["cuota_devengada_4"] == 80
    assert res["cuota_deducible_corrientes"] == 2000
    assert res["cuota_deducible_inversion"] == 500
    assert res["resultado_liquidacion_anual"] == 4880  # 800+1400+900+1780


def test_build_acepta_formato_tool():
    """Acepta también la salida del tool calculate_modelo_303_tool (anidada)."""
    t_tool = {
        "iva_devengado": {
            "cuota_21": 2100,
            "cuota_10": 0,
            "cuota_4": 0,
            "cuota_intracomunitaria": 0,
            "total_devengado": 2100,
        },
        "iva_deducible": {
            "bienes_corrientes": 500,
            "bienes_inversion": 0,
            "importaciones": 0,
            "intracomunitarias": 0,
            "total_deducible": 500,
        },
        "resultado": {"resultado_final": 1600},
    }
    res = Modelo390Calculator.build_from_303_quarterly([t_tool] * 4)
    assert res["cuota_devengada_21"] == 8400
    assert res["cuota_deducible_corrientes"] == 2000
    assert res["resultado_liquidacion_anual"] == 6400


def test_build_intracomunitarias_e_isp():
    t = _t303(cuota_21=2100, intra=1050, isp=420, resultado=3570)
    res = Modelo390Calculator.build_from_303_quarterly([t, t, t, t])
    assert res["cuota_devengada_intra"] == 4200
    assert res["cuota_devengada_isp"] == 1680
    assert res["total_devengado_anual"] == (2100 + 1050 + 420) * 4


def test_build_falla_si_no_4_trimestres():
    with pytest.raises(ValueError):
        Modelo390Calculator.build_from_303_quarterly([_t303(), _t303()])


def test_build_falla_si_no_es_lista():
    with pytest.raises(ValueError):
        Modelo390Calculator.build_from_303_quarterly("not a list")  # type: ignore


# ---------------------------------------------------------------------- #
# 6. calculate (API principal)
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_calculate_obligado_con_303(calc):
    t = _t303(cuota_21=2100, deducible_corr=500, resultado=1600)
    res = await calc.calculate(
        trimestres_303=[t, t, t, t],
        territory="Madrid",
        volumen_operaciones_ano_anterior=80_000,
        year=2025,
    )
    assert res["obligado"] is True
    assert res["modelo"] == "390"
    assert res["resumen_anual"] is not None
    assert res["resumen_anual"]["resultado_liquidacion_anual"] == 6400
    assert "1 al 30 de enero de 2026" == res["plazo"]


@pytest.mark.asyncio
async def test_calculate_exonerado_sii_no_calcula_sumatorio(calc):
    """Si está exonerado, no calcula el sumatorio aunque se pasen los 4 303."""
    t = _t303(cuota_21=2100, resultado=1600)
    res = await calc.calculate(
        trimestres_303=[t, t, t, t],
        territory="Madrid",
        volumen_operaciones_ano_anterior=10_000_000,
    )
    assert res["obligado"] is False
    assert res["resumen_anual"] is None
    assert "SII" in res["motivo_exoneracion"]


@pytest.mark.asyncio
async def test_calculate_canarias_redirige_a_425(calc):
    res = await calc.calculate(
        territory="Canarias",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["modelo"] == "425"
    assert res["resumen_anual"] is None  # No calculamos 425 aquí (vive en 420 calc)


@pytest.mark.asyncio
async def test_calculate_ceuta_no_aplica(calc):
    res = await calc.calculate(territory="Ceuta")
    assert res["obligado"] is False
    assert res["modelo"] is None
    assert "IPSI" in res["motivo_exoneracion"]


@pytest.mark.asyncio
async def test_calculate_bizkaia_obligado_sin_303(calc):
    """Sin trimestres pasados: devuelve metadata de obligación pero sin sumatorio."""
    res = await calc.calculate(
        territory="Bizkaia",
        volumen_operaciones_ano_anterior=80_000,
        year=2025,
    )
    assert res["obligado"] is True
    assert res["modelo"] == "391"
    assert res["resumen_anual"] is None
    assert "Bizkaia" in res["hacienda"]


@pytest.mark.asyncio
async def test_calculate_navarra_obligado(calc):
    res = await calc.calculate(
        territory="Navarra",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["modelo"] == "F-66"
    assert res["obligado"] is True


@pytest.mark.asyncio
async def test_calculate_recargo_equivalencia_exonerado(calc):
    """Farmacéutico en RE: exonerado del 390."""
    res = await calc.calculate(
        territory="Madrid",
        regimen_especial="recargo_equivalencia",
    )
    assert res["obligado"] is False
    assert "Recargo de Equivalencia" in res["motivo_exoneracion"]


@pytest.mark.asyncio
async def test_calculate_simplificado_exonerado(calc):
    res = await calc.calculate(
        territory="Madrid",
        regimen_especial="simplificado",
    )
    assert res["obligado"] is False
    assert "simplificado" in res["motivo_exoneracion"]


@pytest.mark.asyncio
async def test_calculate_grupo_iva_exonerado(calc):
    res = await calc.calculate(
        territory="Madrid",
        en_grupo_iva=True,
    )
    assert res["obligado"] is False
    assert "grupo de IVA" in res["motivo_exoneracion"]


@pytest.mark.asyncio
async def test_calculate_year_define_plazo(calc):
    res = await calc.calculate(territory="Madrid", year=2024)
    assert res["plazo"] == "1 al 30 de enero de 2025"


@pytest.mark.asyncio
async def test_calculate_obligado_sin_303_no_crashea(calc):
    """Sujeto obligado sin pasar trimestres: devuelve metadata sin error."""
    res = await calc.calculate(
        territory="Madrid",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["obligado"] is True
    assert res["resumen_anual"] is None
