import pytest
from app.territories.foral_vasco.plugin import ForalVascoTerritory
from app.territories.foral_navarra.plugin import ForalNavarraTerritory


# --- Foral Vasco ---

def test_foral_vasco_covers_3_territories():
    plugin = ForalVascoTerritory()
    assert set(plugin.territories) == {"Araba", "Bizkaia", "Gipuzkoa"}
    assert plugin.regime == "foral_vasco"


def test_foral_vasco_indirect_tax_bizkaia_araba():
    plugin = ForalVascoTerritory()
    assert plugin.get_indirect_tax_model() == "303"
    assert plugin.get_indirect_tax_model(ccaa="Bizkaia") == "303"
    assert plugin.get_indirect_tax_model(ccaa="Araba") == "303"


def test_foral_vasco_indirect_tax_gipuzkoa():
    """Gipuzkoa uses Modelo 300 (not 303)."""
    plugin = ForalVascoTerritory()
    assert plugin.get_indirect_tax_model(ccaa="Gipuzkoa") == "300"


def test_foral_vasco_renta_model_gipuzkoa():
    """Gipuzkoa uses Modelo 109 for IRPF."""
    plugin = ForalVascoTerritory()
    assert plugin.get_renta_model(ccaa="Gipuzkoa") == "109"


def test_foral_vasco_renta_model_bizkaia_araba():
    """Bizkaia and Araba use Modelo 100."""
    plugin = ForalVascoTerritory()
    assert plugin.get_renta_model() == "100"
    assert plugin.get_renta_model(ccaa="Bizkaia") == "100"
    assert plugin.get_renta_model(ccaa="Araba") == "100"


def test_foral_vasco_retenciones_modelo_110():
    """All Basque territories use Modelo 110 (not 111)."""
    plugin = ForalVascoTerritory()
    assert plugin.get_retenciones_model() == "110"


def test_foral_vasco_minimos_are_quota_deductions():
    plugin = ForalVascoTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 5472.0
    assert minimos.apply_as == "quota_deduction"


# --- Foral Navarra ---

def test_foral_navarra_covers_1_territory():
    plugin = ForalNavarraTerritory()
    assert plugin.territories == ["Navarra"]
    assert plugin.regime == "foral_navarra"


def test_foral_navarra_indirect_tax_f69():
    """Navarra uses Modelo F69 for IVA (not 303)."""
    plugin = ForalNavarraTerritory()
    assert plugin.get_indirect_tax_model() == "F69"


def test_foral_navarra_renta_model_f90():
    """Navarra uses Modelo F-90 for IRPF (not 100)."""
    plugin = ForalNavarraTerritory()
    assert plugin.get_renta_model() == "F-90"


def test_foral_navarra_is_model_s90():
    """Navarra uses Modelo S-90 for IS (not 200)."""
    plugin = ForalNavarraTerritory()
    assert plugin.get_is_model() == "S-90"


def test_foral_navarra_retenciones_111():
    """Navarra uses Modelo 111 for retenciones (same as AEAT)."""
    plugin = ForalNavarraTerritory()
    assert plugin.get_retenciones_model() == "111"


def test_foral_navarra_minimos():
    plugin = ForalNavarraTerritory()
    minimos = plugin.get_minimos_personales()
    assert minimos.contribuyente == 1084.0
    assert minimos.apply_as == "quota_deduction"
