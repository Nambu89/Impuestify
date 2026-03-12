"""
Deduction Service for TaxIA.

Provides CRUD operations and eligibility evaluation for IRPF deductions.
"""
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeductionService:
    """Service for querying and evaluating IRPF deductions."""

    def __init__(self, db_client=None):
        self._db = db_client

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client
        self._db = await get_db_client()
        return self._db

    async def get_deductions(
        self,
        territory: str = "Estatal",
        tax_year: int = 2025,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get all active deductions for a territory and year.

        Args:
            territory: 'Estatal' or CCAA name
            tax_year: Fiscal year
            category: Optional filter by category

        Returns:
            List of deduction dicts
        """
        db = await self._get_db()

        if category:
            result = await db.execute(
                """SELECT * FROM deductions
                   WHERE territory = ? AND tax_year = ? AND category = ? AND is_active = 1
                   ORDER BY category, code""",
                [territory, tax_year, category],
            )
        else:
            result = await db.execute(
                """SELECT * FROM deductions
                   WHERE territory = ? AND tax_year = ? AND is_active = 1
                   ORDER BY category, code""",
                [territory, tax_year],
            )

        return self._parse_rows(result.rows)

    async def get_all_deductions(
        self,
        ccaa: str,
        tax_year: int = 2025,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get combined Estatal + CCAA deductions.

        For régimen común CCAA, returns both state-level and autonomous deductions.
        For foral territories (Araba, Bizkaia, Gipuzkoa, Navarra), returns ONLY
        the foral deductions since they have their own complete IRPF system.

        Args:
            ccaa: CCAA name (e.g. 'Madrid', 'Araba', 'Navarra')
            tax_year: Fiscal year
            category: Optional filter by category

        Returns:
            List of deduction dicts (combined)
        """
        foral_territories = {"Araba", "Bizkaia", "Gipuzkoa", "Navarra"}

        if ccaa in foral_territories:
            # Foral territories have their own complete system
            return await self.get_deductions(ccaa, tax_year, category)

        # Régimen común: combine Estatal + CCAA
        estatal = await self.get_deductions("Estatal", tax_year, category)
        ccaa_deductions = await self.get_deductions(ccaa, tax_year, category)
        return estatal + ccaa_deductions

    def _parse_rows(self, rows) -> List[Dict[str, Any]]:
        """Parse DB rows into deduction dicts with JSON fields."""
        deductions = []
        for row in rows:
            d = dict(row)
            if d.get("requirements_json"):
                d["requirements"] = json.loads(d["requirements_json"])
            else:
                d["requirements"] = {}
            if d.get("questions_json"):
                d["questions"] = json.loads(d["questions_json"])
            else:
                d["questions"] = []
            deductions.append(d)
        return deductions

    async def evaluate_eligibility(
        self,
        territory: str = "Estatal",
        tax_year: int = 2025,
        answers: Optional[Dict[str, Any]] = None,
        ccaa: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate which deductions a user is eligible for based on their answers.

        Args:
            territory: 'Estatal' or CCAA name (legacy, used if ccaa is None)
            tax_year: Fiscal year
            answers: Dict of user answers (key -> value)
            ccaa: If provided, uses get_all_deductions for combined results

        Returns:
            Dict with eligible, maybe_eligible, not_eligible deductions
            and estimated total savings
        """
        answers = answers or {}
        if ccaa:
            deductions = await self.get_all_deductions(ccaa, tax_year)
        else:
            deductions = await self.get_deductions(territory, tax_year)

        eligible = []
        maybe_eligible = []
        not_eligible = []

        for d in deductions:
            reqs = d.get("requirements", {})
            if not reqs:
                maybe_eligible.append(d)
                continue

            # Check each requirement against answers
            all_met = True
            any_unmet = False
            has_unanswered = False

            for req_key, req_value in reqs.items():
                user_answer = answers.get(req_key)
                if user_answer is None:
                    has_unanswered = True
                    all_met = False
                elif isinstance(req_value, bool):
                    if bool(user_answer) != req_value:
                        any_unmet = True
                        all_met = False

            if any_unmet:
                not_eligible.append(d)
            elif all_met:
                eligible.append(d)
            elif has_unanswered:
                maybe_eligible.append(d)

        # Estimate savings from eligible deductions
        estimated_savings = 0.0
        for d in eligible:
            if d.get("fixed_amount"):
                estimated_savings += d["fixed_amount"]
            elif d.get("max_amount") and d.get("percentage"):
                # Conservative: use max_amount as base, apply percentage
                estimated_savings += d["max_amount"] * d["percentage"] / 100

        return {
            "eligible": [self._summarize(d) for d in eligible],
            "maybe_eligible": [self._summarize(d) for d in maybe_eligible],
            "not_eligible": [self._summarize(d) for d in not_eligible],
            "estimated_savings": round(estimated_savings, 2),
            "total_deductions": len(deductions),
        }

    async def get_missing_questions(
        self,
        territory: str = "Estatal",
        tax_year: int = 2025,
        answers: Optional[Dict[str, Any]] = None,
        ccaa: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get questions that still need to be answered to evaluate eligibility.

        Returns only questions for deductions that haven't been ruled out.
        """
        answers = answers or {}
        if ccaa:
            deductions = await self.get_all_deductions(ccaa, tax_year)
        else:
            deductions = await self.get_deductions(territory, tax_year)

        seen_keys = set()
        missing_questions = []

        for d in deductions:
            reqs = d.get("requirements", {})

            # Skip if any requirement is explicitly not met
            skip = False
            for req_key, req_value in reqs.items():
                user_answer = answers.get(req_key)
                if user_answer is not None and isinstance(req_value, bool) and bool(user_answer) != req_value:
                    skip = True
                    break
            if skip:
                continue

            # Collect unanswered questions
            for q in d.get("questions", []):
                qkey = q.get("key")
                if qkey and qkey not in answers and qkey not in seen_keys:
                    seen_keys.add(qkey)
                    missing_questions.append({
                        "key": qkey,
                        "text": q.get("text", ""),
                        "type": q.get("type", "bool"),
                        "deduction_code": d["code"],
                        "deduction_name": d["name"],
                    })

        return missing_questions

    @staticmethod
    def build_answers_from_profile(profile: dict, ccaa: str = "") -> dict:
        """
        Map fiscal profile fields to deduction requirement keys.

        This allows the deduction engine to pre-populate answers automatically
        from the user's stored profile, so the agent does not need to ask for
        information that is already known.

        Args:
            profile: Flat dict of profile values (from datos_fiscales + top-level columns).
            ccaa: CCAA name (used for territory-specific answers).

        Returns:
            Dict of answer keys understood by evaluate_eligibility().
        """
        answers: Dict[str, Any] = {}

        # --- Derived boolean answers ---
        if (profile.get("num_descendientes", 0) or 0) > 0:
            answers["tiene_hijos"] = True

        # Ascendientes
        asc_65 = profile.get("num_ascendientes_65", 0) or 0
        asc_75 = profile.get("num_ascendientes_75", 0) or 0
        if asc_65 > 0 or asc_75 > 0:
            answers["ascendiente_a_cargo"] = True

        # Discapacidad contribuyente
        disc_pct = profile.get("discapacidad_contribuyente", 0) or 0
        if disc_pct >= 33:
            answers["discapacidad_reconocida"] = True

        # Familia numerosa
        if profile.get("familia_numerosa"):
            answers["familia_numerosa"] = True

        # Madre trabajadora (deduccion maternidad)
        if profile.get("madre_trabajadora_ss"):
            answers["madre_trabajadora"] = True

        # Age-based derivations (menor_35/36/40_anos)
        edad = profile.get("edad_contribuyente")
        if edad is not None:
            try:
                edad = int(edad)
                if edad <= 35:
                    answers["menor_35_anos"] = True
                    answers["menor_36_anos"] = True
                    answers["menor_40_anos"] = True
                elif edad <= 36:
                    answers["menor_35_anos"] = False
                    answers["menor_36_anos"] = True
                    answers["menor_40_anos"] = True
                elif edad <= 40:
                    answers["menor_35_anos"] = False
                    answers["menor_36_anos"] = False
                    answers["menor_40_anos"] = True
                else:
                    answers["menor_35_anos"] = False
                    answers["menor_36_anos"] = False
                    answers["menor_40_anos"] = False
            except (ValueError, TypeError):
                pass

        # Ceuta / Melilla residency
        if profile.get("ceuta_melilla") or ccaa in ("Ceuta", "Melilla"):
            answers["residente_ceuta_melilla"] = True

        # Hipoteca pre-2013
        if profile.get("hipoteca_pre2013"):
            answers["adquisicion_antes_2013"] = True
            answers["deducia_antes_2013"] = True  # conservative assumption

        # Planes de pensiones
        if (profile.get("aportaciones_plan_pensiones", 0) or 0) > 0 or \
           (profile.get("aportaciones_plan_pensiones_empresa", 0) or 0) > 0:
            answers["aportaciones_planes_pensiones"] = True

        # Donativo
        if (profile.get("donativos_ley_49_2002", 0) or 0) > 0:
            answers["donativo_a_entidad_acogida"] = True

        # Autonomo
        if profile.get("situacion_laboral") == "autonomo":
            estimacion = profile.get("metodo_estimacion_irpf", "") or ""
            if "directa" in estimacion:
                answers["autonomo_estimacion_directa"] = True

        # Criptomonedas (casillas 1800-1814)
        if profile.get("tiene_criptomonedas"):
            answers["tiene_criptomonedas"] = True
        if (profile.get("cripto_ganancia_neta", 0) or 0) > 0 or \
           (profile.get("cripto_perdida_neta", 0) or 0) > 0:
            answers["tiene_ganancias_cripto"] = True

        # Ganancias patrimoniales financieras
        if profile.get("tiene_acciones"):
            answers["tiene_acciones"] = True
        if profile.get("tiene_fondos_inversion"):
            answers["tiene_fondos_inversion"] = True
        if profile.get("tiene_derivados"):
            answers["tiene_derivados"] = True

        # --- Direct 1:1 boolean mappings ---
        DIRECT_MAPPINGS = [
            "alquiler_vivienda_habitual",
            "vivienda_habitual_propiedad",
            "nacimiento_adopcion_reciente",
            "adopcion_internacional",
            "acogimiento_familiar",
            "familia_monoparental",
            "descendiente_discapacidad",
            "ascendiente_discapacidad",
            "hijos_escolarizados",
            "vehiculo_electrico_nuevo",
            "obras_mejora_energetica",
            "municipio_despoblado",
            "rehabilitacion_vivienda",
            "inversion_empresa_nueva",
            "instalacion_renovable",
            "gastos_guarderia",
            "ambos_progenitores_trabajan",
            "hijos_estudios_universitarios",
            "donativo_entidad_autonomica",
            "donativo_investigacion",
            "donativo_patrimonio",
            "donativo_fundacion_local",
            "familiar_discapacitado_cargo",
            "empleada_hogar_cuidado",
            "dacion_pago_alquiler",
            "arrendador_vivienda_social",
            "vivienda_rural",
            # Foral
            "pension_viudedad",
            "reduccion_jornada_cuidado",
            # Legacy keys (kept for compatibility with existing deduction requirements)
            "tarifa_plana",
            "pluriactividad",
            "territorio_foral",
            # Crypto / trading (new — direct boolean passthrough)
            "tiene_criptomonedas",
            "tiene_acciones",
            "tiene_fondos_inversion",
            "tiene_derivados",
            "tiene_ganancias_juegos_privados",
            "tiene_premios_loterias",
            "cripto_en_extranjero_50k",
            "tiene_staking_defi",
        ]
        for key in DIRECT_MAPPINGS:
            val = profile.get(key)
            if val is True:
                answers[key] = True
            elif val is False:
                answers[key] = False

        return answers

    def compute_ccaa_deduction_amounts(
        self,
        eligible: List[Dict[str, Any]],
        user_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Compute exact EUR amounts for eligible CCAA deductions.

        Takes eligible deductions (from evaluate_eligibility) and the user's
        financial data to compute exact deduction amounts. Only computes
        CCAA/territorial deductions (scope != 'estatal'), since estatal
        deductions are already handled by the simulator.

        Args:
            eligible: List of eligible deduction dicts (from evaluate_eligibility).
            user_data: Dict with user financial data:
                - alquiler_pagado_anual: Annual rent paid
                - edad_contribuyente: Taxpayer age
                - num_descendientes: Number of children
                - anios_nacimiento_desc: Birth years of children
                - donativos_autonomicos: Donations to CCAA entities
                - gastos_guarderia_anual: Annual childcare expenses
                - gastos_educativos: Educational expenses
                - base_imponible: Approximate gross income (for threshold checks)
                - inversion_vivienda: Housing investment amount
                - instalacion_renovable_importe: Renewable energy investment
                - vehiculo_electrico_importe: Electric vehicle purchase amount
                - obras_mejora_importe: Energy improvement works amount
                - cotizaciones_empleada_hogar: Domestic employee SS contributions

        Returns:
            List of {code, name, amount, description} dicts for applied deductions.
        """
        results = []
        alquiler = user_data.get("alquiler_pagado_anual", 0) or 0
        edad = user_data.get("edad_contribuyente", 35) or 35
        num_desc = user_data.get("num_descendientes", 0) or 0
        nacimientos = user_data.get("anios_nacimiento_desc", []) or []
        donativos_aut = user_data.get("donativos_autonomicos", 0) or 0
        guarderia = user_data.get("gastos_guarderia_anual", 0) or 0
        gastos_educ = user_data.get("gastos_educativos", 0) or 0
        bi = user_data.get("base_imponible", 0) or 0
        inversion_viv = user_data.get("inversion_vivienda", 0) or 0
        renovable = user_data.get("instalacion_renovable_importe", 0) or 0
        vehiculo_elec = user_data.get("vehiculo_electrico_importe", 0) or 0
        obras_mejora = user_data.get("obras_mejora_importe", 0) or 0
        cotiz_empleada = user_data.get("cotizaciones_empleada_hogar", 0) or 0
        year = user_data.get("year", 2025)

        for d in eligible:
            # Skip estatal deductions — handled by simulator
            scope = d.get("scope", d.get("territory", ""))
            if scope == "Estatal" or d.get("code", "").startswith("EST-"):
                continue

            code = d.get("code", "")
            name = d.get("name", "")
            fixed = d.get("fixed_amount") or 0
            pct = d.get("percentage") or 0
            max_amt = d.get("max_amount") or 0
            amount = 0.0

            # --- Fixed-amount deductions (nacimiento, familia numerosa, etc.) ---
            if fixed > 0 and pct == 0:
                amount = fixed

            # --- Percentage-based deductions (need user data to compute) ---
            elif pct > 0:
                # Rent deductions (alquiler vivienda habitual)
                if "ALQUILER" in code or "ARRENDAMIENTO" in code:
                    if alquiler > 0:
                        base = alquiler
                        if max_amt > 0:
                            # max_amount is the cap on the DEDUCTION, not the base
                            amount = min(alquiler * pct / 100, max_amt)
                        else:
                            amount = alquiler * pct / 100

                # Housing investment / purchase
                elif "VIV-JOVEN" in code or "VIV-HABITUAL" in code or "ADQUISICION-VIV" in code or "COMPRA-VIV" in code or "VIV-RURAL" in code:
                    if inversion_viv > 0:
                        base = min(inversion_viv, max_amt) if max_amt > 0 else inversion_viv
                        amount = base * pct / 100

                # Childcare (guarderia)
                elif "GUARDERIA" in code or "CUIDADO-HIJOS" in code:
                    if guarderia > 0:
                        base = guarderia
                        if max_amt > 0:
                            amount = min(base * pct / 100, max_amt)
                        else:
                            amount = base * pct / 100

                # Educational expenses
                elif "GASTOS-EDUC" in code or "LIBROS" in code or "MAT-ESCOLAR" in code:
                    if gastos_educ > 0:
                        base = gastos_educ
                        if max_amt > 0:
                            amount = min(base * pct / 100, max_amt)
                        else:
                            amount = base * pct / 100

                # Donations
                elif "DONAT" in code or "DONAC" in code:
                    if donativos_aut > 0:
                        base = donativos_aut
                        if max_amt > 0:
                            amount = min(base * pct / 100, max_amt)
                        else:
                            amount = base * pct / 100

                # Renewable energy installations
                elif "RENOVABLE" in code or "SOSTENIBILIDAD" in code or "FOTOVOLT" in code:
                    if renovable > 0:
                        base = renovable
                        if max_amt > 0:
                            amount = min(base * pct / 100, max_amt)
                        else:
                            amount = base * pct / 100

                # Electric vehicle
                elif "VEH-ELEC" in code or "BICI" in code:
                    if vehiculo_elec > 0:
                        base = vehiculo_elec
                        if max_amt > 0:
                            amount = min(base * pct / 100, max_amt)
                        else:
                            amount = base * pct / 100

                # Energy improvement works (rehabilitacion)
                elif "REHAB" in code or "OBRAS-MEJORA" in code or "MEDIOAMBIENTE" in code:
                    if obras_mejora > 0:
                        base = min(obras_mejora, max_amt) if max_amt > 0 else obras_mejora
                        amount = base * pct / 100

                # Domestic employee (empleada hogar)
                elif "CUIDADO-HIJOS" in code or "AYUDA-DOMESTICA" in code or "EMPLEADA" in code:
                    if cotiz_empleada > 0:
                        base = cotiz_empleada
                        if max_amt > 0:
                            amount = min(base * pct / 100, max_amt)
                        else:
                            amount = base * pct / 100

                # Enterprise investment
                elif "INVERSION-EMPRESA" in code:
                    # Use max_amount as conservative estimate
                    if max_amt > 0:
                        amount = max_amt

                # Generic percentage-based: compute from max_amount as base
                else:
                    if max_amt > 0:
                        amount = max_amt * pct / 100
                    elif pct > 0:
                        # Cannot compute without a base — skip
                        continue

            # Skip zero amounts
            if amount <= 0:
                continue

            results.append({
                "code": code,
                "name": name,
                "amount": round(amount, 2),
                "percentage": pct,
                "max_amount": max_amt,
                "fixed_amount": fixed,
            })

        return results

    def _summarize(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary dict for a deduction (without internal fields)."""
        summary = {
            "code": d["code"],
            "name": d["name"],
            "type": d["type"],
            "category": d["category"],
            "legal_reference": d.get("legal_reference", ""),
            "description": d.get("description", ""),
        }
        if d.get("percentage"):
            summary["percentage"] = d["percentage"]
        if d.get("max_amount"):
            summary["max_amount"] = d["max_amount"]
        if d.get("fixed_amount"):
            summary["fixed_amount"] = d["fixed_amount"]
        return summary


# Singleton
_deduction_service: Optional[DeductionService] = None


def get_deduction_service(db_client=None) -> DeductionService:
    """Get global DeductionService instance."""
    global _deduction_service
    if _deduction_service is None:
        _deduction_service = DeductionService(db_client)
    return _deduction_service
