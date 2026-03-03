"""
IRPF Simulator — Orchestrates all calculators for a full IRPF simulation.

Composes WorkIncomeCalculator, SavingsIncomeCalculator, RentalIncomeCalculator,
and MPYFCalculator to produce a complete tax estimate from gross income to
final tax liability (cuota líquida).

Follows Open/Closed: new income types can be added by creating a new calculator
and plugging it in here, without modifying existing calculators.
"""
from typing import Any, Dict, List, Optional
import logging

from app.utils.tax_parameter_repository import TaxParameterRepository
from app.utils.irpf_calculator import IRPFCalculator
from app.utils.calculators.work_income import WorkIncomeCalculator
from app.utils.calculators.savings_income import SavingsIncomeCalculator
from app.utils.calculators.rental_income import RentalIncomeCalculator
from app.utils.calculators.mpyf import MPYFCalculator

logger = logging.getLogger(__name__)


class IRPFSimulator:
    """
    Orchestrates multiple income calculators for a complete IRPF simulation.

    Flow:
    1. Calculate net income for each income type (work, savings, rental)
    2. Compute base imponible general (work + rental) and base del ahorro
    3. Apply progressive general scale (tarifa general)
    4. Apply savings scale (tarifa del ahorro)
    5. Compute MPYF (personal and family minimum)
    6. Subtract MPYF quota from cuota íntegra → cuota líquida
    """

    def __init__(self, db):
        self._db = db
        self._repo = TaxParameterRepository(db)
        self._irpf_calc = IRPFCalculator()
        self._irpf_calc.db = db

        self.work = WorkIncomeCalculator(self._repo)
        self.savings = SavingsIncomeCalculator(self._repo, db)
        self.rental = RentalIncomeCalculator(self._repo)
        self.mpyf = MPYFCalculator(self._repo)

    async def simulate(
        self,
        *,
        jurisdiction: str,
        year: int = 2024,
        # Work income
        ingresos_trabajo: float = 0,
        ss_empleado: float = 0,
        cuotas_sindicales: float = 0,
        colegio_profesional: float = 0,
        # Savings income
        intereses: float = 0,
        dividendos: float = 0,
        ganancias_fondos: float = 0,
        # Rental income
        ingresos_alquiler: float = 0,
        gastos_alquiler_total: float = 0,
        valor_adquisicion_inmueble: float = 0,
        es_vivienda_habitual: bool = True,
        # Family situation (for MPYF)
        edad_contribuyente: int = 35,
        num_descendientes: int = 0,
        anios_nacimiento_desc: Optional[List[int]] = None,
        custodia_compartida: bool = False,
        num_ascendientes_65: int = 0,
        num_ascendientes_75: int = 0,
        discapacidad_contribuyente: int = 0,
        # Ceuta/Melilla
        ceuta_melilla: bool = False,
    ) -> Dict[str, Any]:
        """
        Run a complete IRPF simulation.

        Args:
            jurisdiction: CCAA name (affects autonomous scale and MPYF).
            year: Fiscal year.
            ingresos_trabajo: Annual gross work income.
            ss_empleado: Employee SS contributions (0 = auto-estimated).
            cuotas_sindicales: Union dues.
            colegio_profesional: Professional association fees.
            intereses: Bank interest income.
            dividendos: Dividend income.
            ganancias_fondos: Fund/ETF capital gains.
            ingresos_alquiler: Annual rental income.
            gastos_alquiler_total: Total deductible rental expenses.
            valor_adquisicion_inmueble: Property acquisition value (for amortization).
            es_vivienda_habitual: If rental is primary residence.
            edad_contribuyente: Taxpayer age.
            num_descendientes: Number of dependent children.
            anios_nacimiento_desc: Birth years of children.
            custodia_compartida: Shared custody.
            num_ascendientes_65: Dependent ascendants >65.
            num_ascendientes_75: Dependent ascendants >75.
            discapacidad_contribuyente: Disability percentage.

        Returns:
            Complete simulation result with all intermediate values.
        """
        # --- 1. Work income ---
        trabajo_result = await self.work.calculate(
            ingresos_brutos=ingresos_trabajo,
            ss_empleado=ss_empleado,
            cuotas_sindicales=cuotas_sindicales,
            colegio_profesional=colegio_profesional,
            year=year,
        )

        # --- 2. Rental income (if any) ---
        inmuebles_result = None
        rend_inmuebles = 0.0
        if ingresos_alquiler > 0:
            inmuebles_result = await self.rental.calculate(
                ingresos_alquiler=ingresos_alquiler,
                gastos_comunidad=gastos_alquiler_total,  # simplified: user provides total
                valor_adquisicion=valor_adquisicion_inmueble,
                es_vivienda_habitual=es_vivienda_habitual,
                year=year,
            )
            rend_inmuebles = inmuebles_result["rendimiento_neto_reducido"]

        # --- 3. Base imponible general ---
        bi_general = trabajo_result["rendimiento_neto_reducido"] + rend_inmuebles

        # --- 4. Savings income (if any) ---
        ahorro_result = None
        if intereses > 0 or dividendos > 0 or ganancias_fondos > 0:
            ahorro_result = await self.savings.calculate(
                intereses=intereses,
                dividendos=dividendos,
                ganancias_fondos=ganancias_fondos,
                jurisdiction=jurisdiction,
                year=year,
            )

        base_ahorro = ahorro_result["base_ahorro"] if ahorro_result else 0.0

        # --- 5. Apply general progressive scale ---
        general_result = await self._irpf_calc.calculate_irpf(
            base_liquidable=bi_general,
            jurisdiction=jurisdiction,
            year=year,
        )

        # --- 6. MPYF ---
        mpyf_result = await self.mpyf.calculate(
            jurisdiction=jurisdiction,
            year=year,
            edad_contribuyente=edad_contribuyente,
            num_descendientes=num_descendientes,
            anios_nacimiento_desc=anios_nacimiento_desc,
            custodia_compartida=custodia_compartida,
            num_ascendientes_65=num_ascendientes_65,
            num_ascendientes_75=num_ascendientes_75,
            discapacidad_contribuyente=discapacidad_contribuyente,
        )

        # --- 7. Apply MPYF: subtract MPYF quota from cuota íntegra ---
        state_scale = await self._irpf_calc._get_scale("Estatal", year)
        ccaa_scale = await self._irpf_calc._get_scale(jurisdiction, year)

        cuota_mpyf_est, _ = self._irpf_calc._apply_scale(
            mpyf_result["mpyf_estatal"], state_scale
        )
        cuota_mpyf_aut, _ = self._irpf_calc._apply_scale(
            mpyf_result["mpyf_autonomico"], ccaa_scale
        )

        cuota_liquida_est = max(0, general_result["cuota_estatal"] - cuota_mpyf_est)
        cuota_liquida_aut = max(0, general_result["cuota_autonomica"] - cuota_mpyf_aut)
        cuota_liquida_general = cuota_liquida_est + cuota_liquida_aut

        # --- 8. Ceuta/Melilla deduction (Art. 68.4 LIRPF) ---
        # 60% deduction on the cuota íntegra (estatal + autonómica + ahorro)
        # for income earned by residents in Ceuta or Melilla.
        deduccion_ceuta_melilla = 0.0
        cuota_ahorro = ahorro_result["cuota_ahorro_total"] if ahorro_result else 0.0

        if ceuta_melilla:
            cuota_integra_total = general_result["cuota_total"] + cuota_ahorro
            deduccion_ceuta_melilla = round(cuota_integra_total * 0.60, 2)
            # Apply deduction: first reduce general, then ahorro if needed
            remaining_deduction = deduccion_ceuta_melilla
            deduccion_on_general = min(remaining_deduction, cuota_liquida_general)
            cuota_liquida_general = max(0, cuota_liquida_general - deduccion_on_general)
            remaining_deduction -= deduccion_on_general
            if remaining_deduction > 0:
                cuota_ahorro = max(0, cuota_ahorro - remaining_deduction)
            # Recalculate estatal/autonomica split proportionally
            if cuota_liquida_est + cuota_liquida_aut > 0:
                ratio_est = cuota_liquida_est / (cuota_liquida_est + cuota_liquida_aut)
                cuota_liquida_est = round(cuota_liquida_general * ratio_est, 2)
                cuota_liquida_aut = round(cuota_liquida_general - cuota_liquida_est, 2)
            else:
                cuota_liquida_est = 0.0
                cuota_liquida_aut = 0.0
            logger.info(
                "Ceuta/Melilla deduction applied: -%.2f€ (60%% of %.2f€ cuota íntegra)",
                deduccion_ceuta_melilla, cuota_integra_total,
            )

        # --- 9. Total ---
        cuota_total = cuota_liquida_general + cuota_ahorro

        base_total = bi_general + base_ahorro
        tipo_medio = (cuota_total / base_total * 100) if base_total > 0 else 0.0

        return {
            "success": True,
            "year": year,
            "jurisdiction": jurisdiction,
            "ceuta_melilla": ceuta_melilla,
            # Income breakdown
            "trabajo": trabajo_result,
            "inmuebles": inmuebles_result,
            "ahorro": ahorro_result,
            # Tax bases
            "base_imponible_general": round(bi_general, 2),
            "base_imponible_ahorro": round(base_ahorro, 2),
            # General tax
            "cuota_integra_estatal": general_result["cuota_estatal"],
            "cuota_integra_autonomica": general_result["cuota_autonomica"],
            "cuota_integra_general": general_result["cuota_total"],
            "breakdown_estatal": general_result["breakdown_estatal"],
            "breakdown_autonomica": general_result["breakdown_autonomica"],
            # MPYF
            "mpyf": mpyf_result,
            "cuota_mpyf_estatal": round(cuota_mpyf_est, 2),
            "cuota_mpyf_autonomica": round(cuota_mpyf_aut, 2),
            # Ceuta/Melilla deduction
            "deduccion_ceuta_melilla": deduccion_ceuta_melilla,
            # Final
            "cuota_liquida_estatal": round(cuota_liquida_est, 2),
            "cuota_liquida_autonomica": round(cuota_liquida_aut, 2),
            "cuota_liquida_general": round(cuota_liquida_general, 2),
            "cuota_ahorro": round(cuota_ahorro, 2),
            "cuota_total": round(cuota_total, 2),
            "tipo_medio": round(tipo_medio, 2),
        }
