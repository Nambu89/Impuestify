# TaxIA — Memoria del Agente

> Ultima actualizacion: 2026-03-13 (sesion 9)
> Ver detalles en archivos separados por tema
> Bugs fixeados: `memory/bugfixes-2026-03.md`

## Indice de archivos de memoria

| Archivo | Contenido |
|---------|-----------|
| `memory/MEMORY.md` | Este indice + resumen de cada area |
| `memory/backend-subscription.md` | Detalles backend Stripe |
| `memory/crawler-state.md` | Estado del crawler + drift analyzer (54 URLs, 23 territorios) |
| `memory/frontend-features.md` | UX/Streaming, PWA, Landing, DeductionCards, Cookies, Admin |
| `memory/bugfixes-2026-03.md` | Bugs fixeados marzo 2026 (13 bugs documentados) |
| `memory/mcp-design-tools.md` | Google Stitch + Nano Banana MCP config y modelos Gemini 3 |
| `memory/response-quality-gap.md` | Analisis calidad respuesta vs Google/Claude — plan de mejora |
| `memory/agent-system-improvements.md` | Mejoras GSD al sistema multi-agente (2026-03-08) |
| `memory/awesome-claude-code.md` | Integracion herramientas awesome-claude-code (2026-03-08) |
| `memory/aeat-docs-integration.md` | Integracion docs AEAT: casillas, XSD, XLS, VeriFactu (2026-03-08) |
| `memory/beta_testers.md` | 4 beta testers activos (Ramon, Juan Pablo, Jose Antonio, Maria) |

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

## Suscripciones Stripe (COMPLETO — DUAL PLAN)

> Detalles: `memory/backend-subscription.md`

- Plan Particular: 5 EUR/mes | Plan Autonomo: 39 EUR/mes IVA incl.
- Owner: `fernando.prada@proton.me` (sin restricciones)
- 13 usuarios existentes: grace_period hasta 31/12/2026

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

## Crawler Automatizado + Drift Analyzer (2026-03-13)

- Modulo `backend/scripts/doc_crawler/` — 10 ficheros Python + .bat, 41 tests PASS
- **54 URLs**: 23 territorios (incluyendo Ceuta, Melilla, Canarias IGIC)
- Rate limit: 4s/request, 50/dominio/sesion, backoff 10/30/60/STOP, robots.txt
- Windows Task Scheduler: `TaxIA-DocCrawler-Weekly`, lunes 09:00
- CLI: `python -m backend.scripts.doc_crawler [--territory X] [--dry-run] [--stats]`
- **Drift Analyzer** (Layer 2): `drift_analyzer.py` — clasifica cambios por prioridad (free), invoca Claude haiku headless solo para high/medium (cheap). Genera `plans/drift-report-YYYY-MM-DD.md`
- Integrado en `scheduled_check.py`: post-crawl automatico si hay cambios
- CLI drift: `python -m backend.scripts.doc_crawler.drift_analyzer [--dry-run] [--skip-llm]`
- Commit: `250e8a2` (crawler) + pendiente commit drift analyzer

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

## Notas tecnicas

- venv/ en raiz (TaxIA/venv/), en Windows usar `venv/Scripts/python.exe`
- PYTHONUTF8=1 necesario para backend en Windows (emojis en prints)
- Tests: `python -m pytest tests/ -v` — 762+ tests
- `.mcp.json` en `.gitignore` (contiene API keys)
- `data/reference/` — JSON de referencia generados (no en BD)
