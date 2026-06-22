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
