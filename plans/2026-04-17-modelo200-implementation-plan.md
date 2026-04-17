# Modelo 200 IS — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simulador del Impuesto sobre Sociedades (Modelo 200 + 202) con modo manual publico + auto-fill desde workspace, PDF borrador, y tool para TaxAgent.

**Architecture:** Nuevo modulo `is_simulator.py` con sub-calculadoras (mismo patron que `irpf_simulator.py`). Endpoint `POST /api/irpf/is-estimate` (lightweight, sin LLM). Frontend wizard 4 pasos en `/modelo-200` con `useIsEstimator` hook y `LiveEstimatorBar` reutilizado. Integracion workspace via `GET /api/workspaces/{id}/is-prefill`.

**Tech Stack:** Python 3.12+ (backend), React 18 + TypeScript (frontend), ReportLab (PDF), Pydantic (validation).

**Spec:** `plans/2026-04-17-modelo200-is-design.md`

**Branch:** `claude/modelo-200-v1`

---

## File Structure

### Backend — nuevos

| File | Responsabilidad |
|------|----------------|
| `backend/app/utils/is_simulator.py` | Motor IS: ISSimulator + 7 sub-calculadoras |
| `backend/app/utils/is_scales.py` | Escalas IS por territorio + deducciones parametrizadas |
| `backend/app/routers/is_estimate.py` | Endpoints POST /api/irpf/is-estimate + /api/irpf/is-202 |
| `backend/app/tools/is_simulator_tool.py` | Tool `simulate_is` para TaxAgent |
| `backend/tests/test_is_simulator.py` | Tests unitarios del simulador (~25 tests) |
| `backend/tests/test_is_estimate.py` | Tests endpoints (~12 tests) |
| `backend/tests/test_is_202.py` | Tests pagos fraccionados (~8 tests) |

### Backend — modificados

| File | Cambio |
|------|--------|
| `backend/app/main.py` | `app.include_router(is_estimate.router)` |
| `backend/app/tools/__init__.py` | Registrar IS_SIMULATOR_TOOL en ALL_TOOLS + TOOL_EXECUTORS |
| `backend/app/services/modelo_pdf_generator.py` | Anadir `_render_200()` con casillas IS |
| `backend/app/routers/workspaces.py` | Anadir GET `/api/workspaces/{id}/is-prefill` |
| `backend/app/agents/tax_agent.py` | Actualizar system prompt con reglas IS |

### Frontend — nuevos

| File | Responsabilidad |
|------|----------------|
| `frontend/src/pages/Modelo200Page.tsx` | Wizard 4 pasos IS |
| `frontend/src/pages/Modelo200Page.css` | Estilos dark theme |
| `frontend/src/pages/Modelo202Page.tsx` | Formulario pagos fraccionados |
| `frontend/src/pages/Modelo202Page.css` | Estilos |
| `frontend/src/hooks/useIsEstimator.ts` | Hook debounced POST /api/irpf/is-estimate |
| `frontend/src/hooks/useIsPrefill.ts` | Hook GET /api/workspaces/{id}/is-prefill |
| `frontend/src/components/ISResultCard.tsx` | Componente resultado IS con desglose |
| `frontend/src/components/ISResultCard.css` | Estilos |

### Frontend — modificados

| File | Cambio |
|------|--------|
| `frontend/src/App.tsx` | Rutas /modelo-200 y /modelo-202 (lazy) |
| `frontend/src/components/Header.tsx` | Entrada en dropdown Herramientas/Calculadoras |

---

## Wave 1 — Motor de calculo backend (parallelizable)

### Task 1: Escalas IS por territorio (`is_scales.py`)

**Files:**
- Create: `backend/app/utils/is_scales.py`

- [ ] **Step 1: Crear fichero con escalas IS**

```python
"""Escalas del Impuesto sobre Sociedades por territorio.

Fuentes:
- Regimen comun: Art. 29 LIS (Ley 27/2014), actualizado Ley 7/2024
- Alava: NF 37/2013
- Bizkaia: NF 11/2013
- Gipuzkoa: NF 2/2014
- Navarra: LF 26/2016
- Canarias ZEC: Art. 43 Ley 19/1994
- Ceuta/Melilla: Art. 33.6 LIS
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ISTramo:
    base_hasta: float  # EUR, float("inf") para ilimitado
    tipo: float        # porcentaje (ej: 25.0)


@dataclass(frozen=True)
class ISRegimen:
    nombre: str
    tramos_general: list[ISTramo]
    tramos_pyme: list[ISTramo]         # facturacion <1M
    tramos_nueva_creacion: list[ISTramo]
    bonificacion_cuota: float          # 0.0 o 0.5 (Ceuta/Melilla)
    tipo_zec: float | None             # solo Canarias ZEC


# --- Regimen comun ---
COMUN = ISRegimen(
    nombre="comun",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    tramos_pyme=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 25.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 20.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

# --- Forales ---
ALAVA = ISRegimen(
    nombre="foral_alava",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_pyme=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

BIZKAIA = ISRegimen(
    nombre="foral_bizkaia",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_pyme=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

GIPUZKOA = ISRegimen(
    nombre="foral_gipuzkoa",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_pyme=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

NAVARRA = ISRegimen(
    nombre="foral_navarra",
    tramos_general=[ISTramo(float("inf"), 28.0)],
    tramos_pyme=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 28.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 28.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

CANARIAS_ZEC = ISRegimen(
    nombre="zec_canarias",
    tramos_general=[ISTramo(float("inf"), 4.0)],
    tramos_pyme=[ISTramo(float("inf"), 4.0)],
    tramos_nueva_creacion=[ISTramo(float("inf"), 4.0)],
    bonificacion_cuota=0.0,
    tipo_zec=4.0,
)

CEUTA_MELILLA = ISRegimen(
    nombre="ceuta_melilla",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    tramos_pyme=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 25.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 20.0)],
    bonificacion_cuota=0.5,  # 50% bonificacion cuota
    tipo_zec=None,
)


def get_is_regimen(territorio: str, es_zec: bool = False) -> ISRegimen:
    """Devuelve el regimen IS para un territorio.

    Usa los mismos nombres canonicos que ccaa_constants.py.
    """
    from app.utils.ccaa_constants import normalize_ccaa, FORAL_VASCO, CEUTA_MELILLA as CM_SET

    canon = normalize_ccaa(territorio)

    if es_zec and canon == "Canarias":
        return CANARIAS_ZEC
    if canon in FORAL_VASCO:
        return {"Araba": ALAVA, "Bizkaia": BIZKAIA, "Gipuzkoa": GIPUZKOA}[canon]
    if canon == "Navarra":
        return NAVARRA
    if canon in CM_SET:
        return CEUTA_MELILLA
    return COMUN


def calcular_cuota_por_tramos(base_imponible: float, tramos: list[ISTramo]) -> float:
    """Aplica escala progresiva IS y devuelve cuota integra."""
    if base_imponible <= 0:
        return 0.0
    cuota = 0.0
    restante = base_imponible
    prev_hasta = 0.0
    for tramo in tramos:
        ancho = tramo.base_hasta - prev_hasta if tramo.base_hasta != float("inf") else restante
        gravable = min(restante, ancho)
        cuota += gravable * tramo.tipo / 100
        restante -= gravable
        prev_hasta = tramo.base_hasta
        if restante <= 0:
            break
    return round(cuota, 2)


# --- Deducciones IS por territorio ---
@dataclass(frozen=True)
class ISDeduccionParams:
    id_pct: float           # I+D porcentaje
    it_pct: float           # IT porcentaje
    limite_deducciones_pct: float  # limite sobre cuota integra
    reserva_cap_pct: float  # reserva capitalizacion

IS_DEDUCCIONES_COMUN = ISDeduccionParams(id_pct=25.0, it_pct=12.0, limite_deducciones_pct=25.0, reserva_cap_pct=10.0)
IS_DEDUCCIONES_BIZKAIA = ISDeduccionParams(id_pct=30.0, it_pct=15.0, limite_deducciones_pct=35.0, reserva_cap_pct=10.0)
IS_DEDUCCIONES_GIPUZKOA = ISDeduccionParams(id_pct=30.0, it_pct=15.0, limite_deducciones_pct=35.0, reserva_cap_pct=10.0)
IS_DEDUCCIONES_NAVARRA = ISDeduccionParams(id_pct=25.0, it_pct=12.0, limite_deducciones_pct=25.0, reserva_cap_pct=10.0)

def get_is_deduccion_params(territorio: str) -> ISDeduccionParams:
    from app.utils.ccaa_constants import normalize_ccaa
    canon = normalize_ccaa(territorio)
    if canon in ("Bizkaia",):
        return IS_DEDUCCIONES_BIZKAIA
    if canon in ("Gipuzkoa",):
        return IS_DEDUCCIONES_GIPUZKOA
    if canon == "Navarra":
        return IS_DEDUCCIONES_NAVARRA
    return IS_DEDUCCIONES_COMUN
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/utils/is_scales.py
git commit -m "feat(is): escalas IS 7 territorios + deducciones parametrizadas"
```

---

### Task 2: Simulador IS (`is_simulator.py`) + tests

**Files:**
- Create: `backend/app/utils/is_simulator.py`
- Create: `backend/tests/test_is_simulator.py`

- [ ] **Step 1: Escribir tests primero (TDD)**

```python
"""Tests del simulador IS (Modelo 200)."""
import pytest
from app.utils.is_simulator import ISSimulator, ISInput, ISResult


class TestISSimulatorComun:
    """Regimen comun (25%)."""

    def test_sl_basica_25pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Madrid",
        ))
        assert r.base_imponible == 100_000
        assert r.cuota_integra == 25_000  # 25%
        assert r.tipo == "a_ingresar"

    def test_pyme_23_25_tramos(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,  # <1M = pyme
            territorio="Madrid",
        ))
        # primeros 50k al 23% = 11500, siguientes 50k al 25% = 12500
        assert r.cuota_integra == 24_000

    def test_nueva_creacion_15_20(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            tipo_entidad="nueva_creacion",
            ejercicios_con_bi_positiva=1,
            territorio="Madrid",
        ))
        # primeros 50k al 15% = 7500, siguientes 50k al 20% = 10000
        assert r.cuota_integra == 17_500

    def test_gastos_no_deducibles(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=80_000,
            gastos_no_deducibles=20_000,
            territorio="Madrid",
        ))
        assert r.base_imponible == 100_000
        assert r.ajustes_positivos == 20_000

    def test_bins_compensacion(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            bins_pendientes=30_000,
            territorio="Madrid",
        ))
        assert r.compensacion_bins == 30_000
        assert r.base_imponible == 70_000

    def test_bins_limite_70pct_grandes(self):
        """Empresas >20M facturacion: limite 70% compensacion BINs."""
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            bins_pendientes=100_000,
            facturacion_anual=25_000_000,
            territorio="Madrid",
        ))
        assert r.compensacion_bins == 70_000  # 70% de 100k
        assert r.base_imponible == 30_000

    def test_resultado_negativo(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=-50_000,
            territorio="Madrid",
        ))
        assert r.base_imponible == 0  # no puede ser negativa (genera BIN)
        assert r.cuota_integra == 0
        assert r.bin_generada == 50_000

    def test_deducciones_id(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=200_000,
            gasto_id=40_000,  # 25% = 10000 deduccion
            territorio="Madrid",
        ))
        assert r.deducciones_detalle["id"] == 10_000
        assert r.cuota_liquida == 200_000 * 0.25 - 10_000

    def test_reserva_capitalizacion(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            incremento_ffpp=50_000,  # 10% = 5000 reduccion BI
            territorio="Madrid",
        ))
        # BI = 100k - 5k (reserva cap) = 95k; limitado al 10% BI
        assert r.base_imponible == 95_000

    def test_retenciones_a_devolver(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            retenciones_ingresos_cuenta=30_000,
            territorio="Madrid",
        ))
        assert r.cuota_liquida == 25_000
        assert r.resultado_liquidacion == -5_000
        assert r.tipo == "a_devolver"


class TestISSimulatorForal:
    """Territorios forales."""

    def test_bizkaia_24pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Bizkaia",
        ))
        assert r.cuota_integra == 24_000
        assert r.regimen == "foral_bizkaia"

    def test_navarra_28pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Navarra",
        ))
        assert r.cuota_integra == 28_000
        assert r.regimen == "foral_navarra"

    def test_navarra_pyme_23_28(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Navarra",
        ))
        # 50k * 23% + 50k * 28% = 11500 + 14000 = 25500
        assert r.cuota_integra == 25_500

    def test_gipuzkoa_pyme_20_24(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Gipuzkoa",
        ))
        # 50k * 20% + 50k * 24% = 10000 + 12000 = 22000
        assert r.cuota_integra == 22_000


class TestISSimulatorEspeciales:
    """Canarias ZEC + Ceuta/Melilla."""

    def test_zec_canarias_4pct(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Canarias",
            es_zec=True,
        ))
        assert r.cuota_integra == 4_000
        assert r.regimen == "zec_canarias"

    def test_ceuta_melilla_bonificacion_50(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Melilla",
            rentas_ceuta_melilla=100_000,
        ))
        # cuota 25000, bonificacion 50% sobre rentas en territorio
        assert r.bonificaciones_total == 12_500
        assert r.cuota_liquida == 12_500

    def test_canarias_ric(self):
        r = ISSimulator.calculate(ISInput(
            resultado_contable=100_000,
            territorio="Canarias",
            dotacion_ric=50_000,
        ))
        # RIC reduce BI en dotacion (limitado a 90% beneficio no distribuido)
        assert r.base_imponible < 100_000


class TestISPagosFraccionados:
    """Modelo 202."""

    def test_202_art40_2_basico(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_2",
            cuota_integra_ultimo=50_000,
            deducciones_bonificaciones_ultimo=5_000,
            retenciones_ultimo=3_000,
        )
        # 18% de (50000 - 5000 - 3000) = 18% de 42000 = 7560
        assert r.pago_trimestral == 7_560

    def test_202_art40_3_basico(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=5_000_000,
        )
        # 17% de 100000 = 17000
        assert r.pago_trimestral == 17_000

    def test_202_art40_3_grande(self):
        r = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=100_000,
            facturacion_anual=15_000_000,
        )
        # >10M: 24% de 100000 = 24000
        assert r.pago_trimestral == 24_000
```

- [ ] **Step 2: Ejecutar tests — deben fallar**

```bash
cd backend && pytest tests/test_is_simulator.py -v
# Expected: FAIL — ImportError (is_simulator no existe)
```

- [ ] **Step 3: Implementar ISSimulator**

Crear `backend/app/utils/is_simulator.py` con las clases `ISInput`, `ISResult`, `IS202Result` y `ISSimulator` con metodos `calculate()` y `calcular_202()`. Seguir el patron de composicion de `irpf_simulator.py`. Cada sub-calculo es un metodo privado (`_calcular_base_imponible`, `_aplicar_bins`, `_calcular_cuota`, `_aplicar_deducciones`, `_aplicar_bonificaciones`).

- [ ] **Step 4: Ejecutar tests — deben pasar**

```bash
cd backend && pytest tests/test_is_simulator.py -v
# Expected: 25 PASS
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/is_simulator.py backend/tests/test_is_simulator.py
git commit -m "feat(is): simulador IS con 25 tests (7 territorios, BINs, deducciones)"
```

---

### Task 3: Endpoint `/api/irpf/is-estimate` + tests

**Files:**
- Create: `backend/app/routers/is_estimate.py`
- Create: `backend/tests/test_is_estimate.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Escribir tests del endpoint**

Tests de request valido modo manual, validacion, territorio invalido, resultado a devolver, etc. (~12 tests)

- [ ] **Step 2: Implementar router con Pydantic models**

`ISEstimateRequest`, `ISEstimateResponse`, endpoints POST `/is-estimate` y POST `/is-202`. Registrar en `main.py` con `app.include_router(is_estimate.router)`.

- [ ] **Step 3: Tests pasan**

```bash
cd backend && pytest tests/test_is_estimate.py -v
# Expected: 12 PASS
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/is_estimate.py backend/tests/test_is_estimate.py backend/app/main.py
git commit -m "feat(is): endpoints POST /api/irpf/is-estimate + /api/irpf/is-202"
```

---

### Task 4: Workspace IS prefill endpoint

**Files:**
- Modify: `backend/app/routers/workspaces.py`
- Create: `backend/tests/test_is_prefill.py`

- [ ] **Step 1: Tests del prefill**

Test workspace con libro_registro completo, workspace vacio, workspace de otro usuario (404).

- [ ] **Step 2: Implementar GET `/api/workspaces/{id}/is-prefill`**

Lee agregaciones del `libro_registro` (ingresos, gastos, resultado) filtrado por ejercicio. Devuelve `ISPrefillResponse` con desglose por cuenta PGC.

- [ ] **Step 3: Tests pasan**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(is): workspace IS prefill endpoint con desglose PGC"
```

---

### Task 5: Tool `simulate_is` para TaxAgent

**Files:**
- Create: `backend/app/tools/is_simulator_tool.py`
- Modify: `backend/app/tools/__init__.py`
- Modify: `backend/app/agents/tax_agent.py`

- [ ] **Step 1: Crear tool definition + executor**

Mismo patron que `irpf_simulator_tool.py`: dict con OpenAI function spec + `async def simulate_is_tool(db, params)`.

- [ ] **Step 2: Registrar en `__init__.py`**

Anadir `IS_SIMULATOR_TOOL` a `ALL_TOOLS` y `"simulate_is": simulate_is_tool` a `TOOL_EXECUTORS`.

- [ ] **Step 3: Actualizar system prompt TaxAgent**

Anadir regla: si usuario menciona "mi empresa", "SL", "sociedades", "modelo 200", "impuesto de sociedades" → usar `simulate_is`. No asumir que es empresa si no lo dice explicitamente.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(is): tool simulate_is registrado en TaxAgent"
```

---

### Task 6: PDF borrador Modelo 200

**Files:**
- Modify: `backend/app/services/modelo_pdf_generator.py`

- [ ] **Step 1: Anadir `_render_200()` al generador**

Casillas principales: 552 (BI), 558 (tipo), 560 (cuota integra), 582 (deducciones), 592 (cuota liquida), 595 (retenciones), 599 (resultado). Reutilizar `_render_casillas_table()` y `_render_resultado()`.

- [ ] **Step 2: Registrar "200" en VALID_MODELOS**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(is): PDF borrador Modelo 200 con casillas principales"
```

---

## Wave 2 — Frontend (parallelizable con Wave 1 tras Task 1)

### Task 7: Hook `useIsEstimator` + types

**Files:**
- Create: `frontend/src/hooks/useIsEstimator.ts`
- Create: `frontend/src/types/is.ts`

- [ ] **Step 1: Crear types IS**

```typescript
export interface ISEstimateInput {
  workspace_id?: string;
  ejercicio: number;
  tipo_entidad: "sl" | "slp" | "sa" | "nueva_creacion";
  territorio: string;
  facturacion_anual: number;
  ejercicios_con_bi_positiva: number;
  resultado_contable?: number;
  ingresos_explotacion?: number;
  gastos_explotacion?: number;
  gastos_no_deducibles: number;
  bins_pendientes: number;
  gasto_id: number;
  gasto_it: number;
  incremento_ffpp: number;
  donativos: number;
  es_zec: boolean;
  rentas_ceuta_melilla: number;
  retenciones_ingresos_cuenta: number;
  pagos_fraccionados_realizados: number;
}

export interface ISEstimateResult {
  resultado_contable: number;
  base_imponible: number;
  cuota_integra: number;
  deducciones_total: number;
  cuota_liquida: number;
  resultado_liquidacion: number;
  tipo: "a_ingresar" | "a_devolver";
  tipo_efectivo: number;
  regimen: string;
  pago_fraccionado_202_art40_2: number | null;
  pago_fraccionado_202_art40_3: number | null;
  disclaimer: string;
}
```

- [ ] **Step 2: Crear hook (mirror useIrpfEstimator)**

600ms debounce, POST `/irpf/is-estimate` via `apiRequest`, abort pattern, guards.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(is): useIsEstimator hook + types IS"
```

---

### Task 8: Hook `useIsPrefill`

**Files:**
- Create: `frontend/src/hooks/useIsPrefill.ts`

- [ ] **Step 1: Implementar hook**

GET `/workspaces/{id}/is-prefill?ejercicio=X` via `apiRequest`. Devuelve datos pre-rellenados o null si workspace no tiene datos suficientes.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(is): useIsPrefill hook para auto-fill desde workspace"
```

---

### Task 9: Pagina `/modelo-200` (wizard 4 pasos)

**Files:**
- Create: `frontend/src/pages/Modelo200Page.tsx`
- Create: `frontend/src/pages/Modelo200Page.css`
- Create: `frontend/src/components/ISResultCard.tsx`
- Create: `frontend/src/components/ISResultCard.css`

- [ ] **Step 1: Implementar wizard**

4 pasos: datos entidad (con WorkspaceSelector), resultado contable (manual o prefill), ajustes/deducciones, resultado (ISResultCard + LiveEstimatorBar). Dark theme consistente con design system. useSEO con schema WebApplication.

- [ ] **Step 2: Implementar ISResultCard**

Desglose visual paso-a-paso del calculo. Verde/rojo para a devolver/ingresar. Tipo efectivo. Estimacion 202.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(is): pagina /modelo-200 wizard 4 pasos + ISResultCard"
```

---

### Task 10: Pagina `/modelo-202` + rutas + header

**Files:**
- Create: `frontend/src/pages/Modelo202Page.tsx`
- Create: `frontend/src/pages/Modelo202Page.css`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Header.tsx`

- [ ] **Step 1: Implementar formulario 202**

Selector modalidad, inputs, resultado 3 pagos trimestrales.

- [ ] **Step 2: Registrar rutas en App.tsx**

```tsx
const Modelo200Page = lazy(() => import("./pages/Modelo200Page"));
const Modelo202Page = lazy(() => import("./pages/Modelo202Page"));
// Rutas publicas (sin auth para modo manual)
<Route path="/modelo-200" element={<Modelo200Page />} />
<Route path="/modelo-202" element={<Modelo202Page />} />
```

- [ ] **Step 3: Anadir a Header.tsx**

Entrada en dropdown "Calculadoras" o "Herramientas".

- [ ] **Step 4: Build + commit**

```bash
cd frontend && npm run build
git commit -m "feat(is): pagina /modelo-202 + rutas App.tsx + entrada Header"
```

---

## Wave 3 — Integracion + verificacion

### Task 11: Frontend tests (Vitest)

**Files:**
- Create: `frontend/src/pages/Modelo200Page.test.tsx`

- [ ] **Step 1: Tests del wizard**

Renderiza 4 pasos, selector workspace, pre-fill, resultado, LiveEstimatorBar. ~8 tests.

- [ ] **Step 2: Commit**

```bash
git commit -m "test(is): Vitest tests Modelo200Page wizard"
```

---

### Task 12: Build + regression + commit final

- [ ] **Step 1: Backend tests completos**

```bash
cd backend && pytest tests/test_is_simulator.py tests/test_is_estimate.py tests/test_is_202.py tests/test_is_prefill.py -v
# Expected: ~45 PASS
```

- [ ] **Step 2: Frontend build**

```bash
cd frontend && npm run build
# Expected: exit 0
```

- [ ] **Step 3: Frontend tests**

```bash
cd frontend && npx vitest run
# Expected: all PASS
```

- [ ] **Step 4: Commit final**

```bash
git commit -m "chore(is): verificacion final — tests + build OK"
```

---

## Parallelization Map

```
Wave 1 (backend):
  Task 1 (scales) → Task 2 (simulator+tests) → Task 3 (endpoint) → Task 4 (prefill) → Task 5 (tool) → Task 6 (PDF)

Wave 2 (frontend, puede empezar tras Task 1):
  Task 7 (hook+types) → Task 8 (prefill hook) → Task 9 (wizard page) → Task 10 (202+rutas)

Wave 3 (integracion, tras Wave 1+2):
  Task 11 (frontend tests) → Task 12 (verificacion)
```

**Grupos RuFlo:**
- **Grupo A** (backend motor): Task 1 → 2 → 3 secuencial
- **Grupo B** (backend integracion): Task 4 + 5 + 6 paralelo (tras Grupo A)
- **Grupo C** (frontend): Task 7 → 8 → 9 → 10 secuencial (puede empezar tras Task 1)
- **Grupo D** (verificacion): Task 11 → 12 (tras todo)
