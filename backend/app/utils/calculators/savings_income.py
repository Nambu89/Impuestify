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
        # --- 1. Rendimientos del capital mobiliario (Art. 25 LIRPF) ---
        ingresos = intereses + dividendos + ganancias_fondos + otros_ahorro
        rendimiento_neto_rcm = ingresos - gastos_administracion  # Can be negative

        # --- 2. Ganancias patrimoniales del ahorro (Art. 46, 49 LIRPF) ---
        # All gains and losses are NETTED TOGETHER across sub-types (not individually).
        # Per Art. 49.1.b: "se compensarán entre sí" within ganancias patrimoniales.
        total_ganancias = (
            ganancias_acciones + ganancias_reembolso_fondos
            + ganancias_derivados + cripto_ganancia_neta
        )
        total_perdidas = (
            perdidas_acciones + perdidas_reembolso_fondos
            + perdidas_derivados + cripto_perdida_neta
        )
        ganancias_patrimoniales_netas = total_ganancias - total_perdidas

        # Per-type netos (for reporting only)
        neto_acciones = ganancias_acciones - perdidas_acciones
        neto_fondos_reembolso = ganancias_reembolso_fondos - perdidas_reembolso_fondos
        neto_derivados = ganancias_derivados - perdidas_derivados
        neto_cripto = cripto_ganancia_neta - cripto_perdida_neta

        # --- 3. Cross-compensation Art. 49 LIRPF (regla del 25%) ---
        # If one category has net loss and the other has net gain,
        # the loss can compensate up to 25% of the positive balance in the other.
        compensacion_rcm_en_gp = 0.0
        compensacion_gp_en_rcm = 0.0

        if rendimiento_neto_rcm < 0 and ganancias_patrimoniales_netas > 0:
            # RCM losses compensate up to 25% of GP gains
            max_comp = ganancias_patrimoniales_netas * 0.25
            compensacion_rcm_en_gp = min(abs(rendimiento_neto_rcm), max_comp)
            rendimiento_neto_rcm += compensacion_rcm_en_gp  # becomes less negative or 0
            ganancias_patrimoniales_netas -= compensacion_rcm_en_gp
        elif ganancias_patrimoniales_netas < 0 and rendimiento_neto_rcm > 0:
            # GP losses compensate up to 25% of RCM gains
            max_comp = rendimiento_neto_rcm * 0.25
            compensacion_gp_en_rcm = min(abs(ganancias_patrimoniales_netas), max_comp)
            ganancias_patrimoniales_netas += compensacion_gp_en_rcm  # becomes less negative or 0
            rendimiento_neto_rcm -= compensacion_gp_en_rcm

        # Floor both at 0 for base del ahorro (remaining losses carry forward to next year)
        rendimiento_neto = max(0, rendimiento_neto_rcm)
        ganancias_patrimoniales_netas = max(0, ganancias_patrimoniales_netas)

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
            "compensacion_art49": {
                "rcm_en_gp": round(compensacion_rcm_en_gp, 2),
                "gp_en_rcm": round(compensacion_gp_en_rcm, 2),
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
