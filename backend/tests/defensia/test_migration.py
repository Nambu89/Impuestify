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
