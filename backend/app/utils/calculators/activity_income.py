"""
Activity Income Calculator — Rendimientos de Actividades Economicas (LIRPF arts. 27-32).

XSD Modelo 100 casillas: 0100-0170 (estimacion directa), 0171-0185 (estimacion objetiva).

Calculates:
- Ingresos de actividad - Gastos deducibles = Rendimiento neto
- Gastos de dificil justificacion (5% en ED simplificada, max 2.000 EUR)
- Reduccion por inicio de actividad (Art. 32.3: 20% primeros 2 anos positivos)
- Reduccion por rendimientos de actividades economicas (Art. 32.2: similar a Art. 20 trabajo)
- Rendimiento neto reducido

IMPORTANT: This calculator handles the ANNUAL IRPF declaration (Modelo 100).
The quarterly Modelo 130 feeds data INTO this calculator (cumulative income/expenses).
The connection is: sum(4 quarters of Modelo 130 data) = annual activity income for Modelo 100.
"""
from typing import Any, Dict

from app.utils.tax_parameter_repository import TaxParameterRepository


class ActivityIncomeCalculator:
    """Calculates net income from economic activities (autonomos) following LIRPF arts. 27-32."""

    def __init__(self, repo: TaxParameterRepository):
        self._repo = repo

    async def calculate(
        self,
        *,
        ingresos_actividad: float,
        gastos_actividad: float = 0,
        cuota_autonomo_anual: float = 0,
        amortizaciones: float = 0,
        provisiones: float = 0,
        otros_gastos_deducibles: float = 0,
        estimacion: str = "directa_simplificada",
        inicio_actividad: bool = False,
        un_solo_cliente: bool = False,
        year: int = 2025,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate net reduced activity income.

        Args:
            ingresos_actividad: Annual gross income from economic activity (casilla 0100).
                This is the total invoiced amount (base imponible, without VAT/IGIC).
            gastos_actividad: Total deductible expenses for the activity (casilla 0101).
                Includes: supplies, rent, insurance, professional services, materials,
                travel, training, marketing, subscriptions, etc.
                Does NOT include SS autonomo (separate field) or amortizations (separate).
            cuota_autonomo_anual: Annual SS contribution as autonomo (casilla 0102).
                Typically 80-590 EUR/month x 12. This is a fully deductible expense.
            amortizaciones: Annual amortization of fixed assets (casilla 0103).
                ED normal: per official tables. ED simplificada: simplified table.
            provisiones: Deductible provisions (casilla 0104).
                Only in ED normal. ED simplificada does not allow provisions.
            otros_gastos_deducibles: Other deductible expenses not in previous categories.
            estimacion: Estimation method: 'directa_normal', 'directa_simplificada', 'objetiva'.
                ED simplificada adds 5% "gastos dificil justificacion" (max 2.000 EUR).
            inicio_actividad: True if taxpayer started activity in current year or previous year
                AND has not had positive net income before. Enables 20% reduction (Art. 32.3).
            un_solo_cliente: True if >75% of income comes from a single client.
                May enable reduction similar to Art. 20 (work income reduction) via Art. 32.2.
            year: Fiscal year.

        Returns:
            Dict with income, expenses breakdown, reductions, and net reduced income.
        """
        # --- 1. Total gastos deducibles ---
        total_gastos = (
            gastos_actividad
            + cuota_autonomo_anual
            + amortizaciones
            + otros_gastos_deducibles
        )

        # Provisiones solo en ED normal
        if estimacion == "directa_normal":
            total_gastos += provisiones

        # --- 2. Rendimiento neto previo ---
        rendimiento_neto_previo = ingresos_actividad - total_gastos

        # --- 3. Gastos de dificil justificacion (solo ED simplificada) ---
        # Art. 30 Reglamento IRPF: 5% del rendimiento neto previo, max 2.000 EUR/ano
        gastos_dificil_justificacion = 0.0
        if estimacion == "directa_simplificada" and rendimiento_neto_previo > 0:
            gastos_dificil_justificacion = min(
                rendimiento_neto_previo * 0.05,
                2000.0
            )

        # --- 4. Rendimiento neto ---
        rendimiento_neto = rendimiento_neto_previo - gastos_dificil_justificacion

        # --- 5. Reducciones sobre el rendimiento neto ---

        # 5a. Reduccion por inicio de actividad economica (Art. 32.3 LIRPF)
        # 20% del rendimiento neto positivo, en el primer periodo impositivo con
        # rendimiento neto positivo y en el siguiente.
        reduccion_inicio_actividad = 0.0
        if inicio_actividad and rendimiento_neto > 0:
            reduccion_inicio_actividad = round(rendimiento_neto * 0.20, 2)

        # 5b. Reduccion por rendimientos de actividades economicas (Art. 32.2 LIRPF)
        # Para autonomos economicamente dependientes (TRADE) o con un solo cliente (>75%),
        # aplica una reduccion similar a la del Art. 20 (rendimientos del trabajo).
        # Condiciones:
        #   - Todas las actividades en estimacion directa
        #   - El conjunto de rendimientos netos < 14.450 EUR
        #   - No tenga rentas distintas de actividades > 6.500 EUR
        #   - >75% ingresos de un solo pagador (un_solo_cliente=True)
        # Cuantia: igual que Art. 20 trabajo (max 6.498 EUR, decreciente)
        reduccion_art32_2 = 0.0
        if un_solo_cliente and rendimiento_neto > 0:
            reduccion_art32_2 = self._calculate_reduccion_art32_2(rendimiento_neto)

        # Total reducciones (no acumulables: se aplica la mayor)
        # Nota: Art. 32.3 (inicio) y Art. 32.2 (dependiente) no son acumulables.
        # Se aplica la que resulte mayor.
        reduccion_aplicada = max(reduccion_inicio_actividad, reduccion_art32_2)
        tipo_reduccion = "ninguna"
        if reduccion_aplicada > 0:
            if reduccion_inicio_actividad >= reduccion_art32_2:
                tipo_reduccion = "inicio_actividad_art32_3"
            else:
                tipo_reduccion = "dependiente_art32_2"

        # --- 6. Rendimiento neto reducido ---
        rendimiento_neto_reducido = max(0, rendimiento_neto - reduccion_aplicada)

        return {
            "ingresos_actividad": round(ingresos_actividad, 2),
            "total_gastos_deducibles": round(total_gastos, 2),
            "rendimiento_neto_previo": round(rendimiento_neto_previo, 2),
            "gastos_dificil_justificacion": round(gastos_dificil_justificacion, 2),
            "rendimiento_neto": round(rendimiento_neto, 2),
            "reduccion_aplicada": round(reduccion_aplicada, 2),
            "tipo_reduccion": tipo_reduccion,
            "rendimiento_neto_reducido": round(rendimiento_neto_reducido, 2),
            "estimacion": estimacion,
            "desglose_gastos": {
                "gastos_actividad": round(gastos_actividad, 2),
                "cuota_autonomo_anual": round(cuota_autonomo_anual, 2),
                "amortizaciones": round(amortizaciones, 2),
                "provisiones": round(provisiones if estimacion == "directa_normal" else 0, 2),
                "otros_gastos": round(otros_gastos_deducibles, 2),
                "gastos_dificil_justificacion": round(gastos_dificil_justificacion, 2),
            },
            "reducciones_detalle": {
                "reduccion_inicio_actividad": round(reduccion_inicio_actividad, 2),
                "reduccion_art32_2": round(reduccion_art32_2, 2),
            },
        }

    @staticmethod
    def _calculate_reduccion_art32_2(rend_neto: float) -> float:
        """
        Reduction for economically dependent self-employed (Art. 32.2 LIRPF).

        Same scale as Art. 20 (work income reduction):
        - rend_neto <= 14.852: 6.498 EUR
        - 14.852 < rend_neto <= 19.747,50: linear decrease from 6.498 to 0
        - rend_neto > 19.747,50: 0
        """
        max_red = 6498.0
        rend_min = 14852.0
        rend_max = 19747.5

        if rend_neto <= rend_min:
            return max_red
        elif rend_neto <= rend_max:
            return max_red - ((rend_neto - rend_min) * max_red / (rend_max - rend_min))
        return 0.0
