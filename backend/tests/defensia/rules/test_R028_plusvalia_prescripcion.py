"""Tests de la regla R028 — plusvalia_prescripcion_o_notificacion (T1B-028).

Base normativa: arts. 66-68 LGT aplicables a tributos locales por remision del
art. 12 TRLHL (Real Decreto Legislativo 2/2004). La STS de 28-2-2024 (Sala 3.ª)
admite incluso la nulidad de liquidaciones de plusvalia firmes dictadas fuera
del plazo de 4 anos desde el devengo.

La regla dispara cuando el Ayuntamiento notifica una liquidacion de plusvalia
municipal (IIVTNU) mas de 4 anos despues del devengo del impuesto (fecha de
fallecimiento en transmisiones mortis causa o fecha de escritura/contrato en
transmisiones inter vivos) sin que haya existido una interrupcion valida del
plazo de prescripcion.

Patron de aislamiento: se recarga unicamente el modulo de R028 antes de cada
test para garantizar que el REGISTRY contiene solo esta regla y que ningun
side-effect de otros tests contamina el resultado.
"""
from __future__ import annotations

import importlib
import sys
from datetime import datetime, timezone

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import REGISTRY, reset_registry


# ---------------------------------------------------------------------------
# Patron de aislamiento: cargar solo R028
# ---------------------------------------------------------------------------

def _cargar_solo_R028() -> None:
    """Recarga unicamente el modulo de R028 para aislar el test del REGISTRY.

    El fixture `_aislar_registry` del conftest ya limpia el REGISTRY antes y
    despues de cada test, pero aqui ademas forzamos la reimportacion del modulo
    para que el decorador ``@regla`` vuelva a registrar la regla en el registry
    recien reseteado (de lo contrario, al ser un import cacheado, el decorador
    no se re-ejecutaria).
    """
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_otros_tributos."
        "R028_plusvalia_prescripcion"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture
def r028_module():
    """Carga R028 de forma aislada y devuelve el modulo importado."""
    _cargar_solo_R028()
    module_name = (
        "app.services.defensia_rules.reglas_otros_tributos."
        "R028_plusvalia_prescripcion"
    )
    return sys.modules[module_name]


# ---------------------------------------------------------------------------
# Positivos
# ---------------------------------------------------------------------------

def test_r028_positivo_liquidacion_2026_sobre_devengo_2021(
    r028_module, build_exp, build_doc, build_brief
):
    """Devengo 2021-03-15, liquidacion notificada 2026-04-01 -> dispara.

    Transcurridos 5 anos desde el devengo, sin acto interruptivo valido.
    Los datos de disparo deben exponer `anos_transcurridos = 5`.
    """
    doc_liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "fecha_devengo": "2021-03-15",
            "fecha_notificacion_liquidacion": "2026-04-01",
            "hubo_interrupcion": False,
        },
        fecha_acto=datetime(2026, 4, 1, tzinfo=timezone.utc),
        doc_id="liq-plusvalia-2026",
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_liquidacion],
    )
    brief = build_brief(
        "El ayuntamiento me liquida ahora una plusvalia de hace 5 anos"
    )

    resultado = r028_module.evaluar(exp, brief)

    assert resultado is not None
    assert isinstance(resultado, ArgumentoCandidato)
    assert resultado.regla_id == "R028"
    assert "anos_transcurridos" in resultado.datos_disparo
    assert resultado.datos_disparo["anos_transcurridos"] == 5


def test_r028_positivo_limite_4_anos_mas_un_dia(
    r028_module, build_exp, build_doc, build_brief
):
    """Devengo 2020-04-01, notificacion 2024-04-02 -> dispara.

    Exactamente 4 anos y 1 dia desde el devengo: fuera del plazo de 4 anos
    computado de fecha a fecha, por lo tanto el derecho a liquidar ha prescrito.
    """
    doc_liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "fecha_devengo": "2020-04-01",
            "fecha_notificacion_liquidacion": "2024-04-02",
            "hubo_interrupcion": False,
        },
        fecha_acto=datetime(2024, 4, 2, tzinfo=timezone.utc),
        doc_id="liq-plusvalia-limite",
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_liquidacion],
    )
    brief = build_brief("")

    resultado = r028_module.evaluar(exp, brief)

    assert resultado is not None
    assert resultado.regla_id == "R028"


# ---------------------------------------------------------------------------
# Negativos
# ---------------------------------------------------------------------------

def test_r028_negativo_dentro_del_plazo(
    r028_module, build_exp, build_doc, build_brief
):
    """Devengo 2023-01-01, notificacion 2025-06-01 -> NO dispara.

    Aproximadamente 2,5 anos, claramente dentro del plazo de 4 anos.
    """
    doc_liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "fecha_devengo": "2023-01-01",
            "fecha_notificacion_liquidacion": "2025-06-01",
            "hubo_interrupcion": False,
        },
        fecha_acto=datetime(2025, 6, 1, tzinfo=timezone.utc),
        doc_id="liq-plusvalia-dentro",
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_liquidacion],
    )
    brief = build_brief("")

    resultado = r028_module.evaluar(exp, brief)

    assert resultado is None


def test_r028_negativo_interrupcion_previa(
    r028_module, build_exp, build_doc, build_brief
):
    """Aunque los 4 anos hayan transcurrido, `hubo_interrupcion=True` evita disparo."""
    doc_liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "fecha_devengo": "2020-01-01",
            "fecha_notificacion_liquidacion": "2026-01-02",
            "hubo_interrupcion": True,
        },
        fecha_acto=datetime(2026, 1, 2, tzinfo=timezone.utc),
        doc_id="liq-plusvalia-interrumpida",
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_liquidacion],
    )
    brief = build_brief("")

    resultado = r028_module.evaluar(exp, brief)

    assert resultado is None


def test_r028_negativo_tributo_no_plusvalia(
    r028_module, build_exp, build_doc, build_brief
):
    """La regla no debe disparar si el tributo del expediente no es PLUSVALIA."""
    doc_liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IRPF",
            "fecha_devengo": "2020-01-01",
            "fecha_notificacion_liquidacion": "2026-01-02",
            "hubo_interrupcion": False,
        },
        fecha_acto=datetime(2026, 1, 2, tzinfo=timezone.utc),
        doc_id="liq-irpf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_liquidacion],
    )
    brief = build_brief("")

    resultado = r028_module.evaluar(exp, brief)

    assert resultado is None


# ---------------------------------------------------------------------------
# Anti-hardcode
# ---------------------------------------------------------------------------

def test_r028_cita_no_hardcoded(
    r028_module, build_exp, build_doc, build_brief
):
    """La cita normativa debe ser SEMANTICA, no hardcoded con textos legales.

    El RAG verificador es quien proporcionara la cita verbatim en Parte 2. La
    regla solo debe describir el concepto juridico, sin arrastrar numeros de
    articulo ni referencias legislativas hardcoded.
    """
    doc_liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "fecha_devengo": "2021-03-15",
            "fecha_notificacion_liquidacion": "2026-04-01",
            "hubo_interrupcion": False,
        },
        fecha_acto=datetime(2026, 4, 1, tzinfo=timezone.utc),
        doc_id="liq-plusvalia-cita",
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_liquidacion],
    )
    brief = build_brief("")

    resultado = r028_module.evaluar(exp, brief)

    assert resultado is not None
    cita = resultado.cita_normativa_propuesta
    assert "Art. 66" not in cita
    assert "TRLHL" not in cita
    assert "art. 12" not in cita.lower()
    assert "LGT" not in cita
