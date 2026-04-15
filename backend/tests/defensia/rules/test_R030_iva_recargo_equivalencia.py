"""Tests R030 — iva_recargo_equivalencia (T1B-030).

Dispara cuando AEAT regulariza IVA a un comerciante minorista PF o EARE
que deberia estar en regimen obligatorio de recargo de equivalencia.
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


_R030_MODULE_NAME = (
    "app.services.defensia_rules.reglas_otros_tributos.R030_iva_recargo_equivalencia"
)


def _cargar_solo_R030() -> None:
    reset_registry()
    if _R030_MODULE_NAME in sys.modules:
        importlib.reload(sys.modules[_R030_MODULE_NAME])
    else:
        importlib.import_module(_R030_MODULE_NAME)


@pytest.fixture(autouse=True)
def _recargar_R030():
    _cargar_solo_R030()
    yield


def _evaluar(exp, brief):
    modulo = sys.modules[_R030_MODULE_NAME]
    return modulo.evaluar(exp, brief)


# ---------------------------------------------------------------------------
# Positivos
# ---------------------------------------------------------------------------


def test_R030_positivo_persona_fisica_minorista_regularizada(
    build_exp, build_doc, build_brief
):
    """PF minorista regularizada fuera del recargo de equivalencia -> dispara."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "tipo_obligado": "persona_fisica_minorista",
            "aeat_regulariza_iva": True,
            "recargo_equivalencia_aplicado": False,
            "cumple_requisitos_minorista": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Soy minorista y me han regularizado IVA.")

    arg = _evaluar(exp, brief)
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R030"


def test_R030_positivo_eare_minorista(build_exp, build_doc, build_brief):
    """Entidad en atribucion de rentas minorista -> dispara."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "tipo_obligado": "entidad_atribucion_rentas_minorista",
            "aeat_regulariza_iva": True,
            "recargo_equivalencia_aplicado": False,
            "cumple_requisitos_minorista": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")

    arg = _evaluar(exp, brief)
    assert arg is not None
    assert arg.regla_id == "R030"


# ---------------------------------------------------------------------------
# Negativos
# ---------------------------------------------------------------------------


def test_R030_negativo_recargo_ya_aplicado(build_exp, build_doc, build_brief):
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "tipo_obligado": "persona_fisica_minorista",
            "aeat_regulariza_iva": True,
            "recargo_equivalencia_aplicado": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


def test_R030_negativo_no_cumple_requisitos_minorista(
    build_exp, build_doc, build_brief
):
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "tipo_obligado": "persona_fisica_minorista",
            "aeat_regulariza_iva": True,
            "recargo_equivalencia_aplicado": False,
            "cumple_requisitos_minorista": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


def test_R030_negativo_persona_juridica_no_eare(
    build_exp, build_doc, build_brief
):
    """R030 solo aplica a PF o EARE — sociedades limitadas quedan fuera."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "tipo_obligado": "sociedad_limitada",
            "aeat_regulariza_iva": True,
            "recargo_equivalencia_aplicado": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


# ---------------------------------------------------------------------------
# Anti-hardcode y registro
# ---------------------------------------------------------------------------


def test_R030_cita_es_semantica_no_hardcoded(
    build_exp, build_doc, build_brief
):
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "tipo_obligado": "persona_fisica_minorista",
            "aeat_regulariza_iva": True,
            "recargo_equivalencia_aplicado": False,
            "cumple_requisitos_minorista": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    arg = _evaluar(exp, brief)
    assert arg is not None
    cita = arg.cita_normativa_propuesta
    assert "Art. 148" not in cita
    assert "art. 163 liva" not in cita.lower()
    assert "148 a 163" not in cita
    assert len(cita) > 20


def test_R030_registrada_en_registry():
    assert "R030" in REGISTRY
    info = REGISTRY["R030"]
    assert "IVA" in info["tributos"]
    assert 0 <= len(REGISTRY) <= 30
