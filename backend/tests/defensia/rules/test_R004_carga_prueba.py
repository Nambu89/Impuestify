"""Tests para R004 — carga_prueba_administracion (T1B-004).

R004 detecta el supuesto en que la Administracion (AEAT) deniega una deduccion,
exencion u otro beneficio fiscal SIN haber ejercido la carga probatoria que le
corresponde:

1. No requirio documentacion al contribuyente antes de denegar, O
2. El contribuyente aporto documentacion pero la Administracion no motivo por
   que resulta insuficiente para acreditar el hecho imponible.

Base normativa (la resuelve el RAG verificador, NO la regla):
- Art. 105.1 LGT (la Administracion debe probar los hechos en los que funda
  sus actos cuando el obligado aporta principio de prueba).
- Doctrina TS sobre facilidad y disponibilidad probatoria.
- Art. 217 LEC supletoriamente.

La regla NO hardcodea la cita del articulo — solo emite una cita semantica
("Incumplimiento de la carga de la prueba por la Administracion") que el
verificador RAG traducira al texto canonico correcto.
"""
from __future__ import annotations

import importlib

import pytest

from app.models.defensia import (
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import REGISTRY, evaluar, reset_registry


@pytest.fixture(autouse=True)
def _registrar_r004(_aislar_registry):  # noqa: ARG001 — fuerza orden
    """Re-importa el modulo R004 tras cada `reset_registry()` del conftest.

    El fixture autouse `_aislar_registry` del conftest limpia REGISTRY antes
    de cada test. Como el decorador `@regla` se ejecuta al importar el modulo
    por primera vez (side-effect), necesitamos reimportarlo para que vuelva a
    registrarse. Declaramos `_aislar_registry` como dependencia explicita
    para garantizar que el reset ocurra ANTES de este re-registro.

    Hacemos un `reset_registry()` adicional justo antes del `reload` para
    cubrir el caso en el que la primera importacion del modulo ya registro
    la regla dentro del propio bloque de setup del fixture (en ese caso
    `reload` veria una regla duplicada).
    """
    from app.services.defensia_rules.reglas_procedimentales import (
        R004_carga_prueba,
    )
    reset_registry()
    importlib.reload(R004_carga_prueba)
    yield


# ---------------------------------------------------------------------------
# Positivo 1: deduccion denegada sin requerimiento previo
# ---------------------------------------------------------------------------

def test_R004_dispara_cuando_denegacion_sin_requerimiento_previo(
    build_exp, build_doc, build_brief
):
    """AEAT deniega deduccion en liquidacion provisional y nunca requirio docs."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deniega_beneficio_fiscal": True,
            "concepto_denegado": "deduccion por inversion en vivienda habitual",
            "motivacion_insuficiencia_prueba": False,
        },
        doc_id="doc-liq-001",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("AEAT me ha denegado la deduccion por vivienda sin pedirme nada")

    candidatos = evaluar(exp, brief)

    r004 = [c for c in candidatos if c.regla_id == "R004"]
    assert len(r004) == 1, f"R004 deberia disparar exactamente una vez, got {len(r004)}"

    cita = r004[0].cita_normativa_propuesta
    # Cita SEMANTICA — nunca hardcoded del articulo.
    assert "Art. 105.1" not in cita, f"cita no puede contener 'Art. 105.1' literal: {cita}"
    assert "articulo 105" not in cita.lower(), f"cita no puede hardcodear articulo: {cita}"
    assert "105.1 LGT" not in cita, f"cita no puede contener referencia canonica: {cita}"
    assert "carga de la prueba" in cita.lower(), f"cita semantica debe mencionar carga probatoria: {cita}"
    assert "administracion" in cita.lower(), f"cita semantica debe referirse a la Administracion: {cita}"

    assert r004[0].datos_disparo.get("motivo") == "sin_requerimiento_previo"


# ---------------------------------------------------------------------------
# Positivo 2: documentacion aportada pero denegacion no motivada
# ---------------------------------------------------------------------------

def test_R004_dispara_cuando_aportada_pero_no_motivada(
    build_exp, build_doc, build_brief
):
    """Contribuyente aporto pruebas, AEAT denego sin motivar la insuficiencia."""
    requerimiento = build_doc(
        TipoDocumento.REQUERIMIENTO,
        datos={"pide_documentacion": True},
        doc_id="doc-req-001",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deniega_beneficio_fiscal": True,
            "concepto_denegado": "exencion por reinversion",
            "documentacion_aportada": True,
            "motivacion_insuficiencia_prueba": False,
        },
        doc_id="doc-liq-002",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[requerimiento, liquidacion],
    )
    brief = build_brief("Aporte la sentencia de divorcio y me han denegado igualmente")

    candidatos = evaluar(exp, brief)

    r004 = [c for c in candidatos if c.regla_id == "R004"]
    assert len(r004) == 1, f"R004 deberia disparar con aportada+no motivada, got {len(r004)}"

    datos = r004[0].datos_disparo
    assert datos.get("motivo") == "aportada_sin_motivar_insuficiencia"
    assert datos.get("documentacion_aportada") is True


# ---------------------------------------------------------------------------
# Negativo 1: requerimiento + respuesta + denegacion motivada
# ---------------------------------------------------------------------------

def test_R004_no_dispara_cuando_hay_requerimiento_y_denegacion_motivada(
    build_exp, build_doc, build_brief
):
    """Si AEAT requirio, hubo respuesta y la denegacion esta motivada, R004 calla."""
    requerimiento = build_doc(
        TipoDocumento.REQUERIMIENTO,
        datos={"pide_documentacion": True},
        doc_id="doc-req-002",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deniega_beneficio_fiscal": True,
            "concepto_denegado": "deduccion por familia numerosa",
            "documentacion_aportada": True,
            "motivacion_insuficiencia_prueba": True,  # AEAT SI motivo por que no basta
        },
        doc_id="doc-liq-003",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[requerimiento, liquidacion],
    )
    brief = build_brief("Me denegaron la deduccion tras requerimiento")

    candidatos = evaluar(exp, brief)

    r004 = [c for c in candidatos if c.regla_id == "R004"]
    assert r004 == [], (
        f"R004 NO debe disparar cuando hay requerimiento + respuesta + "
        f"denegacion motivada, got {r004}"
    )


# ---------------------------------------------------------------------------
# Negativo 2: solo correccion aritmetica (no hay denegacion de beneficio)
# ---------------------------------------------------------------------------

def test_R004_no_dispara_en_correccion_aritmetica(
    build_exp, build_doc, build_brief
):
    """Si la liquidacion solo corrige un calculo aritmetico, R004 calla."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deniega_beneficio_fiscal": False,
            "correccion_aritmetica": True,
            "concepto": "ajuste por error en suma de rendimientos",
        },
        doc_id="doc-liq-004",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Me han recalculado la declaracion")

    candidatos = evaluar(exp, brief)

    r004 = [c for c in candidatos if c.regla_id == "R004"]
    assert r004 == [], (
        f"R004 NO debe disparar en mera correccion aritmetica sin denegacion "
        f"de beneficio fiscal, got {r004}"
    )


# ---------------------------------------------------------------------------
# Sanity check del registry (solo R004)
# ---------------------------------------------------------------------------

def test_R004_registrada_en_registry():
    """Al importar el modulo, R004 queda registrada con metadata correcta."""
    assert "R004" in REGISTRY, f"R004 no registrada. Keys: {list(REGISTRY.keys())}"
    info = REGISTRY["R004"]

    # Tributos: los 5 cubiertos por DefensIA v1.
    assert info["tributos"] == {"IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"}

    # Fases: debe incluir liquidacion provisional, sancionador, propuesta,
    # reposicion y TEAR (donde aun se puede plantear el argumento).
    assert Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value in info["fases"]
    assert Fase.TEAR_INTERPUESTA.value in info["fases"]
    assert Fase.TEAR_AMPLIACION_POSIBLE.value in info["fases"]
    assert Fase.REPOSICION_INTERPUESTA.value in info["fases"]

    # Descripcion semantica — sin cita canonica hardcoded.
    desc = info["descripcion"].lower()
    assert "carga de la prueba" in desc or "carga probatoria" in desc
