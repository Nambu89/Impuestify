"""Tests R006 non_bis_in_idem (T1B-006).

Regla: AEAT sanciona por Art. 191 LGT (dejar de ingresar) Y adicionalmente por
Art. 194 LGT (solicitud indebida de devoluciones) sobre los mismos hechos. La
regla dispara cuando se detecta esa doble tipicidad 191+194.

Principios de estos tests:

- La regla NO debe hardcodear la cita "Art. 180 LGT" ni "Art. 25 CE" ni ninguna
  referencia normativa explicita. Eso es dogma del invariante #2 del plan: las
  reglas proponen argumentos con descripcion semantica libre y es el RAG
  verifier quien devuelve la cita canonica. El test 5 hace esta asercion
  explicita.
- Parte 1 expone en el extractor de sanciones el derivado booleano
  `tiene_doble_tipicidad_191_194`. La regla debe consumirlo directamente y
  tambien soportar una fallback via `tipos_infraccion` para robustez.
- Cero dependencia de `load_all()`: el scaffold de Parte 2 aun tiene reglas
  hermanas en desarrollo paralelo (Grupo A) que pueden estar rotas en cualquier
  instante. Para mantener R006 verde de forma independiente, el test importa
  directamente su propio modulo — eso dispara el decorador `@regla` y registra
  la R006 en el REGISTRY sin tocar las otras.
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


def _cargar_solo_R006() -> None:
    """Importa UNICAMENTE el modulo de R006, registrando la regla en REGISTRY.

    El conftest autouse limpia el registry entre tests, asi que cada test
    necesita llamar a este helper para activar R006. Siempre hacemos
    `reset_registry()` + `importlib.reload()` para ser idempotentes sea cual
    sea el estado previo del proceso: el import inicial ejecuta el decorador,
    los reloads subsiguientes tambien — y el reset evita el ValueError por
    duplicado del motor.
    """
    from app.services.defensia_rules.reglas_procedimentales import (
        R006_non_bis_in_idem,
    )
    reset_registry()
    importlib.reload(R006_non_bis_in_idem)


# ---------------------------------------------------------------------------
# Helpers locales — encapsulan el boilerplate minimo para cada caso
# ---------------------------------------------------------------------------

def _exp_con_sancion(
    *,
    fase: Fase,
    datos_sancion: dict,
    build_exp,
    build_doc,
) -> ExpedienteEstructurado:
    doc = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos=datos_sancion,
        doc_id="doc-sancion-R006",
        nombre_original="acuerdo_sancion.pdf",
    )
    return build_exp(
        tributo=Tributo.IRPF,
        fase=fase,
        docs=[doc],
        exp_id="exp-R006-test",
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo caso David: doble tipicidad 191+194 detectada por extractor
# ---------------------------------------------------------------------------

def test_R006_dispara_con_doble_tipicidad_flag_true(
    build_exp, build_doc, build_brief,
):
    """El flag `tiene_doble_tipicidad_191_194=True` debe disparar la regla.

    Este es el camino del caso David: el extractor de Parte 1
    (`extract_acuerdo_sancion`) calcula el derivado y la regla lo consume
    directamente. La regla NO debe re-inspeccionar `base_sancion_191/194`
    cuando el flag ya esta presente — usar el derivado es su contrato.
    """
    _cargar_solo_R006()
    assert "R006" in REGISTRY, "R006 debe estar registrada tras load_all()"

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        datos_sancion={
            "tiene_doble_tipicidad_191_194": True,
            "base_sancion_191": 6183.05,
            "base_sancion_194": 2013.39,
            "articulos_tipicos": ["Art. 191 LGT", "Art. 194.1 LGT"],
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("AEAT me ha sancionado dos veces por los mismos hechos")

    candidatos = evaluar(expediente, brief)

    r006 = [c for c in candidatos if c.regla_id == "R006"]
    assert len(r006) == 1, (
        f"R006 debe disparar exactamente 1 vez con flag True; got {len(r006)}"
    )
    assert isinstance(r006[0], ArgumentoCandidato)
    assert r006[0].datos_disparo, "datos_disparo no puede estar vacio"


# ---------------------------------------------------------------------------
# Test 2 — Positivo alternativo: datos explicitos via tipos_infraccion
# ---------------------------------------------------------------------------

def test_R006_dispara_con_tipos_infraccion_191_y_194(
    build_exp, build_doc, build_brief,
):
    """Fallback: la regla tambien dispara si `tipos_infraccion` contiene 191 y 194.

    Este path cubre expedientes con extractores legacy o fuentes manuales que
    todavia no exponen el derivado `tiene_doble_tipicidad_191_194`. La regla
    debe ser robusta a ambas formas del dato.
    """
    _cargar_solo_R006()

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        datos_sancion={
            # Nota: NO se pasa `tiene_doble_tipicidad_191_194` — forzamos el
            # path de fallback basado en `tipos_infraccion`.
            "tipos_infraccion": ["191", "194.1"],
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)

    r006 = [c for c in candidatos if c.regla_id == "R006"]
    assert len(r006) == 1, (
        "R006 debe disparar cuando tipos_infraccion contiene 191 y 194 aunque "
        "el flag derivado no este presente"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: solo 191 sin concurrencia con 194
# ---------------------------------------------------------------------------

def test_R006_no_dispara_con_solo_191(
    build_exp, build_doc, build_brief,
):
    """Una sancion 191 aislada NO constituye non bis in idem — no dispara."""
    _cargar_solo_R006()

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        datos_sancion={
            "tipos_infraccion": ["191"],
            "tiene_doble_tipicidad_191_194": False,
            "base_sancion_191": 6183.05,
            "base_sancion_194": None,
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)

    assert not any(c.regla_id == "R006" for c in candidatos), (
        "R006 NO debe disparar cuando solo hay infraccion 191"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: fase no sancionadora
# ---------------------------------------------------------------------------

def test_R006_no_dispara_fuera_de_fase_sancionadora(
    build_exp, build_doc, build_brief,
):
    """Aunque el documento contenga datos compatibles, si la fase del expediente
    es liquidacion provisional (sin sancion aun), R006 NO debe disparar por
    filtrado de fase del motor.

    Este test valida dos cosas simultaneamente:
    1. La lista de `fases` declaradas en el decorador excluye las fases de
       comprobacion/liquidacion.
    2. El engine efectivamente filtra antes de ejecutar la regla (defensa
       en profundidad).
    """
    _cargar_solo_R006()

    # Construimos una fase distinta a las sancionadoras/recurso para validar
    # el filtrado. COMPROBACION_PROPUESTA es representativa de "pre-sancion".
    expediente = _exp_con_sancion(
        fase=Fase.COMPROBACION_PROPUESTA,
        datos_sancion={
            "tiene_doble_tipicidad_191_194": True,
            "tipos_infraccion": ["191", "194.1"],
        },
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)

    assert not any(c.regla_id == "R006" for c in candidatos), (
        "R006 NO debe disparar en fases no sancionadoras"
    )


# ---------------------------------------------------------------------------
# Test 5 — Asercion anti-hardcode (invariante #2 del plan)
# ---------------------------------------------------------------------------

def test_R006_no_hardcodea_cita_normativa(
    build_exp, build_doc, build_brief,
):
    """BLOCKER B2: la regla NO puede hardcodear ninguna cita normativa literal.

    La `cita_normativa_propuesta` debe ser una descripcion semantica libre; la
    resolucion canonica (articulo concreto, redaccion vigente, referencia BOE)
    se delega al RAG verifier en fases posteriores. Este test enforce el
    invariante en el unit test de la propia regla para fallar al commit si
    alguien introduce texto hardcodeado mas adelante.
    """
    _cargar_solo_R006()

    expediente = _exp_con_sancion(
        fase=Fase.SANCIONADOR_IMPUESTA,
        datos_sancion={"tiene_doble_tipicidad_191_194": True},
        build_exp=build_exp,
        build_doc=build_doc,
    )
    brief = build_brief("")

    candidatos = evaluar(expediente, brief)
    r006 = [c for c in candidatos if c.regla_id == "R006"]
    assert len(r006) == 1, "R006 debe disparar para ejecutar las aserciones de texto"

    cita = r006[0].cita_normativa_propuesta
    descripcion = r006[0].descripcion

    # Tokens prohibidos — la lista es deliberadamente paranoica: cualquier
    # variante de "Art. XXX LGT/LIRPF/CE" o numero de articulo con prefijo
    # legal que pudiera usarse como atajo hardcodeado.
    tokens_prohibidos = [
        "Art. 180 LGT",
        "Art. 180",
        "art. 180",
        "articulo 180",
        "Art. 25 CE",
        "Art. 25.1 CE",
        "Artículo 25",
        "Ley 40/2015",
        "Ley 58/2003",
    ]
    for token in tokens_prohibidos:
        assert token not in cita, (
            f"R006.cita_normativa_propuesta NO puede contener '{token}' "
            f"(hardcode prohibido por invariante #2). Valor actual: {cita!r}"
        )
        assert token not in descripcion, (
            f"R006.descripcion NO puede contener '{token}' "
            f"(hardcode prohibido por invariante #2). Valor actual: {descripcion!r}"
        )

    # Positive assertion: la cita debe ser no vacia y tener sabor semantico.
    assert cita, "cita_normativa_propuesta no puede estar vacia"
    assert "non bis in idem" in cita.lower(), (
        "La cita semantica debe mencionar el principio 'non bis in idem' "
        "aunque NO puede referenciar articulos literales"
    )
