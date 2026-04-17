"""Tests de la regla R024 — isd_reduccion_parentesco (T1B-024).

La regla modela el supuesto del art. 20.2.a LISD (Ley 29/1987, del Impuesto
sobre Sucesiones y Donaciones) — reducciones estatales por razon del
parentesco con el causante, aplicables a los grupos I (descendientes y
adoptados menores de 21 anos) y II (descendientes de 21 o mas, conyuges,
ascendientes y adoptantes) — sin perjuicio de las bonificaciones y mejoras
autonomicas que la Comunidad Autonoma del causante haya aprobado (por
ejemplo, el 99 % de Madrid o Andalucia).

La regla dispara cuando la liquidacion / propuesta ISD:

    - No aplica la reduccion estatal por parentesco a un causahabiente del
      grupo I o II.
    - Aplica la estatal pero ignora la bonificacion autonomica procedente
      de la Comunidad Autonoma del causante (grupos I / II).

La regla NO dispara cuando:

    - El causahabiente pertenece al grupo III (hermanos, sobrinos, tios) o
      al IV (colaterales mas lejanos, extranos) — esta primera pasada cubre
      unicamente la reduccion por parentesco de los grupos I y II.
    - La liquidacion ya aplica tanto la reduccion estatal como la
      bonificacion autonomica aplicable: no hay error que impugnar.

Invariante #2 (anti-alucinacion): la regla devuelve una descripcion y una
cita semanticas libres. La cita canonica ("Art. 20.2.a LISD",
"Ley 29/1987", "Art. 20.2.a") la resuelve el ``defensia_rag_verifier``
contra el corpus normativo, nunca este modulo.
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
from app.services.defensia_rules_engine import evaluar, reset_registry


# ---------------------------------------------------------------------------
# Helper de aislamiento — carga solo R024 tras el reset del conftest
# ---------------------------------------------------------------------------
#
# El conftest autouse `_aislar_registry` vacia el REGISTRY antes de cada test.
# Como `importlib.import_module` devuelve el modulo cacheado sin re-ejecutar
# el decorador `@regla`, hay que forzar un reload para re-registrar R024 en
# el REGISTRY recien limpiado.

def _cargar_solo_R024() -> None:
    """Limpia el REGISTRY y re-registra exclusivamente la regla R024."""
    reset_registry()
    module_name = (
        "app.services.defensia_rules.reglas_otros_tributos."
        "R024_isd_reduccion_parentesco"
    )
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R024():
    """Garantiza que R024 esta registrada en el REGISTRY al iniciar cada test."""
    _cargar_solo_R024()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Art. 20.2.a LISD", "Ley 29/1987") la resuelve el RAG
    verificador contra el corpus normativo. Aqui solo aceptamos descripciones
    semanticas libres.
    """
    assert "Art. 20.2.a" not in cita, (
        f"Cita hardcoded detectada: 'Art. 20.2.a' en '{cita}'. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "20.2.a LISD" not in cita, (
        f"Cita hardcoded detectada: '20.2.a LISD' en '{cita}'."
    )
    assert "Ley 29/1987" not in cita, (
        f"Cita hardcoded detectada: 'Ley 29/1987' en '{cita}'."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: grupo II sin reduccion estatal aplicada
# ---------------------------------------------------------------------------

def test_R024_positivo_grupo_II_sin_reduccion_estatal(
    build_exp, build_brief, build_doc
):
    """Grupo II (descendiente +21, conyuge, ascendiente) sin reduccion estatal.

    Causahabiente perteneciente al grupo II (descendientes de 21 o mas anos,
    conyuges, ascendientes y adoptantes). La liquidacion complementaria ISD
    no aplica la reduccion estatal por parentesco, lo que eleva
    artificialmente la cuota. R024 debe disparar y proponer el argumento
    para que el defensa lo incorpore al escrito.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ISD",
            "grupo_parentesco": "II",
            "reduccion_estatal_aplicada": False,
            "ejercicio": 2025,
        },
        doc_id="doc-liquidacion-R024-001",
        fecha_acto=datetime(2025, 6, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.ISD,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
        ccaa="Madrid",
    )
    brief = build_brief(
        "Mi padre fallecio y en la liquidacion del impuesto de sucesiones "
        "no me han aplicado ninguna reduccion por ser su hijo."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R024"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("grupo_parentesco") == "II"
    assert disparo.get("reduccion_estatal_aplicada") is False


# ---------------------------------------------------------------------------
# Test 2 — Positivo: grupo I (descendiente <21) sin reduccion estatal
# ---------------------------------------------------------------------------

def test_R024_positivo_grupo_I_sin_reduccion_estatal(
    build_exp, build_brief, build_doc
):
    """Grupo I (descendiente o adoptado menor de 21 anos) sin reduccion estatal.

    El grupo I es el mas protegido por la normativa: descendientes y
    adoptados menores de 21 anos, que se benefician de la reduccion estatal
    mas alta y ademas de las bonificaciones autonomicas ampliadas en la
    mayoria de CCAA. Omitir la reduccion estatal en este grupo es un error
    material grave.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ISD",
            "grupo_parentesco": "I",
            "reduccion_estatal_aplicada": False,
            "ejercicio": 2025,
        },
        doc_id="doc-liquidacion-R024-002",
        fecha_acto=datetime(2025, 7, 1, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.ISD,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
        ccaa="Andalucia",
    )
    brief = build_brief(
        "Mi hijo de 14 anos ha heredado de su abuelo y no le han aplicado "
        "la reduccion por parentesco en la liquidacion."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R024"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("grupo_parentesco") == "I"
    assert disparo.get("reduccion_estatal_aplicada") is False


# ---------------------------------------------------------------------------
# Test 3 — Positivo: estatal aplicada pero autonomica ignorada
# ---------------------------------------------------------------------------

def test_R024_positivo_bonificacion_autonomica_ignorada(
    build_exp, build_brief, build_doc
):
    """Estatal aplicada pero bonificacion autonomica procedente no aplicada.

    Ejemplo clasico: causante con residencia habitual en Madrid. La
    liquidacion aplica la reduccion estatal por parentesco pero ignora la
    bonificacion autonomica del 99 % del art. 25 del TR madrileno. El
    resultado es una cuota sustancialmente mas alta de la que procederia.
    La regla debe detectar el escenario y proponer el argumento.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ISD",
            "grupo_parentesco": "II",
            "reduccion_estatal_aplicada": True,
            "bonificacion_autonomica_aplicable": True,
            "bonificacion_autonomica_aplicada": False,
            "ccaa_causante": "Madrid",
            "ejercicio": 2025,
        },
        doc_id="doc-liquidacion-R024-003",
        fecha_acto=datetime(2025, 5, 20, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.ISD,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
        ccaa="Madrid",
    )
    brief = build_brief(
        "Mi madre fallecio en Madrid. Me han aplicado la reduccion estatal "
        "pero no la bonificacion autonomica madrilena del 99 %."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R024"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    disparo = arg.datos_disparo
    assert disparo.get("grupo_parentesco") == "II"
    assert disparo.get("bonificacion_autonomica_aplicable") is True
    assert disparo.get("bonificacion_autonomica_aplicada") is False
    assert disparo.get("ccaa_causante") == "Madrid"


# ---------------------------------------------------------------------------
# Test 4 — Negativo: grupo III (hermanos, tios) — fuera de alcance v1
# ---------------------------------------------------------------------------

def test_R024_negativo_grupo_III_fuera_de_alcance(
    build_exp, build_brief, build_doc
):
    """Grupo III (hermanos, sobrinos, tios): R024 NO debe disparar.

    Esta primera pasada de la regla cubre unicamente los grupos I y II, que
    son los que reciben tanto la reduccion estatal del art. 20.2.a LISD en
    su cuantia maxima como las bonificaciones autonomicas del 95-99 %. El
    grupo III tiene reducciones especificas mucho mas reducidas y pocas CCAA
    ofrecen bonificacion significativa, por lo que queda excluido de R024
    hasta que se modele una regla R0xx dedicada.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ISD",
            "grupo_parentesco": "III",
            "reduccion_estatal_aplicada": False,
            "ejercicio": 2025,
        },
        doc_id="doc-liquidacion-R024-004",
        fecha_acto=datetime(2025, 8, 15, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.ISD,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
        ccaa="Madrid",
    )
    brief = build_brief(
        "He heredado de mi hermano y creo que la liquidacion no es correcta."
    )

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R024 NO deberia disparar para grupo III (hermanos, sobrinos, tios) "
        f"en esta primera pasada, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: todas las reducciones aplicadas
# ---------------------------------------------------------------------------

def test_R024_negativo_reducciones_correctamente_aplicadas(
    build_exp, build_brief, build_doc
):
    """Liquidacion que aplica estatal + bonificacion autonomica: no dispara.

    Si la Administracion ha aplicado tanto la reduccion estatal por
    parentesco como la bonificacion autonomica procedente, no existe error
    que defender y R024 debe permanecer silenciosa. El filtro evita generar
    falsos positivos que contaminen la lista de argumentos candidatos.
    """
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ISD",
            "grupo_parentesco": "II",
            "reduccion_estatal_aplicada": True,
            "bonificacion_autonomica_aplicable": True,
            "bonificacion_autonomica_aplicada": True,
            "ccaa_causante": "Madrid",
            "ejercicio": 2025,
        },
        doc_id="doc-liquidacion-R024-005",
        fecha_acto=datetime(2025, 5, 20, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.ISD,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
        ccaa="Madrid",
    )
    brief = build_brief("Revision de la liquidacion por sucesion.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R024 NO deberia disparar cuando estatal y autonomica ya estan "
        f"aplicadas, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode: la cita es semantica, no cita canonica
# ---------------------------------------------------------------------------

def test_R024_cita_es_semantica_no_hardcoded(
    build_exp, build_brief, build_doc
):
    """Invariante #2: la cita normativa NO puede contener el articulo canonico."""
    liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "ISD",
            "grupo_parentesco": "II",
            "reduccion_estatal_aplicada": False,
            "ejercicio": 2025,
        },
        doc_id="doc-liquidacion-R024-006",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.ISD,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[liquidacion],
        ccaa="Madrid",
    )
    brief = build_brief("Defiende mi caso de reduccion por parentesco ISD.")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1
    arg = candidatos[0]

    cita = arg.cita_normativa_propuesta
    assert (
        "Art. 20.2.a" not in cita
        and "20.2.a LISD" not in cita
        and "Ley 29/1987" not in cita
    ), (
        f"La cita normativa debe ser semantica, got: {cita!r}"
    )


