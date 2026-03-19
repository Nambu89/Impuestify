# TaxIA — Memoria del Agente

> Ultima actualizacion: 2026-03-19 (sesion 15)
> Ver detalles en archivos separados por tema
> Bugs fixeados: `memory/bugfixes-2026-03.md` (62 bugs documentados, sesion 13)

## Indice de archivos de memoria

| Archivo | Contenido |
|---------|-----------|
| `memory/MEMORY.md` | Este indice + resumen de cada area |
| `memory/backend-subscription.md` | Stripe: Particular 5 EUR, Creator 49 EUR, Autonomo 39 EUR |
| `memory/crawler-state.md` | Estado del crawler + drift analyzer (90 URLs, 23 territorios, Influencers+Creadores docs) |
| `memory/frontend-features.md` | UX/Streaming, PWA, Landing, DeductionCards, Cookies, Admin, Feedback, CreatorsPage, SEO-GEO, AdminDashboard |
| `memory/bugfixes-2026-03.md` | Bugs fixeados marzo 2026 (62 bugs documentados, sesion 13) |
| `memory/mcp-design-tools.md` | Google Stitch + Nano Banana MCP config y modelos Gemini 3 |
| `memory/response-quality-gap.md` | Analisis calidad respuesta vs Google/Claude — plan de mejora |
| `memory/agent-system-improvements.md` | Mejoras GSD al sistema multi-agente (2026-03-08) |
| `memory/awesome-claude-code.md` | Integracion herramientas awesome-claude-code (2026-03-08) |
| `memory/aeat-docs-integration.md` | Integracion docs AEAT: casillas, XSD, XLS, VeriFactu (2026-03-08) |
| `memory/project_creators_segment.md` | Segmento Creadores de Contenido: 3 planes, TaxAgent contexto, roles adicionales |
| `memory/project_upgrade_downgrade.md` | CRITICO: Validar plan Stripe compatible al cambiar roles — proxima sesion 13 |
| `memory/beta_testers.md` | 4 beta testers activos (Ramon, Juan Pablo, Jose Antonio, Maria) |
| `memory/feedback_ortografia_pre_push.md` | Regla obligatoria: verificar tildes ANTES de push — reputacion marca |
| `memory/reference_mission_control.md` | Herramienta futura: dashboard orquestacion 6 agentes IA |

## Arquitectura del proyecto

- Backend: `backend/app/` — FastAPI + OpenAI function calling
- Frontend: `frontend/src/` — React 18 + Vite 5 + TypeScript
- Docs RAG: `docs/` — 439 archivos organizados por territorio
- Agent comms: `agent-comms.md` (raiz) — canal inter-agentes
- Skills: `.claude/skills/` — 10 modulos (6 dominio + 4 desarrollo)
- Subagentes: `.claude/subagents/` — 6 agentes (backend, frontend, python, docscrawler, plan-checker, verifier)
- Hooks: `.claude/hooks/` — bash-gate.js + quality-check.js
- Commands: `.claude/commands/` — 20 slash commands

## Guia Fiscal Interactiva (COMPLETO) — 2026-03-06

- Ruta: `/guia-fiscal` (lazy, protected, en Header nav)
- 7 pasos: personal, trabajo, ahorro, inmuebles, familia, deducciones, resultado
- LiveEstimatorBar: sticky bottom (mobile) / sidebar (desktop), verde=devolucion, rojo=pagar
- Endpoint: POST `/api/irpf/estimate` — sin LLM, ~50-100ms, registrado en main.py
- Simulador: `app/utils/irpf_simulator.py` — Phase 1 + Phase 2
- Hooks: `useIrpfEstimator` (debounce 600ms) + `useTaxGuideProgress` (localStorage)
- Fuente XSD: Renta2024.xsd (sede.agenciatributaria.gob.es, Diseno Registro DR_100_199)

### Phase 1 (implementado)
- Planes de pensiones (Art. 51-52): reduce BI general, max 1.500/8.500 EUR
- Hipoteca pre-2013 (DT 18a): 15%, max base 9.040 EUR = 1.356 EUR deduccion
- Maternidad (Art. 81): 1.200 EUR/hijo <3 + 1.000 EUR guarderia
- Familia numerosa (Art. 81bis): 1.200/2.400 EUR
- Donativos (Art. 68.3 + Ley 49/2002): 80% primeros 250 + 40/45% exceso
- Retenciones completas: trabajo + ahorro + alquiler

### Phase 2 (implementado)
- Tributacion conjunta (Art. 84): reduccion 3.400/2.150 EUR
- Alquiler vivienda habitual pre-2015 (DT 15a): 10,05%, max base 9.040 EUR
- Rentas imputadas inmuebles (Art. 85): 1,1%/2% valor catastral

## Motor de Deducciones IRPF (~554 deducciones en BD)

- 16 estatales + 192 territoriales v1/v2 + 339 XSD oficiales + 50 forales = **~554 deducciones**
- **XSD Modelo 100**: 339 deducciones oficiales AEAT (seed_deductions_xsd.py, tax_year=2024)
- **Forales v2**: 50 activas (Araba 15, Bizkaia 11, Gipuzkoa 11, Navarra 13)
- Forales: sistema IRPF propio, NO incluyen estatales
- `build_answers_from_profile()`: bridge automatico perfil → deduction answers
- Seeds: `seed_deductions.py` + `_territorial.py` + `_v2.py` + `_xsd.py` + `_forales_v2.py` + `seed_estatal_scale.py` + `seed_foral_scales.py`

## Suscripciones Stripe (COMPLETO — TRIPLE PLAN)

> Detalles: `memory/backend-subscription.md`

- Plan Particular: 5 EUR/mes | Plan Creator: 49 EUR/mes | Plan Autonomo: 39 EUR/mes IVA incl.
- Owner: `fernando.prada@proton.me` (sin restricciones)
- 15+ usuarios existentes: grace_period hasta 31/12/2026
- Segmento Creator: influencers, streamers, YouTubers, bloggers, creadores audiovisuales
- **PENDIENTE sesion 13:** Validar plan compatible al cambiar roles (ver `project_upgrade_downgrade.md`)

## Perfil Fiscal Adaptativo por CCAA (COMPLETO)

- CCAA obligatorio en registro, hints por regimen (foral/Ceuta-Melilla/Canarias)
- `regime_classifier.py`: 5 regimenes
- `GET /api/fiscal-profile/fields?ccaa=`: campos dinamicos
- `DynamicFiscalForm.tsx` + `useFiscalFields.ts`
- ~90 campos en FiscalProfileRequest

## Ceuta/Melilla (COMPLETO)

- Deduccion 60% cuota integra IRPF (Art. 68.4 LIRPF)
- Auto-deteccion por ccaa="Ceuta"/"Melilla"
- IPSI bloqueado para plan Particular
- 50% bonificacion SS autonomos

## Cookies LSSI-CE + RGPD (COMPLETO)

> Detalles: `memory/frontend-features.md`

- vanilla-cookieconsent v3, AEPD compliant
- NUNCA cambiar `equalWeightButtons: true`

## UX Streaming + PWA + Landing (COMPLETO)

> Detalles: `memory/frontend-features.md`

- SSE v3.0: content_chunk (append) + content (replace)
- PWA manual, Landing con React Bits, DeductionCards en Chat

## Crawler Automatizado + Drift Analyzer (2026-03-17)

- Modulo `backend/scripts/doc_crawler/` — 12 ficheros Python + .bat, 50+ tests PASS
- **90 URLs**: 23 territorios + URLs Influencers/Creadores (AEAT, haciendas forales, Canarias IGIC, Ceuta/Melilla, plataformas)
- Rate limit: 4s/request, 50/dominio/sesion, backoff 10/30/60/STOP, robots.txt
- Windows Task Scheduler: `TaxIA-DocCrawler-Weekly`, lunes 09:00
- CLI: `python -m backend.scripts.doc_crawler [--territory X] [--dry-run] [--stats]`
- **Drift Analyzer** (Layer 2): `drift_analyzer.py` — clasifica cambios por prioridad (free), invoca Claude haiku headless solo para high/medium (cheap). Genera `plans/drift-report-YYYY-MM-DD.md`
- Integrado en `scheduled_check.py`: post-crawl automatico si hay cambios
- CLI drift: `python -m backend.scripts.doc_crawler.drift_analyzer [--dry-run] [--skip-llm]`
- Commit: `250e8a2` (crawler) + drift analyzer

## Biblioteca RAG

- 419 PDFs + 9 Excel + 11 AEAT specs = **439 archivos** en `docs/`
- Ver `memory/crawler-state.md` para estado detallado

### Pendiente ~abril 2026
1. Manual Practico Renta 2025 (AEAT) — en watchlist como "future"
2. Orden HAC Modelo 100 ejercicio 2025

## Reglas de proceso

- **Post-Bugfix Protocol**: Documentar en 3 sitios (CLAUDE.md, bugfixes, agent-comms)
- **Quality Gates**: `/check-plan` (pre) + `/verify` (post) obligatorios
- **Revision exhaustiva**: Al aplicar cambios, revisar TODAS las paginas afectadas
- **Feedback System**: Widget + ChatRating + AdminFeedbackPage/AdminContactPage/AdminDashboardPage (completo)
- **Admin Dashboard**: 3 nuevas pages, dropdown en Header, owner-only
- **Multi-role Fiscal**: `roles_adicionales` (no excluyentes), adaptativo por CCAA

## Notas tecnicas

- venv/ en raiz (TaxIA/venv/), en Windows usar `venv/Scripts/python.exe`
- PYTHONUTF8=1 necesario para backend en Windows (emojis en prints)
- Tests: `python -m pytest tests/ -v` — **1138 tests PASS** (55 nuevos DIS sesion 13), frontend build OK
- `.mcp.json` en `.gitignore` (contiene API keys)
- `data/reference/` — JSON de referencia generados (no en BD)
- **ORTOGRAFIA PRE-PUSH OBLIGATORIA** (ver `feedback_ortografia_pre_push.md`): Verificar tildes en TODOS los strings visibles
- **Fecha Renta 2026**: 8 de abril (corregida de 5 de abril)
- **Push Notifications**: VAPID keys configuradas (sesion 13 fix: regenerar SECP256R1, clear stale, retry). Notificaciones 15d/5d/1d antes de plazos. Funciona en browser limpio (Playwright), bloqueado por MetaMask/adblocker.
- **JWT_SECRET_KEY**: Debe cambiarse en Railway (accion usuario)
- **Crawler**: 90 URLs, 23 territorios, Windows Task Scheduler lunes 09:00
- **Deadlines estatales**: 32 (28 base + 4 nuevos sesion 13: Modelo 721, 714, cita previa, atención presencial)
