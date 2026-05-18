"""
Modelo 130 Bizkaia (Pago Fraccionado IRPF — Diputación Foral de Bizkaia).

Modelo PROPIO de la Hacienda Foral de Bizkaia. NO confundir con el Modelo 130
estatal (`modelo_130.py`), que tiene casillas y reglas distintas.

Base legal:
  - Norma Foral 13/2013, de 5 de diciembre, del IRPF de Bizkaia.
  - Decreto Foral 47/2014, de 8 de abril, por el que se aprueba el Reglamento
    del IRPF de Bizkaia (regla pago fraccionado en arts. de actividades
    económicas).
  - Orden Foral del Diputado de Hacienda y Finanzas que aprueba el modelo y
    sus instrucciones (variable por ejercicio — verificar la vigente).

Cálculo (resumen aplicable a `Modelo130BizkaiaCalculator`):
  * Régimen general (≥ 3 años de actividad y rendimiento neto del penúltimo
    año positivo):
        cuota = max(0, rend_neto_penultimo × 5% − retenciones_penultimo × 25%)
  * Régimen excepcional (rendimiento neto penúltimo año negativo o nulo):
        cuota = max(0, volumen_ventas_penultimo × 5% − retenciones_penultimo × 25%)
  * Primeros 2 años de actividad (`anos_actividad < 3`):
        Reglas análogas al territorio común — 20% sobre rendimiento neto
        ACUMULADO desde 1 enero, minorado por retenciones acumuladas y pagos
        fraccionados anteriores. NO aplican deducciones art. 80 bis ni vivienda
        habitual del Estatal.

Plazos AEAT/Bizkaia (verificados con la Orden Foral vigente; documentar revisión
anual): coinciden con los del Estatal (1-25 abril/julio/octubre, 1-30 enero del
año siguiente para 4T) — confirmar siempre con la Orden Foral del ejercicio.

NOTA: las casillas exactas del modelo papel/PDF de Bizkaia varían entre
campañas. Esta calculadora expone una representación funcional consistente
con el cálculo legal: el wrapper de PDF (`modelo_pdf_generator.py`) puede
mapearlas a la maquetación oficial mientras los importes coincidan.
"""

from typing import Any, Dict, Optional


class Modelo130BizkaiaCalculator:
    """Pago fraccionado IRPF — Modelo 130 propio de Bizkaia."""

    _TIPO_GENERAL_PCT = 5.0
    _TIPO_PRIMEROS_ANOS_PCT = 20.0
    _MINORACION_RETENCIONES_PCT = 0.25  # 25% de las retenciones del penúltimo año

    _PLAZOS = {
        1: "1 al 25 de abril",
        2: "1 al 25 de julio",
        3: "1 al 25 de octubre",
        4: "1 al 30 de enero del año siguiente",
    }

    def __init__(self, repo: Optional[Any] = None) -> None:
        # repo no es necesario — los tipos están fijados por norma foral.
        # Se mantiene para coherencia con la firma del resto de calculators.
        self._repo = repo

    async def calculate(
        self,
        *,
        quarter: int,
        anos_actividad: int = 3,
        regimen: str = "general",
        # ---- Régimen general / excepcional (datos del penúltimo año) ----
        rend_neto_penultimo: float = 0.0,
        retenciones_penultimo: float = 0.0,
        volumen_ventas_penultimo: float = 0.0,
        # ---- Primeros 2 años (datos acumulados desde 1 enero) ----
        ingresos_acumulados: float = 0.0,
        gastos_acumulados: float = 0.0,
        retenciones_acumuladas: float = 0.0,
        pagos_anteriores: float = 0.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calcula el resultado del Modelo 130 Bizkaia para el trimestre indicado.

        Args:
            quarter: Trimestre (1-4).
            anos_actividad: Años completos de actividad. <3 → reglas de los
                primeros 2 años (datos acumulados, 20%).
            regimen: "general" | "excepcional". Sólo aplica desde el 3.º año.
                Excepcional: usar `volumen_ventas_penultimo` cuando el
                rendimiento neto del penúltimo año fue ≤ 0.
            rend_neto_penultimo: Rendimiento neto del penúltimo año
                (régimen general).
            retenciones_penultimo: Retenciones e ingresos a cuenta soportados
                en el penúltimo año.
            volumen_ventas_penultimo: Volumen de ventas / operaciones del
                penúltimo año (régimen excepcional).
            ingresos_acumulados / gastos_acumulados / retenciones_acumuladas /
            pagos_anteriores: Datos acumulados desde 1 enero (primeros 2 años).

        Returns:
            Dict con:
                territory ("Bizkaia"), quarter, regimen ("general" |
                "excepcional" | "primeros_anos"), tipo_aplicado, resultado,
                casillas, desglose, plazo.
        """
        if quarter not in (1, 2, 3, 4):
            raise ValueError(f"Quarter '{quarter}' invalid. Valid: 1, 2, 3, 4.")
        if anos_actividad < 0:
            raise ValueError(f"anos_actividad '{anos_actividad}' no puede ser negativo.")

        # ---- Primeros 2 años ----
        if anos_actividad < 3:
            return self._calculate_primeros_anos(
                quarter=quarter,
                anos_actividad=anos_actividad,
                ingresos_acumulados=ingresos_acumulados,
                gastos_acumulados=gastos_acumulados,
                retenciones_acumuladas=retenciones_acumuladas,
                pagos_anteriores=pagos_anteriores,
            )

        # ---- 3.er año en adelante ----
        regimen_norm = (regimen or "").strip().lower()
        if regimen_norm not in {"general", "excepcional"}:
            raise ValueError(f"regimen '{regimen}' invalid. Valid: 'general', 'excepcional'.")

        if regimen_norm == "excepcional":
            base = max(0.0, volumen_ventas_penultimo)
            base_label = "volumen_ventas_penultimo"
            base_concepto = (
                "Régimen excepcional: rend. neto penúltimo año ≤ 0 → "
                "base = volumen de ventas del penúltimo año."
            )
        else:
            base = max(0.0, rend_neto_penultimo)
            base_label = "rend_neto_penultimo"
            base_concepto = "Régimen general: base = rend. neto del penúltimo año."

        cuota_base = round(base * (self._TIPO_GENERAL_PCT / 100), 2)
        minorar = round(retenciones_penultimo * self._MINORACION_RETENCIONES_PCT, 2)
        resultado = round(max(0.0, cuota_base - minorar), 2)

        return {
            "territory": "Bizkaia",
            "quarter": quarter,
            "regimen": regimen_norm,
            "anos_actividad": anos_actividad,
            "tipo_aplicado": self._TIPO_GENERAL_PCT,
            "resultado": resultado,
            "casillas": {
                "01_base_calculo": round(base, 2),
                "02_tipo_aplicable_pct": self._TIPO_GENERAL_PCT,
                "03_cuota_base": cuota_base,
                "04_retenciones_penultimo": round(retenciones_penultimo, 2),
                "05_minoracion_25pct_retenciones": minorar,
                "06_resultado_pago_fraccionado": resultado,
            },
            "desglose": {
                "regimen": regimen_norm,
                "base_label": base_label,
                "base_calculo": round(base, 2),
                "tipo_pct": self._TIPO_GENERAL_PCT,
                "cuota_base": cuota_base,
                "retenciones_penultimo": round(retenciones_penultimo, 2),
                "minorar_25pct": minorar,
                "concepto": base_concepto,
            },
            "plazo": self._PLAZOS[quarter],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calculate_primeros_anos(
        self,
        *,
        quarter: int,
        anos_actividad: int,
        ingresos_acumulados: float,
        gastos_acumulados: float,
        retenciones_acumuladas: float,
        pagos_anteriores: float,
    ) -> Dict[str, Any]:
        """
        Reglas análogas al Estatal para los primeros 2 años de actividad.

        Cuota = max(0, (ingresos_acumulados − gastos_acumulados) × 20%
                    − retenciones_acumuladas − pagos_anteriores).
        """
        tipo_pct = self._TIPO_PRIMEROS_ANOS_PCT

        casilla_01 = round(max(0.0, ingresos_acumulados), 2)
        casilla_02 = round(max(0.0, gastos_acumulados), 2)
        casilla_03 = round(casilla_01 - casilla_02, 2)
        casilla_04 = round(max(0.0, casilla_03) * (tipo_pct / 100), 2)
        casilla_05 = round(max(0.0, retenciones_acumuladas), 2)
        casilla_06 = round(max(0.0, pagos_anteriores), 2)
        resultado = round(max(0.0, casilla_04 - casilla_05 - casilla_06), 2)

        return {
            "territory": "Bizkaia",
            "quarter": quarter,
            "regimen": "primeros_anos",
            "anos_actividad": anos_actividad,
            "tipo_aplicado": tipo_pct,
            "resultado": resultado,
            "casillas": {
                "01_ingresos_acumulados": casilla_01,
                "02_gastos_acumulados": casilla_02,
                "03_rendimiento_neto_acumulado": casilla_03,
                "04_cuota_20pct": casilla_04,
                "05_retenciones_acumuladas": casilla_05,
                "06_pagos_anteriores": casilla_06,
                "07_resultado_pago_fraccionado": resultado,
            },
            "desglose": {
                "regimen": "primeros_anos",
                "anos_actividad": anos_actividad,
                "tipo_pct": tipo_pct,
                "rendimiento_neto_acumulado": casilla_03,
                "cuota_bruta": casilla_04,
                "minoraciones": round(casilla_05 + casilla_06, 2),
                "concepto": (
                    "Primeros 2 años de actividad: base acumulada desde 1 "
                    "enero, tipo 20%, minorada por retenciones y pagos previos."
                ),
            },
            "plazo": self._PLAZOS[quarter],
        }
