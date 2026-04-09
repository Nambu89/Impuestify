import pytest
from app.territories.comun.plugin import CommonTerritory


def test_common_territory_covers_15_ccaa():
    plugin = CommonTerritory()
    assert len(plugin.territories) == 15
    assert "Madrid" in plugin.territories
    assert "Andalucía" in plugin.territories
    assert "Cataluña" in plugin.territories


def test_common_territory_regime():
    plugin = CommonTerritory()
    assert plugin.regime == "comun"


def test_common_territory_indirect_tax():
    plugin = CommonTerritory()
    assert plugin.get_indirect_tax_model() == "303"


def test_common_territory_minimos():
    plugin = CommonTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 5550.0
    assert minimos.apply_as == "base_reduction"


def test_common_territory_rag_filters():
    plugin = CommonTerritory()
    filters = plugin.get_rag_filters("Madrid")
    assert filters["territory"] == "Madrid"
    assert filters["regime"] == "comun"
