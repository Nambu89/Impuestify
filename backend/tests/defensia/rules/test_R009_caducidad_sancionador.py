"""Tests TDD para la regla R009 — caducidad_sancionador (T1B-009).

Base normativa research 2026-04-14:
    - Art. 211.2 LGT (Ley 58/2003): el procedimiento sancionador deberá
      concluir en el plazo máximo de SEIS MESES contados desde la
      notificación del acuerdo de iniciación.
    - Art. 211.4 LGT: la caducidad impide iniciar un nuevo procedimiento
      sancionador sobre los mismos hechos.
    - Doctrina reiterada TS y TEAC sobre cómputo estricto de los 6 meses.

Trigger:
    Dispara cuando, sobre un documento `ACUERDO_IMPOSICION_SANCION`, la
    diferencia entre `datos.fecha_notificacion_sancion` (fin) y
    `datos.fecha_inicio_sancionador` (inicio) excede los 6 meses calendario.
    El calculo usa `dateutil.relativedelta` para respetar meses calendario
    reales (no una aproximacion lineal de 183 dias).

Excepciones (NO dispara):
    - Fase del expediente ajena a sancionador (ej. `LIQUIDACION_FIRME_*`).
    - Plazo dentro de 6 meses (inclusive el limite exacto).

Invariante #2 del plan Parte 2: la regla NUNCA hardcodea citas canonicas
("Art. 211.2 LGT"). La cita la resuelve el RAG verificador en una fase
posterior del pipeline. Aqui solo devolvemos descripciones semanticas.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import REGISTRY, evaluar


# ---------------------------------------------------------------------------
# Helper: carga unicamente la regla R009 (aislamiento respecto a R001-R030
# que podrian no existir en Wave 1B en paralelo).
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _cargar_solo_r009():
    """Importa exclusivamente el modulo R009 para activar su `@regla` decorator.

    Uso de import dinamico dentro del fixture para que el `reset_registry()`
    autouse del conftest de la carpeta se ejecute ANTES (vaciando el REGISTRY)
    y aqui volvamos a registrar solo R009.
    """
    import importlib
    import sys

    modulo = "app.services.defensia_rules.reglas_procedimentales.R009_caducidad_sancionador"
    if modulo in sys.modules:
        del sys.modules[modulo]
    importlib.import_module(modulo)
    yield


# ---------------------------------------------------------------------------
# Guard invariante #2 — cita nunca hardcoded a un articulo concreto.
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """La cita semantica NO puede contener referencias literales al articulo.

    La verificacion canonica contra BOE/TEAC se hace en el RAG verificador.
    """
    prohibidas = [
        "Art. 211.2 LGT",
        "Art. 211.4 LGT",
        "Articulo 211.2 LGT",
        "Articulo 211.4 LGT",
        "art. 211.2",
        "art. 211.4",
        "art 211.2",
        "art 211.4",
    ]
    for prohibida in prohibidas:
        assert prohibida.lower() not in cita.lower(), (
            f"Cita hardcoded detectada: '{prohibida}' en '{cita}'. "
            "La cita canonica debe venir del RAG verificador."
        )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: tramitacion de 7 meses (claramente fuera de plazo).
# ---------------------------------------------------------------------------

def test_R009_positivo_siete_meses_tramitacion(build_exp, build_brief, build_doc):
    """Sancion iniciada 2025-01-15 y notificada 2025-08-20 -> dispara.

    Diferencia aproximada: 217 dias (7 meses + 5 dias). Excede claramente
    el plazo de 6 meses. `datos_disparo.dias_exceso` debe ser ~36 dias (el
    plazo maximo se calcula sumando 6 meses calendario al inicio; el exceso
    son los dias sobre ese limite).
    """
    sancion = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos={
            "fecha_inicio_sancionador": "2025-01-15",
            "fecha_notificacion_sancion": "2025-08-20",
        },
        doc_id="doc-san-001",
        nombre_original="acuerdo_sancion.pdf",
        fecha_acto=datetime(2025, 8, 20, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.SANCIONADOR_IMPUESTA,
        docs=[sancion],
    )
    brief = build_brief(
        "Me han notificado la sancion mas de 7 meses despues del acuerdo de inicio"
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R009"

    # Cita semantica, nunca hardcoded.
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "caducidad" in arg.cita_normativa_propuesta.lower(), (
        f"La cita semantica debe mencionar 'caducidad', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )
    assert "sancionador" in arg.cita_normativa_propuesta.lower(), (
        f"La cita semantica debe mencionar 'sancionador', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    # datos_disparo.dias_exceso debe indicar el exceso sobre los 6 meses.
    dias_exceso = arg.datos_disparo.get("dias_exceso")
    assert dias_exceso is not None, (
        f"datos_disparo debe exponer 'dias_exceso', got: {arg.datos_disparo!r}"
    )
    # 2025-01-15 + 6 meses = 2025-07-15. 2025-08-20 - 2025-07-15 = 36 dias.
    assert dias_exceso == 36, (
        f"dias_exceso esperado ~36 (2025-07-15 -> 2025-08-20), "
        f"got {dias_exceso}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: limite exacto + 1 dia (6 meses + 1 dia).
# ---------------------------------------------------------------------------

def test_R009_positivo_limite_mas_un_dia(build_exp, build_brief, build_doc):
    """Sancion iniciada 2025-01-01 y notificada 2025-07-02 -> dispara.

    2025-01-01 + 6 meses calendario = 2025-07-01 (limite inclusive). El dia
    2025-07-02 esta 1 dia fuera del plazo, por tanto la regla dispara con
    `dias_exceso == 1`. Este es el caso borde que garantiza que el calculo
    NO usa una aproximacion floja de "183 dias" — usa meses calendario.
    """
    sancion = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos={
            "fecha_inicio_sancionador": "2025-01-01",
            "fecha_notificacion_sancion": "2025-07-02",
        },
        doc_id="doc-san-002",
        nombre_original="acuerdo_sancion_limite.pdf",
        fecha_acto=datetime(2025, 7, 2, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.SANCIONADOR_IMPUESTA,
        docs=[sancion],
    )
    brief = build_brief("Notificacion justo un dia fuera del plazo de 6 meses")

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato en el limite +1 dia, "
        f"got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R009"
    assert arg.datos_disparo.get("dias_exceso") == 1, (
        f"dias_exceso en el borde debe ser 1, got {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: dentro del plazo de 6 meses.
# ---------------------------------------------------------------------------

def test_R009_negativo_dentro_de_plazo(build_exp, build_brief, build_doc):
    """Sancion iniciada 2025-01-15 y notificada 2025-05-10 -> NO dispara.

    Diferencia: ~115 dias (menos de 4 meses). Claramente dentro del plazo
    legal de 6 meses. La regla NO debe emitir argumento.
    """
    sancion = build_doc(
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        datos={
            "fecha_inicio_sancionador": "2025-01-15",
            "fecha_notificacion_sancion": "2025-05-10",
        },
        doc_id="doc-san-003",
        nombre_original="acuerdo_sancion_ok.pdf",
        fecha_acto=datetime(2025, 5, 10, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.SANCIONADOR_IMPUESTA,
        docs=[sancion],
    )
    brief = build_brief("Sancion notificada dentro de plazo, revisando otras defensas")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R009 NO deberia disparar dentro del plazo de 6 meses, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: no es sancion (fase de liquidacion).
# ---------------------------------------------------------------------------

def test_R009_negativo_fase_no_sancionadora(build_exp, build_brief, build_doc):
    """Expediente en fase `LIQUIDACION_FIRME_PLAZO_RECURSO` -> NO dispara.

    Aunque las fechas del documento excederian los 6 meses, el filtro por
    fase del motor (`fases=[...]` del decorador) impide la ejecucion de la
    regla porque la caducidad del art. 211 LGT solo aplica al procedimiento
    sancionador, no a las comprobaciones limitadas ni a las liquidaciones.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            # Fechas que en una sancion dispararian, pero este doc es una
            # liquidacion y el expediente esta en fase no sancionadora.
            "fecha_inicio_sancionador": "2025-01-15",
            "fecha_notificacion_sancion": "2025-08-20",
        },
        doc_id="doc-liq-001",
        nombre_original="liquidacion.pdf",
        fecha_acto=datetime(2025, 8, 20, tzinfo=timezone.utc),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Estoy revisando una liquidacion, no hay sancion abierta")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R009 NO deberia disparar fuera de fase sancionadora, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Smoke de registro en el REGISTRY.
# ---------------------------------------------------------------------------

def test_R009_registrada_en_registry():
    """Tras el import autouse, R009 debe estar en el REGISTRY con metadata OK."""
    assert "R009" in REGISTRY, (
        f"R009 no aparece en el REGISTRY. Claves: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R009"]

    # Tributo transversal: el sancionador aplica a los 5 tributos del scope.
    for tributo in ("IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"):
        assert tributo in info["tributos"], (
            f"R009 debe aplicar a {tributo}, tributos={info['tributos']}"
        )

    # Fases aplicables: todas las fases sancionadoras + recurso + TEAR.
    fases_esperadas = {
        "SANCIONADOR_INICIADO",
        "SANCIONADOR_PROPUESTA",
        "SANCIONADOR_IMPUESTA",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    }
    for fase in fases_esperadas:
        assert fase in info["fases"], (
            f"R009 debe incluir fase {fase}, fases={info['fases']}"
        )
