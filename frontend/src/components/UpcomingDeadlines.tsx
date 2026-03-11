import { useNavigate } from 'react-router-dom'
import { CalendarClock, AlertCircle } from 'lucide-react'
import { useDeadlines, FiscalDeadline } from '../hooks/useDeadlines'
import './UpcomingDeadlines.css'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UpcomingDeadlinesProps {
    isPublic?: boolean
    maxItems?: number
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getCountdownLabel(deadline: FiscalDeadline): string {
    if (deadline.daysRemaining <= 0) return 'Hoy'
    if (deadline.daysRemaining === 1) return '1 día'
    return `${deadline.daysRemaining} días`
}

function getShortName(deadline: FiscalDeadline): string {
    // Show model number + full name: "303 — IVA trimestral"
    return `${deadline.model} ${deadline.model_name}`
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function UpcomingDeadlines({ isPublic = false, maxItems = 3 }: UpcomingDeadlinesProps) {
    const navigate = useNavigate()
    const { deadlines, loading, error } = useDeadlines({
        days: 60,
        isPublic,
    })

    const handleClick = () => {
        if (isPublic) {
            navigate('/login')
        } else {
            navigate('/calendario')
        }
    }

    // Show only upcoming (not past), sorted by urgency then by days
    const upcoming = deadlines
        .filter(d => d.urgency !== 'past')
        .sort((a, b) => a.daysRemaining - b.daysRemaining)
        .slice(0, maxItems)

    if (loading) {
        return (
            <div className="ud-container ud-container--loading">
                <CalendarClock size={18} />
                <span>Cargando plazos...</span>
            </div>
        )
    }

    if (error || upcoming.length === 0) {
        return null
    }

    return (
        <div className="ud-container" role="navigation" aria-label="Próximos plazos fiscales">
            <div className="ud-header">
                <CalendarClock size={16} />
                <span>Próximos plazos</span>
            </div>
            <div className="ud-pills">
                {upcoming.map(d => (
                    <button
                        key={d.id}
                        className={`ud-pill ud-pill--${d.urgency}`}
                        onClick={handleClick}
                        title={`${d.model_name} — ${d.period} ${d.tax_year}. Vence el ${new Date(d.end_date).toLocaleDateString('es-ES')}`}
                        aria-label={`${d.model_name}, vence en ${getCountdownLabel(d)}`}
                    >
                        {d.urgency === 'urgent' && (
                            <AlertCircle size={12} className="ud-pill__alert" />
                        )}
                        <span className="ud-pill__name">{getShortName(d)}</span>
                        <span className="ud-pill__sep">—</span>
                        <span className="ud-pill__count">{getCountdownLabel(d)}</span>
                    </button>
                ))}
            </div>
        </div>
    )
}
