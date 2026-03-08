# backend/CLAUDE.md — Backend Guide

## Stack & Setup

Python 3.12+ | FastAPI 0.104+ | Microsoft Agent Framework 1.0.0b | OpenAI API | Groq API (LlamaGuard4)

```bash
cd backend && pip install -r requirements.txt
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd backend && pytest tests/ -v --tb=short
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
| `FRONTEND_URL` | Base URL for reset-password link (default: https://impuestify.es) |

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
| `irpf_estimate.py` | `/api/irpf` | **NEW**: Lightweight POST /api/irpf/estimate (no LLM, ~50-100ms) |

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

Tool registration: `app/tools/__init__.py` (ALL_TOOLS + TOOL_EXECUTORS)

## Services (`app/services/`)

| Service | File | Purpose |
|---------|------|---------|
| WorkspaceService | `workspace_service.py` | Workspace CRUD with ownership checks |
| FileProcessingService | `file_processing_service.py` | PDF/Excel → structured data pipeline |
| InvoiceExtractor | `invoice_extractor.py` | 30+ regex patterns for Spanish invoices |
| WorkspaceEmbeddingService | `workspace_embedding_service.py` | OpenAI embeddings (3072 dim), Turso storage |
| DeductionService | `deduction_service.py` | get_all_deductions(ccaa), evaluate_eligibility |
| ReportGenerator | `report_generator.py` | PDF ReportLab (IRPF report) |
| EmailService | `email_service.py` | Resend wrapper for advisor emails |
| RAGService | `rag_service.py` | Search + rerank orchestration |
| PayslipExtractor | `payslip_extractor.py` | PDF text extraction for payslips |

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
  subscription_plan TEXT DEFAULT 'particular',
  stripe_customer_id TEXT,
  grace_period_until TEXT,
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
| `import fitz` fails | `pip install PyMuPDF pymupdf4llm` |
| Tests import errors | Mock jose/bcrypt/slowapi (chain __init__.py imports) |
| Rate limit 429 on login/register during dev | Increase `RATE_LIMIT_PER_MINUTE` or clear Redis. Login/register are now hard-limited at 5/min, forgot-password at 3/min. |
| CORS errors | Check `ALLOWED_ORIGINS` includes frontend URL |
| `h11 LocalProtocolError: Illegal header value` | CSP header en `main.py` NO debe tener trailing space/semicolon en el ultimo directive. Cambiar `"frame-ancestors 'none'; "` a `"frame-ancestors 'none'"` |
| `UnicodeEncodeError: charmap codec` en Windows | Ejecutar con `PYTHONUTF8=1` env var. Los print() con emojis crashean en cp1252. |
| Usuarios de test QA | Run `python scripts/seed_test_users.py`. Crea particular (Madrid) + autonomo (Cataluna) con suscripcion active. |
