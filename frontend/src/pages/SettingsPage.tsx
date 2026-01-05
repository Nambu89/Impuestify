import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, Download, Trash2, Save, AlertCircle, CheckCircle, Loader, Shield } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'
import './SettingsPage.css'

export default function SettingsPage() {
    const { user, logout } = useAuth()
    const navigate = useNavigate()

    // Form state
    const [name, setName] = useState('')
    const [email, setEmail] = useState('')

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

    // Auto-dismiss messages
    useEffect(() => {
        if (message) {
            const timer = setTimeout(() => setMessage(null), 5000)
            return () => clearTimeout(timer)
        }
    }, [message])

    // Update profile
    const handleUpdateProfile = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsLoading(true)
        setMessage(null)

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/users/me`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ name, email })
            })

            if (!response.ok) {
                const error = await response.json()
                throw new Error(error.detail || 'Error al actualizar perfil')
            }

            await response.json() // Parse response but don't store (user context will refresh)
            setMessage({ type: 'success', text: '✅ Perfil actualizado correctamente' })

            // Update local user state if needed
            // Note: You may want to implement a refresh user context here
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message })
        } finally {
            setIsLoading(false)
        }
    }

    // Export user data
    const handleExportData = async () => {
        setIsExporting(true)
        setMessage(null)

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/users/me/data`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (!response.ok) {
                throw new Error('Error al exportar datos')
            }

            const data = await response.json()

            // Create and download JSON file
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `impuestify-mis-datos-${new Date().toISOString().split('T')[0]}.json`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)

            setMessage({ type: 'success', text: '✅ Datos exportados correctamente' })
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message })
        } finally {
            setIsExporting(false)
        }
    }

    // Delete account
    const handleDeleteAccount = async () => {
        const confirmed = window.confirm(
            '⚠️ ATENCIÓN: Esta acción es IRREVERSIBLE.\\n\\n' +
            'Se eliminarán permanentemente:\\n' +
            '• Tu cuenta de usuario\\n' +
            '• Todas tus conversaciones\\n' +
            '• Todos los mensajes\\n\\n' +
            '¿Estás seguro de que deseas continuar?'
        )

        if (!confirmed) return

        // Second confirmation
        const doubleConfirm = window.confirm(
            '⚠️ ÚLTIMA CONFIRMACIÓN\\n\\n' +
            'Escribe "ELIMINAR" mentalmente y confirma.\\n\\n' +
            '¿Proceder con la eliminación permanente?'
        )

        if (!doubleConfirm) return

        setIsLoading(true)
        setMessage(null)

        try {
            const token = localStorage.getItem('token')
            const response = await fetch(`${import.meta.env.VITE_API_URL}/api/users/me`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })

            if (!response.ok) {
                throw new Error('Error al eliminar cuenta')
            }

            // Logout and redirect
            logout()
            navigate('/', { replace: true })

            // Show final message (won't be seen on current page)
            alert('✅ Tu cuenta ha sido eliminada permanentemente.')
        } catch (error: any) {
            setMessage({ type: 'error', text: error.message })
            setIsLoading(false)
        }
    }

    return (
        <div className="settings-page">
            <Header />

            <div className="settings-container">
                <div className="settings-header">
                    <h1>
                        <Shield size={32} />
                        Configuración de Cuenta
                    </h1>
                    <p className="settings-subtitle">
                        Gestiona tu perfil y tus derechos de protección de datos (RGPD)
                    </p>
                </div>

                {/* Message Banner */}
                {message && (
                    <div className={`message-banner ${message.type}`}>
                        {message.type === 'success' ? (
                            <CheckCircle size={20} />
                        ) : (
                            <AlertCircle size={20} />
                        )}
                        <span>{message.text}</span>
                    </div>
                )}

                {/* Profile Section */}
                <section className="settings-section">
                    <div className="section-header">
                        <User size={24} />
                        <h2>Información del Perfil</h2>
                    </div>

                    <form onSubmit={handleUpdateProfile} className="settings-form">
                        <div className="form-group">
                            <label htmlFor="name">Nombre</label>
                            <input
                                type="text"
                                id="name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Tu nombre"
                                className="form-input"
                            />
                        </div>

                        <div className="form-group">
                            <label htmlFor="email">Email</label>
                            <input
                                type="email"
                                id="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="tu@email.com"
                                className="form-input"
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <>
                                    <Loader size={18} className="animate-spin" />
                                    Guardando...
                                </>
                            ) : (
                                <>
                                    <Save size={18} />
                                    Guardar Cambios
                                </>
                            )}
                        </button>
                    </form>
                </section>

                {/* GDPR Data Rights Section */}
                <section className="settings-section">
                    <div className="section-header">
                        <Shield size={24} />
                        <h2>Tus Derechos RGPD</h2>
                    </div>

                    <p className="section-description">
                        De acuerdo con el Reglamento General de Protección de Datos (RGPD),
                        tienes derecho a acceder, rectificar y eliminar tus datos personales.
                    </p>

                    {/* Export Data */}
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
                        <button
                            onClick={handleExportData}
                            className="btn btn-secondary"
                            disabled={isExporting}
                        >
                            {isExporting ? (
                                <>
                                    <Loader size={18} className="animate-spin" />
                                    Exportando...
                                </>
                            ) : (
                                <>
                                    <Download size={18} />
                                    Exportar Datos
                                </>
                            )}
                        </button>
                    </div>
                </section>

                {/* Danger Zone */}
                <section className="settings-section danger-zone">
                    <div className="section-header">
                        <AlertCircle size={24} />
                        <h2>Zona Peligrosa</h2>
                    </div>

                    <p className="section-description danger-text">
                        ⚠️ Las acciones en esta sección son <strong>irreversibles</strong>.
                        Procede con precaución.
                    </p>

                    {/* Delete Account */}
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
                                <li>❌ Tu cuenta de usuario</li>
                                <li>❌ Todas tus conversaciones</li>
                                <li>❌ Todos tus mensajes</li>
                                <li>❌ Esta acción NO se puede deshacer</li>
                            </ul>
                        </div>
                        <button
                            onClick={handleDeleteAccount}
                            className="btn btn-danger"
                            disabled={isLoading}
                        >
                            <Trash2 size={18} />
                            Eliminar Cuenta
                        </button>
                    </div>
                </section>
            </div>
        </div>
    )
}
