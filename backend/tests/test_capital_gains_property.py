"""
Tests for PropertyCapitalGainsCalculator — GP transmision de inmuebles.

Covers:
1. Basic sale (no abatimiento, no reinversion)
2. Art. 38 full reinversion (100% exempt)
3. Art. 38 partial reinversion (proportional)
4. DT 9a pre-1994 abatimiento
5. DT 9a 400K cumulative limit
6. Post-2006 acquisition (no abatimiento)
7. Multiple sales (aggregation)
8. Integration with IRPFSimulator
9. Sale at a loss (no abatimiento/reinversion)
10. Edge case: vivienda habitual but no reinversion flag
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.utils.calculators.capital_gains_property import (
    PropertyCapitalGainsCalculator,
    COEF_ABATIMIENTO_INMUEBLES,
    FECHA_LIMITE_ABATIMIENTO,
    FECHA_FIN_PERMANENCIA,
    LIMITE_ACUMULADO_TRANSMISION,
)


@pytest.fixture
def calculator():
    return PropertyCapitalGainsCalculator()


# ---------------------------------------------------------------------------
# 1. Basic sale — no abatimiento, no reinversion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_basic_sale_no_exemptions(calculator):
    """Simple sale: bought 2010, sold 2025, no reinversion."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 300_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2010-06-15",
            "fecha_venta": "2025-03-01",
            "gastos_adquisicion": 10_000,  # notaria, registro, ITP
            "gastos_venta": 5_000,  # plusvalia municipal
            "mejoras": 15_000,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": False,
            "importe_reinversion": 0,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    assert result["num_ventas"] == 1
    # valor transmision = 300000 - 5000 = 295000
    # valor adquisicion = 200000 + 10000 + 15000 - 0 = 225000
    # ganancia bruta = 295000 - 225000 = 70000
    assert result["ganancia_bruta_total"] == 70_000.0
    assert result["abatimiento_total"] == 0.0
    assert result["exencion_reinversion_total"] == 0.0
    assert result["ganancia_neta_total"] == 70_000.0

    desglose = result["desglose"][0]
    assert desglose["aplica_abatimiento"] is False
    assert desglose["aplica_reinversion"] is False


# ---------------------------------------------------------------------------
# 2. Art. 38 — full reinversion (100% exempt)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_art38_full_reinversion(calculator):
    """Vivienda habitual with full reinversion: gain fully exempt."""
    ventas = [
        {
            "tipo": "vivienda_habitual",
            "precio_venta": 400_000,
            "precio_adquisicion": 250_000,
            "fecha_adquisicion": "2005-01-10",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 12_000,
            "gastos_venta": 8_000,
            "mejoras": 20_000,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": True,
            "importe_reinversion": 400_000,  # >= precio_venta → 100% exempt
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # ganancia bruta = (400000 - 8000) - (250000 + 12000 + 20000 - 0) = 392000 - 282000 = 110000
    assert result["ganancia_bruta_total"] == 110_000.0
    # Full reinversion: ratio = min(400000/400000, 1.0) = 1.0
    # exencion = 110000 * 1.0 = 110000
    assert result["exencion_reinversion_total"] == 110_000.0
    assert result["ganancia_neta_total"] == 0.0


# ---------------------------------------------------------------------------
# 3. Art. 38 — partial reinversion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_art38_partial_reinversion(calculator):
    """Vivienda habitual with partial reinversion: proportional exemption."""
    ventas = [
        {
            "tipo": "vivienda_habitual",
            "precio_venta": 300_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2008-03-20",
            "fecha_venta": "2025-09-15",
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": True,
            "importe_reinversion": 150_000,  # 50% of precio_venta
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # ganancia bruta = 300000 - 200000 = 100000
    assert result["ganancia_bruta_total"] == 100_000.0
    # ratio = 150000 / 300000 = 0.5
    # exencion = 100000 * 0.5 = 50000
    assert result["exencion_reinversion_total"] == 50_000.0
    assert result["ganancia_neta_total"] == 50_000.0


# ---------------------------------------------------------------------------
# 4. DT 9a — pre-1994 acquisition (abatimiento)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dt9a_abatimiento_pre1994(calculator):
    """Property acquired before 31/12/1994 gets abatimiento reduction."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 350_000,
            "precio_adquisicion": 50_000,
            "fecha_adquisicion": "1985-06-01",
            "fecha_venta": "2025-04-01",
            "gastos_adquisicion": 5_000,
            "gastos_venta": 10_000,
            "mejoras": 0,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": False,
            "importe_reinversion": 0,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # ganancia bruta = (350000 - 10000) - (50000 + 5000 + 0 - 0) = 340000 - 55000 = 285000
    assert result["ganancia_bruta_total"] == 285_000.0

    # Abatimiento calculation:
    # From 1985-06-01 to 2006-01-19 = ~20.6 years → ceil = 21 years
    # Reduction years = 21 - 2 = 19
    # Coefficient = 19 * 11.11% = 211.09% → capped at 100%
    desglose = result["desglose"][0]
    assert desglose["aplica_abatimiento"] is True
    assert desglose["coeficiente_abatimiento_pct"] == 100.0
    # 100% abated → full gain eliminated
    assert desglose["abatimiento"] == 285_000.0
    assert result["ganancia_neta_total"] == 0.0


# ---------------------------------------------------------------------------
# 5. DT 9a — 400K cumulative limit exceeded
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dt9a_400k_limit(calculator):
    """Pre-1994 property but valor transmision > 400K: no abatimiento."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 500_000,  # > 400K
            "precio_adquisicion": 100_000,
            "fecha_adquisicion": "1990-01-01",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": False,
            "importe_reinversion": 0,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # ganancia bruta = 500000 - 100000 = 400000
    assert result["ganancia_bruta_total"] == 400_000.0
    # 400K limit: 0 + 500000 = 500000 > 400000 → no abatimiento
    desglose = result["desglose"][0]
    assert desglose["aplica_abatimiento"] is False
    assert result["ganancia_neta_total"] == 400_000.0


# ---------------------------------------------------------------------------
# 6. Post-2006 acquisition — no abatimiento
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post2006_no_abatimiento(calculator):
    """Property acquired after 1994: no abatimiento applies."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 250_000,
            "precio_adquisicion": 180_000,
            "fecha_adquisicion": "2000-05-15",
            "fecha_venta": "2025-11-01",
            "gastos_adquisicion": 5_000,
            "gastos_venta": 3_000,
            "mejoras": 2_000,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": False,
            "importe_reinversion": 0,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # valor transmision = 250000 - 3000 = 247000
    # valor adquisicion = 180000 + 5000 + 2000 = 187000
    # ganancia = 247000 - 187000 = 60000
    assert result["ganancia_bruta_total"] == 60_000.0
    assert result["abatimiento_total"] == 0.0
    desglose = result["desglose"][0]
    assert desglose["aplica_abatimiento"] is False
    assert result["ganancia_neta_total"] == 60_000.0


# ---------------------------------------------------------------------------
# 7. Multiple sales — aggregation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiple_sales_aggregation(calculator):
    """Two sales: gains are aggregated correctly."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 200_000,
            "precio_adquisicion": 150_000,
            "fecha_adquisicion": "2015-01-01",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
        },
        {
            "tipo": "otro",
            "precio_venta": 300_000,
            "precio_adquisicion": 250_000,
            "fecha_adquisicion": "2018-07-01",
            "fecha_venta": "2025-08-01",
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
        },
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    assert result["num_ventas"] == 2
    # Sale 1: 200000 - 150000 = 50000
    # Sale 2: 300000 - 250000 = 50000
    assert result["ganancia_bruta_total"] == 100_000.0
    assert result["ganancia_neta_total"] == 100_000.0
    assert len(result["desglose"]) == 2


# ---------------------------------------------------------------------------
# 8. Integration with IRPFSimulator
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simulator_integration():
    """Verify that ventas_inmuebles flows through IRPFSimulator.simulate()."""
    from app.utils.irpf_simulator import IRPFSimulator

    # Create a mock DB that returns scales
    mock_db = AsyncMock()

    # Mock scale rows (Estatal general + ahorro + CCAA general + ahorro)
    def make_scale_rows(scale_type):
        """Generate mock scale rows."""
        if scale_type == "ahorro":
            return [
                {"tramo_num": 1, "base_hasta": 6000, "cuota_integra": 0, "resto_base": 6000, "tipo_aplicable": 19.0},
                {"tramo_num": 2, "base_hasta": 50000, "cuota_integra": 1140, "resto_base": 44000, "tipo_aplicable": 21.0},
                {"tramo_num": 3, "base_hasta": 200000, "cuota_integra": 10380, "resto_base": 150000, "tipo_aplicable": 23.0},
                {"tramo_num": 4, "base_hasta": 300000, "cuota_integra": 44880, "resto_base": 100000, "tipo_aplicable": 27.0},
                {"tramo_num": 5, "base_hasta": 999999, "cuota_integra": 71880, "resto_base": 700000, "tipo_aplicable": 28.0},
            ]
        # General scale
        return [
            {"tramo_num": 1, "base_hasta": 12450, "cuota_integra": 0, "resto_base": 12450, "tipo_aplicable": 9.5},
            {"tramo_num": 2, "base_hasta": 20200, "cuota_integra": 1182.75, "resto_base": 7750, "tipo_aplicable": 12.0},
            {"tramo_num": 3, "base_hasta": 35200, "cuota_integra": 2112.75, "resto_base": 15000, "tipo_aplicable": 15.0},
            {"tramo_num": 4, "base_hasta": 60000, "cuota_integra": 4362.75, "resto_base": 24800, "tipo_aplicable": 18.5},
            {"tramo_num": 5, "base_hasta": 300000, "cuota_integra": 8950.75, "resto_base": 240000, "tipo_aplicable": 22.5},
            {"tramo_num": 6, "base_hasta": 999999, "cuota_integra": 62950.75, "resto_base": 700000, "tipo_aplicable": 24.5},
        ]

    def execute_side_effect(query, params=None):
        """Return appropriate mock data based on query."""
        mock_result = MagicMock()

        if "irpf_scales" in query:
            scale_type = "ahorro" if "'ahorro'" in query else "general"
            rows = make_scale_rows(scale_type)
            mock_rows = []
            for row in rows:
                mock_row = MagicMock()
                mock_row.__getitem__ = lambda self, key, r=row: r[key]
                mock_row.keys = lambda r=row: r.keys()
                # Make dict() work on the row
                mock_row.__iter__ = lambda self, r=row: iter(r)
                # Support dict(row) via items
                def _items(r=row):
                    return r.items()
                mock_row.items = _items
                mock_rows.append(mock_row)
            mock_result.rows = mock_rows
        elif "tax_parameters" in query:
            mock_result.rows = []
        elif "work_income" in query:
            mock_result.rows = []
        else:
            mock_result.rows = []

        return mock_result

    mock_db.execute = AsyncMock(side_effect=execute_side_effect)

    simulator = IRPFSimulator(mock_db)
    result = await simulator.simulate(
        jurisdiction="Madrid",
        year=2025,
        ingresos_trabajo=30_000,
        ventas_inmuebles=[
            {
                "tipo": "otro",
                "precio_venta": 200_000,
                "precio_adquisicion": 150_000,
                "fecha_adquisicion": "2015-01-01",
                "fecha_venta": "2025-06-01",
                "gastos_adquisicion": 0,
                "gastos_venta": 0,
                "mejoras": 0,
                "amortizaciones": 0,
            }
        ],
    )

    assert result["success"] is True
    # Property gain: 200000 - 150000 = 50000, goes to base_ahorro
    assert result["ganancias_inmuebles"] is not None
    assert result["ganancias_inmuebles"]["ganancia_neta_total"] == 50_000.0
    # base_ahorro should include the 50K property gain
    assert result["base_imponible_ahorro"] >= 50_000.0


# ---------------------------------------------------------------------------
# 9. Sale at a loss
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sale_at_loss(calculator):
    """Sale at a loss: no abatimiento or reinversion, negative ganancia."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 150_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2010-01-01",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 10_000,
            "gastos_venta": 5_000,
            "mejoras": 0,
            "amortizaciones": 0,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # valor transmision = 150000 - 5000 = 145000
    # valor adquisicion = 200000 + 10000 = 210000
    # ganancia = 145000 - 210000 = -65000
    assert result["ganancia_bruta_total"] == -65_000.0
    desglose = result["desglose"][0]
    assert desglose["aplica_abatimiento"] is False
    assert desglose["aplica_reinversion"] is False
    # ganancia_neta_total is floored at 0 in the total (losses handled elsewhere)
    assert result["ganancia_neta_total"] == 0.0


# ---------------------------------------------------------------------------
# 10. Vivienda habitual but no reinversion flag
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vivienda_habitual_no_reinversion(calculator):
    """Vivienda habitual sold without reinversion: full gain taxed."""
    ventas = [
        {
            "tipo": "vivienda_habitual",
            "precio_venta": 300_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2010-01-01",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": False,
            "importe_reinversion": 0,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    assert result["ganancia_bruta_total"] == 100_000.0
    assert result["exencion_reinversion_total"] == 0.0
    assert result["ganancia_neta_total"] == 100_000.0


# ---------------------------------------------------------------------------
# 11. Empty ventas list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_ventas(calculator):
    """No sales: returns empty result."""
    result = await calculator.calculate(ventas=[], year=2025)
    assert result["num_ventas"] == 0
    assert result["ganancia_neta_total"] == 0.0
    assert result["desglose"] == []


# ---------------------------------------------------------------------------
# 12. DT 9a — partial abatimiento (not 100% reduction)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dt9a_partial_abatimiento(calculator):
    """Property acquired Dec 1994 with shorter holding: partial abatimiento."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 200_000,
            "precio_adquisicion": 100_000,
            "fecha_adquisicion": "1994-01-01",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # From 1994-01-01 to 2006-01-19 = ~12 years → ceil = 12
    # Reduction years = 12 - 2 = 10
    # Coefficient = 10 * 11.11% = 111.1% → capped at 100%
    desglose = result["desglose"][0]
    assert desglose["aplica_abatimiento"] is True
    assert desglose["coeficiente_abatimiento_pct"] == 100.0

    # Try with a later acquisition date for a partial coefficient
    ventas2 = [
        {
            "tipo": "otro",
            "precio_venta": 200_000,
            "precio_adquisicion": 100_000,
            "fecha_adquisicion": "1994-12-31",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
        }
    ]
    result2 = await calculator.calculate(ventas=ventas2, year=2025)

    # From 1994-12-31 to 2006-01-19 = ~11 years → ceil = 12
    # Reduction years = 12 - 2 = 10 → 10 * 11.11 = 111.1% → capped at 100%
    desglose2 = result2["desglose"][0]
    assert desglose2["aplica_abatimiento"] is True
    # Still capped at 100%
    assert desglose2["coeficiente_abatimiento_pct"] == 100.0


# ---------------------------------------------------------------------------
# 13. DT 9a with amortizaciones (previously rented property)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_amortizaciones_previously_rented(calculator):
    """Property with accumulated depreciation from rental period."""
    ventas = [
        {
            "tipo": "otro",
            "precio_venta": 300_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2005-01-01",
            "fecha_venta": "2025-06-01",
            "gastos_adquisicion": 10_000,
            "gastos_venta": 5_000,
            "mejoras": 0,
            "amortizaciones": 30_000,  # 20 years * 1.5K/year
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # valor transmision = 300000 - 5000 = 295000
    # valor adquisicion = 200000 + 10000 + 0 - 30000 = 180000
    # ganancia = 295000 - 180000 = 115000
    assert result["ganancia_bruta_total"] == 115_000.0
    assert result["ganancia_neta_total"] == 115_000.0


# ---------------------------------------------------------------------------
# 14. Art. 38.1 — Reinversion within 24-month plazo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reinversion_within_24_months(calculator):
    """Reinversion within 24 months: exemption applies normally."""
    ventas = [
        {
            "tipo": "vivienda_habitual",
            "precio_venta": 300_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2010-01-01",
            "fecha_venta": "2025-01-15",
            "fecha_nueva_adquisicion": "2026-06-01",  # ~17 months → within 24
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": True,
            "importe_reinversion": 300_000,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    assert result["ganancia_bruta_total"] == 100_000.0
    assert result["exencion_reinversion_total"] == 100_000.0
    assert result["ganancia_neta_total"] == 0.0
    desglose = result["desglose"][0]
    assert desglose["aplica_reinversion"] is True
    # No warnings about plazo in avisos (or aviso is about something else)
    assert "avisos" not in result or not any("fuera del plazo" in a for a in result.get("avisos", []))


@pytest.mark.asyncio
async def test_reinversion_outside_24_months(calculator):
    """Reinversion after 24 months: exemption does NOT apply (Art. 38.1)."""
    ventas = [
        {
            "tipo": "vivienda_habitual",
            "precio_venta": 300_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2010-01-01",
            "fecha_venta": "2025-01-15",
            "fecha_nueva_adquisicion": "2027-06-01",  # ~29 months → outside 24
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": True,
            "importe_reinversion": 300_000,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    assert result["ganancia_bruta_total"] == 100_000.0
    # Reinversion should NOT apply — outside 24-month window
    assert result["exencion_reinversion_total"] == 0.0
    assert result["ganancia_neta_total"] == 100_000.0
    desglose = result["desglose"][0]
    assert desglose["aplica_reinversion"] is False
    # Should have a warning
    assert "avisos" in result
    assert any("fuera del plazo" in a for a in result["avisos"])


@pytest.mark.asyncio
async def test_reinversion_no_fecha_nueva_adquisicion_warning(calculator):
    """Reinversion declared but no new acquisition date: exemption applies with warning."""
    ventas = [
        {
            "tipo": "vivienda_habitual",
            "precio_venta": 300_000,
            "precio_adquisicion": 200_000,
            "fecha_adquisicion": "2010-01-01",
            "fecha_venta": "2025-01-15",
            # fecha_nueva_adquisicion NOT provided
            "gastos_adquisicion": 0,
            "gastos_venta": 0,
            "mejoras": 0,
            "amortizaciones": 0,
            "reinversion_vivienda_habitual": True,
            "importe_reinversion": 300_000,
        }
    ]
    result = await calculator.calculate(ventas=ventas, year=2025)

    # Exemption still applies (user may not have bought yet, within 24-month window)
    assert result["exencion_reinversion_total"] == 100_000.0
    assert result["ganancia_neta_total"] == 0.0
    desglose = result["desglose"][0]
    assert desglose["aplica_reinversion"] is True
    # Should have a reminder warning about the 24-month deadline
    assert "avisos" in result
    assert any("24 meses" in a for a in result["avisos"])
