# frontend/CLAUDE.md — Frontend Guide

## Stack & Setup

React 18 + Vite 5 + TypeScript 5.2. Custom CSS (NO Tailwind). Icons: Lucide React.

```bash
cd frontend && npm run dev   # Dev server on :5173
cd frontend && npm run build # Must pass before any commit
```

### Color Palette (CSS variables in styles/global.css)
- `--color-primary: #1a56db` | `--color-primary-dark: #1e40af` | `--color-primary-light: #3b82f6`
- `--color-accent: #06b6d4` | `--color-secondary: #0f172a`

## Custom Hooks

| Hook | File | Purpose |
|------|------|---------|
| `useAuth` | hooks/useAuth.tsx | Auth context (login, logout, token management). User includes `is_owner`, `subscription_status`, `subscription_plan` |
| `useApi` | hooks/useApi.ts | Axios instance with automatic token refresh (401 → refresh → retry) |
| `useConversations` | hooks/useConversations.ts | Conversation CRUD operations |
| `useStreamingChat` | hooks/useStreamingChat.ts | SSE v3.0: `content_chunk` append + `content` replace. `responseAccRef` (useRef) avoids stale closures. `TimelineStep[]` for StreamingTimeline |
| `useWorkspaces` | hooks/useWorkspaces.ts | Workspace CRUD, file upload, active workspace state |
| `useSubscription` | hooks/useSubscription.ts | Stripe: status, createCheckout, openPortal (Particular/Creator/Autonomo plans) |
| `useFiscalProfile` | hooks/useFiscalProfile.ts | Fiscal profile CRUD. Includes Phase 1+2 fields + `roles_adicionales` (non-exclusive) |
| `useIrpfEstimator` | hooks/useIrpfEstimator.ts | Debounced calls (600ms) to POST /api/irpf/estimate. Returns cuota, type ("a_pagar"/"a_devolver"), loading state |
| `useTaxGuideProgress` | hooks/useTaxGuideProgress.ts | 7-step wizard state with localStorage persistence for /guia-fiscal |
| `useFeedback` | hooks/useFeedback.ts | **NEW**: Feedback submission (rating, comment, metadata) with optimistic UI updates |
| `useFiscalFields` | hooks/useFiscalFields.ts | **NEW**: Dynamic form fields by CCAA/regime. Returns adaptive field schema |

## Key Components

| Component | Purpose |
|-----------|---------|
| `Chat.tsx` | Main chat with SSE streaming, integrates DeductionCards + ReportActions + FeedbackWidget |
| `FormattedMessage.tsx` | Pre-processes assistant content: strips raw JSON, IRPF→visual cards, emoji→callout boxes |
| `StreamingTimeline.tsx` | Vertical timeline (Brain/Wrench/CheckCircle2/PenLine icons) |
| `DeductionCards.tsx` | Auto-detects deduction content, parses markdown→eligible/possible arrays, CountUp savings |
| `ReportActions.tsx` | "Download PDF" + "Send to advisor" buttons (auto-detects IRPF simulation) |
| `ShareReportModal.tsx` | Email advisor modal (bottom-sheet mobile, popup desktop) |
| `ConversationSidebar.tsx` | Conversation history panel |
| `CookieConsent.tsx` | vanilla-cookieconsent v3 wrapper. Exports `showCookiePreferences()`. NEVER change `equalWeightButtons: true` (AEPD requirement) |
| `ProtectedRoute.tsx` | Auth + subscription guard. `requireSubscription={false}` for auth-only routes |
| `WorkspacesPage.tsx` | Workspace management + file list |
| `AdminUsersPage.tsx` | Owner-only user admin (/admin/users). Cards mobile, table desktop (1024px breakpoint) |
| `TaxGuidePage.tsx` | 7-step IRPF wizard (/guia-fiscal). Steps: personal, trabajo, ahorro, inmuebles, familia, deducciones, resultado. Protected route, lazy loaded |
| `LiveEstimatorBar.tsx` | Sticky bottom bar (mobile) / sidebar (desktop). Green = a devolver, red = a pagar. Powered by useIrpfEstimator |
| `FeedbackWidget.tsx` | **NEW**: Inline chat rating (stars 1-5) + comment modal after responses |
| `ChatRating.tsx` | **NEW**: Rating component with comment text + metadata checkboxes (useful, clear, sources) |
| `AdminFeedbackPage.tsx` | **NEW**: Owner-only page (/admin/feedback). Feedback aggregation, ratings chart, export CSV |
| `AdminContactPage.tsx` | **NEW**: Owner-only page (/admin/contacts). Contact form submissions |
| `AdminDashboardPage.tsx` | **NEW**: Owner-only page (/admin/dashboard). Overview: active users, subscriptions, feedback summary |
| `CreatorsPage.tsx` | **NEW**: Landing page for creators segment (/creadores-de-contenido). SEO-GEO optimized |
| `DynamicFiscalForm.tsx` | Adaptive form by CCAA/regime. `compact=true` mode filters base sections |
| `Header.tsx` | Navigation header. **NEW**: Admin dropdown for owner (Feedback, Contacts, Dashboard) |

## SSE Event Format

```typescript
// Event types from backend (chat_stream.py):
type SSEEventType = 'thinking' | 'tool_call' | 'tool_result' | 'content_chunk' | 'content' | 'done';

// Sequence: thinking* → tool_call → tool_result → content_chunk* → content (final) → done
// content_chunk: incremental text (append to accumulator)
// content: final authoritative text (replaces accumulated)
// done: triggers onComplete callback

// Example:
event: content_chunk
data: {"type": "content_chunk", "data": "La respuesta", "index": 0}
```

## React Bits Components

Location: `components/reactbits/` (local copies, NOT npm packages — this is how the library works).

Available: `CountUp.tsx`, `GradientText.tsx+css` (requires `motion` npm), `SpotlightCard.tsx+css`, `StarBorder.tsx+css`, `FadeContent.tsx` (custom IntersectionObserver, no GSAP).

To add new: `GET https://raw.githubusercontent.com/DavidHDev/react-bits/main/public/r/{Component}-TS-CSS.json`

## TypeScript Patterns

```typescript
// API response interface (always define)
interface ChatResponse {
  answer: string;
  sources: Source[];
  metadata: Record<string, any>;
}

// Error handling
try {
  const response = await api.post<ChatResponse>('/api/ask', { question });
  return response.data;
} catch (error) {
  if (axios.isAxiosError(error)) {
    throw new Error(error.response?.data?.error || 'Request failed');
  }
  throw error;
}
```

## Loading State (OBLIGATORIO)

En hooks async con estado `loading`, **TODA rama de ejecución** debe llamar `setLoading(false)` — incluyendo early returns y guards. Nunca dejar `loading = true` sin salida. Si hay un guard al inicio (`if (!isAuthenticated) return`), hacer `setLoading(false)` antes del return. Un `loading` que nunca se resetea = spinner infinito en la UI.

## Ortografía Española (OBLIGATORIO PRE-PUSH)

Todo texto visible al usuario DEBE llevar tildes correctas. **ANTES DE HACER PUSH**, auditar con grep TODOS los archivos tocados. Palabras que SIEMPRE llevan tilde:

`sesión, régimen, contraseña, período, próximo, máximo, mínimo, válido, días, año, también, además, aquí, según, dirección, descripción, declaración, estimación, deducción, sección, obligación, información, única, más, aún, acción, límite, archipiélago, Unión, cálculo, método, número, teléfono, código, básico, único, técnico, económico, último, página, configuración, clasificación, resolución, conservación, penúltimo, creador, influencer`

**NO confundir** variables JS (`data.regimen`, `contrasena` como key) con texto visible (`"Régimen"`, `"Contraseña"`). Solo corregir strings entre comillas que el usuario ve en pantalla.

**Audit command:**
```bash
# Before push, search for common misspellings
grep -r "regimen" frontend/src --include="*.tsx" --include="*.ts" | grep -v "data\." | grep -v "_" # Check for "régimen"
grep -r "contrasena" frontend/src --include="*.tsx" --include="*.ts" | grep -v "data\." # Check for "contraseña"
```

## DynamicFiscalForm: Modo Compact (OBLIGATORIO)

Cuando `DynamicFiscalForm` se usa con `compact=true` (en TaxGuidePage y SettingsPage), las **secciones base** se filtran automáticamente para evitar campos duplicados. Las secciones filtradas son: `datos_personales`, `rendimientos_trabajo`, `rendimientos_ahorro`, `inmuebles`, `familia`, `discapacidad`, `reducciones`, `criptomonedas`, `apuestas_juegos`, `ganancias_patrimoniales_financieras`, `actividad_economica`. Solo se muestran secciones CCAA-específicas (vivienda Sprint 1, donaciones, sostenibilidad, territorio, deducciones_autonomicas, forales). Si se añade una nueva sección base al backend, **añadirla también a `BASE_SECTION_IDS`** en `DynamicFiscalForm.tsx`.

## Markdown Rendering Rules

- **ALWAYS** use `remarkPlugins={[remarkGfm]}` on every `<ReactMarkdown>` component (tables, strikethrough, task lists need it)
- **NEVER** use `white-space: pre-wrap` on containers that hold ReactMarkdown output (causes double line breaks)
- Table, code block, blockquote styles are in `Chat.css` under `.message-text` selectors

## Common Frontend Tasks

**Add a new page:** Create `pages/MyPage.tsx`, add route in `App.tsx` inside `ProtectedRoute` (with `requireSubscription` if needed), add nav link in `Header.tsx`.

**Routes (App.tsx):** `/` (landing), `/login`, `/register`, `/chat`, `/workspaces`, `/settings`, `/subscribe`, `/guia-fiscal` (lazy, protected), `/creadores-de-contenido` (marketing landing), `/admin/users` (owner-only), `/admin/feedback` (owner-only), `/admin/contacts` (owner-only), `/admin/dashboard` (owner-only).

**Add a new hook:** Create `hooks/useMyHook.ts`, use `useApi()` for API calls with token refresh.

**Subscription guard:** Wrap route with `<ProtectedRoute requireSubscription>`. Settings page uses `requireSubscription={false}` so users can manage their subscription.

## PWA

- `public/manifest.json` — standalone, icons 192+512, lang es
- `public/sw.js` — manual SW (not vite-plugin-pwa). Network-first API, cache-first assets
- `src/main.tsx` — registers SW only in production (`import.meta.env.PROD`)
