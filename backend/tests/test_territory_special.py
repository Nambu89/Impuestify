import pytest
from app.territories.canarias.plugin import CanariasTerritory
from app.territories.ceuta_melilla.plugin import CeutaMelillaTerritory


# --- Canarias ---

def test_canarias_territory():
    plugin = CanariasTerritory()
    assert plugin.territories == ["Canarias"]
    assert plugin.regime == "canarias"
    assert plugin.get_indirect_tax_model() == "420"  # IGIC


def test_canarias_minimos_are_base_reduction():
    plugin = CanariasTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.apply_as == "base_reduction"


def test_canarias_rag_filters_modelo_349_not_applicable():
    """Modelo 349 does not apply in Canarias (not EU VAT territory)."""
    plugin = CanariasTerritory()
    filters = plugin.get_rag_filters("Canarias")
    assert filters.get("modelo_349") is False
    assert filters.get("igic") is True


def test_canarias_uses_default_renta_model():
    """Canarias uses common Modelo 100."""
    plugin = CanariasTerritory()
    assert plugin.get_renta_model() == "100"


# --- Ceuta / Melilla ---

def test_ceuta_melilla_territory():
    plugin = CeutaMelillaTerritory()
    assert set(plugin.territories) == {"Ceuta", "Melilla"}
    assert plugin.regime == "ceuta_melilla"


def test_ceuta_indirect_tax_modelo_001():
    """Ceuta uses Modelo 001 for IPSI."""
    plugin = CeutaMelillaTerritory()
    assert plugin.get_indirect_tax_model(ccaa="Ceuta") == "001"


def test_melilla_indirect_tax_modelo_420():
    """Melilla uses Modelo 420 for IPSI."""
    plugin = CeutaMelillaTerritory()
    assert plugin.get_indirect_tax_model(ccaa="Melilla") == "420"


def test_ceuta_melilla_default_is_melilla():
    """Without ccaa param, defaults to Melilla's 420."""
    plugin = CeutaMelillaTerritory()
    assert plugin.get_indirect_tax_model() == "420"


def test_ceuta_ipsi_rate_3_percent():
    plugin = CeutaMelillaTerritory()
    assert plugin.get_ipsi_general_rate("Ceuta") == 0.03


def test_melilla_ipsi_rate_4_percent():
    plugin = CeutaMelillaTerritory()
    assert plugin.get_ipsi_general_rate("Melilla") == 0.04


def test_ceuta_melilla_minimos_are_base_reduction():
    plugin = CeutaMelillaTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.apply_as == "base_reduction"


def test_ceuta_melilla_rag_filters_include_special_flag():
    plugin = CeutaMelillaTerritory()
    filters = plugin.get_rag_filters("Ceuta")
    assert filters["territory"] == "Ceuta"
    assert filters.get("deduccion_60") is True
