# TaxIA (Impuestify) - Roadmap de Desarrollo

## Estado del Proyecto: Marzo 2026

---

## EN PROGRESO — Perfil Fiscal Adaptativo por CCAA

> Plan: `plans/plan_perfil_fiscal_adaptativo.md`
> Inicio: 2026-03-08

### Sprint 1 — Backend infrastructure + Frontend base (DONE)
- [x] `regime_classifier.py` — 5 regímenes fiscales
- [x] `GET /api/fiscal-profile/fields?ccaa=` — campos dinámicos por CCAA
- [x] `build_answers_from_profile()` — bridge perfil → deduction answers
- [x] FiscalProfileRequest ampliado (~35 campos nuevos)
- [x] CCAA obligatorio en registro + hints por régimen
- [x] `DynamicFiscalForm.tsx` + `useFiscalFields.ts`
- [x] Integrado en SettingsPage
- [x] CCAA naming normalizado (sin acentos)
- [x] 706/706 tests PASS + build OK
- Commit: `9930d06`

### Sprint 2 — TaxGuidePage integration (EN PROGRESO)
- [ ] Integrar DynamicFiscalForm en paso 5 (Deducciones)
- [ ] Fix B-GF-01: Hero section
- [ ] Fix B-GF-06: Validación pasos
- [ ] Fix B-GF-07: Error state deducciones

### Sprint 3 — Motor foral + seed completo (EN PROGRESO)
- [ ] Seed tramos IRPF forales (4 territorios)
- [ ] Seed deducciones forales (~27 deducciones)
- [ ] Motor IRPF foral en irpf_simulator.py
- [ ] Tests foral simulator

### Sprint 4 — QA + deploy
- [ ] Fix bugs guía fiscal restantes
- [ ] QA E2E con perfiles de cada régimen
- [ ] Ejecutar seed_deductions_xsd.py (339 deducciones XSD)
- [ ] Deploy a Railway

---

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
- [ ] Ejecutar seed_deductions_xsd.py en Turso producción (339 deducciones)
- [ ] MFA / 2FA (recomendación auditoría)
- [ ] CAPTCHA en login (recomendación auditoría)

### Media prioridad
- [ ] Agente actualización documental (crawler automático AEAT/BOE)
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
| Deducciones en BD | 192 activas (+ 339 XSD pendientes seed) |
| CCAA cubiertas | 21 (15 común + 4 forales + Ceuta + Melilla) |
| Tests backend | 706 |
| Tests frontend | build PASS |
