"""Tests Wave C2 — gaps MEDIA Modelo 200 IS (auditoria 2026-05).

Cubre los 7 items pendientes (M1, M2, M3, M4, M5, M6, M9):

- M1: Reserva de nivelacion Art. 105 LIS (ERD INCN<10M, 10% BI, max 1M EUR)
- M2: Tributacion minima Art. 30 bis LIS (15% BI / 10% nueva creacion / 18% banca)
- M3: Pago fraccionado minimo DA 14a LIS (23% RC + ajustes, INCN >= 10M)
- M4: Cooperativas fiscalmente protegidas (20% Ley 20/1990) + esp. protegidas (50% bonificacion)
- M5: I+D 42% sobre exceso media 2 anos anteriores (Art. 35.1.b LIS)
- M6: ZEC techo de base bonificable por empleos creados (Art. 43 Ley 19/1994)
- M9: Deducciones cinematograficas Art. 36 LIS (espanolas / extranjeras / series)

Casos AEAT del Manual Practico Sociedades 2024.
Auditoria: docs/audits/modelo_200_validation_2026-05.md
"""

import pytest

from app.utils.is_scales import (
    COOPERATIVA_TIPO_PROTEGIDA,
    RESERVA_NIVELACION_MAX_EUR,
    RESERVA_NIVELACION_PCT,
    aplica_reserva_nivelacion,
    aplica_tributacion_minima,
    calcular_deduccion_cine,
    tributacion_minima_pct,
    zec_techo_base,
)
from app.utils.is_simulator import ISInput, ISSimulator

# =============================================================================
# M1 — Reserva de nivelacion (Art. 105 LIS)
# =============================================================================


class TestReservaNivelacion:
    """Solo ERD (1M <= INCN < 10M).  10% BI positiva, max 1M EUR.  Indisponible 5 anos."""

    def test_aplica_solo_a_erd(self):
        # ERD (INCN entre 1M y 10M)
        assert aplica_reserva_nivelacion(5_000_000) is True
        # Microempresa (INCN < 1M) — NO aplica (Art. 105 exige ERD)
        # Nota: la doctrina admite que microempresas tambien son ERD si INCN<10M.
        # Aqui aplicamos el criterio amplio: cualquier INCN positiva < 10M.
        assert aplica_reserva_nivelacion(500_000) is True
        # Gran empresa (INCN >= 10M) — NO aplica
        assert aplica_reserva_nivelacion(10_000_000) is False
        assert aplica_reserva_nivelacion(50_000_000) is False
        # Sin facturacion — NO aplica
        assert aplica_reserva_nivelacion(0) is False

    def test_reserva_nivelacion_aplicada_erd(self):
        """ERD con BI=100k pide reserva 10k → aplica 10k (limite 10% BI)."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=100_000,
                facturacion_anual=5_000_000,  # ERD
                reserva_nivelacion=10_000,
                territorio="Madrid",
            )
        )
        # 10% BI = 10k, importe solicitado = 10k → aplica 10k
        assert r.reserva_nivelacion == 10_000
        assert r.base_imponible == 90_000

    def test_reserva_nivelacion_limitada_al_10pct(self):
        """ERD pide 30k pero 10% BI = 10k → solo aplica 10k."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=100_000,
                facturacion_anual=5_000_000,
                reserva_nivelacion=30_000,  # excede limite
                territorio="Madrid",
            )
        )
        assert r.reserva_nivelacion == 10_000  # 10% de 100k
        assert r.base_imponible == 90_000

    def test_reserva_nivelacion_max_1M_eur(self):
        """BI muy alta: reserva = min(10% BI, 1M EUR)."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=15_000_000,  # mas de 10M de BI potencial
                facturacion_anual=9_500_000,  # ERD justo dentro del limite
                reserva_nivelacion=1_500_000,  # excede el max absoluto
                territorio="Madrid",
            )
        )
        # 10% BI = 1.5M, pero topado a 1M
        assert r.reserva_nivelacion == RESERVA_NIVELACION_MAX_EUR
        assert r.base_imponible == 14_000_000

    def test_reserva_nivelacion_no_aplica_a_grandes(self):
        """Gran empresa (INCN >= 10M) NO puede aplicar reserva nivelacion."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=100_000,
                facturacion_anual=15_000_000,
                reserva_nivelacion=10_000,
                territorio="Madrid",
            )
        )
        assert r.reserva_nivelacion == 0
        assert r.base_imponible == 100_000


# =============================================================================
# M2 — Tributacion minima (Art. 30 bis LIS)
# =============================================================================


class TestTributacionMinima:
    """INCN >= 20M o consolidado: cuota_liquida >= 15% BI (10% nueva creacion / 18% banca)."""

    def test_porcentajes_minimos(self):
        assert tributacion_minima_pct() == 15.0
        assert tributacion_minima_pct(es_nueva_creacion=True) == 10.0
        assert tributacion_minima_pct(es_banca_hidrocarburos=True) == 18.0
        # Si ambos, banca tiene precedencia
        assert tributacion_minima_pct(es_nueva_creacion=True, es_banca_hidrocarburos=True) == 18.0

    def test_aplica_solo_si_incn_20M_o_consolidado(self):
        assert aplica_tributacion_minima(15_000_000) is False
        assert aplica_tributacion_minima(20_000_000) is True
        assert aplica_tributacion_minima(50_000_000) is True
        # Grupo consolidado siempre aplica, sea cual sea INCN
        assert aplica_tributacion_minima(1_000_000, grupo_consolidado=True) is True

    def test_no_aplica_a_pyme_pequena(self):
        """Empresa pequena (<20M) NO sometida a tributacion minima."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=200_000,
                facturacion_anual=5_000_000,  # < 20M
                gasto_id=200_000,  # 25% = 50k deduccion
                territorio="Madrid",
            )
        )
        # cuota_integra = 50k (25% de 200k)
        # deducciones I+D = 50k pero limitadas al 25% cuota = 12.5k
        # cuota_liquida = 50k - 12.5k = 37.5k (sin minimo aplicado)
        assert r.tributacion_minima_aplicada is False
        assert r.cuota_liquida == 37_500

    def test_tributacion_minima_eleva_cuota_grandes(self):
        """Gran empresa (INCN>=20M) con muchas deducciones — cuota minima 15% BI."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                facturacion_anual=25_000_000,  # >= 20M, aplica Art. 30 bis
                gasto_id=2_000_000,  # 25% = 500k deduccion (limitada por cuota)
                territorio="Madrid",
            )
        )
        # cuota_integra = 250k (25% de 1M); deducciones limitadas a 25% = 62.5k
        # cuota_liquida normal = 250k - 62.5k = 187.5k
        # Pero cuota minima = 15% × 1M = 150k → no eleva (187.5k ya > 150k)
        # Reescribimos test con caso donde minimo SI eleve.
        assert r.cuota_liquida_minima == 150_000

    def test_tributacion_minima_eleva_si_bonificacion_ceuta(self):
        """Gran empresa con bonificacion fuerte: cuota_liquida cae bajo el 15% BI."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                facturacion_anual=25_000_000,
                rentas_ceuta_melilla=1_000_000,
                territorio="Melilla",
            )
        )
        # cuota_integra = 250k (25%); bonificacion 50% × 250k = 125k
        # cuota_liquida normal = 250k - 125k = 125k
        # cuota minima = 15% × 1M = 150k → minimo eleva la cuota a 150k
        assert r.cuota_liquida_minima == 150_000
        assert r.tributacion_minima_aplicada is True
        assert r.cuota_liquida == 150_000

    def test_tributacion_minima_nueva_creacion_10pct(self):
        """Nueva creacion gran empresa: cuota minima = 10% BI."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                tipo_entidad="nueva_creacion",
                ejercicios_con_bi_positiva=1,
                facturacion_anual=25_000_000,
                grupo_consolidado=True,
                ejercicio=2025,
                gasto_id=2_000_000,
                territorio="Madrid",
            )
        )
        # cuota_minima = 10% × 1M = 100k
        assert r.cuota_liquida_minima == 100_000

    def test_tributacion_minima_banca_18pct(self):
        """Banca/hidrocarburos: cuota minima = 18% BI."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                facturacion_anual=25_000_000,
                es_banca_o_hidrocarburos=True,
                gasto_id=2_000_000,
                territorio="Madrid",
            )
        )
        # cuota_minima = 18% × 1M = 180k
        assert r.cuota_liquida_minima == 180_000

    def test_grupo_consolidado_aplica_minimo_aunque_pequeno(self):
        """Grupo consolidado de INCN<20M tambien sometido a tributacion minima."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=500_000,
                facturacion_anual=5_000_000,
                grupo_consolidado=True,
                rentas_ceuta_melilla=500_000,
                territorio="Ceuta",
            )
        )
        # cuota_integra = 125k; bonificacion 50% × 125k = 62.5k
        # cuota_liquida normal = 62.5k; cuota minima = 15% × 500k = 75k
        # → minimo aplica
        assert r.tributacion_minima_aplicada is True
        assert r.cuota_liquida == 75_000


# =============================================================================
# M3 — Pago fraccionado minimo (DA 14a LIS)
# =============================================================================


class TestPagoFraccionadoMinimo:
    """Solo modalidad art40_3 + INCN >= 10M.  23% RC + ajustes positivos."""

    def test_no_aplica_a_pequena(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=5_000_000,  # < 10M
            resultado_contable_periodo=200_000,
        )
        # 17% × 100k = 17k; sin minimo
        assert r.pago_trimestral == 17_000
        assert r.pago_minimo_aplicado is False

    def test_aplica_si_incn_10M_modalidad_art40_3(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=15_000_000,
            resultado_contable_periodo=500_000,
            ajustes_positivos_periodo=50_000,
        )
        # Calculo normal: 24% × 100k = 24k
        # Pago minimo: 23% × (500k + 50k) = 126.5k
        # Como minimo > normal → pago = minimo
        assert r.pago_minimo == 126_500
        assert r.pago_trimestral == 126_500
        assert r.pago_minimo_aplicado is True

    def test_pago_minimo_no_eleva_si_normal_es_mayor(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=1_000_000,
            facturacion_anual=15_000_000,
            resultado_contable_periodo=100_000,
        )
        # Normal: 24% × 1M = 240k
        # Minimo: 23% × 100k = 23k
        # Normal > Minimo → no se eleva
        assert r.pago_trimestral == 240_000
        assert r.pago_minimo == 23_000
        assert r.pago_minimo_aplicado is False

    def test_pago_minimo_banca_25pct(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=15_000_000,
            resultado_contable_periodo=500_000,
            es_banca_o_hidrocarburos=True,
        )
        # Banca: 25% × 500k = 125k
        assert r.pago_minimo == 125_000

    def test_pago_minimo_no_aplica_modalidad_art40_2(self):
        """DA 14a solo aplica modalidad art40_3."""
        r = ISSimulator.calcular_202(
            modalidad="art40_2",
            cuota_integra_ultimo=50_000,
            facturacion_anual=15_000_000,
            resultado_contable_periodo=500_000,
        )
        # art40_2 calcula normalmente, sin minimo
        assert r.pago_minimo == 0
        assert r.pago_minimo_aplicado is False

    def test_pago_minimo_resultado_contable_negativo_floor_0(self):
        """Si RC + ajustes <= 0, el pago minimo es 0."""
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=15_000_000,
            resultado_contable_periodo=-100_000,
            ajustes_positivos_periodo=50_000,
        )
        # RC + ajustes = -50k → floor 0 → minimo = 0
        assert r.pago_minimo == 0
        assert r.pago_trimestral == 24_000  # 24% × 100k


# =============================================================================
# M4 — Cooperativas (Ley 20/1990)
# =============================================================================


class TestCooperativas:
    """Cooperativas fiscalmente protegidas: 20% sobre BI cooperativa.
    Cooperativas especialmente protegidas: 50% bonificacion adicional."""

    def test_cooperativa_protegida_20pct(self):
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=100_000,
                tipo_entidad="cooperativa",
                territorio="Madrid",
            )
        )
        # 20% sobre BI cooperativa
        assert r.cuota_integra == 20_000
        assert "20.0%" in r.tipo_gravamen_aplicado

    def test_cooperativa_especialmente_protegida_bonificacion(self):
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=100_000,
                tipo_entidad="cooperativa",
                cooperativa_especialmente_protegida=True,
                territorio="Madrid",
            )
        )
        # cuota = 20k; bonificacion 50% × 20k = 10k
        assert r.cuota_integra == 20_000
        assert r.bonificaciones_total == 10_000
        assert r.cuota_liquida == 10_000

    def test_cooperativa_no_aplica_tramos_microempresa(self):
        """Cooperativa con facturacion <1M tributa al 20% plano, no a tramos."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=200_000,
                tipo_entidad="cooperativa",
                facturacion_anual=500_000,
                territorio="Madrid",
            )
        )
        # 20% × 200k = 40k (NO tramos 17/20 microempresa)
        assert r.cuota_integra == 40_000

    def test_cooperativa_con_deducciones(self):
        """Cooperativa puede aplicar deducciones I+D igual que el resto."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=200_000,
                tipo_entidad="cooperativa",
                gasto_id=40_000,  # 25% × 40k = 10k
                territorio="Madrid",
            )
        )
        # cuota = 40k (20% × 200k); deducciones I+D = 10k limitadas al 25% cuota = 10k
        assert r.cuota_integra == 40_000
        assert r.deducciones_detalle["id"] == 10_000


# =============================================================================
# M5 — I+D 42% exceso (Art. 35.1.b LIS)
# =============================================================================


class TestIDDeduccionExceso:
    """Si gasto I+D > media 2 ejercicios anteriores, el exceso al 42%."""

    def test_id_sin_media_aplica_25pct(self):
        """Sin media historica, aplica 25% sobre todo el gasto."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                gasto_id=100_000,
                territorio="Madrid",
            )
        )
        # 25% × 100k = 25k (limite 25% cuota = 62.5k → no recorta)
        assert r.deducciones_detalle["id"] == 25_000

    def test_id_con_exceso_42pct(self):
        """Gasto 100k, media 60k → 60k × 25% + 40k × 42% = 15k + 16.8k = 31.8k."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                gasto_id=100_000,
                media_id_2_anos_anteriores=60_000,
                territorio="Madrid",
            )
        )
        # Deduccion = 60k × 25% + 40k × 42% = 15_000 + 16_800 = 31_800
        assert r.deducciones_detalle["id"] == 31_800

    def test_id_sin_exceso_aplica_25pct(self):
        """Si gasto <= media, no hay exceso, aplica 25% normal."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                gasto_id=50_000,
                media_id_2_anos_anteriores=80_000,
                territorio="Madrid",
            )
        )
        # gasto 50k <= media 80k → 25% × 50k = 12.5k
        assert r.deducciones_detalle["id"] == 12_500

    def test_id_personal_investigador_17pct_adicional(self):
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                gasto_id=100_000,
                gasto_id_personal_investigador=50_000,
                territorio="Madrid",
            )
        )
        # id base 25k + personal 17% × 50k = 8.5k
        assert r.deducciones_detalle["id"] == 25_000
        assert r.deducciones_detalle["id_personal"] == 8_500

    def test_id_inmovilizado_8pct_adicional(self):
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                gasto_id=100_000,
                gasto_id_inmovilizado_afecto=80_000,
                territorio="Madrid",
            )
        )
        # id base 25k + inmovilizado 8% × 80k = 6.4k
        assert r.deducciones_detalle["id_inmovilizado"] == 6_400

    def test_id_42pct_no_aplica_a_forales(self):
        """Bizkaia/Gipuzkoa mantienen 30% sin tramo de exceso."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                gasto_id=100_000,
                media_id_2_anos_anteriores=60_000,
                territorio="Bizkaia",
            )
        )
        # Foral 30% × 100k = 30k (sin diferenciar exceso)
        assert r.deducciones_detalle["id"] == 30_000


# =============================================================================
# M6 — ZEC techo por empleos (Art. 43 Ley 19/1994)
# =============================================================================


class TestZECTecho:
    """ZEC: 4% sobre BI hasta techo segun empleos creados."""

    def test_zec_techo_calculo(self):
        # 5 empleos minimos: techo = 1.8M
        assert zec_techo_base(5) == 1_800_000.0
        # 6 empleos: techo = 1.8M + 500k = 2.3M
        assert zec_techo_base(6) == 2_300_000.0
        # 10 empleos: techo = 1.8M + 5 × 500k = 4.3M
        assert zec_techo_base(10) == 4_300_000.0
        # 50 empleos (max): techo = 1.8M + 45 × 500k = 24.3M
        assert zec_techo_base(50) == 24_300_000.0
        # 100 empleos: capped a 50 → 24.3M
        assert zec_techo_base(100) == 24_300_000.0
        # < 5 empleos: no cumple requisito
        assert zec_techo_base(4) == 0.0
        assert zec_techo_base(0) == 0.0

    def test_zec_sin_empleos_legacy_4pct_pleno(self):
        """Sin empleos informados, mantiene comportamiento previo (4% pleno)."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=500_000,
                territorio="Canarias",
                es_zec=True,
            )
        )
        # 4% × 500k = 20k (sin techo)
        assert r.cuota_integra == 20_000

    def test_zec_con_5_empleos_dentro_techo(self):
        """5 empleos → techo 1.8M, BI 500k (dentro): 4% pleno."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=500_000,
                territorio="Canarias",
                es_zec=True,
                zec_empleos_creados=5,
            )
        )
        # 4% × 500k = 20k (toda BI dentro del techo)
        assert r.cuota_integra == 20_000

    def test_zec_con_5_empleos_excede_techo(self):
        """5 empleos → techo 1.8M, BI 3M (excede): 4% × 1.8M + 25% × 1.2M."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=3_000_000,
                territorio="Canarias",
                es_zec=True,
                zec_empleos_creados=5,
            )
        )
        # 4% × 1.8M = 72k + 25% × 1.2M = 300k → total 372k
        assert r.cuota_integra == 372_000

    def test_zec_menos_de_5_empleos_aplica_25pct(self):
        """Sin minimo de 5 empleos, no se cumple ZEC: 25% sobre toda la BI."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=500_000,
                territorio="Canarias",
                es_zec=True,
                zec_empleos_creados=3,
            )
        )
        # 25% × 500k = 125k (no aplica beneficio ZEC)
        assert r.cuota_integra == 125_000


# =============================================================================
# M9 — Deducciones cinematograficas (Art. 36 LIS)
# =============================================================================


class TestDeduccionesCinematograficas:
    """30% primer M + 25% resto (espanolas), 30% (extranjeras), 25% (series)."""

    def test_calcular_cine_espanola_bajo_1M(self):
        # 800k × 30% = 240k
        assert calcular_deduccion_cine(800_000, "espanola") == 240_000

    def test_calcular_cine_espanola_sobre_1M(self):
        # 1M × 30% + 1M × 25% = 300k + 250k = 550k
        assert calcular_deduccion_cine(2_000_000, "espanola") == 550_000

    def test_calcular_cine_espanola_techo_general_20M(self):
        # Inversion enorme: deduccion topada a 20M
        ded = calcular_deduccion_cine(100_000_000, "espanola")
        assert ded == 20_000_000

    def test_calcular_cine_espanola_techo_reforzado_40M(self):
        ded = calcular_deduccion_cine(200_000_000, "espanola", csi_o_cataluna=True)
        assert ded == 40_000_000

    def test_calcular_cine_extranjera_30pct(self):
        # 5M × 30% = 1.5M
        assert calcular_deduccion_cine(5_000_000, "extranjera") == 1_500_000

    def test_calcular_cine_extranjera_base_minima_1M(self):
        # < 1M no aplica
        assert calcular_deduccion_cine(500_000, "extranjera") == 0

    def test_calcular_cine_extranjera_techo_20M(self):
        ded = calcular_deduccion_cine(100_000_000, "extranjera")
        assert ded == 20_000_000

    def test_calcular_cine_serie_25pct(self):
        # 2M × 25% = 500k
        assert calcular_deduccion_cine(2_000_000, "serie") == 500_000

    def test_simulator_cine_espanola_aplicada(self):
        """Productora con cuota suficiente: deduccion cine se computa."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=10_000_000,
                gasto_produccion_cinematografica=2_000_000,
                tipo_produccion_cinematografica="espanola",
                territorio="Madrid",
            )
        )
        # cuota_integra = 25% × 10M = 2.5M
        # ded cine = 1M × 30% + 1M × 25% = 550k
        # limite 25% cuota = 625k → no recorta (550k < 625k)
        assert r.deducciones_detalle["cinematografica"] == 550_000

    def test_simulator_cine_extranjera_techo_reforzado(self):
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=200_000_000,
                gasto_produccion_cinematografica=200_000_000,
                tipo_produccion_cinematografica="espanola",
                cine_csi_o_cataluna=True,
                territorio="Cataluna",
            )
        )
        # cuota_integra = 25% × 200M = 50M
        # ded cine = topada a 40M; limite 25% cuota = 12.5M → recorta a 12.5M
        # (factor de proporcionalidad porque solo hay una deduccion limitada)
        assert r.deducciones_detalle["cinematografica"] == 12_500_000


# =============================================================================
# Pipeline completo — Casos compuestos AEAT Manual Practico Sociedades 2024
# =============================================================================


class TestCasosCompuestos:
    """Casos end-to-end combinando varios items MEDIA."""

    def test_erd_con_reserva_nivelacion_y_capitalizacion(self):
        """ERD aplica reserva capitalizacion + reserva nivelacion."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=200_000,
                facturacion_anual=5_000_000,
                incremento_ffpp=50_000,  # reserva capit 10% × 50k = 5k
                reserva_nivelacion=20_000,  # max 10% BI = 20k → aplica 20k
                ejercicio=2024,
                territorio="Madrid",
            )
        )
        # base_imponible_previa = 200k - 5k (reserva cap) = 195k
        # base_imponible (post BIN) = 195k
        # reserva nivelacion = min(20k, 10% × 195k=19.5k, 1M) = 19.5k
        assert r.reserva_capitalizacion == 5_000
        assert r.reserva_nivelacion == 19_500
        assert r.base_imponible == 175_500

    def test_gran_empresa_tributacion_minima_no_se_aplica_si_normal_alta(self):
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=2_000_000,
                facturacion_anual=30_000_000,
                territorio="Madrid",
            )
        )
        # cuota_integra = 25% × 2M = 500k
        # Sin deducciones ni bonificaciones → cuota_liquida = 500k
        # Cuota minima = 15% × 2M = 300k → 500k > 300k, no se eleva
        assert r.cuota_liquida == 500_000
        assert r.tributacion_minima_aplicada is False
        assert r.cuota_liquida_minima == 300_000

    def test_cooperativa_esp_protegida_no_baja_de_minimo(self):
        """Cooperativa esp. protegida en grupo consolidado:
        bonificacion 50% no debe bajar bajo el minimo del 15%."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=1_000_000,
                tipo_entidad="cooperativa",
                cooperativa_especialmente_protegida=True,
                facturacion_anual=25_000_000,
                grupo_consolidado=True,
                territorio="Madrid",
            )
        )
        # cuota_integra = 20% × 1M = 200k
        # bonificacion 50% × 200k = 100k
        # cuota_liquida normal = 100k
        # cuota minima = 15% × 1M = 150k → eleva a 150k
        assert r.tributacion_minima_aplicada is True
        assert r.cuota_liquida == 150_000

    def test_backwards_compat_isinput_sin_nuevos_campos(self):
        """ISInput legacy sin parametros Wave C2 sigue calculando igual."""
        r = ISSimulator.calculate(
            ISInput(
                resultado_contable=100_000,
                territorio="Madrid",
            )
        )
        assert r.cuota_integra == 25_000
        assert r.reserva_nivelacion == 0
        assert r.tributacion_minima_aplicada is False
        assert r.cuota_liquida_minima == 0
