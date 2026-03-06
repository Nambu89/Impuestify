import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, Mail, Loader2 } from 'lucide-react'
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
            <div className="auth-container">
                <div className="auth-card">
                    <div className="auth-header">
                        <Link to="/" className="auth-logo">
                            <FileText size={32} />
                            <span>Impuestify</span>
                        </Link>
                        <h1>Restablecer contraseña</h1>
                        <p>Introduce tu email para recibir el enlace</p>
                    </div>

                    {success ? (
                        <div className="auth-form">
                            <div className="auth-success">
                                Si el email está registrado, recibirás un enlace para restablecer tu contraseña.
                            </div>
                        </div>
                    ) : (
                        <form onSubmit={handleSubmit} className="auth-form">
                            {error && (
                                <div className="auth-error">
                                    {error}
                                </div>
                            )}

                            <div className="form-group">
                                <label className="label" htmlFor="email">Email</label>
                                <div className="input-with-icon">
                                    <Mail size={20} />
                                    <input
                                        type="email"
                                        id="email"
                                        className="input"
                                        placeholder="tu@email.com"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>

                            <button
                                type="submit"
                                className="btn btn-primary btn-lg auth-submit"
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <>
                                        <Loader2 size={20} className="animate-spin" />
                                        Enviando...
                                    </>
                                ) : (
                                    'Enviar enlace'
                                )}
                            </button>
                        </form>
                    )}

                    <div className="auth-footer">
                        <p>
                            <Link to="/login">Volver al login</Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
