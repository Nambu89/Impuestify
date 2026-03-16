import { useState, useEffect, useCallback } from 'react'
import { Navigate } from 'react-router-dom'
import {
    Shield, RefreshCw, AlertCircle, CheckCircle, Loader, Mail,
    ChevronLeft, ChevronRight, X, Check
} from 'lucide-react'
import { useSubscription } from '../hooks/useSubscription'
import { useFeedback, ContactRequest } from '../hooks/useFeedback'
import Header from '../components/Header'
import './AdminContactPage.css'

export default function AdminContactPage() {
    const { isOwner, loading: subLoading } = useSubscription()
    const { adminGetContactRequests, adminUpdateContactRequest } = useFeedback()

    const [items, setItems] = useState<ContactRequest[]>([])
    const [total, setTotal] = useState(0)
    const [loading, setLoading] = useState(true)
    const [page, setPage] = useState(1)
    const LIMIT = 20

    const [filterStatus, setFilterStatus] = useState('')

    const [selectedItem, setSelectedItem] = useState<ContactRequest | null>(null)
    const [updating, setUpdating] = useState<string | null>(null)

    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

    const fetchItems = useCallback(async () => {
        setLoading(true)
        try {
            const result = await adminGetContactRequests({
                status: filterStatus || undefined,
                page,
                limit: LIMIT,
            })
            setItems(result?.items || [])
            setTotal(result?.total || 0)
        } catch (err: any) {
            setItems([])
            setTotal(0)
            setMessage({ type: 'error', text: err.message || 'Error al cargar solicitudes de contacto' })
        } finally {
            setLoading(false)
        }
    }, [adminGetContactRequests, filterStatus, page])

    useEffect(() => {
        if (isOwner) fetchItems()
    }, [isOwner, fetchItems])

    useEffect(() => {
        if (message) {
            const t = setTimeout(() => setMessage(null), 5000)
            return () => clearTimeout(t)
        }
    }, [message])

    const handleMarkResponded = async (item: ContactRequest) => {
        if (updating) return
        setUpdating(item.id)
        try {
            await adminUpdateContactRequest(item.id, 'responded')
            setMessage({ type: 'success', text: `Solicitud de ${item.email} marcada como respondida` })
            await fetchItems()
            if (selectedItem?.id === item.id) {
                setSelectedItem({ ...item, status: 'responded' })
            }
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Error al actualizar solicitud' })
        } finally {
            setUpdating(null)
        }
    }

    const totalPages = Math.max(1, Math.ceil(total / LIMIT))

    const formatDate = (s: string) => {
        try {
            return new Date(s).toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' })
        } catch { return s }
    }

    const truncate = (text: string, max = 80) =>
        text.length > max ? text.slice(0, max) + '...' : text

    if (subLoading) return <div className="loading-screen">Cargando...</div>
    if (!isOwner) return <Navigate to="/chat" replace />

    return (
        <div className="admin-page acp-page">
            <Header />

            <main className="admin-main acp-main">
                <div className="admin-container acp-container">
                    {/* Page header */}
                    <div className="admin-header">
                        <div className="admin-title-row">
                            <h1><Mail size={26} /> Admin — Contacto</h1>
                            <button
                                className="btn-refresh"
                                onClick={fetchItems}
                                disabled={loading}
                                title="Recargar"
                            >
                                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                            </button>
                        </div>
                        <p className="admin-subtitle">
                            Solicitudes de contacto de usuarios ({total} total)
                        </p>
                    </div>

                    {/* Message banner */}
                    {message && (
                        <div className={`admin-message ${message.type}`}>
                            {message.type === 'success' ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
                            {message.text}
                        </div>
                    )}

                    {/* Filters */}
                    <div className="acp-filters">
                        <select
                            className="acp-select"
                            value={filterStatus}
                            onChange={e => { setFilterStatus(e.target.value); setPage(1) }}
                        >
                            <option value="">Todos los estados</option>
                            <option value="pending">Pendiente</option>
                            <option value="responded">Respondido</option>
                        </select>
                    </div>

                    {/* Layout */}
                    <div className={`acp-layout ${selectedItem ? 'acp-layout--with-detail' : ''}`}>
                        {/* List */}
                        <div className="acp-list">
                            {loading ? (
                                <div className="admin-loading">
                                    <Loader size={24} className="animate-spin" />
                                    <p>Cargando solicitudes...</p>
                                </div>
                            ) : items.length === 0 ? (
                                <div className="acp-empty">
                                    <Mail size={32} />
                                    <p>No hay solicitudes de contacto</p>
                                </div>
                            ) : (
                                <>
                                    {/* Mobile cards */}
                                    <div className="acp-cards">
                                        {items.map(item => (
                                            <div
                                                key={item.id}
                                                className={`acp-card ${selectedItem?.id === item.id ? 'acp-card--selected' : ''}`}
                                                onClick={() => setSelectedItem(item)}
                                            >
                                                <div className="acp-card__top">
                                                    <span className="acp-card__email">
                                                        <Mail size={13} />
                                                        {item.email}
                                                    </span>
                                                    <span className={`acp-status-badge acp-status--${item.status}`}>
                                                        {item.status === 'pending' ? 'Pendiente' : 'Respondido'}
                                                    </span>
                                                </div>
                                                {item.name && (
                                                    <p className="acp-card__name">{item.name}</p>
                                                )}
                                                {item.subject && (
                                                    <p className="acp-card__subject">{item.subject}</p>
                                                )}
                                                <p className="acp-card__preview">{truncate(item.message)}</p>
                                                <div className="acp-card__footer">
                                                    <span className="acp-date">{formatDate(item.created_at)}</span>
                                                    {item.status === 'pending' && (
                                                        <button
                                                            className="acp-respond-btn"
                                                            onClick={e => { e.stopPropagation(); handleMarkResponded(item) }}
                                                            disabled={updating === item.id}
                                                        >
                                                            {updating === item.id
                                                                ? <Loader size={12} className="animate-spin" />
                                                                : <Check size={12} />
                                                            }
                                                            Marcar respondido
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Desktop table */}
                                    <div className="acp-table-wrapper">
                                        <table className="acp-table">
                                            <thead>
                                                <tr>
                                                    <th>Email</th>
                                                    <th>Nombre</th>
                                                    <th>Asunto</th>
                                                    <th>Mensaje</th>
                                                    <th>Estado</th>
                                                    <th>Fecha</th>
                                                    <th>Acción</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {items.map(item => (
                                                    <tr
                                                        key={item.id}
                                                        className={selectedItem?.id === item.id ? 'acp-row--selected' : ''}
                                                        onClick={() => setSelectedItem(item)}
                                                    >
                                                        <td className="acp-cell-email">{item.email}</td>
                                                        <td>{item.name || '-'}</td>
                                                        <td className="acp-cell-subject">{item.subject || '-'}</td>
                                                        <td className="acp-cell-message">{truncate(item.message, 60)}</td>
                                                        <td>
                                                            <span className={`acp-status-badge acp-status--${item.status}`}>
                                                                {item.status === 'pending' ? 'Pendiente' : 'Respondido'}
                                                            </span>
                                                        </td>
                                                        <td className="acp-cell-date">{formatDate(item.created_at)}</td>
                                                        <td>
                                                            {item.status === 'pending' && (
                                                                <button
                                                                    className="acp-respond-btn"
                                                                    onClick={e => { e.stopPropagation(); handleMarkResponded(item) }}
                                                                    disabled={updating === item.id}
                                                                >
                                                                    {updating === item.id
                                                                        ? <Loader size={12} className="animate-spin" />
                                                                        : <Check size={12} />
                                                                    }
                                                                    Respondido
                                                                </button>
                                                            )}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>

                                    {/* Pagination */}
                                    <div className="acp-pagination">
                                        <button
                                            className="afp-page-btn"
                                            onClick={() => setPage(p => Math.max(1, p - 1))}
                                            disabled={page === 1 || loading}
                                        >
                                            <ChevronLeft size={16} />
                                        </button>
                                        <span className="afp-page-info">
                                            Página {page} de {totalPages}
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
                        {selectedItem && (
                            <div className="acp-detail">
                                <div className="acp-detail__header">
                                    <h3>Mensaje completo</h3>
                                    <button
                                        className="afp-detail__close"
                                        onClick={() => setSelectedItem(null)}
                                        aria-label="Cerrar panel"
                                    >
                                        <X size={18} />
                                    </button>
                                </div>

                                <div className="acp-detail__body">
                                    <div className="acp-detail__row">
                                        <span className="acp-detail__label">Email</span>
                                        <a href={`mailto:${selectedItem.email}`} className="acp-detail__link">
                                            {selectedItem.email}
                                        </a>
                                    </div>
                                    {selectedItem.name && (
                                        <div className="acp-detail__row">
                                            <span className="acp-detail__label">Nombre</span>
                                            <span className="acp-detail__value">{selectedItem.name}</span>
                                        </div>
                                    )}
                                    {selectedItem.subject && (
                                        <div className="acp-detail__row">
                                            <span className="acp-detail__label">Asunto</span>
                                            <span className="acp-detail__value">{selectedItem.subject}</span>
                                        </div>
                                    )}
                                    <div className="acp-detail__row">
                                        <span className="acp-detail__label">Fecha</span>
                                        <span className="acp-detail__value">{formatDate(selectedItem.created_at)}</span>
                                    </div>
                                    <div className="acp-detail__row">
                                        <span className="acp-detail__label">Estado</span>
                                        <span className={`acp-status-badge acp-status--${selectedItem.status}`}>
                                            {selectedItem.status === 'pending' ? 'Pendiente' : 'Respondido'}
                                        </span>
                                    </div>

                                    <div className="acp-detail__divider" />

                                    <p className="acp-detail__message">{selectedItem.message}</p>

                                    {selectedItem.status === 'pending' && (
                                        <button
                                            className="afp-save-btn"
                                            onClick={() => handleMarkResponded(selectedItem)}
                                            disabled={updating === selectedItem.id}
                                        >
                                            {updating === selectedItem.id
                                                ? <><Loader size={14} className="animate-spin" /> Guardando...</>
                                                : <><Check size={14} /> Marcar como respondido</>
                                            }
                                        </button>
                                    )}

                                    <a
                                        className="acp-reply-link"
                                        href={`mailto:${selectedItem.email}?subject=Re: ${selectedItem.subject || 'Tu consulta en Impuestify'}`}
                                    >
                                        <Mail size={14} />
                                        Responder por email
                                    </a>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    )
}
