# Bugfixes Marzo 2026

## [2026-03-13] Bugs 53-55: Groq model 404, guardrails false positive, demo router (Commit fdfd0c0)

### Bug 53: Groq model meta-llama/llama-guard-4-12b devuelve 404
**Causa raiz:** Groq elimino el modelo `meta-llama/llama-guard-4-12b` de su plataforma. Afectaba a 3 modulos: llama_guard.py (content moderation), sql_injection.py (S14), pii_detector.py (S7).
**Fix:** Cambiar `GROQ_MODEL` y `GROQ_MODEL_SAFETY` defaults a `openai/gpt-oss-safeguard-20b` en config.py. Actualizar .env local y .env.example.
**Accion usuario:** Cambiar GROQ_MODEL en Railway produccion. CUIDADO: no poner "m" extra al inicio del nombre del modelo.
**Archivos:** config.py, .env, .env.example, llama_guard.py (docstring), pii_detector.py (comment)

### Bug 54: Guardrails bloquea pregunta legitima "no declarar"
**Causa raiz:** `PROHIBITED_KEYWORDS` en guardrails.py contenia "no declarar" y "eludir" que son demasiado amplios. Un usuario preguntando "cuanto es el limite sin necesidad de declarar el IRPF" era bloqueado como evasion fiscal.
**Fix:** Eliminado "no declarar" y "eludir". Anadido "como no pagar impuestos" (intencion clara de evasion).
**Archivos:** guardrails.py

### Bug 55: demo.py atributos incorrectos en ModerationResult y PIIDetectionResult
**Causa raiz:** demo.py usaba `moderation.categories` (no existe, correcto: `blocked_categories`), `pii_result.pii_types` (correcto: `detected_types`), `pii_result.redacted_text` (correcto: `masked_text`). Bugs latentes que no crasheaban porque los try/except los capturaban, pero habrian fallado con el nuevo modelo funcional.
**Fix:** Corregir los 3 atributos. Tambien renombrado `request` → `body` en user_rights.py (change_password + update_fiscal_profile) como prevencion del patron slowapi.
**Archivos:** demo.py, user_rights.py

---

## [2026-03-13] Bugs 49-52: 4 bugs beta testers (Commit b148564)

### Bug 52: Password reset no envia email (Jose Antonio Alvarez)
**Causa raiz:** Dominio incorrecto `impuestify.es` en defaults de config.py y .env.example. El dominio verificado en Resend es `impuestify.com`. Resend rechazaba emails desde dominio no verificado.
**Fix:** 6 referencias `.es` → `.com` en config.py (RESEND_FROM_EMAIL, VAPID_CLAIMS_EMAIL, FRONTEND_URL), report_generator.py, CLAUDE.md, test_fiscal_deadlines.py, .env.example, e2e spec.
**Accion usuario:** Cambiar RESEND_FROM_EMAIL en Railway produccion a `noreply@impuestify.com`.
**Archivos:** config.py, report_generator.py, CLAUDE.md, test_fiscal_deadlines.py, .env.example, regression spec

### Bug 50: Workspaces loading infinito al agregar mas de uno (Juan Pablo Sanchez)
**Causa raiz:** 4 problemas encadenados:
1. `useApi.ts`: fetch() sin timeout — Promise nunca resuelve si servidor tarda
2. `WorkspacesPage.tsx`: dependency array incorrecto causa re-fetches multiples
3. `useWorkspaces.ts`: race condition al cambiar workspace mientras anterior carga
4. `workspaces.py`: crash en `created_at.isoformat()` si campo es NULL → 500
**Fix:**
- useApi.ts: AbortController + timeout 30s
- useWorkspaces.ts: filesRequestIdRef para descartar respuestas obsoletas
- workspaces.py: guard `(w.created_at or datetime.utcnow()).isoformat()`
**Archivos:** useApi.ts, useWorkspaces.ts, workspaces.py

### Bug 49: NotificationAgent respuestas excesivamente verbosas

**Detectado por:** Beta tester — certificado de rentas PDF producía respuesta que justificaba cada detalle obvio antes de la conclusión.

**Causa raíz:**
1. `SYSTEM_PROMPT` del NotificationAgent imponía 6 secciones obligatorias con headers markdown fijos (¿Qué es esto?, Plazos, Tu situación fiscal, Qué tienes que hacer, Enlaces útiles, Consejos) — el LLM las rellenaba todas aunque estuvieran vacías o fueran triviales.
2. `_build_analysis_prompt` terminaba con "Genera una explicación siguiendo EXACTAMENTE la estructura del SYSTEM_PROMPT" — forzaba al LLM a cumplir la plantilla completa.
3. `format_notification_friendly` en `notifications.py` envolvía el `summary` del LLM en OTRA capa con intro hardcodeada + pasos hardcodeados por tipo de notificación → duplicación total del contenido.

**Fix:**
- `backend/app/agents/notification_agent.py`:
  - `SYSTEM_PROMPT` reescrito con patrón answer-first (misma regla que TaxAgent): responde primero, explica solo lo no obvio, no rellenes secciones vacías.
  - Instrucción final de `_build_analysis_prompt` cambiada de "EXACTAMENTE la estructura" a "responde directamente, sé breve".
- `backend/app/routers/notifications.py`:
  - `format_notification_friendly` simplificada: el `summary` del LLM pasa directamente como cuerpo principal. Solo añade bloque de plazos calculados (datos estructurados server-side) y footer de 1 línea.

**Archivos modificados:**
- `backend/app/agents/notification_agent.py`
- `backend/app/routers/notifications.py`

**Tests:** 5/5 notification tests PASS. 1009 total sin regresiones.

### Bug 51: Comparativa conjunta vs individual solo muestra un resultado (Juan Pablo Sanchez)
**Causa raiz:** `tax_agent.py` linea ~443 solo procesaba `tool_calls[0]` — descartaba el resto. Cuando OpenAI proponia 2 tool calls (conjunta + individual), solo ejecutaba la primera. System prompt sin instrucciones de comparativa.
**Fix:**
- Loop sobre todos los tool_calls (no solo [0])
- Instruccion de comparativa anadida al system prompt: "Si pide comparativa → llama multiples veces, presenta tabla markdown"
**Archivos:** tax_agent.py

---

## [2026-03-12] Bug 48: Cataluña "No scale found" — falta "cataluna" en CCAA_NORMALIZATION

**Detectado por:** QA API test 5 territorios
**Síntomas:** POST /api/irpf/estimate con `comunidad_autonoma: "Cataluna"` devuelve `success: false, error: "No scale found for Cataluna 2024"`. Todos los campos del resultado a 0.

**Causa raíz:** `CCAA_NORMALIZATION` en `web_scraper_tool.py` tenía keys `"cataluña"` y `"catalunya"` pero NO `"cataluna"` (sin tilde en la ñ). El frontend envía `"Cataluna"` → `normalize_ccaa_name("Cataluna")` busca `"cataluna"` (lowercase) → no match → devuelve `"Cataluna"` sin cambio → BD tiene `jurisdiction = "Cataluña"` → SQL 0 resultados.

**Fix:** Añadir `"cataluna": "Cataluña"` al dict `CCAA_NORMALIZATION`.

**Archivo:** `backend/app/tools/web_scraper_tool.py` (línea 34)

**Lección:** Siempre incluir variantes sin tilde de TODAS las CCAA en el dict de normalización, ya que el frontend usa nombres sin acentos.

**Commit:** `1bf61ac`

---

## [2026-03-12] Bug 47: Deducciones autonómicas CCAA no aparecen en Resultado de Guía Fiscal

**Detectado por:** QA Playwright test Guía Fiscal
**Síntomas:** Paso 8 (Resultado) no mostraba sección "Deducciones autonómicas" ni restaba las deducciones CCAA de la cuota. Madrid alquiler 8.000 EUR + edad 37 debería dar MAD-ALQUILER-VIV = 1.237,20 EUR.

**Causa raíz (3 bugs):**

1. **Territory name mismatch** (`irpf_estimate.py`): `normalize_ccaa_name("Madrid")` → `"Comunidad de Madrid"` pero las deducciones en BD usan `territory = "Madrid"`. SQL `WHERE territory = 'Comunidad de Madrid'` → 0 resultados.
   - **Fix:** Usar `body.comunidad_autonoma` (nombre corto) para deduction lookups, mantener `ccaa` normalizado para escalas IRPF.

2. **Age-based answers never derived** (`deduction_service.py`): Requirement keys `menor_40_anos`, `menor_36_anos`, `menor_35_anos` nunca se derivaban de `edad_contribuyente`. `build_answers_from_profile()` no recibía edad.
   - **Fix:** Añadir `edad_contribuyente` al `profile_for_answers` dict + derivar `menor_35/36/40_anos` automáticamente en `build_answers_from_profile()`.

3. **Frontend `alquiler_pagado_anual` always 0** (`TaxGuidePage.tsx`): DynamicFiscalForm guarda el alquiler en `dynamicFormValues.importe_alquiler_anual`, pero el estimate enviaba `data.alquiler_pagado_anual` que era 0.
   - **Fix:** Fallback `data.alquiler_pagado_anual || dynamicFormValues.importe_alquiler_anual || 0`.

**Archivos modificados:**
- `backend/app/routers/irpf_estimate.py` — `ccaa_for_deductions` + `edad_contribuyente` en profile
- `backend/app/services/deduction_service.py` — derivación edad en `build_answers_from_profile()`
- `frontend/src/pages/TaxGuidePage.tsx` — fallback `importe_alquiler_anual`
- `frontend/src/hooks/useIrpfEstimator.ts` — interfaces `IrpfEstimateInput` y `IrpfEstimateResult` con campos CCAA

**Resultado verificado:** Madrid, 37 años, alquiler 8.000 EUR → MAD-ALQUILER-VIV: -1.237,20 EUR → "Hacienda te devuelve 128,19 EUR" (antes: "A pagar 1.109,01 EUR")

---

## [2026-03-11] slowapi crash 500 en /api/irpf/estimate y /deductions/discover + JWT 401 en SSE

**Reportado por:** Ramon Palomares (beta tester)
**Sintomas usuario:** (1) "Expecting value: line 1 column 1 (char 0)" al analizar nomina, (2) "HTTP error! status: 401" al preguntar sobre retenciones con hija

**Causa raiz (2 bugs):**
1. **slowapi requiere `request: Request` como nombre exacto del parametro**. Los endpoints usaban `req: Request` + `request: IRPFEstimateRequest` (body Pydantic). slowapi no encontraba `request` de tipo Request → crash `Exception: parameter 'request' must be an instance of starlette.requests.Request` → 500 Internal Server Error. El frontend recibia HTML de error y JSON.parse() fallaba con "Expecting value".
2. **useStreamingChat.ts usa fetch() directo (no Axios)** → no pasa por el interceptor de auto-refresh JWT de useApi.ts. Cuando el token de 30min expiraba, la llamada a `/api/ask/stream` recibia 401 y se mostraba al usuario sin intentar refresh.

**Fix backend:** Renombrar parametros en `irpf_estimate.py`:
- `req: Request` → `request: Request` (slowapi lo encuentra)
- `request: IRPFEstimateRequest` → `body: IRPFEstimateRequest` (evita conflicto de nombre)
- Aplicado a ambos endpoints: `estimate_irpf()` y `discover_deductions_endpoint()`

**Fix frontend:** Anadir auto-refresh JWT en `useStreamingChat.ts`:
- Si fetch() recibe 401 → intentar refresh con `/auth/refresh`
- Si refresh OK → reintentar el fetch con nuevo token
- Si refresh falla → limpiar tokens y redirigir a `/login?expired=true`

**Anti-patron documentado:** NUNCA usar `req: Request` cuando hay `@limiter.limit()` de slowapi. Siempre usar `request: Request` como primer parametro y nombrar el body Pydantic como `body` o `data`.

**Archivos modificados:**
- `backend/app/routers/irpf_estimate.py` (lineas 147-150, 347-350)
- `frontend/src/hooks/useStreamingChat.ts` (lineas 136-163)

**Tests:** 82 IRPF tests PASS, frontend build OK

---

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

---

## [2026-03-09] B-CHAT-01: Respuesta modelo 303 reemplazada por error generico

**Problema:** Al preguntar sobre modelo 303, el agente devolvia "hubo un problema al formatear la respuesta" en lugar de la respuesta real.

**Causa raiz:** `validate_output_format()` en guardrails.py detecta patrones JSON-like (`{"tool":`, `{"query":`, etc.) y reemplazaba TODA la respuesta con un mensaje de error. Las respuestas sobre modelos fiscales a menudo incluyen JSON-like content legitimate (parametros de tools, casillas, etc.).

**Solucion:** Cambiar el comportamiento: solo logear warning, NO reemplazar la respuesta. El guardrail de output format es informativo, no destructivo.

**Archivos modificados:**
- `backend/app/agents/tax_agent.py` (linea ~530)

**Regla:** Los guardrails de formato de output NUNCA deben destruir la respuesta entera. Logear warnings para monitorizacion, pero dejar que la respuesta llegue al usuario. Si hay JSON real expuesto, es mejor un falso positivo que perder la respuesta.

---

## [2026-03-09] B-GF-06: Wizard permite saltar al resultado sin datos

**Problema:** El usuario podia clickear directamente en el paso "Resultado" del progress bar sin haber rellenado CCAA ni ingresos. Mostraba "Completa los pasos anteriores".

**Causa raiz:** `canProceed` solo validaba steps 0 y 1. El progress bar permitia navegar libremente a cualquier step sin validacion.

**Solucion:** Anadir `canGoToStep(i)` que bloquea el paso Resultado si no hay CCAA + ingresos. Progresar bar buttons deshabilitados si no se puede ir a ese step.

**Archivos modificados:**
- `frontend/src/pages/TaxGuidePage.tsx`

---

## [2026-03-09] B-MOB-01: Modales apilados en mobile bloquean interfaz

**Problema:** En mobile, OnboardingModal y AITransparencyModal se mostraban simultaneamente, bloqueando toda la interfaz.

**Causa raiz:** Ambos modales se renderizan al mismo tiempo en Chat.tsx. En desktop no es tan grave (se pueden cerrar), pero en mobile ocupan toda la pantalla y se apilan.

**Solucion:** Modales secuenciales: AITransparencyModal solo se muestra despues de que OnboardingModal haya sido cerrado. State `onboardingDone` controla la secuencia. OnboardingModal acepta callback `onDismiss`.

**Archivos modificados:**
- `frontend/src/pages/Chat.tsx`
- `frontend/src/components/OnboardingModal.tsx`

---

## [2026-03-09] B-LOGOUT-01: Logout intermitente por window.confirm

**Problema:** El boton de logout no funcionaba de forma consistente. `window.confirm()` no se disparaba siempre.

**Causa raiz:** `window.confirm` en event handlers tiene timing issues, especialmente en tests automatizados y en ciertos navegadores mobile.

**Solucion:** Eliminar `window.confirm` — hacer logout directo. No necesita confirmacion ya que el historial se conserva.

**Archivos modificados:**
- `frontend/src/components/Header.tsx`

---

## [2026-03-09] CcaaTip foral detection rota (CCAA unaccented)

**Problema:** CcaaTip no detectaba territorios forales. El tip de "Territorio foral" no aparecia al seleccionar Araba/Bizkaia/Gipuzkoa.

**Causa raiz:** `ccaa.startsWith('País Vasco')` no matchea porque los CCAA_OPTIONS usan nombres sin acentos (Araba, Bizkaia, Gipuzkoa, no "País Vasco - Araba").

**Solucion:** Cambiar a `['Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra'].includes(ccaa)`.

**Archivos modificados:**
- `frontend/src/pages/TaxGuidePage.tsx`

## [2026-03-10] 4 bugs: tildes, dropdown dark, conversacion, perfil fiscal

### Bug 11: Faltas de ortografia (tildes) en perfil fiscal
**Problema:** Todas las ~50+ etiquetas de campos fiscales carecian de acentos.
**Causa raiz:** Labels escritos sin tildes en fiscal_fields.py desde la creacion.
**Solucion:** Corregir todos los labels con acentos correctos.
**Archivos:** `backend/app/routers/fiscal_fields.py`

### Bug 12: Dropdown blanco sobre blanco en dark theme
**Problema:** `<select>` del perfil fiscal con texto blanco sobre fondo blanco.
**Causa raiz:** `.dff-select` sin `color`/`background-color` explicitos.
**Solucion:** Anadir color/bg explicitos + `.dff-select option { background: #1e293b }`.
**Archivos:** `frontend/src/components/DynamicFiscalForm.css`

### Bug 13: Conversacion nueva en cada mensaje
**Problema:** Cada mensaje creaba conversacion nueva.
**Causa raiz:** Backend no enviaba conversation_id en evento done. Frontend usaba undefined.
**Solucion:** Backend envia `{"conversation_id":"xxx"}` en done. Frontend parsea y usa.
**Archivos:** `backend/app/utils/streaming.py`, `backend/app/routers/chat_stream.py`, `frontend/src/hooks/useStreamingChat.ts`

### Bug 14: AI dice que actualizo perfil pero no lo hizo
**Problema:** No existia tool para actualizar perfil fiscal desde el chat.
**Solucion:** Crear `update_fiscal_profile` tool. Integrado en TaxAgent + WorkspaceAgent.
**Archivos:** `backend/app/tools/fiscal_profile_tool.py` (nuevo), `backend/app/tools/__init__.py`, `backend/app/agents/tax_agent.py`, `backend/app/agents/workspace_agent.py`, `backend/app/utils/streaming.py`

---

## [2026-03-12] Auditoria CCAA deducciones: 13 errores corregidos

### Bug 15: Double-counting deducciones alquiler forales
**Problema:** Las deducciones de alquiler en los 4 territorios forales (Araba, Bizkaia, Gipuzkoa, Navarra) se contaban DOS VECES en `compute_ccaa_deduction_amounts`.
**Causa raiz:** `seed_deductions_forales_v2.py` tenia codigos `-VIVIENDA` (ARA-VIVIENDA, BIZ-VIVIENDA, etc.) que duplicaban los `-ALQUILER-VIV` de `seed_deductions_territorial.py`. Ambos matcheaban el patron `"VIVIENDA" in code.upper()` en el servicio.
**Solucion:** Eliminar los 4 registros `-VIVIENDA` de `forales_v2.py`. Eliminar los 4 registros `-DISCAPACIDAD` duplicados tambien. Anadir logica de cleanup para borrar registros legacy de produccion. Tightened pattern matching: eliminar `"VIVIENDA" in code.upper()` de la deteccion de alquiler.
**Archivos:** `backend/scripts/seed_deductions_forales_v2.py`, `backend/app/services/deduction_service.py`

### Bug 16: VAL-ALQUILER-VIV max_amount incorrecto
**Problema:** max_amount era 950 EUR (tier enhanced) en vez de 800 EUR (tier general).
**Datos correctos AEAT 2024:** 20%/800 general, 25%/950 con 1 condicion, 30%/1100 con 2+ condiciones.
**Archivos:** `backend/scripts/seed_deductions_territorial.py`

### Bug 17: ARA-DESC-HIJOS fixed_amount incorrecto
**Problema:** 734.80 EUR incluia el bonus rural (+10%) baked in. El importe base correcto es 668 EUR.
**Fuente:** AEAT + Diputacion Foral de Araba (Art. 79 NF 33/2013).
**Archivos:** `backend/scripts/seed_deductions_territorial.py`

### Bug 18: ARA-DISCAPACIDAD fixed_amount incorrecto
**Problema:** 888 EUR era el valor de Bizkaia, no de Araba. Araba tiene 932.40 EUR.
**Fuente:** Art. 82 NF 33/2013 Araba (actualizado NF 3/2025).
**Archivos:** `backend/scripts/seed_deductions_territorial.py`

### Bug 19: ARG-ARRENDAMIENTO-VIV deduccion inexistente
**Problema:** Aragon NO tiene deduccion general por alquiler de vivienda habitual. Solo existe una deduccion por dacion en pago (10%, max 4.800 EUR, Art. 110-8 DL 1/2005).
**Solucion:** Renombrar a `ARG-DACION-ALQUILER`, corregir condiciones y limites.
**Archivos:** `backend/scripts/seed_deductions_territorial_v2.py`

### Bug 20: AST-ARRENDAMIENTO-VIV valores desactualizados
**Problema:** 10%/455 + 15%/606 eran de un ano anterior. Correcto 2024: 10%/500 + 30%/1500.
**Fuente:** AEAT manual IRPF 2024 - Asturias.
**Archivos:** `backend/scripts/seed_deductions_territorial_v2.py`

### Bug 21: CANA-ALQUILER-VIV porcentaje e importes incorrectos
**Problema:** 20%/600 EUR era incorrecto. Correcto: 24%/740 EUR (760 para <40 o >=75). Limites renta incorrectos: 22.000/33.000 → 45.500/60.500.
**Fuente:** Art. 15 DLeg 1/2009 Canarias (mod. Ley 4/2018).
**Archivos:** `backend/scripts/seed_deductions_territorial_v2.py`

### Bugs 22-25: Descripciones incompletas/incorrectas
- **GAL-ALQUILER-VIV**: edad <=36 → <=35, faltaba tier 20%/600 para 2+ hijos menores, faltaba regla discapacidad duplica importes
- **CANT-ARRENDAMIENTO-VIV**: edad <35 → <36 o >=65, sin limite de renta, dos deducciones incompatibles
- **RIO-ARRENDAMIENTO-VIV**: ambos tiers requieren <36 (no es general), aclarar condicion municipio
- **deduction_service.py**: anadir VIV-RURAL al patron de inversion vivienda

**Tests:** 1008 passed, 0 failed
**Anti-patron:** NUNCA copiar importes de un territorio foral a otro (Bizkaia != Araba). NUNCA crear deducciones sin verificar contra AEAT/BOCA/BOE oficial. NUNCA usar codigos ambiguos (ARA- puede ser Araba o Aragon).

---

## [2026-03-12] Auditoria AEAT 8 CCAA restantes — 18 errores corregidos

**Origen:** Verificacion sistematica contra AEAT Manual IRPF 2024 de Madrid, Cataluna, Andalucia, CyL, CLM, Extremadura, Baleares, Murcia.

### Bug 26: AND-AYUDA-DOMESTICA — porcentaje 15% → 20%
- **Archivo:** `seed_deductions_territorial.py`
- **Causa:** Porcentaje inventado. Oficial: 20% de cotizaciones SS empleada hogar
- **Legal:** Arts. 19, 4 y DT 3a Ley 5/2021

### Bug 27: EXT-TRABAJO-DEPENDIENTE — importe 200€ → 75€, limites incorrectos
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Importe 200€ no existe. Oficial: 75€, rend. trabajo <=12.000€, otros <=300€
- **Legal:** Art. 2 DL 1/2018 (no Art. 7)

### Bug 28: EXT-VIV-JOVEN — porcentaje 8% → 3%/5%, edad <35 → <36
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** 8% no existe. Oficial: 3% general, 5% rural (<3.000 hab). Max base 9.040€
- **Legal:** Arts. 8, 12 bis y 13 DL 1/2018

### Bug 29: EXT-ARRENDAMIENTO-VIV — CRITICO: 10%/300€ → 30%/1.000€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Valores totalmente obsoletos. Reformado por ley reciente
- **Cambios:** 10→30%, 300→1.000€ (1.500 rural), BI 19.000→28.000€
- **Legal:** Arts. 9, 12 bis y 13 DL 1/2018

### Bug 30: EXT-CUIDADO-DISCAPACIDAD — referencia legal incorrecta
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Art. 8 → Arts. 5, 12 bis y 13. Faltaba variante 220€ dependencia
- **Legal:** Arts. 5, 12 bis y 13 DL 1/2018

### Bug 31: CYL-FAM-NUM — importe 246€ → 600€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** 246€ es valor totalmente desactualizado. Oficial: 600/1.500/2.500€
- **Legal:** Arts. 3 y 10 DL 1/2013

### Bug 32: CYL-NACIMIENTO — 2o hijo 1.262→1.475€, 3o 1.515→2.351€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Importes desactualizados. Anadido bonus rural y discapacidad
- **Legal:** Arts. 4.1-3 y 10 DL 1/2013

### Bug 33: CYL-CUIDADO-HIJOS — 312€ fijo → 30%/322€ + 100%/1.320€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** No es deduccion de importe fijo. Son 2 sub-deducciones (hogar + guarderia)
- **Legal:** Arts. 5.1 y 10 DL 1/2013

### Bug 34: CYL-VIV-JOVEN — 7,5% → 15%, faltaba max base 10.000€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Porcentaje incorrecto. Es 15% para vivienda rural, max base 10.000€/anio
- **Legal:** Arts. 7.1 y 10 DL 1/2013

### Bug 35: CYL-ALQUILER-VIV — 15% → 20%, faltaba edad <36 y bonus rural
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Porcentaje desactualizado. 20% standard, 25%/612€ rural
- **Legal:** Arts. 7.4, 7.5 y 10 DL 1/2013

### Bug 36: CLM-DISCAPACIDAD — umbral >=33% → >=65%
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** 300€ solo aplica a >=65%, no >=33% como decia la descripcion
- **Legal:** Arts. 1 y 13 Ley 8/2013

### Bug 37: CLM-ARRENDAMIENTO-VIV — limites renta 27.000→12.500€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Limites de renta MUY incorrectos (27.000→12.500 indiv, 36.000→25.000 conj)
- **Legal:** Arts. 9 y 13 Ley 8/2013

### Bug 38: CLM-GASTOS-EDUCATIVOS — estructura simplificada incorrectamente
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** No es simple 15%/300€. Es 100% libros + 15% otros, con tramos de renta
- **Legal:** Arts. 3 y 13 Ley 8/2013

### Bug 39: BAL-ARRENDAMIENTO-VIV — max 440→530€, limites renta incorrectos
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** 440€ es viejo. Oficial: 530€ (650€ tier mejorado 20%). BI 33.000/52.800€
- **Legal:** Art. 3 bis DL 1/2014

### Bug 40: MUR-VIV-JOVEN — 3%→5%, edad <35→<=40, max 300€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Todos los valores incorrectos. 5%/300€/<=40 anios/BI 40.000€
- **Legal:** Art. 1 DL 1/2010

### Bug 41: MUR-GUARDERIA — 15%/330€ → 20%/1.000€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Todos los valores incorrectos. BI 30.000/50.000€
- **Legal:** Art. 1.Tres DL 1/2010

### Bug 42: MUR-MEDIOAMBIENTE — CRITICO: 10%/300€ → 50%/7.000€
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Deduccion actualizada masivamente. 50%/37,5%/25% por tramos, max 7.000€
- **Legal:** Art. 1.Seis DL 1/2010

### Bug 43: MUR-ARRENDAMIENTO-VIV — BI 24.000→24.380€, edad <35→<=40
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Limite de renta ligeramente incorrecto, umbral de edad equivocado
- **Legal:** Art. 1.Trece DL 1/2010

### Bug 44: ARG-DACION-PAGO duplicado de ARG-DACION-ALQUILER
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Misma deduccion con 2 codigos distintos (Art. 110-8 y Art. 110-10). Eliminado duplicado.

**Archivos modificados:** `seed_deductions_territorial.py`, `seed_deductions_territorial_v2.py`
**Tests:** 67 passed, 0 failed (test_deductions + test_irpf_simulator)
### Bug 45: BAL-IDIOMAS — max 100→110€, limites renta incorrectos
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Max 100€ → 110€ por hijo. BI 25.000→33.000 / 45.000→52.800€. Descripcion: es extraescolar de idiomas para hijos, no certificacion B2 adultos.

### Bug 46: MUR-DONATIVOS — porcentaje 30% → 50%
- **Archivo:** `seed_deductions_territorial_v2.py`
- **Causa:** Actualizado por Ley 4/2022 de Mecenazgo de Murcia. 50% donaciones puras dinerarias (no 30%).
- **Legal:** Art. 1.Siete DL 1/2010 (mod. Ley 4/2022)

**Total bugs auditoria CCAA:** 21 corregidos (Bugs 26-46)
**Tests:** 67 passed, 0 failed
**Anti-patron:** NUNCA inventar valores de deducciones sin verificar contra la web oficial de AEAT (sede.agenciatributaria.gob.es). Las CCAA actualizan sus deducciones frecuentemente — verificar siempre contra datos del ejercicio fiscal mas reciente.

---

## [2026-03-17] Bugs 53-58: Admin UI, Calendar, CTA alineacion (Sesion 12 final)

### Bug 53: Admin Feedback/Contact pages crash — result?.items undefined
**Problema:** AdminFeedbackPage y AdminContactPage mostraban error al cargar. Consola: `Cannot read property 'items' of undefined`.
**Causa raiz:** Componentes importaban CSS de Chat.css (compartido) pero ese CSS tenia clase `.message-text` con `display: flex` que no aplica a tablas. Faltaba CSS local para tablas feedback/contacts.
**Fix:** Crear `AdminFeedbackPage.css` + `AdminContactPage.css` con estilos especificos para tablas, charts, export buttons.
**Archivos:** `frontend/src/pages/AdminFeedbackPage.tsx`, `AdminContactPage.tsx`, nuevos CSS files.

### Bug 54: Subscribe page mobile overflow 113px
**Problema:** En mobile, 3 plan cards desbordaban 113px a la derecha. Scrollbar horizontal no deseable.
**Causa raiz:** Cards tenian `width: 300px` fijo + gap 24px. Con viewport <384px, 3x300 + 2x24 = 948px > 320px viewport.
**Fix:** Media query mobile: `width: 100%` + responsive grid `grid-template-columns: 1fr` (stack vertical). Gap reduce a 16px en mobile.
**Archivos:** `frontend/src/pages/SubscribePage.tsx` o SubscribePage.css.

### Bug 55: Fecha Renta "2 abril" → "8 abril 2026"
**Problema:** Calendario fiscal y email reminders anunciaban "2 de abril" como deadline Renta 2026.
**Causa raiz:** Fecha copiada incorrectamente de 2025. Oficial AEAT 2026: **8 de abril**.
**Fix:** Actualizar fecha en:
- `backend/scripts/seed_fiscal_calendar_2026.py` — RENTA: `deadline_date: "2026-04-08"`
- `frontend/src/hooks/useIrpfEstimator.ts` (si tiene hardcoded)
- `test_fiscal_deadlines.py` — assertion fecha
**Archivos:** seed script, tests.

### Bug 56: Calendar solo muestra 6 meses, deberia mostrar 12
**Problema:** CalendarPage cargaba pero solo mostraba enero-junio. Usuario no veía plazos de julio-diciembre.
**Causa raiz:** Fetch `GET /api/fiscal-deadlines?months=6` hardcodeado a 6 en lugar de 12. Variable `CALENDAR_LOOKBACK_MONTHS` en componente mal configurada.
**Fix:** Cambiar parametro a `months=12` o `months=365` (dias). Backend devuelve fechas 2026 completo. Test: verificar que todas 58 fechas se renderizan.
**Archivos:** `frontend/src/pages/CalendarPage.tsx`, `useIrpfEstimator.ts`.

### Bug 57: Calendar applies_to — asalariado no estaba en mapa, Patrimonio/347 no eran 'todos'
**Problema:** CalendarPage mostraba plazos pero indicador `applies_to` (se aplica a Autonomo/Particular/Ambos) no tenia logica para "Asalariado". Patrimonio/347 se mostraba como "solo Autonomo" cuando deberia ser "Todos".
**Causa raiz:** `applies_to` enum solo tenia "autonomo", "particular". Faltaba "asalariado" (empleado). Modelo 347 se seeded como autonomo pero aplica a todos.
**Fix:**
- Backend: actualizar enum `DeadlineAppliesTo` a incluir "asalariado" + "todos"
- Seed: Modelo 347 → `applies_to: "todos"`, Modelo 303 → `applies_to: "autonomo"`, Renta → `applies_to: "todos"`
- Frontend: renderizar icono/label para cada applies_to
**Archivos:** `backend/app/database/turso_client.py` (schema), seed script, CalendarPage.tsx.

### Bug 58: CTA creadores apuntaba a /creadores-de-contenido en vez de /subscribe
**Problema:** HomeLanding "Crear tu perfil de creador" boton redirigía a `/creadores-de-contenido` (landing educativa) en lugar de `/subscribe` (suscripcion). Usuario nunca podía contratarse.
**Causa raiz:** HomeLanding.tsx boton tenia hardcodeado `href="/creadores-de-contenido"` en lugar de condicional: si usuario `logueado && !subscribed → /subscribe`, else `/creadores-de-contenido`.
**Fix:** Verificar estado user/subscription, redirigir a `/subscribe` si necesita suscripcion. Post-suscripcion, redirigir a `/crear-perfil-creador`.
**Archivos:** `frontend/src/components/HomeLanding.tsx`.

---

---

## [2026-03-17] Bugs 59-62 + Document Integrity Scanner Capa 13 (Sesion 13)

### Bug 59: Calendario fiscal — deadlines solo en mes end_date, no en rango start→end
**Problema:** Deadlines multimes (ej: Modelo 303, desde 1 mayo hasta 20 junio) solo aparecian en el mes de end_date (junio). Mayo era vacio.
**Causa raiz:** FiscalCalendar.tsx renderizaba deadlines solo si `deadline.month == currentMonth`, sin considerar deadlines que abarcan varios meses.
**Fix:** Reemplazar comparacion de meses por overlap check: `(start <= monthEnd && end >= monthStart)`. Permite detectar deadlines que comienzan antes o terminan despues del mes actual.
**Archivos:** `frontend/src/components/FiscalCalendar.tsx`
**Commit:** `19935d4`

### Bug 60: Calendario fiscal — meses pasados vacios (vencidos filtrados)
**Problema:** Deadlines vencidos (meses previos, status "past") no se mostraban. Usuario no veía historial de plazos ya pasados.
**Causa raiz:** `frontend/src/hooks/useIrpfEstimator.ts` filtraba deadlines con `if (deadline.urgency === 'past') continue`, eliminandolos de la lista renderizada.
**Fix:** Eliminar filtro. Renderizar deadlines "past" con estilo CSS atenuado (`.fc-card--past { opacity: 0.5; color: #888; }`).
**Archivos:** `frontend/src/hooks/useIrpfEstimator.ts`, `frontend/src/pages/CalendarPage.css`
**Commit:** `19935d4`

### Bug 61: Push notifications — "Registration failed - push service error"
**Problema:** Usuarios recibían error "Registration failed" al habilitar push notifications. El navegador rechazaba el registro.
**Causa raiz:** 2 problemas:
1. VAPID keys regeneradas in-session no formaban par P-256 válido. El backend generaba public/private keys pero el par no era matemáticamente válido (falló validación cryptography SECP256R1).
2. Stale subscriptions en BD: usuarios con subscriptions viejas no válidas bloqueaban nuevas. El backend intentaba reutilizar claves viejas.
**Fix:**
- `backend/app/utils/push_notifications.py`: Regenerar VAPID keys usando `cryptography.hazmat.primitives.asymmetric.ec.generate_private_key(SECP256R1())`. Verificar que `private_key.public_key()` produce par válido antes de usar.
- `backend/scripts/`: Crear script de cleanup que elimine subscriptions inválidas (webhook 410 Gone) + reintente con retry exponencial (1s, 2s, 4s).
- Frontend: PushPermissionBanner con state para mostrar "Retry en 3s..." durante reintentos.
**Resultado:** Funciona en navegador limpio sin extensiones (verificado con Playwright headless). Bloqueado cuando usuario tiene MetaMask/adblocker que interceptan service worker.
**Archivos:** `backend/app/utils/push_notifications.py`, `frontend/src/components/PushPermissionBanner.tsx`
**Commits:** `3048d9f`, `6f45b3d`, `8e329ce`

### Bug 62: `/creadores-de-contenido` redirigía a `/` (ruta no registrada)
**Problema:** Clickear el botón CTA "Crear perfil creador" llevaba a `/creadores-de-contenido` pero la ruta no estaba registrada en App.tsx. El router fallaba con 404 → redirect a Home → `/`.
**Causa raiz:** `CreatorsPage.tsx` importada con `lazy(() => import(...))` pero nunca añadida al switch de `<Routes>`. Componente existía pero ruta faltaba.
**Fix:** Añadir `<Route path="/creadores-de-contenido" element={<Suspense><CreatorsPage /></Suspense>} />` a App.tsx.
**Archivos:** `frontend/src/App.tsx`
**Commit:** `dadf58e`

---

## Document Integrity Scanner (Capa 13 de Seguridad, Sesion 13)

**Contexto:** Inspirado por Microsoft Defender "AI Recommendation Poisoning" (Feb 2026) y SignalOrbit Trust. Detecta intentos de jailbreak/prompt injection en documentos RAG.

**Caracteristicas:**
- **40 patrones bilingües ES/EN**: adversarial instructions, inversion jailbreak, data exfiltration, privilege escalation, instruction override, knowledge distillation, etc.
- **10 categorías de riesgo**: JAILBREAK_ATTEMPT, PRIVILEGE_ESCALATION, INSTRUCTION_OVERRIDE, DATA_EXFILTRATION, KNOWLEDGE_DISTILLATION, ADVERSARIAL_INPUT, LOGIC_INVERSION, ROLEPLAY_ABUSE, RESOURCE_EXHAUSTION, MODEL_POISONING
- **Integración en 3 puntos:**
  1. **User uploads** (workspaces): Validación en `upload_file` endpoint. Niveles: PASS (sin riesgo), WARN (riesgo bajo, permite con badge), SANITIZE (riesgo medio, limpia patrones), BLOCK (riesgo alto, rechaza)
  2. **Crawler** (doc_crawler): Validación post-descarga. Si HIGH/MEDIUM → quarantine en `docs/_quarantine/` con log
  3. **RAG** (embeddings): Scoring trust en cada documento (0-100). Documentos BLOCK nunca se indexan. WARN/SANITIZE se marcan con `integrity_findings` JSON
- **UI**: IntegrityBadge en workspaces mostrando score e icono (🟢 100-75, 🟡 75-50, 🔴 <50)
- **BD**: Nuevas columnas en `workspace_files` y `documents`: `integrity_score (int)`, `integrity_findings (JSON)`
- **Tests:** 55 tests nuevos cobriendo todos los patrones y niveles
- **Commits:** `1fd2835` (implementation), `436d009` (tests + UI)

---

**Total bugs marzo 2026:** 62 documentados (Bugs 1-62)
**Tests sesion 13:** 1138 backend PASS (55 nuevos Document Integrity Scanner), frontend build OK
**Capas seguridad:** 13 (nueva: Document Integrity Scanner)
**Archivos actualizados sesion 13:** ROADMAP.md, MEMORY.md, bugfixes-2026-03.md, agent-comms.md
**Siguiente:** Sesion 14 — validar plan Stripe al cambiar roles, Turnstile bypass para QA
