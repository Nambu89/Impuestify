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
| `useAuth` | hooks/useAuth.tsx | Auth context (login, logout, token management). User includes `is_owner`, `subscription_status` |
| `useApi` | hooks/useApi.ts | Axios instance with automatic token refresh (401 → refresh → retry) |
| `useConversations` | hooks/useConversations.ts | Conversation CRUD operations |
| `useStreamingChat` | hooks/useStreamingChat.ts | SSE v3.0: `content_chunk` append + `content` replace. `responseAccRef` (useRef) avoids stale closures. `TimelineStep[]` for StreamingTimeline |
| `useWorkspaces` | hooks/useWorkspaces.ts | Workspace CRUD, file upload, active workspace state |
| `useSubscription` | hooks/useSubscription.ts | Stripe: status, createCheckout, openPortal |
| `useFiscalProfile` | hooks/useFiscalProfile.ts | Fiscal profile CRUD (12 autonomo fields) |

## Key Components

| Component | Purpose |
|-----------|---------|
| `Chat.tsx` | Main chat with SSE streaming, integrates DeductionCards + ReportActions |
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

## Common Frontend Tasks

**Add a new page:** Create `pages/MyPage.tsx`, add route in `App.tsx` inside `ProtectedRoute` (with `requireSubscription` if needed), add nav link in `Header.tsx`.

**Add a new hook:** Create `hooks/useMyHook.ts`, use `useApi()` for API calls with token refresh.

**Subscription guard:** Wrap route with `<ProtectedRoute requireSubscription>`. Settings page uses `requireSubscription={false}` so users can manage their subscription.

## PWA

- `public/manifest.json` — standalone, icons 192+512, lang es
- `public/sw.js` — manual SW (not vite-plugin-pwa). Network-first API, cache-first assets
- `src/main.tsx` — registers SW only in production (`import.meta.env.PROD`)
