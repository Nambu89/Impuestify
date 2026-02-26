"""
Savings Income Calculator — Rendimientos del Capital Mobiliario del Ahorro.

XSD Modelo 100 casillas: B11 (0027) → B1RNR (0040).

Calculates:
- Total savings income (interests, dividends, fund gains)
- Net savings income after expenses
- Applies the savings tax scale (tarifa del ahorro, LIRPF art. 66)
"""
from typing import Any, Dict, List

from app.utils.tax_parameter_repository import TaxParameterRepository


class SavingsIncomeCalculator:
    """Calculates savings income and applies the savings tax scale."""

    def __init__(self, repo: TaxParameterRepository, db):
        self._repo = repo
        self._db = db

    async def calculate(
        self,
        *,
        intereses: float = 0,
        dividendos: float = 0,
        ganancias_fondos: float = 0,
        otros_ahorro: float = 0,
        gastos_administracion: float = 0,
        jurisdiction: str = "Estatal",
        year: int = 2024,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate savings income and tax.

        Args:
            intereses: Bank account/deposit interest (casilla 0027).
            dividendos: Dividends and equity income (casilla 0029).
            ganancias_fondos: Fund/ETF capital gains (casilla 0031).
            otros_ahorro: Other savings income.
            gastos_administracion: Deductible admin/custody expenses.
            jurisdiction: CCAA for autonomous savings scale.
            year: Fiscal year.

        Returns:
            Dict with base_ahorro, cuota breakdown (estatal + autonomica).
        """
        ingresos = intereses + dividendos + ganancias_fondos + otros_ahorro
        rendimiento_neto = max(0, ingresos - gastos_administracion)

        cuota_est = 0.0
        cuota_aut = 0.0
        bd_est: List[Dict] = []
        bd_aut: List[Dict] = []

        if rendimiento_neto > 0:
            state_scale = await self._get_ahorro_scale("Estatal", year)
            ccaa_scale = await self._get_ahorro_scale(jurisdiction, year)

            cuota_est, bd_est = self._apply_scale(rendimiento_neto, state_scale)
            if ccaa_scale:
                cuota_aut, bd_aut = self._apply_scale(rendimiento_neto, ccaa_scale)

        return {
            "base_ahorro": round(rendimiento_neto, 2),
            "cuota_ahorro_estatal": round(cuota_est, 2),
            "cuota_ahorro_autonomica": round(cuota_aut, 2),
            "cuota_ahorro_total": round(cuota_est + cuota_aut, 2),
            "desglose_ingresos": {
                "intereses": round(intereses, 2),
                "dividendos": round(dividendos, 2),
                "ganancias_fondos": round(ganancias_fondos, 2),
                "otros": round(otros_ahorro, 2),
                "gastos": round(gastos_administracion, 2),
            },
            "breakdown": {"estatal": bd_est, "autonomica": bd_aut},
        }

    async def _get_ahorro_scale(self, jurisdiction: str, year: int) -> List[Dict]:
        """Get savings tax scale from irpf_scales table."""
        result = await self._db.execute(
            "SELECT tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable "
            "FROM irpf_scales "
            "WHERE jurisdiction = ? AND year = ? AND scale_type = 'ahorro' "
            "ORDER BY tramo_num",
            [jurisdiction, year],
        )
        return [dict(row) for row in result.rows]

    @staticmethod
    def _apply_scale(base: float, scale: List[Dict]) -> tuple:
        """
        Apply progressive savings tax scale.

        Same algorithm as IRPFCalculator._apply_scale but self-contained
        to avoid circular dependency.
        """
        cuota_total = 0.0
        breakdown = []

        for i, tramo in enumerate(scale):
            base_hasta = tramo["base_hasta"]
            cuota_integra = tramo["cuota_integra"]
            tipo_aplicable = tramo["tipo_aplicable"]
            base_desde = 0 if i == 0 else scale[i - 1]["base_hasta"]

            if base <= base_hasta or base_hasta >= 999999:
                base_en_tramo = base - base_desde
                cuota_en_tramo = base_en_tramo * (tipo_aplicable / 100)
                cuota_total = cuota_integra + cuota_en_tramo
                breakdown.append({
                    "tramo": i + 1,
                    "base_desde": round(base_desde, 2),
                    "base_hasta": round(base_hasta, 2) if base_hasta < 999999 else "En adelante",
                    "base_gravada": round(base_en_tramo, 2),
                    "tipo": tipo_aplicable,
                    "cuota": round(cuota_en_tramo, 2),
                })
                break
            else:
                resto_base = tramo["resto_base"]
                cuota_en_tramo = resto_base * (tipo_aplicable / 100)
                breakdown.append({
                    "tramo": i + 1,
                    "base_desde": round(base_desde, 2),
                    "base_hasta": round(base_hasta, 2),
                    "base_gravada": round(resto_base, 2),
                    "tipo": tipo_aplicable,
                    "cuota": round(cuota_en_tramo, 2),
                })

        return cuota_total, breakdown
