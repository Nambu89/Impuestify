# Plan: Integracion Ruflo v3.5 en Workflow de Desarrollo TaxIA

> **Objetivo**: Integrar Ruflo como orquestador del sistema multi-agente de desarrollo de Impuestify
> **Estado**: PENDIENTE APROBACION
> **Fecha**: 2026-03-19
> **Impacto**: Workflow de desarrollo (NO afecta al producto en produccion)

## Situacion actual

### Nuestro sistema de agentes (manual)
```
PM (Claude Code) → spawn manual → agentes especializados
                 → coordinacion via agent-comms.md
                 → memoria via memory/*.md (grep, no semantica)
                 → quality gates manuales (plan-checker, verifier)
                 → sin learning entre sesiones
```

### Inventario actual

**10 agentes** (`.claude/agents/`):
| Agente | Rol | Mapeo Ruflo |
|--------|-----|-------------|
| pm-coordinator | Vision estrategica, delegacion, decisiones | Queen (Strategic) |
| backend-architect | FastAPI, DB, seguridad, APIs | Worker: Coder (backend) |
| frontend-dev | React, TypeScript, CSS, UX | Worker: Coder (frontend) |
| python-pro | Python optimization, debugging | Worker: Optimizer |
| qa-tester | Playwright E2E, reportes QA | Worker: Tester |
| doc-crawler | Rastreo docs fiscales AEAT/BOE | Worker: Researcher |
| competitive-intel | Analisis mercado fiscal | Worker: Analyst |
| doc-auditor | Documentacion tecnica | Worker: Documenter |
| plan-checker | Verificacion pre-implementacion | Worker: Reviewer (pre) |
| verifier | Verificacion post-implementacion | Worker: Reviewer (post) |

**14 skills** (`.claude/skills/`):
irpf-calculation, sse-streaming, turso-patterns, security-layers, stripe-integration,
deployment-railway, playwright-testing, systematic-debugging, verification-before-completion,
subagent-driven-development, dispatching-parallel-agents, git-worktree-isolation,
project-research, roadmap-manager

**20 commands** (`.claude/commands/`):
/pm, /backend, /frontend, /python, /qa, /crawl, /competitive, /docs, /verify,
/check-plan, /commit, /deploy, /test, /review, /start, /prime, /sync,
/drift-detect, /files, /workspace

## Que aporta Ruflo

### Beneficios directos

1. **Orquestacion automatica** — En vez de spawneo manual secuencial, Ruflo descompone tareas y asigna agentes en paralelo automaticamente
2. **Routing inteligente** — Q-Learning router aprende que agente es mejor para cada tipo de tarea (hoy es decision manual del PM)
3. **Memoria semantica** — HNSW vector search sobre patrones exitosos (hoy: grep en archivos .md)
4. **Learning cross-session** — ReasoningBank + EWC++ preservan lo aprendido (hoy: se pierde entre sesiones salvo memory/)
5. **Token optimization** — Agent Booster (WASM) para edits triviales sin LLM + compresion (30-50% ahorro)
6. **Background workers** — Auto-trigger: tests on change, lint, security audit continuo (hoy: manual)
7. **Anti-drift** — Verification gates automaticos con consensus (hoy: plan-checker manual)
8. **Claims system** — Coordinacion humano-agente para handoffs (hoy: agent-comms.md manual)

### Lo que NO cambia
- Los agentes siguen siendo los mismos (solo se registran en Ruflo)
- Las skills siguen siendo las mismas
- El codigo de produccion (FastAPI + React) no se toca
- CLAUDE.md sigue siendo la fuente de verdad del proyecto

## Plan de implementacion

### Fase -1: Backup + Due Diligence (15 min)

**T-1.1. Backup de configuracion actual**
```bash
mkdir -p backups/pre-ruflo
cp .claude/settings.local.json backups/pre-ruflo/
cp .mcp.json backups/pre-ruflo/
cp -r memory/ backups/pre-ruflo/memory/
```
- Verificacion: `ls backups/pre-ruflo/` muestra 3 items

**T-1.2. Due diligence Ruflo**
- Verificar paquete npm: `npm view ruflo` — debe existir y tener version >= 3.5
- Verificar compatibilidad Windows 11: revisar issues/docs
- Confirmar que no requiere plan de pago propio (MIT license, usa nuestras API keys)
- Verificacion: npm view devuelve metadata valida

**T-1.3. Documentar procedimiento de rollback**
Si Ruflo no funciona o causa problemas:
```bash
# 1. Restaurar configs
cp backups/pre-ruflo/settings.local.json .claude/settings.local.json
cp backups/pre-ruflo/.mcp.json .mcp.json
# 2. Desinstalar
npm uninstall -g ruflo
# 3. Limpiar entrada MCP de settings
# 4. Verificar: Claude Code funciona con agentes manuales como antes
```

### Fase 0: Instalacion y setup (30 min)

**T0.1. Instalar Ruflo globalmente**
```bash
npx ruflo@latest init --wizard
```
- Seguir wizard interactivo
- Configurar `ANTHROPIC_API_KEY` (ya tenemos)
- Storage: SQLite (default, suficiente para 1 dev)

**T0.2. Verificar MCP integration**
- Confirmar que `.claude/settings.local.json` tiene el MCP server de Ruflo
- Confirmar que `.mcp.json` tiene entrada para Ruflo (anadir si no)
- Confirmar que `enabledMcpjsonServers` incluye Ruflo en settings
- Test basico: `ruflo status`
- Verificacion: `ruflo status` responde sin errores

### Fase 1: Registrar agentes existentes (1h)

**T1.1. Mapear agentes a formato Ruflo**

Nuestros agentes ya tienen YAML frontmatter compatible. Ruflo necesita:
```json
{
  "name": "backend-architect",
  "type": "coder",
  "model": "opus",
  "capabilities": ["fastapi", "turso", "security", "testing"],
  "max_workers": 1,
  "timeout_seconds": 600
}
```

Crear mapeo para los 10 agentes. Ruflo puede leer directamente los `.claude/agents/*.md` si configuramos el path.

**T1.2. Registrar skills como capabilities**

Mapeo completo de las 14 skills:
| Skill | Ruflo Domain | Notas |
|-------|-------------|-------|
| `irpf-calculation` | fiscal | Core domain |
| `sse-streaming` | integration | Backend streaming |
| `turso-patterns` | database | DB patterns |
| `security-layers` | security | 13 capas |
| `stripe-integration` | integration | Payments |
| `deployment-railway` | devops | Deploy |
| `playwright-testing` | qa | E2E testing |
| `systematic-debugging` | debugging | 4-phase debug |
| `verification-before-completion` | qa | **EVALUAR: potencialmente redundante con Ruflo auto-verify** |
| `subagent-driven-development` | orchestration | **EVALUAR: potencialmente redundante con Ruflo swarm** |
| `dispatching-parallel-agents` | orchestration | **EVALUAR: potencialmente redundante con Ruflo routing** |
| `git-worktree-isolation` | devops | Worktree patterns |
| `project-research` | research | Web research |
| `roadmap-manager` | management | Roadmap CRUD |

Las 3 skills marcadas "EVALUAR" describen procesos manuales que Ruflo automatiza. En Fase 4 decidiremos si deprecarlas o mantenerlas como fallback.

**T1.3. Registrar commands**

Los 20 commands (`.claude/commands/`) son shortcuts a agentes. Ruflo deberia poder invocarlos o reemplazarlos con su routing:
- Commands que Ruflo reemplaza: `/backend`, `/frontend`, `/python`, `/qa` (routing automatico)
- Commands que coexisten: `/pm`, `/commit`, `/deploy`, `/start`, `/prime` (acciones humanas)
- Commands que Ruflo automatiza: `/check-plan`, `/verify` (quality gates auto)

**T1.4. Configurar Queen hierarchy**

**T1.5. Configurar Queen hierarchy**
```
Strategic Queen: pm-coordinator (planning, roadmap, decisions)
  └── Tactical Queens:
      ├── backend-architect (backend coordination)
      └── frontend-dev (frontend coordination)
          └── Workers:
              ├── python-pro (optimization)
              ├── qa-tester (testing)
              ├── doc-crawler (research)
              ├── competitive-intel (analysis)
              ├── doc-auditor (documentation)
              ├── plan-checker (pre-review)
              └── verifier (post-review)
```

### Fase 2: Configurar hooks (30 min)

**T2.0. Auditar hooks existentes (CRITICO)**

`settings.local.json` ya tiene 2 hooks activos:
- `PreToolUse:Bash` → `bash-gate.js` (bloquea comandos peligrosos)
- `PostToolUse:Write|Edit|MultiEdit` → `quality-check.js` (verifica calidad)

Decision: Ruflo ENVUELVE los hooks existentes (no los reemplaza). Los hooks de Ruflo se ejecutan DESPUES de los nuestros. Verificar que el orden es determinista.

Verificacion: editar un archivo .tsx → `quality-check.js` se ejecuta primero → hook Ruflo se ejecuta despues.

**T2.1. Hooks de desarrollo (complementarios, NO solapan)**
- `TaskCompleted` → auto-update agent-comms.md + memory/ (no colisiona)
- `SessionStart` → cargar contexto CLAUDE.md + MEMORY.md (no colisiona)
- `PreCompact` → guardar resumen de sesion en memory/ (no colisiona)
- `SubagentStart` → log en agent-comms.md (nuevo, no colisiona)

**T2.2. Hooks de quality gates (automatizar lo manual)**
- `PlanCreated` → auto-trigger plan-checker
- `ImplementationDone` → auto-trigger verifier
- `PreCommit` → ortografia + build + tests

### Fase 3: Migrar memoria (1h)

**T3.1. Indexar memoria existente en HNSW**
- Importar `memory/*.md` (17 archivos) al vector store de Ruflo
- Importar `plans/*.md` (roadmap, decisions, research)
- Importar `agent-comms.md` (historial de tareas)

**T3.2. Definir fuente de verdad de memoria**

Decision: `memory/*.md` SIGUE siendo fuente de verdad. Ruflo INDEXA (read-only) para busqueda semantica pero NO escribe en memory/. Las escrituras a memoria siguen el flujo actual (Write → MEMORY.md index).

Esto evita desincronizacion y mantiene compatibilidad si desinstalamos Ruflo.

**T3.3. Configurar ReasoningBank**
- Alimentar con patrones exitosos de sesiones anteriores:
  - "Guia adaptativa por rol" → descomposicion exitosa en 9 tareas
  - "Crypto module" → 7 fases, 20 tareas, verificado
  - "DIS security layer" → 55 tests, 40 patrones
- Estos patrones guiaran futuras descomposiciones similares
- Verificacion: `ruflo memory search "guia adaptativa"` devuelve el patron

### Fase 4: Test drive (1h)

**T4.1. Tarea de prueba: "Implementa calculadora sueldo neto autonomo"**

Esta tarea del research es perfecta para probar:
- Ruflo deberia descomponer en: backend (endpoint), frontend (UI), tests, docs
- Asignar: backend-architect + frontend-dev + qa-tester
- Ejecutar en paralelo donde posible
- Verificar con plan-checker (pre) y verifier (post)

**T4.2. Comparar con workflow manual**
- Tiempo de ejecucion
- Calidad del resultado
- Tokens consumidos
- Numero de intervenciones manuales necesarias

**T4.3. GO/NO-GO checkpoint**

Criterios de NO-GO (ejecutar rollback Fase -1):
- Tokens consumidos > 2x del workflow manual para la misma tarea
- Intervenciones manuales > 5 para completar la tarea
- Build o tests fallan por causa de Ruflo (no del codigo)
- Hooks de Ruflo interfieren con `bash-gate.js` o `quality-check.js`

Si NO-GO: restaurar backups de Fase -1 y documentar por que no funciono.

### Fase 5: Ajuste fino (iterativo)

**T5.1. Tuning del router**
- Ajustar routing segun resultados de Fase 4
- Configurar fallbacks (si un agente falla, que otro toma la tarea)
- Optimizar token budget por agente

**T5.2. Documentar workflow nuevo**
- Actualizar CLAUDE.md con instrucciones Ruflo
- Crear `.claude/skills/ruflo-orchestration/SKILL.md`
- Actualizar agent-comms.md con nuevo formato (o deprecar en favor de AgentDB)

## Archivos a crear/modificar

| Archivo | Accion | Proposito |
|---------|--------|-----------|
| `.claude/settings.local.json` | MODIFICAR | Anadir MCP server Ruflo |
| `ruflo.config.json` (raiz) | CREAR | Config principal Ruflo |
| `.claude/agents/*.md` | SIN CAMBIOS | Ruflo los lee directamente |
| `.claude/skills/*` | SIN CAMBIOS | Se registran como capabilities |
| `CLAUDE.md` | MODIFICAR | Documentar workflow Ruflo |
| `memory/MEMORY.md` | MODIFICAR | Referencia a integracion Ruflo |

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigacion |
|--------|-------------|------------|
| Ruflo no lee nuestro formato YAML frontmatter | MEDIA | Crear adaptador o convertir a JSON |
| Overhead de Ruflo > beneficio para 1 dev | BAJA | Desactivar si no aporta, es reversible |
| Conflicto con hooks existentes (settings.json) | MEDIA | Merge cuidadoso, backup previo |
| Token budget se dispara con swarm | BAJA | Configurar limites por agente |
| Learning incorrecto (malos patrones) | BAJA | Review manual de ReasoningBank periodico |

## Criterios de exito

1. Una tarea de complejidad media (3-5 archivos) se completa con <2 intervenciones manuales
2. Token usage <= que workflow manual para la misma tarea
3. Quality gates (plan-checker + verifier) se ejecutan automaticamente
4. Memoria semantica encuentra patrones relevantes de sesiones anteriores
5. Build + tests pasan sin regresiones

## Timeline estimado

| Fase | Duracion | Dependencia |
|------|----------|-------------|
| Fase -1: Backup + Due diligence | 15 min | Ninguna |
| Fase 0: Install + setup | 30 min | Fase -1 |
| Fase 1: Registrar agentes + skills + commands | 1.5h | Fase 0 |
| Fase 2: Configurar hooks (audit + nuevos) | 45 min | Fase 1 |
| Fase 3: Migrar memoria (indexar + ReasoningBank) | 1h | Fase 1 |
| Fase 4: Test drive + GO/NO-GO | 1h | Fases 2+3 |
| Fase 5: Ajuste fino | Iterativo | Fase 4 (si GO) |
| **Total setup**: | **~5h** | |
