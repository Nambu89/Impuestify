import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FileText, Lock, Loader2 } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import './Auth.css'

export default function ResetPassword() {
    const { apiRequest } = useApi()
    const [searchParams] = useSearchParams()
    const token = searchParams.get('token') || ''

    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [error, setError] = useState('')
    const [success, setSuccess] = useState(false)
    const [isLoading, setIsLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (newPassword.length < 8) {
            setError('La contraseña debe tener al menos 8 caracteres')
            return
        }

        if (newPassword !== confirmPassword) {
            setError('Las contraseñas no coinciden')
            return
        }

        if (!token) {
            setError('El enlace de restablecimiento no es válido o ha expirado')
            return
        }

        setIsLoading(true)

        try {
            await apiRequest('/auth/reset-password', {
                method: 'POST',
                body: JSON.stringify({ token, new_password: newPassword })
            })
            setSuccess(true)
        } catch (err: any) {
            setError(err.message || 'El enlace no es válido o ha expirado. Solicita uno nuevo.')
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
                        <h1>Nueva contraseña</h1>
                        <p>Introduce tu nueva contraseña</p>
                    </div>

                    {success ? (
                        <div className="auth-form">
                            <div className="auth-success">
                                Contraseña actualizada correctamente.
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
                                <label className="label" htmlFor="newPassword">Nueva contraseña</label>
                                <div className="input-with-icon">
                                    <Lock size={20} />
                                    <input
                                        type="password"
                                        id="newPassword"
                                        className="input"
                                        placeholder="Mínimo 8 caracteres"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        required
                                        minLength={8}
                                    />
                                </div>
                            </div>

                            <div className="form-group">
                                <label className="label" htmlFor="confirmPassword">Confirmar contraseña</label>
                                <div className="input-with-icon">
                                    <Lock size={20} />
                                    <input
                                        type="password"
                                        id="confirmPassword"
                                        className="input"
                                        placeholder="Repite la contraseña"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
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
                                        Guardando...
                                    </>
                                ) : (
                                    'Guardar contraseña'
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
