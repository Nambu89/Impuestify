---
name: No browser console
description: User cannot execute JavaScript in browser console (F12). Never suggest this approach.
type: feedback
---

El navegador del usuario tiene BLOQUEADA la consola (F12) por seguridad. NO se pueden ejecutar comandos JavaScript en la consola del navegador. NUNCA sugerir `fetch()` en consola, ni Playwright login, ni nada que dependa del navegador.

**Why:** El usuario lo ha dicho MUCHAS veces y es una restricción de seguridad de su entorno. No es negociable.

**How to apply:** Para operaciones admin en producción, usar SOLO: (1) Railway CLI (`railway`), (2) scripts backend que se ejecutan en local con credenciales de .env, (3) endpoints públicos sin auth, o (4) código que se deploya y ejecuta en el startup del servidor. NUNCA: consola del navegador, Playwright login, ni pedir al usuario que haga nada en el navegador.
