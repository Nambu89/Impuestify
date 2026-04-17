"""Tests de la regla R025 — itp_valor_referencia (T2-R025).

La regla dispara cuando, en una liquidacion ITP que aplica como base imponible
el valor de referencia catastral fijado por la Direccion General del Catastro
(DGC), el contribuyente dispone de una prueba pericial (tasacion pericial
contradictoria o informe tecnico) que acredita un valor real inferior al
valor de referencia utilizado por la Administracion.

Base normativa (la RESUELVE el RAG verificador, NO la regla — invariante #2):
    - Art. 10.2 TRLITPAJD tras la redaccion dada por la Ley 11/2021 — regla
      general: base imponible = mayor de (valor declarado, valor de
      referencia catastral). Cuando el valor declarado es inferior al de
      referencia, la Administracion aplica el valor de referencia.
    - TC 2024 — desestima la cuestion de inconstitucionalidad general de la
      Ley 11/2021, pero admite expresamente la impugnacion individualizada
      del valor de referencia mediante prueba pericial en contrario.

Invariante #2 (anti-alucinacion): la regla emite una cita SEMANTICA. El texto
canonico lo traduce el RAG verificador contra el corpus normativo. Zero
hardcoded article references en este modulo ni en los tests de verificacion.

Aislamiento: seguimos el patron del brief (reset_registry + import/reload
controlado) para que solo R025 este en el REGISTRY durante estos tests.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2-R025
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
# Aislamiento del REGISTRY — carga solo R025
# ---------------------------------------------------------------------------

_R025_MODULE_NAME = (
    "app.services.defensia_rules.reglas_otros_tributos.R025_itp_valor_referencia"
)


def _cargar_solo_R025() -> None:
    """Deja en el REGISTRY unicamente la regla R025.

    Sigue el patron del brief: reset + import/reload. Si el modulo ya estaba
    cargado en un run anterior, `importlib.reload` fuerza la re-ejecucion del
    decorador `@regla` para que la regla vuelva a aparecer en el REGISTRY
    que el conftest global acaba de limpiar.
    """
    reset_registry()
    if _R025_MODULE_NAME in sys.modules:
        importlib.reload(sys.modules[_R025_MODULE_NAME])
    else:
        importlib.import_module(_R025_MODULE_NAME)


@pytest.fixture(autouse=True)
def _recargar_R025():
    """Recarga R025 tras el reset del conftest global antes de cada test."""
    _cargar_solo_R025()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear el articulo canonico.

    La cita final ("Art. 10.2 TRLITPAJD", "Ley 11/2021", etc.) la resuelve
    el RAG verificador contra el corpus normativo. Aqui solo aceptamos
    descripciones semanticas libres que hablen del concepto juridico.
    """
    assert "Art. 10" not in cita, (
        f"Cita hardcoded detectada: 'Art. 10' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "TRLITPAJD" not in cita, (
        f"Cita hardcoded detectada: 'TRLITPAJD' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "Ley 11/2021" not in cita, (
        f"Cita hardcoded detectada: 'Ley 11/2021' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: valor referencia con tasacion pericial contradictoria
# ---------------------------------------------------------------------------

def test_R025_positivo_tasacion_pericial_contradictoria(
    build_exp, build_brief, build_doc
):
    """La liquidacion ITP aplica el valor de referencia catastral (300.000)
    como base imponible. El contribuyente dispone de tasacion pericial
    contradictoria que acredita un valor real de 250.000 EUR. R025 debe
    disparar con diferencia = 50.000."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "base_imponible_valor_referencia": 300000,
            "tasacion_pericial_contradictoria": True,
            "valor_pericial": 250000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "La Junta me ha liquidado ITP sobre el valor de referencia catastral "
        "(300.000 EUR) pero tengo una tasacion pericial contradictoria que "
        "valora el inmueble en 250.000 EUR."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R025"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    cita_lower = arg.cita_normativa_propuesta.lower()
    assert (
        "valor de referencia" in cita_lower
        or "pericial" in cita_lower
    ), (
        f"La cita semantica debe mencionar 'valor de referencia' o "
        f"'pericial', got: {arg.cita_normativa_propuesta!r}"
    )

    assert arg.datos_disparo.get("diferencia") == 50000, (
        f"datos_disparo.diferencia inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: valor referencia con informe tecnico discrepante
# ---------------------------------------------------------------------------

def test_R025_positivo_informe_tecnico_discrepante(
    build_exp, build_brief, build_doc
):
    """Alternativa a la tasacion pericial contradictoria: un informe tecnico
    emitido por arquitecto / tasador homologado que tambien discrepa del
    valor de referencia. Igualmente habilita la impugnacion individualizada
    reconocida por el TC."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "base_imponible_valor_referencia": 300000,
            "informe_tecnico_discrepante": True,
            "valor_informe": 270000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "Tengo un informe tecnico que valora el inmueble por debajo del valor "
        "de referencia catastral aplicado en la liquidacion."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R025"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    assert arg.datos_disparo.get("diferencia") == 30000, (
        f"datos_disparo.diferencia inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: sin prueba pericial no hay defensa
# ---------------------------------------------------------------------------

def test_R025_negativo_sin_prueba_pericial(build_exp, build_brief, build_doc):
    """Sin una prueba pericial o informe tecnico que acredite valor inferior,
    la impugnacion individualizada reconocida por el TC carece de soporte
    probatorio: R025 no dispara. El TC exige explicitamente prueba en
    contrario cualificada."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "base_imponible_valor_referencia": 300000,
            "tasacion_pericial_contradictoria": False,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "Me parece caro el valor de referencia pero no tengo tasacion."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R025 no deberia disparar sin prueba pericial, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: valor declarado >= valor referencia
# ---------------------------------------------------------------------------

def test_R025_negativo_valor_declarado_mayor_o_igual(
    build_exp, build_brief, build_doc
):
    """Si el valor declarado por el contribuyente en la escritura es mayor o
    igual al valor de referencia catastral, la base imponible ya es la
    declarada (no la de referencia) y la regla no aplica: no hay
    regularizacion al alza que impugnar."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "base_imponible_valor_referencia": 300000,
            "valor_declarado": 310000,
            "tasacion_pericial_contradictoria": True,
            "valor_pericial": 250000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "Declare 310.000 EUR en la escritura pero tengo tasacion pericial por "
        "250.000 EUR."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R025 no deberia disparar cuando el valor declarado es mayor o igual "
        f"al valor de referencia, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: tributo distinto de ITP
# ---------------------------------------------------------------------------

def test_R025_negativo_tributo_distinto_de_ITP(
    build_exp, build_brief, build_doc
):
    """La regla solo aplica a ITP. Si el expediente es de IRPF, IVA, ISD o
    Plusvalia Municipal, la regla no debe disparar aunque el documento
    contenga los datos de disparo."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "base_imponible_valor_referencia": 300000,
            "tasacion_pericial_contradictoria": True,
            "valor_pericial": 250000,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Expediente IRPF sin relacion con ITP.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R025 no deberia disparar fuera de ITP, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Invariante anti-hardcode de citas
# ---------------------------------------------------------------------------

def test_R025_cita_no_es_hardcoded(build_exp, build_brief, build_doc):
    """Invariante #2 del plan: la cita normativa propuesta NO puede contener
    el articulo canonico ni la ley. Solo una descripcion semantica del
    concepto juridico."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ITP",
            "base_imponible_valor_referencia": 300000,
            "tasacion_pericial_contradictoria": True,
            "valor_pericial": 250000,
        },
    )
    exp = build_exp(
        tributo=Tributo.ITP,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")

    candidatos = evaluar(exp, brief)
    assert len(candidatos) == 1
    cita = candidatos[0].cita_normativa_propuesta

    # Assertions exactas pedidas por el brief.
    assert "Art. 10" not in cita
    assert "TRLITPAJD" not in cita
    assert "Ley 11/2021" not in cita
    # Debe seguir siendo una cita util (no vacia) y mencionar el concepto.
    assert len(cita) > 20
    cita_lower = cita.lower()
    assert (
        "valor de referencia" in cita_lower
        or "pericial" in cita_lower
        or "impugnacion" in cita_lower
    )


# ---------------------------------------------------------------------------
# Test 7 — Smoke de registro: R025 aparece en el REGISTRY y rango 0-30
# ---------------------------------------------------------------------------

def test_R025_registrada_en_registry():
    """Tras cargar solo R025 el REGISTRY debe contener exactamente esa clave,
    y el len debe estar dentro del rango [0, 30] del smoke global."""
    assert "R025" in REGISTRY, (
        f"R025 no aparece en el REGISTRY tras carga aislada. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R025"]
    assert "ITP" in info["tributos"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "COMPROBACION_PROPUESTA" in info["fases"]
    assert "COMPROBACION_POST_ALEGACIONES" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
    assert "TEAR_AMPLIACION_POSIBLE" in info["fases"]
    assert 0 <= len(REGISTRY) <= 30, (
        f"REGISTRY fuera del rango [0, 30], got {len(REGISTRY)}"
    )
