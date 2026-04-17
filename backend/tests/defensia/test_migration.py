import sqlite3
from pathlib import Path

import pytest

# Resolve relative to this file: tests/defensia/ -> backend/ -> app/database/migrations/
MIGRATION = Path(__file__).parent.parent.parent / "app" / "database" / "migrations" / "20260413_defensia_tables.sql"


def test_migration_creates_all_tables(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
    conn.executescript(MIGRATION.read_text(encoding="utf-8"))

    tablas_esperadas = {
        "defensia_expedientes",
        "defensia_documentos",
        "defensia_briefs",
        "defensia_dictamenes",
        "defensia_escritos",
        "defensia_cuotas_mensuales",
        "defensia_rag_log",
    }
    encontradas = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'defensia_%'"
        )
    }
    assert encontradas == tablas_esperadas


def test_init_schema_creates_defensia_tables(tmp_path, monkeypatch):
    """Smoke test: init_schema() must actually create the DefensIA tables.

    This catches the case where someone adds a migration SQL file but forgets
    to wire it into the production init_schema() entry point.
    """
    import sqlite3
    db_path = tmp_path / "prod.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Simulate init_schema's DefensIA block inline (we can't call init_schema
    # directly in a unit test without the full Turso client setup)
    from pathlib import Path
    migration = (
        Path(__file__).parent.parent.parent
        / "app" / "database" / "migrations"
        / "20260413_defensia_tables.sql"
    )
    assert migration.exists(), f"Migration file missing: {migration}"

    # The production entry point in turso_client.py MUST contain a reference
    # to this exact file name. This is the real guard against drift.
    turso_source = (
        Path(__file__).parent.parent.parent
        / "app" / "database" / "turso_client.py"
    ).read_text(encoding="utf-8")
    assert "20260413_defensia_tables.sql" in turso_source, (
        "init_schema() in turso_client.py does not reference the DefensIA "
        "migration file. Add: executescript(migration.read_text()) inside "
        "init_schema()."
    )

    # Users table (FK target)
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
    conn.executescript(migration.read_text(encoding="utf-8"))
    conn.commit()

    encontradas = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'defensia_%'"
        )
    }
    assert len(encontradas) == 7


def test_migration_cascade_user_delete(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
    conn.executescript(MIGRATION.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO users VALUES ('u1')")
    conn.execute(
        "INSERT INTO defensia_expedientes (id, user_id, nombre, tributo, ccaa, "
        "tipo_procedimiento_declarado, estado, created_at, updated_at) VALUES "
        "('e1','u1','Test','IRPF','Madrid','liquidacion','borrador','2026-04-13','2026-04-13')"
    )
    conn.execute("DELETE FROM users WHERE id='u1'")
    count = conn.execute(
        "SELECT COUNT(*) FROM defensia_expedientes WHERE id='e1'"
    ).fetchone()[0]
    assert count == 0, "cascade delete must remove expediente when user deleted"


# ============================================================================
# Copilot round 2 #4-#7: fail-fast en migraciones no idempotentes
# ============================================================================


class _FailingFakeDB:
    """Fake DB que lanza una excepcion especifica en el primer UPDATE."""

    def __init__(self, error_msg: str):
        self._error_msg = error_msg
        self.calls: list[str] = []

    async def execute(self, sql: str, params=None):
        self.calls.append(sql)
        raise RuntimeError(self._error_msg)


class _IdempotentFakeDB:
    """Fake DB que simula errores benignos de duplicate column."""

    def __init__(self):
        self.calls: list[str] = []

    async def execute(self, sql: str, params=None):
        self.calls.append(sql)
        raise RuntimeError("SQLite error: duplicate column name")


@pytest.mark.asyncio
async def test_migration_raises_on_non_idempotent_error(tmp_path):
    """Copilot round 2 #4: un SQL invalido debe abortar init_schema."""
    from app.database.turso_client import TursoClient

    migration_file = tmp_path / "test_migration.sql"
    migration_file.write_text("ALTER TABLE inexistente ADD COLUMN foo TEXT;", encoding="utf-8")

    client = TursoClient.__new__(TursoClient)  # bypass __init__
    client.execute = _FailingFakeDB("no such table: inexistente").execute  # type: ignore

    with pytest.raises(RuntimeError, match="no such table"):
        await client._apply_defensia_migration(migration_file, label="test")


@pytest.mark.asyncio
async def test_migration_swallows_duplicate_column(tmp_path):
    """Copilot round 2 #4: duplicate column sigue siendo idempotente."""
    from app.database.turso_client import TursoClient

    migration_file = tmp_path / "test_migration.sql"
    migration_file.write_text("ALTER TABLE foo ADD COLUMN bar TEXT;", encoding="utf-8")

    client = TursoClient.__new__(TursoClient)
    fake = _IdempotentFakeDB()
    client.execute = fake.execute  # type: ignore

    # No debe levantar: error duplicate column es benigno
    await client._apply_defensia_migration(migration_file, label="test")
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_migration_noop_if_file_missing(tmp_path):
    """Si el fichero no existe, solo warning, no crash."""
    from app.database.turso_client import TursoClient

    client = TursoClient.__new__(TursoClient)
    missing = tmp_path / "no_existe.sql"
    await client._apply_defensia_migration(missing, label="missing")  # sin excepcion
