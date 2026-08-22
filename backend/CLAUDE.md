# backend/CLAUDE.md — Backend Guide

## Stack & Setup

Python 3.12+ | FastAPI 0.104+ | Microsoft Agent Framework 1.0.0b | OpenAI API | Groq API (LlamaGuard4)

```bash
cd backend && pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd backend && pytest tests/ -v --tb=short
# Expected: 1083+ tests PASS
cd backend && ruff check .              # Lint (CI gate, --exit-zero Phase 1)
cd backend && ruff format .             # Format (CI gate)
cd backend && pip install -r requirements-dev.txt  # First time only
```

### Environment Variables (required)

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | GPT-5-mini / GPT-5 |
| `GROQ_API_KEY` | Llama Guard 4 + Prompt Guard (free: 14,400 req/day) |
| `TURSO_DATABASE_URL` | libsql://... |
| `TURSO_AUTH_TOKEN` | Turso auth |
| `JWT_SECRET_KEY` | `openssl rand -hex 32` |
| `UPSTASH_REDIS_REST_URL` + `TOKEN` | Rate limiting + session cache |
| `UPSTASH_VECTOR_REST_URL` + `TOKEN` | Semantic cache |
| `STRIPE_SECRET_KEY` + `WEBHOOK_SECRET` + `PRICE_ID` | Payments |
| `RESEND_API_KEY` + `RESEND_FROM_EMAIL` | Email to advisors |
| `ALLOWED_ORIGINS` | CORS (frontend URL) |
| `FRONTEND_URL` | Base URL for reset-password link (default: https://impuestify.com) |

## Multi-Agent System (`app/agents/`)

### CoordinatorAgent (`coordinator_agent.py`)
Routes queries to specialized agents based on intent analysis. Microsoft Agent Framework.

### TaxAgent (`tax_agent.py`)
Expert on IRPF, IVA, autonomous quotas. Tools: `calculate_irpf`, `calculate_autonomous_quota`, `search_tax_regulations`, `discover_deductions`. Tone: conversational, educational.

**REGLA: Clarificación obligatoria antes de asumir situación laboral**
- El system prompt DEBE instruir al agente a verificar `situacion_laboral` del perfil fiscal ANTES de usar tools de autónomos (`calculate_autonomous_quota`, `calculate_modelo_303`, `calculate_modelo_130`).
- Si el usuario es "particular" y menciona ingresos por actividad económica → PREGUNTAR si es autónomo, nunca asumir.
- `_build_prompt()` recibe `fiscal_profile` y genera tool hints condicionales según `situacion_laboral`.
- NUNCA poner "no preguntes en exceso" sin matizar que datos clave (CCAA, situación laboral) SÍ se deben preguntar.

### PayslipAgent (`payslip_agent.py`)
Extracts 13 fields from payslips (gross/net salary, IRPF, SS, extras). Calculates annual projections.

### NotificationAgent (`notification_agent.py`)
Analyzes AEAT notification PDFs. Extracts amounts, deadlines, concepts.

**REGLA: Patrón answer-first — NO estructura rígida de secciones**
- El `SYSTEM_PROMPT` usa patrón answer-first igual que TaxAgent: responde primero, explica solo lo no obvio.
- NO imponer secciones fijas (¿Qué es esto?, Plazos, Tu situación fiscal, etc.) — el LLM las rellenaría aunque estuvieran vacías.
- `format_notification_friendly` en `notifications.py` NO debe añadir intro hardcodeada ni pasos hardcodeados por tipo — solo envuelve el summary del LLM con el bloque de plazos calculados server-side y un footer mínimo.

### WorkspaceAgent (`workspace_agent.py`)
Analyzes uploaded documents. Tools: `get_workspace_summary`, `calculate_vat_balance`, `project_annual_irpf`, `get_quarterly_deadlines`.

## Security Layers (`app/security/`)

Pipeline (in order):
1. **Rate limiting** (`rate_limiter.py`) — SlowAPI + Upstash Redis. /api/ask 10/min, /auth/login 5/min. 5 violations → 60-min IP block.
2. **Security headers** (`main.py:322`) — CSP, X-Frame-Options, XSS, Referrer-Policy
3. **JWT validation** (`auth/jwt_handler.py`) — `get_current_user()` returns `TokenData` Pydantic model
4. **Prompt injection** (`prompt_injection.py`) — Llama Prompt Guard 2 via Groq
5. **PII detection** (`pii_detector.py`) — Spanish DNI/NIE, phones, emails, bank accounts
6. **SQL injection** (`sql_injection.py`) — Pattern detection
7. **Content moderation** (`llama_guard.py`) — Llama Guard 4, 14 categories, Spanish, fails open
8. **Complexity routing** (`complexity_router.py`) — simple/moderate/complex
9. **Content restriction** — Autonomo content blocked for plan Particular
10. **Semantic cache** (`semantic_cache.py`) — Upstash Vector, 0.93 threshold, 24h TTL
11. **Guardrails** (`guardrails.py`) — Input/output validation
12. **Audit logging** (`audit_logger.py`) — Immutable security event log

**CRITICAL**: `get_current_user()` returns `TokenData` model. Use `current_user.user_id`, `current_user.email` — NOT `.get("user_id")`.

### REGLA: todo endpoint que pase texto de usuario a un LLM DEBE llamar a `security_pipeline.check()`

No basta con que el agente tenga su propio `_check_input_safety()` — los
guardrails del agente son fail-open y no cubren PII, SQLi ni clasificador de
temas. El pipeline central es el único punto donde están las 12 capas.

```python
# OK — el router filtra ANTES de invocar al agente
from app.security.security_pipeline import security_pipeline

result = security_pipeline.check(question=body.message or "", user_id=str(current_user.user_id))
if not result.is_safe:
    ...  # devolver rechazo
safe_message = result.sanitized_text or body.message   # usar el saneado, no el crudo

# NO — pasar el input crudo directamente al agente
async for chunk in agent.chat_stream(body.message): ...
```

Al emitir el rechazo usar `result.rejection_message` (texto para el usuario),
**NUNCA** `result.reason` — ese nombra la capa y los patrones que hicieron
match, y filtrarlo es un info leak. Precedente: Bug 104 (DefensIA llevaba
desde la sesión 32 sin pipeline).

### REGLA: una capa de seguridad basada en LLM necesita suelo determinista

Si Groq no está disponible (sin API key, 429, timeout), la capa **no puede
devolver "seguro"**: eso la apaga en silencio y sigue figurando en el inventario
de seguridad como si funcionara.

Antes de dar por bueno un `return ... is_safe=True` en una rama de error,
**seguir el flujo hasta el llamador**. El comportamiento sin Groq no es binario:

| Capa | Sin Groq | Detalle |
|---|---|---|
| `pii_detector` | **parcial** | `detect()` corre el regex y deja mandar a `_HIGH_CONFIDENCE_PII`, así que DNI/NIE/IBAN/email/teléfono/CIF SÍ se cazan. Lo que queda fuera de ese conjunto (`postal_address`) NO |
| `prompt_injection` | **cubierto** | su rama sin cliente ocurre DESPUÉS del regex |
| `sql_injection` | **era fail-open total** | `security_pipeline` llamaba y se fiaba. Arreglado con `_regex_only()`. Bug 116 |

Leer la rama aislada lleva a conclusiones falsas en las dos direcciones: se
"arregló" un fail-open inexistente en `pii_detector` (y el arreglo empeoraba las
cosas, porque hacía bloquear a los patrones ambiguos) y se pasó por alto uno real
en `sql_injection`.

Dos cosas más que hay que tener presentes al razonar sobre estas capas:

- **`risk_level` debe ser `"high"` o `"critical"`** al degradar. El pipeline solo
  rechaza con esos dos valores, así que un `"medium"` pasa igual que un
  fail-open.
- **El pipeline se traga las excepciones de cada capa**
  (`except Exception: logger.warning("... non-blocking")`). Si una capa lanza, se
  salta entera y la petición sigue. Es deliberado —que un fallo de Groq no tumbe
  el chat— pero significa que una excepción no controlada dentro de una capa la
  desactiva en silencio.

### REGLA: los patrones de ataque se describen por FORMA, no por ejemplos

Enumerar cadenas de manual da cobertura aparente. La primera versión de
`_BLOCKING_PATTERNS` listaba `UNION SELECT` y `' OR '1'='1`, y **8 de 9**
evasiones triviales la esquivaban: `' OR 'x'='x`, `UNION ALL SELECT`,
`UNION/**/SELECT`, `; DELETE FROM`, `OR TRUE`, `pg_sleep(`, y la versión
url-codificada `%27%20OR%201%3D1`.

Al escribir un patrón de ataque, preguntarse **cómo lo escribiría alguien que
quiere esquivarlo**: separadores alternativos, comentarios intercalados,
sinónimos del verbo, codificación. Y analizar también el texto decodificado.

### REGLA: un regex de PII caza lo inequívoco; lo ambiguo es del LLM

Un patrón de `PII_PATTERNS` decide **solo** cuando el texto pasa de 3000
caracteres, porque ahí `detect()` salta a Groq. Si el patrón describe una forma
que otra cosa comparte, en ese camino rechaza consultas legítimas.

Antes de añadir un patrón, preguntarse: **¿esta forma significa una única cosa
en castellano fiscal?**

```python
# NO — describe la forma, no el significado
"postal_code": r"\b(?:0[1-9]|[1-4]\d|5[0-2])\d{3}\b"   # tambien es 30000 EUR
"passport":    r"\b[A-Z]{2,3}\d{6,9}\b"                # tambien es un expediente

# SI — la etiqueta desambigua, y "pasaporte" no tiene otro sentido
"passport": r"\b(?i:pasaporte|passport)[^\d\n]{0,8}?([A-Z]{2,3}\d{6,9})\b"
```

La ventana del conector se MIDE, no se estima: 8 es la longitud exacta de
`" numero "`, el conector legítimo más largo. Con 12 aún colaba
`Pasaporte: s/d; exp ABC123456`, que son dos datos distintos en la misma frase.

Si ni con etiqueta se desambigua, describe la **forma del dato completo** en vez
del número: `postal_code` (5 cifras) se sustituyó por `postal_address` (código
postal **seguido de población**), que un importe no puede imitar porque va
seguido de su moneda. Y si tampoco eso funciona, **el patrón sobra**: `postal_code` se eliminó
porque `c.p.` es *corto plazo* en contabilidad y ningún lookbehind aguanta
`deuda a corto plazo (C.P.): 30000 EUR` sin comerse a la vez `Enviar a C.P.
28013`. Eso es semántica y le toca al LLM, que lee la frase entera y conoce la
CCAA del perfil. Precedente: Bug 114.

Práctica estándar (Microsoft Presidio, tutorial 06_context): un regex de pocas
cifras es de confianza muy baja por sí solo y necesita palabras de contexto.

### REGLA: nunca hardcodear un id de modelo LLM/Vision

Siempre `settings.<PROVIDER>_MODEL`. Cuando el proveedor retira un modelo, la
mitigación debe ser cambiar una env var, no desplegar código. Precedente:
Bug 106 — `gemini-3-flash-preview` retirado por Google con 6 de 9 call sites
hardcodeados, así que la env var de Railway no servía de nada.

**Y comprobar un id de modelo es LLAMARLO, no leerlo.** Que el nombre esté en
`config.py` y coincida con la lista de la consola del proveedor no prueba nada:

```bash
cd backend && python -c "
from groq import Groq; from app.config import settings
c = Groq(api_key=settings.GROQ_API_KEY)
for m in (settings.GROQ_MODEL, settings.GROQ_MODEL_ROUTER,
          settings.GROQ_MODEL_SAFETY, settings.GROQ_MODEL_PROMPT_GUARD):
    try:
        c.chat.completions.create(model=m, messages=[{'role':'user','content':'hola'}], max_tokens=1)
        print('OK  ', m)
    except Exception as e:
        print('FALLA', m, str(e)[:90])
"
```

Distinguir los códigos: **404** = el modelo ya no existe (retirado). **403 con
`model_permission_blocked_org`** = existe pero hay que habilitarlo en la consola
del proveedor — ojo, esos aparecen igual en `models.list()`, así que estar en el
listado no significa poder usarlo.

Precedente: Bug 117 — `llama-3.1-8b-instant` retirado por Groq el 2026-08-16.
Se revisó la config, coincidía con la lista de activos, se dio por buena, y el
modelo llevaba seis días devolviendo 404 y tumbando el clasificador de temas
(que falla cerrado, o sea: chat rechazando TODO).

## Routers (`app/routers/`)

| Router | Prefix | Purpose |
|--------|--------|---------|
| `auth.py` | `/api/auth` | Login, register, refresh token, forgot-password, reset-password |
| `ask.py` | `/api/ask` | Main SSE chat endpoint |
| `fiscal_profile.py` | `/api/fiscal-profile` | User fiscal profile CRUD |
| `workspaces.py` | `/api/workspaces` | Workspace + file management |
| `reports.py` | `/api/reports` | PDF report generation + sharing |
| `export.py` | `/api/export` | PDF export + email to advisor |
| `subscriptions.py` | `/api/subscriptions` | Stripe checkout + portal |
| `admin.py` | `/api/admin` | Owner-only user admin |
| `irpf_estimate.py` | `/api/irpf` | Lightweight POST /api/irpf/estimate (no LLM, ~50-100ms) + **NEW** POST /api/irpf/net-salary (net salary calculator, 5 regimes, 21 tests) |

## Tools (Function Calling) (`app/tools/`)

| Tool | File | Purpose |
|------|------|---------|
| `calculate_irpf` | `irpf_calculator_tool.py` | IRPF by income + CCAA. Fallback: DB → prev year |
| `calculate_autonomous_quota` | `autonomous_quota_tool.py` | Self-employed SS quotas 2025 |
| `search_tax_regulations` | `search_tool.py` | FTS5 + BM25 + web scraping fallback |
| `analyze_payslip` | `payslip_analysis_tool.py` | 13 regex patterns for Spanish payslips |
| `discover_deductions` | `deduction_discovery_tool.py` | 64 deductions (16 estatal + 48 territorial) |
| `simulate_irpf` | `irpf_simulator_tool.py` | Full simulation + auto-discover deductions. Phase 1+2 params: planes_pensiones, hipoteca_pre2013, maternidad, familia_numerosa, donativos, tributacion_conjunta, alquiler_pre2015, rentas_imputadas |
| `web_scraper` | `web_scraper_tool.py` | AEAT/BOE/SS scraping + CCAA normalization |
| `lookup_casilla` | `casilla_lookup_tool.py` | Busca casillas IRPF Modelo 100 por numero o descripcion (2064 casillas en BD) |
| `calculate_modelo_ipsi` | `modelo_ipsi_tool.py` | IPSI Ceuta/Melilla: 6 tipos (0.5%-10%), trimestral |
| `compare_joint_individual` | `joint_comparison_tool.py` | **NEW**: Comparativa tributacion conjunta vs individual. 4 escenarios |
| `iae_lookup` | `iae_lookup_tool.py` | **NEW**: Lookup codigo IAE para creadores (8690, 9020, 6010.1, etc.) |

Tool registration: `app/tools/__init__.py` (ALL_TOOLS + TOOL_EXECUTORS)

## New Routers (Session 12)

| Router | Prefix | Purpose |
|--------|--------|---------|
| `feedback.py` | `/api/feedback` | **NEW**: Chat rating + feedback collection (owner-only retrieval) |

## Services (`app/services/`)

| Service | File | Purpose |
|---------|------|---------|
| WorkspaceService | `workspace_service.py` | Workspace CRUD with ownership checks |
| FileProcessingService | `file_processing_service.py` | PDF/Excel → structured data pipeline |
| InvoiceExtractor | `invoice_extractor.py` | 30+ regex patterns for Spanish invoices |
| WorkspaceEmbeddingService | `workspace_embedding_service.py` | OpenAI embeddings (3072 dim), Turso storage |
| DeductionService | `deduction_service.py` | get_all_deductions(ccaa), evaluate_eligibility. **IMPORTANTE**: territory names en BD usan nombre corto ("Madrid"), NO normalizado ("Comunidad de Madrid"). `build_answers_from_profile()` deriva automáticamente `menor_35/36/40_anos` desde `edad_contribuyente`. |
| ReportGenerator | `report_generator.py` | PDF ReportLab (IRPF report) |
| EmailService | `email_service.py` | Resend wrapper for advisor emails |
| RAGService | `rag_service.py` | Search + rerank orchestration |
| PayslipExtractor | `payslip_extractor.py` | PDF text extraction for payslips |
| **FeedbackService** | **`feedback_service.py`** | **NEW**: Feedback CRUD, rating aggregation, export (owner-only) |

## Database Schema (Turso SQLite)

```sql
-- Authentication
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT,
  is_admin BOOLEAN DEFAULT FALSE,
  is_owner BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  subscription_status TEXT DEFAULT 'none',
  subscription_plan TEXT DEFAULT 'particular',  -- 'particular', 'creator', 'autonomo'
  stripe_customer_id TEXT,
  grace_period_until TEXT,
  roles_adicionales TEXT,  -- JSON array: ['autonomo', 'creador', 'inversor'] (non-exclusive)
  created_at TIMESTAMP, updated_at TIMESTAMP
);

CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  refresh_token_hash TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP
);

CREATE TABLE user_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT UNIQUE REFERENCES users(id),
  ccaa_residencia TEXT,
  situacion_laboral TEXT,
  datos_fiscales TEXT,  -- JSON: autonomo fields + Phase 1 (planes_pensiones, hipoteca_pre2013_base, maternidad_hijos, familia_numerosa, donativos, retenciones_alquiler) + Phase 2 (tributacion_conjunta, alquiler_pre2015_base, rentas_imputadas_catastral, rentas_imputadas_tipo)
  created_at TIMESTAMP, updated_at TIMESTAMP
);

-- Conversations
CREATE TABLE conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  title TEXT,
  workspace_id TEXT REFERENCES workspaces(id),  -- nullable; per-client chat history (Modo Gestoría). Migrated in turso_client.py init_schema
  created_at TIMESTAMP, updated_at TIMESTAMP
);

CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id),
  role TEXT CHECK(role IN ('user','assistant','system')),
  content TEXT NOT NULL,
  metadata TEXT,  -- JSON: sources, tool calls
  created_at TIMESTAMP
);

-- RAG
CREATE TABLE documents (
  id TEXT PRIMARY KEY, filename TEXT NOT NULL,
  doc_type TEXT, source TEXT, processed_at TIMESTAMP
);

CREATE TABLE document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT REFERENCES documents(id),
  text TEXT NOT NULL, chunk_index INTEGER,
  section_id TEXT, metadata TEXT
);

CREATE TABLE embeddings (
  id TEXT PRIMARY KEY,
  chunk_id TEXT REFERENCES document_chunks(id),
  vector_hash TEXT, metadata TEXT
);

-- Payslips
CREATE TABLE payslips (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  filename TEXT NOT NULL,
  period_month INTEGER, period_year INTEGER,
  company_name TEXT,
  gross_salary REAL, net_salary REAL,
  irpf_withholding REAL, ss_contribution REAL,
  extraction_status TEXT, extracted_data TEXT,
  analysis_summary TEXT, created_at TIMESTAMP
);

-- IRPF scales
CREATE TABLE irpf_scales (
  id TEXT PRIMARY KEY,
  jurisdiction TEXT NOT NULL,  -- 'Estatal' or CCAA name
  year INTEGER NOT NULL,
  scale_type TEXT NOT NULL,    -- 'general'
  tramo_num INTEGER NOT NULL,
  base_hasta REAL, cuota_integra REAL,
  resto_base REAL, tipo_aplicable REAL
);

-- Deductions
CREATE TABLE deductions (
  id TEXT PRIMARY KEY,
  code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  category TEXT NOT NULL,
  scope TEXT DEFAULT 'estatal',  -- 'estatal' or 'territorial'
  ccaa TEXT,                     -- NULL for estatal
  max_amount REAL, percentage REAL,
  requirements TEXT,  -- JSON conditions
  tax_year INTEGER DEFAULT 2025,
  is_active BOOLEAN DEFAULT 1,
  questions TEXT,     -- JSON eligibility questions
  legal_reference TEXT
);

-- IRPF Casillas (Modelo 100 field dictionary)
CREATE TABLE irpf_casillas (
  id TEXT PRIMARY KEY,
  casilla_num TEXT NOT NULL,   -- Zero-padded 4 digits: '0505'
  description TEXT NOT NULL,
  xsd_path TEXT,
  section TEXT,
  source TEXT DEFAULT 'xsd',   -- 'xsd' or 'dlg'
  year INTEGER DEFAULT 2024
);
-- Indexes: idx_casillas_num, idx_casillas_desc
-- Seed: scripts/seed_casillas.py (parses diccionarioXSD_2024.properties)

-- Feedback (NEW)
CREATE TABLE feedback (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  conversation_id TEXT REFERENCES conversations(id),
  rating INTEGER CHECK(rating >= 1 AND rating <= 5),
  comment TEXT,
  metadata TEXT,  -- JSON: useful, clear, sources, etc.
  created_at TIMESTAMP
);
-- Indexes: idx_feedback_user, idx_feedback_created

-- Reports
CREATE TABLE reports (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL, report_type TEXT NOT NULL,
  title TEXT, report_data TEXT, pdf_bytes BLOB,
  share_token TEXT, shared_with_email TEXT, shared_at TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Workspaces
CREATE TABLE workspaces (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL, description TEXT,
  icon TEXT DEFAULT '📁',
  is_default BOOLEAN DEFAULT 0,
  max_files INTEGER DEFAULT 50, max_size_mb INTEGER DEFAULT 100,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE workspace_files (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, file_type TEXT NOT NULL,
  mime_type TEXT, file_size INTEGER,
  extracted_text TEXT, extracted_data TEXT,
  processing_status TEXT DEFAULT 'pending',
  error_message TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE workspace_file_embeddings (
  id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES workspace_files(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL, chunk_text TEXT NOT NULL,
  embedding_vector TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Metrics
CREATE TABLE usage_metrics (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  endpoint TEXT, tokens_used INTEGER,
  processing_time REAL, created_at TIMESTAMP
);
```

## Python Patterns

```python
# Async all I/O operations
async def my_function():
    result = await db.execute("SELECT ...", [param])

# Parameterized queries ALWAYS
await db.execute("SELECT * FROM users WHERE email = ?", [email])

# Error handling in routers
from fastapi import HTTPException
raise HTTPException(status_code=404, detail="Not found")

# Logging
import logging
logger = logging.getLogger(__name__)

# FK-safe inserts: ALWAYS validate foreign keys before INSERT
# Never let a FK constraint crash the user-facing response
chunk_ids = [s['id'] for s in sources]
result = await db.execute(f"SELECT id FROM parent_table WHERE id IN ({placeholders})", chunk_ids)
existing = {r['id'] for r in result.rows or []}
valid = [s for s in sources if s['id'] in existing]
```

### Tool LLM = wrapper del calculator (REGLA OBLIGATORIA)

> **NUNCA reimplementar logica numerica en `app/tools/modelo_*.py`.** El tool LLM
> debe limitarse a (1) validar inputs, (2) invocar el calculator canonico de
> `app/utils/calculators/`, (3) formatear la respuesta para el LLM, y (4) manejar
> `restricted_mode`. Si el calculator tiene un bug, **arreglar el calculator**, no
> el tool. Las casillas oficiales AEAT viven en el calculator.

Motivacion: el drift entre `modelo_303_tool.py` (reimplementado) y
`Modelo303Calculator` (testado) causo BUG-303-01..03 en produccion: casillas mal
numeradas (78 vs 71), `casilla_45` incompleta (5 sumandos en vez de 10), plazos
T4 erroneos. Auditoria: `docs/audits/modelo_303_validation_2026-05.md`.

```python
# OK — wrapper delegando al calculator
from app.utils.calculators.modelo_303 import Modelo303Calculator

async def calculate_modelo_303_tool(trimestre, base_21, ..., restricted_mode=False):
    if restricted_mode:
        return {"success": False, "error": "restricted", ...}
    if trimestre not in (1, 2, 3, 4):
        return {"success": False, "error": "trimestre invalido", ...}
    calc = Modelo303Calculator(None)
    result = await calc.calculate(base_21=base_21, quarter=trimestre, ...)
    formatted = _format_for_llm(result)  # solo presentacion
    return {"success": True, **map_keys(result), "formatted_response": formatted}

# NO — reimplementar la aritmetica en el tool (drift garantizado)
casilla_45 = casilla_29 + casilla_31 + casilla_33 + casilla_37 + casilla_41  # FALTAN 35,39,42,43,44
casilla_71 = compensacion_periodos_anteriores  # MAL: 71 es resultado, 78 es compensacion
```

Aplicable a: `modelo_303_tool.py`, `modelo_130_tool.py`, `modelo_308_tool.py`,
`modelo_309_tool.py`, `modelo_720_tool.py`, `modelo_721_tool.py`,
`modelo_ipsi_tool.py`, `is_simulator_tool.py` y futuros wrappers de modelos AEAT.

## Common Backend Tasks

**New endpoint**: Create `app/routers/my_feature.py` → `router = APIRouter(prefix="/api/my-feature")` → register in `main.py` with `app.include_router()`.

**New tool**: Create `app/tools/my_tool.py` with tool definition dict + async executor → register in `tools/__init__.py` (ALL_TOOLS + TOOL_EXECUTORS) → add to agent tools list.

**New table**: Add `CREATE TABLE IF NOT EXISTS` in `database/turso_client.py:init_schema()`.

**New env var**: Add to `config.py` Settings class + `.env.example`.

**Seed data**: Create `scripts/seed_*.py` (use TursoClient, idempotent: DELETE existing + INSERT).

## Testing

```bash
pytest tests/ -v                    # All tests
pytest tests/test_auth.py -v        # Specific module
pytest tests/ --cov=app             # With coverage
```

Key test files: `test_agents.py`, `test_api.py`, `test_auth.py`, `test_ai_security.py`, `test_deductions.py`, `test_export.py`, `test_ceuta_melilla.py`, `test_subscription.py`, `test_modelo_ipsi.py`, `test_casilla_lookup.py`

Fixtures in `conftest.py`: `mock_db`, `auth_token`, `mock_openai_response`, `test_user`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `TokenData has no attribute 'get'` | Use `current_user.user_id` not `.get("user_id")` |
| `FOREIGN KEY constraint failed` en message_sources | `add_message_sources()` debe validar que chunk_ids existen en `document_chunks` antes de INSERT. Filtrar sources con id NULL y verificar existencia con SELECT previo. NUNCA romper la respuesta del agente por sources inválidas — degradar gracefully. |
| Agente asume que usuario es autónomo | Verificar que `_build_prompt()` recibe `fiscal_profile` y que el system prompt tiene reglas de clarificación obligatoria. `situacion_laboral` debe inyectarse de forma prominente en el contexto. |
| Escala estatal no encontrada | Run `python scripts/seed_estatal_scale.py` |
| Casillas IRPF vacías | Run `python scripts/seed_casillas.py` (2064 casillas from AEAT .properties) |
| `irpf_casillas` table not found | El seed script crea la tabla automáticamente. También está en `turso_client.py:init_schema()` |
| Semantic cache disabled | Check `UPSTASH_VECTOR_REST_URL` + `TOKEN` env vars |
| SSE buffering on Railway | Use `print(flush=True)` in streaming code |
| Railway: `Healthcheck failed! 1/1 replicas never became healthy` + `service unavailable` | Comprobar EN ESTE ORDEN: (1) qué fichero de config aplica a ese servicio (ver fila siguiente); (2) el `startCommand` efectivo — con builder DOCKERFILE va en exec form y NO expande `$PORT`; (3) `healthcheckTimeout` frente al arranque real. Y pedir los **Deploy Logs**, no los Build Logs: el build puede salir verde y el contenedor morir igual. Bugs 110-112. |
| ¿Qué `railway.toml` lee cada servicio? | Monorepo: la ruta del config es un ajuste **por servicio** y no sigue al Root Directory — doc oficial: *"The Railway Config File does not follow the Root Directory path"*. Aquí: `railway.toml` de la RAÍZ → servicio **frontend**; `backend/railway.toml` → servicio **backend**. Editar el de la raíz creyendo que es del backend tumbó los dos servicios el 2026-08-10. Bug 111. |
| `startCommand` con `$PORT` mata el proceso al arrancar | Doc oficial: *"the start command overrides the image's ENTRYPOINT in exec form"* y *"commands ran in exec form do not support variable expansion"*. Con builder DOCKERFILE, `--port $PORT` llega literal → `Invalid value for '--port'` y el proceso muere antes de importar la app. Envolverlo: `/bin/sh -c "exec uvicorn ... --port ${PORT:-8000} ..."`, o borrar el `startCommand` y dejar el `CMD` (que ya es forma shell). Con Railpack no pasaba: ahí el start command corre en shell. Bug 111. |
| ¿Manda el `CMD` del Dockerfile o el `startCommand`? | El **build** lo gana el Dockerfile; el **arranque** lo gana el `startCommand` de `backend/railway.toml` si existe. Hoy hay comando de arranque en 2 sitios (`backend/railway.toml` y el `CMD`), idénticos a propósito porque Coolify solo lee el `CMD`. Si tocas uno, sincroniza el otro. |
| Deploy marcado fallido aunque la app levante bien | `healthcheckTimeout` demasiado bajo. Arranque real: ~10 s de imports (`agent_framework` + routers) + `init_schema` contra Turso remoto (~79 statements CREATE/ALTER, cada uno con su `commit()`). Usar 300 (el default de Railway), no 30. NO hay modelos de embeddings locales: van por API. Bug 110. |
| El arranque se vuelve lento "sin tocar nada" | Dependencia con rango abierto que se actualizó sola. Precedente: `pymupdf4llm>=0.2.6` saltó a 1.28.2 (release del 2026-08-06), que arrastra `pymupdf_layout` + `onnxruntime` y **construye sesiones ONNX en el import** (+112 MB RSS). Lo paga cada arranque porque `notification_agent.py` hace `import pymupdf4llm` a nivel de módulo. Pin exacto para todo lo que se importe en el camino de arranque. Bug 112. |
| `import fitz` fails | `pip install PyMuPDF pymupdf4llm` |
| Tests import errors | Mock jose/bcrypt/slowapi (chain __init__.py imports) |
| Rate limit 429 on login/register during dev | Increase `RATE_LIMIT_PER_MINUTE` or clear Redis. Login/register are now hard-limited at 5/min, forgot-password at 3/min. |
| slowapi crash: `parameter 'request' must be an instance of starlette.requests.Request` | El primer parametro del endpoint DEBE llamarse `request: Request`. Si hay body Pydantic, nombrarlo `body` o `data`, NUNCA `request`. Ejemplo: `async def my_endpoint(request: Request, body: MyModel)` |
| CORS errors | Check `ALLOWED_ORIGINS` includes frontend URL |
| Checkout spinner infinito (backend) | `create_stripe_customer()` retornaba NULL si row existía con `stripe_customer_id = NULL` (beta/grace users). NUNCA retornar None en servicios que el frontend espera un valor — siempre raise ValueError. |
| Subscribe page spinner infinito (frontend) | `useSubscription.fetchStatus()` retornaba sin `setLoading(false)` cuando `!isAuthenticated`. En hooks async con loading state, TODA rama debe resetear loading. |
| `h11 LocalProtocolError: Illegal header value` | CSP header en `main.py` NO debe tener trailing space/semicolon en el ultimo directive. Cambiar `"frame-ancestors 'none'; "` a `"frame-ancestors 'none'"` |
| `UnicodeEncodeError: charmap codec` en Windows | Ejecutar con `PYTHONUTF8=1` env var. Los print() con emojis crashean en cp1252. |
| Usuarios de test QA | Run `python scripts/seed_test_users.py`. Crea particular (Madrid) + autonomo (Cataluna) con suscripcion active. |
| Deducciones CCAA 0 resultados | `normalize_ccaa_name()` convierte "Madrid"→"Comunidad de Madrid" pero BD deductions usa territory="Madrid". Usar nombre corto (sin normalizar) para deduction lookups, normalizado solo para escalas IRPF. Ver `ccaa_for_deductions` en `irpf_estimate.py`. |
| `menor_XX_anos` nunca True en deducciones | `build_answers_from_profile()` no derivaba age keys. Asegurar que `edad_contribuyente` se pasa en el profile dict y que el bloque de derivación edad→`menor_35/36/40_anos` existe en `deduction_service.py`. |
| DynamicFiscalForm valores no llegan al estimate | DynamicFiscalForm guarda en `dynamicFormValues` (state separado), no en `data` del wizard. Al construir el payload del estimate, añadir fallbacks: `data.campo || dynamicFormValues.campo_ccaa || 0`. |
| `No scale found for Cataluna` | Falta `"cataluna"` (sin tilde ñ) en `CCAA_NORMALIZATION` de `web_scraper_tool.py`. Frontend envía nombres sin acentos. Siempre incluir variantes sin tilde de TODAS las CCAA. |
| `No territory plugin registered for 'Aragón'` | `COMUN_TERRITORIES` usaba nombres sin tildes. SIEMPRE usar canonical de `ccaa_constants.py` (con tildes). `get_territory()` tiene fallback `normalize_ccaa()` como safety net. |
| `Child process died` sin traceback (RAG) | OOM killer de Railway. Cada worker usa ~344 MB. Con workers > 1 se supera el limite. Solucion: `--workers 1` en `railway.toml`. Diagnosticar con `resource.getrusage()`. |
| Upstash Vector bloquea event loop | `Index.query()` es sincrono. Usar `asyncio.to_thread(self._vector_index.query, ...)` en funciones async. |
| Trust scoring OOM con muchos chunks | No usar `asyncio.gather` para N queries a Turso — hacerlas secuenciales en `_apply_trust_scoring()`. |
| Topic classifier bloquea preguntas legítimas con workspace adjunto | El classifier solo veía el texto crudo y rechazaba ambiguas como "evalúa si esto es correcto". Solución (sesión 38): pasar `TopicContext` (workspace name + recent turns) al pipeline vía `security_pipeline.check(..., context=ctx)`. System prompt en `topic_classifier.py` tiene regla "ambigua + ctx fiscal → fiscal=true; off-scope explícito ignora ctx". Cache LRU rekeyed con `(question_hash, ctx_hash)`. |
| Token budget / velocity check fail-open silencioso | `token_budget.check/record` y `velocity_checker.check` son `async def`. Cliente `AsyncRedis` requiere `await`. Usar `await tracker.check(...)` en TODOS los call sites. Tests: dual sync/async via `if hasattr(x, "__await__"): x = await x`. |
| PII detector revienta con 413/429 Groq | `pii_detector.detect()` con length guard 3000 chars (>3k → `_regex_only` con `self.PII_PATTERNS`). LRU per-instance dict. Retry sync 1× en 429 con `time.sleep(0.5)`. Mantiene firma sync — NO convertir a async (rompe pipeline). |
| Migración `duplicate column` ruidosa al startup | Usar `_column_exists(table, col)` con `PRAGMA table_info` ANTES del `ALTER TABLE ... ADD COLUMN`, en lugar de try/except. El driver Hrana loguea el error antes de Python lo capture. Regex `_ALTER_ADD_COL_RE` parsea statements. |
| PII no detectada aunque el texto lleve DNI/IBAN | El regex determinista debe correr SIEMPRE y PRIMERO en `pii_detector.detect()`. Groq es demasiado permisivo en contexto fiscal ("mi DNI es 12345…" lo daba por seguro). Union de detectores: si cualquiera marca PII, se rechaza. Bug 105. |
| Una consulta legitima se rechaza como PII | Mirar si el texto pasa de 3000 chars: ahi `detect()` salta el LLM (`_REGEX_FALLBACK_THRESHOLD`, para evitar el 413 de Groq) y el regex decide SOLO. `_HIGH_CONFIDENCE_PII` no protege ese camino — solo limita el override. Un patron ambiguo ahi bloquea de verdad. Bug 114. |
| `if not self.client` en `_detect_uncached()` parece fail-open | NO lo es, y no lo "arregles" llamando a `_regex_only()`. Devuelve `has_pii=False`, y entonces `detect()` corre el regex por su cuenta dejando mandar a `_HIGH_CONFIDENCE_PII`: sin Groq, DNI/NIE/IBAN/email/telefono/CIF se siguen cazando. Degradar ahi haria contar TODOS los patrones y los ambiguos pasarian a bloquear. Hay test que lo fija. |
| Gemini devuelve 404 / OCR de facturas roto | El id de modelo estaba hardcodeado en 6 call sites. Usar `settings.GEMINI_MODEL` (default `gemini-2.5-flash-lite`). `gemini-3-flash-preview` fue retirado por Google. Bug 106. |
| Rate limit se resetea al volver a hacer login | `get_rate_limit_key()` hasheaba el token (`md5(Authorization)`), así que cada token nuevo = contador nuevo. Debe decodificar el JWT y keyear por el claim `sub`. Fallback a IP, con `except` amplio: una excepción en la key function hace que slowapi devuelva 500. Bug 107. |
| DefensIA cuelga / responde en blanco | gpt-5-mini gasta todo el presupuesto en razonamiento oculto y emite 0 chunks. Requiere `reasoning_effort="minimal"` + `max_completion_tokens=10000` + `asyncio.wait_for` 60s. Añadir fallback si `content_chunks == 0` para no dejar la UI vacía. Bug 108. |
