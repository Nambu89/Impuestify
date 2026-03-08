# TaxIA — Memoria del Agente

> Ultima actualizacion: 2026-03-08
> Ver detalles en archivos separados por tema
> Bugs fixeados: `memory/bugfixes-2026-03.md`

## Indice de archivos de memoria

| Archivo | Contenido |
|---------|-----------|
| `memory/MEMORY.md` | Este indice + resumen de cada area |
| `memory/backend-subscription.md` | Detalles backend Stripe |
| `memory/crawler-state.md` | Estado del crawler de documentos |
| `memory/frontend-features.md` | UX/Streaming, PWA, Landing, DeductionCards, Cookies, Admin |
| `memory/bugfixes-2026-03.md` | Bugs fixeados marzo 2026 + tareas pendientes frontend |

## Arquitectura del proyecto

- Backend: `backend/app/` — FastAPI + Microsoft Agent Framework
- Frontend: `frontend/src/` — React 18 + Vite 5 + TypeScript
- Docs RAG: `docs/` — 428 archivos organizados por territorio
- Agent comms: `agent-comms.md` (raiz) — canal inter-agentes
- Skills: `.claude/skills/` — 6 modulos de conocimiento
- Subagentes: `.claude/subagents/` (backend, frontend, python, docscrawler)

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

## Motor de Deducciones IRPF (COMPLETO)

- 16 estatales + 48 territoriales = 64 deducciones totales
- 8 CCAA: Araba(8), Bizkaia(6), Gipuzkoa(6), Navarra(7), Madrid(6), Cataluna(5), Andalucia(5), Valencia(6)
- Forales: sistema IRPF propio, NO incluyen estatales
- simulate_irpf auto-encadena discover_deductions
- Export PDF (ReportLab) + Email (Resend)
- Post-deploy: `seed_deductions.py` + `seed_deductions_territorial.py` + `seed_estatal_scale.py`

## Suscripciones Stripe (COMPLETO)

> Detalles: `memory/backend-subscription.md` + `.claude/skills/stripe-integration.md`

- Producto: `prod_U4lJ9l8NhKvFHZ`, 5 EUR/mes
- Owner: `fernando.prada@proton.me` (sin restricciones)
- 13 usuarios existentes: grace_period hasta 31/12/2026
- Frontend: useSubscription, SubscribePage, ProtectedRoute con subscription guard

## Perfil Fiscal + Admin (COMPLETO)

- datos_fiscales JSON: autonomo fields + Phase 1+2 fields (guia fiscal)
- Admin router: GET/PUT /api/admin/users (owner-only)
- Frontend: AdminUsersPage (cards mobile, tabla desktop)

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

## Biblioteca RAG

- 419 PDFs + 9 Excel = 428 archivos en `docs/`
- Araba COMPLETO (37 docs)
- Disenos de Registro AEAT: 15 archivos (flat-file, NO XSD)
- Ver `memory/crawler-state.md` para estado detallado

### Pendiente ~abril 2026
1. Manual Practico Renta 2025 (AEAT) — 404 a 3/3/2026
2. Orden HAC Modelo 100 ejercicio 2025

## Reglas de proceso

- **Post-Bugfix Protocol**: Tras arreglar cualquier bug, SIEMPRE documentar en 3 sitios: CLAUDE.md del area (regla + troubleshooting), `memory/bugfixes-YYYY-MM.md` (detalle tecnico), `agent-comms.md` (estado tarea). Definido en `CLAUDE.md` raiz.

## Notas tecnicas

- venv/ en raiz (TaxIA/venv/), en Windows usar `venv/Scripts/python.exe`
- Tests: `python -m pytest tests/ -v` (mock jose/bcrypt/slowapi por chain imports)
- Config: `.env` en raiz, cargada via pydantic Settings
