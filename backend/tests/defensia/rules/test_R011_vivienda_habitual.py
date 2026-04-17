"""Tests de la regla R011 — vivienda_habitual_excepcion_separacion (T1B-011).

La regla modela la defensa principal del caso David Oliva: AEAT deniega la
exencion por reinversion en vivienda habitual alegando que el contribuyente
no ha cumplido el plazo continuado de 3 anos de residencia (art. 41 bis.1
RIRPF parrafo 1), pero existe una sentencia judicial que modifica medidas
familiares por separacion matrimonial y que activa la excepcion del parrafo 2
del mismo articulo ("circunstancias que necesariamente exijan el cambio de
domicilio, tales como separacion matrimonial").

Fases aplicables (segun enum real `Fase` en `app/models/defensia.py`):
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - COMPROBACION_PROPUESTA / COMPROBACION_POST_ALEGACIONES
    - SANCIONADOR_INICIADO / SANCIONADOR_PROPUESTA / SANCIONADOR_IMPUESTA
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Invariante #2 (anti-alucinacion): la regla devuelve una descripcion semantica
libre. La cita canonica ("art. 41 bis.1 parrafo 2 RIRPF", "STS 553/2023 de
5-5-2023") la resuelve el `defensia_rag_verifier` contra el corpus normativo,
nunca este modulo.
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
# Helper de aislamiento — carga solo R011 tras el reset del conftest
# ---------------------------------------------------------------------------
#
# El conftest autouse `_aislar_registry` vacia el REGISTRY antes de cada test.
# Como `importlib.import_module` devuelve el modulo cacheado sin re-ejecutar
# el decorador `@regla`, hay que forzar un reload para re-registrar R011 en
# el REGISTRY recien limpiado. Patron validado por los agents del Grupo A.

def _cargar_solo_R011() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R011."""
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_irpf.R011_vivienda_habitual_excepcion"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R011():
    """Garantiza que R011 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R011()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear el articulo canonico.

    La cita final ("Art. 41 bis RIRPF", "STS 553/2023") la resuelve el RAG
    verificador contra el corpus normativo. Aqui solo aceptamos descripciones
    semanticas libres.
    """
    cita_lower = cita.lower()
    assert "Art. 41 bis" not in cita, (
        f"Cita hardcoded detectada: 'Art. 41 bis' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "art. 41 bis" not in cita_lower, (
        f"Cita hardcoded detectada: 'art. 41 bis' en '{cita}'."
    )
    assert "STS 553/2023" not in cita, (
        f"Cita hardcoded detectada: 'STS 553/2023' en '{cita}'."
    )
    assert "sts 553/2023" not in cita_lower, (
        f"Cita hardcoded detectada: 'sts 553/2023' en '{cita}'."
    )
    assert "art. 38" not in cita_lower, (
        f"Cita hardcoded detectada: 'art. 38' en '{cita}'."
    )
    assert "rirpf" not in cita_lower, (
        f"Cita hardcoded detectada: 'rirpf' en '{cita}'."
    )


def _docs_caso_david(build_doc, *, incluir_sentencia: bool = True):
    """Construye el conjunto de documentos del caso David Oliva.

    - Liquidacion provisional AEAT denegando la exencion por reinversion
      sobre la base de que la residencia fue inferior a 3 anos.
    - Sentencia judicial que modifica medidas familiares por separacion
      matrimonial (fecha 2024-06-28).
    - Escritura con fechas de adquisicion (2022-05-12) y transmision
      (2024-10-22), marcada como vivienda habitual.

    Total residencia: ~2 anos 5 meses (< 3 anos del parrafo 1), pero con
    sentencia de crisis matrimonial que activa la excepcion del parrafo 2.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deniega_exencion_reinversion": True,
            "motivo_denegacion": "residencia_inferior_3_anos",
            "tributo": "IRPF",
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-001",
        nombre_original="liquidacion_provisional_irpf_2024.pdf",
        fecha_acto=datetime(2025, 3, 15, tzinfo=timezone.utc),
    )
    escritura = build_doc(
        TipoDocumento.ESCRITURA,
        datos={
            "fecha_adquisicion": "2022-05-12",
            "fecha_transmision": "2024-10-22",
            "es_vivienda_habitual": True,
        },
        doc_id="doc-escritura-001",
        nombre_original="escritura_vivienda_habitual.pdf",
        fecha_acto=datetime(2024, 10, 22, tzinfo=timezone.utc),
    )
    docs = [liquidacion, escritura]

    if incluir_sentencia:
        sentencia = build_doc(
            TipoDocumento.SENTENCIA_JUDICIAL,
            datos={
                "fecha_sentencia": "2024-06-28",
                "modifica_medidas_familiares": True,
                "causa": "separacion_matrimonial",
            },
            doc_id="doc-sentencia-001",
            nombre_original="sentencia_modificacion_medidas.pdf",
            fecha_acto=datetime(2024, 6, 28, tzinfo=timezone.utc),
        )
        docs.append(sentencia)

    return docs


# ---------------------------------------------------------------------------
# Test 1 — Positivo caso David: denegacion + sentencia + residencia < 3 anos
# ---------------------------------------------------------------------------

def test_R011_positivo_caso_david_dispara_por_excepcion_familiar(
    build_exp, build_brief, build_doc
):
    """Caso ground truth David Oliva.

    AEAT deniega la exencion por reinversion porque la residencia efectiva fue
    de ~2 anos 5 meses. Sin embargo, existe una sentencia de modificacion de
    medidas familiares por separacion matrimonial que activa la excepcion al
    plazo continuado de 3 anos. R011 debe disparar con una descripcion
    semantica libre (sin hardcodear el articulo canonico).
    """
    docs = _docs_caso_david(build_doc, incluir_sentencia=True)
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=docs,
    )
    brief = build_brief(
        "AEAT me deniega la exencion por reinversion en vivienda habitual "
        "porque residi menos de 3 anos, pero tuve una sentencia de separacion "
        "que me obligo a dejar la casa."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R011"

    # La cita debe ser semantica, NO hardcoded.
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    cita_lower = arg.cita_normativa_propuesta.lower()
    assert "vivienda habitual" in cita_lower, (
        f"La cita semantica debe mencionar 'vivienda habitual', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )
    assert "tres anos" in cita_lower or "3 anos" in cita_lower, (
        f"La cita semantica debe mencionar el plazo de tres anos, got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    # datos_disparo debe exponer la causa y la fecha de la sentencia.
    disparo = arg.datos_disparo
    assert disparo.get("causa_excepcional") == "separacion_matrimonial", (
        f"datos_disparo.causa_excepcional inesperado: {disparo!r}"
    )
    assert disparo.get("fecha_sentencia") == "2024-06-28", (
        f"datos_disparo.fecha_sentencia inesperada: {disparo!r}"
    )
    dias_residencia = disparo.get("dias_residencia")
    assert isinstance(dias_residencia, int), (
        f"datos_disparo.dias_residencia debe ser int, got: {dias_residencia!r}"
    )
    # 2022-05-12 -> 2024-10-22 = 894 dias (< 1095 del plazo de 3 anos)
    assert 850 <= dias_residencia <= 950, (
        f"dias_residencia fuera de rango esperado (~894): {dias_residencia}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Negativo: denegacion + residencia corta, pero SIN sentencia
# ---------------------------------------------------------------------------

def test_R011_negativo_sin_sentencia_familiar(build_exp, build_brief, build_doc):
    """Sin sentencia de crisis matrimonial NO hay prueba de la excepcion.

    Aunque la residencia sea inferior a 3 anos y AEAT haya denegado la
    exencion, sin la sentencia judicial el argumento del parrafo 2 no tiene
    base probatoria y R011 no debe disparar (defenderlo seria inventar
    hechos).
    """
    docs = _docs_caso_david(build_doc, incluir_sentencia=False)
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=docs,
    )
    brief = build_brief(
        "Me denegaron la exencion porque estuve solo 2 anos y 5 meses."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R011 NO deberia disparar sin sentencia de crisis matrimonial, "
        f"got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: residencia cumple los 3 anos del parrafo 1
# ---------------------------------------------------------------------------

def test_R011_negativo_residencia_cumple_3_anos(
    build_exp, build_brief, build_doc
):
    """Si la residencia continuada alcanza los 3 anos, la exencion ya aplica
    por el parrafo 1 del art. 41 bis RIRPF. No hay conflicto que resolver y
    R011 no debe disparar."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deniega_exencion_reinversion": True,
            "motivo_denegacion": "residencia_inferior_3_anos",
            "tributo": "IRPF",
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-002",
        fecha_acto=datetime(2025, 3, 15, tzinfo=timezone.utc),
    )
    # 4 anos de residencia continuada -> cumple el plazo, sin excepcion.
    escritura = build_doc(
        TipoDocumento.ESCRITURA,
        datos={
            "fecha_adquisicion": "2020-01-15",
            "fecha_transmision": "2024-02-01",
            "es_vivienda_habitual": True,
        },
        doc_id="doc-escritura-002",
        fecha_acto=datetime(2024, 2, 1, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion, escritura],
    )
    brief = build_brief("Vendi mi vivienda habitual tras mas de 4 anos viviendo en ella.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R011 NO deberia disparar cuando la residencia cumple el plazo, "
        f"got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: denegacion por otra razon distinta al plazo
# ---------------------------------------------------------------------------

def test_R011_negativo_denegacion_por_otra_razon(
    build_exp, build_brief, build_doc
):
    """Si AEAT deniega la exencion por un motivo distinto al plazo de 3 anos
    (p.ej. reinversion parcial o fuera de plazo de reinversion), R011 esta
    fuera de su alcance y no debe disparar."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deniega_exencion_reinversion": True,
            "motivo_denegacion": "reinversion_parcial",
            "tributo": "IRPF",
            "ejercicio": 2024,
        },
        doc_id="doc-liquidacion-003",
        fecha_acto=datetime(2025, 3, 15, tzinfo=timezone.utc),
    )
    escritura = build_doc(
        TipoDocumento.ESCRITURA,
        datos={
            "fecha_adquisicion": "2022-05-12",
            "fecha_transmision": "2024-10-22",
            "es_vivienda_habitual": True,
        },
        doc_id="doc-escritura-003",
        fecha_acto=datetime(2024, 10, 22, tzinfo=timezone.utc),
    )
    sentencia = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "fecha_sentencia": "2024-06-28",
            "modifica_medidas_familiares": True,
            "causa": "separacion_matrimonial",
        },
        doc_id="doc-sentencia-003",
        fecha_acto=datetime(2024, 6, 28, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion, escritura, sentencia],
    )
    brief = build_brief(
        "La AEAT me deniega la exencion porque dice que no reinverti todo el "
        "importe en la nueva vivienda."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R011 NO deberia disparar si la denegacion es por motivo distinto "
        f"al plazo de residencia, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Anti-hardcode: asercion explicita sobre la cita semantica
# ---------------------------------------------------------------------------

def test_R011_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: la cita normativa NO puede contener el articulo canonico.

    Este test replica las aserciones anti-hardcode del brief en un test aparte
    para dejar trazabilidad explicita del invariante de anti-alucinacion.
    """
    docs = _docs_caso_david(build_doc, incluir_sentencia=True)
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=docs,
    )
    brief = build_brief("Defiende mi caso de vivienda habitual por separacion.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1
    arg = candidatos[0]

    # Asercion literal del brief.
    assert (
        "Art. 41 bis" not in arg.cita_normativa_propuesta
        and "art. 41 bis" not in arg.cita_normativa_propuesta.lower()
        and "STS 553/2023" not in arg.cita_normativa_propuesta
    ), (
        f"La cita normativa debe ser semantica, got: "
        f"{arg.cita_normativa_propuesta!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Smoke de registro: R011 aparece en el REGISTRY tras el reload
# ---------------------------------------------------------------------------

def test_R011_registrada_en_registry():
    """El reload del modulo R011 debe auto-registrar la regla en el REGISTRY."""
    assert "R011" in REGISTRY, (
        f"R011 no aparece en el REGISTRY tras reload. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R011"]
    assert "IRPF" in info["tributos"], (
        f"R011 debe aplicar a IRPF, tributos={info['tributos']}"
    )
    # IRPF unicamente — la excepcion del art. 41 bis RIRPF no aplica a IVA/ISD/ITP.
    assert "IVA" not in info["tributos"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
