/**
 * FormattedMessage - Rich formatting for assistant messages
 *
 * Pre-processes raw assistant content to:
 * 1. Hide/collapse inline JSON blocks
 * 2. Render IRPF simulation data as styled cards
 * 3. Convert emoji-prefixed sections into callout boxes
 * 4. Keep regular markdown rendered normally
 */
import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Calculator, Lightbulb, CheckCircle2, AlertTriangle, MessageCircle, Info, TrendingUp } from 'lucide-react'
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

type ContentBlock = TextBlock | SimulationBlock | CalloutBlock

// --- Emoji-to-callout mapping ---

const CALLOUT_PATTERNS: {
    emoji: string
    variant: CalloutBlock['variant']
    keywords: string[]
}[] = [
    { emoji: '\\u2705', variant: 'success', keywords: ['Resumen', 'directo', 'Al grano'] },          // ✅
    { emoji: '\\u2714\\uFE0F', variant: 'success', keywords: ['recomiendo', 'Recomend'] },            // ✔️
    { emoji: '\\u{1F4A1}', variant: 'info', keywords: ['explicaci', 'Breve', 'Para que quede'] },     // 💡
    { emoji: '\\u26A0\\uFE0F', variant: 'warning', keywords: ['Fuentes', 'aviso', 'Importante'] },    // ⚠️
    { emoji: '\\u{1F4AC}', variant: 'question', keywords: ['Quieres', 'quieres'] },                   // 💬
    { emoji: '\\u{1F4C8}', variant: 'tip', keywords: ['proyecci', 'estimaci'] },                      // 📈
    { emoji: '\\u{1F4CB}', variant: 'info', keywords: ['Resumen', 'Detalle'] },                       // 📋
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
        /(?:^|\n)(Simulaci[oó]n\s+IRPF\s+\d{4}\s*[—–-]\s*[^\n]+)\n([\s\S]+?)(?=\n\n|\n(?:[A-ZÁÉÍÓÚ])|$)/i
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

function detectCalloutSection(text: string): { variant: CalloutBlock['variant']; title: string; content: string } | null {
    // Match lines that start with emoji + bold title pattern
    // e.g., "Resumen directo ✅" or "✅ Resumen directo" or "**Resumen directo (al grano) ✅**"
    const firstLine = text.split('\n')[0]
    if (!firstLine) return null

    // Check for emoji markers anywhere in the first line
    const emojiRegex = /[\u2705\u2714\uFE0F\u26A0\u{1F4A1}\u{1F4AC}\u{1F4C8}\u{1F4CB}]/u
    if (!emojiRegex.test(firstLine)) return null

    // Determine variant from emoji
    let variant: CalloutBlock['variant'] = 'info'
    if (/[\u2705]|[\u2714]\uFE0F?/.test(firstLine)) {
        // ✅ or ✔️ - check keywords to distinguish
        if (/recomiendo|Recomend/i.test(firstLine)) variant = 'tip'
        else variant = 'success'
    }
    if (/\u{1F4A1}/u.test(firstLine)) variant = 'info'      // 💡
    if (/\u26A0/u.test(firstLine)) variant = 'warning'       // ⚠️
    if (/\u{1F4AC}/u.test(firstLine)) variant = 'question'   // 💬
    if (/\u{1F4C8}/u.test(firstLine)) variant = 'tip'        // 📈

    // Clean title: remove emojis, asterisks, extra whitespace
    const title = firstLine
        .replace(/[\u2705\u2714\uFE0F\u26A0\u{1F4A1}\u{1F4AC}\u{1F4C8}\u{1F4CB}\u{1F4B6}]/gu, '')
        .replace(/\*+/g, '')
        .replace(/#+\s*/g, '')
        .trim()

    const content = text.split('\n').slice(1).join('\n').trim()

    if (!title) return null
    return { variant, title, content }
}

function parseContent(rawContent: string): ContentBlock[] {
    const blocks: ContentBlock[] = []

    // Step 1: Strip JSON blocks
    let content = stripJsonBlocks(rawContent)

    // Step 1b: Strip leaked technical lines (invoke_*, tool_name, function_call, Calling ...)
    content = content.replace(/^(?:invoke_\w+|tool_name|function_call|calling)\s*[:=]\s*\S+.*$/gim, '')
    content = content.replace(/^Calling\s+\w+\s+with.*$/gim, '')
    // Strip Spanish tool call phrases
    content = content.replace(/\(?\s*(?:LLAMADA|llamada)\s+A\s+(?:HERRAMIENTA|herramienta)\s+\w+\s*\)?/gi, '')
    content = content.replace(/Ahora\s+(?:hago|realizo|ejecuto)\s+el\s+c[aá]lculo\s+r[aá]pido\.?/gi, '')
    // Strip broken source lines: "(pág. 0)" with no title
    content = content.replace(/^,?\s*\(p[aá]g\.\s*\d+\)\s*$/gm, '')
    content = content.replace(/^Fuentes:\s*\n(?:\s*,?\s*\(p[aá]g\.\s*\d+\)\s*\n?)+/gm, '')

    // Step 2: Clean up multiple blank lines
    content = content.replace(/\n{3,}/g, '\n\n')

    // Step 3: Split into sections by double newlines followed by emoji or header markers
    // We split on patterns that indicate a new "section"
    const sections = splitIntoSections(content)

    for (const section of sections) {
        const trimmed = section.trim()
        if (!trimmed) continue

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
                content: callout.content
            })
            continue
        }

        // Regular text
        blocks.push({ type: 'text', content: trimmed })
    }

    return blocks
}

function splitIntoSections(content: string): string[] {
    // Split on double newlines that precede lines with emojis or markdown headers
    // but keep everything together that doesn't have clear section breaks
    const lines = content.split('\n')
    const sections: string[] = []
    let current: string[] = []

    const sectionStartRegex = /^(?:#{1,4}\s|[\u2705\u2714\uFE0F\u26A0\u{1F4A1}\u{1F4AC}\u{1F4C8}\u{1F4CB}]|\*{1,2}[A-ZÁÉÍÓÚÑ])/u

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

function CalloutBox({ block }: { block: CalloutBlock }) {
    return (
        <div className={`fmt-callout fmt-callout--${block.variant}`}>
            <div className="fmt-callout-header">
                {CALLOUT_ICONS[block.variant]}
                <span>{block.title}</span>
            </div>
            {block.content && (
                <div className="fmt-callout-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.content}</ReactMarkdown>
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
                    case 'simulation':
                        return <SimulationCard key={i} block={block} />
                    case 'callout':
                        return <CalloutBox key={i} block={block} />
                    case 'text':
                        return (
                            <div key={i} className="fmt-text">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{block.content}</ReactMarkdown>
                            </div>
                        )
                }
            })}
        </div>
    )
}

export default FormattedMessage
