"""Tests de la regla R013 — gastos_inherentes_transmision_inmueble (T1B-013).

La regla dispara cuando, en una liquidacion provisional por ganancia
patrimonial por transmision de inmueble, AEAT NO computa los gastos y tributos
inherentes a la adquisicion y/o a la transmision que el contribuyente habia
declarado y puede acreditar.

Casuistica cubierta:

1. **Gastos de adquisicion omitidos** (notaria, registro, gestoria, ITP/IVA
   soportado, tasacion, comision inmobiliaria en su dia). El contribuyente los
   habia declarado en su autoliquidacion y AEAT los elimina al recalcular la
   ganancia.

2. **Comision inmobiliaria en la transmision no admitida**. El vendedor pago
   comision a una agencia inmobiliaria para vender el inmueble; AEAT la
   rechaza por falta de justificacion o sin mas.

3. **Plusvalia municipal satisfecha no deducida** del valor de transmision.
   El Impuesto sobre el Incremento de Valor de los Terrenos de Naturaleza
   Urbana, cuando lo paga el transmitente, es un tributo inherente a la
   transmision y minora el valor de transmision a efectos IRPF.

Base normativa (la RESUELVE el RAG verificador, NO la regla — invariante #2):
    - Art. 35.1.b) LIRPF — valor de adquisicion incluye inversiones, gastos y
      tributos inherentes a la adquisicion satisfechos por el adquirente.
    - Art. 35.2 LIRPF — valor de transmision se minora en gastos y tributos
      inherentes a la transmision satisfechos por el transmitente.
    - DGT V2625-20 — comision inmobiliaria computable.

Aislamiento: importante no confiar en `importlib.reload` de un modulo
potencialmente ya cacheado por otros tests del Grupo A. Seguimos el patron del
brief (drift corregido): reset_registry + reload/import controlado para que
solo R013 este en el REGISTRY durante estos tests.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T1B-013
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
# Aislamiento del REGISTRY — carga solo R013
# ---------------------------------------------------------------------------

_R013_MODULE_NAME = "app.services.defensia_rules.reglas_irpf.R013_gastos_transmision"


def _cargar_solo_R013() -> None:
    """Deja en el REGISTRY unicamente la regla R013.

    Sigue el patron del brief: reset + import/reload. Si el modulo ya estaba
    cargado en un run anterior, `importlib.reload` fuerza la re-ejecucion del
    decorador `@regla` para que la regla vuelva a aparecer en el REGISTRY
    que el conftest global acaba de limpiar.
    """
    reset_registry()
    if _R013_MODULE_NAME in sys.modules:
        importlib.reload(sys.modules[_R013_MODULE_NAME])
    else:
        importlib.import_module(_R013_MODULE_NAME)


@pytest.fixture(autouse=True)
def _recargar_R013():
    """Recarga R013 tras el reset del conftest global antes de cada test."""
    _cargar_solo_R013()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear el articulo canonico.

    La cita final ("Art. 35.1.b) LIRPF" / "Art. 35.2 LIRPF") la resuelve el RAG
    verificador contra el corpus normativo. Aqui solo aceptamos descripciones
    semanticas libres que hablen del concepto juridico.
    """
    cita_lower = cita.lower()
    assert "art. 35" not in cita_lower, (
        f"Cita hardcoded detectada: 'Art. 35' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "35.1.b" not in cita_lower, (
        f"Cita hardcoded detectada: '35.1.b' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "35.2 lirpf" not in cita_lower, (
        f"Cita hardcoded detectada: '35.2 LIRPF' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: gastos de adquisicion omitidos por AEAT
# ---------------------------------------------------------------------------

def test_R013_positivo_gastos_adquisicion_omitidos(build_exp, build_brief, build_doc):
    """AEAT no incluye los gastos de adquisicion (notaria, registro, ITP) que
    el contribuyente habia declarado y que forman parte del valor de
    adquisicion a efectos de calcular la ganancia patrimonial."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "ganancia_patrimonial_inmueble": True,
            "gastos_adquisicion_incluidos": False,
            "gastos_adquisicion_declarados": 15000,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT me ha eliminado del valor de adquisicion los gastos de notaria, "
        "registro e ITP al recalcular la ganancia patrimonial."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R013"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "gastos" in arg.cita_normativa_propuesta.lower(), (
        f"La cita semantica debe mencionar 'gastos', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    assert arg.datos_disparo.get("tipo") == "adquisicion", (
        f"datos_disparo.tipo inesperado: {arg.datos_disparo!r}"
    )
    assert arg.datos_disparo.get("gastos_omitidos") == 15000, (
        f"datos_disparo.gastos_omitidos inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: comision inmobiliaria en la transmision omitida
# ---------------------------------------------------------------------------

def test_R013_positivo_comision_inmobiliaria_transmision(
    build_exp, build_brief, build_doc
):
    """El vendedor pago 5.000 EUR de comision inmobiliaria para vender el
    inmueble. AEAT admite 0 EUR. DGT V2625-20: la comision inmobiliaria es
    gasto inherente a la transmision y minora el valor de transmision."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "ganancia_patrimonial_inmueble": True,
            "comision_inmobiliaria_declarada": 5000,
            "comision_inmobiliaria_admitida": 0,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "Pague 5.000 EUR de comision inmobiliaria al vender el piso pero AEAT "
        "no me la admite como gasto de transmision."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R013"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    assert arg.datos_disparo.get("tipo") == "transmision_comision_inmobiliaria", (
        f"datos_disparo.tipo inesperado: {arg.datos_disparo!r}"
    )
    assert arg.datos_disparo.get("gastos_omitidos") == 5000, (
        f"datos_disparo.gastos_omitidos inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Positivo: plusvalia municipal satisfecha no deducida
# ---------------------------------------------------------------------------

def test_R013_positivo_plusvalia_municipal_no_computada(
    build_exp, build_brief, build_doc
):
    """El transmitente pago plusvalia municipal (IIVTNU) por importe de 3.000
    EUR. AEAT no la ha tenido en cuenta al minorar el valor de transmision.
    Tributo inherente a la transmision satisfecho por el transmitente ->
    minora el valor de transmision."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "ganancia_patrimonial_inmueble": True,
            "plusvalia_municipal_satisfecha": 3000,
            "plusvalia_incluida_en_calculo": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "Pague la plusvalia municipal en el ayuntamiento al vender mi piso. "
        "AEAT no la ha restado del valor de transmision."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R013"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    assert arg.datos_disparo.get("tipo") == "transmision_plusvalia_municipal", (
        f"datos_disparo.tipo inesperado: {arg.datos_disparo!r}"
    )
    assert arg.datos_disparo.get("gastos_omitidos") == 3000, (
        f"datos_disparo.gastos_omitidos inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: todos los gastos incluidos correctamente
# ---------------------------------------------------------------------------

def test_R013_negativo_todos_los_gastos_incluidos(
    build_exp, build_brief, build_doc
):
    """Cuando AEAT ha computado correctamente gastos de adquisicion, comision
    inmobiliaria y plusvalia municipal, la regla NO debe disparar."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "ganancia_patrimonial_inmueble": True,
            "gastos_adquisicion_incluidos": True,
            "comision_inmobiliaria_declarada": 5000,
            "comision_inmobiliaria_admitida": 5000,
            "plusvalia_municipal_satisfecha": 3000,
            "plusvalia_incluida_en_calculo": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Reviso la liquidacion; los gastos estan incluidos.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R013 no deberia disparar cuando todos los gastos estan "
        f"computados, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: no hay ganancia patrimonial por inmueble
# ---------------------------------------------------------------------------

def test_R013_negativo_sin_ganancia_patrimonial_inmueble(
    build_exp, build_brief, build_doc
):
    """Si la liquidacion solo regulariza rendimientos del trabajo y no hay
    ganancia patrimonial por transmision de inmueble, R013 no aplica."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "ganancia_patrimonial_inmueble": False,
            "regulariza_rendimientos_trabajo": True,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT me ha regularizado los rendimientos del trabajo, nada que ver "
        "con inmuebles."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R013 no deberia disparar sin ganancia patrimonial por inmueble, "
        f"got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Invariante anti-hardcode de citas
# ---------------------------------------------------------------------------

def test_R013_cita_no_es_hardcoded(build_exp, build_brief, build_doc):
    """Invariante #2 del plan: la cita normativa propuesta NO puede contener
    el articulo canonico. Solo una descripcion semantica del concepto."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "ganancia_patrimonial_inmueble": True,
            "gastos_adquisicion_incluidos": False,
            "gastos_adquisicion_declarados": 10000,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")

    candidatos = evaluar(exp, brief)
    assert len(candidatos) == 1
    cita = candidatos[0].cita_normativa_propuesta

    # Assertions exactas pedidas por el brief.
    assert "Art. 35" not in cita
    assert "35.1.b" not in cita
    assert "35.2 LIRPF" not in cita.lower()
    # Debe seguir siendo una cita util (no vacia) y mencionar el concepto.
    assert len(cita) > 20
    assert "gastos" in cita.lower() or "inherentes" in cita.lower()


# ---------------------------------------------------------------------------
# Test 7 — Smoke de registro: R013 aparece en el REGISTRY y rango 0-30
# ---------------------------------------------------------------------------

def test_R013_registrada_en_registry():
    """Tras cargar solo R013 el REGISTRY debe contener exactamente esa clave,
    y el len debe estar dentro del rango [0, 30] del smoke global."""
    assert "R013" in REGISTRY, (
        f"R013 no aparece en el REGISTRY tras carga aislada. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R013"]
    assert "IRPF" in info["tributos"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
    assert "TEAR_AMPLIACION_POSIBLE" in info["fases"]
    assert 0 <= len(REGISTRY) <= 30, (
        f"REGISTRY fuera del rango [0, 30], got {len(REGISTRY)}"
    )
