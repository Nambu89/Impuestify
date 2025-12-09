import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { FileText } from 'lucide-react'
import './Header.css'

export default function Header() {
    const { isAuthenticated, user, logout } = useAuth()

    return (
        <header className="header">
            <div className="container">
                <div className="header-content">
                    <Link to="/" className="logo">
                        <FileText size={28} />
                        <span>TaxIA</span>
                    </Link>

                    <nav className="nav">
                        {isAuthenticated ? (
                            <>
                                <Link to="/chat" className="nav-link">Chat</Link>
                                {user?.is_admin && (
                                    <Link to="/dashboard" className="nav-link">Dashboard</Link>
                                )}
                                <div className="user-menu">
                                    <span className="user-name">{user?.name || user?.email}</span>
                                    <button onClick={logout} className="btn btn-ghost">
                                        Cerrar Sesión
                                    </button>
                                </div>
                            </>
                        ) : (
                            <>
                                <Link to="/login" className="nav-link">Iniciar Sesión</Link>
                                <Link to="/register" className="btn btn-primary">
                                    Registrarse
                                </Link>
                            </>
                        )}
                    </nav>
                </div>
            </div>
        </header>
    )
}
