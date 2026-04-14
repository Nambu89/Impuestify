"""Tests de la regla R020 — multipagadores_obligacion_declarar (T1B-020).

La regla modela el supuesto del art. 96 LIRPF — obligacion de declarar — en
su redaccion vigente tras la modificacion introducida por el Real Decreto-ley
de 2024 (RDL 4/2024). Para el ejercicio 2024 y siguientes, el limite de
rendimientos del trabajo que obliga a declarar cuando se perciben de mas de
un pagador es de 15.876 EUR (antes 15.000 EUR), siempre que el segundo y
restantes pagadores hayan abonado, en conjunto, mas de 1.500 EUR. El limite
general sigue siendo 22.000 EUR.

La regla dispara cuando la AEAT:

    - Aplica el limite general (22.000 EUR) a un contribuyente que debio
      quedar sometido al limite de multipagadores (15.876 EUR) por superar
      el umbral del segundo pagador.
    - Sanciona por no declarar a un contribuyente cuyos ingresos estan por
      encima del limite actualizado (15.876 EUR) aunque no alcancen el
      limite general.
    - Usa el limite de 22.000 EUR a pesar de que el segundo pagador supero
      los 1.500 EUR (condicion del umbral multipagadores).

La regla NO dispara cuando:

    - El segundo pagador no supera los 1.500 EUR (el limite 22.000 EUR es el
      correcto).
    - Los ingresos totales superan el limite general de 22.000 EUR (el
      contribuyente estaba obligado a declarar con cualquiera de los dos
      limites, no hay conflicto).

Invariante #2 (anti-alucinacion): la regla devuelve una descripcion semantica
libre. La cita canonica ("Art. 96 LIRPF", "RDL 4/2024") la resuelve el
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
from app.services.defensia_rules_engine import REGISTRY, evaluar, reset_registry


# ---------------------------------------------------------------------------
# Helper de aislamiento — carga solo R020 tras el reset del conftest
# ---------------------------------------------------------------------------
#
# El conftest autouse `_aislar_registry` vacia el REGISTRY antes de cada test.
# Como `importlib.import_module` devuelve el modulo cacheado sin re-ejecutar
# el decorador `@regla`, hay que forzar un reload para re-registrar R020 en
# el REGISTRY recien limpiado.

def _cargar_solo_R020() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R020."""
    reset_registry()
    module_name = "app.services.defensia_rules.reglas_irpf.R020_multipagadores"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R020():
    """Garantiza que R020 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R020()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Art. 96 LIRPF", "RDL 4/2024") la resuelve el RAG
    verificador contra el corpus normativo. Aqui solo aceptamos descripciones
    semanticas libres.
    """
    cita_upper = cita.upper()
    assert "Art. 96" not in cita, (
        f"Cita hardcoded detectada: 'Art. 96' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "RDL 4/2024" not in cita, (
        f"Cita hardcoded detectada: 'RDL 4/2024' en '{cita}'."
    )
    assert "96 LIRPF" not in cita_upper, (
        f"Cita hardcoded detectada: '96 LIRPF' en '{cita}'."
    )
    assert "LIRPF" not in cita_upper, (
        f"Cita hardcoded detectada: 'LIRPF' en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: AEAT usa limite 22.000 cuando procede 15.876
# ---------------------------------------------------------------------------

def test_R020_positivo_limite_multipagadores_mal_aplicado(
    build_exp, build_brief, build_doc
):
    """AEAT aplica el limite 22.000 EUR cuando debia aplicar el de 15.876 EUR.

    Contribuyente con dos pagadores, ingresos totales 18.000 EUR. AEAT
    declara que no estaba obligado a presentar IRPF porque aplica el limite
    general (22.000 EUR), pero segun la redaccion actualizada del art. 96
    LIRPF (RDL 4/2024) el limite aplicable a multipagadores es 15.876 EUR,
    y 18.000 > 15.876 -> deberia haber declarado.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "multipagadores": True,
            "ingresos_totales": 18000,
            "limite_aplicado_por_aeat": 22000,
            "limite_real_procedente": 15876,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R020-001",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "He tenido dos pagadores y AEAT me dice que no tenia que haber "
        "presentado la declaracion, pero creo que si estaba obligado con "
        "el limite nuevo."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R020"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("tipo") == "limite_multipagadores_mal_aplicado", (
        f"datos_disparo.tipo inesperado: {disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: sancion por no declarar debajo del umbral real
# ---------------------------------------------------------------------------

def test_R020_positivo_sancion_por_no_declarar_bajo_umbral(
    build_exp, build_brief, build_doc
):
    """Sancion por no declarar a un contribuyente con ingresos < 15.876 EUR.

    Si la AEAT sanciona por falta de presentacion pero los ingresos del
    declarante NO llegan al umbral actualizado del art. 96 LIRPF
    (15.876 EUR en 2024), la sancion carece de base material: no existia
    obligacion de declarar, luego no puede haber infraccion por omisa.
    """
    acuerdo_sancion = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos={
            "ingresos_declarante": 15000,
            "umbral_multipagadores_2024": 15876,
            "ejercicio": 2024,
        },
        doc_id="doc-sancion-R020-002",
        fecha_acto=datetime(2025, 6, 20, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.SANCIONADOR_IMPUESTA,
        docs=[acuerdo_sancion],
    )
    brief = build_brief(
        "Me sancionan por no presentar la renta pero yo no llegaba al limite."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R020"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    # El motivo debe reflejar que el umbral real no se alcanza.
    assert disparo.get("ingresos_declarante") == 15000
    assert disparo.get("umbral_aplicable") == 15876


# ---------------------------------------------------------------------------
# Test 3 — Positivo: limite 22.000 con segundo pagador > 1.500
# ---------------------------------------------------------------------------

def test_R020_positivo_limite_general_con_segundo_pagador_sobre_umbral(
    build_exp, build_brief, build_doc
):
    """AEAT usa 22.000 EUR cuando el segundo pagador supera los 1.500 EUR.

    El art. 96 LIRPF condiciona el uso del limite general (22.000 EUR) a que
    el segundo y restantes pagadores no superen, en conjunto, los 1.500 EUR.
    Si el segundo pagador pago 2.000 EUR, ese umbral se incumple y el limite
    aplicable pasa a ser el de multipagadores (15.876 EUR). Aplicar 22.000
    EUR en ese escenario es un error.
    """
    propuesta = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "segundo_pagador_importe": 2000,
            "limite_aplicado": 22000,
            "ejercicio": 2024,
        },
        doc_id="doc-propuesta-R020-003",
        fecha_acto=datetime(2025, 4, 1, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[propuesta],
    )
    brief = build_brief(
        "En la propuesta de AEAT me aplican el limite de 22.000 pero mi "
        "segundo pagador me abono mas de 1.500 euros."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R020"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("segundo_pagador_importe") == 2000
    assert disparo.get("limite_aplicado") == 22000


# ---------------------------------------------------------------------------
# Test 4 — Negativo: limite 22.000 correctamente aplicado
# ---------------------------------------------------------------------------

def test_R020_negativo_segundo_pagador_bajo_umbral(
    build_exp, build_brief, build_doc
):
    """Segundo pagador <= 1.500 EUR: el limite 22.000 EUR es correcto.

    Si el importe del segundo pagador no supera los 1.500 EUR, la condicion
    del art. 96 LIRPF para usar el limite general (22.000 EUR) se cumple y
    AEAT actua correctamente. R020 NO debe disparar.
    """
    propuesta = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "segundo_pagador_importe": 1200,
            "limite_aplicado": 22000,
            "ejercicio": 2024,
        },
        doc_id="doc-propuesta-R020-004",
        fecha_acto=datetime(2025, 4, 1, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[propuesta],
    )
    brief = build_brief("Tuve dos pagadores pero el segundo apenas 1.200 EUR.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R020 NO deberia disparar cuando el segundo pagador esta bajo el "
        f"umbral de 1.500 EUR, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: ingresos > 22.000 (obligado con cualquier limite)
# ---------------------------------------------------------------------------

def test_R020_negativo_ingresos_superan_limite_general(
    build_exp, build_brief, build_doc
):
    """Ingresos > 22.000 EUR: obligado a declarar con cualquier limite.

    Si los ingresos totales superan incluso el limite general (22.000 EUR),
    el contribuyente estaba obligado a declarar en todo caso y no hay
    conflicto entre el limite aplicado por AEAT y el real. R020 no debe
    disparar porque el debate sobre multipagadores es irrelevante.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "multipagadores": True,
            "ingresos_totales": 30000,
            "limite_aplicado_por_aeat": 22000,
            "limite_real_procedente": 15876,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R020-005",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Dos pagadores, ingresos totales 30.000 euros.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R020 NO deberia disparar cuando los ingresos totales superan "
        f"el limite general (22.000 EUR), got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: asercion explicita sobre la cita semantica
# ---------------------------------------------------------------------------

def test_R020_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: la cita normativa NO puede contener el articulo canonico."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "multipagadores": True,
            "ingresos_totales": 18000,
            "limite_aplicado_por_aeat": 22000,
            "limite_real_procedente": 15876,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R020-006",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Defiende mi caso de multipagadores.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1
    arg = candidatos[0]

    cita = arg.cita_normativa_propuesta
    assert (
        "Art. 96" not in cita
        and "RDL 4/2024" not in cita
        and "96 LIRPF" not in cita.upper()
    ), (
        f"La cita normativa debe ser semantica, got: {cita!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Smoke de registro: R020 aparece en el REGISTRY tras el reload
# ---------------------------------------------------------------------------

def test_R020_registrada_en_registry():
    """El reload del modulo R020 debe auto-registrar la regla en el REGISTRY."""
    assert "R020" in REGISTRY, (
        f"R020 no aparece en el REGISTRY tras reload. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R020"]
    assert "IRPF" in info["tributos"], (
        f"R020 debe aplicar a IRPF, tributos={info['tributos']}"
    )
    # Obligacion de declarar es especifica de IRPF, no se extiende a otros tributos.
    assert "IVA" not in info["tributos"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "SANCIONADOR_IMPUESTA" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
