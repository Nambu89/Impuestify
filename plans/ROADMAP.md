# TaxIA (Impuestify) - Roadmap de Desarrollo

## Estado del Proyecto: Marzo 2026

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
- [ ] Deploy a Railway (pendiente)
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

## BACKLOG

### Alta prioridad
- [ ] Deploy a Railway (incluir seeds pendientes)
- [ ] Ejecutar seed_deductions_xsd.py en Turso producción (339 deducciones)
- [ ] MFA / 2FA (recomendación auditoría)
- [ ] CAPTCHA en login (recomendación auditoría)

### Media prioridad
- [x] ~~Agente actualización documental (crawler automático AEAT/BOE)~~ → DONE (250e8a2)
- [ ] Pipeline auto-ingesta RAG (leer `_pending_ingest.json` → embeddings)
- [ ] ML fiscal features (ml_fiscal_features table)
- [ ] Alertas de plazos fiscales

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
| Tests backend | 762+ |
| Tests frontend | build PASS |
| Bugs fixeados (mar 2026) | 13 documentados |
| URLs monitorizadas (crawler) | 48 en 21 territorios |
