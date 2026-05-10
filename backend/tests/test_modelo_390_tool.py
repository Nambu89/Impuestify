"""
Tests para `calculate_modelo_390_tool` (wrapper LLM).

Cubre:
    - Caso régimen general común <6M EUR → obligado, sumatorio 303.
    - Sujeto SII (>6M EUR) → exonerado.
    - Sujeto en REDEME → exonerado.
    - Sujeto en grupo IVA → exonerado.
    - Régimen simplificado / RE → exonerado.
    - Bizkaia → Modelo 391.
    - Navarra → F-66.
    - Canarias → 425.
    - Ceuta/Melilla → no aplica.
    - Validaciones (volumen negativo, trimestres incorrectos, restricted_mode).
"""
from __future__ import annotations

import pytest

from app.tools.modelo_390_tool import (
    MODELO_390_TOOL,
    calculate_modelo_390_tool,
)
from app.utils.calculators.modelo_390 import UMBRAL_SII_EUR


def _t303_dict(cuota_21=2100, deducible=500, resultado=1600):
    """Dict simulando salida de calculate_modelo_303_tool (formato anidado)."""
    return {
        "iva_devengado": {
            "cuota_21": cuota_21,
            "cuota_10": 0,
            "cuota_4": 0,
            "cuota_intracomunitaria": 0,
            "total_devengado": cuota_21,
        },
        "iva_deducible": {
            "bienes_corrientes": deducible,
            "bienes_inversion": 0,
            "importaciones": 0,
            "intracomunitarias": 0,
            "total_deducible": deducible,
        },
        "resultado": {"resultado_final": resultado},
    }


# ---------------------------------------------------------------------- #
# 1. Tool definition
# ---------------------------------------------------------------------- #


def test_tool_definition_estructura():
    assert MODELO_390_TOOL["type"] == "function"
    fn = MODELO_390_TOOL["function"]
    assert fn["name"] == "calculate_modelo_390"
    props = fn["parameters"]["properties"]
    # Parametros clave del audit
    assert "ccaa" in props
    assert "volumen_operaciones_ano_anterior" in props
    assert "en_redeme" in props
    assert "en_grupo_iva" in props
    assert "regimen_especial" in props
    assert "trimestres_303" in props


# ---------------------------------------------------------------------- #
# 2. Casos del audit
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_madrid_general_pequeno_obligado_con_sumatorio():
    """Madrid, régimen general <6M, con 4 trimestres → obligado y sumatorio."""
    trimestres = [_t303_dict()] * 4
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        year=2025,
        volumen_operaciones_ano_anterior=80_000,
        regimen_especial="general",
        trimestres_303=trimestres,
    )
    assert res["success"] is True
    assert res["obligado"] is True
    assert res["modelo"] == "390"
    assert res["resumen_anual"]["total_devengado_anual"] == 8400
    assert res["resumen_anual"]["resultado_liquidacion_anual"] == 6400
    assert "Modelo 390" in res["formatted_response"]
    assert "OBLIGADO" in res["formatted_response"]


@pytest.mark.asyncio
async def test_sujeto_sii_exonerado():
    """Volumen >6M EUR → SII obligatorio → exonerado del 390."""
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        volumen_operaciones_ano_anterior=10_000_000,
    )
    assert res["success"] is True
    assert res["obligado"] is False
    assert "EXONERADO" in res["formatted_response"]
    assert "SII" in res["formatted_response"]
    assert res["modelo"] == "390"  # El modelo aplicable es 390 (pero está exonerado)
    chequeos = [c["chequeo"] for c in res["exoneraciones_aplicables"]]
    assert "SII" in chequeos


@pytest.mark.asyncio
async def test_sujeto_redeme_exonerado():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        volumen_operaciones_ano_anterior=80_000,
        en_redeme=True,
    )
    assert res["obligado"] is False
    assert "REDEME" in res["formatted_response"]


@pytest.mark.asyncio
async def test_sujeto_grupo_iva_exonerado():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        en_grupo_iva=True,
    )
    assert res["obligado"] is False
    assert "grupo de IVA" in res["formatted_response"]


@pytest.mark.asyncio
async def test_regimen_recargo_equivalencia_exonerado():
    """Farmacéutico en RE: exonerado del 390 (caso clave)."""
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        regimen_especial="recargo_equivalencia",
    )
    assert res["obligado"] is False
    assert "Recargo de Equivalencia" in res["formatted_response"]


@pytest.mark.asyncio
async def test_regimen_simplificado_exonerado():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        regimen_especial="simplificado",
    )
    assert res["obligado"] is False
    assert "simplificado" in res["formatted_response"].lower()


@pytest.mark.asyncio
async def test_bizkaia_redirige_a_391():
    res = await calculate_modelo_390_tool(
        ccaa="Bizkaia",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["success"] is True
    assert res["modelo"] == "391"
    assert "Bizkaia" in res["formatted_response"]
    assert "Norma Foral" in res["formatted_response"]


@pytest.mark.asyncio
async def test_navarra_redirige_a_f66():
    res = await calculate_modelo_390_tool(
        ccaa="Navarra",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["modelo"] == "F-66"
    assert "F-66" in res["formatted_response"]


@pytest.mark.asyncio
async def test_canarias_redirige_a_425():
    res = await calculate_modelo_390_tool(
        ccaa="Canarias",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["modelo"] == "425"
    assert "Modelo 425" in res["formatted_response"]
    assert "IGIC" in res["formatted_response"]


@pytest.mark.asyncio
async def test_ceuta_no_aplica():
    res = await calculate_modelo_390_tool(ccaa="Ceuta")
    assert res["success"] is True
    assert res["obligado"] is False
    assert res["modelo"] is None
    assert "IPSI" in res["formatted_response"]


@pytest.mark.asyncio
async def test_melilla_no_aplica():
    res = await calculate_modelo_390_tool(ccaa="Melilla")
    assert res["modelo"] is None
    assert "IPSI" in res["formatted_response"]


# ---------------------------------------------------------------------- #
# 3. Validaciones
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_volumen_negativo_falla():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        volumen_operaciones_ano_anterior=-100,
    )
    assert res["success"] is False
    assert "negativo" in res["error"].lower()


@pytest.mark.asyncio
async def test_trimestres_no_lista_falla():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        trimestres_303={"not": "a list"},  # type: ignore
    )
    assert res["success"] is False
    assert "lista" in res["error"].lower() or "lista" in res["formatted_response"].lower()


@pytest.mark.asyncio
async def test_trimestres_count_incorrecto():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        trimestres_303=[_t303_dict(), _t303_dict()],  # solo 2
    )
    assert res["success"] is False
    assert "4" in res["formatted_response"]


@pytest.mark.asyncio
async def test_trimestres_lista_vacia_se_ignora():
    """Lista vacía = mismo comportamiento que None (sin sumatorio, no error)."""
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        volumen_operaciones_ano_anterior=80_000,
        trimestres_303=[],
    )
    assert res["success"] is True
    assert res["obligado"] is True
    assert res["resumen_anual"] is None


@pytest.mark.asyncio
async def test_restricted_mode_bloquea():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        restricted_mode=True,
    )
    assert res["success"] is False
    assert res["error"] == "restricted"


# ---------------------------------------------------------------------- #
# 4. Metadata y formato de respuesta
# ---------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_year_define_plazo_correctamente():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        year=2024,
    )
    assert "1 al 30 de enero de 2025" == res["plazo"]


@pytest.mark.asyncio
async def test_umbral_sii_expuesto_en_respuesta():
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["umbral_sii"] == UMBRAL_SII_EUR


@pytest.mark.asyncio
async def test_normaliza_alias_ccaa():
    """Frontend manda 'cataluna' sin tilde, debe normalizar a Cataluña."""
    res = await calculate_modelo_390_tool(
        ccaa="cataluna",
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["success"] is True
    assert res["modelo"] == "390"
    assert res["territory_info"]["territory"] == "Cataluña"


@pytest.mark.asyncio
async def test_sin_ccaa_default_comun():
    """Sin CCAA → régimen común (390 AEAT)."""
    res = await calculate_modelo_390_tool(
        volumen_operaciones_ano_anterior=80_000,
    )
    assert res["success"] is True
    assert res["modelo"] == "390"
    assert "AEAT" in res["hacienda"]


@pytest.mark.asyncio
async def test_acepta_formato_303_plano():
    """Formato plano (casilla_03/06/09/27/45/...) también funciona."""
    t_plano = {
        "casilla_03": 0,
        "casilla_06": 0,
        "casilla_09": 2100,
        "casilla_12": 0,
        "casilla_14": 0,
        "casilla_27": 2100,
        "casilla_29": 500,
        "casilla_31": 0,
        "casilla_33": 0,
        "casilla_37": 0,
        "casilla_45": 500,
        "resultado_liquidacion": 1600,
    }
    res = await calculate_modelo_390_tool(
        ccaa="Madrid",
        volumen_operaciones_ano_anterior=80_000,
        trimestres_303=[t_plano] * 4,
    )
    assert res["success"] is True
    assert res["resumen_anual"]["total_devengado_anual"] == 8400
    assert res["resumen_anual"]["resultado_liquidacion_anual"] == 6400
