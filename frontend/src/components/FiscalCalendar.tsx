import { useState, useEffect, useRef } from 'react'
import { Calendar, Receipt, FileText, AlertCircle, Clock, Filter, ChevronLeft, ChevronRight } from 'lucide-react'
import { FiscalDeadline, UrgencyLevel } from '../hooks/useDeadlines'
import './FiscalCalendar.css'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FilterKey = 'todos' | 'autonomos' | 'particulares' | 'mis-plazos'

interface FiscalCalendarProps {
    deadlines: FiscalDeadline[]
    loading?: boolean
    error?: string | null
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getModelIcon(model: string) {
    const m = model.toLowerCase()
    if (m === '100' || m === 'renta' || m === 's90') return <Receipt size={20} />
    if (m === '303' || m === '420' || m === 'f-69' || m === '300') return <FileText size={20} />
    if (m === '130' || m === '131') return <Calculator size={20} />
    return <Calendar size={20} />
}

function Calculator({ size }: { size: number }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24"
            fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="4" y="2" width="16" height="20" rx="2" />
            <line x1="8" y1="6" x2="16" y2="6" />
            <line x1="8" y1="10" x2="10" y2="10" />
            <line x1="12" y1="10" x2="14" y2="10" />
            <line x1="16" y1="10" x2="16" y2="10" />
            <line x1="8" y1="14" x2="10" y2="14" />
            <line x1="12" y1="14" x2="14" y2="14" />
            <line x1="16" y1="14" x2="16" y2="14" />
            <line x1="8" y1="18" x2="10" y2="18" />
            <line x1="12" y1="18" x2="14" y2="18" />
            <line x1="16" y1="18" x2="16" y2="18" />
        </svg>
    )
}

const MONTH_NAMES = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

function formatDate(isoDate: string): string {
    const d = new Date(isoDate)
    return `${d.getDate()} de ${MONTH_NAMES[d.getMonth()]}`
}

function getUrgencyLabel(deadline: FiscalDeadline): string {
    if (deadline.urgency === 'past') return 'Vencido'
    if (deadline.daysRemaining === 0) return 'Vence hoy'
    if (deadline.daysRemaining === 1) return 'Vence mañana'
    if (deadline.urgency === 'urgent' || deadline.urgency === 'soon') {
        return `Vence en ${deadline.daysRemaining} días`
    }
    return `Vence el ${formatDate(deadline.end_date)}`
}

// ---------------------------------------------------------------------------
// Countdown Timer
// ---------------------------------------------------------------------------

interface CountdownProps {
    deadline: FiscalDeadline
}

function CountdownTimer({ deadline }: CountdownProps) {
    const [timeLeft, setTimeLeft] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 })

    useEffect(() => {
        function update() {
            const now = Date.now()
            const end = new Date(deadline.end_date)
            end.setHours(23, 59, 59, 0)
            const diff = end.getTime() - now

            if (diff <= 0) {
                setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0 })
                return
            }

            const totalSeconds = Math.floor(diff / 1000)
            const days = Math.floor(totalSeconds / 86400)
            const hours = Math.floor((totalSeconds % 86400) / 3600)
            const minutes = Math.floor((totalSeconds % 3600) / 60)
            const seconds = totalSeconds % 60
            setTimeLeft({ days, hours, minutes, seconds })
        }

        update()
        const interval = setInterval(update, 1000)
        return () => clearInterval(interval)
    }, [deadline.end_date])

    const pad = (n: number) => String(n).padStart(2, '0')

    return (
        <div className="fc-countdown">
            <Clock size={16} />
            <span className="fc-countdown__label">Próximo plazo:</span>
            <span className="fc-countdown__timer">
                <span className="fc-countdown__unit">
                    <strong>{pad(timeLeft.days)}</strong>
                    <em>d</em>
                </span>
                <span className="fc-countdown__sep">:</span>
                <span className="fc-countdown__unit">
                    <strong>{pad(timeLeft.hours)}</strong>
                    <em>h</em>
                </span>
                <span className="fc-countdown__sep">:</span>
                <span className="fc-countdown__unit">
                    <strong>{pad(timeLeft.minutes)}</strong>
                    <em>m</em>
                </span>
                <span className="fc-countdown__sep">:</span>
                <span className="fc-countdown__unit">
                    <strong>{pad(timeLeft.seconds)}</strong>
                    <em>s</em>
                </span>
            </span>
            <span className="fc-countdown__model">{deadline.model_name}</span>
        </div>
    )
}

// ---------------------------------------------------------------------------
// Timeline header
// ---------------------------------------------------------------------------

interface TimelineProps {
    deadlines: FiscalDeadline[]
    currentMonth: number
    currentYear: number
    onMonthChange: (month: number, year: number) => void
}

function Timeline({ deadlines, currentMonth, currentYear, onMonthChange }: TimelineProps) {
    const months = []
    for (let i = 0; i < 12; i++) {
        let m = (currentMonth + i) % 12
        let y = currentYear + Math.floor((currentMonth + i) / 12)
        months.push({ month: m, year: y })
    }

    const prev = () => {
        let m = currentMonth - 1
        let y = currentYear
        if (m < 0) { m = 11; y-- }
        onMonthChange(m, y)
    }

    const next = () => {
        let m = currentMonth + 1
        let y = currentYear
        if (m > 11) { m = 0; y++ }
        onMonthChange(m, y)
    }

    return (
        <div className="fc-timeline">
            <button className="fc-timeline__nav" onClick={prev} aria-label="Mes anterior">
                <ChevronLeft size={18} />
            </button>
            <div className="fc-timeline__months">
                {months.map(({ month, year }) => {
                    const dotsCount = deadlines.filter(d => {
                        const start = new Date(d.start_date)
                        const end = new Date(d.end_date)
                        const mStart = new Date(year, month, 1)
                        const mEnd = new Date(year, month + 1, 0)
                        return start <= mEnd && end >= mStart
                    }).length
                    const isActive = month === currentMonth && year === currentYear
                    return (
                        <button
                            key={`${year}-${month}`}
                            className={`fc-timeline__month ${isActive ? 'active' : ''}`}
                            onClick={() => onMonthChange(month, year)}
                        >
                            <span className="fc-timeline__month-name">{MONTH_NAMES[month].slice(0, 3)}</span>
                            {dotsCount > 0 && (
                                <span className="fc-timeline__dots">
                                    {Array.from({ length: Math.min(dotsCount, 4) }).map((_, i) => (
                                        <span key={i} className="fc-timeline__dot" />
                                    ))}
                                </span>
                            )}
                        </button>
                    )
                })}
            </div>
            <button className="fc-timeline__nav" onClick={next} aria-label="Mes siguiente">
                <ChevronRight size={18} />
            </button>
        </div>
    )
}

// ---------------------------------------------------------------------------
// Deadline Card
// ---------------------------------------------------------------------------

interface DeadlineCardProps {
    deadline: FiscalDeadline
}

function DeadlineCard({ deadline }: DeadlineCardProps) {
    const urgency = deadline.urgency as UrgencyLevel
    return (
        <div className={`fc-card fc-card--${urgency}`}>
            <div className="fc-card__icon">
                {getModelIcon(deadline.model)}
            </div>
            <div className="fc-card__body">
                <div className="fc-card__header-row">
                    <span className="fc-card__model">{deadline.model}</span>
                    <span className="fc-card__period">{deadline.period} {deadline.tax_year}</span>
                </div>
                <h3 className="fc-card__name">{deadline.model_name}</h3>
                {deadline.territory !== 'Estatal' && (
                    <span className="fc-card__territory">{deadline.territory}</span>
                )}
                {deadline.description && (
                    <p className="fc-card__description">{deadline.description}</p>
                )}
                {deadline.domiciliation_date && deadline.urgency !== 'past' && (
                    <p className="fc-card__domiciliation">
                        Domiciliación hasta el {formatDate(deadline.domiciliation_date)}
                    </p>
                )}
            </div>
            <div className="fc-card__footer">
                <span className={`fc-card__badge fc-card__badge--${urgency}`}>
                    {urgency === 'urgent' && <AlertCircle size={12} />}
                    {getUrgencyLabel(deadline)}
                </span>
                <span className="fc-card__end-date">{formatDate(deadline.end_date)}</span>
            </div>
        </div>
    )
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const FILTERS: { key: FilterKey; label: string }[] = [
    { key: 'todos', label: 'Todos' },
    { key: 'autonomos', label: 'Autónomos' },
    { key: 'particulares', label: 'Particulares' },
]

export default function FiscalCalendar({ deadlines, loading, error }: FiscalCalendarProps) {
    const today = new Date()
    const [currentMonth, setCurrentMonth] = useState(today.getMonth())
    const [currentYear, setCurrentYear] = useState(today.getFullYear())
    const [activeFilter, setActiveFilter] = useState<FilterKey>('todos')
    const timelineRef = useRef<HTMLDivElement>(null)

    const handleMonthChange = (month: number, year: number) => {
        setCurrentMonth(month)
        setCurrentYear(year)
    }

    // Filter by applies_to (past deadlines are kept — shown with atenuated style in past months)
    const filtered = deadlines.filter(d => {
        if (activeFilter === 'todos') return true
        if (activeFilter === 'autonomos') return d.applies_to === 'autonomos' || d.applies_to === 'todos'
        if (activeFilter === 'particulares') return d.applies_to === 'particulares' || d.applies_to === 'todos'
        return true
    })

    // Filter by current month — show any deadline whose range overlaps with this month
    const monthDeadlines = filtered.filter(d => {
        const start = new Date(d.start_date)
        const end = new Date(d.end_date)
        const monthStart = new Date(currentYear, currentMonth, 1)
        const monthEnd = new Date(currentYear, currentMonth + 1, 0)
        return start <= monthEnd && end >= monthStart
    })

    // Sort by end_date
    monthDeadlines.sort((a, b) => a.end_date.localeCompare(b.end_date))

    // Next upcoming deadline (not past)
    const upcoming = filtered
        .filter(d => d.daysRemaining >= 0)
        .sort((a, b) => a.daysRemaining - b.daysRemaining)[0]

    if (loading) {
        return (
            <div className="fc-loading">
                <div className="fc-loading__spinner" />
                <p>Cargando calendario fiscal...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="fc-error">
                <AlertCircle size={24} />
                <p>{error}</p>
            </div>
        )
    }

    return (
        <div className="fc-container">
            {/* Countdown para el próximo plazo */}
            {upcoming && <CountdownTimer deadline={upcoming} />}

            {/* Timeline de meses */}
            <Timeline
                deadlines={filtered}
                currentMonth={currentMonth}
                currentYear={currentYear}
                onMonthChange={handleMonthChange}
            />

            {/* Filtros */}
            <div className="fc-filters" ref={timelineRef}>
                <Filter size={16} className="fc-filters__icon" />
                {FILTERS.map(f => (
                    <button
                        key={f.key}
                        className={`fc-filter-btn ${activeFilter === f.key ? 'active' : ''}`}
                        onClick={() => setActiveFilter(f.key)}
                    >
                        {f.label}
                    </button>
                ))}
            </div>

            {/* Heading del mes */}
            <div className="fc-month-heading">
                <h2>{MONTH_NAMES[currentMonth]} {currentYear}</h2>
                <span className="fc-month-count">
                    {monthDeadlines.length} {monthDeadlines.length === 1 ? 'plazo' : 'plazos'}
                </span>
            </div>

            {/* Cards */}
            {monthDeadlines.length === 0 ? (
                <div className="fc-empty">
                    <Calendar size={40} />
                    <p>No hay plazos fiscales en {MONTH_NAMES[currentMonth]}</p>
                </div>
            ) : (
                <div className="fc-grid">
                    {monthDeadlines.map(d => (
                        <DeadlineCard key={d.id} deadline={d} />
                    ))}
                </div>
            )}
        </div>
    )
}
