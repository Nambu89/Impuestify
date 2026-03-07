"""Tests for IRPFProjector -- annual IRPF projection from quarterly data."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from typing import Any, Dict, List
from app.utils.calculators.irpf_projector import IRPFProjector


# -----------------------------------------------------------------------
# Mock infrastructure (shared with test_irpf_simulator.py patterns)
# -----------------------------------------------------------------------

@dataclass
class MockRow:
    data: Dict[str, Any]
    def __getitem__(self, key): return self.data[key]
    def get(self, key, default=None): return self.data.get(key, default)
    def keys(self): return self.data.keys()
    def values(self): return self.data.values()
    def items(self): return self.data.items()
    def __iter__(self): return iter(self.data)
    def __len__(self): return len(self.data)


@dataclass
class MockResult:
    rows: List[MockRow]


# Minimal IRPF scales for Madrid (enough for simulator to work)
ESTATAL_SCALE = [
    {"tramo_num": 1, "base_hasta": 12450, "cuota_integra": 0, "resto_base": 12450, "tipo_aplicable": 9.5},
    {"tramo_num": 2, "base_hasta": 20200, "cuota_integra": 1182.75, "resto_base": 7750, "tipo_aplicable": 12},
    {"tramo_num": 3, "base_hasta": 35200, "cuota_integra": 2112.75, "resto_base": 15000, "tipo_aplicable": 15},
    {"tramo_num": 4, "base_hasta": 60000, "cuota_integra": 4362.75, "resto_base": 24800, "tipo_aplicable": 18.5},
    {"tramo_num": 5, "base_hasta": 300000, "cuota_integra": 8952.75, "resto_base": 240000, "tipo_aplicable": 22.5},
]

MADRID_SCALE = [
    {"tramo_num": 1, "base_hasta": 12961.49, "cuota_integra": 0, "resto_base": 12961.49, "tipo_aplicable": 8.5},
    {"tramo_num": 2, "base_hasta": 18612.43, "cuota_integra": 1101.73, "resto_base": 5650.94, "tipo_aplicable": 10.7},
    {"tramo_num": 3, "base_hasta": 35200.42, "cuota_integra": 1706.38, "resto_base": 16588.00, "tipo_aplicable": 12.8},
    {"tramo_num": 4, "base_hasta": 55000.42, "cuota_integra": 3829.64, "resto_base": 19800.00, "tipo_aplicable": 17.4},
    {"tramo_num": 5, "base_hasta": 999999, "cuota_integra": 7274.84, "resto_base": 944998.58, "tipo_aplicable": 20.5},
]

MOCK_MPYF = {
    "contribuyente": 5550, "contribuyente_65": 6700, "contribuyente_75": 8100,
    "descendiente_1": 2400, "descendiente_2": 2700, "descendiente_3": 4000,
    "descendiente_4_plus": 4500, "descendiente_menor_3": 2800,
    "ascendiente_65": 1150, "ascendiente_75": 2550,
    "discapacidad_33_65": 3000, "discapacidad_65_plus": 9000, "gastos_asistencia": 3000,
}

MOCK_TRABAJO = {
    "otros_gastos": 2000, "reduccion_max": 6498, "reduccion_rend_min": 14852,
    "reduccion_rend_max": 19747.5, "cuotas_colegio_max": 500,
    "defensa_juridica_max": 300, "ss_empleado_pct": 6.35,
}

MOCK_INMUEBLES = {"reduccion_alquiler_vivienda": 60, "amortizacion_pct": 3}

AHORRO_SCALE = [
    {"tramo_num": 1, "base_hasta": 6000, "cuota_integra": 0, "resto_base": 6000, "tipo_aplicable": 9.5},
    {"tramo_num": 2, "base_hasta": 50000, "cuota_integra": 570, "resto_base": 44000, "tipo_aplicable": 10.5},
]


def build_projector_db(declarations_130=None, declarations_303=None,
                       declarations_420=None):
    """Build mock DB that serves both declarations AND irpf_scales/tax_parameters."""
    declarations_130 = declarations_130 or []
    declarations_303 = declarations_303 or []
    declarations_420 = declarations_420 or []

    async def mock_execute(sql, params=None):
        sql_lower = sql.strip().lower()
        params = params or []

        # --- Declaration queries ---
        if "from quarterly_declarations" in sql_lower and "select" in sql_lower:
            decl_type = params[1] if len(params) > 1 else ""
            if decl_type == "130":
                rows = [MockRow(d) for d in declarations_130]
            elif decl_type == "303":
                rows = [MockRow(d) for d in declarations_303]
            elif decl_type == "420":
                rows = [MockRow(d) for d in declarations_420]
            else:
                rows = []
            return MockResult(rows=rows)

        # --- Annual projections (for save) ---
        if "annual_projections" in sql_lower:
            return MockResult(rows=[])

        # --- Tax parameter queries (for IRPFSimulator) ---
        if "tax_parameters" in sql_lower and "select" in sql_lower:
            category = params[0] if len(params) > 0 else ""
            data = {}
            if category == "mpyf":
                data = MOCK_MPYF
            elif category == "trabajo":
                data = MOCK_TRABAJO
            elif category == "inmuebles":
                data = MOCK_INMUEBLES
            rows = [MockRow({"param_key": k, "value": v}) for k, v in data.items()]
            return MockResult(rows=rows)

        # --- IRPF scales ahorro ---
        if "irpf_scales" in sql_lower and "ahorro" in sql_lower:
            return MockResult(rows=[MockRow(r) for r in AHORRO_SCALE])

        # --- IRPF scales general ---
        if "irpf_scales" in sql_lower and "select" in sql_lower:
            jurisdiction = params[0] if params else "Estatal"
            if jurisdiction == "Comunidad de Madrid":
                return MockResult(rows=[MockRow(r) for r in MADRID_SCALE])
            return MockResult(rows=[MockRow(r) for r in ESTATAL_SCALE])

        # Default: empty
        return MockResult(rows=[])

    db = AsyncMock()
    db.execute = mock_execute
    return db


def _make_130_row(quarter, ingresos_acum, gastos_acum, retenciones_acum=0,
                  tax_due=500, territory="Comun"):
    """Mock Modelo 130 quarterly_declarations row."""
    return {
        "quarter": quarter,
        "territory": territory,
        "tax_due": tax_due,
        "total_income": ingresos_acum,
        "total_expenses": gastos_acum,
        "form_data": json.dumps({
            "ingresos_acumulados": ingresos_acum,
            "gastos_acumulados": gastos_acum,
            "retenciones_acumuladas": retenciones_acum,
            "territory": territory,
        }),
        "calculated_result": json.dumps({"resultado": tax_due}),
    }


def _make_303_row(quarter, total_devengado=2100, total_deducible=700):
    """Mock Modelo 303 quarterly_declarations row."""
    return {
        "quarter": quarter,
        "territory": "comun",
        "tax_due": total_devengado - total_deducible,
        "total_income": 10000,
        "total_expenses": 0,
        "form_data": json.dumps({"base_21": 10000}),
        "calculated_result": json.dumps({
            "total_devengado": total_devengado,
            "total_deducible": total_deducible,
        }),
    }


# ===========================================================================
# Unit tests: aggregation
# ===========================================================================

def test_aggregate_activity_comun_accumulated():
    """Comun territory uses accumulated figures from last quarter."""
    projector = IRPFProjector(None)
    data = [
        _make_130_row(1, 10000, 3000),
        _make_130_row(2, 22000, 7000),
    ]
    result = projector._aggregate_activity_income(data)
    assert result["ingresos"] == 22000
    assert result["gastos"] == 7000
    assert result["num_quarters"] == 2


def test_aggregate_activity_araba_per_quarter():
    """Araba uses per-quarter figures that must be summed."""
    projector = IRPFProjector(None)
    data = [
        {
            "quarter": 1, "territory": "Araba", "tax_due": 250,
            "total_income": 8000, "total_expenses": 3000,
            "form_data": {"ingresos_trimestre": 8000, "gastos_trimestre": 3000},
            "calculated_result": {},
        },
        {
            "quarter": 2, "territory": "Araba", "tax_due": 300,
            "total_income": 10000, "total_expenses": 4000,
            "form_data": {"ingresos_trimestre": 10000, "gastos_trimestre": 4000},
            "calculated_result": {},
        },
    ]
    result = projector._aggregate_activity_income(data)
    assert result["ingresos"] == 18000
    assert result["gastos"] == 7000


def test_aggregate_activity_empty():
    """No data returns zeros."""
    projector = IRPFProjector(None)
    result = projector._aggregate_activity_income([])
    assert result["ingresos"] == 0
    assert result["num_quarters"] == 0


# ===========================================================================
# Unit tests: annualization
# ===========================================================================

def test_annualize_1_quarter():
    """1 quarter: factor x4."""
    projector = IRPFProjector(None)
    activity = {"ingresos": 10000, "gastos": 3000, "rendimiento_neto": 7000,
                "cuota_autonomo_anual": 0, "num_quarters": 1}
    result = projector._annualize(activity, 1)
    assert result["ingresos"] == 40000
    assert result["gastos"] == 12000
    assert result["factor"] == 4.0


def test_annualize_2_quarters():
    """2 quarters: factor x2."""
    projector = IRPFProjector(None)
    activity = {"ingresos": 20000, "gastos": 6000, "rendimiento_neto": 14000,
                "cuota_autonomo_anual": 0, "num_quarters": 2}
    result = projector._annualize(activity, 2)
    assert result["ingresos"] == 40000
    assert result["factor"] == 2.0


def test_annualize_3_quarters():
    """3 quarters: factor x4/3."""
    projector = IRPFProjector(None)
    activity = {"ingresos": 30000, "gastos": 9000, "rendimiento_neto": 21000,
                "cuota_autonomo_anual": 0, "num_quarters": 3}
    result = projector._annualize(activity, 3)
    assert result["ingresos"] == 40000
    assert result["factor"] == round(4 / 3, 4)


def test_annualize_4_quarters():
    """4 quarters: factor x1."""
    projector = IRPFProjector(None)
    activity = {"ingresos": 40000, "gastos": 12000, "rendimiento_neto": 28000,
                "cuota_autonomo_anual": 0, "num_quarters": 4}
    result = projector._annualize(activity, 4)
    assert result["ingresos"] == 40000
    assert result["factor"] == 1.0


def test_annualize_0_quarters():
    """0 quarters: all zeros."""
    projector = IRPFProjector(None)
    activity = {"ingresos": 0, "gastos": 0, "rendimiento_neto": 0,
                "cuota_autonomo_anual": 0, "num_quarters": 0}
    result = projector._annualize(activity, 0)
    assert result["ingresos"] == 0
    assert result["factor"] == 0


# ===========================================================================
# Unit tests: IVA aggregation
# ===========================================================================

def test_aggregate_iva_303():
    """IVA aggregation from Modelo 303."""
    projector = IRPFProjector(None)
    data_303 = [
        _make_303_row(1, 2100, 700),
        _make_303_row(2, 1500, 500),
    ]
    result = projector._aggregate_iva(data_303, [])
    assert result["total_iva_devengado"] == 3600
    assert result["total_iva_deducible"] == 1200
    assert result["saldo_iva"] == 2400


def test_aggregate_iva_empty():
    """No IVA data."""
    projector = IRPFProjector(None)
    result = projector._aggregate_iva([], [])
    assert result["total_iva_devengado"] == 0


# ===========================================================================
# Integration tests: full projection (mock DB + real IRPFSimulator)
# ===========================================================================

@pytest.mark.asyncio
async def test_project_2_quarters_comun():
    """Full projection from 2 quarters of Modelo 130 data (Comun)."""
    decl_130 = [
        _make_130_row(1, 15000, 5000, retenciones_acum=1000, tax_due=1800),
        _make_130_row(2, 30000, 10000, retenciones_acum=2000, tax_due=3600),
    ]
    decl_303 = [_make_303_row(1), _make_303_row(2)]

    db = build_projector_db(declarations_130=decl_130, declarations_303=decl_303)
    projector = IRPFProjector(db)

    result = await projector.project(
        user_id="test-user", year=2025,
        jurisdiction="Comunidad de Madrid",
        save_projection=False,
    )

    assert result["confidence"] == "medium"
    assert result["quarterly_data"]["num_quarters_activity"] == 2
    assert result["quarterly_data"]["total_pagos_130"] == 5400

    # Annualized from 2Q: ingresos=30000*2=60000, gastos=10000*2=20000
    assert result["annualized"]["ingresos"] == 60000
    assert result["annualized"]["gastos"] == 20000
    assert result["annualized"]["factor"] == 2.0

    proj = result["projection"]
    assert proj["success"] is True
    assert proj["cuota_total"] > 0


@pytest.mark.asyncio
async def test_project_no_data():
    """No quarterly data -> no_data confidence, zero projection."""
    db = build_projector_db()
    projector = IRPFProjector(db)

    result = await projector.project(
        user_id="test-user", year=2025,
        jurisdiction="Comunidad de Madrid",
        save_projection=False,
    )

    assert result["confidence"] == "no_data"
    assert result["annualized"]["ingresos"] == 0
    # Still runs simulator (with 0 income)
    assert result["projection"]["success"] is True


@pytest.mark.asyncio
async def test_project_4_quarters_high_confidence():
    """4 quarters -> high confidence, no annualization factor."""
    decl_130 = [
        _make_130_row(1, 10000, 3000, tax_due=1200),
        _make_130_row(2, 20000, 6000, tax_due=2400),
        _make_130_row(3, 30000, 9000, tax_due=3600),
        _make_130_row(4, 40000, 12000, retenciones_acum=3000, tax_due=4400),
    ]

    db = build_projector_db(declarations_130=decl_130)
    projector = IRPFProjector(db)

    result = await projector.project(
        user_id="test-user", year=2025,
        jurisdiction="Comunidad de Madrid",
        save_projection=False,
    )

    assert result["confidence"] == "high"
    assert result["annualized"]["factor"] == 1.0
    assert result["annualized"]["ingresos"] == 40000
    assert result["annualized"]["gastos"] == 12000


@pytest.mark.asyncio
async def test_project_with_work_income():
    """Projection includes work income passed manually."""
    decl_130 = [_make_130_row(1, 10000, 3000, tax_due=1200)]

    db = build_projector_db(declarations_130=decl_130)
    projector = IRPFProjector(db)

    result = await projector.project(
        user_id="test-user", year=2025,
        jurisdiction="Comunidad de Madrid",
        ingresos_trabajo=30000,
        save_projection=False,
    )

    proj = result["projection"]
    assert proj["trabajo"]["ingresos_brutos"] == 30000
    assert proj["actividad"] is not None


@pytest.mark.asyncio
async def test_iva_summary_in_projection():
    """IVA summary is included in the projection result."""
    decl_303 = [_make_303_row(1, 2100, 700)]

    db = build_projector_db(declarations_303=decl_303)
    projector = IRPFProjector(db)

    result = await projector.project(
        user_id="test-user", year=2025,
        jurisdiction="Comunidad de Madrid",
        save_projection=False,
    )

    assert result["iva_summary"]["total_iva_devengado"] == 2100
    assert result["iva_summary"]["total_iva_deducible"] == 700
    assert result["iva_summary"]["num_quarters_303"] == 1


@pytest.mark.asyncio
async def test_project_saves_to_db():
    """When save_projection=True, the projection is persisted."""
    decl_130 = [_make_130_row(1, 10000, 3000, tax_due=1200)]

    db = build_projector_db(declarations_130=decl_130)
    projector = IRPFProjector(db)

    # Track INSERT calls
    original_execute = db.execute
    insert_calls = []

    async def tracking_execute(sql, params=None):
        if "insert into annual_projections" in sql.lower():
            insert_calls.append((sql, params))
        return await original_execute(sql, params)

    db.execute = tracking_execute

    result = await projector.project(
        user_id="test-user", year=2025,
        jurisdiction="Comunidad de Madrid",
        save_projection=True,
    )

    assert len(insert_calls) == 1
    assert result["confidence"] == "low"  # 1 quarter
