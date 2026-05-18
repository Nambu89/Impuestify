"""
Tests for Modelo 455 — AIEM ZEC Canarias (entidades ZEC).

Cubre Modelo455Calculator + calculate_modelo_455_tool.

Norma vigente:
- Decreto Legislativo 1/2025 (BOC nº 207, 2025-10-20).
- Ley 19/1994 (Titulo V — ZEC).
- RD 1758/2007 (Reglamento ZEC).

Periodicidad: ANUAL (1-30 enero ano siguiente). Trimestral excepcional.
"""

from __future__ import annotations

import pytest

from app.utils.calculators.modelo_455 import (
    PLAZO_MODELO_455_ANUAL,
    TIPO_AIEM_ESPECIAL,
    TIPO_AIEM_GENERAL,
    TIPO_AIEM_INTERMEDIO,
    TIPO_AIEM_REDUCIDO,
    Modelo455Calculator,
)


@pytest.fixture
def calc():
    return Modelo455Calculator(None)


# ---------------------------------------------------------------------------
# 1. Calculator basico
# ---------------------------------------------------------------------------
class TestModelo455Basic:
    @pytest.mark.asyncio
    async def test_anual_un_bien_tipo_general(self, calc):
        """Entidad ZEC factura 100.000 EUR de hormigon en el ejercicio."""
        r = await calc.calculate(
            bienes_anuales=[
                {
                    "epigrafe_iae": "243",
                    "descripcion": "Hormigon",
                    "base_imponible": 100000,
                }
            ],
            epigrafe_zec="ZEC-243-IND",
            year=2025,
        )
        assert r["modelo"] == "455"
        assert r["regimen"] == "ZEC"
        assert r["periodicidad"] == "anual"
        assert r["epigrafe_zec"] == "ZEC-243-IND"
        # 100.000 * 0.15 = 15.000
        assert r["total_cuota_devengada"] == 15000.0
        assert r["resultado_liquidacion"] == 15000.0

    @pytest.mark.asyncio
    async def test_anual_multi_bien(self, calc):
        r = await calc.calculate(
            bienes_anuales=[
                {"epigrafe_iae": "243", "base_imponible": 50000},  # 15% → 7500
                {"epigrafe_iae": "1500", "base_imponible": 20000},  # 25% → 5000
            ],
            year=2025,
        )
        # 7500 + 5000 = 12500
        assert r["total_cuota_devengada"] == 12500.0

    @pytest.mark.asyncio
    async def test_anual_tipo_manual(self, calc):
        r = await calc.calculate(
            bienes_anuales=[
                {
                    "base_imponible": 80000,
                    "tipo_aiem": 0.10,
                }
            ],
            year=2025,
        )
        # 80.000 * 0.10 = 8.000
        assert r["total_cuota_devengada"] == 8000.0
        assert r["desglose_bienes"][0]["origen_tipo"] == "manual"


# ---------------------------------------------------------------------------
# 2. Plazo y periodicidad
# ---------------------------------------------------------------------------
class TestModelo455Plazos:
    def test_plazo_anual_constante(self):
        assert PLAZO_MODELO_455_ANUAL["dia_fin"] == 30
        assert PLAZO_MODELO_455_ANUAL["mes_fin"] == 1
        assert PLAZO_MODELO_455_ANUAL["anio_siguiente"] is True

    @pytest.mark.asyncio
    async def test_plazo_anual_string(self, calc):
        r = await calc.calculate(
            bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 1000}],
            year=2025,
        )
        # Plazo: 1-30 enero 2026
        assert "30 de enero de 2026" in r["plazo_presentacion"]
        assert r["periodo_label"] == "ANUAL"

    @pytest.mark.asyncio
    async def test_periodicidad_trimestral_acepta_quarter(self, calc):
        r = await calc.calculate(
            bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            year=2025,
            periodicidad="trimestral",
            quarter=2,
        )
        assert r["periodicidad"] == "trimestral"
        assert r["periodo_label"] == "T2"
        assert "20 de julio" in r["plazo_presentacion"]

    @pytest.mark.asyncio
    async def test_trimestral_sin_quarter_raises(self, calc):
        with pytest.raises(ValueError, match="quarter"):
            await calc.calculate(
                bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 100}],
                periodicidad="trimestral",
            )


# ---------------------------------------------------------------------------
# 3. Ajustes y compensaciones
# ---------------------------------------------------------------------------
class TestModelo455Ajustes:
    @pytest.mark.asyncio
    async def test_regularizacion_anual_se_aplica_siempre_en_modo_anual(self, calc):
        """En 455 ANUAL la regularizacion siempre se aplica (es la liquidacion final)."""
        r = await calc.calculate(
            bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            regularizacion_anual=200,
            year=2025,
        )
        # 1500 + 200 = 1700
        assert r["regularizacion_anual"] == 200.0
        assert r["resultado_liquidacion"] == 1700.0

    @pytest.mark.asyncio
    async def test_compensacion_periodos_anteriores(self, calc):
        r = await calc.calculate(
            bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            cuotas_compensar_anteriores=400,
            year=2025,
        )
        # 1500 - 400 = 1100
        assert r["resultado_liquidacion"] == 1100.0

    @pytest.mark.asyncio
    async def test_complementaria(self, calc):
        r = await calc.calculate(
            bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            resultado_anterior_complementaria=500,
            year=2025,
        )
        # 1500 - 500 = 1000
        assert r["cuota_diferencial_complementaria"] == 1000.0


# ---------------------------------------------------------------------------
# 4. Validaciones
# ---------------------------------------------------------------------------
class TestModelo455Validations:
    @pytest.mark.asyncio
    async def test_periodicidad_invalida(self, calc):
        with pytest.raises(ValueError, match="periodicidad"):
            await calc.calculate(
                bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 100}],
                periodicidad="mensual",  # no soportado en 455
            )

    @pytest.mark.asyncio
    async def test_compensacion_negativa_raises(self, calc):
        with pytest.raises(ValueError, match="cuotas_compensar"):
            await calc.calculate(
                bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 1000}],
                cuotas_compensar_anteriores=-50,
                year=2025,
            )

    @pytest.mark.asyncio
    async def test_year_fuera_rango(self, calc):
        with pytest.raises(ValueError, match="year"):
            await calc.calculate(
                bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 100}],
                year=2200,
            )


# ---------------------------------------------------------------------------
# 5. Tool wrapper
# ---------------------------------------------------------------------------
class TestModelo455Tool:
    @pytest.mark.asyncio
    async def test_tool_anual_basico(self):
        from app.tools.modelo_455_tool import calculate_modelo_455_tool

        r = await calculate_modelo_455_tool(
            bienes_anuales=[
                {"epigrafe_iae": "243", "descripcion": "Hormigon", "base_imponible": 100000},
            ],
            epigrafe_zec="ZEC-243-IND",
            year=2025,
        )
        assert r["success"] is True
        assert r["total_cuota_devengada"] == 15000.0
        assert "AIEM ZEC Canarias" in r["formatted_response"]
        assert "ANUAL 2025" in r["formatted_response"]
        assert "30 de enero de 2026" in r["formatted_response"]

    @pytest.mark.asyncio
    async def test_tool_bienes_vacios(self):
        from app.tools.modelo_455_tool import calculate_modelo_455_tool

        r = await calculate_modelo_455_tool(bienes_anuales=[])
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_tool_restricted_mode(self):
        from app.tools.modelo_455_tool import calculate_modelo_455_tool

        r = await calculate_modelo_455_tool(
            bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            restricted_mode=True,
        )
        assert r["success"] is False
        assert r["error"] == "restricted"

    @pytest.mark.asyncio
    async def test_tool_periodicidad_trimestral(self):
        from app.tools.modelo_455_tool import calculate_modelo_455_tool

        r = await calculate_modelo_455_tool(
            bienes_anuales=[{"epigrafe_iae": "243", "base_imponible": 10000}],
            periodicidad="trimestral",
            trimestre=3,
            year=2025,
        )
        assert r["success"] is True
        assert "T3" in r["formatted_response"]


# ---------------------------------------------------------------------------
# 6. Tool registration y plugin
# ---------------------------------------------------------------------------
class TestModelo455Registration:
    def test_tool_in_all_tools(self):
        from app.tools import ALL_TOOLS

        names = [t["function"]["name"] for t in ALL_TOOLS]
        assert "calculate_modelo_455" in names

    def test_tool_in_executors(self):
        from app.tools import TOOL_EXECUTORS

        assert "calculate_modelo_455" in TOOL_EXECUTORS

    def test_plugin_anyade_modelo_455_si_zec(self):
        from app.territories.canarias.plugin import CanariasTerritory

        plugin = CanariasTerritory()
        obs = plugin.get_model_obligations(
            {
                "situacion_laboral": "sociedad",
                "regimen_zec": True,
            }
        )
        modelos = [o.modelo for o in obs]
        assert "455" in modelos

    def test_plugin_no_anyade_455_si_no_zec(self):
        from app.territories.canarias.plugin import CanariasTerritory

        plugin = CanariasTerritory()
        obs = plugin.get_model_obligations(
            {
                "situacion_laboral": "sociedad",
                "regimen_zec": False,
            }
        )
        modelos = [o.modelo for o in obs]
        assert "455" not in modelos
