"""Territory plugin registry -- maps CCAA names to their TerritoryPlugin."""
from typing import Dict, List
from app.territories.base import TerritoryPlugin

_registry: Dict[str, TerritoryPlugin] = {}


def register_territory(plugin: TerritoryPlugin) -> None:
    """Register a plugin for all its territories."""
    for territory in plugin.territories:
        _registry[territory] = plugin


def get_territory(ccaa: str) -> TerritoryPlugin:
    """Get the plugin for a CCAA. Raises KeyError if not found."""
    if ccaa not in _registry:
        raise KeyError(f"No territory plugin registered for '{ccaa}'")
    return _registry[ccaa]


def list_territories() -> List[str]:
    """Return all registered territory names."""
    return list(_registry.keys())
