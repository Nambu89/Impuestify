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
    if ccaa in _registry:
        return _registry[ccaa]
    # Normalize via ccaa_constants before giving up
    from app.utils.ccaa_constants import normalize_ccaa
    canonical = normalize_ccaa(ccaa)
    if canonical in _registry:
        return _registry[canonical]
    raise KeyError(f"No territory plugin registered for '{ccaa}'")


def list_territories() -> List[str]:
    """Return all registered territory names."""
    return list(_registry.keys())
