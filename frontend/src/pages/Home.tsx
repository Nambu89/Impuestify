import { Link } from 'react-router-dom'
import { MessageSquare, Shield, FileText, ArrowRight } from 'lucide-react'
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
                            <span>Powered by Azure AI</span>
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
                                        Empezar Gratis
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
                            <p>Tus datos están protegidos. No almacenamos información personal sensible.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* About TaxIA Section */}
            <section className="about">
                <div className="container">
                    <h2 className="section-title">Sobre Impuestify</h2>
                    <div className="about-content">
                        <p>
                            Impuestify utiliza tecnología <strong>RAG (Retrieval-Augmented Generation)</strong> para
                            proporcionar respuestas precisas basadas en documentación oficial de la AEAT.
                        </p>
                        <p>
                            Nuestro sistema combina inteligencia artificial avanzada con una base de conocimiento
                            actualizada de normativa tributaria española, garantizando respuestas fiables y
                            contextualizadas a tus consultas fiscales.
                        </p>
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="cta">
                <div className="container">
                    <div className="cta-card">
                        <h2>¿Listo para simplificar tu fiscalidad?</h2>
                        <p>Únete a miles de usuarios que ya confían en Impuestify</p>
                        <Link to="/register" className="btn btn-primary btn-lg">
                            Crear Cuenta Gratis
                            <ArrowRight size={20} />
                        </Link>
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="footer">
                <div className="container">
                    <p>© 2025 Impuestify. Información orientativa, no sustituye asesoramiento profesional.</p>
                </div>
            </footer>
        </div>
    )
}
