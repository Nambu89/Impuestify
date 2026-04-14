"""Tests de la regla R021 — iva_prorrata (T1B-021).

La regla modela el regimen de prorrata en el Impuesto sobre el Valor Anadido
conforme a los arts. 102 a 106 LIVA. La prorrata general se aplica por defecto,
pero el art. 106 LIVA impone la prorrata especial de forma obligatoria cuando
la deduccion resultante de la aplicacion de la general exceda en un 10 % o mas
a la que se obtendria aplicando la especial. El Tribunal Supremo ha calificado
la eleccion entre general y especial como una autentica opcion tributaria.

La regla dispara cuando la AEAT:

    - Aplica la prorrata general a un sujeto pasivo pese a que la deduccion
      resultante de la general excedia en mas del 10 % a la que se habria
      obtenido con la especial (especial obligatoria no reconocida).
    - Deniega la opcion del sujeto pasivo por la prorrata especial sin
      analizar previamente si concurrian los supuestos de obligatoriedad
      del art. 106 LIVA.

La regla NO dispara cuando:

    - La deduccion por prorrata general y la especial difieren en menos
      del 10 % (umbral de obligatoriedad no alcanzado, se puede mantener
      la general).
    - El sujeto pasivo ya tiene aplicada la prorrata especial (no hay
      conflicto vivo).
    - El tributo del expediente no es IVA.

Invariante #2 (anti-alucinacion): la regla devuelve una cita semantica libre.
La cita canonica ("Art. 102 LIVA", "art. 106 LIVA") la resuelve el
``defensia_rag_verifier`` contra el corpus normativo, nunca este modulo.
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
from app.services.defensia_rules_engine import evaluar, reset_registry


# ---------------------------------------------------------------------------
# Helper de aislamiento — carga solo R021 tras el reset del conftest
# ---------------------------------------------------------------------------
#
# El conftest autouse `_aislar_registry` vacia el REGISTRY antes de cada test.
# Como `importlib.import_module` devuelve el modulo cacheado sin re-ejecutar
# el decorador `@regla`, hay que forzar un reload para re-registrar R021 en
# el REGISTRY recien limpiado.

def _cargar_solo_R021() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R021."""
    reset_registry()
    module_name = "app.services.defensia_rules.reglas_otros_tributos.R021_iva_prorrata"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R021():
    """Garantiza que R021 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R021()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica."""
    assert "Art. 102" not in cita, (
        f"Cita hardcoded detectada: 'Art. 102' en '{cita}'."
    )
    assert "art. 106 liva" not in cita.lower(), (
        f"Cita hardcoded detectada: 'art. 106 liva' en '{cita}'."
    )
    assert "102 LIVA" not in cita.upper(), (
        f"Cita hardcoded detectada: '102 LIVA' en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: especial obligatoria no aplicada (diff 20 % > 10 %)
# ---------------------------------------------------------------------------

def test_R021_positivo_especial_obligatoria_no_aplicada(
    build_exp, build_brief, build_doc
):
    """Deduccion general 100.000 vs especial 80.000 — diff 25 % > 10 %.

    La AEAT ha aplicado la prorrata general cuando la deduccion resultante
    excedia en mas del 10 % a la especial. El art. 106 LIVA obliga en este
    caso a aplicar la prorrata especial, por lo que R021 debe disparar.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "prorrata_general_aplicada": True,
            "prorrata_especial_obligatoria": True,
            "deduccion_general": 100000,
            "deduccion_especial": 80000,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R021-001",
        fecha_acto=datetime(2025, 6, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "AEAT me aplica la prorrata general pese a que la especial me daba "
        "bastante menos deduccion y creo que era obligatoria."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R021"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("deduccion_general") == 100000
    assert disparo.get("deduccion_especial") == 80000


# ---------------------------------------------------------------------------
# Test 2 — Positivo: opcion especial denegada sin analizar obligatoriedad
# ---------------------------------------------------------------------------

def test_R021_positivo_opcion_especial_denegada_sin_analisis(
    build_exp, build_brief, build_doc
):
    """AEAT deniega la opcion por prorrata especial sin analisis de obligatoriedad.

    El sujeto pasivo solicito la aplicacion de la prorrata especial, la AEAT
    la deniega pero no analiza si se superaba el umbral del 10 % que hace
    obligatoria la especial conforme al art. 106 LIVA. Defecto de motivacion
    material: R021 debe disparar.
    """
    propuesta = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "tributo": "IVA",
            "especial_solicitada": True,
            "especial_denegada": True,
            "analisis_obligatoriedad": False,
            "ejercicio": 2024,
        },
        doc_id="doc-propuesta-R021-002",
        fecha_acto=datetime(2025, 5, 5, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[propuesta],
    )
    brief = build_brief(
        "Pedi acogerme a la prorrata especial y me la denegaron sin mas "
        "explicaciones."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R021"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("especial_solicitada") is True
    assert disparo.get("especial_denegada") is True
    assert disparo.get("analisis_obligatoriedad") is False


# ---------------------------------------------------------------------------
# Test 3 — Negativo: general correctamente aplicada (diff 5 % < 10 %)
# ---------------------------------------------------------------------------

def test_R021_negativo_general_correcta_diferencia_bajo_umbral(
    build_exp, build_brief, build_doc
):
    """Deduccion general 100.000 vs especial 95.000 — diff 5 % < 10 %.

    La diferencia entre prorrata general y especial es inferior al umbral
    del 10 %, por lo que la especial no es obligatoria y la general aplicada
    por la AEAT es correcta. R021 NO debe disparar.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "prorrata_general_aplicada": True,
            "deduccion_general": 100000,
            "deduccion_especial": 95000,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R021-003",
        fecha_acto=datetime(2025, 6, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Me aplican la prorrata general.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R021 NO deberia disparar cuando la diferencia entre general y "
        f"especial es inferior al 10 %, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: especial ya aplicada (no hay conflicto)
# ---------------------------------------------------------------------------

def test_R021_negativo_especial_ya_aplicada(
    build_exp, build_brief, build_doc
):
    """La prorrata especial ya esta aplicada: no hay controversia.

    Si la AEAT ha aplicado directamente la prorrata especial, no existe
    conflicto que defender y R021 no debe disparar aunque la diferencia
    con la general fuese grande.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "prorrata_especial_aplicada": True,
            "deduccion_general": 100000,
            "deduccion_especial": 80000,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R021-004",
        fecha_acto=datetime(2025, 6, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Me han aplicado la prorrata especial.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R021 NO deberia disparar cuando la especial ya esta aplicada, "
        f"got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: tributo distinto de IVA
# ---------------------------------------------------------------------------

def test_R021_negativo_tributo_no_es_iva(
    build_exp, build_brief, build_doc
):
    """Expediente IRPF: la regla R021 solo aplica a IVA.

    El motor filtra por tributo antes de invocar la regla, de modo que un
    expediente cuyo tributo no es IVA nunca debe disparar R021.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IRPF",
            "prorrata_general_aplicada": True,
            "prorrata_especial_obligatoria": True,
            "deduccion_general": 100000,
            "deduccion_especial": 80000,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R021-005",
        fecha_acto=datetime(2025, 6, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Caso IRPF, nada que ver con IVA.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R021 NO deberia disparar cuando el tributo no es IVA, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: asercion explicita sobre la cita semantica
# ---------------------------------------------------------------------------

def test_R021_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: la cita normativa NO puede contener el articulo canonico."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IVA",
            "prorrata_general_aplicada": True,
            "prorrata_especial_obligatoria": True,
            "deduccion_general": 100000,
            "deduccion_especial": 80000,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R021-006",
        fecha_acto=datetime(2025, 6, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Defiende mi caso de prorrata IVA.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1
    arg = candidatos[0]

    cita = arg.cita_normativa_propuesta
    assert (
        "Art. 102" not in cita
        and "art. 106 liva" not in cita.lower()
        and "102 LIVA" not in cita.upper()
    ), (
        f"La cita normativa debe ser semantica, got: {cita!r}"
    )


