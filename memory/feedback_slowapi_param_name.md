---
name: slowapi-param-must-be-named-request
description: "slowapi rate limiter inspecciona params por nombre. Primer param de handler con `@limiter.limit(...)` DEBE llamarse `request: Request`, no `req` ni `r`."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8080b03d-745c-403d-b45b-88240e4dcb6d
---

slowapi rate limiter inspecciona los argumentos del handler por nombre. Si el primer parámetro `Request` no se llama exactamente `request`, lanza error en runtime al recibir tráfico (no en startup).

**Why:** Sesión 44 deploy demo Coolify. Endpoint `/api/ask` y `/api/ask/stream` crasheaban con error slowapi al primer mensaje real. El handler tenía `req: Request` por convención cómoda. slowapi `@limiter.limit(...)` busca literalmente `request` en la firma. Commits `8eec52c` + `af205b5` corrigieron: rename `req`→`request` y mover el body Pydantic a otro nombre (`body`/`data`).

**How to apply:**
- Cualquier handler FastAPI decorado con `@limiter.limit(...)` o `@limiter.shared_limit(...)`: primer param obligatorio `request: Request` (nombre exacto, lowercase).
- Si necesitas el body Pydantic, NO lo llames `request` — usar `body: SchemaModel`, `data: SchemaModel`, o nombre temático.
- Hacer grep `@limiter\.` en cualquier refactor de firmas de handlers. Reescribir nombre de param sin verificar = bug en producción.
- Regla ya documentada en `CLAUDE.md` (sección Reglas de proceso): "slowapi: Primer param DEBE ser `request: Request`, body Pydantic como `body`/`data`".
