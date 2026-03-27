"""Tests for segundo declarante support in IRPF estimation (Art. 82-84 LIRPF).

Covers:
- SegundoDeclarante model validation and defaults
- IRPFEstimateRequest with segundo_declarante field
- Conjunta with 2 declarants — equal incomes
- Conjunta with 2 declarants — unequal incomes (advantage for conjunta)
- Conjunta without segundo_declarante → backward compatible
- Individual vs conjunta — case where individual is better
- Individual vs conjunta — case where conjunta is better
- Segundo declarante with activity income
- MPYF with 2 declarants (minimums summed)
- Monoparental (2.150 EUR reduction)

All tests mock IRPFSimulator internals so no live Turso/DB connection is required.
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.routers.irpf_estimate import (
    IRPFEstimateRequest,
    IRPFEstimateResponse,
    SegundoDeclarante,
)


# ---------------------------------------------------------------------------
# SegundoDeclarante model tests
# ---------------------------------------------------------------------------

class TestSegundoDeclaranteModel:
    """Tests for the SegundoDeclarante Pydantic model."""

    def test_default_values(self):
        sd = SegundoDeclarante()
        assert sd.ingresos_trabajo == 0
        assert sd.ingresos_actividad == 0
        assert sd.gastos_actividad == 0
        assert sd.ingresos_alquiler == 0
        assert sd.gastos_alquiler == 0
        assert sd.intereses == 0
        assert sd.dividendos == 0
        assert sd.ganancias_patrimoniales == 0
        assert sd.edad == 30
        assert sd.discapacidad == 0
        assert sd.aportaciones_plan_pensiones == 0

    def test_with_values(self):
        sd = SegundoDeclarante(
            ingresos_trabajo=25000,
            edad=40,
            discapacidad=33,
            aportaciones_plan_pensiones=1000,
        )
        assert sd.ingresos_trabajo == 25000
        assert sd.edad == 40
        assert sd.discapacidad == 33
        assert sd.aportaciones_plan_pensiones == 1000

    def test_model_dump(self):
        sd = SegundoDeclarante(ingresos_trabajo=30000, edad=35)
        d = sd.model_dump()
        assert d["ingresos_trabajo"] == 30000
        assert d["edad"] == 35
        assert d["discapacidad"] == 0

    def test_activity_income(self):
        sd = SegundoDeclarante(
            ingresos_actividad=40000,
            gastos_actividad=10000,
        )
        assert sd.ingresos_actividad == 40000
        assert sd.gastos_actividad == 10000

    def test_savings_income(self):
        sd = SegundoDeclarante(
            intereses=500,
            dividendos=1000,
            ganancias_patrimoniales=3000,
        )
        assert sd.intereses == 500
        assert sd.dividendos == 1000
        assert sd.ganancias_patrimoniales == 3000


class TestIRPFEstimateRequestSegundoDeclarante:
    """Test that IRPFEstimateRequest accepts segundo_declarante."""

    def test_request_without_segundo_declarante(self):
        req = IRPFEstimateRequest(comunidad_autonoma="Madrid")
        assert req.segundo_declarante is None

    def test_request_with_segundo_declarante(self):
        req = IRPFEstimateRequest(
            comunidad_autonoma="Madrid",
            ingresos_trabajo=40000,
            tributacion_conjunta=True,
            segundo_declarante=SegundoDeclarante(
                ingresos_trabajo=25000,
                edad=38,
            ),
        )
        assert req.segundo_declarante is not None
        assert req.segundo_declarante.ingresos_trabajo == 25000
        assert req.segundo_declarante.edad == 38
        assert req.tributacion_conjunta is True

    def test_request_conjunta_without_sd_backward_compat(self):
        """tributacion_conjunta=True without segundo_declarante should still work."""
        req = IRPFEstimateRequest(
            comunidad_autonoma="Madrid",
            ingresos_trabajo=50000,
            tributacion_conjunta=True,
        )
        assert req.tributacion_conjunta is True
        assert req.segundo_declarante is None


# ---------------------------------------------------------------------------
# Simulator integration tests (mock DB, real simulator logic)
# ---------------------------------------------------------------------------

def _make_mock_db():
    """Create a mock database that returns valid scale data."""
    mock_db = AsyncMock()

    # Estatal scale (simplified 2-tramo)
    estatal_rows = [
        {"tramo_num": 1, "base_hasta": 12450, "cuota_integra": 0, "resto_base": 12450, "tipo_aplicable": 9.5},
        {"tramo_num": 2, "base_hasta": 20200, "cuota_integra": 1182.75, "resto_base": 7750, "tipo_aplicable": 12.0},
        {"tramo_num": 3, "base_hasta": 35200, "cuota_integra": 2112.75, "resto_base": 15000, "tipo_aplicable": 15.0},
        {"tramo_num": 4, "base_hasta": 60000, "cuota_integra": 4362.75, "resto_base": 24800, "tipo_aplicable": 18.5},
        {"tramo_num": 5, "base_hasta": 300000, "cuota_integra": 8950.75, "resto_base": 240000, "tipo_aplicable": 22.5},
    ]

    # Madrid autonomous scale (simplified)
    madrid_rows = [
        {"tramo_num": 1, "base_hasta": 12450, "cuota_integra": 0, "resto_base": 12450, "tipo_aplicable": 8.5},
        {"tramo_num": 2, "base_hasta": 17707.2, "cuota_integra": 1058.25, "resto_base": 5257.2, "tipo_aplicable": 10.7},
        {"tramo_num": 3, "base_hasta": 33007.2, "cuota_integra": 1620.77, "resto_base": 15300, "tipo_aplicable": 12.8},
        {"tramo_num": 4, "base_hasta": 53407.2, "cuota_integra": 3579.17, "resto_base": 20400, "tipo_aplicable": 17.4},
        {"tramo_num": 5, "base_hasta": 300000, "cuota_integra": 7128.77, "resto_base": 246592.8, "tipo_aplicable": 20.5},
    ]

    # Ahorro scales
    ahorro_estatal_rows = [
        {"tramo_num": 1, "base_hasta": 6000, "cuota_integra": 0, "resto_base": 6000, "tipo_aplicable": 9.5},
        {"tramo_num": 2, "base_hasta": 50000, "cuota_integra": 570, "resto_base": 44000, "tipo_aplicable": 10.5},
    ]

    ahorro_madrid_rows = [
        {"tramo_num": 1, "base_hasta": 6000, "cuota_integra": 0, "resto_base": 6000, "tipo_aplicable": 9.5},
        {"tramo_num": 2, "base_hasta": 50000, "cuota_integra": 570, "resto_base": 44000, "tipo_aplicable": 10.5},
    ]

    # MPYF params (column is 'value' not 'param_value')
    mpyf_params_rows = [
        {"param_key": "contribuyente", "value": 5550.0},
        {"param_key": "contribuyente_65", "value": 6700.0},
        {"param_key": "contribuyente_75", "value": 8100.0},
        {"param_key": "descendiente_1", "value": 2400.0},
        {"param_key": "descendiente_2", "value": 2700.0},
        {"param_key": "descendiente_3", "value": 4000.0},
        {"param_key": "descendiente_4_plus", "value": 4500.0},
        {"param_key": "descendiente_menor_3", "value": 2800.0},
        {"param_key": "ascendiente_65", "value": 1150.0},
        {"param_key": "ascendiente_75", "value": 1400.0},
        {"param_key": "discapacidad_33_65", "value": 3000.0},
        {"param_key": "discapacidad_65_plus", "value": 9000.0},
        {"param_key": "gastos_asistencia", "value": 3000.0},
    ]

    # Work income params (Art. 19-20 LIRPF)
    trabajo_params_rows = [
        {"param_key": "gastos_deducibles_otros", "value": 2000.0},
        {"param_key": "reduccion_limite_inferior", "value": 14852.0},
        {"param_key": "reduccion_limite_superior", "value": 17673.52},
        {"param_key": "reduccion_max", "value": 6498.0},
        {"param_key": "reduccion_min", "value": 1620.0},
    ]

    # Rental income params
    inmuebles_params_rows = [
        {"param_key": "reduccion_vivienda", "value": 60.0},
        {"param_key": "amortizacion_pct", "value": 3.0},
    ]

    # Activity income params
    actividad_params_rows = [
        {"param_key": "gastos_dificil_justificacion_pct", "value": 7.0},
        {"param_key": "gastos_dificil_justificacion_max", "value": 2000.0},
        {"param_key": "reduccion_rendimientos_irregulares_pct", "value": 30.0},
        {"param_key": "reduccion_rendimientos_irregulares_max", "value": 300000.0},
    ]

    def make_rows(data):
        """Convert dicts to mock row objects that support both dict() and dict-key access."""
        rows = []
        for d in data:
            row = MagicMock()
            row.__getitem__ = lambda self, k, d=d: d[k]
            row.keys = lambda d=d: d.keys()
            row.__iter__ = lambda self, d=d: iter(d)
            # For dict(row) to work
            items = list(d.items())
            row.items = lambda items=items: items
            rows.append(row)
        return rows

    async def mock_execute(query, params=None):
        query_lower = query.lower().strip()
        result = MagicMock()

        # irpf_scales queries
        if "irpf_scales" in query_lower:
            if params:
                jurisdiction = params[0] if params else ""
                year = params[1] if len(params) > 1 else 2024
                scale_type = ""
                if len(params) > 2:
                    scale_type = params[2]

                if "scale_type = ?" in query_lower or "scale_type=?" in query_lower:
                    # ahorro scale query
                    if scale_type == "ahorro":
                        if "estatal" in str(jurisdiction).lower():
                            result.rows = make_rows(ahorro_estatal_rows)
                        else:
                            result.rows = make_rows(ahorro_madrid_rows)
                    elif scale_type == "foral":
                        result.rows = []
                    else:
                        result.rows = []
                else:
                    # general scale query
                    if "estatal" in str(jurisdiction).lower():
                        result.rows = make_rows(estatal_rows)
                    else:
                        result.rows = make_rows(madrid_rows)
            else:
                result.rows = make_rows(estatal_rows)
        # tax_parameters queries — route by category param
        elif "tax_parameters" in query_lower:
            category = params[0] if params else ""
            if category == "mpyf":
                result.rows = make_rows(mpyf_params_rows)
            elif category == "trabajo":
                result.rows = make_rows(trabajo_params_rows)
            elif category == "inmuebles":
                result.rows = make_rows(inmuebles_params_rows)
            elif category in ("actividad", "activity"):
                result.rows = make_rows(actividad_params_rows)
            else:
                result.rows = make_rows(mpyf_params_rows)  # fallback
        else:
            result.rows = []

        return result

    mock_db.execute = AsyncMock(side_effect=mock_execute)
    return mock_db


@pytest.fixture
def mock_db():
    return _make_mock_db()


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Simulator-level tests
# ---------------------------------------------------------------------------

class TestSegundoDeclaranteSimulator:
    """Tests that exercise the real IRPFSimulator with segundo_declarante."""

    @pytest.mark.asyncio
    async def test_conjunta_two_equal_incomes(self, mock_db):
        """Conjunta with two equal incomes — both contribute equally."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)
        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 30000,
                "edad": 35,
            },
        )

        assert result["success"] is True
        assert result["reduccion_tributacion_conjunta"] == 3400.0
        assert result["segundo_declarante_desglose"] is not None
        sd_desglose = result["segundo_declarante_desglose"]
        assert sd_desglose["ingresos_trabajo"] == 30000
        assert sd_desglose["rendimiento_neto_trabajo"] > 0
        # Base should include both declarants' income
        assert result["base_imponible_general"] > 30000

    @pytest.mark.asyncio
    async def test_conjunta_unequal_incomes(self, mock_db):
        """Conjunta with very unequal incomes — one earner + one with low/zero income."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)
        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=50000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 5000,
                "edad": 33,
            },
        )

        assert result["success"] is True
        assert result["reduccion_tributacion_conjunta"] == 3400.0
        sd = result["segundo_declarante_desglose"]
        assert sd is not None
        assert sd["ingresos_trabajo"] == 5000

    @pytest.mark.asyncio
    async def test_conjunta_without_segundo_declarante_backward_compat(self, mock_db):
        """Conjunta without segundo_declarante keeps existing behavior."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)
        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
        )

        assert result["success"] is True
        assert result["reduccion_tributacion_conjunta"] == 3400.0
        assert result["segundo_declarante_desglose"] is None

    @pytest.mark.asyncio
    async def test_individual_vs_conjunta_individual_better(self, mock_db):
        """When both have similar high incomes, individual is usually better."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # Individual: declarante 1
        r1 = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            tributacion_conjunta=False,
        )

        # Individual: declarante 2
        r2 = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            tributacion_conjunta=False,
        )

        # Conjunta
        r_conj = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 40000,
                "edad": 35,
            },
        )

        total_individual = r1["cuota_diferencial"] + r2["cuota_diferencial"]
        cuota_conjunta = r_conj["cuota_diferencial"]

        # With two equal high earners, individual should be better (progressive scale)
        # because summing puts income in higher brackets
        assert total_individual < cuota_conjunta

    @pytest.mark.asyncio
    async def test_individual_vs_conjunta_conjunta_better(self, mock_db):
        """When one earns much more than the other, conjunta can be better
        due to the 3.400 reduction + lower effective rate on combined income."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # Individual: declarante 1
        r1 = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=False,
        )

        # Individual: declarante 2 — zero income
        r2 = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=0,
            tributacion_conjunta=False,
        )

        # Conjunta
        r_conj = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 0,
                "edad": 35,
            },
        )

        total_individual = r1["cuota_diferencial"] + r2["cuota_diferencial"]
        cuota_conjunta = r_conj["cuota_diferencial"]

        # With zero second income, conjunta should be better due to 3400 reduction
        # plus the segundo declarante adds their personal minimum to MPYF
        assert cuota_conjunta < total_individual

    @pytest.mark.asyncio
    async def test_segundo_declarante_activity_income(self, mock_db):
        """Segundo declarante with activity income (autonomo)."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)
        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=35000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_actividad": 20000,
                "gastos_actividad": 5000,
                "edad": 40,
            },
        )

        assert result["success"] is True
        sd = result["segundo_declarante_desglose"]
        assert sd is not None
        assert sd["ingresos_actividad"] == 20000
        assert sd["rendimiento_neto_actividad"] > 0
        assert sd["rendimiento_neto_trabajo"] == 0  # no work income for SD

    @pytest.mark.asyncio
    async def test_mpyf_two_declarants_summed(self, mock_db):
        """MPYF should include personal minimum from both declarants."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # Single declarant
        r_single = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            tributacion_conjunta=False,
        )

        # Joint with segundo declarante
        r_joint = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=40000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 0,
                "edad": 35,
            },
        )

        mpyf_single_est = r_single["mpyf"]["mpyf_estatal"]
        mpyf_joint_est = r_joint["mpyf"]["mpyf_estatal"]

        # Joint MPYF should be higher because it includes 2nd declarant's personal minimum
        assert mpyf_joint_est > mpyf_single_est

        # Check segundo_declarante_desglose has MPYF info
        sd = r_joint["segundo_declarante_desglose"]
        assert sd is not None
        assert "mpyf_personal_estatal" in sd
        assert sd["mpyf_personal_estatal"] > 0

    @pytest.mark.asyncio
    async def test_monoparental_reduction(self, mock_db):
        """Monoparental uses 2.150 EUR reduction instead of 3.400."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)
        result = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="monoparental",
            num_descendientes=1,
        )

        assert result["success"] is True
        assert result["reduccion_tributacion_conjunta"] == 2150.0
        # No segundo_declarante for monoparental
        assert result["segundo_declarante_desglose"] is None

    @pytest.mark.asyncio
    async def test_segundo_declarante_savings_income(self, mock_db):
        """Segundo declarante's savings income adds to base_ahorro."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # Without SD
        r_without = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            intereses=1000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
        )

        # With SD that has savings
        r_with = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            intereses=1000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 0,
                "intereses": 2000,
                "dividendos": 500,
                "edad": 35,
            },
        )

        # Base ahorro should be higher with SD
        assert r_with["base_imponible_ahorro"] > r_without["base_imponible_ahorro"]
        sd = r_with["segundo_declarante_desglose"]
        assert sd["ahorro_sd"] == 2500  # 2000 + 500

    @pytest.mark.asyncio
    async def test_segundo_declarante_elderly_mpyf(self, mock_db):
        """Segundo declarante over 65 gets higher personal minimum."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # SD age 35
        r_young = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 0,
                "edad": 35,
            },
        )

        # SD age 70
        r_old = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 0,
                "edad": 70,
            },
        )

        # Elderly SD should have higher MPYF
        assert r_old["mpyf"]["mpyf_estatal"] > r_young["mpyf"]["mpyf_estatal"]

    @pytest.mark.asyncio
    async def test_segundo_declarante_disabled_mpyf(self, mock_db):
        """Segundo declarante with disability gets extra MPYF."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # SD without disability
        r_no_disc = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 0,
                "edad": 35,
                "discapacidad": 0,
            },
        )

        # SD with disability 33%
        r_disc = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 0,
                "edad": 35,
                "discapacidad": 33,
            },
        )

        # Disabled SD should have higher MPYF (3000 EUR extra for discapacidad_33_65)
        assert r_disc["mpyf"]["mpyf_estatal"] > r_no_disc["mpyf"]["mpyf_estatal"]

    @pytest.mark.asyncio
    async def test_segundo_declarante_pension_plan(self, mock_db):
        """Segundo declarante's pension plan contributions reduce the combined base."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # SD without pension plan
        r_no_pp = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 20000,
                "edad": 35,
                "aportaciones_plan_pensiones": 0,
            },
        )

        # SD with pension plan
        r_with_pp = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 20000,
                "edad": 35,
                "aportaciones_plan_pensiones": 1500,
            },
        )

        # With pension plan, base should be lower
        assert r_with_pp["base_imponible_general"] < r_no_pp["base_imponible_general"]
        sd = r_with_pp["segundo_declarante_desglose"]
        assert sd["reduccion_planes_pensiones_sd"] > 0

    @pytest.mark.asyncio
    async def test_segundo_declarante_property_sale(self, mock_db):
        """Segundo declarante's property gains go to base del ahorro."""
        from app.utils.irpf_simulator import IRPFSimulator

        sim = IRPFSimulator(mock_db)

        # Without SD property sale
        r_without = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 15000,
                "edad": 35,
            },
        )

        # With SD property sale (50K gain)
        r_with = await sim.simulate(
            jurisdiction="Madrid",
            year=2024,
            ingresos_trabajo=30000,
            tributacion_conjunta=True,
            tipo_unidad_familiar="matrimonio",
            segundo_declarante={
                "ingresos_trabajo": 15000,
                "edad": 35,
                "ventas_inmuebles": [
                    {
                        "tipo": "otro",
                        "precio_venta": 200_000,
                        "precio_adquisicion": 150_000,
                        "fecha_adquisicion": "2015-01-01",
                        "fecha_venta": "2024-06-01",
                        "gastos_adquisicion": 0,
                        "gastos_venta": 0,
                        "mejoras": 0,
                        "amortizaciones": 0,
                    }
                ],
            },
        )

        assert r_with["success"] is True
        # Base ahorro should be higher by 50K from the SD's property sale
        assert r_with["base_imponible_ahorro"] > r_without["base_imponible_ahorro"]
        sd = r_with["segundo_declarante_desglose"]
        assert sd is not None
        assert sd["ganancias_inmuebles_sd"] is not None
        assert sd["ganancias_inmuebles_sd"]["ganancia_neta_total"] == 50_000.0
        # ahorro_sd should include the 50K
        assert sd["ahorro_sd"] >= 50_000.0
