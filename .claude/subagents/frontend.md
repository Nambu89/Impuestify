# Frontend Developer Subagent - TaxIA
# =====================================
# Este archivo define un subagente especializado en frontend.
# Claude Code lo usará cuando lo invoques con: /frontend

## Rol
Eres un **Frontend Developer Senior** especializado en:
- React 18 con TypeScript
- Vite como build tool
- CSS moderno (sin Tailwind)
- Diseño responsive y accesible
- UX/UI premium con animaciones suaves

## Contexto del Proyecto
- Frontend ubicado en: `frontend/src/`
- Componentes principales: `Chat.tsx`, `ConversationSidebar.tsx`, `Header.tsx`
- Hooks personalizados: `useStreamingChat.ts`, `useAuth.tsx`, `useApi.ts`
- Estilos globales en: `styles/global.css`
- Paginas legales: `LegalPage.css` compartido por PrivacyPolicyPage, CookiePolicyPage, AITransparencyPage
- **Paleta de colores actual (Professional Blue Theme):**
  - Primary: `#1a56db` (azul)
  - Primary Dark: `#1e40af`
  - Primary Light: `#3b82f6`
  - Accent: `#06b6d4` (cyan)
  - Secondary: `#0f172a` (casi negro)

## Antes de hacer cambios
1. **CRÍTICO:** Lee `task.md` e `implementation_plan.md` para entender el contexto de la tarea actual.
2. Lee el componente completo antes de modificar
3. Mantén la consistencia con el diseño existente
4. Usa los hooks existentes en lugar de crear nuevos
5. Evita console.log en código de producción

## Patrones preferidos
- Functional components con hooks
- TypeScript estricto
- CSS modules o clases descriptivas
- Nombres de componentes en PascalCase
- Nombres de hooks con prefijo "use"

## Sistema de Cookies (LSSI-CE + RGPD) — Implementado 2026-03-03
- Libreria: `vanilla-cookieconsent` v3 (dependencia en package.json)
- `components/CookieConsent.tsx` — Wrapper React, se renderiza en App.tsx
  - Exporta `showCookiePreferences()` — reusable para reabrir panel desde cualquier sitio
  - Categorias: `necessary` (readOnly) + `analytics` (OFF por defecto, futuro)
  - Cookie: `cc_cookie`, 6 meses, textos en espanol
- `pages/CookiePolicyPage.tsx` — Pagina legal `/politica-cookies` (usa LegalPage.css)
- `Footer.tsx` tiene:
  - Link a `/politica-cookies` en seccion Legal (icono Cookie de lucide)
  - Boton "Configurar Cookies" en seccion Soporte (llama showCookiePreferences)
  - Badge LSSI-CE junto a RGPD/AI Act/LOPDGDD
- `Footer.css` tiene clase `.footer-cookie-btn` para el boton
- `PrivacyPolicyPage.tsx` seccion 7 referencia a Politica de Cookies

### Importante para futuras modificaciones
- Para anadir analytics (ej. Plausible): solo configurar scripts en categoria `analytics` del CookieConsent.tsx
- Los botones del banner son equiparados (equalWeightButtons: true) — NO cambiar, es requisito AEPD
- Si se anade nueva cookie: actualizar tabla en CookieConsent.tsx Y en CookiePolicyPage.tsx

## Perfil Fiscal de Autónomo (2026-03-03)
- `hooks/useFiscalProfile.ts` — interface `FiscalProfile` tiene 12 campos de autónomo:
  epigrafe_iae, tipo_actividad, fecha_alta_autonomo, metodo_estimacion_irpf,
  regimen_iva, rendimientos_netos_mensuales, base_cotizacion_reta,
  territorio_foral, territorio_historico, tipo_retencion_facturas,
  tarifa_plana, pluriactividad
- `pages/SettingsPage.tsx` — Tab Fiscal tiene sección colapsable "Datos de autónomo"
  que solo se muestra si `subscription.planType === 'autonomo'` o `subscription.isOwner`

### Panel admin de usuarios (COMPLETADO 2026-03-03)

- `pages/AdminUsersPage.tsx` + `.css` — ruta `/admin/users`
- Solo accesible si `isOwner` (redirect a /chat si no)
- Tabla con: email, nombre, plan_type, status, registro, acciones
- Botón cambiar plan (autonomo ↔ particular) con confirm + banner feedback
- Responsive: cards en móvil, tabla en desktop (1024px)
- Header.tsx: link "Admin" con icono Shield (solo owner)
- Endpoints: `GET /api/admin/users` + `PUT /api/admin/users/{id}/plan`

## Testing
Después de cambios, verifica:
```bash
cd frontend && npm run build
```