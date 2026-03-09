import { useState } from 'react'
import { FileText, LogOut, Menu, MessageSquare, Settings, Shield, Calculator, History, ClipboardList, CalendarDays } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useSubscription } from '../hooks/useSubscription'
import './Header.css'

interface HeaderProps {
    onMenuToggle?: () => void
}

export default function Header({ onMenuToggle }: HeaderProps) {
    const { user, logout } = useAuth()
    const { isOwner } = useSubscription()
    const navigate = useNavigate()
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

    const handleLogout = () => {
        logout()
        navigate('/login')
    }

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
        <>
        <header className="header">
            <div className="header-content">
                <button
                    className="menu-toggle"
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    aria-label="Toggle menu"
                >
                    <Menu size={24} />
                </button>

                <Link to="/chat" className="logo">
                    <FileText size={28} />
                    <span>Impuestify</span>
                </Link>

                <nav className="nav">
                    <Link to="/chat" className="nav-link">Chat</Link>
                    <Link to="/guia-fiscal" className="nav-link">
                        <Calculator size={16} /> Guia Fiscal
                    </Link>
                    <Link to="/modelos-trimestrales" className="nav-link">
                        <ClipboardList size={16} /> Modelos
                    </Link>
                    <Link to="/calendario" className="nav-link">
                        <CalendarDays size={16} /> Calendario
                    </Link>
                    <Link to="/settings" className="nav-link">
                        <Settings size={16} /> Configuración
                    </Link>
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
                        title="Cerrar sesion"
                    >
                        <LogOut size={18} />
                    </button>
                </div>
            </div>
        </header>

        {mobileMenuOpen && (
            <div className="mobile-nav-overlay" onClick={() => setMobileMenuOpen(false)}>
                <nav className="mobile-nav" onClick={e => e.stopPropagation()}>
                    <Link to="/chat" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <MessageSquare size={20} /> Chat
                    </Link>
                    <Link to="/guia-fiscal" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Calculator size={20} /> Guia Fiscal
                    </Link>
                    <Link to="/modelos-trimestrales" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <ClipboardList size={20} /> Modelos Trimestrales
                    </Link>
                    <Link to="/calendario" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <CalendarDays size={20} /> Calendario Fiscal
                    </Link>
                    <Link to="/settings" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Settings size={20} /> Configuración
                    </Link>
                    {isOwner && (
                        <Link to="/admin/users" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                            <Shield size={20} /> Admin
                        </Link>
                    )}
                    {onMenuToggle && (
                        <button
                            className="mobile-nav__link mobile-nav__link--btn"
                            onClick={() => { setMobileMenuOpen(false); onMenuToggle() }}
                        >
                            <History size={20} /> Historial de conversaciones
                        </button>
                    )}
                </nav>
            </div>
        )}
        </>
    )
}