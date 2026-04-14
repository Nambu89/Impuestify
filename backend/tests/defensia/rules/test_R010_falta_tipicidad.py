"""Tests TDD para la regla R010 — falta_tipicidad_o_norma_inaplicable (T1B-010).

La regla dispara cuando el acuerdo sancionador imputa una conducta que NO
encaja en el tipo infractor citado (arts. 191-206 LGT) o cuando se aplica
analogicamente un tipo sancionador a un supuesto no previsto expresamente
por la norma.

Base normativa (la resuelve el RAG verificador, NO la regla):
    - Art. 178 LGT: principios de la potestad sancionadora tributaria
      (legalidad, tipicidad, responsabilidad, proporcionalidad, no
      concurrencia e irretroactividad).
    - Art. 183.1 LGT: definicion de infraccion tributaria como accion u
      omision dolosa o culposa con cualquier grado de negligencia
      tipificada y sancionada en la propia Ley.
    - Art. 25.1 CE: principio de legalidad sancionadora — nadie puede
      ser condenado o sancionado por acciones que en el momento de
      producirse no constituyan infraccion segun la legislacion vigente.
    - STC 2/2003 y jurisprudencia TC/TS sobre tipicidad estricta:
      no cabe interpretacion extensiva ni analogica in peius en materia
      sancionadora.

Fases aplicables (del enum real `Fase`):
    - SANCIONADOR_INICIADO / SANCIONADOR_PROPUESTA / SANCIONADOR_IMPUESTA
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Triggers soportados (segun research R010):
    - `datos.conducta_no_encaja_en_tipo=True`: la conducta imputada no
      encaja en el tipo infractor citado.
    - `datos.aplicacion_analogica=True`: se aplica analogicamente un tipo
      sancionador a un supuesto no previsto.

La regla NO hardcodea la cita del articulo — solo emite una cita semantica
("Falta de tipicidad estricta...") que el verificador RAG traducira al
texto canonico correcto.
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
from app.services.defensia_rules_engine import REGISTRY, evaluar, reset_registry


@pytest.fixture(autouse=True)
def _registrar_r010(_aislar_registry):  # noqa: ARG001 — fuerza orden
    """Re-importa R010 tras cada `reset_registry()` del conftest.

    El fixture autouse `_aislar_registry` del conftest limpia el REGISTRY
    antes de cada test. Como el decorador ``@regla`` se ejecuta por
    side-effect en el import del modulo, debemos reimportarlo para que
    la regla vuelva a registrarse. Declaramos `_aislar_registry` como
    dependencia explicita para garantizar que el reset ocurra ANTES de
    este re-registro.

    El `reset_registry()` adicional antes del ``reload`` cubre el caso
    en el que la primera importacion del modulo ya haya registrado la
    regla durante el propio setup del fixture (en ese caso `reload`
    detectaria un ID duplicado).
    """
    from app.services.defensia_rules.reglas_procedimentales import (
        R010_falta_tipicidad,
    )
    reset_registry()
    importlib.reload(R010_falta_tipicidad)
    yield


# ---------------------------------------------------------------------------
# Helper local — la cita NUNCA puede hardcodear articulos canonicos
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Arts. 178 y 183 LGT", "Art. 25.1 CE") la resuelve el
    RAG verificador contra el corpus normativo. Aqui solo aceptamos
    descripciones semanticas libres.
    """
    prohibidas = [
        "Art. 178",
        "Art. 183",
        "Art. 25.1",
        "Articulo 178",
        "Articulo 183",
        "Articulo 25.1",
        "art. 178",
        "art. 183",
        "art. 25.1",
        "LGT 178",
        "LGT 183",
        "CE 25",
        "STC 2/2003",
    ]
    for prohibida in prohibidas:
        assert prohibida.lower() not in cita.lower(), (
            f"Cita hardcoded detectada: '{prohibida}' en '{cita}'. "
            "La cita canonica debe venir del RAG verificador."
        )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: conducta no encaja en el tipo infractor citado
# ---------------------------------------------------------------------------

def test_R010_positivo_conducta_no_encaja_en_tipo(
    build_exp, build_brief, build_doc
):
    """Si el acuerdo sancionador imputa una conducta que no encaja en el
    tipo infractor citado (arts. 191-206 LGT), dispara R010.
    """
    doc = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos={
            "conducta_no_encaja_en_tipo": True,
            "aplicacion_analogica": False,
            "tipo_infractor_citado": "191 LGT",
        },
        doc_id="doc-sancion-001",
        nombre_original="acuerdo_imposicion_sancion.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.SANCIONADOR_IMPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT me sanciona por dejar de ingresar pero mi conducta no encaja "
        "en el tipo del 191 LGT"
    )

    candidatos = evaluar(exp, brief)

    r010 = [c for c in candidatos if c.regla_id == "R010"]
    assert len(r010) == 1, (
        f"R010 deberia disparar cuando la conducta no encaja en el tipo, "
        f"got {candidatos}"
    )

    arg = r010[0]
    assert isinstance(arg, ArgumentoCandidato)

    # La cita debe ser semantica — NUNCA hardcoded
    cita = arg.cita_normativa_propuesta
    _assert_cita_no_hardcoded(cita)
    assert "tipicidad" in cita.lower(), (
        f"La cita semantica debe mencionar 'tipicidad', got: {cita!r}"
    )
    assert "infraccion" in cita.lower(), (
        f"La cita semantica debe mencionar 'infraccion', got: {cita!r}"
    )

    # datos_disparo debe exponer el motivo para que el writer lo use
    assert arg.datos_disparo.get("motivo") == "conducta_no_encaja_en_tipo", (
        f"datos_disparo.motivo inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: aplicacion analogica de un tipo sancionador
# ---------------------------------------------------------------------------

def test_R010_positivo_aplicacion_analogica(
    build_exp, build_brief, build_doc
):
    """Si se aplica analogicamente un tipo sancionador, dispara R010.

    La jurisprudencia constitucional prohibe expresamente la analogia in
    peius en materia sancionadora (principio de tipicidad estricta).
    """
    doc = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos={
            "conducta_no_encaja_en_tipo": False,
            "aplicacion_analogica": True,
            "tipo_infractor_citado": "195 LGT",
        },
        doc_id="doc-sancion-002",
        nombre_original="acuerdo_sancion_analogia.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.TEAR_INTERPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "Me han sancionado aplicando el tipo por analogia a un supuesto "
        "que la ley no preve"
    )

    candidatos = evaluar(exp, brief)

    r010 = [c for c in candidatos if c.regla_id == "R010"]
    assert len(r010) == 1, (
        f"R010 deberia disparar cuando hay aplicacion analogica, "
        f"got {candidatos}"
    )

    arg = r010[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "analogica" in arg.cita_normativa_propuesta.lower() or (
        "tipicidad" in arg.cita_normativa_propuesta.lower()
    ), (
        f"La cita semantica debe mencionar tipicidad/analogica, got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    assert arg.datos_disparo.get("motivo") == "aplicacion_analogica", (
        f"datos_disparo.motivo inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: tipo infractor encaja y sin analogia
# ---------------------------------------------------------------------------

def test_R010_negativo_tipo_encaja_sin_analogia(
    build_exp, build_brief, build_doc
):
    """Si la conducta encaja en el tipo y no hay aplicacion analogica,
    la regla NO dispara.
    """
    doc = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos={
            "conducta_no_encaja_en_tipo": False,
            "aplicacion_analogica": False,
            "tipo_infractor_citado": "191 LGT",
        },
        doc_id="doc-sancion-ok",
        nombre_original="acuerdo_sancion_correcta.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.SANCIONADOR_IMPUESTA,
        docs=[doc],
    )
    brief = build_brief("Me han sancionado por dejar de ingresar el IRPF")

    candidatos = evaluar(exp, brief)

    r010 = [c for c in candidatos if c.regla_id == "R010"]
    assert r010 == [], (
        f"R010 NO debe disparar cuando el tipo encaja y no hay analogia, "
        f"got {r010}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: expediente no esta en fase sancionadora
# ---------------------------------------------------------------------------

def test_R010_negativo_fase_no_sancionadora(
    build_exp, build_brief, build_doc
):
    """Si el expediente esta en fase de liquidacion (no sancionadora),
    la regla NO dispara aunque los flags esten activos — R010 solo
    aplica al procedimiento sancionador.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "conducta_no_encaja_en_tipo": True,
            "aplicacion_analogica": True,
        },
        doc_id="doc-liq-provisional",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Me ha llegado una liquidacion provisional")

    candidatos = evaluar(exp, brief)

    r010 = [c for c in candidatos if c.regla_id == "R010"]
    assert r010 == [], (
        f"R010 NO debe disparar en fase de liquidacion (no sancionadora), "
        f"got {r010}"
    )


# ---------------------------------------------------------------------------
# Sanity check: la regla esta registrada tras el import
# ---------------------------------------------------------------------------

def test_R010_registrada_en_registry():
    """Tras importar el modulo, R010 debe estar en el REGISTRY con la
    metadata correcta (tributos transversales, fases sancionador/recurso).
    """
    assert "R010" in REGISTRY, (
        f"R010 no encontrada en REGISTRY. Keys actuales: {list(REGISTRY.keys())}"
    )
    info = REGISTRY["R010"]
    # Transversal sancionador — aplica a los 5 tributos del scope DefensIA
    for tributo in ("IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"):
        assert tributo in info["tributos"], (
            f"R010 deberia aplicar a {tributo}, tributos={info['tributos']}"
        )
    # Fases sancionador + vias de recurso
    assert "SANCIONADOR_IMPUESTA" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
    assert "TEAR_AMPLIACION_POSIBLE" in info["fases"]
    # No debe aplicar a fases de liquidacion
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" not in info["fases"]
