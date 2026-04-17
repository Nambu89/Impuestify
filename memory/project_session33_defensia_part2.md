---
name: project_session33_defensia_part2
description: Sesion 33 DefensIA Parte 2 — Wave 2B Backend + Wave 1F/2F Frontend + Wave 3 parcial + 2 rondas Copilot + 5 gap fixes funcionales end-to-end
type: project
---

# Sesion 33 — DefensIA Parte 2 (2026-04-15)

Rama: `claude/defensia-v1` (62 commits ahead de main, sin mergear aún).

## Resumen ejecutivo

Sesion enorme que cierra el pipeline end-to-end de DefensIA. Partiamos de
Wave 1 Backend + 30 reglas (sesion 32, commit `873e9df`) y cerramos con:

- **Wave 2B Backend** completa: rate limits, storage AES-GCM + zstd, quota
  reserve-commit-release, RAG verifier, writer + 9 plantillas Jinja2, export
  DOCX/PDF, service fachada, agent, router 13 endpoints.
- **Wave 1F + 2F Frontend** completas: Vitest + RTL + jsdom instalado, 15
  tasks T1F (types, 7 components, 3 hooks, 3 pages, Header, App.tsx, useSEO)
  + 6 tasks T2F (3 hooks SSE, EscritoEditor Tiptap, PreExportModal, DefensiaChat).
- **Wave 3 parcial**: T3-002 audit ortografia (script + fix 87 tildes en 9
  plantillas), T3-003 GDPR cascade delete 7 tablas, T3-004 dead code, T3-005
  anti-hallucination audit. T3-001 E2E Playwright diferido (requiere fixtures
  anonimizadas caso David).
- **Copilot review round 1**: 9 comentarios reales (7 bugs CRITICAL).
- **Copilot review round 2**: 7 comentarios (3 bugs CRITICAL).
- **Security GitHub Actions**: Bandit B701 silenciado (false positive —
  markdown no HTML), axios CVE (SSRF + metadata exfiltration) parcheado.
- **Dark theme refactor**: 11 CSS rehechos al design system del proyecto.
- **5 gap fixes funcionales end-to-end**: pipeline real ya funcional
  (upload → Fase 1 auto → brief → analyze SSE → dictamen + escrito).

## Metricas

- **Commits**: 62 desde main
- **Backend defensia tests**: 375 verdes
- **Frontend tests**: 92 verdes, build 7s
- **Copilot comentarios resueltos**: 16/16
- **Security scans**: Bandit 0 HIGH, npm audit 0 CRIT/HIGH

## Gaps funcionales tapados (los mas importantes)

### 1. Fase 1 auto-extraccion en upload (`84a945a`)

**Antes**: POST /documentos solo cifraba bytes. El usuario subia PDF y el
wizard paso 3 quedaba eternamente en "Analizando los documentos..." porque
nadie ejecutaba el classifier, extractor ni phase detector.

**Fix**: helper `_run_fase1_auto()` en el router que ejecuta:
1. extract_pdf_text_plain (para texto al classifier)
2. DocumentClassifier.classify_text (regex rapido + Gemini fallback)
3. Extractor especifico segun tipo (Gemini Vision) via asyncio.to_thread
4. Persiste tipo + confianza + fecha_acto + datos_estructurados_json
5. Relee todos los docs del expediente y corre detect_fase
6. Persiste fase_detectada + fase_confianza en defensia_expedientes

Best-effort: cualquier fallo se loggea con warning pero NO tumba la
request. Regla #1 del producto preservada: NO dispara reglas juridicas ni
RAG ni writer aqui.

### 2. Cuota maxima para plantilla TEAR (`f372ca5`)

**Antes**: `cuota_estimada_eur=0.0` hardcoded con TODO. El writer usa
umbral 6000 EUR (Art. 245 LGT) para decidir TEAR abreviada vs general.
Con 0.0 siempre elegia abreviada aunque la liquidacion fuese de 50k EUR.

**Fix**: `_extraer_cuota_maxima()` recorre `documentos[*].datos` buscando
campos canonicos (cuota, cuota_propuesta, cuota_tributaria,
importe_sancion, importe_total, total_a_ingresar) y devuelve el maximo.

### 3. Wizard paso 3 SET_FASE nunca dispatchado (`87885bb`)

**Antes**: Aunque el backend (tras commit `84a945a`) devolvia fase_detectada
en la response del upload, el wizard no lo leia. El paso 3 quedaba en el
placeholder de spinner.

**Fix**: useDefensiaUpload tipa la response como `UploadResponse` con
fase_detectada. Wizard.handleFileSelected dispatch SET_FASE si viene y
no es INDETERMINADA.

### 4 y 5. Wizard paso 4 sin POST brief + paso 5 sin llamar analyze (`fe8b283`)

**Antes**: El brief vivia solo en el state del wizard, nunca se POSTeaba.
Y el paso 5 "Analizar expediente" solo hacia navigate sin llamar al
endpoint analyze. El backend nunca arrancaba el pipeline de reglas + RAG
verifier + writer. El usuario llegaba al expediente con borrador vacio.

**Fix**:
- Paso 4 -> 5: POST /api/defensia/expedientes/:id/brief antes de avanzar.
- Paso 5: useDefensiaAnalyze.analyze con callbacks de progreso textual
  (onPhase, onCandidatos, onVerificando, onDictamen, onEscrito). El UI
  muestra el estado en tiempo real. onDone navega al expediente.

## Pipeline end-to-end funcional

```
Upload PDF
  → classifier (regex/Gemini)
  → extractor (Gemini Vision) → datos estructurados
  → phase_detector recalcula fase
  → UI wizard paso 3 muestra fase real

Brief + Analyze
  → POST /brief persiste texto
  → POST /analyze SSE:
    ├─ reserve cuota atomica (check-and-increment)
    ├─ rules engine 30 reglas
    ├─ RAG verifier descarta <0.7
    ├─ extraer cuota maxima → plantilla TEAR correcta
    ├─ writer render_escrito + render_dictamen
    └─ persist dictamen + escrito
  → onDone navigate /defensia/:id
  → ExpedientePage muestra tabs Resumen/Argumentos/Escrito/Chat
```

## Copilot review — resolucion

### Round 1 (9 comentarios / 7 bugs CRITICAL)

1. **rules_engine**: @regla aceptaba enums pero comparaba strings → R001/R002/R009 nunca se disparaban. Fix: normalizar con `.value` en el decorador.
2. **phase_detector PROPUESTA_SANCION → IMPUESTA**: expedientes en tramite marcados como sancion firme. Fix: mantener PROPUESTA hasta ACUERDO_IMPOSICION.
3. **phase_detector naive datetime**: TypeError al restar fecha naive vs aware. Fix: normalizar a UTC en detect_fase.
4. **writer REPOSICION_INTERPUESTA → reclamacion_tear**: plantilla equivocada. Fix: mapear a recurso_reposicion.j2.
5. **recurso_reposicion.j2 loop.index0**: renderizaba "0 bis.-". Fix: loop.index (1-based).
6. **turso_client solo aplicaba 1 de 3 migraciones**: storage y quota nunca persistidas en prod. Fix: wire inline de los 3 migraciones + idempotencia.
7. **storage _disabled inconsistente** con docstring.
8. **quota reserva_id no idempotente**: doble commit movia contador N veces. Fix: tracking en _reservas_activas dict.
9. **quota race multi-worker**: TOCTOU entre workers. Fix: UPDATE condicional atomico con rowcount check.

### Round 2 (7 comentarios / 3 bugs CRITICAL)

1. `_row_exists` sin uso en fake DB — cleanup.
2-3. **quota commit/release user_id mismatch**: podia consumir tokens de otro user. Fix: validar stored_user == user_id ANTES del pop.
4-7. **migrations fail-fast**: errores no idempotentes se tragaban con warning. Fix: helper `_apply_defensia_migration()` que re-lanza sobre cualquier error distinto de duplicate column.

## Security GitHub Actions

1. **Bandit B701 false positive**: `autoescape=False` en writer Jinja2 es intencional (markdown, no HTML). Silenciado con `# nosec B701`.
2. **axios CVE**: SSRF via NO_PROXY Hostname Normalization Bypass + Cloud Metadata Exfiltration via Header Injection Chain. `npm audit fix` → 0 CRIT/HIGH.

## Dark theme CSS refactor

11 archivos CSS de DefensIA estaban escritos en tema claro (bg #fff, text
#0f172a) mientras el resto del proyecto usa dark theme coherente. Refactor
con los mismos tokens que CalculadoraUmbrales.css (referencia canonica):

- Page bg: `var(--color-secondary, #0f172a)`
- Card bg: `rgba(255,255,255,0.04)` + border `rgba(255,255,255,0.08)` + `border-radius: 20px`
- Text primary: `#f1f5f9`
- Text secondary: `rgba(255,255,255,0.65)` / `0.55` / `0.4`
- Inputs/selects: `bg #1e293b + text #f1f5f9 + border rgba(255,255,255,0.12)`
- Focus ring: `rgba(6,182,212,0.15)` cyan accent
- Section titles: uppercase + `var(--color-accent)` + `0.5px tracking`
- H1 hero: `linear-gradient(135deg, primary-light, accent)` + `background-clip: text`
- Primary buttons: gradient + hover translateY(-1px) + box-shadow accent
- Custom select dropdown arrow SVG inline

**Nota honesta**: no pude verificar pixel-perfect via dev server porque el
bypass del ProtectedRoute con Playwright+page.route() no funciono (axios
baseURL) y no hay backend local sin .env. La consistencia se verifico
mecanicamente contra la referencia — build + tests OK.

## Artifacts creados

### Backend services (Wave 2B + Fase 1 wire)

- `app/services/defensia_rate_limits.py`
- `app/services/defensia_storage.py` + migration
- `app/services/defensia_quota_service.py` + migration en_curso
- `app/services/defensia_rag_verifier.py`
- `app/services/defensia_writer_service.py` + 9 templates Jinja2
- `app/services/defensia_export_service.py`
- `app/services/defensia_service.py` (fachada)
- `app/services/defensia_dependencies.py`
- `app/agents/defensia_agent.py`
- `app/routers/defensia.py` (11 endpoints) + helper `_run_fase1_auto()`

### Frontend (Wave 1F + 2F)

- `frontend/src/types/defensia.ts`
- `frontend/src/components/defensia/*` (11 componentes)
- `frontend/src/pages/Defensia{List,Wizard,Expediente}Page.tsx`
- `frontend/src/hooks/useDefensia{Expedientes,Expediente,Upload,Analyze,Export,Chat}.ts`
- `frontend/src/components/Header.tsx` — entry "DefensIA" en dropdown
- `frontend/src/App.tsx` — rutas /defensia, /defensia/nuevo, /defensia/:id

### Scripts auditoria

- `backend/scripts/defensia_ortografia_audit.py` (T3-002)
- `backend/scripts/defensia_anti_hallucination_audit.py` (T3-005)

### Tests

- Backend: +75 tests defensia (375 total)
- Frontend: 92 tests en 20 files (Vitest + RTL + jsdom)

## Estado de la rama

**NO mergeada a main todavia**. Pendiente:

1. T3-001 E2E Playwright caso David (requiere fixtures PDFs anonimizados).
2. T3-006 Verifier final antes de merge.
3. Beta con David Oliva primero.
4. Deploy prod: seed de tests users defensia + DEFENSIA_STORAGE_KEY env var.

## Referencias

- Spec: `plans/2026-04-13-defensia-design.md`
- Plan Parte 1: `plans/2026-04-13-defensia-implementation-plan.md`
- Plan Parte 2: `plans/2026-04-13-defensia-implementation-plan-part2.md`
- Memoria sesion 32: `memory/project_session32_defensia_part1.md`
