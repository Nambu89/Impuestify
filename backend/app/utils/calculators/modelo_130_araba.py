"""
Modelo 130 Araba/Álava (Pago Fraccionado IRPF — Diputación Foral de Álava).

Modelo PROPIO de la Hacienda Foral de Álava, distinto del Modelo 130 estatal.

Base legal:
  - Norma Foral 33/2013, de 27 de noviembre, del IRPF de Álava.
  - Decreto Foral 40/2014 (Reglamento IRPF Álava).
  - Orden Foral del Diputado de Hacienda, Finanzas y Presupuestos que aprueba
    el Modelo 130 vigente.

Cálculo:
  * Base TRIMESTRAL (no acumulada como el Estatal):
        rend_neto = ingresos_trimestre − gastos_trimestre
        cuota = max(0, rend_neto × 5% − retenciones_trimestre − pagos_anteriores)

Plazos: análogos al Estatal (1-25 abril/julio/octubre, 1-30 enero año siguiente
para 4T) — confirmar con la Orden Foral del ejercicio.

NOTA: Álava NO distingue régimen general / excepcional como Bizkaia o Gipuzkoa
— aplica un único 5 % sobre el rendimiento neto del trimestre. Los primeros
años de actividad usan las mismas reglas (cifras trimestrales).
"""

from typing import Any


class Modelo130ArabaCalculator:
    """Pago fraccionado IRPF — Modelo 130 propio de Araba/Álava."""

    _TIPO_PCT = 5.0

    _PLAZOS = {
        1: "1 al 25 de abril",
        2: "1 al 25 de julio",
        3: "1 al 25 de octubre",
        4: "1 al 30 de enero del año siguiente",
    }

    def __init__(self, repo: Any | None = None) -> None:
        self._repo = repo

    async def calculate(
        self,
        *,
        quarter: int,
        ingresos_trimestre: float = 0.0,
        gastos_trimestre: float = 0.0,
        retenciones_trimestre: float = 0.0,
        pagos_anteriores: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Calcula el resultado del Modelo 130 Araba.

        Args:
            quarter: Trimestre (1-4).
            ingresos_trimestre: Ingresos del TRIMESTRE (no acumulados).
            gastos_trimestre: Gastos deducibles del TRIMESTRE.
            retenciones_trimestre: Retenciones e ingresos a cuenta del trimestre.
            pagos_anteriores: Pagos fraccionados ya ingresados en trimestres
                anteriores del mismo ejercicio.

        Returns:
            Dict con territory ("Araba"), quarter, tipo_aplicado, resultado,
            casillas, desglose, plazo.
        """
        if quarter not in (1, 2, 3, 4):
            raise ValueError(f"Quarter '{quarter}' invalid. Valid: 1, 2, 3, 4.")

        tipo_pct = self._TIPO_PCT

        casilla_01 = round(max(0.0, ingresos_trimestre), 2)
        casilla_02 = round(max(0.0, gastos_trimestre), 2)
        casilla_03 = round(casilla_01 - casilla_02, 2)
        casilla_04 = round(max(0.0, casilla_03) * (tipo_pct / 100), 2)
        casilla_05 = round(max(0.0, retenciones_trimestre), 2)
        casilla_06 = round(max(0.0, pagos_anteriores), 2)
        resultado = round(max(0.0, casilla_04 - casilla_05 - casilla_06), 2)

        return {
            "territory": "Araba",
            "quarter": quarter,
            "tipo_aplicado": tipo_pct,
            "resultado": resultado,
            "casillas": {
                "01_ingresos_trimestre": casilla_01,
                "02_gastos_trimestre": casilla_02,
                "03_rendimiento_neto_trimestral": casilla_03,
                "04_cuota_5pct": casilla_04,
                "05_retenciones_trimestre": casilla_05,
                "06_pagos_anteriores": casilla_06,
                "07_resultado_pago_fraccionado": resultado,
            },
            "desglose": {
                "tipo_pct": tipo_pct,
                "base_calculo": "trimestral",
                "rendimiento_neto_trimestral": casilla_03,
                "cuota_bruta": casilla_04,
                "minoraciones": round(casilla_05 + casilla_06, 2),
                "concepto": (
                    "Araba/Álava: 5 % sobre el rendimiento neto del trimestre, "
                    "minorado por retenciones y pagos previos del ejercicio."
                ),
            },
            "plazo": self._PLAZOS[quarter],
        }
