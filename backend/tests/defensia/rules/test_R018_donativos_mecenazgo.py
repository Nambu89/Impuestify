"""Tests TDD para la regla R018 — donativos_mecenazgo (T1B-018).

La regla dispara cuando AEAT admite parcialmente o deniega una deduccion por
donativos declarada por el contribuyente, existiendo un certificado valido
emitido por una entidad beneficiaria del regimen fiscal de mecenazgo. Tambien
dispara cuando una donacion recurrente (misma entidad durante al menos tres
anos consecutivos) no ha visto aplicado el porcentaje incrementado.

Base normativa (la resuelve el RAG verificador, NO la regla):
    - Art. 68.3 LIRPF: deduccion por donativos en cuota integra estatal.
    - Ley 49/2002 (arts. 17-20): regimen fiscal de entidades sin fines
      lucrativos y de los incentivos al mecenazgo. Tras la Ley 7/2024,
      disposicion adicional, los porcentajes aplicables son 80% sobre los
      primeros 250 EUR y 40% sobre el resto, con elevacion al 45% cuando el
      contribuyente haya realizado donaciones a la misma entidad por importe
      igual o superior durante los dos anos anteriores (donacion recurrente).
    - Requisito formal: certificado emitido por la entidad donataria con el
      contenido del art. 24 Ley 49/2002.

Fases aplicables (del enum real `Fase`):
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - COMPROBACION_PROPUESTA / COMPROBACION_POST_ALEGACIONES
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA / TEAR_AMPLIACION_POSIBLE

Triggers soportados:
    - AEAT deniega el donativo teniendo certificado: la deduccion admitida
      es cero y el contribuyente declaro un donativo con certificado valido.
    - AEAT admite parcialmente el donativo con certificado: la deduccion
      admitida es estrictamente inferior a la teorica calculada a partir
      del importe declarado.
    - Donacion recurrente de 3 anos consecutivos a la misma entidad sin que
      se haya aplicado el porcentaje incrementado del 45% sobre el exceso
      de 250 EUR (la Administracion aplica 40% cuando deberia aplicar 45%).

La regla NO hardcodea la cita del articulo — solo emite una cita semantica
que el RAG verificador traducira al texto canonico correcto.
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


def _cargar_solo_R018() -> None:
    """Reset + reload aislado del modulo R018.

    El fixture `_aislar_registry` del conftest limpia el REGISTRY antes de
    cada test. Como el decorador `@regla` se ejecuta por side-effect en el
    import del modulo, debemos reimportarlo para que la regla vuelva a
    registrarse. `reset_registry()` adicional antes del reload cubre el
    caso en el que la primera importacion del modulo ya haya registrado la
    regla durante el propio setup del fixture.
    """
    reset_registry()
    module_name = "app.services.defensia_rules.reglas_irpf.R018_donativos_mecenazgo"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _registrar_r018(_aislar_registry):  # noqa: ARG001 — fuerza orden
    """Re-importa R018 tras cada `reset_registry()` del conftest."""
    _cargar_solo_R018()
    yield


# ---------------------------------------------------------------------------
# Helper local — la cita NUNCA puede hardcodear articulos canonicos
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La cita final ("Art. 68.3 LIRPF", "Ley 49/2002") la resuelve el RAG
    verificador contra el corpus normativo. Aqui solo aceptamos
    descripciones semanticas libres.
    """
    cita_upper = cita.upper()
    assert "Art. 68.3" not in cita
    assert "Ley 49/2002" not in cita
    assert "68.3 LIRPF" not in cita_upper
    assert "ART. 68" not in cita_upper
    assert "ARTICULO 68" not in cita_upper
    assert "LEY 49/2002" not in cita_upper
    assert "49/2002" not in cita


# ---------------------------------------------------------------------------
# Test 1 — Positivo: donativo 500 EUR con certificado, AEAT deniega
# ---------------------------------------------------------------------------

def test_R018_positivo_donativo_denegado_con_certificado(
    build_exp, build_brief, build_doc
):
    """Si el contribuyente declaro un donativo con certificado valido y AEAT
    lo deniega integramente (deduccion admitida = 0), R018 debe disparar.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "donativo_declarado": 500.0,
            "certificado_donacion_presentado": True,
            "deduccion_admitida": 0.0,
            "donacion_recurrente_3_anos": False,
        },
        doc_id="doc-liq-001",
        nombre_original="liquidacion_provisional_irpf.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT me ha denegado la deduccion por donativo a una ONG aunque "
        "tengo el certificado firmado por la entidad"
    )

    candidatos = evaluar(exp, brief)

    r018 = [c for c in candidatos if c.regla_id == "R018"]
    assert len(r018) == 1, (
        f"R018 deberia disparar con donativo denegado + certificado, "
        f"got {candidatos}"
    )

    arg = r018[0]
    assert isinstance(arg, ArgumentoCandidato)

    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    cita_lower = arg.cita_normativa_propuesta.lower()
    assert "donativ" in cita_lower or "mecenazgo" in cita_lower, (
        f"La cita semantica debe mencionar donativos/mecenazgo, "
        f"got: {arg.cita_normativa_propuesta!r}"
    )

    assert arg.datos_disparo.get("donativo_negado") == 500.0, (
        f"datos_disparo.donativo_negado inesperado: {arg.datos_disparo!r}"
    )
    assert arg.datos_disparo.get("tiene_certificado") is True


# ---------------------------------------------------------------------------
# Test 2 — Positivo: admision parcial del donativo
# ---------------------------------------------------------------------------

def test_R018_positivo_donativo_parcialmente_admitido(
    build_exp, build_brief, build_doc
):
    """Si la deduccion admitida es estrictamente inferior a la teorica
    calculada desde el donativo declarado, R018 debe disparar con delta.
    """
    # 400 EUR donados: teorico = 80% * 250 + 40% * 150 = 200 + 60 = 260
    # AEAT solo admite 100 -> hay admision parcial indebida.
    doc = build_doc(
        TipoDocumento.PROPUESTA_LIQUIDACION,
        datos={
            "donativo_declarado": 400.0,
            "certificado_donacion_presentado": True,
            "deduccion_calculada_teorica": 260.0,
            "deduccion_admitida": 100.0,
            "donacion_recurrente_3_anos": False,
        },
        doc_id="doc-prop-002",
        nombre_original="propuesta_liquidacion_irpf.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT solo me ha admitido 100 EUR de la deduccion por donativos y "
        "yo calculo que deberian ser mas"
    )

    candidatos = evaluar(exp, brief)

    r018 = [c for c in candidatos if c.regla_id == "R018"]
    assert len(r018) == 1, (
        f"R018 deberia disparar con admision parcial, got {candidatos}"
    )

    arg = r018[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)

    # El delta entre teorica y admitida debe viajar en datos_disparo
    delta = arg.datos_disparo.get("delta_deduccion")
    assert delta == pytest.approx(160.0), (
        f"delta_deduccion esperado 160.0, got {delta} ({arg.datos_disparo!r})"
    )
    assert arg.datos_disparo.get("tiene_certificado") is True


# ---------------------------------------------------------------------------
# Test 3 — Positivo: donacion recurrente 3 anos, 45% no aplicado
# ---------------------------------------------------------------------------

def test_R018_positivo_donacion_recurrente_sin_elevacion_45(
    build_exp, build_brief, build_doc
):
    """Si la donacion es recurrente (3 anos consecutivos a la misma entidad)
    y la Administracion aplica el 40% sobre el exceso de 250 EUR en lugar
    del 45% incrementado, R018 debe disparar.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "donativo_declarado": 1000.0,
            "certificado_donacion_presentado": True,
            "donacion_recurrente_3_anos": True,
            "porcentaje_aplicado": 0.40,
            "deduccion_admitida": 500.0,  # 80%*250 + 40%*750 = 200 + 300
        },
        doc_id="doc-liq-003",
        nombre_original="liquidacion_provisional_recurrente.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.TEAR_INTERPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "Llevo tres anos donando a la misma ONG pero AEAT me aplica 40% en "
        "lugar del 45% incrementado"
    )

    candidatos = evaluar(exp, brief)

    r018 = [c for c in candidatos if c.regla_id == "R018"]
    assert len(r018) == 1, (
        f"R018 deberia disparar con recurrencia + 40% mal aplicado, "
        f"got {candidatos}"
    )

    arg = r018[0]
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert arg.datos_disparo.get("motivo") == "recurrencia_sin_elevacion"
    assert arg.datos_disparo.get("porcentaje_aplicado") == 0.40


# ---------------------------------------------------------------------------
# Test 4 — Negativo: sin certificado no dispara (requisito formal)
# ---------------------------------------------------------------------------

def test_R018_negativo_sin_certificado(
    build_exp, build_brief, build_doc
):
    """Si el contribuyente no aporta certificado de la entidad donataria,
    la regla NO debe disparar: el certificado es requisito formal
    constitutivo de la deduccion.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "donativo_declarado": 500.0,
            "certificado_donacion_presentado": False,
            "deduccion_admitida": 0.0,
        },
        doc_id="doc-liq-004",
        nombre_original="liquidacion_sin_certificado.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("AEAT me ha denegado un donativo que hice pero no tengo certificado")

    candidatos = evaluar(exp, brief)

    r018 = [c for c in candidatos if c.regla_id == "R018"]
    assert r018 == [], (
        f"R018 NO debe disparar sin certificado (requisito formal), got {r018}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: deduccion correcta aplicada
# ---------------------------------------------------------------------------

def test_R018_negativo_deduccion_correcta(
    build_exp, build_brief, build_doc
):
    """Si la deduccion admitida coincide con la teorica y no hay indicios
    de recurrencia mal aplicada, la regla NO debe disparar.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "donativo_declarado": 400.0,
            "certificado_donacion_presentado": True,
            "deduccion_calculada_teorica": 260.0,
            "deduccion_admitida": 260.0,
            "donacion_recurrente_3_anos": False,
        },
        doc_id="doc-liq-005",
        nombre_original="liquidacion_correcta.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("AEAT me ha aceptado el donativo correctamente")

    candidatos = evaluar(exp, brief)

    r018 = [c for c in candidatos if c.regla_id == "R018"]
    assert r018 == [], (
        f"R018 NO debe disparar si la deduccion esta bien aplicada, got {r018}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode de citas canonicas
# ---------------------------------------------------------------------------

def test_R018_cita_no_hardcoded(build_exp, build_brief, build_doc):
    """La cita normativa emitida por R018 debe ser semantica, NUNCA
    hardcoded. El RAG verificador se encarga de resolver la cita canonica.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "donativo_declarado": 500.0,
            "certificado_donacion_presentado": True,
            "deduccion_admitida": 0.0,
        },
        doc_id="doc-liq-hard-001",
        nombre_original="liquidacion_provisional.pdf",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Denegaron mi donativo teniendo certificado")

    candidatos = evaluar(exp, brief)
    r018 = [c for c in candidatos if c.regla_id == "R018"]
    assert len(r018) == 1

    cita = r018[0].cita_normativa_propuesta
    assert "Art. 68.3" not in cita
    assert "Ley 49/2002" not in cita
    assert "68.3 LIRPF" not in cita.upper()


# ---------------------------------------------------------------------------
# Sanity checks: la regla esta registrada con metadata correcta
# ---------------------------------------------------------------------------

def test_R018_registrada_en_registry():
    """Tras importar el modulo, R018 debe estar en el REGISTRY con la
    metadata correcta (IRPF, fases de liquidacion + recurso).
    """
    assert "R018" in REGISTRY, (
        f"R018 no encontrada en REGISTRY. Keys actuales: {list(REGISTRY.keys())}"
    )
    info = REGISTRY["R018"]
    assert "IRPF" in info["tributos"], (
        f"R018 deberia aplicar a IRPF, tributos={info['tributos']}"
    )
    # Fases aplicables
    fases_esperadas = {
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    }
    for fase in fases_esperadas:
        assert fase in info["fases"], (
            f"R018 deberia aplicar a {fase}, fases={info['fases']}"
        )
