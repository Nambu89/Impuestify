import { Home, Users, Heart, TrendingUp, Leaf, Briefcase, Globe, Shield, HelpCircle, Check, AlertCircle } from 'lucide-react'
import CountUp from './reactbits/CountUp'
import FadeContent from './reactbits/FadeContent'
import './DeductionCards.css'

/** Keywords to detect deduction sections in assistant messages */
const DEDUCTION_KEYWORDS = [
    'deducciones a las que tienes derecho',
    'deducciones irpf',
    'deducciones aplicables',
    'deducciones elegibles',
    'deducciones posibles',
]

/** Check if message content contains deduction information */
export function hasDeductions(content: string): boolean {
    const lower = content.toLowerCase()
    return DEDUCTION_KEYWORDS.some((kw) => lower.includes(kw))
}

interface Deduction {
    name: string
    amount: string
    description: string
    legalRef: string
    status: 'eligible' | 'possible'
    category: string
}

/** Category to icon mapping */
function getCategoryIcon(category: string) {
    const lower = category.toLowerCase()
    if (lower.includes('vivienda') || lower.includes('alquiler')) return Home
    if (lower.includes('familia') || lower.includes('hijo') || lower.includes('nacimiento') || lower.includes('descendiente')) return Users
    if (lower.includes('donati') || lower.includes('donacion')) return Heart
    if (lower.includes('inversion') || lower.includes('empresa') || lower.includes('i+d')) return TrendingUp
    if (lower.includes('eficiencia') || lower.includes('electrico') || lower.includes('renovable') || lower.includes('sostenibilidad')) return Leaf
    if (lower.includes('actividad') || lower.includes('autonomo') || lower.includes('profesional')) return Briefcase
    if (lower.includes('ceuta') || lower.includes('melilla') || lower.includes('territorial') || lower.includes('internacional')) return Globe
    if (lower.includes('discapacidad') || lower.includes('prevision') || lower.includes('segur')) return Shield
    return HelpCircle
}

/** Parse deduction markdown content into structured data */
function parseDeductions(content: string): { eligible: Deduction[]; possible: Deduction[]; totalSavings: number } {
    const eligible: Deduction[] = []
    const possible: Deduction[] = []
    let totalSavings = 0

    // Extract total savings: "Ahorro estimado: X€" or "Ahorro estimado: X.XXX€"
    const savingsMatch = content.match(/ahorro\s+estimado[:\s]*(?:hasta\s+)?(\d[\d.,]*)\s*€/i)
    if (savingsMatch) {
        totalSavings = parseFloat(savingsMatch[1].replace(/\./g, '').replace(',', '.'))
    }

    // Split by sections
    const lines = content.split('\n')
    let currentStatus: 'eligible' | 'possible' | null = null

    for (const line of lines) {
        const lower = line.toLowerCase()

        // Detect section headers
        if (lower.includes('deducciones a las que tienes derecho') || lower.includes('deducciones elegibles') || lower.includes('deducciones aplicables')) {
            currentStatus = 'eligible'
            continue
        }
        if (lower.includes('deducciones posibles') || lower.includes('necesito más datos') || lower.includes('necesito mas datos')) {
            currentStatus = 'possible'
            continue
        }

        // Parse deduction lines: "- **Name** — Hasta X€" or "- **Name**: description"
        if (currentStatus && line.trim().startsWith('-')) {
            const nameMatch = line.match(/\*\*([^*]+)\*\*/)
            if (!nameMatch) continue

            const name = nameMatch[1].trim()
            // Extract amount: "Hasta X€", "X€", "X%"
            const amountMatch = line.match(/(?:hasta\s+)?(\d[\d.,]*)\s*€|(\d[\d.,]*)\s*%/i)
            const amount = amountMatch ? amountMatch[0].trim() : ''
            // Extract description: text after — or :
            const descMatch = line.match(/(?:—|:)\s*(.+?)(?:\*|$)/)
            const description = descMatch ? descMatch[1].replace(/\*/g, '').trim() : ''
            // Extract legal ref: (Art. XX ...) or text in parentheses with "Art"
            const legalMatch = line.match(/\(([^)]*(?:Art|NF|Ley|DT|DA|DL)[^)]*)\)/i)
            const legalRef = legalMatch ? legalMatch[1].trim() : ''

            const deduction: Deduction = {
                name,
                amount,
                description,
                legalRef,
                status: currentStatus,
                category: name,
            }

            if (currentStatus === 'eligible') {
                eligible.push(deduction)
            } else {
                possible.push(deduction)
            }
        }
    }

    return { eligible, possible, totalSavings }
}

interface DeductionCardsProps {
    content: string
}

export function DeductionCards({ content }: DeductionCardsProps) {
    const { eligible, possible, totalSavings } = parseDeductions(content)

    // Don't render if no deductions parsed
    if (eligible.length === 0 && possible.length === 0) return null

    return (
        <div className="deduction-cards">
            {/* Total savings banner */}
            {totalSavings > 0 && (
                <FadeContent delay={0} duration={500}>
                    <div className="deduction-savings-banner">
                        <span className="deduction-savings-label">Ahorro estimado</span>
                        <span className="deduction-savings-amount">
                            <CountUp to={totalSavings} separator="." duration={2} />
                            <span>&nbsp;€</span>
                        </span>
                    </div>
                </FadeContent>
            )}

            {/* Eligible deductions */}
            {eligible.length > 0 && (
                <div className="deduction-section">
                    <h4 className="deduction-section-title deduction-section-eligible">
                        <Check size={16} />
                        Deducciones aplicables ({eligible.length})
                    </h4>
                    <div className="deduction-grid">
                        {eligible.map((d, i) => (
                            <FadeContent key={i} delay={i * 100} duration={400}>
                                <DeductionCard deduction={d} />
                            </FadeContent>
                        ))}
                    </div>
                </div>
            )}

            {/* Possible deductions */}
            {possible.length > 0 && (
                <div className="deduction-section">
                    <h4 className="deduction-section-title deduction-section-possible">
                        <AlertCircle size={16} />
                        Posibles deducciones ({possible.length})
                    </h4>
                    <div className="deduction-grid">
                        {possible.map((d, i) => (
                            <FadeContent key={i} delay={eligible.length * 100 + i * 100} duration={400}>
                                <DeductionCard deduction={d} />
                            </FadeContent>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}

function DeductionCard({ deduction }: { deduction: Deduction }) {
    const Icon = getCategoryIcon(deduction.category)
    const isEligible = deduction.status === 'eligible'

    return (
        <div className={`deduction-card ${isEligible ? 'deduction-card-eligible' : 'deduction-card-possible'}`}>
            <div className="deduction-card-header">
                <div className="deduction-card-icon">
                    <Icon size={18} />
                </div>
                <div className="deduction-card-info">
                    <span className="deduction-card-name">{deduction.name}</span>
                    {deduction.amount && (
                        <span className="deduction-card-amount">{deduction.amount}</span>
                    )}
                </div>
                <span className={`deduction-badge ${isEligible ? 'deduction-badge-eligible' : 'deduction-badge-possible'}`}>
                    {isEligible ? 'Elegible' : 'Posible'}
                </span>
            </div>
            {deduction.description && (
                <p className="deduction-card-desc">{deduction.description}</p>
            )}
            {deduction.legalRef && (
                <span className="deduction-card-legal">{deduction.legalRef}</span>
            )}
        </div>
    )
}
