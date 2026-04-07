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

## Key Updates (2026-04-07)

- **Session 28 QA + Security** (sesion 28): 12 bugs clasificador/contabilidad arreglados, auditoria seguridad 20/21 issues (4 CRITICAL), PageSpeed 69→85+, chat.py TaxIAResponse crash fix, rate limiting /ask, deploy fix
- **Clasificador Facturas QA**: upload FormData fix, timeout 120s, mapping backend→frontend, column names alineados con DB
- **Contabilidad 4 tabs**: Diario/Mayor/Balance/PyG mapping arreglado (cuenta_code→cuenta, etc.)
- **Security hardening**: shared owner_guard.py, JWT startup validation, CORS prod hardening, SQL injection scripts parametrizados, security test endpoints gated por ENV
- **Code quality**: 55x datetime.utcnow→datetime.now(timezone.utc), gpt-4o-mini→gpt-5-mini en todo backend, dead code eliminado
- **PageSpeed**: hero image 234KB→27KB (88%), lazy load Home/Chat/Dashboard, cache headers, font non-blocking
- **Test users**: 3 usuarios (particular + autonomo + creator) con suscripciones hasta 2026-12-31
- **Model**: SIEMPRE gpt-5-mini, NUNCA gpt-4o-mini
- **Git**: NUNCA incluir ruvnet, claude-flow, Claude, Co-Authored-By en commits

- **SEO Overhaul** (sesion 27): Hook `useSEO()`, 12 paginas con schema JSON-LD (WebApplication, FAQPage, HowTo, BreadcrumbList), sitemap 21 URLs, OG image, Twitter cards, canonical URLs. Home: 3 pricing cards inline (Particular/Creator/Autonomo verde) + card Farmacias en Tecnologia
- **Crawler Watchlist** (sesion 27): 59 URLs activas (antes 48). 11 URLs activadas para campana renta: Manual Renta 2025, retenciones, modelos 303/390/190/720/349/036, Plan Tributario 2026
- **Phase 3: Clasificador Facturas + Contabilidad PGC** (sesion 26): Gemini 3 Flash Vision OCR ($0.0003/factura), clasificacion PGC automatica, asientos partida doble, Libro Diario/Mayor/Balance/PyG, export CSV/Excel para Registro Mercantil. 56 tests, 10 endpoints, 66 cuentas PGC. Frontend responsive mobile-first.
- **Google Gemini API**: `google-genai` SDK integrado. Env var: `GOOGLE_GEMINI_API_KEY`. Modelo: `gemini-3-flash-preview`
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
- **RuFlo V3.5**: Workflow multi-agente + Superpowers + GSD patterns (~90% capacidad)
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
- Check `memory/MEMORY.md` for project state (updated 2026-03-20, session 16)
- Check `agent-comms.md` for pending inter-agent tasks
- Check `claude-progress.txt` for session history
