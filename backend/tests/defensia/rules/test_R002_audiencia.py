"""Tests TDD para la regla R002 — audiencia_previa_omitida (T1B-002).

Base normativa research 2026-04-14:
    - Art. 99.8 LGT (Ley 58/2003): posibilidad de prescindir del tramite
      de audiencia solo cuando se suscriban actas con acuerdo o cuando
      este previsto un tramite de alegaciones posterior.
    - Art. 34.1.m) LGT: derecho del contribuyente a ser oido.
    - Art. 82 Ley 39/2015: regulacion general del tramite de audiencia en
      procedimientos administrativos.

Trigger:
    Dispara cuando (a) el expediente pasa de requerimiento directo a
    liquidacion sin abrir tramite de audiencia previo, o (b) se modifica la
    propuesta de liquidacion sin reabrir plazo de alegaciones.

Excepciones (NO dispara):
    - Acta con acuerdo (`datos.acta_con_acuerdo=True`).
    - Tramite de audiencia abierto correctamente con alegaciones presentadas.

Los tests usan las factories del `conftest.py` y el fixture autouse
`_aislar_registry` garantiza que el REGISTRY global se limpia entre tests.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import REGISTRY, evaluar


# ---------------------------------------------------------------------------
# Helper: carga unicamente la regla R002 para aislar los tests del resto del
# registry (R001, R003-R030 podrian no existir todavia en Wave 1B paralela).
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _cargar_solo_r002():
    """Importa exclusivamente el modulo R002 para activar su `@regla` decorator.

    Usamos import dinamico dentro del fixture para que el `reset_registry()`
    autouse del conftest se ejecute ANTES y no borre nuestro registro.
    """
    import importlib
    import sys

    modulo = "app.services.defensia_rules.reglas_procedimentales.R002_audiencia"
    # Forzamos reimport para garantizar que el decorador registra la regla en
    # el REGISTRY ya limpiado por el fixture autouse de conftest.
    if modulo in sys.modules:
        del sys.modules[modulo]
    importlib.import_module(modulo)
    yield


# ---------------------------------------------------------------------------
# Tests positivos (la regla DEBE disparar)
# ---------------------------------------------------------------------------

def test_r002_positivo_salto_directo_requerimiento_a_liquidacion(
    build_exp, build_brief, build_doc
):
    """Salto directo de requerimiento a liquidacion sin abrir audiencia.

    Expediente:
        - Doc 1: REQUERIMIENTO (t=0)
        - Doc 2: LIQUIDACION_PROVISIONAL (t=+30d) con
                 `tramite_audiencia_abierto=False`.
        - No existe doc intermedio `PROPUESTA_LIQUIDACION`.

    Resultado esperado: dispara R002 con cita semantica sobre omision del
    tramite de audiencia previa. Nunca texto hardcodeado tipo "Art. 99.8 LGT".
    """
    req = build_doc(
        TipoDocumento.REQUERIMIENTO,
        doc_id="doc-req-001",
        nombre_original="requerimiento_aeat.pdf",
        fecha_acto=datetime(2026, 1, 10, tzinfo=timezone.utc),
    )
    liq = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={"tramite_audiencia_abierto": False},
        doc_id="doc-liq-001",
        nombre_original="liquidacion_provisional.pdf",
        fecha_acto=datetime(2026, 2, 10, tzinfo=timezone.utc),
    )

    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[req, liq],
    )
    brief = build_brief("Me ha llegado una liquidacion sin haberme dado audiencia")

    candidatos = evaluar(exp, brief)

    r002 = [c for c in candidatos if c.regla_id == "R002"]
    assert len(r002) == 1, (
        f"R002 deberia disparar en salto directo req->liq, got {candidatos}"
    )
    arg = r002[0]
    assert isinstance(arg, ArgumentoCandidato)
    # Cita semantica — NUNCA hardcoded articulo concreto
    assert "audiencia" in arg.cita_normativa_propuesta.lower()
    assert "previa" in arg.cita_normativa_propuesta.lower()
    # No debe contener el articulo textual (eso es trabajo del RAG verificador)
    assert "99.8" not in arg.cita_normativa_propuesta
    assert "art." not in arg.cita_normativa_propuesta.lower()
    # Datos de disparo deben dar contexto para el escrito posterior
    assert "documento_id" in arg.datos_disparo or "motivo" in arg.datos_disparo


def test_r002_positivo_propuesta_modificada_sin_reabrir_plazo(
    build_exp, build_brief, build_doc
):
    """Propuesta modificada con liquidacion posterior sin reabrir alegaciones.

    Expediente:
        - Doc 1: PROPUESTA_LIQUIDACION (t=0)
        - Doc 2: LIQUIDACION_PROVISIONAL (t=+20d) con
                 `propuesta_modificada=True` y `nuevo_plazo_alegaciones=False`.

    Resultado esperado: dispara R002. La doctrina exige reabrir audiencia
    cuando se modifica la propuesta tras alegaciones.
    """
    prop = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={"tramite_audiencia_abierto": True},
        doc_id="doc-prop-001",
        nombre_original="propuesta_liquidacion.pdf",
        fecha_acto=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    liq = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "propuesta_modificada": True,
            "nuevo_plazo_alegaciones": False,
        },
        doc_id="doc-liq-002",
        nombre_original="liquidacion_provisional.pdf",
        fecha_acto=datetime(2026, 1, 21, tzinfo=timezone.utc),
    )

    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[prop, liq],
    )
    brief = build_brief("Cambiaron la propuesta pero no me dieron nuevo plazo")

    candidatos = evaluar(exp, brief)

    r002 = [c for c in candidatos if c.regla_id == "R002"]
    assert len(r002) == 1, (
        f"R002 deberia disparar cuando se modifica propuesta sin reabrir plazo, "
        f"got {candidatos}"
    )
    assert "audiencia" in r002[0].cita_normativa_propuesta.lower()


# ---------------------------------------------------------------------------
# Tests negativos (la regla NO debe disparar)
# ---------------------------------------------------------------------------

def test_r002_negativo_audiencia_abierta_correctamente(
    build_exp, build_brief, build_doc
):
    """Tramite de audiencia abierto y alegaciones presentadas.

    Expediente:
        - Doc 1: PROPUESTA_LIQUIDACION con `tramite_audiencia_abierto=True`
                 y `alegaciones_presentadas=True`.
        - Doc 2: LIQUIDACION_PROVISIONAL sin modificacion posterior.

    Resultado esperado: NO dispara.
    """
    prop = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "tramite_audiencia_abierto": True,
            "alegaciones_presentadas": True,
        },
        doc_id="doc-prop-ok",
        nombre_original="propuesta_ok.pdf",
        fecha_acto=datetime(2026, 1, 5, tzinfo=timezone.utc),
    )
    liq = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tramite_audiencia_abierto": True,
            "propuesta_modificada": False,
        },
        doc_id="doc-liq-ok",
        nombre_original="liquidacion_ok.pdf",
        fecha_acto=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[prop, liq],
    )
    brief = build_brief("Me dieron audiencia y presente alegaciones")

    candidatos = evaluar(exp, brief)

    r002 = [c for c in candidatos if c.regla_id == "R002"]
    assert r002 == [], (
        f"R002 NO debe disparar cuando la audiencia esta abierta, got {r002}"
    )


def test_r002_negativo_acta_con_acuerdo(build_exp, build_brief, build_doc):
    """Acta con acuerdo — excepcion art. 99.8 LGT.

    Cuando el contribuyente suscribe un acta con acuerdo, la norma permite
    expresamente prescindir del tramite de audiencia. La regla no debe disparar.
    """
    liq = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "acta_con_acuerdo": True,
            "tramite_audiencia_abierto": False,
        },
        doc_id="doc-acuerdo",
        nombre_original="liquidacion_acta_acuerdo.pdf",
        fecha_acto=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )

    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liq],
    )
    brief = build_brief("Firme acta con acuerdo")

    candidatos = evaluar(exp, brief)

    r002 = [c for c in candidatos if c.regla_id == "R002"]
    assert r002 == [], (
        f"R002 NO debe disparar cuando hay acta con acuerdo (excepcion art. "
        f"99.8 LGT), got {r002}"
    )


# ---------------------------------------------------------------------------
# Sanity check: la regla esta registrada
# ---------------------------------------------------------------------------

def test_r002_registrada_en_registry():
    """Tras importar el modulo, R002 debe estar en el REGISTRY."""
    assert "R002" in REGISTRY, (
        f"R002 no encontrada en REGISTRY. Keys actuales: {list(REGISTRY.keys())}"
    )
    info = REGISTRY["R002"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "IRPF" in info["tributos"]
    assert "IVA" in info["tributos"]
