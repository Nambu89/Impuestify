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
- ReasoningBank: implementado en `agentic-flow` (node_modules/agentic-flow/dist/reasoningbank/), ruflo usa bridge controller. Falla en Windows por 3 capas: (1) @xenova/transformers v2.17.2 static import de onnxruntime-node, (2) ruta OneDrive con espacios, (3) dos versiones conflictivas onnxruntime-node 1.14.0 vs 1.24.3. Fix: instalar VC++ 2022 Redistributable x64, o patch local onnx.js, o WSL2. En Railway/Linux funciona sin cambios
- Intelligence stats se resetean tras restart (pretrain repobla desde archivos)
- Version MCP reporta 3.0.0 pero CLI es 3.5.41 (cache desactualizado)
- AgentDB v1.3.9 tiene ESM import issues — ruflo incluye runtime patch automatico

**Capacidad estimada: ~85% (techo real hasta que ruflo implemente ReasoningBank)**
