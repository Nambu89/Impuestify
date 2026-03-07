"""
Declaration Service — CRUD for quarterly tax declarations (Modelos 303, 130, 420).
"""
import json
import uuid
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeclarationService:
    def __init__(self, db):
        self._db = db

    async def save(
        self,
        *,
        user_id: str,
        declaration_type: str,  # "303", "130", "420"
        territory: str,
        year: int,
        quarter: int,
        form_data: Dict[str, Any],
        calculated_result: Dict[str, Any],
        status: str = "calculated",
    ) -> Dict[str, Any]:
        """Save or upsert a quarterly declaration."""
        # Check if exists
        existing = await self._db.execute(
            "SELECT id FROM quarterly_declarations WHERE user_id = ? AND declaration_type = ? AND year = ? AND quarter = ?",
            [user_id, declaration_type, year, quarter],
        )

        resultado = calculated_result.get("resultado_liquidacion", calculated_result.get("resultado", 0))

        if existing.rows:
            decl_id = existing.rows[0]["id"]
            await self._db.execute(
                """UPDATE quarterly_declarations
                   SET territory = ?, form_data = ?, calculated_result = ?,
                       total_income = ?, total_expenses = ?, net_income = ?,
                       tax_due = ?, status = ?, updated_at = datetime('now')
                   WHERE id = ?""",
                [
                    territory,
                    json.dumps(form_data),
                    json.dumps(calculated_result),
                    form_data.get("ingresos_acumulados", form_data.get("base_21", 0) + form_data.get("base_10", 0) + form_data.get("base_4", 0)),
                    form_data.get("gastos_acumulados", 0),
                    calculated_result.get("casillas", {}).get("03_rendimiento_neto", 0),
                    resultado,
                    status,
                    decl_id,
                ],
            )
        else:
            decl_id = str(uuid.uuid4())
            await self._db.execute(
                """INSERT INTO quarterly_declarations
                   (id, user_id, declaration_type, territory, year, quarter,
                    form_data, calculated_result, total_income, total_expenses,
                    net_income, tax_due, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    decl_id, user_id, declaration_type, territory, year, quarter,
                    json.dumps(form_data), json.dumps(calculated_result),
                    form_data.get("ingresos_acumulados", 0),
                    form_data.get("gastos_acumulados", 0),
                    calculated_result.get("casillas", {}).get("03_rendimiento_neto", 0),
                    resultado,
                    status,
                ],
            )

        return {"id": decl_id, "declaration_type": declaration_type, "year": year, "quarter": quarter, "status": status}

    async def get_by_year(self, user_id: str, year: int) -> List[Dict[str, Any]]:
        """Get all declarations for a user in a given year."""
        result = await self._db.execute(
            """SELECT id, declaration_type, territory, year, quarter,
                      total_income, total_expenses, net_income, tax_due,
                      status, source, created_at, updated_at
               FROM quarterly_declarations
               WHERE user_id = ? AND year = ?
               ORDER BY quarter, declaration_type""",
            [user_id, year],
        )
        return [dict(row) for row in result.rows]

    async def get_detail(self, user_id: str, declaration_id: str) -> Optional[Dict[str, Any]]:
        """Get full declaration detail including form_data and calculated_result."""
        result = await self._db.execute(
            """SELECT * FROM quarterly_declarations WHERE id = ? AND user_id = ?""",
            [declaration_id, user_id],
        )
        if not result.rows:
            return None
        row = dict(result.rows[0])
        row["form_data"] = json.loads(row["form_data"]) if row.get("form_data") else {}
        row["calculated_result"] = json.loads(row["calculated_result"]) if row.get("calculated_result") else {}
        return row

    async def get_quarter(self, user_id: str, year: int, quarter: int) -> List[Dict[str, Any]]:
        """Get all declarations for a specific quarter."""
        result = await self._db.execute(
            """SELECT * FROM quarterly_declarations
               WHERE user_id = ? AND year = ? AND quarter = ?
               ORDER BY declaration_type""",
            [user_id, year, quarter],
        )
        rows = []
        for row in result.rows:
            r = dict(row)
            r["form_data"] = json.loads(r["form_data"]) if r.get("form_data") else {}
            r["calculated_result"] = json.loads(r["calculated_result"]) if r.get("calculated_result") else {}
            rows.append(r)
        return rows

    async def delete(self, user_id: str, declaration_id: str) -> bool:
        """Delete a draft declaration."""
        result = await self._db.execute(
            "SELECT status FROM quarterly_declarations WHERE id = ? AND user_id = ?",
            [declaration_id, user_id],
        )
        if not result.rows:
            return False
        if result.rows[0]["status"] == "presented":
            return False  # Cannot delete presented declarations
        await self._db.execute(
            "DELETE FROM quarterly_declarations WHERE id = ? AND user_id = ?",
            [declaration_id, user_id],
        )
        return True

    async def get_accumulated(self, user_id: str, declaration_type: str, year: int, up_to_quarter: int) -> Dict[str, float]:
        """Get accumulated totals for quarters 1..up_to_quarter-1 (for Modelo 130 pagos_anteriores)."""
        result = await self._db.execute(
            """SELECT COALESCE(SUM(tax_due), 0) as total_paid,
                      COALESCE(SUM(total_income), 0) as total_income,
                      COALESCE(SUM(total_expenses), 0) as total_expenses
               FROM quarterly_declarations
               WHERE user_id = ? AND declaration_type = ? AND year = ? AND quarter < ?""",
            [user_id, declaration_type, year, up_to_quarter],
        )
        if result.rows:
            return dict(result.rows[0])
        return {"total_paid": 0, "total_income": 0, "total_expenses": 0}

    async def save_ml_features(self, user_id: str, year: int, quarter: int, features: Dict[str, Any]) -> None:
        """Upsert ML fiscal features for a quarter."""
        feat_id = str(uuid.uuid4())
        await self._db.execute(
            """INSERT INTO ml_fiscal_features
               (id, user_id, year, quarter, revenue, expenses, net_margin,
                vat_balance, irpf_payment, ss_contribution, retention_rate,
                territory, activity_sector, estimation_method, expense_ratio)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, year, quarter) DO UPDATE SET
                revenue = excluded.revenue, expenses = excluded.expenses,
                net_margin = excluded.net_margin, vat_balance = excluded.vat_balance,
                irpf_payment = excluded.irpf_payment, expense_ratio = excluded.expense_ratio""",
            [
                feat_id, user_id, year, quarter,
                features.get("revenue", 0), features.get("expenses", 0),
                features.get("net_margin", 0), features.get("vat_balance", 0),
                features.get("irpf_payment", 0), features.get("ss_contribution", 0),
                features.get("retention_rate", 0), features.get("territory"),
                features.get("activity_sector"), features.get("estimation_method"),
                features.get("expense_ratio", 0),
            ],
        )
