# Bugfixes 2026-08

## Contexto: backport de la rama `demo/fiscal-ia-melilla` a `main`

La rama de la demo IA-Melilla bifurcó de `main` el 2026-05-19 (`f68afef`) y
acumuló 38 commits. Al auditar la divergencia (2026-08-09) se detectó que
contenía **arreglos genéricos, no de marca**, que nunca volvieron a `main` —
es decir, bugs vivos en producción de Impuestify durante ~3 meses.

Rama del backport: `claude/backport-demo-fixes`.

**No se hizo cherry-pick**: los commits de la rama demo mezclan arreglos
genéricos con cambios de marca (`BRAND_NAME`) y de producto de Melilla
(system prompt relajado, bypasses `DEMO_MODE`). El backport es curado,
fichero a fichero.

---

## Bug 104 — DefensIA se saltaba el pipeline de seguridad (CRÍTICO)

**Archivo**: `backend/app/routers/defensia.py`

**Síntoma**: `POST /api/defensia/chat` pasaba `body.message` directamente al
`DefensiaAgent`. El router no tenía **ninguna** referencia a
`security_pipeline` (verificado: 0 ocurrencias en `main`, 3 en la rama demo).

**Causa raíz**: al construir DefensIA (sesión 32-33) se replicó el patrón de
streaming de `chat_stream.py` pero se omitió la llamada al pipeline central.
El agente tenía su propio `_check_input_safety()` (solo guardrails, y
fail-open), lo que dio falsa sensación de cobertura.

**Impacto**: los endpoints DefensIA aceptaban input sin detección de prompt
injection, sin PII, sin SQLi, sin clasificador de temas y sin Llama Guard.

**Fix**: ejecutar `security_pipeline.check(question=..., user_id=...)` antes
de invocar al agente; si `is_safe=False`, devolver un `EventSourceResponse`
de rechazo. Se usa `pipeline_result.sanitized_text` (recortado, sin control
chars) en lugar del input crudo.

**Desviación respecto a la rama demo**: la demo emitía
`pipeline_result.reason`, que es el motivo **interno** (nombra la capa y los
patrones que hicieron match). En `main` se emite `rejection_message`, que es
el texto pensado para el usuario. Filtrar `reason` sería un info leak.

---

## Bug 105 — Detector de PII ignoraba el regex si Groq decía "safe"

**Archivo**: `backend/app/security/pii_detector.py`

**Síntoma**: "mi DNI es 12345678Z" se clasificaba como seguro y pasaba.

**Causa raíz**: `detect()` consultaba primero a Groq (`_detect_uncached`) y
solo caía al regex determinista en el camino de fallback (>3000 chars o
error). El modelo de seguridad LLM es demasiado permisivo en contexto fiscal:
un DNI dentro de una consulta tributaria "tiene sentido" y no lo marca.

**Fix**: unir los dos veredictos. Groq sigue corriendo primero; si devuelve
`has_pii=False`, se pasa el regex y, si encuentra PII de alta confianza, el
regex gana.

**La primera versión del fix estaba mal y la tumbaron los tests.** La rama demo
cortocircuitaba: regex primero y, si marcaba algo, return inmediato sin llamar
a Groq. Dos problemas:

1. **Falso positivo masivo.** El patrón `postal_code` es
   `\b(?:0[1-9]|[1-4]\d|5[0-2])\d{3}\b`, o sea **cualquier número de 5 cifras
   entre 01000 y 52999**. En una app fiscal donde la gente escribe importes,
   "¿Cuánto IRPF pago si gano 30000 EUR en Madrid?" pasaba a bloquearse como
   PII. Lo cazó `test_pipeline_passes_legitimate`.
2. **Rompía la semántica del detector.** `test_detect_pii_s7` y los 3 de
   `test_pii_detector_resilience` afirman que Groq SÍ se llama (para conservar
   sus categorías S7 y la ruta de fallback 413/429). Cortocircuitar dejaba
   `call_count == 0`.

Versión final: Groq primero (semántica intacta, tests verdes) + override por
regex solo con tipos de **alta confianza**. `_HIGH_CONFIDENCE_PII` excluye
`postal_code` (importes) y `passport` (`[A-Z]{2,3}\d{6,9}` matchea códigos de
expediente). Ambos siguen contando cuando el regex actúa como detector único
(input largo o fallo de Groq) — solo se les niega el poder de invalidar al LLM.

**Lección**: portar un fix de seguridad de una rama que no ejecuta la misma
batería de tests puede importar el bug que esa rama no vio. La demo tenía este
falso positivo y nadie se enteró.

---

## Bug 106 — Modelo Gemini retirado por Google (9 call sites)

**Archivos**: `backend/app/config.py`, `services/defensia_data_extractor.py`
(5x), `services/defensia_document_classifier.py`,
`services/invoice_classifier_service.py`, `services/invoice_ocr_service.py`

**Síntoma**: `gemini-3-flash-preview` devuelve 404. Verificado contra la doc
oficial de Google el 2026-08-09: aparece bajo "Previous models" como *shut
down*. Ya se había detectado el 2026-05-25 en la demo de Melilla, pero el
arreglo se quedó en esa rama.

**Impacto**: clasificador de facturas (OCR Gemini Vision) y extracción de
documentos DefensIA rotos en producción de Impuestify.

**Causa raíz de la gravedad**: 6 de los 9 call sites tenían el id de modelo
**hardcodeado**, no leído de `settings.GEMINI_MODEL`. Por eso poner la env
var en Railway no habría bastado para mitigarlo.

**Fix**: `settings.GEMINI_MODEL` default → `gemini-2.5-flash-lite` (estable y
ya validado en la demo de Melilla). Los 6 sitios hardcodeados ahora leen
`settings.GEMINI_MODEL`. En `InvoiceOCRService` e `InvoiceClassifierService`
el parámetro pasa a `model: str | None = None` con
`self.model = model or settings.GEMINI_MODEL`.

**Regla permanente**: NUNCA hardcodear un id de modelo LLM/Vision en el
código. Siempre `settings.<PROVIDER>_MODEL`. Una retirada de modelo por parte
del proveedor debe arreglarse con una env var, no con un deploy.

**Pendiente (no incluido)**: evaluar `gemini-3.5-flash-lite` (más nuevo y
barato) contra los fixtures de facturas antes de cambiar. Un backport de
emergencia no es el sitio para cambiar la precisión de extracción.

---

## Bug 107 — Rate limit por token en vez de por usuario (bypass trivial)

**Archivo**: `backend/app/security/rate_limiter.py`

**Síntoma**: `get_rate_limit_key()` devolvía `user:{md5(Authorization)[:16]}`.

**Causa raíz**: el código llevaba el comentario "For now, use a hash of the
token" — un TODO que se quedó. Como el hash es del token y no del usuario,
**volver a hacer login mintaba un token nuevo y por tanto un contador nuevo**.
Cualquiera podía resetear su propio rate limit a voluntad.

**Fix**: decodificar el JWT (sin verificar expiración — las dependencias de
auth ya hacen la validación real) y keyear por el claim `sub`, que es estable
por usuario. Fallback a IP si no hay token o no se puede parsear; el `except`
es deliberadamente amplio porque una excepción dentro de la key function haría
que slowapi devolviera 500.

**Desviación respecto a la rama demo**: no se trae `_DEMO_USER_EMAILS` (keyear
por IP a las cuentas demo compartidas). Eso es específico de la demo.

---

## Bug 108 — DefensIA agotaba el presupuesto de tokens razonando

**Archivo**: `backend/app/agents/defensia_agent.py`

**Síntoma**: el chat de DefensIA se quedaba colgado y la UI en blanco.

**Causa raíz**: `max_completion_tokens=1024` sin `reasoning_effort`. gpt-5-mini
gastaba el presupuesto entero en razonamiento oculto y emitía **cero** chunks
de contenido. El stream terminaba sin error y sin texto.

**Fix**: `MAX_COMPLETION_TOKENS` 1024 → 10000, `reasoning_effort="minimal"`,
`asyncio.wait_for` de 60s sobre `create()` (igual que TaxAgent), y un fallback
explícito cuando `content_chunks == 0` para que la UI nunca se quede vacía.

**Desviación respecto a la rama demo**: NO se trae la reescritura del
`SYSTEM_PROMPT`. La demo lo relajó para que el bot respondiera dudas
directamente; `main` conserva la Regla #1 del producto (DefensIA no arranca
análisis jurídico hasta que el usuario escribe su brief). Es una decisión de
producto, no un bugfix. Tampoco se traen los marcadores
`logger.error("DEFENSIA_AGENT_TRACE ...")`, que eran andamiaje de diagnóstico
y a nivel ERROR ensuciarían los logs de producción.

**Corrección durante la implementación**: el código de la rama demo accedía a
`choice.finish_reason` directamente. El SDK real siempre lo trae, pero los
dobles de test no, y como el acceso vive dentro del `try` amplio, un
`AttributeError` se tragaba el stream entero y devolvía el mensaje de error
técnico. Cazado por `test_chat_stream_pasa_guardrails`. Se usa
`getattr(choice, "finish_reason", None)` — es solo para diagnóstico.

**Test actualizado**: `test_chat_stream_usa_max_completion_tokens` afirmaba
`== 1024`, que es literalmente el valor que causaba el bug. Se reancla a
`DefensiaAgent.MAX_COMPLETION_TOKENS` con un suelo de 4096 y se le añade la
comprobación de `reasoning_effort`, para que el test proteja la intención
("usa max_completion_tokens, nunca max_tokens") sin fosilizar el valor roto.

---

## Cobertura de regresión

`backend/tests/test_backport_regressions.py` (15 tests) + 2 tests nuevos en
`tests/defensia/test_defensia_endpoints.py`. Verificado que **8 de los 15
fallan** al revertir `app/` a `main`, así que son regresiones de verdad y no
tests vacíos. Los 7 restantes son guardas antifalso-positivo que deben pasar
en ambos lados.

El test `test_ningun_modulo_hardcodea_un_modelo_gemini` escanea `app/` en busca
de literales `"gemini-*"` fuera de `config.py`: impide que vuelva a colarse un
id de modelo incrustado.

---

## Bug 109 — El merge del PR #17 dejó DOS implementaciones de `detect()` superpuestas

**Archivo**: `backend/app/security/pii_detector.py`

**Cuándo**: horas después de mergear el PR #22 (bug 105), al mergear el PR #17
(`demo/fiscal-ia-melilla` completa) sobre `main`.

**Síntoma en producción**: *"¿Cuánto IRPF pago si gano 30000 EUR en Madrid?"*
—una pregunta central del producto— se rechazaba como PII (`Código Postal`), y
Groq ni se llegaba a llamar (0 invocaciones).

**Causa raíz**: git fusionó **sin conflicto** dos versiones distintas de la
misma función, porque estaban en puntos diferentes de `detect()`:

1. La de la rama demo: `_regex_only()` primero y `return` inmediato ante
   cualquier match, `postal_code` incluido.
2. La del bug 105: Groq primero y override solo con `_HIGH_CONFIDENCE_PII`.

La (1) corta antes, así que la (2) quedó como **código muerto**. El guard de
alta confianza seguía en el fichero, pero no se ejecutaba nunca.

**Fix**: eliminar el bloque de cortocircuito. Queda solo la union.

**Cómo se detectó**: `test_importes_no_se_confunden_con_codigo_postal` (añadido
en el PR #22) empezó a fallar al rebasar otra rama sobre el `main` nuevo. Sin
ese test la regresión habría vivido en producción indefinidamente: no lanza
excepción, no aparece en logs de error, solo rechaza preguntas legítimas.

**Lección 1 — verificar presencia NO es verificar comportamiento.** Tras el
merge comprobé que `_HIGH_CONFIDENCE_PII` seguía en `main` con `grep -c` y di
los fixes por supervivientes. Estaba, pero inerte. Un `grep` demuestra que el
texto existe, no que se ejecute. **Para dar por bueno un fix tras un merge hay
que ejecutar su test, no buscar su código.**

**Lección 2 — un merge sin conflictos no es un merge correcto.** Dos ramas que
arreglan el mismo bug de formas distintas se superponen en silencio si tocan
líneas diferentes. Al mergear una rama larga que ha arreglado cosas en
paralelo, hay que revisar a mano las funciones que ambas tocaron.

**Lección 3 — afirmar sobre el efecto observable, no solo sobre el veredicto.**
El test nuevo `test_el_regex_no_cortocircuita_la_consulta_al_llm` comprueba que
`create.call_count == 1`, o sea que **se consultó al LLM**. Es lo único que
distingue "el regex no encontró nada" de "el regex cortocircuitó", y por tanto
lo único que detecta la recaída.

---

## Bug 110 — El Dockerfile de Coolify tumbó el despliegue de Railway

**Archivos**: `backend/Dockerfile`, `railway.toml`

**Síntoma**: build OK, `Healthcheck failed! 1/1 replicas never became healthy`,
con `Attempt #1 failed with service unavailable`. Deploy del 2026-08-09 21:47.

**Causa raíz** (cadena de tres pasos):

1. El PR #17 mergeó `demo/fiscal-ia-melilla` completa, y con ella
   `backend/Dockerfile` — creado en el commit `6814835`
   *"build(demo): backend Dockerfile + dockerignore **for Coolify deploy**"*.
   Antes de ese merge **`main` no tenía Dockerfile**.
2. Railway lo detectó y construyó con él en vez de con Railpack. La doc oficial
   es explícita: *"Railway will always build with a Dockerfile if it finds
   one"* — el `builder = "RAILPACK"` de `railway.toml` **no lo evita**. El log
   del build lo confirma: `load build definition from backend/Dockerfile`.
3. Ese Dockerfile estaba escrito para Coolify, donde el puerto es fijo, así que
   hardcodea `--port 8000`. Railway inyecta `PORT` y enruta ahí. La app
   escuchaba en 8000, Railway preguntaba en `$PORT` → *service unavailable*.
   La doc de healthchecks lo dice literalmente: no escuchar en `PORT` "can
   result in your health check returning a `service unavailable` error".

El `railpack.json` (inactivo desde entonces) sí lo hacía bien:
`--port $PORT`. Al pasar a Dockerfile se perdió esa pieza sin que nadie lo
notara, porque el comando de arranque vive ahora en otro fichero.

**Fix**: `CMD` en forma shell con `${PORT:-8000}`, de modo que el mismo
artefacto sirva para las dos plataformas — Railway usa el puerto inyectado y
Coolify/compose caen al 8000. Igual en el `HEALTHCHECK`.

**Segundo problema, latente**: `healthcheckTimeout = 30`, cuando el default de
Railway es **300**. El arranque importa `agent_framework` y modelos de
embeddings y tarda ~1-2 min (medido: la app respondió 200 en `/health` tras
~90 s en local). Con 30 s, cualquier lentitud extra marca el deploy como
fallido aunque esté levantando bien. Subido a 300.

**Verificación**: no se pudo construir la imagen (el daemon de Docker no estaba
arrancado), así que se verificó (a) que la app arranca y `/health` devuelve 200
respetando el `--port` que se le pasa, y (b) que `${PORT:-8000}` expande a
`4321` con `PORT=4321` y a `8000` sin la variable, tanto en el `CMD` como en el
`HEALTHCHECK`.

**Lección**: al mergear una rama de despliegue distinto, los ficheros de
infraestructura (`Dockerfile`, `docker-compose.yml`, `*.toml`) son tan
peligrosos como el código. Un Dockerfile pensado para una plataforma **secuestra
el build de la otra en silencio**, porque su detección tiene prioridad sobre la
configuración declarada. Antes de mergear una rama de otro despliegue: revisar
qué ficheros de infra trae y si alguno cambia el builder efectivo.

### ⚠️ CORRECCIÓN (2026-08-11): la causa raíz de arriba es FALSA

El fix de este Bug 110 se mergeó (PR #24, `c0868bd`, committer date
2026-08-10T22:30:37Z; el build arranca 20 s después) y el deploy
siguiente **volvió a caer**, esta vez los dos servicios. Con el log de ese
deploy en la mano, dos afirmaciones del apartado anterior no se sostienen:

1. **«La app escuchaba en 8000 y Railway preguntaba en `$PORT`»** — no.
   `backend/railway.toml` ya definía `startCommand` con `--port $PORT`, y el
   start command de Railway **pisa el `CMD` de la imagen**. El puerto fijo del
   `CMD` de Coolify nunca llegó a ejecutarse en Railway. Prueba directa: el
   deploy del 2026-08-10 llevaba ya el `CMD` con `${PORT:-8000}` y cayó igual.
2. **«`healthcheckTimeout` 30 → 300»** — se cambió en el `railway.toml` de la
   **raíz**, que el backend no lee. El log del deploy posterior sigue diciendo
   `Retry window: 30s`, el valor de `backend/railway.toml`, que el fix no tocó.

3. **«El log del build lo confirma: `load build definition from
   backend/Dockerfile`»** — esa línea **no aparece** en el export (1001 líneas,
   empieza a mitad de un `apt-get`). Lo que sí lo confirma son las etapas
   `[builder 5/5] RUN pip install --user -r requirements.txt` y
   `[runtime 5/5] COPY . .`, que casan 1:1 con `backend/Dockerfile:20,36,39`.
4. **«El arranque carga modelos de embeddings»** — no hay modelos locales.
   `requirements.txt` no trae torch, sentence-transformers, transformers ni
   fastembed: los embeddings van por API de OpenAI + Upstash Vector. Lo que
   tarda es el import de `app.main` (~10 s) y el `init_schema` contra Turso.
5. **«`railpack.json` sí lo hacía bien y al pasar a Dockerfile se perdió esa
   pieza»** — falso: el `startCommand` con `$PORT` vivía (y vive) en
   `backend/railway.toml` desde `eb41704`. No cambió *dónde* estaba el comando,
   sino **cómo lo ejecuta Railway** (shell con Railpack, exec form con Docker).

Lo que sí era correcto: que 30 s se quedaban cortos. Pero se arregló en el
fichero equivocado, y **el motivo por el que de pronto se quedaron cortos era
otro** (Bug 112).

**Verificación de aquel fix, releída**: sólo comprobó que `${PORT:-8000}` se
expande en el `CMD` — y el `CMD` **no se ejecuta en Railway** mientras
`backend/railway.toml` defina `startCommand`. Es decir: se verificó el arranque
de Coolify y se dio por verificado el de Railway.

---

## Bug 111 — un commit de deploy, dos servicios caídos

**Archivos**: `railway.toml` (raíz), `backend/railway.toml`

**Síntoma**: tras mergear el PR #24 (`c0868bd`, 2026-08-10 22:30:37Z), Railway lanzó build de
los dos servicios a las 22:30:57Z y murieron los dos:

- **Frontend**: `couldn't locate a dockerfile at path /frontend/Dockerfile in
  code archive`. Ni siquiera llegó a compilar.
- **Backend**: build OK, imagen subida, y `Retry window: 30s` →
  `Attempt #1/#2 failed with service unavailable` → `1/1 replicas never became
  healthy!`.

**Causa raíz — cada servicio lee un fichero de config distinto**:

| Servicio | Root Directory | Config que aplica |
|----------|----------------|-------------------|
| frontend | `/frontend` | `railway.toml` de la **raíz** del repo |
| backend  | `/backend`  | `backend/railway.toml` |

Doc oficial de monorepos, literal: *"The Railway Config File does not follow the
Root Directory path. You have to specify the absolute path for the
`railway.json` or `railway.toml` file"*. Es un ajuste **por servicio**; el
frontend se quedó con el valor por defecto (el de la raíz) y el backend apunta
al suyo.

Ese `railway.toml` de la raíz fue históricamente la config del backend, cuando
se construía desde `/` con Railpack (`7e892c2`, `1b3a673`, `3befb0e`). Nadie
actualizó el comentario cuando el backend se mudó a `/backend`, así que el PR
#24 lo editó creyendo que tocaba el backend. Efectos cruzados:

- `builder = "DOCKERFILE"` → se lo comió el **frontend**, que no tiene
  Dockerfile. Doc de Dockerfiles: *"Railway will look for and use a `Dockerfile`
  at the root of the source directory"*; con source dir `/frontend`, la ruta
  resuelta es exactamente la del error. Verificado: `frontend/Dockerfile` no ha
  existido **nunca** en ninguna rama (`git log --all --name-only | grep -i
  dockerfile` → solo `backend/Dockerfile` y un `Dockerfile` de raíz borrado en
  2025-12).
- `healthcheckTimeout = 300` → **no llegó al backend**, que siguió con 30.

**Fix**:
- `railway.toml` (raíz) vuelve a `builder = "RAILPACK"`, `healthcheckPath = "/"`
  (SPA: el fallback a `index.html` devuelve 200) y queda encabezado con un aviso
  de que es el fichero del FRONTEND.
- `backend/railway.toml` se queda con toda la config de backend:
  `healthcheckTimeout = 300`, `builder = "DOCKERFILE"` (que es lo que Railway
  hace de verdad) y sin `buildCommand` (lo ignora el builder de Docker).
- `healthcheckTimeout = 300` en **los dos** ficheros: si mañana cambia qué
  config aplica a cada servicio, el valor sigue siendo el bueno.

**El sospechoso principal del backend, que nadie había mirado: el
`startCommand` en exec form.** Citas literales de
`docs.railway.com/guides/start-command`:

> *"the start command overrides the image's `ENTRYPOINT` in exec form"*
> *"commands ran in exec form do not support variable expansion"*
> Patrón recomendado por la propia doc: `/bin/sh -c "exec python main.py --port $PORT"`
> Y sobre Railpack: *"the start command is ran in a shell process. This supports
> the use of environment variables without needing to wrap your command in a shell."*

`backend/railway.toml` traía `startCommand = "uvicorn ... --port $PORT ..."`
desde `86ede74` (2026-04-09) y funcionaba **porque el builder era Railpack**,
que lo ejecuta en shell. `backend/Dockerfile` entró en main con el PR #17
(`dc41b8b`, **2026-08-09 21:06**) y cambió el builder a Docker → el mismo start
command pasa a exec form → uvicorn recibe la cadena literal `"$PORT"` y muere en
el parseo de argumentos (`Error: Invalid value for '--port': '$PORT' is not a
valid integer`, reproducido en local), **antes incluso de importar la app**:
cero stdout, cero traceback y el edge respondiendo `service unavailable`.

Esto explica lo que "la app va lenta" no explica: **por qué rompió justo ese
día**. El coste del arranque no cambió el 2026-08-09; el builder sí.

Fix: `startCommand = '/bin/sh -c "exec uvicorn ... --port ${PORT:-8000} ..."'`,
que es literalmente el patrón de la doc. Se mantiene explícito en vez de
borrarlo porque la config-as-code gana al dashboard, así que además neutraliza
cualquier start command que quedara puesto a mano ahí.

**Honestidad sobre la evidencia**: no está *probado* que esto fuera lo que pasó.
El export de logs es 100 % build (`deploymentInstanceId: null`,
`source: buildkit`); no hay una sola línea de runtime. Lo seguro es que la
combinación *builder DOCKERFILE + `$PORT` desnudo* **no puede funcionar** según
la doc del proveedor. Para confirmarlo hacen falta los **Deploy Logs** (no los
Build Logs) y buscar `is not a valid integer`.

**Lección**: en un monorepo, un fichero de config en la raíz **no es de nadie en
particular**. Antes de tocarlo, comprobar en el log de qué servicio salieron los
valores que estás cambiando. La prueba de que el backend no leía la raíz estaba
en una sola línea del log (`Retry window: 30s` con la raíz ya en 300) y no se
miró.

---

## Bug 112 — `pymupdf4llm` sin pinear se comió la ventana del healthcheck

**Archivo**: `backend/requirements.txt`

**Por qué importa**: es el motivo de que 30 s de healthcheck, que llevaban meses
bastando, dejaran de bastar de un día para otro **sin que nadie tocara el
código de arranque**.

**Cadena**:

1. `requirements.txt:34` decía `pymupdf4llm>=0.2.6`, rango abierto.
2. `pymupdf4llm 1.28.2` se publicó en PyPI el **2026-08-06**. Su metadata pina
   `pymupdf==1.28.2` y `pymupdf_layout==1.28.2` (wheel de **42,9 MB**, con ~50
   MB de modelos `.onnx`) y arrastra `onnxruntime`. El primer build limpio
   posterior se lo tragó solo: el log de Railway lo enseña —
   `Downloading pymupdf_layout-1.28.2 ... (42.9 MB)`,
   `Successfully installed ... pymupdf-1.28.2 pymupdf4llm-1.28.2
   pymupdf_layout-1.28.2 onnxruntime-1.28.0`. El primer deploy caído es del
   2026-08-09, tres días después de esa release.
3. En esa versión el **import** ya construye las sesiones ONNX de análisis de
   layout (`pymupdf4llm/__init__.py` → `pymupdf.layout.activate()` →
   `DocumentLayoutAnalyzer.get_model()`), no bajo demanda. Medido en un venv con
   las versiones exactas que instaló Railway: **+112 MB de RSS** solo por el
   import.
4. Ese coste lo paga **todo arranque del backend**, no solo quien suba un PDF:
   `app/main.py:27` importa el router de notificaciones →
   `routers/notifications.py:18` → `agents/notification_agent.py:23
   import pymupdf4llm`, a nivel de módulo y **sin `try/except`**.

Sumado a lo que ya costaba el arranque (`import app.main` ≈ 9-11 s, y un
`init_schema` que son ~79 statements CREATE/ALTER, cada uno con su `commit()` →
~158 round trips HTTP contra Turso remoto **antes** de que uvicorn acepte
conexiones), la ventana de 30 s era imposible.

**Fix**: pin exacto a las versiones contra las que corren los tests —
`pymupdf4llm==0.2.9` y `pymupdf==1.26.7`.

**Bomba latente desactivada de paso**: el `__init__.py` de la línea 1.x hace
`if _pvt != VERSION_TUPLE: raise ImportError(...)`. Con los dos rangos abiertos,
cualquier resolución dispar de pip rompía el import de **la aplicación entera**,
con el mismo síntoma de log (imagen construida, contenedor que no escucha).

**Pendiente (no incluido)**: evaluar si interesa subir a la línea 1.28 por la
mejora de extracción de layout. Si se sube, hay que (a) medir el arranque y
subir el healthcheck en consecuencia, (b) vigilar la memoria — Railway ya iba a
~344 MB por worker y esto suma ~112 MB, y (c) mover
`import pymupdf4llm` dentro de la función que lo usa, para que el coste lo pague
quien analiza un PDF y no cada arranque. Un hotfix de producción no es el sitio.

**Regla permanente**: una dependencia con rango abierto es un **deploy que no
has revisado**, programado para el día que el upstream publique. Para las que se
importan en el camino de arranque, pin exacto.

---

## Bug 113 (menor, latente) — `.railwayignore` excluía `backend/data/`

**Archivo**: `.railwayignore`

`data/` sin barra inicial, con semántica `.gitignore`, excluye **cualquier**
carpeta `data` del repo — también `backend/data/legal/` (corpus legal:
`norms.yaml`, `articles.yaml`). No tumba la app porque
`get_legal_registry()` captura `LegalDataError` y devuelve un registro vacío
degradado, pero significa **enlaces al BOE y verificación de citas silenciosamente
apagados** si ese fichero llega a aplicarse.

Fix: dejar solo `/data/`, anclado a la raíz, que es lo que se quería excluir
(los PDFs y los índices FAISS pesados).

Nota medida: comparando el tamaño del archivo que subió Railway
(103.567.360 bytes) con el tar del árbol completo (103.512.576, −0,05 %) frente
al que resultaría de aplicar `.railwayignore` (99.698.688, −3,74 %), **ese
fichero no se está aplicando** en los builds actuales. El arreglo es correcto
igualmente, pero no esperes que cambie nada hasta que Railway lo lea.

---

## Lección transversal

Una rama de larga duración para una marca blanca **acumula arreglos genéricos
que nadie retropropaga**. El coste no se ve hasta que se audita la divergencia.

Mitigación adoptada: reducir `demo/fiscal-ia-melilla` a diferencias de
configuración (env vars) para que no vuelva a haber sitio donde esconder un
bugfix genérico. Ver el plan de separación en
`../IA-Melilla/memory/MEMORY.md`.

Regla operativa: **antes de dar por cerrada cualquier sesión sobre la rama
demo, diffear los ficheros de `app/security/`, `app/agents/` y `app/services/`
contra `main` y decidir explícitamente qué vuelve.**
