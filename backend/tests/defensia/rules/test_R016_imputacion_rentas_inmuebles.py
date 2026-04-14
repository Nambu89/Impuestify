"""Tests TDD para la regla R016 — imputacion_rentas_inmuebles (T1B-016).

La regla dispara cuando AEAT imputa renta inmobiliaria (art. 85 LIRPF) sobre
un inmueble que, total o parcialmente durante el periodo impositivo, NO
genera obligacion de imputar, o cuando se imputa sin prorratear por los dias
de efectiva disposicion del titular:

- Inmueble que fue ``vivienda habitual`` (total o parcialmente en el ejercicio)
  — el art. 85 LIRPF excluye la vivienda habitual de la imputacion de rentas.
- Inmueble ``afecto a una actividad economica`` — tampoco genera imputacion.
- Inmueble a disposicion del titular solo una fraccion de dias (por ejemplo,
  tras una adquisicion o una transmision intra-ejercicio) sin que AEAT
  prorratee la imputacion por esos dias.

Base normativa (la resuelve el RAG verificador, NO la regla):
    - Art. 85 LIRPF: imputacion de rentas inmobiliarias, 2% (1,1% en los casos
      de revision catastral reciente) sobre valor catastral, con exclusion
      expresa de la vivienda habitual, los suelos no edificados y los bienes
      afectos a actividades economicas. La imputacion se realiza en proporcion
      al numero de dias del ejercicio en que el inmueble estuvo a disposicion
      de su titular.

Fases aplicables (brief corregido):
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - COMPROBACION_PROPUESTA / COMPROBACION_POST_ALEGACIONES
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Triggers soportados:
    - ``datos.imputa_renta_inmueble=True`` es la precondicion — si AEAT no
      esta imputando renta, la regla no tiene nada que impugnar.
    - Y ademas al menos uno de:
        * ``datos.es_vivienda_habitual_en_periodo=True``
        * ``datos.afecto_actividad_economica=True``
        * ``datos.prorrateo_por_dias_aplicado=False`` con
          ``datos.dias_a_disposicion`` < 365 (prorrateo omitido).

La regla NO hardcodea la cita canonica (`Art. 85 LIRPF`) — solo emite una
cita semantica que el verificador RAG traducira al texto legal correcto.
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
from app.services.defensia_rules_engine import REGISTRY, evaluar, reset_registry


# ---------------------------------------------------------------------------
# Aislamiento del modulo R016 — patron autocontenido
# ---------------------------------------------------------------------------

def _cargar_solo_R016() -> None:
    """Limpia el REGISTRY y re-importa unicamente el modulo R016.

    El fixture autouse ``_aislar_registry`` del conftest ya limpia el
    REGISTRY, pero aqui reseteamos de nuevo y forzamos un ``reload`` para
    que el decorador ``@regla`` se ejecute aunque el modulo ya estuviera
    cacheado en ``sys.modules``.
    """
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_irpf."
        "R016_imputacion_rentas_inmuebles"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _registrar_r016(_aislar_registry):  # noqa: ARG001 — fuerza orden
    """Re-registra R016 despues de que el conftest limpie el REGISTRY."""
    _cargar_solo_R016()
    yield


# ---------------------------------------------------------------------------
# Helper local — la cita NUNCA puede hardcodear el articulo canonico
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Art. 85 LIRPF", "art. 85.1 LIRPF", ...) la resuelve el
    RAG verificador contra el corpus normativo. Aqui solo aceptamos
    descripciones semanticas libres.
    """
    assert "Art. 85" not in cita and "85 LIRPF" not in cita.upper(), (
        f"Cita hardcoded detectada en R016: '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: el inmueble fue vivienda habitual en el periodo
# ---------------------------------------------------------------------------

def test_R016_positivo_vivienda_habitual_en_periodo(
    build_exp, build_brief, build_doc
):
    """Si el inmueble fue vivienda habitual durante el periodo y AEAT aun
    asi imputa renta, la regla dispara — el art. 85 LIRPF excluye la
    vivienda habitual de la imputacion.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "imputa_renta_inmueble": True,
            "es_vivienda_habitual_en_periodo": True,
        },
        doc_id="doc-liq-r016-001",
        nombre_original="liquidacion_imputacion_vivienda.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT me imputa renta por una vivienda que fue mi habitual durante "
        "parte del periodo"
    )

    candidatos = evaluar(exp, brief)

    r016 = [c for c in candidatos if c.regla_id == "R016"]
    assert len(r016) == 1, (
        f"R016 deberia disparar cuando el inmueble fue vivienda habitual "
        f"en el periodo, got {candidatos}"
    )

    arg = r016[0]
    assert isinstance(arg, ArgumentoCandidato)
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "imputacion" in arg.cita_normativa_propuesta.lower(), (
        f"La cita semantica debe mencionar 'imputacion', "
        f"got: {arg.cita_normativa_propuesta!r}"
    )
    assert arg.datos_disparo.get("motivo") == "vivienda_habitual_en_periodo"


# ---------------------------------------------------------------------------
# Test 2 — Positivo: inmueble afecto a una actividad economica
# ---------------------------------------------------------------------------

def test_R016_positivo_afecto_actividad_economica(
    build_exp, build_brief, build_doc
):
    """Si el inmueble esta afecto a una actividad economica, el art. 85
    LIRPF tambien lo excluye expresamente de la imputacion. R016 dispara.
    """
    doc = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "imputa_renta_inmueble": True,
            "afecto_actividad_economica": True,
        },
        doc_id="doc-prop-r016-002",
        nombre_original="propuesta_imputacion_local.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "Me imputan renta sobre un local afecto a mi actividad economica"
    )

    candidatos = evaluar(exp, brief)

    r016 = [c for c in candidatos if c.regla_id == "R016"]
    assert len(r016) == 1, (
        f"R016 deberia disparar cuando el inmueble esta afecto a actividad, "
        f"got {candidatos}"
    )

    arg = r016[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert arg.datos_disparo.get("motivo") == "afecto_actividad_economica"


# ---------------------------------------------------------------------------
# Test 3 — Positivo: imputacion sin prorratear por dias a disposicion
# ---------------------------------------------------------------------------

def test_R016_positivo_sin_prorrateo_por_dias(
    build_exp, build_brief, build_doc
):
    """Si AEAT imputa una renta completa sin prorratear por los dias que el
    inmueble estuvo a disposicion del titular, R016 dispara y expone en
    ``datos_disparo`` el numero de dias no prorrateados (365 - dias a
    disposicion).
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "imputa_renta_inmueble": True,
            "prorrateo_por_dias_aplicado": False,
            "dias_a_disposicion": 180,
            "es_vivienda_habitual_en_periodo": False,
            "afecto_actividad_economica": False,
        },
        doc_id="doc-liq-r016-003",
        nombre_original="liquidacion_sin_prorrateo.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.TEAR_INTERPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT me imputa la renta completa sin prorratear los dias que el "
        "inmueble estuvo realmente a mi disposicion"
    )

    candidatos = evaluar(exp, brief)

    r016 = [c for c in candidatos if c.regla_id == "R016"]
    assert len(r016) == 1, (
        f"R016 deberia disparar cuando no se prorratea por dias, "
        f"got {candidatos}"
    )

    arg = r016[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "prorrateo" in arg.cita_normativa_propuesta.lower() or (
        "dias" in arg.cita_normativa_propuesta.lower()
    ), (
        f"La cita semantica debe mencionar 'prorrateo'/'dias', "
        f"got: {arg.cita_normativa_propuesta!r}"
    )
    assert arg.datos_disparo.get("motivo") == "sin_prorrateo_por_dias"
    assert arg.datos_disparo.get("dias_no_prorrateados") == 185, (
        f"datos_disparo.dias_no_prorrateados deberia ser 365-180=185, "
        f"got {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: imputacion correcta (prorrateo aplicado, no excluido)
# ---------------------------------------------------------------------------

def test_R016_negativo_imputacion_correcta(
    build_exp, build_brief, build_doc
):
    """Si AEAT imputa correctamente (prorrateo aplicado y el inmueble no
    esta excluido por ser vivienda habitual ni estar afecto a actividad),
    la regla NO dispara.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "imputa_renta_inmueble": True,
            "prorrateo_por_dias_aplicado": True,
            "es_vivienda_habitual_en_periodo": False,
            "afecto_actividad_economica": False,
            "dias_a_disposicion": 365,
        },
        doc_id="doc-liq-r016-ok",
        nombre_original="liquidacion_imputacion_correcta.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Me imputan renta por una segunda vivienda")

    candidatos = evaluar(exp, brief)

    r016 = [c for c in candidatos if c.regla_id == "R016"]
    assert r016 == [], (
        f"R016 NO debe disparar si la imputacion es correcta, got {r016}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: AEAT no imputa renta en absoluto
# ---------------------------------------------------------------------------

def test_R016_negativo_sin_imputacion(
    build_exp, build_brief, build_doc
):
    """Si el acto administrativo no contiene imputacion de renta
    inmobiliaria, la regla NO dispara aunque haya datos colaterales.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "imputa_renta_inmueble": False,
            # Flags que normalmente dispararian la regla, pero sin la
            # precondicion "imputa_renta_inmueble=True" son irrelevantes.
            "es_vivienda_habitual_en_periodo": True,
            "afecto_actividad_economica": True,
            "prorrateo_por_dias_aplicado": False,
            "dias_a_disposicion": 100,
        },
        doc_id="doc-liq-r016-sin-imp",
        nombre_original="liquidacion_sin_imputacion.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Me llega una liquidacion sin imputacion inmobiliaria")

    candidatos = evaluar(exp, brief)

    r016 = [c for c in candidatos if c.regla_id == "R016"]
    assert r016 == [], (
        f"R016 NO debe disparar si no hay imputacion de renta, got {r016}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: la cita semantica no menciona el articulo canonico
# ---------------------------------------------------------------------------

def test_R016_cita_no_hardcoded(build_exp, build_brief, build_doc):
    """Verifica de forma explicita que la cita propuesta por R016 NO
    contiene el literal ``Art. 85`` ni ``85 LIRPF`` — la cita canonica
    la resuelve el RAG verificador.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "imputa_renta_inmueble": True,
            "es_vivienda_habitual_en_periodo": True,
        },
        doc_id="doc-liq-r016-cita",
        nombre_original="liquidacion_vivienda_habitual.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.REPOSICION_INTERPUESTA,
        docs=[doc],
    )
    brief = build_brief("Me imputan renta sobre mi vivienda habitual")

    candidatos = evaluar(exp, brief)

    r016 = [c for c in candidatos if c.regla_id == "R016"]
    assert len(r016) == 1

    cita = r016[0].cita_normativa_propuesta
    assert "Art. 85" not in cita and "85 LIRPF" not in cita.upper(), (
        f"R016 hardcodea la cita canonica: '{cita}'. "
        "Debe ser una cita semantica libre resolvible por el RAG verificador."
    )


# ---------------------------------------------------------------------------
# Sanity check: la regla esta registrada tras el import
# ---------------------------------------------------------------------------

def test_R016_registrada_en_registry():
    """Tras cargar el modulo, R016 debe estar en el REGISTRY con la
    metadata correcta: solo IRPF y fases de liquidacion/recurso.
    """
    assert "R016" in REGISTRY, (
        f"R016 no encontrada en REGISTRY. Keys: {list(REGISTRY.keys())}"
    )
    info = REGISTRY["R016"]
    # Solo IRPF — la imputacion de rentas inmobiliarias es especifica de IRPF
    assert info["tributos"] == {"IRPF"}, (
        f"R016 solo debe aplicar a IRPF, got tributos={info['tributos']}"
    )
    # Fases de liquidacion y recurso
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "COMPROBACION_PROPUESTA" in info["fases"]
    assert "COMPROBACION_POST_ALEGACIONES" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
    assert "TEAR_AMPLIACION_POSIBLE" in info["fases"]
    # No debe aplicar a fases sancionadoras
    assert "SANCIONADOR_IMPUESTA" not in info["fases"]
    # REGISTRY en rango permitido [0, 30] tras cargar solo R016
    assert 0 <= len(REGISTRY) <= 30
