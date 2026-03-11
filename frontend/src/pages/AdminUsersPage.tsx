import { useState, useEffect, useCallback } from 'react'
import { Navigate } from 'react-router-dom'
import {
    Users, RefreshCw, Shield, AlertCircle, CheckCircle,
    Crown, ArrowUpDown, Loader, UserCheck, UserX
} from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { useSubscription } from '../hooks/useSubscription'
import Header from '../components/Header'
import './AdminUsersPage.css'

interface UserListItem {
    id: string
    email: string
    name: string | null
    is_owner: boolean
    plan_type: string | null
    subscription_status: string | null
    created_at: string | null
}

export default function AdminUsersPage() {
    const { apiRequest } = useApi()
    const { isOwner, loading: subLoading } = useSubscription()

    const [users, setUsers] = useState<UserListItem[]>([])
    const [loading, setLoading] = useState(true)
    const [changingPlan, setChangingPlan] = useState<string | null>(null)
    const [togglingBeta, setTogglingBeta] = useState<string | null>(null)
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

    const fetchUsers = useCallback(async () => {
        try {
            setLoading(true)
            const result = await apiRequest<UserListItem[]>('/api/admin/users')
            setUsers(result)
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Error al cargar usuarios' })
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    useEffect(() => {
        if (isOwner) fetchUsers()
    }, [isOwner, fetchUsers])

    // Auto-dismiss messages
    useEffect(() => {
        if (message) {
            const timer = setTimeout(() => setMessage(null), 5000)
            return () => clearTimeout(timer)
        }
    }, [message])

    if (subLoading) {
        return <div className="loading-screen">Cargando...</div>
    }

    if (!isOwner) {
        return <Navigate to="/chat" replace />
    }

    const handleChangePlan = async (userId: string, email: string, newPlan: string) => {
        const planLabel = newPlan === 'autonomo' ? 'Autónomo' : 'Particular'
        const confirmed = window.confirm(
            `Cambiar plan de ${email} a "${planLabel}"?`
        )
        if (!confirmed) return

        try {
            setChangingPlan(userId)
            await apiRequest(`/api/admin/users/${userId}/plan`, {
                method: 'PUT',
                body: JSON.stringify({ plan_type: newPlan }),
            })
            setMessage({ type: 'success', text: `Plan de ${email} cambiado a ${planLabel}` })
            await fetchUsers()
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || 'Error al cambiar plan' })
        } finally {
            setChangingPlan(null)
        }
    }

    const handleToggleBeta = async (userId: string, email: string, isActive: boolean) => {
        const action = isActive ? 'revocar' : 'activar'
        const confirmed = window.confirm(
            `¿${isActive ? 'Revocar' : 'Activar'} acceso beta para ${email}?`
        )
        if (!confirmed) return

        try {
            setTogglingBeta(userId)
            const endpoint = isActive ? 'revoke-beta' : 'grant-beta'
            await apiRequest(`/api/admin/users/${userId}/${endpoint}`, { method: 'PUT' })
            setMessage({ type: 'success', text: `Beta ${isActive ? 'revocado' : 'activado'} para ${email}` })
            await fetchUsers()
        } catch (err: any) {
            setMessage({ type: 'error', text: err.message || `Error al ${action} beta` })
        } finally {
            setTogglingBeta(null)
        }
    }

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-'
        try {
            return new Date(dateStr).toLocaleDateString('es-ES', {
                day: '2-digit', month: 'short', year: 'numeric'
            })
        } catch {
            return dateStr
        }
    }

    const getPlanBadgeClass = (planType: string | null) => {
        switch (planType) {
            case 'owner': return 'badge-owner'
            case 'autonomo': return 'badge-autonomo'
            case 'particular': return 'badge-particular'
            default: return 'badge-none'
        }
    }

    const getStatusBadgeClass = (status: string | null) => {
        switch (status) {
            case 'active': return 'badge-active'
            case 'grace_period': return 'badge-grace'
            case 'inactive': return 'badge-inactive'
            default: return 'badge-none'
        }
    }

    const getStatusLabel = (status: string | null) => {
        switch (status) {
            case 'active': return 'Activo'
            case 'grace_period': return 'Grace Period'
            case 'inactive': return 'Inactivo'
            default: return 'Sin suscripción'
        }
    }

    return (
        <div className="admin-page">
            <Header />

            <main className="admin-main">
                <div className="admin-container">
                    <div className="admin-header">
                        <div className="admin-title-row">
                            <h1><Shield size={28} /> Admin - Usuarios</h1>
                            <button
                                className="btn-refresh"
                                onClick={fetchUsers}
                                disabled={loading}
                                title="Recargar lista"
                            >
                                <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                            </button>
                        </div>
                        <p className="admin-subtitle">
                            Gestión de planes y suscripciones ({users.length} usuarios)
                        </p>
                    </div>

                    {message && (
                        <div className={`admin-message ${message.type}`}>
                            {message.type === 'success'
                                ? <CheckCircle size={18} />
                                : <AlertCircle size={18} />
                            }
                            {message.text}
                        </div>
                    )}

                    {loading ? (
                        <div className="admin-loading">
                            <Loader size={24} className="animate-spin" />
                            <p>Cargando usuarios...</p>
                        </div>
                    ) : (
                        <>
                            {/* Mobile: Cards layout */}
                            <div className="users-cards">
                                {users.map(u => (
                                    <div key={u.id} className="user-card">
                                        <div className="user-card-header">
                                            <div className="user-card-info">
                                                <span className="user-card-email">
                                                    {u.is_owner && <Crown size={14} className="owner-icon" />}
                                                    {u.email}
                                                </span>
                                                <span className="user-card-name">{u.name || '-'}</span>
                                            </div>
                                            <span className={`plan-badge ${getPlanBadgeClass(u.plan_type)}`}>
                                                {u.plan_type || 'sin plan'}
                                            </span>
                                        </div>
                                        <div className="user-card-details">
                                            <div className="user-card-detail">
                                                <span className="detail-label">Estado</span>
                                                <span className={`status-badge ${getStatusBadgeClass(u.subscription_status)}`}>
                                                    {getStatusLabel(u.subscription_status)}
                                                </span>
                                            </div>
                                            <div className="user-card-detail">
                                                <span className="detail-label">Registro</span>
                                                <span>{formatDate(u.created_at)}</span>
                                            </div>
                                        </div>
                                        {!u.is_owner && (
                                            <div className="user-card-actions">
                                                {u.plan_type !== 'autonomo' ? (
                                                    <button
                                                        className="btn-plan btn-to-autonomo"
                                                        onClick={() => handleChangePlan(u.id, u.email, 'autonomo')}
                                                        disabled={changingPlan === u.id}
                                                    >
                                                        {changingPlan === u.id
                                                            ? <Loader size={14} className="animate-spin" />
                                                            : <ArrowUpDown size={14} />
                                                        }
                                                        Cambiar a Autónomo
                                                    </button>
                                                ) : (
                                                    <button
                                                        className="btn-plan btn-to-particular"
                                                        onClick={() => handleChangePlan(u.id, u.email, 'particular')}
                                                        disabled={changingPlan === u.id}
                                                    >
                                                        {changingPlan === u.id
                                                            ? <Loader size={14} className="animate-spin" />
                                                            : <ArrowUpDown size={14} />
                                                        }
                                                        Cambiar a Particular
                                                    </button>
                                                )}
                                                <button
                                                    className={`btn-plan ${u.subscription_status === 'active' ? 'btn-revoke-beta' : 'btn-grant-beta'}`}
                                                    onClick={() => handleToggleBeta(u.id, u.email, u.subscription_status === 'active')}
                                                    disabled={togglingBeta === u.id}
                                                >
                                                    {togglingBeta === u.id
                                                        ? <Loader size={14} className="animate-spin" />
                                                        : u.subscription_status === 'active'
                                                            ? <UserX size={14} />
                                                            : <UserCheck size={14} />
                                                    }
                                                    {u.subscription_status === 'active' ? 'Revocar beta' : 'Activar beta'}
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>

                            {/* Desktop: Table layout */}
                            <div className="users-table-wrapper">
                                <table className="users-table">
                                    <thead>
                                        <tr>
                                            <th>Email</th>
                                            <th>Nombre</th>
                                            <th>Plan</th>
                                            <th>Estado</th>
                                            <th>Registro</th>
                                            <th>Acciones</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {users.map(u => (
                                            <tr key={u.id}>
                                                <td className="cell-email">
                                                    {u.is_owner && <Crown size={14} className="owner-icon" />}
                                                    {u.email}
                                                </td>
                                                <td>{u.name || '-'}</td>
                                                <td>
                                                    <span className={`plan-badge ${getPlanBadgeClass(u.plan_type)}`}>
                                                        {u.plan_type || 'sin plan'}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className={`status-badge ${getStatusBadgeClass(u.subscription_status)}`}>
                                                        {getStatusLabel(u.subscription_status)}
                                                    </span>
                                                </td>
                                                <td className="cell-date">{formatDate(u.created_at)}</td>
                                                <td className="cell-actions">
                                                    {u.is_owner ? (
                                                        <span className="owner-label">Owner</span>
                                                    ) : (
                                                        <>
                                                            {u.plan_type !== 'autonomo' ? (
                                                                <button
                                                                    className="btn-plan btn-to-autonomo"
                                                                    onClick={() => handleChangePlan(u.id, u.email, 'autonomo')}
                                                                    disabled={changingPlan === u.id}
                                                                >
                                                                    {changingPlan === u.id
                                                                        ? <Loader size={14} className="animate-spin" />
                                                                        : <ArrowUpDown size={14} />
                                                                    }
                                                                    Autónomo
                                                                </button>
                                                            ) : (
                                                                <button
                                                                    className="btn-plan btn-to-particular"
                                                                    onClick={() => handleChangePlan(u.id, u.email, 'particular')}
                                                                    disabled={changingPlan === u.id}
                                                                >
                                                                    {changingPlan === u.id
                                                                        ? <Loader size={14} className="animate-spin" />
                                                                        : <ArrowUpDown size={14} />
                                                                    }
                                                                    Particular
                                                                </button>
                                                            )}
                                                            <button
                                                                className={`btn-plan ${u.subscription_status === 'active' ? 'btn-revoke-beta' : 'btn-grant-beta'}`}
                                                                onClick={() => handleToggleBeta(u.id, u.email, u.subscription_status === 'active')}
                                                                disabled={togglingBeta === u.id}
                                                            >
                                                                {togglingBeta === u.id
                                                                    ? <Loader size={14} className="animate-spin" />
                                                                    : u.subscription_status === 'active'
                                                                        ? <UserX size={14} />
                                                                        : <UserCheck size={14} />
                                                                }
                                                                {u.subscription_status === 'active' ? 'Revocar' : 'Beta'}
                                                            </button>
                                                        </>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>
            </main>
        </div>
    )
}
