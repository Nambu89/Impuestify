---
name: project_workspace_vision
description: Vision de producto para workspaces — centro de operaciones de autonomos/creadores/farmacias con RAG hibrido (global + documentos usuario)
type: project
---

# Workspace Vision — Centro de Operaciones Fiscal

**Why:** Los workspaces deben ser la herramienta de trabajo diaria de autonomos, creadores y farmacias. No un simple almacen de archivos.

**How to apply:** Toda funcionalidad de workspace debe combinar 3 fuentes de contexto:
1. RAG global (legislacion AEAT/BOE, deducciones, normativa)
2. Documentos del usuario (facturas emitidas/recibidas, nominas, contratos)
3. Perfil fiscal del usuario (CCAA, situacion laboral, regimen)

## Fases de implementacion

### Fase 1: RAG hibrido (global + workspace) — sesion 30
- Conectar workspace embeddings al RAG search
- Cuando hay workspace_id, buscar en AMBOS: docs globales + docs del workspace
- Verificar flujo con facturas de ejemplo

### Fase 2: Auto-clasificacion → contabilidad
- Facturas subidas al workspace se clasifican automaticamente via Gemini OCR
- Resultados van al libro registro / contabilidad PGC
- Tools del WorkspaceAgent usan datos estructurados (no regex)

### Fase 3: Experiencia integrada
- Chat integrado dentro de /workspaces (no navegar a /chat)
- Conversaciones particionadas por workspace
- Proyecciones automaticas trimestrales (IVA, IRPF, gastos)
- Dashboard resumen dentro del workspace
