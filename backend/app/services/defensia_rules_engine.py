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
from typing import Callable, Optional

from app.models.defensia import (
    ExpedienteEstructurado, Brief, ArgumentoCandidato,
)

logger = logging.getLogger(__name__)

ReglaFunc = Callable[[ExpedienteEstructurado, Brief], Optional[ArgumentoCandidato]]

REGISTRY: dict[str, dict] = {}


def regla(
    *,
    id: str,
    tributos: list[str],
    fases: list[str],
    descripcion: str,
):
    """Decorador que registra una regla en el registry global.

    Ejemplo::

        @regla(
            id="R001_motivacion_insuficiente",
            tributos=["IRPF", "IVA"],
            fases=["LIQUIDACION_FIRME_PLAZO_RECURSO"],
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
            "tributos": set(tributos),
            "fases": set(fases),
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
