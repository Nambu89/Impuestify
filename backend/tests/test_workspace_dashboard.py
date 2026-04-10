"""
Tests for workspace dashboard endpoint.

Verifies GET /{workspace_id}/dashboard returns the expected
response structure with all KPIs, quarterly/monthly breakdowns,
PGC accounts, suppliers, and recent invoices.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rows(dicts):
    """Turn a list of dicts into a result object with .rows that support .get()."""
    result = SimpleNamespace()
    result.rows = dicts
    return result


EMPTY_KPI_ROW = {
    "ingresos_total": 0,
    "gastos_total": 0,
    "iva_repercutido": 0,
    "iva_soportado": 0,
    "retencion_irpf_total": 0,
    "facturas_count": 0,
    "facturas_pendientes": 0,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_response_structure():
    """The dashboard endpoint returns a dict with all expected top-level keys
    and correct sub-structures, even when the workspace has no invoices."""
    from app.routers.workspaces import get_workspace_dashboard

    # --- Mocks ---
    mock_request = MagicMock()

    mock_workspace = SimpleNamespace(
        id="ws-1", user_id="u-1", name="Test", description=None,
        icon="📁", is_default=False, max_files=50, max_size_mb=100,
        created_at=None, updated_at=None, file_count=0,
    )

    mock_service = AsyncMock()
    mock_service.get_workspace.return_value = mock_workspace

    # Every db.execute call returns empty rows except KPIs (needs at least one row)
    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        _make_rows([EMPTY_KPI_ROW]),   # KPIs
        _make_rows([]),                 # por_trimestre
        _make_rows([]),                 # por_mes
        _make_rows([]),                 # por_cuenta_pgc
        _make_rows([]),                 # top_proveedores
        _make_rows([]),                 # facturas_recientes
    ]

    mock_user = SimpleNamespace(user_id="u-1", email="test@example.com")

    # --- Call ---
    result = await get_workspace_dashboard(
        request=mock_request,
        workspace_id="ws-1",
        year=2026,
        current_user=mock_user,
        service=mock_service,
        db=mock_db,
    )

    # --- Assertions: top-level keys ---
    assert "kpis" in result
    assert "por_trimestre" in result
    assert "por_mes" in result
    assert "por_cuenta_pgc" in result
    assert "top_proveedores" in result
    assert "facturas_recientes" in result

    # --- KPIs ---
    kpis = result["kpis"]
    expected_kpi_keys = {
        "ingresos_total", "gastos_total",
        "iva_repercutido", "iva_soportado", "balance_iva",
        "retencion_irpf_total", "resultado_neto",
        "facturas_count", "facturas_pendientes",
    }
    assert set(kpis.keys()) == expected_kpi_keys
    # All should be zero for an empty workspace
    assert kpis["ingresos_total"] == 0.0
    assert kpis["gastos_total"] == 0.0
    assert kpis["balance_iva"] == 0.0
    assert kpis["resultado_neto"] == 0.0
    assert kpis["facturas_count"] == 0
    assert kpis["facturas_pendientes"] == 0

    # --- Quarters: always 4 entries ---
    assert len(result["por_trimestre"]) == 4
    for i, q in enumerate(result["por_trimestre"], start=1):
        assert q["trimestre"] == f"{i}T"
        assert "ingresos" in q
        assert "gastos" in q
        assert "iva_repercutido" in q
        assert "iva_soportado" in q

    # --- Empty lists for workspace with no data ---
    assert result["por_mes"] == []
    assert result["por_cuenta_pgc"] == []
    assert result["top_proveedores"] == []
    assert result["facturas_recientes"] == []


@pytest.mark.asyncio
async def test_dashboard_with_data():
    """The dashboard correctly aggregates sample invoice data."""
    from app.routers.workspaces import get_workspace_dashboard

    mock_request = MagicMock()
    mock_workspace = SimpleNamespace(
        id="ws-2", user_id="u-2", name="Facturas", description=None,
        icon="📁", is_default=False, max_files=50, max_size_mb=100,
        created_at=None, updated_at=None, file_count=5,
    )

    mock_service = AsyncMock()
    mock_service.get_workspace.return_value = mock_workspace

    mock_db = AsyncMock()
    mock_db.execute.side_effect = [
        # KPIs
        _make_rows([{
            "ingresos_total": 10000.50,
            "gastos_total": 3200.00,
            "iva_repercutido": 2100.105,
            "iva_soportado": 672.00,
            "retencion_irpf_total": 1500.00,
            "facturas_count": 8,
            "facturas_pendientes": 2,
        }]),
        # por_trimestre
        _make_rows([
            {"trimestre": 1, "ingresos": 5000.0, "gastos": 1600.0,
             "iva_repercutido": 1050.0, "iva_soportado": 336.0},
            {"trimestre": 2, "ingresos": 5000.50, "gastos": 1600.0,
             "iva_repercutido": 1050.105, "iva_soportado": 336.0},
        ]),
        # por_mes
        _make_rows([
            {"mes": "2026-01", "ingresos": 2500.0, "gastos": 800.0},
            {"mes": "2026-02", "ingresos": 2500.0, "gastos": 800.0},
        ]),
        # por_cuenta_pgc
        _make_rows([
            {"cuenta": "700", "nombre": "Ventas", "total": 10000.50, "tipo_cuenta": "ingreso"},
            {"cuenta": "600", "nombre": "Compras", "total": 3200.00, "tipo_cuenta": "gasto"},
        ]),
        # top_proveedores
        _make_rows([
            {"nombre": "Vodafone", "nif": "A12345678", "total": 1800.0, "facturas": 3},
        ]),
        # facturas_recientes
        _make_rows([
            {
                "id": "inv-1", "fecha_factura": "2026-02-15",
                "emisor_nombre": "Vodafone", "concepto": "Telefonia",
                "total": 60.50, "tipo": "recibida",
                "cuenta_pgc": "629", "clasificacion_confianza": "alta",
            },
        ]),
    ]

    mock_user = SimpleNamespace(user_id="u-2", email="test@example.com")

    result = await get_workspace_dashboard(
        request=mock_request,
        workspace_id="ws-2",
        year=2026,
        current_user=mock_user,
        service=mock_service,
        db=mock_db,
    )

    # KPIs
    assert result["kpis"]["ingresos_total"] == 10000.50
    assert result["kpis"]["gastos_total"] == 3200.00
    assert result["kpis"]["balance_iva"] == round(2100.105 - 672.00, 2)
    assert result["kpis"]["resultado_neto"] == round(10000.50 - 3200.00, 2)
    assert result["kpis"]["facturas_count"] == 8
    assert result["kpis"]["facturas_pendientes"] == 2

    # Quarters: Q3 and Q4 should be zero-filled
    assert result["por_trimestre"][0]["trimestre"] == "1T"
    assert result["por_trimestre"][0]["ingresos"] == 5000.0
    assert result["por_trimestre"][2]["trimestre"] == "3T"
    assert result["por_trimestre"][2]["ingresos"] == 0.0

    # Months
    assert len(result["por_mes"]) == 2
    assert result["por_mes"][0]["mes"] == "2026-01"

    # PGC
    assert len(result["por_cuenta_pgc"]) == 2
    assert result["por_cuenta_pgc"][0]["cuenta"] == "700"

    # Suppliers
    assert len(result["top_proveedores"]) == 1
    assert result["top_proveedores"][0]["nombre"] == "Vodafone"

    # Recent invoices
    assert len(result["facturas_recientes"]) == 1
    assert result["facturas_recientes"][0]["id"] == "inv-1"


@pytest.mark.asyncio
async def test_dashboard_workspace_not_found():
    """Returns 404 when workspace does not exist or belongs to another user."""
    from app.routers.workspaces import get_workspace_dashboard
    from fastapi import HTTPException

    mock_service = AsyncMock()
    mock_service.get_workspace.return_value = None

    mock_user = SimpleNamespace(user_id="u-999", email="nobody@example.com")

    with pytest.raises(HTTPException) as exc_info:
        await get_workspace_dashboard(
            request=MagicMock(),
            workspace_id="ws-nonexistent",
            year=2026,
            current_user=mock_user,
            service=mock_service,
            db=AsyncMock(),
        )

    assert exc_info.value.status_code == 404
