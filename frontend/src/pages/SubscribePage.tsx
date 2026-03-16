import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
    Shield, CheckCircle, CreditCard, Calculator, ArrowLeft,
    Loader, AlertCircle, Briefcase, X, Zap, Video
} from 'lucide-react'
import { useSubscription } from '../hooks/useSubscription'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'
import './SubscribePage.css'

const PLAN_PARTICULAR = {
    id: 'particular',
    name: 'Particular',
    price: 5,
    icon: Calculator,
    description: 'Para trabajadores por cuenta ajena',
    features: [
        'Consultas fiscales ilimitadas con IA',
        'Análisis de nóminas (PDF)',
        'Cálculo de IRPF por comunidad autónoma',
        'Análisis de notificaciones AEAT',
        'Workspace personal de documentos',
        'Fuentes oficiales citadas',
        'Informe IRPF exportable en PDF',
        'Criptomonedas, trading y apuestas (FIFO)',
    ],
    notIncluded: [
        'Cálculo cuota autónomos (RETA)',
        'IVA trimestral (Modelo 303)',
        'Pago fraccionado IRPF (Modelo 130)',
        'Retenciones en facturas',
    ],
}

const PLAN_CREATOR = {
    id: 'creator',
    name: 'Creator',
    price: 49,
    icon: Video,
    description: 'Para creadores de contenido e influencers',
    features: [
        'Todo lo del plan Particular',
        'Simulador IRPF completo con royalties y derechos de autor',
        'Calculadora IVA por plataforma (YouTube, TikTok, Twitch)',
        'Búsqueda de epígrafe IAE para creadores de contenido',
        'Modelo 349 — operaciones intracomunitarias',
        'Asistente IA especializado en fiscalidad de creadores',
        'Cobertura forales + Canarias + Ceuta/Melilla',
        'Workspaces con contexto IA aislado',
    ],
    notIncluded: [],
}

const PLAN_AUTONOMO = {
    id: 'autonomo',
    name: 'Autónomo',
    price: 39,
    icon: Briefcase,
    description: 'Para autónomos y profesionales',
    popular: true,
    features: [
        'Todo lo del plan Particular',
        'Cálculo cuota autónomos (RETA)',
        'IVA trimestral — Modelo 303',
        'Pago fraccionado IRPF — Modelo 130',
        'Retenciones IRPF en facturas',
        'Deducciones específicas de autónomos',
        'Workspaces con contexto IA aislado',
        'Cobertura foral completa (País Vasco + Navarra)',
        'Simulación IRPF con gastos deducibles',
        'Criptomonedas, trading y apuestas (FIFO)',
    ],
    notIncluded: [],
}

export default function SubscribePage() {
    const { isAuthenticated } = useAuth()
    const { hasAccess, loading, createCheckout, error } = useSubscription()
    const [isRedirecting, setIsRedirecting] = useState(false)
    const [selectedPlan, setSelectedPlan] = useState<string | null>(null)
    const [searchParams] = useSearchParams()
    const canceled = searchParams.get('canceled') === 'true'
    const planParam = searchParams.get('plan')

    useEffect(() => {
        if (hasAccess && !loading) {
            window.location.href = '/chat'
        }
    }, [hasAccess, loading])

    const handleCheckout = async (planType: string) => {
        setIsRedirecting(true)
        setSelectedPlan(planType)
        try {
            await createCheckout(planType)
        } catch {
            setIsRedirecting(false)
            setSelectedPlan(null)
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
                    <h1>Elige tu plan</h1>
                    <p className="subscribe-subtitle">
                        El único asistente fiscal con IA que cubre todos los territorios de España,
                        incluidos los forales.
                    </p>
                </div>

                <div className="subscribe-plans subscribe-plans--three">
                    {/* Plan Particular */}
                    <div className="subscribe-plan">
                        <div className="subscribe-plan__header">
                            <div className="subscribe-plan__icon">
                                <Calculator size={28} />
                            </div>
                            <h2>{PLAN_PARTICULAR.name}</h2>
                            <p className="subscribe-plan__desc">{PLAN_PARTICULAR.description}</p>
                        </div>

                        <div className="subscribe-plan__price">
                            <span className="subscribe-plan__currency">EUR</span>
                            <span className="subscribe-plan__value">{PLAN_PARTICULAR.price}</span>
                            <span className="subscribe-plan__period">/mes</span>
                        </div>

                        <ul className="subscribe-plan__features">
                            {PLAN_PARTICULAR.features.map((f) => (
                                <li key={f}>
                                    <CheckCircle size={16} className="subscribe-plan__icon-yes" />
                                    <span>{f}</span>
                                </li>
                            ))}
                            {PLAN_PARTICULAR.notIncluded.map((f) => (
                                <li key={f} className="subscribe-plan__not-included">
                                    <X size={16} className="subscribe-plan__icon-no" />
                                    <span>{f}</span>
                                </li>
                            ))}
                        </ul>

                        {isAuthenticated ? (
                            <button
                                onClick={() => handleCheckout('particular')}
                                className="btn btn-secondary btn-lg subscribe-plan__cta"
                                disabled={isRedirecting}
                            >
                                {isRedirecting && selectedPlan === 'particular' ? (
                                    <>
                                        <Loader size={18} className="animate-spin" />
                                        Redirigiendo...
                                    </>
                                ) : (
                                    <>
                                        <CreditCard size={18} />
                                        Suscribirme
                                    </>
                                )}
                            </button>
                        ) : (
                            <Link to="/register" className="btn btn-secondary btn-lg subscribe-plan__cta">
                                Crear cuenta
                            </Link>
                        )}
                    </div>

                    {/* Plan Creator */}
                    <div className="subscribe-plan subscribe-plan--creator">
                        <div className="subscribe-plan__badge subscribe-plan__badge--creator">
                            <Zap size={14} />
                            Oferta 2026
                        </div>
                        <div className="subscribe-plan__header">
                            <div className="subscribe-plan__icon">
                                <Video size={28} />
                            </div>
                            <h2>{PLAN_CREATOR.name}</h2>
                            <p className="subscribe-plan__desc">{PLAN_CREATOR.description}</p>
                        </div>

                        <div className="subscribe-plan__price">
                            <span className="subscribe-plan__currency">EUR</span>
                            <span className="subscribe-plan__value subscribe-plan__value--creator">{PLAN_CREATOR.price}</span>
                            <span className="subscribe-plan__period">/mes</span>
                        </div>

                        <ul className="subscribe-plan__features">
                            {PLAN_CREATOR.features.map((f) => (
                                <li key={f}>
                                    <CheckCircle size={16} className="subscribe-plan__icon-yes subscribe-plan__icon-yes--creator" />
                                    <span>{f}</span>
                                </li>
                            ))}
                        </ul>

                        {isAuthenticated ? (
                            <button
                                onClick={() => handleCheckout('creator')}
                                className="btn btn-lg subscribe-plan__cta subscribe-plan__cta--creator"
                                disabled={isRedirecting}
                            >
                                {isRedirecting && selectedPlan === 'creator' ? (
                                    <>
                                        <Loader size={18} className="animate-spin" />
                                        Redirigiendo a Stripe...
                                    </>
                                ) : (
                                    <>
                                        <CreditCard size={18} />
                                        Empezar como Creator
                                    </>
                                )}
                            </button>
                        ) : (
                            <Link to="/register?plan=creator" className="btn btn-lg subscribe-plan__cta subscribe-plan__cta--creator">
                                Crear cuenta
                            </Link>
                        )}
                    </div>

                    {/* Plan Autónomo */}
                    <div className="subscribe-plan subscribe-plan--popular">
                        <div className="subscribe-plan__badge">
                            <Zap size={14} />
                            Más completo
                        </div>
                        <div className="subscribe-plan__header">
                            <div className="subscribe-plan__icon">
                                <Briefcase size={28} />
                            </div>
                            <h2>{PLAN_AUTONOMO.name}</h2>
                            <p className="subscribe-plan__desc">{PLAN_AUTONOMO.description}</p>
                        </div>

                        <div className="subscribe-plan__price">
                            <span className="subscribe-plan__currency">EUR</span>
                            <span className="subscribe-plan__value">{PLAN_AUTONOMO.price}</span>
                            <span className="subscribe-plan__period">/mes (IVA incl.)</span>
                        </div>

                        <ul className="subscribe-plan__features">
                            {PLAN_AUTONOMO.features.map((f) => (
                                <li key={f}>
                                    <CheckCircle size={16} className="subscribe-plan__icon-yes" />
                                    <span>{f}</span>
                                </li>
                            ))}
                        </ul>

                        {isAuthenticated ? (
                            <button
                                onClick={() => handleCheckout('autonomo')}
                                className="btn btn-primary btn-lg subscribe-plan__cta"
                                disabled={isRedirecting}
                            >
                                {isRedirecting && selectedPlan === 'autonomo' ? (
                                    <>
                                        <Loader size={18} className="animate-spin" />
                                        Redirigiendo a Stripe...
                                    </>
                                ) : (
                                    <>
                                        <CreditCard size={18} />
                                        Suscribirme al plan Autónomo
                                    </>
                                )}
                            </button>
                        ) : (
                            <Link to="/register?plan=autonomo" className="btn btn-primary btn-lg subscribe-plan__cta">
                                Crear cuenta
                            </Link>
                        )}
                    </div>
                </div>

                <p className="subscribe-note-bottom">
                    Pago seguro con Stripe. Sin permanencia, cancela cuando quieras.
                </p>
            </div>
        </div>
    )
}
