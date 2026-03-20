import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, Mail, Lock, Eye, EyeOff, Loader2, Calculator, Map, Shield, AlertCircle, KeyRound } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import TurnstileWidget from '../components/TurnstileWidget'
import './Auth.css'

export default function Login() {
    const navigate = useNavigate()
    const { login, completeMfaLogin } = useAuth()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [turnstileToken, setTurnstileToken] = useState('')

    // MFA state
    const [mfaStep, setMfaStep] = useState(false)
    const [mfaToken, setMfaToken] = useState('')
    const [mfaCode, setMfaCode] = useState('')
    const [useBackupCode, setUseBackupCode] = useState(false)
    const mfaInputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        if (mfaStep && mfaInputRef.current) {
            mfaInputRef.current.focus()
        }
    }, [mfaStep])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (!turnstileToken) {
            setError('Por favor, completa la verificación de seguridad.')
            return
        }

        setIsLoading(true)

        try {
            await login(email, password, turnstileToken)
            navigate('/chat')
        } catch (err: any) {
            if (err.message === 'MFA_REQUIRED' && err.mfa_token) {
                setMfaStep(true)
                setMfaToken(err.mfa_token)
                setIsLoading(false)
                return
            }
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

    const handleMfaSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)

        try {
            await completeMfaLogin(mfaToken, mfaCode)
            navigate('/chat')
        } catch (err: any) {
            const status = err?.response?.status
            if (status === 401) {
                setError('Código incorrecto. Inténtalo de nuevo.')
            } else if (status === 429) {
                setError('Demasiados intentos. Espera un momento.')
            } else {
                setError('Error de verificación. Inténtalo de nuevo.')
            }
            setMfaCode('')
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
                {mfaStep ? (
                <div className="auth-card">
                    <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                        <KeyRound size={40} style={{ color: 'var(--color-primary)', marginBottom: '0.75rem' }} />
                        <h2>Verificación en dos pasos</h2>
                        <p className="auth-card__subtitle">
                            {useBackupCode
                                ? 'Introduce uno de tus códigos de respaldo'
                                : 'Introduce el código de 6 dígitos de tu app de autenticación'}
                        </p>
                    </div>

                    <form onSubmit={handleMfaSubmit} className="auth-form">
                        {error && (
                            <div className="auth-message auth-message--error">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}

                        <div className="auth-input-group">
                            <label htmlFor="mfa-code">{useBackupCode ? 'Código de respaldo' : 'Código TOTP'}</label>
                            <div className="auth-input-wrapper">
                                <span className="auth-input-icon">
                                    <KeyRound size={18} />
                                </span>
                                <input
                                    ref={mfaInputRef}
                                    type={useBackupCode ? 'text' : 'text'}
                                    id="mfa-code"
                                    className="auth-input"
                                    placeholder={useBackupCode ? 'abc12345' : '000000'}
                                    value={mfaCode}
                                    onChange={(e) => {
                                        const val = useBackupCode ? e.target.value : e.target.value.replace(/\D/g, '').slice(0, 6)
                                        setMfaCode(val)
                                    }}
                                    required
                                    autoComplete="one-time-code"
                                    inputMode={useBackupCode ? 'text' : 'numeric'}
                                    style={{ letterSpacing: useBackupCode ? 'normal' : '0.5em', fontFamily: 'monospace', fontSize: '1.25rem', textAlign: 'center' }}
                                />
                            </div>
                        </div>

                        <button type="submit" className="auth-submit-btn" disabled={isLoading || (!useBackupCode && mfaCode.length < 6)}>
                            {isLoading ? (
                                <><Loader2 size={18} className="animate-spin" /> Verificando...</>
                            ) : (
                                <><Shield size={18} /> Verificar</>
                            )}
                        </button>

                        <button
                            type="button"
                            className="auth-forgot-link"
                            style={{ display: 'block', textAlign: 'center', marginTop: '0.5rem', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-primary)' }}
                            onClick={() => { setUseBackupCode(!useBackupCode); setMfaCode('') }}
                        >
                            {useBackupCode ? 'Usar código de la app' : '¿No tienes la app? Usar código de respaldo'}
                        </button>
                    </form>
                </div>
                ) : (
                <div className="auth-card">
                    <h2>Bienvenido de nuevo</h2>
                    <p className="auth-card__subtitle">Inicia sesión para continuar</p>

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
                            <label htmlFor="password">Contraseña</label>
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
                                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <Link to="/forgot-password" className="auth-forgot-link">
                            ¿Olvidaste tu contraseña?
                        </Link>

                        <TurnstileWidget
                            onVerify={(token) => setTurnstileToken(token)}
                            onExpire={() => setTurnstileToken('')}
                            onError={() => setTurnstileToken('')}
                        />

                        <button
                            type="submit"
                            className="auth-submit-btn"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 size={18} className="animate-spin" />
                                    Iniciando sesión...
                                </>
                            ) : (
                                <>
                                    <Shield size={18} />
                                    Iniciar Sesión
                                </>
                            )}
                        </button>
                    </form>

                    <p className="auth-switch-link">
                        ¿No tienes cuenta?{' '}
                        <Link to="/register">Crear cuenta</Link>
                    </p>
                </div>
                )}
            </div>
        </div>
    )
}
