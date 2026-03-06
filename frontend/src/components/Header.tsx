import { FileText, LogOut, Menu, Settings, Shield, Calculator } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useSubscription } from '../hooks/useSubscription'
import './Header.css'

interface HeaderProps {
    onMenuToggle?: () => void // ✅ NUEVO: Prop opcional para toggle
}

export default function Header({ onMenuToggle }: HeaderProps) {
    const { user, logout } = useAuth()
    const { isOwner } = useSubscription()
    const navigate = useNavigate()

    const handleLogout = () => {
        // ✅ ADD: Confirmation dialog before logout (beta tester feedback)
        const confirmed = window.confirm(
            '¿Estás seguro de que deseas cerrar sesión? '
            + 'Tu historial de conversaciones se conservará para la próxima vez.'
        )

        if (confirmed) {
            logout()
            navigate('/login')
        }
    }

    // Obtener iniciales del nombre del usuario
    const getInitials = (name?: string) => {
        if (!name) return user?.email?.charAt(0).toUpperCase() || 'U'
        return name
            .split(' ')
            .map(n => n.charAt(0))
            .join('')
            .toUpperCase()
            .slice(0, 2)
    }

    return (
        <header className="header">
            <div className="header-content">
                {/* ✅ NUEVO: Botón hamburguesa para móvil */}
                {onMenuToggle && (
                    <button
                        className="menu-toggle"
                        onClick={onMenuToggle}
                        aria-label="Toggle menu"
                    >
                        <Menu size={24} />
                    </button>
                )}

                <Link to="/chat" className="logo">
                    <FileText size={28} />
                    <span>Impuestify</span>
                </Link>

                <nav className="nav">
                    <Link to="/chat" className="nav-link">Chat</Link>
                    <Link to="/guia-fiscal" className="nav-link">
                        <Calculator size={16} /> Guia Fiscal
                    </Link>
                    <Link to="/settings" className="nav-link">
                        <Settings size={16} /> Configuración
                    </Link>
                    {/* ✅ FIX: Solo mostrar Dashboard si is_admin === 1 */}
                    {user?.is_admin === 1 && (
                        <Link to="/dashboard" className="nav-link">Dashboard</Link>
                    )}
                    {isOwner && (
                        <Link to="/admin/users" className="nav-link">
                            <Shield size={16} /> Admin
                        </Link>
                    )}
                </nav>

                <div className="user-menu">
                    {user?.name && <span className="user-name">{user.name}</span>}
                    <div className="user-avatar">
                        {getInitials(user?.name)}
                    </div>
                    <button
                        className="logout-btn"
                        onClick={handleLogout}
                        title="Cerrar sesión"
                    >
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </header>
    )
}