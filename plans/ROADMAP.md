# TaxIA (Impuestify) - Roadmap de Desarrollo

## Estado del Proyecto: Marzo 2026 (Sesion 17 — 2026-03-20)

---

## COMPLETADO — Sesion 15: Guia Fiscal Adaptativa por Rol (2026-03-19)

- [x] **Feature**: Guia fiscal adaptativa — 3 flujos diferentes segun plan usuario
  - PARTICULAR (7 pasos): sin actividad economica, wizard simplificado
  - CREATOR (8 pasos): step dedicado "Actividad como creador" con grid plataformas, IAE, IVA intracomunitario, withholding tax, gastos creator, M349
  - AUTONOMO (8 pasos): step dedicado "Actividad economica" (reorganizado)
- [x] **Frontend**: useTaxGuideProgress con userPlan, getStepContent(), StepCreadorActividad, resultado adaptativo con obligaciones por rol
- [x] **Backend**: Campos creator en irpf_estimate.py (plataformas_ingresos, gastos granulares, withholding, IAE, M349 flag)
- [x] **Tests**: 12 tests creator PASS
- [x] **CSS**: Estilos creator step + obligaciones grid + responsive
- [x] **Research**: Necesidades usuarios (particulares/autonomos/creadores) — `plans/user-needs-research-2026.md`
- Archivos: useTaxGuideProgress.ts, TaxGuidePage.tsx, TaxGuidePage.css, useIrpfEstimator.ts, irpf_estimate.py, test_irpf_estimate_creator.py

---

## COMPLETADO — Sesion 13: Calendar Fix, Push Diagnostics, Document Integrity Scanner, CreatorsPage Route (2026-03-17)

- [x] **Bug 59**: Calendario fiscal — deadlines solo en mes end_date, no en rango start→end
  - Fix: FiscalCalendar.tsx overlap check `(start <= monthEnd && end >= monthStart)`
  - Commit: `19935d4`
- [x] **Bug 60**: Calendario fiscal — meses pasados vacios (vencidos filtrados)
  - Fix: Eliminado filtro `urgency === 'past'`, mostrar con estilo atenuado `fc-card--past`
  - Commit: `19935d4`
- [x] **Bug 61**: Push notifications — "Registration failed - push service error"
  - Causa: VAPID keys no formaban par P-256 válido
  - Fix: Regenerar keys SECP256R1 + clear stale subscriptions + retry
  - Commits: `3048d9f`, `6f45b3d`, `8e329ce`
  - Nota: Funciona en browser limpio (Playwright verificado), bloqueado por MetaMask/adblocker
- [x] **Bug 62**: `/creadores-de-contenido` redirigía a `/` (ruta no registrada)
  - Causa: CreatorsPage importada lazy() pero faltaba en Routes App.tsx
  - Fix: Añadir Route
  - Commit: `dadf58e`
- [x] **Feature**: Document Integrity Scanner (Capa 13 de seguridad)
  - 40 patrones bilingües ES/EN contra prompt injection
  - 10 categorías (adversarial instructions, inversion jailbreak, etc.)
  - Integrado en user uploads (PASS/WARN/SANITIZE/BLOCK), crawler (quarantine), RAG (trust scoring)
  - IntegrityBadge UI en workspaces
  - 55 tests nuevos
  - Commits: `1fd2835`, `436d009`
- [x] **Feature**: 4 nuevos deadlines para particulares
  - Modelo 721 (cripto extranjero), 714 (Patrimonio), cita previa Renta, atención presencial AEAT
  - Commit: `19935d4`
- [x] **Migración BD**: 4 columnas nuevas (integrity_score + integrity_findings)
  - Ejecutada en Turso producción

**Métricas Sesión 13:**
- Tests: 1138 passed (55 nuevos DIS)
- Bugs: 62 documentados
- Deadlines estatal: 32 (antes 28)
- Capas seguridad: 13 (nueva: Document Integrity Scanner)

---

## COMPLETADO — Sistema de Feedback + Admin Dashboard (2026-03-17)

- [x] Widget FeedbackWidget en Chat + ChatRating component
- [x] Tabla `feedback` en BD (user_id, rating, comment, metadata)
- [x] Router `/api/feedback` (POST crear, GET owner-only)
- [x] Service `feedback_service.py` para CRUD + agregacion
- [x] AdminFeedbackPage (/admin/feedback) — ratings chart + export CSV
- [x] AdminContactPage (/admin/contacts) — contact form submissions
- [x] AdminDashboardPage (/admin/dashboard) — overview metrics
- [x] Header dropdown admin para owner (Feedback, Contacts, Dashboard)
- [x] Integracion en Chat: FeedbackWidget post-respuesta
- [x] Tests feedback CRUD + permission checks
- Commits: TBD

---

## COMPLETADO — Plan Creator 49 EUR/mes (2026-03-17)

- [x] Plan Creator en Stripe: 49 EUR/mes
- [x] Tabla `users.subscription_plan` acepta "creator"
- [x] SubscribePage UI: 3 plan cards (Particular/Creator/Autonomo)
- [x] STRIPE_PRICE_ID_CREATOR en backend config
- [x] TaxAgent context especializado para creadores (IAE 8690, IVA plataforma, Modelo 349, DAC7)
- [x] Restricciones contenido Autonomo solo para plan Particular (no Creator)
- [x] Landing /creadores-de-contenido con SEO-GEO
- [x] Marketing: influencers, YouTubers, streamers, bloggers
- Commits: TBD

---

## COMPLETADO — Modelo 100 XSD ~100% Coverage + IAE Lookup (2026-03-17)

- [x] Tool `iae_lookup` (IAE codes: 8690, 9020, 6010.1, etc.)
- [x] Tool `compare_joint_individual` — comparativa 4 escenarios
- [x] XSD Modelo 100: gastos granulares, módulos, royalties coverage
- [x] Integración TaxAgent: lookup IAE automático para creadores
- [x] Comparativa conjunta en simulador
- Commits: TBD

---

## COMPLETADO — CCAA-aware Tax Models (2026-03-17)

- [x] Modelo 303 → 300 (Gipuzkoa)
- [x] Modelo 303 → F69 (Navarra)
- [x] Modelo 420 IGIC (Canarias)
- [x] IPSI (Ceuta/Melilla)
- [x] Labels dinámicos en UI por territorio
- [x] TaxAgent contexto por modelo
- Commits: TBD

---

## COMPLETADO — Multi-role Fiscal Profiles (2026-03-17)

- [x] Campo `roles_adicionales` en users (JSON array, non-exclusive)
- [x] Perfil soporta: asalariado + autonomo, creador + particular, inversor + empleado
- [x] DynamicFiscalForm adaptativo por roles
- [x] Restricciones por plan: Creator no elige Autonomo, etc.
- [x] CCAA-aware profile builder
- Commits: TBD

---

## COMPLETADO — Push Notifications VAPID (2026-03-17)

- [x] VAPID keys configuration
- [x] Alertas 15d, 5d, 1d antes de plazos fiscales
- [x] Opt-in en header
- [x] Backend: envio desde scheduler
- [x] Frontend: PushPermissionBanner
- Commits: TBD

---

## COMPLETADO — Crawler 90 URLs + Documentos Creadores (2026-03-17)

- [x] Crawler: 90 URLs, 23 territorios
- [x] URLs Creadores/Influencers: AEAT, haciendas forales, plataformas (Google, Meta, Twitch)
- [x] Drift analyzer: post-crawl clasificacion cambios
- [x] Seed: documentos creadores indexados
- Commits: TBD

---

## COMPLETADO — Bugs Sesion 12 (Bugs 53-58) (2026-03-17)

- [x] Bug 53: Admin Feedback/Contact pages crash — CSS faltante
- [x] Bug 54: Subscribe page mobile overflow 113px
- [x] Bug 55: Fecha Renta "2 abril" → "8 abril 2026" CORREGIDO
- [x] Bug 56: Calendar solo muestra 6 meses (→12)
- [x] Bug 57: Calendar applies_to — asalariado + Patrimonio/347
- [x] Bug 58: CTA creadores apuntaba a /creadores-de-contenido (→/subscribe)
- Tests: 1083+ backend PASS, frontend build OK

---

## COMPLETADO — Módulo Criptomonedas, Trading y Apuestas (2026-03-11)

> Plan: `plans/plan_crypto_trading_apuestas.md`

### 7 fases implementadas (20 tareas)
- [x] **Fase 1**: Campos perfil fiscal alineados con XSD Modelo 100 AEAT (casillas 1800-1814, 0281-0297, 0316-0354)
- [x] **Fase 2**: Calculadora FIFO (antiaplicación Art. 33.5.f, 61 días) + Parser CSV 5 exchanges (Binance, Coinbase, Kraken, KuCoin, Bitget)
- [x] **Fase 3**: Router REST crypto (upload, transactions, holdings, gains, delete) + rate limiting + magic bytes
- [x] **Fase 4**: Integración simulador IRPF (cripto→base ahorro, juegos privados→base general, loterías→gravamen especial 20%)
- [x] **Fase 5**: Tools chat (calculate_crypto_gains + parse_crypto_csv) registrados en TaxAgent
- [x] **Fase 6**: Frontend CryptoPage (/crypto) con upload, 3 tabs, alerta Modelo 721
- [x] **Fase 7**: Wizard paso "Inversiones y cripto" + marketing (SubscribePage + Home)
- [x] Migración campos renombrados (migrate_fiscal_fields_crypto.py)
- [x] GDPR: borrado tablas crypto en delete_user_account
- [x] 140 tests nuevos (998 total) — 0 fail
- Commit: `91faf01`

---

## COMPLETADO — Calendario Fiscal + Email Reminders (2026-03-10/11)

- 58 fechas 2026 en producción: 32 estatales + 26 forales
- Seed foral ejecutado 2026-03-11: Gipuzkoa 8, Bizkaia 5, Araba 5, Navarra 8
- Email reminders autónomos: 30 días antes, opt-in
- Web Push: alertas 15d, 5d, 1d antes via VAPID
- Frontend: CalendarPage, FiscalCalendar, UpcomingDeadlines, PushPermissionBanner
- Commits: `a849ce1`, `b2079eb`

---

## COMPLETADO — Perfil Fiscal Adaptativo por CCAA (2026-03-08)

> Plan: `plans/plan_perfil_fiscal_adaptativo.md`

### Sprint 1 — Backend + Frontend base (DONE)
- [x] `regime_classifier.py` — 5 regímenes fiscales
- [x] `GET /api/fiscal-profile/fields?ccaa=` — campos dinámicos por CCAA
- [x] `build_answers_from_profile()` — bridge perfil → deduction answers
- [x] FiscalProfileRequest ampliado (~35 campos nuevos)
- [x] CCAA obligatorio en registro + hints por régimen
- [x] `DynamicFiscalForm.tsx` + `useFiscalFields.ts`
- Commit: `9930d06`

### Sprint 2+3 — Motor foral + TaxGuidePage (DONE)
- [x] Seed tramos IRPF forales (58 tramos, 4 territorios)
- [x] Seed deducciones forales v2 (50 activas)
- [x] Motor IRPF foral en irpf_simulator.py (vasco + navarra)
- [x] 56 tests foral simulator PASS
- [x] Fix B-GF-01, B-GF-06: hero + validación pasos
- Commit: `86ecd16`

### Sprint 4 — QA + bugfix (DONE)
- [x] Fix 10 bugs QA (ca3e9f4 + 60d23f2)
- [x] QA regression: 7/10 confirmados FIXED
- [x] Deploy a Railway (2dd09ff, 8f077d3, b2079eb)
- [ ] Ejecutar seed_deductions_xsd.py en Turso producción

---

## COMPLETADO — Crawler Automatizado (2026-03-09)

- Módulo `backend/scripts/doc_crawler/` — 9 ficheros + .bat + 32 tests
- 48 URLs monitorizadas en 21 territorios
- Rate limiting, robots.txt, validación PDF/Excel, dedup SHA-256
- Windows Task Scheduler: lunes 09:00 (`TaxIA-DocCrawler-Weekly`)
- CLI: `python -m backend.scripts.doc_crawler [--territory X] [--dry-run] [--stats]`
- Commit: `250e8a2`

## COMPLETADO — Fix 10 Bugs QA (2026-03-09)

- 4 críticos: landing invisible, guardrail educativo, IRPF tool crash, RETA 2026
- 5 mayores: chat format, wizard validation, modales mobile, logout, foral tip
- B-COOK-01: no es bug (vanilla-cookieconsent genera sus propios botones)
- Commits: `ca3e9f4` + `60d23f2`

## COMPLETADO

### Perfil Fiscal Completo XSD (2026-03-08)
- `seed_deductions_xsd.py` — 339 deducciones oficiales del XSD Modelo 100
- `data/reference/deducciones_autonomicas_xsd.json` — referencia JSON
- Commit: `d5fd9a0`

### Integración Documentos AEAT (2026-03-08)
- Tool `lookup_casilla` — 2064 casillas IRPF Modelo 100
- Parser `parse_aeat_docs.py` — XSD, XLS, VeriFactu
- Schema JSON Renta 2024 (6769 elementos)
- Modelos 130/131 fields JSON
- VeriFactu RAG (5 ficheros)
- 44 tests PASS | Commit: `3cc3aa0`

### UI Adaptativa por Territorio (2026-03-08)
- Labels forales + tabs condicionales (IPSI, IGIC, 303, 130)
- Commit: `f3d6ca7`

### Calculadora IPSI Ceuta/Melilla (2026-03-08)
- 6 tipos impositivos + REST endpoint + tool chat + frontend condicional
- 34 tests | Commit: `9be68c6`

### SSE Stream Fix (2026-03-08)
- Per-chunk timeout 30s + smart fallback
- Commit: `e61633d`

### System Prompt Rewrite (2026-03-08)
- 414→42 líneas, patrón "answer-first"
- Commit: `ee2364f`

### Herramienta ISD (2026-03-07)
- Tarifa estatal + bonificaciones 8+ CCAA + 4 forales
- 61 tests PASS

### Redesign Visual (2026-03-07)
- Dark theme, glassmorphism, landing SEO

### Deducciones Territoriales v2 (2026-03-07)
- 64 nuevas → 128 total en 19 territorios

### Sistema Fiscal Trimestral (2026-03-07)
- Modelos 303/130/420, persistencia, frontend wizard
- 58 tests backend

### Suscripciones Stripe (completo)
- Particular 5 EUR/mes | Autónomo 39 EUR/mes

---

## COMPLETADO — 4 Bugs Beta Testers (2026-03-13)

- Bug 52: Password reset no enviaba email — dominio `.es` → `.com` (Resend)
- Bug 50: Workspaces loading infinito — timeout + race condition + NULL guard
- Bug 49: NotificationAgent respuestas verbosas — patrón answer-first
- Bug 51: Comparativa conjunta vs individual incompleta — loop tool_calls
- Commit: `b148564`

---

## COMPLETADO — Ortografía + Dropdown CSS + Seed Foral (2026-03-11)

- 27 tildes corregidas en 12 archivos frontend (autónomo, nómina, declaración, estimación, método, cálculo, situación, número, régimen)
- Dropdown CSS oscuro para selects en SettingsPage (CCAA, Situación Laboral, Grado Discapacidad)
- 26 fechas forales seeded en producción Turso (58 total 2026)
- Commit: `b2079eb`

---

## COMPLETADO — Bugfix Ramón Palomares (beta tester) (2026-03-11)

- slowapi crash 500: `req: Request` → `request: Request` en irpf_estimate.py
- JWT 401 en SSE chat: auto-refresh token en useStreamingChat.ts
- Guía fiscal paso "Inversiones" faltante: StepInversiones + reindex switch cases
- Commits: `2dd09ff`, `8f077d3`

---

## COMPLETADO — Sesion 17: Stripe Role Validation + Security Cleanup (2026-03-20)

- [x] **RuFlo MCP activado**: 259 tools, 26 hooks, ~95% capacidad. ReasoningBank funcional (2 patches + postinstall)
- [x] **Security cleanup**: secretos eliminados de historial git (filter-repo 3 pasadas, 235 commits)
- [x] **Stripe role validation**: UpgradePlanModal en SettingsPage (commit `8440917`)
- [x] **Turnstile bypass QA**: ya implementado (`TURNSTILE_TEST_MODE=True` en Railway)
- [x] **Calculadora neto**: 22 tildes + neto fiscal real (neto_anual/12) + warning reserva IRPF (commit `c70dea5`)
- [x] **PDF export completo**: 30+ campos fiscales + observaciones chat + tildes (commit `c3aa17c`)
- [x] **ReasoningBank Windows**: 2 patches + postinstall automatico (commit `ed6f5dd`)
- [x] **SONA trajectories**: 7 trayectorias registradas, 18 entries HNSW
- [x] **SEO-GEO CreatorsPage**: meta tags, JSON-LD FAQPage, GEO cards 4 territorios, long-tail keywords (commit `718cff0`)
- [x] **Calculadora IVA Creadores**: `/calculadora-iva-creadores` — 7 plataformas, multi-calc, Modelo 303/349 (commit `718cff0`)

---

## BACKLOG

### CRITICA
- [ ] Re-ejecutar crawler con 90 URLs corregidas (si hay cambios)

### Alta prioridad
- [x] ~~Ejecutar seed_deductions_xsd.py en Turso producción (339 deducciones)~~ → DONE (2026-03-13)
- [ ] MFA / 2FA (recomendación auditoría)
- [ ] **Security audit stack** (4 capas, todo gratis):
  - [ ] Semana 1: Bandit + Semgrep como pre-commit hooks (SAST)
  - [ ] Semana 2: OWASP ZAP headless contra staging (DAST)
  - [ ] Semana 3: Nuclei templates web-app/FastAPI/JWT
  - [ ] Semana 4: Todo en GitHub Actions (CI/CD security gate)
- [x] ~~CAPTCHA en login (recomendación auditoría)~~ → DONE — Cloudflare Turnstile en Login + Register (frontend TurnstileWidget.tsx + backend verify_turnstile())
- [x] ~~Estrategia Social Media~~ — DONE (2026-03-15, TikTok integrado 2026-03-16). Plan en `plans/social-media-strategy-2026.md` + contenido Q1 en `plans/social-media-content-plan-2026-Q1.md` + research TikTok en `plans/tiktok-research-2026.md`. 3 canales: Instagram + LinkedIn + TikTok. 4 carruseles generados, 10 posts completos, 15 guiones Reels, 9 screenshots. Pendiente: ejecucion por Fernando (setup Metricool, LinkedIn, TikTok @impuestify, primer post 21 marzo)

### Media prioridad
- [x] ~~Agente actualización documental (crawler automático AEAT/BOE)~~ → DONE (250e8a2)
- [x] ~~Alertas de plazos fiscales~~ → DONE (a849ce1) — calendario + email + push
- [x] ~~Criptomonedas, trading y apuestas~~ → DONE (91faf01) — FIFO, 5 exchanges, XSD casillas
- [x] ~~**Fase 5: Guia fiscal adaptativa por rol**~~ → DONE (2026-03-19, sesion 15)
- [x] ~~Landing SEO creadores de contenido~~ → DONE (2026-03-20, sesion 17, commit `718cff0`)
- [x] ~~Calculadora IVA por plataforma~~ → DONE (2026-03-20, sesion 17, commit `718cff0`)
- [ ] **Google SSO** — login/registro con "Continuar con Google" (@react-oauth/google + google-auth backend)
- [ ] Pipeline auto-ingesta RAG (leer `_pending_ingest.json` → embeddings)
- [ ] ML fiscal features (ml_fiscal_features table)

### Baja prioridad
- [ ] Integración factura electrónica (FacturaE)
- [ ] App móvil (React Native)
- [ ] Redesign TaxGuidePage + WorkspacesPage (pending baja prioridad)

---

## Métricas

| Métrica | Valor |
|---------|-------|
| Documentos RAG | 439 (419 PDF + 9 Excel + 11 AEAT specs) |
| Deducciones en BD | ~554 (192 v1/v2 + 339 XSD + 50 forales) |
| CCAA cubiertas | 21 (15 común + 4 forales + Ceuta + Melilla) |
| Tests backend | **1199+27** (export tests nuevos sesion 17) |
| Tests frontend | build PASS |
| RuFlo MCP | **259 tools**, 26 hooks, ~95% capacidad, SONA 5 traj |
| Exchanges crypto soportados | 5 (Binance, Coinbase, Kraken, KuCoin, Bitget) |
| Fechas fiscales 2026 | 58 (32 estatales + 4 nuevos = 36 **pendiente actualizar**) |
| Bugs fixeados (mar 2026) | **62 documentados** (Bugs 1-62, sesion 13) |
| URLs monitorizadas (crawler) | **90 en 23 territorios** |
| Drift Analyzer | Layer 1 (free) + Layer 2 (haiku headless) |
| Planes de suscripcion | 3 (Particular 5€, Creator 49€, Autonomo 39€) |
| Admin pages | 4 nuevas (Feedback, Contacts, Dashboard, Creators) |
| Capas de seguridad | **13** (nueva: Document Integrity Scanner) |
