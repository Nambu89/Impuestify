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

        # AIEM (Modelo 450) — productores canarios con bienes en lista AIEM.
        # Heuristica conservadora: el plugin lo añade si el perfil declara
        # explicitamente `produce_bienes_aiem=True` o tiene `epigrafe_iae`
        # registrado en `AIEM_TIPOS_POR_EPIGRAFE`. Asi evitamos falsos
        # positivos para autonomos de servicios (que NO tributan AIEM).
        if situacion in ("autonomo", "sociedad"):
            produce_aiem = profile.get("produce_bienes_aiem", False)
            epigrafes = profile.get("epigrafes_iae") or []
            if not isinstance(epigrafes, list):
                epigrafes = [epigrafes]
            if not produce_aiem and epigrafes:
                from app.utils.calculators.modelo_450 import lookup_tipo_aiem
                produce_aiem = any(
                    lookup_tipo_aiem(str(e)) is not None for e in epigrafes
                )

            if produce_aiem:
                obligations.append(ModelObligation(
                    modelo="450",
                    nombre="Modelo 450 - AIEM trimestral",
                    descripcion=(
                        "Autoliquidacion trimestral del Arbitrio sobre "
                        "Importaciones y Entregas de Mercancias en Canarias "
                        "(productores en lista AIEM, Anexo IV TR Decreto "
                        "Legislativo 1/2025)."
                    ),
                    periodicidad="trimestral",
                    aplica_si=situacion,
                    obligatorio=True,
                    deadlines=_trimestral_deadlines("450"),
                    organismo="ATC",
                    notas=(
                        "Tipos AIEM 5/10/15/25 %. Plazo T4: 1-30 enero ano "
                        "siguiente. Impuesto monofasico — solo lo paga el "
                        "productor. Importaciones se liquidan en aduana via DUA."
                    ),
                ))

        # AIEM ZEC (Modelo 455) — entidades ZEC con autorizacion para
        # producir/entregar mercancias. Requiere flag explicito `regimen_zec`.
        if situacion == "sociedad" and profile.get("regimen_zec", False):
            obligations.append(ModelObligation(
                modelo="455",
                nombre="Modelo 455 - AIEM ZEC anual",
                descripcion=(
                    "Autoliquidacion anual del AIEM para entidades ZEC "
                    "(Zona Especial Canaria) con autorizacion para producir / "
                    "entregar mercancias en Canarias."
                ),
                periodicidad="anual",
                aplica_si="sociedad",
                obligatorio=True,
                deadlines=[Deadline(
                    modelo="455",
                    description="Modelo 455 - AIEM ZEC anual",
                    date="2026-01-30",
                    period="annual",
                )],
                organismo="ATC",
                notas=(
                    "Periodicidad ANUAL (1-30 enero ano siguiente). Requiere "
                    "autorizacion previa del Consorcio ZEC (Ley 19/1994). "
                    "Tipos AIEM 5/10/15/25 %."
                ),
            ))

        return obligations

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        return {
            "territory": "Canarias",
            "regime": "canarias",
            "igic": True,
            "modelo_349": False,  # Not applicable in Canarias
        }
