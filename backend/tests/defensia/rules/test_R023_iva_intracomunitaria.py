"""Tests de la regla R023 — iva_intracomunitaria (T1B-023).

La regla modela el supuesto del art. 25 LIVA (exencion de las entregas
intracomunitarias de bienes — EIB) leido en conjunto con el art. 15 LIVA
(adquisiciones intracomunitarias — AIB) y, sobre todo, la doctrina del
Tribunal de Justicia de la Union Europea en el asunto C-146/05 Collee: los
requisitos formales (alta del adquirente en VIES, correcta inclusion en el
modelo 349) NO pueden prevalecer sobre los requisitos materiales (transporte
efectivo al territorio de otro Estado miembro y condicion de empresario o
profesional del destinatario) cuando estos ultimos estan acreditados.

La regla dispara cuando la AEAT deniega la exencion de una EIB:

    - Por no constar el NIF-IVA del adquirente en VIES pese a que el
      transporte a otro Estado miembro se acredita y el destinatario es
      empresario o profesional comunitario.
    - Por un error formal en el modelo 349 (omision, diferencia de importe
      o perido equivocado) cuando los requisitos materiales estan
      acreditados.

La regla NO dispara cuando:

    - No consta transporte efectivo al territorio de otro Estado miembro
      (el requisito material no se cumple: la denegacion de exencion es
      legitima).
    - El destinatario no es empresario o profesional de la UE (decae la
      estructura B2B que habilita la exencion).
    - La AEAT no ha denegado la exencion — no hay conflicto que defender.

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica ("Art. 25 LIVA", "STJUE C-146/05
Collee") la resuelve el ``defensia_rag_verifier`` contra el corpus
normativo, nunca este modulo.
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
# Helper de aislamiento — carga solo R023 tras el reset del conftest
# ---------------------------------------------------------------------------
#
# El conftest autouse `_aislar_registry` vacia el REGISTRY antes de cada test.
# Como `importlib.import_module` devuelve el modulo cacheado sin re-ejecutar
# el decorador `@regla`, hay que forzar un reload para re-registrar R023 en
# el REGISTRY recien limpiado.

def _cargar_solo_R023() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R023."""
    reset_registry()
    module_name = (
        "app.services.defensia_rules."
        "reglas_otros_tributos.R023_iva_intracomunitaria"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R023():
    """Garantiza que R023 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R023()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Art. 25 LIVA", "STJUE C-146/05 Collee") la resuelve el
    RAG verificador contra el corpus normativo. Aqui solo aceptamos
    descripciones semanticas libres del supuesto.
    """
    cita_upper = cita.upper()
    assert "Art. 25" not in cita, (
        f"Cita hardcoded detectada: 'Art. 25' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "TJUE" not in cita_upper, (
        f"Cita hardcoded detectada: 'TJUE' en '{cita}'."
    )
    assert "C-146" not in cita, (
        f"Cita hardcoded detectada: 'C-146' en '{cita}'."
    )
    assert "COLLEE" not in cita_upper, (
        f"Cita hardcoded detectada: 'Collee' en '{cita}'."
    )
    assert "LIVA" not in cita_upper, (
        f"Cita hardcoded detectada: 'LIVA' en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: denegacion por NIF-VIES con transporte acreditado
# ---------------------------------------------------------------------------

def test_R023_positivo_denegacion_por_falta_nif_vies_con_transporte_acreditado(
    build_exp, build_brief, build_doc
):
    """AEAT deniega la exencion por ausencia de NIF en VIES pese a transporte.

    El empresario espanol vende a un adquirente UE que materialmente es
    empresario, pero en el momento de la operacion su NIF-IVA no figura en
    el censo VIES. El transporte al otro Estado miembro esta acreditado con
    CMR y carta de porte. AEAT niega la exencion del art. 25 LIVA por el
    defecto formal. Doctrina Collee: los requisitos materiales prevalecen
    sobre los formales cuando estan plenamente acreditados -> R023 dispara.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_exencion_EIB": True,
            "nif_vies_ausente": True,
            "transporte_efectivo_acreditado": True,
            "destinatario_empresario_UE": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R023-001",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Me deniegan la exencion de una entrega intracomunitaria porque "
        "el cliente no figuraba en VIES el dia de la factura, pero tengo "
        "CMR firmado que acredita el transporte a Francia."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R023"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("tipo") == "exencion_EIB_denegada_por_forma", (
        f"datos_disparo.tipo inesperado: {disparo!r}"
    )
    assert disparo.get("nif_vies_ausente") is True
    assert disparo.get("transporte_efectivo_acreditado") is True
    assert disparo.get("destinatario_empresario_UE") is True


# ---------------------------------------------------------------------------
# Test 2 — Positivo: error formal modelo 349 con requisitos materiales OK
# ---------------------------------------------------------------------------

def test_R023_positivo_error_modelo_349_con_requisitos_materiales_cumplidos(
    build_exp, build_brief, build_doc
):
    """AEAT deniega la exencion por un error en el modelo 349.

    La entrega intracomunitaria se realizo correctamente (transporte
    efectivo a Alemania, destinatario empresario con NIF-VIES valido) pero
    el contribuyente omitio la operacion en el modelo 349 del trimestre.
    AEAT deniega la exencion del art. 25 LIVA por incumplimiento formal.
    Doctrina Collee: el defecto formal no puede impedir la exencion si los
    requisitos materiales estan acreditados -> R023 dispara.
    """
    propuesta = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "denegacion_exencion_EIB": True,
            "error_modelo_349": True,
            "transporte_efectivo_acreditado": True,
            # `destinatario_empresario_UE` por defecto True en este caso:
            # el error es solo formal en el 349.
            "destinatario_empresario_UE": True,
            "ejercicio": 2024,
        },
        doc_id="doc-propuesta-R023-002",
        fecha_acto=datetime(2025, 6, 15, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[propuesta],
    )
    brief = build_brief(
        "Se me olvido incluir una venta intracomunitaria en el 349 y "
        "ahora AEAT me quiere cobrar el IVA como si no fuera exenta."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R023"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("error_modelo_349") is True
    assert disparo.get("transporte_efectivo_acreditado") is True


# ---------------------------------------------------------------------------
# Test 3 — Negativo: sin transporte efectivo acreditado
# ---------------------------------------------------------------------------

def test_R023_negativo_sin_transporte_efectivo_acreditado(
    build_exp, build_brief, build_doc
):
    """Transporte NO acreditado: la denegacion de AEAT es legitima.

    La doctrina Collee solo desactiva los defectos formales cuando los
    requisitos materiales estan acreditados. Si el sujeto pasivo NO puede
    acreditar el transporte efectivo al territorio de otro Estado miembro,
    el requisito material falla y la exencion del art. 25 LIVA no resulta
    aplicable. R023 NO debe disparar porque no hay defensa que construir.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_exencion_EIB": True,
            "nif_vies_ausente": True,
            "transporte_efectivo_acreditado": False,
            "destinatario_empresario_UE": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R023-003",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "AEAT me deniega la exencion y no tengo CMR ni carta de porte."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        "R023 NO deberia disparar cuando el transporte efectivo no esta "
        f"acreditado (requisito material legitimo), got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: destinatario no es empresario UE
# ---------------------------------------------------------------------------

def test_R023_negativo_destinatario_no_es_empresario_UE(
    build_exp, build_brief, build_doc
):
    """Destinatario NO empresario: decae la estructura B2B exigida.

    La exencion del art. 25 LIVA presupone que el adquirente es un
    empresario o profesional identificado a efectos del IVA en otro Estado
    miembro. Si el destinatario es un particular o un no empresario, la
    operacion deja de ser una EIB y pasa al regimen general de ventas a
    distancia o entregas interiores. R023 no debe disparar.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_exencion_EIB": True,
            "nif_vies_ausente": True,
            "transporte_efectivo_acreditado": True,
            "destinatario_empresario_UE": False,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R023-004",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Vendi a un particular frances y me dicen que no es EIB."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        "R023 NO deberia disparar cuando el destinatario no es empresario "
        f"o profesional identificado en la UE, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: exencion ya admitida, no hay denegacion
# ---------------------------------------------------------------------------

def test_R023_negativo_exencion_ya_admitida(
    build_exp, build_brief, build_doc
):
    """Si no hay denegacion de exencion, no hay conflicto que defender.

    Puede que la liquidacion trate de otra cuestion (p.ej. deduciblidad de
    cuotas soportadas) y el bloque intracomunitario no se discuta. En ese
    caso los flags de transporte y destinatario son irrelevantes: R023 solo
    tiene sentido cuando AEAT rechaza expresamente la exencion del art. 25.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_exencion_EIB": False,
            "nif_vies_ausente": True,
            "transporte_efectivo_acreditado": True,
            "destinatario_empresario_UE": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R023-005",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "La liquidacion no toca mis ventas intracomunitarias."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        "R023 NO deberia disparar cuando la exencion de la EIB no esta "
        f"siendo denegada por la Administracion, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: asercion explicita sobre la cita semantica
# ---------------------------------------------------------------------------

def test_R023_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: la cita normativa NO puede contener el articulo canonico."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "denegacion_exencion_EIB": True,
            "nif_vies_ausente": True,
            "transporte_efectivo_acreditado": True,
            "destinatario_empresario_UE": True,
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-R023-006",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IVA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Defiende mi caso de entrega intracomunitaria.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1
    arg = candidatos[0]

    cita = arg.cita_normativa_propuesta
    assert (
        "Art. 25" not in cita
        and "TJUE" not in cita
        and "C-146" not in cita
        and "Collee" not in cita
    ), (
        f"La cita normativa debe ser semantica, got: {cita!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Smoke de registro: R023 aparece en el REGISTRY tras el reload
# ---------------------------------------------------------------------------

def test_R023_registrada_en_registry():
    """El reload del modulo R023 debe auto-registrar la regla en el REGISTRY."""
    assert "R023" in REGISTRY, (
        f"R023 no aparece en el REGISTRY tras reload. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R023"]
    assert "IVA" in info["tributos"], (
        f"R023 debe aplicar a IVA, tributos={info['tributos']}"
    )
    # La regla de intracomunitaria es especifica de IVA — no se extiende a IRPF.
    assert "IRPF" not in info["tributos"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "COMPROBACION_PROPUESTA" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
