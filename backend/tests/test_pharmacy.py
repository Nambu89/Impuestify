"""Tests for Pharmacy (Farmaceutico) vertical — Phase 2A.

Validates:
- RE (Recargo de Equivalencia) rates
- Model obligations for farmaceutico profile
- Pharmacy deductions constants
- CNAE/IAE constants
- Modelo303Calculator RE awareness
"""
import pytest
from app.territories.startup import register_all_territories
from app.territories.registry import get_territory, _registry
from app.utils.pharmacy_constants import (
    PHARMACY_CNAE, PHARMACY_IAE, PHARMACY_ACTIVITY,
    RE_RATES, PHARMACY_DEDUCTIONS, PHARMACY_IVA_TYPES,
)
from app.utils.calculators.modelo_303 import Modelo303Calculator


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


# ── Constants tests ──────────────────────────────────────────────

class TestPharmacyConstants:
    def test_cnae(self):
        assert PHARMACY_CNAE == "47.73"

    def test_iae(self):
        assert PHARMACY_IAE == "652.1"

    def test_activity_description(self):
        assert "farmaceuticos" in PHARMACY_ACTIVITY.lower()

    def test_re_rates_general(self):
        assert RE_RATES[21] == 5.2

    def test_re_rates_reducido(self):
        assert RE_RATES[10] == 1.4

    def test_re_rates_superreducido(self):
        assert RE_RATES[4] == 0.5

    def test_re_rates_has_three_entries(self):
        assert len(RE_RATES) == 3

    def test_pharmacy_deductions_count(self):
        assert len(PHARMACY_DEDUCTIONS) == 6

    def test_pharmacy_deduction_codes(self):
        codes = {d["code"] for d in PHARMACY_DEDUCTIONS}
        expected = {"FARM-01", "FARM-02", "FARM-03", "FARM-04", "FARM-05", "FARM-06"}
        assert codes == expected

    def test_pharmacy_iva_types_medicamentos(self):
        assert PHARMACY_IVA_TYPES["medicamentos_uso_humano"] == 4

    def test_pharmacy_iva_types_parafarmacia(self):
        assert PHARMACY_IVA_TYPES["parafarmacia"] == 21

    def test_pharmacy_iva_types_sanitarios(self):
        assert PHARMACY_IVA_TYPES["productos_sanitarios"] == 10


# ── Modelo303Calculator RE awareness ─────────────────────────────

class TestModelo303RecargoEquivalencia:
    def test_farmaceutico_is_re(self):
        assert Modelo303Calculator.is_recargo_equivalencia("farmaceutico") is True

    def test_autonomo_is_not_re(self):
        assert Modelo303Calculator.is_recargo_equivalencia("autonomo") is False

    def test_particular_is_not_re(self):
        assert Modelo303Calculator.is_recargo_equivalencia("particular") is False

    def test_empty_is_not_re(self):
        assert Modelo303Calculator.is_recargo_equivalencia("") is False

    def test_re_rates_on_class(self):
        assert Modelo303Calculator.RE_RATES[21] == 5.2
        assert Modelo303Calculator.RE_RATES[10] == 1.4
        assert Modelo303Calculator.RE_RATES[4] == 0.5


# ── Model obligations for farmaceutico ───────────────────────────

class TestFarmaceuticoObligations:
    def test_farmaceutico_madrid_no_303(self):
        """Farmaceutico should NOT have Modelo 303 (IVA)."""
        obs = _get_modelos("Madrid", {"situacion_laboral": "farmaceutico"})
        ids = _modelo_ids(obs)
        assert "303" not in ids, f"Farmaceutico should NOT have 303, got {ids}"

    def test_farmaceutico_madrid_no_390(self):
        """Farmaceutico should NOT have Modelo 390 (resumen anual IVA)."""
        obs = _get_modelos("Madrid", {"situacion_laboral": "farmaceutico"})
        ids = _modelo_ids(obs)
        assert "390" not in ids, f"Farmaceutico should NOT have 390, got {ids}"

    def test_farmaceutico_madrid_has_130(self):
        """Farmaceutico should have Modelo 130 (pago fraccionado IRPF)."""
        obs = _get_modelos("Madrid", {"situacion_laboral": "farmaceutico"})
        ids = _modelo_ids(obs)
        assert "130" in ids, f"Farmaceutico should have 130, got {ids}"

    def test_farmaceutico_madrid_has_100(self):
        """Farmaceutico should have Modelo 100 (renta anual)."""
        obs = _get_modelos("Madrid", {"situacion_laboral": "farmaceutico"})
        ids = _modelo_ids(obs)
        assert "100" in ids, f"Farmaceutico should have 100, got {ids}"

    def test_farmaceutico_madrid_basic_set(self):
        """Farmaceutico basic obligations: 130 + 100, no 303, no 390."""
        obs = _get_modelos("Madrid", {"situacion_laboral": "farmaceutico"})
        ids = _modelo_ids(obs)
        assert ids == {"130", "100"}, f"Farmaceutico basic set should be 130+100, got {ids}"

    def test_farmaceutico_with_employees(self):
        """Farmaceutico with employees should have retenciones 111 + 190."""
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "farmaceutico",
            "tiene_empleados": True,
        })
        ids = _modelo_ids(obs)
        assert "111" in ids, "Should have retenciones 111 with employees"
        assert "190" in ids, "Should have resumen anual 190"
        assert "303" not in ids, "Still no 303"

    def test_farmaceutico_with_alquileres(self):
        """Farmaceutico with rented premises should have 115 + 180."""
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "farmaceutico",
            "tiene_alquileres": True,
        })
        ids = _modelo_ids(obs)
        assert "115" in ids, "Should have retenciones alquiler 115"
        assert "180" in ids, "Should have resumen anual alquiler 180"

    def test_farmaceutico_estimacion_objetiva(self):
        """Farmaceutico with estimacion objetiva should use 131 instead of 130."""
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "farmaceutico",
            "estimacion": "objetiva",
        })
        ids = _modelo_ids(obs)
        assert "131" in ids, "Estimacion objetiva should use 131"
        assert "130" not in ids, "Should NOT have 130 with estimacion objetiva"

    def test_farmaceutico_ops_terceros(self):
        """Farmaceutico with ops >3005 should have 347."""
        obs = _get_modelos("Madrid", {
            "situacion_laboral": "farmaceutico",
            "tiene_ops_terceros_3005": True,
        })
        ids = _modelo_ids(obs)
        assert "347" in ids, "Should have 347 with ops >3005"

    def test_farmaceutico_re_note_present(self):
        """Farmaceutico obligations should include a note about Recargo de Equivalencia."""
        obs = _get_modelos("Madrid", {"situacion_laboral": "farmaceutico"})
        all_notes = " ".join(ob.notas or "" for ob in obs)
        assert "Recargo de Equivalencia" in all_notes, (
            f"Should mention Recargo de Equivalencia in notes, got: {all_notes}"
        )

    def test_farmaceutico_canarias_no_420(self):
        """Farmaceutico in Canarias should NOT have IGIC 420 either (RE applies)."""
        obs = _get_modelos("Canarias", {"situacion_laboral": "farmaceutico"})
        ids = _modelo_ids(obs)
        assert "420" not in ids, f"Farmaceutico Canarias should NOT have 420, got {ids}"
        assert "130" in ids

    def test_farmaceutico_gipuzkoa_no_300(self):
        """Farmaceutico in Gipuzkoa should NOT have Modelo 300 (foral IVA)."""
        obs = _get_modelos("Gipuzkoa", {"situacion_laboral": "farmaceutico"})
        ids = _modelo_ids(obs)
        assert "300" not in ids, f"Farmaceutico Gipuzkoa should NOT have 300, got {ids}"
        assert "303" not in ids
