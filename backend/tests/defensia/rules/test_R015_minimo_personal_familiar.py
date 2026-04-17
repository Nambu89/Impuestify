"""Tests TDD para la regla R015 — minimo_personal_familiar.

La regla dispara cuando AEAT no aplica correctamente el minimo personal y
familiar (personal, por descendientes, ascendientes o discapacidad) y, en
especial, cuando tras una sentencia de modificacion de medidas con custodia
compartida la liquidacion no reparte el minimo por descendientes al 50% /
50% (DGT V2330-19), o cuando existiendo custodia exclusiva no se aplica
al 100% al progenitor custodio.

Base normativa (la resuelve el RAG verificador, NO la regla):
    - Arts. 56 a 61 LIRPF: minimo personal, minimo por descendientes,
      minimo por ascendientes, minimo por discapacidad y normas comunes
      de aplicacion.
    - DGT V2330-19: en custodia compartida, el minimo por descendientes
      se prorratea al 50% entre ambos progenitores con independencia de
      con cual convivan efectivamente.

Fases aplicables (del enum real `Fase`):
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - COMPROBACION_PROPUESTA / COMPROBACION_POST_ALEGACIONES /
      COMPROBACION_REQUERIMIENTO
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Triggers soportados:
    - `datos.custodia="compartida"` + `datos.minimo_descendientes_aplicado_proporcional=False`
      en el documento de liquidacion/propuesta (y con una SENTENCIA_JUDICIAL
      en el expediente que acredite la modificacion de medidas).
    - `datos.custodia="exclusiva"` + `datos.progenitor_custodio=True` +
      `datos.minimo_descendientes_aplicado=0` (AEAT no aplica el minimo al
      custodio).
    - `datos.tiene_discapacidad_33_por_ciento=True` +
      `datos.minimo_discapacidad_aplicado=0` (no se aplica el minimo por
      discapacidad pese a reunir el requisito).

La regla NO hardcodea la cita del articulo — solo emite una cita semantica
libre que el verificador RAG traducira al texto canonico correcto.

Patron de aislamiento: seguimos el mismo patron que R010 — limpiamos el
REGISTRY y reimportamos el modulo en cada test para garantizar que el
decorador `@regla` re-registra R015 de forma limpia.
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
# Aislamiento especifico de R015
# ---------------------------------------------------------------------------

def _cargar_solo_R015() -> None:
    """Re-importa R015 tras cada reset del REGISTRY.

    Este helper sigue el patron del brief: si el modulo ya esta en
    ``sys.modules`` lo recargamos via ``importlib.reload`` (lo que vuelve a
    ejecutar el decorador ``@regla``); si no, lo importamos por primera vez.
    En ambos casos empezamos con un ``reset_registry()`` para evitar IDs
    duplicados y que un test previo contamine el estado de R015.
    """
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_irpf.R015_minimo_personal_familiar"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _registrar_r015(_aislar_registry):  # noqa: ARG001 — fuerza orden
    """Fixture autouse: tras el reset del conftest, recarga R015.

    Declaramos ``_aislar_registry`` como dependencia explicita para que el
    reset del conftest ocurra ANTES del reload. Asi el decorador ``@regla``
    vuelve a registrar R015 de forma limpia sin colisionar con el registro
    previo de otra session.
    """
    _cargar_solo_R015()
    yield


# ---------------------------------------------------------------------------
# Helper local — la cita NUNCA puede hardcodear articulos canonicos
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la cita semantica NO puede contener literales canonicos.

    La cita canonica ("Art. 58 LIRPF", "Arts. 56 a 61 LIRPF", DGT V2330-19)
    la resuelve el RAG verificador contra el corpus normativo. Aqui solo
    aceptamos descripciones semanticas libres.
    """
    # Las tres prohibidas explicitas del brief
    assert "Art. 56" not in cita, (
        f"Cita hardcoded detectada: 'Art. 56' en '{cita}'"
    )
    assert "art. 58" not in cita.lower(), (
        f"Cita hardcoded detectada: 'art. 58' en '{cita}'"
    )
    assert "56 a 61 LIRPF" not in cita.upper(), (
        f"Cita hardcoded detectada: '56 a 61 LIRPF' en '{cita}'"
    )

    # Defensa adicional — otros literales que podrian colarse
    prohibidas_extra = [
        "Art. 57",
        "Art. 58",
        "Art. 59",
        "Art. 60",
        "Art. 61",
        "Articulo 56",
        "Articulo 58",
        "LIRPF 56",
        "LIRPF 58",
        "V2330-19",
        "DGT V2330",
    ]
    for prohibida in prohibidas_extra:
        assert prohibida.lower() not in cita.lower(), (
            f"Cita hardcoded detectada: '{prohibida}' en '{cita}'. "
            "La cita canonica debe venir del RAG verificador."
        )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: custodia compartida sin reparto 50/50 del minimo
# ---------------------------------------------------------------------------

def test_R015_positivo_custodia_compartida_sin_reparto_50_50(
    build_exp, build_brief, build_doc
):
    """Tras sentencia de modificacion de medidas con custodia compartida,
    AEAT debe prorratear el minimo por descendientes al 50%/50%. Si la
    liquidacion lo aplica integro a uno solo de los progenitores, dispara.
    """
    sentencia = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "custodia": "compartida",
            "tipo_resolucion": "modificacion_medidas",
        },
        doc_id="doc-sentencia-001",
        nombre_original="sentencia_modificacion_medidas.pdf",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "custodia": "compartida",
            "minimo_descendientes_aplicado_proporcional": False,
            "numero_descendientes": 2,
        },
        doc_id="doc-liq-001",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[sentencia, liquidacion],
    )
    brief = build_brief(
        "Tengo sentencia de custodia compartida pero AEAT aplica el minimo "
        "por descendientes integro a mi ex-pareja"
    )

    candidatos = evaluar(exp, brief)

    r015 = [c for c in candidatos if c.regla_id == "R015"]
    assert len(r015) == 1, (
        f"R015 deberia disparar con custodia compartida sin reparto 50/50, "
        f"got {candidatos}"
    )

    arg = r015[0]
    assert isinstance(arg, ArgumentoCandidato)

    # La cita debe ser semantica — NUNCA hardcoded
    cita = arg.cita_normativa_propuesta
    _assert_cita_no_hardcoded(cita)
    assert "minimo" in cita.lower(), (
        f"La cita semantica debe mencionar 'minimo', got: {cita!r}"
    )
    assert (
        "familiar" in cita.lower() or "descendientes" in cita.lower()
    ), (
        f"La cita semantica debe mencionar familia/descendientes, got: {cita!r}"
    )

    # datos_disparo debe exponer el motivo para que el writer lo use
    assert arg.datos_disparo.get("motivo") == "custodia_compartida_sin_prorrateo", (
        f"datos_disparo.motivo inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: custodia exclusiva con minimo no aplicado al custodio
# ---------------------------------------------------------------------------

def test_R015_positivo_custodia_exclusiva_minimo_no_aplicado(
    build_exp, build_brief, build_doc
):
    """Si el contribuyente es progenitor custodio exclusivo pero la
    liquidacion no le aplica el minimo por descendientes (valor 0),
    R015 dispara.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "custodia": "exclusiva",
            "progenitor_custodio": True,
            "minimo_descendientes_aplicado": 0,
            "numero_descendientes": 1,
        },
        doc_id="doc-liq-002",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Soy el progenitor custodio exclusivo pero AEAT no me aplica el "
        "minimo por descendientes"
    )

    candidatos = evaluar(exp, brief)

    r015 = [c for c in candidatos if c.regla_id == "R015"]
    assert len(r015) == 1, (
        f"R015 deberia disparar con custodia exclusiva y minimo=0 al "
        f"custodio, got {candidatos}"
    )

    arg = r015[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert arg.datos_disparo.get("motivo") == "custodia_exclusiva_sin_minimo", (
        f"datos_disparo.motivo inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Positivo: minimo por discapacidad no aplicado
# ---------------------------------------------------------------------------

def test_R015_positivo_minimo_discapacidad_no_aplicado(
    build_exp, build_brief, build_doc
):
    """Si el contribuyente acredita discapacidad >= 33% pero la liquidacion
    no aplica el minimo por discapacidad (valor 0), R015 dispara.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tiene_discapacidad_33_por_ciento": True,
            "minimo_discapacidad_aplicado": 0,
        },
        doc_id="doc-liq-003",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.TEAR_INTERPUESTA,
        docs=[liquidacion],
    )
    brief = build_brief(
        "Tengo reconocida discapacidad del 35% y AEAT no me aplica el "
        "minimo por discapacidad"
    )

    candidatos = evaluar(exp, brief)

    r015 = [c for c in candidatos if c.regla_id == "R015"]
    assert len(r015) == 1, (
        f"R015 deberia disparar con discapacidad acreditada y minimo=0, "
        f"got {candidatos}"
    )

    arg = r015[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "discapacidad" in arg.cita_normativa_propuesta.lower() or (
        "minimo" in arg.cita_normativa_propuesta.lower()
    ), (
        f"La cita debe mencionar minimo/discapacidad, got: "
        f"{arg.cita_normativa_propuesta!r}"
    )
    assert arg.datos_disparo.get("motivo") == "discapacidad_sin_minimo", (
        f"datos_disparo.motivo inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: minimos correctamente aplicados
# ---------------------------------------------------------------------------

def test_R015_negativo_minimos_correctamente_aplicados(
    build_exp, build_brief, build_doc
):
    """Si todos los flags de aplicacion estan en True (o los importes son
    positivos), R015 NO dispara.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "custodia": "compartida",
            "minimo_descendientes_aplicado_proporcional": True,
            "minimo_descendientes_aplicado": 2400,
            "tiene_discapacidad_33_por_ciento": True,
            "minimo_discapacidad_aplicado": 3000,
            "numero_descendientes": 2,
        },
        doc_id="doc-liq-ok",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Revision preventiva de la liquidacion del IRPF")

    candidatos = evaluar(exp, brief)

    r015 = [c for c in candidatos if c.regla_id == "R015"]
    assert r015 == [], (
        f"R015 NO debe disparar cuando los minimos estan correctamente "
        f"aplicados, got {r015}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: no hay descendientes/ascendientes/discapacidad
# ---------------------------------------------------------------------------

def test_R015_negativo_sin_descendientes_ni_discapacidad(
    build_exp, build_brief, build_doc
):
    """Si la liquidacion no contiene ningun dato relacionado con minimos
    familiares (ni descendientes, ni ascendientes, ni discapacidad), R015
    NO dispara — no hay nada que reclamar.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "concepto": "rendimientos_trabajo",
            "importe_regularizado": 1500.0,
        },
        doc_id="doc-liq-sin-familia",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "AEAT me regulariza rendimientos del trabajo por dietas"
    )

    candidatos = evaluar(exp, brief)

    r015 = [c for c in candidatos if c.regla_id == "R015"]
    assert r015 == [], (
        f"R015 NO debe disparar sin datos de minimos familiares en el "
        f"expediente, got {r015}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: la cita pasa el filtro especifico del brief
# ---------------------------------------------------------------------------

def test_R015_anti_hardcode_cita_normativa(
    build_exp, build_brief, build_doc
):
    """Invariante #2 del diseno DefensIA: la cita emitida por la regla
    debe ser SEMANTICA. Este test la comprueba literal con el filtro del
    brief.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tiene_discapacidad_33_por_ciento": True,
            "minimo_discapacidad_aplicado": 0,
        },
        doc_id="doc-liq-anti-hardcode",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief("Discapacidad reconocida no aplicada")

    candidatos = evaluar(exp, brief)
    r015 = [c for c in candidatos if c.regla_id == "R015"]
    assert len(r015) == 1

    cita = r015[0].cita_normativa_propuesta
    assert (
        "Art. 56" not in cita
        and "art. 58" not in cita.lower()
        and "56 a 61 LIRPF" not in cita.upper()
    ), (
        f"La regla no puede hardcodear articulos canonicos del LIRPF, "
        f"got cita={cita!r}"
    )


# ---------------------------------------------------------------------------
# Sanity check: la regla esta registrada tras el import
# ---------------------------------------------------------------------------

def test_R015_registrada_en_registry():
    """Tras importar el modulo, R015 debe estar en el REGISTRY con la
    metadata correcta (tributo IRPF, fases de liquidacion/comprobacion/recurso).
    """
    assert "R015" in REGISTRY, (
        f"R015 no encontrada en REGISTRY. Keys actuales: {list(REGISTRY.keys())}"
    )
    info = REGISTRY["R015"]
    assert "IRPF" in info["tributos"], (
        f"R015 deberia aplicar a IRPF, tributos={info['tributos']}"
    )
    # Debe cubrir las fases principales (liquidacion, comprobacion, recursos)
    fases_esperadas = {
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "COMPROBACION_REQUERIMIENTO",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    }
    for fase in fases_esperadas:
        assert fase in info["fases"], (
            f"R015 deberia aplicar a la fase {fase}, fases={info['fases']}"
        )
