import pytest
from app.territories.registry import get_territory, register_territory, list_territories, _registry
from app.territories.base import TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig


class FakePlugin(TerritoryPlugin):
    territories = ["FakeLand"]
    regime = "fake"

    async def get_irpf_scales(self, year):
        return []

    async def simulate_irpf(self, profile, db):
        return SimulationResult()

    async def get_deductions(self, ccaa, year, db):
        return []

    def get_indirect_tax_model(self):
        return "303"

    def get_minimos_personales(self):
        return MinimosConfig()


def test_register_and_get_territory():
    _registry.clear()
    plugin = FakePlugin()
    register_territory(plugin)
    result = get_territory("FakeLand")
    assert result is plugin


def test_get_territory_unknown_raises():
    _registry.clear()
    with pytest.raises(KeyError, match="No territory plugin"):
        get_territory("Atlantis")


def test_list_territories():
    _registry.clear()
    plugin = FakePlugin()
    register_territory(plugin)
    territories = list_territories()
    assert "FakeLand" in territories
