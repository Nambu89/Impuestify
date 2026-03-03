import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Shield, CheckCircle, CreditCard, Calculator, ArrowLeft, Loader, AlertCircle } from 'lucide-react'
import { useSubscription } from '../hooks/useSubscription'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'
import './SubscribePage.css'

export default function SubscribePage() {
    const { isAuthenticated } = useAuth()
    const { hasAccess, loading, createCheckout, error } = useSubscription()
    const [isRedirecting, setIsRedirecting] = useState(false)
    const [searchParams] = useSearchParams()
    const canceled = searchParams.get('canceled') === 'true'

    useEffect(() => {
        if (hasAccess && !loading) {
            window.location.href = '/chat'
        }
    }, [hasAccess, loading])

    const handleCheckout = async () => {
        setIsRedirecting(true)
        try {
            await createCheckout()
        } catch {
            setIsRedirecting(false)
        }
    }

    if (loading) {
        return (
            <div className="subscribe-page">
                <Header />
                <div className="subscribe-loading">
                    <Loader size={32} className="animate-spin" />
                    <p>Cargando...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="subscribe-page">
            <Header />

            <div className="subscribe-container">
                <Link to="/" className="back-link">
                    <ArrowLeft size={16} />
                    Volver al inicio
                </Link>

                {canceled && (
                    <div className="subscribe-alert">
                        <AlertCircle size={20} />
                        <span>El proceso de pago fue cancelado. Puedes intentarlo de nuevo cuando quieras.</span>
                    </div>
                )}

                {error && (
                    <div className="subscribe-alert subscribe-alert-error">
                        <AlertCircle size={20} />
                        <span>{error}</span>
                    </div>
                )}

                <div className="subscribe-header">
                    <div className="subscribe-badge">
                        <Shield size={16} />
                        <span>Plan Particular</span>
                    </div>
                    <h1>Tu asesor fiscal inteligente</h1>
                    <p className="subscribe-subtitle">
                        Accede a todas las funcionalidades de Impuestify con un plan adaptado a trabajadores por cuenta ajena.
                    </p>
                </div>

                <div className="subscribe-card">
                    <div className="subscribe-price">
                        <div className="subscribe-price-icon">
                            <Calculator size={32} />
                        </div>
                        <div className="subscribe-price-amount">
                            <span className="subscribe-price-currency">EUR</span>
                            <span className="subscribe-price-value">15</span>
                            <span className="subscribe-price-period">/mes</span>
                        </div>
                    </div>

                    <ul className="subscribe-features">
                        <li>
                            <CheckCircle size={18} />
                            <span>Consultas fiscales ilimitadas con IA</span>
                        </li>
                        <li>
                            <CheckCircle size={18} />
                            <span>Analisis de nominas (PDF)</span>
                        </li>
                        <li>
                            <CheckCircle size={18} />
                            <span>Calculo de IRPF por comunidad autonoma</span>
                        </li>
                        <li>
                            <CheckCircle size={18} />
                            <span>Analisis de notificaciones AEAT</span>
                        </li>
                        <li>
                            <CheckCircle size={18} />
                            <span>Workspace personal de documentos</span>
                        </li>
                        <li>
                            <CheckCircle size={18} />
                            <span>Fuentes oficiales citadas</span>
                        </li>
                    </ul>

                    {isAuthenticated ? (
                        <button
                            onClick={handleCheckout}
                            className="btn btn-primary btn-lg subscribe-cta"
                            disabled={isRedirecting}
                        >
                            {isRedirecting ? (
                                <>
                                    <Loader size={20} className="animate-spin" />
                                    Redirigiendo a Stripe...
                                </>
                            ) : (
                                <>
                                    <CreditCard size={20} />
                                    Suscribirme ahora
                                </>
                            )}
                        </button>
                    ) : (
                        <Link to="/register" className="btn btn-primary btn-lg subscribe-cta">
                            Crear cuenta para suscribirme
                        </Link>
                    )}

                    <p className="subscribe-note">
                        Pago seguro con Stripe. Cancela cuando quieras.
                    </p>
                </div>

                <p className="subscribe-autonomos">
                    ¿Eres autonomo o profesional por cuenta propia?{' '}
                    <Link to="/contact?type=autonomo">Solicita informacion sobre planes especializados</Link>
                </p>
            </div>
        </div>
    )
}
