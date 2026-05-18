"""
Modelo 130 Gipuzkoa (Pago Fraccionado IRPF — Diputación Foral de Gipuzkoa).

Modelo PROPIO de la Hacienda Foral de Gipuzkoa, distinto del Modelo 130
estatal (`modelo_130.py`).

Base legal:
  - Norma Foral 3/2014, de 17 de enero, del IRPF de Gipuzkoa.
  - Decreto Foral 33/2014 (Reglamento IRPF Gipuzkoa) — pago fraccionado.
  - Orden Foral del Departamento de Hacienda y Finanzas (Modelo 130 vigente).

Cálculo:
  * Régimen general (≥ 3 años de actividad y rend. neto del penúltimo año
    positivo):
        cuota = max(0, rend_neto_penultimo × 5% − retenciones_penultimo × 25%)
  * Régimen excepcional (años 1-2 o rend. neto del penúltimo año ≤ 0):
        cuota = max(0, volumen_operaciones_trimestre × 1% − retenciones_trimestre)

Dispensa (verificada en la web oficial Gipuzkoa, 2026-05):
  - Profesionales: ≥ 50 % de los ingresos del año anterior con retención.
  - Agrarios:      ≥ 70 % de los ingresos del año anterior con retención
                   (excluyendo subvenciones e indemnizaciones).

Plazos (verificados en gipuzkoa.eus, 2026-05):
  - Q1: 1 abril – 10 mayo
  - Q2: 1 julio – 10 agosto
  - Q3: 1 octubre – 10 noviembre
  - Q4: 1 enero – 10 febrero del año siguiente
"""

from typing import Any


class Modelo130GipuzkoaCalculator:
    """Pago fraccionado IRPF — Modelo 130 propio de Gipuzkoa."""

    _TIPO_GENERAL_PCT = 5.0
    _TIPO_EXCEPCIONAL_PCT = 1.0
    _MINORACION_RETENCIONES_PCT = 0.25  # 25 % retenciones penúltimo año

    _DISPENSA_PROFESIONAL_PCT = 50.0
    _DISPENSA_AGRARIA_PCT = 70.0

    _PLAZOS = {
        1: "1 de abril al 10 de mayo",
        2: "1 de julio al 10 de agosto",
        3: "1 de octubre al 10 de noviembre",
        4: "1 de enero al 10 de febrero del año siguiente",
    }

    def __init__(self, repo: Any | None = None) -> None:
        self._repo = repo

    async def calculate(
        self,
        *,
        quarter: int,
        regimen: str = "general",
        # ---- Régimen general (datos del penúltimo año) ----
        rend_neto_penultimo: float = 0.0,
        retenciones_penultimo: float = 0.0,
        # ---- Régimen excepcional (datos del trimestre) ----
        volumen_operaciones_trimestre: float = 0.0,
        retenciones_trimestre: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Calcula el resultado del Modelo 130 Gipuzkoa.

        Args:
            quarter: Trimestre (1-4).
            regimen: "general" (≥ 3.er año, rend. penúltimo > 0) o
                "excepcional" (años 1-2 o rend. penúltimo ≤ 0).
            rend_neto_penultimo: Rendimiento neto del penúltimo año
                (régimen general).
            retenciones_penultimo: Retenciones del penúltimo año
                (régimen general).
            volumen_operaciones_trimestre: Volumen de operaciones del trimestre
                (régimen excepcional).
            retenciones_trimestre: Retenciones del trimestre
                (régimen excepcional).

        Returns:
            Dict con territory, quarter, regimen, tipo_aplicado, resultado,
            casillas, desglose, plazo.
        """
        if quarter not in (1, 2, 3, 4):
            raise ValueError(f"Quarter '{quarter}' invalid. Valid: 1, 2, 3, 4.")

        regimen_norm = (regimen or "").strip().lower()
        if regimen_norm not in {"general", "excepcional"}:
            raise ValueError(f"regimen '{regimen}' invalid. Valid: 'general', 'excepcional'.")

        if regimen_norm == "general":
            tipo_pct = self._TIPO_GENERAL_PCT
            base = max(0.0, rend_neto_penultimo)
            cuota_base = round(base * (tipo_pct / 100), 2)
            minorar = round(retenciones_penultimo * self._MINORACION_RETENCIONES_PCT, 2)
            resultado = round(max(0.0, cuota_base - minorar), 2)

            casillas = {
                "01_rend_neto_penultimo": round(rend_neto_penultimo, 2),
                "02_tipo_aplicable_pct": tipo_pct,
                "03_cuota_base": cuota_base,
                "04_retenciones_penultimo": round(retenciones_penultimo, 2),
                "05_minoracion_25pct_retenciones": minorar,
                "06_resultado_pago_fraccionado": resultado,
            }
            desglose = {
                "regimen": "general",
                "tipo_pct": tipo_pct,
                "base_calculo": round(base, 2),
                "cuota_base": cuota_base,
                "minorar_25pct": minorar,
                "concepto": (
                    "Régimen general: 5 % sobre rend. neto del penúltimo año, "
                    "minorado por el 25 % de las retenciones del mismo año."
                ),
            }
        else:  # excepcional
            tipo_pct = self._TIPO_EXCEPCIONAL_PCT
            base = max(0.0, volumen_operaciones_trimestre)
            cuota_base = round(base * (tipo_pct / 100), 2)
            retenciones = round(max(0.0, retenciones_trimestre), 2)
            resultado = round(max(0.0, cuota_base - retenciones), 2)

            casillas = {
                "01_volumen_operaciones_trimestre": round(base, 2),
                "02_tipo_aplicable_pct": tipo_pct,
                "03_cuota_base": cuota_base,
                "04_retenciones_trimestre": retenciones,
                "05_resultado_pago_fraccionado": resultado,
            }
            desglose = {
                "regimen": "excepcional",
                "tipo_pct": tipo_pct,
                "base_calculo": round(base, 2),
                "cuota_base": cuota_base,
                "retenciones_trimestre": retenciones,
                "concepto": (
                    "Régimen excepcional (años 1-2 o rend. penúltimo ≤ 0): "
                    "1 % sobre volumen de operaciones del trimestre, "
                    "minorado por las retenciones del mismo trimestre."
                ),
            }

        return {
            "territory": "Gipuzkoa",
            "quarter": quarter,
            "regimen": regimen_norm,
            "tipo_aplicado": tipo_pct,
            "resultado": resultado,
            "casillas": casillas,
            "desglose": desglose,
            "plazo": self._PLAZOS[quarter],
        }

    # ------------------------------------------------------------------
    # Dispensa por retención (Norma Foral IRPF Gipuzkoa)
    # ------------------------------------------------------------------

    @classmethod
    def is_dispensado_por_retencion(
        cls,
        *,
        es_profesional: bool,
        actividad_agraria: bool,
        pct_retencion_anio_anterior: float,
    ) -> bool:
        """
        Comprueba la dispensa de presentar Modelo 130 Gipuzkoa.

        - Profesionales con ≥ 50 % de retención el año anterior → dispensado.
        - Agrarios con ≥ 70 % de retención el año anterior → dispensado.
        - Empresariales no agrarios: NO existe dispensa por retención.
        """
        if not (es_profesional or actividad_agraria):
            return False
        threshold = (
            cls._DISPENSA_PROFESIONAL_PCT
            if es_profesional and not actividad_agraria
            else cls._DISPENSA_AGRARIA_PCT
        )
        return pct_retencion_anio_anterior >= threshold
