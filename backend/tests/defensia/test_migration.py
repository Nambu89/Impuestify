import sqlite3
from pathlib import Path

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
