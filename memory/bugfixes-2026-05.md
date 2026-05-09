# Bugfixes — Mayo 2026 (sesion 38+)

## Bug 85 — Topic classifier bloquea preguntas legitimas con workspace adjunto

**Reportado por**: David Oliva (cuenta hotmail) 2026-05-07.
**Sintoma**: Workspace "Declaracion RENTA 2025" con 6 archivos. Pregunta `evalua si mi declaracion es correcta` (36 chars) → bloqueada 6 veces consecutivas con mensaje canned `Soy Impuestify... Reformula tu pregunta`. Sistema percibido como inutilizable.

**Causa raiz**:
- `chat_stream.py:117` llamaba `security_pipeline.check(question, user_id)` sin pasar metadata del workspace.
- Topic classifier (Groq llama-3.1-8b-instant) recibia la pregunta sola, sin contexto. Razono: "No se proporciona informacion sobre la declaracion en cuestion" → `fiscal_es=false`.
- Velocity check no funcionaba (Bug B), asi que no throttleaba al 4. intento.

**Fix general** (no parche del caso):
- Nuevo dataclass `TopicContext(workspace_name, doc_count, file_types, recent_user_turns)` en `topic_classifier.py`.
- `SecurityPipeline.check(question, user_id, context=None)` propaga al classifier (solo layer 6 lo lee, capas 1-5 son inmunes).
- Helper `_build_pipeline_context()` en `chat_stream.py` hace 1-2 queries Turso (workspace + last 2 user turns) ANTES del pipeline.
- System prompt actualizado con regla: "ambigua + ctx fiscal → fiscal=true; off-scope explicito → ignora ctx".
- Cache LRU rekeyed con `(question_hash, ctx_hash)` para no envenenar entre conversaciones.

**Seguridad mantenida**:
- Off-scope explicito (cocina, codigo) sigue bloqueado aunque haya workspace (test `test_offscope_with_fiscal_workspace_still_blocked`).
- Prompt injection bloqueado en layer 2 ANTES de llegar al classifier (test `test_prompt_injection_blocked_even_with_workspace`).
- Pregunta ambigua sin contexto → sigue bloqueada (regresion intacta).

**Archivos modificados**:
- `backend/app/security/topic_classifier.py`: TopicContext, helpers, system prompt, cache.
- `backend/app/security/security_pipeline.py`: parametro context propagado.
- `backend/app/routers/chat_stream.py`: `_build_pipeline_context()` helper, restore workspace_id antes del pipeline, eliminado segundo restore duplicado.
- `backend/tests/test_topic_classifier_context.py` (NEW): 15 tests.
- `backend/tests/test_security_pipeline_context.py` (NEW): 7 tests.

## Bug 86 — Token budget + velocity check fail-open silencioso (sprint 3 sesion 37)

**Sintoma**: Logs Railway 35+ entries en 4 dias: `Token budget read failed (fail-open): int() argument must be a string, ..., not 'coroutine'`.
**Impacto**: TODA proteccion anti-runaway de coste y anti-flooding desactivada desde sprint 3. Cualquier user podia flood `/api/ask/stream` sin throttle.

**Causa raiz**: `main.py:164` inicializa `AsyncRedis`. `token_budget.py` y `velocity_check.py` (sprint 3) usaban `redis.get/incr/expire` sin `await`. Resultado: `int(coroutine)` → TypeError → fail-open.

**Fix**:
- `token_budget.check()` y `record()` → `async def`.
- `velocity_check.check()` → `async def`.
- Callers en `chat_stream.py:140,156,704` → `await`.
- Codigo robusto a sync mocks: `if hasattr(x, "__await__"): x = await x`.

**Tests**:
- `test_token_budget.py`: 17 tests migrados a async + 1 nuevo (`test_works_with_async_redis_mock`).
- `test_velocity_check.py`: 8 tests migrados + 1 nuevo.
- 27/27 PASS.

## Bug 87 — PII detector revienta con prompts largos / rate limit

**Sintoma**: Logs Railway: `PII Detector API Error: Error code: 429 - Rate limit reached for model gpt-oss-safeguard-20b` y `Error code: 413 - Request too large`. Free tier Groq compartido con LlamaGuard (14400/dia).
**Impacto**: PII detector fail-open (no bloquea), pero gasta cuota Groq + 1-2s latencia.

**Causa raiz**: `pii_detector.detect()` llamaba a Groq con texto crudo sin limit ni cache.

**Fix**:
- Per-instance dict cache `self._cache` (max 2048).
- Length guard: textos `>3000` chars → fallback `_regex_only()` usando `self.PII_PATTERNS` ya existentes (DNI, NIE, IBAN, email, phone, CIF, etc.).
- Retry sync con `time.sleep(0.5)` en 429. Si falla otra vez → fallback regex.
- En 413 / error generico → fallback regex inmediato.
- Mantiene firma sync (no rompe `security_pipeline.py:184` ni `demo.py:378`).

**Tests** (`test_pii_detector_resilience.py` NEW):
- 11 tests: length guard, cache hit/miss, 429 retry exito/fallo, 413 fallback, sin client.
- 12/12 PASS (incluye regression `test_ai_security.py::TestAIPIIDetector`).

## Bug 88 — Logs ruidosos `duplicate column name` al startup

**Sintoma**: 4 entries `Database query failed: Hrana: stream error: SQLite error: duplicate column name: contenido_cifrado/nonce/algo/en_curso` al re-deploy.
**Impacto**: Cosmetico (try/except ya capturaba), pero contamina monitoring.

**Causa raiz**: `_apply_defensia_migration` ejecutaba `ALTER TABLE ... ADD COLUMN`. SQLite no soporta `IF NOT EXISTS` en ADD COLUMN. El driver Hrana logueaba el error ANTES de que Python lo capture.

**Fix**: Pre-check con `PRAGMA table_info(<table>)`. Si la columna ya existe → skip silencioso. Helper `_column_exists()` + regex `_ALTER_ADD_COL_RE` en `turso_client.py`.

## Reglas permanentes derivadas

1. **Pipeline de seguridad NUNCA debe ser ciego al contexto de la conversacion**. Si una capa de bloqueo razona sobre la pregunta sola, debe recibir metadata server-side (workspace, hilo) para decidir bien. Capas previas (regex, prompt injection) ya filtran lo malicioso.
2. **AsyncRedis requires `await`**. Cualquier funcion que use el cliente Redis debe ser `async`. Si por compat necesita aceptar mocks sync, usar `if hasattr(x, "__await__"): x = await x`.
3. **Servicios externos con cuota limitada (Groq free tier) requieren cache + length guard + fallback determinista**. No depender 100% del LLM para decisiones que se pueden tomar offline.
4. **Migraciones idempotentes**: para `ALTER TABLE ... ADD COLUMN` usar `PRAGMA table_info` antes en vez de try/except, para evitar logs ruidosos del driver.
