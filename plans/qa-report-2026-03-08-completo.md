# QA Report — Impuestify (Sesion Completa)
> Fecha: 2026-03-08
> Perfiles testeados: Particular (test.particular@impuestify.es)
> Entorno: https://impuestify.com (produccion)
> Metodologia: Analisis estatico exhaustivo del codigo + scripts Playwright generados
> Nota: Playwright MCP no disponible en esta sesion — se uso inspeccion directa de codigo fuente

---

## Resumen ejecutivo

| Metrica | Valor |
|---------|-------|
| Componentes analizados | 12 |
| Bugs criticos | 3 |
| Bugs mayores | 5 |
| Bugs menores | 4 |
| Sugerencias UX | 6 |
| Script Playwright generado | tests/e2e/qa-session-completa-2026-03-08.spec.ts |

---

## PRIORIDAD MAXIMA: /guia-fiscal

### Estado del deployement

Segun el historial de agent-comms.md, la feature TaxGuidePage fue implementada el 2026-03-06 pero en aquella sesion QA (sesion 5) se confirmo que `/guia-fiscal` redirigía a `/subscribe` para el usuario `particular`. En sesion 5 se reporto como B15 con estado "pendiente aclarar si es intencional".

**Verificacion del codigo actual (2026-03-08):**

`App.tsx` linea 95-100:
```tsx
path="/guia-fiscal"
element={
    <ProtectedRoute>
        <TaxGuidePage />
    </ProtectedRoute>
}
```

`App.tsx` linea 47-59:
```tsx
function ProtectedRoute({ children, requireSubscription = true }) {
    const { hasAccess, loading: subLoading } = useSubscription()
    if (requireSubscription && !hasAccess) {
        // redirige a /subscribe
    }
}
```

`useSubscription.ts` linea 100:
```typescript
const hasAccess = data?.has_access || isOwner
```

**Conclusion:** La ruta `/guia-fiscal` usa `requireSubscription={true}` (valor por defecto). Para que un usuario `particular` tenga acceso, su `has_access` debe ser `true` en el backend.

El endpoint `GET /api/subscription/status` devuelve `has_access=True` cuando:
- `subscription_status = 'active'` O
- `grace_period_until` es futuro

Si el usuario `test.particular@impuestify.es` tiene una suscripcion activa (plan `particular` activo en Stripe), `has_access` debería ser `true` y la guia fiscal deberia cargar.

**Pendiente de verificacion en produccion** — necesita Playwright MCP o ejecucion manual del script.

---

## BUG CRITICO B-GF-01: TaxGuidePage sin seccion hero visible

**Severidad:** CRITICA
**Componente:** `frontend/src/pages/TaxGuidePage.tsx`
**Tipo:** Bug de estructura UI — contenido perdido

**Descripcion:**
El CSS define `.tax-guide__header` con un hero de titulo y descripcion (lineas 12-53 de TaxGuidePage.css), pero el componente `TaxGuidePage` (JSX lineas 1096-1153) NO renderiza ese div:

```tsx
// Lo que hay en el JSX:
return (
    <div className="tax-guide">
        <Header />                    // header global de la app
        <div className="tax-guide__layout">  // directamente al layout
            ...
```

No hay `<div className="tax-guide__header">` en el JSX. El CSS del hero nunca se aplica. El usuario llega a la guia fiscal y ve directamente los pasos del wizard sin contexto — sin titulo "Guia Fiscal", sin descripcion de que es la pagina.

**Expected:** Hero visible con titulo "Guia Fiscal IRPF" y descripcion antes del wizard.
**Actual:** El wizard empieza directamente sin titulo ni contexto.
**Impacto:** UX pobre — el usuario no sabe que pagina es.

---

## BUG CRITICO B-GF-02: /api/irpf/estimate requiere autenticacion JWT

**Severidad:** CRITICA (si la guia fiscal se quiere usar sin login en el futuro)
**Componente:** `backend/app/routers/irpf_estimate.py` linea 130
**Tipo:** Discrepancia documentacion vs implementacion

**Descripcion:**
El CLAUDE.md dice "(no auth required for estimate)" pero el endpoint tiene:
```python
async def estimate_irpf(
    request: IRPFEstimateRequest,
    req: object = None,
    current_user: TokenData = Depends(get_current_user),  # AUTH REQUERIDO
):
```

El endpoint `/api/irpf/estimate` requiere JWT. Esto es correcto para el flujo actual (usuario logeado en /guia-fiscal). Solo es bug si se pretende que sea publico (ej. para landing de captacion).

**Accion:** Actualizar CLAUDE.md para reflejar que la autenticacion es requerida, O si se quiere hacer publico, eliminar `Depends(get_current_user)` y cambiar a `Optional[TokenData]`.

---

## BUG CRITICO B-GF-03: IrpfEstimateResult.cuota_liquida_total inconsistente

**Severidad:** MAYOR (puede causar error JS en produccion)
**Componente:** Frontend `useIrpfEstimator.ts` vs Backend `irpf_estimate.py`
**Tipo:** Mismatch de tipos entre frontend y backend

**Descripcion:**
El hook `useIrpfEstimator.ts` define en su interface (linea 67):
```typescript
cuota_liquida_total: number
```

El backend devuelve el campo `cuota_liquida_total` (linea 101 de irpf_estimate.py):
```python
cuota_liquida_total: float = 0
```

Hasta aqui hay consistencia. PERO en `TaxGuidePage.tsx` linea 699:
```tsx
<BreakdownRow label="Cuota liquida total" value={result.cuota_liquida_total} />
```

Y `agent-comms.md` menciona un "Bug fix: cuota_liquida_total key → cuota_total" del 2026-03-06. Esto sugiere que en algun momento el campo se llamo diferente. Verificar que el campo devuelto por el simulador (`irpf_simulator.py`) efectivamente se mapea a `cuota_liquida_total` en el response y no a `cuota_total`.

**Verificar en produccion:** Hacer POST a `/api/irpf/estimate` con datos de prueba y comprobar que la respuesta incluye `cuota_liquida_total` (no `cuota_total`).

---

## BUG MAYOR B-GF-04: LiveEstimatorBar — bug de orden de renderizado

**Severidad:** MAYOR
**Componente:** `frontend/src/components/LiveEstimatorBar.tsx`
**Tipo:** UX — estado vacio confuso

**Descripcion:**
La condicion en LiveEstimatorBar linea 18:
```tsx
if (!result && !loading) {
    return <placeholder "Introduce tus datos..." />
}
```

Cuando el usuario carga la pagina con CCAA pre-rellenada del perfil fiscal (`useEffect` en TaxGuidePage linea 856), el hook `useIrpfEstimator` se llama inmediatamente pero con debounce de 600ms. Durante esos 600ms, `loading` es `false` y `result` es `null`, mostrando el placeholder. Luego entra en `loading=true` y muestra el spinner. Esto causa un "flash" visual del estado vacio que puede confundir.

**Expected:** Si hay un perfil pre-rellenado, el estimator deberia empezar directamente en loading.
**Actual:** Flash de 600ms de estado vacio incluso cuando el perfil esta completo.

---

## BUG MAYOR B-GF-05: Wizard "Quick" mode — resultado inmediato sin datos suficientes

**Severidad:** MAYOR
**Componente:** `frontend/src/pages/TaxGuidePage.tsx` lineas 1071-1086
**Tipo:** Logica de negocio

**Descripcion:**
En modo "Rapido" (quick), el paso 0 incluye StepPersonal + StepTrabajo. El estimador IRPF se lanza con debounce cada vez que cambian los datos. Si el usuario selecciona CCAA y la guia tiene ingresos_trabajo > 0 en el perfil pre-rellenado, el resultado del estimador aparece en el sidebar ANTES de que el usuario haya rellenado ningún dato en el paso actual.

Esto puede ser buena UX (ver el resultado actualizado en tiempo real) pero es confuso porque el resultado mostrado corresponde al perfil guardado, no al que el usuario esta rellenando.

**Sugerencia:** Resetear los datos del estimador cuando el usuario entra al wizard en modo rapido y no haya guardado datos previamente.

---

## BUG MAYOR B-GF-06: `canProceed` solo valida paso 0

**Severidad:** MAYOR
**Componente:** `TaxGuidePage.tsx` linea 1094
**Tipo:** Validacion incompleta

```tsx
const canProceed = step === 0 ? !!data.comunidad_autonoma : true
```

Solo se valida que haya CCAA en el paso 0. En todos los pasos posteriores `canProceed = true` siempre, permitiendo avanzar al paso de Resultado sin haber introducido ningun ingreso. El resultado del estimador mostrara "Completa los pasos anteriores..." pero el usuario puede llegar al final con todos los campos vacios.

**Expected:** Validar en el paso de Trabajo que hay al menos un ingreso > 0 antes de permitir avanzar al paso de Resultado.
**Actual:** Se puede llegar al Resultado con 0 en todos los campos.

---

## BUG MAYOR B-GF-07: `useDeductionDiscovery` — sin manejo de errores en UI

**Severidad:** MAYOR
**Componente:** `TaxGuidePage.tsx` lineas 604-659 + `useDeductionDiscovery.ts` lineas 66-70
**Tipo:** Manejo de errores

**Descripcion:**
El hook `useDeductionDiscovery` en caso de error simplemente hace `setResult(null)` sin guardar el error. En la UI (StepDeducciones), el bloque `{discoveryResult && ...}` no se renderiza. El usuario ve la seccion "Deducciones descubiertas para Madrid" con el titulo pero sin contenido ni mensaje de error — parece que no hay deducciones.

**Expected:** Si la llamada a `/api/irpf/deductions/discover` falla, mostrar un mensaje "No se pudieron cargar las deducciones. Intentalo de nuevo."
**Actual:** Silencio total — la seccion queda vacia sin explicacion.

---

## BUG MENOR B-GF-08: Acentos faltantes en textos del wizard

**Severidad:** MENOR
**Componente:** `TaxGuidePage.tsx` multiples lugares
**Tipo:** Contenido / i18n

Textos con acentos faltantes o inconsistentes (detectados en el codigo):
- Linea 147: "Necesitamos saber donde resides" → deberia ser "dónde"
- Linea 298: "dejalo en 0" → "déjalo"
- Linea 584: "reducen la base imponible" — correcto
- `QUICK_STEP_LABELS` linea 139: "Datos basicos" → "Datos básicos"
- `STEP_LABELS` linea 128-136: "Ahorro e inversiones" — correcto

Nota: Esto puede ser intencional para evitar problemas de encoding en algunos entornos, pero en produccion con UTF-8 deberian usarse los acentos correctos.

---

## BUG MENOR B-GF-09: Step animation con `useMemo` — dependencias incorrectas

**Severidad:** MENOR
**Componente:** `TaxGuidePage.tsx` linea 1088-1090
**Tipo:** React anti-pattern

```tsx
const stepContent = useMemo(() => {
    return isQuick ? renderQuickStep() : renderFullStep()
}, [step, data, updateData, result, loading, handleSaveProfile, savingProfile, saveProfileDone, discoveryResult, discoveryLoading, discoveryAnswers, handleAnswerQuestion, isQuick])
```

Las funciones `renderQuickStep` y `renderFullStep` no estan en las dependencias del `useMemo`, pero se recalculan en cada render igualmente porque las funciones se redefinen en cada render. El `useMemo` no tiene efecto real aqui y puede ocultar bugs de stale closures.

**Expected:** Usar `useCallback` para `renderFullStep` y `renderQuickStep` con sus dependencias correctas, o simplemente eliminar el `useMemo` y renderizar directamente.

---

## Otros flujos — Hallazgos

### T01: Landing Page

**Estado:** PENDIENTE verificacion en produccion

Desde el codigo de `Home.tsx` (commit f3d6ca7 sesion 6), la landing tiene las secciones:
- Hero con imagen estatica `hero-spain-3d.webp`
- Stats (CountUp): analizar si los valores son 428+, 64, 21
- Comparativa con TaxDown
- Features
- Pricing (plan particular 5€/mes + autonomo 39€/mes)
- CTA footer

**Pendiente:** Verificar en produccion que la seccion de pricing muestra AMBOS planes (B3 del desktop audit decia que solo aparecia el plan Particular).

### T05: Settings — Perfil Fiscal

**Estado:** Funcionando segun sesiones anteriores (sesion 8b)
- CCAA select funciona y persiste
- 20 opciones de CCAA incluyendo Melilla
- Tabs: Personal, Seguridad, Perfil Fiscal, Suscripcion, Privacidad

### T06: /modelos-trimestrales

**Estado:** Desplegado (commit e61633d, sesion 8b)
- Ruta: `/modelos-trimestrales` (alias: `/declaraciones`)
- Plan particular: muestra Modelo 303 + 130
- Plan autonomo: igual pero con mas campos

### B13: Menu hamburguesa mobile

**Estado:** Pendiente verificacion del commit `0ab0a9e`
- Segun sesion 5: el hamburger abre ConversationSidebar en lugar de mobile-nav
- El commit `0ab0a9e` dice "fix" en el historial
- Necesita verificacion en produccion — no hay screenshots post-fix

### B14: Stats landing incorrectas

**Estado:** Pendiente
- Sesion 5 detecto: 138+ documentos / 47 deducciones / 7 territorios
- Deberia ser: 428+ / 64 o 128 / 21
- `Home.tsx` actualizado en sesion 6 (commit f3d6ca7) con "128 deducciones"

---

## Tabla de bugs

| ID | Severidad | Area | Descripcion | Estado |
|----|-----------|------|-------------|--------|
| B-GF-01 | CRITICA | Guia Fiscal | Hero del wizard no se renderiza — falta `div.tax-guide__header` en JSX | NUEVO |
| B-GF-02 | CRITICA* | API | `/api/irpf/estimate` requiere JWT — CLAUDE.md incorrecto dice "no auth" | NUEVO |
| B-GF-03 | MAYOR | API/Frontend | Verificar que `cuota_liquida_total` (no `cuota_total`) llega del backend | NUEVO |
| B-GF-04 | MAYOR | Guia Fiscal | Flash de 600ms en LiveEstimatorBar con perfil pre-rellenado | NUEVO |
| B-GF-05 | MAYOR | Guia Fiscal | Modo rapido muestra resultado pre-rellenado antes de que usuario lo cambie | NUEVO |
| B-GF-06 | MAYOR | Guia Fiscal | `canProceed` no valida ingresos — usuario puede ir al resultado con todo 0 | NUEVO |
| B-GF-07 | MAYOR | Guia Fiscal | Errores de deduction discovery silenciosos — seccion queda vacia sin aviso | NUEVO |
| B-GF-08 | MENOR | Guia Fiscal | Acentos faltantes en textos del wizard | NUEVO |
| B-GF-09 | MENOR | Guia Fiscal | `useMemo` con dependencias incorrectas — anti-pattern React | NUEVO |
| B13 | ALTA | Mobile | Hamburger abre sidebar en lugar de nav — verificar fix commit 0ab0a9e | PENDIENTE |
| B14 | MEDIA | Landing | Stats incorrectas (138/47/7 en lugar de 428/64o128/21) | PENDIENTE |
| B-MOB-06 | MAJOR | Mobile | Tabla IGIC en /canarias overflow horizontal en 375px | PENDIENTE |
| B-S7-02 | MEDIA | Auth | Login owner fernando.prada@proton.me falla — password desconocido | PENDIENTE |

*B-GF-02 es critico solo si el objetivo es hacer el endpoint publico. Si es privado, es solo documentacion incorrecta.

---

## Analisis de la Guia Fiscal — Flujo Completo (basado en codigo)

### Paso 1: Datos personales
- Select CCAA con 21 opciones — correcto
- Campo edad — correcto
- Modo rapido vs completo — correcto
- Tributacion conjunta — solo en modo completo — correcto
- `canProceed` valida que haya CCAA — correcto

### Paso 2: Trabajo
- Toggle anual/mensual — correcto
- Si mensual: calcula bruto anual automaticamente — correcto
- Campo ingresos de actividad (autonomos) — expandible
- **Issue UX:** El usuario no sabe que la SS (~6.35%) se puede dejar en 0 — el help text lo indica pero puede ser confuso

### Paso 3: Ahorro e inversiones
- Intereses, dividendos, ganancias fondos — correcto
- Retenciones ahorro — correcto

### Paso 4: Inmuebles
- Ingresos alquiler, gastos, valor adquisicion — correcto
- Alquiler habitual pre-2015 — correcto
- Rentas imputadas segundas viviendas — correcto

### Paso 5: Familia
- Hijos con anos de nacimiento — correcto (generacion automatica de campos)
- Ascendientes — correcto
- Discapacidad — select con 3 opciones — correcto
- Madre trabajadora + guarderia — correcto

### Paso 6: Deducciones
- Planes de pensiones — correcto
- Hipoteca pre-2013 — correcto con campos expandibles
- Donativos — correcto
- **Discovery de deducciones territoriales** — llamada a `/api/irpf/deductions/discover` — depende de BD

### Paso 7: Resultado
- Tarjeta resultado verde (devolver) / roja (pagar)
- Desglose completo con lineas individuales
- Boton "Guardar en mi perfil" — guarda en fiscal profile
- Deducciones potenciales del discovery

### LiveEstimatorBar
- Desktop: sidebar sticky a 280px
- Mobile: barra sticky abajo (padding-bottom: 100px en el layout)
- Se actualiza con debounce 600ms — correcto

---

## Sugerencias UX

| # | Area | Sugerencia | Impacto |
|---|------|-----------|---------|
| S1 | Guia Fiscal | Anadir seccion hero visible con titulo "Calcula tu IRPF" antes del wizard | Alto |
| S2 | Guia Fiscal | Mostrar mensaje de error cuando deduction discovery falla | Alto |
| S3 | Guia Fiscal | Validar que ingresos > 0 antes de permitir avanzar al paso de Resultado | Medio |
| S4 | Guia Fiscal | Anadir tooltip en campo SS con calculo automatico ("Si lo dejas en 0, estimamos 6.35% de tu salario bruto") | Medio |
| S5 | Guia Fiscal | En el resultado, anadir boton "Ir al chat" para consultar con el asistente | Alto |
| S6 | Mobile | LiveEstimatorBar en mobile: mostrar solo el importe (sin tipo medio) para ahorrar espacio vertical | Bajo |

---

## Para PM Coordinator

### Bugs criticos — atencion inmediata

1. **B-GF-01** (CRITICA): El hero de la Guia Fiscal no se renderiza — la pagina no tiene titulo ni descripcion visible. Fix de 5 minutos: anadir `<div className="tax-guide__header">` con titulo y descripcion al principio del return.

2. **B-GF-03** (MAYOR): Verificar que el backend devuelve `cuota_liquida_total` (no `cuota_total`) — si hay mismatch, el desglose del resultado estara vacio.

### Bugs que pueden esperar al proximo sprint

- B-GF-04 (flash visual) — impacto bajo, solo estetico
- B-GF-05 (modo rapido con datos pre-rellenados) — comportamiento aceptable
- B-GF-06 (canProceed sin validacion de ingresos) — UX menor
- B-GF-08 (acentos) — menor, no afecta funcionalidad

### Sugerencias que mejorarian la conversion

- **S5** (boton "Ir al chat" desde resultado): Despues de ver el calculo IRPF, un CTA directo al chat con la consulta pre-rellenada aumentaria el engagement.
- **S1** (hero visible en guia fiscal): La pagina actual no tiene contexto. Un titulo visible mejoraria la comprension.

---

## Script de verificacion en produccion

Para ejecutar los tests E2E en produccion cuando Playwright MCP este disponible:

```bash
cd "C:\Users\Fernando Prada\OneDrive - SVAN TRADING SL\Escritorio\Personal\Proyectos\TaxIA"
npx playwright test tests/e2e/qa-session-completa-2026-03-08.spec.ts --workers=1 --reporter=list
```

El script cubre:
- T01-A/B: Landing desktop + mobile
- T02: Login + JWT
- T03-GUIA-A: Acceso a /guia-fiscal (detecta redirect)
- T03-GUIA-B: Wizard 7 pasos completo con Madrid + 35000€
- T03-GUIA-C: LiveEstimatorBar en tiempo real
- T03-GUIA-D: POST /api/irpf/estimate directo
- T04: Chat deducciones IRPF
- T05: Settings CCAA
- T06: /modelos-trimestrales
- T07: Navigation mobile hamburger
- T08-A/B/C: Paginas territoriales
- T09: Paginas legales
- T10: Cookie consent

Screenshots: tests/e2e/screenshots/sc-*.png

---

## Estado del sistema segun sesion anterior (8b)

- Backend SSE: RESUELTO — tiempos 15-25s, sin congelamiento
- Chat: FUNCIONAL — calidad de respuesta excelente
- Perfil fiscal: FUNCIONAL — persiste correctamente
- Modelos trimestrales: DESPLEGADO (pendiente verificacion visual)
- Guia Fiscal: DESPLEGADA pero con bugs B-GF-01 a B-GF-09
