"""Common regime territory plugin -- covers 15 CCAA under standard IRPF system."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig, Deadline, ModelObligation,
)


# All 15 CCAA under common regime (canonical short names from ccaa_constants.py)
# Note: Canarias uses common IRPF but IGIC instead of IVA.
# CanariasTerritory plugin overrides it in the registry for indirect tax handling.
COMUN_TERRITORIES = [
    "Andalucia", "Aragon", "Asturias", "Baleares", "Cantabria",
    "Castilla-La Mancha", "Castilla y Leon", "Cataluna", "Extremadura",
    "Galicia", "La Rioja", "Madrid", "Murcia", "Comunidad Valenciana",
    "Canarias",
]


class CommonTerritory(TerritoryPlugin):
    """
    Plugin for the 15 CCAA under common fiscal regime.

    IRPF: Estatal + Autonomica scales (split).
    Deductions: Estatal + Territorial.
    Indirect tax: IVA (Modelo 303).
    Minimos: Applied as base reduction (not quota deduction).
    """
    territories = COMUN_TERRITORIES
    regime = "comun"

    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        """Delegates to IRPFCalculator which loads scales from irpf_scales table."""
        # Scales are loaded from DB by IRPFCalculator -- this method is for the interface
        return []  # Actual calculation delegated to simulate_irpf

    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        """Delegate to existing IRPFSimulator._simulate_common logic."""
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
        """Delegate to existing DeductionService -- returns estatal + territorial."""
        from app.services.deduction_service import DeductionService
        service = DeductionService(db)
        return await service.get_all_deductions(ccaa=ccaa, tax_year=year)

    def get_indirect_tax_model(self, ccaa: str = None) -> str:
        return "303"

    def get_minimos_personales(self) -> MinimosConfig:
        """Common regime MPYF -- base reductions per Art. 57-61 LIRPF."""
        return MinimosConfig(
            contribuyente=5550.0,
            descendientes=[2400.0, 2700.0, 4000.0, 4500.0],
            ascendiente_65=1150.0,
            ascendiente_75=2550.0,  # cumulative with 65
            apply_as="base_reduction",
        )

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {"territory": ccaa, "regime": "comun"}
