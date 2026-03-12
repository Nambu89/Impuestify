"""
Rental Income Calculator — Rendimientos del Capital Inmobiliario (LIRPF arts. 22-23).

XSD Modelo 100 casillas: C_IIC (0102) → C_RNR (0154).

Calculates:
- Rental income minus deductible expenses
- Automatic amortization (3% of acquisition value from DB)
- 60% reduction for housing rental (art. 23.2 LIRPF, from DB)
"""
from typing import Any, Dict

from app.utils.tax_parameter_repository import TaxParameterRepository


class RentalIncomeCalculator:
    """Calculates net rental income following LIRPF arts. 22-23."""

    def __init__(self, repo: TaxParameterRepository):
        self._repo = repo

    async def calculate(
        self,
        *,
        ingresos_alquiler: float,
        gastos_financiacion: float = 0,
        gastos_reparacion: float = 0,
        gastos_comunidad: float = 0,
        gastos_seguros: float = 0,
        gastos_suministros: float = 0,
        ibi: float = 0,
        amortizacion: float = 0,
        valor_adquisicion: float = 0,
        es_vivienda_habitual: bool = True,
        year: int = 2024,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate net reduced rental income.

        Args:
            ingresos_alquiler: Annual rental income (casilla 0102).
            gastos_financiacion: Mortgage interest and financing costs (casilla 0105).
            gastos_reparacion: Repair and conservation costs (casilla 0106).
            gastos_comunidad: Community fees (casilla 0109).
            gastos_seguros: Insurance premiums (casilla 0114).
            gastos_suministros: Utilities (casilla 0113).
            ibi: Property tax (IBI).
            amortizacion: Manual amortization amount. If 0, auto-calculated.
            valor_adquisicion: Acquisition value for auto-amortization (casilla 0126).
            es_vivienda_habitual: If rented as primary residence (for 60% reduction).
            year: Fiscal year.

        Returns:
            Dict with income, expenses, net, reduction, and net reduced.
        """
        params = await self._repo.get_params("inmuebles", year)

        # Auto-calculate amortization if not provided
        if amortizacion == 0 and valor_adquisicion > 0:
            pct = params.get("amortizacion_pct", 3)
            amortizacion = valor_adquisicion * (pct / 100)

        # Art. 23.1.a LIRPF: ONLY financing + repair costs are capped at income.
        # Other expenses (IBI, community fees, insurance, amortization) have no cap.
        gastos_limitados = min(
            gastos_financiacion + gastos_reparacion,
            ingresos_alquiler,
        )
        gastos_no_limitados = (
            gastos_comunidad
            + gastos_seguros
            + gastos_suministros
            + ibi
            + amortizacion
        )
        total_gastos = gastos_limitados + gastos_no_limitados
        rendimiento_neto = ingresos_alquiler - total_gastos

        # Housing rental reduction (art. 23.2 LIRPF)
        reduccion = 0.0
        if es_vivienda_habitual and rendimiento_neto > 0:
            pct_red = params.get("reduccion_alquiler_vivienda", 60)
            reduccion = rendimiento_neto * (pct_red / 100)

        rendimiento_neto_reducido = max(0, rendimiento_neto - reduccion)

        return {
            "ingresos_alquiler": round(ingresos_alquiler, 2),
            "total_gastos": round(total_gastos, 2),
            "rendimiento_neto": round(rendimiento_neto, 2),
            "reduccion_vivienda": round(reduccion, 2),
            "rendimiento_neto_reducido": round(rendimiento_neto_reducido, 2),
            "desglose_gastos": {
                "financiacion": round(gastos_financiacion, 2),
                "reparacion": round(gastos_reparacion, 2),
                "comunidad": round(gastos_comunidad, 2),
                "seguros": round(gastos_seguros, 2),
                "suministros": round(gastos_suministros, 2),
                "ibi": round(ibi, 2),
                "amortizacion": round(amortizacion, 2),
            },
        }
