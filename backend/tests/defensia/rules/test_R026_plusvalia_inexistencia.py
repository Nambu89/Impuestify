"""Tests de la regla R026 — plusvalia_inexistencia_incremento (T2C-026).

La regla dispara cuando una liquidacion del Impuesto sobre el Incremento de
Valor de los Terrenos de Naturaleza Urbana (plusvalia municipal) grava una
transmision en la que el valor de transmision es igual o inferior al valor de
adquisicion, de acuerdo con las escrituras publicas. En esos supuestos no
existe un incremento real de valor que pueda sujetarse al impuesto.

Fundamento juridico (la RESUELVE el RAG verificador, NO la regla — invariante
#2):

    - Art. 104.5 TRLHL (introducido por RDL 26/2021, tras STC 59/2017 y STC
      182/2021): supuesto de no sujecion cuando el sujeto pasivo acredita la
      inexistencia de incremento de valor, admitiendo como prueba las
      escrituras publicas de adquisicion y transmision.
    - STS Sala 3.ª 28-2-2024: extiende los efectos de la nulidad a
      liquidaciones firmes en determinados supuestos.

Aislamiento: seguimos el mismo patron que R013 — reset_registry + reload/
import controlado para que solo R026 este en el REGISTRY durante estos
tests, de modo que el conftest global no nos contamine con otras reglas y
los asserts de "len(candidatos) == 1" sean estables.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2C-026
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
# Aislamiento del REGISTRY — carga solo R026
# ---------------------------------------------------------------------------

_R026_MODULE_NAME = (
    "app.services.defensia_rules.reglas_otros_tributos."
    "R026_plusvalia_inexistencia"
)


def _cargar_solo_R026() -> None:
    """Deja en el REGISTRY unicamente la regla R026.

    Patron del brief (drift corregido): reset + import/reload. Si el modulo
    ya estaba cargado en un run anterior, `importlib.reload` fuerza la re-
    ejecucion del decorador `@regla` para que la regla vuelva a aparecer en
    el REGISTRY que el conftest global acaba de limpiar con su autouse.
    """
    reset_registry()
    if _R026_MODULE_NAME in sys.modules:
        importlib.reload(sys.modules[_R026_MODULE_NAME])
    else:
        importlib.import_module(_R026_MODULE_NAME)


@pytest.fixture(autouse=True)
def _recargar_R026():
    """Recarga R026 tras el reset del conftest global antes de cada test."""
    _cargar_solo_R026()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la referencia canonica.

    La cita final ("Art. 104.5 TRLHL", "RDL 26/2021", "STC 59/2017") la
    resuelve el RAG verificador contra el corpus normativo. Aqui solo se
    acepta una descripcion semantica libre del concepto juridico.
    """
    assert "Art. 104.5" not in cita, (
        f"Cita hardcoded detectada: 'Art. 104.5' en {cita!r}. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "TRLHL" not in cita, (
        f"Cita hardcoded detectada: 'TRLHL' en {cita!r}. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "STC 59/2017" not in cita, (
        f"Cita hardcoded detectada: 'STC 59/2017' en {cita!r}. "
        "La cita canonica debe venir del RAG verificador."
    )
    assert "RDL 26/2021" not in cita, (
        f"Cita hardcoded detectada: 'RDL 26/2021' en {cita!r}. "
        "La cita canonica debe venir del RAG verificador."
    )


# ---------------------------------------------------------------------------
# Test 1 — Positivo: perdida acreditada en escrituras
# ---------------------------------------------------------------------------

def test_R026_positivo_perdida_acreditada_escrituras(
    build_exp, build_brief, build_doc
):
    """El contribuyente transmite un inmueble por 270.000 EUR habiendolo
    adquirido en su dia por 300.000 EUR. Las escrituras publicas acreditan
    una perdida de 30.000 EUR, por lo que la plusvalia municipal liquidada
    carece de hecho imponible (no existe incremento de valor)."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "valor_adquisicion_escritura": 300000,
            "valor_transmision_escritura": 270000,
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "El ayuntamiento me ha girado plusvalia municipal por la venta de mi "
        "piso, pero lo vendi por menos de lo que me costo."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R026"

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    cita_lower = arg.cita_normativa_propuesta.lower()
    assert (
        "incremento" in cita_lower
        or "inexistencia" in cita_lower
        or "no sujecion" in cita_lower
    ), (
        f"La cita semantica debe describir el concepto juridico, got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    assert arg.datos_disparo.get("perdida") == 30000, (
        f"datos_disparo.perdida inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: valores iguales (cero incremento)
# ---------------------------------------------------------------------------

def test_R026_positivo_valores_iguales_cero_incremento(
    build_exp, build_brief, build_doc
):
    """Si el valor de transmision coincide exactamente con el de adquisicion
    tampoco hay incremento de valor que pueda gravarse. La regla debe
    disparar igualmente."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "valor_adquisicion_escritura": 250000,
            "valor_transmision_escritura": 250000,
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "Vendi el piso por el mismo precio que lo compre y aun asi me cobran "
        "plusvalia."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R026"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    # Perdida == 0 porque valor_adquisicion == valor_transmision.
    assert arg.datos_disparo.get("perdida") == 0, (
        f"datos_disparo.perdida inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Negativo: incremento positivo real
# ---------------------------------------------------------------------------

def test_R026_negativo_incremento_positivo(build_exp, build_brief, build_doc):
    """Cuando las escrituras acreditan un incremento de valor real
    (transmision > adquisicion) el hecho imponible existe y la regla no
    debe disparar."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "valor_adquisicion_escritura": 200000,
            "valor_transmision_escritura": 300000,
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Vendi el piso con ganancia.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R026 no deberia disparar con incremento positivo, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: valores no disponibles en las escrituras
# ---------------------------------------------------------------------------

def test_R026_negativo_valores_no_disponibles(
    build_exp, build_brief, build_doc
):
    """Si falta alguno de los dos valores de escritura la regla no puede
    acreditar la inexistencia de incremento y, por tanto, no debe disparar
    (benefit of the doubt)."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "valor_adquisicion_escritura": 300000,
            # falta valor_transmision_escritura
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("No encuentro la escritura de venta.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R026 no deberia disparar sin ambos valores de escritura, got: "
        f"{candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: tributo distinto de PLUSVALIA
# ---------------------------------------------------------------------------

def test_R026_negativo_tributo_no_plusvalia(
    build_exp, build_brief, build_doc
):
    """La regla R026 solo aplica al tributo PLUSVALIA. Si el expediente es
    IRPF (u otro), aun con los mismos valores de escritura, no debe
    disparar."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "IRPF",
            "valor_adquisicion_escritura": 300000,
            "valor_transmision_escritura": 270000,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Liquidacion IRPF, no tiene que ver con plusvalia.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"R026 no deberia disparar sobre tributos distintos de PLUSVALIA, "
        f"got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Invariante anti-hardcode de citas
# ---------------------------------------------------------------------------

def test_R026_cita_no_es_hardcoded(build_exp, build_brief, build_doc):
    """Invariante #2 del plan: la cita normativa propuesta NO puede contener
    la referencia canonica (articulo, real decreto-ley ni sentencia del TC).
    Solo una descripcion semantica del concepto."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "tributo": "PLUSVALIA",
            "valor_adquisicion_escritura": 400000,
            "valor_transmision_escritura": 350000,
        },
    )
    exp = build_exp(
        tributo=Tributo.PLUSVALIA,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("")

    candidatos = evaluar(exp, brief)
    assert len(candidatos) == 1
    cita = candidatos[0].cita_normativa_propuesta

    # Assertions exactas pedidas por el brief.
    assert "Art. 104.5" not in cita
    assert "TRLHL" not in cita
    assert "STC 59/2017" not in cita
    assert "RDL 26/2021" not in cita
    # Debe seguir siendo una cita util (no vacia).
    assert len(cita) > 20


# ---------------------------------------------------------------------------
# Test 7 — Smoke de registro: R026 aparece en el REGISTRY y rango 0-30
# ---------------------------------------------------------------------------

def test_R026_registrada_en_registry():
    """Tras cargar solo R026 el REGISTRY debe contener exactamente esa clave,
    y el len debe estar dentro del rango [0, 30] del smoke global."""
    assert "R026" in REGISTRY, (
        f"R026 no aparece en el REGISTRY tras carga aislada. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R026"]
    assert "PLUSVALIA" in info["tributos"]
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
    assert "TEAR_AMPLIACION_POSIBLE" in info["fases"]
    assert 0 <= len(REGISTRY) <= 30, (
        f"REGISTRY fuera del rango [0, 30], got {len(REGISTRY)}"
    )
