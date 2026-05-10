"""
Modelo 131 Calculator — Pago Fraccionado IRPF Estimación Objetiva (Módulos).

Legal basis:
  - Art. 110.1.c RIRPF (RD 439/2007) — pago fraccionado en estimación objetiva.
  - Art. 110.1.b RIRPF — actividades agrícolas, ganaderas, forestales, pesqueras
    (apartado III, 2% sobre volumen de ingresos).
  - Art. 110.2 RIRPF + Disp. Adic. 28ª LIRPF — reducción 60% Ceuta/Melilla.
  - Orden EHA/672/2007 — aprueba el Modelo 131 vigente.
  - Orden HAC/1425/2025 — módulos IRPF ejercicio 2026.

Apartados oficiales del Modelo 131:
  Apartado I  — Actividades empresariales en estimación objetiva (con datos-base).
                Tipos: 4% (>1 asalariado) / 3% (1 asalariado) / 2% (sin asalariados).
  Apartado II — Actividades empresariales sin datos-base disponibles.
                Tipo: 2% sobre volumen de ingresos del trimestre.
  Apartado III — Actividades agrícolas/ganaderas/forestales/pesqueras.
                Tipo: 2% sobre volumen de ingresos del trimestre.

Casillas oficiales (apartado I — empresarial):
  01  Rendimiento neto previo módulos (anualizado).
  02  Tipo aplicable (4% / 3% / 2%).
  03  Resultado actividades empresariales (01 × 02).
  04  Volumen ingresos agrario.
  05  Cantidad 2% × 04 (cuota agraria).
  06  Total cuotas (03 + 05).
  07  Reducciones (Ceuta/Melilla 60%, La Palma cuando aplique).
  08  Resultado tras reducciones.
  09  Retenciones del trimestre.
  10  Pagos fraccionados anteriores del ejercicio.
  11  Resultado autoliquidación complementaria (4T).
  12  Resultado a ingresar/devolver.

NOTA SOBRE FORALES:
  Los territorios forales (Araba, Bizkaia, Gipuzkoa, Navarra) tienen sus propios
  modelos de pago fraccionado regulados por sus normas forales del IRPF y NO
  utilizan el Modelo 131 estatal. Esta calculadora cubre exclusivamente el
  Modelo 131 estatal (Territorio Común + Ceuta/Melilla). Soporte foral queda
  fuera de alcance — debe implementarse en calculadoras específicas.

NOTA SOBRE LA PALMA:
  La reducción del 60% para La Palma fue introducida por la Orden HFP/1359/2023
  (módulos 2024) tras la erupción del volcán Cumbre Vieja y se ha extendido en
  órdenes posteriores. La calculadora la soporta como flag opcional `la_palma`
  pero el caller DEBE verificar su vigencia para el ejercicio concreto antes
  de activarla (Orden HAC/1425/2025 para 2026).
"""
from typing import Any, Dict, Optional


class Modelo131Calculator:
    """
    Calculates the quarterly Modelo 131 result (estimación objetiva).

    The public `calculate()` method dispatches based on `actividad_tipo`:
      - "empresarial"          → apartado I (con datos-base, 4/3/2%)
      - "sin_datos_base"       → apartado II (2% sobre ingresos trimestre)
      - "agraria"              → apartado III (2% sobre ingresos trimestre)
    """

    # Tipos por número de asalariados (apartado I — empresarial)
    _TIPO_MAS_DE_UN_ASALARIADO = 4.0
    _TIPO_UN_ASALARIADO = 3.0
    _TIPO_SIN_ASALARIADOS = 2.0

    # Apartado II y III — actividades sin datos-base / agrarias
    _TIPO_AGRARIA = 2.0
    _TIPO_SIN_DATOS_BASE = 2.0

    # Reducciones territoriales (Art. 110.2 RIRPF)
    _REDUCCION_CEUTA_MELILLA = 0.60   # 60%
    _REDUCCION_LA_PALMA = 0.60        # 60% — verificar vigencia con Orden anual

    # Tabla de minoración por rendimientos bajos (escalonada plana, NO lineal).
    # Ámbito: análoga al art. 80 bis LIRPF aplicada al 131. Tramos discretos
    # publicados en el Anexo de la Orden anual de módulos.
    _MINORACION_TABLA = [
        (9_000.0,  100.0),   # ≤ 9.000
        (10_000.0,  75.0),   # 9.001-10.000
        (11_000.0,  50.0),   # 10.001-11.000
        (12_000.0,  25.0),   # 11.001-12.000
    ]

    # Plazos AEAT
    _PLAZOS = {
        1: "1 al 20 de abril",
        2: "1 al 20 de julio",
        3: "1 al 20 de octubre",
        4: "1 al 30 de enero del año siguiente",
    }

    def __init__(self, repo: Optional[Any] = None) -> None:
        # repo no es necesario para 131 — todos los tipos están fijados por ley.
        # Se mantiene en la firma para coherencia con otros calculadores.
        self._repo = repo

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def calculate(
        self,
        *,
        quarter: int,
        actividad_tipo: str = "empresarial",
        # Apartado I (empresarial con datos-base)
        rendimiento_neto_modulos_anual: float = 0.0,
        num_asalariados: int = 0,
        # Apartados II / III (sin datos-base / agraria)
        volumen_ingresos_trimestre: float = 0.0,
        # Comunes — minoración + retenciones + pagos previos
        rendimiento_neto_anterior: float = 0.0,
        retenciones_trimestre: float = 0.0,
        pagos_anteriores: float = 0.0,
        resultado_anterior_complementaria: float = 0.0,
        # Reducciones territoriales
        ceuta_melilla: bool = False,
        la_palma: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calculate the quarterly Modelo 131 result.

        Args:
            quarter: Trimestre (1-4).
            actividad_tipo: "empresarial" | "sin_datos_base" | "agraria".
            rendimiento_neto_modulos_anual: Rendimiento neto previo módulos
                anualizado a 1 de enero (apartado I).
            num_asalariados: Personas asalariadas a 1 de enero (apartado I).
                0 → 2%; 1 → 3%; ≥2 → 4%.
            volumen_ingresos_trimestre: Volumen de ingresos del trimestre,
                excluyendo subvenciones de capital (apartados II/III).
            rendimiento_neto_anterior: Rendimiento neto del año anterior, para
                aplicar la minoración por rendimientos bajos (sólo apartado I).
            retenciones_trimestre: Retenciones e ingresos a cuenta del trimestre.
            pagos_anteriores: Pagos fraccionados ya ingresados en trimestres
                anteriores del mismo ejercicio.
            resultado_anterior_complementaria: Resultado de una autoliquidación
                anterior del mismo trimestre (sólo complementarias).
            ceuta_melilla: Aplica reducción 60% Ceuta/Melilla.
            la_palma: Aplica reducción 60% La Palma (verificar vigencia anual).

        Returns:
            Dict con territory, quarter, apartado, resultado, tipo_aplicado,
            casillas (01-12), desglose, plazo.

        Raises:
            ValueError: Si quarter o actividad_tipo no son válidos.
        """
        if quarter not in (1, 2, 3, 4):
            raise ValueError(
                f"Quarter '{quarter}' invalid. Valid: 1, 2, 3, 4."
            )

        actividad_norm = (actividad_tipo or "").strip().lower()
        if actividad_norm not in {"empresarial", "sin_datos_base", "agraria"}:
            raise ValueError(
                f"actividad_tipo '{actividad_tipo}' invalid. "
                "Valid: 'empresarial', 'sin_datos_base', 'agraria'."
            )

        if actividad_norm == "empresarial":
            return self._calculate_empresarial(
                quarter=quarter,
                rendimiento_neto_modulos_anual=rendimiento_neto_modulos_anual,
                num_asalariados=num_asalariados,
                rendimiento_neto_anterior=rendimiento_neto_anterior,
                retenciones_trimestre=retenciones_trimestre,
                pagos_anteriores=pagos_anteriores,
                resultado_anterior_complementaria=resultado_anterior_complementaria,
                ceuta_melilla=ceuta_melilla,
                la_palma=la_palma,
            )

        if actividad_norm == "agraria":
            return self._calculate_agraria(
                quarter=quarter,
                volumen_ingresos_trimestre=volumen_ingresos_trimestre,
                retenciones_trimestre=retenciones_trimestre,
                pagos_anteriores=pagos_anteriores,
                resultado_anterior_complementaria=resultado_anterior_complementaria,
                ceuta_melilla=ceuta_melilla,
                la_palma=la_palma,
            )

        # sin_datos_base
        return self._calculate_sin_datos_base(
            quarter=quarter,
            volumen_ingresos_trimestre=volumen_ingresos_trimestre,
            retenciones_trimestre=retenciones_trimestre,
            pagos_anteriores=pagos_anteriores,
            resultado_anterior_complementaria=resultado_anterior_complementaria,
            ceuta_melilla=ceuta_melilla,
            la_palma=la_palma,
        )

    # ------------------------------------------------------------------
    # Apartado I — Actividades empresariales (con datos-base)
    # ------------------------------------------------------------------

    def _calculate_empresarial(
        self,
        *,
        quarter: int,
        rendimiento_neto_modulos_anual: float,
        num_asalariados: int,
        rendimiento_neto_anterior: float,
        retenciones_trimestre: float,
        pagos_anteriores: float,
        resultado_anterior_complementaria: float,
        ceuta_melilla: bool,
        la_palma: bool,
    ) -> Dict[str, Any]:
        """
        Apartado I del Modelo 131 — actividades empresariales con datos-base.

        Fórmula:
            casilla 01 = rendimiento_neto_modulos_anual
            casilla 02 = tipo (% según num_asalariados)
            casilla 03 = 01 × 02
            casilla 06 = casilla 03 (sin componente agraria)
            casilla 07 = reducción territorial (60% Ceuta/Melilla, 60% La Palma)
            casilla 08 = casilla 06 − casilla 07
            casilla 09 = retenciones_trimestre
            casilla 10 = pagos_anteriores
            casilla 11 = resultado_anterior_complementaria (4T)
            casilla 12 = max(0, 08 − 09 − 10 − 11) − minoración rendimientos bajos
        """
        tipo_pct = self._tipo_segun_asalariados(num_asalariados)

        casilla_01 = round(max(0.0, rendimiento_neto_modulos_anual), 2)
        casilla_02 = tipo_pct
        casilla_03 = round(casilla_01 * (tipo_pct / 100), 2)

        # Sin componente agraria en este apartado
        casilla_04 = 0.0
        casilla_05 = 0.0
        casilla_06 = round(casilla_03 + casilla_05, 2)

        # Reducción territorial
        reduccion_pct, reduccion_label = self._reduccion_territorial(
            ceuta_melilla=ceuta_melilla, la_palma=la_palma,
        )
        casilla_07 = round(casilla_06 * reduccion_pct, 2)
        casilla_08 = round(max(0.0, casilla_06 - casilla_07), 2)

        # Minoración rendimientos bajos (sólo apartado I).
        # Se aplica DESPUÉS de la reducción territorial sobre el resultado
        # tras minoraciones de retenciones y pagos previos. Se proyecta como
        # ajuste final al resultado a ingresar.
        minoracion = self._minoracion_rendimientos_bajos(rendimiento_neto_anterior)

        casilla_09 = round(max(0.0, retenciones_trimestre), 2)
        casilla_10 = round(max(0.0, pagos_anteriores), 2)
        casilla_11 = round(max(0.0, resultado_anterior_complementaria), 2)

        # Resultado intermedio: cuota tras reducción − retenciones − pagos − complementaria
        intermedio = casilla_08 - casilla_09 - casilla_10 - casilla_11
        # Aplicar minoración (max 0)
        casilla_12 = round(max(0.0, intermedio - minoracion), 2)

        return {
            "territory": self._territory_label(ceuta_melilla, la_palma),
            "quarter": quarter,
            "apartado": "I",
            "actividad_tipo": "empresarial",
            "resultado": casilla_12,
            "tipo_aplicado": tipo_pct,
            "num_asalariados": num_asalariados,
            "casillas": {
                "01_rendimiento_neto_modulos": casilla_01,
                "02_tipo_aplicable": casilla_02,
                "03_resultado_empresarial": casilla_03,
                "04_volumen_ingresos_agrario": casilla_04,
                "05_cuota_agraria": casilla_05,
                "06_total_cuotas": casilla_06,
                "07_reducciones": casilla_07,
                "08_resultado_tras_reducciones": casilla_08,
                "09_retenciones_trimestre": casilla_09,
                "10_pagos_anteriores": casilla_10,
                "11_complementaria": casilla_11,
                "12_resultado_final": casilla_12,
            },
            "desglose": {
                "tipo_pct": tipo_pct,
                "criterio_tipo": self._criterio_tipo(num_asalariados),
                "reduccion_pct": reduccion_pct * 100,
                "reduccion_concepto": reduccion_label,
                "minoracion_rendimientos_bajos": minoracion,
                "rendimiento_neto_anterior": round(rendimiento_neto_anterior, 2),
                "ceuta_melilla": ceuta_melilla,
                "la_palma": la_palma,
            },
            "plazo": self._PLAZOS[quarter],
        }

    # ------------------------------------------------------------------
    # Apartado III — Actividades agrícolas/ganaderas/forestales/pesqueras
    # ------------------------------------------------------------------

    def _calculate_agraria(
        self,
        *,
        quarter: int,
        volumen_ingresos_trimestre: float,
        retenciones_trimestre: float,
        pagos_anteriores: float,
        resultado_anterior_complementaria: float,
        ceuta_melilla: bool,
        la_palma: bool,
    ) -> Dict[str, Any]:
        """
        Apartado III del Modelo 131 — actividades agrarias.

        Cuota = 2% × volumen_ingresos_trimestre (excluyendo subvenciones de capital).
        Reducción 60% Ceuta/Melilla / La Palma sobre la cuota.
        NO aplica minoración por rendimientos bajos (sólo apartado I).
        """
        tipo_pct = self._TIPO_AGRARIA

        casilla_04 = round(max(0.0, volumen_ingresos_trimestre), 2)
        casilla_05 = round(casilla_04 * (tipo_pct / 100), 2)
        # Sin componente empresarial en este apartado
        casilla_03 = 0.0
        casilla_06 = round(casilla_03 + casilla_05, 2)

        reduccion_pct, reduccion_label = self._reduccion_territorial(
            ceuta_melilla=ceuta_melilla, la_palma=la_palma,
        )
        casilla_07 = round(casilla_06 * reduccion_pct, 2)
        casilla_08 = round(max(0.0, casilla_06 - casilla_07), 2)

        casilla_09 = round(max(0.0, retenciones_trimestre), 2)
        casilla_10 = round(max(0.0, pagos_anteriores), 2)
        casilla_11 = round(max(0.0, resultado_anterior_complementaria), 2)

        casilla_12 = round(
            max(0.0, casilla_08 - casilla_09 - casilla_10 - casilla_11),
            2,
        )

        return {
            "territory": self._territory_label(ceuta_melilla, la_palma),
            "quarter": quarter,
            "apartado": "III",
            "actividad_tipo": "agraria",
            "resultado": casilla_12,
            "tipo_aplicado": tipo_pct,
            "casillas": {
                "01_rendimiento_neto_modulos": 0.0,
                "02_tipo_aplicable": 0.0,
                "03_resultado_empresarial": casilla_03,
                "04_volumen_ingresos_agrario": casilla_04,
                "05_cuota_agraria": casilla_05,
                "06_total_cuotas": casilla_06,
                "07_reducciones": casilla_07,
                "08_resultado_tras_reducciones": casilla_08,
                "09_retenciones_trimestre": casilla_09,
                "10_pagos_anteriores": casilla_10,
                "11_complementaria": casilla_11,
                "12_resultado_final": casilla_12,
            },
            "desglose": {
                "tipo_pct": tipo_pct,
                "reduccion_pct": reduccion_pct * 100,
                "reduccion_concepto": reduccion_label,
                "ceuta_melilla": ceuta_melilla,
                "la_palma": la_palma,
                "nota": (
                    "Apartado III — actividades agrarias: 2% sobre volumen "
                    "de ingresos del trimestre. Excluir subvenciones de capital."
                ),
            },
            "plazo": self._PLAZOS[quarter],
        }

    # ------------------------------------------------------------------
    # Apartado II — Sin datos-base
    # ------------------------------------------------------------------

    def _calculate_sin_datos_base(
        self,
        *,
        quarter: int,
        volumen_ingresos_trimestre: float,
        retenciones_trimestre: float,
        pagos_anteriores: float,
        resultado_anterior_complementaria: float,
        ceuta_melilla: bool,
        la_palma: bool,
    ) -> Dict[str, Any]:
        """
        Apartado II del Modelo 131 — actividad empresarial sin datos-base.

        Cuota = 2% × volumen_ingresos_trimestre.
        Mismo cálculo que apartado III pero la actividad NO es agraria.
        """
        tipo_pct = self._TIPO_SIN_DATOS_BASE

        casilla_04 = 0.0
        casilla_05 = 0.0
        # Aplicamos el 2% al volumen y lo proyectamos en la casilla 03
        # (resultado actividades empresariales) para distinguirlo del agrario.
        casilla_01 = round(max(0.0, volumen_ingresos_trimestre), 2)
        casilla_02 = tipo_pct
        casilla_03 = round(casilla_01 * (tipo_pct / 100), 2)
        casilla_06 = round(casilla_03 + casilla_05, 2)

        reduccion_pct, reduccion_label = self._reduccion_territorial(
            ceuta_melilla=ceuta_melilla, la_palma=la_palma,
        )
        casilla_07 = round(casilla_06 * reduccion_pct, 2)
        casilla_08 = round(max(0.0, casilla_06 - casilla_07), 2)

        casilla_09 = round(max(0.0, retenciones_trimestre), 2)
        casilla_10 = round(max(0.0, pagos_anteriores), 2)
        casilla_11 = round(max(0.0, resultado_anterior_complementaria), 2)

        casilla_12 = round(
            max(0.0, casilla_08 - casilla_09 - casilla_10 - casilla_11),
            2,
        )

        return {
            "territory": self._territory_label(ceuta_melilla, la_palma),
            "quarter": quarter,
            "apartado": "II",
            "actividad_tipo": "sin_datos_base",
            "resultado": casilla_12,
            "tipo_aplicado": tipo_pct,
            "casillas": {
                "01_rendimiento_neto_modulos": casilla_01,
                "02_tipo_aplicable": casilla_02,
                "03_resultado_empresarial": casilla_03,
                "04_volumen_ingresos_agrario": casilla_04,
                "05_cuota_agraria": casilla_05,
                "06_total_cuotas": casilla_06,
                "07_reducciones": casilla_07,
                "08_resultado_tras_reducciones": casilla_08,
                "09_retenciones_trimestre": casilla_09,
                "10_pagos_anteriores": casilla_10,
                "11_complementaria": casilla_11,
                "12_resultado_final": casilla_12,
            },
            "desglose": {
                "tipo_pct": tipo_pct,
                "reduccion_pct": reduccion_pct * 100,
                "reduccion_concepto": reduccion_label,
                "ceuta_melilla": ceuta_melilla,
                "la_palma": la_palma,
                "nota": (
                    "Apartado II — sin datos-base: 2% sobre volumen de "
                    "ingresos del trimestre."
                ),
            },
            "plazo": self._PLAZOS[quarter],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tipo_segun_asalariados(self, num_asalariados: int) -> float:
        """
        Devuelve el % aplicable según número de asalariados a 1 de enero.

            ≥ 2 asalariados → 4%
            1 asalariado     → 3%
            0 asalariados    → 2%
        """
        if num_asalariados < 0:
            raise ValueError(
                f"num_asalariados '{num_asalariados}' no puede ser negativo."
            )
        if num_asalariados >= 2:
            return self._TIPO_MAS_DE_UN_ASALARIADO
        if num_asalariados == 1:
            return self._TIPO_UN_ASALARIADO
        return self._TIPO_SIN_ASALARIADOS

    def _criterio_tipo(self, num_asalariados: int) -> str:
        """Etiqueta humana del criterio de selección de tipo."""
        if num_asalariados >= 2:
            return f"{num_asalariados} asalariados a 1 enero → 4%"
        if num_asalariados == 1:
            return "1 asalariado a 1 enero → 3%"
        return "Sin asalariados a 1 enero → 2%"

    def _reduccion_territorial(
        self, *, ceuta_melilla: bool, la_palma: bool,
    ) -> tuple[float, str]:
        """
        Devuelve (porcentaje_decimal, etiqueta) de reducción territorial.

        Si ambas flags son True, prevalece Ceuta/Melilla (no son acumulables).
        """
        if ceuta_melilla:
            return self._REDUCCION_CEUTA_MELILLA, "Ceuta/Melilla 60%"
        if la_palma:
            return self._REDUCCION_LA_PALMA, "La Palma 60%"
        return 0.0, "Sin reducción"

    def _territory_label(self, ceuta_melilla: bool, la_palma: bool) -> str:
        if ceuta_melilla:
            return "Ceuta/Melilla"
        if la_palma:
            return "La Palma"
        return "Comun"

    def _minoracion_rendimientos_bajos(self, rendimiento_anterior: float) -> float:
        """
        Devuelve la minoración trimestral por rendimientos bajos del año previo.

        Tabla escalonada plana (NO interpolación lineal):
            ≤ 9.000          → 100 EUR/trim
            9.001 - 10.000   →  75 EUR/trim
            10.001 - 11.000  →  50 EUR/trim
            11.001 - 12.000  →  25 EUR/trim
            > 12.000         →   0 EUR/trim
        """
        if rendimiento_anterior <= 0:
            # Sin dato → no aplica (caller debe pasar el dato real)
            return 0.0
        for threshold, minoracion in self._MINORACION_TABLA:
            if rendimiento_anterior <= threshold:
                return minoracion
        return 0.0
