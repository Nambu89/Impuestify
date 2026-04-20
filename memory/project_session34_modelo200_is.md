---
name: project_session34_modelo200_is
description: Sesion 34 continuacion — Modelo 200 IS completo (simulador 7 territorios, 47 tests, endpoints, workspace prefill, tool TaxAgent, PDF, frontend wizard 4 pasos)
type: project
---

# Sesion 34 (continuacion) — Modelo 200 IS (2026-04-17)

Rama: `claude/modelo-200-v1` (11 commits desde main).

## Resumen ejecutivo

Implementacion completa del simulador Impuesto sobre Sociedades (Modelo 200
+ Modelo 202 pagos fraccionados) en una sola sesion via RuFlo con 3 agentes
paralelos (backend-core, frontend-hooks, frontend-pages) + 1 agente
secuencial (backend-integration).

## Scope v1

- **Entidades**: SL, SLP, SA, nueva creacion (primeros 2 ejercicios BI positiva)
- **Territorios**: regimen comun + Alava + Bizkaia + Gipuzkoa + Navarra + ZEC Canarias + Ceuta/Melilla
- **Modo dual**: manual publico (sin auth, lead magnet SEO) + workspace (auth, auto-fill desde PyG)
- **Pagos fraccionados**: Modelo 202 Art. 40.2 (cuota) y Art. 40.3 (base imponible)
- **PDF borrador**: 16 casillas principales con ReportLab

## Arquitectura

```
ISSimulator (is_simulator.py)
  ├── ISInput → ISResult pipeline 14 pasos
  ├── calcular_202() → IS202Result
  └── Usa is_scales.py (7 regimenes + deducciones parametrizadas)

Endpoints (is_estimate.py, prefix /api/irpf)
  ├── POST /is-estimate (publico)
  └── POST /is-202 (publico)

Workspace prefill (workspaces.py)
  └── GET /{id}/is-prefill?ejercicio=X (auth + ownership)

Tool TaxAgent (is_simulator_tool.py)
  └── simulate_is → ISSimulator.calculate()

PDF (modelo_pdf_generator.py)
  └── _render_200() con 16 casillas

Frontend
  ├── /modelo-200 → Modelo200Page wizard 4 pasos
  ├── /modelo-202 → Modelo202Page formulario
  ├── useIsEstimator (600ms debounce)
  ├── useIsPrefill
  └── ISResultCard desglose visual
```

## Commits (11)

1. `40a3728` feat(is): escalas IS 7 territorios + deducciones parametrizadas
2. `acfe979` feat(is): simulador IS con 26 tests (7 territorios, BINs, deducciones, 202)
3. `3382fed` feat(is): types IS + hooks useIsEstimator + useIsPrefill
4. `972d01a` feat(is): Modelo200Page wizard 4 pasos + ISResultCard desglose
5. `1f5ac4f` feat(is): Modelo202Page + rutas /modelo-200 /modelo-202 + Header entry
6. `75b6a81` feat(is): endpoints POST /api/irpf/is-estimate + /api/irpf/is-202 + 15 tests
7. `2a5ee6c` feat(is): workspace IS prefill endpoint + 6 tests
8. `966c781` feat(is): tool simulate_is registrado en TaxAgent + IS detection prompt
9. `06aa9f8` feat(is): PDF borrador Modelo 200 con 16 casillas
10. `e2294cc` docs(is): plan implementacion Modelo 200 — 12 tasks, 3 waves
11. `8f1aea1` docs: spec Modelo 200 IS + resolve merge conflict requirements.txt

## Tests

- Backend IS: 47 PASS (26 simulador + 15 endpoint + 6 prefill)
- Frontend: build OK (8.81s)

## Archivos nuevos (11)

- `backend/app/utils/is_scales.py` (162 lineas)
- `backend/app/utils/is_simulator.py` (~400 lineas)
- `backend/app/routers/is_estimate.py` (~300 lineas)
- `backend/app/tools/is_simulator_tool.py` (~200 lineas)
- `backend/tests/test_is_simulator.py` (26 tests)
- `backend/tests/test_is_estimate.py` (15 tests)
- `backend/tests/test_is_prefill.py` (6 tests)
- `frontend/src/types/is.ts`
- `frontend/src/hooks/useIsEstimator.ts`
- `frontend/src/hooks/useIsPrefill.ts`
- `frontend/src/pages/Modelo200Page.tsx` + CSS
- `frontend/src/pages/Modelo202Page.tsx` + CSS
- `frontend/src/components/ISResultCard.tsx` + CSS

## Archivos modificados (5)

- `backend/app/main.py` — router registration
- `backend/app/tools/__init__.py` — ALL_TOOLS + TOOL_EXECUTORS
- `backend/app/agents/tax_agent.py` — IS detection keywords
- `backend/app/services/modelo_pdf_generator.py` — _render_200()
- `backend/app/routers/workspaces.py` — is-prefill endpoint
- `frontend/src/App.tsx` — rutas lazy /modelo-200, /modelo-202
- `frontend/src/components/Header.tsx` — entrada Modelo 200 (IS)

## Bug corregido durante implementacion

Fix /api/ prefix en hooks: useIsEstimator y useIsPrefill usaban
`/api/irpf/is-estimate` pero apiRequest ya prepende `/api`. Mismo bug
que DefensIA. Corregido inline antes de commitear.

## Ingesta RAG pendiente

13 PDFs no ingestados por API key Azure DI expirada (401). Script
`backend/scripts/ingest_pending_batch.py` creado para re-intentar.
Documentos pendientes:
- AEAT-Manual_Practico_IRPF_2025 (Parte 1 + 2)
- AEAT-Manual_IVA_2025
- AEAT-Especificacion_Retenciones_2026
- AEAT-Algoritmo_Retenciones_2026
- Araba-DF_42_2025_IRPF
- Baleares-DLeg_1_2014
- Bizkaia-NormativaForal-13_2013
- Canarias-RD_1758_2007_ZEC
- Galicia-DLeg_1_2011
- Influencers-RD_1065_2007_DAC7
- Madrid-DLeg_1_2010

## Fuera de scope v1

- Plan suscripcion "Empresa" (nuevo tier)
- Perfil fiscal de empresa (NIF empresa, tipo entidad, fecha constitucion)
- Presentacion ante AEAT
- Regimenes especiales (cooperativas, asociaciones, parcialmente exentas)
- Concierto/Convenio reparto multi-territorio (>10M)
- Ingesta RAG Manual Sociedades (bloqueada por Azure DI key)
