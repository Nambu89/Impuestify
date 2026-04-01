"""Foral Navarra territory plugin."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
)


class ForalNavarraTerritory(TerritoryPlugin):
    """
    Navarra foral regime.

    IRPF: Single unified foral scale (11 brackets).
    Deductions: Foral only.
    Indirect tax: IVA via Modelo F69 (not 303).
    Renta: Modelo F-90 (not 100).
    IS: Modelo S-90 (not 200).
    Retenciones: Modelo 111 (same as AEAT).
    Minimos: Applied as direct quota deduction.
    """
    territories = ["Navarra"]
    regime = "foral_navarra"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        return []

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
        """Navarra uses Modelo F69 for IVA (not the common 303)."""
        return "F69"

    def get_renta_model(self, ccaa: str = None) -> str:
        """Navarra uses Modelo F-90 for IRPF (not 100)."""
        return "F-90"

    def get_is_model(self) -> str:
        """Navarra uses Modelo S-90 for IS (not 200)."""
        return "S-90"

    def get_retenciones_model(self) -> str:
        """Navarra uses Modelo 111 for retenciones (same as AEAT)."""
        return "111"

    def get_minimos_personales(self) -> MinimosConfig:
        return MinimosConfig(
            contribuyente=1084.0,
            descendientes=[600.0, 750.0, 1200.0, 1350.0],
            ascendiente_65=450.0,
            ascendiente_75=900.0,
            apply_as="quota_deduction",
        )
