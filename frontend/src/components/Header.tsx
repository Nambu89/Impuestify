import { useState } from 'react'
import { LogOut, Menu, MessageSquare, Settings, Shield, Calculator, History, ClipboardList, CalendarDays, Bitcoin, Wallet, Receipt, Building2, FileText } from 'lucide-react'
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
                    <img
                        src="/images/logo-header.webp"
                        alt="Impuestify"
                        className="logo-img"
                        width="241"
                        height="80"
                    />
                </Link>

                <nav className="nav">
                    <Link to="/chat" className="nav-link">Chat</Link>
                    <Link to="/guia-fiscal" className="nav-link">
                        <Calculator size={16} /> Guia Fiscal
                    </Link>
                    <Link to="/calculadora-neto" className="nav-link">
                        <Wallet size={16} /> Calculadora Neto
                    </Link>
                    <Link to="/calculadora-retenciones" className="nav-link">
                        <Calculator size={16} /> Retenciones
                    </Link>
                    <Link to="/calculadora-iva-creadores" className="nav-link">
                        <Receipt size={16} /> IVA Creadores
                    </Link>
                    <Link to="/calculadora-umbrales" className="nav-link">
                        <Building2 size={16} /> Umbrales
                    </Link>
                    <Link to="/modelos-obligatorios" className="nav-link">
                        <FileText size={16} /> Obligaciones
                    </Link>
                    <Link to="/modelos-trimestrales" className="nav-link">
                        <ClipboardList size={16} /> Modelos
                    </Link>
                    <Link to="/crypto" className="nav-link">
                        <Bitcoin size={16} /> Crypto
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
                        <div className="nav-dropdown">
                            <button className="nav-link nav-dropdown__trigger">
                                <Shield size={16} /> Admin
                            </button>
                            <div className="nav-dropdown__menu">
                                <Link to="/admin" className="nav-dropdown__item">Dashboard</Link>
                                <Link to="/admin/users" className="nav-dropdown__item">Usuarios</Link>
                                <Link to="/admin/feedback" className="nav-dropdown__item">Feedback</Link>
                                <Link to="/admin/contact" className="nav-dropdown__item">Contacto</Link>
                                <Link to="/admin/rag-quality" className="nav-dropdown__item">Calidad RAG</Link>
                            </div>
                        </div>
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

        {mobileMenuOpen && (
            <div className="mobile-nav-overlay" onClick={() => setMobileMenuOpen(false)}>
                <nav className="mobile-nav" onClick={e => e.stopPropagation()}>
                    <Link to="/chat" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <MessageSquare size={20} /> Chat
                    </Link>
                    <Link to="/guia-fiscal" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Calculator size={20} /> Guia Fiscal
                    </Link>
                    <Link to="/calculadora-neto" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Wallet size={20} /> Calculadora Neto
                    </Link>
                    <Link to="/calculadora-retenciones" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Calculator size={20} /> Retenciones IRPF
                    </Link>
                    <Link to="/calculadora-iva-creadores" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Receipt size={20} /> IVA Creadores
                    </Link>
                    <Link to="/calculadora-umbrales" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Building2 size={20} /> Umbrales Contables
                    </Link>
                    <Link to="/modelos-obligatorios" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <FileText size={20} /> Obligaciones Fiscales
                    </Link>
                    <Link to="/modelos-trimestrales" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <ClipboardList size={20} /> Modelos Trimestrales
                    </Link>
                    <Link to="/crypto" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Bitcoin size={20} /> Criptomonedas
                    </Link>
                    <Link to="/calendario" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <CalendarDays size={20} /> Calendario Fiscal
                    </Link>
                    <Link to="/settings" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Settings size={20} /> Configuración
                    </Link>
                    {isOwner && (
                        <>
                            <Link to="/admin" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                                <Shield size={20} /> Dashboard Admin
                            </Link>
                            <Link to="/admin/users" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                                <Shield size={20} /> Usuarios
                            </Link>
                            <Link to="/admin/feedback" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                                <Shield size={20} /> Feedback
                            </Link>
                            <Link to="/admin/contact" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                                <Shield size={20} /> Contacto
                            </Link>
                            <Link to="/admin/rag-quality" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                                <Shield size={20} /> Calidad RAG
                            </Link>
                        </>
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