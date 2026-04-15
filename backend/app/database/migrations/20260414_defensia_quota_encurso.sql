-- DefensIA quota reserve-commit-release (T2B-010).
-- Anade columna `en_curso` al contador mensual para poder ejecutar el patron
-- reserve/commit/release atomico y evitar DoS intra-ventana (H8 del plan-checker).
--
-- La tabla base `defensia_cuotas_mensuales` (migracion 20260413) ya contiene:
--   (user_id, ano_mes, expedientes_creados)
-- Solo falta la reserva temporal. Contamos `expedientes_creados + en_curso`
-- contra el limite mensual del plan.
--
-- NOTA: SQLite no soporta `ALTER TABLE ADD COLUMN IF NOT EXISTS`. La
-- idempotencia se garantiza en `turso_client.py` envolviendo el statement
-- en try/except que ignora "duplicate column name".

ALTER TABLE defensia_cuotas_mensuales ADD COLUMN en_curso INTEGER NOT NULL DEFAULT 0;
