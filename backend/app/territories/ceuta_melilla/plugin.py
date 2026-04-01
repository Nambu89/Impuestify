"""Ceuta/Melilla territory plugin -- IPSI + 60% deduction."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
)


class CeutaMelillaTerritory(TerritoryPlugin):
    """
    Ceuta and Melilla fiscal regime.

    IRPF: Uses estatal scale for both portions (no autonomica scale).
    60% deduction on cuota integra (Art. 68.4 LIRPF).
    Deductions: Estatal only + IPSI.
    Indirect tax: IPSI (6 rate tiers: 0.5%, 1%, 2%, 4%, 8%, 10%).
    """
    territories = ["Ceuta", "Melilla"]
    regime = "ceuta_melilla"

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

    def get_indirect_tax_model(self) -> str:
        return "ipsi"

    def get_minimos_personales(self) -> MinimosConfig:
        # Same base MPYF as common, but applied to estatal-only scale
        return MinimosConfig(
            contribuyente=5550.0,
            descendientes=[2400.0, 2700.0, 4000.0, 4500.0],
            ascendiente_65=1150.0,
            ascendiente_75=2550.0,
            apply_as="base_reduction",
        )

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {"territory": ccaa, "regime": "ceuta_melilla", "deduccion_60": True}
