"""Ceuta/Melilla territory plugin -- IPSI + 60% deduction."""
from typing import Any, Dict, List

from app.territories.base import (
    TerritoryPlugin, ScaleData, SimulationResult, MinimosConfig,
    ModelObligation, Deadline, DEADLINES_2026, _trimestral_deadlines,
)


class CeutaMelillaTerritory(TerritoryPlugin):
    """
    Ceuta and Melilla fiscal regime.

    IRPF: Uses estatal scale for both portions (no autonomica scale).
    60% deduction on cuota integra (Art. 68.4 LIRPF).
    Deductions: Estatal only + IPSI.
    Indirect tax: IPSI -- Ceuta Modelo 001 (general 3%), Melilla Modelo 420 (general 4%).
    IPSI rate tiers: 0.5%, 1%, 2%, 4% (Ceuta 3%), 8%, 10%.
    """
    territories = ["Ceuta", "Melilla"]
    regime = "ceuta_melilla"

    # IPSI general rates per city
    IPSI_RATES = {
        "Ceuta": 0.03,    # 3% general
        "Melilla": 0.04,  # 4% general
    }

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
        """Ceuta uses Modelo 001 IPSI, Melilla uses Modelo 420 IPSI."""
        if ccaa == "Ceuta":
            return "001"  # Modelo 001 IPSI Ceuta
        return "420"  # Modelo 420 IPSI Melilla

    def get_ipsi_general_rate(self, ccaa: str) -> float:
        """Return the general IPSI rate for the given city."""
        return self.IPSI_RATES.get(ccaa, 0.04)

    def get_minimos_personales(self) -> MinimosConfig:
        # Same base MPYF as common, but applied to estatal-only scale
        return MinimosConfig(
            contribuyente=5550.0,
            descendientes=[2400.0, 2700.0, 4000.0, 4500.0],
            ascendiente_65=1150.0,
            ascendiente_75=2550.0,
            apply_as="base_reduction",
        )

    def get_model_obligations(self, profile: Dict[str, Any]) -> List[ModelObligation]:
        """Ceuta/Melilla: IPSI instead of IVA, no 349, organismo split."""
        ccaa = profile.get("ccaa", "Ceuta")
        # Force no intra-comunitarias (349 not applicable)
        profile_no_intra = {**profile, "ccaa": ccaa, "tiene_ops_intracomunitarias": False}
        obligations = super().get_model_obligations(profile_no_intra)

        ipsi_modelo = self.get_indirect_tax_model(ccaa)
        ciudad = f"Ciudad Autonoma de {ccaa}"

        for ob in obligations:
            if ob.modelo == ipsi_modelo:
                ob.nombre = f"Modelo {ipsi_modelo} - IPSI trimestral ({ccaa})"
                ob.descripcion = (
                    f"Impuesto sobre la Produccion, los Servicios y la Importacion en {ccaa}"
                )
                ob.organismo = ciudad
                rate = self.IPSI_RATES.get(ccaa, 0.04)
                ob.notas = f"IPSI tipo general {rate*100:.0f}%. No aplica IVA ni Modelo 349"
            # Rest of models stay AEAT

        return obligations

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {"territory": ccaa, "regime": "ceuta_melilla", "deduccion_60": True}
