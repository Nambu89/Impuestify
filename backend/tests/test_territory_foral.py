import pytest
from app.territories.foral_vasco.plugin import ForalVascoTerritory
from app.territories.foral_navarra.plugin import ForalNavarraTerritory


def test_foral_vasco_covers_3_territories():
    plugin = ForalVascoTerritory()
    assert set(plugin.territories) == {"Araba", "Bizkaia", "Gipuzkoa"}
    assert plugin.regime == "foral_vasco"


def test_foral_vasco_indirect_tax():
    plugin = ForalVascoTerritory()
    assert plugin.get_indirect_tax_model() == "303"  # IVA foral + TicketBAI


def test_foral_vasco_minimos_are_quota_deductions():
    plugin = ForalVascoTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 5472.0
    assert minimos.apply_as == "quota_deduction"


def test_foral_navarra_covers_1_territory():
    plugin = ForalNavarraTerritory()
    assert plugin.territories == ["Navarra"]
    assert plugin.regime == "foral_navarra"


def test_foral_navarra_minimos():
    plugin = ForalNavarraTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 1084.0
    assert minimos.apply_as == "quota_deduction"
