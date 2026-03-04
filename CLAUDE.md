# CLAUDE.md — TaxIA (Impuestify)

> **CRITICAL:** Before starting any complex task, check if `task.md` or `implementation_plan.md` exist. They are the source of truth for current objectives.

## Project Overview

TaxIA (Impuestify) is a Spanish tax assistant using RAG + multi-agent architecture (FastAPI + React). Provides IRPF calculation, deduction discovery, payslip analysis, and AEAT notification parsing for all 17 CCAA + 4 foral territories + Ceuta/Melilla.

## Request Flow

User → React frontend → FastAPI `/api/ask/stream` → JWT auth → Rate limiting → Guardrails (LlamaGuard4, prompt injection, PII) → Semantic cache → CoordinatorAgent → [TaxAgent|PayslipAgent|NotificationAgent|WorkspaceAgent] → Tools + RAG → OpenAI GPT → SSE response

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

## Compacting Strategy

When context reaches ~50%, Claude Code compresses history. To preserve critical info:
- Re-read `CLAUDE.md` + relevant descendant CLAUDE.md after compaction
- Check `memory/MEMORY.md` for project state
- Check `agent-comms.md` for pending inter-agent tasks
- Check `claude-progress.txt` for session history
