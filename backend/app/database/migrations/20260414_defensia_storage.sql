-- DefensIA Wave 2B storage cifrado (T2B-013a).
-- Anade columnas de almacenamiento cifrado a `defensia_documentos`.
-- Decision de producto Q1 (cerrada): base64 + zstd + AES-256-GCM, con clave
-- en env var `DEFENSIA_STORAGE_KEY` (32 bytes = 64 chars hex).
--
-- NOTA: SQLite no soporta `ALTER TABLE ADD COLUMN IF NOT EXISTS`. La
-- idempotencia la garantiza el codigo de aplicacion en `turso_client.py`
-- envolviendo cada statement en try/except que ignora errores del tipo
-- "duplicate column name" (columna ya existe tras primer arranque).

ALTER TABLE defensia_documentos ADD COLUMN contenido_cifrado BLOB;
ALTER TABLE defensia_documentos ADD COLUMN nonce BLOB;
ALTER TABLE defensia_documentos ADD COLUMN algo TEXT DEFAULT 'aes-256-gcm-zstd';
