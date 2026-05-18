"""
Modelo 130 Navarra (Pago Fraccionado IRPF — Hacienda Tributaria de Navarra).

Modelo PROPIO de la Hacienda Foral de Navarra (modelo unificado que sustituye
a los antiguos 717 y FR-2). Distinto del Modelo 130 estatal.

Base legal:
  - Ley Foral 22/1998, de 30 de diciembre, del IRPF de Navarra.
  - Decreto Foral 174/1999, Reglamento del IRPF de Navarra.
  - Orden Foral del Consejero de Economía y Hacienda que aprueba el modelo
    vigente (verificar la del ejercicio en curso).

Cálculo (verificado en navarra.es, 2026-05):
  Existen DOS modalidades de pago fraccionado:

  * MODALIDAD PRIMERA — basada en el rendimiento neto del PENÚLTIMO año.
        Casillas oficiales: 131-135, 140.
        Aplicación de tabla progresiva sobre `rend_neto_penultimo`:
            ≤ 6.500       →  6 %
            ≤ 12.000      → 12 %
            ≤ 24.000      → 18 %
            > 24.000      → 24 %
        cuota_anual = rend_neto_penultimo × pct
        cuota_neta  = cuota_anual − retenciones_penultimo
        pago_trim   = max(0, cuota_neta) / 4

  * MODALIDAD SEGUNDA — basada en el rendimiento ACUMULADO del año en curso.
        Casillas oficiales: 01-10, 15.
        rend_neto_acum = ingresos_acumulados − gastos_acumulados
        rend_anualizado = rend_neto_acum × factor_trimestre (Q1 ×4, Q2 ×2,
            Q3 ×4/3, Q4 ×1)
        pct = look-up tabla progresiva sobre rend_anualizado
        cuota = rend_neto_acum × pct
        pago = max(0, cuota − retenciones_acumuladas − pagos_anteriores)

Obligación de presentar (modalidad primera):
  - Sólo presentan los que tengan rend. neto > 6.500 EUR del penúltimo año
    Y cuota trimestral en la modalidad primera ≥ 100 EUR.

Plazos (verificados en navarra.es, 2026-05):
  - Q1: 1 al 20 de abril
  - Q2: 1 al 5 de agosto
  - Q3: 1 al 20 de octubre
  - Q4: 1 al 31 de enero del año siguiente
"""

from typing import Any


class Modelo130NavarraCalculator:
    """Pago fraccionado IRPF — Modelo 130 propio de Navarra."""

    _TABLA_PROGRESIVA = [
        (6_500.0, 6.0),
        (12_000.0, 12.0),
        (24_000.0, 18.0),
        (float("inf"), 24.0),
    ]

    _UMBRAL_OBLIGACION_REND_NETO = 6_500.0
    _UMBRAL_OBLIGACION_CUOTA_TRIM = 100.0

    _ANNUALISE = {1: 4.0, 2: 2.0, 3: 4.0 / 3.0, 4: 1.0}

    _PLAZOS = {
        1: "1 al 20 de abril",
        2: "1 al 5 de agosto",
        3: "1 al 20 de octubre",
        4: "1 al 31 de enero del año siguiente",
    }

    def __init__(self, repo: Any | None = None) -> None:
        self._repo = repo

    async def calculate(
        self,
        *,
        quarter: int,
        modalidad: str = "segunda",
        # ---- Modalidad primera (datos del penúltimo año) ----
        rend_neto_penultimo: float = 0.0,
        retenciones_penultimo: float = 0.0,
        # ---- Modalidad segunda (datos acumulados del ejercicio) ----
        ingresos_acumulados: float = 0.0,
        gastos_acumulados: float = 0.0,
        retenciones_acumuladas: float = 0.0,
        pagos_anteriores: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Calcula el resultado del Modelo 130 Navarra.

        Args:
            quarter: Trimestre (1-4).
            modalidad: "primera" o "segunda".
            rend_neto_penultimo: Rendimiento neto del penúltimo año
                (modalidad primera).
            retenciones_penultimo: Retenciones del penúltimo año
                (modalidad primera).
            ingresos_acumulados / gastos_acumulados / retenciones_acumuladas /
            pagos_anteriores: Datos acumulados desde 1 enero (modalidad segunda).

        Returns:
            Dict con territory ("Navarra"), quarter, modalidad, tipo_aplicado,
            resultado, casillas, desglose, plazo, obligado_presentar
            (sólo en modalidad primera).
        """
        if quarter not in (1, 2, 3, 4):
            raise ValueError(f"Quarter '{quarter}' invalid. Valid: 1, 2, 3, 4.")

        modalidad_norm = (modalidad or "").strip().lower()
        if modalidad_norm not in {"primera", "segunda"}:
            raise ValueError(f"modalidad '{modalidad}' invalid. Valid: 'primera', 'segunda'.")

        if modalidad_norm == "primera":
            return self._calculate_primera(
                quarter=quarter,
                rend_neto_penultimo=rend_neto_penultimo,
                retenciones_penultimo=retenciones_penultimo,
            )

        return self._calculate_segunda(
            quarter=quarter,
            ingresos_acumulados=ingresos_acumulados,
            gastos_acumulados=gastos_acumulados,
            retenciones_acumuladas=retenciones_acumuladas,
            pagos_anteriores=pagos_anteriores,
        )

    # ------------------------------------------------------------------
    # Modalidad primera
    # ------------------------------------------------------------------

    def _calculate_primera(
        self,
        *,
        quarter: int,
        rend_neto_penultimo: float,
        retenciones_penultimo: float,
    ) -> dict[str, Any]:
        pct = self._lookup_pct(rend_neto_penultimo)
        cuota_anual = round(max(0.0, rend_neto_penultimo) * (pct / 100), 2)
        cuota_neta = round(cuota_anual - max(0.0, retenciones_penultimo), 2)
        pago_trim = round(max(0.0, cuota_neta) / 4, 2)

        # Obligación de presentar: rend > 6.500 Y pago trimestral primera ≥ 100
        obligado = (
            rend_neto_penultimo > self._UMBRAL_OBLIGACION_REND_NETO
            and pago_trim >= self._UMBRAL_OBLIGACION_CUOTA_TRIM
        )

        return {
            "territory": "Navarra",
            "quarter": quarter,
            "modalidad": "primera",
            "tipo_aplicado": pct,
            "resultado": pago_trim,
            "obligado_presentar": obligado,
            "casillas": {
                "131_rend_neto_penultimo": round(rend_neto_penultimo, 2),
                "132_porcentaje_tabla": pct,
                "133_cuota_anual": cuota_anual,
                "134_retenciones_penultimo": round(retenciones_penultimo, 2),
                "135_cuota_neta_anual": cuota_neta,
                "140_pago_trimestral": pago_trim,
            },
            "desglose": {
                "modalidad": "primera",
                "rend_neto_penultimo": round(rend_neto_penultimo, 2),
                "porcentaje_tabla": pct,
                "cuota_anual": cuota_anual,
                "cuota_neta_anual": cuota_neta,
                "division_trimestral": 4,
                "umbral_obligacion_rend_neto": self._UMBRAL_OBLIGACION_REND_NETO,
                "umbral_obligacion_cuota_trim": self._UMBRAL_OBLIGACION_CUOTA_TRIM,
                "concepto": (
                    "Modalidad primera: tabla progresiva sobre rend. neto del "
                    "penúltimo año, dividido en 4 trimestres tras retenciones."
                ),
            },
            "plazo": self._PLAZOS[quarter],
        }

    # ------------------------------------------------------------------
    # Modalidad segunda
    # ------------------------------------------------------------------

    def _calculate_segunda(
        self,
        *,
        quarter: int,
        ingresos_acumulados: float,
        gastos_acumulados: float,
        retenciones_acumuladas: float,
        pagos_anteriores: float,
    ) -> dict[str, Any]:
        factor = self._ANNUALISE[quarter]

        casilla_01 = round(max(0.0, ingresos_acumulados), 2)
        casilla_02 = round(max(0.0, gastos_acumulados), 2)
        casilla_03 = round(casilla_01 - casilla_02, 2)  # rend_neto_acum
        rend_anualizado = casilla_03 * factor
        pct = self._lookup_pct(rend_anualizado)
        cuota = round(max(0.0, casilla_03) * (pct / 100), 2)

        casilla_07 = round(max(0.0, retenciones_acumuladas), 2)
        casilla_08 = round(max(0.0, pagos_anteriores), 2)
        casilla_15 = round(max(0.0, cuota - casilla_07 - casilla_08), 2)

        return {
            "territory": "Navarra",
            "quarter": quarter,
            "modalidad": "segunda",
            "tipo_aplicado": pct,
            "resultado": casilla_15,
            "casillas": {
                "01_ingresos_acumulados": casilla_01,
                "02_gastos_acumulados": casilla_02,
                "03_rendimiento_neto_acumulado": casilla_03,
                "04_factor_anualizacion": round(factor, 4),
                "05_rendimiento_neto_anualizado": round(rend_anualizado, 2),
                "06_porcentaje_tabla": pct,
                "07_retenciones_acumuladas": casilla_07,
                "08_pagos_anteriores": casilla_08,
                "10_cuota_sobre_rend_real": cuota,
                "15_resultado_pago_fraccionado": casilla_15,
            },
            "desglose": {
                "modalidad": "segunda",
                "quarter": quarter,
                "factor_anualizacion": round(factor, 4),
                "rend_neto_acumulado": casilla_03,
                "rend_neto_anualizado": round(rend_anualizado, 2),
                "porcentaje_tabla": pct,
                "cuota_bruta": cuota,
                "minoraciones": round(casilla_07 + casilla_08, 2),
                "concepto": (
                    "Modalidad segunda: rend. neto acumulado del ejercicio, "
                    "anualizado para look-up de tipo, cuota sobre rend. real, "
                    "minorada por retenciones y pagos previos."
                ),
            },
            "plazo": self._PLAZOS[quarter],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @classmethod
    def _lookup_pct(cls, rend_neto: float) -> float:
        """Look-up del porcentaje aplicable en la tabla progresiva."""
        for threshold, pct in cls._TABLA_PROGRESIVA:
            if rend_neto <= threshold:
                return pct
        return cls._TABLA_PROGRESIVA[-1][1]
