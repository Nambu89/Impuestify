---
name: RuFlo V3.5 Workflow
description: RuFlo es el workflow multi-agente estandar del proyecto. Estado de configuracion, capacidad y limitaciones conocidas.
type: feedback
---

RuFlo V3.5 es el workflow estandar para desarrollo multi-agente en Impuestify. Complementado con Superpowers plugin (v5.0.6) y 3 skills GSD adaptadas.

**Why:** Permite orquestar agentes especializados (backend, frontend, QA, etc.) con routing inteligente, memoria compartida y aprendizaje continuo.

**How to apply:**
- MCP server configurado en `.mcp.json` (comando: `npx -y ruflo@latest mcp start`)
- Config en `.claude-flow/config.yaml`, team en `.claude-flow/agents/impuestify-team.yaml`
- Usar `agent_spawn` para crear agentes (swarm_init tiene bug en Windows)
- Memoria: namespace `impuestify`, backend sql.js + HNSW
- Intelligence: pretrain con `hooks_pretrain` depth=deep al inicio de sesion si stats muestran 0
- Hooks: 26 activos, se registran automaticamente al iniciar MCP
- Patrones: almacenar via `hooks_intelligence_pattern-store` para alimentar routing
- Router adaptativo: scores por (patron, agente), persiste en `routing-history.json`

**Complementos anadidos sesion 22:**
- **Superpowers v5.0.6** (plugin oficial Anthropic): TDD enforcement, brainstorming, planning, code review, finishing branches. Auto-activacion contextual. Complementa las 5 skills ya adaptadas (subagent-driven-dev, dispatching-parallel, git-worktree, systematic-debugging, verification-before-completion)
- **3 skills GSD** (adaptadas, no el paquete completo — evita conflicto con RuFlo):
  - `fresh-context-execution`: Subagentes con contexto fresco (previene context rot >50%)
  - `wave-execution`: Tareas agrupadas por dependencias, ejecutadas en paralelo por oleadas
  - `atomic-commits`: Un commit por tarea, historial limpio para git bisect

**Limitaciones conocidas (2026-03-26):**
- `swarm_init` falla en Windows (store interno undefined). Agentes funcionan individualmente
- ReasoningBank: FUNCIONA en Windows tras 2 patches (sesion 17): (1) renombrar nested onnxruntime-node 1.24.3 NAPI v6 → fallback a top-level 1.14.0 NAPI v3, (2) crear alias agentdb/dist/controllers/index.js. Patches se pierden en npm install
- Intelligence stats se resetean tras restart (pretrain repobla desde archivos)
- AgentDB v1.3.9 tiene ESM import issues — ruflo incluye runtime patch automatico
- GSD completo NO instalado (conflicta con RuFlo por orquestacion). Solo patrones cherry-picked como skills

**Nuevas herramientas sesion 22 (para orquestar en futuras sesiones):**
- Calculadora Retenciones IRPF: `/calculadora-retenciones` (publica, algoritmo AEAT 2026)
- Share Conversations: `/shared/:token` (enlaces publicos con anonimizacion PII)
- AEAT Crawler: `crawl_aeat_full.py` + `crawl_aeat_html.py` (PDFs + HTML con Playwright)
- Purge Semantic Cache: `railway run python backend/scripts/purge_semantic_cache.py`

**Capacidad estimada: ~90% (mejora con Superpowers + GSD patterns)**

## Lecciones sesion 32 (DefensIA Parte 1, 2026-04-13)

### Patron de ejecucion "batches por wave" es mas eficiente que task-por-task estricto

**Context:** La sesion 32 ejecuto la Parte 1 de DefensIA (16 tasks TDD) via subagent-driven-development. Probamos primero task-por-task estricto con T0 (anadir deps) y consumio **5 subagent calls** para un cambio trivial de 2 lineas debido a review loops (spec review + code quality review + fix + re-review). Multiplicado por 22 tasks daba ~100 calls, inviable.

**Solucion aplicada:** Batches por wave con review agregado:
- Batch 1 «Fundaciones» → T1+T2+T3 en un solo dispatch de implementer (DB migration + Pydantic models + router stub)
- Batch 2 «Taxonomy + Classifier» → T10+T11
- Batch 3 «Extractores 1» → T12+T13+T14
- Batch 4 «Extractores 2» → T15+T16+T17+T18
- Batch 5 individual «Phase detector + Caso David» → T19+T20 (individuales por criticidad)
- Batch 6 individual → T30 (rules engine)

**Resultado:** 7 dispatches de implementer + 2 reviews agregadas + 2 fix passes = 11 calls totales para 16 tasks. 58 tests verdes. ~30 minutos de ejecucion real.

**Regla:** Agrupar en batches tasks que:
- Compartan un patron estructural (los 7 extractores siguen todos el mismo triplete `_PROMPT_*` + `_gemini_extract_*` + `extract_*`)
- Modifiquen ficheros compatibles sin conflictos entre commits separados
- NO dependan de un test cross-task para validarse

Dispatch individual solo para:
- Tasks criticas con ground truth (phase detector, caso David integration)
- Tasks arquitectonicas donde el review agregado perderia contexto (rules engine core)

### Verificacion factual obligatoria antes de aplicar fixes de reviewers

**Incidente T0:** Un code quality reviewer afirmo que `lxml==5.3.0` y `Jinja2==3.1.4` eran duplicados cuando no lo eran. Un fix implementer las elimino basado en esa afirmacion falsa. El controlador tuvo que revertir con un tercer commit (`98e0487`) tras verificar con `git show <sha>` que las lineas nunca habian existido antes.

**Regla:** Antes de aceptar un fix derivado de una afirmacion factual de un reviewer sobre el estado previo del codigo, el controlador DEBE verificar la afirmacion con `git show`, `git diff` o `grep`. Los subagents reviewers no tienen memoria del diff original y pueden fabricar hechos.

**Patron de prompt para reviewers:** Cuando le pidas a un reviewer que valide un commit, dale el SHA y pide explicitamente: *"Run `git show <sha> -- <path>` and state exactly what lines were added/removed. Do NOT claim that a line existed before the commit unless you verified it with `git show <sha>^ -- <path>`."*

### Auto-accept settings para flow continuo

Sesion 32 anadio 21 reglas `allow` a `.claude/settings.local.json` para que los comandos seguros del loop de subagents (git add/commit/show/log, pytest, pip install, Edit/Write en backend/frontend/plans) pasen sin prompt. Esto acelero la ejecucion de los 4 ultimos batches sustancialmente.

**Reglas minimas recomendadas para sesiones largas de implementacion:**
- `Bash(git add:*)`, `Bash(git commit:*)`, `Bash(git show:*)`, `Bash(git log:*)`, `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git branch:*)`
- `Bash(cd backend && pytest:*)`, `Bash(cd backend && python:*)`, `Bash(cd backend && pip install:*)`
- `Edit(backend/**)`, `Edit(frontend/**)`, `Edit(plans/**)`, `Edit(backend/tests/**)`
- `Write(backend/**)`, `Write(frontend/**)`, `Write(plans/**)`, `Write(backend/tests/**)`

**Nunca anadir:** `Bash(rm:*)`, `Bash(git reset --hard:*)`, `Bash(git push --force:*)`, acceso a `.env`, nada que modifique secretos.

### Skills Superpowers validadas en sesion 32

- `superpowers:using-superpowers` — invocada al inicio de cada sesion compleja (funciona)
- `superpowers:brainstorming` — ejecutada con 6 preguntas estructuradas + spec escrito a `plans/YYYY-MM-DD-<topic>-design.md` (funciona, convention override a `plans/` en vez de `docs/superpowers/specs/` correcta)
- `superpowers:writing-plans` — ejecutada para la Parte 1 (funciona). Parte 2 pendiente
- `superpowers:subagent-driven-development` — ejecutada para Parte 1 con adaptacion a batches (funciona pero requiere adaptacion pragmatica para features grandes)
- `superpowers:test-driven-development` — aplicada implicita en cada task TDD (funciona)

### Convenciones del proyecto que sobreescriben defaults de skills

- **Spec/plan location:** `plans/` (gitignored para specs internos) NO `docs/superpowers/specs/` NI `docs/superpowers/plans/`
- **Branch convention:** `claude/<descriptor>` para trabajo AI-asistido (NO worktree)
- **Commit attribution:** sin `Co-Authored-By: Claude`, sin `ruvnet`, sin `claude-flow` — project hard rule
- **Migration pattern:** inline `CREATE TABLE IF NOT EXISTS` en `turso_client.py::init_schema()` (NO Alembic, NO auto-discover runners)

**Capacidad actualizada: ~92% tras lecciones sesion 32 (batching eficiente + verificacion factual obligatoria).**
