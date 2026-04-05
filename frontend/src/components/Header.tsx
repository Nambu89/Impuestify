import { useState, useRef, useEffect } from 'react'
import { LogOut, Menu, MessageSquare, Settings, Shield, Calculator, History, ClipboardList, CalendarDays, Bitcoin, Wallet, Receipt, Building2, FileText, BookOpen, ChevronDown } from 'lucide-react'
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
    const [toolsOpen, setToolsOpen] = useState(false)
    const [mobileToolsOpen, setMobileToolsOpen] = useState(false)
    const toolsRef = useRef<HTMLDivElement>(null)

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

    // Close tools dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (toolsRef.current && !toolsRef.current.contains(e.target as Node)) {
                setToolsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

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
                    <Link to="/chat" className="nav-link">
                        <MessageSquare size={16} /> Chat
                    </Link>

                    {/* Herramientas dropdown */}
                    <div
                        className={`nav-dropdown${toolsOpen ? ' nav-dropdown--open' : ''}`}
                        ref={toolsRef}
                        onMouseEnter={() => setToolsOpen(true)}
                        onMouseLeave={() => setToolsOpen(false)}
                    >
                        <button
                            className="nav-link nav-dropdown__trigger"
                            onClick={() => setToolsOpen(!toolsOpen)}
                            aria-expanded={toolsOpen}
                            aria-haspopup="true"
                        >
                            <Calculator size={16} /> Herramientas <ChevronDown size={14} className={`nav-chevron${toolsOpen ? ' nav-chevron--up' : ''}`} />
                        </button>
                        <div className="nav-dropdown__menu nav-dropdown__menu--tools" role="menu">
                            <Link to="/guia-fiscal" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <Calculator size={15} /> Guía Fiscal
                            </Link>
                            <Link to="/calculadora-neto" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <Wallet size={15} /> Calculadora Neto
                            </Link>
                            <Link to="/calculadora-retenciones" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <Calculator size={15} /> Retenciones IRPF
                            </Link>
                            <Link to="/calculadora-iva-creadores" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <Receipt size={15} /> IVA Creadores
                            </Link>
                            <Link to="/calculadora-umbrales" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <Building2 size={15} /> Umbrales Contables
                            </Link>
                            <Link to="/modelos-obligatorios" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <FileText size={15} /> Obligaciones Fiscales
                            </Link>
                            <Link to="/modelos-trimestrales" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <ClipboardList size={15} /> Modelos Trimestrales
                            </Link>
                            <Link to="/clasificador-facturas" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <FileText size={15} /> Clasificador Facturas
                            </Link>
                            <Link to="/contabilidad" className="nav-dropdown__item" onClick={() => setToolsOpen(false)}>
                                <BookOpen size={15} /> Contabilidad
                            </Link>
                        </div>
                    </div>

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
                                <Shield size={16} /> Admin <ChevronDown size={14} />
                            </button>
                            <div className="nav-dropdown__menu" role="menu">
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
                    <Link to="/crypto" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Bitcoin size={20} /> Criptomonedas
                    </Link>
                    <Link to="/calendario" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <CalendarDays size={20} /> Calendario Fiscal
                    </Link>
                    <Link to="/settings" className="mobile-nav__link" onClick={() => setMobileMenuOpen(false)}>
                        <Settings size={20} /> Configuración
                    </Link>

                    {/* Herramientas group */}
                    <button
                        className="mobile-nav__group-toggle"
                        onClick={() => setMobileToolsOpen(!mobileToolsOpen)}
                        aria-expanded={mobileToolsOpen}
                    >
                        <span className="mobile-nav__group-label"><Calculator size={20} /> Herramientas</span>
                        <ChevronDown size={18} className={mobileToolsOpen ? 'mobile-nav__chevron--up' : ''} />
                    </button>
                    {mobileToolsOpen && (
                        <div className="mobile-nav__group">
                            <Link to="/guia-fiscal" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <Calculator size={18} /> Guía Fiscal
                            </Link>
                            <Link to="/calculadora-neto" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <Wallet size={18} /> Calculadora Neto
                            </Link>
                            <Link to="/calculadora-retenciones" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <Calculator size={18} /> Retenciones IRPF
                            </Link>
                            <Link to="/calculadora-iva-creadores" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <Receipt size={18} /> IVA Creadores
                            </Link>
                            <Link to="/calculadora-umbrales" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <Building2 size={18} /> Umbrales Contables
                            </Link>
                            <Link to="/modelos-obligatorios" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <FileText size={18} /> Obligaciones Fiscales
                            </Link>
                            <Link to="/modelos-trimestrales" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <ClipboardList size={18} /> Modelos Trimestrales
                            </Link>
                            <Link to="/clasificador-facturas" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <FileText size={18} /> Clasificador Facturas
                            </Link>
                            <Link to="/contabilidad" className="mobile-nav__link mobile-nav__link--sub" onClick={() => setMobileMenuOpen(false)}>
                                <BookOpen size={18} /> Contabilidad
                            </Link>
                        </div>
                    )}

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