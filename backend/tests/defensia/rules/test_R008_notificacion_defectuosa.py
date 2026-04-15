"""Tests para R008 — notificacion_defectuosa (T1B-008).

R008 detecta notificaciones administrativas con defectos formales esenciales
que provocan anulabilidad del acto hasta su correcta practica:

1. **DEHu sin puesta a disposicion efectiva**: notificacion por Direccion
   Electronica Habilitada unica sin que conste puesta a disposicion efectiva.
2. **Domicilio postal sin segundo intento**: notificacion por correo postal
   con un solo intento fallido y sin acuse, incumpliendo el doble intento
   exigido por la normativa.
3. **Domicilio incorrecto**: notificacion practicada en un domicilio que no
   coincide con el que el obligado tributario tiene declarado en el Censo.

Base normativa (la RESUELVE el RAG verificador, NO la regla):
- Arts. 109-112 LGT (notificaciones tributarias)
- Art. 41 Ley 39/2015 (regimen general)
- RD 203/2021 sobre DEHu
- STC 112/2019 sobre notificaciones electronicas y derecho a recurso efectivo

La regla NO hardcodea la cita canonica — emite una cita SEMANTICA que
describe el defecto formal, y el verificador RAG la traduce al texto
normativo exacto contra el corpus indexado.
"""
from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import REGISTRY, evaluar, reset_registry


@pytest.fixture(autouse=True)
def _registrar_r008(_aislar_registry):  # noqa: ARG001 — fuerza orden
    """Re-importa el modulo R008 tras cada `reset_registry()` del conftest.

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
        R008_notificacion_defectuosa,
    )
    reset_registry()
    importlib.reload(R008_notificacion_defectuosa)
    yield


# ---------------------------------------------------------------------------
# Positivo 1: DEHu sin puesta a disposicion efectiva
# ---------------------------------------------------------------------------

def test_R008_dispara_cuando_dehu_sin_puesta_disposicion_efectiva(
    build_exp, build_doc, build_brief
):
    """Canal DEHu pero sin constancia de puesta a disposicion efectiva."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "canal_notificacion": "DEHU",
            "puesta_disposicion_efectiva": False,
        },
        doc_id="doc-liq-dehu-001",
        nombre_original="liquidacion_dehu.pdf",
        fecha_acto=datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Me ha llegado una liquidacion por DEHu que nunca pude leer"
    )

    candidatos = evaluar(exp, brief)

    r008 = [c for c in candidatos if c.regla_id == "R008"]
    assert len(r008) == 1, (
        f"R008 deberia disparar exactamente una vez en DEHu sin puesta a "
        f"disposicion, got {len(r008)}: {candidatos}"
    )

    arg = r008[0]
    assert isinstance(arg, ArgumentoCandidato)

    cita = arg.cita_normativa_propuesta
    # Cita SEMANTICA — nunca articulo concreto hardcoded.
    assert "notificacion" in cita.lower(), (
        f"cita semantica debe mencionar notificacion, got: {cita}"
    )
    assert "defectuosa" in cita.lower(), (
        f"cita semantica debe mencionar defecto, got: {cita}"
    )
    # No debe contener referencias canonicas literales.
    assert "109" not in cita, f"cita no puede hardcodear articulo 109: {cita}"
    assert "Ley 39/2015" not in cita, f"cita no puede hardcodear ley: {cita}"
    assert "art." not in cita.lower(), f"cita no debe usar 'art.': {cita}"

    datos = arg.datos_disparo
    assert datos.get("motivo") == "dehu_sin_puesta_disposicion_efectiva"
    assert datos.get("canal_notificacion") == "DEHU"


# ---------------------------------------------------------------------------
# Positivo 2: Postal con un solo intento y sin acuse
# ---------------------------------------------------------------------------

def test_R008_dispara_cuando_postal_sin_segundo_intento(
    build_exp, build_doc, build_brief
):
    """Notificacion por correo postal con un solo intento fallido y sin acuse."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "canal_notificacion": "POSTAL",
            "numero_intentos": 1,
            "acuse_recibido": False,
        },
        doc_id="doc-liq-postal-001",
        nombre_original="liquidacion_postal.pdf",
        fecha_acto=datetime(2026, 2, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Dicen que el cartero vino una vez y ya dieron por notificado"
    )

    candidatos = evaluar(exp, brief)

    r008 = [c for c in candidatos if c.regla_id == "R008"]
    assert len(r008) == 1, (
        f"R008 deberia disparar con postal+1 intento+sin acuse, got {r008}"
    )

    arg = r008[0]
    datos = arg.datos_disparo
    assert datos.get("motivo") == "postal_sin_segundo_intento"
    assert datos.get("numero_intentos") == 1
    assert datos.get("acuse_recibido") is False


# ---------------------------------------------------------------------------
# Positivo 3: Domicilio que no coincide con el declarado
# ---------------------------------------------------------------------------

def test_R008_dispara_cuando_domicilio_incorrecto(
    build_exp, build_doc, build_brief
):
    """Notificacion practicada en domicilio no coincidente con el del Censo."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "canal_notificacion": "POSTAL",
            "domicilio_coincide_con_registro": False,
        },
        doc_id="doc-liq-dom-001",
        nombre_original="liquidacion_domicilio.pdf",
        fecha_acto=datetime(2026, 3, 5, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "La carta la mandaron a mi antiguo piso, no donde vivo ahora"
    )

    candidatos = evaluar(exp, brief)

    r008 = [c for c in candidatos if c.regla_id == "R008"]
    assert len(r008) == 1, (
        f"R008 deberia disparar cuando domicilio no coincide con registro, "
        f"got {r008}"
    )

    datos = r008[0].datos_disparo
    assert datos.get("motivo") == "domicilio_no_coincide_con_registro"
    assert datos.get("domicilio_coincide_con_registro") is False


# ---------------------------------------------------------------------------
# Negativo: notificacion valida (canal + puesta disposicion + acuse OK)
# ---------------------------------------------------------------------------

def test_R008_no_dispara_cuando_notificacion_valida(
    build_exp, build_doc, build_brief
):
    """Canal valido, puesta a disposicion efectiva, acuse correcto y domicilio OK."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "canal_notificacion": "DEHU",
            "puesta_disposicion_efectiva": True,
            "acuse_recibido": True,
            "domicilio_coincide_con_registro": True,
        },
        doc_id="doc-liq-ok",
        nombre_original="liquidacion_notif_ok.pdf",
        fecha_acto=datetime(2026, 2, 20, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Me llego bien la notificacion por DEHu")

    candidatos = evaluar(exp, brief)

    r008 = [c for c in candidatos if c.regla_id == "R008"]
    assert r008 == [], (
        f"R008 NO debe disparar cuando la notificacion es valida, got {r008}"
    )


# ---------------------------------------------------------------------------
# Sanity check del registry
# ---------------------------------------------------------------------------

def test_R008_registrada_en_registry():
    """Al importar el modulo, R008 queda registrada con metadata correcta."""
    assert "R008" in REGISTRY, (
        f"R008 no registrada. Keys: {list(REGISTRY.keys())}"
    )
    info = REGISTRY["R008"]

    # Tributos: los 5 cubiertos por DefensIA v1.
    assert info["tributos"] == {"IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"}

    # Fases: transversal — liquidacion, sancionador, propuesta, requerimiento,
    # reposicion y TEAR (donde aun se puede alegar el defecto de notificacion).
    assert Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value in info["fases"]
    assert Fase.SANCIONADOR_IMPUESTA.value in info["fases"]
    assert Fase.COMPROBACION_PROPUESTA.value in info["fases"]
    assert Fase.COMPROBACION_REQUERIMIENTO.value in info["fases"]
    assert Fase.REPOSICION_INTERPUESTA.value in info["fases"]
    assert Fase.TEAR_INTERPUESTA.value in info["fases"]
    assert Fase.TEAR_AMPLIACION_POSIBLE.value in info["fases"]

    # Descripcion semantica — sin cita canonica hardcoded.
    desc = info["descripcion"].lower()
    assert "notificacion" in desc
    assert "109" not in desc
    assert "39/2015" not in desc
