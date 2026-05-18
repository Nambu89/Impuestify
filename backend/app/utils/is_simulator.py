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
    bin_limite_pct,
    reserva_capitalizacion_pct_2025,
    # MEDIA gaps (auditoria 2026-05) — Wave C2
    tributacion_minima_pct,
    aplica_tributacion_minima,
    aplica_reserva_nivelacion,
    RESERVA_NIVELACION_PCT,
    RESERVA_NIVELACION_MAX_EUR,
    COOPERATIVA_TIPO_PROTEGIDA,
    COOPERATIVA_ESP_PROTEGIDA_BONIFICACION_PCT,
    ID_PCT_EXCESO_MEDIA,
    PAGO_FRACC_MINIMO_PCT_GENERAL,
    PAGO_FRACC_MINIMO_PCT_BANCA,
    PAGO_FRACC_MINIMO_INCN_THRESHOLD,
    zec_techo_base,
    calcular_deduccion_cine,
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
    tipo_entidad: str = "sl"  # sl, slp, sa, nueva_creacion, cooperativa
    facturacion_anual: float = 0.0
    ejercicios_con_bi_positiva: int = 10
    ejercicio: int = 2024  # 2024 default (pre-Ley 7/2024). Pasar 2025+ para reformas.
    incremento_plantilla_pct: float = 0.0  # Para reserva capitalizacion 2025+ (Ley 7/2024)

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

    # ------------------------------------------------------------------
    # Wave C2 (MEDIA gaps auditoria 2026-05) — todos opt-in con default 0/False
    # ------------------------------------------------------------------

    # M1 — Reserva de nivelacion Art. 105 LIS (ERD INCN<10M)
    # Importe que la empresa quiere minorar de la BI positiva (max 10% BI o 1M EUR).
    reserva_nivelacion: float = 0.0

    # M2 — Tributacion minima Art. 30 bis LIS
    # Aplicabilidad: INCN >= 20M o grupo consolidado.
    grupo_consolidado: bool = False
    es_banca_o_hidrocarburos: bool = False  # tributacion minima 18% / pf minimo 25%

    # M4 — Cooperativas (Ley 20/1990)
    # Si tipo_entidad="cooperativa" se aplica 20% sobre BI cooperativa.
    cooperativa_especialmente_protegida: bool = False  # +50% bonificacion cuota

    # M5 — I+D 42% sobre exceso media 2 anos anteriores (Art. 35.1.b LIS)
    media_id_2_anos_anteriores: float = 0.0

    # M5 — I+D adicionales (Art. 35.1.b LIS)
    gasto_id_personal_investigador: float = 0.0  # +17% adicional
    gasto_id_inmovilizado_afecto: float = 0.0  # +8% adicional

    # M6 — ZEC techo por empleos (Art. 43 Ley 19/1994)
    zec_empleos_creados: int = 0  # min 5 (3 areas remotas, no validado aqui)

    # M9 — Deducciones cinematograficas (Art. 36 LIS)
    gasto_produccion_cinematografica: float = 0.0
    tipo_produccion_cinematografica: str = "espanola"  # espanola | extranjera | serie
    cine_csi_o_cataluna: bool = False  # techo reforzado 40M


@dataclass
class ISResult:
    """Resultado completo de la liquidacion IS."""

    resultado_contable: float = 0.0
    ajustes_positivos: float = 0.0
    ajustes_negativos: float = 0.0
    reserva_capitalizacion: float = 0.0
    reserva_nivelacion: float = 0.0  # Wave C2 — Art. 105 LIS
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

    # Wave C2 — Tributacion minima Art. 30 bis LIS
    cuota_liquida_minima: float = 0.0
    tributacion_minima_aplicada: bool = False

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

    # Wave C2 — DA 14a LIS: pago minimo INCN >= 10M (modalidad art40_3)
    pago_minimo: float = 0.0
    pago_minimo_aplicado: bool = False


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
        regimen = get_is_regimen(inp.territorio, inp.es_zec, ejercicio=inp.ejercicio)
        result.regimen = regimen.nombre
        result.territorio = inp.territorio

        # 1. Resultado contable
        result.resultado_contable = cls._calcular_resultado_contable(inp)

        # 2-3. Ajustes extracontables
        result.ajustes_positivos = cls._calcular_ajustes_positivos(inp)
        result.ajustes_negativos = inp.ajustes_negativos

        # 4. Reserva capitalizacion (Art. 25 LIS)
        base_previa_antes_rc = (
            result.resultado_contable + result.ajustes_positivos - result.ajustes_negativos
        )
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

        # 7.bis — Reserva de nivelacion (Art. 105 LIS) — solo ERD INCN<10M
        result.reserva_nivelacion = cls._calcular_reserva_nivelacion(inp, result.base_imponible)
        if result.reserva_nivelacion > 0:
            result.base_imponible = round(result.base_imponible - result.reserva_nivelacion, 2)

        # RIC Canarias: reduce base imponible (limitado a 90% beneficio no distribuido)
        if inp.dotacion_ric > 0 and result.base_imponible > 0:
            limite_ric = result.resultado_contable * 0.9 if result.resultado_contable > 0 else 0
            reduccion_ric = min(inp.dotacion_ric, limite_ric, result.base_imponible)
            result.base_imponible = round(result.base_imponible - reduccion_ric, 2)

        # 8. Seleccionar tramos y calcular cuota
        # M4 — Cooperativas fiscalmente protegidas: 20% sobre la BI cooperativa.
        if inp.tipo_entidad == "cooperativa":
            result.cuota_integra = round(
                result.base_imponible * COOPERATIVA_TIPO_PROTEGIDA / 100, 2
            )
            result.tipo_gravamen_aplicado = f"{COOPERATIVA_TIPO_PROTEGIDA}% (cooperativa)"
        else:
            tramos = cls._seleccionar_tramos(regimen, inp)
            # M6 — ZEC techo por empleos (Art. 43 Ley 19/1994)
            if inp.es_zec and inp.zec_empleos_creados > 0:
                result.cuota_integra = cls._calcular_cuota_zec_con_techo(
                    result.base_imponible, inp.zec_empleos_creados, tramos
                )
                result.tipo_gravamen_aplicado = (
                    f"ZEC 4% hasta techo + 25% exceso " f"({inp.zec_empleos_creados} empleos)"
                )
            else:
                result.cuota_integra = calcular_cuota_por_tramos(result.base_imponible, tramos)
                result.tipo_gravamen_aplicado = cls._describir_tipo(tramos)

        # 9-10. Deducciones
        result.deducciones_detalle = cls._calcular_deducciones(inp, result.cuota_integra)
        result.deducciones_total = round(sum(result.deducciones_detalle.values()), 2)

        # 11. Bonificaciones (Ceuta/Melilla + cooperativas especialmente protegidas)
        result.bonificaciones_total = cls._calcular_bonificaciones(
            inp, result.cuota_integra, regimen.bonificacion_cuota
        )
        # M4 — Cooperativas especialmente protegidas: 50% sobre cuota integra
        # (Art. 34.2 Ley 20/1990). Acumulable a Ceuta/Melilla en proporcion.
        if inp.tipo_entidad == "cooperativa" and inp.cooperativa_especialmente_protegida:
            bonif_coop = round(result.cuota_integra * COOPERATIVA_ESP_PROTEGIDA_BONIFICACION_PCT, 2)
            result.bonificaciones_total = round(result.bonificaciones_total + bonif_coop, 2)

        # 12. Cuota liquida
        result.cuota_liquida = round(
            max(0.0, result.cuota_integra - result.deducciones_total - result.bonificaciones_total),
            2,
        )

        # 12.bis — Tributacion minima (Art. 30 bis LIS) — INCN >= 20M o consolidado
        cls._aplicar_tributacion_minima(inp, result)

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
        # Wave C2 — DA 14a LIS pago minimo
        resultado_contable_periodo: float = 0.0,
        ajustes_positivos_periodo: float = 0.0,
        es_banca_o_hidrocarburos: bool = False,
    ) -> IS202Result:
        """Calcula el pago fraccionado trimestral (Modelo 202).

        Dos modalidades:
        - art40_2: 18% de (cuota_integra - deducciones_bonificaciones - retenciones)
        - art40_3: 17% de base_imponible_periodo (24% si facturacion >10M)

        DA 14a LIS — pago minimo (solo modalidad art40_3, INCN >= 10M):
        - 23% del resultado contable positivo + ajustes positivos
        - 25% para entidades de credito y exploracion/produccion hidrocarburos
        Si el calculo normal queda por debajo del minimo, se eleva al minimo.
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

            # DA 14a LIS — pago fraccionado minimo
            if facturacion_anual >= PAGO_FRACC_MINIMO_INCN_THRESHOLD:
                base_minimo = max(
                    0.0,
                    resultado_contable_periodo + ajustes_positivos_periodo,
                )
                pct_minimo = (
                    PAGO_FRACC_MINIMO_PCT_BANCA
                    if es_banca_o_hidrocarburos
                    else PAGO_FRACC_MINIMO_PCT_GENERAL
                )
                pago_minimo = round(base_minimo * pct_minimo / 100, 2)
                result.pago_minimo = pago_minimo
                if pago_minimo > result.pago_trimestral:
                    result.pago_trimestral = pago_minimo
                    result.pago_minimo_aplicado = True
                    result.porcentaje_aplicado = pct_minimo

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
        if (
            inp.amortizacion_fiscal is not None
            and inp.amortizacion_fiscal > inp.amortizacion_contable
        ):
            ajustes += inp.amortizacion_fiscal - inp.amortizacion_contable
        return round(ajustes, 2)

    @staticmethod
    def _calcular_reserva_capitalizacion(inp: ISInput, base_previa: float) -> float:
        """Paso 4: reserva capitalizacion (Art. 25 LIS).

        Pre-Ley 7/2024 (ejercicio < 2025):
          10% del incremento de fondos propios, limitado al 10% de la base imponible previa.
        Ley 7/2024 (ejercicio >= 2025):
          20% base, escala 23/26.5/30% segun incremento plantilla, limite 20% base previa.
        """
        if inp.incremento_ffpp <= 0 or base_previa <= 0:
            return 0.0
        deduccion_params = get_is_deduccion_params(inp.territorio, inp.ejercicio)
        # En 2025+ aplicar escala plantilla si esta informada.
        if inp.ejercicio >= 2025 and inp.incremento_plantilla_pct > 0:
            rc_pct = reserva_capitalizacion_pct_2025(inp.incremento_plantilla_pct) / 100
        else:
            rc_pct = deduccion_params.reserva_cap_pct / 100
        reserva = inp.incremento_ffpp * rc_pct
        limite = base_previa * (deduccion_params.reserva_cap_limite_pct / 100)
        return round(min(reserva, limite), 2)

    @staticmethod
    def _calcular_bins(inp: ISInput, base_previa: float) -> float:
        """Paso 6: compensacion de BINs (Art. 26 LIS).

        Limites segun INCN (parametrizados en is_scales.bin_limite_pct):
        - INCN < 20M     : 100% (suelo 1M libre)
        - 20M <= INCN < 60M : 70%
        - INCN >= 60M    : 50%
        """
        if inp.bins_pendientes <= 0 or base_previa <= 0:
            return 0.0
        pct = bin_limite_pct(inp.facturacion_anual) / 100
        limite = base_previa * pct
        return round(min(inp.bins_pendientes, limite), 2)

    @staticmethod
    def _seleccionar_tramos(regimen, inp: ISInput):
        """Paso 8: selecciona escala segun tipo entidad y facturacion (INCN)."""
        if inp.tipo_entidad == "nueva_creacion" and inp.ejercicios_con_bi_positiva <= 2:
            return regimen.tramos_nueva_creacion
        # Microempresa: INCN < 1M (RDL 4/2024 + Ley 7/2024)
        if 0 < inp.facturacion_anual < 1_000_000:
            return regimen.tramos_microempresa
        # ERD: 1M <= INCN < 10M (Empresa Reducida Dimension Art. 101 LIS)
        if 1_000_000 <= inp.facturacion_anual < 10_000_000:
            return regimen.tramos_erd
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
        Cinematograficas Art. 36 LIS — limite 25% cuota junto al resto (Art. 39.1).
        """
        if cuota_integra <= 0:
            return {}

        params = get_is_deduccion_params(inp.territorio, inp.ejercicio)
        detalle: dict[str, float] = {}

        # I+D (Art. 35.1 LIS) — base (25% / 30% Bizkaia-Gipuzkoa)
        if inp.gasto_id > 0:
            base_id = inp.gasto_id
            id_base = 0.0
            id_exceso = 0.0
            # M5 — Si gasto > media 2 anos anteriores: 42% sobre el exceso (Art. 35.1.b LIS).
            # Solo aplica al regimen comun (forales mantienen su porcentaje base).
            if (
                inp.media_id_2_anos_anteriores > 0
                and base_id > inp.media_id_2_anos_anteriores
                and params.id_pct == 25.0  # solo regimen comun
            ):
                exceso = base_id - inp.media_id_2_anos_anteriores
                id_base = round(inp.media_id_2_anos_anteriores * params.id_pct / 100, 2)
                id_exceso = round(exceso * ID_PCT_EXCESO_MEDIA / 100, 2)
                detalle["id"] = round(id_base + id_exceso, 2)
            else:
                detalle["id"] = round(base_id * params.id_pct / 100, 2)

            # M5 — adicionales: +17% personal investigador, +8% inmovilizado afecto
            if inp.gasto_id_personal_investigador > 0:
                detalle["id_personal"] = round(inp.gasto_id_personal_investigador * 17.0 / 100, 2)
            if inp.gasto_id_inmovilizado_afecto > 0:
                detalle["id_inmovilizado"] = round(inp.gasto_id_inmovilizado_afecto * 8.0 / 100, 2)

        # IT (Art. 35.2 LIS)
        if inp.gasto_it > 0:
            detalle["it"] = round(inp.gasto_it * params.it_pct / 100, 2)

        # Donativos mecenazgo Sociedades (Art. 20 Ley 49/2002) — 40% (NO 35% IRPF)
        if inp.donativos > 0:
            detalle["donativos"] = round(inp.donativos * params.donativos_pct / 100, 2)

        # M9 — Deducciones cinematograficas (Art. 36 LIS).
        # Limite especifico 20M general / 40M reforzado, aplicado dentro de
        # `calcular_deduccion_cine`. Limite global 25% cuota integra (Art. 39.1)
        # se aplica conjuntamente con I+D/IT/donativos.
        if inp.gasto_produccion_cinematografica > 0:
            ded_cine = calcular_deduccion_cine(
                inp.gasto_produccion_cinematografica,
                tipo_produccion=inp.tipo_produccion_cinematografica,
                csi_o_cataluna=inp.cine_csi_o_cataluna,
            )
            if ded_cine > 0:
                detalle["cinematografica"] = ded_cine

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

    # -------------------------------------------------------------------
    # Wave C2 (MEDIA gaps auditoria 2026-05) — sub-calculadoras nuevas
    # -------------------------------------------------------------------

    @staticmethod
    def _calcular_reserva_nivelacion(inp: ISInput, base_imponible: float) -> float:
        """M1 — Reserva de nivelacion (Art. 105 LIS).

        Solo ERD (INCN < 10M).  Minora la BI positiva en hasta 10% (max 1M EUR).
        El simulador toma `inp.reserva_nivelacion` como importe solicitado por
        el contribuyente y aplica el limite legal.
        """
        if inp.reserva_nivelacion <= 0 or base_imponible <= 0:
            return 0.0
        if not aplica_reserva_nivelacion(inp.facturacion_anual):
            return 0.0
        limite_pct = base_imponible * RESERVA_NIVELACION_PCT / 100
        return round(min(inp.reserva_nivelacion, limite_pct, RESERVA_NIVELACION_MAX_EUR), 2)

    @staticmethod
    def _calcular_cuota_zec_con_techo(base_imponible: float, empleos: int, tramos) -> float:
        """M6 — ZEC techo por empleos (Art. 43 Ley 19/1994).

        Aplica 4% sobre el tramo de BI hasta el techo permitido segun empleos
        creados; el exceso tributa al tipo general (25%).

        Si empleos < 5 (minimo legal), no se cumple requisito ZEC y se aplica
        el tipo general sobre toda la BI.
        """
        if base_imponible <= 0:
            return 0.0
        techo = zec_techo_base(empleos)
        if techo <= 0:
            # Sin minimo de empleos no aplica beneficio ZEC: tipo general 25%.
            return round(base_imponible * 25.0 / 100, 2)
        bi_zec = min(base_imponible, techo)
        bi_exceso = max(0.0, base_imponible - techo)
        cuota_zec = bi_zec * 4.0 / 100
        cuota_exceso = bi_exceso * 25.0 / 100
        return round(cuota_zec + cuota_exceso, 2)

    @staticmethod
    def _aplicar_tributacion_minima(inp: ISInput, result: ISResult) -> None:
        """M2 — Tributacion minima (Art. 30 bis LIS).

        Si la entidad esta sometida a tributacion minima (INCN >= 20M o
        consolidado), la cuota liquida no puede ser inferior al
        % minimo (15% general / 10% nueva creacion / 18% banca-hidrocarburos)
        sobre la BI positiva.  Las retenciones y pagos fraccionados no
        intervienen en este calculo.

        Si aplica y eleva la cuota, marca `tributacion_minima_aplicada=True`.
        """
        if not aplica_tributacion_minima(inp.facturacion_anual, inp.grupo_consolidado):
            return
        if result.base_imponible <= 0:
            return

        es_nueva = inp.tipo_entidad == "nueva_creacion" and inp.ejercicios_con_bi_positiva <= 2
        pct_minimo = tributacion_minima_pct(
            es_nueva_creacion=es_nueva,
            es_banca_hidrocarburos=inp.es_banca_o_hidrocarburos,
        )
        cuota_minima = round(result.base_imponible * pct_minimo / 100, 2)
        result.cuota_liquida_minima = cuota_minima
        if cuota_minima > result.cuota_liquida:
            result.cuota_liquida = cuota_minima
            result.tributacion_minima_aplicada = True
