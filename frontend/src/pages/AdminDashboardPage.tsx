import { useState, useEffect, useCallback } from 'react'
import { Navigate, Link } from 'react-router-dom'
import {
    Shield, RefreshCw, Users, CreditCard, Bug, ThumbsUp,
    AlertCircle, Loader, ArrowRight, MessageCircle, Lightbulb,
    Mail, ThumbsDown, DollarSign
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useSubscription } from '../hooks/useSubscription'
import { useFeedback, DashboardData, FeedbackItem, ContactRequest, ChatRatingItem } from '../hooks/useFeedback'
import Header from '../components/Header'
import './AdminDashboardPage.css'

const TYPE_LABELS: Record<string, string> = {
    bug: 'Error',
    feature: 'Sugerencia',
    general: 'General',
}

const STATUS_LABELS: Record<string, string> = {
    new: 'Nuevo',
    reviewed: 'Revisado',
    planned: 'Planificado',
    in_progress: 'En progreso',
    done: 'Resuelto',
    wont_fix: 'Descartado',
}

interface CostSummary {
    period: string
    total_requests: number
    total_tokens: number
    total_cost_usd: number
    total_cost_eur: number
    top_users: Array<{
        user_id: string
        email: string
        subscription_plan: string
        user_cost_usd: number
        request_count: number
    }>
    by_plan: Record<string, { plan_cost_usd: number; user_count: number }>
}

export default function AdminDashboardPage() {
    const { isOwner, loading: subLoading } = useSubscription()
    const { adminGetDashboard, adminGetFeedback, adminGetContactRequests, adminGetChatRatings } = useFeedback()
    const { apiRequest } = useApi()

    const [dashboard, setDashboard] = useState<DashboardData | null>(null)
    const [recentFeedback, setRecentFeedback] = useState<FeedbackItem[]>([])
    const [pendingContacts, setPendingContacts] = useState<ContactRequest[]>([])
    const [negativeRatings, setNegativeRatings] = useState<ChatRatingItem[]>([])
    const [costData, setCostData] = useState<CostSummary | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchAll = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const [dash, fb, contacts, ratings] = await Promise.all([
                adminGetDashboard(),
                adminGetFeedback({ limit: 5 }),
                adminGetContactRequests({ status: 'pending', limit: 5 }),
                adminGetChatRatings({ rating: '-1', limit: 5 }),
            ])
            setDashboard(dash || null)
            setRecentFeedback(fb?.items || [])
            setPendingContacts(contacts?.items || [])
            setNegativeRatings(ratings?.items || [])

            // Fetch cost data separately (non-blocking if it fails)
            try {
                const costs = await apiRequest<CostSummary>('/api/admin/costs?period=month')
                setCostData(costs)
            } catch {
                setCostData(null)
            }
        } catch (err: any) {
            setRecentFeedback([])
            setPendingContacts([])
            setNegativeRatings([])
            setError(err.message || 'Error al cargar el dashboard')
        } finally {
            setLoading(false)
        }
    }, [adminGetDashboard, adminGetFeedback, adminGetContactRequests, adminGetChatRatings, apiRequest])

    useEffect(() => {
        if (isOwner) fetchAll()
    }, [isOwner, fetchAll])

    const formatDate = (s: string) => {
        try {
            return new Date(s).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' })
        } catch { return s }
    }

    if (subLoading) return <div className="loading-screen">Cargando...</div>
    if (!isOwner) return <Navigate to="/chat" replace />

    return (
        <div className="admin-page adp-page">
            <Header />

            <main className="admin-main adp-main">
                <div className="admin-container adp-container">
                    {/* Page header */}
                    <div className="admin-header">
                        <div className="admin-title-row">
                            <h1><Shield size={26} /> Admin — Dashboard</h1>
                            <button
                                className="btn-refresh"
                                onClick={fetchAll}
                                disabled={loading}
                                title="Recargar datos"
                            >
                                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                            </button>
                        </div>
                        <p className="admin-subtitle">Vista general del sistema</p>
                    </div>

                    {error && (
                        <div className="admin-message error">
                            <AlertCircle size={18} />
                            {error}
                        </div>
                    )}

                    {loading ? (
                        <div className="admin-loading">
                            <Loader size={28} className="animate-spin" />
                            <p>Cargando métricas...</p>
                        </div>
                    ) : dashboard ? (
                        <>
                            {/* KPI Cards */}
                            <div className="adp-kpi-grid">
                                <div className="adp-kpi adp-kpi--users">
                                    <div className="adp-kpi__icon">
                                        <Users size={22} />
                                    </div>
                                    <div className="adp-kpi__content">
                                        <span className="adp-kpi__value">{dashboard.users.total}</span>
                                        <span className="adp-kpi__label">Usuarios totales</span>
                                        <span className="adp-kpi__sub">
                                            {dashboard.users.active_this_week} activos esta semana
                                        </span>
                                    </div>
                                </div>

                                <div className="adp-kpi adp-kpi--subs">
                                    <div className="adp-kpi__icon">
                                        <CreditCard size={22} />
                                    </div>
                                    <div className="adp-kpi__content">
                                        <span className="adp-kpi__value">{dashboard.users.subscribers_paid}</span>
                                        <span className="adp-kpi__label">Suscriptores de pago</span>
                                        <span className="adp-kpi__sub">
                                            {dashboard.users.by_plan.particular} Particular · {dashboard.users.by_plan.autonomo} Autónomo
                                        </span>
                                    </div>
                                </div>

                                <div className="adp-kpi adp-kpi--bugs">
                                    <div className="adp-kpi__icon">
                                        <Bug size={22} />
                                    </div>
                                    <div className="adp-kpi__content">
                                        <span className="adp-kpi__value">{dashboard.feedback.bugs_open}</span>
                                        <span className="adp-kpi__label">Bugs abiertos</span>
                                        <span className="adp-kpi__sub">
                                            {dashboard.feedback.features_pending} sugerencias pendientes
                                        </span>
                                    </div>
                                </div>

                                <div className="adp-kpi adp-kpi--ratings">
                                    <div className="adp-kpi__icon">
                                        <ThumbsUp size={22} />
                                    </div>
                                    <div className="adp-kpi__content">
                                        <span className="adp-kpi__value">
                                            {dashboard.ratings.positive_pct > 0
                                                ? `${dashboard.ratings.positive_pct.toFixed(1)}%`
                                                : '-'}
                                        </span>
                                        <span className="adp-kpi__label">Valoraciones positivas</span>
                                        <span className="adp-kpi__sub">
                                            {dashboard.ratings.total} valoraciones · tendencia {dashboard.ratings.trend_30d}
                                        </span>
                                    </div>
                                </div>

                                {costData && (
                                    <div className="adp-kpi adp-kpi--costs">
                                        <div className="adp-kpi__icon">
                                            <DollarSign size={22} />
                                        </div>
                                        <div className="adp-kpi__content">
                                            <span className="adp-kpi__value">
                                                {costData.total_cost_eur.toFixed(2)} EUR
                                            </span>
                                            <span className="adp-kpi__label">Coste LLM este mes</span>
                                            <span className="adp-kpi__sub">
                                                {costData.total_requests} peticiones · {(costData.total_tokens / 1000).toFixed(0)}K tokens
                                            </span>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Sections row */}
                            <div className="adp-sections">
                                {/* Recent feedback */}
                                <div className="adp-section">
                                    <div className="adp-section__header">
                                        <h3>
                                            <MessageCircle size={16} />
                                            Feedback reciente
                                        </h3>
                                        <Link to="/admin/feedback" className="adp-section__link">
                                            Ver todo <ArrowRight size={14} />
                                        </Link>
                                    </div>
                                    {recentFeedback.length === 0 ? (
                                        <p className="adp-empty-text">Sin feedbacks recientes</p>
                                    ) : (
                                        <ul className="adp-list">
                                            {recentFeedback.map(item => (
                                                <li key={item.id} className="adp-list-item">
                                                    <div className="adp-list-item__main">
                                                        <span className={`adp-type-dot adp-type--${item.type}`} title={TYPE_LABELS[item.type]} />
                                                        <span className="adp-list-item__title">{item.title}</span>
                                                    </div>
                                                    <div className="adp-list-item__meta">
                                                        <span className={`adp-status-mini adp-status--${item.status}`}>
                                                            {STATUS_LABELS[item.status]}
                                                        </span>
                                                        <span className="adp-date">{formatDate(item.created_at)}</span>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>

                                {/* Pending contacts */}
                                <div className="adp-section">
                                    <div className="adp-section__header">
                                        <h3>
                                            <Mail size={16} />
                                            Contactos pendientes
                                            {dashboard.contact_requests.pending > 0 && (
                                                <span className="adp-badge">{dashboard.contact_requests.pending}</span>
                                            )}
                                        </h3>
                                        <Link to="/admin/contact" className="adp-section__link">
                                            Ver todo <ArrowRight size={14} />
                                        </Link>
                                    </div>
                                    {pendingContacts.length === 0 ? (
                                        <p className="adp-empty-text">Sin solicitudes pendientes</p>
                                    ) : (
                                        <ul className="adp-list">
                                            {pendingContacts.map(item => (
                                                <li key={item.id} className="adp-list-item">
                                                    <div className="adp-list-item__main">
                                                        <span className="adp-list-item__email">{item.email}</span>
                                                    </div>
                                                    <div className="adp-list-item__meta">
                                                        <span className="adp-date">{formatDate(item.created_at)}</span>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>

                                {/* Negative ratings */}
                                <div className="adp-section">
                                    <div className="adp-section__header">
                                        <h3>
                                            <ThumbsDown size={16} />
                                            Valoraciones negativas
                                        </h3>
                                        <Link to="/admin/feedback" className="adp-section__link">
                                            Ver feedback <ArrowRight size={14} />
                                        </Link>
                                    </div>
                                    {negativeRatings.length === 0 ? (
                                        <p className="adp-empty-text">Sin valoraciones negativas recientes</p>
                                    ) : (
                                        <ul className="adp-list">
                                            {negativeRatings.map(item => (
                                                <li key={item.id} className="adp-list-item">
                                                    <div className="adp-list-item__main">
                                                        <ThumbsDown size={12} className="adp-thumb-down" />
                                                        <span className="adp-list-item__comment">
                                                            {item.comment || 'Sin comentario'}
                                                        </span>
                                                    </div>
                                                    <div className="adp-list-item__meta">
                                                        <span className="adp-list-item__email">{item.user_email || '-'}</span>
                                                        <span className="adp-date">{formatDate(item.created_at)}</span>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>

                                {/* Top users by cost */}
                                {costData && costData.top_users.length > 0 && (
                                    <div className="adp-section">
                                        <div className="adp-section__header">
                                            <h3>
                                                <DollarSign size={16} />
                                                Top usuarios por coste
                                            </h3>
                                        </div>
                                        <ul className="adp-list">
                                            {costData.top_users.slice(0, 5).map((user, idx) => (
                                                <li key={user.user_id || idx} className="adp-list-item">
                                                    <div className="adp-list-item__main">
                                                        <span className="adp-list-item__email">
                                                            {user.email || user.user_id?.slice(0, 8)}
                                                        </span>
                                                    </div>
                                                    <div className="adp-list-item__meta">
                                                        <span className="adp-status-mini">
                                                            {user.subscription_plan || 'none'}
                                                        </span>
                                                        <span className="adp-kpi__value" style={{ fontSize: '0.85rem' }}>
                                                            ${user.user_cost_usd?.toFixed(4)}
                                                        </span>
                                                        <span className="adp-date">
                                                            {user.request_count} req
                                                        </span>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>

                            {/* Quick links */}
                            <div className="adp-quicklinks">
                                <h3 className="adp-quicklinks__title">Accesos rápidos</h3>
                                <div className="adp-quicklinks__grid">
                                    <Link to="/admin/users" className="adp-quicklink">
                                        <Users size={20} />
                                        <span>Gestión de usuarios</span>
                                        <ArrowRight size={16} className="adp-quicklink__arrow" />
                                    </Link>
                                    <Link to="/admin/feedback" className="adp-quicklink">
                                        <Lightbulb size={20} />
                                        <span>Feedback y sugerencias</span>
                                        <ArrowRight size={16} className="adp-quicklink__arrow" />
                                    </Link>
                                    <Link to="/admin/contact" className="adp-quicklink">
                                        <Mail size={20} />
                                        <span>Solicitudes de contacto</span>
                                        <ArrowRight size={16} className="adp-quicklink__arrow" />
                                    </Link>
                                </div>
                            </div>
                        </>
                    ) : null}
                </div>
            </main>
        </div>
    )
}
