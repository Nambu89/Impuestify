"""Tests de la regla R001 — motivacion_insuficiente (T1B-001).

La regla dispara cuando la liquidacion provisional u otro acto AEAT no motiva
suficientemente el rechazo de una deduccion/exencion conforme al art. 102.2.c
LGT. El codigo de la regla NO hardcodea la cita normativa — devuelve una
descripcion semantica libre; la cita canonica la resuelve el RAG verificador
(invariante #2 del plan Parte 2).

Fases aplicables (segun enum real `Fase` en `app/models/defensia.py`):
    - COMPROBACION_REQUERIMIENTO
    - COMPROBACION_PROPUESTA
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - SANCIONADOR_INICIADO / SANCIONADOR_PROPUESTA / SANCIONADOR_IMPUESTA
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Triggers soportados (segun research R001):
    - Falta de fundamentos de derecho (`tiene_fundamentos_derecho=False`)
    - Motivacion por remision sin haber notificado el acto previo
      (`motivacion_por_remision=True` + `acto_previo_notificado=False`)
"""
from __future__ import annotations

import importlib

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules.reglas_procedimentales import R001_motivacion
from app.services.defensia_rules_engine import REGISTRY, evaluar


# ---------------------------------------------------------------------------
# Re-registro de R001 en cada test
# ---------------------------------------------------------------------------
#
# El conftest autouse llama a `reset_registry()` antes de cada test, dejando
# el REGISTRY vacio. Como `importlib.import_module` devuelve el modulo cacheado
# y NO re-ejecuta el decorador `@regla`, necesitamos `importlib.reload()` para
# forzar la re-registracion de R001 antes de cada test.

@pytest.fixture(autouse=True)
def _recargar_R001():
    """Recarga el modulo R001 tras el reset del registry del conftest global."""
    importlib.reload(R001_motivacion)
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear el articulo canonico.

    La cita final ("Art. 102.2.c LGT") la resuelve el RAG verificador contra
    el corpus normativo. Aqui solo aceptamos descripciones semanticas libres.
    """
    prohibidas = [
        "Art. 102.2.c LGT",
        "Art. 102.2.c) LGT",
        "Articulo 102.2.c LGT",
        "Articulo 102.2 c LGT",
        "art. 102.2.c",
        "art 102.2.c",
    ]
    for prohibida in prohibidas:
        assert prohibida.lower() not in cita.lower(), (
            f"Cita hardcoded detectada: '{prohibida}' en '{cita}'. "
            "La cita canonica debe venir del RAG verificador."
        )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: liquidacion sin fundamentos de derecho
# ---------------------------------------------------------------------------

def test_R001_positivo_sin_fundamentos_de_derecho(build_exp, build_brief, build_doc):
    """Si la liquidacion provisional no contiene fundamentos de derecho, dispara."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tiene_fundamentos_derecho": False,
            "motivacion_por_remision": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("AEAT me deniega la deduccion sin explicar por que.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R001"

    # La cita debe ser semantica, NO hardcoded.
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "motivacion" in arg.cita_normativa_propuesta.lower(), (
        f"La cita semantica debe mencionar 'motivacion', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    # datos_disparo debe exponer el motivo por el que dispara.
    assert arg.datos_disparo.get("motivo") == "sin_fundamentos_derecho", (
        f"datos_disparo.motivo inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: motivacion por remision sin acto previo notificado
# ---------------------------------------------------------------------------

def test_R001_positivo_motivacion_por_remision_sin_acto_previo(
    build_exp, build_brief, build_doc
):
    """Motivacion 'por remision' solo es valida si el acto previo esta notificado.

    Doctrina TEAC reiterada — si la liquidacion se remite a un acto anterior
    que no ha sido notificado al contribuyente, hay indefension.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tiene_fundamentos_derecho": True,
            "motivacion_por_remision": True,
            "acto_previo_notificado": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("La liquidacion solo remite a otro acto que nunca recibi.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R001"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert arg.datos_disparo.get("motivo") == "remision_sin_acto_previo", (
        f"datos_disparo.motivo inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: motivacion completa (fundamentos + sin remision)
# ---------------------------------------------------------------------------

def test_R001_negativo_motivacion_completa(build_exp, build_brief, build_doc):
    """Si el acto contiene fundamentos de derecho y no usa motivacion por
    remision, la regla NO debe disparar."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tiene_fundamentos_derecho": True,
            "motivacion_por_remision": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Me han liquidado y estoy revisando la motivacion.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"La regla NO deberia disparar cuando hay motivacion completa, "
        f"got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: fase fuera de alcance
# ---------------------------------------------------------------------------

def test_R001_negativo_fase_fuera_de_alcance(build_exp, build_brief, build_doc):
    """Aunque el documento cumpla el trigger tecnico, si la fase del expediente
    esta FUERA_DE_ALCANCE la regla no debe disparar (el filtrado lo hace el
    motor a partir del `fases=[...]` del decorador)."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tiene_fundamentos_derecho": False,
            "motivacion_por_remision": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.FUERA_DE_ALCANCE,
        docs=[doc],
    )
    brief = build_brief("Caso fuera de alcance — p.ej. contencioso administrativo.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"La regla NO deberia disparar en fase FUERA_DE_ALCANCE, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Smoke de registro: R001 aparece en el REGISTRY tras el import
# ---------------------------------------------------------------------------

def test_R001_registrada_en_registry():
    """El reload del modulo R001_motivacion debe auto-registrar la regla."""
    assert "R001" in REGISTRY, (
        f"R001 no aparece en el REGISTRY tras reload. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R001"]
    assert "IRPF" in info["tributos"]
    assert "IVA" in info["tributos"]
    assert "ISD" in info["tributos"]
    assert "ITP" in info["tributos"]
    assert "PLUSVALIA" in info["tributos"]
    # La fase LIQUIDACION_FIRME_PLAZO_RECURSO debe estar en el set de fases.
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
