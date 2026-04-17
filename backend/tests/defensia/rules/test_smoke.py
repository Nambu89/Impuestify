"""Smoke test del paquete `defensia_rules` (T1B-000).

Este test NO valida ninguna regla concreta — solo verifica que el scaffolding
de auto-descubrimiento funciona:

1. `defensia_rules.load_all()` existe y es invocable.
2. Tras cargar, el REGISTRY queda en el rango `[0, 30]` — rango, NO exacto.
   La asercion exacta `== 30` pertenece a T1B-030, no a este smoke test.
   Permitir el rango desbloquea la paralelizacion segura del Grupo A (un
   agente puede mergear T1B-005 mientras otro todavia no ha escrito T1B-008
   sin que el smoke test rompa).
3. No hay IDs duplicados en el REGISTRY (si dos reglas colisionan, el motor
   `defensia_rules_engine` ya lanza ValueError, pero replicamos la asercion
   aqui para tener un mensaje claro al nivel del smoke test).
4. `load_all()` es idempotente: invocarlo dos veces tras un `reset_registry()`
   intermedio produce el mismo numero de reglas.
"""
from __future__ import annotations

from app.services import defensia_rules
from app.services.defensia_rules_engine import REGISTRY, reset_registry


def test_smoke_registry_loadable():
    """load_all() se puede invocar sin excepciones y deja el REGISTRY en rango."""
    reset_registry()
    defensia_rules.load_all()

    assert 0 <= len(REGISTRY) <= 30, (
        f"REGISTRY debe estar en rango [0, 30], got {len(REGISTRY)}. "
        "Tests de reglas individuales aumentan el count; el upper bound 30 "
        "se valida exacto en T1B-030."
    )


def test_smoke_no_duplicate_ids():
    """Ningun ID de regla puede estar duplicado en el REGISTRY."""
    reset_registry()
    defensia_rules.load_all()

    ids = [info["id"] for info in REGISTRY.values()]
    assert len(ids) == len(set(ids)), f"IDs duplicados detectados: {ids}"


def test_smoke_load_all_es_idempotente():
    """Llamar a load_all() dos veces (con reset intermedio) da el mismo count.

    Esto protege frente a imports con side-effects que pudieran duplicar
    registros si el modulo se reimporta.
    """
    reset_registry()
    defensia_rules.load_all()
    primera_cuenta = len(REGISTRY)

    reset_registry()
    defensia_rules.load_all()
    segunda_cuenta = len(REGISTRY)

    assert primera_cuenta == segunda_cuenta, (
        f"load_all() no es idempotente: {primera_cuenta} vs {segunda_cuenta}"
    )


def test_smoke_paquete_importable():
    """El paquete `app.services.defensia_rules` debe importarse sin errores."""
    # El import en si mismo ya se ha ejecutado al cargar este modulo; solo
    # comprobamos que el atributo `load_all` existe y es callable.
    assert hasattr(defensia_rules, "load_all"), (
        "defensia_rules debe exponer una funcion `load_all()` auto-descubridora"
    )
    assert callable(defensia_rules.load_all)
