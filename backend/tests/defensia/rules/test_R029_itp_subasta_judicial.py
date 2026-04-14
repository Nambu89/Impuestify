"""Tests R029 — itp_base_imponible_subasta_judicial (T1B-029).

La regla dispara cuando la liquidacion ITP sobre un inmueble adjudicado en
subasta judicial o ejecucion hipotecaria aplica el valor de referencia
catastral como base imponible en lugar del precio de remate efectivamente
pagado (doctrina TS consolidada).
"""
from __future__ import annotations

import importlib
import sys

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import REGISTRY, reset_registry


_R029_MODULE_NAME = (
    "app.services.defensia_rules.reglas_otros_tributos.R029_itp_subasta_judicial"
)


def _cargar_solo_R029() -> None:
    reset_registry()
    if _R029_MODULE_NAME in sys.modules:
        importlib.reload(sys.modules[_R029_MODULE_NAME])
    else:
        importlib.import_module(_R029_MODULE_NAME)


@pytest.fixture(autouse=True)
def _recargar_R029():
    _cargar_solo_R029()
    yield


def _evaluar(exp, brief):
    modulo = sys.modules[_R029_MODULE_NAME]
    return modulo.evaluar(exp, brief)


# ---------------------------------------------------------------------------
# Positivos
# ---------------------------------------------------------------------------


def test_R029_positivo_subasta_judicial_valor_referencia(
    build_exp, build_doc, build_brief
):
    """Subasta judicial con precio remate 150.000 y base aplicada 220.000."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "origen_adquisicion": "subasta_judicial",
            "precio_remate": 150000,
            "base_imponible_aplicada_por_aeat": 220000,
            "valor_referencia_usado": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Adquiri el piso en subasta judicial.")

    arg = _evaluar(exp, brief)
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R029"
    assert arg.datos_disparo.get("diferencia") == 70000


def test_R029_positivo_ejecucion_hipotecaria(
    build_exp, build_doc, build_brief
):
    """Ejecucion hipotecaria con precio remate < base aplicada."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "origen_adquisicion": "ejecucion_hipotecaria",
            "precio_remate": 120000,
            "base_imponible_aplicada_por_aeat": 200000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")

    arg = _evaluar(exp, brief)
    assert arg is not None
    assert arg.regla_id == "R029"


# ---------------------------------------------------------------------------
# Negativos
# ---------------------------------------------------------------------------


def test_R029_negativo_compraventa_ordinaria(build_exp, build_doc, build_brief):
    """Origen compraventa ordinaria -> R029 no aplica (la defensa es R025)."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "origen_adquisicion": "compraventa_ordinaria",
            "precio_remate": 150000,
            "base_imponible_aplicada_por_aeat": 220000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


def test_R029_negativo_base_igual_precio_remate(
    build_exp, build_doc, build_brief
):
    """Base aplicada == precio remate -> NO dispara."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "origen_adquisicion": "subasta_judicial",
            "precio_remate": 150000,
            "base_imponible_aplicada_por_aeat": 150000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


def test_R029_negativo_tributo_no_itp(build_exp, build_doc, build_brief):
    """Tributo distinto de ITP -> NO dispara."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IRPF",
            "origen_adquisicion": "subasta_judicial",
            "precio_remate": 150000,
            "base_imponible_aplicada_por_aeat": 220000,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


# ---------------------------------------------------------------------------
# Anti-hardcode y registro
# ---------------------------------------------------------------------------


def test_R029_cita_es_semantica_no_hardcoded(
    build_exp, build_doc, build_brief
):
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "origen_adquisicion": "subasta_judicial",
            "precio_remate": 100000,
            "base_imponible_aplicada_por_aeat": 180000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    arg = _evaluar(exp, brief)
    assert arg is not None
    cita = arg.cita_normativa_propuesta
    assert "Art. 10" not in cita
    assert "TRLITPAJD" not in cita
    assert "STS" not in cita
    assert len(cita) > 20


def test_R029_registrada_en_registry():
    assert "R029" in REGISTRY
    info = REGISTRY["R029"]
    assert "ITP" in info["tributos"]
    assert 0 <= len(REGISTRY) <= 30
