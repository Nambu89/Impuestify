import { Link } from 'react-router-dom'
import {
    MessageSquare, Shield, FileText, ArrowRight, Calculator, CreditCard,
    CheckCircle, X, Users, Cpu, Search, Lock, Map, Zap, ExternalLink, CalendarDays, Video
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import Header from '../components/Header'
import GradientText from '../components/reactbits/GradientText'
import SpotlightCard from '../components/reactbits/SpotlightCard'
import CountUp from '../components/reactbits/CountUp'
import FadeContent from '../components/reactbits/FadeContent'
import StarBorder from '../components/reactbits/StarBorder'
import InteractiveSpainMap from '../components/InteractiveSpainMap'
import UpcomingDeadlines from '../components/UpcomingDeadlines'
import './Home.css'

const TERRITORIES = [
    { name: 'Andalucía', foral: false, link: null },
    { name: 'Aragón', foral: false, link: null },
    { name: 'Asturias', foral: false, link: null },
    { name: 'Baleares', foral: false, link: null },
    { name: 'Canarias', foral: false, link: '/canarias' },
    { name: 'Cantabria', foral: false, link: null },
    { name: 'Castilla-La Mancha', foral: false, link: null },
    { name: 'Castilla y León', foral: false, link: null },
    { name: 'Cataluña', foral: false, link: null },
    { name: 'C. Valenciana', foral: false, link: null },
    { name: 'Extremadura', foral: false, link: null },
    { name: 'Galicia', foral: false, link: null },
    { name: 'Madrid', foral: false, link: null },
    { name: 'Murcia', foral: false, link: null },
    { name: 'La Rioja', foral: false, link: null },
    { name: 'Ceuta', foral: false, link: '/ceuta-melilla' },
    { name: 'Melilla', foral: false, link: '/ceuta-melilla' },
    { name: 'Araba', foral: true, link: '/territorios-forales' },
    { name: 'Bizkaia', foral: true, link: '/territorios-forales' },
    { name: 'Gipuzkoa', foral: true, link: '/territorios-forales' },
    { name: 'Navarra', foral: true, link: '/territorios-forales' },
]

export default function Home() {
    const { isAuthenticated } = useAuth()

    return (
        <div className="home">
            <Header />

            {/* Hero Section — centered text */}
            <section className="hero">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="hero-badge">
                            <Cpu size={16} />
                            <span>IA Fiscal Multi-Agente</span>
                        </div>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <h1 className="hero-title">
                            Tu Asistente Fiscal{' '}
                            <GradientText
                                colors={['#1a56db', '#06b6d4', '#3b82f6', '#1a56db']}
                                animationSpeed={6}
                                className="hero-gradient"
                            >
                                Inteligente
                            </GradientText>
                        </h1>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <p className="hero-subtitle">
                            El único asistente fiscal con IA que cubre todas las comunidades autónomas,
                            incluyendo los territorios forales del País Vasco y Navarra.
                        </p>
                    </FadeContent>
                    <FadeContent delay={300} duration={600}>
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
                    </FadeContent>
                </div>
            </section>

            {/* Interactive Map Section — full width */}
            <section className="map-section">
                <div className="container">
                    <FadeContent delay={0} duration={800}>
                        <InteractiveSpainMap />
                    </FadeContent>
                </div>
            </section>

            {/* Value Proposition — Quantified Savings */}
            <section className="savings">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Ahorra en tu declaración de la renta</h2>
                        <p className="section-subtitle">La mayoría de contribuyentes desconoce deducciones a las que tiene derecho</p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="savings-grid">
                            <div className="savings-card">
                                <span className="savings-card__amount">
                                    <CountUp to={847} separator="." duration={2.5} /> EUR
                                </span>
                                <span className="savings-card__label">Ahorro medio descubierto por usuario</span>
                                <span className="savings-card__detail">En deducciones autonómicas no aplicadas</span>
                            </div>
                            <div className="savings-card">
                                <span className="savings-card__amount">
                                    <CountUp to={3} duration={1.5} /> min
                                </span>
                                <span className="savings-card__label">Tiempo medio de consulta</span>
                                <span className="savings-card__detail">vs 45 min de media con un asesor fiscal</span>
                            </div>
                            <div className="savings-card">
                                <span className="savings-card__amount">
                                    5 EUR<span className="savings-card__period">/mes</span>
                                </span>
                                <span className="savings-card__label">vs 150-300 EUR de una asesoría</span>
                                <span className="savings-card__detail">Ahorra hasta un 97% en asesoramiento fiscal</span>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Stats Section */}
            <section className="stats">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="stats-grid">
                            <div className="stat-item">
                                <span className="stat-number">
                                    <CountUp to={428} separator="." duration={2.5} />
                                    <span>+</span>
                                </span>
                                <span className="stat-label">Documentos oficiales</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-number">
                                    <CountUp to={128} duration={2} />
                                </span>
                                <span className="stat-label">Deducciones fiscales</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-number">
                                    <CountUp to={21} duration={2} />
                                </span>
                                <span className="stat-label">Territorios cubiertos</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-number">24/7</span>
                                <span className="stat-label">Disponibilidad</span>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Territorial Coverage Section */}
            <section className="coverage">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Cobertura fiscal completa de toda España</h2>
                        <p className="section-subtitle">Incluidas las comunidades con sistema fiscal propio</p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="territory-grid">
                            {TERRITORIES.map((t) => {
                                const chipContent = (
                                    <>
                                        {t.foral && <Map size={14} />}
                                        {t.link && !t.foral && <ExternalLink size={12} />}
                                        {t.name}
                                    </>
                                )
                                return t.link ? (
                                    <Link
                                        key={t.name}
                                        to={t.link}
                                        className={`territory-chip ${t.foral ? 'territory-foral' : ''} territory-chip--linked`}
                                    >
                                        {chipContent}
                                    </Link>
                                ) : (
                                    <div
                                        key={t.name}
                                        className={`territory-chip ${t.foral ? 'territory-foral' : ''}`}
                                    >
                                        {chipContent}
                                    </div>
                                )
                            })}
                        </div>
                    </FadeContent>
                    <FadeContent delay={200} duration={500}>
                        <p className="coverage-note">
                            Somos el único asistente fiscal con IA que integra las normativas forales
                            del País Vasco y Navarra, con sus deducciones propias que no existen en el régimen común.
                        </p>
                    </FadeContent>
                </div>
            </section>

            {/* Comparison Section */}
            <section className="comparison">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">¿Por qué nuestra IA es diferente?</h2>
                    </FadeContent>
                    <div className="comparison-grid">
                        <FadeContent delay={100} duration={500}>
                            <div className="comparison-col comparison-generic">
                                <h3 className="comparison-title">
                                    <MessageSquare size={20} />
                                    Asistentes genéricos
                                </h3>
                                <ul className="comparison-list">
                                    <li><X size={16} className="comparison-icon-no" /> Chatbot genérico sin fuentes verificadas</li>
                                    <li><X size={16} className="comparison-icon-no" /> Sin análisis de documentos</li>
                                    <li><X size={16} className="comparison-icon-no" /> Sin cobertura de territorios forales</li>
                                    <li><X size={16} className="comparison-icon-no" /> Respuestas genéricas sin personalización</li>
                                    <li><X size={16} className="comparison-icon-no" /> Sin protección de datos con IA</li>
                                </ul>
                            </div>
                        </FadeContent>
                        <FadeContent delay={200} duration={500}>
                            <SpotlightCard className="comparison-col comparison-impuestify" spotlightColor="rgba(26, 86, 219, 0.12)">
                                <h3 className="comparison-title comparison-title-highlight">
                                    <Zap size={20} />
                                    Impuestify
                                </h3>
                                <ul className="comparison-list">
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> Sistema multi-agente especializado</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> RAG sobre 428+ documentos oficiales con citas legales</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> 17 CCAA + territorios forales + Ceuta/Melilla</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> Motor de 128 deducciones personalizadas</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> Guardrails IA: moderación, anti-inyección, filtrado PII</li>
                                </ul>
                            </SpotlightCard>
                        </FadeContent>
                    </div>
                </div>
            </section>

            {/* Features Section */}
            <section className="features">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Tecnología de vanguardia</h2>
                    </FadeContent>
                    <div className="features-grid">
                        <FadeContent delay={100} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(26, 86, 219, 0.1)">
                                <div className="feature-icon">
                                    <Users size={28} />
                                </div>
                                <h3>IA Multi-Agente</h3>
                                <p>Agentes especializados en fiscal, nóminas, notificaciones AEAT y gestión documental.</p>
                            </SpotlightCard>
                        </FadeContent>
                        <FadeContent delay={200} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(6, 182, 212, 0.1)">
                                <div className="feature-icon">
                                    <Search size={28} />
                                </div>
                                <h3>428+ Documentos Oficiales</h3>
                                <p>RAG sobre normativa real de AEAT, BOE y Diputaciones Forales. Cada respuesta cita su fuente.</p>
                            </SpotlightCard>
                        </FadeContent>
                        <FadeContent delay={300} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(16, 185, 129, 0.1)">
                                <div className="feature-icon">
                                    <Lock size={28} />
                                </div>
                                <h3>Seguro y Privado</h3>
                                <p>Guardrails IA: moderación de contenido, detección de inyección y filtrado de datos personales. RGPD compliant.</p>
                            </SpotlightCard>
                        </FadeContent>
                    </div>
                </div>
            </section>

            {/* Pricing Section */}
            <section className="pricing">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Planes y precios</h2>
                        <p className="section-subtitle">Sin permanencia. Cancela cuando quieras.</p>
                    </FadeContent>
                    <FadeContent delay={100} duration={500}>
                        <div className="pricing-grid">
                            {/* Particular */}
                            <div className="pricing-card">
                                <div className="pricing-header">
                                    <div className="pricing-icon">
                                        <Calculator size={32} />
                                    </div>
                                    <div>
                                        <h3 className="pricing-plan-name">Particular</h3>
                                        <p className="pricing-plan-desc">Para trabajadores por cuenta ajena</p>
                                    </div>
                                </div>
                                <div className="pricing-amount">
                                    <span className="pricing-currency">EUR</span>
                                    <span className="pricing-value">5</span>
                                    <span className="pricing-period">/mes</span>
                                </div>
                                <ul className="pricing-features">
                                    <li><CheckCircle size={18} /><span>Consultas fiscales ilimitadas con IA</span></li>
                                    <li><CheckCircle size={18} /><span>Motor de 128 deducciones personalizadas</span></li>
                                    <li><CheckCircle size={18} /><span>Cobertura completa: 17 CCAA + forales</span></li>
                                    <li><CheckCircle size={18} /><span>Análisis de nóminas y notificaciones AEAT</span></li>
                                    <li><CheckCircle size={18} /><span>Informe IRPF exportable en PDF</span></li>
                                    <li><CheckCircle size={18} /><span>Criptomonedas, trading y apuestas (FIFO)</span></li>
                                </ul>
                                <Link to="/register" className="btn btn-secondary btn-lg pricing-cta">
                                    <CreditCard size={20} />
                                    Comenzar
                                </Link>
                            </div>

                            {/* Creator */}
                            <div className="pricing-card pricing-card--creator">
                                <div className="pricing-badge pricing-badge--creator">
                                    <Zap size={13} />
                                    Oferta 2026
                                </div>
                                <div className="pricing-header">
                                    <div className="pricing-icon pricing-icon--creator">
                                        <Video size={32} />
                                    </div>
                                    <div>
                                        <h3 className="pricing-plan-name">Creator</h3>
                                        <p className="pricing-plan-desc">Para creadores de contenido e influencers</p>
                                    </div>
                                </div>
                                <div className="pricing-amount">
                                    <span className="pricing-currency">EUR</span>
                                    <span className="pricing-value pricing-value--creator">30</span>
                                    <span className="pricing-period">/mes</span>
                                </div>
                                <ul className="pricing-features">
                                    <li><CheckCircle size={18} className="pricing-check--creator" /><span>Todo lo del plan Particular</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--creator" /><span>Simulador IRPF con royalties y derechos de autor</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--creator" /><span>IVA por plataforma (YouTube, TikTok, Twitch)</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--creator" /><span>Epígrafe IAE para creadores</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--creator" /><span>Modelo 349 — operaciones intracomunitarias</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--creator" /><span>Asistente IA especializado en creadores</span></li>
                                </ul>
                                <Link to="/subscribe" className="btn btn-lg pricing-cta pricing-cta--creator">
                                    <CreditCard size={20} />
                                    Empezar como Creator
                                </Link>
                            </div>
                        </div>
                        <p className="pricing-autonomos">
                            ¿Eres autónomo o profesional por cuenta propia?{' '}
                            <Link to="/subscribe">Ver plan Autónomo — 39 €/mes</Link>
                        </p>
                        <p className="pricing-note pricing-note--center">
                            Pago seguro con Stripe. Sin permanencia, cancela cuando quieras.
                        </p>
                    </FadeContent>
                </div>
            </section>

            {/* Upcoming Deadlines Section */}
            <section className="home-deadlines">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="home-deadlines__header">
                            <CalendarDays size={24} />
                            <h2 className="section-title">Próximos plazos fiscales</h2>
                        </div>
                        <p className="section-subtitle">
                            No te pierdas ninguna fecha clave de la AEAT
                        </p>
                    </FadeContent>
                    <FadeContent delay={150} duration={500}>
                        <UpcomingDeadlines isPublic={true} maxItems={4} />
                        <div className="home-deadlines__cta">
                            <Link to="/login" className="btn btn-ghost btn-sm">
                                Ver calendario completo con tu perfil
                                <ArrowRight size={16} />
                            </Link>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* CTA Section */}
            <section className="cta">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <StarBorder color="#1a56db" speed="8s" className="cta-star-border">
                            <div className="cta-card">
                                <h2>¿Listo para simplificar tu fiscalidad?</h2>
                                <p>Tu asesor fiscal con IA, disponible 24/7</p>
                                <Link to="/register" className="btn btn-primary btn-lg">
                                    Crear Cuenta
                                    <ArrowRight size={20} />
                                </Link>
                            </div>
                        </StarBorder>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
