# CLAUDE.md — TaxIA (Impuestify)

> **CRITICAL:** Before starting any complex task, check if `task.md` or `implementation_plan.md` exist. They are the source of truth for current objectives.

## Project Overview

TaxIA (Impuestify) is a Spanish tax assistant using RAG + multi-agent architecture (FastAPI + React). Provides IRPF calculation, deduction discovery, payslip analysis, AEAT notification parsing, and an interactive 7-step tax guide (/guia-fiscal) for all 17 CCAA + 4 foral territories + Ceuta/Melilla.

## Request Flow

**Chat:** User → React frontend → FastAPI `/api/ask/stream` → JWT auth → Rate limiting → Guardrails (LlamaGuard4, prompt injection, PII) → Semantic cache → CoordinatorAgent → [TaxAgent|PayslipAgent|NotificationAgent|WorkspaceAgent] → Tools + RAG → OpenAI GPT → SSE response

**Tax Guide (no LLM):** User → `/guia-fiscal` wizard → POST `/api/irpf/estimate` → `irpf_simulator.py` → JSON response (~50-100ms, no LLM, no auth required for estimate)

## Directory Layout

```
TaxIA/
├── backend/         # FastAPI Python 3.12+ (see backend/CLAUDE.md)
├── frontend/        # React 18 + Vite + TS (see frontend/CLAUDE.md)
├── docs/            # 428 RAG documents (PDFs + Excel) by territory
├── data/            # FAISS embeddings, knowledge_updates/
├── .claude/
│   ├── commands/    # 14 slash commands
│   ├── skills/      # Domain knowledge modules
│   └── subagents/   # 6 agent personas
├── agent-comms.md   # Inter-agent communication log
├── memory/          # Persistent agent memory
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

## Compacting Strategy

When context reaches ~50%, Claude Code compresses history. To preserve critical info:
- Re-read `CLAUDE.md` + relevant descendant CLAUDE.md after compaction
- Check `memory/MEMORY.md` for project state
- Check `agent-comms.md` for pending inter-agent tasks
- Check `claude-progress.txt` for session history
