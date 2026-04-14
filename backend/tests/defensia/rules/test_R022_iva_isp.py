"""Tests de la regla R022 — iva_inversion_sujeto_pasivo (T1B-022).

La regla modela el supuesto del art. 84.Uno.2.o LIVA — inversion del sujeto
pasivo en operaciones interiores — en sus cuatro ramas clasicas:

    - Ejecuciones de garantia inmobiliaria (dacion en pago, subasta).
    - Renuncia a exenciones inmobiliarias del art. 20 LIVA (segundas y
      ulteriores transmisiones de edificaciones, terrenos rusticos, etc.).
    - Entregas en el seno de un procedimiento concursal.
    - Ejecuciones de obra de urbanizacion o rehabilitacion de edificaciones.

En todos estos supuestos, quien debe repercutir e ingresar el IVA NO es el
transmitente sino el adquirente (inversion del sujeto pasivo). La regla
dispara cuando la AEAT liquida IVA no repercutido al transmitente ignorando
que la operacion estaba sujeta a ISP: en ese escenario el IVA lo debia haber
autorrepercutido el adquirente (con derecho simultaneo a deduccion en muchos
casos), y la liquidacion al transmitente carece de base.

La regla NO dispara cuando:

    - El contribuyente ya aplico ISP correctamente (``isp_aplicado=True``).
    - Se trata de una operacion ordinaria no sujeta a ISP (``venta_ordinaria``).

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica ("Art. 84 LIVA", "84.Uno.2.o") la
resuelve el ``defensia_rag_verifier`` contra el corpus normativo. Por eso
aqui no aparecen literales del articulado — solo terminos descriptivos del
supuesto.
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
# Helper de aislamiento — carga solo R022 tras el reset del conftest
# ---------------------------------------------------------------------------

def _cargar_solo_R022() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R022."""
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_otros_tributos."
        "R022_iva_inversion_sujeto_pasivo"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R022():
    """Garantiza que R022 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R022()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Art. 84 LIVA", "84.Uno.2.o") la resuelve el RAG
    verificador contra el corpus normativo. Aqui solo aceptamos descripciones
    semanticas libres del supuesto de ISP.
    """
    assert "Art. 84" not in cita, (
        f"Cita hardcoded detectada: 'Art. 84' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "84.Uno.2" not in cita, (
        f"Cita hardcoded detectada: '84.Uno.2' en '{cita}'."
    )
    assert "art. 84 liva" not in cita.lower(), (
        f"Cita hardcoded detectada: 'art. 84 liva' en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: ejecucion de garantia inmobiliaria sin ISP
# ---------------------------------------------------------------------------

def test_R022_positivo_ejecucion_garantia_inmobiliaria(
    build_exp, build_brief, build_doc
):
    """AEAT liquida IVA al transmitente en ejecucion de garantia inmobiliaria.

    Supuesto tipico: dacion en pago / adjudicacion en subasta de un inmueble
    hipotecado. El adquirente (entidad financiera, fondo) es quien debe
    autorrepercutir el IVA mediante ISP. Si AEAT liquida al transmitente
    porque no repercutio IVA, esta ignorando la inversion del sujeto pasivo.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tipo_operacion": "ejecucion_garantia_inmobiliaria",
            "iva_repercutido_por_transmitente": True,
            "aeat_liquida_iva_no_repercutido": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R022-001",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "AEAT me liquida IVA por una dacion en pago de un inmueble hipotecado "
        "cuando deberia haberlo autorrepercutido el banco adquirente."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R022"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("tipo_operacion") == "ejecucion_garantia_inmobiliaria"


# ---------------------------------------------------------------------------
# Test 2 — Positivo: renuncia a exencion del art. 20 sin ISP
# ---------------------------------------------------------------------------

def test_R022_positivo_renuncia_exencion_inmobiliaria(
    build_exp, build_brief, build_doc
):
    """AEAT liquida IVA al transmitente en renuncia a exencion inmobiliaria.

    Cuando el transmitente renuncia a la exencion del art. 20 LIVA (segundas
    y ulteriores entregas de edificaciones, terrenos no edificables, etc.),
    la LIVA somete la operacion a ISP: el adquirente es quien autorrepercute.
    Si AEAT liquida al transmitente por no haber repercutido IVA, esta
    ignorando la inversion del sujeto pasivo que opera por ministerio de la
    ley tras la renuncia.
    """
    propuesta = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "tipo_operacion": "renuncia_exencion_inmobiliaria",
            "iva_repercutido_por_transmitente": True,
            "ejercicio": 2024,
        },
        doc_id="doc-propuesta-R022-002",
        fecha_acto=datetime(2025, 4, 1, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[propuesta],
    )
    brief = build_brief(
        "Vendi una nave industrial renunciando a la exencion del IVA y "
        "AEAT me reclama el IVA cuando deberia haberlo ingresado el comprador."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R022"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("tipo_operacion") == "renuncia_exencion_inmobiliaria"


# ---------------------------------------------------------------------------
# Test 3 — Positivo: entrega en procedimiento concursal sin ISP
# ---------------------------------------------------------------------------

def test_R022_positivo_entrega_concurso(
    build_exp, build_brief, build_doc
):
    """AEAT liquida IVA al transmitente en entrega realizada en concurso.

    En las entregas de bienes y prestaciones de servicios realizadas por un
    concursado dentro del procedimiento concursal, la LIVA somete la
    operacion a ISP: el adquirente autorrepercute. Si AEAT liquida al
    concursado por no repercutir IVA, esta ignorando la inversion del sujeto
    pasivo propia del concurso.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tipo_operacion": "entrega_concurso",
            "iva_repercutido_por_transmitente": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R022-003",
        fecha_acto=datetime(2025, 6, 15, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.TEAR_INTERPUESTA,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Estoy en concurso de acreedores y AEAT me reclama IVA de unas "
        "entregas cuando el adquirente deberia haber aplicado ISP."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R022"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("tipo_operacion") == "entrega_concurso"


# ---------------------------------------------------------------------------
# Test 4 — Negativo: ISP correctamente aplicado
# ---------------------------------------------------------------------------

def test_R022_negativo_isp_aplicado(
    build_exp, build_brief, build_doc
):
    """Si el contribuyente ya aplico ISP correctamente, R022 NO dispara.

    La regla solo defiende al contribuyente cuando la Administracion ha
    ignorado la ISP. Si la ISP esta correctamente aplicada, no hay nada que
    defender y la regla debe permanecer silente.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tipo_operacion": "ejecucion_garantia_inmobiliaria",
            "iva_repercutido_por_transmitente": False,
            "isp_aplicado": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R022-004",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("ISP aplicada correctamente, ya autorrepercuti.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R022 NO deberia disparar cuando la ISP esta correctamente "
        f"aplicada, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: operacion ordinaria no sujeta a ISP
# ---------------------------------------------------------------------------

def test_R022_negativo_operacion_ordinaria(
    build_exp, build_brief, build_doc
):
    """Operaciones ordinarias (venta regular B2B/B2C) NO estan sujetas a ISP.

    Las ventas ordinarias siguen el regimen general de IVA: el transmitente
    repercute e ingresa. Si AEAT liquida IVA no repercutido en una venta
    ordinaria, puede haber un problema distinto (omision de facturacion,
    deduccion, etc.) pero NO es un supuesto de ISP. R022 debe permanecer
    silente para dejar paso a otras reglas.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tipo_operacion": "venta_ordinaria",
            "iva_repercutido_por_transmitente": False,
            "aeat_liquida_iva_no_repercutido": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R022-005",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Venta normal entre empresas, me reclaman IVA.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R022 NO deberia disparar en operaciones ordinarias no sujetas a "
        f"ISP, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: la cita es semantica
# ---------------------------------------------------------------------------

def test_R022_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: la cita normativa NO puede contener el articulo canonico.

    El RAG verificador resuelve la cita canonica a posteriori contra el
    corpus normativo. La regla solo puede devolver una descripcion semantica
    libre del supuesto.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tipo_operacion": "ejecucion_garantia_inmobiliaria",
            "iva_repercutido_por_transmitente": True,
            "aeat_liquida_iva_no_repercutido": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R022-006",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Defiende mi caso de ISP en ejecucion de garantia.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1
    arg = candidatos[0]

    cita = arg.cita_normativa_propuesta
    assert (
        "Art. 84" not in cita
        and "84.Uno.2" not in cita
        and "art. 84 liva" not in cita.lower()
    ), (
        f"La cita normativa debe ser semantica, got: {cita!r}"
    )
