"""
Tests for Modelo 450 — AIEM Canarias (productores).

Cubre Modelo450Calculator + calculate_modelo_450_tool.

Norma vigente:
- Decreto Legislativo 1/2025 (BOC nº 207, 2025-10-20, vigor 2025-10-21)
  Texto Refundido IGIC + AIEM.
- Tipos AIEM 2025+: 5 % / 10 % / 15 % / 25 %.
"""

from __future__ import annotations

import pytest

from app.utils.calculators.modelo_450 import (
    AIEM_TIPOS_POR_EPIGRAFE,
    ALLOWED_AIEM_RATES,
    PLAZOS_MODELO_450,
    TIPO_AIEM_ESPECIAL,
    TIPO_AIEM_GENERAL,
    TIPO_AIEM_INTERMEDIO,
    TIPO_AIEM_REDUCIDO,
    UMBRAL_MENSUAL_EUR,
    Modelo450Calculator,
    lookup_tipo_aiem,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def calc():
    return Modelo450Calculator(None)


# ---------------------------------------------------------------------------
# 1. Constantes vigentes
# ---------------------------------------------------------------------------
class TestAIEMRates:
    def test_tipo_reducido(self):
        assert TIPO_AIEM_REDUCIDO == 0.05

    def test_tipo_intermedio(self):
        assert TIPO_AIEM_INTERMEDIO == 0.10

    def test_tipo_general(self):
        assert TIPO_AIEM_GENERAL == 0.15

    def test_tipo_especial_tabaco(self):
        assert TIPO_AIEM_ESPECIAL == 0.25

    def test_allowed_rates_set(self):
        assert set(ALLOWED_AIEM_RATES) == {0.05, 0.10, 0.15, 0.25}

    def test_umbral_mensual(self):
        # Mismo umbral que SII / grandes empresas
        assert UMBRAL_MENSUAL_EUR == 6_010_121.04


# ---------------------------------------------------------------------------
# 2. Lookup epigrafe IAE → tipo AIEM
# ---------------------------------------------------------------------------
class TestLookupTipoAIEM:
    def test_lookup_tabaco_25pct(self):
        # Industria del tabaco
        assert lookup_tipo_aiem("1500") == TIPO_AIEM_ESPECIAL

    def test_lookup_conservas_15pct(self):
        # Conservas vegetales
        assert lookup_tipo_aiem("415") == TIPO_AIEM_GENERAL

    def test_lookup_textil_10pct(self):
        assert lookup_tipo_aiem("433") == TIPO_AIEM_INTERMEDIO

    def test_lookup_match_por_prefijo(self):
        # Epigrafe largo con prefijo conocido (415 → conservas)
        assert lookup_tipo_aiem("4151") == TIPO_AIEM_GENERAL

    def test_lookup_desconocido_devuelve_none(self):
        # Servicios profesionales NO estan en lista AIEM
        assert lookup_tipo_aiem("8430") is None

    def test_lookup_vacio_devuelve_none(self):
        assert lookup_tipo_aiem("") is None
        assert lookup_tipo_aiem(None) is None


# ---------------------------------------------------------------------------
# 3. Calculator basico — un solo bien, tipo manual
# ---------------------------------------------------------------------------
class TestModelo450Basic:
    @pytest.mark.asyncio
    async def test_single_bien_tipo_general(self, calc):
        """Productor canario factura 10.000 EUR de hormigon (tipo general 15%)."""
        r = await calc.calculate(
            bienes_producidos=[
                {
                    "epigrafe_iae": "243",
                    "descripcion": "Hormigon",
                    "base_imponible": 10000,
                }
            ],
            quarter=1,
        )
        assert r["total_base_imponible"] == 10000.0
        # 10.000 * 0.15 = 1.500
        assert r["total_cuota_devengada"] == 1500.0
        assert r["resultado_liquidacion"] == 1500.0
        assert r["modelo"] == "450"
        assert r["organismo"] == "ATC"
        assert r["territorio"] == "Canarias"

    @pytest.mark.asyncio
    async def test_tipo_aiem_manual_override(self, calc):
        """Si el usuario indica tipo_aiem explicito, se usa (no el lookup)."""
        r = await calc.calculate(
            bienes_producidos=[
                {
                    "epigrafe_iae": "1500",  # tabaco → lookup 25%
                    "base_imponible": 10000,
                    "tipo_aiem": 0.05,  # override manual a 5%
                }
            ],
            quarter=2,
        )
        # 10.000 * 0.05 = 500 (NO 2500 que seria el lookup)
        assert r["total_cuota_devengada"] == 500.0
        assert r["desglose_bienes"][0]["origen_tipo"] == "manual"

    @pytest.mark.asyncio
    async def test_bien_sin_tipo_ni_lookup_genera_warning(self, calc):
        """Bien sin tipo_aiem y epigrafe desconocido → warning, cuota 0."""
        r = await calc.calculate(
            bienes_producidos=[
                {
                    "epigrafe_iae": "8430",  # servicios — NO esta en lista AIEM
                    "descripcion": "Servicios profesionales",
                    "base_imponible": 10000,
                }
            ],
            quarter=1,
        )
        assert r["total_cuota_devengada"] == 0.0
        assert len(r["warnings"]) == 1
        assert r["desglose_bienes"][0]["warning"] is True
        assert r["desglose_bienes"][0]["tipo_aiem"] is None

    @pytest.mark.asyncio
    async def test_lookup_aplica_si_no_hay_tipo_manual(self, calc):
        """Sin tipo_aiem pero con epigrafe conocido → lookup."""
        r = await calc.calculate(
            bienes_producidos=[
                {
                    "epigrafe_iae": "1500",  # tabaco
                    "base_imponible": 1000,
                }
            ],
            quarter=1,
        )
        # 1000 * 0.25 = 250
        assert r["total_cuota_devengada"] == 250.0
        assert r["desglose_bienes"][0]["origen_tipo"] == "lookup"


# ---------------------------------------------------------------------------
# 4. Multi-bien
# ---------------------------------------------------------------------------
class TestModelo450MultiBien:
    @pytest.mark.asyncio
    async def test_varios_bienes_distintos_tipos(self, calc):
        r = await calc.calculate(
            bienes_producidos=[
                {"epigrafe_iae": "243", "base_imponible": 10000},  # 15%  → 1500
                {"epigrafe_iae": "1500", "base_imponible": 5000},  # 25%  → 1250
                {"epigrafe_iae": "433", "base_imponible": 8000},  # 10%  → 800
                {"epigrafe_iae": "493", "base_imponible": 2000},  #  5%  → 100
            ],
            quarter=2,
        )
        # Total bases: 25.000
        assert r["total_base_imponible"] == 25000.0
        # Total cuotas: 1500 + 1250 + 800 + 100 = 3650
        assert r["total_cuota_devengada"] == 3650.0
        assert r["resultado_liquidacion"] == 3650.0
        assert len(r["desglose_bienes"]) == 4

    @pytest.mark.asyncio
    async def test_lista_vacia_ok(self, calc):
        """Sin bienes → todo a 0, sin error."""
        r = await calc.calculate(bienes_producidos=[], quarter=1)
        assert r["total_base_imponible"] == 0.0
        assert r["total_cuota_devengada"] == 0.0
        assert r["resultado_liquidacion"] == 0.0


# ---------------------------------------------------------------------------
# 5. Compensaciones, ajustes, complementaria
# ---------------------------------------------------------------------------
class TestModelo450Ajustes:
    @pytest.mark.asyncio
    async def test_compensacion_periodos_anteriores(self, calc):
        r = await calc.calculate(
            bienes_producidos=[
                {"epigrafe_iae": "243", "base_imponible": 10000},  # 1500
            ],
            cuotas_compensar_anteriores=300,
            quarter=2,
        )
        # 1500 - 300 = 1200
        assert r["resultado_liquidacion"] == 1200.0
        assert r["cuotas_compensar_anteriores"] == 300.0

    @pytest.mark.asyncio
    async def test_compensacion_negativa_raises(self, calc):
        with pytest.raises(ValueError, match="cuotas_compensar"):
            await calc.calculate(
                bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 1000}],
                cuotas_compensar_anteriores=-100,
                quarter=1,
            )

    @pytest.mark.asyncio
    async def test_rectificacion_cuotas_suma(self, calc):
        r = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            rectificacion_cuotas=200,
            quarter=1,
        )
        # 1500 + 200 = 1700
        assert r["cuota_devengada_ajustada"] == 1700.0
        assert r["resultado_liquidacion"] == 1700.0

    @pytest.mark.asyncio
    async def test_regularizacion_anual_solo_t4(self, calc):
        """En T1-T3 la regularizacion_anual debe ignorarse."""
        r_q2 = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            regularizacion_anual=500,
            quarter=2,
        )
        assert r_q2["regularizacion_anual"] == 0.0

        r_q4 = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            regularizacion_anual=500,
            quarter=4,
        )
        assert r_q4["regularizacion_anual"] == 500.0
        # 1500 + 500 = 2000
        assert r_q4["resultado_liquidacion"] == 2000.0

    @pytest.mark.asyncio
    async def test_complementaria(self, calc):
        r = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            resultado_anterior_complementaria=400,
            quarter=1,
        )
        # 1500 - 400 = 1100
        assert r["cuota_diferencial_complementaria"] == 1100.0


# ---------------------------------------------------------------------------
# 6. Validaciones
# ---------------------------------------------------------------------------
class TestModelo450Validations:
    @pytest.mark.asyncio
    async def test_quarter_invalido(self, calc):
        with pytest.raises(ValueError, match="quarter"):
            await calc.calculate(
                bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 1000}],
                quarter=5,
            )

    @pytest.mark.asyncio
    async def test_base_negativa_raises(self, calc):
        with pytest.raises(ValueError, match="base_imponible"):
            await calc.calculate(
                bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": -1}],
                quarter=1,
            )

    @pytest.mark.asyncio
    async def test_year_fuera_rango(self, calc):
        with pytest.raises(ValueError, match="year"):
            await calc.calculate(
                bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 100}],
                quarter=1,
                year=1500,
            )

    @pytest.mark.asyncio
    async def test_periodicidad_invalida(self, calc):
        with pytest.raises(ValueError, match="periodicidad"):
            await calc.calculate(
                bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 100}],
                quarter=1,
                periodicidad="semanal",
            )

    @pytest.mark.asyncio
    async def test_mensual_sin_mes_raises(self, calc):
        with pytest.raises(ValueError, match="mes"):
            await calc.calculate(
                bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 100}],
                periodicidad="mensual",
            )

    @pytest.mark.asyncio
    async def test_bien_no_dict_raises(self, calc):
        with pytest.raises(ValueError, match="dict"):
            await calc.calculate(
                bienes_producidos=["no-soy-un-dict"],
                quarter=1,
            )


# ---------------------------------------------------------------------------
# 7. Periodicidad mensual (grandes empresas)
# ---------------------------------------------------------------------------
class TestModelo450Mensual:
    @pytest.mark.asyncio
    async def test_calculo_mensual_basico(self, calc):
        r = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 100000}],
            periodicidad="mensual",
            mes=3,
            year=2025,
        )
        assert r["periodicidad"] == "mensual"
        assert r["mes"] == 3
        assert r["periodo_label"] == "M03"
        # 100.000 * 0.15 = 15.000
        assert r["resultado_liquidacion"] == 15000.0

    @pytest.mark.asyncio
    async def test_mensual_regularizacion_no_aplica(self, calc):
        """En periodicidad mensual la regularizacion anual no se aplica."""
        r = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            periodicidad="mensual",
            mes=12,
            regularizacion_anual=999,  # ignorado
            year=2025,
        )
        assert r["regularizacion_anual"] == 0.0

    @pytest.mark.asyncio
    async def test_plazo_mensual_diciembre_pasa_a_enero_siguiente(self, calc):
        r = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 1000}],
            periodicidad="mensual",
            mes=12,
            year=2025,
        )
        # Plazo: 1-20 enero 2026
        assert "enero" in r["plazo_presentacion"]
        assert "2026" in r["plazo_presentacion"]


# ---------------------------------------------------------------------------
# 8. Plazos trimestrales
# ---------------------------------------------------------------------------
class TestModelo450Plazos:
    def test_plazos_constantes(self):
        # T1: hasta 20 abril
        assert PLAZOS_MODELO_450[1]["dia_fin"] == 20
        assert PLAZOS_MODELO_450[1]["mes_fin"] == 4
        # T4: hasta 30 enero ano siguiente
        assert PLAZOS_MODELO_450[4]["dia_fin"] == 30
        assert PLAZOS_MODELO_450[4]["mes_fin"] == 1
        assert PLAZOS_MODELO_450[4]["anio_siguiente"] is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quarter,expected_str",
        [
            (1, "del 1 al 20 de abril"),
            (2, "del 1 al 20 de julio"),
            (3, "del 1 al 20 de octubre"),
            (4, "del 1 al 30 de enero de 2026"),
        ],
    )
    async def test_plazos_por_trimestre(self, calc, quarter, expected_str):
        r = await calc.calculate(
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 1000}],
            quarter=quarter,
            year=2025,
        )
        assert expected_str in r["plazo_presentacion"]


# ---------------------------------------------------------------------------
# 9. Tool wrapper
# ---------------------------------------------------------------------------
class TestModelo450Tool:
    @pytest.mark.asyncio
    async def test_tool_basico(self):
        from app.tools.modelo_450_tool import calculate_modelo_450_tool

        r = await calculate_modelo_450_tool(
            trimestre=1,
            bienes_producidos=[
                {"epigrafe_iae": "243", "descripcion": "Hormigon", "base_imponible": 10000},
            ],
            year=2025,
        )
        assert r["success"] is True
        assert r["total_cuota_devengada"] == 1500.0
        assert "AIEM Canarias" in r["formatted_response"]
        assert "T1 2025" in r["formatted_response"]

    @pytest.mark.asyncio
    async def test_tool_trimestre_invalido(self):
        from app.tools.modelo_450_tool import calculate_modelo_450_tool

        r = await calculate_modelo_450_tool(
            trimestre=5,
            bienes_producidos=[
                {"epigrafe_iae": "243", "base_imponible": 1000},
            ],
        )
        assert r["success"] is False
        assert "trimestre" in r["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_bienes_vacios(self):
        from app.tools.modelo_450_tool import calculate_modelo_450_tool

        r = await calculate_modelo_450_tool(
            trimestre=1,
            bienes_producidos=[],
        )
        assert r["success"] is False
        assert "vacio" in r["error"].lower() or "vacio" in r["formatted_response"].lower()

    @pytest.mark.asyncio
    async def test_tool_restricted_mode(self):
        from app.tools.modelo_450_tool import calculate_modelo_450_tool

        r = await calculate_modelo_450_tool(
            trimestre=1,
            bienes_producidos=[{"epigrafe_iae": "243", "base_imponible": 1000}],
            restricted_mode=True,
        )
        assert r["success"] is False
        assert r["error"] == "restricted"

    @pytest.mark.asyncio
    async def test_tool_warning_se_propaga_a_formatted_response(self):
        from app.tools.modelo_450_tool import calculate_modelo_450_tool

        r = await calculate_modelo_450_tool(
            trimestre=1,
            bienes_producidos=[
                {
                    "epigrafe_iae": "8430",
                    "descripcion": "Asesoria",
                    "base_imponible": 5000,
                }
            ],
        )
        assert r["success"] is True
        assert "Avisos" in r["formatted_response"]
        assert r["total_cuota_devengada"] == 0.0


# ---------------------------------------------------------------------------
# 10. Tool registration
# ---------------------------------------------------------------------------
class TestModelo450Registration:
    def test_tool_in_all_tools(self):
        from app.tools import ALL_TOOLS

        names = [t["function"]["name"] for t in ALL_TOOLS]
        assert "calculate_modelo_450" in names

    def test_tool_in_executors(self):
        from app.tools import TOOL_EXECUTORS

        assert "calculate_modelo_450" in TOOL_EXECUTORS


# ---------------------------------------------------------------------------
# 11. Plugin Canarias — obligacion 450
# ---------------------------------------------------------------------------
class TestCanariasPluginAIEM:
    def test_plugin_anyade_modelo_450_si_produce_aiem(self):
        from app.territories.canarias.plugin import CanariasTerritory

        plugin = CanariasTerritory()
        obs = plugin.get_model_obligations(
            {
                "situacion_laboral": "autonomo",
                "produce_bienes_aiem": True,
            }
        )
        modelos = [o.modelo for o in obs]
        assert "450" in modelos

    def test_plugin_no_anyade_450_si_no_produce_aiem(self):
        from app.territories.canarias.plugin import CanariasTerritory

        plugin = CanariasTerritory()
        obs = plugin.get_model_obligations(
            {
                "situacion_laboral": "autonomo",
                "produce_bienes_aiem": False,
            }
        )
        modelos = [o.modelo for o in obs]
        assert "450" not in modelos

    def test_plugin_detecta_aiem_por_epigrafe_iae(self):
        from app.territories.canarias.plugin import CanariasTerritory

        plugin = CanariasTerritory()
        obs = plugin.get_model_obligations(
            {
                "situacion_laboral": "autonomo",
                "epigrafes_iae": ["243"],  # hormigon → AIEM 15%
            }
        )
        modelos = [o.modelo for o in obs]
        assert "450" in modelos


# ---------------------------------------------------------------------------
# 12. AIEM_TIPOS_POR_EPIGRAFE — sanidad de la tabla seed
# ---------------------------------------------------------------------------
class TestAIEMTiposTabla:
    def test_todos_los_tipos_son_validos(self):
        for epi, tipo in AIEM_TIPOS_POR_EPIGRAFE.items():
            assert (
                tipo in ALLOWED_AIEM_RATES
            ), f"Epigrafe {epi} tiene tipo {tipo} fuera de la lista oficial."

    def test_tabla_no_vacia(self):
        assert len(AIEM_TIPOS_POR_EPIGRAFE) > 10
