"""Tests de la regla R014 — deduccion_eficiencia_energetica (T1B-014).

La regla dispara cuando AEAT deniega la deduccion por obras de mejora de
eficiencia energetica en vivienda (DA 50.ª LIRPF, introducida por RDL 19/2021
y prorrogada hasta 31-12-2026) habiendo el contribuyente acreditado la obra
con certificado energetico valido dentro del periodo de vigencia.

Tres tipos de deduccion cubiertos por la base normativa:
    - 20 %: reduccion de al menos 7 % de la demanda de calefaccion/refrigeracion.
    - 40 %: reduccion de al menos 30 % del consumo de energia primaria no
      renovable, o mejora a clase energetica A o B.
    - 60 %: obras en edificios residenciales completos.

El codigo de la regla NO hardcodea la cita normativa canonica ("DA 50.ª LIRPF",
"Disposicion Adicional Quincuagesima", "RDL 19/2021", "art. 68.7") — devuelve
una descripcion semantica libre; la cita canonica la resuelve el RAG verificador
(invariante #2 del plan Parte 2, anti-alucinacion).

Fases aplicables (segun enum real `Fase` en `app/models/defensia.py`):
    - LIQUIDACION_FIRME_PLAZO_RECURSO
    - COMPROBACION_PROPUESTA
    - COMPROBACION_POST_ALEGACIONES
    - REPOSICION_INTERPUESTA
    - TEAR_INTERPUESTA
    - TEAR_AMPLIACION_POSIBLE

Triggers soportados:
    - Obra con certificado clase A/B post-obra + deduccion denegada (tipo 40 %).
    - Reduccion >= 30 % consumo energia primaria + denegada (tipo 40 %).
    - Reduccion >= 7 % demanda calefaccion/refrigeracion + denegada (tipo 20 %).

Descartes (NO dispara):
    - Sin certificado energetico presentado (requisito formal legitimo).
    - Deduccion ya admitida parcialmente (AEAT no la denego).
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
# Aislamiento — carga explicita y exclusiva de R014
# ---------------------------------------------------------------------------
#
# El conftest autouse ya ejecuta `reset_registry()` antes de cada test. Sin
# embargo, como `importlib.import_module` devuelve el modulo cacheado y NO
# re-ejecuta el decorador `@regla`, necesitamos `importlib.reload()` para
# forzar la re-registracion de R014 en el REGISTRY limpio.
#
# Este patron de aislamiento garantiza que el test solo ve R014, sin
# contaminacion de otras reglas del Grupo A (importante para paralelizacion).

def _cargar_solo_R014() -> None:
    """Resetea el registry y carga exclusivamente el modulo R014."""
    reset_registry()
    module_name = "app.services.defensia_rules.reglas_irpf.R014_eficiencia_energetica"
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])
    else:
        importlib.import_module(module_name)


@pytest.fixture(autouse=True)
def _recargar_R014():
    """Recarga el modulo R014 tras el reset del registry del conftest global."""
    _cargar_solo_R014()
    yield


# ---------------------------------------------------------------------------
# Helpers locales
# ---------------------------------------------------------------------------

def _assert_cita_no_hardcoded(cita: str) -> None:
    """Invariante #2: la regla NUNCA puede hardcodear la cita canonica.

    La base real de las deducciones por eficiencia energetica es la
    Disposicion Adicional Quincuagesima (DA 50.ª) LIRPF, introducida por el
    RDL 19/2021 y prorrogada hasta 31-12-2026. El spec original citaba
    (erroneamente) "art. 68.7 LIRPF" — tambien vetado aqui. La cita canonica
    debe resolverla el RAG verificador contra el corpus normativo.
    """
    assert "DA 50" not in cita, (
        f"Cita hardcoded detectada: 'DA 50' en '{cita}'"
    )
    assert "Disposicion Adicional Quincuagesima" not in cita, (
        f"Cita hardcoded detectada: 'Disposicion Adicional Quincuagesima' en '{cita}'"
    )
    assert "RDL 19/2021" not in cita, (
        f"Cita hardcoded detectada: 'RDL 19/2021' en '{cita}'"
    )
    assert "art. 68.7" not in cita.lower(), (
        f"Cita hardcoded detectada: 'art. 68.7' en '{cita}'"
    )


def _datos_obra_clase_B_denegada() -> dict:
    """Datos tipo: obra con certificado clase B post-obra, deduccion denegada."""
    return {
        "deduccion_eficiencia_declarada": True,
        "certificado_energetico_presentado": True,
        "clase_energetica_post_obra": "B",
        "deduccion_admitida": 0,
    }


# ---------------------------------------------------------------------------
# Test 1 — Positivo: obra con certificado clase B denegada
# ---------------------------------------------------------------------------

def test_R014_positivo_obra_clase_B_denegada(build_exp, build_brief, build_doc):
    """Obra con certificado clase B post-obra y deduccion denegada → dispara.

    La clase B es una de las condiciones que habilita la deduccion del 40 %.
    """
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos=_datos_obra_clase_B_denegada(),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief(
        "AEAT me deniega la deduccion por eficiencia energetica pese al "
        "certificado energetico clase B."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert isinstance(arg, ArgumentoCandidato)
    assert arg.regla_id == "R014"

    # Cita semantica, no hardcoded.
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert "eficiencia energetica" in arg.cita_normativa_propuesta.lower(), (
        f"La cita semantica debe mencionar 'eficiencia energetica', got: "
        f"{arg.cita_normativa_propuesta!r}"
    )

    # datos_disparo debe exponer tipo_deduccion y clase_energetica.
    assert arg.datos_disparo.get("tipo_deduccion") == "40_por_ciento", (
        f"datos_disparo.tipo_deduccion inesperado: {arg.datos_disparo!r}"
    )
    assert arg.datos_disparo.get("clase_energetica") == "B", (
        f"datos_disparo.clase_energetica inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Positivo: reduccion >= 30 % consumo energia primaria
# ---------------------------------------------------------------------------

def test_R014_positivo_reduccion_consumo_primaria(build_exp, build_brief, build_doc):
    """Reduccion del 35 % del consumo de energia primaria → dispara (40 %)."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deduccion_eficiencia_declarada": True,
            "certificado_energetico_presentado": True,
            "reduccion_consumo_energia": 0.35,
            "deduccion_admitida": 0,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.COMPROBACION_PROPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "La obra redujo un 35 % el consumo de energia primaria no renovable."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R014"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert arg.datos_disparo.get("tipo_deduccion") == "40_por_ciento", (
        f"datos_disparo.tipo_deduccion inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Positivo: reduccion >= 7 % demanda calefaccion/refrigeracion
# ---------------------------------------------------------------------------

def test_R014_positivo_reduccion_demanda(build_exp, build_brief, build_doc):
    """Reduccion del 10 % de la demanda → dispara (tipo 20 %)."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deduccion_eficiencia_declarada": True,
            "certificado_energetico_presentado": True,
            "reduccion_demanda": 0.10,
            "deduccion_admitida": 0,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.TEAR_INTERPUESTA,
        docs=[doc],
    )
    brief = build_brief(
        "La obra redujo un 10 % la demanda de calefaccion y refrigeracion."
    )

    candidatos = evaluar(exp, brief)

    assert len(candidatos) == 1, (
        f"Se esperaba 1 argumento candidato, got {len(candidatos)}: {candidatos}"
    )
    arg = candidatos[0]
    assert arg.regla_id == "R014"
    _assert_cita_no_hardcoded(arg.cita_normativa_propuesta)
    assert arg.datos_disparo.get("tipo_deduccion") == "20_por_ciento", (
        f"datos_disparo.tipo_deduccion inesperado: {arg.datos_disparo!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — Negativo: sin certificado energetico
# ---------------------------------------------------------------------------

def test_R014_negativo_sin_certificado(build_exp, build_brief, build_doc):
    """Si el contribuyente no presento certificado energetico, la denegacion
    es un requisito formal legitimo y la regla NO debe disparar."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deduccion_eficiencia_declarada": True,
            "certificado_energetico_presentado": False,
            "clase_energetica_post_obra": "B",
            "deduccion_admitida": 0,
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("AEAT me deniega por falta de certificado energetico.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"La regla NO deberia disparar sin certificado energetico, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 5 — Negativo: deduccion ya admitida
# ---------------------------------------------------------------------------

def test_R014_negativo_deduccion_admitida(build_exp, build_brief, build_doc):
    """Si AEAT ya admitio (total o parcialmente) la deduccion, no hay
    denegacion que impugnar y la regla NO debe disparar."""
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={
            "deduccion_eficiencia_declarada": True,
            "certificado_energetico_presentado": True,
            "clase_energetica_post_obra": "B",
            "deduccion_admitida": 500.0,  # AEAT admitio parte de la deduccion
        },
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Revisando la liquidacion de eficiencia energetica.")

    candidatos = evaluar(exp, brief)

    assert candidatos == [], (
        f"La regla NO deberia disparar con deduccion admitida, got: {candidatos}"
    )


# ---------------------------------------------------------------------------
# Test 6 — Anti-hardcode + smoke de registro (invariante #2 + rango REGISTRY)
# ---------------------------------------------------------------------------

def test_R014_anti_hardcode_y_registry(build_exp, build_brief, build_doc):
    """Combina dos acceptance criteria:

    1. La cita_normativa_propuesta NO puede contener la referencia canonica.
       El spec original citaba erroneamente "art. 68.7 LIRPF" — la base real
       es la Disposicion Adicional Quincuagesima (DA 50.ª) LIRPF introducida
       por el RDL 19/2021. Ninguna de esas formas puede aparecer en la cita
       generada por la regla: la resolucion a texto canonico es
       responsabilidad del RAG verificador.

    2. R014 debe estar registrada en el REGISTRY tras el reload y su id debe
       estar dentro del rango numerico del Grupo IRPF [0, 30].
    """
    # --- Parte 1: anti-hardcode ---
    doc = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos=_datos_obra_clase_B_denegada(),
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc],
    )
    brief = build_brief("Prueba anti-hardcode + registry.")

    candidatos = evaluar(exp, brief)
    assert len(candidatos) == 1
    cita = candidatos[0].cita_normativa_propuesta

    assert "DA 50" not in cita
    assert "Disposicion Adicional Quincuagesima" not in cita
    assert "RDL 19/2021" not in cita
    assert "art. 68.7" not in cita.lower()

    # --- Parte 2: registro y rango [0, 30] ---
    assert "R014" in REGISTRY, (
        f"R014 no aparece en el REGISTRY tras reload. "
        f"Claves actuales: {sorted(REGISTRY.keys())}"
    )
    info = REGISTRY["R014"]
    assert "IRPF" in info["tributos"]
    num = int("R014"[1:])
    assert 0 <= num <= 30, f"R014 fuera del rango [0, 30]: {num}"
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in info["fases"]
    assert "REPOSICION_INTERPUESTA" in info["fases"]
    assert "TEAR_INTERPUESTA" in info["fases"]
