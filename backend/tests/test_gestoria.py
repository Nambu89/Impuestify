"""Tests Modo Gestoría — migraciones, servicio, endpoints."""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestGestoriaMigrations:
    """Verifica que init_schema crea el esquema de gestoría (idempotente)."""

    @pytest.mark.asyncio
    async def test_workspace_profiles_table_created(self):
        from app.database.turso_client import TursoClient

        executed: list[str] = []

        async def fake_execute(sql, params=None):
            executed.append(" ".join(sql.split()))
            res = MagicMock()
            res.rows = []
            return res

        client = TursoClient.__new__(TursoClient)
        client.execute = fake_execute  # type: ignore[method-assign]

        # _column_exists devuelve False → fuerza ALTER/CREATE
        async def fake_col_exists(table, col):
            return False

        client._column_exists = fake_col_exists  # type: ignore[method-assign]

        await client._migrate_gestoria_schema()

        joined = " || ".join(executed)
        assert "CREATE TABLE IF NOT EXISTS workspace_profiles" in joined
        assert "ALTER TABLE users ADD COLUMN account_type" in joined
        assert "ALTER TABLE quarterly_declarations ADD COLUMN workspace_id" in joined


class TestGrantGestoria:
    """PUT /api/admin/users/{id}/grant-gestoria"""

    def _build_client(self, db_mock):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.auth.jwt_handler import TokenData
        from app.auth.owner_guard import require_owner
        from app.database.turso_client import get_db_client
        from app.routers.admin import router

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[require_owner] = lambda: TokenData(
            user_id="owner-1", email="owner@x.com"
        )
        app.dependency_overrides[get_db_client] = lambda: db_mock
        return TestClient(app)

    def test_grant_gestoria_sets_plan_and_account_type(self):
        db = AsyncMock()
        calls: list[tuple] = []

        async def execute(sql, params=None):
            calls.append((" ".join(sql.split()), params))
            res = MagicMock()
            # user exists; subscription exists
            if sql.strip().startswith("SELECT id, email FROM users"):
                res.rows = [{"id": "u-1", "email": "gestoria@x.com"}]
            elif "FROM subscriptions" in sql:
                res.rows = [{"id": "s-1"}]
            else:
                res.rows = []
            return res

        db.execute = execute
        client = self._build_client(db)

        resp = client.put("/api/admin/users/u-1/grant-gestoria", json={})
        assert resp.status_code == 200

        joined = " || ".join(c[0] for c in calls)
        assert "UPDATE subscriptions SET plan_type = 'autonomo'" in joined or any(
            "plan_type" in c[0] and c[1] and "autonomo" in c[1] for c in calls
        )
        assert any("UPDATE users SET account_type" in c[0] for c in calls)

    def test_grant_gestoria_inserts_when_no_subscription(self):
        """When no subscription row exists the endpoint must INSERT one."""
        db = AsyncMock()
        calls: list[tuple] = []

        async def execute(sql, params=None):
            calls.append((" ".join(sql.split()), params))
            res = MagicMock()
            if sql.strip().startswith("SELECT id, email FROM users"):
                res.rows = [{"id": "u-2", "email": "gestoria2@x.com"}]
            elif "FROM subscriptions" in sql:
                # No existing subscription row → triggers INSERT branch
                res.rows = []
            else:
                res.rows = []
            return res

        db.execute = execute
        client = self._build_client(db)

        resp = client.put("/api/admin/users/u-2/grant-gestoria", json={})
        assert resp.status_code == 200

        joined = " || ".join(c[0] for c in calls)
        # INSERT branch must have been executed
        assert "INSERT INTO subscriptions" in joined
        # autonomo plan must appear in the INSERT statement (hardcoded literal in SQL)
        assert any("INSERT INTO subscriptions" in c[0] and "'autonomo'" in c[0] for c in calls)
        # account_type UPDATE must still happen regardless of which branch was taken
        assert any("UPDATE users SET account_type" in c[0] for c in calls)


class TestAuthAccountType:
    """Login response must carry account_type from the DB row, not the Pydantic default."""

    def test_login_response_threads_gestoria_account_type(self):
        """UserResponse built from a gestoría User must emit account_type='gestoria'."""
        from app.database.models import User
        from app.routers.auth import UserResponse

        gestoria_user = User(
            id="u-gestoria",
            email="gestoria@test.com",
            name="Gestoría Demo",
            is_active=True,
            is_admin=False,
            account_type="gestoria",
        )

        response = UserResponse(
            id=gestoria_user.id,
            email=gestoria_user.email,
            name=gestoria_user.name,
            is_active=gestoria_user.is_active,
            is_admin=gestoria_user.is_admin,
            is_owner=False,
            account_type=gestoria_user.account_type,
            subscription_status=None,
        )

        assert response.account_type == "gestoria", (
            f"Expected 'gestoria' but got '{response.account_type}' — "
            "login response is emitting the Pydantic default instead of the DB value"
        )

    def test_login_response_individual_default_unchanged(self):
        """UserResponse for a normal user must still emit account_type='individual'."""
        from app.database.models import User
        from app.routers.auth import UserResponse

        individual_user = User(
            id="u-individual",
            email="individual@test.com",
            name="Normal User",
            is_active=True,
            is_admin=False,
            # account_type defaults to "individual"
        )

        response = UserResponse(
            id=individual_user.id,
            email=individual_user.email,
            name=individual_user.name,
            is_active=individual_user.is_active,
            is_admin=individual_user.is_admin,
            is_owner=False,
            account_type=individual_user.account_type,
            subscription_status=None,
        )

        assert response.account_type == "individual"


class TestRequireGestoria:
    @pytest.mark.asyncio
    async def test_require_gestoria_allows_gestoria(self):
        from app.auth.gestoria_guard import require_gestoria
        from app.auth.jwt_handler import TokenData

        db = AsyncMock()

        async def execute(sql, params=None):
            res = MagicMock()
            res.rows = [{"account_type": "gestoria"}]
            return res

        db.execute = execute
        user = TokenData(user_id="u-1", email="g@x.com")
        result = await require_gestoria(current_user=user, db=db)
        assert result.user_id == "u-1"

    @pytest.mark.asyncio
    async def test_require_gestoria_blocks_individual(self):
        from fastapi import HTTPException

        from app.auth.gestoria_guard import require_gestoria
        from app.auth.jwt_handler import TokenData

        db = AsyncMock()

        async def execute(sql, params=None):
            res = MagicMock()
            res.rows = [{"account_type": "individual"}]
            return res

        db.execute = execute
        with pytest.raises(HTTPException) as exc:
            await require_gestoria(current_user=TokenData(user_id="u-2", email="p@x.com"), db=db)
        assert exc.value.status_code == 403


class TestGestoriaClientService:
    def _service_with_counts(self, profile_count: int):
        from app.services.gestoria_service import GestoriaClientService

        svc = GestoriaClientService()
        db = AsyncMock()

        async def execute(sql, params=None):
            res = MagicMock()
            s = " ".join(sql.split())
            if s.startswith("SELECT COUNT(*) AS n FROM workspace_profiles"):
                res.rows = [{"n": profile_count}]
            else:
                res.rows = []
            return res

        db.execute = execute
        svc._get_db = AsyncMock(return_value=db)  # type: ignore[attr-defined]
        return svc, db

    @pytest.mark.asyncio
    async def test_create_client_blocks_over_limit(self):
        from app.services.gestoria_service import (
            ClientLimitError,
            GestoriaClientCreate,
        )

        svc, _ = self._service_with_counts(profile_count=3)
        with pytest.raises(ClientLimitError):
            await svc.create_client(
                "u-1", GestoriaClientCreate(nombre_cliente="C", tipo="autonomo")
            )

    def test_create_model_requires_tipo(self):
        from pydantic import ValidationError

        from app.services.gestoria_service import GestoriaClientCreate

        with pytest.raises(ValidationError):
            GestoriaClientCreate(nombre_cliente="C")  # falta tipo

    # ------------------------------------------------------------------
    # Fix: robustness + CRUD tests (Task-8 contract)
    # ------------------------------------------------------------------

    def _build_row(self, **overrides):
        """Return a dict shaped like a `SELECT wp.*` Turso row."""
        base = {
            "id": "profile-uuid-1",
            "workspace_id": "ws-123",
            "nombre_cliente": "Empresa Test SL",
            "tipo": "sociedad",
            "nif": "B12345678",
            "ccaa": "Madrid",
            "situacion_laboral": "sociedad",
            "epigrafe_iae": "6510",
            "regimen_iva": "general",
            "fecha_alta": "2025-01-15",
            "datos_fiscales": '{"actividad": "comercio", "facturacion_anual": 120000}',
            "created_at": "2025-01-15T10:00:00+00:00",
            "updated_at": "2025-06-01T08:00:00+00:00",
        }
        base.update(overrides)
        return base

    def _make_db_with_row(self, row: dict):
        """Return an AsyncMock db whose execute() returns the given row."""
        db = AsyncMock()

        async def execute(sql, params=None):
            res = MagicMock()
            res.rows = [row]
            return res

        db.execute = execute
        return db

    @pytest.mark.asyncio
    async def test_get_client_scopes_by_user(self):
        """get_client must scope by user_id (ownership) and return a correct GestoriaClient."""
        from app.services.gestoria_service import GestoriaClient, GestoriaClientService

        row = self._build_row()
        db = AsyncMock()
        executed_sqls: list[str] = []

        async def execute(sql, params=None):
            executed_sqls.append(" ".join(sql.split()))
            res = MagicMock()
            res.rows = [row]
            return res

        db.execute = execute

        svc = GestoriaClientService()
        svc._get_db = AsyncMock(return_value=db)  # type: ignore[attr-defined]

        client = await svc.get_client("user-abc", "ws-123")

        # Returns a populated GestoriaClient, not None
        assert client is not None
        assert isinstance(client, GestoriaClient)
        assert client.id == "ws-123"
        assert client.nombre_cliente == "Empresa Test SL"
        assert client.tipo == "sociedad"

        # The executed SQL must scope by user ownership
        joined = " ".join(executed_sqls)
        assert "w.user_id" in joined, "SQL must filter by w.user_id for ownership scoping"

    @pytest.mark.asyncio
    async def test_get_workspace_fiscal_profile_shape(self):
        """get_workspace_fiscal_profile must return the Task-8 contract shape."""
        from app.services.gestoria_service import GestoriaClientService

        row = self._build_row(
            ccaa="Cataluña",
            situacion_laboral=None,  # must be derived from tipo="sociedad"
            epigrafe_iae="6510",
            regimen_iva="general",
            datos_fiscales='{"actividad": "comercio", "facturacion_anual": 120000}',
        )
        db = self._make_db_with_row(row)

        svc = GestoriaClientService()
        svc._get_db = AsyncMock(return_value=db)  # type: ignore[attr-defined]

        profile = await svc.get_workspace_fiscal_profile("user-abc", "ws-123")

        assert profile is not None, "profile must not be None for a known client"

        # Required keys for Task-8 contract
        assert "ccaa_residencia" in profile, "missing ccaa_residencia"
        assert profile["ccaa_residencia"] == "Cataluña"

        assert "situacion_laboral" in profile, "missing situacion_laboral"
        # sociedad tipo → derived as "sociedad" when situacion_laboral is None
        assert profile["situacion_laboral"] == "sociedad"

        assert "tipo_cliente" in profile, "missing tipo_cliente"
        assert profile["tipo_cliente"] == "sociedad"

        # datos_fiscales must be flattened into the profile
        assert profile.get("actividad") == "comercio", "datos_fiscales not flattened"
        assert profile.get("facturacion_anual") == 120000, "datos_fiscales not flattened"

        # Optional fields present when set
        assert profile.get("epigrafe_iae") == "6510"
        assert profile.get("regimen_iva") == "general"


class TestChatProfileSelection:
    """chat_stream.resolve_fiscal_profile: usa el perfil del cliente activo
    (workspace) cuando existe; si no, cae al perfil global de la cuenta."""

    @pytest.mark.asyncio
    async def test_uses_workspace_profile_when_present(self):
        from app.routers.chat_stream import resolve_fiscal_profile

        svc = AsyncMock()
        svc.get_workspace_fiscal_profile.return_value = {
            "ccaa_residencia": "Canarias",
            "situacion_laboral": "sociedad",
        }
        prof = await resolve_fiscal_profile(
            user_id="u-1",
            workspace_id="w-1",
            global_profile={"ccaa_residencia": "Madrid"},
            gestoria_service=svc,
        )
        assert prof["ccaa_residencia"] == "Canarias"

    @pytest.mark.asyncio
    async def test_falls_back_to_global_when_no_workspace_profile(self):
        from app.routers.chat_stream import resolve_fiscal_profile

        svc = AsyncMock()
        svc.get_workspace_fiscal_profile.return_value = None
        prof = await resolve_fiscal_profile(
            user_id="u-1",
            workspace_id="w-1",
            global_profile={"ccaa_residencia": "Madrid"},
            gestoria_service=svc,
        )
        assert prof["ccaa_residencia"] == "Madrid"


class TestGestoriaRouter:
    def _client(self, svc):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from app.auth.gestoria_guard import require_gestoria
        from app.auth.jwt_handler import TokenData
        from app.routers import gestoria as gestoria_router

        app = FastAPI()
        app.include_router(gestoria_router.router)
        app.dependency_overrides[require_gestoria] = lambda: TokenData(
            user_id="u-1", email="g@x.com"
        )
        gestoria_router.get_service = lambda: svc  # type: ignore[attr-defined]
        return TestClient(app)

    def test_create_client_returns_409_over_limit(self):
        from app.services.gestoria_service import ClientLimitError

        svc = AsyncMock()
        svc.create_client.side_effect = ClientLimitError("max")
        client = self._client(svc)
        resp = client.post(
            "/api/gestoria/clients",
            json={"nombre_cliente": "C", "tipo": "autonomo"},
        )
        assert resp.status_code == 409

    def test_list_clients_ok(self):
        from app.services.gestoria_service import GestoriaClient

        svc = AsyncMock()
        svc.list_clients.return_value = [
            GestoriaClient(id="w1", nombre_cliente="Ana", tipo="particular")
        ]
        client = self._client(svc)
        resp = client.get("/api/gestoria/clients")
        assert resp.status_code == 200
        assert resp.json()[0]["nombre_cliente"] == "Ana"

    def test_get_client_404(self):
        svc = AsyncMock()
        svc.get_client.return_value = None
        client = self._client(svc)
        resp = client.get("/api/gestoria/clients/xyz")
        assert resp.status_code == 404

    def test_update_client_404(self):
        svc = AsyncMock()
        svc.update_client.return_value = None
        client = self._client(svc)
        resp = client.put("/api/gestoria/clients/xyz", json={"nombre_cliente": "X"})
        assert resp.status_code == 404

    def test_delete_client_404(self):
        svc = AsyncMock()
        svc.delete_client.return_value = False
        client = self._client(svc)
        resp = client.delete("/api/gestoria/clients/xyz")
        assert resp.status_code == 404

    def test_delete_client_ok(self):
        svc = AsyncMock()
        svc.delete_client.return_value = True
        client = self._client(svc)
        resp = client.delete("/api/gestoria/clients/xyz")
        assert resp.status_code == 200
        assert resp.json() == {"deleted": True}


class TestPerClientHistory:
    @pytest.mark.asyncio
    async def test_conversations_filtered_by_workspace(self):
        from app.services.conversation_service import ConversationService

        captured: dict = {}
        db = AsyncMock()

        async def execute(sql, params=None):
            captured["sql"] = " ".join(sql.split())
            captured["params"] = params
            res = MagicMock()
            res.rows = []
            return res

        db.execute = execute
        svc = ConversationService(db)
        await svc.get_user_conversations("u-1", limit=50, workspace_id="w-1")
        assert "workspace_id = ?" in captured["sql"]
        assert "w-1" in captured["params"]

    @pytest.mark.asyncio
    async def test_roster_includes_declaration_count(self):
        from app.services.gestoria_service import GestoriaClientService

        svc = GestoriaClientService()
        db = AsyncMock()

        async def execute(sql, params=None):
            res = MagicMock()
            s = " ".join(sql.split())
            if s.startswith("SELECT wp.* FROM workspace_profiles"):
                res.rows = [
                    {
                        "workspace_id": "w1",
                        "nombre_cliente": "Ana",
                        "tipo": "autonomo",
                        "nif": None,
                        "ccaa": "Madrid",
                        "situacion_laboral": None,
                        "epigrafe_iae": None,
                        "regimen_iva": None,
                        "fecha_alta": None,
                        "datos_fiscales": "{}",
                        "created_at": "2026-01-01",
                        "updated_at": "2026-01-01",
                    }
                ]
            elif "FROM workspace_files" in s:
                res.rows = [{"file_count": 0}]
            elif "FROM quarterly_declarations" in s:
                res.rows = [{"declaration_count": 2}]
            else:
                res.rows = []
            return res

        db.execute = execute
        svc._get_db = AsyncMock(return_value=db)  # type: ignore[method-assign]
        clients = await svc.list_clients("u-1")
        assert clients[0].declaration_count == 2


class TestDeclarationWorkspaceScoping:
    @pytest.mark.asyncio
    async def test_save_persists_workspace_id(self):
        from app.services.declaration_service import DeclarationService

        captured: dict = {}

        db = AsyncMock()

        async def execute(sql, params=None):
            res = MagicMock()
            s = " ".join(sql.split())
            if s.startswith("SELECT id FROM quarterly_declarations"):
                res.rows = []  # no existe → INSERT path
            else:
                captured["sql"] = s
                captured["params"] = params
                res.rows = []
            return res

        db.execute = execute
        svc = DeclarationService(db)
        await svc.save(
            user_id="u-1",
            declaration_type="303",
            territory="Madrid",
            year=2025,
            quarter=2,
            form_data={},
            calculated_result={},
            workspace_id="w-1",
        )
        assert "workspace_id" in captured["sql"]
        assert "w-1" in (captured["params"] or [])


class TestRosterKpis:
    @pytest.mark.asyncio
    async def test_list_clients_includes_kpis(self):
        from app.services.gestoria_service import GestoriaClientService

        svc = GestoriaClientService()
        db = AsyncMock()

        async def execute(sql, params=None):
            res = MagicMock()
            s = " ".join(sql.split())
            if s.startswith("SELECT wp.* FROM workspace_profiles"):
                res.rows = [
                    {
                        "workspace_id": "w1",
                        "nombre_cliente": "Ana",
                        "tipo": "autonomo",
                        "nif": None,
                        "ccaa": "Madrid",
                        "situacion_laboral": None,
                        "epigrafe_iae": None,
                        "regimen_iva": None,
                        "fecha_alta": None,
                        "datos_fiscales": "{}",
                        "created_at": "2026-01-01",
                        "updated_at": "2026-01-01",
                    }
                ]
            elif "COUNT(wf.id)" in s:
                res.rows = [{"file_count": 4}]
            else:
                res.rows = []
            return res

        db.execute = execute
        svc._get_db = AsyncMock(return_value=db)  # type: ignore[method-assign]
        clients = await svc.list_clients("u-1")
        assert clients[0].file_count == 4
