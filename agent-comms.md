# Agent Communication Log - TaxIA
# =================================
# Canal de comunicacion entre agentes.
# Cada agente debe leerlo al inicio y escribir al terminar una tarea.
#
# Formato:
# [TIMESTAMP] [AGENT] [STATUS] - Mensaje
# STATUS: 🟢 DONE | 🟡 IN_PROGRESS | 🔴 BLOCKED | 📢 NEEDS_REVIEW

## [2026-03-28] PM Coordinator — 🟢 DONE — Sesion 23: 7 Features Fiscales + Compliance Audit

### Tareas completadas (7 features + 4 fixes)
1. **P1: GP Transmision Inmuebles** — capital_gains_property.py, VentaInmueble, simulador, Art.35+DT9a+Art.38 (plazo 24m). 16 tests
2. **P3: Plusvalia Municipal (IIVTNU)** — Calculator (objetivo+real), STC 182/2021, endpoint REST, tool chat. 17 tests
3. **P4: ISD 21/21 CCAA** — 12 CCAA nuevas + fix donaciones Extremadura (DL 1/2018) + Asturias Grupo II. 76 tests
4. **P5: Modelo 720/721** — 2 tools chat + 2 endpoints REST + TaxAgent. Umbrales 50K/20K. 25 tests
5. **P6: 2o Declarante Conjunta** — SegundoDeclarante model, simulador extendido, 4 escenarios comparativa, inmuebles SD. 21 tests
6. **P7: Pipeline Auto-Ingesta RAG** — auto_ingest.py (--dry-run/--limit), SHA-256 dedup, FTS5 rebuild. 14 tests
7. **P2: Gastos Deducibles Autonomos** — Verificado existente (activity_income.py + GastosDeduciblesPage.tsx)

### Compliance fixes
- ISD Extremadura donaciones 99% (DL 1/2018 Art.15)
- ISD Asturias Grupo II donaciones 95%
- GP reinversion plazo 24 meses Art.38.1 LIRPF
- 2o declarante ventas inmuebles en base ahorro
- Regression fix: test_conjunta_monoparental_andalucia (encoding tildes)

### Archivos creados (~15)
- backend/app/utils/calculators/capital_gains_property.py
- backend/app/utils/calculators/plusvalia_municipal.py
- backend/app/tools/modelo_720_tool.py
- backend/app/tools/modelo_721_tool.py
- backend/app/tools/plusvalia_municipal_tool.py
- backend/app/routers/modelo_720.py
- backend/app/routers/plusvalia.py
- backend/scripts/auto_ingest.py
- backend/tests/test_capital_gains_property.py
- backend/tests/test_plusvalia_municipal.py
- backend/tests/test_isd_ccaa_completo.py
- backend/tests/test_modelo_720_721.py
- backend/tests/test_segundo_declarante.py
- backend/tests/test_auto_ingest.py

### Archivos modificados (~12)
- backend/app/utils/irpf_simulator.py (GP inmuebles + 2o declarante)
- backend/app/routers/irpf_estimate.py (VentaInmueble + SegundoDeclarante)
- backend/app/tools/__init__.py (720/721 + plusvalia)
- backend/app/tools/isd_calculator_tool.py (12 CCAA + fixes)
- backend/app/tools/joint_comparison_tool.py (4 escenarios)
- backend/app/main.py (routers 720 + plusvalia)
- backend/tests/test_irpf_regression.py (tilde encoding fix)

### Metricas
- Tests nuevos: ~170
- Tests totales: ~1,646
- Regresiones: 0
- Agentes paralelos: 8 (6 implementacion + 2 fixes)

### Pendiente proxima sesion
- [ ] Frontend: wizard steps para GP inmuebles, plusvalia, 720/721, 2o declarante
- [ ] ML fiscal features (ml_fiscal_features table)
- [ ] Re-ejecutar crawler 90 URLs
- [ ] Verificar Asturias donaciones Grupo II rate exacto (actualmente 95% conservador)

---

## [2026-03-26] PM Coordinator — 🟢 DONE — Sesion 22: RAG pipeline fix completo (8 bugs)

### Tareas completadas (8)
1. **Repo migrado**: `Nambu89/TaxIA` → `Nambu89/Impuestify` (289 commits conservados)
2. **Territory mismatch**: RegionDetector → DB source mapping (Pais Vasco→Bizkaia, etc.)
3. **Logs Railway**: logger.info → print(flush=True) para diagnostico
4. **FTS5 fix**: OR entre keywords + rebuild 80,481 chunks + stop words espanolas
5. **Semantic cache**: Rechazo patrones stale + prevencion cache poisoning + purge script
6. **System prompt rewrite**: Tecnicas GPT-5/Claude/NotebookLM (atribucion RAG, concision, anti-narracion)
7. **Frontend sources**: Filtrar "(pag. 0)" y sources sin titulo
8. **Archivos basura**: Limpieza de 20+ archivos junk en raiz del proyecto

### Commits: 2c06abe, 5aee9f8, 8b61be6, 2af4830, 1845e1c, f0c6e3e, 8adb0e0, 8f44c8a, 4d7f4ae

---

## [2026-03-26] (anterior) PM Coordinator — 🟢 DONE — Railway CLI deploy + RAG territory fix (RESUELTO 2026-03-27)

### Problema
Railway dejo de auto-deployar despues del commit `e395e12` (19:57). 15 commits posteriores NO estan en produccion.
GitHub Webhooks pagina VACIA — Railway no recibe push events.
railway.toml invalido (usa [[services]] que no existe en el schema).

### Soluciones intentadas SIN exito
- Empty commit + push → no deployea
- Touch requirements.txt → no deployea
- Disconnect/reconnect repo en Railway → no arregla
- Ctrl+K Deploy Latest en Railway → no funciona
- `railway up` desde backend/ → "Could not find root directory: /backend"
- `railway up` desde raiz → "os error 33" (OneDrive lock)
- `taskkill python.exe` + retry → sigue bloqueado

### ACCION INMEDIATA proxima sesion
1. **Deployar fix RAG** (commit f5018ac): `cp backend C:\tmp\taxia-deployX` → `railway link` → `railway up`
2. Probar pregunta ponedoras Bizkaia en conversacion nueva
3. Reconectar GitHub al servicio Railway (investigar por que Bad Credentials)

### Bugs de produccion NO deployados
- TaxAgent pide permiso ("Te digo lo que encuentre, ¿de acuerdo?") — fix en `4acd27c`
- TaxAgent lanza IRPF para toda pregunta — fix en `b0e61be`
- IAE lookup file not found — fix en `370ff29` (puede estar deployado)
- Responsive mobile CSS — fix en `cec0a04`

---

## [2026-03-25] PM Coordinator — 🟢 DONE — Sesion 21: 9 CCAA seeds + frontend params + plan GP

### Tareas completadas (5)
1. **Seeds CCAA Fase 2**: CLM 25 + Asturias 26 + Cantabria 21 = 72 deducciones nuevas
2. **Seeds CCAA Fase 3a**: Baleares 24 + La Rioja 24 + Extremadura 19 = 67 deducciones nuevas
3. **Seeds CCAA Fase 3b**: Aragon 19 + CyL 17 + Cataluna 13 = 49 deducciones nuevas
4. **Frontend params simulador**: 7 campos XSD (pension compensatoria, alimentos hijos, doble imposicion, discapacidad desc/asc) conectados al wizard + estimador + resultados. Build OK
5. **Plan GP transmision inmuebles**: Plan completo en plans/plan_gp_transmision_inmuebles.md (Art. 38 reinversion + DT 9a abatimiento + casillas 0355-0370)

### Archivos creados (9 seeds)
- `backend/scripts/seed_deductions_clm_2025.py` (25 deducciones)
- `backend/scripts/seed_deductions_asturias_2025.py` (26 deducciones)
- `backend/scripts/seed_deductions_cantabria_2025.py` (21 deducciones)
- `backend/scripts/seed_deductions_baleares_2025.py` (24 deducciones)
- `backend/scripts/seed_deductions_larioja_2025.py` (24 deducciones)
- `backend/scripts/seed_deductions_extremadura_2025.py` (19 deducciones)
- `backend/scripts/seed_deductions_aragon_2025.py` (19 deducciones)
- `backend/scripts/seed_deductions_cyl_2025.py` (17 deducciones)
- `backend/scripts/seed_deductions_cataluna_2025.py` (13 deducciones)

### Archivos modificados (frontend)
- `frontend/src/hooks/useIrpfEstimator.ts` — 7 campos input + 3 campos resultado
- `frontend/src/pages/TaxGuidePage.tsx` — formularios discapacidad, obligaciones familiares, doble imposicion, seccion resultados
- `frontend/src/hooks/useTaxGuideProgress.ts` — nuevos defaults

### Motor deducciones actualizado
- Total deducciones 2025: 160 (sesion 20) + 188 CCAA + 60 forales (sesion 21) = **408 nuevas**
- 15/15 CCAA regimen comun seeded al 100% vs AEAT 2025
- 4/4 territorios forales seeded con 15 deducciones cada uno (EPSV, Norma Foral)
- Ceuta/Melilla: correctamente 0 autonomicas (solo 60% estatal)
- **21/21 territorios cubiertos. Gap: 0%**

### Pendiente proxima sesion
- [ ] Ejecutar 16 seeds en produccion (Turso) — 6 sesion 20 + 9 CCAA + 1 foral sesion 21
- [ ] GP transmision inmuebles — implementar calculator (plan listo)
- [ ] 2o declarante conjunta — XSD gap HIGH pendiente
- [ ] Tests para nuevos seeds (validar syntax + insert)
- [ ] Agent Lightning: SKIP por ahora

---

## [2026-03-25] PM Coordinator — 🟢 DONE — Sesion 20: Simulador IRPF + XSD gaps + 160 deducciones CCAA

### Tareas completadas (8)
1. **Renta imputada multi-inmueble** (Art. 85): imputed_income.py, 18 tests
2. **Compensacion perdidas anteriores** (Art. 48-49): loss_compensation.py, 19 tests
3. **Pension compensatoria ex-conyuge** (Art. 55): reduce base general
4. **Anualidades alimentos hijos** (Art. 64): tributacion separada
5. **Doble imposicion internacional** (Art. 80): deduccion cuota
6. **Discapacidad desc/asc MPYF** (Art. 60.2-3): 3K/12K EUR, 11 tests
7. **Auditoria XSD Modelo 100**: 7 HIGH + 14 MEDIUM + 12 LOW gaps identificados
8. **Auditoria + seed deducciones CCAA**: 160 nuevas (Valencia 40, Madrid 23, Andalucia 17, Canarias 27, Galicia 25, Murcia 28)

### Commits sesion 20
- `97fdd56` feat: imputed income + loss compensation + audit reports
- `e022d4b` feat: 5 XSD gaps + Valencia 40 + Madrid 23 + Andalucia 17
- `96b03a4` feat: Canarias 27 + Galicia 25 + Murcia 28

### Pendiente proxima sesion
- [ ] Ejecutar 6 seeds nuevos en produccion (Turso)
- [ ] Terminar CLM + Asturias + Cantabria (agente no termino por timeout)
- [ ] Seedear Fase 3: Baleares, La Rioja, Extremadura, Aragon, CyL, Cataluna
- [ ] Conectar nuevos params simulador al frontend
- [ ] GP transmision inmuebles (venta propiedad) — gap HIGH pendiente
- [ ] Agent Lightning: SKIP por ahora, re-evaluar con 500+ conversaciones

---

## [2026-03-24] PM Coordinator — 🟢 DONE — Sesion 19: Crawler upgrade + RAG masiva + tax_parameters

### Tareas completadas (8)
1. **Crawler v2**: Scrapling anti-bot, ciclos reintento, --verify-urls, 404 sin backoff
2. **27 URLs BOE corregidas**: 19 CCAA + 8 historicos (Valencia, CDIs, REF, ZEC, estatutos)
3. **20 URLs deprecated**: forales manuales, guias regionales, Seg Social, CDI UK
4. **17 nuevos PDFs descargados**: 13 CCAA regimen comun + Regl IRPF/ISD + Ley Audiovisual + DAC7 + Tributacion Autonomica 2025
5. **Ingesta RAG masiva**: ~4,900 chunks nuevos (Azure DI + OpenAI). DB: 409 docs, 80K chunks, 74K embeddings
6. **tax_parameters seed**: 2024+2025 ejecutado en prod (240 params + 160 ahorro scales). Bug 64 MPYF arreglado
7. **RAG Quality eval timeout fix**: useApi acepta timeout custom, evaluacion 600s
8. **Memorias + SONA**: 5 patrones HNSW, memoria proyecto actualizada

### Commits sesion 19
- `a3679a0` feat: crawler upgrade — Scrapling anti-bot, multi-cycle retry, 27 BOE URLs corrected
- `1e6796d` fix: RAG quality evaluation timeout — extend to 10min for 30-question eval

### Pendiente proxima sesion
- [ ] Ejecutar crawler para descargar 7 PDFs nuevos (Valencia, Ceuta/Melilla estatutos, CDIs, REF, ZEC)
- [ ] Ingestar esos 7 PDFs en RAG
- [ ] Vigilar publicacion Manual Renta AEAT 2025 (~abril 2026)
- [ ] Revisar 2 docs en `docs/_quarantine/`

---

## [2026-03-24] Backend/Frontend — 🟢 DONE — Bug 64: IRPF cálculo ~850€ discrepancia
- **Root cause**: `tax_parameters` solo seeded para 2024, frontend envía year=2025 → MPYF = 0
- **Fix**: Year fallback en TaxParameterRepository + seed 2025 + pagadores en profile/estimate
- **Commit**: `74ac9c4` — pushed to main
- **RESUELTO**: `populate_tax_parameters.py` ejecutado en Turso prod (sesion 19)

## [2026-03-24] Frontend/Backend — 🟢 DONE — Bug 63: RAG Quality Dashboard crash
- **Fix**: `useApi()` retorna `{apiRequest}`, no axios. AdminRagQualityPage usaba `.get()/.post()` inexistentes.
- **Fix**: Backend field names no coincidían con interfaces TS (`timestamp`→`evaluated_at`, etc.).
- **Commit**: `77820a0` — pushed to main

## [2026-03-20] PM Coordinator — DONE — Sesion 17: RuFlo + Security + Features + PDF Export

### Tareas completadas (17)
1. **RuFlo MCP** (~95%): 259 tools, 26 hooks, SONA 5 trayectorias, ReasoningBank funcional
2. **Security cleanup**: filter-repo 3 pasadas, 235 commits reescritos, 0 secretos en historial
3. **Stripe role validation**: UpgradePlanModal en SettingsPage (commit `8440917`)
4. **Calculadora neto**: 22 tildes + neto fiscal real + warning reserva IRPF (commit `c70dea5`)
5. **ReasoningBank**: 2 patches Windows + postinstall automatico (commit `ed6f5dd`)
6. **PDF export completo**: 30+ campos + observaciones chat + tildes (commit `c3aa17c`)
7. **Turnstile bypass QA**: ya implementado, falta env var en Railway
8. **Memorias**: 8 archivos actualizados/creados

### Commits sesion 17
- `ab9a941` security: remove secrets from tracked files
- `8440917` feat: Stripe role validation
- `c70dea5` fix: calculadora neto ortografia + neto fiscal real
- `ed6f5dd` chore: postinstall ReasoningBank patches
- `c3aa17c` feat: PDF export completo
- `718cff0` feat: SEO-GEO creators landing + IVA platform calculator
- `254e35b` security: path traversal fix
- `f0718ec` security: SQL parameterization chat.py
- `6c7505f` feat: security pipeline (Bandit+ZAP+Nuclei+GH Actions)
- `dc6768d` feat: MFA/2FA TOTP
- `52ccb95` feat: Google SSO
- `75e08fe` fix: privacy policy SECURITY.md label
- `18d20ac` fix: Home footer privacy link
- `75d2b48` fix: requirements.txt (deploy fix)
- `905a188` fix: index.html noscript for Google verification
- `3195606` feat: IVA calculator CCAA tax zones
- `e890ca4` fix: zone selector CSS

### Pendiente proxima sesion
- [ ] MFA / 2FA (unica tarea critica restante)
- [x] ~~Rotar API keys (Stitch, Gemini, Google OAuth)~~ — DONE por Fernando
- [x] ~~TURNSTILE_TEST_MODE=True en Railway~~ — DONE por Fernando
- [x] ~~Cambiar passwords expuestos~~ — DONE por Fernando
- [ ] Pipeline auto-ingesta RAG
- [ ] Re-ejecutar crawler 90 URLs

---

## [2026-03-20] PM Coordinator — DONE — Sesion 17 (early): RuFlo MCP Activacion

- **RuFlo MCP activado** tras reinicio de Claude Code
  - 259 tools disponibles via stdio (PID 20724)
  - Todos los componentes healthy: swarm, memory, neural, mcp
  - 26 hooks activos (vs 13 en sesion 16)
  - 4/5 AgentDB controllers: hierarchicalMemory, tieredCache, memoryGraph, memoryConsolidation
  - ReasoningBank deshabilitado (ONNX binding falla en Windows)

- **Intelligence re-bootstrapped**:
  - Pretrain deep: 126 files, 45 patterns, 24 strategies, 69 trajectories
  - 3 patrones HNSW-indexed: architecture, security, frontend
  - 7 entries memoria namespace impuestify + 3 patterns
  - Busqueda semantica verificada: <10ms, HNSW + BM25 hybrid

- **Bug conocido**: `swarm_init` falla en Windows (store interno no persiste entre restarts)
  - Workaround: agentes se crean individualmente via `agent_spawn` (verificado OK)
  - No bloquea funcionalidad real

- **Capacidad RuFlo**: ~85% (subio de 75% en sesion 16)

- **Pendiente**:
  - [ ] ReasoningBank: investigar fix ONNX en Windows o deploy en Railway
  - [ ] swarm_init bug: reportar a ruflo o esperar fix en proxima version

---

## [2026-03-20] PM Coordinator — DONE — Sesion 16: Multi-Pagadores IRPF + RuFlo Setup

- **Feature principal**: Soporte multi-pagadores en perfil fiscal y simulador IRPF
  - PagadorItem model (8 campos, mirrors AEAT Datos Fiscales)
  - Agregacion automatica: pagadores[] → ingresos_trabajo + retenciones + SS
  - Obligacion de declarar (Art. 96 LIRPF): 22.000/15.876 EUR, constantes por ejercicio
  - MultiPagadorForm component (acordeones estilo app AEAT)
  - Integrado en: TaxGuidePage (Step 2 toggle), SettingsPage (seccion pagadores), LiveEstimatorBar (alerta)
  - LLM tool actualizado: irpf_simulator_tool.py con pagadores + num_pagadores
  - Retribuciones en especie + ingresos a cuenta en simulador

- **Archivos creados/modificados (14)**:
  - Backend (5): irpf_estimate.py, user_rights.py, irpf_simulator.py, irpf_simulator_tool.py, test_multi_pagadores.py
  - Frontend (9): MultiPagadorForm.tsx, MultiPagadorForm.css, useFiscalProfile.ts, useIrpfEstimator.ts, useTaxGuideProgress.ts, TaxGuidePage.tsx, SettingsPage.tsx, LiveEstimatorBar.tsx, LiveEstimatorBar.css

- **Tests**: 23 nuevos multi-pagadores PASS, 1199 total backend PASS, frontend build OK

- **RuFlo V3.5**: Instalacion auditada y mejorada
  - npm install ruflo better-sqlite3 sql.js (dependencies instaladas)
  - MCP server configurado en .mcp.json
  - Puente SubagentStart/Stop → swarm-state.json implementado
  - 5 nuevos hook handlers: pre-edit, post-bash, compact-manual, compact-auto, notify
  - Intelligence bootstrapped: 226 entries, 198 edges (PageRank)
  - Auditoria: plans/ruflo-audit-report.md (27% → 55% capacidad)
  - PENDIENTE: habilitar MCP en enabledMcpjsonServers, daemon start, security scan

- **RuFlo mejoras adicionales (misma sesion)**:
  - MCP server configurado en .mcp.json + habilitado en enabledMcpjsonServers
  - Daemon arrancado (PID 8316)
  - Security scan ejecutado (solo passwords QA test users)
  - Router conectado con 10 agentes Impuestify del team YAML
  - Router ADAPTATIVO implementado: scores por (patron, agente), feedback en SubagentStop, persiste en routing-history.json
  - Memoria inter-agente: `npx ruflo memory` funcional (sql.js + HNSW, namespace impuestify)
  - 5 hooks nuevos: pre-edit, post-bash, compact-manual, compact-auto, notify
  - Intelligence graph: 226 entries, 198 edges (PageRank)
  - Capacidad RuFlo: 27% → ~75%

- **Pendiente para proxima sesion**:
  - [ ] Commit + push de todos los cambios (multi-pagadores + ruflo)
  - [ ] Reiniciar Claude Code para activar MCP server de RuFlo (259 tools)
  - [ ] ReasoningBank init (requiere Linux/Railway — ONNX no funciona en Windows)
  - [ ] Arreglar AgentDB controller path warning

## [2026-03-19] PM Coordinator — DONE — Sesion 15: Guia Fiscal Adaptativa por Rol

- **Feature principal**: Guia fiscal (/guia-fiscal) ahora muestra pasos diferentes segun plan del usuario
  - PARTICULAR: 7 pasos (sin actividad economica)
  - CREATOR: 8 pasos (con step dedicado plataformas, IAE, IVA intracomunitario, withholding, M349)
  - AUTONOMO: 8 pasos (con step actividad economica reorganizado)

- **Archivos modificados (6)**:
  - `frontend/src/hooks/useTaxGuideProgress.ts` — userPlan param, 4 configs step labels, campos creator
  - `frontend/src/pages/TaxGuidePage.tsx` — getStepContent(), StepCreadorActividad, resultado adaptativo
  - `frontend/src/pages/TaxGuidePage.css` — estilos creator + obligaciones
  - `frontend/src/hooks/useIrpfEstimator.ts` — campos creator en input
  - `backend/app/routers/irpf_estimate.py` — campos creator opcionales + modelo_349 flag
  - `backend/tests/test_irpf_estimate_creator.py` — 12 tests PASS

- **Research completado**: `plans/user-needs-research-2026.md`
  - Particulares: detector deducciones autonomicas (9.000M EUR perdidos/ano), simulador rapido, conjunta vs individual
  - Autonomos: "cuanto me queda limpio", estimador M130 trimestral, 200h/ano en burocracia
  - Creadores: wizard alta autonomo, IVA por plataforma, DAC7, epigrafe IAE

- **Build**: frontend PASS (6.93s), backend 12/12 tests PASS
- **Pendiente**: commit + deploy

---

## [2026-03-17] PM Coordinator — DONE — Sesion 13 completa

- **Bugs fixeados**: 4 (Bugs 59-62)
  - Bug 59: Calendario fiscal — deadlines solo en mes end_date, no en rango (commit `19935d4`)
  - Bug 60: Meses pasados vacios (vencidos filtrados) (commit `19935d4`)
  - Bug 61: Push notifications "Registration failed" — VAPID keys invalid (commits `3048d9f`, `6f45b3d`, `8e329ce`)
  - Bug 62: `/creadores-de-contenido` redirigía a `/` (commit `dadf58e`)

- **Features nuevas**: 1 capa de seguridad
  - Document Integrity Scanner (Capa 13): 40 patrones ES/EN, 10 categorías, integrado en uploads/crawler/RAG, 55 tests (commits `1fd2835`, `436d009`)

- **Mejoras**:
  - 4 deadlines nuevos para particulares (Modelo 721, 714, cita previa, atención presencial)
  - Migración BD: 4 columnas (integrity_score + integrity_findings)

- **Métricas actualizadas**:
  - Tests: 1138 (55 nuevos DIS)
  - Bugs: 62 documentados
  - Capas seguridad: 13
  - Deadlines: 32 estatal (antes 28)

- **Archivos documentación actualizados**:
  - `plans/ROADMAP.md` — sesion 13 completada, backlog sesion 14 anadido
  - `memory/MEMORY.md` — datos sesion 13, 1138 tests, 13 capas seguridad
  - `memory/bugfixes-2026-03.md` — bugs 59-62 + Document Integrity Scanner
  - `agent-comms.md` — entrada sesion 13

- **QA Status**: Pendiente verificacion manual en navegador (Turnstile bloquea CI/CD). Recomendacion: habilitar token test de Cloudflare en Railway.

- **Siguiente sesion 14**: Validar plan Stripe al cambiar roles, Turnstile bypass para QA automatizado

---

## [2026-03-17] QA Tester — DONE — Sesion 17 post-deploy (commit bc5056a)

- **Tests ejecutados**: 9 (3 PASS, 5 SKIP por Turnstile, 0 FAIL)
- **Reporte**: `plans/qa-report-s17-2026-03-17.md`

- **Bugs nuevos**:
  - B-QA-TURNSTILE-01: Cloudflare Turnstile bloquea login headless en CI — fix del calendario NO verificado
  - B-CREADORES-RUTA-01: `/creadores-de-contenido` redirige a `/` sin pagina dedicada

- **Bugs posiblemente resueltos**:
  - B-LAND-FADE: Screenshots de landing (5 niveles de scroll) no muestran secciones negras — puede estar fixed

- **Para PM**: El fix del calendario (deadlines Modelo 100 Abril, 714 Junio) NO pudo verificarse automaticamente. Requiere verificacion manual en el navegador.

- **Accion recomendada para Developer**: Habilitar token de test Cloudflare (`1x00000000000000000000AA`) en Railway para permitir QA automatizado. Ver `plans/qa-report-s17-2026-03-17.md` seccion "Limitacion principal: Turnstile en CI/CD".

---

## [2026-03-17] Documentation Auditor — DONE — Actualizacion completa documentacion sesion 12 (final)

- **Archivos actualizados**:
  - `memory/MEMORY.md` — indice + datos actualizados (tests 1083+, crawler 90 URLs, bugs 58)
  - `memory/bugfixes-2026-03.md` — bugs 53-58 anadidos (Admin CSS, Calendar, CTA alineacion)
  - `memory/project_upgrade_downgrade.md` — CRITICO: validar plan Stripe compatible al cambiar roles (sesion 13)
  - `memory/feedback_ortografia_pre_push.md` — regla obligatoria verificar tildes
  - `memory/reference_mission_control.md` — dashboard futura para orquestacion 6 agentes
  - `plans/ROADMAP.md` — bugs 53-58, backlog sesion 13 anadido, metricas actualizadas
  - `agent-comms.md` — entrada final sesion 12

- **Resumen sesion 12**:
  - Bugs fixeados: 58 total (documentados en bugfixes-2026-03.md)
  - Features completados: Plan Creator 49 EUR, feedback system, CCAA-aware models, multi-role profiles, push notifications, crawler 90 URLs + drift analyzer
  - Tests: 1083+ backend PASS, frontend build OK
  - Memorias agregadas: 3 nuevos archivos (upgrade/downgrade, ortografia, mission control)

- **Notas criticas**:
  - JWT_SECRET_KEY debe cambiarse en Railway (accion usuario)
  - ORTOGRAFIA PRE-PUSH OBLIGATORIA verificada en feedback rules
  - Feedback system completamente integrado (widget + rating + 3 pages admin)
  - Crawler ahora monitoriza 90 URLs en 23 territorios (fue 54→90)
  - Fecha Renta corregida: 8 de abril (no 2)

- **Pendiente CRITICA sesion 13**: Validar plan Stripe compatible cuando usuario cambia roles (ver memory/project_upgrade_downgrade.md)
- **Pendiente sesion 13**: Diagnosticar error push notifications post-VAPID
- **Siguiente**: Backend/Frontend agent implementar cambios documentados si aun no estan hechos. Verifier debe pasar antes de merge a main

---

## [2026-03-17] Competitive — DONE — Inventario completo modelos fiscales creadores todos los territorios

- **Archivo**: `plans/creators-tax-models-all-territories.md` — 9 secciones, todos los territorios cubiertos
- **Cobertura**: Regimen comun (15 CCAA) + Bizkaia + Gipuzkoa + Araba + Navarra + Canarias (IGIC) + Ceuta/Melilla (IPSI)
- **Hallazgo critico 1**: Gipuzkoa usa modelo **300** (no 303) para IVA trimestral — dato no cubierto en RAG actual
- **Hallazgo critico 2**: Navarra usa modelo **F69** (no 303) para IVA trimestral y **715/759** en lugar de 111/115
- **Hallazgo critico 3**: TicketBAI (PV) y BATUZ (Bizkaia) son obligaciones SIN EQUIVALENTE en regimen comun — no cubiertas en RAG
- **Hallazgo critico 4**: Modelo 349 NO aplica desde Canarias (no son territorio UE para IVA armonizado) — las facturas a Google/Meta desde Canarias son exportacion, no intracomunitaria
- **Hallazgo critico 5**: ZEC solo viable para SL con 3-5 empleados y 50-100K EUR inversion — NO para autonomos creadores tipicos
- **Gaps de RAG identificados**: F69 Navarra, Modelo 300 Gipuzkoa, TicketBAI PV, IGIC 420/425, modelos 721, 715/759 Navarra
- **URLs para crawler**: 25+ URLs nuevas identificadas (AEAT, haciendas forales, Canarias, Ceuta/Melilla)
- **Accion para Backend Agent**: Considerar indexar PDF instrucciones F69 Navarra y modelo 300 Gipuzkoa en RAG
- **Accion para Backend Agent**: Verificar si modelos 420 IGIC y IPSI Ceuta/Melilla estan cubiertos en calendario fiscal del sistema

---

## [2026-03-16] Competitive — DONE — Actualizacion datos mercado creadores Q1 2026

- **Archivo**: `plans/creators-market-update-2026-Q1.md` — 14 secciones, datos actualizados con fuentes
- **Hallazgo critico 1**: TaxDown ya no es startup — 4M usuarios, >10M EUR facturacion, rentable. Mucho mas grande de lo esperado.
- **Hallazgo critico 2**: Plan control tributario AEAT 2026 incluye influencers como objetivo prioritario — catalizador de urgencia para nuestro mercado
- **Hallazgo critico 3**: DAC7 Modelo 238 ya presentado en enero 2026 — Hacienda tiene datos de plataformas de 2025
- **Hallazgo critico 4**: VeriFactu para autonomos prorrogado a 1 julio 2027 (antes teniamos dato incorrecto de julio 2025)
- **Hallazgo critico 5**: Inversion influencer marketing ES: 158M EUR en 2025 (vs 125,9M en 2024, +25,9%)
- **Hallazgo critico 6**: 285.000 influencers activos con >10K seguidores (IAB Spain III edicion) — mercado potencial mucho mayor
- **Dato confirmado**: Ningun nuevo competidor IA fiscal detectado en Q1 2026

---

## [2026-03-16] Competitive — DONE — Research pricing y modelo de negocio segmento Creadores / Emprendedores Digitales

- **Archivo**: `plans/creators-pricing-research-2026.md` — 8 secciones, pricing verificado, propuesta concreta
- **Mercado**: 235.000 creadores activos en Espana, 207.000 con ingresos declarables, SAM ~40.000 dispuestos a pagar herramienta digital
- **Competidor clave**: OnlyTax (70 EUR + IVA/mes, sin IA, sin forales) — lider del nicho pero precio fuera de small creators
- **Hallazgo clave 1**: Ninguna herramienta automatiza el Modelo 349 para YouTubers/creadores — gap enorme y buscado en Google
- **Hallazgo clave 2**: Calculo withholding tax W-8BEN de Google — nadie lo automatiza en Espana
- **Hallazgo clave 3**: Epigrafes IAE para creadores son una fuente de confusion — quick win para el chatbot IA
- **Propuesta**: Plan Autonomo + Modulo Creador a 49 EUR/mes (+10 EUR sobre Plan Autonomo base)
- **Nombre recomendado**: "Plan Creator"
- **TAM**: 70.56M EUR/ano | SAM: 23.52M EUR/ano | SOM 3 anos: 0.7-1.2M EUR/ano
- **Roadmap**: Fase 1 (abril 2026): quick wins en chatbot RAG — Fase 2 (mayo-junio): modulo completo + pricing activo

---

## [2026-03-16] Competitive — DONE — Research exhaustivo creadores de contenido y emprendedores digitales (sesion anterior)

- **Archivo**: `plans/creators-entrepreneurs-research-2026.md` — 11 secciones, datos verificados con fuentes
- **Mercado**: 15.000+ creadores con >100k seguidores en Espana; 50.000-150.000 potenciales usuarios de Impuestify
- **Competidor clave del nicho**: OnlyTax (~70 EUR/mes, lider de mercado, sin IA, sin cobertura foral)
- **Hallazgo clave 1**: OnlyTax domina el nicho de creadores en Espana pero NO tiene IA — ventana de diferenciacion enorme
- **Hallazgo clave 2**: Ni OnlyTax ni nadie cubre al creador de contenido FORAL (vasco, navarro) con herramientas digitales
- **Hallazgo clave 3**: La casuistica de IVA por plataforma (Google Ireland, TikTok UK, OnlyFans UK) es compleja y nadie la automatiza
- **Hallazgo clave 4**: Consultas DGT criticas identificadas: V0773-22, V2390/2024, V2428-25 — PENDIENTE indexar en RAG
- **Hallazgo clave 5**: CNAE-2025 (RD 10/2025 enero 2025) reconoce oficialmente a creadores — nuevo codigo 60.39
- **Hallazgo clave 6**: VeriFactu obligatorio para autonomos en julio 2027 — modulo de facturacion necesario
- **URLs crawler**: 25+ URLs oficiales identificadas (DGT, AEAT, BOE, Haciendas Forales, Canarias)
- **Proximos pasos**: (1) Indexar PDFs/docs DGT en RAG, (2) Landing SEO creadores, (3) Calculadora IVA por plataforma

---

## [2026-03-16] PM — DONE — TikTok integrado en estrategia Social Media

- **Estrategia actualizada**: `plans/social-media-strategy-2026.md` — seccion 3C TikTok completa, calendario semanal 3 canales (12 piezas/semana), timeline, metricas, UTMs
- **Research**: `plans/tiktok-research-2026.md` — 9 secciones con fuentes verificadas
- **Roadmap actualizado**: `plans/ROADMAP.md` — TikTok integrado en entrada Social Media
- **Memoria actualizada**: `memory/project_social_media.md` — 3 plataformas documentadas
- **Prioridad canales**: Instagram #1 > LinkedIn #2 > TikTok #3
- **Pendiente Fernando**: Crear cuenta @impuestify en TikTok (Business Account) + primeros 3 videos semana 24-28 marzo
- **Tambien en esta sesion**: Crawler reconfigurado a lunes 09:00 (Task Scheduler). Fernando debe marcar "Run whether user is logged on or not" en taskschd.msc

---

## [2026-03-16] Competitive — DONE — TikTok research exhaustivo completado

- **Archivo**: `plans/tiktok-research-2026.md` — 9 secciones, datos verificados con fuentes
- **Veredicto**: SI a TikTok, prioridad MEDIA-ALTA, empezar en abril 2026 (apertura Campana Renta)
- **Hallazgo clave 1**: 23,4M usuarios en Espana (H1 2025), 70% mayores de 25 — publico objetivo presente
- **Hallazgo clave 2**: Nicho fiscal en TikTok practicamente vacio — TaxDown tiene presencia inconsistente
- **Hallazgo clave 3**: Hacienda lanzo campana TikTok en febrero 2026 — valida el canal para contenido fiscal
- **Hallazgo clave 4**: Contenido foral (Pais Vasco, Navarra) es territorio VIRGEN en TikTok — nadie lo hace
- **Riesgo**: DSA Europa — TikTok sancionado preliminarmente (feb 2026), riesgo de ban bajo pero riesgo de cambios al algoritmo medio
- **No hacer**: No subir Reels de Instagram con watermark — TikTok penaliza activamente
- **Ads**: Esperar hasta tener base organica y validacion de conversion
- **Memoria actualizada**: `.claude/agent-memory/competitive-intel/MEMORY.md`

---

## [2026-03-15] PM — DONE — Estrategia Social Media completa y verificada

- **Estrategia global**: `plans/social-media-strategy-2026.md` — 12 secciones, 7 pilares, LinkedIn + Instagram
- **Plan contenido 6 semanas**: `plans/social-media-content-plan-2026-Q1.md` — 10 posts completos + 15 guiones Reels
- **4 carruseles PDF+PNG**: L2 (deducciones autonomos), L4 (guia IRPF), L7 (errores renta), L8 (calendario fiscal) en `social_media/carruseles/`
- **9 screenshots producto**: `social_media/screenshots/` — landing, subscribe, forales, Ceuta/Melilla, Canarias
- **Carousel generator**: `backend/scripts/carousel_generator.py` — generador Pillow con paleta Impuestify
- **Pendiente usuario**: Setup Metricool, optimizar perfil LinkedIn Fernando, crear Company Page, estructura Google Drive
- **Timeline**: Primer post LinkedIn 21 marzo, primer Reel Instagram 22 marzo, campana Renta desde 8 abril

---

## [2026-03-13] QA — DONE — QA flujo suscripciones produccion (qa-report-2026-03-13.md)

- **5/7 tests PASS**, 2 FAIL (ver reporte completo en `plans/qa-report-2026-03-13.md`)
- **B-SUB-01 (MAYOR)**: `/subscribe` muestra "Crear cuenta" (link a /register) para usuarios autenticados — deberia iniciar checkout Stripe. Gap critico en funnel de conversion para usuarios con cuenta sin suscripcion.
- **B-LAND-FADE (REGRESION)**: Landing secciones intermedias siguen negras sin scroll en headless — fue marcado como FIXED en sesion 15 pero se reproduce. Impacto SEO.
- **Cloudflare Turnstile**: Bloquea login automatizado en produccion. Tests que requieren auth no pudieron ejecutarse. Recomendacion: bypass via API directa para staging.
- **Lo que funciona bien**: /subscribe carga ambos planes y precios correctos, proteccion de rutas OK, 0 errores JS de consola, 0 requests 5xx.
- Screenshots en `tests/e2e/screenshots/sub-*.png`

---

## [2026-03-13] PM — DONE — seed_deductions_xsd.py ejecutado en Turso produccion

- 339 deducciones XSD Modelo 100 AEAT insertadas (15 CCAA)
- 0 errores, idempotente (DELETE existing + INSERT fresh)
- Tarea pendiente desde 2026-03-08, ahora completada

---

## [2026-03-13] PM — DONE — Bugs 49-52: 4 bugs beta testers (Commit b148564)

- **Bug 52** (Jose Antonio Alvarez): Password reset no enviaba email — dominio `.es` → `.com` en 6 archivos. Resend rechazaba dominio no verificado. **Pendiente usuario**: cambiar `RESEND_FROM_EMAIL` en Railway.
- **Bug 50** (Juan Pablo Sanchez): Workspaces loading infinito — AbortController+timeout en useApi, request ID en useWorkspaces, NULL guard en workspaces.py
- **Bug 49** (Ramon Palomares): NotificationAgent verboso — system prompt answer-first, eliminado doble formateo
- **Bug 51** (Juan Pablo Sanchez): Comparativa conjunta vs individual incompleta — loop tool_calls + instrucción comparativa en system prompt
- **Tests**: 1009 PASS, frontend build OK
- **Deploy**: pushed `b148564` to main, Railway auto-deploy

---

## [2026-03-12] PM — DONE — Bug 47+48: CCAA deductions + Cataluña scales

- **Bug 47 (3 sub-bugs)**: territory name mismatch, edad→menor_XX_anos, alquiler_pagado_anual=0
  - Commit: `d61b69b`
- **Bug 48**: `"cataluna"` faltaba en CCAA_NORMALIZATION → "No scale found for Cataluna"
  - Commit: `1bf61ac`
- **QA 5 territorios**: 35/35 PASS (Aragón, Cataluña, Canarias, Gipuzkoa, Melilla)
  - Aragón: A pagar 250€, ARG-ARRENDAMIENTO-VIV 300€
  - Cataluña: A pagar 2.444€, tipo medio 28.52%
  - Canarias: A pagar 519€, CANA-ALQUILER-VIV 600€
  - Gipuzkoa: Devolver 8.500€ (mínimos forales > cuota, correcto)
  - Melilla: Devolver 2.108€, deducción 60% = 3.588€
- **Test script**: `tests/qa-territories.mjs` reutilizable

---

## [2026-03-11] PM — DONE — Ortografia + dropdown CSS + seed foral calendario

- **27 tildes corregidas** en 12 archivos frontend (autonomo, nomina, declaracion, estimacion, metodo, calculo, situacion, numero, regimen)
- **Dropdown CSS oscuro**: `select.form-input option` con fondo #1e293b en SettingsPage
- **Seed foral ejecutado**: 26 fechas forales 2026 en produccion Turso (Gipuzkoa 8, Bizkaia 5, Araba 5, Navarra 8)
- **Total calendario**: 58 fechas 2026 (32 estatales + 26 forales)
- **Guia fiscal fix**: StepInversiones + reindex switch cases + hasIncome guard para salario_base_mensual
- **Deploy**: push main `b2079eb`, Railway auto-deploy OK
- **Nota**: deploy anterior fallo con "Error configuring Network" (transitorio Railway, no es bug de codigo)
- Commits: `2dd09ff`, `8f077d3`, `b2079eb`

---

## [2026-03-11] PM — DONE — Fix 2 bugs reportados por Ramon Palomares (beta tester)

- **Bug 1 (CRITICO): slowapi crash 500** en `/api/irpf/estimate` y `/api/irpf/deductions/discover`
  - Causa: parametro `req: Request` en vez de `request: Request` — slowapi no lo encontraba
  - Fix: renombrar `req` → `request`, body Pydantic `request` → `body` en `irpf_estimate.py`
- **Bug 2 (ALTO): JWT 401 en chat SSE** sin auto-refresh
  - Causa: `useStreamingChat.ts` usa `fetch()` directo, no pasa por interceptor Axios de refresh
  - Fix: anadir logica de refresh JWT en `useStreamingChat.ts` (retry con nuevo token o redirect a login)
- **Pendiente**: Deploy a Railway para que Ramon pueda verificar el fix

---

## [2026-03-11] PM — DONE — Admin: botón activar/revocar beta + 3 bugs QA + email toggle + seed + deploy

- **Admin beta**: PUT grant-beta / revoke-beta en admin.py + botones en AdminUsersPage (verde/rojo)
- **B-GF-ESTIMATOR fix**: campos crypto/trading añadidos al hasIncome check del estimador
- **B-LAND-PLAZOS fix**: getShortName muestra nombre completo del modelo fiscal
- **B-MODELOS-RUTA**: no era bug de codigo, resuelto con deploy
- **Email alerts toggle**: seccion en SettingsPage tab Notificaciones (POST /api/deadlines/email-alerts/toggle)
- **Seed produccion**: 28 fechas estatal 2026 insertadas en Turso
- **Deploy**: push a main (526f955), Railway auto-deploy
- **Beta tester**: Ramon Palomares (ramonpalom@hotmail.com) activado hasta 31/12/2026

---

## [2026-03-11] PM — DONE — Módulo Criptomonedas, Trading y Apuestas completo

- **Plan RPI**: `plans/plan_crypto_trading_apuestas.md` — 20 tareas, 7 fases, verificado por plan-checker
- **Backend (14 archivos)**:
  - `fiscal_fields.py`: 3 secciones alineadas XSD Modelo 100 (casillas 1800-1814, 0281-0297, 0316-0354)
  - `user_rights.py`: ~25 campos nuevos en FiscalProfileRequest + GDPR delete crypto tables
  - `crypto_fifo.py`: calculadora FIFO con antiaplicación Art. 33.5.f (61 días)
  - `crypto_parser.py`: 5 exchanges (Binance, Coinbase, Kraken, KuCoin, Bitget)
  - `crypto.py`: router REST 5 endpoints (upload, transactions, holdings, gains, delete)
  - `crypto_gains_tool.py` + `crypto_csv_tool.py`: tools para TaxAgent
  - `irpf_simulator.py` + `savings_income.py`: integración cripto/trading/apuestas en simulador
  - `deduction_service.py`: bridge perfil → deduction answers actualizado
  - `irpf_simulator_tool.py` + `irpf_estimate.py`: parámetros crypto/trading/apuestas
  - `migrate_fiscal_fields_crypto.py`: migración campos renombrados
- **Frontend (8 archivos)**:
  - `CryptoPage.tsx` + `.css`: upload, 3 tabs, alerta Modelo 721
  - `useCrypto.ts`: hook API crypto
  - `TaxGuidePage.tsx`: nuevo paso "Inversiones y cripto"
  - `DynamicFiscalForm.tsx`: soporte option_labels en select
  - `SubscribePage.tsx` + `Home.tsx`: "Criptomonedas, trading y apuestas (FIFO)" en features
- **Tests**: 140 nuevos (27 FIFO + 66 parser + 29 router + 17 integración) — 998 total, 0 fail
- **Commit**: `91faf01`
- **Pendiente**: Deploy a Railway

---

## [2026-03-10] Backend — DONE — Calendario fiscal completo + email reminders

- **28 fechas estatales** hardcodeadas (seed_estatal_deadlines.py): todos los trimestrales (303, 130, 131, 111, 115), anuales (180, 190, 390, 347, 720), Renta (100), Sociedades (200), 2do plazo
- **Email reminders autonomos**: 30 dias antes de vencimiento, opt-in via perfil
- **Endpoints nuevos**: POST /api/deadlines/email-alerts/toggle + GET /status
- **BD**: columna deadline_email_alerts en user_profiles
- **Cron actualizado**: push + email en paralelo
- **858 tests PASS**
- Commit: `a849ce1`
- **Pendiente**: Ejecutar `seed_estatal_deadlines.py --year 2026` en produccion (Railway)
- **Pendiente frontend**: Boton toggle email alerts en perfil/calendario

---

## [2026-03-10] PM — DONE — Estrategia Social Media Impuestify (completada 2026-03-15)

**Plan completo**: `plans/social-media-strategy-2026.md` + `plans/social-media-content-plan-2026-Q1.md`
**Assets generados**: 4 carruseles en `social_media/carruseles/`, 9 screenshots en `social_media/screenshots/`
**Estado**: COMPLETO — todos los entregables creados. Pendiente ejecucion por Fernando.

---

## [2026-03-09] QA — NEEDS_REVIEW — Sesion 15: QA Exhaustivo post-commit c608ac6

### Resultado: 13 PASS / 0 FAIL / 1 FLAKY — 4 bugs nuevos, 3 bugs corregidos confirmados

**Reporte completo**: `plans/qa-report-s15-2026-03-09.md`
**Script**: `tests/e2e/qa-s15-exhaustivo-2026-03-09.spec.ts`

**BUGS CORREGIDOS CONFIRMADOS EN PRODUCCION:**
1. B-GF-BLANK: /guia-fiscal ya NO es pantalla negra — wizard renderiza titulo, tabs, select CCAA, inputs — PASS
2. B-MOD-PERSIST (parcial): Modal onboarding cierra al enviar 1er mensaje — OK. Pero modal IA aparece en su lugar (ver B-MOD-IA-PERSIST)
3. B-LAND-FADE: Landing secciones negras — RESUELTO, FadeContent funciona con scroll
4. B13 (hamburger mobile): Menu mobile ahora muestra Chat, Guia Fiscal, Modelos, Calendario, Configuracion, Historial — RESUELTO

**BUGS NUEVOS (accion requerida):**

1. **B-MOD-IA-PERSIST (ALTO)**: Al enviar el 1er mensaje el modal onboarding cierra (correcto) pero el modal "Sistema de Inteligencia Artificial" aparece inmediatamente despues, bloqueando la vista de la respuesta del chat. El usuario nuevo no puede ver la respuesta a su primer mensaje. Fix: cerrar tambien el modal IA al enviar primer mensaje, o mostrar ambos modales en secuencia ANTES de permitir envio de mensajes.

2. **B-MODELOS-RUTA (ALTO)**: Nav link "Modelos" en header (desktop y mobile) navega a la landing page de marketing, no a la pagina de formularios trimestrales. El usuario autonomo no puede acceder a 303/130 desde el nav. Verificar ruta correcta (/declarations o similar) y corregir el Link en el header.

3. **B-GF-ESTIMATOR (MEDIO)**: LiveEstimatorBar no actualiza en tiempo real cuando el usuario introduce ingresos en el wizard. Solo muestra "Introduce tus datos para ver la estimacion". Deberia actualizar al cambiar valores para mostrar estimacion progresiva.

4. **B-LAND-PLAZOS (BAJO)**: Widget "Proximos plazos fiscales" en landing (sin login) muestra pills con dias restantes pero sin nombre del modelo fiscal. Falta descripcion junto al countdown.

**DECISION DE PRODUCTO PENDIENTE:** /guia-fiscal ahora carga para plan `particular` (antes redirigía a /subscribe). Confirmar si es intencional.

**Para PM:** Prioridad: B-MODELOS-RUTA (bloquea funcion core autonomo) > B-MOD-IA-PERSIST (UX critica primer uso) > B-GF-ESTIMATOR (UX wizard) > B-LAND-PLAZOS (cosmético).

---

## [2026-03-09] QA — NEEDS_REVIEW — Sesion 14: QA Exhaustivo post-commit 55bfbc2

### Resultado: 9 PASS / 1 FAIL / 2 PARTIAL — 2 bugs criticos nuevos

**Reporte completo**: `plans/qa-report-s14-2026-03-09.md`
**Script**: `tests/e2e/qa-s14-exhaustivo-2026-03-09.spec.ts`

**BUGS CRITICOS (accion inmediata):**

1. **B-GF-BLANK (CRITICA)**: `/guia-fiscal` renderiza pantalla completamente negra. URL carga OK, no redirige, pero el wizard no muestra ningun contenido. Screenshot: `s14-F5-01-guia-entrada.png`. Afecta todos los usuarios con acceso a Guia Fiscal.

2. **B-MOD-PERSIST (ALTO)**: Modal onboarding "Bienvenido, [nombre]" persiste mientras el usuario escribe/envia mensajes. El usuario no puede VER las respuestas del asistente. El chat funciona en background pero la UX es inutilizable. Fix: cerrar modal al enviar primer mensaje.

**FIXES CONFIRMADOS EN PRODUCCION (sesion 14):**
- B-LOGOUT-01: Logout directo sin window.confirm — OK
- B-GUARD-01: Guardrail no bloquea IRPF basico para particulares — OK
- B-MOB-01: Modales NO apilados en mobile — OK

**Para PM:** B-GF-BLANK es urgente — investigar TaxGuidePage en produccion (pantalla negra).

---

## [2026-03-09] PM — DONE — Crawler automatizado (doc_crawler module) — Commit 250e8a2

**Archivos creados (13 files, 1971 lines):**
- `backend/scripts/doc_crawler/` — 9 modulos Python + run_check.bat + setup_scheduler.py
- `backend/tests/test_doc_crawler.py` — 32 tests, todos PASS
- `plans/crawler-automation-plan.md` — Plan verificado por plan-checker

**Capacidades:**
- 48 URLs monitorizadas (25 alta prioridad, 19 media, 4 baja) en 21 territorios
- Descarga con rate limiting (4s inter-request, 50/dominio/sesion, backoff exponencial)
- robots.txt check, validacion PDF/Excel, deduplicacion SHA-256
- CLI: `python -m backend.scripts.doc_crawler [--territory X] [--dry-run] [--check-new] [--pending] [--stats]`
- Genera `_pending_ingest.json` para futuro pipeline RAG
- Manual Renta 2025 AEAT en watchlist como "future" (monitorizara cuando se publique)

**Windows Task Scheduler:**
- Tarea: `TaxIA-DocCrawler-Weekly` — lunes 09:00
- Metodo: XML import (resuelve paths con espacios en OneDrive)
- Setup: `python -m backend.scripts.doc_crawler.setup_scheduler [--remove] [--check] [--day MON] [--time 09:00]`
- Wrapper: `run_check.bat` (PYTHONUTF8=1, cd relativo con %~dp0)

**Para CRAWLER:** La watchlist tiene ~48 URLs iniciales. Expandir gradualmente en sesiones futuras de /crawl.
**Para BACKEND:** Cuando `_pending_ingest.json` exista, considerar script de re-ingesta RAG automatico.

---

## [2026-03-09] QA — DONE — Sesion 11: Regresion post-fix (commits ca3e9f4 + 60d23f2)

**Metodologia:** Analisis estatico de codigo + script E2E generado
**Reporte:** `plans/qa-report-regression-2026-03-09.md`
**Script:** `tests/e2e/regression-2026-03-09.spec.ts`

**Resultados por analisis de codigo:**
- B-TOOL-01 FIXED: `ingresos_trabajo: float = 0` confirmado en `irpf_simulator_tool.py:251`
- B-GF-06 FIXED: `canProceed()` y `canGoToStep()` confirmados en `TaxGuidePage.tsx:1185-1202`
- B-GF-01 FIXED: div `.tax-guide__header` con h1 confirmado en `TaxGuidePage.tsx:1208`
- B-LOGOUT-01 FIXED: `handleLogout` sin window.confirm confirmado en `Header.tsx:18-21`

**Requieren ejecucion de tests para confirmar:**
- B-LAND-01, B-GUARD-01, B-CHAT-01, B-MOB-01, B-COOK-01
- B-TOOL-02: fix de codigo confirmado (year=2026), verificar seed de BD en produccion

**Para PM:** Ejecutar `npx playwright test tests/e2e/regression-2026-03-09.spec.ts --workers=1`

---

## [2026-03-09] PM — DONE — Fix 10 bugs QA (2 commits: ca3e9f4 + 60d23f2)

**Commit 1 (ca3e9f4) — 4 bugs criticos:**
1. B-LAND-01 FIXED: FadeContent check viewport on mount
2. B-GUARD-01 FIXED: content_restriction keywords action-specific
3. B-TOOL-01 FIXED: simulate_irpf_tool ingresos_trabajo optional
4. B-TOOL-02 FIXED: RETA 2026 seeded + default year 2026

**Commit 2 (60d23f2) — 5 bugs mayores/menores:**
5. B-CHAT-01 FIXED: validate_output_format no reemplaza respuesta
6. B-GF-06 FIXED: canGoToStep bloquea resultado sin CCAA+ingresos
7. B-MOB-01 FIXED: modales secuenciales (no apilados)
8. B-LOGOUT-01 FIXED: logout directo sin window.confirm
9. CcaaTip foral: array includes() en vez de startsWith()

B-COOK-01 (cookie buttons): NO es un bug real — vanilla-cookieconsent genera sus propios botones, el test usaba selectores incorrectos.

QA regresion en curso...

---

## [2026-03-08] PM — DONE — Fix 4 bugs QA criticos (B-LAND-01, B-GUARD-01, B-TOOL-01, B-TOOL-02)

1. **B-LAND-01 FIXED**: FadeContent.tsx — check viewport on mount, not just on scroll
2. **B-GUARD-01 FIXED**: content_restriction.py — keywords action-specific (no educational blocks)
3. **B-TOOL-01 FIXED**: irpf_simulator_tool.py — ingresos_trabajo optional (default 0)
4. **B-TOOL-02 FIXED**: RETA 2026 seeded (45 records) + default year updated to 2026

Tests: 763 PASS | Frontend build OK | Turso seeded

---

## [2026-03-08] QA — NEEDS_REVIEW — Sesion 10: QA E2E Exhaustivo — 3 bugs criticos detectados

### Resumen: 31 PASS / 4 FAIL / 5 WARN — 10 bugs totales

**BUGS CRITICOS (requieren atencion inmediata):**

1. **B-LAND-01**: Landing con secciones invisibles (negro sobre negro). Solo visible: hero + 3 stats + footer. Features, pricing, comparativa desaparecidos visualmente. Impacta conversion. Screenshot: `tests/e2e/screenshots/S10-T06-landing-desktop.png`

2. **B-GUARD-01**: Guardrail bloquea "¿Que es el modelo 303?" para plan particular. Clasifica info general como "consulta de autonomo". Usuario ve mensaje de bloqueo inapropiado. Archivo a revisar: `backend/app/agents/coordinator_agent.py` o guardrails.

3. **B-TOOL-02**: Tool RETA sin datos para 2026. `calculate_autonomous_quota` devuelve "No encontre informacion de cotizacion para ingresos de 2500€/mes en 2026". Los autonomos no pueden calcular su cuota. Urgente — estamos en 2026.

**BUGS MAYORES:**

4. **B-TOOL-01**: `simulate_irpf_tool() missing 1 required positional argument: 'ingresos_trabajo'` — Error Python visible al usuario. Intermitente. Ocurre cuando la IA llama simulate_irpf sin datos de ingresos como paso previo al lookup_casilla.

5. **B-CHAT-01**: Modelo 303 para autonomo devuelve "hubo un problema al formatear la respuesta" — error de sistema.

6. **B-GF-06**: Confirmado. Wizard Guia Fiscal permite llegar al resultado con campos vacios. Muestra "Completa los pasos anteriores" en lugar de resultado.

**Reporte completo:** `plans/qa-report-e2e-2026-03-08.md`
**Spec del test:** `tests/e2e/qa-session10-exhaustivo-2026-03-08.spec.ts`

---

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
- **Login owner fernando.prada@proton.me:** FALLA — password incorrecto o problema de cuenta

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
