"""Tests del simulador IS (Modelo 200)."""
import pytest
from app.utils.is_simulator import ISSimulator, ISInput, ISResult


class TestISSimulatorComun:
    """Regimen comun (25%)."""

    def test_sl_basica_25pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Madrid",
        ))
        assert r.base_imponible == 100_000
        assert r.cuota_integra == 25_000  # 25%
        assert r.tipo == "a_ingresar"

    def test_pyme_23_25_tramos(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,  # <1M = pyme
            territorio="Madrid",
        ))
        # primeros 50k al 23% = 11500, siguientes 50k al 25% = 12500
        assert r.cuota_integra == 24_000

    def test_nueva_creacion_15_20(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            tipo_entidad="nueva_creacion",
            ejercicios_con_bi_positiva=1,
            territorio="Madrid",
        ))
        # primeros 50k al 15% = 7500, siguientes 50k al 20% = 10000
        assert r.cuota_integra == 17_500

    def test_gastos_no_deducibles(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=80_000,
            gastos_no_deducibles=20_000,
            territorio="Madrid",
        ))
        assert r.base_imponible == 100_000
        assert r.ajustes_positivos == 20_000

    def test_bins_compensacion(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            bins_pendientes=30_000,
            territorio="Madrid",
        ))
        assert r.compensacion_bins == 30_000
        assert r.base_imponible == 70_000

    def test_bins_limite_70pct_grandes(self):
        """Empresas >20M facturacion: limite 70% compensacion BINs."""
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            bins_pendientes=100_000,
            facturacion_anual=25_000_000,
            territorio="Madrid",
        ))
        assert r.compensacion_bins == 70_000  # 70% de 100k
        assert r.base_imponible == 30_000

    def test_resultado_negativo(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=-50_000,
            territorio="Madrid",
        ))
        assert r.base_imponible == 0  # no puede ser negativa (genera BIN)
        assert r.cuota_integra == 0
        assert r.bin_generada == 50_000

    def test_deducciones_id(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=200_000,
            gasto_id=40_000,  # 25% = 10000 deduccion
            territorio="Madrid",
        ))
        assert r.deducciones_detalle["id"] == 10_000
        assert r.cuota_liquida == 200_000 * 0.25 - 10_000

    def test_reserva_capitalizacion(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            incremento_ffpp=50_000,  # 10% = 5000 reduccion BI
            territorio="Madrid",
        ))
        # BI = 100k - 5k (reserva cap) = 95k; limitado al 10% BI
        assert r.base_imponible == 95_000

    def test_retenciones_a_devolver(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            retenciones_ingresos_cuenta=30_000,
            territorio="Madrid",
        ))
        assert r.cuota_liquida == 25_000
        assert r.resultado_liquidacion == -5_000
        assert r.tipo == "a_devolver"

    def test_ingresos_menos_gastos(self):
        """Si no se da resultado_contable, usar ingresos-gastos."""
        r = ISSimulator.calculate(ISInput(
            ingresos_explotacion=300_000,
            gastos_explotacion=200_000,
            territorio="Madrid",
        ))
        assert r.resultado_contable == 100_000
        assert r.cuota_integra == 25_000

    def test_ajustes_negativos(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            ajustes_negativos=10_000,
            territorio="Madrid",
        ))
        assert r.base_imponible == 90_000

    def test_tipo_efectivo(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Madrid",
        ))
        assert r.tipo_efectivo == 25.0

    def test_empleo_discapacidad(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=200_000,
            empleados_discapacidad_33=2,
            empleados_discapacidad_65=1,
            territorio="Madrid",
        ))
        assert r.deducciones_detalle["empleo_discapacidad"] == 2 * 9_000 + 12_000


class TestISSimulatorForal:
    """Territorios forales."""

    def test_bizkaia_24pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Bizkaia",
        ))
        assert r.cuota_integra == 24_000
        assert r.regimen == "foral_bizkaia"

    def test_navarra_28pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Navarra",
        ))
        assert r.cuota_integra == 28_000
        assert r.regimen == "foral_navarra"

    def test_navarra_pyme_23_28(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Navarra",
        ))
        # 50k * 23% + 50k * 28% = 11500 + 14000 = 25500
        assert r.cuota_integra == 25_500

    def test_gipuzkoa_pyme_20_24(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Gipuzkoa",
        ))
        # 50k * 20% + 50k * 24% = 10000 + 12000 = 22000
        assert r.cuota_integra == 22_000

    def test_alava_general(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Araba",
        ))
        assert r.cuota_integra == 24_000
        assert r.regimen == "foral_alava"


class TestISSimulatorEspeciales:
    """Canarias ZEC + Ceuta/Melilla."""

    def test_zec_canarias_4pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Canarias",
            es_zec=True,
        ))
        assert r.cuota_integra == 4_000
        assert r.regimen == "zec_canarias"

    def test_ceuta_melilla_bonificacion_50(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Melilla",
            rentas_ceuta_melilla=100_000,
        ))
        # cuota 25000, bonificacion 50% sobre rentas en territorio
        assert r.bonificaciones_total == 12_500
        assert r.cuota_liquida == 12_500

    def test_canarias_ric(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Canarias",
            dotacion_ric=50_000,
        ))
        # RIC reduce BI en dotacion (limitado a 90% beneficio no distribuido)
        assert r.base_imponible < 100_000


class TestISPagosFraccionados:
    """Modelo 202."""

    def test_202_art40_2_basico(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_2",
            cuota_integra_ultimo=50_000,
            deducciones_bonificaciones_ultimo=5_000,
            retenciones_ultimo=3_000,
        )
        # 18% de (50000 - 5000 - 3000) = 18% de 42000 = 7560
        assert r.pago_trimestral == 7_560

    def test_202_art40_3_basico(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=5_000_000,
        )
        # 17% de 100000 = 17000
        assert r.pago_trimestral == 17_000

    def test_202_art40_3_grande(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=15_000_000,
        )
        # >10M: 24% de 100000 = 24000
        assert r.pago_trimestral == 24_000

    def test_202_art40_2_sin_cuota(self):
        """Si cuota - deducciones - retenciones <= 0, pago es 0."""
        r = ISSimulator.calcular_202(
            modalidad="art40_2",
            cuota_integra_ultimo=10_000,
            deducciones_bonificaciones_ultimo=8_000,
            retenciones_ultimo=5_000,
        )
        assert r.pago_trimestral == 0.0
