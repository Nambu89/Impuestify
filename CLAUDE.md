# CLAUDE.md — TaxIA (Impuestify)

> **CRITICAL:** Before starting any complex task, check if `task.md` or `implementation_plan.md` exist. They are the source of truth for current objectives.

## Project Overview

TaxIA (Impuestify) is a Spanish tax assistant using RAG + multi-agent architecture (FastAPI + React). Provides IRPF calculation, deduction discovery, payslip analysis, AEAT notification parsing, adaptive tax guides by role (Particular/Creator/Autonomo), and net salary calculator (/calculadora-neto) for autonomous workers across 5 fiscal regimes (Madrid, Andalucía, Canarias, Melilla, País Vasco). Covers all 17 CCAA + 4 foral territories + Ceuta/Melilla.

## Request Flow

**Chat:** User → React frontend → FastAPI `/api/ask/stream` → JWT auth → Rate limiting → Guardrails (LlamaGuard4, prompt injection, PII) → Semantic cache → CoordinatorAgent → [TaxAgent|PayslipAgent|NotificationAgent|WorkspaceAgent] → Tools + RAG → OpenAI GPT → SSE response

**Tax Guide (no LLM):** User → `/guia-fiscal` wizard (adaptive: 7 steps for Particular, 8 for Creator/Autonomo) → POST `/api/irpf/estimate` → `irpf_simulator.py` → JSON response (~50-100ms, no LLM, no auth required for estimate)

**Net Salary Calculator (no LLM):** Self-employed → `/calculadora-neto` → POST `/api/irpf/net-salary` → Backend calculates net monthly/annual salary (5 fiscal regimes: Madrid, Andalucía, Canarias, Melilla, País Vasco) → JSON with gross, IVA, IRPF, SS, net breakdown (~100ms)

## Directory Layout

```
TaxIA/
├── backend/         # FastAPI Python 3.12+ (see backend/CLAUDE.md)
├── frontend/        # React 18 + Vite + TS (see frontend/CLAUDE.md)
├── docs/            # 439+ RAG documents (PDFs + Excel) by territory
├── data/            # FAISS embeddings, knowledge_updates/
├── .claude/
│   ├── commands/    # 14+ slash commands
│   ├── skills/      # Domain knowledge modules
│   └── subagents/   # 6+ agent personas
├── agent-comms.md   # Inter-agent communication log
├── memory/          # Persistent agent memory (MEMORY.md index)
├── plans/           # Roadmap, implementation plans, drift reports
└── .env             # Environment variables (root)
```

## Deep-Dive References

- **Backend**: `backend/CLAUDE.md` — agents, tools, DB schema, security, testing, troubleshooting
- **Frontend**: `frontend/CLAUDE.md` — hooks, components, SSE format, PWA, React Bits
- **Skills**: `.claude/skills/` — IRPF, SSE, Turso, Security, Stripe, Railway
- **Agent memory**: `memory/MEMORY.md` — index of all topic files

## Naming Conventions

| Context | Style | Example |
|---------|-------|---------|
| Python files | `snake_case.py` | `irpf_calculator_tool.py` |
| TS components | `PascalCase.tsx` | `DeductionCards.tsx` |
| TS hooks/utils | `camelCase.ts` | `useStreamingChat.ts` |
| Python vars/funcs | `snake_case` | `base_imponible` |
| TS vars/funcs | `camelCase` | `sendMessage` |
| Constants | `UPPER_SNAKE` | `MAX_TOKENS` |
| Classes | `PascalCase` | `CoordinatorAgent` |

## Despliegue: DOS ramas, DOS productos (OBLIGATORIO)

| Rama | Despliegue | Producto |
|---|---|---|
| `main` | Railway (frontend + backend) | **Impuestify** |
| `demo/fiscal-ia-melilla` | Coolify, VPS Contabo | **Demo Fiscal IA Melilla** (`iamelilla.com`) |

**Mergear a `main` NO llega a la demo.** Coolify despliega la rama demo.

### REGLA DURA: si tocamos la demo de Melilla, fast-forward SIEMPRE

No preguntar ni esperar a que lo pidan. Si la sesión toca la demo, la rama se
pone al día — al empezar, y otra vez cada vez que se mergee algo de backend a
`main` durante esa sesión.

```bash
git fetch origin
# Debe ser ff PURO: la rama demo no debe tener commits propios
git merge-base --is-ancestor origin/demo/fiscal-ia-melilla origin/main
git rev-list --count origin/main..origin/demo/fiscal-ia-melilla   # debe dar 0
git push origin origin/main:refs/heads/demo/fiscal-ia-melilla
```

Después, **comprobar el commit en el log de Coolify**: `Importing ... (commit
sha ...)` debe coincidir con el `main` recién mergeado. Si no coincide, falta el
ff — no es que "Coolify despliegue código viejo".

Si la rama demo tuviera commits propios, **parar y auditar**: es el escenario que
dejó bugs vivos tres meses (backport de agosto de 2026).

Precedente: el 2026-08-22/23 se arreglaron tres bugs críticos en `main` (117, 119
y 120) y ninguno llegó a la demo, que siguió desplegando `f8c8c96` toda la tarde.

## Git Workflow

- Branch convention: `claude/<descriptor>` for AI-assisted work
- Commit format: `<type>: <description>` (feat/fix/docs/style/refactor/test/chore)
- Main branch: `main`
- Always `npm run build` (frontend) before committing
- Run `pytest tests/ -v` (backend) before pushing

## Security Non-Negotiables

1. **Always** parameterized queries: `WHERE email = ?`, never f-strings
2. **Always** `Depends(get_current_user)` for protected endpoints
3. **Never** log passwords, tokens, or PII
4. **Always** validate file uploads (magic numbers + size limits)
5. **Always** rate-limit expensive endpoints (LLM calls, PDF processing)
6. Owner-only endpoints: check `current_user.is_owner`
7. **ORTOGRAFIA PRE-PUSH OBLIGATORIA**: Verify tildes on ALL user-visible strings before pushing
8. **JWT_SECRET_KEY must be changed** on Railway (user action required — currently default)

## Code Review Checklist

- [ ] Naming conventions followed (PEP 8 / ESLint)
- [ ] Tests pass (`pytest` + `npm run build`)
- [ ] No sensitive data in logs
- [ ] Error handling present
- [ ] Type hints (Python) / interfaces (TypeScript)
- [ ] New env vars added to `.env.example`
- [ ] Security considerations addressed

## Squad de agentes (OBLIGATORIO delegar)

Los agentes viven en `.claude/agents/*.md` y **no dependen de ninguna herramienta
externa** (RuFlo se retiró el 2026-08-23 y no se perdió ninguno).

### REGLA DURA: el asistente principal es PM. NO toca código.

Quien lleva la conversación actúa como **Project Manager**: entiende el
problema, lo diagnostica, redacta el encargo y verifica el resultado.
**No edita ficheros de código.** Eso lo hace el agente del dominio.

Lo que SÍ hace el PM:
- Investigar y diagnosticar (leer código, logs, docs oficiales, reproducir).
- Decidir qué hay que hacer y por qué.
- Redactar el encargo con contexto suficiente para que el agente no tenga que
  redescubrirlo.
- Revisar lo que devuelve el agente y aceptarlo o devolverlo.
- Escribir documentación, memoria y `agent-comms.md`.

Lo que NO hace el PM: `Edit`/`Write` sobre `backend/`, `frontend/`, `scripts/`
ni tests. Si se ve escribiendo código, **parar y delegar**.

Excepción única: que Fernando lo pida explícitamente ("hazlo tú", "cámbiame esta
línea").

**Por qué**: cada agente arranca con contexto limpio. En la sesión del
2026-08-22/23 el PM resolvió ~20 tareas sin invocar ni un subagente, y los
errores que cometió son exactamente los de contexto saturado: dar por buenos los
modelos de Groq sin llamarlos, "arreglar" un fail-open que no existía, inventarse
los nombres de los flags en un test. Delegar no es ceremonia: es higiene.

| Tarea | Agente | Tipo |
|---|---|---|
| Bug o feature de backend, FastAPI, Turso | `backend-architect` | proyecto |
| Python puro: debugging, async, optimización | `python-pro` | proyecto |
| React, TS, Vite, UX, PWA | `frontend-dev` | proyecto |
| Probar como usuario real (Playwright) | `qa-tester` | proyecto |
| Verificar un plan ANTES de ejecutarlo | `plan-checker` | proyecto |
| Verificar la implementación DESPUÉS | `verifier` | proyecto |
| Documentación, auditoría de docs | `doc-auditor` | proyecto |
| Descargar normativa oficial (AEAT/BOE) | `doc-crawler` | proyecto |
| Roadmap, decisiones, delegación | `pm-coordinator` | proyecto |
| Análisis de competencia | `competitive-intel` | proyecto |
| **Tests: escribirlos o ampliarlos** | `tester` / `tdd-london-swarm` | built-in |
| **PRs: revisión, merge, ciclo de vida** | `pr-manager` | built-in |
| **Issues de GitHub, triaje** | `issue-tracker` | built-in |
| **Releases y versionado** | `release-manager` | built-in |
| **Revisión de código adversarial** | `reviewer` / `code-review-swarm` | built-in |
| Auditoría de seguridad | `security-auditor` | built-in |
| Búsqueda amplia en el repo | `Explore` | built-in |

Los marcados **built-in** no tienen fichero en `.claude/agents/` — se invocan por
nombre igual, con `subagent_type`.

Cuándo NO delegar: una pregunta conversacional, un cambio de una línea ya
localizado, o cuando el usuario pide explícitamente que lo haga yo.

### REGLA DURA: toda modificación de código pasa por Codex

Antes de empujar cualquier cambio de código del proyecto (`backend/`,
`frontend/`, `scripts/`, tests, workflows), pasarlo por Codex para una segunda
opinión. No hace falta para documentación ni memoria.

```powershell
codex exec --sandbox read-only -C "<ruta del repo>" $prompt
```

- `--sandbox read-only` siempre: revisa, no toca.
- El prompt **sin comillas dobles dentro** y con `-C <ruta>` explícito —
  PowerShell 5.1 rompe el paso de argumentos a ejecutables nativos si las lleva.
- Pedirle que responda **solo con fallos concretos**, y que lo diga en una línea
  si no hay ninguno.
- Pedirle también qué **falta**, no solo qué sobra: un arreglo de seguridad puede
  fallar por quedarse corto.
- Si tras aplicar sus hallazgos el cambio quedó materialmente distinto, **volver
  a pasarlo**. El 2026-08-23 hicieron falta tres rondas sobre el mismo fichero.
- Verificar sus hallazgos, no aceptarlos a ciegas: ese día uno era falso ("hace
  falta vite 8") y se descartó con datos — el rango vulnerable acababa en 6.4.2.

Precedente: Codex entró en 5 revisiones y encontró **12 hallazgos reales**. Dos
cambiaron la solución de raíz — que `c.p.` es *corto plazo* en contabilidad, y
que los patrones de SQLi eran cobertura aparente (8 de 9 evasiones triviales los
esquivaban).

### Memoria y aislamiento (configurado el 2026-08-23)

**Memoria propia por agente**: los 10 llevan `memory: project`, que les da
`.claude/agent-memory/<nombre>/` — persiste entre sesiones y es versionable, así
que el conocimiento que acumula cada uno se comparte con el equipo por git. No
confundir con la memoria del PM (`memory/` + `MEMORY.md`), que es otra cosa.

**Aislamiento por worktree**: solo en `backend-architect`, `python-pro` y
`frontend-dev`. Les da una copia aislada del repo, para que dos agentes que
escriben código a la vez no se pisen; la copia se descarta sola si no hay
cambios.

Deliberadamente **sin** worktree:

| Agente | Por qué |
|---|---|
| `doc-auditor`, `doc-crawler`, `competitive-intel` | sus ficheros deben aterrizar en el checkout real, no en una copia |
| `qa-tester` | Playwright depende de las rutas y la config del repo real |
| `plan-checker`, `verifier` | son de solo lectura, no hay nada que aislar |
| `pm-coordinator` | por la regla de arriba, el PM no escribe código |

El worktree cuesta ~200-500 ms y disco por agente, así que solo compensa donde
hay riesgo real de conflicto.

### Coordinación entre agentes

Disponible **sin activar nada**: `SendMessage` permite que un agente con nombre
mensajee a otro, y cada agente recibe al arrancar la lista de sus hermanos.

**Agent teams** (pizarra de tareas compartida, dependencias entre tareas, buzón,
*file locking* al reclamar trabajo) requiere
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. **NO está activado**: es experimental,
cuesta bastantes más tokens, `/resume` no restaura compañeros, y en Windows
Terminal solo funciona el modo *in-process* (los paneles divididos necesitan tmux
o iTerm2). Activarlo para un caso concreto que se beneficie del paralelismo, no
como modo permanente.

## Quality Gates (OBLIGATORIO)

Todo plan de implementacion debe pasar por quality gates automaticos:

### Pre-ejecucion: Plan Checker
**ANTES** de presentar cualquier plan al usuario para aprobacion, ejecutar el agente `plan-checker`:
1. Escribir el plan en `plans/` o `implementation_plan.md`
2. Invocar `/check-plan` (o spawn subagente plan-checker)
3. Si resultado es `ISSUES_FOUND`: corregir el plan y re-verificar
4. Solo presentar al usuario planes que hayan pasado con `PASS`

Aplica a: planes de implementacion, planes RPI, planes de refactoring, cualquier plan con >3 tareas.

### Post-ejecucion: Verifier
**DESPUES** de implementar TODAS las tareas de un plan, ejecutar el agente `verifier`:
1. Completar todas las tareas del plan
2. Invocar `/verify` (o spawn subagente verifier)
3. Si resultado es `ISSUES_FOUND`: corregir los issues y re-verificar
4. Solo reportar "plan completado" al usuario cuando verifier pase con `VERIFIED`

Aplica a: cualquier implementacion que involucre >2 archivos o >2 tareas.

### Flujo completo
```
Plan → /check-plan (PASS?) → Presentar al usuario → Aprobacion → Implementar → /verify (VERIFIED?) → Reportar completado
```

## Code Quality Tooling

| Layer | Tool | Run |
|-------|------|-----|
| Backend lint | ruff | `cd backend && ruff check .` |
| Backend format | ruff format | `cd backend && ruff format .` |
| Backend tests | pytest | `cd backend && pytest tests/ -q` |
| Frontend lint | eslint v9 | `cd frontend && npm run lint` |
| Frontend format | prettier | `cd frontend && npm run format` |
| Frontend typecheck | tsc --noEmit | `cd frontend && npm run typecheck` |
| Frontend build | vite | `cd frontend && npm run build` |
| Pre-commit (all) | pre-commit | `pre-commit run --all-files` |

**Install dev tooling once per machine:**

```bash
cd backend && pip install -r requirements-dev.txt
pre-commit install
```

**CI runs all checks on every PR** (`.github/workflows/ci.yml`, 5 parallel jobs). Bypass pre-commit ONLY for emergency commits: `git commit --no-verify` — but CI will still report. Baseline tolerances (Phase 1):
- Backend ruff: `--exit-zero` for 179 pre-existing violations (cleanup: issue #15)
- Frontend eslint: `--max-warnings 256` for **243** warnings (medido 2026-08-23; el 234 anterior estaba desactualizado). Cleanup: issue #14
- Frontend typecheck: soft-fail for ~30 pre-existing TS errors (cleanup: issue #15)

## Post-Bugfix Protocol (OBLIGATORIO)

Después de arreglar cualquier bug, SIEMPRE documentar en estos 3 sitios:

1. **`backend/CLAUDE.md` o `frontend/CLAUDE.md`** (según corresponda):
   - Añadir regla/patrón en la sección relevante para prevenir recurrencia
   - Añadir entrada en Troubleshooting con el error y la solución
2. **`memory/bugfixes-YYYY-MM.md`**: Detalle técnico del bug, causa raíz, archivos modificados y cambios realizados
3. **`agent-comms.md`**: Registrar la tarea como DONE y si genera trabajo pendiente para otro agente

El objetivo es que ningún agente futuro repita el mismo error. Si el bug revela un anti-patrón (ej: "no preguntes en exceso" causó que el agente no clarificara datos clave), documentar el anti-patrón y su corrección como regla permanente.

## Subscription Plans (Updated 2026-03-17)

| Plan | Price | Audience | Features |
|------|-------|----------|----------|
| Particular | 5 EUR/mes | Salaried, pensionists | IRPF guide, payslip analysis, basic deductions |
| Creator | 49 EUR/mes | Influencers, YouTubers, streamers, bloggers | + IVA by platform, Modelo 349, DAC7, CNAE 60.39, multi-role profiles |
| Autonomo | 39 EUR/mes IVA incl. | Self-employed | + All models (303/130/131), crypto, workspace, calendar |

## Key Updates (2026-04-20)

- **Deploy Railway — regla de oro (2026-08-11, Bugs 111-113)**: son **2 servicios sobre el mismo repo** y cada uno lee un fichero de config distinto — `railway.toml` de la **raíz** = FRONTEND (Root Directory `/frontend`, builder Railpack); `backend/railway.toml` = BACKEND (Root Directory `/backend`, builder `backend/Dockerfile`). La ruta del config es un ajuste por servicio y *no* sigue al Root Directory. Con builder Dockerfile, el `startCommand` corre en **exec form** y NO expande variables: `$PORT` debe ir envuelto en `/bin/sh -c "exec ..."`. Y las dependencias que se importan en el arranque van **pineadas exactas**. Detalle en `memory/bugfixes-2026-08.md` y en el skill `deployment-railway`

- **Hotfix 2026-04-20 — Bug 84**: DefensIA `/defensia/expedientes` 404 en produccion. Causa: backend monta `/api/defensia`, frontend llamaba `/defensia` sin prefix. Fix: prefix `/api/` anadido en 9 call sites (7 archivos). Tests actualizados. Regla documentada en `frontend/CLAUDE.md` — TODO hook nuevo DEBE usar `/api/<router>/...`. Commit `20bf545` en main.
- **DefensIA — "Volver a inicio"**: Back-link anadido en `DefensiaListPage`, `DefensiaWizardPage` y `DefensiaExpedientePage` (este ultimo navega a `/defensia`). Estilo `.defensia-back-link` clonado del patron `.cf-back-link`. Commit `8f7932c` en main.
- **Session 34 — Merge final a main**: DefensIA (71+ commits) + Modelo 200 IS (11 commits) mergeados a main en produccion. Hotfix lazy imports `Modelo200Page` (app crasheaba por imports faltantes). Copilot rounds 8-9 (48 comentarios resueltos en total). RAG ingesta completa: 463 docs, 92,393 chunks, 85,587 embeddings. `copilot-instructions.md` activo.
- **Cleanup 2026-04-20**: 23 fragmentos de codigo basura borrados del root (fragments de paste rotos: `({`, `[...prev`, `parseDeductions(content)`, etc.). `.gitignore` ampliado: vectors.db, vite timestamps, playwright reports, QA session-specific tests, carpetas locales.
- **Session 32 — DefensIA Parte 1** (sesion 32): Nuevo modulo defensor fiscal con motor hibrido anti-alucinacion (Gemini extraccion → reglas deterministas → RAG verificador → LLM redactor controlado). Brainstorming + spec + plan + Wave 1 Back ejecutada en rama `claude/defensia-v1`. **58 tests verdes** (migracion, models, taxonomy, classifier, 7 extractores, phase detector 12-estados, caso David ground truth, rules engine scaffold). Caso David Oliva (141 archivos, 4 reclamaciones encadenadas) como ground truth del producto. 4 bugs detectados y fixeados (ver bugfixes-2026-04.md Bug 78-81). Parte 2 pendiente (~58 tasks: 30 reglas R001-R030, RAG verificador, writer service, frontend completo, E2E, beta). Spec en `plans/2026-04-13-defensia-design.md`, plan en `plans/2026-04-13-defensia-implementation-plan.md`, memoria sesion en `memory/project_session32_defensia_part1.md`. 23 commits.
- **DefensIA scope v1**: 5 tributos (IRPF + IVA + ISD + ITP + Plusvalia Municipal) + procedimientos verificacion/comprobacion limitada/sancionador + vias reposicion/TEAR (abreviado y general). FUERA: inspeccion, apremio, TEAC, contencioso, IS. Monetizacion: 1/3/5 expedientes/mes por plan Particular/Autonomo/Creator + 15/12/10 EUR por expediente extra. Disclaimer obligatorio en 4 superficies (banner, argumentos, escrito exportado, checkbox pre-export). Entrada en dropdown "Herramientas" del Header.tsx (en Parte 2).
- **Regla #1 de producto DefensIA**: el sistema NO arranca analisis juridico hasta que el usuario escriba su brief. Fase 1 (extraccion tecnica) SI puede auto-dispararse al subir documentos. Fases 2-4 (reglas + RAG verificador + redactor) requieren accion explicita del usuario.
- **Session 31** (sesion 31): 9 features + 12 security + 8 bugfixes. PDF modelos, workspace dashboard visual (Recharts), auto-classify, chat workspace selector. 12 commits
- **Generador PDF Modelos**: POST `/api/export/modelo-pdf` — 303/130/308/720/721/IPSI + forales (300/F69/420). Hook `useModeloPDF`, botones en DeclarationsPage y M130CalculatorPage
- **Workspace Dashboard Visual**: KPIs (SpotlightCard+CountUp), barras IVA trimestral, linea ingresos/gastos mensual, tabla PGC, top proveedores, facturas recientes. Recharts v3.8.1. Endpoint `GET /api/workspaces/{id}/dashboard`
- **Workspace Fase 2**: Auto-clasificacion PGC al subir factura + confirm-classification + classify-pending retroactivo + auto-detect tipo (emitida/recibida por NIF)
- **Workspace Fase 3**: Selector dropdown workspace en Chat + indicador visual + workspace_id persistido en conversations + WorkspaceCards acceso rapido
- **Session 30 RAG fix completo** (sesion 30): 4 bugs encadenados arreglados — territory tildes, OOM (workers 4→1), SSE keepalive, Upstash Vector sync 84K. RAG hibrido (FTS5+Vector) ahora funcional. Vector search con accent fallback + 10s timeout
- **Railway**: 1 worker obligatorio (~344 MB por worker). El `--workers 1 --timeout-keep-alive 120` vive en `backend/railway.toml` (`startCommand`) y en el `CMD` de `backend/Dockerfile`, NO en el `railway.toml` de la raíz
- **Upstash Vector**: 84,036 embeddings sincronizados (100%). Sync script: `scripts/sync_to_upstash.py`. Verificar count periodicamente
- **Territory names**: SIEMPRE canonical de `ccaa_constants.py` (con tildes). `get_territory()` tiene fallback `normalize_ccaa()`
- **SSE keepalive**: Enviar `thinking` event ANTES de RAG search para evitar connection drop por inactividad
- **Session 29 Clasificador Facturas mobile fix** (sesion 29): 5 bugs arreglados — "Ver detalles" implementado (GET /api/invoices/{id}), upload movil iOS Safari (label htmlFor + visually-hidden), formatEUR null-safe, back link, preconnect URL fix
- **iOS file upload pattern**: NUNCA `display:none` en `<input type="file">`. Usar `position:absolute; opacity:0; clip:rect(0,0,0,0)` + `<label htmlFor>` en vez de `.click()` programatico
- **Session 28 QA + Security** (sesion 28): 12 bugs clasificador/contabilidad arreglados, auditoria seguridad 20/21 issues (4 CRITICAL), PageSpeed 69→85+, chat.py TaxIAResponse crash fix, rate limiting /ask, deploy fix
- **Clasificador Facturas QA**: upload FormData fix, timeout 120s, mapping backend→frontend, column names alineados con DB
- **Contabilidad 4 tabs**: Diario/Mayor/Balance/PyG mapping arreglado (cuenta_code→cuenta, etc.)
- **Security hardening**: shared owner_guard.py, JWT startup validation, CORS prod hardening, SQL injection scripts parametrizados, security test endpoints gated por ENV
- **Code quality**: 55x datetime.utcnow→datetime.now(timezone.utc), gpt-4o-mini→gpt-5-mini en todo backend, dead code eliminado
- **PageSpeed**: hero image 234KB→27KB (88%), lazy load Home/Chat/Dashboard, cache headers, font non-blocking
- **Test users**: 3 usuarios (particular + autonomo + creator) con suscripciones hasta 2026-12-31
- **Model**: SIEMPRE gpt-5-mini, NUNCA gpt-4o-mini. Params OpenAI: `temperature=1` (unico valor soportado), `max_completion_tokens` (NUNCA `max_tokens`). Groq puede usar `temperature=0` y `max_tokens`
- **Git**: NUNCA incluir ruvnet, claude-flow, Claude, Co-Authored-By en commits

- **SEO Overhaul** (sesion 27): Hook `useSEO()`, 12 paginas con schema JSON-LD (WebApplication, FAQPage, HowTo, BreadcrumbList), sitemap 21 URLs, OG image, Twitter cards, canonical URLs. Home: 3 pricing cards inline (Particular/Creator/Autonomo verde) + card Farmacias en Tecnologia
- **Crawler Watchlist** (sesion 27): 59 URLs activas (antes 48). 11 URLs activadas para campana renta: Manual Renta 2025, retenciones, modelos 303/390/190/720/349/036, Plan Tributario 2026
- **Phase 3: Clasificador Facturas + Contabilidad PGC** (sesion 26): Gemini 3 Flash Vision OCR ($0.0003/factura), clasificacion PGC automatica, asientos partida doble, Libro Diario/Mayor/Balance/PyG, export CSV/Excel para Registro Mercantil. 56 tests, 10 endpoints, 66 cuentas PGC. Frontend responsive mobile-first.
- **Google Gemini API**: `google-genai` SDK integrado. Env var: `GOOGLE_GEMINI_API_KEY`. Modelo: `gemini-2.5-flash-lite` (`settings.GEMINI_MODEL`). **`gemini-3-flash-preview` fue RETIRADO por Google (404)** — nunca hardcodear el id de modelo, siempre leer `settings.GEMINI_MODEL`
- **ADR-009**: Gemini 3 Flash para OCR facturas (33x mas barato que Azure DI). ADR-010: Contabilidad completa
- **Tests**: ~1758 backend PASS + frontend build OK (sesion 28 verified)
- **Repo**: Migrado a `Nambu89/Impuestify` (antes TaxIA). Railway auto-deploy conectado
- **RAG Pipeline** (FIXED sesion 22): 454 docs, 89,174 chunks, 82,098 embeddings, FTS5 sync. Territory filter normalizado, FTS5 OR query, semantic cache poisoning prevention, auto-rebuild FTS5 en ingesta
- **System Prompt** (REWRITE sesion 22): Tecnicas GPT-5/Claude/NotebookLM — etiquetas `<contexto_fiscal>`, nivel 3/10, show dont tell, zero process narration
- **AEAT Crawler** (NEW): crawl_aeat_full.py (PDFs con Scrapling) + crawl_aeat_html.py (HTML con Playwright). 7 PDFs + 19 HTMLs descargados e ingestados
- **Superpowers v5.0.6** (NEW): Plugin oficial Anthropic instalado. TDD, brainstorming, planning, code review
- **3 skills GSD** (NEW): fresh-context-execution, wave-execution, atomic-commits
- **Multi-Pagadores IRPF**: PagadorItem model, obligacion declarar Art.96 LIRPF
- **Calculadora Retenciones IRPF** (NEW): `/calculadora-retenciones` publica, algoritmo AEAT 2026, 28 tests, lead magnet SEO
- **Share Conversations** (NEW): `/shared/:token` enlaces publicos con anonimizacion PII (DNI, IBAN, importes)
- **RuFlo RETIRADO (2026-08-23)**: aportaba 98 de las 100 alertas de code-scanning (árbol de utillaje que no se despliega) y no se usaba. Los agentes NO dependían de él: `impuestify-team.yaml` era solo un mapeo que apuntaba a `.claude/agents/*.md`, que siguen intactos. Ver la sección "Squad de agentes"
- **Adaptive Tax Guide by Role**: PARTICULAR (7 steps), CREATOR (8 steps + plataformas/IAE/IVA intracomunitario/withholding/M349), AUTONOMO (8 steps + actividad económica). Adaptive result with role-specific obligations
- **Net Salary Calculator**: `/calculadora-neto` endpoint. 5 fiscal regimes (Madrid common IVA 21%, Andalucía, Canarias IGIC 7%, Melilla IPSI 4% + 60% deduction, País Vasco 7-tranche foral). SS auto-calculated by income (15 brackets RDL 13/2022). IGIC/IPSI auto-detection. 21 tests PASS. Disclaimer on each response
- **Crawler**: 90 URLs, 23 territories + Creators/Influencers docs
- **Feedback System**: Widget + ChatRating + Admin Dashboard (3 pages) COMPLETE
- **XSD Modelo 100**: ~100% coverage (granular expenses, modules, royalties, IAE lookup)
- **Joint Declaration**: Comparison tool for 4 scenarios (tool: `compare_joint_individual`)
- **CCAA-aware Models**: 303→300 Gipuzkoa, F69 Navarra, 420 IGIC Canarias, IPSI Ceuta/Melilla
- **Landing /creadores-de-contenido**: SEO-GEO optimized, Creator segment marketing
- **Multi-role Fiscal**: `roles_adicionales` (non-exclusive), adaptive by CCAA
- **TaxAgent Creator Context**: IAE 8690, IVA by platform, Modelo 349, DAC7, CNAE 60.39
- **Push Notifications**: VAPID keys configured
- **Tax Date Correction**: Filing date 8 April 2026 (not 5 April)

## Dev Tools (local only, not deployed)

- **Feature flags**: `.feature_flags.json` — toggle features locally. Env var override: `FF_FEATURE_NAME=true/false`. See `.feature_flags.json.example`
- **AutoDream**: `python scripts/autodream.py` — code analysis report (large files, missing tests, TODOs)
- **Task types**: Use specialized `subagent_type` in Agent tool: `coder`, `researcher`, `tester`, `reviewer`, `Explore`

## Compacting Strategy

When context reaches ~50%, Claude Code compresses history. To preserve critical info:
- Re-read `CLAUDE.md` + relevant descendant CLAUDE.md after compaction
- Check `memory/MEMORY.md` for project state (updated 2026-04-20, session 34 + hotfixes)
- Check `agent-comms.md` for pending inter-agent tasks
- Check `claude-progress.txt` for session history
