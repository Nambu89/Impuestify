"""
Work Income Calculator — Rendimientos del Trabajo (LIRPF arts. 17-20).

XSD Modelo 100 casillas: TPDIN (0003) → TPTOTAL (0025).

Calculates:
- Gross income → deductible expenses → net income
- Work income reduction (art. 20 LIRPF)
- Net reduced income (rendimiento neto reducido del trabajo)
"""
from typing import Any, Dict

from app.utils.tax_parameter_repository import TaxParameterRepository


class WorkIncomeCalculator:
    """Calculates net work income following LIRPF arts. 17-20."""

    def __init__(self, repo: TaxParameterRepository):
        self._repo = repo

    async def calculate(
        self,
        *,
        ingresos_brutos: float,
        ss_empleado: float = 0,
        cuotas_sindicales: float = 0,
        colegio_profesional: float = 0,
        defensa_juridica: float = 0,
        year: int = 2024,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate net reduced work income.

        Args:
            ingresos_brutos: Annual gross work income (casilla 0012).
            ss_empleado: Employee SS contributions (casilla 0013).
                If 0, estimated from ss_empleado_pct parameter.
            cuotas_sindicales: Union dues (casilla 0014).
            colegio_profesional: Professional association fees (casilla 0015).
                Capped at cuotas_colegio_max from DB.
            defensa_juridica: Legal defense costs vs employer (casilla 0016).
                Capped at defensa_juridica_max from DB.
            year: Fiscal year.

        Returns:
            Dict with gross, deductions breakdown, net, reduction, and net reduced.
        """
        params = await self._repo.get_params("trabajo", year)

        # Apply caps from DB
        colegio_max = params.get("cuotas_colegio_max", 500)
        defensa_max = params.get("defensa_juridica_max", 300)
        colegio = min(colegio_profesional, colegio_max)
        defensa = min(defensa_juridica, defensa_max)
        otros_gastos = params.get("otros_gastos", 2000)

        # Estimate SS if not provided
        if ss_empleado == 0 and ingresos_brutos > 0:
            ss_pct = params.get("ss_empleado_pct", 6.35)
            ss_empleado = ingresos_brutos * (ss_pct / 100)

        gastos_deducibles = ss_empleado + cuotas_sindicales + colegio + defensa + otros_gastos
        rendimiento_neto = max(0, ingresos_brutos - gastos_deducibles)

        # Work income reduction (art. 20 LIRPF)
        reduccion = self._calculate_reduccion(rendimiento_neto, params)
        rendimiento_neto_reducido = max(0, rendimiento_neto - reduccion)

        return {
            "ingresos_brutos": round(ingresos_brutos, 2),
            "gastos_deducibles": round(gastos_deducibles, 2),
            "rendimiento_neto": round(rendimiento_neto, 2),
            "reduccion_trabajo": round(reduccion, 2),
            "rendimiento_neto_reducido": round(rendimiento_neto_reducido, 2),
            "desglose_gastos": {
                "ss_empleado": round(ss_empleado, 2),
                "otros_gastos": otros_gastos,
                "cuotas_sindicales": round(cuotas_sindicales, 2),
                "colegio_profesional": round(colegio, 2),
                "defensa_juridica": round(defensa, 2),
            },
        }

    @staticmethod
    def _calculate_reduccion(rend_neto: float, params: Dict[str, float]) -> float:
        """
        Work income reduction (art. 20 LIRPF).

        - If rend_neto <= rend_min: full reduction (reduccion_max)
        - If rend_min < rend_neto <= rend_max: proportional reduction
        - If rend_neto > rend_max: no reduction
        """
        max_red = params.get("reduccion_max", 6498)
        rend_min = params.get("reduccion_rend_min", 14852)
        rend_max = params.get("reduccion_rend_max", 19747.5)

        if rend_neto <= rend_min:
            return max_red
        elif rend_neto <= rend_max:
            return max_red - ((rend_neto - rend_min) * max_red / (rend_max - rend_min))
        return 0
