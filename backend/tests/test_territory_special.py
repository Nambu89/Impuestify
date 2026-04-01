import pytest
from app.territories.canarias.plugin import CanariasTerritory
from app.territories.ceuta_melilla.plugin import CeutaMelillaTerritory


def test_canarias_territory():
    plugin = CanariasTerritory()
    assert plugin.territories == ["Canarias"]
    assert plugin.regime == "canarias"
    assert plugin.get_indirect_tax_model() == "420"  # IGIC


def test_canarias_minimos_are_base_reduction():
    plugin = CanariasTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.apply_as == "base_reduction"


def test_ceuta_melilla_territory():
    plugin = CeutaMelillaTerritory()
    assert set(plugin.territories) == {"Ceuta", "Melilla"}
    assert plugin.regime == "ceuta_melilla"
    assert plugin.get_indirect_tax_model() == "ipsi"


def test_ceuta_melilla_minimos_are_base_reduction():
    plugin = CeutaMelillaTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.apply_as == "base_reduction"


def test_ceuta_melilla_rag_filters_include_special_flag():
    plugin = CeutaMelillaTerritory()
    filters = plugin.get_rag_filters("Ceuta")
    assert filters["territory"] == "Ceuta"
    assert filters.get("deduccion_60") is True
