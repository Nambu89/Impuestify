"""
Territory Plugin System for Impuestify.

Each fiscal regime (comun, foral_vasco, foral_navarra, canarias, ceuta_melilla)
is encapsulated in a plugin that implements TerritoryPlugin.
"""
from app.territories.base import TerritoryPlugin
from app.territories.registry import get_territory, register_territory, list_territories

__all__ = ["TerritoryPlugin", "get_territory", "register_territory", "list_territories"]
