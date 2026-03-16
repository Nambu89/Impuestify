import { useState, useEffect, useCallback } from 'react'
import { Navigate } from 'react-router-dom'
import {
    Shield, RefreshCw, AlertCircle, CheckCircle, Loader, Bug, Lightbulb,
    MessageCircle, X, ExternalLink, ChevronLeft, ChevronRight, Image as ImageIcon
} from 'lucide-react'
import { useSubscription } from '../hooks/useSubscription'
import { useFeedback, FeedbackItem, FeedbackStats } from '../hooks/useFeedback'
import Header from '../components/Header'
import './AdminFeedbackPage.css'

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

const PRIORITY_LABELS: Record<string, string> = {
    low: 'Baja',
    normal: 'Normal',
    high: 'Alta',
    critical: 'Crítica',
}

function TypeIcon({ type }: { type: string }) {
    if (type === 'bug') return <Bug size={14} />
    if (type === 'feature') return <Lightbulb size={14} />
    return <MessageCircle size={14} />
}

export default function AdminFeedbackPage() {
    const { isOwner, loading: subLoading } = useSubscription()
    const { adminGetFeedback, adminGetFeedbackStats, adminGetFeedbackDetail, adminUpdateFeedback } = useFeedback()

    const [items, setItems] = useState<FeedbackItem[]>([])
    const [stats, setStats] = useState<FeedbackStats | null>(null)
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const LIMIT = 20

    // Filters
    const [filterType, setFilterType] = useState('')
    const [filterStatus, setFilterStatus] = useState('')
    const [filterPriority, setFilterPriority] = useState('')

    // Detail panel
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [detail, setDetail] = useState<(FeedbackItem & { screenshot_data?: string }) | null>(null)
    const [detailLoading, setDetailLoading] = useState(false)
    const [editStatus, setEditStatus] = useState<FeedbackItem['status']>('new')
    const [editPriority, setEditPriority] = useState<FeedbackItem['priority']>('normal')
    const [editNotes, setEditNotes] = useState('')
    const [saving, setSaving] = useState(false)
    const [showScreenshot, setShowScreenshot] = useState(false)

    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

    const fetchItems = useCallback(async () => {
        setLoading(true)
        try {
            const result = await adminGetFeedback({
                type: filterType || undefined,
                status: filterStatus || undefined,
                priority: filterPriority || undefined,
                page,
                limit: LIMIT,
            })
            setItems(result?.items || [])
            setTotal(result?.total || 0)
        } catch (err: any) {
            setItems([])
            setTotal(0)
            setMessage({ type: 'error', text: err.message || 'Error al cargar feedbacks' })
        } finally {
            setLoading(false)
        }
    }, [adminGetFeedback, filterType, filterStatus, filterPriority, page])

    const fetchStats = useCallback(async () => {
        try {
            const s = await adminGetFeedbackStats()
            setStats(s)
        } catch {
            // Stats are non-critical
        }
    }, [adminGetFeedbackStats])

    useEffect(() => {
        if (isOwner) {
            fetchItems()
            fetchStats()
        }
    }, [isOwner, fetchItems, fetchStats])

    useEffect(() => {
        if (message) {
            const t = setTimeout(() => setMessage(null), 5000)
            return () => clearTimeout(t)
        }
    }, [message])

    const handleRowClick = async (id: string) => {
        setSelectedId(id)
        setDetailLoading(true)
        setShowScreenshot(false)
        try {
            const d = await adminGetFeedbackDetail(id)
            setDetail(d)
            setEditStatus(d.status)
            setEditPriority(d.priority)
            setEditNotes(d.admin_notes || '')
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Error al cargar detalle' })
        } finally {
            setDetailLoading(false)
        }
    }

    const handleSave = async () => {
        if (!selectedId || saving) return
        setSaving(true)
        try {
            await adminUpdateFeedback(selectedId, {
                status: editStatus,
                priority: editPriority,
                admin_notes: editNotes,
            })
            setMessage({ type: 'success', text: 'Feedback actualizado' })
            await fetchItems()
            await fetchStats()
            // Update item in list inline
            setItems(prev => prev.map(i => i.id === selectedId
                ? { ...i, status: editStatus, priority: editPriority, admin_notes: editNotes }
                : i
            ))
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Error al guardar cambios' })
        } finally {
            setSaving(false)
        }
    }

    const handleFilter = () => {
        setPage(1)
        fetchItems()
        fetchStats()
    }

    const totalPages = Math.max(1, Math.ceil(total / LIMIT))

    const formatDate = (s: string) => {
        try {
            return new Date(s).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
        } catch { return s }
    }

    if (subLoading) return <div className="loading-screen">Cargando...</div>
    if (!isOwner) return <Navigate to="/chat" replace />

    return (
        <div className="admin-page afp-page">
            <Header />

            <main className="admin-main afp-main">
                <div className="admin-container afp-container">
                    {/* Page header */}
                    <div className="admin-header">
                        <div className="admin-title-row">
                            <h1><Shield size={26} /> Admin — Feedback</h1>
                            <button
                                className="btn-refresh"
                                onClick={() => { fetchItems(); fetchStats() }}
                                disabled={loading}
                                title="Recargar"
                            >
                                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                            </button>
                        </div>
                        <p className="admin-subtitle">Gestión de reportes y sugerencias de usuarios</p>
                    </div>

                    {/* Stats bar */}
                    {stats && (
                        <div className="afp-stats">
                            <div className="afp-stat afp-stat--bug">
                                <Bug size={16} />
                                <div>
                                    <span className="afp-stat__value">{stats.bugs_open}</span>
                                    <span className="afp-stat__label">Bugs abiertos</span>
                                </div>
                            </div>
                            <div className="afp-stat afp-stat--feature">
                                <Lightbulb size={16} />
                                <div>
                                    <span className="afp-stat__value">{stats.features_pending}</span>
                                    <span className="afp-stat__label">Sugerencias</span>
                                </div>
                            </div>
                            <div className="afp-stat afp-stat--new">
                                <AlertCircle size={16} />
                                <div>
                                    <span className="afp-stat__value">{stats.new_count}</span>
                                    <span className="afp-stat__label">Sin revisar</span>
                                </div>
                            </div>
                            <div className="afp-stat afp-stat--total">
                                <MessageCircle size={16} />
                                <div>
                                    <span className="afp-stat__value">{stats.total}</span>
                                    <span className="afp-stat__label">Total</span>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Message banner */}
                    {message && (
                        <div className={`admin-message ${message.type}`}>
                            {message.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                            {message.text}
                        </div>
                    )}

                    {/* Filters */}
                    <div className="afp-filters">
                        <select
                            className="afp-select"
                            value={filterType}
                            onChange={e => setFilterType(e.target.value)}
                        >
                            <option value="">Todos los tipos</option>
                            <option value="bug">Error</option>
                            <option value="feature">Sugerencia</option>
                            <option value="general">General</option>
                        </select>
                        <select
                            className="afp-select"
                            value={filterStatus}
                            onChange={e => setFilterStatus(e.target.value)}
                        >
                            <option value="">Todos los estados</option>
                            <option value="new">Nuevo</option>
                            <option value="reviewed">Revisado</option>
                            <option value="planned">Planificado</option>
                            <option value="in_progress">En progreso</option>
                            <option value="done">Resuelto</option>
                            <option value="wont_fix">Descartado</option>
                        </select>
                        <select
                            className="afp-select"
                            value={filterPriority}
                            onChange={e => setFilterPriority(e.target.value)}
                        >
                            <option value="">Todas las prioridades</option>
                            <option value="critical">Crítica</option>
                            <option value="high">Alta</option>
                            <option value="normal">Normal</option>
                            <option value="low">Baja</option>
                        </select>
                        <button className="afp-filter-btn" onClick={handleFilter}>
                            Filtrar
                        </button>
                    </div>

                    {/* Content: list + detail panel */}
                    <div className={`afp-layout ${selectedId ? 'afp-layout--with-detail' : ''}`}>
                        {/* List */}
                        <div className="afp-list">
                            {loading ? (
                                <div className="admin-loading">
                                    <Loader size={24} className="animate-spin" />
                                    <p>Cargando feedbacks...</p>
                                </div>
                            ) : items.length === 0 ? (
                                <div className="afp-empty">
                                    <MessageCircle size={32} />
                                    <p>No hay feedbacks con estos filtros</p>
                                </div>
                            ) : (
                                <>
                                    {/* Mobile cards */}
                                    <div className="afp-cards">
                                        {items.map(item => (
                                            <div
                                                key={item.id}
                                                className={`afp-card ${selectedId === item.id ? 'afp-card--selected' : ''}`}
                                                onClick={() => handleRowClick(item.id)}
                                            >
                                                <div className="afp-card__top">
                                                    <span className={`afp-type-badge afp-type--${item.type}`}>
                                                        <TypeIcon type={item.type} />
                                                        {TYPE_LABELS[item.type]}
                                                    </span>
                                                    <span className={`afp-status-badge afp-status--${item.status}`}>
                                                        {STATUS_LABELS[item.status]}
                                                    </span>
                                                </div>
                                                <p className="afp-card__title">{item.title}</p>
                                                <div className="afp-card__meta">
                                                    <span className={`afp-priority afp-priority--${item.priority}`}>
                                                        {PRIORITY_LABELS[item.priority]}
                                                    </span>
                                                    <span className="afp-date">{formatDate(item.created_at)}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Desktop table */}
                                    <div className="afp-table-wrapper">
                                        <table className="afp-table">
                                            <thead>
                                                <tr>
                                                    <th>Tipo</th>
                                                    <th>Título</th>
                                                    <th>Usuario</th>
                                                    <th>Estado</th>
                                                    <th>Prioridad</th>
                                                    <th>Fecha</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {items.map(item => (
                                                    <tr
                                                        key={item.id}
                                                        className={selectedId === item.id ? 'afp-row--selected' : ''}
                                                        onClick={() => handleRowClick(item.id)}
                                                    >
                                                        <td>
                                                            <span className={`afp-type-badge afp-type--${item.type}`}>
                                                                <TypeIcon type={item.type} />
                                                                {TYPE_LABELS[item.type]}
                                                            </span>
                                                        </td>
                                                        <td className="afp-cell-title">{item.title}</td>
                                                        <td className="afp-cell-email">{item.user_email || '-'}</td>
                                                        <td>
                                                            <span className={`afp-status-badge afp-status--${item.status}`}>
                                                                {STATUS_LABELS[item.status]}
                                                            </span>
                                                        </td>
                                                        <td>
                                                            <span className={`afp-priority afp-priority--${item.priority}`}>
                                                                {PRIORITY_LABELS[item.priority]}
                                                            </span>
                                                        </td>
                                                        <td className="afp-cell-date">{formatDate(item.created_at)}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>

                                    {/* Pagination */}
                                    <div className="afp-pagination">
                                        <button
                                            className="afp-page-btn"
                                            onClick={() => setPage(p => Math.max(1, p - 1))}
                                            disabled={page === 1 || loading}
                                        >
                                            <ChevronLeft size={16} />
                                        </button>
                                        <span className="afp-page-info">
                                            Página {page} de {totalPages} ({total} total)
                                        </span>
                                        <button
                                            className="afp-page-btn"
                                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                                            disabled={page >= totalPages || loading}
                                        >
                                            <ChevronRight size={16} />
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Detail panel */}
                        {selectedId && (
                            <div className="afp-detail">
                                <div className="afp-detail__header">
                                    <h3>Detalle</h3>
                                    <button
                                        className="afp-detail__close"
                                        onClick={() => { setSelectedId(null); setDetail(null) }}
                                        aria-label="Cerrar panel"
                                    >
                                        <X size={18} />
                                    </button>
                                </div>

                                {detailLoading ? (
                                    <div className="admin-loading">
                                        <Loader size={20} className="animate-spin" />
                                    </div>
                                ) : detail ? (
                                    <div className="afp-detail__body">
                                        {/* Meta */}
                                        <div className="afp-detail__meta">
                                            <span className={`afp-type-badge afp-type--${detail.type}`}>
                                                <TypeIcon type={detail.type} />
                                                {TYPE_LABELS[detail.type]}
                                            </span>
                                            <span className="afp-date">{formatDate(detail.created_at)}</span>
                                        </div>

                                        <h4 className="afp-detail__title">{detail.title}</h4>
                                        <p className="afp-detail__desc">{detail.description}</p>

                                        {detail.page_url && (
                                            <a
                                                className="afp-detail__url"
                                                href={detail.page_url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                <ExternalLink size={12} />
                                                {detail.page_url}
                                            </a>
                                        )}

                                        {detail.screenshot_data && (
                                            <div className="afp-detail__screenshot">
                                                {showScreenshot ? (
                                                    <>
                                                        <img
                                                            src={detail.screenshot_data}
                                                            alt="Captura adjunta"
                                                            onClick={() => setShowScreenshot(false)}
                                                        />
                                                        <button
                                                            className="afp-screenshot-toggle"
                                                            onClick={() => setShowScreenshot(false)}
                                                        >
                                                            Ocultar captura
                                                        </button>
                                                    </>
                                                ) : (
                                                    <button
                                                        className="afp-screenshot-toggle"
                                                        onClick={() => setShowScreenshot(true)}
                                                    >
                                                        <ImageIcon size={14} />
                                                        Ver captura adjunta
                                                    </button>
                                                )}
                                            </div>
                                        )}

                                        <div className="afp-detail__divider" />

                                        {/* Edit fields */}
                                        <div className="afp-edit-field">
                                            <label className="afp-edit-label">Estado</label>
                                            <select
                                                className="afp-edit-select"
                                                value={editStatus}
                                                onChange={e => setEditStatus(e.target.value as FeedbackItem['status'])}
                                            >
                                                <option value="new">Nuevo</option>
                                                <option value="reviewed">Revisado</option>
                                                <option value="planned">Planificado</option>
                                                <option value="in_progress">En progreso</option>
                                                <option value="done">Resuelto</option>
                                                <option value="wont_fix">Descartado</option>
                                            </select>
                                        </div>

                                        <div className="afp-edit-field">
                                            <label className="afp-edit-label">Prioridad</label>
                                            <select
                                                className="afp-edit-select"
                                                value={editPriority}
                                                onChange={e => setEditPriority(e.target.value as FeedbackItem['priority'])}
                                            >
                                                <option value="critical">Crítica</option>
                                                <option value="high">Alta</option>
                                                <option value="normal">Normal</option>
                                                <option value="low">Baja</option>
                                            </select>
                                        </div>

                                        <div className="afp-edit-field">
                                            <label className="afp-edit-label">Notas de admin</label>
                                            <textarea
                                                className="afp-edit-textarea"
                                                value={editNotes}
                                                onChange={e => setEditNotes(e.target.value)}
                                                placeholder="Notas internas sobre este feedback..."
                                                rows={3}
                                            />
                                        </div>

                                        <button
                                            className="afp-save-btn"
                                            onClick={handleSave}
                                            disabled={saving}
                                        >
                                            {saving
                                                ? <><Loader size={14} className="animate-spin" /> Guardando...</>
                                                : <><CheckCircle size={14} /> Guardar cambios</>
                                            }
                                        </button>
                                    </div>
                                ) : null}
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    )
}
