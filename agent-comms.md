# Agent Communication Log - TaxIA
# =================================
# Canal de comunicacion entre agentes.
# Cada agente debe leerlo al inicio y escribir al terminar una tarea.
#
# Formato:
# [TIMESTAMP] [AGENT] [STATUS] - Mensaje
# STATUS: 🟢 DONE | 🟡 IN_PROGRESS | 🔴 BLOCKED | 📢 NEEDS_REVIEW

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
