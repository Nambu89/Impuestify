"""Tests para R005 — principio de integra regularizacion (T1B-005).

La regla dispara cuando la AEAT regulariza un concepto sin computar ajustes
positivos derivados del mismo hecho imponible, violando el principio de
integra regularizacion consolidado por el Tribunal Supremo y el TEAC.

CRITICO — riesgo_alucinacion=MEDIO. La cita canonica especifica (STS 2024,
TEAC RG 5642/2022, TEAC RG 3226/2023) NO se hardcodea en la regla — el RAG
verificador la resuelve contra el corpus. La regla solo emite una cita
semantica generica.
"""
from __future__ import annotations

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules.reglas_procedimentales.R005_integra_regularizacion import (
    evaluar as evaluar_r005,
)


# ---------------------------------------------------------------------------
# Positivos
# ---------------------------------------------------------------------------


def test_R005_dispara_cuando_deniega_beneficio_sin_ajustes_compensatorios(
    build_exp, build_brief, build_doc,
):
    """AEAT niega exencion/deduccion sin aplicar coeficientes reductores ni
    ajustar pagos a cuenta derivados del mismo hecho -> dispara R005.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_beneficio": True,
            "ajustes_compensatorios_aplicados": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("AEAT me ha negado la exencion sin aplicar coeficientes reductores.")

    resultado = evaluar_r005(exp, brief)

    assert resultado is not None, "R005 debe disparar cuando hay denegacion sin ajustes"
    assert isinstance(resultado, ArgumentoCandidato)
    assert resultado.regla_id == "R005"
    # Cita semantica — NUNCA hardcodear STS/TEAC/RG.
    cita = resultado.cita_normativa_propuesta.lower()
    assert "integra regularizacion" in cita or "integra regularización" in cita, (
        "La cita debe referirse al principio de integra regularizacion"
    )
    # Prohibiciones explicitas de hardcoding (invariante #2 anti-alucinacion).
    prohibidos = ["sts 2024", "rg 5642", "rg 3226", "teac rg", "sentencia"]
    for prohibido in prohibidos:
        assert prohibido not in cita, (
            f"La cita no debe hardcodear referencias jurisprudenciales concretas: '{prohibido}'"
        )
    assert resultado.datos_disparo.get("riesgo_alucinacion") == "MEDIO"


def test_R005_dispara_cuando_iva_soportado_rechazado_sin_permitir_rectificar(
    build_exp, build_brief, build_doc,
):
    """En IVA: AEAT rechaza IVA soportado sin permitir rectificar el IVA
    repercutido correlativo -> dispara R005 (caso paradigmatico STS IVA).
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "iva_soportado_rechazado": True,
            "permite_rectificar_repercutido": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Han rechazado el IVA soportado pero no dejan rectificar el repercutido.")

    resultado = evaluar_r005(exp, brief)

    assert resultado is not None, "R005 debe disparar en IVA soportado rechazado sin rectificacion"
    assert resultado.regla_id == "R005"
    cita = resultado.cita_normativa_propuesta.lower()
    assert "integra regularizacion" in cita or "integra regularización" in cita
    assert resultado.datos_disparo.get("riesgo_alucinacion") == "MEDIO"


# ---------------------------------------------------------------------------
# Negativos
# ---------------------------------------------------------------------------


def test_R005_no_dispara_cuando_regularizacion_es_completa(
    build_exp, build_brief, build_doc,
):
    """Si AEAT ya aplico los ajustes compensatorios favorables, el principio
    de integra regularizacion esta cumplido -> NO dispara.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_beneficio": True,
            "ajustes_compensatorios_aplicados": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("AEAT aplico correctamente los coeficientes reductores.")

    resultado = evaluar_r005(exp, brief)

    assert resultado is None, (
        "R005 no debe disparar cuando la regularizacion ya incluye ajustes favorables"
    )


def test_R005_no_dispara_sin_regularizacion_a_favor_posible(
    build_exp, build_brief, build_doc,
):
    """Si no hay denegacion de beneficio ni IVA soportado rechazado, no hay
    hecho del que derivar ajustes compensatorios -> NO dispara.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_beneficio": False,
            "ajustes_compensatorios_aplicados": False,
            "iva_soportado_rechazado": False,
            "permite_rectificar_repercutido": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Me han notificado una liquidacion sin regularizacion a favor.")

    resultado = evaluar_r005(exp, brief)

    assert resultado is None, (
        "R005 no debe disparar cuando no hay base para la regularizacion a favor"
    )
