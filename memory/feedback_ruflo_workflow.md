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
