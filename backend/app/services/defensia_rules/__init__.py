"""Paquete de reglas deterministas DefensIA (T1B-000).

Este paquete agrupa las reglas R001-R030 organizadas por bloque funcional:

- `reglas_procedimentales/` — R001-R010 (motivacion, caducidad, plazos, etc.)
- `reglas_irpf/`             — R011-R020 (exenciones, deducciones, minimos, etc.)
- `reglas_otros_tributos/`   — R021-R030 (IVA, ISD, ITP, Plusvalia Municipal)

Cada regla vive en un archivo `R0NN_nombre_descriptivo.py` y se auto-registra
en `defensia_rules_engine.REGISTRY` cuando su modulo se importa (side-effect
del decorador `@regla`).

Para forzar la carga de todas las reglas (por ejemplo al arrancar el motor o
al ejecutar tests) llama a `load_all()`. La funcion es idempotente siempre y
cuando el llamador haga `reset_registry()` entre invocaciones, cosa que el
conftest de tests hace via un fixture autouse.

Diseno cero-hardcoded:
- No listamos manualmente los ficheros R0NN_*.py — se auto-descubren con
  `pkgutil.iter_modules()` sobre cada subpaquete.
- Esto permite anadir/quitar reglas sin tocar este archivo, y habilita la
  paralelizacion segura del Grupo A (T1B-001..T1B-030) sin race conditions
  en el import order.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

logger = logging.getLogger(__name__)

# Subpaquetes donde viven las reglas. El orden no importa — cada modulo se
# registra a si mismo via el decorador `@regla` y el motor ya filtra por
# tributo/fase en tiempo de evaluacion.
_SUBPACKAGES: tuple[str, ...] = (
    "reglas_procedimentales",
    "reglas_irpf",
    "reglas_otros_tributos",
)


def load_all() -> None:
    """Auto-descubre e importa todos los modulos `R0NN_*.py` de los subpaquetes.

    El import triggerea el decorador ``@regla`` que registra cada regla en
    ``defensia_rules_engine.REGISTRY``. No retorna nada — el efecto observable
    es que ``len(REGISTRY)`` aumenta.

    Convencion de nombres: solo se importan modulos cuyo nombre empieza por
    una R seguida de tres digitos (`R001_*.py`, `R014_*.py`, ...). Ficheros
    auxiliares (helpers, constantes) que no sigan esta convencion NO se
    importan automaticamente, de modo que se pueden anadir utilidades locales
    sin polucionar el REGISTRY.

    Idempotencia: llamar varias veces a esta funcion sobre el mismo proceso
    Python NO duplica registros (el motor `defensia_rules_engine` mantiene un
    dict indexado por id). Si algun test quiere un estado limpio, debe llamar
    a ``reset_registry()`` antes.

    Robustez: si un subpaquete concreto no existe todavia (por ejemplo en la
    mitad de la Wave 1B cuando solo se han shippeado R001-R010), la funcion
    salta silenciosamente a los siguientes sin lanzar excepciones.
    """
    base = Path(__file__).parent

    for sub in _SUBPACKAGES:
        pkg_path = base / sub
        if not pkg_path.is_dir():
            logger.debug("defensia_rules: subpaquete %s no existe, saltando", sub)
            continue

        for mod_info in pkgutil.iter_modules([str(pkg_path)]):
            name = mod_info.name
            if not _es_modulo_de_regla(name):
                continue
            full_name = f"app.services.defensia_rules.{sub}.{name}"
            try:
                importlib.import_module(full_name)
            except Exception as exc:  # pragma: no cover — defensa en profundidad
                logger.error(
                    "defensia_rules: fallo al importar %s: %s", full_name, exc,
                )
                raise


def _es_modulo_de_regla(nombre: str) -> bool:
    """Devuelve True si el nombre del modulo sigue la convencion `R0NN_...`.

    Ejemplos validos:
        - "R001_motivacion"           -> True
        - "R014_deduccion_eficiencia" -> True
        - "R030_iva_recargo"          -> True

    Ejemplos invalidos (no se importan):
        - "helpers"           -> False
        - "constantes"        -> False
        - "Rxxx_foo"          -> False
        - "R1_foo"            -> False (solo 1 digito)
        - "R9999_foo"         -> False (mas de 3 digitos, con la convencion actual)
    """
    if len(nombre) < 5:  # "R" + 3 digitos + "_" = 5 chars minimo
        return False
    if nombre[0] != "R":
        return False
    if not nombre[1:4].isdigit():
        return False
    if nombre[4] != "_":
        return False
    return True


__all__ = ["load_all"]
