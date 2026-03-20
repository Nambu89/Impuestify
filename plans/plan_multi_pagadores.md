# Plan: Soporte Multi-Pagadores en Perfil Fiscal + Simulador IRPF

> **Objetivo**: Permitir que el usuario registre multiples pagadores (como muestra la app AEAT), con desglose por cada uno, y que el simulador IRPF use estos datos para un calculo mas preciso + deteccion de obligacion de declarar.

> **Motivacion**: El 30% de los asalariados espanoles tienen 2+ pagadores. La app AEAT muestra desglose por pagador. Ser fieles a la realidad fiscal.

> **Impacto**: Perfil fiscal, Guia fiscal, Simulador IRPF, LLM tools, Deteccion obligacion declarar.

> **Verificacion plan-checker**: v2 — todos los issues I1-I7 y warnings W1-W4 resueltos.

---

## Modelo de datos: Pagador

```python
# Backend (Pydantic)
class PagadorItem(BaseModel):
    nombre: str = ""                    # "DEVOTEAM DRAGO SAU"
    nif: Optional[str] = None           # "B73737553" (opcional, futuro)
    clave: str = "empleado"             # "empleado" | "pensionista" | "desempleo" | "otro"
    retribuciones_dinerarias: float = 0 # 22.300,99
    retenciones: float = 0             # 4.046,27
    gastos_deducibles: float = 0       # 1.445,00 (SS del trabajador)
    retribuciones_especie: float = 0   # Retrib. en especie (coche empresa, seguro, etc.)
    ingresos_cuenta: float = 0         # Ingresos a cuenta
```

```typescript
// Frontend (TypeScript)
interface Pagador {
  nombre: string
  nif?: string
  clave: 'empleado' | 'pensionista' | 'desempleo' | 'otro'
  retribuciones_dinerarias: number
  retenciones: number
  gastos_deducibles: number
  retribuciones_especie: number
  ingresos_cuenta: number
}
```

**Nota**: Campos de incapacidad temporal (IT) quedan FUERA de scope. Se implementaran cuando se aborde el art. 7 LIRPF completo.

---

## Constantes de obligacion (actualizables por ejercicio)

```python
# backend/app/routers/irpf_estimate.py
OBLIGACION_LIMITES = {
    2025: {
        "un_pagador": 22_000,
        "multi_pagador": 15_876,
        "segundo_pagador_minimo": 1_500,
        "rentas_inmobiliarias": 1_000,
        "rendimientos_capital": 1_600,
        "ganancias_patrimoniales": 1_000,
    }
}
```

---

## Tareas

### T1. Backend — Modelo Pydantic + Agregacion + Persistencia

**Archivos**:
- `backend/app/routers/irpf_estimate.py`
- `backend/app/routers/user_rights.py`

**Acciones**:
1. Crear modelo `PagadorItem(BaseModel)` (ver modelo arriba) en `irpf_estimate.py`
2. Anadir a `IRPFEstimateRequest`:
   - `pagadores: List[PagadorItem] = Field(default_factory=list)`
   - `num_pagadores: int = 1`
3. Anadir a `FiscalProfileRequest` (en `user_rights.py`):
   - `pagadores: Optional[List[PagadorItem]] = None` (mismo tipo, con validacion Pydantic)
   - `num_pagadores: Optional[int] = None`
4. **Anadir `'pagadores'` y `'num_pagadores'` a `_DATOS_FISCALES_KEYS`** en `user_rights.py`
5. Logica de agregacion en endpoint `/api/irpf/estimate`:
   - Si `pagadores` tiene items: agregar totales automaticamente
     - `ingresos_trabajo = sum(p.retribuciones_dinerarias + p.retribuciones_especie + p.ingresos_cuenta)`
     - `retenciones_trabajo = sum(p.retenciones)`
     - `ss_empleado = sum(p.gastos_deducibles)`
     - `num_pagadores = len(pagadores)`
   - Si `pagadores` esta vacio: usar `ingresos_trabajo` directo (retrocompatible)

**Verificacion**: `pytest tests/test_multi_pagadores.py -v` pasa

### T2. Backend — Deteccion obligacion de declarar

**Archivo**: `backend/app/routers/irpf_estimate.py`

**Acciones**:
1. Crear dict `OBLIGACION_LIMITES` con constantes por ano (ver arriba)
2. Crear funcion `calcular_obligacion_declarar(body, ingresos_trabajo, year)`:
   - 1 pagador: obligado si `ingresos_trabajo > limite_un_pagador`
   - 2+ pagadores: ordenar por retribuciones DESC, sumar del 2o en adelante. Si suma > 1.500 EUR → limite = 15.876, sino → limite = 22.000
   - Siempre obligado si: rentas inmobiliarias > 1.000, rendimientos capital > 1.600, ganancias > 1.000
3. Anadir al response dict: `obligacion_declarar: { obligado: bool, motivo: str, limite_aplicable: float }`

**Verificacion**: `pytest tests/test_multi_pagadores.py -v` pasa (tests de obligacion)

### T3. Backend — Simulador IRPF (retrib. especie + ingresos cuenta)

**Archivos**:
- `backend/app/utils/irpf_simulator.py` (logica de calculo real)
- `backend/app/tools/irpf_simulator_tool.py` (wrapper LLM)

**Acciones**:
1. En `irpf_simulator.py` — funcion `simulate()`:
   - Anadir parametros: `retribuciones_especie: float = 0`, `ingresos_cuenta: float = 0`
   - Sumar a base imponible del trabajo: `base_trabajo = ingresos_trabajo + retribuciones_especie + ingresos_cuenta`
2. En `irpf_simulator_tool.py`:
   - Anadir a `IRPF_SIMULATOR_TOOL` dict (OpenAI function schema): `retribuciones_especie`, `ingresos_cuenta`, `pagadores`, `num_pagadores`
   - En `simulate_irpf_tool()`: si `pagadores` presente, agregar totales antes de llamar al simulador
   - Patron EXTEND: defaults = 0, no rompe nada

**Verificacion**: `pytest tests/test_irpf_simulator.py -v` sigue pasando + nuevos tests

### T4. Frontend — Interfaces TypeScript

**Archivos**:
- `frontend/src/hooks/useFiscalProfile.ts`
- `frontend/src/hooks/useIrpfEstimator.ts`

**Acciones**:
1. En `useFiscalProfile.ts`:
   - Crear tipo `Pagador` (ver modelo TS arriba)
   - Anadir a `FiscalProfile`: `pagadores: Pagador[] | null` y `num_pagadores: number | null`
   - Anadir a `EMPTY_PROFILE`: `pagadores: null` y `num_pagadores: null`
2. En `useIrpfEstimator.ts`:
   - Anadir a `IrpfEstimateResult`: `obligacion_declarar?: { obligado: boolean, motivo: string, limite_aplicable: number }`
   - Actualizar payload builder para incluir `pagadores` y `num_pagadores` cuando esten presentes en los datos

**Verificacion**: `npm run build` pasa sin errores TS

### T5. Frontend — Componente MultiPagadorForm

**Archivo nuevo**: `frontend/src/components/MultiPagadorForm.tsx`

**Acciones**:
Componente reutilizable:
- Props: `pagadores: Pagador[]`, `onChange: (pagadores: Pagador[]) => void`
- Lista de pagadores con boton "Anadir pagador" (maximo 10)
- Por cada pagador: acordeon expandible con:
  - Nombre (text input)
  - Clave (select: Empleado/Pensionista/Desempleo/Otro)
  - Retribuciones dinerarias (number)
  - Retenciones (number)
  - Gastos deducibles - SS (number)
  - Retribuciones en especie (number, colapsado por defecto)
- Boton eliminar por pagador (con confirmacion si tiene datos)
- Totales calculados automaticamente en la parte inferior
- CSS en `MultiPagadorForm.css` (patron existente)
- UX: similar a la app AEAT (acordeones por pagador)

**Verificacion**: `npm run build` pasa

### T6. Frontend — Integrar en TaxGuidePage (Step 2: Trabajo)

**Archivos**:
- `frontend/src/pages/TaxGuidePage.tsx`

**Acciones**:
1. En `StepTrabajo`:
   - Anadir toggle: "Un pagador / Varios pagadores" (toggle-group existente)
   - Si "Un pagador": formulario actual (sin cambios)
   - Si "Varios pagadores": mostrar `MultiPagadorForm`
   - Los totales alimentan `data.ingresos_trabajo`, `data.retenciones_trabajo`, `data.ss_empleado` automaticamente
2. Anadir `pagadores: []` y `num_pagadores: 1` al estado inicial del wizard
3. En el payload que se envia al estimador: incluir `pagadores` cuando `num_pagadores > 1`
4. Si hay 2+ pagadores: mostrar alerta informativa sobre obligacion de declarar (client-side pre-calculo)

**Verificacion**: `npm run build` pasa + UI funcional manual

### T7. Frontend — Integrar en SettingsPage (Perfil Fiscal)

**Archivo**: `frontend/src/pages/SettingsPage.tsx`

**Acciones**:
- Anadir seccion "Pagadores" despues de la seccion de rendimientos del trabajo
- Mostrar `MultiPagadorForm` con datos del perfil fiscal
- Guardar array `pagadores` al hacer save del perfil
- **NO tocar DynamicFiscalForm** (es data-driven, no hardcoded)

**Verificacion**: `npm run build` pasa + guardar/recuperar funciona

### T8. Frontend — Alerta obligacion declarar en LiveEstimatorBar

**Archivo**: `frontend/src/components/LiveEstimatorBar.tsx`

**Acciones**:
- Leer `result.obligacion_declarar` del response del estimador
- Si `obligado === true`: mostrar badge con icono alerta
- Texto: "Estas obligado a declarar" con motivo al hacer hover/click
- Si `obligado === false` y hay datos: mostrar "No estas obligado a declarar" (informativo)
- Ortografia: "Esta**s**" con tilde verificada

**Verificacion**: `npm run build` pasa

### T9. Tests

**Archivos**: `backend/tests/test_multi_pagadores.py` (nuevo)

**Tests backend**:
1. Un pagador — retrocompatibilidad (`ingresos_trabajo` directo, `pagadores` vacio)
2. Multiples pagadores — agregacion correcta de totales
3. Pagadores con retribuciones en especie — suman a base imponible
4. Obligacion declarar: 1 pagador < 22.000 → no obligado
5. Obligacion declarar: 1 pagador > 22.000 → obligado
6. Obligacion declarar: 2 pagadores, 2o > 1.500 y total > 15.876 → obligado
7. Obligacion declarar: 2 pagadores, 2o < 1.500 → no obligado (aplica limite 22.000)
8. Obligacion declarar: 3 pagadores, suma 2o+3o > 1.500 → obligado
9. Perfil fiscal: guardar/recuperar pagadores en `datos_fiscales` JSON
10. Validacion Pydantic: PagadorItem rechaza campos invalidos
11. LLM tool: simulate_irpf_tool con pagadores agrega correctamente

**Verificacion frontend**: `npm run build` pasa sin errores

---

## Archivos impactados (completo)

| Archivo | Tarea | Tipo cambio |
|---------|-------|-------------|
| `backend/app/routers/irpf_estimate.py` | T1, T2 | Modelo + endpoint |
| `backend/app/routers/user_rights.py` | T1 | Modelo + `_DATOS_FISCALES_KEYS` |
| `backend/app/utils/irpf_simulator.py` | T3 | Params simulador |
| `backend/app/tools/irpf_simulator_tool.py` | T3 | Tool dict + wrapper |
| `frontend/src/hooks/useFiscalProfile.ts` | T4 | Interface + EMPTY_PROFILE |
| `frontend/src/hooks/useIrpfEstimator.ts` | T4 | Interface + payload |
| `frontend/src/components/MultiPagadorForm.tsx` | T5 | **NUEVO** |
| `frontend/src/components/MultiPagadorForm.css` | T5 | **NUEVO** |
| `frontend/src/pages/TaxGuidePage.tsx` | T6 | StepTrabajo |
| `frontend/src/pages/SettingsPage.tsx` | T7 | Seccion pagadores |
| `frontend/src/components/LiveEstimatorBar.tsx` | T8 | Alerta obligacion |
| `backend/tests/test_multi_pagadores.py` | T9 | **NUEVO** |

## Retrocompatibilidad

- **100% retrocompatible**: Si `pagadores` esta vacio/null, se usa `ingresos_trabajo` directo
- No se modifica la tabla de BD (todo va en el JSON `datos_fiscales`)
- No se rompe ningun endpoint existente
- Patron EXTEND del simulador respetado
- PagadorItem con defaults en todos los campos

## Orden de implementacion

1. T1 (backend models + agregacion + persistencia)
2. T2 (obligacion de declarar)
3. T3 (simulador + LLM tool)
4. T4 (TS interfaces)
5. T5 (MultiPagadorForm component)
6. T6 (TaxGuidePage integration)
7. T7 (SettingsPage integration)
8. T8 (LiveEstimatorBar alert)
9. T9 (tests — ejecutar tras cada tarea, test suite completo al final)

## Fuera de scope (futuro)

- Import automatico desde XML/fichero AEAT
- OCR de capturas de la app AEAT
- NIF validation del pagador
- Campos IT (incapacidad temporal) con exencion art. 7 LIRPF
- Modelo 190 (declaracion informativa del pagador)
- Integracion DynamicFiscalForm backend-driven (requiere cambio en endpoint fiscal-fields)
