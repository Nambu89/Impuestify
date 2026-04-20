# TaxIA (Impuestify) — Memoria del Agente

> Ultima actualizacion: 2026-04-20 (sesion 34 + hotfixes post-merge)
> Sesion 34: DefensIA + Modelo 200 IS mergeados a main en produccion
> Bug 84 hotfix: prefix /api/ faltante en endpoints DefensIA frontend
> DefensIA back-link "Volver a inicio" anadido en las 3 paginas
> README reescrito con toque visual cliente + logo + screenshots capterra
> Cleanup: 23 fragmentos de codigo basura borrados del root, gitignore ampliado

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
| `memory/project_session32_defensia_part1.md` | Sesion 32 (2026-04-13): DefensIA Parte 1. Motor hibrido 4 fases anti-alucinacion. 58 tests, caso David ground truth |
| `memory/project_session33_defensia_part2.md` | Sesion 33 (2026-04-15): DefensIA Parte 2 COMPLETA. Wave 2B Back + Wave 1F/2F Front + Wave 3 parcial. 62 commits, 375 back + 92 front tests. Copilot 16/16 |
| `memory/project_session34_modelo200_is.md` | Sesion 34: Modelo 200 IS — simulador 7 territorios, 47 tests, endpoints, workspace prefill, PDF, frontend wizard |
| `memory/project_session34_defensia_fixtures_copilot3.md` | Sesion 34: T3-001b fixtures PDF caso David + Copilot round 3 + cleanup 58 archivos basura |
| `memory/project_session22_rag_fix.md` | Sesion 22: RAG fix completo (territory tildes, OOM, SSE, Vector sync 84K) |
| `memory/project_workspace_vision.md` | Vision workspace = centro operaciones autonomo. RAG hibrido (global + docs usuario) |
| `memory/bugfixes-2026-04.md` | Bugs Abril 2026 (65-84): clasificador, RAG crash, importes OCR, workspace, defensia, hotfix /api prefix |
| `memory/feedback_always_research_first.md` | SIEMPRE investigar antes de dar datos factuales (anti-alucinacion) |
| `memory/feedback_no_browser_console.md` | NUNCA hacer console.log con datos sensibles (PII, tokens) |

## Datos clave del proyecto

- **Dominio**: `impuestify.com` (NO .es)
- **Hosting**: Railway (frontend + backend). Auto-deploy ON. **1 worker** (344 MB, OOM con >1)
- **VITE_API_URL**: `https://taxia-production.up.railway.app` (sin `/api`, hay que anadirlo en cada call)
- **Backend API prefix**: TODOS los routers usan `prefix="/api/..."` — olvidarlo en frontend = 404 (Bug 84)
- **Tests**: ~1,800+ backend PASS + frontend build OK
- **Modelo LLM**: SIEMPRE gpt-5-mini. Params: `temperature=1`, `max_completion_tokens` (NUNCA `max_tokens`)
- **RAG**: 463 docs, 92,393 chunks, 85,587 embeddings sincronizados en Upstash Vector
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

### Alta prioridad (proxima sesion)
- [x] ~~**DefensIA merge a main**~~ DONE sesion 34 (mergeado 71+ commits)
- [x] ~~**Ingestar al RAG los 3 Manuales AEAT 2025**~~ DONE sesion 34 (463 docs, 92K chunks, 85K embeddings)
- [x] ~~**Hotfix lazy imports Modelo200Page**~~ DONE sesion 34
- [x] ~~**Bug 84 hotfix: prefix /api faltante DefensIA**~~ DONE 2026-04-20 (commit 20bf545)
- [x] ~~**DefensIA back-link "Volver a inicio"**~~ DONE 2026-04-20 (commit 8f7932c)
- [ ] **DEFENSIA_STORAGE_KEY en Railway** — sin esto uploads DefensIA devuelven 503
- [ ] **Seed pharmacy deductions en produccion Turso**
- [ ] **Investigar DR130 diseno de registro actualizado** — El historico `DR130_e2019.xls` (ejercicio 2015 version 11) ya no esta en sede. AEAT tiene ahora los disenos en `sede.agenciatributaria.gob.es/Sede/iva/pre-303/nuevo-servicio-pre303-importacion-libros-electronico/formatos-electronicos-libros-registro.html` actualizados a 01-01-2026. Accion: WebFetch esa pagina, localizar link al DR del Modelo 130 actual, actualizar watchlist. Estimado: 10 min.
- [ ] **Investigar Scrapling anti-bot fail en AEAT downloads** — En sesion 32 detectado que `check_url_exists` devuelve 200 pero `download_document` devuelve 404 para los mismos URLs tras volumen de requests. `curl` directo descarga sin problema. Probable rate limiting / fingerprint detection de Cloudflare en AEAT. Accion: reviewar Scrapling fetcher config, considerar fallback a urllib/httpx para dominio `sede.agenciatributaria.gob.es`, o pasar User-Agent manual. Estimado: 30-45 min.
- [ ] **PDFs prerrellenados desde chat** — Tool `generate_modelo_pdf` en WorkspaceAgent. El RAG calcula modelo (303/130) con datos workspace + CCAA usuario → genera PDF descargable desde el chat
- [ ] **CCAA-aware en workspace RAG** — WorkspaceAgent debe considerar CCAA del usuario (Cataluna vs PV vs Canarias vs Melilla) para modelos correctos (303/300/F69/420/IPSI)
- [ ] **Dashboard: selector de ano** — Agregar dropdown para filtrar por 2025/2026/todos en el dashboard

### Media prioridad
- [ ] **Refactoring archivos >500 lineas** — irpf_estimate.py (1340), turso_client.py (1074), chat.py (781)
- [ ] **Laborai acercamiento** — mensaje de partnership tech (licencia motor IA fiscal)
- [ ] **ML fiscal features** — ml_fiscal_features table
- [ ] Generador XBRL/ZIP para Registro Mercantil (largo plazo)

### Baja prioridad
- [ ] Integracion factura electronica (FacturaE/VeriFactu)
- [ ] App movil (React Native)

## DefensIA — Estado actual (post-merge main, sesion 34)

- **Estado**: MERGEADO A MAIN en produccion (71+ commits integrados).
- **Tests**: 375 backend + 92 frontend verdes. Build frontend OK.
- **Hotfix 2026-04-20**: prefix `/api/` anadido a los 9 endpoints DefensIA del frontend (Bug 84). Back-link "Volver a inicio" anadido a las 3 paginas.
- **Pipeline end-to-end funcional**: upload PDF → Fase 1 auto (classifier + extractor Gemini + phase detector) → POST brief → analyze SSE (reglas + RAG verifier + writer con TEAR abreviada/general segun cuota) → dictamen + escrito persistidos → ExpedientePage con tabs.
- **Regla #1 del producto**: NO arranca analisis juridico hasta que user escribe brief. Fase 1 (extraccion tecnica) SI auto-dispara al upload.
- **Invariantes**: (#2) 0 citas normativas hardcoded en plantillas Jinja2. (#multi-worker) quota reserve atomico via UPDATE condicional.
- **Alcance v1**: 5 tributos (IRPF + IVA + ISD + ITP + Plusvalia) + verificacion / comprobacion limitada / sancionador + reposicion / TEAR abreviada / TEAR general.
- **Monetizacion**: 1 / 3 / 5 expedientes/mes por plan Particular/Autonomo/Creator + 15 / 12 / 10 EUR por expediente extra.
- **Pendiente prod**: `DEFENSIA_STORAGE_KEY` en Railway (sin esto uploads devuelven 503).
- **Docs**: `plans/2026-04-13-defensia-{design,implementation-plan,implementation-plan-part2}.md`, `memory/project_session32_defensia_part1.md`, `memory/project_session33_defensia_part2.md`, `memory/project_session34_defensia_fixtures_copilot3.md`.

## Modelo 200 IS — Estado actual (sesion 34)

- **Estado**: MERGEADO A MAIN (11 commits). Hotfix lazy imports Modelo200Page aplicado.
- **Tests**: 47 tests Modelo 200 + Modelo 202.
- **Territorios**: 7 (regimen comun + 4 forales + ZEC + Ceuta/Melilla).
- **Features**: simulador IS, pagos fraccionados Modelo 202 (Art. 40 LIS), workspace prefill desde PyG contable, PDF borrador 16 casillas, frontend wizard 4 pasos.
- **Tool**: `simulate_is` integrada en TaxAgent.
- **Docs**: `memory/project_session34_modelo200_is.md`.
