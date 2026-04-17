"""Tests del endpoint IS prefill desde workspace."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class MockRow(dict):
    """Dict-like row with attribute access."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


class MockResult:
    """Mock Turso query result."""
    def __init__(self, rows=None, rowcount=0):
        self.rows = rows or []
        self.rowcount = rowcount


@pytest.fixture(autouse=True)
def mock_deps():
    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "test-key",
        "TURSO_DATABASE_URL": "libsql://test.turso.io",
        "TURSO_AUTH_TOKEN": "test-token",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only-32chars!",
    }):
        yield


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def mock_workspace_service():
    service = AsyncMock()
    return service


@pytest.fixture
def client(mock_deps, mock_db, mock_workspace_service):
    from fastapi.testclient import TestClient
    from fastapi import FastAPI, Depends
    from app.routers.workspaces import router
    from app.auth.jwt_handler import TokenData
    from app.database.turso_client import TursoClient

    app = FastAPI()

    # Override auth dependency
    async def mock_current_user():
        return TokenData(user_id="user-123", email="test@test.com")

    async def mock_get_db():
        return mock_db

    async def mock_get_ws_service():
        return mock_workspace_service

    app.include_router(router)

    # Override dependencies
    from app.auth.jwt_handler import get_current_user
    from app.routers.workspaces import get_db, get_workspace_service
    app.dependency_overrides[get_current_user] = mock_current_user
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_workspace_service] = mock_get_ws_service

    return TestClient(app)


class TestISPrefillEndpoint:
    """GET /api/workspaces/{workspace_id}/is-prefill"""

    def test_prefill_basic(self, client, mock_workspace_service, mock_db):
        """Returns aggregated workspace data for IS prefill."""
        mock_workspace_service.get_workspace.return_value = {
            "id": "ws-1", "name": "Mi Empresa SL", "user_id": "user-123"
        }

        # Mock the aggregate query
        mock_db.execute.return_value = MockResult(rows=[MockRow({
            "ingresos": 200_000,
            "gastos": 120_000,
            "num_facturas": 45,
            "fecha_min": "2025-01-15",
            "fecha_max": "2025-12-20",
        })])

        resp = client.get("/api/workspaces/ws-1/is-prefill?ejercicio=2025")
        assert resp.status_code == 200
        data = resp.json()
        assert data["workspace_name"] == "Mi Empresa SL"
        assert data["ejercicio"] == 2025
        assert data["ingresos"] == 200_000
        assert data["gastos"] == 120_000
        assert data["resultado"] == 80_000
        assert data["num_facturas"] == 45

    def test_prefill_workspace_not_found(self, client, mock_workspace_service):
        """Returns 404 if workspace not found or not owned."""
        mock_workspace_service.get_workspace.return_value = None

        resp = client.get("/api/workspaces/ws-bad/is-prefill?ejercicio=2025")
        assert resp.status_code == 404

    def test_prefill_empty_workspace(self, client, mock_workspace_service, mock_db):
        """Returns zeros for workspace with no invoices."""
        mock_workspace_service.get_workspace.return_value = {
            "id": "ws-1", "name": "Empresa Vacía", "user_id": "user-123"
        }

        mock_db.execute.return_value = MockResult(rows=[MockRow({
            "ingresos": None,
            "gastos": None,
            "num_facturas": 0,
            "fecha_min": None,
            "fecha_max": None,
        })])

        resp = client.get("/api/workspaces/ws-1/is-prefill")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ingresos"] == 0
        assert data["gastos"] == 0
        assert data["resultado"] == 0
        assert data["num_facturas"] == 0

    def test_prefill_default_ejercicio(self, client, mock_workspace_service, mock_db):
        """Default ejercicio is 2025."""
        mock_workspace_service.get_workspace.return_value = {
            "id": "ws-1", "name": "Test", "user_id": "user-123"
        }
        mock_db.execute.return_value = MockResult(rows=[MockRow({
            "ingresos": 0, "gastos": 0, "num_facturas": 0,
            "fecha_min": None, "fecha_max": None,
        })])

        resp = client.get("/api/workspaces/ws-1/is-prefill")
        assert resp.status_code == 200
        assert resp.json()["ejercicio"] == 2025

    def test_prefill_cuentas_desglose(self, client, mock_workspace_service, mock_db):
        """Returns PGC account breakdown if available."""
        mock_workspace_service.get_workspace.return_value = {
            "id": "ws-1", "name": "Test SL", "user_id": "user-123"
        }

        # First call: aggregate query
        # Second call: cuentas desglose query
        mock_db.execute.side_effect = [
            MockResult(rows=[MockRow({
                "ingresos": 100_000, "gastos": 60_000, "num_facturas": 20,
                "fecha_min": "2025-01-01", "fecha_max": "2025-06-30",
            })]),
            MockResult(rows=[
                MockRow({"cuenta_pgc": "700", "nombre_cuenta": "Ventas de mercaderías", "total": 100_000, "count": 15}),
                MockRow({"cuenta_pgc": "600", "nombre_cuenta": "Compras de mercaderías", "total": 60_000, "count": 5}),
            ]),
        ]

        resp = client.get("/api/workspaces/ws-1/is-prefill?ejercicio=2025")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["cuentas_desglose"]) == 2
        assert data["cuentas_desglose"][0]["cuenta_pgc"] == "700"

    def test_prefill_requires_auth(self):
        """Endpoint requires authentication (get_current_user dependency)."""
        # This is implicitly tested since the fixture overrides get_current_user.
        # Without the override, the endpoint would return 401.
        # We verify the endpoint signature requires auth in the router definition.
        from app.routers.workspaces import get_workspace_is_prefill
        import inspect
        sig = inspect.signature(get_workspace_is_prefill)
        param_names = list(sig.parameters.keys())
        assert "current_user" in param_names
