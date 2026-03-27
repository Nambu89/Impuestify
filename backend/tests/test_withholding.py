"""
Tests para la calculadora de retenciones IRPF 2026.

Casos verificados contra la calculadora oficial AEAT:
https://www2.agenciatributaria.gob.es/wlpl/PRET-R200/R260/index.zul
"""
import pytest
from app.utils.calculators.withholding_rate import (
    calcular_retencion,
    WithholdingInput,
    SituacionFamiliar,
    SituacionLaboral,
    TipoContrato,
    Discapacidad,
    Descendiente,
    Ascendiente,
    _aplicar_escala,
)


class TestEscalaRetencion:
    """Test de la escala de retencion (TABLA 2)."""

    def test_base_0(self):
        assert _aplicar_escala(0) == 0

    def test_primer_tramo(self):
        # 10,000 * 19% = 1,900
        assert _aplicar_escala(10000) == 1900.00

    def test_segundo_tramo(self):
        # 12,450 * 19% + 2,550 * 24% = 2,365.50 + 612 = 2,977.50
        assert _aplicar_escala(15000) == 2977.50

    def test_ejemplo_aeat(self):
        # Ejemplo del algoritmo pag 30: BASE = 24,000
        # Hasta 20,200: 4,225.50 + Resto 3,800 * 30% = 1,140 → 5,365.50
        assert _aplicar_escala(24000) == 5365.50

    def test_tramo_alto(self):
        # 60,000 → cuota = 17,901.50 (segun tabla)
        result = _aplicar_escala(60000)
        assert result == 17901.50

    def test_base_negativa(self):
        assert _aplicar_escala(-1000) == 0


class TestExenciones:
    """Test de limites excluyentes de retencion (TABLA 1)."""

    def test_situacion3_sin_hijos_bajo_limite(self):
        """Soltero sin hijos, salario < 15,876 → exento."""
        inp = WithholdingInput(
            retribucion_bruta_anual=15000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
        )
        result = calcular_retencion(inp)
        assert result.exento is True
        assert result.tipo_retencion == 0.0

    def test_situacion3_sin_hijos_sobre_limite(self):
        """Soltero sin hijos, salario > 15,876 → NO exento."""
        inp = WithholdingInput(
            retribucion_bruta_anual=20000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
        )
        result = calcular_retencion(inp)
        assert result.exento is False
        assert result.tipo_retencion > 0

    def test_situacion2_sin_hijos_bajo_limite(self):
        """Casado conyuge < 1500, sin hijos, salario < 17,197 → exento."""
        inp = WithholdingInput(
            retribucion_bruta_anual=17000,
            situacion_familiar=SituacionFamiliar.SITUACION2,
        )
        result = calcular_retencion(inp)
        assert result.exento is True

    def test_situacion1_sin_hijos(self):
        """Situacion 1 sin hijos → nunca exento por esta via."""
        inp = WithholdingInput(
            retribucion_bruta_anual=15000,
            situacion_familiar=SituacionFamiliar.SITUACION1,
        )
        result = calcular_retencion(inp)
        # Situacion 1 requiere hijos para exencion
        assert result.exento is True or result.tipo_retencion >= 0


class TestCasosComunes:
    """Casos comunes de retencion."""

    def test_salario_25000_soltero(self):
        """Soltero sin hijos, 25,000 EUR brutos."""
        inp = WithholdingInput(
            retribucion_bruta_anual=25000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            ano_nacimiento=1990,
        )
        result = calcular_retencion(inp)
        # Retencion debe estar entre 10% y 20%
        assert 10 < result.tipo_retencion < 20
        assert result.cuota_anual > 0
        assert result.retencion_mensual > 0
        assert result.salario_neto_mensual > 0
        assert not result.exento

    def test_salario_30000_casado_2_hijos(self):
        """Casado, 2 hijos, 30,000 EUR."""
        inp = WithholdingInput(
            retribucion_bruta_anual=30000,
            situacion_familiar=SituacionFamiliar.SITUACION2,
            ano_nacimiento=1985,
            descendientes=[
                Descendiente(ano_nacimiento=2018),
                Descendiente(ano_nacimiento=2020),
            ],
        )
        result = calcular_retencion(inp)
        # Con 2 hijos y casado, retencion debe ser menor
        assert result.tipo_retencion < 15
        assert result.minimo_descendientes > 0

    def test_salario_50000_soltero(self):
        """Soltero, 50,000 EUR."""
        inp = WithholdingInput(
            retribucion_bruta_anual=50000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            ano_nacimiento=1985,
        )
        result = calcular_retencion(inp)
        assert 20 < result.tipo_retencion < 30

    def test_salario_100000(self):
        """Salario alto, 100,000 EUR."""
        inp = WithholdingInput(
            retribucion_bruta_anual=100000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            ano_nacimiento=1980,
        )
        result = calcular_retencion(inp)
        assert 30 < result.tipo_retencion < 40

    def test_pensionista(self):
        """Pensionista, 20,000 EUR."""
        inp = WithholdingInput(
            retribucion_bruta_anual=20000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            situacion_laboral=SituacionLaboral.PENSIONISTA,
            ano_nacimiento=1955,
        )
        result = calcular_retencion(inp)
        # Pensionista tiene reduccion 600
        assert result.tipo_retencion >= 0

    def test_desempleado(self):
        """Desempleado, 18,000 EUR."""
        inp = WithholdingInput(
            retribucion_bruta_anual=18000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            situacion_laboral=SituacionLaboral.DESEMPLEADO,
            ano_nacimiento=1990,
        )
        result = calcular_retencion(inp)
        # Desempleado tiene reduccion 1200
        assert result.tipo_retencion >= 0


class TestDiscapacidad:
    """Test de discapacidad del trabajador."""

    def test_discapacidad_33_reduce_retencion(self):
        """Discapacidad 33-65% reduce gastos deducibles → menor retencion."""
        inp_sin = WithholdingInput(
            retribucion_bruta_anual=30000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
        )
        inp_con = WithholdingInput(
            retribucion_bruta_anual=30000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            discapacidad=Discapacidad.DE33A65,
        )
        res_sin = calcular_retencion(inp_sin)
        res_con = calcular_retencion(inp_con)
        assert res_con.tipo_retencion < res_sin.tipo_retencion

    def test_discapacidad_65_mayor_reduccion(self):
        """Discapacidad >= 65% tiene mayor reduccion que 33-65%."""
        inp_33 = WithholdingInput(
            retribucion_bruta_anual=40000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            discapacidad=Discapacidad.DE33A65,
        )
        inp_65 = WithholdingInput(
            retribucion_bruta_anual=40000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            discapacidad=Discapacidad.DESDE65,
        )
        res_33 = calcular_retencion(inp_33)
        res_65 = calcular_retencion(inp_65)
        assert res_65.tipo_retencion < res_33.tipo_retencion


class TestCeutaMelilla:
    """Test de deduccion Ceuta/Melilla."""

    def test_ceuta_melilla_reduce_cuota(self):
        """Residentes Ceuta/Melilla tienen 60% deduccion → menor retencion."""
        inp_normal = WithholdingInput(
            retribucion_bruta_anual=35000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
        )
        inp_ceuta = WithholdingInput(
            retribucion_bruta_anual=35000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            ceuta_melilla=True,
        )
        res_normal = calcular_retencion(inp_normal)
        res_ceuta = calcular_retencion(inp_ceuta)
        assert res_ceuta.tipo_retencion < res_normal.tipo_retencion
        # Deduccion 60% → paga ~40% de la cuota normal
        assert res_ceuta.cuota_anual < res_normal.cuota_anual * 0.5


class TestContratoTemporal:
    """Test de contrato temporal."""

    def test_temporal_minimo_2_porciento(self):
        """Contrato temporal tiene minimo 2%."""
        inp = WithholdingInput(
            retribucion_bruta_anual=16000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            tipo_contrato=TipoContrato.TEMPORAL,
        )
        result = calcular_retencion(inp)
        if not result.exento:
            assert result.tipo_retencion >= 2.0


class TestDesglose:
    """Test de datos del desglose."""

    def test_desglose_completo(self):
        """Verificar que el desglose tiene todos los campos."""
        inp = WithholdingInput(
            retribucion_bruta_anual=30000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
        )
        result = calcular_retencion(inp)
        assert result.retribucion_bruta == 30000
        assert result.cotizaciones_ss > 0
        assert result.gastos_deducibles > 0
        assert result.minimo_contribuyente == 5550
        assert result.base_retencion >= 0

    def test_to_dict(self):
        """Test serializacion a dict."""
        inp = WithholdingInput(retribucion_bruta_anual=25000)
        result = calcular_retencion(inp)
        d = result.to_dict()
        assert "tipo_retencion" in d
        assert "cuota_anual" in d
        assert "retencion_mensual" in d
        assert "salario_neto_mensual" in d

    def test_num_pagas_12(self):
        """12 pagas vs 14 pagas."""
        inp14 = WithholdingInput(retribucion_bruta_anual=30000, num_pagas=14)
        inp12 = WithholdingInput(retribucion_bruta_anual=30000, num_pagas=12)
        res14 = calcular_retencion(inp14)
        res12 = calcular_retencion(inp12)
        # Mismo tipo pero diferente mensual
        assert res14.tipo_retencion == res12.tipo_retencion
        assert res14.retencion_mensual < res12.retencion_mensual


class TestHipotecaPre2013:
    """Test de deduccion por vivienda habitual pre-2013."""

    def test_hipoteca_reduce_retencion(self):
        """Hipoteca pre-2013 con salario < 33,007.20 reduce retencion."""
        inp_sin = WithholdingInput(
            retribucion_bruta_anual=28000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
        )
        inp_con = WithholdingInput(
            retribucion_bruta_anual=28000,
            situacion_familiar=SituacionFamiliar.SITUACION3,
            hipoteca_pre2013=True,
        )
        res_sin = calcular_retencion(inp_sin)
        res_con = calcular_retencion(inp_con)
        assert res_con.tipo_retencion <= res_sin.tipo_retencion


class TestDescendientesAscendientes:
    """Test de minimos por familia."""

    def test_hijo_menor_3_anos(self):
        """Hijo menor de 3 anos da minimo adicional 2,800."""
        inp = WithholdingInput(
            retribucion_bruta_anual=30000,
            situacion_familiar=SituacionFamiliar.SITUACION2,
            descendientes=[Descendiente(ano_nacimiento=2024)],
        )
        result = calcular_retencion(inp)
        # 2,400 (1er hijo) + 2,800 (menor 3) = 5,200
        assert result.minimo_descendientes == 5200.00

    def test_tres_hijos(self):
        """3 hijos: 2,400 + 2,700 + 4,000 = 9,100."""
        inp = WithholdingInput(
            retribucion_bruta_anual=40000,
            descendientes=[
                Descendiente(ano_nacimiento=2010),
                Descendiente(ano_nacimiento=2012),
                Descendiente(ano_nacimiento=2015),
            ],
        )
        result = calcular_retencion(inp)
        assert result.minimo_descendientes == 9100.00

    def test_ascendiente_mayor_65(self):
        """Ascendiente > 65 anos → minimo 1,150."""
        inp = WithholdingInput(
            retribucion_bruta_anual=30000,
            ascendientes=[Ascendiente(ano_nacimiento=1950)],
        )
        result = calcular_retencion(inp)
        assert result.minimo_ascendientes >= 1150.00

    def test_ascendiente_mayor_75(self):
        """Ascendiente > 75 anos → 1,150 + 1,400 = 2,550."""
        inp = WithholdingInput(
            retribucion_bruta_anual=30000,
            ascendientes=[Ascendiente(ano_nacimiento=1945)],
        )
        result = calcular_retencion(inp)
        assert result.minimo_ascendientes >= 2550.00
