"""Tests TDD para la regla R017 — compensacion_perdidas_patrimoniales_4_anos (T1B-017).

La regla dispara cuando existen perdidas patrimoniales pendientes de compensar
declaradas en ejercicios anteriores (dentro del plazo de cuatro anos) y la
liquidacion del ejercicio actual NO las aplica (o las aplica por debajo del
limite normativo) contra el saldo positivo del ejercicio.

Fundamento juridico (lo resuelve el RAG verificador, NO la regla):
    - Art. 49 LIRPF: integracion y compensacion de rentas en la base imponible
      del ahorro. Saldo negativo de perdidas patrimoniales compensable en los
      cuatro ejercicios siguientes con el limite del 25% del saldo positivo
      de los rendimientos del capital mobiliario.
    - Art. 48 LIRPF: integracion y compensacion de rentas en la base imponible
      general (perdidas de la base general, limite 25%).

Fases aplicables (segun enum real `Fase` en `app/models/defensia.py`):
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - COMPROBACION_PROPUESTA / COMPROBACION_POST_ALEGACIONES
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Relevancia caso David Oliva: condicional. Si David tiene perdidas patrimoniales
pendientes de los ejercicios 2020-2023 y AEAT deniega la exencion por
reinversion de la venta de vivienda 2024, la ganancia patrimonial resultante
debe compensarse previamente con esas perdidas pendientes antes de calcular
la cuota tributaria impugnada.

Invariante #2 (anti-alucinacion): la regla devuelve una cita semantica libre
("compensacion de saldos negativos... cuatro anos..."). La cita canonica
("Art. 49 LIRPF") la resuelve el `defensia_rag_verifier`.
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
# Helper de aislamiento — carga solo R017 tras el reset del conftest
# ---------------------------------------------------------------------------

def _cargar_solo_R017() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R017."""
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_irpf.R017_compensacion_perdidas"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R017():
    """Garantiza que R017 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R017()
    yield


# ---------------------------------------------------------------------------
# Helper anti-hardcode (Invariante #2)
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """La cita NO puede hardcodear el articulo canonico — lo resuelve el RAG."""
    assert "Art. 49" not in cita, (
        f"Cita hardcoded detectada: 'Art. 49' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "art. 49 lirpf" not in cita.lower(), (
        f"Cita hardcoded detectada: 'art. 49 LIRPF' en '{cita}'."
    )
    assert "articulo 49" not in cita.lower(), (
        f"Cita hardcoded detectada: 'articulo 49' en '{cita}'."
    )
    assert "art. 48" not in cita.lower(), (
        f"Cita hardcoded detectada: 'art. 48' en '{cita}'."
    )
    assert "lirpf 49" not in cita.lower(), (
        f"Cita hardcoded detectada: 'LIRPF 49' en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Helpers de construccion de documentos
# ---------------------------------------------------------------------------

def _liquidacion_con_datos(build_doc, datos: dict, *, doc_id: str = "doc-liq-R017"):
    """Factory local: liquidacion provisional con el bloque de datos indicado."""
    return build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos=datos,
        doc_id=doc_id,
        nombre_original="liquidacion_provisional_irpf.pdf",
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: perdidas pendientes dentro del plazo, no compensadas
# ---------------------------------------------------------------------------

def test_R017_positivo_perdidas_pendientes_no_compensadas(
    build_exp, build_brief, build_doc
):
    """Si existen perdidas patrimoniales pendientes de un ejercicio anterior
    (< 4 anos) y la liquidacion actual no las aplica contra la ganancia del
    ejercicio, R017 dispara con el total de perdidas pendientes en datos_disparo.
    """
    datos_liquidacion = {
        "ejercicio": 2024,
        "perdidas_pendientes_ejercicios_anteriores": [
            {"ejercicio": 2022, "importe": 5000},
        ],
        "perdidas_compensadas_ejercicio_actual": 0,
        "ganancia_patrimonial_ejercicio": 20000,
    }
    liquidacion = _liquidacion_con_datos(build_doc, datos_liquidacion)

    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Tengo perdidas patrimoniales pendientes del 2022 y AEAT no me las "
        "compensa contra la ganancia de la venta de la vivienda en 2024."
    )

    candidatos = evaluar(exp, brief)

    r017 = [c for c in candidatos if c.regla_id == "R017"]
    assert len(r017) == 1, (
        f"R017 deberia disparar con perdidas 2022 no compensadas, got {candidatos}"
    )
    arg = r017[0]
    assert isinstance(arg, ArgumentoCandidato)

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    cita_lower = arg.cita_normativa_propuesta.lower()
    assert "compensacion" in cita_lower, (
        f"La cita semantica debe mencionar 'compensacion', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )
    assert "perdidas" in cita_lower, (
        f"La cita semantica debe mencionar 'perdidas', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )
    assert "cuatro" in cita_lower or "4 " in cita_lower, (
        f"La cita semantica debe mencionar el plazo de cuatro anos, got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    # datos_disparo debe exponer el total de perdidas pendientes
    disparo = arg.datos_disparo
    assert disparo.get("perdidas_pendientes_total") == 5000, (
        f"datos_disparo.perdidas_pendientes_total inesperado: {disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: compensadas por debajo del limite 25%
# ---------------------------------------------------------------------------

def test_R017_positivo_parcialmente_compensadas_bajo_limite(
    build_exp, build_brief, build_doc
):
    """Si las perdidas estan compensadas por debajo del limite calculado
    (25% del saldo positivo), R017 dispara con el delta no aplicado."""
    datos_liquidacion = {
        "ejercicio": 2024,
        "perdidas_pendientes_ejercicios_anteriores": [
            {"ejercicio": 2023, "importe": 8000},
        ],
        "perdidas_compensadas_ejercicio_actual": 1000,
        # El usuario/extractor ya ha resuelto el limite del 25% aguas arriba.
        "limite_compensacion_calculado": 3000,
        "ganancia_patrimonial_ejercicio": 12000,
    }
    liquidacion = _liquidacion_con_datos(
        build_doc, datos_liquidacion, doc_id="doc-liq-R017-parcial"
    )

    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[liquidacion],
    )
    brief = build_brief(
        "AEAT solo me compensa 1000 EUR de perdidas cuando podria compensarme "
        "hasta 3000 EUR del limite del 25%."
    )

    candidatos = evaluar(exp, brief)

    r017 = [c for c in candidatos if c.regla_id == "R017"]
    assert len(r017) == 1, (
        f"R017 deberia disparar cuando la compensacion esta por debajo del "
        f"limite, got {candidatos}"
    )
    arg = r017[0]

    disparo = arg.datos_disparo
    assert disparo.get("perdidas_pendientes_total") == 8000, (
        f"perdidas_pendientes_total inesperado: {disparo!r}"
    )
    assert disparo.get("compensado_actual") == 1000, (
        f"compensado_actual inesperado: {disparo!r}"
    )
    assert disparo.get("limite_aplicable") == 3000, (
        f"limite_aplicable inesperado: {disparo!r}"
    )
    # Delta: lo que AEAT dejo de aplicar dentro del margen permitido.
    assert disparo.get("delta_no_aplicado") == 2000, (
        f"delta_no_aplicado inesperado: {disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: compensacion al maximo permitido
# ---------------------------------------------------------------------------

def test_R017_negativo_compensacion_al_maximo(
    build_exp, build_brief, build_doc
):
    """Si la compensacion ya alcanza el limite calculado, la regla NO dispara."""
    datos_liquidacion = {
        "ejercicio": 2024,
        "perdidas_pendientes_ejercicios_anteriores": [
            {"ejercicio": 2023, "importe": 8000},
        ],
        "perdidas_compensadas_ejercicio_actual": 3000,
        "limite_compensacion_calculado": 3000,
        "ganancia_patrimonial_ejercicio": 12000,
    }
    liquidacion = _liquidacion_con_datos(
        build_doc, datos_liquidacion, doc_id="doc-liq-R017-maximo"
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("AEAT ya me ha compensado las perdidas al maximo.")

    candidatos = evaluar(exp, brief)

    r017 = [c for c in candidatos if c.regla_id == "R017"]
    assert r017 == [], (
        f"R017 NO debe disparar si compensacion == limite, got {r017}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: sin perdidas pendientes declaradas
# ---------------------------------------------------------------------------

def test_R017_negativo_sin_perdidas_pendientes(
    build_exp, build_brief, build_doc
):
    """Sin perdidas pendientes declaradas en ejercicios anteriores, no hay
    sustrato factico para disparar la regla."""
    datos_liquidacion = {
        "ejercicio": 2024,
        "perdidas_pendientes_ejercicios_anteriores": [],
        "perdidas_compensadas_ejercicio_actual": 0,
        "ganancia_patrimonial_ejercicio": 20000,
    }
    liquidacion = _liquidacion_con_datos(
        build_doc, datos_liquidacion, doc_id="doc-liq-R017-vacio"
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("No tengo perdidas pendientes de ejercicios anteriores.")

    candidatos = evaluar(exp, brief)

    r017 = [c for c in candidatos if c.regla_id == "R017"]
    assert r017 == [], (
        f"R017 NO debe disparar sin perdidas pendientes, got {r017}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: perdidas caducadas (fuera del plazo de 4 anos)
# ---------------------------------------------------------------------------

def test_R017_negativo_perdidas_caducadas_fuera_plazo(
    build_exp, build_brief, build_doc
):
    """Una perdida de 2019 ya no puede compensarse contra la ganancia de 2024
    porque han transcurrido mas de 4 ejercicios. R017 no debe disparar."""
    datos_liquidacion = {
        "ejercicio": 2024,
        "perdidas_pendientes_ejercicios_anteriores": [
            {"ejercicio": 2019, "importe": 10000},
        ],
        "perdidas_compensadas_ejercicio_actual": 0,
        "ganancia_patrimonial_ejercicio": 20000,
    }
    liquidacion = _liquidacion_con_datos(
        build_doc, datos_liquidacion, doc_id="doc-liq-R017-caducada"
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Tengo una perdida del 2019 que me gustaria compensar en 2024."
    )

    candidatos = evaluar(exp, brief)

    r017 = [c for c in candidatos if c.regla_id == "R017"]
    assert r017 == [], (
        f"R017 NO debe disparar con perdidas caducadas (>4 anos), got {r017}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: asercion literal del brief
# ---------------------------------------------------------------------------

def test_R017_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: la cita normativa NO puede contener el articulo canonico."""
    datos_liquidacion = {
        "ejercicio": 2024,
        "perdidas_pendientes_ejercicios_anteriores": [
            {"ejercicio": 2022, "importe": 5000},
        ],
        "perdidas_compensadas_ejercicio_actual": 0,
        "ganancia_patrimonial_ejercicio": 20000,
    }
    liquidacion = _liquidacion_con_datos(
        build_doc, datos_liquidacion, doc_id="doc-liq-R017-anti-hardcode"
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Defiende la compensacion de mis perdidas pendientes.")

    candidatos = evaluar(exp, brief)

    r017 = [c for c in candidatos if c.regla_id == "R017"]
    assert len(r017) == 1
    cita = r017[0].cita_normativa_propuesta

    # Asercion literal del brief.
    assert "Art. 49" not in cita and "art. 49 LIRPF" not in cita.lower(), (
        f"Cita hardcoded detectada en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Smoke test — R017 aparece en el REGISTRY tras el reload
# ---------------------------------------------------------------------------

def test_R017_registrada_en_registry():
    """El reload del modulo R017 debe auto-registrar la regla en el REGISTRY."""
    assert "R017" in REGISTRY, (
        f"R017 no aparece en el REGISTRY tras reload. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R017"]
    assert "IRPF" in info["tributos"], (
        f"R017 debe aplicar a IRPF, tributos={info['tributos']}"
    )
    # Compensacion de perdidas es exclusiva de IRPF.
    assert "IVA" not in info["tributos"]
    assert "ISD" not in info["tributos"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "COMPROBACION_PROPUESTA" in info["fases"]
    assert "COMPROBACION_POST_ALEGACIONES" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
    assert "TEAR_AMPLIACION_POSIBLE" in info["fases"]
