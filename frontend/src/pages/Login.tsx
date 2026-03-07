import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, Mail, Lock, Eye, EyeOff, Loader2, Calculator, Map, Shield, AlertCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import './Auth.css'

export default function Login() {
    const navigate = useNavigate()
    const { login } = useAuth()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)

        try {
            await login(email, password)
            navigate('/chat')
        } catch (err: any) {
            const status = err?.response?.status
            if (status === 401) {
                setError('Email o contraseña incorrectos. Inténtalo de nuevo.')
            } else if (status === 429) {
                setError('Demasiados intentos. Espera un momento antes de volver a intentarlo.')
            } else {
                setError('Error al iniciar sesión. Inténtalo de nuevo más tarde.')
            }
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="auth-page">
            {/* Brand panel */}
            <div className="auth-brand">
                <Link to="/" className="auth-brand__logo">
                    <FileText size={22} />
                    <span>Impuestify</span>
                </Link>

                <h1 className="auth-brand__title">Tu asesor fiscal con IA</h1>

                <p className="auth-brand__subtitle">
                    El unico asistente que cubre los 21 territorios de Espana con IA y fuentes oficiales.
                </p>

                <div className="auth-brand__pills">
                    <span className="auth-brand__pill">
                        <FileText size={13} />
                        428+ documentos oficiales
                    </span>
                    <span className="auth-brand__pill">
                        <Calculator size={13} />
                        128 deducciones fiscales
                    </span>
                    <span className="auth-brand__pill">
                        <Map size={13} />
                        IRPF foral completo
                    </span>
                </div>

                <div className="auth-brand__badges">
                    <span className="auth-brand__badge">RGPD</span>
                    <span className="auth-brand__badge">AI Act</span>
                    <span className="auth-brand__badge">LSSI-CE</span>
                    <span className="auth-brand__badge">LOPDGDD</span>
                </div>
            </div>

            {/* Form panel */}
            <div className="auth-form-panel">
                <div className="auth-card">
                    <h2>Bienvenido de nuevo</h2>
                    <p className="auth-card__subtitle">Inicia sesion para continuar</p>

                    <form onSubmit={handleSubmit} className="auth-form">
                        {error && (
                            <div className="auth-message auth-message--error">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}

                        <div className="auth-input-group">
                            <label htmlFor="email">Email</label>
                            <div className="auth-input-wrapper">
                                <span className="auth-input-icon">
                                    <Mail size={18} />
                                </span>
                                <input
                                    type="email"
                                    id="email"
                                    className="auth-input"
                                    placeholder="tu@email.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    autoComplete="email"
                                />
                            </div>
                        </div>

                        <div className="auth-input-group">
                            <label htmlFor="password">Contrasena</label>
                            <div className="auth-input-wrapper">
                                <span className="auth-input-icon">
                                    <Lock size={18} />
                                </span>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    id="password"
                                    className="auth-input auth-input--with-toggle"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    autoComplete="current-password"
                                />
                                <button
                                    type="button"
                                    className="auth-input-toggle"
                                    onClick={() => setShowPassword((v) => !v)}
                                    aria-label={showPassword ? 'Ocultar contrasena' : 'Mostrar contrasena'}
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <Link to="/forgot-password" className="auth-forgot-link">
                            ¿Olvidaste tu contrasena?
                        </Link>

                        <button
                            type="submit"
                            className="auth-submit-btn"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 size={18} className="animate-spin" />
                                    Iniciando sesion...
                                </>
                            ) : (
                                <>
                                    <Shield size={18} />
                                    Iniciar Sesion
                                </>
                            )}
                        </button>
                    </form>

                    <p className="auth-switch-link">
                        ¿No tienes cuenta?{' '}
                        <Link to="/register">Registrarse gratis</Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
