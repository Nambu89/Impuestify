"""Tests TDD para la regla R012 — anualidades_alimentos_hijos.

La regla dispara cuando el acto AEAT regulariza IRPF sin aplicar la
especialidad tributaria de las anualidades por alimentos a hijos fijadas
por decision judicial (arts. 64 y 75 LIRPF — escalas separadas A y B de
gravamen).

Base normativa (la resuelve el RAG verificador, NO la regla):
    - Art. 64 LIRPF: especialidad aplicable a las anualidades por
      alimentos a favor de los hijos — separacion de la base liquidable
      general en dos partes para aplicar la escala estatal de gravamen.
    - Art. 75 LIRPF: misma especialidad a efectos de la escala
      autonomica / complementaria.
    - Convenio regulador homologado judicialmente o sentencia de
      modificacion de medidas familiares como titulo que fija las
      anualidades.

Relevancia caso David Oliva (ground truth del producto): la sentencia de
28-06-2024 modifica medidas familiares. Probable inclusion de anualidades
por alimentos → regla dispara como ajuste defensivo a favor del
contribuyente cuando la liquidacion provisional no haya aplicado la
especialidad.

Triggers soportados:
    - Documento ``SENTENCIA_JUDICIAL`` con ``datos.incluye_anualidades_alimentos=True``
      o ``datos.modifica_medidas_familiares=True`` como prueba del titulo.
    - Documento ``LIQUIDACION_PROVISIONAL`` con ``datos.aplica_escalas_separadas=False``
      (AEAT no ha aplicado la especialidad).
    - Flag ``datos.progenitor_no_custodio=True`` cuando figura en la
      liquidacion — es el perfil tipico del pagador de anualidades.

La regla NO hardcodea los literales "Art. 64" ni "Art. 75 LIRPF" — solo
emite una cita semantica ("anualidades por alimentos", "escalas separadas
de gravamen") que el verificador RAG traducira al texto canonico correcto.
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
# Aislamiento R012 — re-import del modulo tras el reset del conftest
# ---------------------------------------------------------------------------

def _cargar_solo_R012() -> None:
    """Fuerza la re-carga del modulo R012 para que el decorador se ejecute.

    El fixture autouse ``_aislar_registry`` del conftest limpia el REGISTRY
    antes de cada test. Como ``@regla`` registra por side-effect del import,
    hay que reimportar el modulo para que la regla vuelva a aparecer.
    """
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_irpf.R012_anualidades_alimentos"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _registrar_r012(_aislar_registry):  # noqa: ARG001 — fuerza orden
    """Re-importa R012 tras cada ``reset_registry()`` del conftest.

    Declaramos ``_aislar_registry`` como dependencia explicita para
    garantizar que el reset del conftest ocurre ANTES de este re-registro.
    """
    _cargar_solo_R012()
    yield


# ---------------------------------------------------------------------------
# Helper local — la cita NUNCA puede hardcodear articulos canonicos
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: ArgumentoCandidato | str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Arts. 64 y 75 LIRPF") la resuelve el RAG verificador
    contra el corpus normativo. Aqui solo aceptamos descripciones
    semanticas libres. Aceptamos directamente ``ArgumentoCandidato`` para
    comodidad del call-site.
    """
    texto = cita.cita_normativa_propuesta if isinstance(cita, ArgumentoCandidato) else cita
    prohibidas = [
        "Art. 64",
        "Art. 75 LIRPF",
        "75 LIRPF",
        "Articulo 64",
        "Articulo 75",
        "art. 64",
        "art. 75",
        "LIRPF 64",
        "LIRPF 75",
    ]
    for prohibida in prohibidas:
        assert prohibida.lower() not in texto.lower(), (
            f"Cita hardcoded detectada: '{prohibida}' en '{texto}'. "
            "La cita canonica debe venir del RAG verificador."
        )


# ---------------------------------------------------------------------------
# Test 1 — Positivo caso David: liquidacion + sentencia modificacion medidas
# ---------------------------------------------------------------------------

def test_R012_positivo_caso_david_sentencia_modifica_medidas(
    build_exp, build_brief, build_doc
):
    """Caso David Oliva: liquidacion provisional sin aplicar la
    especialidad de anualidades por alimentos + sentencia judicial que
    modifica las medidas familiares e incluye anualidades → dispara.
    """
    sentencia = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "modifica_medidas_familiares": True,
            "incluye_anualidades_alimentos": True,
        },
        doc_id="doc-sentencia-28jun2024",
        nombre_original="sentencia_modificacion_medidas_28_06_2024.pdf",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "aplica_escalas_separadas": False,
            "progenitor_no_custodio": True,
        },
        doc_id="doc-liq-irpf-david",
        nombre_original="liquidacion_provisional_irpf.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[sentencia, liquidacion],
    )
    brief = build_brief(
        "AEAT me ha regularizado el IRPF sin tener en cuenta las "
        "anualidades por alimentos que pago por sentencia de modificacion "
        "de medidas"
    )

    candidatos = evaluar(exp, brief)

    r012 = [c for c in candidatos if c.regla_id == "R012"]
    assert len(r012) == 1, (
        f"R012 deberia disparar en caso David (sentencia + liquidacion "
        f"sin escalas separadas), got {candidatos}"
    )

    arg = r012[0]
    assert isinstance(arg, ArgumentoCandidato)

    _assert_cita_no_hardcoded(arg)
    texto_cita = arg.cita_normativa_propuesta.lower()
    assert "anualidades" in texto_cita, (
        f"La cita semantica debe mencionar 'anualidades', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )
    assert "alimentos" in texto_cita, (
        f"La cita semantica debe mencionar 'alimentos', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    # datos_disparo debe exponer informacion util para el writer
    assert arg.datos_disparo.get("sentencia_id") == "doc-sentencia-28jun2024"
    assert arg.datos_disparo.get("liquidacion_id") == "doc-liq-irpf-david"
    assert arg.datos_disparo.get("aplica_escalas_separadas") is False


# ---------------------------------------------------------------------------
# Test 2 — Positivo: progenitor no custodio sin escalas separadas
# ---------------------------------------------------------------------------

def test_R012_positivo_progenitor_no_custodio(
    build_exp, build_brief, build_doc
):
    """Si el expediente contiene una sentencia con anualidades por
    alimentos y la liquidacion marca al contribuyente como progenitor no
    custodio sin aplicar escalas separadas, dispara.
    """
    sentencia = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "incluye_anualidades_alimentos": True,
            "modifica_medidas_familiares": False,
        },
        doc_id="doc-sentencia-divorcio",
        nombre_original="sentencia_divorcio.pdf",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "aplica_escalas_separadas": False,
            "progenitor_no_custodio": True,
        },
        doc_id="doc-liq-irpf",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[sentencia, liquidacion],
    )
    brief = build_brief(
        "Soy el progenitor no custodio y pago anualidades por alimentos "
        "a mis hijos"
    )

    candidatos = evaluar(exp, brief)

    r012 = [c for c in candidatos if c.regla_id == "R012"]
    assert len(r012) == 1, (
        f"R012 deberia disparar para progenitor no custodio sin escalas "
        f"separadas, got {candidatos}"
    )

    arg = r012[0]
    _assert_cita_no_hardcoded(arg)
    assert arg.datos_disparo.get("progenitor_no_custodio") is True


# ---------------------------------------------------------------------------
# Test 3 — Negativo: sentencia sin anualidades por alimentos
# ---------------------------------------------------------------------------

def test_R012_negativo_sentencia_sin_anualidades(
    build_exp, build_brief, build_doc
):
    """Si la sentencia judicial NO incluye anualidades por alimentos (y
    tampoco modifica medidas familiares), la regla NO dispara aunque la
    liquidacion no aplique escalas separadas.
    """
    sentencia = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "incluye_anualidades_alimentos": False,
            "modifica_medidas_familiares": False,
        },
        doc_id="doc-sentencia-otros",
        nombre_original="sentencia_otros_asuntos.pdf",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "aplica_escalas_separadas": False,
        },
        doc_id="doc-liq",
        nombre_original="liquidacion.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[sentencia, liquidacion],
    )
    brief = build_brief("Tengo una liquidacion provisional de IRPF")

    candidatos = evaluar(exp, brief)

    r012 = [c for c in candidatos if c.regla_id == "R012"]
    assert r012 == [], (
        f"R012 NO debe disparar si la sentencia no incluye anualidades "
        f"por alimentos, got {r012}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: escalas ya aplicadas correctamente
# ---------------------------------------------------------------------------

def test_R012_negativo_escalas_ya_aplicadas(
    build_exp, build_brief, build_doc
):
    """Si la liquidacion provisional ya aplica las escalas separadas de
    gravamen, la regla NO dispara — la especialidad ya esta reconocida
    por AEAT y no hay ajuste defensivo que reclamar.
    """
    sentencia = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "incluye_anualidades_alimentos": True,
            "modifica_medidas_familiares": True,
        },
        doc_id="doc-sentencia-ok",
        nombre_original="sentencia.pdf",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "aplica_escalas_separadas": True,
            "progenitor_no_custodio": True,
        },
        doc_id="doc-liq-ok",
        nombre_original="liquidacion_con_escalas.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[sentencia, liquidacion],
    )
    brief = build_brief("Me han aplicado correctamente las escalas separadas")

    candidatos = evaluar(exp, brief)

    r012 = [c for c in candidatos if c.regla_id == "R012"]
    assert r012 == [], (
        f"R012 NO debe disparar si AEAT ya aplica las escalas separadas, "
        f"got {r012}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Anti-hardcode: la cita nunca referencia literales canonicos
# ---------------------------------------------------------------------------

def test_R012_cita_no_hardcodea_articulos(
    build_exp, build_brief, build_doc
):
    """Invariante #2 explicito: la cita semantica NUNCA puede contener
    los literales "Art. 64" ni "75 LIRPF" — esas referencias canonicas
    las resuelve el RAG verificador contra el corpus normativo.
    """
    sentencia = build_doc(
        TipoDocumento.SENTENCIA_JUDICIAL,
        datos={
            "incluye_anualidades_alimentos": True,
            "modifica_medidas_familiares": True,
        },
        doc_id="doc-sentencia",
        nombre_original="sentencia.pdf",
    )
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "aplica_escalas_separadas": False,
            "progenitor_no_custodio": True,
        },
        doc_id="doc-liq",
        nombre_original="liq.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[sentencia, liquidacion],
    )
    brief = build_brief("Test anti-hardcode")

    candidatos = evaluar(exp, brief)
    r012 = [c for c in candidatos if c.regla_id == "R012"]
    assert len(r012) == 1

    arg = r012[0]
    # Asercion textual literal exigida por el brief de la tarea:
    # la cita no puede contener "Art. 64" ni "75 LIRPF".
    assert "art. 64" not in arg.cita_normativa_propuesta.lower() and (
        "75 lirpf" not in arg.cita_normativa_propuesta.lower()
    ), (
        f"La cita de R012 hardcodea un articulo canonico: "
        f"{arg.cita_normativa_propuesta!r}. Debe ser semantica."
    )

    # Descripcion tampoco debe hardcodear articulos — es el texto que el
    # writer usa como base; el RAG verifica la cita canonica aparte.
    _assert_cita_no_hardcoded(arg)


# ---------------------------------------------------------------------------
# Sanity check: la regla esta registrada con la metadata correcta
# ---------------------------------------------------------------------------

def test_R012_registrada_en_registry():
    """Tras importar el modulo, R012 debe estar en el REGISTRY con los
    tributos (solo IRPF) y las fases declaradas en el brief.
    """
    assert "R012" in REGISTRY, (
        f"R012 no encontrada en REGISTRY. "
        f"Keys actuales: {list(REGISTRY.keys())}"
    )
    info = REGISTRY["R012"]

    # R012 es una regla sustantiva IRPF — solo aplica a IRPF.
    assert info["tributos"] == {"IRPF"}, (
        f"R012 deberia aplicar solo a IRPF, tributos={info['tributos']}"
    )

    # Fases exigidas por el brief de la tarea.
    fases_esperadas = {
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "SANCIONADOR_IMPUESTA",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    }
    assert fases_esperadas.issubset(info["fases"]), (
        f"R012 debe aplicar a {fases_esperadas}, fases={info['fases']}"
    )
