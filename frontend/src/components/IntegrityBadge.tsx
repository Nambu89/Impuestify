import { Shield, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react'
import './IntegrityBadge.css'

interface Finding {
    pattern_id: string
    category: string
    severity: string
    matched_text: string
    position: number
    description: string
}

interface IntegrityBadgeProps {
    score: number | null
    findings?: string  // JSON string con array de Finding
    compact?: boolean  // true = solo icono, false = icono + texto
}

function getBadgeConfig(score: number | null): {
    icon: React.ReactNode
    label: string
    modifier: string
    titlePrefix: string
} {
    if (score === null) {
        return {
            icon: <Shield size={12} />,
            label: 'Pendiente de escaneo',
            modifier: 'pending',
            titlePrefix: 'Pendiente de escaneo'
        }
    }
    if (score >= 0.7) {
        return {
            icon: <ShieldX size={12} />,
            label: 'Bloqueado',
            modifier: 'blocked',
            titlePrefix: 'Contenido bloqueado'
        }
    }
    if (score >= 0.3) {
        return {
            icon: <ShieldAlert size={12} />,
            label: 'Advertencias',
            modifier: 'warn',
            titlePrefix: 'Advertencias detectadas'
        }
    }
    return {
        icon: <ShieldCheck size={12} />,
        label: 'Verificado',
        modifier: 'clean',
        titlePrefix: 'Documento verificado'
    }
}

function buildTooltip(titlePrefix: string, findings?: string): string {
    if (!findings) return titlePrefix

    try {
        const parsed: Finding[] = JSON.parse(findings)
        if (!parsed || parsed.length === 0) return titlePrefix

        const lines = parsed
            .slice(0, 5)
            .map(f => `• ${f.description}`)
            .join('\n')

        const suffix = parsed.length > 5 ? `\n... y ${parsed.length - 5} hallazgos más` : ''
        return `${titlePrefix}\n\n${lines}${suffix}`
    } catch {
        return titlePrefix
    }
}

export default function IntegrityBadge({ score, findings, compact = false }: IntegrityBadgeProps) {
    const config = getBadgeConfig(score)
    const tooltip = buildTooltip(config.titlePrefix, findings)

    return (
        <span
            className={`integrity-badge integrity-badge--${config.modifier}`}
            title={tooltip}
            aria-label={config.label}
        >
            {config.icon}
            {!compact && <span>{config.label}</span>}
        </span>
    )
}
