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
