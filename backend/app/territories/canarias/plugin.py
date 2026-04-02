"""Canarias territory plugin -- IGIC instead of IVA, common IRPF."""
from typing import Any, Dict, List

from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
    ModelObligation, Deadline, DEADLINES_2026, _trimestral_deadlines,
)


class CanariasTerritory(TerritoryPlugin):
    """
    Canarias fiscal regime.

    IRPF: Uses estatal scales (both portions) like common regime.
    Deductions: Estatal + Canarias territorial.
    Indirect tax: IGIC (Modelo 420), NOT IVA.
    General IGIC rate: 7% (vs 21% peninsular IVA).
    Modelo 349 does NOT apply -- Canarias is not harmonized EU VAT territory.
    AIEM (Arbitrio sobre Importaciones y Entregas de Mercancias en Canarias)
    applies on specific goods imported into the islands.
    """
    territories = ["Canarias"]
    regime = "canarias"

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
        return "420"  # IGIC

    def get_minimos_personales(self) -> MinimosConfig:
        # Canarias uses same MPYF as common regime
        return MinimosConfig(
            contribuyente=5550.0,
            descendientes=[2400.0, 2700.0, 4000.0, 4500.0],
            ascendiente_65=1150.0,
            ascendiente_75=2550.0,
            apply_as="base_reduction",
        )

    def get_model_obligations(self, profile: Dict[str, Any]) -> List[ModelObligation]:
        """Canarias: IGIC 420 instead of IVA 303, resumen 425 instead of 390, NO 349.
        AIEM models (450, 455) if applicable."""
        # Get base obligations from parent
        profile_with_ccaa = {**profile, "ccaa": "Canarias"}
        # Force no intra-comunitarias (349 not applicable in Canarias)
        profile_no_intra = {**profile_with_ccaa, "tiene_ops_intracomunitarias": False}
        obligations = super().get_model_obligations(profile_no_intra)

        # Add Canarias-specific notes to IGIC model
        for ob in obligations:
            if ob.modelo == "420":
                ob.nombre = "Modelo 420 - IGIC trimestral"
                ob.descripcion = "Autoliquidacion trimestral del Impuesto General Indirecto Canario (IGIC 7%)"
                ob.organismo = "ATC"
                ob.notas = "Canarias no aplica IVA sino IGIC. Tipo general 7%"

        # Add resumen anual IGIC (425 instead of 390)
        situacion = profile.get("situacion_laboral", "particular")
        if situacion in ("autonomo", "sociedad"):
            obligations.append(ModelObligation(
                modelo="425",
                nombre="Modelo 425 - Resumen anual IGIC",
                descripcion="Resumen anual del Impuesto General Indirecto Canario",
                periodicidad="anual",
                aplica_si=situacion,
                obligatorio=True,
                deadlines=[Deadline(modelo="425", description="Resumen anual IGIC", date="2026-01-30", period="annual")],
                organismo="ATC",
            ))

        return obligations

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {
            "territory": "Canarias",
            "regime": "canarias",
            "igic": True,
            "modelo_349": False,  # Not applicable in Canarias
        }
