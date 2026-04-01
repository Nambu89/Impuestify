import pytest
from app.territories.base import TerritoryPlugin


def test_territory_plugin_is_abstract():
    """TerritoryPlugin cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TerritoryPlugin()


def test_territory_plugin_has_required_methods():
    """TerritoryPlugin defines all required abstract methods."""
    abstract_methods = TerritoryPlugin.__abstractmethods__
    assert "get_irpf_scales" in abstract_methods
    assert "simulate_irpf" in abstract_methods
    assert "get_deductions" in abstract_methods
    assert "get_indirect_tax_model" in abstract_methods
    assert "get_minimos_personales" in abstract_methods
