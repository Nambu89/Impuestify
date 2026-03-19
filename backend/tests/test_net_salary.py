"""
Tests para la calculadora de sueldo neto autonomo.

Llaman directamente a _compute_net_salary (funcion pura, sin HTTP ni slowapi)
y a _calcular_irpf_simplificado para tests unitarios de la escala IRPF.

No requiere DB, LLM ni servidor levantado.
"""
import math
import pytest

from app.routers.irpf_estimate import (
    _calcular_irpf_simplificado,
    _compute_net_salary,
    NetSalaryRequest,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _r(
    facturacion_bruta_mensual: float = 3000.0,
    tipo_iva: float | None = None,
    retencion_irpf: float = 15.0,
    cuota_autonomo_mensual: float | None = None,
    gastos_deducibles_mensual: float = 0.0,
    es_nuevo_autonomo: bool = False,
    comunidad_autonoma: str | None = None,
):
    """Atajo para construir un NetSalaryRequest y calcular el resultado."""
    body = NetSalaryRequest(
        facturacion_bruta_mensual=facturacion_bruta_mensual,
        tipo_iva=tipo_iva,
        retencion_irpf=retencion_irpf,
        cuota_autonomo_mensual=cuota_autonomo_mensual,
        gastos_deducibles_mensual=gastos_deducibles_mensual,
        es_nuevo_autonomo=es_nuevo_autonomo,
        comunidad_autonoma=comunidad_autonoma,
    )
    return _compute_net_salary(body)


# ---------------------------------------------------------------------------
# Tests auxiliares: escala IRPF
# ---------------------------------------------------------------------------

class TestIRPFSimplificado:
    def test_base_cero_devuelve_cero(self):
        assert _calcular_irpf_simplificado(0) == 0.0

    def test_base_negativa_devuelve_cero(self):
        assert _calcular_irpf_simplificado(-1000) == 0.0

    def test_base_por_debajo_minimo_personal_devuelve_cero(self):
        # 5.550 EUR es el minimo personal exento -> cuota cero
        assert _calcular_irpf_simplificado(5000) == 0.0

    def test_tramo_19pct(self):
        # Base liquidable de 1.000 EUR (dentro del primer tramo 19%)
        cuota = _calcular_irpf_simplificado(5550 + 1000)
        assert cuota == pytest.approx(1000 * 0.19 * 2, rel=0.01)

    def test_tramo_alto_genera_cuota_elevada(self):
        cuota = _calcular_irpf_simplificado(100_000)
        assert cuota > 30_000


# ---------------------------------------------------------------------------
# Test 1: facturacion basica 3.000 EUR, params por defecto
# ---------------------------------------------------------------------------

class TestBasic3000EUR:
    def test_basic_3000_eur(self):
        r = _r(facturacion_bruta_mensual=3000.0)

        assert r.success is True
        assert r.facturacion_bruta == 3000.0

        # IVA 21% sobre 3000
        assert r.iva_repercutido == pytest.approx(630.0)
        assert r.total_factura == pytest.approx(3630.0)

        # Retencion 15% sobre bruto (sin IVA)
        assert r.retencion_irpf_factura == pytest.approx(450.0)
        assert r.cobro_efectivo == pytest.approx(3180.0)  # 3630 - 450

        # Sin gastos: neto = cobro_efectivo - cuota_ss (auto-calculada)
        assert r.neto_mensual == pytest.approx(r.cobro_efectivo - r.cuota_autonomo)

        # Anual
        assert r.facturacion_bruta_anual == pytest.approx(36_000.0)
        assert r.cuota_autonomo_anual == pytest.approx(r.cuota_autonomo * 12)

        # IRPF anual positivo
        assert r.irpf_estimado_anual > 0

        # Neto anual positivo para 3.000 EUR/mes
        assert r.neto_anual > 0

        # Porcentajes en rango valido
        assert 0 <= r.tipo_irpf_efectivo <= 100
        assert 0 <= r.porcentaje_neto <= 100


# ---------------------------------------------------------------------------
# Test 2: nuevo autonomo, retencion 7%
# ---------------------------------------------------------------------------

class TestNewAutonomo7Pct:
    def test_new_autonomo_7pct(self):
        r_nuevo = _r(facturacion_bruta_mensual=3000.0, es_nuevo_autonomo=True)
        r_normal = _r(facturacion_bruta_mensual=3000.0, es_nuevo_autonomo=False)

        # La retencion aplicada debe ser exactamente el 7% del bruto
        assert r_nuevo.retencion_irpf_factura == pytest.approx(3000.0 * 0.07)

        # Al retener menos, el cobro efectivo es mayor
        assert r_nuevo.cobro_efectivo > r_normal.cobro_efectivo

        # La base imponible es la misma, el IRPF estimado anual es identico
        assert r_nuevo.irpf_estimado_anual == pytest.approx(r_normal.irpf_estimado_anual)

        # Con 7% se retiene menos de lo que toca: ahorro menor (debera pagar en declaracion)
        assert r_nuevo.ahorro_retencion_vs_irpf < r_normal.ahorro_retencion_vs_irpf


# ---------------------------------------------------------------------------
# Test 3: facturacion cero (edge case)
# ---------------------------------------------------------------------------

class TestZeroFacturacion:
    def test_zero_facturacion(self):
        r = _r(facturacion_bruta_mensual=0.0)

        assert r.success is True
        assert r.facturacion_bruta == 0.0
        assert r.iva_repercutido == 0.0
        assert r.total_factura == 0.0
        assert r.retencion_irpf_factura == 0.0
        assert r.cobro_efectivo == 0.0
        assert r.irpf_estimado_anual == 0.0
        assert r.tipo_irpf_efectivo == 0.0
        assert r.porcentaje_neto == 0.0
        # Neto negativo: cuota SS sigue pagandose aunque no se facture
        assert r.neto_mensual == pytest.approx(0.0 - r.cuota_autonomo)


# ---------------------------------------------------------------------------
# Test 4: exento de IVA (sanitarios, educacion)
# ---------------------------------------------------------------------------

class TestExemptIVA:
    def test_exempt_iva(self):
        r = _r(facturacion_bruta_mensual=2000.0, tipo_iva=0.0)

        assert r.iva_repercutido == 0.0
        assert r.total_factura == pytest.approx(2000.0)
        assert r.iva_a_pagar_hacienda == 0.0

        expected_retencion = round(2000.0 * 0.15, 2)
        assert r.retencion_irpf_factura == pytest.approx(expected_retencion)
        assert r.cobro_efectivo == pytest.approx(2000.0 - expected_retencion)


# ---------------------------------------------------------------------------
# Test 5: IVA reducido 10%
# ---------------------------------------------------------------------------

class TestReducedIVA:
    def test_reduced_iva(self):
        r = _r(facturacion_bruta_mensual=2000.0, tipo_iva=10.0)

        assert r.iva_repercutido == pytest.approx(200.0)
        assert r.total_factura == pytest.approx(2200.0)
        # Sin gastos: IVA a pagar = IVA repercutido (sin IVA soportado)
        assert r.iva_a_pagar_hacienda == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# Test 6: con gastos deducibles 500 EUR/mes
# ---------------------------------------------------------------------------

class TestWithExpenses:
    def test_with_expenses(self):
        r_sin = _r(facturacion_bruta_mensual=3000.0, gastos_deducibles_mensual=0.0)
        r_con = _r(facturacion_bruta_mensual=3000.0, gastos_deducibles_mensual=500.0)

        # El cobro efectivo es el mismo (los gastos no afectan al cobro de facturas)
        assert r_con.cobro_efectivo == pytest.approx(r_sin.cobro_efectivo)

        # El neto mensual baja (gastos se descuentan del neto liquido)
        assert r_con.neto_mensual < r_sin.neto_mensual

        # El IVA a pagar baja al haber IVA soportado
        assert r_con.iva_a_pagar_hacienda < r_sin.iva_a_pagar_hacienda

        # Base imponible menor: IRPF anual menor
        assert r_con.irpf_estimado_anual < r_sin.irpf_estimado_anual

        # Los gastos reducen la base imponible pero tambien el neto disponible
        # La mejora fiscal no compensa el gasto: neto anual con gastos es menor
        assert r_con.neto_anual < r_sin.neto_anual


# ---------------------------------------------------------------------------
# Test 7: ingresos altos, tramo 45%
# ---------------------------------------------------------------------------

class TestHighIncome45Pct:
    def test_high_income_45pct(self):
        # 10.000 EUR/mes = 120.000 EUR/anual -> tramo 45%
        r = _r(facturacion_bruta_mensual=10_000.0)

        assert r.success is True
        assert r.facturacion_bruta_anual == pytest.approx(120_000.0)

        # Tipo efectivo >30% para ingresos altos
        assert r.tipo_irpf_efectivo > 30.0

        # IRPF real supera la retencion del 15% -> habra que ingresar al declarar
        retencion_anual = 120_000.0 * 0.15
        assert r.irpf_estimado_anual > retencion_anual

        # El ahorro es negativo (debe pagar la diferencia)
        assert r.ahorro_retencion_vs_irpf < 0

        # Neto anual aun positivo y significativo
        assert r.neto_anual > 30_000.0


# ---------------------------------------------------------------------------
# Test 8: estructura completa de la respuesta
# ---------------------------------------------------------------------------

class TestResponseStructure:
    def test_response_structure(self):
        r = _r(
            facturacion_bruta_mensual=4000.0,
            tipo_iva=21.0,
            retencion_irpf=15.0,
            cuota_autonomo_mensual=350.0,
            gastos_deducibles_mensual=300.0,
        )

        # Todos los campos numericos: no None, numericos, no NaN, no infinito
        campos_numericos = [
            "facturacion_bruta",
            "iva_repercutido",
            "total_factura",
            "retencion_irpf_factura",
            "cobro_efectivo",
            "cuota_autonomo",
            "gastos_deducibles",
            "iva_a_pagar_hacienda",
            "neto_mensual",
            "facturacion_bruta_anual",
            "irpf_estimado_anual",
            "cuota_autonomo_anual",
            "neto_anual",
            "tipo_irpf_efectivo",
            "porcentaje_neto",
            "ahorro_retencion_vs_irpf",
        ]
        for campo in campos_numericos:
            valor = getattr(r, campo)
            assert valor is not None, f"Campo '{campo}' es None"
            assert isinstance(valor, (int, float)), f"Campo '{campo}' no es numerico"
            assert not math.isnan(valor), f"Campo '{campo}' es NaN"
            assert not math.isinf(valor), f"Campo '{campo}' es infinito"

        assert r.success is True
        assert r.error is None

        # Invariante: total_factura = facturacion_bruta + iva_repercutido
        assert r.total_factura == pytest.approx(r.facturacion_bruta + r.iva_repercutido, rel=1e-4)

        # Invariante: cobro_efectivo = total_factura - retencion
        assert r.cobro_efectivo == pytest.approx(
            r.total_factura - r.retencion_irpf_factura, rel=1e-4
        )

        # Invariante: neto_mensual = cobro_efectivo - cuota_ss - gastos
        assert r.neto_mensual == pytest.approx(
            r.cobro_efectivo - r.cuota_autonomo - r.gastos_deducibles, rel=1e-4
        )

        # Invariante: cuota_autonomo_anual = cuota_autonomo * 12
        assert r.cuota_autonomo_anual == pytest.approx(r.cuota_autonomo * 12, rel=1e-4)


# ---------------------------------------------------------------------------
# Tests territoriales: los 5 regimenes fiscales
# ---------------------------------------------------------------------------

class TestTerritorialMadrid:
    """Madrid: regimen comun, IVA 21%."""
    def test_madrid_comun(self):
        r = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Comunidad de Madrid")
        assert r.regimen_fiscal == "comun"
        assert r.impuesto_indirecto == "IVA"
        assert r.tipo_impuesto_indirecto == 21.0
        assert r.iva_repercutido == pytest.approx(630.0)
        assert r.deduccion_ceuta_melilla is None


class TestTerritorialMalaga:
    """Malaga (Andalucia): regimen comun, IVA 21%, escala autonomica diferente."""
    def test_malaga_comun(self):
        r = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Andalucía")
        assert r.regimen_fiscal == "comun"
        assert r.impuesto_indirecto == "IVA"
        assert r.tipo_impuesto_indirecto == 21.0
        # Mismo IRPF que Madrid en esta v1 (escala simplificada x2)
        r_mad = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Comunidad de Madrid")
        assert r.irpf_estimado_anual == pytest.approx(r_mad.irpf_estimado_anual)


class TestTerritorialTenerife:
    """Tenerife (Canarias): IGIC 7% en vez de IVA 21%."""
    def test_canarias_igic(self):
        r = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Canarias")
        assert r.regimen_fiscal == "canarias"
        assert r.impuesto_indirecto == "IGIC"
        assert r.tipo_impuesto_indirecto == 7.0
        assert r.iva_repercutido == pytest.approx(210.0)  # 3000 * 7%
        # Total factura menor que en peninsula
        r_mad = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Comunidad de Madrid")
        assert r.total_factura < r_mad.total_factura


class TestTerritorialMelilla:
    """Melilla: IPSI 4%, deduccion 60% cuota IRPF."""
    def test_melilla_ipsi_y_deduccion(self):
        r = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Melilla")
        assert r.regimen_fiscal == "ceuta_melilla"
        assert r.impuesto_indirecto == "IPSI"
        assert r.tipo_impuesto_indirecto == 4.0
        assert r.iva_repercutido == pytest.approx(120.0)  # 3000 * 4%
        # Deduccion 60% Ceuta/Melilla aplicada
        assert r.deduccion_ceuta_melilla is not None
        assert r.deduccion_ceuta_melilla > 0
        # IRPF mucho menor que Madrid gracias al 60%
        r_mad = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Comunidad de Madrid")
        assert r.irpf_estimado_anual < r_mad.irpf_estimado_anual * 0.5


class TestTerritorialBilbao:
    """Bilbao (Bizkaia): foral vasco, IVA 21%, escala propia."""
    def test_bizkaia_foral(self):
        r = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Bizkaia")
        assert r.regimen_fiscal == "foral_vasco"
        assert r.impuesto_indirecto == "IVA"
        assert r.tipo_impuesto_indirecto == 21.0
        # El IRPF foral vasco es diferente al comun
        r_mad = _r(facturacion_bruta_mensual=3000.0, comunidad_autonoma="Comunidad de Madrid")
        # No deben ser iguales (escalas diferentes)
        assert r.irpf_estimado_anual != pytest.approx(r_mad.irpf_estimado_anual, rel=0.01)


class TestCuotaSSPorIngresos:
    """Cuota SS auto-calculada por ingresos reales (sin cuota manual)."""
    def test_cuota_baja_ingresos(self):
        # 1000 EUR/mes facturacion -> rendimiento ~600 -> cuota baja
        r = _r(facturacion_bruta_mensual=1000.0)
        assert r.cuota_autonomo < 260.0  # Tramo bajo

    def test_cuota_alta_ingresos(self):
        # 8000 EUR/mes facturacion -> rendimiento ~4800 -> cuota alta
        r = _r(facturacion_bruta_mensual=8000.0)
        assert r.cuota_autonomo > 350.0  # Tramo alto

    def test_cuota_manual_override(self):
        # Si el usuario pasa cuota manual, no se auto-calcula
        r = _r(facturacion_bruta_mensual=3000.0, cuota_autonomo_mensual=293.0)
        assert r.cuota_autonomo == 293.0
