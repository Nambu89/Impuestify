"""
IRPF Annual Projector -- Extrapolates quarterly data to project annual IRPF.

Takes quarterly declarations (Modelos 130/303/420) stored in the DB and:
1. Aggregates income/expenses from completed quarters.
2. Annualizes by extrapolating to 4 quarters.
3. Feeds the annualized data into IRPFSimulator for a full IRPF projection.
4. Optionally persists the projection in `annual_projections`.

This bridges the gap between quarterly filings and the annual Modelo 100 (IRPF).

Usage:
    projector = IRPFProjector(db)
    result = await projector.project(user_id="...", year=2025)
"""
import json
import uuid
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IRPFProjector:
    """
    Projects annual IRPF from quarterly declaration data.

    Strategy:
      - Reads all Modelo 130 rows for the year (direct IRPF quarterly data).
      - Reads all Modelo 303/420 rows for IVA/IGIC context (income volumes).
      - Calculates totals from available quarters, then annualizes.
      - Calls IRPFSimulator with the projected annual figures.
    """

    def __init__(self, db):
        self._db = db

    async def project(
        self,
        *,
        user_id: str,
        year: int = 2025,
        jurisdiction: str = "Madrid",
        # Optional overrides (from user profile or manual input)
        edad_contribuyente: int = 35,
        num_descendientes: int = 0,
        anios_nacimiento_desc: Optional[List[int]] = None,
        custodia_compartida: bool = False,
        num_ascendientes_65: int = 0,
        num_ascendientes_75: int = 0,
        discapacidad_contribuyente: int = 0,
        ceuta_melilla: bool = False,
        estimacion_actividad: str = "directa_simplificada",
        inicio_actividad: bool = False,
        un_solo_cliente: bool = False,
        # Phase 1/2 params from profile
        aportaciones_plan_pensiones: float = 0,
        hipoteca_pre2013: bool = False,
        capital_amortizado_hipoteca: float = 0,
        intereses_hipoteca: float = 0,
        madre_trabajadora_ss: bool = False,
        gastos_guarderia_anual: float = 0,
        familia_numerosa: bool = False,
        tipo_familia_numerosa: str = "general",
        donativos_ley_49_2002: float = 0,
        donativo_recurrente: bool = False,
        tributacion_conjunta: bool = False,
        tipo_unidad_familiar: str = "matrimonio",
        # Additional income not in quarterly declarations
        ingresos_trabajo: float = 0,
        ss_empleado: float = 0,
        intereses: float = 0,
        dividendos: float = 0,
        ganancias_fondos: float = 0,
        ingresos_alquiler: float = 0,
        gastos_alquiler_total: float = 0,
        retenciones_alquiler: float = 0,
        retenciones_ahorro: float = 0,
        # Control
        save_projection: bool = True,
    ) -> Dict[str, Any]:
        """
        Project annual IRPF from quarterly declarations.

        Args:
            user_id: User ID to query declarations for.
            year: Fiscal year to project.
            jurisdiction: CCAA for tax scales (from user profile).
            save_projection: If True, persist the projection in annual_projections.
            ... other args: Passed through to IRPFSimulator for deductions/family.

        Returns:
            Dict with:
            - quarterly_data: summary of quarters found
            - annualized: extrapolated annual figures
            - projection: full IRPFSimulator result
            - confidence: "high" (4Q), "medium" (2-3Q), "low" (1Q), "no_data" (0Q)
        """
        # --- 1. Fetch quarterly declarations ---
        modelo_130_data = await self._fetch_declarations(user_id, "130", year)
        modelo_303_data = await self._fetch_declarations(user_id, "303", year)
        modelo_420_data = await self._fetch_declarations(user_id, "420", year)

        quarters_130 = [d["quarter"] for d in modelo_130_data]
        quarters_303 = [d["quarter"] for d in modelo_303_data]
        quarters_420 = [d["quarter"] for d in modelo_420_data]

        num_quarters = len(quarters_130) or len(quarters_303) or len(quarters_420)

        # --- 2. Extract and aggregate quarterly figures ---
        activity = self._aggregate_activity_income(modelo_130_data)
        iva_data = self._aggregate_iva(modelo_303_data, modelo_420_data)

        # --- 3. Annualize ---
        annualized = self._annualize(activity, num_quarters)

        # Determine confidence
        if num_quarters == 0:
            confidence = "no_data"
        elif num_quarters == 1:
            confidence = "low"
        elif num_quarters <= 3:
            confidence = "medium"
        else:
            confidence = "high"

        # --- 4. Run IRPFSimulator ---
        from app.utils.irpf_simulator import IRPFSimulator
        simulator = IRPFSimulator(self._db)

        # Sum pagos fraccionados (Modelo 130) already paid
        total_pagos_130 = sum(
            d.get("tax_due", 0) or 0 for d in modelo_130_data
        )

        # Retenciones from activity (accumulated from last quarter's 130)
        retenciones_actividad = 0.0
        if modelo_130_data:
            last_130 = max(modelo_130_data, key=lambda d: d["quarter"])
            last_result = last_130.get("calculated_result", {})
            if isinstance(last_result, str):
                last_result = json.loads(last_result)
            # In Comun territory, retenciones_acumuladas is in form_data
            last_form = last_130.get("form_data", {})
            if isinstance(last_form, str):
                last_form = json.loads(last_form)
            retenciones_actividad = last_form.get("retenciones_acumuladas", 0)

        # Annualize retenciones proportionally
        if num_quarters > 0 and num_quarters < 4:
            retenciones_actividad = retenciones_actividad * 4 / num_quarters

        # Cuota autonomo from 130 form_data (gastos include SS)
        cuota_autonomo_anual = annualized.get("cuota_autonomo_anual", 0)

        projection = await simulator.simulate(
            jurisdiction=jurisdiction,
            year=year,
            ceuta_melilla=ceuta_melilla,
            # Work income (passed directly, not from quarterly)
            ingresos_trabajo=ingresos_trabajo,
            ss_empleado=ss_empleado,
            # Activity income (from quarterly data)
            ingresos_actividad=annualized.get("ingresos", 0),
            gastos_actividad=annualized.get("gastos", 0),
            cuota_autonomo_anual=cuota_autonomo_anual,
            estimacion_actividad=estimacion_actividad,
            inicio_actividad=inicio_actividad,
            un_solo_cliente=un_solo_cliente,
            retenciones_actividad=round(retenciones_actividad, 2),
            pagos_fraccionados_130=round(total_pagos_130, 2),
            # Savings
            intereses=intereses,
            dividendos=dividendos,
            ganancias_fondos=ganancias_fondos,
            # Rental
            ingresos_alquiler=ingresos_alquiler,
            gastos_alquiler_total=gastos_alquiler_total,
            retenciones_alquiler=retenciones_alquiler,
            retenciones_ahorro=retenciones_ahorro,
            # Family
            edad_contribuyente=edad_contribuyente,
            num_descendientes=num_descendientes,
            anios_nacimiento_desc=anios_nacimiento_desc,
            custodia_compartida=custodia_compartida,
            num_ascendientes_65=num_ascendientes_65,
            num_ascendientes_75=num_ascendientes_75,
            discapacidad_contribuyente=discapacidad_contribuyente,
            # Deductions
            aportaciones_plan_pensiones=aportaciones_plan_pensiones,
            hipoteca_pre2013=hipoteca_pre2013,
            capital_amortizado_hipoteca=capital_amortizado_hipoteca,
            intereses_hipoteca=intereses_hipoteca,
            madre_trabajadora_ss=madre_trabajadora_ss,
            gastos_guarderia_anual=gastos_guarderia_anual,
            familia_numerosa=familia_numerosa,
            tipo_familia_numerosa=tipo_familia_numerosa,
            donativos_ley_49_2002=donativos_ley_49_2002,
            donativo_recurrente=donativo_recurrente,
            tributacion_conjunta=tributacion_conjunta,
            tipo_unidad_familiar=tipo_unidad_familiar,
        )

        result = {
            "quarterly_data": {
                "quarters_130": quarters_130,
                "quarters_303": quarters_303,
                "quarters_420": quarters_420,
                "num_quarters_activity": len(quarters_130),
                "total_pagos_130": round(total_pagos_130, 2),
                "retenciones_actividad_anualizadas": round(retenciones_actividad, 2),
            },
            "annualized": annualized,
            "iva_summary": iva_data,
            "projection": projection,
            "confidence": confidence,
            "year": year,
            "jurisdiction": jurisdiction,
        }

        # --- 5. Persist projection ---
        if save_projection and num_quarters > 0:
            await self._save_projection(user_id, year, result)

        return result

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    async def _fetch_declarations(
        self, user_id: str, declaration_type: str, year: int
    ) -> List[Dict[str, Any]]:
        """Fetch all declarations of a type for a user/year."""
        result = await self._db.execute(
            """SELECT quarter, form_data, calculated_result, tax_due,
                      total_income, total_expenses, territory
               FROM quarterly_declarations
               WHERE user_id = ? AND declaration_type = ? AND year = ?
               ORDER BY quarter""",
            [user_id, declaration_type, year],
        )
        rows = []
        for row in result.rows:
            r = dict(row)
            for field in ("form_data", "calculated_result"):
                if r.get(field) and isinstance(r[field], str):
                    try:
                        r[field] = json.loads(r[field])
                    except (json.JSONDecodeError, TypeError):
                        r[field] = {}
            rows.append(r)
        return rows

    def _aggregate_activity_income(
        self, modelo_130_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Extract activity income/expenses from Modelo 130 declarations.

        For Comun territory, 130 uses accumulated figures (ingresos_acumulados,
        gastos_acumulados), so the last quarter has the year-to-date totals.

        For foral territories (Araba), 130 uses per-quarter figures
        (ingresos_trimestre, gastos_trimestre), so we must sum them.
        """
        if not modelo_130_data:
            return {"ingresos": 0, "gastos": 0, "cuota_autonomo_anual": 0,
                    "rendimiento_neto": 0, "num_quarters": 0}

        last_decl = max(modelo_130_data, key=lambda d: d["quarter"])
        territory = last_decl.get("territory", "Comun")
        form = last_decl.get("form_data", {})
        if isinstance(form, str):
            try:
                form = json.loads(form)
            except (json.JSONDecodeError, TypeError):
                form = {}

        # Check if it's a territory that uses per-quarter data
        foral_trimestral = territory in ("Araba",)

        if foral_trimestral:
            # Sum per-quarter figures
            total_ingresos = 0
            total_gastos = 0
            for d in modelo_130_data:
                fd = d.get("form_data", {})
                if isinstance(fd, str):
                    try:
                        fd = json.loads(fd)
                    except (json.JSONDecodeError, TypeError):
                        fd = {}
                total_ingresos += fd.get("ingresos_trimestre", 0) or 0
                total_gastos += fd.get("gastos_trimestre", 0) or 0
        else:
            # Comun: use accumulated from the last quarter
            total_ingresos = form.get("ingresos_acumulados", 0) or 0
            total_gastos = form.get("gastos_acumulados", 0) or 0

        # Cuota autonomo: estimate from gastos if not explicit
        # Typically SS autonomo is a significant portion of gastos_acumulados
        # but it's better to get it from the profile. Default: 0
        cuota_autonomo = 0.0

        return {
            "ingresos": total_ingresos,
            "gastos": total_gastos,
            "cuota_autonomo_anual": cuota_autonomo,
            "rendimiento_neto": total_ingresos - total_gastos,
            "num_quarters": len(modelo_130_data),
        }

    def _aggregate_iva(
        self,
        modelo_303_data: List[Dict[str, Any]],
        modelo_420_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Aggregate IVA/IGIC data for informational purposes."""
        total_devengado = 0.0
        total_deducible = 0.0

        for decl in modelo_303_data:
            result = decl.get("calculated_result", {})
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    result = {}
            total_devengado += result.get("total_devengado", 0) or 0
            total_deducible += result.get("total_deducible", 0) or 0

        for decl in modelo_420_data:
            result = decl.get("calculated_result", {})
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except (json.JSONDecodeError, TypeError):
                    result = {}
            total_devengado += result.get("total_devengado", 0) or 0
            total_deducible += result.get("total_deducible", 0) or 0

        return {
            "total_iva_devengado": round(total_devengado, 2),
            "total_iva_deducible": round(total_deducible, 2),
            "saldo_iva": round(total_devengado - total_deducible, 2),
            "num_quarters_303": len(modelo_303_data),
            "num_quarters_420": len(modelo_420_data),
        }

    def _annualize(
        self, activity: Dict[str, float], num_quarters: int
    ) -> Dict[str, Any]:
        """
        Annualize activity income from partial year data.

        If 2 quarters of data: multiply by 2.
        If 3 quarters: multiply by 4/3.
        If 4 quarters: already annual.
        If 0: all zeros.
        """
        if num_quarters == 0:
            return {
                "ingresos": 0, "gastos": 0, "rendimiento_neto": 0,
                "cuota_autonomo_anual": 0, "factor": 0,
                "nota": "Sin datos trimestrales disponibles",
            }

        # The activity data already represents year-to-date totals
        # (for Comun) or summed quarters (for foral).
        # We need to scale to a full year.
        factor = 4 / num_quarters if num_quarters < 4 else 1.0

        return {
            "ingresos": round(activity["ingresos"] * factor, 2),
            "gastos": round(activity["gastos"] * factor, 2),
            "rendimiento_neto": round(activity["rendimiento_neto"] * factor, 2),
            "cuota_autonomo_anual": round(activity["cuota_autonomo_anual"] * factor, 2),
            "factor": round(factor, 4),
            "nota": (
                "Datos completos (4 trimestres)" if num_quarters == 4
                else f"Extrapolado desde {num_quarters} trimestre(s) (factor x{factor:.2f})"
            ),
        }

    async def _save_projection(
        self, user_id: str, year: int, result: Dict[str, Any]
    ) -> None:
        """Persist the annual projection in the annual_projections table."""
        projection = result.get("projection", {})
        annualized = result.get("annualized", {})
        num_quarters = result["quarterly_data"]["num_quarters_activity"]

        input_summary = json.dumps({
            "quarterly_data": result["quarterly_data"],
            "annualized": annualized,
            "iva_summary": result["iva_summary"],
        })

        projection_detail = json.dumps(projection)

        projected_income = annualized.get("ingresos", 0)
        projected_expenses = annualized.get("gastos", 0)
        projected_net = annualized.get("rendimiento_neto", 0)
        projected_irpf = projection.get("cuota_total", 0)
        projected_payments = projection.get("total_retenciones", 0)
        projected_differential = projection.get("cuota_diferencial", 0)
        effective_rate = projection.get("tipo_medio", 0)

        # Confidence as float: high=0.95, medium=0.7, low=0.4, no_data=0
        confidence_map = {"high": 0.95, "medium": 0.7, "low": 0.4, "no_data": 0.0}
        confidence_val = confidence_map.get(result["confidence"], 0.5)

        # Check for existing projection with same quarters_available
        existing = await self._db.execute(
            "SELECT id FROM annual_projections WHERE user_id = ? AND year = ? AND quarters_available = ?",
            [user_id, year, num_quarters],
        )

        if existing.rows:
            proj_id = existing.rows[0]["id"]
            await self._db.execute(
                """UPDATE annual_projections
                   SET input_summary = ?, projected_income = ?,
                       projected_expenses = ?, projected_net_income = ?,
                       projected_irpf = ?, projected_payments = ?,
                       projected_differential = ?, effective_rate = ?,
                       projection_detail = ?, confidence = ?,
                       calculated_at = datetime('now')
                   WHERE id = ?""",
                [
                    input_summary, projected_income, projected_expenses,
                    projected_net, projected_irpf, projected_payments,
                    projected_differential, effective_rate,
                    projection_detail, confidence_val, proj_id,
                ],
            )
            logger.info("Updated annual projection %s for user %s year %d",
                        proj_id, user_id, year)
        else:
            proj_id = str(uuid.uuid4())
            await self._db.execute(
                """INSERT INTO annual_projections
                   (id, user_id, year, quarters_available, input_summary,
                    projected_income, projected_expenses, projected_net_income,
                    projected_irpf, projected_payments, projected_differential,
                    effective_rate, projection_detail, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    proj_id, user_id, year, num_quarters, input_summary,
                    projected_income, projected_expenses, projected_net,
                    projected_irpf, projected_payments, projected_differential,
                    effective_rate, projection_detail, confidence_val,
                ],
            )
            logger.info("Created annual projection %s for user %s year %d",
                        proj_id, user_id, year)
