import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, Mail, Lock, User, Eye, EyeOff, Loader2, Calculator, Map, AlertCircle, CheckCircle, MapPin } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import './Auth.css'

const CCAA_OPTIONS = [
    { value: '', label: 'Selecciona tu comunidad' },
    { value: 'Andalucia', label: 'Andalucía' },
    { value: 'Aragon', label: 'Aragón' },
    { value: 'Asturias', label: 'Asturias' },
    { value: 'Baleares', label: 'Illes Balears' },
    { value: 'Canarias', label: 'Canarias' },
    { value: 'Cantabria', label: 'Cantabria' },
    { value: 'Castilla y Leon', label: 'Castilla y León' },
    { value: 'Castilla-La Mancha', label: 'Castilla-La Mancha' },
    { value: 'Cataluna', label: 'Cataluña' },
    { value: 'Ceuta', label: 'Ceuta' },
    { value: 'Valencia', label: 'Comunitat Valenciana' },
    { value: 'Extremadura', label: 'Extremadura' },
    { value: 'Galicia', label: 'Galicia' },
    { value: 'Gipuzkoa', label: 'Gipuzkoa' },
    { value: 'La Rioja', label: 'La Rioja' },
    { value: 'Madrid', label: 'Comunidad de Madrid' },
    { value: 'Melilla', label: 'Melilla' },
    { value: 'Murcia', label: 'Murcia' },
    { value: 'Navarra', label: 'Navarra' },
    { value: 'Araba', label: 'Araba/Álava' },
    { value: 'Bizkaia', label: 'Bizkaia' },
]

const FORAL_CCAA = ['Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra']
const FORAL_NAMES: Record<string, string> = {
    'Araba': 'Araba/Álava',
    'Bizkaia': 'Bizkaia',
    'Gipuzkoa': 'Gipuzkoa',
    'Navarra': 'Navarra',
}

export default function Register() {
    const navigate = useNavigate()
    const { register } = useAuth()

    const [name, setName] = useState('')
    const [ccaa, setCcaa] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [showConfirmPassword, setShowConfirmPassword] = useState(false)
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    const isForal = FORAL_CCAA.includes(ccaa)
    const isCeutaMelilla = ccaa === 'Ceuta' || ccaa === 'Melilla'
    const isCanarias = ccaa === 'Canarias'

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (!ccaa) {
            setError('Por favor, selecciona tu Comunidad Autónoma')
            return
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRegex.test(email)) {
            setError('Por favor, introduce un email valido')
            return
        }

        if (password !== confirmPassword) {
            setError('Las contrasenas no coinciden')
            return
        }

        if (password.length < 8) {
            setError('La contrasena debe tener al menos 8 caracteres')
            return
        }

        setIsLoading(true)

        try {
            await register(email, password, name, ccaa)
            navigate('/chat')
        } catch (err: any) {
            setError(err.message || 'Error al crear la cuenta')
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
                    <h2>Crear cuenta</h2>
                    <p className="auth-card__subtitle">Crea tu cuenta en Impuestify</p>

                    <form onSubmit={handleSubmit} className="auth-form">
                        {error && (
                            <div className="auth-message auth-message--error">
                                <AlertCircle size={16} />
                                {error}
                            </div>
                        )}

                        <div className="auth-input-group">
                            <label htmlFor="name">Nombre (opcional)</label>
                            <div className="auth-input-wrapper">
                                <span className="auth-input-icon">
                                    <User size={18} />
                                </span>
                                <input
                                    type="text"
                                    id="name"
                                    className="auth-input"
                                    placeholder="Tu nombre"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    autoComplete="name"
                                />
                            </div>
                        </div>

                        <div className="auth-input-group">
                            <label htmlFor="ccaa">Comunidad Autónoma de residencia <span className="auth-required">*</span></label>
                            <div className="auth-input-wrapper">
                                <span className="auth-input-icon">
                                    <MapPin size={18} />
                                </span>
                                <select
                                    id="ccaa"
                                    className="auth-input auth-select"
                                    value={ccaa}
                                    onChange={(e) => setCcaa(e.target.value)}
                                    required
                                >
                                    {CCAA_OPTIONS.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>
                            {isForal && (
                                <p className="auth-ccaa-hint auth-ccaa-hint--foral">
                                    Tu IRPF se calcula con la normativa foral de {FORAL_NAMES[ccaa]}
                                </p>
                            )}
                            {isCeutaMelilla && (
                                <p className="auth-ccaa-hint auth-ccaa-hint--ceuta">
                                    Aplica deducción del 60% en IRPF + IPSI en lugar de IVA
                                </p>
                            )}
                            {isCanarias && (
                                <p className="auth-ccaa-hint auth-ccaa-hint--canarias">
                                    Aplica IGIC en lugar de IVA
                                </p>
                            )}
                        </div>

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
                                    placeholder="Minimo 8 caracteres"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                    minLength={8}
                                    autoComplete="new-password"
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

                        <div className="auth-input-group">
                            <label htmlFor="confirmPassword">Confirmar contrasena</label>
                            <div className="auth-input-wrapper">
                                <span className="auth-input-icon">
                                    <Lock size={18} />
                                </span>
                                <input
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    id="confirmPassword"
                                    className="auth-input auth-input--with-toggle"
                                    placeholder="Repite la contrasena"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                    autoComplete="new-password"
                                />
                                <button
                                    type="button"
                                    className="auth-input-toggle"
                                    onClick={() => setShowConfirmPassword((v) => !v)}
                                    aria-label={showConfirmPassword ? 'Ocultar contrasena' : 'Mostrar contrasena'}
                                >
                                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
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
                                    Creando cuenta...
                                </>
                            ) : (
                                <>
                                    <CheckCircle size={18} />
                                    Crear cuenta
                                </>
                            )}
                        </button>
                    </form>

                    <p className="auth-switch-link">
                        ¿Ya tienes cuenta?{' '}
                        <Link to="/login">Iniciar Sesión</Link>
                    </p>

                    <p className="auth-legal">
                        Al registrarte aceptas los{' '}
                        <Link to="/terminos">Términos de Servicio</Link>
                        {' '}y la{' '}
                        <Link to="/privacidad">Política de Privacidad</Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
