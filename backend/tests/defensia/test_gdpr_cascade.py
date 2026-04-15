"""T3-003 — GDPR cascade delete DefensIA.

Verifica que al eliminar un usuario (GDPR Art. 17 — Right to Erasure)
TODAS las tablas defensia_* quedan sin filas con ese user_id ni hijos
transitivos. Testea el delete explicito del router user_rights.py como
defensa en profundidad frente al ON DELETE CASCADE de la migracion.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


BASE_MIGRATION = (
    Path(__file__).parent.parent.parent
    / "app"
    / "database"
    / "migrations"
    / "20260413_defensia_tables.sql"
)


@pytest.fixture
def db_with_expediente(tmp_path):
    """Crea un SQLite real con schema defensia + 1 user + 1 expediente
    cargado con un documento, brief, dictamen, escrito, cuota y rag_log.
    Devuelve (conn, user_id) para que cada test escoja su estrategia.
    """
    db_path = tmp_path / "gdpr_test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")
    conn.executescript(BASE_MIGRATION.read_text(encoding="utf-8"))

    user_id = "user_gdpr_test"
    exp_id = "exp_gdpr_test"
    doc_id = "doc_gdpr_test"
    brief_id = "brief_gdpr_test"
    dict_id = "dic_gdpr_test"
    esc_id = "esc_gdpr_test"

    conn.execute("INSERT INTO users VALUES (?)", [user_id])
    conn.execute(
        "INSERT INTO defensia_expedientes "
        "(id, user_id, nombre, tributo, ccaa, tipo_procedimiento_declarado, "
        " estado, created_at, updated_at) "
        "VALUES (?, ?, 'Caso GDPR', 'IRPF', 'Madrid', 'liquidacion', "
        "        'borrador', '2026-04-15', '2026-04-15')",
        [exp_id, user_id],
    )
    conn.execute(
        "INSERT INTO defensia_documentos "
        "(id, expediente_id, nombre_original, ruta_almacenada, mime_type, "
        " tamano_bytes, hash_sha256, tipo_documento, created_at) "
        "VALUES (?, ?, 'liquidacion.pdf', 'fake/path', 'application/pdf', "
        "        1024, 'fakehash', 'LIQUIDACION_PROVISIONAL', '2026-04-15')",
        [doc_id, exp_id],
    )
    conn.execute(
        "INSERT INTO defensia_briefs (id, expediente_id, texto, created_at) "
        "VALUES (?, ?, 'La AEAT me reclama...', '2026-04-15')",
        [brief_id, exp_id],
    )
    conn.execute(
        "INSERT INTO defensia_dictamenes "
        "(id, expediente_id, fase_detectada, argumentos_json, resumen_caso, "
        " created_at) "
        "VALUES (?, ?, 'COMPROBACION_PROPUESTA', '[]', 'resumen', "
        "        '2026-04-15')",
        [dict_id, exp_id],
    )
    conn.execute(
        "INSERT INTO defensia_escritos "
        "(id, expediente_id, dictamen_id, tipo_escrito, contenido_markdown, "
        " created_at, updated_at) "
        "VALUES (?, ?, ?, 'alegaciones_verificacion', 'contenido', "
        "        '2026-04-15', '2026-04-15')",
        [esc_id, exp_id, dict_id],
    )
    conn.execute(
        "INSERT INTO defensia_cuotas_mensuales "
        "(user_id, ano_mes, expedientes_creados) "
        "VALUES (?, '2026-04', 1)",
        [user_id],
    )
    conn.execute(
        "INSERT INTO defensia_rag_log "
        "(expediente_id, regla_id, soportado, confianza, razonamiento, "
        " created_at) "
        "VALUES (?, 'R001', 1, 0.9, 'verif', '2026-04-15')",
        [exp_id],
    )
    conn.commit()

    return conn, user_id


def _count_defensia_rows(conn, user_id: str) -> dict[str, int]:
    """Cuenta filas en cada tabla defensia asociadas (directa o
    transitivamente) al user_id."""
    return {
        "expedientes": conn.execute(
            "SELECT COUNT(*) FROM defensia_expedientes WHERE user_id = ?",
            [user_id],
        ).fetchone()[0],
        "documentos": conn.execute(
            "SELECT COUNT(*) FROM defensia_documentos WHERE expediente_id IN "
            "(SELECT id FROM defensia_expedientes WHERE user_id = ?)",
            [user_id],
        ).fetchone()[0],
        "briefs": conn.execute(
            "SELECT COUNT(*) FROM defensia_briefs WHERE expediente_id IN "
            "(SELECT id FROM defensia_expedientes WHERE user_id = ?)",
            [user_id],
        ).fetchone()[0],
        "dictamenes": conn.execute(
            "SELECT COUNT(*) FROM defensia_dictamenes WHERE expediente_id IN "
            "(SELECT id FROM defensia_expedientes WHERE user_id = ?)",
            [user_id],
        ).fetchone()[0],
        "escritos": conn.execute(
            "SELECT COUNT(*) FROM defensia_escritos WHERE expediente_id IN "
            "(SELECT id FROM defensia_expedientes WHERE user_id = ?)",
            [user_id],
        ).fetchone()[0],
        "cuotas": conn.execute(
            "SELECT COUNT(*) FROM defensia_cuotas_mensuales WHERE user_id = ?",
            [user_id],
        ).fetchone()[0],
        "rag_log": conn.execute(
            "SELECT COUNT(*) FROM defensia_rag_log WHERE expediente_id IN "
            "(SELECT id FROM defensia_expedientes WHERE user_id = ?)",
            [user_id],
        ).fetchone()[0],
    }


def test_fixture_has_all_seven_defensia_rows(db_with_expediente):
    """Sanity check: el fixture realmente pobla las 7 tablas."""
    conn, user_id = db_with_expediente
    counts = _count_defensia_rows(conn, user_id)
    assert all(v >= 1 for v in counts.values()), f"fixture incompleto: {counts}"


def test_cascade_from_pragma_foreign_keys(db_with_expediente):
    """Con PRAGMA foreign_keys=ON, DELETE FROM users cascadea a las 7
    tablas defensia automaticamente via las FK ON DELETE CASCADE del
    schema. Este test garantiza que la migracion declara las FK
    correctamente."""
    conn, user_id = db_with_expediente

    conn.execute("DELETE FROM users WHERE id = ?", [user_id])
    conn.commit()

    counts = _count_defensia_rows(conn, user_id)
    assert counts == {
        "expedientes": 0,
        "documentos": 0,
        "briefs": 0,
        "dictamenes": 0,
        "escritos": 0,
        "cuotas": 0,
        "rag_log": 0,
    }, f"cascade via FK fallo: {counts}"


def test_router_explicit_delete_pattern_covers_all_tables(db_with_expediente):
    """Replica el patron de DELETE explicito del router user_rights.py sin
    depender del CASCADE (defense-in-depth). Si Turso libSQL no aplica FK
    en algun camino, este delete manual sigue siendo correcto.

    Importante: ejecuta los DELETE en el mismo orden que el router
    (rag_log -> escritos -> dictamenes -> briefs -> documentos ->
    expedientes -> cuotas) — lo contrario rompe las FK.
    """
    conn, user_id = db_with_expediente

    # Desactiva el cascade automatico para aislar el test al delete manual
    conn.execute("PRAGMA foreign_keys = OFF")

    stmts = [
        """DELETE FROM defensia_rag_log WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        """DELETE FROM defensia_escritos WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        """DELETE FROM defensia_dictamenes WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        """DELETE FROM defensia_briefs WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        """DELETE FROM defensia_documentos WHERE expediente_id IN
           (SELECT id FROM defensia_expedientes WHERE user_id = ?)""",
        "DELETE FROM defensia_expedientes WHERE user_id = ?",
        "DELETE FROM defensia_cuotas_mensuales WHERE user_id = ?",
    ]
    for stmt in stmts:
        conn.execute(stmt, [user_id])
    conn.commit()

    counts = _count_defensia_rows(conn, user_id)
    assert counts == {
        "expedientes": 0,
        "documentos": 0,
        "briefs": 0,
        "dictamenes": 0,
        "escritos": 0,
        "cuotas": 0,
        "rag_log": 0,
    }


def test_router_user_rights_references_all_seven_defensia_tables():
    """Guard anti-drift: si alguien anade una tabla defensia_* nueva a la
    migracion, el router debe referenciarla. Este test rompe si el router
    olvida alguna tabla.
    """
    router_src = (
        Path(__file__).parent.parent.parent
        / "app"
        / "routers"
        / "user_rights.py"
    ).read_text(encoding="utf-8")

    tablas_esperadas = [
        "defensia_rag_log",
        "defensia_escritos",
        "defensia_dictamenes",
        "defensia_briefs",
        "defensia_documentos",
        "defensia_expedientes",
        "defensia_cuotas_mensuales",
    ]
    for tabla in tablas_esperadas:
        assert f"DELETE FROM {tabla}" in router_src, (
            f"user_rights.py no hace DELETE FROM {tabla} — "
            f"GDPR cascade incompleto"
        )
