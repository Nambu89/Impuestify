"""Tests R027 — plusvalia_metodo_optimo (T1B-027).

La regla dispara cuando el Ayuntamiento liquida la plusvalia municipal por
el metodo objetivo con una cuota superior a la que resultaria de la
estimacion directa (diferencia entre valores de escritura), o cuando no se
ha ofrecido al contribuyente la opcion por el metodo que arroja menor cuota
pese a que el incremento real era calculable.

Base normativa (RAG verificador): art. 107.5 TRLHL tras RDL 26/2021 y STC
182/2021. La cita canonica la resuelve el RAG verificador, no la regla.

Patron de aislamiento: reset_registry + reload/import controlado.
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


_R027_MODULE_NAME = (
    "app.services.defensia_rules.reglas_otros_tributos.R027_plusvalia_metodo_optimo"
)


def _cargar_solo_R027() -> None:
    reset_registry()
    if _R027_MODULE_NAME in sys.modules:
        importlib.reload(sys.modules[_R027_MODULE_NAME])
    else:
        importlib.import_module(_R027_MODULE_NAME)


@pytest.fixture(autouse=True)
def _recargar_R027():
    _cargar_solo_R027()
    yield


def _evaluar(exp, brief):
    modulo = sys.modules[_R027_MODULE_NAME]
    return modulo.evaluar(exp, brief)


# ---------------------------------------------------------------------------
# Positivos
# ---------------------------------------------------------------------------


def test_R027_positivo_objetivo_superior_a_directa(
    build_exp, build_doc, build_brief
):
    """Metodo objetivo 3000 EUR, directa 1500 EUR -> dispara con ahorro 1500."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "cuota_metodo_objetivo": 3000,
            "cuota_metodo_directa": 1500,
            "metodo_aplicado": "objetivo",
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Liquidacion plusvalia metodo objetivo.")

    arg = _evaluar(exp, brief)
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R027"
    assert arg.datos_disparo.get("ahorro") == 1500


def test_R027_positivo_sin_opcion_directa_ofrecida(
    build_exp, build_doc, build_brief
):
    """Objetivo 3000, calculable, sin opcion ofrecida -> dispara."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "cuota_metodo_objetivo": 3000,
            "incremento_real_calculable": True,
            "opcion_directa_ofrecida": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")

    arg = _evaluar(exp, brief)
    assert arg is not None
    assert arg.regla_id == "R027"
    assert arg.datos_disparo.get("tipo") == "opcion_directa_no_ofrecida"


# ---------------------------------------------------------------------------
# Negativos
# ---------------------------------------------------------------------------


def test_R027_negativo_directa_mayor_o_igual(build_exp, build_doc, build_brief):
    """Cuota directa >= objetivo -> NO dispara (objetivo ya es optimo)."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "cuota_metodo_objetivo": 1500,
            "cuota_metodo_directa": 2000,
            "metodo_aplicado": "objetivo",
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


def test_R027_negativo_metodo_directa_ya_aplicado(
    build_exp, build_doc, build_brief
):
    """Si el metodo aplicado ya es 'directa', no hay conflicto."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "cuota_metodo_objetivo": 3000,
            "cuota_metodo_directa": 1500,
            "metodo_aplicado": "directa",
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


def test_R027_negativo_sin_datos_escritura(build_exp, build_doc, build_brief):
    """Sin cuota_metodo_directa y sin incremento_real_calculable -> NO dispara."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "cuota_metodo_objetivo": 3000,
            "incremento_real_calculable": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    assert _evaluar(exp, brief) is None


# ---------------------------------------------------------------------------
# Anti-hardcode y registro
# ---------------------------------------------------------------------------


def test_R027_cita_es_semantica_no_hardcoded(
    build_exp, build_doc, build_brief
):
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "cuota_metodo_objetivo": 3000,
            "cuota_metodo_directa": 1500,
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")
    arg = _evaluar(exp, brief)
    assert arg is not None
    cita = arg.cita_normativa_propuesta
    assert "Art. 107.5" not in cita
    assert "TRLHL" not in cita
    assert "STC 182/2021" not in cita
    assert "RDL 26/2021" not in cita
    assert len(cita) > 20


def test_R027_registrada_en_registry():
    assert "R027" in REGISTRY
    info = REGISTRY["R027"]
    assert "PLUSVALIA" in info["tributos"]
    assert 0 <= len(REGISTRY) <= 30
