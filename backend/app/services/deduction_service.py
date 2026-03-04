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

        deductions = []
        for row in result.rows:
            d = dict(row)
            # Parse JSON fields
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
    ) -> Dict[str, Any]:
        """
        Evaluate which deductions a user is eligible for based on their answers.

        Args:
            territory: 'Estatal' or CCAA name
            tax_year: Fiscal year
            answers: Dict of user answers (key -> value)

        Returns:
            Dict with eligible, maybe_eligible, not_eligible deductions
            and estimated total savings
        """
        answers = answers or {}
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
    ) -> List[Dict[str, Any]]:
        """
        Get questions that still need to be answered to evaluate eligibility.

        Returns only questions for deductions that haven't been ruled out.
        """
        answers = answers or {}
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
