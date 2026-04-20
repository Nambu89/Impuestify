---
name: Always research before acting
description: MUST research solutions online before implementing anything. Never assume, always investigate first.
type: feedback
---

SIEMPRE investigar soluciones en la web (WebSearch, documentación oficial, GitHub issues, Stack Overflow) ANTES de escribir código o proponer cambios.

**Why:** El usuario se frustra enormemente cuando se asumen soluciones sin investigar. Ha dado esta instrucción repetidamente.

**How to apply:** Ante cualquier problema:
1. PRIMERO buscar en la web cómo otros devs lo han resuelto
2. Leer documentación oficial del servicio/librería involucrada
3. Comparar múltiples soluciones
4. SOLO ENTONCES proponer/implementar la mejor opción
5. NUNCA saltar directamente a escribir código sin investigar

**Caso concreto (2026-03-28 sesión OpenClaw):**
Se asumieron los parámetros de `upload_post.UploadPostClient.upload_photos()` SIN consultar PyPI, causando 4 iteraciones fallidas. Se asumió la URL del API (`app.upload-post.com`) en vez de verificar en el código fuente del SDK (`api.upload-post.com`). Esto costó ~1 hora de debugging innecesario.

**Regla reforzada:** Para CUALQUIER SDK/API:
- WebFetch a la documentación de PyPI/npm/GitHub ANTES de escribir una sola línea
- Si el SDK está instalado, hacer `help(Clase.metodo)` o `inspect.getsource()` para ver la firma real
- NUNCA asumir nombres de parámetros, URLs de endpoints, o formatos de respuesta
