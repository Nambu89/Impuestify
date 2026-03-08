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

---

## [2026-03-08] B-LAND-01: Landing sections invisible (negro sobre negro)

**Problema:** Secciones de la landing (features, pricing, comparison, CTA) eran invisibles. Solo se veian hero + stats + footer. Reportado como negro sobre negro.

**Causa raiz:** `FadeContent.tsx` (componente IntersectionObserver) inicializa todos los elementos con `opacity: 0`. Los elementos below-the-fold solo se hacen visibles cuando el usuario scrollea y el IntersectionObserver los detecta. Playwright y algunos navegadores/crawlers no scrollean automaticamente, asi que las secciones permanecian invisibles.

**Solucion:** Anadir check en `useEffect` de FadeContent: si el elemento ya esta en el viewport al montar (`getBoundingClientRect`), setear `isVisible=true` inmediatamente sin esperar al IntersectionObserver.

**Archivos modificados:**
- `frontend/src/components/reactbits/FadeContent.tsx`

**Regla:** Componentes con animaciones scroll-triggered DEBEN tener fallback para elementos ya visibles en el viewport al montar. Nunca asumir que el usuario siempre scrollea.

---

## [2026-03-08] B-GUARD-01: Guardrail bloquea info educativa sobre modelos fiscales

**Problema:** Preguntar "¿Que es el modelo 303?" como particular era bloqueado con "Estas solicitando informacion sobre autonomos". El guardrail trataba CUALQUIER mencion de "modelo 303", "modelo 130" etc. como contenido de autonomos.

**Causa raiz:** `content_restriction.py` tenia keywords demasiado amplias ("modelo 303", "modelo 130", "modelo 131", "modelo 390") que bloqueaban incluso preguntas educativas generales. Tambien bloqueaba "ipsi" que aplica a TODOS los residentes de Ceuta/Melilla, no solo autonomos.

**Solucion:** Cambiar keywords de modelos fiscales a ser action-specific: "presentar modelo 303", "rellenar modelo 303", "calcular modelo 303", "mi modelo 303" (indican uso activo como autonomo). Preguntas generales ("que es el modelo 303") ya no se bloquean. Eliminados keywords IPSI completamente.

**Archivos modificados:**
- `backend/app/security/content_restriction.py`
- `backend/tests/test_ceuta_melilla.py` (tests IPSI actualizados)
- `backend/tests/test_subscription.py` (tests modelo 303/130 actualizados)

**Regla:** Content restriction keywords deben ser ACCION-ESPECIFICAS, no genricas. "modelo 303" es educativo; "rellenar modelo 303" indica actividad de autonomo. Misma logica para IPSI: es un impuesto territorial, no exclusivo de autonomos.

---

## [2026-03-08] B-TOOL-01: simulate_irpf_tool crash — missing argument

**Problema:** Error `simulate_irpf_tool() missing 1 required positional argument: 'ingresos_trabajo'` expuesto al usuario cuando el LLM llamaba al tool sin pasar ingresos_trabajo.

**Causa raiz:** `ingresos_trabajo` era parametro required tanto en el schema JSON como en la firma Python. Cuando el LLM intentaba simular sin datos de ingresos (ej: solo queria lookup de casillas), el tool crasheaba.

**Solucion:** Hacer `ingresos_trabajo` opcional: default=0 en firma Python y eliminado de `required` en schema JSON. El simulador funciona correctamente con ingresos_trabajo=0.

**Archivos modificados:**
- `backend/app/tools/irpf_simulator_tool.py` (required + default)
- `backend/tests/test_irpf_simulator.py` (assertion required list)

**Regla:** Tools de function calling deben tener la minima cantidad de parametros required. Si un parametro puede defaultear a 0 sin romper la logica, hacerlo opcional. El LLM no siempre envia todos los parametros.

---

## [2026-03-08] B-TOOL-02: RETA calculator sin datos 2026

**Problema:** Tool calculate_autonomous_quota no encontraba datos para ano 2026 (default del tool era 2025, y no habia datos 2026 en BD).

**Causa raiz:** Solo se habian seeded tramos RETA para 2025. El default year del tool era 2025 pero estamos en 2026.

**Solucion:**
1. Crear `scripts/seed_autonomous_quotas_2026.py` con 15 tramos x 3 regiones (general, ceuta, melilla) = 45 registros
2. Ejecutar seed contra Turso produccion
3. Actualizar default year del tool de 2025 a 2026

**Archivos modificados:**
- `backend/scripts/seed_autonomous_quotas_2026.py` (nuevo)
- `backend/app/tools/autonomous_quota_tool.py` (default year 2026)
