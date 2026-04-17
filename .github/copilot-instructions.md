# Copilot Code Review — Impuestify (TaxIA)

Spanish tax assistant: FastAPI backend + React 18 frontend. Multi-agent RAG architecture.

## Architecture Rules

- Backend: Python 3.12+, FastAPI, Turso (SQLite via libsql). Agents use Microsoft Agent Framework.
- Frontend: React 18 + Vite + TypeScript. Custom CSS (NO Tailwind). Icons: Lucide React.
- `useApi()` hook returns `apiRequest(path)` with baseURL `/api`. Paths must NOT include `/api/` prefix (causes double `/api/api/`). Exception: hooks using raw `fetch`/`XHR` use `API_URL` which is already `/api`.
- DefensIA router uses prefix `/api/defensia`. Vite proxy has specific pass-through rule for it.

## Security (Critical — flag violations)

- SQL: ALWAYS parameterized queries (`WHERE email = ?`). NEVER f-strings with user data.
- Auth: Protected endpoints MUST use `Depends(get_current_user)`. `get_current_user()` returns `TokenData` — use `.user_id`, `.email`, NEVER `.get("user_id")`.
- File uploads: validate magic numbers + size limits. iOS Safari: NEVER `display:none` on `<input type="file">`, use `position:absolute; opacity:0; clip:rect(0,0,0,0)` + `<label htmlFor>`.
- Rate limiting (slowapi): first param MUST be `request: Request`, body Pydantic as `body`/`data`.
- Startup: NEVER crash on missing secrets — warning only. App must always start.
- NEVER log passwords, tokens, or PII.

## Spanish Text (Flag missing tildes)

All user-visible strings MUST have correct Spanish tildes. Common words: sesión, régimen, declaración, liquidación, sanción, información, descripción, clasificación, código, análisis, resolución, notificación, atención. Uppercase words ALSO carry tildes (RAE rule): ATENCIÓN not ATENCION.

Variables/keys (data.regimen, contrasena) are exempt — only strings between quotes shown to users.

## Testing Patterns

- Backend: pytest, async tests with `@pytest.mark.asyncio`. Fixtures in conftest.py.
- Frontend: Vitest + @testing-library/react + jsdom. EscritoEditor uses Tiptap (ProseMirror teardown error is known, not a failure).
- Loading state: EVERY async branch must call `setLoading(false)` — including early returns and error paths. A loading that never resets = infinite spinner.

## DefensIA Module

- Anti-hallucination invariant: Jinja2 templates (.j2) must NEVER hardcode legal citations (Art. X, STS, Ley N/YYYY). All citations come from `arg.cita_verificada` or `arg.referencia_normativa_canonica` via RAG verifier.
- Rule decorator `descripcion` field must NOT contain explicit article references (could surface in UI). Use semantic descriptions only.
- Phase detector must NOT mutate input `expediente.documentos` — use sorted() with key function.
- Storage: `DefensiaStorageUnavailable` → HTTP 503 (never crash app).
- GDPR cascade: explicit DELETE of 7 defensia_* tables in user_rights.py (defense-in-depth).

## IS/Modelo 200 Module

- Scales in `is_scales.py`, simulator in `is_simulator.py`. Never hardcode tax rates in simulator.
- 7 territories: comun (25%), Álava/Bizkaia/Gipuzkoa (24%), Navarra (28%), ZEC (4%), Ceuta/Melilla (25% + 50% bonif).
- Pyme: facturación <1M → first 50k at reduced rate.

## Common Bugs to Watch

- Double `/api/api/` prefix in frontend hooks using `apiRequest`.
- `loop.index0` in Jinja2 templates (renders "0 bis.—"). Use `loop.index` for 1-based numbering.
- Turso client: `dict(row)['field']` not `row[0]` (rows are Row objects, not tuples).
- `datetime.utcnow()` deprecated — use `datetime.now(timezone.utc)`.
- LLM model: ALWAYS `gpt-5-mini`, NEVER `gpt-4o-mini`.
