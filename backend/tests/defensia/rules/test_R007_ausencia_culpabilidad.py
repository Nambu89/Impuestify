"""Tests R007 — ausencia_culpabilidad (T1B-007).

Regla: el acuerdo sancionador debe motivar especificamente la culpabilidad del
obligado tributario. Dispara cuando la motivacion es generica (formulas tipo
"resulta evidente", "no podia ignorar"), cuando razona por exclusion, o cuando
no analiza si la norma admite interpretacion razonable (art. 179.2.d LGT).

Fundamento juridico (resuelto por el RAG verificador, no hardcoded):
    - Art. 179.2.d LGT: exencion por interpretacion razonable de la norma.
    - Art. 183.1 LGT: exigencia de dolo o culpa en las infracciones tributarias.
    - Art. 24.2 CE: presuncion de inocencia.
    - STS 21-9-2020: necesidad de motivacion especifica de la culpabilidad.
    - STS 1695/2024: prohibicion de razonar culpa por exclusion.

Caso David (ground truth): la norma fiscal aplicable (art. 41 bis RIRPF sobre
exencion por reinversion en vivienda habitual con excepcion por separacion
matrimonial ex STS 553/2023) es objetivamente compleja y admite interpretacion
razonable. El acuerdo sancionador 191+194 que AEAT le notifico carece de
motivacion especifica de culpabilidad -> R007 debe disparar.

Principios de estos tests:

- La regla NO hardcodea cita normativa literal (invariante #2 del plan). La
  `cita_normativa_propuesta` es una descripcion semantica libre.
- Cero dependencia de `load_all()`: el scaffold de Parte 2 tiene reglas hermanas
  en desarrollo paralelo (Grupo A) que pueden estar rotas en cualquier instante.
  Para mantener R007 verde de forma independiente, el test importa directamente
  su propio modulo con `importlib.reload` tras el reset autouse del conftest.
"""
from __future__ import annotations

import importlib

from app.models.defensia import (
    ArgumentoCandidato,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import REGISTRY, evaluar, reset_registry


def _cargar_solo_R007() -> None:
    """Importa UNICAMENTE el modulo de R007, registrando la regla en REGISTRY.

    El conftest autouse limpia el registry entre tests, pero la combinacion
    "import normal + reload" ejecuta el decorador dos veces (una por el import
    que popula sys.modules, otra por el reload), causando `Regla duplicada`.
    Estrategia correcta: reset de REGISTRY, y luego bifurcacion — si el modulo
    ya estaba cargado en sys.modules (caso habitual en la suite), reload del
    objeto existente; en caso contrario, import por primera vez. Asi el
    decorador se ejecuta exactamente una vez.
    """
    import sys

    reset_registry()
    module_name = "app.services.defensia_rules.reglas_procedimentales.R007_ausencia_culpabilidad"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


# ---------------------------------------------------------------------------
# Helpers locales — encapsulan el boilerplate minimo para cada caso
# ---------------------------------------------------------------------------

def _exp_con_sancion(
    *,
    fase: Fase,
    datos_sancion: dict,
    tipo_doc: TipoDocumento,
    build_exp,
    build_doc,
) -> ExpedienteEstructurado:
    doc = build_doc(
        tipo_doc,
        datos=datos_sancion,
        doc_id="doc-sancion-R007",
        nombre_original="acuerdo_sancion.pdf",
    )
    return build_exp(
        tributo=Tributo.IRPF,
        fase=fase,
        docs=[doc],
        exp_id="exp-R007-test",
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo caso David: motivacion generica en norma compleja
# ---------------------------------------------------------------------------

def test_R007_dispara_con_motivacion_culpabilidad_generica(
    build_exp, build_doc, build_brief,
):
    """Caso David: acuerdo 191+194 sobre art. 41 bis RIRPF (norma compleja).

    La AEAT motiva la culpabilidad con formulas genericas ("resulta evidente",
    "el contribuyente no podia ignorar"). La norma aplicada admite
    interpretacion razonable. R007 debe disparar con
    `datos_disparo={"motivo": "motivacion_generica"}`.
    """
    _cargar_solo_R007()
    assert "R007" in REGISTRY, "R007 debe estar registrada tras importar su modulo"

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        tipo_doc=TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos_sancion={
            "motivacion_culpabilidad_generica": True,
            "razonamiento_por_exclusion": False,
            "analisis_interpretacion_razonable": False,
            "tipos_infraccion": ["191", "194.1"],
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief(
        "AEAT me ha sancionado 191+194 pero la norma de reinversion es "
        "compleja y admite interpretacion razonable"
    )

    candidatos = evaluar(expediente, brief)

    r007 = [c for c in candidatos if c.regla_id == "R007"]
    assert len(r007) == 1, (
        f"R007 debe disparar con motivacion generica; got {len(r007)} "
        f"candidatos: {candidatos}"
    )
    arg = r007[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.datos_disparo.get("motivo") == "motivacion_generica", (
        f"datos_disparo debe contener motivo='motivacion_generica'; "
        f"got {arg.datos_disparo!r}"
    )
    # Cita semantica — NUNCA hardcoded articulo concreto
    cita = arg.cita_normativa_propuesta.lower()
    assert "culpabilidad" in cita, (
        f"cita_normativa_propuesta debe mencionar 'culpabilidad'; got {cita!r}"
    )
    assert "motivacion" in cita or "motivación" in cita, (
        f"cita_normativa_propuesta debe mencionar 'motivacion'; got {cita!r}"
    )
    # Anti-hardcode: no debe contener referencias literales a articulos
    assert "179.2" not in arg.cita_normativa_propuesta
    assert "183.1" not in arg.cita_normativa_propuesta
    assert "art." not in cita
    assert "ley 58/2003" not in cita


# ---------------------------------------------------------------------------
# Test 2 — Positivo: razonamiento por exclusion
# ---------------------------------------------------------------------------

def test_R007_dispara_con_razonamiento_por_exclusion(
    build_exp, build_doc, build_brief,
):
    """STS 1695/2024 proscribe razonar la culpa "por exclusion".

    Si el acuerdo deduce la culpabilidad solo porque no ve concurrencia de
    alguna causa de exoneracion, sin probar dolo ni culpa positiva, R007
    debe disparar.
    """
    _cargar_solo_R007()

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        tipo_doc=TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos_sancion={
            "motivacion_culpabilidad_generica": False,
            "razonamiento_por_exclusion": True,
            "analisis_interpretacion_razonable": True,
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)

    r007 = [c for c in candidatos if c.regla_id == "R007"]
    assert len(r007) == 1, (
        "R007 debe disparar cuando el acuerdo razona la culpa por exclusion"
    )
    assert r007[0].datos_disparo.get("motivo") == "razonamiento_por_exclusion"


# ---------------------------------------------------------------------------
# Test 3 — Positivo: falta analisis de interpretacion razonable
# ---------------------------------------------------------------------------

def test_R007_dispara_sin_analisis_interpretacion_razonable(
    build_exp, build_doc, build_brief,
):
    """Art. 179.2.d LGT exige analizar si la norma admite interpretacion razonable.

    Si el acuerdo sancionador omite ese analisis, la motivacion es
    estructuralmente defectuosa y R007 debe disparar.
    """
    _cargar_solo_R007()

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        tipo_doc=TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos_sancion={
            "motivacion_culpabilidad_generica": False,
            "razonamiento_por_exclusion": False,
            "analisis_interpretacion_razonable": False,
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)

    r007 = [c for c in candidatos if c.regla_id == "R007"]
    assert len(r007) == 1, (
        "R007 debe disparar cuando no hay analisis de interpretacion razonable"
    )
    assert r007[0].datos_disparo.get("motivo") == "sin_analisis_interpretacion_razonable"


# ---------------------------------------------------------------------------
# Test 4 — Negativo: motivacion especifica completa
# ---------------------------------------------------------------------------

def test_R007_no_dispara_con_motivacion_especifica_completa(
    build_exp, build_doc, build_brief,
):
    """Cuando el acuerdo sancionador motiva especificamente la culpabilidad,
    no razona por exclusion y analiza expresamente si la norma admite
    interpretacion razonable, R007 NO debe disparar.
    """
    _cargar_solo_R007()

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        tipo_doc=TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos_sancion={
            "motivacion_culpabilidad_generica": False,
            "razonamiento_por_exclusion": False,
            "analisis_interpretacion_razonable": True,
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)

    assert not any(c.regla_id == "R007" for c in candidatos), (
        "R007 NO debe disparar cuando la motivacion de la culpabilidad es "
        "especifica, no razona por exclusion y analiza la interpretacion "
        "razonable de la norma"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: fase no sancionadora (filtro del motor)
# ---------------------------------------------------------------------------

def test_R007_no_dispara_fuera_de_fase_sancionadora(
    build_exp, build_doc, build_brief,
):
    """Aunque los datos coincidan con el trigger, si la fase del expediente es
    LIQUIDACION_FIRME_PLAZO_RECURSO (sin sancion notificada todavia), R007
    NO debe disparar por filtrado de fase del motor.

    Este test valida dos cosas simultaneamente:
    1. La lista de `fases` declaradas en el decorador excluye las fases de
       comprobacion/liquidacion pre-sancion.
    2. El engine efectivamente filtra antes de ejecutar la regla (defensa
       en profundidad).
    """
    _cargar_solo_R007()

    # Usamos una LIQUIDACION_PROVISIONAL en fase pre-sancion. El documento no
    # es un acuerdo sancionador, y la fase no esta en la whitelist de R007.
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "motivacion_culpabilidad_generica": True,
            "razonamiento_por_exclusion": True,
            "analisis_interpretacion_razonable": False,
        },
        doc_id="doc-liq-R007",
        nombre_original="liquidacion_provisional.pdf",
    )
    expediente = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
        exp_id="exp-R007-fase-no-sancion",
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)

    assert not any(c.regla_id == "R007" for c in candidatos), (
        "R007 NO debe disparar en fase LIQUIDACION_FIRME_PLAZO_RECURSO: "
        "la whitelist de fases del decorador debe excluirla"
    )
