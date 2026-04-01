"""Foral Vasco territory plugin -- Araba, Bizkaia, Gipuzkoa."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
)


class ForalVascoTerritory(TerritoryPlugin):
    """
    Pais Vasco foral regime.

    IRPF: Single unified foral scale (7 brackets).
    Deductions: Foral only (no estatal deductions).
    Indirect tax: IVA foral + TicketBAI.
    Minimos: Applied as direct quota deduction (EUR off the bill).
    EPSV: Replaces pension plan contributions.
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

    def get_indirect_tax_model(self) -> str:
        return "303"  # IVA foral (+ TicketBAI obligation)

    def get_minimos_personales(self) -> MinimosConfig:
        return MinimosConfig(
            contribuyente=5472.0,
            descendientes=[2808.0, 3432.0, 5040.0, 5040.0],
            ascendiente_65=2040.0,
            ascendiente_75=4080.0,
            apply_as="quota_deduction",
        )
