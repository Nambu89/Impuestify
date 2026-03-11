import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    User, Download, Trash2, Save, AlertCircle, CheckCircle,
    Loader, Shield, Lock, Calculator, ChevronDown, ChevronRight, RefreshCw,
    CreditCard, ExternalLink, Bell, BellOff, Mail
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useApi } from '../hooks/useApi'
import { useSubscription } from '../hooks/useSubscription'
import { useFiscalProfile, FiscalProfile } from '../hooks/useFiscalProfile'
import { usePushNotifications } from '../hooks/usePushNotifications'
import Header from '../components/Header'
import DynamicFiscalForm from '../components/DynamicFiscalForm'
import './SettingsPage.css'

type TabKey = 'personal' | 'security' | 'fiscal' | 'subscription' | 'privacy' | 'notifications'

const CCAA_OPTIONS = [
    '', 'Andalucia', 'Aragon', 'Asturias', 'Baleares', 'Canarias',
    'Cantabria', 'Castilla y Leon', 'Castilla-La Mancha', 'Cataluna',
    'Valencia', 'Extremadura', 'Galicia', 'Madrid',
    'Murcia', 'Navarra', 'Araba', 'Bizkaia', 'Gipuzkoa', 'La Rioja', 'Ceuta', 'Melilla'
]

const CCAA_DISPLAY: Record<string, string> = {
    'Andalucia': 'Andalucía',
    'Aragon': 'Aragón',
    'Cataluna': 'Cataluña',
    'Castilla y Leon': 'Castilla y León',
    'Araba': 'Araba/Álava',
}

const SITUACION_OPTIONS = [
    { value: '', label: 'Selecciona...' },
    { value: 'asalariado', label: 'Asalariado/a' },
    { value: 'autonomo', label: 'Autónomo/a' },
    { value: 'pensionista', label: 'Pensionista' },
    { value: 'desempleado', label: 'Desempleado/a' },
]

export default function SettingsPage() {
    const { user, logout } = useAuth()
    const { apiRequest } = useApi()
    const subscription = useSubscription()
    const navigate = useNavigate()
    const push = usePushNotifications()

    // Alert days preference state (notifications tab)
    const [alertDays, setAlertDays] = useState<number[]>([15, 5, 1])

    // Email alerts state
    const [emailAlertsEnabled, setEmailAlertsEnabled] = useState(false)
    const [emailAlertsLoading, setEmailAlertsLoading] = useState(false)

    // Active tab
    const [activeTab, setActiveTab] = useState<TabKey>('personal')

    // Form state — Personal
    const [name, setName] = useState('')
    const [email, setEmail] = useState('')

    // Form state — Security
    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')

    // Fiscal profile hook
    const fiscal = useFiscalProfile()
    const [fiscalForm, setFiscalForm] = useState<Partial<FiscalProfile>>({})
    const [childYears, setChildYears] = useState<string[]>([])

    // Collapsible sections
    const [showAhorro, setShowAhorro] = useState(false)
    const [showInmuebles, setShowInmuebles] = useState(false)
    const [showDeducciones, setShowDeducciones] = useState(false)
    const [showAutonomo, setShowAutonomo] = useState(false)

    // UI state
    const [isLoading, setIsLoading] = useState(false)
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
    const [isExporting, setIsExporting] = useState(false)

    // Load user data
    useEffect(() => {
        if (user) {
            setName(user.name || '')
            setEmail(user.email || '')
        }
    }, [user])

    // Sync fiscal profile into form when loaded
    useEffect(() => {
        if (!fiscal.loading && fiscal.profile) {
            setFiscalForm(fiscal.profile)
            const desc = fiscal.profile.anios_nacimiento_desc
            if (desc && desc.length > 0) {
                setChildYears(desc.map(String))
            }
            // Auto-expand sections if they have data
            if ((fiscal.profile.intereses ?? 0) > 0 || (fiscal.profile.dividendos ?? 0) > 0 || (fiscal.profile.ganancias_fondos ?? 0) > 0) {
                setShowAhorro(true)
            }
            if ((fiscal.profile.ingresos_alquiler ?? 0) > 0) {
                setShowInmuebles(true)
            }
            if ((fiscal.profile.aportaciones_plan_pensiones ?? 0) > 0
                || fiscal.profile.hipoteca_pre2013
                || fiscal.profile.madre_trabajadora_ss
                || fiscal.profile.familia_numerosa
                || (fiscal.profile.donativos_ley_49_2002 ?? 0) > 0
                || (fiscal.profile.retenciones_trabajo ?? 0) > 0
                || (fiscal.profile.retenciones_alquiler ?? 0) > 0
                || (fiscal.profile.retenciones_ahorro ?? 0) > 0) {
                setShowDeducciones(true)
            }
            if (fiscal.profile.epigrafe_iae || fiscal.profile.regimen_iva || fiscal.profile.metodo_estimacion_irpf) {
                setShowAutonomo(true)
            }
        }
    }, [fiscal.loading, fiscal.profile])

    // Fetch email alerts status
    useEffect(() => {
        if (activeTab === 'notifications') {
            apiRequest<{ enabled: boolean }>('/api/deadlines/email-alerts/status')
                .then(data => setEmailAlertsEnabled(data.enabled))
                .catch(() => {})
        }
    }, [activeTab, apiRequest])

    const handleToggleEmailAlerts = async () => {
        setEmailAlertsLoading(true)
        try {
            const data = await apiRequest<{ enabled: boolean }>('/api/deadlines/email-alerts/toggle', { method: 'POST' })
            setEmailAlertsEnabled(data.enabled)
            setMessage({ type: 'success', text: data.enabled ? 'Alertas por email activadas' : 'Alertas por email desactivadas' })
        } catch {
            setMessage({ type: 'error', text: 'Error al cambiar las alertas por email' })
        } finally {
            setEmailAlertsLoading(false)
        }
    }

    // Auto-dismiss messages
    useEffect(() => {
        if (message) {
            const timer = setTimeout(() => setMessage(null), 5000)
            return () => clearTimeout(timer)
        }
    }, [message])

    // Helper: update fiscal form field
    const updateFiscal = (key: keyof FiscalProfile, value: any) => {
        setFiscalForm(prev => ({ ...prev, [key]: value }))
    }

    // Check if field was auto-detected from conversation
    const isFromConversation = (key: string) =>
        fiscal.fieldMeta[key]?.source === 'conversation'

    // ---- HANDLERS ----

    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)
        setMessage(null)
        try {
            await apiRequest('/api/users/me', {
                method: 'PATCH',
                body: JSON.stringify({ name, email }),
            })
            setMessage({ type: 'success', text: 'Perfil actualizado correctamente' })
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message })
        } finally {
            setIsLoading(false)
        }
    }

    const handleChangePassword = async (e: React.FormEvent) => {
        e.preventDefault()
        setMessage(null)

        if (newPassword !== confirmPassword) {
            setMessage({ type: 'error', text: 'Las contraseñas no coinciden' })
            return
        }
        if (newPassword.length < 8) {
            setMessage({ type: 'error', text: 'La nueva contraseña debe tener al menos 8 caracteres' })
            return
        }

        setIsLoading(true)
        try {
            await apiRequest('/api/users/me/password', {
                method: 'PUT',
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword,
                }),
            })
            setMessage({ type: 'success', text: 'Contraseña actualizada correctamente' })
            setCurrentPassword('')
            setNewPassword('')
            setConfirmPassword('')
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message })
        } finally {
            setIsLoading(false)
        }
    }

    const handleSaveFiscalProfile = async (e: React.FormEvent) => {
        e.preventDefault()
        setMessage(null)

        // Parse child years
        const parsedYears = childYears
            .map(y => parseInt(y, 10))
            .filter(y => !isNaN(y) && y > 1900 && y <= new Date().getFullYear())

        const dataToSave: Partial<FiscalProfile> = {
            ...fiscalForm,
            anios_nacimiento_desc: parsedYears.length > 0 ? parsedYears : null,
        }

        const ok = await fiscal.save(dataToSave)
        if (ok) {
            setMessage({ type: 'success', text: 'Perfil fiscal guardado correctamente' })
        } else if (fiscal.error) {
            setMessage({ type: 'error', text: fiscal.error })
        }
    }

    const handleExportData = async () => {
        setIsExporting(true)
        setMessage(null)
        try {
            const data = await apiRequest('/api/users/me/data')

            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `impuestify-mis-datos-${new Date().toISOString().split('T')[0]}.json`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)

            setMessage({ type: 'success', text: 'Datos exportados correctamente' })
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message })
        } finally {
            setIsExporting(false)
        }
    }

    const handleDeleteAccount = async () => {
        const confirmed = window.confirm(
            'ATENCIÓN: Esta acción es IRREVERSIBLE.\n\n' +
            'Se eliminarán permanentemente:\n' +
            '- Tu cuenta de usuario\n' +
            '- Todas tus conversaciones\n' +
            '- Todos tus mensajes\n' +
            '- Tu perfil fiscal\n\n' +
            '¿Estás seguro de que deseas continuar?'
        )
        if (!confirmed) return

        const doubleConfirm = window.confirm(
            'ÚLTIMA CONFIRMACIÓN\n\n' +
            '¿Proceder con la eliminación permanente?'
        )
        if (!doubleConfirm) return

        setIsLoading(true)
        setMessage(null)
        try {
            await apiRequest('/api/users/me', { method: 'DELETE' })
            logout()
            navigate('/', { replace: true })
            alert('Tu cuenta ha sido eliminada permanentemente.')
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message })
            setIsLoading(false)
        }
    }

    // ---- ADD/REMOVE child year helpers ----
    const addChildYear = () => setChildYears(prev => [...prev, ''])
    const removeChildYear = (index: number) =>
        setChildYears(prev => prev.filter((_, i) => i !== index))
    const updateChildYear = (index: number, value: string) =>
        setChildYears(prev => prev.map((y, i) => i === index ? value : y))

    // Sync num_descendientes when childYears change
    useEffect(() => {
        updateFiscal('num_descendientes', childYears.length || null)
    }, [childYears.length])

    // ---- RENDER ----

    const ConversationBadge = ({ field }: { field: string }) =>
        isFromConversation(field) ? (
            <span className="conversation-badge" title="Detectado automáticamente en una conversación">
                <RefreshCw size={12} /> Conversación
            </span>
        ) : null

    return (
        <div className="settings-page">
            <Header />

            <div className="settings-container">
                <div className="settings-header">
                    <h1>
                        <Shield size={32} />
                        Mi Cuenta
                    </h1>
                    <p className="settings-subtitle">
                        Gestiona tu perfil, seguridad, datos fiscales y derechos RGPD
                    </p>
                </div>

                {/* Message Banner */}
                {message && (
                    <div className={`message-banner ${message.type}`}>
                        {message.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
                        <span>{message.text}</span>
                    </div>
                )}

                {/* Tabs */}
                <div className="settings-tabs">
                    <button className={`tab-btn ${activeTab === 'personal' ? 'active' : ''}`} onClick={() => setActiveTab('personal')}>
                        <User size={16} /> Personal
                    </button>
                    <button className={`tab-btn ${activeTab === 'security' ? 'active' : ''}`} onClick={() => setActiveTab('security')}>
                        <Lock size={16} /> Seguridad
                    </button>
                    <button className={`tab-btn ${activeTab === 'fiscal' ? 'active' : ''}`} onClick={() => setActiveTab('fiscal')}>
                        <Calculator size={16} /> Perfil Fiscal
                    </button>
                    <button className={`tab-btn ${activeTab === 'subscription' ? 'active' : ''}`} onClick={() => setActiveTab('subscription')}>
                        <CreditCard size={16} /> Suscripción
                    </button>
                    <button className={`tab-btn ${activeTab === 'privacy' ? 'active' : ''}`} onClick={() => setActiveTab('privacy')}>
                        <Shield size={16} /> Privacidad
                    </button>
                    <button className={`tab-btn ${activeTab === 'notifications' ? 'active' : ''}`} onClick={() => setActiveTab('notifications')}>
                        <Bell size={16} /> Notificaciones
                    </button>
                </div>

                {/* ==================== PERSONAL TAB ==================== */}
                {activeTab === 'personal' && (
                    <section className="settings-section">
                        <div className="section-header">
                            <User size={24} />
                            <h2>Información Personal</h2>
                        </div>

                        <form onSubmit={handleUpdateProfile} className="settings-form">
                            <div className="form-group">
                                <label htmlFor="name">Nombre</label>
                                <input type="text" id="name" value={name} onChange={e => setName(e.target.value)}
                                    placeholder="Tu nombre" className="form-input" />
                            </div>
                            <div className="form-group">
                                <label htmlFor="email">Email</label>
                                <input type="email" id="email" value={email} onChange={e => setEmail(e.target.value)}
                                    placeholder="tu@email.com" className="form-input" disabled />
                                <span className="form-hint">El email no se puede cambiar por seguridad</span>
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={isLoading}>
                                {isLoading ? <><Loader size={18} className="animate-spin" /> Guardando...</>
                                    : <><Save size={18} /> Guardar Cambios</>}
                            </button>
                        </form>
                    </section>
                )}

                {/* ==================== SECURITY TAB ==================== */}
                {activeTab === 'security' && (
                    <section className="settings-section">
                        <div className="section-header">
                            <Lock size={24} />
                            <h2>Cambiar Contraseña</h2>
                        </div>

                        <form onSubmit={handleChangePassword} className="settings-form">
                            <div className="form-group">
                                <label htmlFor="currentPassword">Contraseña actual</label>
                                <input type="password" id="currentPassword" value={currentPassword}
                                    onChange={e => setCurrentPassword(e.target.value)}
                                    className="form-input" required />
                            </div>
                            <div className="form-group">
                                <label htmlFor="newPassword">Nueva contraseña</label>
                                <input type="password" id="newPassword" value={newPassword}
                                    onChange={e => setNewPassword(e.target.value)}
                                    className="form-input" required minLength={8} />
                                <span className="form-hint">Mínimo 8 caracteres</span>
                            </div>
                            <div className="form-group">
                                <label htmlFor="confirmPassword">Confirmar nueva contraseña</label>
                                <input type="password" id="confirmPassword" value={confirmPassword}
                                    onChange={e => setConfirmPassword(e.target.value)}
                                    className="form-input" required minLength={8} />
                            </div>
                            <button type="submit" className="btn btn-primary" disabled={isLoading}>
                                {isLoading ? <><Loader size={18} className="animate-spin" /> Cambiando...</>
                                    : <><Lock size={18} /> Cambiar Contraseña</>}
                            </button>
                        </form>
                    </section>
                )}

                {/* ==================== FISCAL PROFILE TAB ==================== */}
                {activeTab === 'fiscal' && (
                    <section className="settings-section">
                        <div className="section-header">
                            <Calculator size={24} />
                            <h2>Perfil Fiscal</h2>
                        </div>
                        <p className="section-description">
                            Estos datos son <strong>voluntarios</strong> y permiten calcular tu IRPF de forma precisa.
                            Si mencionas datos fiscales en una conversación, se rellenarán automáticamente aquí.
                        </p>

                        {fiscal.loading ? (
                            <div className="fiscal-loading"><Loader size={24} className="animate-spin" /> Cargando perfil fiscal...</div>
                        ) : (
                            <form onSubmit={handleSaveFiscalProfile} className="settings-form" noValidate>

                                {/* --- Datos personales fiscales --- */}
                                <h3 className="fiscal-section-title">Datos personales</h3>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Comunidad Autónoma <ConversationBadge field="ccaa_residencia" /></label>
                                        <select className="form-input" value={fiscalForm.ccaa_residencia || ''}
                                            onChange={e => updateFiscal('ccaa_residencia', e.target.value || null)}>
                                            {CCAA_OPTIONS.map(c => (
                                                <option key={c} value={c}>{c ? (CCAA_DISPLAY[c] || c) : 'Selecciona...'}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label>Fecha de nacimiento</label>
                                        <input type="date" className="form-input"
                                            value={fiscalForm.fecha_nacimiento || ''}
                                            onChange={e => updateFiscal('fecha_nacimiento', e.target.value || null)} />
                                    </div>
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Situación laboral</label>
                                        <select className="form-input" value={fiscalForm.situacion_laboral || ''}
                                            onChange={e => updateFiscal('situacion_laboral', e.target.value || null)}>
                                            {SITUACION_OPTIONS.map(o => (
                                                <option key={o.value} value={o.value}>{o.label}</option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="form-group">
                                        <label>Grado de discapacidad (%)</label>
                                        <select className="form-input"
                                            value={fiscalForm.discapacidad_contribuyente ?? ''}
                                            onChange={e => updateFiscal('discapacidad_contribuyente', e.target.value ? Number(e.target.value) : null)}>
                                            <option value="">Sin discapacidad</option>
                                            <option value="33">33% o más</option>
                                            <option value="65">65% o más</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label className="checkbox-label">
                                            <input type="checkbox"
                                                checked={fiscalForm.tributacion_conjunta || false}
                                                onChange={e => updateFiscal('tributacion_conjunta', e.target.checked)} />
                                            Tributación conjunta
                                        </label>
                                        <span className="form-hint">Permite declarar con tu unidad familiar</span>
                                    </div>
                                    {fiscalForm.tributacion_conjunta && (
                                        <div className="form-group">
                                            <label>Tipo de unidad familiar</label>
                                            <select className="form-input"
                                                value={fiscalForm.tipo_unidad_familiar || 'matrimonio'}
                                                onChange={e => updateFiscal('tipo_unidad_familiar', e.target.value)}>
                                                <option value="matrimonio">Matrimonio (reducción 3.400 EUR)</option>
                                                <option value="monoparental">Monoparental (reducción 2.150 EUR)</option>
                                            </select>
                                        </div>
                                    )}
                                </div>

                                {/* --- Ingresos del trabajo --- */}
                                <h3 className="fiscal-section-title">Ingresos del trabajo</h3>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Ingresos brutos anuales <ConversationBadge field="ingresos_trabajo" /></label>
                                        <div className="input-with-suffix">
                                            <input type="number" className="form-input" placeholder="0"
                                                value={fiscalForm.ingresos_trabajo ?? ''}
                                                onChange={e => updateFiscal('ingresos_trabajo', e.target.value ? Number(e.target.value) : null)} />
                                            <span className="input-suffix">EUR/año</span>
                                        </div>
                                    </div>
                                    <div className="form-group">
                                        <label>SS empleado anual</label>
                                        <div className="input-with-suffix">
                                            <input type="number" className="form-input" placeholder="Se estima al 6,35%"
                                                value={fiscalForm.ss_empleado ?? ''}
                                                onChange={e => updateFiscal('ss_empleado', e.target.value ? Number(e.target.value) : null)} />
                                            <span className="input-suffix">EUR/año</span>
                                        </div>
                                    </div>
                                </div>

                                {/* --- Situación familiar (MPYF) --- */}
                                <h3 className="fiscal-section-title">Situación familiar (MPYF)</h3>

                                <div className="form-group">
                                    <label>Hijos/as a cargo</label>
                                    {childYears.map((year, i) => (
                                        <div key={i} className="child-year-row">
                                            <span className="child-label">Hijo/a {i + 1}</span>
                                            <input type="number" className="form-input child-year-input"
                                                placeholder="Año nacimiento" min="1900" max={new Date().getFullYear()}
                                                value={year} onChange={e => updateChildYear(i, e.target.value)} />
                                            <button type="button" className="btn-icon-remove" onClick={() => removeChildYear(i)}>
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    ))}
                                    <button type="button" className="btn btn-add-child" onClick={addChildYear}>
                                        + Añadir hijo/a
                                    </button>
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label className="checkbox-label">
                                            <input type="checkbox" checked={fiscalForm.custodia_compartida || false}
                                                onChange={e => updateFiscal('custodia_compartida', e.target.checked)} />
                                            Custodia compartida
                                        </label>
                                    </div>
                                </div>

                                <div className="form-row">
                                    <div className="form-group">
                                        <label>Ascendientes mayores de 65 a cargo</label>
                                        <input type="number" className="form-input" min="0" max="10"
                                            value={fiscalForm.num_ascendientes_65 ?? ''}
                                            onChange={e => updateFiscal('num_ascendientes_65', e.target.value ? Number(e.target.value) : null)} />
                                    </div>
                                    <div className="form-group">
                                        <label>Ascendientes mayores de 75 a cargo</label>
                                        <input type="number" className="form-input" min="0" max="10"
                                            value={fiscalForm.num_ascendientes_75 ?? ''}
                                            onChange={e => updateFiscal('num_ascendientes_75', e.target.value ? Number(e.target.value) : null)} />
                                    </div>
                                </div>

                                {/* --- Rentas del ahorro (collapsible) --- */}
                                <button type="button" className="collapsible-header" onClick={() => setShowAhorro(!showAhorro)}>
                                    {showAhorro ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    <span>Rentas del ahorro</span>
                                </button>
                                {showAhorro && (
                                    <div className="collapsible-content">
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Intereses de cuentas/depósitos</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0"
                                                        value={fiscalForm.intereses ?? ''}
                                                        onChange={e => updateFiscal('intereses', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                            </div>
                                            <div className="form-group">
                                                <label>Dividendos</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0"
                                                        value={fiscalForm.dividendos ?? ''}
                                                        onChange={e => updateFiscal('dividendos', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="form-group">
                                            <label>Ganancias de fondos de inversión</label>
                                            <div className="input-with-suffix">
                                                <input type="number" className="form-input" placeholder="0"
                                                    value={fiscalForm.ganancias_fondos ?? ''}
                                                    onChange={e => updateFiscal('ganancias_fondos', e.target.value ? Number(e.target.value) : null)} />
                                                <span className="input-suffix">EUR/año</span>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* --- Rentas de inmuebles (collapsible) --- */}
                                <button type="button" className="collapsible-header" onClick={() => setShowInmuebles(!showInmuebles)}>
                                    {showInmuebles ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    <span>Rentas de inmuebles</span>
                                </button>
                                {showInmuebles && (
                                    <div className="collapsible-content">
                                        <h4 className="fiscal-subsection-title">Como arrendador (propietario)</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Ingresos por alquiler</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0"
                                                        value={fiscalForm.ingresos_alquiler ?? ''}
                                                        onChange={e => updateFiscal('ingresos_alquiler', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                            </div>
                                            <div className="form-group">
                                                <label>Valor adquisición inmueble</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0"
                                                        value={fiscalForm.valor_adquisicion_inmueble ?? ''}
                                                        onChange={e => updateFiscal('valor_adquisicion_inmueble', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR</span>
                                                </div>
                                            </div>
                                        </div>

                                        <h4 className="fiscal-subsection-title">Como inquilino (vivienda habitual)</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Alquiler anual pagado</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0"
                                                        value={fiscalForm.alquiler_pagado_anual ?? ''}
                                                        onChange={e => updateFiscal('alquiler_pagado_anual', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                                <span className="form-hint">Necesario para deducciones autonómicas por alquiler</span>
                                            </div>
                                            <div className="form-group">
                                                <label className="checkbox-label">
                                                    <input type="checkbox"
                                                        checked={fiscalForm.alquiler_habitual_pre2015 || false}
                                                        onChange={e => updateFiscal('alquiler_habitual_pre2015', e.target.checked)} />
                                                    Contrato anterior al 1/1/2015
                                                </label>
                                                <span className="form-hint">Régimen transitorio estatal: deducción 10,05% (máx. 9.040 EUR)</span>
                                            </div>
                                        </div>

                                        <h4 className="fiscal-subsection-title">Segundas viviendas</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Valor catastral segundas viviendas</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0"
                                                        value={fiscalForm.valor_catastral_segundas_viviendas ?? ''}
                                                        onChange={e => updateFiscal('valor_catastral_segundas_viviendas', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR</span>
                                                </div>
                                                <span className="form-hint">Viviendas no alquiladas ni habitual. Imputa renta del 1,1%-2%</span>
                                            </div>
                                            <div className="form-group">
                                                <label className="checkbox-label">
                                                    <input type="checkbox"
                                                        checked={fiscalForm.valor_catastral_revisado_post1994 ?? true}
                                                        onChange={e => updateFiscal('valor_catastral_revisado_post1994', e.target.checked)} />
                                                    Valor catastral revisado después de 1994
                                                </label>
                                                <span className="form-hint">Si no fue revisado se aplica el 2% en lugar del 1,1%</span>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* --- Reducciones y Deducciones (collapsible) --- */}
                                <button type="button" className="collapsible-header" onClick={() => setShowDeducciones(!showDeducciones)}>
                                    {showDeducciones ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                    <span>Reducciones y deducciones</span>
                                </button>
                                {showDeducciones && (
                                    <div className="collapsible-content">

                                        <h4 className="fiscal-subsection-title">Planes de pensiones</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Aportaciones propias</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0" min="0"
                                                        value={fiscalForm.aportaciones_plan_pensiones ?? ''}
                                                        onChange={e => updateFiscal('aportaciones_plan_pensiones', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                                <span className="form-hint">Max. 1.500 EUR/año (reduce base imponible general)</span>
                                            </div>
                                            <div className="form-group">
                                                <label>Aportaciones de la empresa</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0" min="0"
                                                        value={fiscalForm.aportaciones_plan_pensiones_empresa ?? ''}
                                                        onChange={e => updateFiscal('aportaciones_plan_pensiones_empresa', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                                <span className="form-hint">Límite conjunto con propias: 8.500 EUR</span>
                                            </div>
                                        </div>

                                        <h4 className="fiscal-subsection-title">Vivienda habitual (hipoteca anterior a 2013)</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label className="checkbox-label">
                                                    <input type="checkbox"
                                                        checked={fiscalForm.hipoteca_pre2013 || false}
                                                        onChange={e => updateFiscal('hipoteca_pre2013', e.target.checked)} />
                                                    Hipoteca firmada antes del 1/1/2013
                                                </label>
                                                <span className="form-hint">Deducción 15% sobre máx. 9.040 EUR/año</span>
                                            </div>
                                        </div>
                                        {fiscalForm.hipoteca_pre2013 && (
                                            <div className="form-row">
                                                <div className="form-group">
                                                    <label>Capital amortizado en el año</label>
                                                    <div className="input-with-suffix">
                                                        <input type="number" className="form-input" placeholder="0" min="0"
                                                            value={fiscalForm.capital_amortizado_hipoteca ?? ''}
                                                            onChange={e => updateFiscal('capital_amortizado_hipoteca', e.target.value ? Number(e.target.value) : null)} />
                                                        <span className="input-suffix">EUR</span>
                                                    </div>
                                                </div>
                                                <div className="form-group">
                                                    <label>Intereses de hipoteca pagados</label>
                                                    <div className="input-with-suffix">
                                                        <input type="number" className="form-input" placeholder="0" min="0"
                                                            value={fiscalForm.intereses_hipoteca ?? ''}
                                                            onChange={e => updateFiscal('intereses_hipoteca', e.target.value ? Number(e.target.value) : null)} />
                                                        <span className="input-suffix">EUR</span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        <h4 className="fiscal-subsection-title">Maternidad</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label className="checkbox-label">
                                                    <input type="checkbox"
                                                        checked={fiscalForm.madre_trabajadora_ss || false}
                                                        onChange={e => updateFiscal('madre_trabajadora_ss', e.target.checked)} />
                                                    Madre trabajadora dada de alta en la SS
                                                </label>
                                                <span className="form-hint">Deducción por maternidad: 1.200 EUR/hijo menor de 3 años</span>
                                            </div>
                                            {fiscalForm.madre_trabajadora_ss && (
                                                <div className="form-group">
                                                    <label>Gastos de guardería (anual)</label>
                                                    <div className="input-with-suffix">
                                                        <input type="number" className="form-input" placeholder="0" min="0"
                                                            value={fiscalForm.gastos_guarderia_anual ?? ''}
                                                            onChange={e => updateFiscal('gastos_guarderia_anual', e.target.value ? Number(e.target.value) : null)} />
                                                        <span className="input-suffix">EUR/año</span>
                                                    </div>
                                                    <span className="form-hint">Hasta 1.000 EUR adicionales por hijo en guardería autorizada</span>
                                                </div>
                                            )}
                                        </div>

                                        <h4 className="fiscal-subsection-title">Familia numerosa</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label className="checkbox-label">
                                                    <input type="checkbox"
                                                        checked={fiscalForm.familia_numerosa || false}
                                                        onChange={e => updateFiscal('familia_numerosa', e.target.checked)} />
                                                    Familia numerosa reconocida
                                                </label>
                                            </div>
                                            {fiscalForm.familia_numerosa && (
                                                <div className="form-group">
                                                    <label>Tipo de familia numerosa</label>
                                                    <select className="form-input"
                                                        value={fiscalForm.tipo_familia_numerosa || 'general'}
                                                        onChange={e => updateFiscal('tipo_familia_numerosa', e.target.value)}>
                                                        <option value="general">General (3-4 hijos) — 1.200 EUR</option>
                                                        <option value="especial">Especial (5+ hijos) — 2.400 EUR</option>
                                                    </select>
                                                </div>
                                            )}
                                        </div>

                                        <h4 className="fiscal-subsection-title">Donativos (Ley 49/2002)</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Importe donado</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0" min="0"
                                                        value={fiscalForm.donativos_ley_49_2002 ?? ''}
                                                        onChange={e => updateFiscal('donativos_ley_49_2002', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR</span>
                                                </div>
                                                <span className="form-hint">ONGs, fundaciones... 80% primeros 250 EUR, 40% resto</span>
                                            </div>
                                            {(fiscalForm.donativos_ley_49_2002 ?? 0) > 0 && (
                                                <div className="form-group">
                                                    <label className="checkbox-label">
                                                        <input type="checkbox"
                                                            checked={fiscalForm.donativo_recurrente || false}
                                                            onChange={e => updateFiscal('donativo_recurrente', e.target.checked)} />
                                                        Donante recurrente (3+ años a la misma entidad)
                                                    </label>
                                                    <span className="form-hint">Sube al 45% el exceso sobre 250 EUR</span>
                                                </div>
                                            )}
                                        </div>

                                        <h4 className="fiscal-subsection-title">Retenciones pagadas</h4>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Retenciones del trabajo</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0" min="0"
                                                        value={fiscalForm.retenciones_trabajo ?? ''}
                                                        onChange={e => updateFiscal('retenciones_trabajo', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                                <span className="form-hint">Total retenido en nómina por tu empresa</span>
                                            </div>
                                            <div className="form-group">
                                                <label>Retenciones sobre alquileres</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0" min="0"
                                                        value={fiscalForm.retenciones_alquiler ?? ''}
                                                        onChange={e => updateFiscal('retenciones_alquiler', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                                <span className="form-hint">19% retenido por inquilinos empresas/profesionales</span>
                                            </div>
                                        </div>
                                        <div className="form-row">
                                            <div className="form-group">
                                                <label>Retenciones sobre capital mobiliario</label>
                                                <div className="input-with-suffix">
                                                    <input type="number" className="form-input" placeholder="0" min="0"
                                                        value={fiscalForm.retenciones_ahorro ?? ''}
                                                        onChange={e => updateFiscal('retenciones_ahorro', e.target.value ? Number(e.target.value) : null)} />
                                                    <span className="input-suffix">EUR/año</span>
                                                </div>
                                                <span className="form-hint">19% retenido por bancos sobre intereses y dividendos</span>
                                            </div>
                                        </div>

                                    </div>
                                )}

                                {/* --- Datos de autónomo (collapsible, only for autonomo/owner plans) --- */}
                                {(subscription.planType === 'autonomo' || subscription.isOwner) && (
                                    <>
                                        <button type="button" className="collapsible-header" onClick={() => setShowAutonomo(!showAutonomo)}>
                                            {showAutonomo ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                            <span>Datos de autónomo</span>
                                        </button>
                                        {showAutonomo && (
                                            <div className="collapsible-content">
                                                <p className="section-description" style={{ marginBottom: 'var(--spacing-4)', fontSize: '0.85rem' }}>
                                                    Estos datos permiten personalizar el cálculo del Modelo 303, 130 y cuota de autónomos.
                                                </p>

                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label>Epígrafe IAE</label>
                                                        <input type="text" className="form-input" placeholder="Ej: 861, 749.1"
                                                            value={fiscalForm.epigrafe_iae || ''}
                                                            onChange={e => updateFiscal('epigrafe_iae', e.target.value || null)} />
                                                    </div>
                                                    <div className="form-group">
                                                        <label>Tipo de actividad</label>
                                                        <select className="form-input" value={fiscalForm.tipo_actividad || ''}
                                                            onChange={e => updateFiscal('tipo_actividad', e.target.value || null)}>
                                                            <option value="">Selecciona...</option>
                                                            <option value="profesional">Profesional</option>
                                                            <option value="empresarial">Empresarial</option>
                                                            <option value="artistica">Artística</option>
                                                        </select>
                                                    </div>
                                                </div>

                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label>Fecha alta autónomo</label>
                                                        <input type="date" className="form-input"
                                                            value={fiscalForm.fecha_alta_autonomo || ''}
                                                            onChange={e => updateFiscal('fecha_alta_autonomo', e.target.value || null)} />
                                                    </div>
                                                    <div className="form-group">
                                                        <label>Método estimación IRPF</label>
                                                        <select className="form-input" value={fiscalForm.metodo_estimacion_irpf || ''}
                                                            onChange={e => updateFiscal('metodo_estimacion_irpf', e.target.value || null)}>
                                                            <option value="">Selecciona...</option>
                                                            <option value="directa_normal">Directa normal</option>
                                                            <option value="directa_simplificada">Directa simplificada</option>
                                                            <option value="objetiva">Objetiva (módulos)</option>
                                                        </select>
                                                    </div>
                                                </div>

                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label>Régimen IVA</label>
                                                        <select className="form-input" value={fiscalForm.regimen_iva || ''}
                                                            onChange={e => updateFiscal('regimen_iva', e.target.value || null)}>
                                                            <option value="">Selecciona...</option>
                                                            <option value="general">General</option>
                                                            <option value="simplificado">Simplificado</option>
                                                            <option value="recargo_equivalencia">Recargo de equivalencia</option>
                                                            <option value="exento">Exento</option>
                                                            <option value="ipsi">IPSI (Ceuta/Melilla)</option>
                                                        </select>
                                                    </div>
                                                    <div className="form-group">
                                                        <label>Tipo retención facturas</label>
                                                        <select className="form-input"
                                                            value={fiscalForm.tipo_retencion_facturas ?? ''}
                                                            onChange={e => updateFiscal('tipo_retencion_facturas', e.target.value ? Number(e.target.value) : null)}>
                                                            <option value="">Selecciona...</option>
                                                            <option value="15">15% (general)</option>
                                                            <option value="7">7% (primeros 3 años)</option>
                                                        </select>
                                                    </div>
                                                </div>

                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label>Rendimientos netos mensuales</label>
                                                        <div className="input-with-suffix">
                                                            <input type="number" className="form-input" placeholder="0"
                                                                value={fiscalForm.rendimientos_netos_mensuales ?? ''}
                                                                onChange={e => updateFiscal('rendimientos_netos_mensuales', e.target.value ? Number(e.target.value) : null)} />
                                                            <span className="input-suffix">EUR/mes</span>
                                                        </div>
                                                    </div>
                                                    <div className="form-group">
                                                        <label>Base cotización RETA</label>
                                                        <div className="input-with-suffix">
                                                            <input type="number" className="form-input" placeholder="0"
                                                                value={fiscalForm.base_cotizacion_reta ?? ''}
                                                                onChange={e => updateFiscal('base_cotizacion_reta', e.target.value ? Number(e.target.value) : null)} />
                                                            <span className="input-suffix">EUR/mes</span>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label className="checkbox-label">
                                                            <input type="checkbox" checked={fiscalForm.territorio_foral || false}
                                                                onChange={e => updateFiscal('territorio_foral', e.target.checked)} />
                                                            Territorio foral (País Vasco / Navarra)
                                                        </label>
                                                    </div>
                                                    {fiscalForm.territorio_foral && (
                                                        <div className="form-group">
                                                            <label>Territorio histórico</label>
                                                            <select className="form-input" value={fiscalForm.territorio_historico || ''}
                                                                onChange={e => updateFiscal('territorio_historico', e.target.value || null)}>
                                                                <option value="">Selecciona...</option>
                                                                <option value="bizkaia">Bizkaia</option>
                                                                <option value="gipuzkoa">Gipuzkoa</option>
                                                                <option value="araba">Araba/Álava</option>
                                                                <option value="navarra">Navarra</option>
                                                            </select>
                                                        </div>
                                                    )}
                                                </div>

                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label className="checkbox-label">
                                                            <input type="checkbox" checked={fiscalForm.tarifa_plana || false}
                                                                onChange={e => updateFiscal('tarifa_plana', e.target.checked)} />
                                                            Tarifa plana (80 EUR/mes)
                                                        </label>
                                                    </div>
                                                    <div className="form-group">
                                                        <label className="checkbox-label">
                                                            <input type="checkbox" checked={fiscalForm.pluriactividad || false}
                                                                onChange={e => updateFiscal('pluriactividad', e.target.checked)} />
                                                            Pluriactividad (también asalariado)
                                                        </label>
                                                    </div>
                                                </div>

                                                <div className="form-row">
                                                    <div className="form-group">
                                                        <label className="checkbox-label">
                                                            <input type="checkbox" checked={fiscalForm.ceuta_melilla || false}
                                                                onChange={e => {
                                                                    const checked = e.target.checked
                                                                    updateFiscal('ceuta_melilla', checked)
                                                                    if (checked && (!fiscalForm.regimen_iva || fiscalForm.regimen_iva === 'general')) {
                                                                        updateFiscal('regimen_iva', 'ipsi')
                                                                    }
                                                                    if (!checked && fiscalForm.regimen_iva === 'ipsi') {
                                                                        updateFiscal('regimen_iva', 'general')
                                                                    }
                                                                }} />
                                                            Residente en Ceuta o Melilla
                                                        </label>
                                                        <small className="field-hint">
                                                            Deducción del 60% en IRPF + bonificación 50% cuota SS + IPSI en lugar de IVA
                                                        </small>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </>
                                )}

                                {/* --- Deducciones autonómicas (DynamicFiscalForm) --- */}
                                {fiscalForm.ccaa_residencia && (
                                    <DynamicFiscalForm
                                        ccaa={fiscalForm.ccaa_residencia}
                                        values={fiscalForm}
                                        onChange={(key, value) => updateFiscal(key, value)}
                                        compact
                                    />
                                )}

                                {/* Save button */}
                                <button type="submit" className="btn btn-primary" disabled={fiscal.saving}>
                                    {fiscal.saving ? <><Loader size={18} className="animate-spin" /> Guardando...</>
                                        : <><Save size={18} /> Guardar Perfil Fiscal</>}
                                </button>
                            </form>
                        )}
                    </section>
                )}

                {/* ==================== SUBSCRIPTION TAB ==================== */}
                {activeTab === 'subscription' && (
                    <section className="settings-section">
                        <div className="section-header">
                            <CreditCard size={24} />
                            <h2>Mi Suscripción</h2>
                        </div>

                        {subscription.loading ? (
                            <div className="fiscal-loading"><Loader size={24} className="animate-spin" /> Cargando...</div>
                        ) : subscription.isOwner ? (
                            <div className="subscription-status">
                                <div className="subscription-badge owner">
                                    <Shield size={18} />
                                    <span>Owner</span>
                                </div>
                                <p className="section-description">
                                    Tienes acceso completo como propietario de la plataforma.
                                </p>
                            </div>
                        ) : subscription.hasAccess ? (
                            <div className="subscription-status">
                                <div className="subscription-badge active">
                                    <CheckCircle size={18} />
                                    <span>
                                        {subscription.status === 'grace_period' ? 'Período de gracia' : 'Activa'}
                                    </span>
                                </div>
                                <p className="section-description">
                                    {subscription.status === 'grace_period'
                                        ? 'Tienes acceso gratuito durante el periodo de gracia. Tu acceso continuará hasta el final del periodo.'
                                        : `Plan ${subscription.planType || 'Particular'} activo.`}
                                </p>

                                {subscription.currentPeriodEnd && subscription.status !== 'grace_period' && (
                                    <p className="subscription-detail">
                                        <strong>Próximo cobro:</strong>{' '}
                                        {new Date(subscription.currentPeriodEnd).toLocaleDateString('es-ES', {
                                            day: 'numeric', month: 'long', year: 'numeric'
                                        })}
                                    </p>
                                )}

                                {subscription.cancelAtPeriodEnd && (
                                    <div className="subscription-warning">
                                        <AlertCircle size={18} />
                                        <span>Tu suscripción se cancelará al final del periodo actual.</span>
                                    </div>
                                )}

                                {subscription.status !== 'grace_period' && (
                                    <button
                                        onClick={subscription.openPortal}
                                        className="btn btn-secondary"
                                    >
                                        <ExternalLink size={18} />
                                        Gestionar suscripción
                                    </button>
                                )}
                            </div>
                        ) : (
                            <div className="subscription-status">
                                <div className="subscription-badge inactive">
                                    <AlertCircle size={18} />
                                    <span>Sin suscripción</span>
                                </div>
                                <p className="section-description">
                                    No tienes una suscripción activa. Suscríbete para acceder a todas
                                    las funcionalidades de Impuestify.
                                </p>
                                <button
                                    onClick={subscription.createCheckout}
                                    className="btn btn-primary"
                                >
                                    <CreditCard size={18} />
                                    Suscribirme - 5 EUR/mes
                                </button>
                            </div>
                        )}

                        {subscription.error && (
                            <div className="message-banner error" style={{ marginTop: 'var(--spacing-4)' }}>
                                <AlertCircle size={20} />
                                <span>{subscription.error}</span>
                            </div>
                        )}
                    </section>
                )}

                {/* ==================== PRIVACY TAB ==================== */}
                {activeTab === 'privacy' && (
                    <>
                        <section className="settings-section">
                            <div className="section-header">
                                <Shield size={24} />
                                <h2>Tus Derechos RGPD</h2>
                            </div>
                            <p className="section-description">
                                De acuerdo con el Reglamento General de Protección de Datos (RGPD),
                                tienes derecho a acceder, rectificar y eliminar tus datos personales.
                            </p>

                            <div className="gdpr-action">
                                <div className="gdpr-action-info">
                                    <div className="gdpr-action-header">
                                        <Download size={20} />
                                        <h3>Exportar Mis Datos</h3>
                                    </div>
                                    <p>
                                        Descarga una copia de todos tus datos personales en formato JSON
                                        (Art. 15 RGPD - Derecho de Acceso)
                                    </p>
                                </div>
                                <button onClick={handleExportData} className="btn btn-secondary" disabled={isExporting}>
                                    {isExporting ? <><Loader size={18} className="animate-spin" /> Exportando...</>
                                        : <><Download size={18} /> Exportar Datos</>}
                                </button>
                            </div>
                        </section>

                        <section className="settings-section danger-zone">
                            <div className="section-header">
                                <AlertCircle size={24} />
                                <h2>Zona Peligrosa</h2>
                            </div>
                            <p className="section-description danger-text">
                                Las acciones en esta sección son <strong>irreversibles</strong>. Procede con precaución.
                            </p>

                            <div className="gdpr-action">
                                <div className="gdpr-action-info">
                                    <div className="gdpr-action-header">
                                        <Trash2 size={20} />
                                        <h3>Eliminar Mi Cuenta</h3>
                                    </div>
                                    <p>
                                        Elimina permanentemente tu cuenta y todos los datos asociados
                                        (Art. 17 RGPD - Derecho de Supresión)
                                    </p>
                                    <ul className="danger-list">
                                        <li>Tu cuenta de usuario</li>
                                        <li>Todas tus conversaciones y mensajes</li>
                                        <li>Tu perfil fiscal</li>
                                        <li>Esta acción NO se puede deshacer</li>
                                    </ul>
                                </div>
                                <button onClick={handleDeleteAccount} className="btn btn-danger" disabled={isLoading}>
                                    <Trash2 size={18} /> Eliminar Cuenta
                                </button>
                            </div>
                        </section>
                    </>
                )}
                {/* ==================== NOTIFICATIONS TAB ==================== */}
                {activeTab === 'notifications' && (
                    <>
                    <section className="settings-section">
                        <div className="section-header">
                            <Bell size={24} />
                            <h2>Notificaciones Push</h2>
                        </div>
                        <p className="section-description">
                            Recibe alertas en tu dispositivo cuando se acerquen plazos fiscales importantes.
                            Compatible con Chrome, Firefox, Edge y Safari 16.4+.
                        </p>

                        {!push.isSupported ? (
                            <div className="notification-unsupported">
                                <BellOff size={20} />
                                <span>Tu navegador no soporta notificaciones push.</span>
                            </div>
                        ) : (
                            <>
                                {/* Status indicator */}
                                <div className="notification-status-row">
                                    <span className="notification-status-label">Estado:</span>
                                    {push.permission === 'denied' ? (
                                        <span className="notification-status notification-status--blocked">
                                            <BellOff size={14} /> Bloqueadas por el navegador
                                        </span>
                                    ) : push.isSubscribed ? (
                                        <span className="notification-status notification-status--active">
                                            <CheckCircle size={14} /> Activas
                                        </span>
                                    ) : (
                                        <span className="notification-status notification-status--off">
                                            <Bell size={14} /> Desactivadas
                                        </span>
                                    )}
                                </div>

                                {push.permission === 'denied' && (
                                    <div className="notification-hint">
                                        <AlertCircle size={16} />
                                        <span>
                                            Las notificaciones estan bloqueadas en este navegador.
                                            Ve a los ajustes del navegador y permite las notificaciones para este sitio.
                                        </span>
                                    </div>
                                )}

                                {push.error && (
                                    <div className="message-banner error" style={{ marginBottom: 'var(--spacing-4)' }}>
                                        <AlertCircle size={20} />
                                        <span>{push.error}</span>
                                    </div>
                                )}

                                {/* Main toggle */}
                                <div className="gdpr-action">
                                    <div className="gdpr-action-info">
                                        <div className="gdpr-action-header">
                                            <Bell size={20} />
                                            <h3>Alertas de plazos fiscales</h3>
                                        </div>
                                        <p>
                                            Recibe una notificacion antes de que venza cada plazo fiscal
                                            relevante para tu perfil.
                                        </p>
                                    </div>
                                    {push.isSubscribed ? (
                                        <button
                                            className="btn btn-secondary"
                                            onClick={() => push.unsubscribe()}
                                            disabled={push.loading}
                                        >
                                            {push.loading
                                                ? <><Loader size={18} className="animate-spin" /> Desactivando...</>
                                                : <><BellOff size={18} /> Desactivar</>}
                                        </button>
                                    ) : (
                                        <button
                                            className="btn btn-primary"
                                            onClick={() => push.subscribe(alertDays)}
                                            disabled={push.loading || push.permission === 'denied'}
                                        >
                                            {push.loading
                                                ? <><Loader size={18} className="animate-spin" /> Activando...</>
                                                : <><Bell size={18} /> Activar</>}
                                        </button>
                                    )}
                                </div>

                                {/* Alert days preferences (only visible when subscribed) */}
                                {push.isSubscribed && (
                                    <div className="notification-prefs">
                                        <h3 className="fiscal-section-title">Cuando avisar</h3>
                                        <p className="section-description" style={{ marginBottom: 'var(--spacing-3)' }}>
                                            Elige con cuánta antelación quieres recibir la alerta.
                                        </p>
                                        <div className="notification-days-grid">
                                            {([15, 5, 1] as const).map((day) => {
                                                const label =
                                                    day === 1 ? '1 día antes (urgente)' :
                                                    day === 5 ? '5 días antes' :
                                                    '15 días antes'
                                                const checked = alertDays.includes(day)
                                                const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
                                                    const next = e.target.checked
                                                        ? [...alertDays, day]
                                                        : alertDays.filter((d) => d !== day)
                                                    setAlertDays(next)
                                                    // Re-subscribe with updated days to persist preference
                                                    push.subscribe(next)
                                                }
                                                return (
                                                    <label key={day} className="checkbox-label notification-day-label">
                                                        <input
                                                            type="checkbox"
                                                            checked={checked}
                                                            onChange={handleChange}
                                                            disabled={push.loading}
                                                        />
                                                        {label}
                                                    </label>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </section>
                    {/* Email alerts section */}
                    <section className="settings-section" style={{ marginTop: 'var(--spacing-6)' }}>
                        <div className="section-header">
                            <Mail size={24} />
                            <h2>Alertas por email</h2>
                        </div>
                        <p className="section-description">
                            Recibe un email recordatorio 30 días antes de cada plazo fiscal importante.
                        </p>

                        <div className="gdpr-action">
                            <div className="gdpr-action-info">
                                <div className="gdpr-action-header">
                                    <Mail size={20} />
                                    <h3>Recordatorios por correo</h3>
                                </div>
                                <p>
                                    Te enviaremos un email a <strong>{user?.email}</strong> cuando
                                    se acerque un plazo fiscal relevante para tu perfil.
                                </p>
                            </div>
                            <button
                                className={`btn ${emailAlertsEnabled ? 'btn-secondary' : 'btn-primary'}`}
                                onClick={handleToggleEmailAlerts}
                                disabled={emailAlertsLoading}
                            >
                                {emailAlertsLoading ? (
                                    <><Loader size={18} className="animate-spin" /> Procesando...</>
                                ) : emailAlertsEnabled ? (
                                    <><BellOff size={18} /> Desactivar</>
                                ) : (
                                    <><Mail size={18} /> Activar</>
                                )}
                            </button>
                        </div>

                        {emailAlertsEnabled && (
                            <div className="notification-hint" style={{ marginTop: 'var(--spacing-3)', background: 'rgba(34, 197, 94, 0.08)', borderColor: 'rgba(34, 197, 94, 0.3)', color: '#22c55e' }}>
                                <CheckCircle size={16} />
                                <span>Las alertas por email están activas. Recibirás un recordatorio 30 días antes de cada plazo.</span>
                            </div>
                        )}
                    </section>
                    </>
                )}
            </div>
        </div>
    )
}
