"""Simulador del Impuesto sobre Sociedades (Modelo 200 + 202).

Calcula la liquidacion IS completa para SL/SLP/SA/nueva creacion
en 7 territorios (comun + 4 forales + ZEC Canarias + Ceuta/Melilla).

Patron: composicion de sub-calculadoras, mismo estilo que irpf_simulator.py.
Todos los importes monetarios en EUR (float), redondeados a 2 decimales en salida.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import logging

from app.utils.is_scales import (
    get_is_regimen,
    calcular_cuota_por_tramos,
    get_is_deduccion_params,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Input / Output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ISInput:
    """Datos de entrada para la liquidacion IS."""

    resultado_contable: float = 0.0
    territorio: str = "Madrid"
    tipo_entidad: str = "sl"  # sl, slp, sa, nueva_creacion
    facturacion_anual: float = 0.0
    ejercicios_con_bi_positiva: int = 10

    # Ajustes
    gastos_no_deducibles: float = 0.0
    ajustes_negativos: float = 0.0
    amortizacion_contable: float = 0.0
    amortizacion_fiscal: float | None = None

    # BINs
    bins_pendientes: float = 0.0

    # Deducciones
    gasto_id: float = 0.0
    gasto_it: float = 0.0
    incremento_ffpp: float = 0.0
    donativos: float = 0.0
    empleados_discapacidad_33: int = 0
    empleados_discapacidad_65: int = 0
    dotacion_ric: float = 0.0

    # Bonificaciones
    es_zec: bool = False
    rentas_ceuta_melilla: float = 0.0

    # Retenciones y pagos previos
    retenciones_ingresos_cuenta: float = 0.0
    pagos_fraccionados_realizados: float = 0.0

    # Alternativa: ingresos - gastos en vez de resultado_contable directo
    ingresos_explotacion: float | None = None
    gastos_explotacion: float | None = None


@dataclass
class ISResult:
    """Resultado completo de la liquidacion IS."""

    resultado_contable: float = 0.0
    ajustes_positivos: float = 0.0
    ajustes_negativos: float = 0.0
    reserva_capitalizacion: float = 0.0
    base_imponible_previa: float = 0.0
    compensacion_bins: float = 0.0
    base_imponible: float = 0.0
    bin_generada: float = 0.0

    tipo_gravamen_aplicado: str = ""
    cuota_integra: float = 0.0

    deducciones_detalle: dict[str, float] = field(default_factory=dict)
    deducciones_total: float = 0.0
    bonificaciones_total: float = 0.0
    cuota_liquida: float = 0.0

    retenciones: float = 0.0
    pagos_fraccionados: float = 0.0
    resultado_liquidacion: float = 0.0
    tipo: str = "a_ingresar"  # a_ingresar | a_devolver
    tipo_efectivo: float = 0.0

    regimen: str = ""
    territorio: str = ""


@dataclass
class IS202Result:
    """Resultado del calculo de pagos fraccionados (Modelo 202)."""

    modalidad: str = ""
    pago_trimestral: float = 0.0
    base_calculo: float = 0.0
    porcentaje_aplicado: float = 0.0


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class ISSimulator:
    """Simulador del Impuesto sobre Sociedades."""

    @classmethod
    def calculate(cls, inp: ISInput) -> ISResult:
        """Calcula la liquidacion IS completa.

        Pipeline:
        1. Resultado contable
        2. + Ajustes positivos
        3. - Ajustes negativos
        4. - Reserva capitalizacion
        5. = Base imponible previa
        6. - Compensacion BINs
        7. = Base imponible (floor 0)
        8. x Tipo gravamen (tramos)
        9. = Cuota integra
        10. - Deducciones
        11. - Bonificaciones
        12. = Cuota liquida
        13. - Retenciones - Pagos fraccionados
        14. = Resultado liquidacion
        """
        result = ISResult()
        regimen = get_is_regimen(inp.territorio, inp.es_zec)
        result.regimen = regimen.nombre
        result.territorio = inp.territorio

        # 1. Resultado contable
        result.resultado_contable = cls._calcular_resultado_contable(inp)

        # 2-3. Ajustes extracontables
        result.ajustes_positivos = cls._calcular_ajustes_positivos(inp)
        result.ajustes_negativos = inp.ajustes_negativos

        # 4. Reserva capitalizacion (Art. 25 LIS)
        base_previa_antes_rc = result.resultado_contable + result.ajustes_positivos - result.ajustes_negativos
        result.reserva_capitalizacion = cls._calcular_reserva_capitalizacion(
            inp, base_previa_antes_rc
        )

        # 5. Base imponible previa
        result.base_imponible_previa = base_previa_antes_rc - result.reserva_capitalizacion

        # 6. Compensacion BINs (Art. 26 LIS)
        result.compensacion_bins = cls._calcular_bins(inp, result.base_imponible_previa)

        # 7. Base imponible (floor 0)
        bi_raw = result.base_imponible_previa - result.compensacion_bins
        if bi_raw < 0:
            result.base_imponible = 0.0
            result.bin_generada = round(abs(bi_raw), 2)
        else:
            result.base_imponible = round(bi_raw, 2)
            result.bin_generada = 0.0

        # RIC Canarias: reduce base imponible (limitado a 90% beneficio no distribuido)
        if inp.dotacion_ric > 0 and result.base_imponible > 0:
            limite_ric = result.resultado_contable * 0.9 if result.resultado_contable > 0 else 0
            reduccion_ric = min(inp.dotacion_ric, limite_ric, result.base_imponible)
            result.base_imponible = round(result.base_imponible - reduccion_ric, 2)

        # 8. Seleccionar tramos y calcular cuota
        tramos = cls._seleccionar_tramos(regimen, inp)
        result.cuota_integra = calcular_cuota_por_tramos(result.base_imponible, tramos)
        result.tipo_gravamen_aplicado = cls._describir_tipo(tramos)

        # 9-10. Deducciones
        result.deducciones_detalle = cls._calcular_deducciones(inp, result.cuota_integra)
        result.deducciones_total = round(sum(result.deducciones_detalle.values()), 2)

        # 11. Bonificaciones (Ceuta/Melilla)
        result.bonificaciones_total = cls._calcular_bonificaciones(
            inp, result.cuota_integra, regimen.bonificacion_cuota
        )

        # 12. Cuota liquida
        result.cuota_liquida = round(
            max(0.0, result.cuota_integra - result.deducciones_total - result.bonificaciones_total), 2
        )

        # 13-14. Resultado liquidacion
        result.retenciones = inp.retenciones_ingresos_cuenta
        result.pagos_fraccionados = inp.pagos_fraccionados_realizados
        result.resultado_liquidacion = round(
            result.cuota_liquida - result.retenciones - result.pagos_fraccionados, 2
        )
        result.tipo = "a_devolver" if result.resultado_liquidacion < 0 else "a_ingresar"

        # Tipo efectivo
        if result.resultado_contable != 0:
            result.tipo_efectivo = round(
                (result.cuota_liquida / abs(result.resultado_contable)) * 100, 2
            )

        return result

    @classmethod
    def calcular_202(
        cls,
        modalidad: str = "art40_2",
        cuota_integra_ultimo: float = 0.0,
        deducciones_bonificaciones_ultimo: float = 0.0,
        retenciones_ultimo: float = 0.0,
        base_imponible_periodo: float = 0.0,
        facturacion_anual: float = 0.0,
        territorio: str = "Madrid",
    ) -> IS202Result:
        """Calcula el pago fraccionado trimestral (Modelo 202).

        Dos modalidades:
        - art40_2: 18% de (cuota_integra - deducciones_bonificaciones - retenciones)
        - art40_3: 17% de base_imponible_periodo (24% si facturacion >10M)
        """
        result = IS202Result(modalidad=modalidad)

        if modalidad == "art40_2":
            base = cuota_integra_ultimo - deducciones_bonificaciones_ultimo - retenciones_ultimo
            base = max(0.0, base)
            result.base_calculo = round(base, 2)
            result.porcentaje_aplicado = 18.0
            result.pago_trimestral = round(base * 0.18, 2)

        elif modalidad == "art40_3":
            pct = 24.0 if facturacion_anual > 10_000_000 else 17.0
            result.base_calculo = round(base_imponible_periodo, 2)
            result.porcentaje_aplicado = pct
            result.pago_trimestral = round(base_imponible_periodo * pct / 100, 2)

        return result

    # -------------------------------------------------------------------
    # Sub-calculadoras privadas
    # -------------------------------------------------------------------

    @staticmethod
    def _calcular_resultado_contable(inp: ISInput) -> float:
        """Paso 1: resultado contable (directo o ingresos-gastos)."""
        if inp.resultado_contable != 0:
            return inp.resultado_contable
        if inp.ingresos_explotacion is not None and inp.gastos_explotacion is not None:
            return round(inp.ingresos_explotacion - inp.gastos_explotacion, 2)
        return 0.0

    @staticmethod
    def _calcular_ajustes_positivos(inp: ISInput) -> float:
        """Paso 2: ajustes extracontables positivos."""
        ajustes = inp.gastos_no_deducibles
        # Diferencia amortizacion si fiscal > contable
        if inp.amortizacion_fiscal is not None and inp.amortizacion_fiscal > inp.amortizacion_contable:
            ajustes += inp.amortizacion_fiscal - inp.amortizacion_contable
        return round(ajustes, 2)

    @staticmethod
    def _calcular_reserva_capitalizacion(inp: ISInput, base_previa: float) -> float:
        """Paso 4: reserva capitalizacion (Art. 25 LIS).

        10% del incremento de fondos propios, limitado al 10% de la base imponible previa.
        """
        if inp.incremento_ffpp <= 0 or base_previa <= 0:
            return 0.0
        deduccion_params = get_is_deduccion_params(inp.territorio)
        rc_pct = deduccion_params.reserva_cap_pct / 100
        reserva = inp.incremento_ffpp * rc_pct
        limite = base_previa * 0.10
        return round(min(reserva, limite), 2)

    @staticmethod
    def _calcular_bins(inp: ISInput, base_previa: float) -> float:
        """Paso 6: compensacion de BINs (Art. 26 LIS).

        Limites:
        - facturacion >20M: maximo 70% de base_previa
        - facturacion <1M: 100%
        - resto: 100%
        """
        if inp.bins_pendientes <= 0 or base_previa <= 0:
            return 0.0
        if inp.facturacion_anual > 20_000_000:
            limite = base_previa * 0.70
        else:
            limite = base_previa  # 100%
        return round(min(inp.bins_pendientes, limite), 2)

    @staticmethod
    def _seleccionar_tramos(regimen, inp: ISInput):
        """Paso 8: selecciona escala segun tipo entidad y facturacion."""
        if inp.tipo_entidad == "nueva_creacion" and inp.ejercicios_con_bi_positiva <= 2:
            return regimen.tramos_nueva_creacion
        if inp.facturacion_anual > 0 and inp.facturacion_anual < 1_000_000:
            return regimen.tramos_pyme
        return regimen.tramos_general

    @staticmethod
    def _describir_tipo(tramos) -> str:
        """Genera descripcion legible del tipo gravamen."""
        if len(tramos) == 1:
            return f"{tramos[0].tipo}%"
        tipos = [f"{t.tipo}%" for t in tramos]
        return "/".join(tipos)

    @staticmethod
    def _calcular_deducciones(inp: ISInput, cuota_integra: float) -> dict[str, float]:
        """Paso 10: deducciones IS.

        I+D, IT, donativos limitados por % cuota integra.
        Empleo discapacitados sin limite.
        """
        if cuota_integra <= 0:
            return {}

        params = get_is_deduccion_params(inp.territorio)
        detalle: dict[str, float] = {}

        # I+D (Art. 35.1 LIS)
        if inp.gasto_id > 0:
            detalle["id"] = round(inp.gasto_id * params.id_pct / 100, 2)

        # IT (Art. 35.2 LIS)
        if inp.gasto_it > 0:
            detalle["it"] = round(inp.gasto_it * params.it_pct / 100, 2)

        # Donativos mecenazgo (Ley 49/2002) — 35%
        if inp.donativos > 0:
            detalle["donativos"] = round(inp.donativos * 0.35, 2)

        # Aplicar limite global (% cuota integra) a deducciones limitadas
        total_limitadas = sum(detalle.values())
        limite = cuota_integra * params.limite_deducciones_pct / 100
        if total_limitadas > limite:
            factor = limite / total_limitadas
            for k in detalle:
                detalle[k] = round(detalle[k] * factor, 2)

        # Empleo discapacitados (Art. 38 LIS) — sin limite
        empleo_33 = inp.empleados_discapacidad_33 * 9_000
        empleo_65 = inp.empleados_discapacidad_65 * 12_000
        empleo_total = empleo_33 + empleo_65
        if empleo_total > 0:
            detalle["empleo_discapacidad"] = float(empleo_total)

        return detalle

    @staticmethod
    def _calcular_bonificaciones(
        inp: ISInput, cuota_integra: float, bonificacion_pct: float
    ) -> float:
        """Paso 11: bonificaciones (Ceuta/Melilla 50%).

        Proporcional a rentas_ceuta_melilla / resultado_contable.
        """
        if bonificacion_pct <= 0 or cuota_integra <= 0:
            return 0.0
        if inp.rentas_ceuta_melilla <= 0:
            return 0.0
        rc = abs(inp.resultado_contable) if inp.resultado_contable != 0 else 1.0
        proporcion = min(inp.rentas_ceuta_melilla / rc, 1.0)
        return round(cuota_integra * bonificacion_pct * proporcion, 2)
