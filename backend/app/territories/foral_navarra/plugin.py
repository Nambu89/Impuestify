"""Foral Navarra territory plugin."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
    ModelObligation, Deadline, DEADLINES_2026, _trimestral_deadlines,
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

    def get_model_obligations(self, profile: Dict[str, Any]) -> List[ModelObligation]:
        """Navarra: F69 instead of 303, F-90 instead of 100, S-90 instead of 200.
        organismo: HTN (Hacienda Tributaria de Navarra)."""
        profile_with_ccaa = {**profile, "ccaa": "Navarra"}
        obligations = super().get_model_obligations(profile_with_ccaa)

        for ob in obligations:
            ob.organismo = "HTN"

            if ob.modelo == "F69":
                ob.nombre = "Modelo F69 - IVA trimestral (Navarra)"
                ob.descripcion = "Autoliquidacion trimestral del IVA ante Hacienda Tributaria de Navarra"
            elif ob.modelo == "F-90":
                ob.nombre = "Modelo F-90 - IRPF (Navarra)"
                ob.descripcion = "Declaracion anual del IRPF ante HTN"
            elif ob.modelo == "S-90":
                ob.nombre = "Modelo S-90 - Impuesto sobre Sociedades (Navarra)"
                ob.descripcion = "Declaracion anual del IS ante HTN"

        return obligations
