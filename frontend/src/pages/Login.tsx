import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, Mail, Lock, Loader2 } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import './Auth.css'

export default function Login() {
    const navigate = useNavigate()
    const { login } = useAuth()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
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
            <div className="auth-container">
                <div className="auth-card">
                    <div className="auth-header">
                        <Link to="/" className="auth-logo">
                            <FileText size={32} />
                            <span>Impuestify</span>
                        </Link>
                        <h1>Bienvenido de nuevo</h1>
                        <p>Inicia sesión para continuar</p>
                    </div>

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

                        <div className="form-group">
                            <label className="label" htmlFor="password">Contraseña</label>
                            <div className="input-with-icon">
                                <Lock size={20} />
                                <input
                                    type="password"
                                    id="password"
                                    className="input"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
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
                                    Iniciando sesión...
                                </>
                            ) : (
                                'Iniciar Sesión'
                            )}
                        </button>
                    </form>

                    <div className="auth-footer">
                        <p>
                            ¿No tienes cuenta?{' '}
                            <Link to="/register">Registrarse</Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
