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
from app.utils.irpf_calculator import IRPFCalculator, ESTATAL_SCALE_JURISDICTIONS
from app.utils.calculators.work_income import WorkIncomeCalculator
from app.utils.calculators.savings_income import SavingsIncomeCalculator
from app.utils.calculators.rental_income import RentalIncomeCalculator
from app.utils.calculators.mpyf import MPYFCalculator
from app.utils.calculators.activity_income import ActivityIncomeCalculator

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
        self.activity = ActivityIncomeCalculator(self._repo)
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
        # --- Activity income (autonomos) ---
        ingresos_actividad: float = 0,
        gastos_actividad: float = 0,
        cuota_autonomo_anual: float = 0,
        amortizaciones_actividad: float = 0,
        provisiones_actividad: float = 0,
        otros_gastos_actividad: float = 0,
        estimacion_actividad: str = "directa_simplificada",
        inicio_actividad: bool = False,
        un_solo_cliente: bool = False,
        retenciones_actividad: float = 0,
        pagos_fraccionados_130: float = 0,
        # --- Phase 1: Reductions to base imponible general ---
        aportaciones_plan_pensiones: float = 0,
        aportaciones_plan_pensiones_empresa: float = 0,
        # --- Phase 1: Deductions on cuota ---
        hipoteca_pre2013: bool = False,
        capital_amortizado_hipoteca: float = 0,
        intereses_hipoteca: float = 0,
        madre_trabajadora_ss: bool = False,
        gastos_guarderia_anual: float = 0,
        familia_numerosa: bool = False,
        tipo_familia_numerosa: str = "general",
        donativos_ley_49_2002: float = 0,
        donativo_recurrente: bool = False,
        # --- Phase 1: Additional withholdings ---
        retenciones_alquiler: float = 0,
        retenciones_ahorro: float = 0,
        # --- Phase 2: Tributación conjunta (Art. 84 LIRPF) ---
        tributacion_conjunta: bool = False,
        tipo_unidad_familiar: str = "matrimonio",
        # --- Phase 2: Alquiler vivienda habitual pre-2015 (DT 15ª LIRPF) ---
        alquiler_habitual_pre2015: bool = False,
        alquiler_pagado_anual: float = 0,
        # --- Phase 2: Rentas imputadas inmuebles (Art. 85 LIRPF) ---
        valor_catastral_segundas_viviendas: float = 0,
        valor_catastral_revisado_post1994: bool = True,
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
        # Auto-detect Ceuta/Melilla from jurisdiction name
        if not ceuta_melilla and jurisdiction.lower() in ESTATAL_SCALE_JURISDICTIONS:
            ceuta_melilla = True
            logger.info("Auto-detected Ceuta/Melilla from jurisdiction=%s", jurisdiction)

        # --- 1. Work income ---
        trabajo_result = await self.work.calculate(
            ingresos_brutos=ingresos_trabajo,
            ss_empleado=ss_empleado,
            cuotas_sindicales=cuotas_sindicales,
            colegio_profesional=colegio_profesional,
            year=year,
        )

        # --- 1b. Activity income (autonomos) ---
        actividad_result = None
        rend_actividad = 0.0
        if ingresos_actividad > 0:
            actividad_result = await self.activity.calculate(
                ingresos_actividad=ingresos_actividad,
                gastos_actividad=gastos_actividad,
                cuota_autonomo_anual=cuota_autonomo_anual,
                amortizaciones=amortizaciones_actividad,
                provisiones=provisiones_actividad,
                otros_gastos_deducibles=otros_gastos_actividad,
                estimacion=estimacion_actividad,
                inicio_actividad=inicio_actividad,
                un_solo_cliente=un_solo_cliente,
                year=year,
            )
            rend_actividad = actividad_result["rendimiento_neto_reducido"]

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
        bi_general = trabajo_result["rendimiento_neto_reducido"] + rend_actividad + rend_inmuebles

        # --- 3b. Reduction: pension plan contributions (Art. 51-52 LIRPF) ---
        reduccion_planes_pensiones = 0.0
        if aportaciones_plan_pensiones > 0 or aportaciones_plan_pensiones_empresa > 0:
            net_work_income = trabajo_result.get("rendimiento_neto_reducido", 0)
            # Own contributions: max 1.500 EUR
            own_limit = min(aportaciones_plan_pensiones, 1500)
            # Employer contributions: joint limit 8.500 EUR
            employer = aportaciones_plan_pensiones_empresa
            joint_limit = min(own_limit + employer, 8500)
            # Cannot exceed 30% of net work income
            pct_limit = net_work_income * 0.30 if net_work_income > 0 else 0
            reduccion_planes_pensiones = min(joint_limit, pct_limit)
            reduccion_planes_pensiones = max(0, reduccion_planes_pensiones)
            bi_general = max(0, bi_general - reduccion_planes_pensiones)

        # --- 3c. Rentas imputadas de inmuebles urbanos (Art. 85 LIRPF) ---
        # Owners of non-rented urban properties (other than primary residence) must
        # include 1.1% (if valor catastral revised post-1994) or 2% of valor catastral
        # as income in their general base BEFORE applying the general scale.
        renta_imputada_inmuebles = 0.0
        if valor_catastral_segundas_viviendas > 0:
            rate = 0.011 if valor_catastral_revisado_post1994 else 0.02
            renta_imputada_inmuebles = round(valor_catastral_segundas_viviendas * rate, 2)
            bi_general += renta_imputada_inmuebles

        # --- 3d. Tributación conjunta (Art. 84 LIRPF) ---
        # If filing jointly, reduce bi_general by:
        #   - 3.400 EUR for matrimonio
        #   - 2.150 EUR for monoparental
        # Applied AFTER pension plan reduction, BEFORE applying the general scale.
        reduccion_tributacion_conjunta = 0.0
        if tributacion_conjunta:
            if tipo_unidad_familiar == "monoparental":
                reduccion_tributacion_conjunta = 2150.0
            else:
                reduccion_tributacion_conjunta = 3400.0
            bi_general = max(0, bi_general - reduccion_tributacion_conjunta)

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
        ccaa_key = (
            "Estatal"
            if jurisdiction.lower() in ESTATAL_SCALE_JURISDICTIONS
            else jurisdiction
        )
        ccaa_scale = await self._irpf_calc._get_scale(ccaa_key, year)

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

        # --- 9. Deductions on cuota (applied after MPYF, before final) ---

        # 9a. Vivienda habitual pre-2013 (DT 18ª): 15% of max 9.040 EUR
        deduccion_vivienda_pre2013 = 0.0
        if hipoteca_pre2013:
            base_ded_viv = min(capital_amortizado_hipoteca + intereses_hipoteca, 9040)
            deduccion_vivienda_pre2013 = round(base_ded_viv * 0.15, 2)
            # Split 50/50 estatal/autonomica
            ded_viv_est = deduccion_vivienda_pre2013 / 2
            ded_viv_aut = deduccion_vivienda_pre2013 / 2
            cuota_liquida_est = max(0, cuota_liquida_est - ded_viv_est)
            cuota_liquida_aut = max(0, cuota_liquida_aut - ded_viv_aut)

        # 9b. Maternidad (Art. 81): 1.200 EUR/hijo <3 + 1.000 EUR guarderia
        deduccion_maternidad = 0.0
        if madre_trabajadora_ss and anios_nacimiento_desc:
            num_menores_3 = sum(1 for a in anios_nacimiento_desc if (year - a) < 3)
            if num_menores_3 > 0:
                deduccion_maternidad = 1200 * num_menores_3
                deduccion_maternidad += min(gastos_guarderia_anual, 1000 * num_menores_3)

        # 9c. Familia numerosa (Art. 81bis)
        deduccion_familia_numerosa = 0.0
        if familia_numerosa:
            deduccion_familia_numerosa = 2400 if tipo_familia_numerosa == "especial" else 1200

        # 9d. Donativos (Art. 68.3 + Ley 49/2002)
        deduccion_donativos = 0.0
        if donativos_ley_49_2002 > 0:
            first_250 = min(donativos_ley_49_2002, 250) * 0.80
            excess_rate = 0.45 if donativo_recurrente else 0.40
            excess = max(0, donativos_ley_49_2002 - 250) * excess_rate
            deduccion_donativos = round(first_250 + excess, 2)

        # 9e. Alquiler vivienda habitual pre-2015 (DT 15ª LIRPF)
        # 10.05% of rent paid (capped at 9.040 EUR base), only if BI < 24.107,20 EUR.
        # Full deduction up to BI 17.707,20 EUR, then linear reduction.
        # Note: alquiler_pagado_anual is rent paid by the taxpayer as tenant.
        # Apply to estatal half of cuota liquida only (50/50 split).
        deduccion_alquiler_pre2015 = 0.0
        if alquiler_habitual_pre2015 and alquiler_pagado_anual > 0:
            if bi_general < 24107.20:
                base_alq = min(alquiler_pagado_anual, 9040.0)
                if bi_general <= 17707.20:
                    deduccion_alquiler_pre2015 = round(base_alq * 0.1005, 2)
                else:
                    # Linear reduction from 17.707,20 to 24.107,20
                    factor = 1 - (bi_general - 17707.20) / (24107.20 - 17707.20)
                    deduccion_alquiler_pre2015 = round(base_alq * 0.1005 * factor, 2)
                # Apply only to the estatal half (50% of the deduction)
                ded_alq_est = deduccion_alquiler_pre2015 / 2
                cuota_liquida_est = max(0, cuota_liquida_est - ded_alq_est)

        # Apply cuota deductions
        # Donativos cannot reduce below zero; maternidad/familia numerosa CAN (refundable)
        cuota_liquida_general = cuota_liquida_est + cuota_liquida_aut
        cuota_liquida_general = max(0, cuota_liquida_general - deduccion_donativos)

        # --- 10. Total (before refundable deductions) ---
        cuota_total = cuota_liquida_general + cuota_ahorro
        # Maternidad + familia numerosa are refundable (can make cuota negative)
        cuota_total -= (deduccion_maternidad + deduccion_familia_numerosa)

        base_total = bi_general + base_ahorro
        tipo_medio = (cuota_total / base_total * 100) if base_total > 0 else 0.0

        # --- 11. Retenciones y pagos a cuenta (para resultado final) ---
        total_retenciones = (
            retenciones_alquiler
            + retenciones_ahorro
            + retenciones_actividad
            + pagos_fraccionados_130
        )
        cuota_diferencial = round(cuota_total - total_retenciones, 2)
        tipo_resultado = "a_pagar" if cuota_diferencial > 0 else "a_devolver"

        return {
            "success": True,
            "year": year,
            "jurisdiction": jurisdiction,
            "ceuta_melilla": ceuta_melilla,
            # Income breakdown
            "trabajo": trabajo_result,
            "actividad": actividad_result,
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
            # Phase 1: new deductions/reductions
            "reduccion_planes_pensiones": round(reduccion_planes_pensiones, 2),
            "deduccion_vivienda_pre2013": round(deduccion_vivienda_pre2013, 2),
            "deduccion_maternidad": round(deduccion_maternidad, 2),
            "deduccion_familia_numerosa": round(deduccion_familia_numerosa, 2),
            "deduccion_donativos": round(deduccion_donativos, 2),
            "total_deducciones_cuota": round(
                deduccion_vivienda_pre2013 + deduccion_maternidad
                + deduccion_familia_numerosa + deduccion_donativos
                + deduccion_alquiler_pre2015, 2
            ),
            # Phase 2: new reductions/deductions/imputations
            "reduccion_tributacion_conjunta": round(reduccion_tributacion_conjunta, 2),
            "deduccion_alquiler_pre2015": round(deduccion_alquiler_pre2015, 2),
            "renta_imputada_inmuebles": round(renta_imputada_inmuebles, 2),
            # Retenciones y resultado final
            "retenciones_actividad": round(retenciones_actividad, 2),
            "pagos_fraccionados_130": round(pagos_fraccionados_130, 2),
            "total_retenciones": round(total_retenciones, 2),
            "cuota_diferencial": cuota_diferencial,
            "tipo_resultado": tipo_resultado,
        }
