# TaxIA (Impuestify) — Memoria del Agente

> Ultima actualizacion: 2026-04-13 (sesion 32)
> Sesion 32: DefensIA Parte 1 COMPLETA — nuevo modulo defensor fiscal anti-alucinacion
> Brainstorming + spec + plan + 16 tasks TDD ejecutadas en rama `claude/defensia-v1`
> 58 tests verdes, caso David (141 archivos, 4 reclamaciones) como ground truth
> Motor hibrido 4 fases: Gemini extraccion → reglas deterministas → RAG verificador → LLM redactor
> Pendiente Parte 2: 30 reglas R001-R030, RAG verificador, writer, frontend, beta

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
| `memory/project_session33_defensia_part2.md` | **Sesion 33 (2026-04-15): DefensIA Parte 2 COMPLETA. Wave 2B Back (9 servicios + 13 endpoints) + Wave 1F/2F Front (Vitest + 15+6 tasks) + Wave 3 parcial (GDPR + audits). 62 commits, 375 backend tests + 92 frontend. Copilot 16/16 resuelto. Pipeline end-to-end funcional: upload Fase 1 auto, brief POST, analyze SSE** |

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

### Alta prioridad (proxima sesion)
- [ ] **DefensIA merge a main** — Rama `claude/defensia-v1` con 62 commits, 375 backend tests + 92 frontend tests, Copilot 16/16 resuelto, pipeline end-to-end funcional. Bloqueadores para merge: (1) T3-001 E2E Playwright caso David 4 viewports con fixtures anonimizados, (2) T3-001b script anonimize_caso_david.py, (3) T3-006 verifier final, (4) beta test con David Oliva primero, (5) deploy prod: seed DEFENSIA_STORAGE_KEY env var en Railway. Ver `memory/project_session33_defensia_part2.md`
- [ ] **Ingestar al RAG los 3 Manuales AEAT 2025 descargados en sesion 32** — `docs/AEAT/IRPF/AEAT-Manual_Practico_IRPF_2025_Parte1.pdf` (7.54 MB), `_Parte2.pdf` (3.80 MB), `docs/AEAT/IVA/AEAT-Manual_Practico_IVA_2025.pdf` (6.30 MB). Total: 17.64 MB nuevos, criticos para el chat fiscal (campana renta 2025 ya activa desde 8-abr-2026). Accion: `backend/scripts/reingest_aeat.py` o ingesta selectiva de los 3 ficheros → Turso + Upstash Vector. Verificar con `python -m backend.scripts.doc_crawler --stats` que inventario refleja docs nuevos. Ver `memory/crawler-state.md`.
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

## DefensIA — Estado actual (sesion 33)

- **Rama**: `claude/defensia-v1` (62 commits, NO mergeada a main)
- **Tests**: 375 backend + 92 frontend verdes
- **Wave 2B Backend COMPLETO**: rate_limits, storage AES-GCM+zstd, quota reserve-commit-release atomico, RAG verifier 0.7, writer + 9 plantillas Jinja2, export DOCX/PDF, service fachada, agent con guardrails, router 13 endpoints
- **Wave 1F+2F Frontend COMPLETO**: Vitest + RTL + jsdom, types, 11 componentes, 6 hooks SSE/blob, 3 pages con dark theme, Header dropdown entry, App.tsx lazy routes
- **Wave 3 PARCIAL**: GDPR cascade 7 tablas, ortografia audit (87 tildes fixed), anti-hallucination audit (invariante #2), dead code removal. Pendiente T3-001 E2E Playwright + T3-006 verifier final
- **Pipeline end-to-end funcional**: upload PDF -> Fase 1 auto (classifier + extractor Gemini + phase detector) -> POST brief -> analyze SSE (reglas + RAG verifier + writer con TEAR abreviada/general segun cuota) -> dictamen + escrito persistidos -> ExpedientePage con tabs
- **Copilot resuelto 16/16**: 2 rondas, 10 bugs CRITICAL fixeados (rules engine enums, phase detector SANCIONADOR + naive datetime, writer REPOSICION, migrations fail-fast, quota user-binding + atomic multi-worker)
- **Security**: Bandit B701 silenciado (writer markdown no HTML), axios CVE SSRF parcheado
- **Motor hibrido 4 fases OPERATIVO**: Fase 1 extraccion automatica tras upload + Fases 2-4 tras brief explicito (regla #1 preservada)
- **Regla #1 del producto**: NO arranca analisis juridico hasta que user escribe brief. Fase 1 (extraccion tecnica) SI auto-dispara al upload
- **Invariante #2 anti-alucinacion**: 0 citas normativas hardcoded en plantillas Jinja2 (script auditor verifica)
- **Invariante multi-worker**: quota reserve usa UPDATE condicional atomico con rowcount check (no TOCTOU)
- **Alcance v1**: 5 tributos (IRPF+IVA+ISD+ITP+Plusvalia) + verificacion/comprobacion limitada + sancionador + reposicion/TEAR abreviada/general
- **Monetizacion**: 1/3/5 expedientes/mes por plan Particular/Autonomo/Creator + 15/12/10 EUR extra
- **Docs**: `plans/2026-04-13-defensia-{design,implementation-plan,implementation-plan-part2}.md` + `memory/project_session32_defensia_part1.md` + `memory/project_session33_defensia_part2.md`
