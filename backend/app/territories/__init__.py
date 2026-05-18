"""
Territory Plugin System for Impuestify.

Each fiscal regime (comun, foral_vasco, foral_navarra, canarias, ceuta_melilla)
is encapsulated in a plugin that implements TerritoryPlugin.
"""

from app.territories.base import (
    DEADLINES_2026,
    Deadline,
    ModelObligation,
    TerritoryPlugin,
    _trimestral_deadlines,
)
from app.territories.registry import get_territory, list_territories, register_territory

__all__ = [
    "TerritoryPlugin",
    "ModelObligation",
    "Deadline",
    "DEADLINES_2026",
    "_trimestral_deadlines",
    "get_territory",
    "register_territory",
    "list_territories",
]
