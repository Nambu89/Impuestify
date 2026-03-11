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
        # Ganancias patrimoniales del ahorro (casillas 0316-0354, 1813-1814)
        ganancias_acciones: float = 0,
        perdidas_acciones: float = 0,
        ganancias_reembolso_fondos: float = 0,
        perdidas_reembolso_fondos: float = 0,
        ganancias_derivados: float = 0,
        perdidas_derivados: float = 0,
        cripto_ganancia_neta: float = 0,
        cripto_perdida_neta: float = 0,
        jurisdiction: str = "Estatal",
        year: int = 2024,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate savings income and tax.

        Args:
            intereses: Bank account/deposit interest (casilla 0027).
            dividendos: Dividends and equity income (casilla 0029).
            ganancias_fondos: Fund/ETF capital gains as rendimientos (casilla 0031).
            otros_ahorro: Other savings income.
            gastos_administracion: Deductible admin/custody expenses.
            ganancias_acciones: Gross gains from share sales (casilla 0338).
            perdidas_acciones: Losses from share sales (casilla 0339).
            ganancias_reembolso_fondos: Gross gains from fund redemptions (casilla 0320).
            perdidas_reembolso_fondos: Losses from fund redemptions.
            ganancias_derivados: Gross gains from derivatives/CFDs/Forex (casilla 0353).
            perdidas_derivados: Losses from derivatives/CFDs/Forex (casilla 0354).
            cripto_ganancia_neta: Net crypto gains (casilla 1814).
            cripto_perdida_neta: Net crypto losses (casilla 1813).
            jurisdiction: CCAA for autonomous savings scale.
            year: Fiscal year.

        Returns:
            Dict with base_ahorro, cuota breakdown (estatal + autonomica),
            and ganancias_patrimoniales_netas breakdown.
        """
        # Rendimientos del capital mobiliario
        ingresos = intereses + dividendos + ganancias_fondos + otros_ahorro
        rendimiento_neto = max(0, ingresos - gastos_administracion)

        # Ganancias patrimoniales del ahorro (arts. 46 y 49 LIRPF)
        # Cada tipo compensa sus propias pérdidas; el neto total va a la base del ahorro
        neto_acciones = max(0, ganancias_acciones - perdidas_acciones)
        neto_fondos_reembolso = max(0, ganancias_reembolso_fondos - perdidas_reembolso_fondos)
        neto_derivados = max(0, ganancias_derivados - perdidas_derivados)
        neto_cripto = max(0, cripto_ganancia_neta - cripto_perdida_neta)
        ganancias_patrimoniales_netas = (
            neto_acciones + neto_fondos_reembolso + neto_derivados + neto_cripto
        )

        base_ahorro_total = rendimiento_neto + ganancias_patrimoniales_netas

        cuota_est = 0.0
        cuota_aut = 0.0
        bd_est: List[Dict] = []
        bd_aut: List[Dict] = []

        if base_ahorro_total > 0:
            state_scale = await self._get_ahorro_scale("Estatal", year)
            ccaa_scale = await self._get_ahorro_scale(jurisdiction, year)

            cuota_est, bd_est = self._apply_scale(base_ahorro_total, state_scale)
            if ccaa_scale:
                cuota_aut, bd_aut = self._apply_scale(base_ahorro_total, ccaa_scale)

        return {
            "base_ahorro": round(base_ahorro_total, 2),
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
            "ganancias_patrimoniales": {
                "neto_acciones": round(neto_acciones, 2),
                "neto_reembolso_fondos": round(neto_fondos_reembolso, 2),
                "neto_derivados": round(neto_derivados, 2),
                "neto_cripto": round(neto_cripto, 2),
                "total_neto": round(ganancias_patrimoniales_netas, 2),
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
