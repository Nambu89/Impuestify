import { CalendarDays, RefreshCw } from 'lucide-react'
import Header from '../components/Header'
import FiscalCalendar from '../components/FiscalCalendar'
import PushPermissionBanner from '../components/PushPermissionBanner'
import { useDeadlines } from '../hooks/useDeadlines'
import './CalendarPage.css'

export default function CalendarPage() {
    const { deadlines, loading, error, refresh } = useDeadlines({
        days: 365,
        isPublic: false,
    })

    return (
        <div className="calendar-page">
            <Header />

            {/* Dark header strip */}
            <div className="calendar-page__header">
                <CalendarDays size={28} />
                <div>
                    <h1>Calendario Fiscal 2026</h1>
                    <p>Plazos fiscales adaptados a tu perfil y comunidad autónoma</p>
                </div>
                <button
                    className="calendar-page__refresh"
                    onClick={refresh}
                    aria-label="Actualizar plazos"
                    title="Actualizar plazos"
                >
                    <RefreshCw size={18} />
                </button>
            </div>

            {/* Main content */}
            <div className="calendar-page__main">
                <PushPermissionBanner />
                <FiscalCalendar
                    deadlines={deadlines}
                    loading={loading}
                    error={error}
                />
            </div>
        </div>
    )
}
