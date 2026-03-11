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
