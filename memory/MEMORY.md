# TaxIA (Impuestify) — Memoria del Agente

> Ultima actualizacion: 2026-04-09 (sesion 30)
> Sesion 30: RAG fix completo — OOM (workers 4→1), territory tildes, SSE keepalive, Upstash Vector sync 84K
> Railway: 1 worker, ~344 MB. Chat funciona con RAG hibrido (FTS5 + Vector)
> Upstash Vector: 84,036 embeddings sincronizados (100%). Vector search funcional para todas las CCAA
> Acercamiento comercial: Laborai.es investigado (B2C fiscal, WordPress, posible licencia tech)

## Indice de archivos de memoria

| Archivo | Contenido |
|---------|-----------|
| `memory/backend-subscription.md` | Stripe: Particular 5 EUR/mes, Creator 49 EUR/mes, Autonomo 39 EUR/mes IVA incl. |
| `memory/crawler-state.md` | Crawler automatizado: 90 URLs, 23 territorios, Scrapling |
| `memory/frontend-features.md` | UX/Streaming, PWA, Landing, DeductionCards, Cookies, Admin, Feedback |
| `memory/bugfixes-2026-03.md` | 64 bugs fixeados marzo 2026 (Bugs 1-64) |
| `memory/bugfixes-2026-04.md` | 11 bugs abril 2026 (Bugs 65-75): clasificador, gpt-5-mini, RAG crash, Vector sync |
| `memory/mcp-design-tools.md` | Google Stitch + Nano Banana MCP config |
| `memory/response-quality-gap.md` | Calidad respuesta (RESUELTO): answer-first, RAG territorial |
| `memory/agent-system-improvements.md` | Mejoras GSD multi-agente (2026-03-08) |
| `memory/awesome-claude-code.md` | Integracion herramientas awesome-claude-code |
| `memory/aeat-docs-integration.md` | Docs AEAT: casillas, XSD, XLS, VeriFactu |
| `memory/feedback_errores_reportados.md` | Capturas beta testers SIEMPRE en `Errores reportados/` |
| `memory/beta_testers.md` | Beta testers: Ramon Palomares, Juan Pablo Sanchez, Jose Antonio Alvarez |
| `memory/reference_resend.md` | Servicio email: Resend (password reset, alertas) |
| `memory/feedback_dominio.md` | Dominio: impuestify.com (NO .es). Verificado en Resend |
| `memory/project_social_media.md` | Social Media: LinkedIn + Instagram + TikTok, 3 canales, 12 piezas/semana |
| `memory/project_creators_segment.md` | Creadores/influencers: research, pricing 49 EUR/mes, XSD gaps, crawler docs |
| `memory/reference_mission_control.md` | Autensa/Mission Control: dashboard orquestacion agentes IA (referencia futura) |
| `memory/feedback_ruflo_workflow.md` | RuFlo V3.5: workflow estandar, config, limitaciones Windows, capacidad ~95% |
| `memory/feedback_secrets_prevention.md` | CRITICO: NUNCA commitear secrets/passwords. Verificar antes de cada git add |
| `memory/feedback_no_claude_references.md` | CRITICO: NUNCA incluir ruvnet, claude-flow, Claude en commits ni push |
| `memory/feedback_ruflo_always_route.md` | SIEMPRE rutear tareas por RuFlo antes de delegar a subagentes |
| `memory/project_security_audit_stack.md` | Plan seguridad: Bandit+Semgrep+ZAP+Nuclei+Trivy (4 capas, $0) |
| `memory/feedback_requirements_sync.md` | SIEMPRE sincronizar pip install con requirements.txt |
| `memory/project_branding_update.md` | Sesion 18: nuevo logo, favicon escudo IA, header blanco, colores corporativos |
| `memory/project_google_oauth.md` | Google OAuth verification: privacy link fix + robots.txt + sitemap.xml |
| `memory/project_rag_quality.md` | RAG quality dashboard: admin page + evaluador ligero |
| `memory/project_crawler_upgrade_s19.md` | Sesion 19: Scrapling, ciclos reintento, 19 BOE IDs corregidos |
| `memory/project_session20_simulador_audit.md` | Sesion 20: renta imputada, perdidas, 5 XSD gaps, 160 deducciones CCAA |
| `memory/reference_azure_di.md` | Azure Document Intelligence: endpoint + API key para ingesta RAG |
| `memory/project_session21_deductions_complete.md` | Sesion 21: 408 deducciones 2025 (9 CCAA + 4 forales), frontend XSD |
| `memory/reference_openclaw_social.md` | OpenClaw: formato JSON, reglas, stats, pilares, workflow |
| `memory/project_social_media_published.md` | 20 publicaciones generadas sesion 23 + temas pendientes |
| `memory/feedback_sync_all_memories.md` | OBLIGATORIO: sincronizar memory/ + MEMORY.md en CADA actualizacion |
| `memory/feedback_check_bugs_first.md` | SIEMPRE revisar bugfixes antes de dar datos factuales al usuario |
| `memory/project_session24_docs_update.md` | Sesion 24: Manual Usuario v2.0 + Business Plan v2.0 |
| `memory/project_session25_column_a.md` | Sesion 25: 5 features Claude Code |
| `memory/project_session25_contabilidad_research.md` | Sesion 25: Research contabilidad PGC, farmacias, Registro Mercantil |
| `memory/project_phase3_gemini_invoices.md` | Phase 3: Gemini 3 Flash Vision OCR facturas + contabilidad PGC |
| `memory/project_session26_phase3.md` | Sesion 26: Phase 3 completa — OCR, PGC, asientos, libros, 56 tests |
| `memory/project_session27_seo_overhaul.md` | Sesion 27: SEO overhaul, useSEO hook, 12 paginas schema, crawler activado |
| `memory/user_legal_status.md` | Fernando NO tiene SL ni autonomo. Necesita crear SL para VCs |
| `memory/project_funding_research.md` | OpenVC 1260 inversores, Abac Nest, TaxDown acqui-hire/partnership |
| `memory/project_session28_qa_security.md` | Sesion 28: QA 12 bugs, audit 21 issues, PageSpeed, deploy fix |
| `memory/project_session30_rag_workspaces.md` | Sesion 30: RAG fix (OOM, tildes, SSE, 84K sync), workspace RAG hibrido, facturas test |
| `memory/project_workspace_vision.md` | Vision workspace = centro operaciones autonomo. RAG hibrido (global + docs usuario) |

## Datos clave del proyecto

- **Dominio**: `impuestify.com` (NO .es)
- **Hosting**: Railway (frontend + backend). Auto-deploy ON. **1 worker** (344 MB, OOM con >1)
- **VITE_API_URL**: `https://taxia-production.up.railway.app`
- **Tests**: ~1,758 backend PASS + frontend build OK
- **Modelo LLM**: SIEMPRE gpt-5-mini. Params: `temperature=1`, `max_completion_tokens` (NUNCA `max_tokens`)
- **Upstash Vector**: 84,036 embeddings sincronizados (100%). Sync script: `scripts/sync_to_upstash.py`
- **Owner**: `fernando.prada@proton.me` (sin restricciones)
- **Test users QA**: `test.particular/autonomo/creator@impuestify.es` (Test2026!)

## Reglas de proceso

- **Post-Bugfix Protocol**: Documentar en bugfixes + agent-comms + CLAUDE.md
- **ORTOGRAFIA OBLIGATORIA**: Verificar tildes en TODOS los strings visibles al usuario
- **Territory names**: SIEMPRE canonical de `ccaa_constants.py` (con tildes). NUNCA hardcodear sin tildes
- **Railway**: 1 worker maximo. "Child process died" sin traceback = OOM killer
- **SSE streaming**: SIEMPRE enviar evento thinking ANTES de operaciones lentas (RAG, LLM)
- **Upstash Vector**: Verificar `index.info().vector_count` vs `SELECT COUNT(*) FROM embeddings` periodicamente
- **iOS file upload**: NUNCA `display:none` en inputs file — usar visually-hidden + `<label htmlFor>`
- **NUNCA** incluir ruvnet, claude-flow, Claude, Co-Authored-By en commits

## BACKLOG — Pendiente

### CRITICO — proxima sesion
- [x] ~~Generador PDF Modelos Tributarios~~ DONE (sesion 31: 7 modelos + forales, endpoint + hook + botones DeclarationsPage/M130, 8 tests)
- [x] ~~Bug: importes incorrectos en extraccion~~ DONE (sesion 31: prompt explicito + validacion magnitud + 6 tests)
- [x] ~~Bug: perdida contexto workspace en follow-ups~~ DONE (sesion 31: columna workspace_id en conversations + restauracion backend + frontend clear)

### Alta prioridad
- [x] ~~Workspace Fase 2: auto-clasificar facturas → PGC~~ DONE (sesion 31: auto-classify on upload + confirm/reclassify endpoint + badges WorkspacesPage, 34 tests)
- [x] ~~Workspace Fase 3: chat integrado por workspace~~ DONE (sesion 31: selector dropdown en Chat + indicador visual + CSS)
- [x] ~~Dropdowns: audit completo~~ DONE
- [x] ~~Limpiar prints diagnostico~~ DONE (sesion 31: 58 prints → logger en 8 archivos)

### Media prioridad
- [x] ~~RAG farmacia — normativa RE (Art. 154-163 LIVA) + guias CGCOF~~ DONE
- [ ] **Laborai acercamiento** — mensaje de partnership tech (licencia motor IA fiscal)
- [ ] Generador XBRL/ZIP para Registro Mercantil (largo plazo)

### Baja prioridad
- [ ] Integracion factura electronica (FacturaE/VeriFactu)
- [ ] App movil (React Native)
- [ ] Redesign WorkspacesPage + modals
