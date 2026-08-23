# Bugfixes — Junio/Julio 2026

## Bug 103 — Ruta `/gestoria/clientes` accesible por cuentas no-gestoría (route guard faltante)

**Fecha:** 2026-07-02
**Severidad:** Baja (pulido UX / defence-in-depth — NO fuga de datos)
**Detectado en:** QA end-to-end en navegador del Modo Gestoría (prueba real como usuario).

### Síntoma
Un usuario con `account_type != 'gestoria'` (p.ej. `individual`) que tecleaba la URL `/gestoria/clientes` a mano **llegaba a la página** y se renderizaba (h1 "Clientes" + formulario "Nuevo cliente"). El enlace de nav "Clientes" ya estaba oculto para no-gestorías, pero la ruta en sí no estaba gateada por `account_type`.

### Causa raíz
La feature solo ocultaba la entrada de navegación (`Header.tsx`) y protegía la API (`require_gestoria` → 403 en todo `/api/gestoria/*`), pero el componente de página `GestoriaClientesPage` no comprobaba `account_type`. `ProtectedRoute` solo valida auth + suscripción, no el tipo de cuenta.

**NO era fuga de seguridad:** el backend responde **403** en cada endpoint `/api/gestoria/*`, así que un no-gestoría no podía leer/crear/editar/borrar clientes. La página se veía pero no funcionaba (todas las llamadas fallaban). Puro pulido UX.

### Fix (commit `aa25a21`, PR #21, merge `4118968`)
`frontend/src/pages/GestoriaClientesPage.tsx`:
- Import `useAuth` + `Navigate` (react-router-dom).
- `const { user } = useAuth()`.
- Guard antes del `return` principal (tras TODOS los hooks, para no violar rules-of-hooks):
  ```tsx
  if (user && user.account_type !== 'gestoria') {
      return <Navigate to="/chat" replace />
  }
  ```
- Guard solo dispara cuando `user` está cargado (evita redirigir durante el loading inicial en que `user` es null).

### Verificación (navegador)
- No-gestoría → `/gestoria/clientes` redirige a `/chat`. ✅
- Gestoría → accede normal (roster, form, nav visibles). ✅
- `npm run build` limpio. ✅
- Backend `pytest -k gestoria` 26/26. ✅

### Regla permanente (anti-recurrencia)
Toda ruta exclusiva de un `account_type` (o rol) debe gatearse en **3 capas**: (1) ocultar nav, (2) guard de ruta/componente que redirige, (3) backend 403. Ocultar el nav NO basta — la URL directa sigue alcanzable. Documentado en `frontend/CLAUDE.md`.

### Lección de proceso — QA con subagente
El agente `qa-tester` **NO hereda el MCP Playwright** (está ligado a la sesión principal interactiva) → cayó a análisis estático en vez de conducir el navegador. Para QA de navegador real hay que conducir Playwright **desde la sesión principal**, autenticando vía **inyección de token JWT en localStorage** (el login tiene CAPTCHA Cloudflare Turnstile que bloquea el form automatizado).
