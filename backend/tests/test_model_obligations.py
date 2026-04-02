"""Tests for Model Obligations Advisor (Phase 1A).

Validates that each territory plugin returns the correct fiscal models
based on taxpayer profile (situacion_laboral, CCAA, empleados, etc.).
"""
import pytest
from app.territories.startup import register_all_territories
from app.territories.registry import get_territory, _registry


@pytest.fixture(autouse=True)
def setup_registry():
    """Ensure all territory plugins are registered before each test."""
    _registry.clear()
    register_all_territories()
    yield
    _registry.clear()


def _get_modelos(ccaa: str, profile_overrides: dict = None) -> list:
    """Helper: get model obligations for a CCAA with optional profile overrides."""
    plugin = get_territory(ccaa)
    profile = {
        "ccaa": ccaa,
        "situacion_laboral": "particular",
        "tiene_empleados": False,
        "tiene_alquileres": False,
        "estimacion": "directa_simplificada",
        "tiene_ops_intracomunitarias": False,
        "tiene_ops_terceros_3005": False,
        "paga_dividendos": False,
    }
    if profile_overrides:
        profile.update(profile_overrides)
    return plugin.get_model_obligations(profile)


def _modelo_ids(obligations: list) -> set:
    """Extract just the modelo numbers from a list of ModelObligation."""
    return {ob.modelo for ob in obligations}


# ── Particular tests ──────────────────────────────────────────────

class TestParticularObligations:
    def test_particular_madrid_only_renta(self):
        obs = _get_modelos("Madrid")
        ids = _modelo_ids(obs)
        assert ids == {"100"}, f"Particular Madrid should only have 100, got {ids}"

    def test_particular_canarias_only_renta(self):
        obs = _get_modelos("Canarias")
        ids = _modelo_ids(obs)
        assert "100" in ids
        assert "420" not in ids  # No IGIC for particular

    def test_particular_gipuzkoa_gets_109(self):
        obs = _get_modelos("Gipuzkoa")
        ids = _modelo_ids(obs)
        assert "109" in ids
        assert "100" not in ids

    def test_particular_navarra_gets_f90(self):
        obs = _get_modelos("Navarra")
        ids = _modelo_ids(obs)
        assert "F-90" in ids
        assert "100" not in ids

    def test_particular_bizkaia_gets_100(self):
        obs = _get_modelos("Bizkaia")
        ids = _modelo_ids(obs)
        assert "100" in ids  # Bizkaia uses 100, not 109

    def test_particular_ceuta_only_renta(self):
        obs = _get_modelos("Ceuta")
        ids = _modelo_ids(obs)
        assert "100" in ids
        assert "001" not in ids  # No IPSI for particular


# ── Autonomo tests ────────────────────────────────────────────────

class TestAutonomoObligations:
    def test_autonomo_madrid_basic(self):
        obs = _get_modelos("Madrid", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "303" in ids, "Should have IVA 303"
        assert "130" in ids, "Should have pago fraccionado 130"
        assert "100" in ids, "Should have renta 100"
        assert "111" not in ids, "No retenciones without employees"
        assert "349" not in ids, "No 349 without intra-comunitarias"

    def test_autonomo_madrid_with_employees(self):
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "autonomo",
            "tiene_empleados": True,
        })
        ids = _modelo_ids(obs)
        assert "111" in ids, "Should have retenciones 111 with employees"
        assert "190" in ids, "Should have resumen anual 190"

    def test_autonomo_madrid_with_alquileres(self):
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "autonomo",
            "tiene_alquileres": True,
        })
        ids = _modelo_ids(obs)
        assert "115" in ids, "Should have retenciones alquiler 115"
        assert "180" in ids, "Should have resumen anual alquiler 180"

    def test_autonomo_madrid_estimacion_objetiva(self):
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "autonomo",
            "estimacion": "objetiva",
        })
        ids = _modelo_ids(obs)
        assert "131" in ids, "Estimacion objetiva should use 131"
        assert "130" not in ids, "Should NOT have 130 with estimacion objetiva"

    def test_autonomo_madrid_ops_intracomunitarias(self):
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "autonomo",
            "tiene_ops_intracomunitarias": True,
        })
        ids = _modelo_ids(obs)
        assert "349" in ids, "Should have 349 with intra-comunitarias"

    def test_autonomo_madrid_ops_terceros(self):
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "autonomo",
            "tiene_ops_terceros_3005": True,
        })
        ids = _modelo_ids(obs)
        assert "347" in ids, "Should have 347 with ops >3005"

    # ── Canarias ──

    def test_autonomo_canarias_igic_not_iva(self):
        obs = _get_modelos("Canarias", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "420" in ids, "Canarias should use IGIC 420"
        assert "303" not in ids, "Canarias should NOT have IVA 303"
        assert "425" in ids, "Canarias should have resumen anual IGIC 425"

    def test_autonomo_canarias_no_349(self):
        obs = _get_modelos("Canarias", {
            "situacion_laboral": "autonomo",
            "tiene_ops_intracomunitarias": True,
        })
        ids = _modelo_ids(obs)
        assert "349" not in ids, "Canarias should NOT have 349 even with intra-comunitarias flag"

    def test_autonomo_canarias_organismo_atc(self):
        obs = _get_modelos("Canarias", {"situacion_laboral": "autonomo"})
        igic = [ob for ob in obs if ob.modelo == "420"]
        assert len(igic) == 1
        assert igic[0].organismo == "ATC"

    # ── Gipuzkoa (Foral Vasco) ──

    def test_autonomo_gipuzkoa_modelo_300(self):
        obs = _get_modelos("Gipuzkoa", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "300" in ids, "Gipuzkoa should use modelo 300 for IVA"
        assert "303" not in ids, "Gipuzkoa should NOT use 303"

    def test_autonomo_gipuzkoa_modelo_109(self):
        obs = _get_modelos("Gipuzkoa", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "109" in ids, "Gipuzkoa should use modelo 109 for IRPF"
        assert "100" not in ids, "Gipuzkoa should NOT use 100"

    def test_autonomo_gipuzkoa_modelo_110(self):
        obs = _get_modelos("Gipuzkoa", {
            "situacion_laboral": "autonomo",
            "tiene_empleados": True,
        })
        ids = _modelo_ids(obs)
        assert "110" in ids, "Foral vasco should use 110 for retenciones"
        assert "111" not in ids, "Should NOT use 111"

    def test_autonomo_gipuzkoa_organismo_dfg(self):
        obs = _get_modelos("Gipuzkoa", {"situacion_laboral": "autonomo"})
        assert all(ob.organismo == "DFG" for ob in obs)

    def test_autonomo_bizkaia_modelo_303(self):
        obs = _get_modelos("Bizkaia", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "303" in ids, "Bizkaia should use 303 for IVA"
        assert "300" not in ids

    def test_autonomo_bizkaia_organismo_dfb(self):
        obs = _get_modelos("Bizkaia", {"situacion_laboral": "autonomo"})
        assert all(ob.organismo == "DFB" for ob in obs)

    def test_autonomo_araba_organismo_dfa(self):
        obs = _get_modelos("Araba", {"situacion_laboral": "autonomo"})
        assert all(ob.organismo == "DFA" for ob in obs)

    # ── Navarra ──

    def test_autonomo_navarra_f69(self):
        obs = _get_modelos("Navarra", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "F69" in ids, "Navarra should use F69 for IVA"
        assert "303" not in ids

    def test_autonomo_navarra_f90(self):
        obs = _get_modelos("Navarra", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "F-90" in ids, "Navarra should use F-90 for IRPF"
        assert "100" not in ids

    def test_autonomo_navarra_organismo_htn(self):
        obs = _get_modelos("Navarra", {"situacion_laboral": "autonomo"})
        assert all(ob.organismo == "HTN" for ob in obs)

    # ── Ceuta ──

    def test_autonomo_ceuta_ipsi_001(self):
        obs = _get_modelos("Ceuta", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "001" in ids, "Ceuta should use IPSI modelo 001"
        assert "303" not in ids, "Ceuta should NOT have IVA 303"

    def test_autonomo_ceuta_no_349(self):
        obs = _get_modelos("Ceuta", {
            "situacion_laboral": "autonomo",
            "tiene_ops_intracomunitarias": True,
        })
        ids = _modelo_ids(obs)
        assert "349" not in ids, "Ceuta should NOT have 349"

    def test_autonomo_ceuta_ipsi_organismo(self):
        obs = _get_modelos("Ceuta", {"situacion_laboral": "autonomo"})
        ipsi = [ob for ob in obs if ob.modelo == "001"]
        assert len(ipsi) == 1
        assert ipsi[0].organismo == "Ciudad Autonoma de Ceuta"

    # ── Melilla ──

    def test_autonomo_melilla_ipsi_420(self):
        obs = _get_modelos("Melilla", {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "420" in ids, "Melilla should use IPSI modelo 420"
        assert "303" not in ids

    def test_autonomo_melilla_no_349(self):
        obs = _get_modelos("Melilla", {
            "situacion_laboral": "autonomo",
            "tiene_ops_intracomunitarias": True,
        })
        ids = _modelo_ids(obs)
        assert "349" not in ids, "Melilla should NOT have 349"


# ── Sociedad tests ────────────────────────────────────────────────

class TestSociedadObligations:
    def test_sociedad_madrid_basic(self):
        obs = _get_modelos("Madrid", {"situacion_laboral": "sociedad"})
        ids = _modelo_ids(obs)
        assert "200" in ids, "Sociedad should have IS 200"
        assert "303" in ids, "Sociedad should have IVA 303"
        assert "111" in ids, "Sociedad should have retenciones 111"
        assert "190" in ids, "Sociedad should have resumen 190"
        assert "202" in ids, "Sociedad should have pagos fraccionados IS 202"

    def test_sociedad_madrid_dividendos(self):
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "sociedad",
            "paga_dividendos": True,
        })
        ids = _modelo_ids(obs)
        assert "123" in ids, "Should have 123 with dividendos"
        assert "193" in ids, "Should have 193 with dividendos"

    def test_sociedad_madrid_alquileres(self):
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "sociedad",
            "tiene_alquileres": True,
        })
        ids = _modelo_ids(obs)
        assert "115" in ids
        assert "180" in ids

    def test_sociedad_navarra_s90(self):
        obs = _get_modelos("Navarra", {"situacion_laboral": "sociedad"})
        ids = _modelo_ids(obs)
        assert "S-90" in ids, "Navarra sociedad should use S-90"
        assert "200" not in ids


# ── Deadline tests ────────────────────────────────────────────────

class TestDeadlines:
    def test_trimestral_has_4_deadlines(self):
        obs = _get_modelos("Madrid", {"situacion_laboral": "autonomo"})
        iva = [ob for ob in obs if ob.modelo == "303"]
        assert len(iva) == 1
        assert len(iva[0].deadlines) == 4, "Trimestral should have 4 deadlines"

    def test_renta_has_1_deadline(self):
        obs = _get_modelos("Madrid")
        renta = [ob for ob in obs if ob.modelo == "100"]
        assert len(renta) == 1
        assert len(renta[0].deadlines) >= 1

    def test_deadline_dates_are_valid(self):
        obs = _get_modelos("Madrid", {"situacion_laboral": "autonomo"})
        for ob in obs:
            for d in ob.deadlines:
                # Verify ISO date format
                assert len(d.date) == 10, f"Date {d.date} should be YYYY-MM-DD"
                assert d.date[4] == "-" and d.date[7] == "-"


# ── TicketBAI / Batuz note tests ──────────────────────────────────

class TestTerritoryNotes:
    def test_foral_vasco_ticketbai_note(self):
        obs = _get_modelos("Gipuzkoa", {"situacion_laboral": "autonomo"})
        for ob in obs:
            assert "TicketBAI" in (ob.notas or ""), f"Model {ob.modelo} should mention TicketBAI"

    def test_canarias_igic_note(self):
        obs = _get_modelos("Canarias", {"situacion_laboral": "autonomo"})
        igic = [ob for ob in obs if ob.modelo == "420"]
        assert len(igic) == 1
        assert "IGIC" in (igic[0].notas or "")

    def test_ceuta_ipsi_note(self):
        obs = _get_modelos("Ceuta", {"situacion_laboral": "autonomo"})
        ipsi = [ob for ob in obs if ob.modelo == "001"]
        assert len(ipsi) == 1
        assert "IPSI" in (ipsi[0].notas or "")
        assert "3%" in (ipsi[0].notas or "")


# ── Common regime CCAA coverage ───────────────────────────────────

class TestCommonRegimeCoverage:
    """Verify that all 15 common CCAA return the same basic models for autonomo."""

    COMMON_CCAA = [
        "Andalucia", "Aragon", "Asturias", "Baleares", "Cantabria",
        "Castilla-La Mancha", "Castilla y Leon", "Cataluna", "Extremadura",
        "Galicia", "La Rioja", "Madrid", "Murcia", "Comunidad Valenciana",
    ]

    @pytest.mark.parametrize("ccaa", COMMON_CCAA)
    def test_autonomo_common_ccaa(self, ccaa):
        obs = _get_modelos(ccaa, {"situacion_laboral": "autonomo"})
        ids = _modelo_ids(obs)
        assert "303" in ids, f"{ccaa} autonomo should have 303"
        assert "130" in ids, f"{ccaa} autonomo should have 130"
        assert "100" in ids, f"{ccaa} autonomo should have 100"
