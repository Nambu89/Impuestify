---
name: bugfixes-2026-04
description: Bugs arreglados en abril 2026 — clasificador, RAG crash, importes OCR, workspace context, security hardening
type: project
---

# Bugfixes Abril 2026

## [2026-04-08] Clasificador Facturas — 4 bugs arreglados (sesion 29)

### Bug 65: Boton "Ver detalles" no funcionaba
**Causa raiz:** `handleView()` en `ClasificadorFacturasPage.tsx` solo hacia `window.scrollTo()` — nunca llamaba al endpoint `GET /api/invoices/{id}` que ya existia en el backend.
**Fix:** Implementar `handleView` como `async function` que llama a `apiRequest(/api/invoices/${id})`, parsea `raw_extraction` JSON, mapea a `InvoiceResult` y muestra `ExtractionCard` + `ClassificationCard`.
**Archivos:** `frontend/src/pages/ClasificadorFacturasPage.tsx`

### Bug 66: Upload facturas no funcionaba en movil (iOS Safari)
**Causa raiz:** El `<input type="file">` tenia `display: none` en CSS. En iOS Safari, llamar `.click()` programaticamente sobre un input con `display:none` no abre el file picker. Ademas, el patron `div + onClick + useRef + .click()` es fragil en navegadores moviles.
**Fix:**
1. CSS: cambiar `display: none` a `position: absolute; width: 1px; height: 1px; overflow: hidden; opacity: 0; clip: rect(0,0,0,0)` — oculto visualmente pero accesible para el browser
2. JSX: reemplazar `<div onClick>` + `useRef` + `.click()` por `<label htmlFor="cf-file-upload">` que abre el file picker nativamente sin JavaScript
3. Anadir `image/*` al atributo `accept` para aceptar fotos HEIC de camara iOS
**Archivos:** `frontend/src/pages/ClasificadorFacturasPage.tsx`, `frontend/src/pages/ClasificadorFacturasPage.css`
**Leccion:** NUNCA usar `display: none` en inputs file — usar visually-hidden. Preferir `<label htmlFor>` sobre `.click()` programatico.

### Bug 67: formatEUR crash con valores undefined en lineas de factura
**Causa raiz:** `formatEUR(n)` llamaba `n.toLocaleString()` sin verificar null/undefined. Cuando `handleView` parseaba facturas del backend, los campos `base`, `precio_unitario`, `cantidad` de las lineas podian ser undefined.
**Fix:** Cambiar `formatEUR(n: number)` a `formatEUR(n: number | null | undefined)` con `(n ?? 0).toLocaleString(...)`.
**Archivos:** `frontend/src/pages/ClasificadorFacturasPage.tsx`

### Bug 68: Faltaba boton "Volver a inicio" en Clasificador Facturas
**Causa raiz:** Todas las herramientas (calculadoras, contacto, etc.) tienen un link `<ArrowLeft> Volver a inicio` excepto el Clasificador de Facturas.
**Fix:** Anadir `<Link to="/" className="cf-back-link"><ArrowLeft size={16} /> Volver a inicio</Link>` con CSS consistente con el patron de las demas paginas.
**Archivos:** `frontend/src/pages/ClasificadorFacturasPage.tsx`, `frontend/src/pages/ClasificadorFacturasPage.css`

### Bug 69: URL preconnect desalineada en index.html
**Causa raiz:** `index.html` tenia `preconnect` apuntando a `impuestify-backend-production.up.railway.app` pero `VITE_API_URL` es `taxia-production.up.railway.app`.
**Fix:** Actualizar ambas referencias (preconnect + dns-prefetch) a `taxia-production.up.railway.app`.
**Archivos:** `frontend/index.html`

## [2026-04-09] gpt-5-mini API params + Chat crash (sesion 29 cont.)

### Bug 70: gpt-5-mini rechaza max_tokens — worker crash en produccion
**Causa raiz:** OpenAI gpt-5-mini no soporta el parametro `max_tokens` — requiere `max_completion_tokens`. El error 400 mataba el worker process sin traceback.
**Fix:** Reemplazar `max_tokens` por `max_completion_tokens` en:
- `warmup_service.py` (100)
- `conversation_analyzer.py` (500)
- `pdf_extractor.py` (4096 x2)
**Archivos:** `backend/app/services/warmup_service.py`, `backend/app/services/conversation_analyzer.py`, `backend/app/utils/pdf_extractor.py`
**Nota:** `llama_guard.py` usa Groq (no OpenAI) — mantiene `max_tokens`. Los agents ya usaban `max_completion_tokens`.

### Bug 71: gpt-5-mini rechaza temperature != 1
**Causa raiz:** gpt-5-mini solo acepta `temperature=1` (default). Valores como 0 o 0.7 generan error 400.
**Fix:** Cambiar `temperature` a 1 en `warmup_service.py` (era 0.7) y `conversation_analyzer.py` (era 0).
**Archivos:** mismos que Bug 70
**Leccion:** gpt-5-mini: SIEMPRE `temperature=1` + `max_completion_tokens` (nunca `max_tokens`). Groq puede usar `temperature=0` y `max_tokens`.

### Bug 72: Chat streaming crash — RAG OOM + territory names sin tildes — RESUELTO
**Sintoma:** Cualquier pregunta al chat crashea el worker: "Child process died" sin traceback. El warmup tambien fallaba con "No territory plugin registered for 'Aragón'".
**Causa raiz (2 problemas combinados):**
1. **Territory plugins sin tildes:** `COMUN_TERRITORIES` en `comun/plugin.py` registraba `"Aragon"`, `"Cataluna"`, `"Andalucia"`, `"Castilla y Leon"`, `"Comunidad Valenciana"` — pero la BD y `ccaa_constants.py` usan canonical con tildes (`"Aragón"`, `"Cataluña"`, etc.). El warmup y el RAG search fallaban con KeyError al buscar `get_territory("Aragón")`.
2. **OOM killer (causa principal del crash):** Railway mataba el worker process sin traceback. Con 4 workers, cada uno usaba ~344 MB = ~1.4 GB total. El RAG search (Upstash Vector sync bloqueante + 30 queries trust scoring en paralelo a Turso) disparaba el consumo y el OOM killer mataba el proceso.
**Fix (3 commits):**
1. `comun/plugin.py`: Alinear `COMUN_TERRITORIES` con canonical names de `ccaa_constants.py` (con tildes). Tambien `"Comunidad Valenciana"` → `"Valencia"`.
2. `registry.py`: Añadir fallback `normalize_ccaa()` en `get_territory()` para aceptar variantes sin tilde.
3. `railway.toml`: Reducir workers 4 → 1 con `--timeout-keep-alive 120`.
4. `hybrid_retriever.py`: `_vector_search` ahora usa `asyncio.to_thread()` para no bloquear el event loop. Trust scoring secuencial en vez de 30 queries paralelas.
5. `test_territory_comun.py`: Actualizar asserts a nombres con tildes.
**Archivos:** `backend/app/territories/comun/plugin.py`, `backend/app/territories/registry.py`, `backend/app/utils/hybrid_retriever.py`, `backend/app/routers/chat_stream.py`, `backend/railway.toml`, `backend/tests/test_territory_comun.py`
**Lecciones:**
- SIEMPRE usar nombres canonical de `ccaa_constants.py` (con tildes) en todo el codebase. NUNCA hardcodear nombres sin tildes.
- Railway con ~512 MB: maximo 1 worker Python con FastAPI + OpenAI + Upstash + Turso (~344 MB base).
- "Child process died" sin traceback = OOM killer. Diagnosticar con `resource.getrusage()` antes de operaciones pesadas.
- Upstash Vector SDK es sincrono — usar `asyncio.to_thread()` en contexto async.
- No lanzar N queries paralelas a Turso con `asyncio.gather` — hacerlas secuenciales para evitar picos de memoria.

### Bug 73: Vector search 0 resultados — accent mismatch en Upstash metadata
**Sintoma:** Upstash Vector siempre devolvia 0 results con filtro `territory = 'Aragón'` o `territory = 'Aragon'`.
**Causa raiz:** Los embeddings en Upstash podian tener territory con o sin tildes. El filtro solo probaba una variante.
**Fix:** `_vector_search` ahora prueba ambas variantes (con tilde y sin tilde) con `_strip_accents()`. FTS5 usa `OR d.source = ?` para ambas variantes.
**Archivos:** `backend/app/utils/hybrid_retriever.py`

### Bug 74: SSE connection drop — frontend no recibe respuesta en 3a pregunta
**Sintoma:** Backend completa en 14.8s pero frontend no muestra nada. La pregunta se queda sin respuesta.
**Causa raiz:** El Vector query a Upstash tardaba 70s (sin resultados). Durante esos 70s no se enviaba ningun byte SSE. Railway/browser cerraba la conexion por inactividad.
**Fix:**
1. `yield {"event": "thinking", ...}` antes del RAG search para enviar bytes inmediatos y mantener la conexion viva.
2. `asyncio.wait_for(..., timeout=10.0)` en cada Vector query — si Upstash no responde en 10s, se cae a FTS5.
**Archivos:** `backend/app/routers/chat_stream.py`, `backend/app/utils/hybrid_retriever.py`
**Leccion:** En SSE streaming, SIEMPRE enviar un evento antes de operaciones lentas. El proxy/browser cierra conexiones inactivas ~30-60s.

### Bug 75: Upstash Vector con solo 39 de 84K embeddings — sync incompleto
**Sintoma:** Vector search siempre 0 resultados para todas las CCAA. Solo FTS5 funcionaba.
**Causa raiz:** El sync original (`sync_to_upstash.py`) nunca completo. Solo 39 vectores de 83,997 estaban en Upstash.
**Fix:** Re-ejecutar sync completo desde local. 84,036 vectores sincronizados. Script usa batches de 100-200 rows desde Turso → upsert a Upstash.
**Estado:** 84,036/83,997 vectores (100%). Vector search ahora devuelve resultados con score 0.80+ para Aragón.
**Leccion:** Verificar `index.info().vector_count` periodicamente. Si no coincide con `SELECT COUNT(*) FROM embeddings`, re-sincronizar.

## [2026-04-10] Sesion 31 — 2 bugs + 12 security/responsive fixes

### Bug 76: Importes incorrectos en extraccion OCR (4.000 leido como 400)
**Sintoma:** Gemini lee "4.000,00" (formato espanol) como 400 en JSON.
**Causa raiz:** Prompt ambiguo no especificaba formato numerico. Validacion IVA pasaba porque proporciones cuadraban (400 x 21% = 84).
**Fix:** 3 cambios en `invoice_ocr_service.py`: (1) prompt explicito "numeros decimales puros, sin separadores de miles", (2) `validate_amount_magnitude()` detecta discrepancia >10x entre lineas y total, (3) confianza "baja" si warnings. 6 tests nuevos.
**Leccion:** Siempre especificar formato numerico en prompts LLM para datos financieros.

### Bug 77: Perdida contexto workspace en follow-ups
**Sintoma:** 2a pregunta en chat pierde workspace_id, respuesta generica sin contexto de documentos.
**Causa raiz:** Tabla `conversations` no tenia columna `workspace_id`. Al cargar conversacion previa, frontend mantenia workspace stale.
**Fix:** 4 archivos: (1) ALTER TABLE conversations ADD workspace_id, (2) conversation_service guarda/restaura workspace, (3) chat_stream restaura workspace en follow-ups, (4) frontend clear workspace al cambiar conversacion.
**Leccion:** Toda entidad que scope otra debe persistir la asociacion en DB, no solo en estado frontend.

### Security fixes (sesion 31): 5 backend + 7 frontend
**Backend:** Rate limiting 3 export endpoints (5/min), 9 error detail leaks → mensaje generico, 500 handler oculta detalles en produccion, XML escape en PDF (ReportLab injection), reprocess_file ownership check (IDOR).
**Frontend:** iOS Safari file upload (display:none → visually-hidden + label), touch targets 44px (clear button + classification buttons), aria-label workspace select, 20+ tildes M130CalculatorPage, reclassify-input overflow 320px, streaming badge contrast.

## [2026-04-13] Sesion 32 — DefensIA Parte 1 — 4 issues detectados y resueltos

### Bug 78: Code quality reviewer afirmo duplicados inexistentes en requirements.txt
**Sintoma:** Durante la ejecucion de T0 (anadir deps), un subagent reviewer afirmo que `lxml==5.3.0` y `Jinja2==3.1.4` ya estaban en `backend/requirements.txt` y eran duplicados del commit recien hecho (`2108a65`). En base a esa afirmacion factual falsa, un fix implementer elimino ambas lineas (commit `29b6ad5`) dejando DefensIA sin sus dependencias directas.
**Causa raiz:** El reviewer no verifico el diff real con `git show 2108a65 -- backend/requirements.txt`. Hizo una afirmacion sobre el estado previo del codigo que era objetivamente incorrecta (las lineas se habian anadido por primera vez en ese commit, nunca hubo duplicados).
**Fix:** Commit `98e0487` restauro `lxml>=5.3.0` y `Jinja2>=3.1.4` como dependencias explicitas. Tambien se corrigio la justificacion falsa del fix anterior que afirmaba que eran "transitive dependencies of beautifulsoup4, reportlab, python-docx" — NO lo son (beautifulsoup4 usa lxml como backend opcional; reportlab no depende de Jinja2; python-docx no depende de lxml).
**Leccion CRITICA:** NUNCA confiar ciegamente en afirmaciones factuales de un subagent reviewer sobre el estado previo del codigo. El controlador DEBE verificar con `git show <sha>` o `git diff <sha>^ <sha>` antes de aceptar fixes basados en estas afirmaciones. Los reviewers subagent no tienen memoria del diff original y pueden confundir el estado del fichero.
**Archivos:** `backend/requirements.txt` (sesion 32)
**Impacto:** Si el fix erroneo no se hubiera detectado, DefensIA habria quedado sin `lxml` y `Jinja2` como deps directas, rompiendo `extract_notificacion_xml` y todas las plantillas Jinja2 del writer service en produccion.

### Bug 79: Dead enum value `Fase.TEAR_INTERPUESTA` en phase detector
**Sintoma:** El enum `Fase.TEAR_INTERPUESTA` definido en `backend/app/models/defensia.py` nunca era retornado por ninguna branch del phase detector. Todas las ramas que detectaban reclamacion TEAR colapsaban en `Fase.TEAR_AMPLIACION_POSIBLE`. Detectado por el final code reviewer (opus) en T99.
**Causa raiz:** El spec §5.2 distinguia ambas fases conceptualmente pero el automaton inicial solo implemento una de ellas. El enum value quedo huerfano — un "dead enum value" que habria causado que cualquier regla con `fases=["TEAR_INTERPUESTA"]` nunca se disparara en Parte 2, fallando silenciosamente.
**Fix:** Commit `be3f52a` implementa la diferenciacion via ventana temporal:
1. `detect_fase(exp, hoy=None)` ahora expone `hoy` como parametro opcional (default = `datetime.now(timezone.utc)`)
2. Helper `_es_tear_reciente(escrito_tear, hoy)`: True si `(hoy - escrito_tear.fecha_acto) < timedelta(days=30)`
3. Helper `_fase_tras_tear(escrito, hoy)` retorna `TEAR_INTERPUESTA` si reciente, `TEAR_AMPLIACION_POSIBLE` si pasados 30 dias
4. Las 2 branches que devolvian `TEAR_AMPLIACION_POSIBLE` directamente ahora llaman `_fase_tras_tear(...)`
5. Tests: `test_reclamacion_tear_reciente_fase_tear_interpuesta` (hoy = 10d despues) + `test_reclamacion_tear_antigua_fase_tear_ampliacion_posible` (hoy = 60d despues). Caso David tiene 2 tests (uno por cada branch del automaton)
**Leccion:** Los enum values deben ser alcanzables desde al menos una branch del codigo que los usa. Si un enum value no tiene test que verifique que algun path lo retorna, es dead code y puede ocultarse indefinidamente. Regla para Parte 2: cualquier regla con `fases=["X"]` debe tener un test de integracion que verifique que existe un expediente realista que dispara X en el phase detector.
**Archivos:** `backend/app/services/defensia_phase_detector.py`, `backend/tests/defensia/test_phase_detector.py`, `backend/tests/defensia/test_caso_david_extraction.py`

### Bug 80: `TipoDocumento.SENTENCIA_JUDICIAL` ignorada por phase detector
**Sintoma:** Un expediente que contenga unicamente una sentencia judicial sobre la deuda fiscal (ej: contencioso-administrativo TSJ) retornaba `INDETERMINADA` con confianza 0.3, cuando deberia ser `FUERA_DE_ALCANCE` (v1 no cubre fase judicial).
**Causa raiz:** `SENTENCIA_JUDICIAL` estaba definida en la taxonomia regex pero no estaba incluida en el set `_FUERA_ALCANCE_TIPOS` del phase detector, junto con `ACTA_INSPECCION`, `PROVIDENCIA_APREMIO`, `RESOLUCION_TEAC`.
**Fix:** Commit `be3f52a` (mismo que Bug 79): anadir `TipoDocumento.SENTENCIA_JUDICIAL` a `_FUERA_ALCANCE_TIPOS`. Test `test_sentencia_judicial_fuera_de_alcance` verifica la transicion.
**Leccion:** Al definir sets de "tipos terminales" (como FUERA_DE_ALCANCE), revisar la taxonomia completa de TipoDocumento y comprobar que todos los tipos que deben caer en ese estado estan incluidos. Cross-check via test por cada tipo.
**Archivos:** `backend/app/services/defensia_phase_detector.py`

### Bug 81: Plan asumio migration runner automatico inexistente
**Sintoma:** El plan original de DefensIA asumia que el proyecto Impuestify tenia un runner automatico que ejecutaba `.sql` en `backend/app/database/migrations/` al arranque. En realidad no existe tal runner — el proyecto usa inline `CREATE TABLE IF NOT EXISTS` statements dentro de `backend/app/database/turso_client.py::init_schema()`. Resultado: las 7 tablas de DefensIA vivian solo en el `.sql` file, NO se crearian jamas en produccion.
**Causa raiz:** El subagent del plan asumio un patron estandar de Django/Alembic sin verificar como Impuestify realmente maneja sus migraciones.
**Fix:** Commit `f1c82f5` wirea el SQL file en `init_schema()`:
1. Lee el fichero `20260413_defensia_tables.sql` al arrancar
2. Split por `;`, ejecuta statement por statement con `await self.execute(stmt)` siguiendo el patron async libsql existente
3. Smoke test en `test_migration.py` verifica que `init_schema()` referencia el fichero por nombre (anti-drift: si alguien anade otra migracion sin wirearla, el test falla)
**Leccion CRITICA (actualizar CLAUDE.md):** Antes de escribir plans de implementacion que incluyan migraciones DB, SIEMPRE verificar primero como el proyecto aplica migraciones en produccion. Opciones comunes: (a) runner automatico con auto-discovery, (b) lista explicita en el runner, (c) inline CREATE TABLE en codigo de init, (d) tooling externo (Alembic, Flyway). Impuestify usa la opcion (c) — documentado ya en `backend/CLAUDE.md` seccion "Common Backend Tasks".
**Archivos:** `backend/app/database/turso_client.py`, `backend/app/database/migrations/20260413_defensia_tables.sql`, `backend/tests/defensia/test_migration.py`

### Bug 82: Crawler deps faltaban en requirements.txt + diagnostico incorrecto de URLs AEAT
**Sintoma:** Al lanzar `python -m backend.scripts.doc_crawler` en sesion 32 fallo con `ModuleNotFoundError: No module named 'scrapling'`, `curl_cffi`, `playwright`, `browserforge`. Tras instalarlas manualmente, el crawler reporto 18 URLs AEAT con HTTP 404.

**Causa raiz (dos problemas independientes):**
1. **Deps del crawler nunca commiteadas a `backend/requirements.txt`**: `scrapling`, `curl_cffi`, `playwright`, `browserforge` se usaban en el codigo pero no estaban fijadas. Cada sesion nueva tropezaba con los mismos ModuleNotFoundError.
2. **Diagnostico inicial erroneo del operador**: Inicialmente documente Bug 81 como "AEAT reorganizo sede electronica" basandome solo en los HTTP 404. En realidad `backend/scripts/doc_crawler/watchlist.py` YA tenia notas explicitas "TIPO A: Pendiente publicacion AEAT" en 14 de las 18 URLs fallidas. El crawler las reintenta en cada ejecucion esperando que AEAT publique la campana renta 2025/2026. Solo 3 URLs (Manual Renta 2025 Tomo1+2, Manual IVA 2025) y 1 doc historico (DR130_e2019) requieren investigacion real.

**Fix:**
- **Commit `718d5c8` en main**: anadir `scrapling==0.4.6`, `curl_cffi==0.15.0`, `playwright==1.58.0`, `browserforge==1.2.4` al `backend/requirements.txt` con comentario de seccion `Doc crawler`. Pin estrictos por estabilidad (browserforge y scrapling evolucionan fuerte).
- **Lateral upgrade**: scrapling fuerza `lxml 6.0.4` (antes 5.3.0) y `orjson 3.11.8` (antes 3.10.15). Los 58 tests de DefensIA Parte 1 siguen pasando con las versiones nuevas (verificado en sesion 32 antes del commit).
- **Documentacion**: nuevo fichero `memory/crawler-state.md` con estado completo del crawler, stats (98 URLs, 23 territorios), deps runtime, clasificacion correcta de los 18 fallos (14 esperados + 1 historico + 3 a investigar), plan A enfocado.

**Lecciones CRITICAS:**
1. **Leer NOTAS del watchlist antes de diagnosticar "URLs rotas"**. El contexto esta en el propio dato. Mi primer reporte decia "AEAT reorganizo sede" sin leer la columna `notes` del watchlist que explicitamente decia "Pendiente publicacion AEAT" en 14 de 18 casos. Un diagnostico erroneo obligaria a una sesion entera de web scraping sobre URLs que el crawler ya esta gestionando correctamente.
2. **Dependencias opcionales del crawler deben estar en requirements.txt**. El crawler es parte del workflow operacional del proyecto — no es una tool "opcional". Si una herramienta se usa, sus deps deben fijarse para reproducibilidad.
3. **Lateral upgrades de deps pueden ser inocuos**: antes de hacer un upgrade mayor de lxml (5→6), correr los tests existentes. En este caso DefensIA Parte 1 pasa con ambas versiones porque solo usa `etree.fromstring()` y `etree.QName()` — API estable entre 5 y 6.

**Archivos:** `backend/requirements.txt`, `memory/crawler-state.md`, `docs/_crawler_report.md`, `docs/_crawler_log.json` (inventario actualizado: 56 docs indexados).

**Scope real pendiente (A.1):** investigar 3 URLs (Manual Renta 2025 Tomo1+2, Manual IVA 2025) + 1 historico DR130. 15-30 min, no 60.

### Bug 83: AEAT cambio nomenclatura Manuales Practicos 2025 (Tomo → Parte)
**Sintoma:** El crawler reportaba 3 URLs de manuales AEAT como HTTP 404: Manual Practico IRPF 2025 Tomo1, Tomo2, y Manual Practico IVA 2025. Como NO tenian nota "Pendiente publicacion" en el watchlist, eran candidatos reales a "URL rota".

**Causa raiz:** AEAT ha cambiado la nomenclatura de los Manuales Practicos en la campana renta 2025:
- `Tomo1` → `Parte1`, `Tomo2` → `Parte2` (en el filename y en el path del dest)
- Parte2 ahora vive en subdirectorio dedicado `IRPF-{year}-Deducciones-autonomicas/` (antes en el mismo subdir `IRPF-{year}/`)
- Manual IVA ahora incluye el ano en el filename: `Manual_IVA.pdf` → `Manual_IVA_{year}.pdf`

El Manual Renta 2025 Parte 1 fue publicado el **27-03-2026** (12 dias antes del inicio de campana el 8-abr-2026). El Manual IVA 2025 tambien fue actualizado.

**Fix:** Commit `100deb2` en main actualiza `backend/scripts/doc_crawler/watchlist.py`:
1. URLs corregidas con el nuevo patron `ManualRenta{year}Parte1_es_es.pdf`
2. Subdirectorio `IRPF-{year}-Deducciones-autonomicas/` para Parte2
3. Filename `Manual_IVA_{year}.pdf`
4. `dest` renombrado de `_Tomo1.pdf` a `_Parte1.pdf` para reflejar nomenclatura real
5. Campo `pattern` actualizado con los nuevos templates (rotado anual)
6. Campo `notes` con fecha + descripcion del cambio para auditoria futura

**Verificacion empirica en sesion 32:**
- `curl` con User-Agent estandar → HTTP 200 en los 3 URLs (tamaños: 7.54, 3.80, 6.30 MB)
- `Scrapling check_url_exists` → HTTP 200
- `Scrapling download_document` → HTTP 404 (!) — bug adicional: el Scrapling fetcher falla al descargar tras volumen de requests (anti-bot detection probablemente). Los 3 manuales se descargaron manualmente con `curl` directo a `docs/AEAT/IRPF/` y `docs/AEAT/IVA/`.

**Pendiente:** ingesta RAG de los 3 manuales (17.64 MB) con `reingest_aeat.py`. Investigacion del bug de Scrapling anti-bot vs curl (anadido al backlog como task dedicada).

**Leccion CORRECCION del Bug 82:** Mi primer diagnostico fue "AEAT reorganizo sede electronica". Corregi luego a "son 'pendiente publicacion' ya documentados". Ninguna era del todo correcta: la verdad es que 14 de 18 eran "pendiente publicacion" (el usuario tenia razon en que las URLs no estaban rotas, solo no publicadas aun — en ese caso concreto del Manual IRPF AEAT retraso la publicacion del 2024 al 2025 pero NO las URL), y 3 de 18 eran **URLs con nomenclatura cambiada** (Tomo→Parte). Este bug 83 documenta la solucion real del caso 3/3.

**Archivos:** `backend/scripts/doc_crawler/watchlist.py` (main), `docs/AEAT/IRPF/AEAT-Manual_Practico_IRPF_2025_Parte1.pdf`, `docs/AEAT/IRPF/AEAT-Manual_Practico_IRPF_2025_Parte2.pdf`, `docs/AEAT/IVA/AEAT-Manual_Practico_IVA_2025.pdf`, `memory/crawler-state.md`, `memory/MEMORY.md`.

**Leccion metacognicion:** En el diagnostico preliminar salte a conclusiones dos veces consecutivas ("AEAT reorganizo" → "son todos pendiente publicacion"). El usuario me corto con razon diciendo "NO llegues a conclusiones precipitadas y SIN SENTIDO". La unica forma correcta de diagnosticar fue **verificar empiricamente con curl + Scrapling antes de aceptar una hipotesis**. Lo hice al tercer intento y el resultado fue claro: es un rename de Tomo→Parte, perfectamente reproducible y commiteable en 5 minutos. **Regla actualizada para futuras sesiones**: NO diagnosticar URLs rotas como "reorganizacion" o "pendiente publicacion" sin verificar con `curl -I <URL>` directo. Si `curl` devuelve 200 y el crawler 404, es el crawler el que tiene bug.

## [2026-04-20] DefensIA /expedientes 404 — prefix /api faltante (hotfix prod)

### Bug 84: DefensIA rompe al entrar a /defensia (Not Found)
**Sintoma:** Al entrar a `/defensia` en produccion, pantalla roja "Error al cargar los expedientes: Not Found". Console: `GET https://taxia-production.up.railway.app/defensia/expedientes 404 (Not Found)`.
**Causa raiz:** Backend monta `router = APIRouter(prefix="/api/defensia")` en `backend/app/routers/defensia.py`. Frontend llamaba `/defensia/...` sin prefix `/api`. `useApi.apiRequest` y calls con `fetch(${API_URL}...)` concatenan directamente sobre `API_URL` (en produccion = `https://taxia-production.up.railway.app`, sin `/api`). Resultado: URL final sin `/api` → 404.
**Fix:** Anadir `/api/` prefix en 9 call sites:
- `frontend/src/hooks/useDefensiaExpedientes.ts:19`
- `frontend/src/hooks/useDefensiaExpediente.ts:20`
- `frontend/src/hooks/useDefensiaAnalyze.ts:30`
- `frontend/src/hooks/useDefensiaChat.ts:34`
- `frontend/src/hooks/useDefensiaUpload.ts:105`
- `frontend/src/hooks/useDefensiaExport.ts:25`
- `frontend/src/pages/DefensiaWizardPage.tsx:128,152`
- `frontend/src/components/defensia/EscritoEditor.tsx:53`
Tests unitarios `useDefensiaExpedientes.test.ts` + `useDefensiaExpediente.test.ts` + `DefensiaWizardPage.test.tsx` actualizados (los que usaban `expect.stringContaining("/defensia/...")` siguen pasando).
**Leccion:** Todos los endpoints del backend usan prefix `/api/...`. Cualquier hook frontend nuevo DEBE usar `/api/<router>/<path>` — incluso cuando el hook anterior del mismo dominio ya lo hacia. Regla ya documentada en `copilot-instructions.md` tras round 9, pero el codigo DefensIA se escribio antes y no se migro.
**Archivos:** 7 archivos frontend + 3 tests.
