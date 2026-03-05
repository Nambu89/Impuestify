# Bugfixes Marzo 2026

## [2026-03-05] Renderizado markdown en chat

**Problema:** Las respuestas del agente con markdown (negritas, tablas, listas, encabezados) no se renderizaban correctamente. El texto se mostraba como raw markdown.

**Causa raiz (3 problemas):**
1. `white-space: pre-wrap` en `.message-text` (Chat.css:139) — preservaba saltos de linea raw, conflictuando con los `<p>`, `<ul>`, `<table>` que genera ReactMarkdown. Causaba doble espaciado y tablas rotas.
2. Sin plugin `remark-gfm` — react-markdown v10 NO incluye GFM por defecto. Sin el, tablas (`| col |`), tachado (`~~text~~`), task lists no se procesan.
3. Sin estilos CSS para tablas, bloques de codigo (`pre`), blockquotes, hr.

**Solucion:**
- `npm install remark-gfm`
- `FormattedMessage.tsx`: import remarkGfm, anadir `remarkPlugins={[remarkGfm]}` a los 3 `<ReactMarkdown>`
- `Chat.tsx`: import remarkGfm, anadir plugin al `<ReactMarkdown>` de mensajes user
- `Chat.css`: eliminar `white-space: pre-wrap`, anadir estilos para: table/th/td (bordes, hover), pre/code blocks, blockquote (borde azul), hr, li spacing

**Archivos modificados:**
- `frontend/src/components/FormattedMessage.tsx`
- `frontend/src/pages/Chat.tsx`
- `frontend/src/pages/Chat.css`
- `frontend/package.json` (nueva dep: remark-gfm)

**Regla para prevenir recurrencia:** Siempre usar `remarkPlugins={[remarkGfm]}` en cualquier nuevo `<ReactMarkdown>`. Nunca usar `white-space: pre-wrap` en contenedores de HTML renderizado por ReactMarkdown.
