---
name: Sesion 32 — DefensIA Parte 1
description: Brainstorming completo + spec + plan + ejecucion Wave 1 Back de DefensIA (asesor defensivo fiscal con motor hibrido anti-alucinacion). 58 tests verdes. Caso David Oliva como ground truth.
type: project
---

# Sesion 32 — DefensIA Parte 1 (2026-04-13)

DefensIA es una nueva herramienta de Impuestify que ingesta expedientes fiscales del usuario, detecta la fase procesal automaticamente y genera dictamen + borrador de escritos (alegaciones, recursos, reclamaciones TEAR) con motor hibrido anti-alucinacion.

## Caso primigenio — David Oliva

Beta tester con expediente IRPF 2024 complejo: **141 archivos** repartidos en 8 carpetas (Autonomo, COMPRA San Antonio 22, Placas Solares, Aislamiento Iberdrola, VENTA Valdidueñas 3, Gestoria, Trabajador cuenta ajena, 4 reclamaciones encadenadas: NOVIEMBRE, DICIEMBRE, ENERO TEAR, ABRIL).

**Hechos clave:**
- Venta vivienda habitual Valdidueñas 3 en 22-10-2024 (adquirida 12-05-2022, solo 2a5m — NO cumple 3 anos art. 41 bis RIRPF)
- Reinversion en San Antonio 22 + obras eficiencia energetica (placas solares + aislamiento Iberdrola)
- Sentencia 28-06-2024 modifica medidas (extingue pension compensatoria, inicia pension alimentos)
- AEAT deniega exencion reinversion art. 38.1 LIRPF — liquidacion provisional 30-01-2026 (6.330,32 euros total)
- Reclamacion TEAR contra liquidacion 01-02-2026 (2026GRC49560011H)
- Sancion 191+194.1 LGT impuesta 07-04-2026 (3.393,52 euros)
- Reclamacion TEAR contra sancion 09-04-2026 (2026RSC49560055BG) — presentada el dia anterior al inicio de esta sesion

Este expediente es el **ground truth** del producto: 58 tests incluyen 6 especificos del caso David.

## Brainstorming (6 preguntas, skill superpowers:brainstorming)

1. **Alcance funcional** → A: Reactivo-defensivo puro (user sube acto administrativo → dictamen + escrito). NO auditoria preventiva, NO solo recursos genericos
2. **Captura del brief** → C: Hibrido wizard 5 pasos + textarea libre + boton chat. Regla #1: el sistema NO arranca analisis hasta que el usuario exprese que necesita
3. **Procedimientos cubiertos** → C: 5 tributos (IRPF + IVA + ISD + ITP + Plusvalia Municipal) + verificacion + comprobacion limitada + sancionador + reposicion + TEAR (abreviado y general). FUERA: inspeccion, apremio, alzada TEAC, contencioso, IS
4. **Arquitectura tecnica** → C: Pagina top-level bajo dropdown "Herramientas" existente (reutiliza auth, upload, OCR Gemini, RAG, multi-tenant). Nombre: **DefensIA**
5. **Cerebro (motor)** → C: Hibrido 4 fases — Gemini Vision extraccion → motor reglas deterministas Python → RAG verificador anti-alucinacion contra HybridRetriever existente → LLM redactor controlado con plantillas Jinja2. Cero alucinacion en citas normativas
6. **Output + monetizacion** → D: 1/3/5 expedientes mes (Particular/Autonomo/Creator) + 15/12/10 EUR por adicional. Dictamen + timeline interactivo + editor WYSIWYG (Tiptap) + export DOCX/PDF. Disclaimer obligatorio 4 superficies

## 10 Reglas invariantes del producto

1. Tras subida, el sistema **no arranca analisis juridico** hasta que el usuario exprese que necesita (Fase 1 extraccion tecnica SI puede auto-dispararse)
2. La fase procesal **NO se asume**, se detecta desde los documentos. Si confianza <0.85, preguntar
3. Alcance v1 fijo: 5 tributos + verificacion/comprobacion limitada + sancionador + reposicion/TEAR. Inspeccion, apremio, TEAC, contencioso → FUERA
4. Disclaimer obligatorio en 4 superficies: banner persistente, pie argumentos, header/footer escrito exportado, checkbox pre-primer export
5. Urgencia GTM: priorizar eficiencia sobre perfeccion
6. Nombre **DefensIA**, entrada en dropdown "Herramientas" del Header.tsx
7. Ejecucion via RuFlo + subagent-driven-development para paralelizar
8. Ortografia impecable con tildes, conexiones back/front auditadas, cero codigo muerto, cero invenciones, responsive perfecto movil+desktop
9. Motor hibrido anti-alucinacion obligatorio: toda cita normativa verificada contra RAG, descarte silencioso de argumentos no soportados
10. David = caso primigenio + primer probador. Beta publica posterior a todos los usuarios activos

## Documentos creados

- `plans/2026-04-13-defensia-design.md` — spec completo (~480 lineas, 22 secciones)
- `plans/2026-04-13-defensia-implementation-plan.md` — Plan Parte 1 (TDD ~22 tasks)
- Pendiente: Plan Parte 2 (~58 tasks restantes)

## Wave 1 Back — Implementado (16 tasks, 58 tests)

### Rama Git

`claude/defensia-v1` — 23 commits desde main. NO mergeada aun.

### Fundaciones (T0-T3)
- `backend/requirements.txt` — python-docx>=1.1.2, lxml>=5.3.0, Jinja2>=3.1.4 (explicitos, no transitivos)
- `backend/app/database/migrations/20260413_defensia_tables.sql` — **7 tablas** DefensIA:
  - `defensia_expedientes` (con CHECK tributo en IRPF/IVA/ISD/ITP/PLUSVALIA)
  - `defensia_documentos` (datos_estructurados_json)
  - `defensia_briefs` (chat_history_json)
  - `defensia_dictamenes` (argumentos_json)
  - `defensia_escritos` (contenido_markdown + version)
  - `defensia_cuotas_mensuales` (UNIQUE user_id,ano_mes)
  - `defensia_rag_log` (auditoria descartes RAG verificador)
  - Indices: `idx_defensia_exp_user`, `idx_defensia_docs_exp`
  - FK CASCADE en todas las chains (user → expediente → hijos)
- **Wired en `turso_client.py::init_schema()`** — lee el .sql y ejecuta statement por statement con el patron async `await self.execute(stmt)`. Smoke test en `test_migration.py` verifica que `init_schema` referencia el fichero por nombre (anti-drift).
- `backend/app/models/defensia.py` — Pydantic v2 con 9 clases:
  - Enums: `Tributo` (5), `Fase` (12), `TipoDocumento` (19), `EstadoExpediente` (4)
  - Models: `DocumentoEstructurado`, `Brief`, `ExpedienteEstructurado` (con metodo `timeline_ordenado()`), `ArgumentoCandidato`, `ArgumentoVerificado` (con `Field(ge=0, le=1)` para confianza)
- `backend/app/routers/defensia.py` — stub con `GET /api/defensia/_health`. Registrado en `main.py`

### Extraccion (T10-T18)
- `defensia_document_taxonomy.py` — 18 patrones regex ordenados (mas especificos primero). Clasificacion determinista fast-path en 0 coste LLM
- `defensia_document_classifier.py` — `DocumentClassifier` con 2 niveles: regex + fallback Gemini Vision (`gemini-3-flash-preview`). `ClassificationResult` con fuente trazable (`regex`/`gemini`/`fallback`). Tests con mocks de Gemini
- `defensia_data_extractor.py` — **7 extractores**:
  - `extract_liquidacion_provisional` (+ derivado `diff_gastos_adquisicion_no_admitidos`)
  - `extract_acuerdo_sancion` (+ derivado `tiene_doble_tipicidad_191_194` para regla R006 non bis in idem)
  - `extract_propuesta_liquidacion`
  - `extract_requerimiento`
  - `extract_escrito_usuario` (detecta tipo: alegaciones/reposicion/reclamacion_tear/ampliacion)
  - `extract_libro_registro_xlsx` — **SIN LLM**, lee con openpyxl, agrega bases e IVAs por heuristica de nombres de columnas
  - `extract_notificacion_xml` — **SIN LLM**, parsing determinista con lxml
  - Helper compartido `_parse_gemini_json()` maneja cercos ```json
  - Todos capturan excepciones y devuelven `{"error": str, "nombre": str}`

### Detector de fase (T19)
- `defensia_phase_detector.py` — automaton de **12 estados** con confidence score explicito por branch. Algoritmo:
  1. Si hay doc en `_FUERA_ALCANCE_TIPOS` → FUERA_DE_ALCANCE (0.99)
  2. Ordenar timeline, identificar ultimo acto AEAT + ultimo escrito usuario
  3. Mapear segun tipo de ultimo acto + si usuario respondio
- Diferenciacion **TEAR_INTERPUESTA** (ventana <30d) vs **TEAR_AMPLIACION_POSIBLE** (>=30d) via helper `_es_tear_reciente(escrito, hoy)`. `detect_fase(exp, hoy=None)` expone `hoy` como parametro para tests deterministas
- `_FUERA_ALCANCE_TIPOS` incluye: acta inspeccion, providencia apremio, resolucion TEAC, **sentencia judicial** (anadido tras review final)

### Caso David integration test (T20)
- `backend/tests/defensia/fixtures/caso_david/expediente_anonimizado.json` — 8 documentos del expediente real anonimizados (d01-d08 desde requerimiento hasta reclamacion TEAR sancion)
- `test_caso_david_extraction.py` — 4 tests que validan end-to-end:
  - Deteccion TEAR_INTERPUESTA si `hoy` dentro ventana 30d
  - Deteccion TEAR_AMPLIACION_POSIBLE si `hoy` pasados 30d
  - Timeline ordenado 8 docs
  - Doble tipicidad 191+194 presente
  - Diff gastos adquisicion = 759.25 EUR

### Motor de reglas scaffolding (T30)
- `defensia_rules_engine.py` — decorador `@regla(id, tributos, fases, descripcion)`, `REGISTRY` global, `reset_registry()` para tests, `evaluar(expediente, brief)` con 3 garantias de robustez:
  1. Enum-or-string normalization (`hasattr(x, "value")`)
  2. Try/except por regla (una regla rota NO tumba el pipeline, se logea y se continua)
  3. Duplicate ID rejection at decoration time (raise `ValueError`)
- 4 carpetas vacias creadas para registrar las 30 reglas en Parte 2:
  - `defensia_rules/reglas_procedimentales/` (R001-R010: motivacion, audiencia, prescripcion, carga prueba, integra regularizacion, non bis in idem...)
  - `defensia_rules/reglas_irpf/` (R011-R020: reinversion vivienda habitual, anualidades alimentos, gastos adquisicion, eficiencia energetica, deducciones autonomicas no invocadas...)
  - `defensia_rules/reglas_otros_tributos/` (R021-R030: IVA prorrata, ISD reduccion parentesco, ITP valor referencia, plusvalia municipal metodo optimo...)

## Review final (opus)

**Verdict: APPROVED (tras fix del TEAR_INTERPUESTA dead enum)**

Strengths:
- Build health: 58/58 tests in 9s, imports OK
- Arquitectura consistente: 7 extractores con patron uniforme `_PROMPT_*` + `_gemini_extract_*` + `extract_*`
- Zero anti-invention leakage: solo 1 `Art./LGT` en docstring de ejemplo
- Hygiene clean: 23 commits sin `claude/co-authored/ruvnet`, sin `datetime.utcnow`, sin f-string SQL, sin `gpt-4o-mini`
- Phase detector auditable, reglas engine robusto

## Pendiente — Parte 2 (~58 tasks)

- Escribir `plans/2026-04-13-defensia-implementation-plan-part2.md` con texto TDD literal
- Wave 1 Back continuacion: 30 reglas R001-R030 (test per regla)
- Wave 2 Back: RAG verificador contra HybridRetriever + Writer service + 9 plantillas Jinja2 + Export DOCX/PDF + defensia_service fachada + defensia_agent chat + 9 endpoints REST + SSE analyze + rate limiting + cuotas
- Wave 1 Front: DefensiaListPage, DefensiaWizardPage (5 pasos), DefensiaExpedientePage, 9 componentes, 5 hooks, Header dropdown entry
- Wave 2 Front: EscritoEditor Tiptap, DisclaimerBanner, DefensiaChat con useStreamingChat
- Wave 3: integracion end-to-end, E2E Playwright en 4 viewports, audit ortografico, limpieza
- Wave 4: beta David + todos los usuarios activos

**Timeline estimado:** ~4 semanas mas hasta beta publica con paralelizacion RuFlo.
