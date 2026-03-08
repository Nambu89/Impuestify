# Bugfixes Marzo 2026

## [2026-03-05] Renderizado markdown en chat

**Problema:** Las respuestas del agente con markdown (negritas, tablas, listas, encabezados) no se renderizaban correctamente. El texto se mostraba como raw markdown.

**Causa raiz (3 problemas):**
1. `white-space: pre-wrap` en `.message-text` (Chat.css:139) — preservaba saltos de linea raw, conflictuando con los `<p>`, `<ul>`, `<table>` que genera ReactMarkdown. Causaba doble espaciado y tablas rotas.
2. Sin plugin `remark-gfm` — react-markdown v10 NO incluye GFM por defecto. Sin el, tablas (`| col |`), tachado (`~~text~~`), task lists no se procesan.
3. Sin estilos CSS para tablas, bloques de codigo (`pre`), blockquotes, hr.

**Solucion:**
- `npm install remark-gfm`
- `FormattedMessage.tsx`: import remarkGfm, anadir `remarkPlugins={[remarkGfm]}` a los 3 `<ReactMarkdown>`
- `Chat.tsx`: import remarkGfm, anadir plugin al `<ReactMarkdown>` de mensajes user
- `Chat.css`: eliminar `white-space: pre-wrap`, anadir estilos para: table/th/td (bordes, hover), pre/code blocks, blockquote (borde azul), hr, li spacing

**Archivos modificados:**
- `frontend/src/components/FormattedMessage.tsx`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/pages/Chat.css`
- `frontend/package.json` (nueva dep: remark-gfm)

**Regla para prevenir recurrencia:** Siempre usar `remarkPlugins={[remarkGfm]}` en cualquier nuevo `<ReactMarkdown>`. Nunca usar `white-space: pre-wrap` en contenedores de HTML renderizado por ReactMarkdown.

---

## [2026-03-06] cuota_liquida_total key error en irpf_estimate

**Problema:** El endpoint `/api/irpf/estimate` devolvía KeyError al intentar leer el resultado del simulador. El frontend recibía 500 en lugar de la estimacion IRPF.

**Causa raiz:** `irpf_estimate.py` usaba la clave `cuota_liquida_total` para leer la cuota del resultado de `irpf_simulator.py`, pero el simulador devuelve la cuota bajo una clave diferente. Desalineamiento entre el nombre de clave producido por el simulador y el nombre esperado por el router.

**Solucion:** Corregir la clave en `irpf_estimate.py` para que coincida con la clave real que devuelve `irpf_simulator.py`. Verificar siempre las claves del dict de resultado del simulador antes de referenciarlas en routers/tools.

**Archivos modificados:**
- `backend/app/routers/irpf_estimate.py`

**Regla para prevenir recurrencia:** Al consumir el resultado de `irpf_simulator.py` en cualquier router o tool, inspeccionar el dict de retorno con un `print` o test antes de asumir nombres de clave. El simulador es la fuente de verdad — nunca asumir nombres por convención.

---

## [2026-03-06] Implementacion Simulador IRPF Fase 1+2

**No es un bug sino una feature completa.** Documentado aqui para referencia futura.

### Fase 1 (deducciones cuota):
- Planes pensiones: reduccion BI general, min(propio + empresa, 8500), max 30% rend. trabajo neto
- Hipoteca pre-2013: 15% de (capital + intereses), max 9.040 EUR, split 50/50 estatal/autonomico
- Maternidad: 1.200 EUR/hijo <3 anos (madre en SS) + 1.000 guarderia. REEMBOLSABLE
- Familia numerosa: 1.200 general, 2.400 especial. REEMBOLSABLE
- Donativos: 80% primeros 250 EUR + 40/45% resto. NO reembolsable (max reduce cuota a 0)
- Retenciones completas: trabajo + alquiler + ahorro

### Fase 2:
- Tributacion conjunta: reduce BI general en 3.400 (matrimonio) o 2.150 (monoparental)
- Alquiler habitual pre-2015: 10.05% de alquiler pagado, con limite renta (24.107 EUR taper)
- Rentas imputadas: valor_catastral * (1.1% si revisado post-1994, 2% si no)

### Clave tecnica:
- Deduciones reembolsables (maternidad, familia numerosa) pueden hacer cuota_total negativa → devolucion
- Deducciones no reembolsables (donativos) no pueden reducir cuota por debajo de 0
- El endpoint devuelve `cuota_total` (no `cuota_liquida_total`)

---

## [2026-03-07] Race condition useSubscription → redirect loop infinito

**Problema:** Navegar a `/guia-fiscal` causaba redirect loop infinito: guia-fiscal → subscribe → guia-fiscal... con errores ERR_ABORTED en network. El usuario no podia acceder a la Guia Fiscal ni a ninguna ruta protegida con `requireSubscription`.

**Causa raiz:** En `useSubscription.ts`, la funcion `fetchStatus` hacia early return cuando `isAuthenticated=false` pero ya habia ejecutado `setLoading(false)` en el bloque `finally`. Cuando auth completaba (isAuthenticated=true→false→true), ProtectedRoute veia `subLoading=false` + `hasAccess=false` (data aun null) y redirigía a /subscribe.

**Solucion:**
- Eliminar `setLoading(false)` del early return (no en finally, sino evitar que finally ejecute)
- Mover `setLoading(true)` al inicio del try block real
- Anadir handling de abort errors para evitar errores fantasma en navegacion

**Archivos modificados:**
- `frontend/src/hooks/useSubscription.ts`

**Regla para prevenir recurrencia:** En hooks que dependen de otro estado async (ej: isAuthenticated), NUNCA setear loading=false hasta que la llamada real se haya intentado. El early return debe dejar loading=true para que ProtectedRoute siga mostrando "Cargando..." hasta tener datos reales.

---

## [2026-03-07] CORS bloqueaba API calls desde localhost:3000

**Problema:** Login y todas las API calls fallaban con CORS error cuando frontend corria en puerto 3000 (configurado en vite.config.ts).

**Causa raiz:** `frontend/.env.local` define `VITE_API_URL=http://localhost:8000`, haciendo llamadas directas al backend (sin pasar por proxy Vite). El puerto 3000 del frontend no estaba en ALLOWED_ORIGINS del `.env` raiz.

**Solucion:** Anadir `http://localhost:3000` a ALLOWED_ORIGINS en `.env`.

**Archivos modificados:**
- `.env` (raiz)

**Regla para prevenir recurrencia:** Al cambiar el puerto del frontend en vite.config.ts, SIEMPRE anadir el nuevo origen a ALLOWED_ORIGINS. Si se usa `.env.local` con VITE_API_URL directo, el frontend hace CORS requests y necesita estar en la lista.

---

## [2026-03-07] Deteccion foral rota en TaxGuidePage (tildes)

**Problema:** CcaaTip no detectaba territorios forales correctamente. Los tips especificos para Pais Vasco no aparecian.

**Causa raiz:** `ccaa.startsWith('Pais Vasco')` no matcheaba porque en sesion anterior se cambiaron los CCAA_OPTIONS a usar tildes (`'País Vasco - Araba'`) pero no se actualizo esta comparacion.

**Solucion:** Cambiar a `ccaa.startsWith('País Vasco')` con tilde.

**Archivos modificados:**
- `frontend/src/pages/TaxGuidePage.tsx` (linea 70)

**Regla para prevenir recurrencia:** Al cambiar valores en arrays de opciones (CCAA_OPTIONS, etc.), buscar TODAS las referencias a esos valores en el mismo archivo y archivos relacionados. Usar grep para encontrar todas las ocurrencias.
