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

## Export PDF + Enviar a Asesor (2026-03-05)

- `components/ReportActions.tsx` + `.css` — Botones "Descargar PDF" + "Enviar a asesor"
  - Se muestra automáticamente debajo de mensajes assistant con simulación IRPF
  - Detección por keywords: >=2 de (cuota íntegra, cuota líquida, tipo efectivo, base liquidable, simulación irpf)
  - Extrae CCAA e ingresos del contenido del mensaje + pregunta del usuario
  - `POST /api/export/irpf-report` (blob PDF) → descarga directa
  - Guarda `X-Report-Id` del response header para compartir
  - Responsive: solo iconos en mobile (<768px), icono+texto en tablet+
- `components/ShareReportModal.tsx` + `.css` — Modal para enviar informe al asesor
  - Input email + textarea mensaje opcional (500 chars)
  - `POST /api/export/share-with-advisor` con report_id + advisor_email
  - Maneja 503 gracefully (Resend no configurado)
  - Bottom-sheet en mobile (<480px), popup centrado en desktop (max-width 480px)
- `pages/Chat.tsx` — Integra `ReportActions` + `isIRPFSimulation` (exportada desde ReportActions)
  - Se renderiza debajo de sources en mensajes assistant
  - Pasa previousUserMessage como contexto para extracción de parámetros

### Importante para futuras modificaciones
- `isIRPFSimulation()` es exportada: se puede reusar desde otros componentes
- Si se cambian las keywords de detección, actualizar el array SIMULATION_KEYWORDS en ReportActions.tsx
- Los endpoints de export requieren JWT (mismos tokens que el resto de la app)
- El botón "Enviar a asesor" solo aparece después de descargar el PDF (necesita reportId)

## React Bits — Componentes locales (2026-03-05)

Componentes copiados de [reactbits.dev](https://reactbits.dev) en `components/reactbits/`.
**NO son un paquete npm** — son archivos locales que se copian del repo GitHub `DavidHDev/react-bits`.

### Componentes disponibles
- `CountUp.tsx` — Contador animado (0→N). Dep: `motion/react`. Locale: 'es-ES'. Usa useInView + useSpring.
- `GradientText.tsx` + `.css` — Texto con gradiente animado. Dep: `motion/react`. Usa `motion.span` (inline).
- `SpotlightCard.tsx` + `.css` — Tarjeta con efecto spotlight siguiendo cursor. Sin deps externas.
- `StarBorder.tsx` + `.css` — Borde animado tipo estrella. Sin deps externas.
- `FadeContent.tsx` — **Custom** (NO de React Bits). IntersectionObserver + CSS transitions. Sin deps.
  Props: blur, duration, delay, threshold, direction ('up'|'down'|'left'|'right'), distance.

### Dependencias npm
- `motion` (MIT) — requerido por CountUp y GradientText

### Donde se usan
- **Home.tsx**: GradientText (hero titulo), CountUp (stats), SpotlightCard (features + comparativa), StarBorder (CTA), FadeContent (todas las secciones)
- **DeductionCards.tsx**: CountUp (ahorro estimado), FadeContent (animacion entrada tarjetas)

### Para anadir nuevos componentes React Bits
1. Buscar el JSON en `https://raw.githubusercontent.com/DavidHDev/react-bits/main/public/r/{Component}-TS-CSS.json`
2. Copiar code + css a `components/reactbits/`
3. Adaptar CSS a variables del proyecto (--color-primary, --color-white, etc.)
4. Si requiere GSAP, crear alternativa custom con IntersectionObserver/CSS transitions

## PWA — Progressive Web App (2026-03-05)

### Archivos
- `public/manifest.json` — Metadata app (name, icons, display: standalone, lang: es)
- `public/sw.js` — Service Worker manual (NO vite-plugin-pwa):
  - Cache-first: assets estaticos (JS, CSS, imagenes, fuentes)
  - Network-first: llamadas API (/api/*, /auth/*, /health)
  - Precache: /, /offline.html, /favicon.svg, /icon-192.png
  - Cache name: `impuestify-v1` (incrementar al hacer breaking changes)
- `public/offline.html` — Pagina offline con boton retry
- `src/main.tsx` — Registro SW solo en produccion (`import.meta.env.PROD`)

### Favicon
- `public/favicon.svg` — SVG vectorial (cuadrado redondeado, gradiente primary→accent, escudo con "I")
- `public/favicon-32.png`, `icon-192.png`, `icon-512.png` — Generados con `npx sharp-cli`
- `index.html` tiene refs a SVG (principal) + PNG 32px (fallback) + apple-touch-icon 192px

### Para regenerar PNGs desde SVG
```bash
cd frontend
npx sharp-cli -i public/favicon.svg -o public/favicon-32.png resize 32 32
npx sharp-cli -i public/favicon.svg -o public/icon-192.png resize 192 192
npx sharp-cli -i public/favicon.svg -o public/icon-512.png resize 512 512
```

## DeductionCards — Tarjetas de deducciones en chat (2026-03-05)

- `components/DeductionCards.tsx` + `.css`
- Se muestra automaticamente en mensajes assistant que contienen deducciones
- Deteccion: `hasDeductions(content)` busca keywords como "deducciones a las que tienes derecho"
- Parsea markdown en datos estructurados: eligible[], possible[], totalSavings
- Cada tarjeta: icono por categoria (Lucide), nombre, importe, badge estado, descripcion, ref legal
- Banner ahorro estimado con CountUp animado
- Grid responsive: 1 col mobile, 2 cols tablet (768px), 3 cols desktop (1024px)
- Integrado en `pages/Chat.tsx` — se renderiza debajo de sources, encima de ReportActions

### Para modificar
- Keywords de deteccion: array `DEDUCTION_KEYWORDS` en DeductionCards.tsx
- Iconos por categoria: funcion `getCategoryIcon()` (mapea palabras clave a Lucide icons)
- Si cambia el formato markdown de deducciones del backend, actualizar `parseDeductions()`

## Landing Page — Home.tsx (2026-03-05)

Secciones (de arriba a abajo):
1. **Hero** — GradientText "Inteligente", badge "IA Fiscal Multi-Agente", chat preview
2. **Stats** — 4 CountUp: 428+ docs, 64 deducciones, 21 territorios, 24/7
3. **Cobertura Territorial** — Grid 21 chips (17 CCAA + 4 forales), forales con icono Map y estilo especial
4. **Comparativa** — 2 columnas: "Asistentes genericos" vs "Impuestify" (SpotlightCard)
5. **Features** — 3 SpotlightCards (Multi-Agente, 428+ Docs, Seguro y Privado)
6. **Pricing** — Plan Particular 5 EUR/mes con features actualizadas
7. **CTA** — StarBorder envolviendo call-to-action

### Datos hardcoded (actualizar si cambian)
- `TERRITORIES` array: 21 territorios con flag `foral` — si se anaden mas, actualizar aqui
- Stats: 428+ docs, 64 deducciones, 21 territorios — actualizar si cambia la base RAG/deducciones
- Pricing features list — sincronizar con backend si cambian features del plan

## Testing
Después de cambios, verifica:
```bash
cd frontend && npm run build
```