"""Tests TDD para la regla R019 — exencion_indemnizacion_danos_personales.

La regla dispara cuando AEAT incluye como renta sujeta una indemnizacion por
danos personales que deberia estar exenta segun el regimen de exencion
tributaria de indemnizaciones por responsabilidad civil:

    - Cuantias legalmente reconocidas o judicialmente reconocidas.
    - Acuerdos de mediacion y otros Metodos Alternativos de Solucion de
      Controversias (MASC), siempre dentro del limite del Baremo legal
      aplicable (extension introducida por la Ley Organica 1/2025).
    - Pagos realizados por aseguradoras en cumplimiento de sentencia firme
      reconociendo la indemnizacion.

Base normativa (la resuelve el RAG verificador, NO la regla):
    - Art. 7.d LIRPF: exencion de indemnizaciones como consecuencia de
      responsabilidad civil por danos personales, en la cuantia legal o
      judicialmente reconocida.
    - Ley Organica 1/2025 de medidas en materia de eficiencia del Servicio
      Publico de Justicia: extension del regimen de exencion a los acuerdos
      alcanzados mediante MASC hasta el limite del Baremo aplicable.
    - Jurisprudencia TS sobre alcance de la exencion: aseguradoras,
      mediacion, responsabilidad civil extracontractual.

Fases aplicables (del enum real `Fase`):
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - COMPROBACION_PROPUESTA / COMPROBACION_POST_ALEGACIONES
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Triggers soportados:
    - `datos.origen == "responsabilidad_civil_danos_personales"` con
      `resolucion_judicial=True` y `incluida_como_renta_sujeta=True`.
    - `datos.origen == "acuerdo_mediacion_MASC"` con `importe` dentro del
      `importe_baremo_aplicable`.
    - `datos.pagador == "aseguradora"` con `en_cumplimiento_sentencia=True`.

Anti-hardcode (Invariante #2): la cita canonica ("Art. 7.d LIRPF",
"LO 1/2025") la resuelve el `defensia_rag_verifier`. La regla solo emite
una cita semantica libre.
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
# Helper de aislamiento — carga solo R019 tras el reset del conftest
# ---------------------------------------------------------------------------

def _cargar_solo_R019() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R019.

    El conftest autouse `_aislar_registry` vacia el REGISTRY antes de cada
    test. Como `importlib.import_module` devuelve el modulo cacheado sin
    re-ejecutar el decorador `@regla`, hay que forzar un reload para que R019
    se vuelva a registrar en el REGISTRY limpio.
    """
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_irpf.R019_exencion_danos_personales"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R019():
    """Garantiza que R019 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R019()
    yield


# ---------------------------------------------------------------------------
# Helper local — anti-hardcode de cita canonica
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear el articulo canonico.

    La cita final ("Art. 7.d LIRPF", "LO 1/2025", "Baremo de la Ley 35/2015")
    la resuelve el RAG verificador contra el corpus normativo. Aqui solo
    aceptamos descripciones semanticas libres.
    """
    assert "Art. 7.d" not in cita, (
        f"Cita hardcoded detectada: 'Art. 7.d' en '{cita}'."
    )
    assert "LO 1/2025" not in cita, (
        f"Cita hardcoded detectada: 'LO 1/2025' en '{cita}'."
    )
    assert "7.d LIRPF" not in cita.upper(), (
        f"Cita hardcoded detectada: '7.d LIRPF' en '{cita}'."
    )
    assert "ley organica 1/2025" not in cita.lower(), (
        f"Cita hardcoded detectada: 'Ley Organica 1/2025' en '{cita}'."
    )
    assert "articulo 7.d" not in cita.lower(), (
        f"Cita hardcoded detectada: 'articulo 7.d' en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: indemnizacion judicial por danos personales
# ---------------------------------------------------------------------------

def test_R019_positivo_indemnizacion_judicial_danos_personales(
    build_exp, build_brief, build_doc
):
    """Si AEAT incluye como renta sujeta una indemnizacion por responsabilidad
    civil por danos personales reconocida por resolucion judicial, dispara R019.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "indemnizacion_declarada_exenta": 30000,
            "origen": "responsabilidad_civil_danos_personales",
            "resolucion_judicial": True,
            "incluida_como_renta_sujeta": True,
            "tributo": "IRPF",
            "ejercicio": 2024,
        },
        doc_id="doc-liq-R019-001",
        nombre_original="liquidacion_indemnizacion_danos.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
    )
    brief = build_brief(
        "AEAT me incluye como renta sujeta una indemnizacion por danos "
        "personales que me reconocio el juzgado tras un accidente."
    )

    candidatos = evaluar(exp, brief)

    r019 = [c for c in candidatos if c.regla_id == "R019"]
    assert len(r019) == 1, (
        f"R019 deberia disparar con indemnizacion judicial por danos "
        f"personales, got {candidatos}"
    )

    arg = r019[0]
    assert isinstance(arg, ArgumentoCandidato)

    # Cita semantica — nunca hardcoded.
    cita = arg.cita_normativa_propuesta
    _assert_cita_no_hardcoded(cita)
    cita_lower = cita.lower()
    assert "indemniza" in cita_lower, (
        f"La cita semantica debe mencionar indemnizacion, got: {cita!r}"
    )
    assert "danos personales" in cita_lower, (
        f"La cita semantica debe mencionar 'danos personales', got: {cita!r}"
    )

    # datos_disparo debe exponer el motivo y conservar rastros del disparo.
    disparo = arg.datos_disparo
    assert disparo.get("motivo") == "responsabilidad_civil_judicial", (
        f"datos_disparo.motivo inesperado: {disparo!r}"
    )
    assert disparo.get("importe") == 30000, (
        f"datos_disparo.importe inesperado: {disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: acuerdo de mediacion MASC dentro del Baremo
# ---------------------------------------------------------------------------

def test_R019_positivo_acuerdo_mediacion_MASC_dentro_baremo(
    build_exp, build_brief, build_doc
):
    """Extension LO 1/2025: acuerdos de mediacion y MASC estan exentos hasta
    el limite del Baremo aplicable. Importe 15000 < Baremo 18000 -> dispara.
    """
    doc = build_doc(
        TipoDocumento.OTROS,
        datos={
            "origen": "acuerdo_mediacion_MASC",
            "importe": 15000,
            "importe_baremo_aplicable": 18000,
            "incluida_como_renta_sujeta": True,
            "tributo": "IRPF",
        },
        doc_id="doc-masc-R019-002",
        nombre_original="acuerdo_mediacion_masc.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "Alcance un acuerdo de mediacion MASC por danos personales y "
        "Hacienda me lo incluye como ingreso."
    )

    candidatos = evaluar(exp, brief)

    r019 = [c for c in candidatos if c.regla_id == "R019"]
    assert len(r019) == 1, (
        f"R019 deberia disparar con acuerdo MASC dentro del Baremo, "
        f"got {candidatos}"
    )

    arg = r019[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    cita_lower = arg.cita_normativa_propuesta.lower()
    assert (
        "mediacion" in cita_lower
        or "masc" in cita_lower
        or "baremo" in cita_lower
    ), (
        f"La cita semantica debe mencionar mediacion/MASC/Baremo, got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    disparo = arg.datos_disparo
    assert disparo.get("motivo") == "acuerdo_mediacion_MASC", (
        f"datos_disparo.motivo inesperado: {disparo!r}"
    )
    assert disparo.get("importe") == 15000
    assert disparo.get("importe_baremo_aplicable") == 18000


# ---------------------------------------------------------------------------
# Test 3 — Positivo: aseguradora paga en cumplimiento de sentencia
# ---------------------------------------------------------------------------

def test_R019_positivo_aseguradora_en_cumplimiento_sentencia(
    build_exp, build_brief, build_doc
):
    """Si la aseguradora paga en cumplimiento de una sentencia firme que
    reconoce la indemnizacion por danos personales, la exencion aplica
    igual — la fuente del pago no desvirtua la naturaleza indemnizatoria.
    """
    doc = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "origen": "responsabilidad_civil_danos_personales",
            "pagador": "aseguradora",
            "en_cumplimiento_sentencia": True,
            "incluida_como_renta_sujeta": True,
            "tributo": "IRPF",
        },
        doc_id="doc-sentencia-R019-003",
        nombre_original="sentencia_indemnizacion_aseguradora.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.REPOSICION_INTERPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "La aseguradora me pago la indemnizacion en cumplimiento de una "
        "sentencia y Hacienda ahora me la incluye como renta."
    )

    candidatos = evaluar(exp, brief)

    r019 = [c for c in candidatos if c.regla_id == "R019"]
    assert len(r019) == 1, (
        f"R019 deberia disparar con aseguradora en cumplimiento de sentencia, "
        f"got {candidatos}"
    )

    arg = r019[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    disparo = arg.datos_disparo
    assert disparo.get("motivo") == "aseguradora_en_cumplimiento_sentencia", (
        f"datos_disparo.motivo inesperado: {disparo!r}"
    )
    assert disparo.get("pagador") == "aseguradora"


# ---------------------------------------------------------------------------
# Test 4 — Negativo: indemnizacion laboral pactada (no exenta)
# ---------------------------------------------------------------------------

def test_R019_negativo_indemnizacion_laboral_pactada(
    build_exp, build_brief, build_doc
):
    """La exencion del art. 7.d LIRPF cubre la responsabilidad civil por
    danos personales. Una indemnizacion laboral pactada (despido, acuerdo
    extrajudicial sin reconocimiento de danos personales) NO encaja en el
    supuesto exento, por lo que R019 no debe disparar.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "origen": "indemnizacion_laboral_pactada",
            "importe": 25000,
            "resolucion_judicial": False,
            "incluida_como_renta_sujeta": True,
            "tributo": "IRPF",
        },
        doc_id="doc-liq-R019-004",
        nombre_original="liquidacion_indem_laboral.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "Recibi una indemnizacion por despido pactado y Hacienda me la "
        "incluye como ingreso."
    )

    candidatos = evaluar(exp, brief)

    r019 = [c for c in candidatos if c.regla_id == "R019"]
    assert r019 == [], (
        f"R019 NO debe disparar con indemnizacion laboral pactada (no es "
        f"responsabilidad civil por danos personales), got {r019}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: MASC por encima del limite del Baremo
# ---------------------------------------------------------------------------

def test_R019_negativo_masc_supera_baremo(
    build_exp, build_brief, build_doc
):
    """La extension LO 1/2025 acota la exencion al limite del Baremo
    aplicable. Si el importe del acuerdo supera ese limite, la parte
    excedente NO esta exenta y R019 no debe defender por encima del
    importe legal. En ese caso, la regla no dispara (decision
    conservadora: no cubrimos reclamaciones parciales).
    """
    doc = build_doc(
        TipoDocumento.OTROS,
        datos={
            "origen": "acuerdo_mediacion_MASC",
            "importe": 30000,
            "importe_baremo_aplicable": 18000,
            "incluida_como_renta_sujeta": True,
            "tributo": "IRPF",
        },
        doc_id="doc-masc-R019-005",
        nombre_original="acuerdo_masc_supera_baremo.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "Acuerdo MASC por 30000 EUR cuando el Baremo aplicable era 18000 EUR."
    )

    candidatos = evaluar(exp, brief)

    r019 = [c for c in candidatos if c.regla_id == "R019"]
    assert r019 == [], (
        f"R019 NO debe disparar cuando el MASC supera el limite del Baremo, "
        f"got {r019}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode explicito del brief
# ---------------------------------------------------------------------------

def test_R019_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: asercion literal del brief — la cita no puede contener
    `Art. 7.d`, `LO 1/2025` ni `7.d LIRPF`.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "indemnizacion_declarada_exenta": 30000,
            "origen": "responsabilidad_civil_danos_personales",
            "resolucion_judicial": True,
            "incluida_como_renta_sujeta": True,
            "tributo": "IRPF",
        },
        doc_id="doc-liq-R019-006",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Defiende la exencion de mi indemnizacion.")

    candidatos = evaluar(exp, brief)
    r019 = [c for c in candidatos if c.regla_id == "R019"]
    assert len(r019) == 1
    cita = r019[0].cita_normativa_propuesta

    # Asercion literal del brief.
    assert (
        "Art. 7.d" not in cita
        and "LO 1/2025" not in cita
        and "7.d LIRPF" not in cita.upper()
    ), (
        f"La cita normativa debe ser semantica, got: {cita!r}"
    )


# ---------------------------------------------------------------------------
# Sanity checks adicionales (no cuentan como test de acceptance pero cubren
# la metadata del REGISTRY — evitan regresiones en el rango R001-R030).
# ---------------------------------------------------------------------------

def test_R019_registrada_en_registry():
    """Tras el reload R019 debe estar en el REGISTRY con metadata coherente."""
    assert "R019" in REGISTRY, (
        f"R019 no aparece en REGISTRY. Keys: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R019"]
    assert "IRPF" in info["tributos"], (
        f"R019 debe aplicar a IRPF, tributos={info['tributos']}"
    )
    # La exencion art. 7.d LIRPF es especifica de IRPF — no aplica a IVA/ITP/etc.
    for tributo_fuera in ("IVA", "ISD", "ITP", "PLUSVALIA"):
        assert tributo_fuera not in info["tributos"], (
            f"R019 NO deberia aplicar a {tributo_fuera}"
        )
    for fase_esperada in (
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ):
        assert fase_esperada in info["fases"], (
            f"R019 debe aplicar a {fase_esperada}, fases={info['fases']}"
        )
