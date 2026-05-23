# TaxIA (Impuestify) — Memoria del Agente

> Última actualización: 2026-05-23 (sesión 44 — Demo Fiscal IA Melilla LIVE + **SEPARACIÓN proyectos: Impuestify ≠ IA-Melilla**)
> **Sesión 44 cierre 2 (2026-05-23) — SEPARACIÓN DE PROYECTOS**: el material de la demo Fiscal IA Melilla se ha movido a carpeta paralela `../IA-Melilla/` (ruta: `C:/Users/Fernando Prada/OneDrive - SVAN TRADING SL/Escritorio/Personal/Proyectos/IA-Melilla/`). Razón: son 2 proyectos distintos — Impuestify es SaaS personal completo (todo el sistema fiscal de España); IA-Melilla es demo para cliente externo (titular legal: Joaquín Gorge Lucianez, tío del CEO). Decisión arquitectónica: opción A — carpetas paralelas en disco, **backend compartido** vía rama `demo/fiscal-ia-melilla` (24 commits divergentes con switches DEMO_MODE/BRAND_NAME, frontend Melilla en repo separado `Nambu89/ia-melilla`). Movido a IA-Melilla: `Demo/`, `Marketing/`, `docs/deploy/handoff-pm-ia-melilla.md` + `coolify-melilla.md`, `docs/qa/baseline-2026-05-23-tecnico.md`, `docs/research/openwa-agente-reservas-whatsapp.md`, `plans/2026-05-20-demo-melilla-backend.md` + `qa-report-2026-03-08-melilla.md`, 2 tests E2E específicos de la demo (qa-session8b-melilla, guia-fiscal-melilla-2026-03-12), memorias `project_demo_fiscal_ia_melilla` + `feedback_demo_brand_audit` + `reference_onepager_marca_blanca` + `reference_openwa_whatsapp`. NO movido: `feedback_slowapi_param_name.md` (regla técnica genérica aplica a Impuestify también), `CeutaMelillaPage.*` (es producto Impuestify cubriendo CCAA real), `backend/tests/test_ceuta_melilla.py`, `tests/e2e/guia-fiscal-melilla.spec.ts` (test legítimo de Impuestify cubriendo Melilla CCAA), código backend. Esta rama `chore/separar-ia-melilla` parte de main para no tocar `demo/fiscal-ia-melilla` (que despliega en Coolify). Ver `../IA-Melilla/README.md` para arquitectura completa y relación entre proyectos.
> Sesión 44 cierre 1 (2026-05-23): Frontend `Nambu89/ia-melilla` conectado al backend Coolify end-to-end (chat operativo). Detectado: frontend solo expone chat — falta integrar resto de tools como páginas nativas consumiendo backend headless. Arquitectura correcta confirmada: **1 backend headless multi-tenant, N frontends**. Handoff técnico autocontenido generado para PM IA-Melilla (ahora en `../IA-Melilla/docs/deploy/handoff-pm-ia-melilla.md`). QA Playwright completo: 4 críticos detectados (chat SSE no renderiza, guía IRPF HTTP 422, /terminos-y-condiciones 404, guardarraíl filtra precios Impuestify) — baseline en `../IA-Melilla/docs/qa/baseline-2026-05-23-tecnico.md`. Research OpenWA (agente WhatsApp + Calendar) para captador leads del tío en `../IA-Melilla/docs/research/openwa-agente-reservas-whatsapp.md`. Cleanup raíz: 11+2 fragmentos paste rotos (0 bytes) borrados.
> Sesión 44 (2026-05-22): **Demo Fiscal IA Melilla LIVE**. Backend `demo/fiscal-ia-melilla` head `82510a0` (24 commits pushed). Turso DB `demo-fiscal-melilla` seedeada (5 scripts). Coolify dual-service operativo en VPS Contabo (backend `Nambu89/Impuestify` + frontend `Nambu89/ia-melilla`). DNS+TLS Let's Encrypt activos. Brand `Fiscal IA Melilla` env-driven (sin hardcodes). Stripe OFF (`SUBSCRIPTIONS_ENABLED=false`). **6 hotfixes deploy iterativos**: CSP jsdelivr Swagger (`e4f9ecb`), subscription_guard bypass (`8ca8556`), slowapi rate-limiter rename `req`→`request` (`8eec52c`), refs residuales chat_stream (`af205b5`), warmup+defensia brand (`7c393cb`), topic classifier bypass DEMO_MODE (`82510a0`). Ver `project_demo_fiscal_ia_melilla.md` para cadena completa. **Lección 1**: slowapi inspecciona params por nombre — primer param HTTP handler decorado con `@limiter.limit(...)` DEBE llamarse `request: Request`. **Lección 2**: bifurcar a demo brandeada requiere auditar TODOS los strings user-facing (system prompts, warmup, rejection messages, /health) — no basta poner `BRAND_NAME` en config. **Lección 3**: clasificadores upstream (topic classifier) deben tener bypass DEMO_MODE para no rechazar mensajes legítimos del demo restringido.
> Sesión 43 (2026-05-19): One-pager comercial marca blanca generado (movido a `../IA-Melilla/Marketing/`). Colores Impuestify (#1e40af navy + #06b6d4 cyan + #3b82f6 sky + crema #faf7f2). 9 herramientas grid 3×3, value-prop banner, coverage CCAA pills, 4 diferenciadores, 5 stats, CTA cyan. Sin placeholders, sin Impuestify visible. Generado vía Chrome headless print-to-pdf. Workaround OneDrive: render a `C:/tmp/` + `cp` final.
> Sesión 43 (2026-05-18): Quality Gates Phase 1 MERGEADO A MAIN — commit `f68afef`. ruff (backend, 0.6.9) + eslint v9 flat config + prettier 3.3.3 + 12 pre-commit hooks + CI workflow `.github/workflows/ci.yml` con 5 jobs paralelos. Branch `claude/quality-gates` borrada tras squash-merge PR #16. Baselines tolerados Phase 1: ruff 179 violations (`--exit-zero`), eslint 234 warnings (`--max-warnings 256`), ~30 errores TS pre-existing (typecheck soft-fail). Cleanup tracking: issue #14 (eslint→0) + #15 (ruff→0 + typecheck cleanup). Fix bonus: react-is@18.3.1 peer dep faltante de recharts 3.x. **Lección crítica anti-whitewashing**: si necesitas tolerar baseline, usa flag de tolerancia en runner (`--exit-zero`, `--max-warnings`, `continue-on-error`), NUNCA desactives reglas globalmente (Task 10 fix `5ff643e` revirtió 12 ignores globales que ocultaban F821=undefined name + otros). **Lección scope creep**: spec reviewer detectó bundling config+fixes (Task 6) → split obligatorio antes de aceptar. **Cada commit ahora gateado por pre-commit local + CI 5/5 verde antes de merge.**
> Sesión 42 (2026-05-17): catálogo legal +12 normas + tool Scrapling.
> Sesión 42: Hallazgo clave: backlog "BOE links chat (P0)" YA estaba HECHO end-to-end (schema + URLs + CitationEnricher + pipeline + frontend MdAnchor — 16/16 tests PASS). Trabajo real: ampliar `backend/data/legal/norms.yaml` de 25 → **37 normas** (+48%). 8 estatales vía BOE API (L39_2015, L40_2015, RDL_26_2021, RDL_13_2022, RDL_19_2021, RD_1007_2023 VeriFactu, RDL_4_2024, L20_1990 cooperativas) + TRIGIC_CANARIAS (DLeg 1/2025 IGIC/AIEM, BOC 207/2025 PDF, encontrado iterando 207 sumarios BOC con Scrapling Fetcher) + 3 más vía doc-crawler (L8_1991_IPSI Ceuta/Melilla, L13_1996 medidas fiscales, L35_2015_BAREMO daños). Tests legal/ 124/124 PASS, validate_norms 37/37 OK. Commits: f0f1576 + 912c3d4 + 6aa0eb0 (todos en main pushed). **Lección crítica**: WebFetch genérico falla anti-bot en portales territoriales; Scrapling local del proyecto (Fetcher HTTP + StealthyFetcher Chromium/patchright) sí pasa. doc-crawler v2 falló por añadir URLs homepage en lugar de texto consolidado — REVERTIDO (zero-invention violation). Tool nueva `scripts/find_norm_in_portal.py` reutilizable. Pendiente PM: NF forales IRPF/IS (Bizkaia/Gipuzkoa/Araba) + LF IRPF Navarra + DLeg autonómicos ITPAJD/ISD — requieren URL específica del texto consolidado vigente (no portal genérico).
> Sesión 40 (FINAL — backlog cerrado): Sprint completo en 8 waves A-H. Catálogo TOTAL: **15 modelos VERDE** (12 originales + 309 + 450 + 455). **~960 tests nuevos** sesión 40 (~520 modelos waves A-C + ~320 waves D-H + 4 commits docs/audit). 9 commits atómicos en main. Backlog próxima sesión: estilos frontend wizards M349/M390 mejoras, lista oficial Anexo IV TR Decreto 1/2025 AIEM (ATC anti-bot), tool LLM 303 exponer nuevos params P1/P2, prorrata especial 303, PDF rotular nuevas secciones 303, plazos Bizkaia/Araba 130 verificación Orden Foral.
> Sesión 40 (POST-FIX waves A-C): 3 waves paralelas — **A** (7 fixes aislados), **B** (4 from scratch + refactor 303), **C** (2 refactors normativa Ley 7/2024 + Decreto Legislativo 1/2025). 12/12 modelos VERDE. Drift tool/calculator eliminado. Modelo 309 nuevo (RE intracom). Master v2: `docs/audits/MASTER_VALIDATION_2026-05_v2_POST_FIX.md`. Reglas nuevas: tool LLM=wrapper de calculator, parametrización por ejercicio, no anunciar sin implementar.
> Sesión 40 (waves D-H): **D** frontends M131/M309/M349/M390 + endpoints REST + rutas (build PASS). **E** Forales 131 (4 calculators Bizkaia/Gipuzkoa/Araba/Navarra + tool router único + PDF foral, 75 tests). **F** 303 P1/P2 (RECC, SII, ISP 7 supuestos, mod bases 5 conceptos, transitorios 0/2/5/7.5%, RE detector ampliado, 30 tests). **G** 200 IS gaps MEDIA (reserva nivelación, tributación mínima Art.30 bis, cooperativas 20%, I+D 42% exceso, ZEC techo empleos, cinematográficas, pago fraccionado mín DA 14ª, 48 tests). **H** AIEM 450 + 455 Canarias (102 tests, lista Anexo IV pendiente).
> Sesión 40 (AUDIT): Auditoría documental masiva disparada por petición de Alfredo (CEO AyudaTPymes). 12 subagentes paralelos auditaron Modelos 100, 130, 131, 200 IS, 303, 308, 349, 390, 420 IGIC, 720, 721, IPSI contra normativa AEAT vigente. **71 gaps detectados** (18 críticos, 19 altos, 26 medios, 8 bajos). 1 VERDE (100), 4 AMARILLO (130, 720, 721, IPSI), 1 NARANJA (200 IS), **6 ROJO** (131/349/390 sin implementar pero anunciados, 303 drift tool/calculator, 308 confundido con 309, 420 tipos derogados). Reports: `docs/audits/`. Master v1: `docs/audits/MASTER_VALIDATION_2026-05.md`. Bugs 89-98 documentados en `bugfixes-2026-05.md`.
> Sesión 39: 11 vídeos verticales 1080x1920 generados con skill `hyperframes` (HeyGen). 5 nuevos (clasificador, guia-fiscal, modelo303, workspace, notif-aeat, payslip) + 2 re-renderizados (chat, retenciones — fix logo estirado por flex `align-items` faltante). Bugs sesión 38 (85-88) desplegados y verificados en producción. anime.js v4.4 evaluada para microinteracciones frontend (decisión adopción pendiente).
> Sesión 38: Bug 85 (topic classifier context-aware) + 86 (AsyncRedis await) + 87 (PII detector resilience) + 88 (logs duplicate-column). DESPLEGADO 2026-05-10.
> Sesión 37: Sprints 1+2+3 seguridad — pipeline 6 capas, RAG spotlighting, citation verifier, token budget, passkeys WebAuthn, refresh rotation, NIS2 runbook, AESIA self-assessment.
> Tests: ~2,080 PASS. Caveman activo.
> Crons Railway: cron-cost-anomaly, cron-purge-trails, cron-rag-quality.
> Docs RAG: 463 ingestados (sesión 34). Repo `docs/`: ~516 archivos. Próxima ingesta tras Manual Renta 2025 publicado por AEAT (~abril 2026).

## Indice de archivos de memoria

| Archivo | Contenido |
|---------|-----------|
| `memory/backend-subscription.md` | Stripe: Particular 5 €/mes, Creator 49 €/mes, Autónomo 39 €/mes IVA incl. |
| `memory/crawler-state.md` | Crawler automatizado: 90 URLs, 23 territorios, Scrapling |
| `memory/frontend-features.md` | UX/Streaming, PWA, Landing, DeductionCards, Cookies, Admin, Feedback |
| `memory/bugfixes-2026-03.md` | 64 bugs fixeados marzo 2026 (Bugs 1-64) |
| `memory/bugfixes-2026-05.md` | Bugs 85-88 sesión 38 + Bugs 89-98 sesión 40 (auditoría modelos vs AEAT) |
| `docs/audits/MASTER_VALIDATION_2026-05.md` | **Master report sesión 40 v1** — auditoría 12 modelos vs AEAT, 71 gaps, plan P0/P1/P2 |
| `docs/audits/MASTER_VALIDATION_2026-05_v2_POST_FIX.md` | **Master v2 POST-FIX** — 12/12 VERDE, 613 tests nuevos, 13 modelos (+ 309 nuevo) |
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
| `memory/feedback_secrets_prevention.md` | CRITICO: NUNCA commitear secrets/passwords. Verificar antes de cada git add. Incidente sesion 17 |
| `memory/feedback_no_claude_references.md` | CRITICO: NUNCA incluir ruvnet, claude-flow, Claude en commits ni push. Limpiar antes de push |
| `memory/feedback_ruflo_always_route.md` | SIEMPRE rutear tareas por RuFlo (hooks_route + agent_spawn) antes de delegar a subagentes |
| `memory/project_security_audit_stack.md` | Plan seguridad: Bandit+Semgrep+ZAP+Nuclei+Trivy (4 capas, $0). PentestGPT descartado |
| `memory/feedback_requirements_sync.md` | SIEMPRE sincronizar pip install con requirements.txt. Incidente sesion 17: 4 deploys fallidos |
| `memory/project_branding_update.md` | Sesion 18: nuevo logo, favicon escudo IA, header blanco, colores corporativos |
| `memory/project_google_oauth.md` | Google OAuth verification: privacy link fix + robots.txt + sitemap.xml |
| `memory/project_rag_quality.md` | RAG quality dashboard: admin page + evaluador ligero (en implementacion sesion 18) |
| `memory/project_crawler_upgrade_s19.md` | Sesion 19: Scrapling, ciclos reintento, 19 BOE IDs corregidos, ingesta masiva |
| `memory/project_session20_simulador_audit.md` | Sesion 20: renta imputada, perdidas, 5 XSD gaps, 160 deducciones CCAA, Agent Lightning SKIP |
| `memory/reference_azure_di.md` | Azure Document Intelligence: endpoint + API key para ingesta RAG |
| `memory/project_session21_deductions_complete.md` | Sesion 21: 408 deducciones 2025 (9 CCAA + 4 forales), frontend XSD, plan GP |
| `memory/reference_openclaw_social.md` | OpenClaw: formato JSON completo, reglas, stats, pilares, workflow. LEER ANTES de generar contenido |
| `memory/project_social_media_published.md` | Registro de 20 publicaciones generadas sesion 23 + temas pendientes para futuros batches |
| `memory/feedback_sync_all_memories.md` | OBLIGATORIO: sincronizar memory/ + MEMORY.md + RuFlo HNSW en CADA actualización |
| `memory/feedback_check_bugs_first.md` | SIEMPRE revisar bugfixes y correcciones previas antes de dar datos factuales al usuario |
| `memory/project_session24_docs_update.md` | Sesión 24: Manual Usuario v2.0 + Business Plan v2.0 actualizados con todas las features |
| `memory/project_session25_column_a.md` | Sesión 25: 5 features Claude Code (territories, cost tracker, memory LLM, semantic window, warmup) |
| `memory/project_session25_contabilidad_research.md` | Sesión 25: Research contabilidad PGC, farmacias, Registro Mercantil, modelos por territorio |
| `memory/project_phase3_gemini_invoices.md` | Phase 3: Gemini 3 Flash Vision para OCR facturas + contabilidad PGC + libros Registro Mercantil |
| `memory/project_session26_phase3.md` | Sesion 26: Phase 3 completa — OCR, PGC, asientos, libros, frontend, 56 tests |
| `memory/project_session27_seo_overhaul.md` | Sesion 27: SEO overhaul, useSEO hook, 12 paginas schema, Home 3 pricing cards, crawler activado |
| `memory/user_legal_status.md` | Fernando NO tiene SL ni autonomo. Necesita crear SL para recibir inversion de VCs |
| `memory/project_funding_research.md` | OpenVC 1260 inversores, Abac Nest (mejor fit), TaxDown acqui-hire/partnership, mensajes LinkedIn listos |
| `memory/project_session28_qa_security.md` | Sesion 28: QA 12 bugs, audit 21 issues, PageSpeed, chat.py crash, deploy fix, secrets rotados |
| `memory/project_bug_upload_mobile_prod.md` | BUG ABIERTO: upload facturas "Failed to fetch" en produccion movil — POST nunca llega al backend |
| `memory/project_session33_defensia_part2.md` | Sesion 33: DefensIA Parte 2 completa — Wave 2B backend + Wave 1F/2F frontend + Copilot rounds 1+2 (16/16) + 5 gap fixes end-to-end |
| `memory/project_session34_defensia_fixtures_copilot3.md` | Sesion 34: T3-001b fixtures PDF caso David (reportlab) + Copilot round 3 (11/11) + cleanup 58 archivos basura |
| `memory/project_session34_modelo200_is.md` | Sesion 34 cont: Modelo 200 IS completo — simulador 7 territorios, 47 tests, endpoints, workspace prefill, tool, PDF, frontend wizard |
| `memory/feedback_caveman_rules.md` | Caveman plugin activo — NO comprimir docs/memory espanol, solo conversacion |
| `memory/feedback_research_first.md` | OBLIGATORIO: WebFetch docs antes de proponer pasos UI o pruebas en Stripe/Railway/etc. No inventar nombres de botones desde memoria |
| `memory/feedback_never_delete_users.md` | PROHIBIDO: nunca DELETE FROM users ni endpoints que lo disparen. CASCADE borra feedback + conversaciones + perfil. UPDATE status, no DELETE |
| `memory/project_session36_gabriel_webhooks.md` | Sesion 36: incidente Gabriel + webhooks Stripe + notif feedback owner + fix MultiPagadorForm. CLI Stripe + reglas nuevas |
| `memory/project_social_media_status.md` | Estado social media post-OpenClaw (retirado 2026-05-04). YouTube nuevo canal recomendado @impuestify Brand Account |
| `memory/project_session37_security_overhaul.md` | Sesión 37: Sprints 1+2+3 seguridad completos. 18 mejoras (9 P0 + 8 P1 + 1 P2). Pipeline 6 capas, passkeys, refresh rotation, NIS2, AESIA |
| `memory/project_session39_videos_marketing.md` | Sesión 39: 11 vídeos verticales HyperFrames + bug logo estirado fixeado + research anime.js + paleta Pantone + prompt Gemini Imagen heros |
| `memory/reference_hyperframes_skill.md` | Skill HyperFrames (HeyGen) — pipeline HTML+GSAP+Chromium → MP4 1080x1920. Anti-bug logo estirado (`align-items: center` obligatorio). 11 demos vivos |
| `memory/reference_animejs_library.md` | anime.js v4.4 evaluada (post midudev). ~10 KB gz, ESM tree-shakeable. Encaja para microinteracciones (calculadoras, DeductionCards). Decisión pendiente |
| `memory/feedback_read_before_fix.md` | **CRITICO sesion 41**: leer TODO config + comentarios + doc oficial ANTES de fix deploy/infra. Bug 100 (purge RAG por error) + .python-version en root sin ver Root Directory=/backend |
| `memory/feedback_no_hardcode_legal.md` | **CRITICO sesion 41**: NUNCA hardcodear corpus legal (leyes/articulos/plantillas factura) en Python. Siempre YAML/SQL con Protocol+Pydantic. Antipatron detectado por user, refactor a `backend/data/legal/` + `app/services/legal/` |
| `memory/pm_legal_catalog_maintenance.md` | **PM TASK sesion 42**: catalogo `backend/data/legal/norms.yaml` lo mantiene PM, no developer. Procedimiento añadir normas via `scripts/add_norm.py` (verificacion en vivo BOE/BOPV/URL). Validacion CI con `validate_norms.py`. Detectar reformas con `sync_boe_recent.py` |
| `memory/feedback_only_official_sources.md` | **CRITICO sesion 42**: PROHIBIDO Wikipedia/blogs/Google Scholar para datos legales/fiscales. Solo BOE/BOPV/BOC/BOJA/DOGC/portales forales/AEAT. Si fuente oficial bloqueada → NOT_FOUND, no buscar alternativa no oficial |
| `memory/feedback_no_browser_console.md` | **CRITICO**: NUNCA pedir al user que abra F12/DevTools/console del navegador. User no puede/no quiere. Verificar siempre server-side (curl bundle JS, grep, Playwright). Anti-patron: "abre console y escribe...". Patron correcto: "pásame URL y verifico via curl" |
| `memory/feedback_karpathy_principles.md` | Sesion 42+: cherry-pick andrej-karpathy-skills — state assumptions, push back simpler, imperative→declarative TDD-first, match existing style, mention dead code don't delete, every line traces to request |
| `memory/project_session43_quality_gates.md` | **Sesión 43 (2026-05-18)**: Quality Gates Phase 1 — ruff + eslint v9 + prettier + pre-commit + CI 5 jobs. Branch `claude/quality-gates`, PR #16. Issues #14+#15 tracking Phase 1.5 cleanup. Anti-whitewashing lesson + scope-creep lesson |
| `memory/feedback_slowapi_param_name.md` | **CRÍTICO sesión 44**: slowapi inspecciona params por nombre. Handler con `@limiter.limit(...)` DEBE tener `request: Request` (no `req`). Body Pydantic = `body`/`data` (regla genérica aplica a Impuestify) |
| **`../IA-Melilla/README.md`** | **Sesión 44 cierre 2 (2026-05-23)**: proyecto IA-Melilla SEPARADO a carpeta paralela. Demo cliente externo (titular legal Joaquín Gorge Lucianez). Backend compartido vía rama `demo/fiscal-ia-melilla`. Material movido fuera de TaxIA: Demo/, Marketing/, docs deploy+QA+research, plans, memorias específicas del proyecto demo |
| `.claude/skills/grill-me/SKILL.md` | Skill `grill-me` (mattpocock MIT): entrevista relentless sobre un plan o disenno antes de implementar. Mas estricto que brainstorm |
| `.claude/skills/diagnose/SKILL.md` | Skill `diagnose` (mattpocock MIT): 6 fases para bugs duros. Construir feedback loop primero, luego hipotesis ranqueadas |
| `.claude/skills/improve-codebase-architecture/SKILL.md` | Skill `improve-codebase-architecture` (mattpocock MIT): identificar deepening opportunities, modulos shallow vs deep, deletion test |

## Datos clave del proyecto

- **Dominio**: `impuestify.com` (NO .es). Verificado en Resend desde 2026-03-04
- **Hosting**: Todo en Railway (frontend + backend). Auto-deploy FUNCIONANDO. NO usamos Vercel
- **Coolify evaluado y descartado** (ADR-007): 11 CVEs críticos ene-2026, beta, overhead ops. Reevaluar si Railway >50 €/mes
- **Tests**: ~1,758 backend PASS (sesion 28 verificado) + frontend build OK
- **Modelo LLM**: SIEMPRE gpt-5-mini (NUNCA gpt-4o-mini). Actualizado sesion 28
- **Security audit**: 20/21 issues resueltos (sesion 28). Shared owner_guard.py, JWT startup validation
- **RuFlo**: V3.5.42 instalado, MCP configurado, funcional
- **Owner**: `fernando.prada@proton.me` (sin restricciones)
- **Social Media**: OpenClaw RETIRADO 2026-05-04. Sin automatizacion publicacion actualmente. Decision pendiente: nueva herramienta o manual

## Motor de Deducciones IRPF — ~1008 deducciones (2026-03-25, sesion 21)

- 16 estatales + 195 territoriales v1/v2 + 339 XSD + 50 forales v1 + **408 nuevas 2025 (sesion 20+21)**
- Seeds sesion 20: `seed_deductions_{valencia,madrid,andalucia,canarias,galicia,murcia}_2025.py` (160)
- Seeds sesion 21 CCAA: `seed_deductions_{clm,asturias,cantabria,baleares,larioja,extremadura,aragon,cyl,cataluna}_2025.py` (188)
- Seeds sesion 21 forales: `seed_deductions_forales_2025.py` (60 = 15x4 territorios)
- **21/21 territorios cubiertos al 100%: 15 CCAA + 4 forales + Ceuta + Melilla. Gap: 0%**
- Pendiente: ejecutar 16 seeds en produccion Turso
- Auditorias: `plans/audit_deducciones_ccaa_2025.md` + `plans/audit_xsd_gaps_2025.md`

## Seguridad (estado actual)

- **CAPTCHA**: Cloudflare Turnstile en Login + Register (COMPLETO)
- **MFA / 2FA**: TOTP + backup codes (COMPLETO sesion 17)
- **13 capas seguridad**: rate limiting, JWT, prompt injection, PII, SQL injection, LlamaGuard4, Document Integrity Scanner, etc.
- **Password reset**: Endpoint completo con Resend. Bug 52 fix: dominio `.es` → `.com`
- **CI/CD Security**: GitHub Actions workflow (Bandit + Semgrep + npm audit). Sesion 18: arreglado

## Branding + OAuth + RAG Quality (resumen)

- **Branding** (s18): logo escudo IA, header blanco, paleta `#1a56db` / `#06b6d4` / `#0f172a`. Detalle Pantone: `project_session39_videos_marketing.md`.
- **Google OAuth**: privacy link + robots.txt + sitemap 21 URLs. Pendiente: responder email Google. Detalle: `project_google_oauth.md`.
- **RAG Quality dashboard**: /admin/rag-quality con evaluador ligero, 30 preguntas ground truth. Detalle: `project_rag_quality.md`.

## Crawler & RAG (estado 2026-05-10)

- **Repo `docs/`**: ~516 archivos. **RAG ingestados**: 463 docs (sesión 34) + corpus FAISS + Upstash Vector.
- **Crawler v2**: Scrapling anti-bot, watchlist 90 URLs (59 activas + 9 future + 20 deprecated + 2 html_only). Detalle: `crawler-state.md` y `project_crawler_upgrade_s19.md`.
- **Pendiente**: Manual Renta 2025 Tomos 1+2 + Orden HAC Modelo 100 (publicación AEAT ~abril 2026). Renta2025.xsd no publicado.
- **Para detalle por territorio + URLs concretas**: leer `crawler-state.md`.

## Feedback + Perfil + IRPF + RuFlo (resumen)

- **Feedback**: widget flotante (bug/feature/general+screenshot) + thumbs chat + admin dashboards `/admin/feedback` `/admin/contacts`. GDPR cascade en user_rights.py.
- **Perfil fiscal adaptativo** (5 regímenes, ~110 campos): CCAA naming canonical con tildes (`ccaa_constants.py`+`ccaa.ts`). Form adaptativo: `DynamicFiscalForm` + `useFiscalFields`.
- **IRPF Simulator (XSD ~100%)**: 8 sub-calculadoras (trabajo, ahorro, inmuebles, MPYF, actividades, imputed, loss, crypto_fifo). Foral vasco 7 / navarra 11 tramos, Ceuta/Melilla 60%, conjunta. Detalle: `project_session20_simulador_audit.md` + `project_session21_deductions_complete.md`.
- **RuFlo V3.5.42**: instalado, MCP no conectado (requiere reinicio CC), 13/27 hooks. ReasoningBank no funcional en Windows. Para tareas paralelas: skill `dispatching-parallel-agents`.

## Beta Testers

- Ramon Palomares (Madrid, particular, padre) — feedback UX verbosidad
- Juan Pablo Sanchez (Bizkaia, foral) — bugs workspaces + comparativa
- Jose Antonio Alvarez Solanilla — bug password reset
- Capturas/archivos SIEMPRE en `TaxIA/Errores reportados/`
- Test users QA: `test.particular@impuestify.es` / `test.autonomo@impuestify.es` / `test.creator@impuestify.es` (Test2026!)

## Reglas de proceso

- **Post-Bugfix Protocol**: Documentar en bugfixes + agent-comms + CLAUDE.md
- **ORTOGRAFIA OBLIGATORIA**: Verificar tildes en TODOS los strings visibles al usuario
- **Loading state**: TODA rama async debe hacer `setLoading(false)` — incluyendo early returns
- **Never return None silently**: En servicios backend, siempre raise ValueError
- **Dominio**: Siempre `impuestify.com`, NUNCA `.es`
- **slowapi**: Primer param DEBE ser `request: Request`, body Pydantic como `body`/`data`
- **IRPF Simulator**: EXTEND, NEVER REFACTOR. Campos nuevos con default 0/null. Tests regresion obligatorios.
- **Startup validation**: NUNCA usar raise/crash por secrets faltantes — solo warning. La app debe arrancar siempre.
- **NUNCA** incluir ruvnet, claude-flow, Claude, Co-Authored-By en commits. Verificar antes de push.
- **Tool LLM = wrapper de calculator** (regla nueva sesión 40): NUNCA reimplementar lógica de cálculo en `app/tools/modelo_*.py`. El tool debe llamar al `Modelo*Calculator` del service. Drift detectado en 303 y 130 → 13+14 bugs.
- **No anunciar modelos sin implementar** (regla nueva sesión 40): ningún modelo aparece en marketing público (Home, Pricing, Farmacias) hasta tener tool + tests + PDF. Riesgo LGDCU Art. 5/7.
- **Reformas fiscales mayores → audit interno obligatorio**: cada Ley/Decreto Legislativo que toque tipos, escalas o umbrales dispara revisión de modelos afectados ANTES de la siguiente campaña.

## BACKLOG — Pendiente

### Alta prioridad (sesión 41 — derivada auditoría sesión 40)

**P0 BLOQUEANTE (acción inmediata, riesgo regulatorio/comercial)** — TODO HECHO (verificado sesión 42):
- [x] ~~Retirar 131/349/390 marketing~~ → Calculators + tools + tests + frontends + PDFs implementados (Wave D sesión 40)
- [x] ~~Modelo 200 IS Ley 7/2024~~ → `is_scales.py` parametrizado, microempresa 17/20% (Wave G, 48 tests)
- [x] ~~Modelo 420 IGIC Decreto Legislativo 1/2025~~ → `modelo_420.py` refactored, REPEP 30K€
- [x] ~~Modelo 308 vs 309~~ → tools separados, anti-patrón documentado
- [x] ~~Modelo 303 refactor tool→calculator~~ → wrapper de `Modelo303Calculator`, regla en backend/CLAUDE.md

**P1 (antes próxima campaña)** — TODO HECHO (verificado sesión 42):
- [x] ~~Modelo 100 ahorro 2025 14%→15%~~ → `populate_tax_parameters.py` + `test_irpf_ahorro_2025.py` (Bug 98)
- [x] ~~Modelo 130 Sección II agrícola + dispensa 70%~~ → `_build_seccion_ii_response`, Art. 109.2/3 dispensa
- [x] ~~Modelo 720 cese de titularidad + subtipos A-F~~ → params `ceses_titularidad` + `subtipos`
- [x] ~~Modelo 721 sucursales españolas exchanges~~ → `exchanges_via_sucursal_espanola` + lista actualizada
- [x] ~~IPSI prorrata Q4 + restricted_mode Particulares~~ → `PARTICULAR_CASES` whitelist, lógica trimestre 4

**Otras pendientes**:
- [x] ~~**Demo Fiscal IA Melilla — Task 0b + deploy Coolify**~~ **DONE 2026-05-22 sesión 44**. Backend `demo/fiscal-ia-melilla` head `82510a0` (24 commits). Turso `demo-fiscal-melilla` seedeada (5 scripts). Coolify dual-service operativo Contabo (backend + frontend `Nambu89/ia-melilla`). DNS+TLS Let's Encrypt activos. 6 hotfixes deploy iterativos aplicados. Ver `project_demo_fiscal_ia_melilla.md`
- [ ] **Integración tools demo Melilla en frontend `Nambu89/ia-melilla`** — handoff entregado a PM IA-Melilla 2026-05-23 (doc en `../IA-Melilla/docs/deploy/handoff-pm-ia-melilla.md`). Fase 1 (4 tools públicas: net-salary, withholding, estimate, deductions/discover) sin auth ~2-3h. Fase 2 (chat) ya hecho. Fase 3 (tools auth: workspace, invoices OCR, payslips, modelos AEAT, defensia, plusvalía) segunda iteración. PM IA-Melilla necesita pasar URL frontend a Fernando para añadir a `ALLOWED_ORIGINS` CORS backend
- [ ] **Subir vídeos a redes** (TikTok / Reels / LinkedIn / Shorts) — pipeline manual desde `videos/<demo>/renders/`
- [ ] **Compartir auditoría con Alfredo (CEO AyudaTPymes)** junto con vídeos — `docs/audits/MASTER_VALIDATION_2026-05.md` como prueba de rigor técnico
- [ ] **Decisión adopción anime.js v4.4** — empezar por `/calculadora-retenciones` y `/calculadora-neto` si SI
- [ ] **DEFENSIA_STORAGE_KEY** en Railway — sin esto uploads DefensIA devuelven 503
- [ ] **Seed pharmacy deductions** en producción Turso
- [ ] **Settings.tsx UI gestionar passkeys** — endpoints existen, falta UI register/list/delete
- [ ] **Admin UI reasoning_trail** — datos en `reasoning_trails`, falta visor admin
- [ ] **Página /transparencia-ia pública** — AESIA Guide 14 lo recomienda
- [ ] **Dropdowns: audit completo** — verificar TODOS los selects en TaxGuidePage y DynamicFiscalForm
- [ ] Arreglar railway.toml — crear ficheros válidos en backend/ y frontend/

### Tech debt sesión 41 (refactor data-driven legal registry)
- [ ] **Migrar `backend/data/legal/*.yaml` a tabla Turso `legal_norms` + `legal_articles`** cuando el catálogo crezca >200 leyes / >2000 artículos. Implementación: añadir `SqlLegalNormsRegistry(LegalNormsRegistry)` impl y cambiar `get_legal_registry()`. Sin tocar callers (Protocol pattern). Ver `backend/app/services/legal/README.md`.
- [ ] **Admin UI para editar `legal_norms.yaml` / `articles.yaml`** — endpoint owner-only que valida pydantic + commit automático a git. Permitiría que un fiscalista mantenga el catálogo sin tocar repo.
### BOE API Datos Abiertos — usos priorizados (sesión 42+)

API oficial verificada 2026-05-17: pública gratuita sin auth, JSON/XML via Accept header.
- Base URL: `https://boe.es/datosabiertos/api/`
- Endpoints: `/legislacion-consolidada`, `/boe/sumario/{yyyymmdd}`, `/borme/sumario/{yyyymmdd}`
- Docs: https://www.boe.es/datosabiertos/api/api.php + PDFs `APIconsolidada.pdf`, `APIsumarioBOE.pdf`
- MCP comunitario alternativo: `ComputingVictor/MCP-BOE`

**Roadmap por valor/esfuerzo**:

- [x] ~~**[Sesión 42 P0] Links BOE en respuestas chat**~~ → YA HECHO end-to-end (descubierto sesión 42): schema `url_html_consolidada` + 37 normas con URLs + `CitationEnricher` parsea Ley/RD/Art.X+LIVA → markdown links + pipeline `chat_stream.py:790` + frontend `MdAnchor` open new tab + ExternalLink icon. 16/16 tests `test_citation_enricher.py` PASS.

- [ ] **[Sesión 42 P0] Citation verifier consulta BOE API** — combinable con el anterior (1 día). Cuando un artículo NO está en `articles.yaml` whitelist, consultar BOE API en background (cache LRU+Turso 30 días) para verificar existencia + vigencia. Si BOE responde derogado → flag al usuario. Refuerza el citation verifier sin engordar el YAML.

- [ ] **[Sesión 42 P1] Sumarios diarios → Calendar/Deadlines** — cron diario lee `/boe/sumario/{today}` (1-2 días). Detecta publicaciones tipo "Orden HAC X/2026 — Modelo 303 plazo 2026" y actualiza `calendario.py` deadlines automáticamente. Hoy se hace manual.

- [ ] **[Sesión 43+ P1] Alertas push de reformas que afecten al usuario** — diferenciador grande (3-5 días). Cron semanal cruza publicaciones BOE relevantes con perfil fiscal del usuario (CCAA, régimen, IAE, modelos presentados). Push notification: "Publicada reforma X que afecta tu Modelo Y. Revisamos tu última declaración."

- [ ] **[Sesión 43+ P2] Auditoría vigencia DefensIA** — cuando DefensIA construye argumentos para recursos TEAR, validar contra BOE API que cada artículo citado sigue vigente (no derogado entre fecha hecho y fecha recurso). Crítico para recursos exitosos. Esfuerzo: 2 días, depende de evolución DefensIA.

- [ ] **[Sesión 44+ P2] Newsletter fiscal semanal automatizado** — resumen LLM de publicaciones BOE relevantes para autónomos/empresas/particulares (5-7 días con templates). Resend → email. Engagement + SEO + autoridad de marca.

- [ ] **[Cuando >50 normas en YAML] Sync automático norms.yaml** — cron semanal abre PR GitHub con diff sugerido al articulado de nuestras normas. Reduce mantenimiento manual a revisar/mergear PRs. Esfuerzo: 2-3 días.

- [ ] **[Cuando registry crezca a >500 articulos] Reemplazar `articles.yaml` por consulta directa BOE API** — eliminar YAML, registry consulta API en runtime con cache agresivo (2 días). Solo cuando mantener el YAML duela más que la latencia añadida.

**Estrategia recomendada sesión 42**: empezar por **P0 #1 + #2 combinados** (links BOE + verificación vigencia, 2 días totales). Base sobre la que construir el resto.

### Pendiente sesión 43+ (cerrado sesión 42)

**Catálogo legal — normas que doc-crawler no pudo añadir por límite técnico**:
- [ ] **NF IRPF Bizkaia/Gipuzkoa/Araba vigentes 2025** — portales JS-heavy, NF específica vigente requiere navegación humana o conocimiento experto fiscal foral. URL del texto consolidado específico (no portal genérico) imprescindible
- [ ] **LF IRPF Navarra vigente** (LF 26/2016 IS ya en YAML) — Hacienda Navarra portal
- [ ] **DLeg ITPAJD/ISD autonómicos** (Madrid, Andalucía, Cataluña, Valencia, Galicia) — BOJA/DOGC/BOCM/DOGV search UI con cookies
- Aviso PM: el patrón seguro es URL específica al texto consolidado (PDF o HTML estable), NUNCA homepage del boletín territorial. Doc-crawler v2 sesión 42 intentó shortcut con homepages → REVERTIDO (zero-invention violation)
- Procedimiento: PM aporta `sigla + nº + año + URL específica oficial verificada`; comando `python scripts/add_norm.py --url <URL>` añade en segundos
- Tool reutilizable: `backend/scripts/find_norm_in_portal.py` (Scrapling Fetcher + StealthyFetcher con patchright/Chromium ya instalado)
- [ ] **Versioning de plantillas factura por año fiscal** — `invoice_templates.yaml` añade `vigent_from/until` por entry (estructura existe en `articles.yaml`, replicar). Permite plantillas distintas para Renta 2024 vs 2025.
- [ ] **Extender registry a otros dominios** (mismo patrón): `data/ccaa/` para regímenes territoriales, `data/modelos/` para casillas/tipos AEAT, `data/tipos_iva/` para IVA general/reducido/superreducido por año.

### Completado sesión 39 (2026-05-10)
- [x] Bugs 85-88 sesión 38 desplegados y verificados en producción
- [x] Stripe webhook Gabriel reintentado y verificado 200
- [x] GitHub Actions Promptfoo nightly verde post-fix transformResponse + login-bot
- [x] 11 vídeos verticales HyperFrames generados (5 nuevos sesión 39)
- [x] Bug logo estirado fixeado en demo-chat + demo-retenciones + demo-defensia + demo-modelo200 (`align-items: center` + `display: block`). Re-render usuario confirmado para los 4
- [x] Research anime.js v4.4 documentado (`memory/reference_animejs_library.md`)
- [x] Paleta Pantone documentada + prompt Gemini Imagen para nuevas heros
- [x] `videos/` añadido a `.gitignore` — carpeta marketing local, no va a git

### Cumplimiento futuro (calendario)
- [ ] **2026-09-11**: deadline NIS2/CRA 24h vuln reporting — runbook listo en `compliance/nis2-runbook.md`
- [ ] **Q3 2026**: simulacro NIS2 anual
- [ ] **2026-11-05**: revisión semestral AESIA self-assessment

### Media prioridad
- [ ] **RAG farmacia** — ingestar normativa RE (Art. 154-163 LIVA) + guías CGCOF
- [ ] ML fiscal features (ml_fiscal_features table)
- [ ] Business Model Canvas infografía (Nano Banana — MCP no conectado)
- [ ] Generador XBRL/ZIP para Registro Mercantil (largo plazo — no hay API del RM)

### Baja prioridad
- [ ] Integracion factura electronica (FacturaE/VeriFactu)
- [ ] App movil (React Native)
- [ ] Redesign WorkspacesPage + modals
- [ ] ReasoningBank init (requiere Linux/Railway — ONNX no funciona en Windows)

### Histórico completado (sesiones 26-28)
- Sesión 26: Phase 3 (Gemini 3 Flash OCR + PGC + 56 tests + 201 cuentas seeded). Detalle: `project_session26_phase3.md`.
- Sesión 27: SEO overhaul (useSEO + 12 schemas + sitemap 21 URLs). Detalle: `project_session27_seo_overhaul.md`.
- Sesión 28: QA 12 bugs + audit 21 issues + PageSpeed + research OpenVC/TaxDown. Detalle: `project_session28_qa_security.md`.
