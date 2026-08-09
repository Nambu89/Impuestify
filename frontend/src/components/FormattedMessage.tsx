/**
 * FormattedMessage - Rich formatting for assistant messages
 *
 * Pre-processes raw assistant content to:
 * 1. Hide/collapse inline JSON blocks
 * 2. Render IRPF simulation data as styled cards
 * 3. Convert emoji-prefixed sections into callout boxes
 * 4. Render direct-answer verdict card (green, prominent)
 * 5. Render copyable blockquotes (legal text / invoice templates)
 * 6. Render Pro tip card (golden)
 * 7. Keep regular markdown rendered normally
 */
import React, { useMemo, useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
    Calculator,
    Lightbulb,
    CheckCircle2,
    AlertTriangle,
    MessageCircle,
    TrendingUp,
    Zap,
    Copy,
    Check,
} from 'lucide-react'
import './FormattedMessage.css'

interface FormattedMessageProps {
    content: string
}

// --- Types for parsed blocks ---

interface TextBlock {
    type: 'text'
    content: string
}

interface SimulationBlock {
    type: 'simulation'
    title: string
    rows: { label: string; value: string; highlight?: boolean }[]
    footer?: string
}

interface CalloutBlock {
    type: 'callout'
    variant: 'success' | 'info' | 'warning' | 'tip' | 'question'
    title: string
    content: string
}

interface DirectAnswerBlock {
    type: 'direct_answer'
    verdict: string
    rest: string
}

interface ProTipBlock {
    type: 'pro_tip'
    content: string
}

type ContentBlock = TextBlock | SimulationBlock | CalloutBlock | DirectAnswerBlock | ProTipBlock

// --- Emoji-to-callout mapping ---

const CALLOUT_PATTERNS: {
    emoji: string
    variant: CalloutBlock['variant']
    keywords: string[]
}[] = [
    { emoji: '\\u2705', variant: 'success', keywords: ['Resumen', 'directo', 'Al grano'] }, // ✅
    { emoji: '\\u2714\\uFE0F', variant: 'success', keywords: ['recomiendo', 'Recomend'] }, // ✔
    { emoji: '\\u{1F4A1}', variant: 'info', keywords: ['explicaci', 'Breve', 'Para que quede'] }, // 💡
    { emoji: '\\u26A0\\uFE0F', variant: 'warning', keywords: ['Fuentes', 'aviso', 'Importante'] }, // ⚠️
    { emoji: '\\u{1F4AC}', variant: 'question', keywords: ['Quieres', 'quieres'] }, // 💬
    { emoji: '\\u{1F4C8}', variant: 'tip', keywords: ['proyecci', 'estimaci'] }, // 📈
    { emoji: '\\u{1F4CB}', variant: 'info', keywords: ['Resumen', 'Detalle'] }, // 📋
]

// --- Parser ---

function stripJsonBlocks(text: string): string {
    // Remove inline JSON objects like {"key":"value",...}
    // Only remove objects that look like raw debug/parameter data (not markdown code blocks)
    return text.replace(/\{(?:"[^"]*"\s*:\s*(?:"[^"]*"|[\d.]+|true|false|null)\s*,?\s*){2,}\}/g, '')
}

function parseSimulationBlock(text: string): SimulationBlock | null {
    // Match "Simulación IRPF YYYY — CCAA" followed by structured lines
    const simMatch = text.match(
        /(?:^|\n)(Simulaci[oó]n\s+IRPF\s+\d{4}\s*[—–-]\s*[^\n]+)\n([\s\S]+?)(?=\n\n|\n(?:[A-ZÁÉÍÓÚ])|$)/i,
    )
    if (!simMatch) return null

    const title = simMatch[1].trim()
    const body = simMatch[2].trim()
    const rows: SimulationBlock['rows'] = []

    for (const line of body.split('\n')) {
        const trimmed = line.trim()
        if (!trimmed) continue

        // Match "Label: Value" pattern
        const match = trimmed.match(/^(.+?):\s+(.+)$/)
        if (match) {
            const label = match[1].trim()
            const value = match[2].trim()
            const highlight = /cuota total|tipo.*efectivo/i.test(label)
            rows.push({ label, value, highlight })
        }
    }

    if (rows.length === 0) return null
    return { type: 'simulation', title, rows }
}

function detectCalloutSection(
    text: string,
): { variant: CalloutBlock['variant']; title: string; content: string } | null {
    // Match lines that start with emoji + bold title pattern
    // e.g., "Resumen directo ✅" or "✅ Resumen directo" or "**Resumen directo (al grano) ✅**"
    const firstLine = text.split('\n')[0]
    if (!firstLine) return null

    // Check for emoji markers anywhere in the first line
    const emojiRegex = /[\u2705\u2714\u26A0\u{1F4A1}\u{1F4AC}\u{1F4C8}\u{1F4CB}]/u
    if (!emojiRegex.test(firstLine)) return null

    // Determine variant from emoji
    let variant: CalloutBlock['variant'] = 'info'
    if (/[\u2705]|[\u2714]\uFE0F?/.test(firstLine)) {
        // ✅ or ✔ - check keywords to distinguish
        if (/recomiendo|Recomend/i.test(firstLine)) variant = 'tip'
        else variant = 'success'
    }
    if (/\u{1F4A1}/u.test(firstLine)) variant = 'info' // 💡
    if (/\u26A0/u.test(firstLine)) variant = 'warning' // ⚠️
    if (/\u{1F4AC}/u.test(firstLine)) variant = 'question' // 💬
    if (/\u{1F4C8}/u.test(firstLine)) variant = 'tip' // 📈

    // Clean title: remove emojis, asterisks, extra whitespace
    const title = firstLine
        .replace(/[\u2705\u2714\u26A0\u{1F4A1}\u{1F4AC}\u{1F4C8}\u{1F4CB}\u{1F4B6}]/gu, '')
        .replace(/\*+/g, '')
        .replace(/#+\s*/g, '')
        .trim()

    const content = text.split('\n').slice(1).join('\n').trim()

    if (!title) return null
    return { variant, title, content }
}

// --- Direct answer detection ---
// Detecta la PRIMERA frase del mensaje cuando expresa un veredicto fiscal.
// Acepta el verdict con o SIN bold (**), con o sin colon, con o sin coma.
// Ejemplos válidos:
//   "Factura SIN IVA: prestación de servicios..."
//   "**Factura SIN IVA**. Cuando facturas..."
//   "NO aplicas IVA español."
//   "Sí, debes presentar Modelo 303."
const VERDICT_KEYWORDS =
    '(?:NO\\s+aplicas|NO\\s+debes|Aplicas|Debes|Factura\\s+(?:SIN|CON)|S[ÍíIi],?|No,?|Exento|Sujet[oa])'
const DIRECT_ANSWER_REGEX = new RegExp(
    `^\\*{0,2}(${VERDICT_KEYWORDS}[^\\n]{0,200}?)(?:[.:!?]|\\*{1,2})`,
    'i',
)

function detectDirectAnswer(text: string): { verdict: string; rest: string } | null {
    const firstPara = text.split(/\n\n/)[0].trim()
    // Must be short enough to be a verdict (not a full paragraph)
    if (firstPara.length > 350) return null
    // Already handled as a callout (has emoji marker)
    if (/[✅✔⚠\u{1F4A1}\u{1F4AC}\u{1F4C8}\u{1F4CB}]/u.test(firstPara)) return null
    const m = firstPara.match(DIRECT_ANSWER_REGEX)
    if (!m) return null
    // Strip leading/trailing asterisks
    const verdict = m[1].replace(/^\*+|\*+$/g, '').trim()
    if (verdict.length < 4) return null
    // Take everything AFTER the matched verdict sentence
    const idx = text.indexOf(m[0]) + m[0].length
    const rest = text.slice(idx).trim()
    return { verdict, rest }
}

// --- Pro tip detection ---
// Detecta "Pro tip" / "Truco" en CUALQUIER parte del texto, incluso dentro
// de bullet list ("- Pro tip: ..."). Extrae el contenido y lo separa.
const PRO_TIP_LINE_REGEX =
    /^[\s>*+\-•]*\*{0,2}(?:Pro\s+tip|Truco|Pro\s+Tip|TRUCO)\*{0,2}\s*[:：]\s*(.+)$/im

function detectProTip(text: string): { content: string; textWithoutProTip: string } | null {
    const m = text.match(PRO_TIP_LINE_REGEX)
    if (!m) return null
    const proTipContent = m[1].trim()
    // Remove the entire matched line (including bullet prefix) from the original text
    const textWithoutProTip = text
        .replace(m[0], '')
        .replace(/\n{3,}/g, '\n\n')
        .trim()
    return { content: proTipContent, textWithoutProTip }
}

function parseContent(rawContent: string): ContentBlock[] {
    const blocks: ContentBlock[] = []

    // Step 1: Strip JSON blocks
    let content = stripJsonBlocks(rawContent)

    // Step 1b: Strip leaked technical lines (invoke_*, tool_name, function_call, Calling ...)
    content = content.replace(
        /^(?:invoke_\w+|tool_name|function_call|calling)\s*[:=]\s*\S+.*$/gim,
        '',
    )
    content = content.replace(/^Calling\s+\w+\s+with.*$/gim, '')
    // Strip ANY inline JSON objects (handles 1-level nested braces):
    // {"call":"project_annual_irpf","args":{}} or {"base_imponible": 30000}
    content = content.replace(/\{"[a-z_]+":(?:[^{}]|\{[^{}]*\})*\}/g, '')
    // Strip Spanish tool call phrases
    content = content.replace(
        /\(?\s*(?:LLAMADA|llamada)\s+A\s+(?:HERRAMIENTA|herramienta)\s+\w+\s*\)?/gi,
        '',
    )
    content = content.replace(
        /Ahora\s+(?:hago|realizo|ejecuto)\s+el\s+c[aá]lculo\s+r[aá]pido\.?/gi,
        '',
    )
    // Strip internal reasoning leaked from LLM (agent thinking, search narration)
    content = content.replace(
        /(?:Llamo|Voy a (?:usar|llamar|ejecutar|utilizar|consultar|buscar|volver)|Utilizo|Uso|Ejecuto|Consulto)\s+(?:la |el |a la |al |en )?(?:herramienta|tool|funci[oó]n|c[aá]lculo|simulador|motor|cat[aá]logo|base de datos|b[uú]squeda)\b[^.!?\n]*[.!?]?\s*/gi,
        '',
    )
    content = content.replace(
        /(?:Calcular[eé]|Primero voy a|Ahora (?:hago|realizo|ejecuto|calculo|analizo|busco)|Realizando\s+(?:nueva\s+)?b[uú]squeda|Buscando\s+(?:en|con|informaci))\b[^.!?\n]*[.!?]?\s*/gi,
        '',
    )
    // Strip search narration patterns (agent describing its search process)
    content = content.replace(
        /(?:Voy a (?:volver a |intentar |re)?\s*buscar)\b[^.!?\n]*[.!?]?\s*/gi,
        '',
    )
    content = content.replace(
        /(?:(?:No |no )?(?:he encontrado|encuentro|aparece)\s+(?:el |la |los |las |ningún|ninguna|resultados))\b[^.!?\n]*[.!?]?\s*/gi,
        '',
    )
    content = content.replace(
        /(?:Déjame|Permíteme|Voy a)\s+(?:verificar|comprobar|revisar|consultar|buscar)\b[^.!?\n]*[.!?]?\s*/gi,
        '',
    )
    // Strip broken source lines: "(pág. 0)" with no title
    content = content.replace(/^,?\s*\(p[aá]g\.\s*\d+\)\s*$/gm, '')
    content = content.replace(/^Fuentes:\s*\n(?:\s*,?\s*\(p[aá]g\.\s*\d+\)\s*\n?)+/gm, '')

    // Step 2: Clean up multiple blank lines
    content = content.replace(/\n{3,}/g, '\n\n')

    // Step 3: Check for direct answer in the whole content (first paragraph only)
    let contentForSections = content
    const directAnswer = detectDirectAnswer(content)
    if (directAnswer) {
        blocks.push({
            type: 'direct_answer',
            verdict: directAnswer.verdict,
            rest: directAnswer.rest,
        })
        // The rest will be processed as normal sections below
        contentForSections = directAnswer.rest
    }

    // Step 3b: Global Pro tip extraction (also handles tips inside bullet
    // lists or anywhere in the body). The verdict for ProTipCard is rendered
    // at the END of the message, so we extract first and push later.
    let trailingProTip: ProTipBlock | null = null
    const globalProTip = detectProTip(contentForSections)
    if (globalProTip) {
        trailingProTip = { type: 'pro_tip', content: globalProTip.content }
        contentForSections = globalProTip.textWithoutProTip
    }

    // Step 4: Split into sections by double newlines followed by emoji or header markers
    // We split on patterns that indicate a new "section"
    const sections = splitIntoSections(contentForSections)

    for (const section of sections) {
        const trimmed = section.trim()
        if (!trimmed) continue

        // Try pro tip block (before simulation so it takes priority).
        // Si la sección contiene OTRO texto además del Pro tip, conserva
        // ese texto en un text block separado para no perder contenido.
        const proTip = detectProTip(trimmed)
        if (proTip) {
            if (proTip.textWithoutProTip) {
                blocks.push({ type: 'text', content: proTip.textWithoutProTip })
            }
            blocks.push({ type: 'pro_tip', content: proTip.content })
            continue
        }

        // Try simulation block
        const sim = parseSimulationBlock(trimmed)
        if (sim) {
            // Check if there's text before the simulation
            const simStart = trimmed.indexOf(sim.title)
            if (simStart > 0) {
                const before = trimmed.substring(0, simStart).trim()
                if (before) blocks.push({ type: 'text', content: before })
            }
            blocks.push(sim)
            continue
        }

        // Try callout section
        const callout = detectCalloutSection(trimmed)
        if (callout) {
            blocks.push({
                type: 'callout',
                variant: callout.variant,
                title: callout.title,
                content: callout.content,
            })
            continue
        }

        // Regular text
        blocks.push({ type: 'text', content: trimmed })
    }

    // Append Pro tip extracted globally (if any) at the end of the message.
    if (trailingProTip) {
        blocks.push(trailingProTip)
    }

    return blocks
}

function splitIntoSections(content: string): string[] {
    // Split on double newlines that precede lines with emojis or markdown headers
    // but keep everything together that doesn't have clear section breaks
    const lines = content.split('\n')
    const sections: string[] = []
    let current: string[] = []

    const sectionStartRegex =
        /^(?:#{1,4}\s|[\u2705\u2714\u26A0\u{1F4A1}\u{1F4AC}\u{1F4C8}\u{1F4CB}]|\*{1,2}[A-ZÁÉÍÓÚÑ])/u

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const prevLine = i > 0 ? lines[i - 1] : null

        // New section if: previous line was blank AND current line starts with section marker
        if (prevLine !== null && prevLine.trim() === '' && sectionStartRegex.test(line.trim())) {
            if (current.length > 0) {
                sections.push(current.join('\n'))
                current = []
            }
        }

        // Also split on "Simulación IRPF" headers
        if (/^Simulaci[oó]n\s+IRPF/i.test(line.trim()) && current.length > 0) {
            const prevContent = current.join('\n').trim()
            if (prevContent) sections.push(prevContent)
            current = []
        }

        current.push(line)
    }

    if (current.length > 0) {
        sections.push(current.join('\n'))
    }

    return sections
}

// --- Renderers ---

function DirectAnswerCard({ block }: { block: DirectAnswerBlock }) {
    return (
        <div className="fmt-direct-answer">
            <div className="fmt-direct-answer-header">
                <Zap size={16} />
                <span className="fmt-direct-answer-label">Respuesta directa</span>
            </div>
            <p className="fmt-direct-answer-verdict">{block.verdict}</p>
        </div>
    )
}

function ProTipCard({ block }: { block: ProTipBlock }) {
    return (
        <div className="fmt-pro-tip">
            <div className="fmt-pro-tip-header">
                <Lightbulb size={16} />
                <span>Pro tip fiscal</span>
            </div>
            <div className="fmt-pro-tip-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
                    {block.content}
                </ReactMarkdown>
            </div>
        </div>
    )
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false)

    const handleCopy = useCallback(async () => {
        try {
            await navigator.clipboard.writeText(text)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // Fallback for older browsers
            const el = document.createElement('textarea')
            el.value = text
            document.body.appendChild(el)
            el.select()
            document.execCommand('copy')
            document.body.removeChild(el)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        }
    }, [text])

    return (
        <button
            className={`fmt-copy-btn${copied ? ' fmt-copy-btn--copied' : ''}`}
            onClick={handleCopy}
            title={copied ? 'Copiado' : 'Copiar texto'}
            aria-label={copied ? 'Texto copiado' : 'Copiar al portapapeles'}
        >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span>{copied ? 'Copiado' : 'Copiar'}</span>
        </button>
    )
}

function SimulationCard({ block }: { block: SimulationBlock }) {
    return (
        <div className="fmt-simulation">
            <div className="fmt-simulation-header">
                <Calculator size={18} />
                <span>{block.title}</span>
            </div>
            <div className="fmt-simulation-body">
                {block.rows.map((row, i) => (
                    <div
                        key={i}
                        className={`fmt-simulation-row ${row.highlight ? 'fmt-simulation-row--highlight' : ''}`}
                    >
                        <span className="fmt-simulation-label">{row.label}</span>
                        <span className="fmt-simulation-value">{row.value}</span>
                    </div>
                ))}
            </div>
        </div>
    )
}

const CALLOUT_ICONS: Record<CalloutBlock['variant'], React.ReactNode> = {
    success: <CheckCircle2 size={18} />,
    info: <Lightbulb size={18} />,
    warning: <AlertTriangle size={18} />,
    tip: <TrendingUp size={18} />,
    question: <MessageCircle size={18} />,
}

// --- Custom markdown components ---

/**
 * Custom blockquote:
 * - add `.blockquote-warning` class when content starts with ⚠
 * - add copy button for legal/invoice template blockquotes (>80 chars, no warning)
 */
function MdBlockquote({ children, ...rest }: React.HTMLAttributes<HTMLQuoteElement>) {
    const childText = React.Children.toArray(children)
        .flatMap((c) => {
            if (typeof c === 'string') return [c]
            if (React.isValidElement(c)) {
                const props = c.props as { children?: React.ReactNode }
                return React.Children.toArray(props.children).map((cc) =>
                    typeof cc === 'string' ? cc : '',
                )
            }
            return ['']
        })
        .join('')
    const isWarning = /⚠|⚠/u.test(childText)
    // Legal/invoice template: long text without warning emoji
    const isLegalText =
        !isWarning &&
        childText.trim().length > 80 &&
        /(?:Art[sí]?\.?\s*\d|Ley\s+\d|RD\s+\d|Directiva|sujeta|exenta|intracomun|IVA|IRPF)/i.test(
            childText,
        )

    if (isLegalText) {
        return (
            <div className="fmt-copyable-quote">
                <blockquote {...rest} className="fmt-copyable-quote__text">
                    {children}
                </blockquote>
                <div className="fmt-copyable-quote__actions">
                    <CopyButton text={childText.trim()} />
                </div>
            </div>
        )
    }

    return (
        <blockquote {...rest} className={isWarning ? 'blockquote-warning' : undefined}>
            {children}
        </blockquote>
    )
}

/**
 * Custom paragraph: detect "📄 Fuentes: ..." sentinel emitted by the
 * backend (tax_agent.format_sources_inline) and wrap it in a styled
 * .sources-block. Falls back to plain paragraph.
 */
function MdParagraph({ children, ...rest }: React.HTMLAttributes<HTMLParagraphElement>) {
    const childText = React.Children.toArray(children)
        .map((c) => (typeof c === 'string' ? c : ''))
        .join('')
    // Backend format: "\n\n📄 **Fuentes**: doc1 (pág X), doc2 (pág Y)"
    if (
        /^\s*📄\s*\*?\*?Fuentes/i.test(childText) ||
        /Fuentes\s*[:：]/i.test(childText.slice(0, 40))
    ) {
        return (
            <p {...rest} className="sources-block">
                {children}
            </p>
        )
    }
    return <p {...rest}>{children}</p>
}

/**
 * Custom anchor: external links (BOE consolidados, etc.) open in new
 * tab with rel="noopener noreferrer" + ExternalLink icon. Internal
 * links (same origin) keep default behaviour.
 */
function MdAnchor({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
    const url = href || ''
    const isExternal =
        /^https?:\/\//i.test(url) &&
        !url.includes(typeof window !== 'undefined' ? window.location.host : '')
    if (!isExternal) {
        return (
            <a href={href} {...rest}>
                {children}
            </a>
        )
    }
    return (
        <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="md-external-link"
            {...rest}
        >
            {children}
        </a>
    )
}

const MARKDOWN_COMPONENTS = {
    blockquote: MdBlockquote,
    p: MdParagraph,
    a: MdAnchor,
} as const

function CalloutBox({ block }: { block: CalloutBlock }) {
    return (
        <div className={`fmt-callout fmt-callout--${block.variant}`}>
            <div className="fmt-callout-header">
                {CALLOUT_ICONS[block.variant]}
                <span>{block.title}</span>
            </div>
            {block.content && (
                <div className="fmt-callout-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
                        {block.content}
                    </ReactMarkdown>
                </div>
            )}
        </div>
    )
}

// --- Main Component ---

export const FormattedMessage: React.FC<FormattedMessageProps> = ({ content }) => {
    const blocks = useMemo(() => parseContent(content), [content])

    // If parsing produced only one text block with the full content, just render markdown directly
    // This avoids unnecessary wrapping for simple messages
    if (blocks.length === 1 && blocks[0].type === 'text') {
        return (
            <div className="fmt-message">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{blocks[0].content}</ReactMarkdown>
            </div>
        )
    }

    return (
        <div className="fmt-message">
            {blocks.map((block, i) => {
                switch (block.type) {
                    case 'direct_answer':
                        return <DirectAnswerCard key={i} block={block} />
                    case 'pro_tip':
                        return <ProTipCard key={i} block={block} />
                    case 'simulation':
                        return <SimulationCard key={i} block={block} />
                    case 'callout':
                        return <CalloutBox key={i} block={block} />
                    case 'text':
                        return (
                            <div key={i} className="fmt-text">
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={MARKDOWN_COMPONENTS}
                                >
                                    {block.content}
                                </ReactMarkdown>
                            </div>
                        )
                }
            })}
        </div>
    )
}

export default FormattedMessage
