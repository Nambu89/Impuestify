import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Mail, Loader2, Calculator, Map, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import './Auth.css'

export default function ForgotPassword() {
    const { apiRequest } = useApi()

    const [email, setEmail] = useState('')
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)
    const [isLoading, setIsLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)

        try {
            await apiRequest('/auth/forgot-password', {
                method: 'POST',
                body: JSON.stringify({ email })
            })
            setSuccess(true)
        } catch {
            // Siempre mostramos el mismo mensaje para no revelar si el email existe
            setSuccess(true)
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
                    El único asistente que cubre los 21 territorios de España con IA y fuentes oficiales.
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
                    <h2>Restablecer contraseña</h2>
                    <p className="auth-card__subtitle">Introduce tu email para recibir el enlace</p>

                    {success ? (
                        <div className="auth-form">
                            <div className="auth-message auth-message--success">
                                <CheckCircle size={16} />
                                Si el email está registrado, recibirás un enlace para restablecer tu contraseña.
                            </div>
                        </div>
                    ) : (
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

                            <button
                                type="submit"
                                className="auth-submit-btn"
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 size={18} className="animate-spin" />
                                        Enviando...
                                    </>
                                ) : (
                                    'Enviar enlace'
                                )}
                            </button>
                        </form>
                    )}

                    <p className="auth-switch-link">
                        <Link to="/login">
                            <ArrowLeft size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                            Volver al login
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
