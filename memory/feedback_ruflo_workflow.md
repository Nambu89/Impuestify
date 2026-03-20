---
name: RuFlo V3.5 Workflow
description: RuFlo es el workflow multi-agente estandar del proyecto. Estado de configuracion, capacidad y limitaciones conocidas.
type: feedback
---

RuFlo V3.5 es el workflow estandar para desarrollo multi-agente en Impuestify.

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

**Limitaciones conocidas (2026-03-20):**
- `swarm_init` falla en Windows (store interno undefined). Agentes funcionan individualmente
- ReasoningBank: FUNCIONA en Windows tras 2 patches (sesion 17): (1) renombrar nested onnxruntime-node 1.24.3 NAPI v6 → fallback a top-level 1.14.0 NAPI v3, (2) crear alias agentdb/dist/controllers/index.js. Init OK, DB .swarm/memory.db, embeddings all-MiniLM-L6-v2 ONNX. Bugs menores: runTask y retrieveMemories tienen schema mismatches de AgentDB v1.3.9. Patches se pierden en npm install
- Intelligence stats se resetean tras restart (pretrain repobla desde archivos)
- Version MCP reporta 3.0.0 pero CLI es 3.5.41 (cache desactualizado)
- AgentDB v1.3.9 tiene ESM import issues — ruflo incluye runtime patch automatico

**Capacidad estimada: ~85% (techo real hasta que ruflo implemente ReasoningBank)**
