"""
Modelo 130 Calculator — Pago Fraccionado IRPF Autonomos (LIRPF art. 99.6 + RD 439/2007).

Covers ALL Spanish territories:
  - Territorio Comun (AEAT) including Canarias
  - Ceuta/Melilla (variant of Comun: 8% instead of 20%)
  - Araba/Alava (Territorio Historico, Diputacion Foral)
  - Gipuzkoa (Territorio Historico, Diputacion Foral)
  - Bizkaia (Territorio Historico, Diputacion Foral)
  - Navarra (Comunidad Foral, Hacienda Tributaria de Navarra)

Each territory's calculation is delegated to a private method. The public
`calculate()` method dispatches based on the `territory` parameter.

NOTE: All rates are fixed by law (no DB look-up needed). TaxParameterRepository
is accepted in __init__ for protocol consistency with other calculators.
"""
from typing import Any, Dict

from app.utils.tax_parameter_repository import TaxParameterRepository


class Modelo130Calculator:
    """
    Calculates the quarterly IRPF prepayment (pago fraccionado) for self-employed.

    Estimation Directa regime only. Section II (actividades agricolas/ganaderas)
    is intentionally omitted as it requires a separate treatment.
    """

    # Art. 80 bis deduction table (Territorio Comun) — annual rend_neto -> quarterly deduction
    _ART_80BIS_TABLE = [
        (9_000.0,  100.0),
        (10_000.0,  75.0),
        (11_000.0,  50.0),
        (12_000.0,  25.0),
    ]
    # Maximum quarterly deduction for vivienda habitual (casilla 16)
    _VIVIENDA_HABITUAL_MAX = 660.14  # EUR per quarter
    _VIVIENDA_HABITUAL_PCT = 0.02   # 2% of rendimiento neto acumulado

    # Navarra progressive table (applied to annualised rend_neto)
    _NAVARRA_TABLE = [
        (6_500.0,   6.0),
        (12_000.0,  12.0),
        (24_000.0,  18.0),
        (float("inf"), 24.0),
    ]

    def __init__(self, repo: TaxParameterRepository) -> None:
        self._repo = repo

    async def calculate(
        self,
        *,
        territory: str,
        quarter: int,
        ceuta_melilla: bool = False,
        # --- Territorio Comun ---
        ingresos_acumulados: float = 0.0,
        gastos_acumulados: float = 0.0,
        retenciones_acumuladas: float = 0.0,
        pagos_anteriores: float = 0.0,
        rend_neto_anterior: float = 0.0,
        tiene_vivienda_habitual: bool = False,
        resultado_anterior_complementaria: float = 0.0,
        # --- Araba ---
        ingresos_trimestre: float = 0.0,
        gastos_trimestre: float = 0.0,
        retenciones_trimestre: float = 0.0,
        # --- Gipuzkoa / Bizkaia common ---
        regimen: str = "general",           # "general" | "excepcional"
        rend_neto_penultimo: float = 0.0,   # rendimiento neto del penultimo ano
        retenciones_penultimo: float = 0.0,
        volumen_operaciones_trimestre: float = 0.0,
        retenciones_trimestre_gipuzkoa: float = 0.0,  # retenciones del trimestre (Gipuzkoa / Bizkaia excepcional)
        # --- Bizkaia extra ---
        anos_actividad: int = 3,            # if < 3 → first-2-years rules apply
        volumen_ventas_penultimo: float = 0.0,
        # --- Navarra ---
        modalidad: str = "segunda",         # "primera" | "segunda"
        retenciones_acumuladas_navarra: float = 0.0,  # alias for clarity in Navarra
        pagos_anteriores_navarra: float = 0.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calculate the quarterly Modelo 130 result.

        Args:
            territory: One of "Comun", "Araba", "Gipuzkoa", "Bizkaia", "Navarra".
            quarter: Fiscal quarter (1-4).
            ceuta_melilla: Apply Ceuta/Melilla variant (8% rate, Comun only).

            -- Territorio Comun / Ceuta-Melilla --
            ingresos_acumulados: Cumulative income Jan 1 to end of quarter (casilla 01).
            gastos_acumulados: Cumulative deductible expenses (casilla 02).
            retenciones_acumuladas: Cumulative withholdings and payments on account (casilla 05).
            pagos_anteriores: Modelo 130 payments made in previous quarters this year (casilla 06).
            rend_neto_anterior: Prior-year net income for art. 80 bis table (casilla 13 look-up).
            tiene_vivienda_habitual: Entitlement to casilla 16 housing deduction.
            resultado_anterior_complementaria: Prior complementary declaration result (casilla 18).

            -- Araba --
            ingresos_trimestre: Quarter gross income (casilla 01).
            gastos_trimestre: Quarter deductible expenses (casilla 02).
            retenciones_trimestre: Quarter withholdings (casilla 05).
            pagos_anteriores: Prior-quarter payments this year (casilla 06).

            -- Gipuzkoa --
            regimen: "general" (from 3rd year) or "excepcional" (years 1-2 / negative rend).
            rend_neto_penultimo: Net income of the year before last (general regime).
            retenciones_penultimo: Withholdings of the year before last (general regime).
            volumen_operaciones_trimestre: Quarter turnover (excepcional regime).
            retenciones_trimestre_gipuzkoa: Quarter withholdings (excepcional regime).

            -- Bizkaia --
            anos_actividad: Years of activity. < 3 triggers first-2-years rules.
            volumen_ventas_penultimo: Prior-penultimate-year turnover (excepcional regime).
            (also uses rend_neto_penultimo, retenciones_penultimo, ingresos_acumulados,
             gastos_acumulados from Comun params for years 1-2)

            -- Navarra --
            modalidad: "primera" (from 3rd year, based on penultimo year) or
                       "segunda" (mandatory years 1-2, optional after).
            rend_neto_penultimo: Net income of the year before last (primera modalidad).
            retenciones_penultimo: Withholdings of the year before last (primera modalidad).
            ingresos_acumulados: Cumulative income (segunda modalidad).
            gastos_acumulados: Cumulative expenses (segunda modalidad).
            retenciones_acumuladas_navarra: Cumulative withholdings (segunda modalidad).
            pagos_anteriores_navarra: Prior-quarter payments this year (segunda modalidad).

        Returns:
            Dict containing:
                territory (str), quarter (int), resultado (float),
                tipo_aplicado (float — percentage used),
                casillas (dict — all named casilla values for the territory),
                desglose (dict — intermediate calculation steps).
        """
        territory_norm = territory.strip().capitalize()

        if territory_norm == "Comun":
            return self._calculate_comun(
                quarter=quarter,
                ceuta_melilla=ceuta_melilla,
                ingresos_acumulados=ingresos_acumulados,
                gastos_acumulados=gastos_acumulados,
                retenciones_acumuladas=retenciones_acumuladas,
                pagos_anteriores=pagos_anteriores,
                rend_neto_anterior=rend_neto_anterior,
                tiene_vivienda_habitual=tiene_vivienda_habitual,
                resultado_anterior_complementaria=resultado_anterior_complementaria,
            )
        if territory_norm == "Araba":
            return self._calculate_araba(
                quarter=quarter,
                ingresos_trimestre=ingresos_trimestre,
                gastos_trimestre=gastos_trimestre,
                retenciones_trimestre=retenciones_trimestre,
                pagos_anteriores=pagos_anteriores,
            )
        if territory_norm == "Gipuzkoa":
            return self._calculate_gipuzkoa(
                quarter=quarter,
                regimen=regimen,
                rend_neto_penultimo=rend_neto_penultimo,
                retenciones_penultimo=retenciones_penultimo,
                volumen_operaciones_trimestre=volumen_operaciones_trimestre,
                retenciones_trimestre=retenciones_trimestre_gipuzkoa,
            )
        if territory_norm == "Bizkaia":
            return self._calculate_bizkaia(
                quarter=quarter,
                anos_actividad=anos_actividad,
                regimen=regimen,
                rend_neto_penultimo=rend_neto_penultimo,
                retenciones_penultimo=retenciones_penultimo,
                volumen_ventas_penultimo=volumen_ventas_penultimo,
                volumen_operaciones_trimestre=volumen_operaciones_trimestre,
                retenciones_trimestre=retenciones_trimestre_gipuzkoa,
                ingresos_acumulados=ingresos_acumulados,
                gastos_acumulados=gastos_acumulados,
                retenciones_acumuladas=retenciones_acumuladas,
                pagos_anteriores=pagos_anteriores,
            )
        if territory_norm == "Navarra":
            return self._calculate_navarra(
                quarter=quarter,
                modalidad=modalidad,
                rend_neto_penultimo=rend_neto_penultimo,
                retenciones_penultimo=retenciones_penultimo,
                ingresos_acumulados=ingresos_acumulados,
                gastos_acumulados=gastos_acumulados,
                retenciones_acumuladas=retenciones_acumuladas_navarra or retenciones_acumuladas,
                pagos_anteriores=pagos_anteriores_navarra or pagos_anteriores,
            )

        raise ValueError(
            f"Territory '{territory}' not supported. "
            "Valid values: Comun, Araba, Gipuzkoa, Bizkaia, Navarra"
        )

    # ------------------------------------------------------------------
    # Private calculation methods
    # ------------------------------------------------------------------

    def _calculate_comun(
        self,
        *,
        quarter: int,
        ceuta_melilla: bool,
        ingresos_acumulados: float,
        gastos_acumulados: float,
        retenciones_acumuladas: float,
        pagos_anteriores: float,
        rend_neto_anterior: float,
        tiene_vivienda_habitual: bool,
        resultado_anterior_complementaria: float,
    ) -> Dict[str, Any]:
        """
        Territorio Comun (AEAT) and Ceuta/Melilla variant.

        Sections I + III of the official Modelo 130 form.
        Legal basis: art. 99.6 LIRPF + art. 110 RIRPF.
        Ceuta/Melilla: art. 68.4 LIRPF applies 8% instead of 20%.
        """
        tipo_pct = 8.0 if ceuta_melilla else 20.0

        # --- Section I (Estimacion Directa) ---
        casilla_01 = round(ingresos_acumulados, 2)
        casilla_02 = round(gastos_acumulados, 2)
        casilla_03 = round(casilla_01 - casilla_02, 2)          # rendimiento neto
        casilla_04 = round(max(0.0, casilla_03) * (tipo_pct / 100), 2)
        casilla_05 = round(retenciones_acumuladas, 2)
        casilla_06 = round(pagos_anteriores, 2)
        casilla_07 = round(max(0.0, casilla_04 - casilla_05 - casilla_06), 2)

        # --- Section III (Total) ---
        casilla_12 = casilla_07   # skip section II (agricola)

        casilla_13 = round(self._art_80bis_deduction(rend_neto_anterior), 2)
        casilla_14 = round(max(0.0, casilla_12 - casilla_13), 2)

        # Resultados negativos trimestres anteriores (casilla 15) — capped at casilla 14
        casilla_15 = 0.0  # caller may pass via kwargs if needed; kept 0 by default

        # Deduccion vivienda habitual (casilla 16) — 2% rend_neto, max 660.14 EUR/trimestre
        casilla_16 = 0.0
        if tiene_vivienda_habitual and casilla_03 > 0:
            raw_deduccion = casilla_03 * self._VIVIENDA_HABITUAL_PCT
            casilla_16 = round(min(raw_deduccion, self._VIVIENDA_HABITUAL_MAX), 2)

        casilla_17 = round(max(0.0, casilla_14 - casilla_15 - casilla_16), 2)
        casilla_18 = round(resultado_anterior_complementaria, 2)
        casilla_19 = round(max(0.0, casilla_17 - casilla_18), 2)

        territory_label = "Ceuta/Melilla" if ceuta_melilla else "Comun"

        return {
            "territory": territory_label,
            "quarter": quarter,
            "resultado": casilla_19,
            "tipo_aplicado": tipo_pct,
            "casillas": {
                "01_ingresos_acumulados": casilla_01,
                "02_gastos_acumulados": casilla_02,
                "03_rendimiento_neto": casilla_03,
                "04_cuota_20pct": casilla_04,
                "05_retenciones_acumuladas": casilla_05,
                "06_pagos_anteriores": casilla_06,
                "07_resultado_seccion_I": casilla_07,
                "12_total_liquidacion": casilla_12,
                "13_deduccion_art80bis": casilla_13,
                "14_cuota_integra_minorada": casilla_14,
                "15_negativos_anteriores": casilla_15,
                "16_deduccion_vivienda": casilla_16,
                "17_cuota_diferencial": casilla_17,
                "18_declaracion_anterior": casilla_18,
                "19_resultado_final": casilla_19,
            },
            "desglose": {
                "tipo_pct": tipo_pct,
                "ceuta_melilla": ceuta_melilla,
                "rendimiento_neto_bruto": casilla_03,
                "cuota_bruta": casilla_04,
                "minoraciones": round(casilla_05 + casilla_06, 2),
                "deduccion_art80bis_aplicada": casilla_13,
                "deduccion_vivienda_aplicada": casilla_16,
                "rend_neto_anterior_para_art80bis": round(rend_neto_anterior, 2),
                "tiene_vivienda_habitual": tiene_vivienda_habitual,
            },
        }

    def _calculate_araba(
        self,
        *,
        quarter: int,
        ingresos_trimestre: float,
        gastos_trimestre: float,
        retenciones_trimestre: float,
        pagos_anteriores: float,
    ) -> Dict[str, Any]:
        """
        Araba/Alava (Territorio Historico).

        Uses QUARTERLY figures (not cumulative). Rate: 5%.
        Legal basis: Norma Foral IRPF Araba.
        """
        tipo_pct = 5.0

        casilla_01 = round(ingresos_trimestre, 2)
        casilla_02 = round(gastos_trimestre, 2)
        casilla_03 = round(casilla_01 - casilla_02, 2)
        casilla_04 = round(max(0.0, casilla_03) * (tipo_pct / 100), 2)
        casilla_05 = round(retenciones_trimestre, 2)
        casilla_06 = round(pagos_anteriores, 2)
        casilla_07 = round(max(0.0, casilla_04 - casilla_05 - casilla_06), 2)

        return {
            "territory": "Araba",
            "quarter": quarter,
            "resultado": casilla_07,
            "tipo_aplicado": tipo_pct,
            "casillas": {
                "01_ingresos_trimestre": casilla_01,
                "02_gastos_trimestre": casilla_02,
                "03_rendimiento_neto_trimestral": casilla_03,
                "04_cuota_5pct": casilla_04,
                "05_retenciones_trimestre": casilla_05,
                "06_pagos_anteriores": casilla_06,
                "07_resultado": casilla_07,
            },
            "desglose": {
                "tipo_pct": tipo_pct,
                "base_calculo": "trimestral",
                "rendimiento_neto_trimestral": casilla_03,
                "cuota_bruta": casilla_04,
                "minoraciones": round(casilla_05 + casilla_06, 2),
            },
        }

    def _calculate_gipuzkoa(
        self,
        *,
        quarter: int,
        regimen: str,
        rend_neto_penultimo: float,
        retenciones_penultimo: float,
        volumen_operaciones_trimestre: float,
        retenciones_trimestre: float,
    ) -> Dict[str, Any]:
        """
        Gipuzkoa (Territorio Historico).

        Regimen General (from 3rd year or when rend_neto_penultimo >= 0):
            pago = (rend_neto_penultimo * 5%) - (retenciones_penultimo * 25%), min 0

        Regimen Excepcional (years 1-2 or if rend_neto_penultimo < 0):
            pago = (volumen_operaciones_trimestre * 1%) - retenciones_trimestre, min 0

        Legal basis: Norma Foral IRPF Gipuzkoa.
        """
        regimen_norm = regimen.strip().lower()

        if regimen_norm == "general":
            tipo_pct = 5.0
            cuota_base = max(0.0, rend_neto_penultimo) * (tipo_pct / 100)
            minorar = retenciones_penultimo * 0.25
            resultado = round(max(0.0, cuota_base - minorar), 2)
            desglose = {
                "regimen": "general",
                "tipo_pct": tipo_pct,
                "rend_neto_penultimo": round(rend_neto_penultimo, 2),
                "cuota_base": round(cuota_base, 2),
                "minorar_retenciones_25pct": round(minorar, 2),
                "retenciones_penultimo": round(retenciones_penultimo, 2),
            }
            casillas = {
                "rend_neto_penultimo": round(rend_neto_penultimo, 2),
                "retenciones_penultimo": round(retenciones_penultimo, 2),
                "pago_trimestral": resultado,
            }
        else:  # excepcional
            tipo_pct = 1.0
            cuota_base = volumen_operaciones_trimestre * (tipo_pct / 100)
            resultado = round(max(0.0, cuota_base - retenciones_trimestre), 2)
            desglose = {
                "regimen": "excepcional",
                "tipo_pct": tipo_pct,
                "volumen_operaciones_trimestre": round(volumen_operaciones_trimestre, 2),
                "cuota_base": round(cuota_base, 2),
                "retenciones_trimestre": round(retenciones_trimestre, 2),
            }
            casillas = {
                "volumen_operaciones_trimestre": round(volumen_operaciones_trimestre, 2),
                "retenciones_trimestre": round(retenciones_trimestre, 2),
                "pago_trimestral": resultado,
            }

        return {
            "territory": "Gipuzkoa",
            "quarter": quarter,
            "resultado": resultado,
            "tipo_aplicado": tipo_pct,
            "regimen": regimen_norm,
            "casillas": casillas,
            "desglose": desglose,
        }

    def _calculate_bizkaia(
        self,
        *,
        quarter: int,
        anos_actividad: int,
        regimen: str,
        rend_neto_penultimo: float,
        retenciones_penultimo: float,
        volumen_ventas_penultimo: float,
        volumen_operaciones_trimestre: float,
        retenciones_trimestre: float,
        ingresos_acumulados: float,
        gastos_acumulados: float,
        retenciones_acumuladas: float,
        pagos_anteriores: float,
    ) -> Dict[str, Any]:
        """
        Bizkaia (Territorio Historico).

        First 2 years (anos_actividad < 3):
            Same rules as Territorio Comun (20% accumulated, no art. 80 bis, no vivienda).

        From 3rd year onward:
          Regimen General: (rend_neto_penultimo * 5%) - (retenciones_penultimo * 25%), min 0
          Regimen Excepcional (rend_neto_penultimo < 0):
            (volumen_ventas_penultimo * 5%) - (retenciones_penultimo * 25%), min 0

        Legal basis: Norma Foral IRPF Bizkaia.
        """
        if anos_actividad < 3:
            # First 2 years: Comun rules (no Ceuta/Melilla variant)
            tipo_pct = 20.0
            casilla_01 = round(ingresos_acumulados, 2)
            casilla_02 = round(gastos_acumulados, 2)
            casilla_03 = round(casilla_01 - casilla_02, 2)
            casilla_04 = round(max(0.0, casilla_03) * (tipo_pct / 100), 2)
            casilla_05 = round(retenciones_acumuladas, 2)
            casilla_06 = round(pagos_anteriores, 2)
            resultado = round(max(0.0, casilla_04 - casilla_05 - casilla_06), 2)
            return {
                "territory": "Bizkaia",
                "quarter": quarter,
                "resultado": resultado,
                "tipo_aplicado": tipo_pct,
                "regimen": "primeros_anos",
                "anos_actividad": anos_actividad,
                "casillas": {
                    "01_ingresos_acumulados": casilla_01,
                    "02_gastos_acumulados": casilla_02,
                    "03_rendimiento_neto": casilla_03,
                    "04_cuota_20pct": casilla_04,
                    "05_retenciones_acumuladas": casilla_05,
                    "06_pagos_anteriores": casilla_06,
                    "07_resultado": resultado,
                },
                "desglose": {
                    "regimen": "primeros_anos",
                    "tipo_pct": tipo_pct,
                    "anos_actividad": anos_actividad,
                    "nota": "Primeros 2 anos: mismas reglas que Territorio Comun",
                },
            }

        # From 3rd year
        regimen_norm = regimen.strip().lower()
        tipo_pct = 5.0

        if regimen_norm == "excepcional":
            # negative rend_neto_penultimo: use volumen_ventas_penultimo as base
            base = max(0.0, volumen_ventas_penultimo)
        else:
            base = max(0.0, rend_neto_penultimo)

        cuota_base = base * (tipo_pct / 100)
        minorar = retenciones_penultimo * 0.25
        resultado = round(max(0.0, cuota_base - minorar), 2)

        return {
            "territory": "Bizkaia",
            "quarter": quarter,
            "resultado": resultado,
            "tipo_aplicado": tipo_pct,
            "regimen": regimen_norm,
            "anos_actividad": anos_actividad,
            "casillas": {
                "rend_neto_penultimo": round(rend_neto_penultimo, 2),
                "volumen_ventas_penultimo": round(volumen_ventas_penultimo, 2),
                "retenciones_penultimo": round(retenciones_penultimo, 2),
                "base_calculo": round(base, 2),
                "pago_trimestral": resultado,
            },
            "desglose": {
                "regimen": regimen_norm,
                "tipo_pct": tipo_pct,
                "anos_actividad": anos_actividad,
                "base_calculo": round(base, 2),
                "cuota_base": round(cuota_base, 2),
                "minorar_retenciones_25pct": round(minorar, 2),
                "retenciones_penultimo": round(retenciones_penultimo, 2),
                "nota": (
                    "Base = volumen_ventas_penultimo (regimen excepcional)"
                    if regimen_norm == "excepcional"
                    else "Base = rend_neto_penultimo (regimen general)"
                ),
            },
        }

    def _calculate_navarra(
        self,
        *,
        quarter: int,
        modalidad: str,
        rend_neto_penultimo: float,
        retenciones_penultimo: float,
        ingresos_acumulados: float,
        gastos_acumulados: float,
        retenciones_acumuladas: float,
        pagos_anteriores: float,
    ) -> Dict[str, Any]:
        """
        Navarra (Comunidad Foral — Hacienda Tributaria de Navarra).

        Modalidad Primera (from 3rd year, based on penultimo year data):
            1. Apply progressive table to rend_neto_penultimo → cuota_anual
            2. cuota_neta = cuota_anual - retenciones_penultimo
            3. pago_trimestral = cuota_neta / 4

        Modalidad Segunda (mandatory years 1-2, optional after):
            1. rend_neto = ingresos_acumulados - gastos_acumulados
            2. Annualize: rend_neto * factor (Q1: x4, Q2: x2, Q3: x4/3, Q4: x1)
            3. Look up percentage from same progressive table using annualised rend
            4. cuota = rend_neto_real * (pct / 100)
            5. resultado = cuota - retenciones_acumuladas - pagos_anteriores, min 0

        Legal basis: Ley Foral 22/1998 IRPF Navarra + Reglamento.
        """
        modalidad_norm = modalidad.strip().lower()

        # Annualisation factors per quarter
        _ANNUALISE = {1: 4.0, 2: 2.0, 3: 4.0 / 3.0, 4: 1.0}
        factor = _ANNUALISE.get(quarter, 1.0)

        if modalidad_norm == "primera":
            pct = self._navarra_percentage(rend_neto_penultimo)
            cuota_anual = rend_neto_penultimo * (pct / 100)
            cuota_neta = cuota_anual - retenciones_penultimo
            pago_trimestral = round(max(0.0, cuota_neta) / 4, 2)

            return {
                "territory": "Navarra",
                "quarter": quarter,
                "resultado": pago_trimestral,
                "tipo_aplicado": pct,
                "modalidad": "primera",
                "casillas": {
                    "rend_neto_penultimo": round(rend_neto_penultimo, 2),
                    "porcentaje_tabla": pct,
                    "cuota_anual": round(cuota_anual, 2),
                    "retenciones_penultimo": round(retenciones_penultimo, 2),
                    "cuota_neta": round(cuota_neta, 2),
                    "pago_trimestral": pago_trimestral,
                },
                "desglose": {
                    "modalidad": "primera",
                    "rend_neto_penultimo": round(rend_neto_penultimo, 2),
                    "porcentaje_tabla": pct,
                    "cuota_anual": round(cuota_anual, 2),
                    "cuota_neta_anual": round(cuota_neta, 2),
                    "division_trimestral": 4,
                    "pago_trimestral": pago_trimestral,
                },
            }

        # Modalidad Segunda
        rend_neto_acumulado = ingresos_acumulados - gastos_acumulados
        rend_neto_anualizado = rend_neto_acumulado * factor
        pct = self._navarra_percentage(rend_neto_anualizado)
        cuota = rend_neto_acumulado * (pct / 100)
        resultado = round(max(0.0, cuota - retenciones_acumuladas - pagos_anteriores), 2)

        return {
            "territory": "Navarra",
            "quarter": quarter,
            "resultado": resultado,
            "tipo_aplicado": pct,
            "modalidad": "segunda",
            "casillas": {
                "ingresos_acumulados": round(ingresos_acumulados, 2),
                "gastos_acumulados": round(gastos_acumulados, 2),
                "rendimiento_neto_acumulado": round(rend_neto_acumulado, 2),
                "factor_anualizacion": round(factor, 4),
                "rendimiento_neto_anualizado": round(rend_neto_anualizado, 2),
                "porcentaje_tabla": pct,
                "cuota_sobre_rend_real": round(cuota, 2),
                "retenciones_acumuladas": round(retenciones_acumuladas, 2),
                "pagos_anteriores": round(pagos_anteriores, 2),
                "resultado": resultado,
            },
            "desglose": {
                "modalidad": "segunda",
                "quarter": quarter,
                "factor_anualizacion": round(factor, 4),
                "rend_neto_acumulado": round(rend_neto_acumulado, 2),
                "rend_neto_anualizado": round(rend_neto_anualizado, 2),
                "porcentaje_tabla": pct,
                "cuota_bruta": round(cuota, 2),
                "minoraciones": round(retenciones_acumuladas + pagos_anteriores, 2),
            },
        }

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _art_80bis_deduction(self, rend_neto_anterior: float) -> float:
        """
        Art. 80 bis quarterly deduction (Territorio Comun) based on prior-year net income.

        Table:
            rend_neto_anterior <= 9.000  → 100 EUR/quarter
            9.001 - 10.000               →  75 EUR/quarter
            10.001 - 11.000              →  50 EUR/quarter
            11.001 - 12.000              →  25 EUR/quarter
            > 12.000                     →   0 EUR/quarter
        """
        for threshold, deduction in self._ART_80BIS_TABLE:
            if rend_neto_anterior <= threshold:
                return deduction
        return 0.0

    @staticmethod
    def _navarra_percentage(rend_neto: float) -> float:
        """
        Look up the applicable percentage from the Navarra progressive table.

        Table applied to (annualised) rendimiento neto:
            <= 6.500     →  6%
            <= 12.000    → 12%
            <= 24.000    → 18%
            > 24.000     → 24%
        """
        navarra_table = [
            (6_500.0,         6.0),
            (12_000.0,       12.0),
            (24_000.0,       18.0),
            (float("inf"),   24.0),
        ]
        for threshold, pct in navarra_table:
            if rend_neto <= threshold:
                return pct
        return 24.0
