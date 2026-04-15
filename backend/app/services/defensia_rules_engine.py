"""Motor de reglas deterministas de DefensIA.

Cada regla es una función Python registrada vía el decorador ``@regla`` con
metadata (tributos aplicables, fases aplicables, descripción). El motor ejecuta
todas las reglas aplicables al expediente y devuelve la lista de argumentos
candidatos.

Cero LLM en esta capa — Python puro y determinista. La verificación de citas
normativas se hace después en ``defensia_rag_verifier.py`` (Parte 2).
"""
from __future__ import annotations
import logging
from enum import Enum
from typing import Callable, Iterable, Optional, Union

from app.models.defensia import (
    ExpedienteEstructurado, Brief, ArgumentoCandidato, Tributo, Fase,
)

logger = logging.getLogger(__name__)

ReglaFunc = Callable[[ExpedienteEstructurado, Brief], Optional[ArgumentoCandidato]]

REGISTRY: dict[str, dict] = {}

# Type alias: tributos/fases admiten enum o string en el decorador
TributoLike = Union[Tributo, str]
FaseLike = Union[Fase, str]


def _normalize(values: Iterable[Union[Enum, str]]) -> set[str]:
    """Normaliza una lista de enums o strings a un conjunto de strings.

    Cualquier elemento con atributo ``.value`` se reemplaza por ``.value``
    (útil para aceptar ``Tributo.IRPF`` o ``Fase.XXX``). El resto se
    convierte a ``str()``. Así el decorador es agnóstico a si la regla
    pasa enums o strings, y la comparación con
    ``expediente.tributo.value`` / ``expediente.fase_detectada.value``
    siempre casa correctamente.
    """
    result: set[str] = set()
    for v in values:
        if hasattr(v, "value"):
            result.add(v.value)
        else:
            result.add(str(v))
    return result


def regla(
    *,
    id: str,
    tributos: list[TributoLike],
    fases: list[FaseLike],
    descripcion: str,
):
    """Decorador que registra una regla en el registry global.

    ``tributos`` y ``fases`` admiten tanto enums (``Tributo.IRPF``,
    ``Fase.COMPROBACION_PROPUESTA``) como strings (``"IRPF"``). El decorador
    normaliza internamente a strings (``.value`` del enum) para que la
    comparación con ``expediente.tributo.value`` en ``evaluar()``
    siempre funcione.

    Ejemplo::

        @regla(
            id="R001_motivacion_insuficiente",
            tributos=[Tributo.IRPF, Tributo.IVA],      # o ["IRPF", "IVA"]
            fases=[Fase.LIQUIDACION_FIRME_PLAZO_RECURSO],
            descripcion="Falta motivación específica de gastos no admitidos",
        )
        def r001(expediente, brief):
            ...
            return ArgumentoCandidato(...)  # o None si no dispara
    """
    def wrapper(fn: ReglaFunc) -> ReglaFunc:
        if id in REGISTRY:
            raise ValueError(f"Regla duplicada en el registry: {id}")
        REGISTRY[id] = {
            "id": id,
            "tributos": _normalize(tributos),
            "fases": _normalize(fases),
            "descripcion": descripcion,
            "fn": fn,
        }
        return fn
    return wrapper


def reset_registry() -> None:
    """Helper para tests — limpia el registry entre ejecuciones."""
    REGISTRY.clear()


def evaluar(
    expediente: ExpedienteEstructurado, brief: Brief
) -> list[ArgumentoCandidato]:
    """Ejecuta todas las reglas aplicables y devuelve los candidatos.

    Filtra por tributo y fase antes de ejecutar la función de la regla.
    Las reglas que devuelven ``None`` se ignoran. Las reglas que lanzan
    una excepción se capturan y loggean pero no tumban el pipeline —
    una regla defectuosa no debe poder impedir que el resto se ejecute.
    """
    candidatos: list[ArgumentoCandidato] = []

    tributo_str = (
        expediente.tributo.value
        if hasattr(expediente.tributo, "value")
        else str(expediente.tributo)
    )
    fase_str = (
        expediente.fase_detectada.value
        if hasattr(expediente.fase_detectada, "value")
        else str(expediente.fase_detectada)
    )

    for info in REGISTRY.values():
        if tributo_str not in info["tributos"]:
            continue
        if fase_str not in info["fases"]:
            continue
        try:
            resultado = info["fn"](expediente, brief)
        except Exception as exc:
            logger.warning(
                "Regla %s lanzó excepción durante evaluación: %s",
                info["id"], exc,
            )
            continue
        if resultado is not None:
            candidatos.append(resultado)

    return candidatos
