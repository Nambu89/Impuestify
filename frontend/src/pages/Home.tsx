import { Link } from 'react-router-dom'
import { MessageSquare, Shield, FileText, ArrowRight, Calculator, CreditCard, CheckCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'
import './Home.css'

export default function Home() {
    const { isAuthenticated } = useAuth()

    return (
        <div className="home">
            <Header />

            {/* Hero Section */}
            <section className="hero">
                <div className="container">
                    <div className="hero-content">
                        <div className="hero-badge">
                            <Shield size={16} />
                            <span>Powered by OpenAI</span>
                        </div>
                        <h1 className="hero-title">
                            Tu Asistente Fiscal
                            <span className="gradient-text"> Inteligente</span>
                        </h1>
                        <p className="hero-subtitle">
                            Resuelve tus dudas fiscales al instante con la ayuda de IA avanzada.
                            Basado en documentación oficial de la AEAT.
                        </p>
                        <div className="hero-actions">
                            {isAuthenticated ? (
                                <Link to="/chat" className="btn btn-primary btn-lg">
                                    Ir al Chat
                                    <ArrowRight size={20} />
                                </Link>
                            ) : (
                                <>
                                    <Link to="/register" className="btn btn-primary btn-lg">
                                        Empezar Ahora
                                        <ArrowRight size={20} />
                                    </Link>
                                    <Link to="/login" className="btn btn-secondary btn-lg">
                                        Iniciar Sesión
                                    </Link>
                                </>
                            )}
                        </div>
                    </div>

                    <div className="hero-visual">
                        <div className="chat-preview">
                            <div className="chat-message user">
                                <p>¿Cuándo debo presentar el modelo 303?</p>
                            </div>
                            <div className="chat-message assistant">
                                <p>El modelo 303 de IVA se presenta trimestralmente...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="features">
                <div className="container">
                    <h2 className="section-title">¿Por qué Impuestify?</h2>
                    <div className="features-grid">
                        <div className="feature-card">
                            <div className="feature-icon">
                                <MessageSquare size={28} />
                            </div>
                            <h3>Respuestas Instantáneas</h3>
                            <p>Obtén respuestas precisas a tus consultas fiscales en segundos, no en horas.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon">
                                <FileText size={28} />
                            </div>
                            <h3>Fuentes Oficiales</h3>
                            <p>Basado en documentación oficial de la AEAT y normativa tributaria española.</p>
                        </div>
                        <div className="feature-card">
                            <div className="feature-icon">
                                <Shield size={28} />
                            </div>
                            <h3>Seguro y Privado</h3>
                            <p>Tus datos están protegidos. Cumplimiento RGPD, AI Act y LOPDGDD.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Pricing Section */}
            <section className="pricing">
                <div className="container">
                    <h2 className="section-title">Plan Particular</h2>
                    <p className="section-subtitle">Para trabajadores por cuenta ajena</p>
                    <div className="pricing-card">
                        <div className="pricing-header">
                            <div className="pricing-icon">
                                <Calculator size={32} />
                            </div>
                            <div className="pricing-amount">
                                <span className="pricing-currency">EUR</span>
                                <span className="pricing-value">15</span>
                                <span className="pricing-period">/mes</span>
                            </div>
                        </div>
                        <ul className="pricing-features">
                            <li>
                                <CheckCircle size={18} />
                                <span>Consultas fiscales ilimitadas con IA</span>
                            </li>
                            <li>
                                <CheckCircle size={18} />
                                <span>Análisis de nóminas (PDF)</span>
                            </li>
                            <li>
                                <CheckCircle size={18} />
                                <span>Cálculo de IRPF por comunidad autónoma</span>
                            </li>
                            <li>
                                <CheckCircle size={18} />
                                <span>Análisis de notificaciones AEAT</span>
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
                        <Link to="/register" className="btn btn-primary btn-lg pricing-cta">
                            <CreditCard size={20} />
                            Comenzar
                        </Link>
                        <p className="pricing-note">
                            Pago seguro con Stripe. Cancela cuando quieras.
                        </p>
                    </div>
                    <p className="pricing-autonomos">
                        ¿Eres autónomo o profesional por cuenta propia?{' '}
                        <Link to="/contact?type=autonomo">Solicita información sobre planes especializados</Link>
                    </p>
                </div>
            </section>

            {/* CTA Section */}
            <section className="cta">
                <div className="container">
                    <div className="cta-card">
                        <h2>¿Listo para simplificar tu fiscalidad?</h2>
                        <p>Tu asesor fiscal con IA, disponible 24/7</p>
                        <Link to="/register" className="btn btn-primary btn-lg">
                            Crear Cuenta
                            <ArrowRight size={20} />
                        </Link>
                    </div>
                </div>
            </section>
        </div>
    )
}
