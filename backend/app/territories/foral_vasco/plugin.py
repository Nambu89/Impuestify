"""Foral Vasco territory plugin -- Araba, Bizkaia, Gipuzkoa."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
    ModelObligation, Deadline, DEADLINES_2026, _trimestral_deadlines,
)


class ForalVascoTerritory(TerritoryPlugin):
    """
    Pais Vasco foral regime.

    IRPF: Single unified foral scale (7 brackets).
    Deductions: Foral only (no estatal deductions).
    Indirect tax: IVA foral (303 for Bizkaia/Araba, 300 for Gipuzkoa).
    TicketBAI/Batuz: Mandatory electronic invoicing across all 3 territories.
    Retenciones: Modelo 110 (not 111 as in common regime).
    EPSV: Replaces pension plan contributions.
    Minimos: Applied as direct quota deduction (EUR off the bill).
    """
    territories = ["Araba", "Bizkaia", "Gipuzkoa"]
    regime = "foral_vasco"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        return []  # Loaded from DB in simulate_irpf

    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        from app.utils.irpf_simulator import IRPFSimulator
        simulator = IRPFSimulator(db)
        result = await simulator.simulate(**profile)
        return SimulationResult(
            base_imponible_general=result.get("base_imponible_general", 0),
            base_imponible_ahorro=result.get("base_imponible_ahorro", 0),
            cuota_integra=result.get("cuota_integra", 0),
            cuota_liquida=result.get("cuota_liquida", 0),
            resultado=result.get("resultado", 0),
            tipo_resultado=result.get("tipo_resultado", "a_pagar"),
            desglose=result,
        )

    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        from app.services.deduction_service import DeductionService
        service = DeductionService(db)
        return await service.get_all_deductions(ccaa=ccaa, tax_year=year)

    def get_indirect_tax_model(self, ccaa: str = None) -> str:
        """Gipuzkoa uses Modelo 300, Bizkaia/Araba use 303."""
        if ccaa == "Gipuzkoa":
            return "300"
        return "303"  # Bizkaia, Araba

    def get_renta_model(self, ccaa: str = None) -> str:
        """Gipuzkoa uses Modelo 109 for IRPF, Bizkaia/Araba use 100."""
        if ccaa == "Gipuzkoa":
            return "109"
        return "100"  # Bizkaia, Araba

    def get_retenciones_model(self) -> str:
        """All 3 Basque territories use Modelo 110 (not 111)."""
        return "110"

    def get_minimos_personales(self) -> MinimosConfig:
        return MinimosConfig(
            contribuyente=5472.0,
            descendientes=[2808.0, 3432.0, 5040.0, 5040.0],
            ascendiente_65=2040.0,
            ascendiente_75=4080.0,
            apply_as="quota_deduction",
        )

    def _get_organismo(self, ccaa: str) -> str:
        """Return the Diputacion Foral identifier."""
        mapping = {"Gipuzkoa": "DFG", "Bizkaia": "DFB", "Araba": "DFA"}
        return mapping.get(ccaa, "DFG")

    def get_model_obligations(self, profile: Dict[str, Any]) -> List[ModelObligation]:
        """Foral Vasco: 300 (Gipuzkoa) or 303 (Bizkaia/Araba), 110 not 111,
        109 (Gipuzkoa) or 100, TicketBAI/Batuz mandatory."""
        ccaa = profile.get("ccaa", "Gipuzkoa")
        profile_with_ccaa = {**profile, "ccaa": ccaa}
        obligations = super().get_model_obligations(profile_with_ccaa)

        organismo = self._get_organismo(ccaa)

        # Update organismo and add TicketBAI note
        for ob in obligations:
            ob.organismo = organismo
            if ob.notas:
                ob.notas += ". TicketBAI/Batuz obligatorio"
            else:
                ob.notas = "TicketBAI/Batuz obligatorio"

            # Rename IRPF model
            if ob.modelo == "109":
                ob.nombre = "Modelo 109 - IRPF (Gipuzkoa)"
                ob.descripcion = "Declaracion anual del IRPF ante la Diputacion Foral de Gipuzkoa"
            elif ob.modelo == "300":
                ob.nombre = "Modelo 300 - IVA trimestral (Gipuzkoa)"
                ob.descripcion = "Autoliquidacion trimestral del IVA ante la DFG"
            elif ob.modelo == "110":
                ob.nombre = "Modelo 110 - Retenciones trabajo (foral)"
                ob.descripcion = "Retenciones e ingresos a cuenta del trabajo (modelo foral)"

        return obligations
