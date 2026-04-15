"""Tests T2B-013a — DefensIA Storage Service (AES-256-GCM + zstd).

TDD tests for `backend/app/services/defensia_storage.py`. Cubren:
- Modo deshabilitado fail-safe cuando `DEFENSIA_STORAGE_KEY` falta o es invalida.
- Roundtrip cifrar/descifrar con clave valida (env var o parametro directo).
- Unicidad del nonce (dos cifrados del mismo plaintext dan ciphertext distintos).
- Deteccion de tampering (AES-GCM verifica integridad).
- Manejo de payloads grandes con compresion zstd.

Regla de seguridad: NUNCA usar una clave dummy. Los tests generan una clave
aleatoria de 32 bytes con `secrets.token_hex(32)` (64 caracteres hex).
"""
from __future__ import annotations

import secrets

import pytest

# Import directo — si las deps (cryptography, zstandard) no estan, debe fallar
# con mensaje claro, no skip silencioso.
from app.services.defensia_storage import (
    DefensiaStorage,
    DefensiaStorageUnavailable,
)


def test_storage_disabled_without_key(monkeypatch):
    """Sin env var -> `is_enabled=False` y cifrar lanza `DefensiaStorageUnavailable`."""
    monkeypatch.delenv("DEFENSIA_STORAGE_KEY", raising=False)
    storage = DefensiaStorage()
    assert storage.is_enabled is False
    with pytest.raises(DefensiaStorageUnavailable):
        storage.cifrar(b"hola")
    with pytest.raises(DefensiaStorageUnavailable):
        storage.descifrar(b"ct", b"nonce")


def test_storage_disabled_with_wrong_length_key(monkeypatch):
    """Env var con longitud incorrecta (no 64 hex chars) -> deshabilitado."""
    monkeypatch.setenv("DEFENSIA_STORAGE_KEY", "deadbeef")  # 8 chars, no 64
    storage = DefensiaStorage()
    assert storage.is_enabled is False
    with pytest.raises(DefensiaStorageUnavailable):
        storage.cifrar(b"payload")


def test_storage_roundtrip_with_valid_key(monkeypatch):
    """Clave valida via env var -> cifrar + descifrar devuelve el plaintext original."""
    key_hex = secrets.token_hex(32)  # 64 hex chars = 32 bytes
    monkeypatch.setenv("DEFENSIA_STORAGE_KEY", key_hex)
    storage = DefensiaStorage()
    assert storage.is_enabled is True

    plaintext = b"liquidacion IRPF David Oliva 2023 - datos confidenciales"
    ciphertext, nonce = storage.cifrar(plaintext)

    assert isinstance(ciphertext, bytes)
    assert isinstance(nonce, bytes)
    assert len(nonce) == 12  # AES-GCM standard nonce length
    assert ciphertext != plaintext  # efectivamente cifrado

    recovered = storage.descifrar(ciphertext, nonce)
    assert recovered == plaintext


def test_storage_roundtrip_large_pdf(monkeypatch):
    """Payload grande (500 KB) -> zstd comprime + AES-GCM cifra + descifra OK."""
    key_hex = secrets.token_hex(32)
    monkeypatch.setenv("DEFENSIA_STORAGE_KEY", key_hex)
    storage = DefensiaStorage()

    # 500 KB de contenido repetitivo (caso realista: PDF con mucho texto similar).
    plaintext = (b"Articulo 41 bis RIRPF - procedimiento de verificacion de datos. " * 8000)
    assert len(plaintext) >= 500_000

    ciphertext, nonce = storage.cifrar(plaintext)
    # zstd debe comprimir fuertemente texto repetitivo antes del cifrado
    assert len(ciphertext) < len(plaintext) // 2, (
        f"zstd deberia comprimir texto repetitivo: ct={len(ciphertext)}, pt={len(plaintext)}"
    )

    recovered = storage.descifrar(ciphertext, nonce)
    assert recovered == plaintext


def test_storage_nonce_is_unique(monkeypatch):
    """Dos cifrados del mismo plaintext producen ciphertext/nonce distintos."""
    key_hex = secrets.token_hex(32)
    monkeypatch.setenv("DEFENSIA_STORAGE_KEY", key_hex)
    storage = DefensiaStorage()

    plaintext = b"mismo contenido dos veces"
    ct1, nonce1 = storage.cifrar(plaintext)
    ct2, nonce2 = storage.cifrar(plaintext)

    assert nonce1 != nonce2, "nonce debe ser aleatorio en cada llamada"
    assert ct1 != ct2, "ciphertext debe diferir porque nonce cambia"
    # Ambos descifran al mismo plaintext
    assert storage.descifrar(ct1, nonce1) == plaintext
    assert storage.descifrar(ct2, nonce2) == plaintext


def test_storage_descifrar_tampered_fails(monkeypatch):
    """Modificar 1 byte del ciphertext -> AES-GCM detecta tampering y raise."""
    from cryptography.exceptions import InvalidTag

    key_hex = secrets.token_hex(32)
    monkeypatch.setenv("DEFENSIA_STORAGE_KEY", key_hex)
    storage = DefensiaStorage()

    plaintext = b"datos intactos"
    ciphertext, nonce = storage.cifrar(plaintext)

    # Flipping one byte en el medio del ciphertext
    tampered = bytearray(ciphertext)
    tampered[len(tampered) // 2] ^= 0x01
    tampered_bytes = bytes(tampered)

    with pytest.raises(InvalidTag):
        storage.descifrar(tampered_bytes, nonce)


def test_storage_key_passed_directly(monkeypatch):
    """Instanciar con key=b'...' (32 bytes) sin env var -> funciona."""
    monkeypatch.delenv("DEFENSIA_STORAGE_KEY", raising=False)
    raw_key = secrets.token_bytes(32)
    storage = DefensiaStorage(key=raw_key)

    assert storage.is_enabled is True
    plaintext = b"instanciacion directa"
    ct, nonce = storage.cifrar(plaintext)
    assert storage.descifrar(ct, nonce) == plaintext


# ---------------------------------------------------------------------------
# Migracion SQL — wiring check y aplicacion idempotente
# ---------------------------------------------------------------------------

def test_storage_migration_referenced_in_init_schema():
    """Guard anti-drift: `turso_client.py` debe referenciar la migracion.

    Mirror del patron usado en `test_migration.py` para la parte 1.
    """
    from pathlib import Path

    turso_source = (
        Path(__file__).parent.parent.parent
        / "app" / "database" / "turso_client.py"
    ).read_text(encoding="utf-8")
    assert "20260414_defensia_storage.sql" in turso_source, (
        "init_schema() en turso_client.py no referencia la migracion de "
        "storage cifrado DefensIA. Anade el bloque que lee y ejecuta "
        "`20260414_defensia_storage.sql`."
    )


def test_storage_migration_adds_columns_and_is_idempotent(tmp_path):
    """Tras aplicar Parte 1 + storage migration, `defensia_documentos` tiene
    las columnas `contenido_cifrado`, `nonce`, `algo`. Aplicar dos veces no
    debe crashear (idempotencia garantizada por el codigo de aplicacion)."""
    import sqlite3
    from pathlib import Path

    db_path = tmp_path / "storage.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id TEXT PRIMARY KEY)")

    migrations_dir = (
        Path(__file__).parent.parent.parent / "app" / "database" / "migrations"
    )
    part1 = migrations_dir / "20260413_defensia_tables.sql"
    storage = migrations_dir / "20260414_defensia_storage.sql"
    assert storage.exists(), f"Storage migration missing: {storage}"

    conn.executescript(part1.read_text(encoding="utf-8"))

    def apply_storage_migration():
        # Mirror del loader de `turso_client.py`: strip por lineas antes del
        # split, para no saltar la primera sentencia por comentarios pegados.
        sql = storage.read_text(encoding="utf-8")
        for raw_stmt in sql.split(";"):
            exec_lines = [
                line
                for line in raw_stmt.splitlines()
                if line.strip() and not line.strip().startswith("--")
            ]
            stmt = "\n".join(exec_lines).strip()
            if not stmt:
                continue
            try:
                conn.execute(stmt)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    continue
                raise

    apply_storage_migration()

    cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(defensia_documentos)")
    }
    assert {"contenido_cifrado", "nonce", "algo"}.issubset(cols), (
        f"Columnas de storage ausentes tras migracion. Columnas: {cols}"
    )

    # Idempotencia: segunda aplicacion no debe crashear.
    apply_storage_migration()
    cols_after = {
        row[1]
        for row in conn.execute("PRAGMA table_info(defensia_documentos)")
    }
    assert cols == cols_after

    conn.close()
