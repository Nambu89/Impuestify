"""
Modular Income Calculator — Estimacion Objetiva (Modulos) LIRPF Art. 31.

This calculator is invoked by ActivityIncomeCalculator when estimacion='objetiva'.
It applies the index corrector, general reduction, and the start-of-activity
reduction (Art. 32.3) on top of the pre-computed rendimiento neto from AEAT tables.

The taxpayer computes their rendimiento neto using official AEAT modulos tables
(number of employees, surface, power, vehicles, etc.) — that figure is passed in
as modulos_rendimiento_neto. This module handles what comes AFTER that figure.

XSD Modelo 100 casillas: 0218-0280 (estimacion objetiva).
Quarterly pre-payment: Modelo 131 (not 130 which is for ED).
"""
from typing import Any, Dict


class ModularIncomeCalculator:
    """
    Calculates net income from economic activities under estimacion objetiva (modulos).

    The rendimiento neto already comes pre-calculated by the taxpayer from AEAT
    module tables. This class applies:
      1. Indice corrector (discount/premium factor per activity or location)
      2. Reduccion general (5% in 2024-2025, fixed by AEAT annually)
      3. Reduccion por inicio de actividad (Art. 32.3: 20% in first two positive years)
    """

    def calculate(
        self,
        modulos_rendimiento_neto: float = 0,
        modulos_indice_corrector: float = 1.0,
        modulos_reduccion_general: float = 0.05,
        inicio_actividad: bool = False,
    ) -> Dict[str, Any]:
        """
        Calcula rendimiento neto por estimacion objetiva (modulos).

        El rendimiento neto ya viene calculado por el contribuyente con tablas AEAT.
        Aqui aplicamos: indice corrector + reduccion general + reduccion inicio actividad.

        Args:
            modulos_rendimiento_neto: Rendimiento neto previo segun tablas AEAT de modulos.
                Es el importe que resulta de aplicar los signos, indices o modulos oficiales
                antes de cualquier reduccion. Debe ser > 0 para que se apliquen reducciones.
            modulos_indice_corrector: Factor corrector aplicable segun actividad, plantilla
                o municipio (por ejemplo 0.80 para actividades con plantilla < 1 persona
                en municipios < 2.000 habitantes). Default 1.0 (sin corrector).
            modulos_reduccion_general: Reduccion general aplicable al rendimiento neto de
                modulos. En 2024-2025 la AEAT fija el 5% (0.05). Default 0.05.
            inicio_actividad: True si el contribuyente inicio la actividad en el ejercicio
                actual o en el anterior y es el primer o segundo periodo con rendimiento
                neto positivo (Art. 32.3 LIRPF). Habilita una reduccion adicional del 20%.

        Returns:
            Dict con rendimiento_neto_modulos (resultado final tras todas las reducciones),
            reduccion_general (importe reduccion general aplicada),
            reduccion_inicio (importe reduccion inicio actividad, 0 si no aplica),
            rendimiento_bruto (importe original sin correccion),
            indice_corrector (factor aplicado).
        """
        if modulos_rendimiento_neto <= 0:
            return {
                "rendimiento_neto_modulos": 0,
                "reduccion_general": 0,
                "reduccion_inicio": 0,
                "rendimiento_bruto": modulos_rendimiento_neto,
                "indice_corrector": modulos_indice_corrector,
            }

        # 1. Aplicar indice corrector
        rn = modulos_rendimiento_neto * modulos_indice_corrector

        # 2. Reduccion general (5% por defecto en 2024-2025)
        red_general = rn * modulos_reduccion_general
        rn_reducido = rn - red_general

        # 3. Reduccion por inicio de actividad (Art. 32.3 LIRPF): 20%
        red_inicio = 0.0
        if inicio_actividad and rn_reducido > 0:
            red_inicio = rn_reducido * 0.20
            rn_reducido -= red_inicio

        return {
            "rendimiento_neto_modulos": round(max(0.0, rn_reducido), 2),
            "reduccion_general": round(red_general, 2),
            "reduccion_inicio": round(red_inicio, 2),
            "rendimiento_bruto": round(modulos_rendimiento_neto, 2),
            "indice_corrector": modulos_indice_corrector,
        }
