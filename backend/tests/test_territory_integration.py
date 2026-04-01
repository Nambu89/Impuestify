import pytest
from app.territories import get_territory, list_territories
from app.territories.registry import _registry


def setup_function():
    """Ensure registry is loaded before each test."""
    _registry.clear()
    from app.territories.startup import register_all_territories
    register_all_territories()


def test_all_21_territories_registered():
    territories = list_territories()
    assert len(territories) == 21


def test_madrid_is_comun():
    plugin = get_territory("Madrid")
    assert plugin.regime == "comun"


def test_araba_is_foral_vasco():
    plugin = get_territory("Araba")
    assert plugin.regime == "foral_vasco"


def test_navarra_is_foral_navarra():
    plugin = get_territory("Navarra")
    assert plugin.regime == "foral_navarra"


def test_canarias_is_canarias():
    plugin = get_territory("Canarias")
    assert plugin.regime == "canarias"


def test_ceuta_is_ceuta_melilla():
    plugin = get_territory("Ceuta")
    assert plugin.regime == "ceuta_melilla"


def test_melilla_is_ceuta_melilla():
    plugin = get_territory("Melilla")
    assert plugin.regime == "ceuta_melilla"
