---
name: project_session30_rag_workspaces
description: Sesion 30 — RAG fix completo (OOM, tildes, SSE, Vector sync 84K), workspace RAG hibrido, facturas test autonomo
type: project
---

# Sesion 30 — RAG Fix + Workspace RAG Hibrido (2026-04-09)

## Bugs arreglados (72-75 + 3 adicionales)

### Bug 72: Territory plugins + OOM
- `COMUN_TERRITORIES` sin tildes → KeyError
- 4 workers × 344 MB = OOM killer
- Fix: canonical names, workers 4→1, async vector, sequential trust

### Bug 73: Vector search accent mismatch
- Filtro no probaba variante sin tilde
- Fix: `_strip_accents()` fallback

### Bug 74: SSE connection drop
- 70s sin bytes → proxy/browser cortaba
- Fix: yield thinking event antes del RAG + 10s timeout vector

### Bug 75: Upstash Vector solo 39 de 84K
- Sync nunca completado
- Fix: re-sync completo. 84,036 embeddings (100%)

### Bugs adicionales (sin numero):
- **Territory bidireccional**: `Cataluna→Cataluña` y `Aragón→Aragon`. Usa `normalize_ccaa()`
- **integrity_score 0.0 en 300 docs**: 5/5 chunks excluidos. Fix: UPDATE a 1.0 (fail-open)
- **Workspace re-analiza facturas**: Cargaba `extracted_text` crudo. Fix: usa `extracted_data` JSON estructurado

## Features implementadas

### Workspace RAG Hibrido
- Chat con `workspace_id` ahora busca en AMBOS: docs globales + docs del workspace
- Contexto combinado con secciones etiquetadas: `DOCUMENTOS DEL USUARIO` + `NORMATIVA FISCAL`
- Workspace embeddings (3072-dim) consultados via `search_workspace()`

### Facturas test autonomo
- 12 PDFs generados: 6 emitidas + 6 recibidas (Q1 2025, consultor IT Madrid)
- Subidas al workspace del test.autonomo en produccion
- Script: `backend/scripts/generate_autonomo_invoices.py`

## Pendiente para proxima sesion

### CRITICO: Generador PDF Modelos Tributarios
- El usuario pide generar el PDF del Modelo 303 prerellenado para subir a la AEAT
- Debe seguir formato oficial de cada modelo (AEAT estatal, autonomica, foral, Canaria, Ceuta/Melilla)
- Modelos necesarios: 303, 130, 131, 100, 349, 390, 720/721, IPSI, IGIC
- Tecnologia: ReportLab con template overlay del formulario oficial
- El agente debe ofrecer generarlo cuando tenga datos suficientes

### Importes incorrectos en extraccion
- LLM leyo bases como 400 en vez de 4.000 EUR (le falta un cero)
- Revisar extracted_data de las facturas — puede ser error de OCR/extraccion
- Confidence scores medianos — mejorar parsing de importes

### Bug: perdida contexto workspace en follow-ups
- Segunda pregunta "Dame el PDF" perdio el workspace_id
- El agente dio respuesta generica en vez de usar los datos del workspace
- Verificar que frontend pasa workspace_id en TODAS las preguntas de la conversacion

## Investigacion comercial
- **Laborai.es** investigado: B2C fiscal, WordPress, posible partnership licencia tech
