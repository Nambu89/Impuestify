"""El leadbot no puede aparecer en un despliegue que no lo pida.

El captador de leads es un módulo opcional de marca blanca. Vive en el repo pero
debe estar APAGADO salvo que se ponga ``LEADBOT_ENABLED=true`` explícitamente.
Estos tests son la red que impide que un endpoint público de captación de datos
personales acabe montado por accidente en Impuestify.
"""

from __future__ import annotations

import pytest

import app.main  # noqa: F401 — importado por efecto: monta las rutas
from app.config import Settings, settings
from app.main import app

# Prefijos que el leadbot expone cuando está encendido.
LEADBOT_PREFIXES = ("/api/lead-chat", "/api/leads")


def _mounted_paths() -> list[str]:
    return [getattr(r, "path", "") for r in app.routes]


# ---------------------------------------------------------------------------
# Apagado por defecto
# ---------------------------------------------------------------------------


def test_leadbot_apagado_por_defecto():
    """Un despliegue que no configura nada NO debe tener el leadbot.

    Si este test falla, cualquier deploy nuevo expondría endpoints públicos de
    captación de leads sin que nadie lo haya pedido.
    """
    assert Settings().LEADBOT_ENABLED is False


def test_rutas_del_leadbot_no_montadas_en_esta_app():
    """Con la bandera apagada, la app no tiene ninguna ruta del leadbot."""
    if settings.LEADBOT_ENABLED:
        pytest.skip("LEADBOT_ENABLED=true en este entorno; ver el test complementario")

    coladas = [p for p in _mounted_paths() if p.startswith(LEADBOT_PREFIXES)]
    assert not coladas, f"rutas del leadbot montadas con la bandera apagada: {coladas}"


def test_el_core_no_importa_el_leadbot_de_forma_incondicional():
    """`app.leadbot` no debe cargarse solo por arrancar la app.

    La defensa en profundidad es que el import viva DENTRO del `if`: si alguien
    lo sube al bloque de imports de `main.py`, el módulo se carga siempre y esta
    prueba deja de tener sentido aunque las rutas sigan sin montarse.
    """
    import sys

    if settings.LEADBOT_ENABLED:
        pytest.skip("LEADBOT_ENABLED=true en este entorno")

    assert "app.leadbot.router" not in sys.modules, (
        "app.leadbot.router se ha importado con LEADBOT_ENABLED=false — "
        "el import debe estar dentro del bloque condicional de main.py"
    )


# ---------------------------------------------------------------------------
# Contrato de lo que aparece al encenderlo
# ---------------------------------------------------------------------------


def test_el_router_expone_los_prefijos_esperados():
    """Al encender la bandera, estas y solo estas familias de rutas aparecen.

    Se importa el módulo directamente en vez de reimportar toda la app: basta
    para fijar el contrato de qué se expondría.
    """
    from app.leadbot.router import chat_router, leads_router

    rutas = [r.path for r in chat_router.routes] + [r.path for r in leads_router.routes]
    assert rutas, "el router del leadbot no declara ninguna ruta"

    fuera = [p for p in rutas if not p.startswith(LEADBOT_PREFIXES)]
    assert not fuera, (
        f"el leadbot declara rutas fuera de sus prefijos {LEADBOT_PREFIXES}: {fuera}. "
        "Todo endpoint suyo debe vivir bajo su propio espacio de nombres."
    )


def test_las_tablas_del_leadbot_llevan_prefijo_propio():
    """El esquema del leadbot no puede colisionar con el del producto."""
    import inspect

    from app.leadbot import schema

    fuente = inspect.getsource(schema)
    creaciones = [
        linea.strip()
        for linea in fuente.splitlines()
        if "CREATE TABLE" in linea.upper() or "CREATE INDEX" in linea.upper()
    ]
    assert creaciones, "no se han encontrado sentencias CREATE en el esquema del leadbot"

    sin_prefijo = [c for c in creaciones if "leadbot_" not in c]
    assert not sin_prefijo, f"objetos de BD sin el prefijo leadbot_: {sin_prefijo}"
