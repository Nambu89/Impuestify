"""
Activity Income Calculator — Rendimientos de Actividades Economicas (LIRPF arts. 27-32).

XSD Modelo 100 casillas: 0100-0170 (estimacion directa), 0171-0217 (desglose granular).

Calculates:
- Ingresos de actividad - Gastos deducibles = Rendimiento neto
- Gastos de dificil justificacion (5% en ED simplificada, max 2.000 EUR)
- Reduccion por inicio de actividad (Art. 32.3: 20% primeros 2 anos positivos)
- Reduccion por rendimientos de actividades economicas (Art. 32.2: similar a Art. 20 trabajo)
- Rendimiento neto reducido
- Estimacion objetiva (modulos): delega a ModularIncomeCalculator si estimacion='objetiva'
- Royalties/derechos de autor (Art. 32.1): reduccion 30% si >2 anos generacion

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
        # --- Fase 1.1: Gastos granulares actividad (casillas 0181-0217) ---
        # Si sum(granulares) > 0, se usan en vez de gastos_actividad (backward compat)
        gastos_compras: float = 0,                    # 0181: Compras mercaderias
        gastos_sueldos: float = 0,                    # 0190: Sueldos y salarios
        gastos_ss_empresa: float = 0,                 # 0191: SS a cargo empresa
        gastos_arrendamientos: float = 0,             # 0196: Alquileres locales/oficinas
        gastos_reparaciones: float = 0,               # 0197: Reparaciones
        gastos_servicios_profesionales: float = 0,    # 0198: Servicios profesionales
        gastos_tributos: float = 0,                   # 0201: Tributos (IAE, IBI local)
        gastos_financieros: float = 0,                # 0203: Gastos financieros
        gastos_suministros: float = 0,                # 0205: Suministros (luz, agua, internet)
        gastos_otros: float = 0,                      # 0217: Otros gastos deducibles
        gastos_publicidad: float = 0,                 # Marketing/anuncios (va en 0217)
        gastos_formacion: float = 0,                  # Cursos/formacion (va en 0217)
        gastos_software: float = 0,                   # Licencias software (va en 0217)
        # --- Fase 1.3: Ingresos granulares actividad (casillas 0171-0179) ---
        # Si sum(granulares) > 0, se usan en vez de ingresos_actividad (backward compat)
        ingresos_ventas: float = 0,                   # 0171: Ventas/prestacion servicios
        ingresos_subvenciones: float = 0,             # 0173: Subvenciones
        ingresos_financieros_actividad: float = 0,    # 0175: Ingresos financieros actividad
        ingresos_otros_actividad: float = 0,          # 0179: Otros ingresos
        # --- Fase 2: Estimacion Objetiva (modulos) ---
        modulos_rendimiento_neto: float = 0,          # Rendimiento neto previo (modulos)
        modulos_indice_corrector: float = 1.0,        # Indice corrector aplicable
        modulos_reduccion_general: float = 0.05,      # Reduccion general 5% (2024-2025)
        # --- Fase 3.1: Royalties / Derechos de autor ---
        ingresos_derechos_autor: float = 0,           # 0128: Royalties, copyright
        reduccion_derechos_autor: bool = False,       # Art. 32.1: 30% reduccion si >2 anos
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate net reduced activity income.

        Args:
            ingresos_actividad: Annual gross income from economic activity (casilla 0100).
                This is the total invoiced amount (base imponible, without VAT/IGIC).
                If ingresos granulares (ingresos_ventas, etc.) are provided and sum > 0,
                they take precedence over this lump sum.
            gastos_actividad: Total deductible expenses for the activity (casilla 0101).
                Includes: supplies, rent, insurance, professional services, materials,
                travel, training, marketing, subscriptions, etc.
                Does NOT include SS autonomo (separate field) or amortizations (separate).
                If gastos granulares are provided and sum > 0, they take precedence.
            cuota_autonomo_anual: Annual SS contribution as autonomo (casilla 0102).
                Typically 80-590 EUR/month x 12. This is a fully deductible expense.
            amortizaciones: Annual amortization of fixed assets (casilla 0103).
                ED normal: per official tables. ED simplificada: simplified table.
            provisiones: Deductible provisions (casilla 0104).
                Only in ED normal. ED simplificada does not allow provisions.
            otros_gastos_deducibles: Other deductible expenses not in previous categories.
            estimacion: Estimation method: 'directa_normal', 'directa_simplificada', 'objetiva'.
                ED simplificada adds 5% "gastos dificil justificacion" (max 2.000 EUR).
                'objetiva' delegates to modular calculation if modulos_rendimiento_neto > 0.
            inicio_actividad: True if taxpayer started activity in current year or previous year
                AND has not had positive net income before. Enables 20% reduction (Art. 32.3).
            un_solo_cliente: True if >75% of income comes from a single client.
                May enable reduction similar to Art. 20 (work income reduction) via Art. 32.2.
            year: Fiscal year.
            ingresos_derechos_autor: Royalties/copyright income (casilla 0128).
                Added to rendimiento neto de actividad. If reduccion_derechos_autor=True,
                30% reduction applied (Art. 32.1 LIRPF).
            reduccion_derechos_autor: True if royalties generated over >2 years (Art. 32.1).

        Returns:
            Dict with income, expenses breakdown, reductions, and net reduced income.
        """
        # --- 0. Estimacion Objetiva (modulos) dispatch ---
        if estimacion == "objetiva" and modulos_rendimiento_neto > 0:
            return await self._calculate_modular(
                modulos_rendimiento_neto=modulos_rendimiento_neto,
                modulos_indice_corrector=modulos_indice_corrector,
                modulos_reduccion_general=modulos_reduccion_general,
                inicio_actividad=inicio_actividad,
                year=year,
            )

        # --- 0b. Ingresos granulares (Fase 1.3) ---
        ingresos_granulares = (
            ingresos_ventas
            + ingresos_subvenciones
            + ingresos_financieros_actividad
            + ingresos_otros_actividad
        )
        # Use granulares if provided, else lump sum (backward compat)
        ingresos_efectivos = ingresos_granulares if ingresos_granulares > 0 else ingresos_actividad

        # --- 0c. Gastos granulares (Fase 1.1) ---
        gastos_granulares = sum([
            gastos_compras, gastos_sueldos, gastos_ss_empresa,
            gastos_arrendamientos, gastos_reparaciones,
            gastos_servicios_profesionales, gastos_tributos,
            gastos_financieros, gastos_suministros, gastos_otros,
            gastos_publicidad, gastos_formacion, gastos_software,
        ])
        # Use granulares if provided, else lump sum (backward compat)
        gastos_efectivos = gastos_granulares if gastos_granulares > 0 else gastos_actividad

        # --- 1. Total gastos deducibles ---
        total_gastos = (
            gastos_efectivos
            + cuota_autonomo_anual
            + amortizaciones
            + otros_gastos_deducibles
        )

        # Provisiones solo en ED normal
        if estimacion == "directa_normal":
            total_gastos += provisiones

        # --- 2. Rendimiento neto previo ---
        rendimiento_neto_previo = ingresos_efectivos - total_gastos

        # --- 3. Gastos de dificil justificacion (solo ED simplificada) ---
        # Art. 30 Reglamento IRPF: 5% del rendimiento neto previo, max 2.000 EUR/ano
        gastos_dificil_justificacion = 0.0
        if estimacion == "directa_simplificada" and rendimiento_neto_previo > 0:
            gastos_dificil_justificacion = min(
                rendimiento_neto_previo * 0.05,
                2000.0
            )

        # --- 4. Rendimiento neto actividad (sin royalties) ---
        rendimiento_neto = rendimiento_neto_previo - gastos_dificil_justificacion

        # --- 4b. Royalties / Derechos de autor (Fase 3.1) ---
        # Los royalties van a base_general como actividad; tienen reduccion propia si >2 anos
        rendimiento_royalties = 0.0
        if ingresos_derechos_autor > 0:
            rendimiento_royalties = ingresos_derechos_autor
            if reduccion_derechos_autor:
                # Art. 32.1: 30% reduccion si generados en mas de 2 anos
                rendimiento_royalties *= 0.70

        # Total rendimiento neto (actividad + royalties)
        rendimiento_neto_total = rendimiento_neto + rendimiento_royalties

        # --- 5. Reducciones sobre el rendimiento neto ---

        # 5a. Reduccion por inicio de actividad economica (Art. 32.3 LIRPF)
        # 20% del rendimiento neto positivo, en el primer periodo impositivo con
        # rendimiento neto positivo y en el siguiente.
        reduccion_inicio_actividad = 0.0
        if inicio_actividad and rendimiento_neto_total > 0:
            reduccion_inicio_actividad = round(rendimiento_neto_total * 0.20, 2)

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
        if un_solo_cliente and rendimiento_neto_total > 0:
            # Art. 32.2 requires ALL of:
            #   1. All activities in estimacion directa (not objetiva)
            #   2. Net activity income < 14.450 EUR
            # Note: condition 3 (other income <= 6.500 EUR) cannot be checked here
            # as this calculator only sees activity income. The simulator should ideally
            # enforce it, but for safety we at least enforce conditions 1 and 2.
            if estimacion != "objetiva" and rendimiento_neto_total < 14450.0:
                reduccion_art32_2 = self._calculate_reduccion_art32_2(rendimiento_neto_total)

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
        rendimiento_neto_reducido = max(0, rendimiento_neto_total - reduccion_aplicada)

        return {
            "ingresos_actividad": round(ingresos_efectivos, 2),
            "total_gastos_deducibles": round(total_gastos, 2),
            "rendimiento_neto_previo": round(rendimiento_neto_previo, 2),
            "gastos_dificil_justificacion": round(gastos_dificil_justificacion, 2),
            "rendimiento_neto": round(rendimiento_neto_total, 2),
            "reduccion_aplicada": round(reduccion_aplicada, 2),
            "tipo_reduccion": tipo_reduccion,
            "rendimiento_neto_reducido": round(rendimiento_neto_reducido, 2),
            "estimacion": estimacion,
            "desglose_gastos": {
                "gastos_actividad": round(gastos_efectivos, 2),
                "cuota_autonomo_anual": round(cuota_autonomo_anual, 2),
                "amortizaciones": round(amortizaciones, 2),
                "provisiones": round(provisiones if estimacion == "directa_normal" else 0, 2),
                "otros_gastos": round(otros_gastos_deducibles, 2),
                "gastos_dificil_justificacion": round(gastos_dificil_justificacion, 2),
                # Gastos granulares (informativo)
                "gastos_granulares_usados": gastos_granulares > 0,
            },
            "desglose_ingresos": {
                "ingresos_actividad_lump": round(ingresos_actividad, 2),
                "ingresos_granulares_usados": ingresos_granulares > 0,
                "ingresos_derechos_autor": round(ingresos_derechos_autor, 2),
                "rendimiento_royalties": round(rendimiento_royalties, 2),
            },
            "reducciones_detalle": {
                "reduccion_inicio_actividad": round(reduccion_inicio_actividad, 2),
                "reduccion_art32_2": round(reduccion_art32_2, 2),
                "reduccion_derechos_autor_pct": 30 if reduccion_derechos_autor and ingresos_derechos_autor > 0 else 0,
            },
        }

    async def _calculate_modular(
        self,
        *,
        modulos_rendimiento_neto: float,
        modulos_indice_corrector: float = 1.0,
        modulos_reduccion_general: float = 0.05,
        inicio_actividad: bool = False,
        year: int = 2025,
    ) -> Dict[str, Any]:
        """
        Estimacion objetiva (modulos) calculation.

        The rendimiento neto by modulos is pre-calculated by the taxpayer (from AEAT tables).
        This method applies:
          1. Indice corrector
          2. Reduccion general (5% in 2024-2025)
          3. Reduccion inicio actividad Art. 32.3 (20%) if applicable

        Returns same structure as calculate() for compatibility.
        """
        # 1. Apply indice corrector
        rend_con_corrector = modulos_rendimiento_neto * modulos_indice_corrector

        # 2. Apply reduccion general (5% default in 2024-2025)
        reduccion_general_modulos = rend_con_corrector * modulos_reduccion_general
        rendimiento_neto = max(0, rend_con_corrector - reduccion_general_modulos)

        # 3. Reduccion inicio actividad (Art. 32.3) if applicable
        reduccion_inicio_actividad = 0.0
        if inicio_actividad and rendimiento_neto > 0:
            reduccion_inicio_actividad = round(rendimiento_neto * 0.20, 2)

        reduccion_aplicada = reduccion_inicio_actividad
        tipo_reduccion = "inicio_actividad_art32_3" if reduccion_inicio_actividad > 0 else "ninguna"

        rendimiento_neto_reducido = max(0, rendimiento_neto - reduccion_aplicada)

        return {
            "ingresos_actividad": round(modulos_rendimiento_neto, 2),
            "total_gastos_deducibles": 0.0,  # In modulos, expenses are pre-calculated into rendimiento_neto
            "rendimiento_neto_previo": round(rend_con_corrector, 2),
            "gastos_dificil_justificacion": round(reduccion_general_modulos, 2),  # Mapped semantically
            "rendimiento_neto": round(rendimiento_neto, 2),
            "reduccion_aplicada": round(reduccion_aplicada, 2),
            "tipo_reduccion": tipo_reduccion,
            "rendimiento_neto_reducido": round(rendimiento_neto_reducido, 2),
            "estimacion": "objetiva",
            "desglose_gastos": {
                "gastos_actividad": 0.0,
                "cuota_autonomo_anual": 0.0,
                "amortizaciones": 0.0,
                "provisiones": 0.0,
                "otros_gastos": 0.0,
                "gastos_dificil_justificacion": round(reduccion_general_modulos, 2),
                "gastos_granulares_usados": False,
            },
            "desglose_ingresos": {
                "ingresos_actividad_lump": round(modulos_rendimiento_neto, 2),
                "ingresos_granulares_usados": False,
                "ingresos_derechos_autor": 0.0,
                "rendimiento_royalties": 0.0,
            },
            "reducciones_detalle": {
                "reduccion_inicio_actividad": round(reduccion_inicio_actividad, 2),
                "reduccion_art32_2": 0.0,
                "reduccion_derechos_autor_pct": 0,
                "modulos_indice_corrector": modulos_indice_corrector,
                "modulos_reduccion_general_pct": modulos_reduccion_general * 100,
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
