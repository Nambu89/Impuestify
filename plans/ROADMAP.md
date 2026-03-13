# TaxIA (Impuestify) - Roadmap de Desarrollo

## Estado del Proyecto: Marzo 2026

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

## BACKLOG

### Alta prioridad
- [x] ~~Ejecutar seed_deductions_xsd.py en Turso producción (339 deducciones)~~ → DONE (2026-03-13)
- [ ] MFA / 2FA (recomendación auditoría)
- [x] ~~CAPTCHA en login (recomendación auditoría)~~ → DONE — Cloudflare Turnstile en Login + Register (frontend TurnstileWidget.tsx + backend verify_turnstile())
- [ ] Estrategia Social Media — plan en `plans/social-media-strategy-2026.md` (7 pilares, LinkedIn + Instagram, pre-campana Renta abril 2026)

### Media prioridad
- [x] ~~Agente actualización documental (crawler automático AEAT/BOE)~~ → DONE (250e8a2)
- [x] ~~Alertas de plazos fiscales~~ → DONE (a849ce1) — calendario + email + push
- [x] ~~Criptomonedas, trading y apuestas~~ → DONE (91faf01) — FIFO, 5 exchanges, XSD casillas
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
| Tests backend | 1009 |
| Tests frontend | build PASS |
| Exchanges crypto soportados | 5 (Binance, Coinbase, Kraken, KuCoin, Bitget) |
| Fechas fiscales 2026 | 58 (32 estatales + 26 forales) |
| Bugs fixeados (mar 2026) | 52 documentados (Bugs 1-52) |
| URLs monitorizadas (crawler) | 54 en 23 territorios |
| Drift Analyzer | Layer 1 (free) + Layer 2 (haiku headless) |
