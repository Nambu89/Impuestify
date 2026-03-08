# Agent Communication Log - TaxIA
# =================================
# Canal de comunicacion entre agentes.
# Cada agente debe leerlo al inicio y escribir al terminar una tarea.
#
# Formato:
# [TIMESTAMP] [AGENT] [STATUS] - Mensaje
# STATUS: 🟢 DONE | 🟡 IN_PROGRESS | 🔴 BLOCKED | 📢 NEEDS_REVIEW

## [2026-03-08] PM — DONE — Integración documentos AEAT (casillas + parsers)

### Tool lookup_casilla + parsers XSD/XLS/VeriFactu

**Archivos creados:**
- `backend/app/tools/casilla_lookup_tool.py` — Tool busca casillas IRPF por numero/descripcion
- `backend/scripts/seed_casillas.py` — Parser .properties → tabla irpf_casillas (2064 casillas)
- `backend/scripts/parse_aeat_docs.py` — Parser XSD/XLS/VeriFactu → JSON + RAG txt
- `backend/tests/test_casilla_lookup.py` — 44 tests (44/44 PASS)

**Archivos generados:**
- `data/reference/renta_2024_schema.json` — 6769 elementos del XSD Renta2024
- `data/reference/modelo_130_fields.json` — 51 campos diseño registro M130
- `data/reference/modelo_131_fields.json` — 195 campos diseño registro M131
- `docs/aeat/VeriFactu/*_reference.txt` — 5 ficheros RAG-ready (726 líneas)

**Archivos modificados:**
- `backend/app/tools/__init__.py` — Registrado lookup_casilla
- `backend/app/database/turso_client.py` — Tabla irpf_casillas en schema

**Commit:** 3cc3aa0

---

## [2026-03-08] PM — DONE — UI adaptativa por territorio (labels forales)

- Gipuzkoa: "Modelo 300" en vez de "303"
- Navarra: "Modelo F-69" en vez de "303"
- Territorios forales: subtitulo "Hacienda Foral de X"
- Modelo 130: indica territorio foral en titulo
- Commit: f3d6ca7

---

## [2026-03-08] PM — DONE — Calculadora IPSI (Ceuta/Melilla)

### Implementacion completa: calculadora + tool + REST + frontend

**Archivos creados:**
- `backend/app/utils/calculators/modelo_ipsi.py` — Calculadora IPSI 6 tipos (0.5%-10%)
- `backend/app/tools/modelo_ipsi_tool.py` — Tool para chat (function calling)
- `backend/tests/test_modelo_ipsi.py` — 34 tests (34/34 PASS)

**Archivos modificados:**
- `backend/app/routers/declarations.py` — POST /api/declarations/ipsi/calculate
- `backend/app/tools/__init__.py` — MODELO_IPSI_TOOL registrada
- `frontend/src/hooks/useDeclarations.ts` — CalculateIpsiInput + ModeloType 'ipsi'
- `frontend/src/pages/DeclarationsPage.tsx` — Tab IPSI condicional + FormIpsi + ResultCard

**Frontend inteligente por territorio:**
- Ceuta/Melilla → IPSI + 130 (oculta 303/420)
- Canarias → 420 + 130 (oculta 303)
- Resto → 303 + 130

**Tests:** 600 passed (34 nuevos IPSI), 6 failed pre-existentes (no relacionados)

---

## [2026-03-08] QA — DONE — Sesion 8b: Validacion fix SSE + perfil Melilla — 5/5 PASS

### Resultado: TODOS LOS TESTS PASS — B-S7-01 RESUELTO

| Paso | Descripcion | Estado | Tiempo SSE |
|------|-------------|--------|------------|
| PASO 0 | Cambiar CCAA a Melilla en Settings | PASS | 18s |
| PASO 1 | IRPF 35.000€ con perfil Melilla | PASS | 20s (vs 120s antes) |
| PASO 2 | Deducciones Melilla (discover_deductions) | PASS | 25s (vs CONGELADO antes) |
| PASO 3 | IPSI vs IVA en Melilla | PASS | 20s |
| PASO 4 | ISD donacion 50.000€ en Melilla | PASS | 15s |
| PASO 5 | Restaurar CCAA a Madrid | PASS | 12s |

### Hallazgos principales
- **B-S7-01 CONFIRMADO RESUELTO** — fix commits e61633d + ee2364f funcionan en produccion
- Tiempos de respuesta SSE: 15-25s (antes: 120-130s o TIMEOUT). Mejora del 80-100%
- Perfil Melilla funciona: deduccion 60% Art. 68.4 LIRPF, IPSI, normativa ISD estatal
- Calidad de respuesta excelente: cifras concretas, formato tabla, sin preguntas innecesarias
- Issue menor QC-1: perfil fiscal del usuario test tiene "donacion pendiente 35.000€" incorrecto

### Reporte completo: `plans/qa-report-2026-03-08-melilla.md`
### Screenshots: `tests/e2e/screenshots/s8b-*.png` (30 capturas)

---

## [2026-03-08] PM — DONE — Mejora calidad respuesta + Fix SSE stream freeze

### Calidad de respuesta (commit ee2364f)
- System prompt reescrito: 414 → 42 lineas (-89%)
- Patron "Responde primero, pregunta despues": usa perfil fiscal directamente
- Tool results protegidos: instruccion append fuerza cifras en tabla markdown
- RAG territorial: territory_filter con CCAA del usuario
- Tono experto directo (no chatty)

### Fix SSE stream freeze B-S7-01 (commit e61633d)
- **Causa raiz**: `_stream_openai_response` no tenia timeout en consumo del stream. `async for chunk in stream` colgaba para siempre si OpenAI dejaba de enviar tokens (openai-python #2725, #1134, #769)
- **Fix 1**: Per-chunk timeout 30s con `asyncio.wait_for(anext(stream), timeout=30)`
- **Fix 2**: Smart fallback — si stream content < 50% de formatted_response, usa tool result
- **Tests**: 48/48 PASS

---

## [2026-03-08] QA — DONE — Sesion 7: Chat deducciones fiscales (test.particular@impuestify.es)

### Bug critico B-S7-01: Respuesta del chat se congela tras texto introductorio
- **Consulta:** "Que deducciones fiscales puedo aplicar en mi declaracion?"
- **Sintoma:** La IA responde con 384 chars de intro ("Voy a calcular... Ahora calculo el IRPF base.") y el stream SSE se congela permanentemente
- **La tool discover_deductions SI se ejecuto** (timeline confirma "Deducciones encontradas")
- **El problema ocurre en la fase de redaccion** — el agente no puede convertir el resultado de la tool en respuesta final
- **Tiempo de congelacion:** Desde ~20s hasta timeout 153s — sin cambios
- **Sin error visible al usuario** — el input queda habilitado como si hubiera terminado
- **Reporte completo:** `plans/qa-report-2026-03-08.md`
- **Screenshots:** `tests/e2e/screenshots/session7-07-*.png`

### Confirmacion de otros hallazgos
- **Salario:** La IA usa 35.000€ (del perfil) — NO 37.500€. Perfil leido correctamente
- **CCAA:** Usa "Comunidad de Madrid" — correcto
- **Texto tecnico:** NO se filtra ningun texto interno — OK
- **Fuentes:** Sin "(pag. 0)" — OK
- **Timeline thinking:** Funciona perfectamente — UX buena en la fase de procesamiento
- **Login owner fernando.prada@proton.me:** FALLA con REDACTED_PASSWORD — password incorrecto o problema de cuenta

### Accion requerida (backend)
1. URGENTE: Investigar por que el stream SSE se congela cuando el agente intenta redactar tras tool call
2. Posible causa: timeout Railway + el agente envia texto en chunks pero el segundo LLM call (post-tool) falla silenciosamente
3. Verificar logs Railway para la sesion de ~15:00 UTC 2026-03-08

---

## [2026-03-08] PM — IN_PROGRESS — Bug: chat format ugly after tool call, wrong salary from profile

- Tras llamar a `invoke_calculate_irpf`, la respuesta del agente se renderiza mal (formato feo)
- El agente se queda bloqueado en algunos flujos post-tool-call
- El agente usa salario 35000 EUR en lugar del valor real del perfil (37500 EUR)
- Causa raiz por investigar: inyeccion del fiscal_profile al agente y renderizado markdown post-tool

---

## [2026-03-08] PM — DONE — Dark theme territorial pages + ForgotPassword + BD cleanup

### Completado
- **Phase 5 redesign**: CeutaMelillaPage, CanariasPage, ForalPage y TerritoryCard migrados a dark theme (#0f172a), coherentes con design system global
- **ForgotPassword**: Migrado a split-screen layout (dark brand panel + white form panel), igual que Login/Register. Clases CSS actualizadas a sistema `auth-*`
- **BD deducciones limpiada**: 190 filas → 134 unicas. Eliminados duplicados de encoding. Territorios normalizados: "Islas Baleares"→"Baleares", "Islas Canarias"→"Canarias"
- **InteractiveSpainMap revertido**: SVG interactivo descartado, reemplazado por imagen estatica `hero-spain-3d.webp`

### Archivos modificados
- `frontend/src/pages/CeutaMelillaPage.tsx` + `.css`
- `frontend/src/pages/CanariasPage.tsx` + `.css`
- `frontend/src/pages/ForalPage.tsx` + `.css`
- `frontend/src/components/TerritoryCard.tsx` + `.css`
- `frontend/src/pages/ForgotPassword.tsx` + `Auth.css`
- BD Turso: tabla `deductions` limpiada

---

## [2026-03-07] QA — DONE — Auditoria desktop 1440x900 (analisis estatico codigo)

### Resultado: 1 bug critico arreglado, 4 bugs menores documentados
- Reporte completo: `plans/qa-desktop-report-2026-03-07.md`

### Bug critico arreglado (ESTE AGENTE):
- **B1 (CRITICO — ARREGLADO)**: `Register.tsx` boton decia "Crear Cuenta Gratis" — cambiado a "Crear cuenta". Archivo: `frontend/src/pages/Register.tsx` linea 209.

### Bugs pendientes para frontend agent:
- **B4 (BAJA)**: Acentos ausentes en FAQ de Canarias, Foral y Ceuta/Melilla — strings con encoding incompleto
- **B3 (MEDIA)**: Landing page solo muestra plan Particular — los autonomos no ven su plan de 39 EUR
- **B2 (MEDIA)**: Hero chat-preview es texto plano sin animacion — no refleja el producto real

### Verificaciones OK (no requieren accion):
- CTA de `/canarias` dice "Empezar ahora — desde 5 €/mes" — correcto (no dice gratis)
- `/subscribe` grid de 2 columnas a 768px+ — correcto
- Imagenes hero .webp existen en `/public/images/` — confirmado
- `/guia-fiscal` y `/chat` redirigen a login — comportamiento correcto (rutas protegidas)

### Nota metodologica:
Playwright MCP no disponible en esta sesion (sin browser headless activo). Auditoria basada en inspeccion de codigo JSX/CSS + screenshots pendientes con Playwright real.

---

## [2026-03-07] QA — DONE — Auditoria mobile 375x812 (analisis estatico CSS)

### Resultado: 4 paginas PASS, 4 con issues
- Reporte completo: `plans/qa-mobile-report-2026-03-07.md`
- Script playwright: `tests/e2e/mobile-audit.spec.ts`

### Bugs prioritarios para frontend agent:
- **B-MOB-10 (CRITICAL)**: Verificar que commit `0ab0a9e` resuelve hamburger en /chat. Si no esta activo, el hamburger sigue abriendo la sidebar en lugar de la nav mobile.
- **B-MOB-08 (MAJOR)**: Usuarios en `/subscribe` sin suscripcion pueden quedar en loop de navegacion en mobile — necesita link "Volver al inicio" sticky o en header.
- **B-MOB-06 (MAJOR)**: Tabla IGIC en `/canarias` tiene `min-width: 540px` — requiere scroll horizontal en 375px. Redisenar como cards apiladas para mobile.
- **B-MOB-01 (MAJOR)**: Stats landing — span del `+` puede quedar en linea separada del numero en 2rem. Fix: `align-items: baseline` en `.stat-number`.
- **B-MOB-05 (MINOR)**: Gradient text en auth-brand__title puede fallar en iOS Safari (overflow:hidden en padre). Necesita verificacion en dispositivo real.

### Nota metodologica:
Playwright MCP no disponible en esta sesion. Auditoria basada en inspeccion de codigo CSS/JSX. Para screenshots reales ejecutar el script con servidor local.

---

## [2026-03-07] PM — DONE — Redesign visual completo (Phases 1-4)

### Phase 1+2 — Chat + Login/Register + Header + Sidebar
- **Login.tsx / Register.tsx**: Split-screen layout (dark brand panel + white form panel), glassmorphism pills, gradient CTAs, password show/hide toggle
- **Auth.css**: Complete overhaul — gradient orbs, premium 48px inputs, gradient submit button
- **Chat.tsx**: Message avatars (Zap for assistant, initials for user), empty state with illustration + 4 suggestion cards, handleSuggestionClick
- **Chat.css**: Gradient user messages, white card assistant messages, floating pill input, asymmetric border-radius
- **ConversationSidebar.css**: Dark navy #0f172a sidebar, blue active state, dark scrollbar
- **Header.css**: Glassmorphism (backdrop-filter: blur(14px), rgba white bg)

### Phase 3 — Subscribe + Settings CSS
- **SubscribePage.css**: Dark hero header section, premium plan cards, gradient border on popular plan, hover lift effects
- **SettingsPage.css**: Premium form inputs, modern tab navigation, gradient save buttons, dark subscription card

### Phase 4 — Home + Declarations CSS
- **Home.css**: Dark hero section, dark stats section, glassmorphism chat preview, blue glow comparison column, feature card blue glow hover
- **DeclarationsPage.css**: Dark header strip, premium form inputs, gradient tabs, hover lift cards

### Image compression DONE
- hero-foral: 6.8MB PNG -> 64KB WebP (99% reduction)
- hero-ceuta-melilla: 7.8MB -> 110KB WebP (98.6%)
- hero-canarias: 7.1MB -> 72KB WebP (99%)
- chat-empty-state: 1.8MB -> 34KB WebP (98%)
- All TSX refs updated to .webp

### Build: OK (6.43s, 0 errors)

### Pending
- Git commit
- Deploy to Railway
- TaxGuidePage, WorkspacesPage CSS refresh (lower priority)
- Modals redesign (lower priority)

---

## [2026-03-07] PM — DONE — Landing Territoriales SEO (ADR-007) con Stitch + Nano Banana

### Completado
- **3 hero images 4K** generadas con Nano Banana (Gemini 3 Pro Image): `hero-foral.png`, `hero-ceuta-melilla.png`, `hero-canarias.png` en `frontend/public/images/`
- **Proyecto Stitch** creado: 4 screens (2 mobile + 2 desktop) para CanariasPage — proyecto ID `7755516611334879290`
- **CanariasPage nueva** (`/canarias`): 8 secciones — hero dark con imagen, ventajas (IGIC/ZEC/RIC/deducciones), tabla IGIC vs IVA, seccion ZEC 3 pasos, comparativa herramientas, FAQ, CTA
- **ForalPage actualizada**: Hero con fondo oscuro #0f172a + imagen isometrica territorios forales
- **CeutaMelillaPage actualizada**: Hero con fondo oscuro + imagen 60% glassmorphism
- **Home.tsx fixes**: Territory chips clickables (Canarias, Ceuta, Melilla, forales), stats corregidas a 128 deducciones
- **Footer**: Link a `/canarias` anadido
- **Build**: OK (6.5s, 0 errores)

### Assets generados
- `frontend/public/images/hero-foral.png` (7.1 MB, 5504x3072, 4K)
- `frontend/public/images/hero-ceuta-melilla.png` (8.1 MB, 5504x3072, 4K)
- `frontend/public/images/hero-canarias.png` (7.4 MB, 5504x3072, 4K)

### Pendiente
- Optimizar imagenes hero (7-8MB cada una, comprimir a WebP <500KB para produccion)
- Deploy a Railway
- Verificar FadeContent animations en navegador real (fullPage screenshots no activan IntersectionObserver)

---

## [2026-03-07] PM — DONE — Sesion PM: ADR-005 + ADR-006 + Stitch OAuth

### Completado
- **ADR-005 Calculadora ISD**: Tool ya existia completa. Creados 61 tests (unit + integration) — todos PASS. Cobertura: tarifa estatal, 4 grupos parentesco, bonificaciones 8+ CCAA + forales.
- **ADR-006 Deducciones 17 CCAA**: Creado `seed_deductions_territorial_v2.py` con 64 nuevas deducciones en 11 CCAA (Galicia, Asturias, Cantabria, La Rioja, Aragon, CyL, CLM, Extremadura, Murcia, Baleares, Canarias). Total proyecto: 128 deducciones. 48 tests creados — todos PASS.
- **Stitch OAuth**: Configurado OAuth2 via gcloud ADC. Bug detectado y resuelto: path gcloud con espacios en Windows (junction C:\gcloud-sdk). `.mcp.json` actualizado sin API key.
- **Nano Banana**: Verificado operativo (show_output_stats OK).

### Pendiente proxima sesion
- **Landing territorial** (forales + Ceuta/Melilla + Canarias): Disenar con Stitch + generar assets con Nano Banana. Paginas SEO publicas `/territorios-forales` y `/ceuta-melilla` (ADR-007).
- Ejecutar `seed_deductions_territorial_v2.py` contra BD Turso para poblar las 64 nuevas deducciones.
- Correr tests completos para verificar que los 61+48 nuevos tests no rompen nada.

---

## [2026-03-06] DOC AUDITOR — DONE — README.md actualizado a v3.0

`README.md` reescrito con 10 features nuevas: IRPF Simulator (9 tools, Phase 1+2), Tax Guide Wizard (7 pasos + LiveEstimatorBar), Motor de Deducciones (64 total), Stripe Subscriptions (Particular 5 EUR + Autonomo 39 EUR), Perfil Fiscal Extendido (13 campos), Export PDF + Email (ReportLab + Resend), Soporte Ceuta/Melilla (Art. 68.4), PWA (service worker manual), Cookie Compliance (vanilla-cookieconsent v3), tools calculate_modelo_303 + calculate_isd documentados. Arquitectura ASCII, stack, estructura del proyecto y troubleshooting expandidos.

---

## [2026-03-06] PM — DONE — Simulador IRPF Fase 1+2 + Guia Fiscal + Documentacion

### Resumen sesion
- **Backend Fase 1**: Planes pensiones, hipoteca pre-2013, maternidad, familia numerosa, donativos, retenciones completas
- **Backend Fase 2**: Tributacion conjunta, alquiler pre-2015, rentas imputadas inmuebles
- **Frontend Fase 1+2**: TaxGuidePage 7 pasos, LiveEstimatorBar, useIrpfEstimator, useTaxGuideProgress, useFiscalProfile actualizado, SettingsPage actualizado
- **Endpoint**: POST /api/irpf/estimate (irpf_estimate.py)
- **Bug fix**: cuota_liquida_total key → cuota_total
- **Verificado**: Frontend build OK, backend imports OK
- **Documentacion**: README, Business Plan, User Manual actualizados
- **Memoria**: MEMORY.md, bugfixes-2026-03.md actualizados

### Archivos principales modificados
- `backend/app/utils/irpf_simulator.py` (Fase 1+2 params + logic)
- `backend/app/routers/irpf_estimate.py` (Fase 1+2 fields + key fix)
- `backend/app/tools/irpf_simulator_tool.py` (Fase 1+2 forwarding)
- `backend/app/agents/tax_agent.py` (system prompt awareness)
- `frontend/src/pages/TaxGuidePage.tsx` (7-step wizard completo)
- `frontend/src/components/LiveEstimatorBar.tsx` + CSS
- `frontend/src/hooks/useIrpfEstimator.ts` (Fase 1+2 interfaces)
- `frontend/src/hooks/useTaxGuideProgress.ts` (Fase 1+2 data)
- `frontend/src/hooks/useFiscalProfile.ts` (Fase 1+2 fields)
- `frontend/src/pages/SettingsPage.tsx` (Fase 1+2 form fields)
- `README.md`, `scripts/generate_business_plan.py`, `scripts/generate_user_manual.py`

### Pendiente deploy
- Deploy a Railway para que QA pueda probar en produccion

---

## [2026-03-07] QA Tester — DONE — QA Sesion 5: Mobile Navigation Bugs + Desktop Suite

> Reporte completo: `plans/qa-report-2026-03-07.md`
> Tests: 12 ejecutados | 10 PASS | 1 FAIL (error script) | 1 SKIP

### Bugs criticos detectados (ACCION REQUERIDA)

**B13 — Alta — Menu hamburguesa mobile NO muestra navegacion**
- El boton hamburguesa (≡) en mobile abre el historial de conversaciones (ConversationSidebar)
- Los links Chat / Guia Fiscal / Configuracion NO son accesibles desde el menu en mobile
- Causa raiz: `Chat.tsx` linea 215 pasa `onMenuToggle` al Header, que secuestra el comportamiento de nav
- Archivos: `frontend/src/pages/Chat.tsx` + `frontend/src/components/Header.tsx`
- Fix propuesto: Separar el boton de historial del boton de navegacion en mobile
- Screenshot: `tests/e2e/screenshots/s5-M03-hamburger-clicked.png`

**B14 — Media — Stats landing incorrectas**
- Muestra 138+ documentos / 47 deducciones / 7 territorios
- Deberia mostrar 428+ / 64 / 21
- Archivo: `frontend/src/pages/Home.tsx` (o componente de stats)
- Screenshot: `tests/e2e/screenshots/s5-D01-stats.png`

**B15 — Media — Verificar acceso Guia Fiscal para plan particular**
- `/guia-fiscal` redirige a `/subscribe` para usuario plan `particular`
- Puede ser intencional (feature de pago) o bug de ProtectedRoute
- Si es intencional: anadir badge "Pro" en el link del nav para no confundir

### Confirmado: Guia Fiscal parcialmente desplegada
- El link "Guia Fiscal" SI aparece en el nav del header (desplegado desde sesion previa)
- Pero `/guia-fiscal` redirige a `/subscribe` para plan particular
- Endpoint `/api/irpf/estimate` no verificado aun

### Estado bugs reportados por usuario
- "No se ve menu de configuracion en mobile": CONFIRMADO — es el bug B13
- "No se ve acceso al chat en mobile": NO REPRODUCIDO — chat visible y funcional en 375px

---

## [2026-03-06] QA Tester — BLOCKED — Guia Fiscal / Tax Guide Feature QA (Sesion 5)

> Reporte: `.claude/agent-memory/qa-tester/qa-report-tax-guide.md`
> Test suite: `tests/e2e/tax-guide-2026-03-06.spec.ts`

### Resultados: 0/13 PASS — DEPLOYMENT BLOCKER

**B-TG1 CRITICO**: La feature `TaxGuidePage` (`/guia-fiscal`) NO está desplegada en produccion.
- Navigating to `https://impuestify.com/guia-fiscal` redirects to `/` (home page)
- Header nav in production only shows "Chat" and "Configuracion" — "Guia Fiscal" link absent
- Root cause: current `main` branch not deployed to Railway since adding TaxGuidePage

**Accion requerida para Frontend Agent / DevOps**:
- Deploy current `main` branch to Railway production
- Verify `https://impuestify.com/guia-fiscal` loads TaxGuidePage after deploy
- Verify `/api/irpf/estimate` endpoint responds (B-TG3 unverified)
- After deploy: re-run `npx playwright test tests/e2e/tax-guide-2026-03-06.spec.ts --workers=1`

**Code review** del codigo local: implementacion correcta, lista para produccion.
Ver detalles completos en el reporte.

---

## [2026-03-06] QA Tester — DONE — QA E2E Produccion Sesion 4 (11 tests) — B2 RESUELTO

> Reporte completo: `plans/qa-report-production-session4-2026-03-06.md`
> Screenshots: `tests/e2e/screenshots/session4-*.png`
> Script: `tests/e2e/qa-session4-2026-03-06.spec.ts`

### Resultados: 11/11 PASS

**B2 RESUELTO**: El fix en `chat_stream.py` linea 96 funciona en produccion. Carlos Martinez Ruiz (test.autonomo@impuestify.es) puede ahora acceder a RETA, Modelo 303, Modelo 130, retenciones y deducciones territoriales sin bloqueo.

**Evidencia**: La tool `calculate_autonomous_quota` se ejecuta correctamente para el usuario autonomo.

**Bugs activos pendientes (menores)**:
- B4: Modal "Sistema de IA" — comportamiento aceptable para usuarios reales (baja prioridad)
- B11 (nuevo): Precios en /subscribe con formato "EUR 5" en lugar de "5 €" — cosmético

**Veredicto**: APP LISTA PARA USUARIOS REALES.

---

## [2026-03-06] QA Tester — DONE — QA E2E Produccion Sesion 2 (22 tests)

> Reporte completo: `plans/qa-report-production-session2-2026-03-06.md`
> Screenshots: `tests/e2e/screenshots/`
> Scripts reutilizables: `tests/e2e/qa-session2-*.spec.ts`

### Resultados: 16/22 PASS funcional, 2 bugs criticos, 4 bugs medios

### RESUELTO desde sesion 1
- B3 Estadisticas landing: RESUELTO — ahora 409+/62/20/24/7
- B5 Error login tecnico: RESUELTO — mensaje amigable correcto

### BUGS PENDIENTES — ACCION REQUERIDA

**B1 [CRITICO] — Landing page: contenido invisible** — Las secciones features, comparativa con TaxDown y pricing siguen sin renderizarse. Solo se ve hero + stats + footer. Impacto directo en conversion. Sigue abierto desde sesion 1.

**B2 [CRITICO] — Usuario autonomo COMPLETAMENTE BLOQUEADO en produccion**
- Carlos Martinez Ruiz (test.autonomo@impuestify.es) tiene plan_type="particular" en BD Turso
- Stripe tiene el plan "autonomo" activo (proximo cobro 1 abril 2026)
- El chat lee de Turso -> bloquea TODAS las consultas de autonomo (RETA, IVA, Modelo 303, Modelo 130, retenciones, deducciones Cataluna)
- Tests T10-T14 todos bloqueados con mensaje "Particular — 5€/mes"
- **Fix inmediato BD**: `UPDATE users SET plan_type='autonomo' WHERE email='test.autonomo@impuestify.es';`
- **Fix estructural**: Revisar webhook Stripe `checkout.session.completed` para que actualice plan_type en Turso automaticamente

**B4 [MEDIA] — Modal "Sistema de IA" se reabre** — En cada sesion de navegador limpia. Verificar persistencia en localStorage por user_id, no por sesion de navegador.

**B6 [MEDIA] — Logout sin label visible** — El boton de cerrar sesion es un icono sin texto. Poco descubrible para usuarios nuevos.

**B7 [MEDIA] — Cookie banner sin botones Aceptar/Rechazar prominentes** — Solo "Configurar" es visible. Revisar diseno para cumplimiento AEPD (equiparacion de botones).

---

## [2026-03-06] QA Tester — DONE — QA E2E Produccion Sesion 1

> Reporte: `plans/qa-report-production-2026-03-06.md`

---

## Historial Completado (Resumen)

[2026-03-05] PWA + Landing + DeductionCards + Favicon + ReportActions + ShareReportModal — 🟢 DONE
[2026-03-05] Motor Deducciones (16 estatales + 48 territoriales) + Export PDF + Email Resend — 🟢 DONE
[2026-03-04] Ceuta/Melilla ventajas fiscales autonomos — Backend 🟢 DONE
[2026-03-03] Suscripciones Stripe (backend + frontend) — 🟢 DONE
[2026-03-03] Perfil fiscal autonomo + Panel admin — 🟢 DONE
[2026-03-03] Cookies LSSI-CE + RGPD — 🟢 DONE
[2026-03-02] Crawler sesiones 1-12 (428 archivos RAG) — 🟢 DONE
[2026-03-02] Streaming SSE v3.0 + FormattedMessage + StreamingTimeline — 🟢 DONE

> Para detalles completos de tareas completadas, ver `agent-comms-archive.md`

---

## 📢 INSTRUCCIONES PARA BACKEND — Diseños de Registro / Modelos AEAT

> **Contexto**: AEAT **NO usa XSD** (excepto Modelo 200). Usa ficheros planos de posiciones fijas. Los diseños de registro están en `docs/AEAT/Modelos/DisenosRegistro/`.

### Archivos disponibles

| Archivo | Modelo | Prioridad |
|---------|--------|-----------|
| `DR303_e2026.xlsx` | 303 - IVA trimestral | **ALTA** |
| `DR130_e2019.xls` | 130 - Pagos fraccionados IRPF ED | **ALTA** |
| `DR131_e2025.xlsx` | 131 - Pagos fraccionados IRPF EO | MEDIA |
| `DR111_e2019.xls` | 111 - Retenciones trabajo/prof. | MEDIA |
| `DR115_e2019.xls` | 115 - Retenciones alquileres | BAJA |
| `DR190_e2025.pdf` | 190 - Resumen anual retenciones | MEDIA |
| `DR200_e2024.xls` | 200 - IS (TIENE XSD) | **ALTA** |
| `DR202_e2025.xlsx` | 202 - Pagos fraccionados IS | MEDIA |
| `DR390_e2025.xlsx` | 390 - Resumen anual IVA | MEDIA |
| `DR347_e2025.pdf` | 347 - Operaciones terceros | BAJA |
| `DR349_e2020.pdf` | 349 - Op. intracomunitarias | BAJA |
| `DR714_e2024.xls` | 714 - Patrimonio | BAJA |
| `DR720.pdf` | 720 - Bienes extranjero | BAJA |
| `Instrucciones_Modelo650_ISD.pdf` | 650 - ISD Sucesiones | MEDIA |
| `Instrucciones_Modelo651_ISD.pdf` | 651 - ISD Donaciones | MEDIA |

### Implementación recomendada

**Opción A (recomendada): Tools de cálculo/simulación**
- Crear tools que calculen campos del modelo (no que generen fichero)
- Ejemplo: `calculate_modelo_303(base_imponible, iva_deducible, ...)` → casillas 01-89
- Diseños de registro como especificación de campos

**Opción B: Generación de ficheros** (futuro)
- Generar ficheros planos conformes al diseño de registro
- Requiere parsear Excel para posiciones/longitudes

**Prioridad:**
1. Modelo 303 IVA → tool cálculo casillas
2. Modelo 130 → pago fraccionado IRPF autónomos
3. Modelo 200 IS → parser XSD

**Excepciones:**
- Modelo 200: Único con XSD (`mod2002024.xsd`) para XML
- Modelos 650/651: Solo formulario web, sin diseño de registro
- Transición XML/XSD: Orden HAC/747/2025, enero 2027

### URLs referencia
- Diseños de registro: https://sede.agenciatributaria.gob.es/Sede/ayuda/disenos-registro.html
- Portal desarrolladores: https://www.agenciatributaria.es/AEAT.desarrolladores/

---

## Pendientes RAG

- Manual Práctico Renta 2025 Tomo 1+2 (AEAT) — 404 a fecha 3/3/2026
- Orden HAC Modelo 100 ejercicio 2025 — antes del 8 abril 2026

---

## [2026-03-08] QA — DONE — Sesion Completa: /guia-fiscal + flujos core — analisis estatico

### Metodologia: analisis estatico exhaustivo del codigo fuente
> Playwright MCP no disponible — se realizo inspeccion directa de TaxGuidePage.tsx, CSS, hooks y backend router.

### Bugs criticos detectados en /guia-fiscal

**B-GF-01 (CRITICA) — Hero del wizard no se renderiza**
- El CSS define `.tax-guide__header` con titulo y descripcion
- El JSX de TaxGuidePage NO renderiza ese div — el wizard empieza directamente sin titulo
- Fix: anadir `<div className="tax-guide__header">` con H1 "Calcula tu IRPF" al inicio del return()
- Archivo: `frontend/src/pages/TaxGuidePage.tsx` lineas 1096-1100

**B-GF-02 — CLAUDE.md dice "/api/irpf/estimate no requiere auth" — INCORRECTO**
- El endpoint tiene `current_user: TokenData = Depends(get_current_user)` — SI requiere JWT
- Actualizar CLAUDE.md seccion Project Overview con nota de que requiere auth

**B-GF-03 (MAYOR) — Verificar cuota_liquida_total vs cuota_total**
- Un bug fix anterior (agent-comms: "cuota_liquida_total key → cuota_total") hace sospechar mismatch
- Verificar que `irpf_simulator.py` devuelve el campo con el nombre correcto
- Si hay mismatch, el desglose del resultado estara vacio en el frontend

**B-GF-06 (MAYOR) — canProceed = true siempre despues del paso 0**
- `TaxGuidePage.tsx` linea 1094: `const canProceed = step === 0 ? !!data.comunidad_autonoma : true`
- Usuario puede llegar al Resultado con todos los campos en 0
- Fix: validar que haya al menos 1 campo de ingresos > 0 en paso 1 (Trabajo) y 6 (Resultado)

**B-GF-07 (MAYOR) — useDeductionDiscovery errores silenciosos**
- El hook hace setResult(null) en caso de error — la seccion de deducciones queda vacia sin aviso
- Fix: anadir estado de error en el hook y mostrar mensaje al usuario

### Estado /guia-fiscal segun acceso
- La ruta usa `ProtectedRoute` con `requireSubscription={true}` (default)
- El usuario `test.particular@impuestify.es` deberia tener `has_access=true` si su suscripcion esta activa
- Si redirige a /subscribe: suscripcion inactiva en backend (verificar tabla users)

### Script Playwright generado
- `tests/e2e/qa-session-completa-2026-03-08.spec.ts` — 10 tests, listo para ejecutar
- Cubre: landing, login, guia-fiscal (4 tests), chat, settings, modelos-trimestrales, mobile nav, territoriales, legales, cookies
- Ejecutar con: `npx playwright test tests/e2e/qa-session-completa-2026-03-08.spec.ts --workers=1`

### Reporte completo
- `plans/qa-report-2026-03-08-completo.md`

### Acciones para PM/Frontend
1. (CRITICA) Anadir hero visible en TaxGuidePage — 5 min de fix
2. (MAYOR) Verificar cuota_liquida_total en irpf_simulator.py y validar en produccion
3. (MAYOR) Mejorar canProceed para validar ingresos en paso de trabajo
4. (MENOR) Actualizar CLAUDE.md — /api/irpf/estimate requiere JWT (no es publico)

## Tareas activas

[2026-03-06] [QA] 🟡 IN_PROGRESS — Tests E2E Workspaces en produccion (https://impuestify.com). Usuarios: test_particular@impuestify.com + test_autonomo@impuestify.com. 6 tests T1-T6.

[2026-03-06] [COMPETITIVE] 🟢 DONE — Investigacion pricing plan Autonomo: 10 plataformas investigadas (TaxDown, Declarando, Taxfix, Abaq, Fiscaliza, Quipu, Holded, Anfix, Billin, Sage + asesores tradicionales). Recomendacion: 39 EUR/mes fase actual, 59 EUR/mes con Colaborador Social AEAT. NO recomendado 200 EUR/mes. Informe en `plans/pricing-research-autonomo-2026-03.md`.

[2026-03-06] [PM] 🟢 DONE — Sesion QA completa. 2 usuarios de test creados (particular Madrid + autonomo Cataluna). 17 tests ejecutados: 15 PASS, 2 FAIL. Fix CSP header (main.py). Informe en `plans/qa-report-2026-03-06.md`. Seed script: `backend/scripts/seed_test_users.py`.

[2026-03-06] [PM] 🟢 DONE — Analisis competitivo TaxDown. GAP CRITICO confirmado: NO cubren forales (Pais Vasco + Navarra + Ceuta/Melilla = ~1.6M declarantes). Impuestify SI. Informe en `plans/competitive-taxdown-2026-03.md`.

[2026-03-06] [PM] 🟢 DONE — Tests unitarios arreglados: 350/352 PASS (antes: 0/0, 15 collection errors). Root cause: `test_admin.py` inyectaba `types.ModuleType` falsos en `sys.modules`. Fix: imports directos + `import_mode=importlib` en pytest.ini. Tambien faltaba `app/utils/__init__.py`.

[2026-03-05] [BACKEND] 🟢 DONE — Fix: TaxAgent ahora verifica situacion_laboral antes de usar herramientas de autonomos. System prompt actualizado con reglas de clarificacion obligatoria. `tax_agent.py` modificado.

[2026-03-05] [BACKEND] 🟢 DONE — Fix: FOREIGN KEY constraint en message_sources. `conversation_service.py` ahora valida chunk_ids antes de insertar. Degrada gracefully si chunks no existen en BD.

[2026-03-05] [FRONTEND] 🟢 DONE — Fix: Renderizado markdown en chat. Instalado `remark-gfm` para soporte GFM (tablas, tachado, task lists). Eliminado `white-space: pre-wrap` que causaba doble salto de línea. Añadidos estilos para tablas, bloques de código, blockquotes, hr, listas anidadas.

---

## Dependencias Pendientes
---
# [AGENT_ESPERANDO] espera a [AGENT_TRABAJANDO] para [TAREA]

## Conflictos Detectados
---
# Si un agente detecta que otro modificó el mismo archivo, lo registra aquí

## Instrucciones para Agentes
---
1. Al INICIAR una tarea: Añade línea con 🟡 IN_PROGRESS
2. Si estás BLOQUEADO esperando a otro: 🔴 BLOCKED
3. Al TERMINAR: Cambia a 🟢 DONE
4. Si necesitas review: 📢 NEEDS_REVIEW
5. SIEMPRE `git pull` antes de empezar
