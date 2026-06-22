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
