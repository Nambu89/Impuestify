import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
    MessageSquare, Shield, FileText, ArrowRight, Calculator, CreditCard,
    CheckCircle, X, Users, Cpu, Search, Lock, Map, Zap, ExternalLink, CalendarDays, Video,
    Globe, AlertTriangle, BookOpen, Building2
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

const CREATOR_CARDS = [
    {
        icon: Globe,
        title: 'YouTube, TikTok, Twitch',
        description: 'IVA intracomunitario + Modelo 349 automático. Cada plataforma tiene su régimen: lo calculamos sin que tengas que estudiarlo.',
    },
    {
        icon: FileText,
        title: 'Epígrafe IAE correcto',
        description: 'Consulta DGT V0773-22: identifica el epígrafe 961.1, 961.2 o 843 que corresponde a tu actividad. Evita sanciones por epígrafe incorrecto.',
    },
    {
        icon: Shield,
        title: 'Royalties al 24%',
        description: 'Retención correcta sobre royalties de plataformas digitales, no el 15% genérico. Ahorra en la declaración aplicando el tipo correcto.',
    },
    {
        icon: Map,
        title: '21 territorios',
        description: 'El único asistente que cubre País Vasco y Navarra (régimen foral) + Canarias (IGIC) + Ceuta y Melilla (IPSI). Sin excepciones.',
    },
]

export default function Home() {
    const { isAuthenticated } = useAuth()

    useEffect(() => {
        // SEO: title + meta tags
        document.title = 'Impuestify — Asistente Fiscal IA para España | IRPF, Autónomos, Creadores'

        const setMeta = (name: string, content: string) => {
            let el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)
            if (!el) {
                el = document.createElement('meta')
                el.setAttribute('name', name)
                document.head.appendChild(el)
            }
            el.setAttribute('content', content)
        }

        const setOg = (property: string, content: string) => {
            let el = document.querySelector<HTMLMetaElement>(`meta[property="${property}"]`)
            if (!el) {
                el = document.createElement('meta')
                el.setAttribute('property', property)
                document.head.appendChild(el)
            }
            el.setAttribute('content', content)
        }

        setMeta(
            'description',
            'Asistente fiscal con IA para particulares, autónomos y creadores de contenido en España. IRPF, IVA, deducciones, Modelo 303, 349. Cubre las 17 CCAA + País Vasco + Navarra + Canarias + Ceuta y Melilla. Desde 5 EUR/mes.'
        )
        setMeta(
            'keywords',
            'impuestos españa, irpf, declaracion renta, autonomos, creadores de contenido, influencers, iva, modelo 303, modelo 349, deducciones, pais vasco, navarra, canarias, ceuta, melilla, asistente fiscal, inteligencia artificial'
        )
        setOg('og:title', 'Impuestify — Asistente Fiscal IA')
        setOg(
            'og:description',
            'El único asistente fiscal con IA que cubre los 21 territorios de España. Para particulares, autónomos y creadores de contenido.'
        )
        setOg('og:type', 'website')
        setOg('og:url', 'https://impuestify.com')

        // Schema.org structured data
        const existingScript = document.querySelector('#home-schema-org')
        if (!existingScript) {
            const script = document.createElement('script')
            script.id = 'home-schema-org'
            script.type = 'application/ld+json'
            script.text = JSON.stringify({
                '@context': 'https://schema.org',
                '@type': 'SoftwareApplication',
                name: 'Impuestify',
                applicationCategory: 'FinanceApplication',
                operatingSystem: 'Web',
                url: 'https://impuestify.com',
                offers: [
                    { '@type': 'Offer', price: '5', priceCurrency: 'EUR', name: 'Plan Particular' },
                    { '@type': 'Offer', price: '49', priceCurrency: 'EUR', name: 'Plan Creator' },
                    { '@type': 'Offer', price: '39', priceCurrency: 'EUR', name: 'Plan Autónomo' },
                ],
                aggregateRating: {
                    '@type': 'AggregateRating',
                    ratingValue: '4.8',
                    ratingCount: '150',
                },
                description:
                    'Asistente fiscal IA para España. IRPF, IVA, deducciones para particulares, autónomos y creadores de contenido.',
            })
            document.head.appendChild(script)
        }

        return () => {
            document.title = 'Impuestify — Asistente Fiscal con IA'
            const schema = document.querySelector('#home-schema-org')
            if (schema) schema.remove()
        }
    }, [])

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
                            del País Vasco y Navarra, con sus deducciones propias que no existen en el régimen común.{' '}
                            <Link to="/territorios-forales" className="coverage-note__link">
                                Saber más sobre territorios forales
                            </Link>
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
                        <FadeContent delay={400} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(234, 179, 8, 0.1)">
                                <div className="feature-icon">
                                    <Calculator size={28} />
                                </div>
                                <h3>Calculadora Neto</h3>
                                <p>Descubre cuánto te queda limpio como autónomo. Desglose real: IRPF, IVA, Seguridad Social y gastos.</p>
                            </SpotlightCard>
                        </FadeContent>
                        <FadeContent delay={500} duration={400}>
                            <a href="/calculadora-retenciones" style={{ textDecoration: 'none' }}>
                                <SpotlightCard className="feature-card" spotlightColor="rgba(16, 185, 129, 0.1)">
                                    <div className="feature-icon">
                                        <Calculator size={28} />
                                    </div>
                                    <h3>Calculadora Retenciones</h3>
                                    <p>¿Cuánto te retienen de IRPF en la nómina? Calcula tu tipo de retención con el algoritmo oficial de la AEAT.</p>
                                </SpotlightCard>
                            </a>
                        </FadeContent>
                        <FadeContent delay={600} duration={400}>
                            <a href="/calculadora-umbrales" style={{ textDecoration: 'none' }}>
                                <SpotlightCard className="feature-card" spotlightColor="rgba(139, 92, 246, 0.1)">
                                    <div className="feature-icon">
                                        <Building2 size={28} />
                                    </div>
                                    <h3>Umbrales Contables</h3>
                                    <p>¿Tu empresa debe usar PGC Normal o PYMES? ¿Necesita auditoría? Clasifica tu empresa según la LSC.</p>
                                </SpotlightCard>
                            </a>
                        </FadeContent>
                        <FadeContent delay={700} duration={400}>
                            <a href="/modelos-obligatorios" style={{ textDecoration: 'none' }}>
                                <SpotlightCard className="feature-card" spotlightColor="rgba(6, 182, 212, 0.1)">
                                    <div className="feature-icon">
                                        <FileText size={28} />
                                    </div>
                                    <h3>Obligaciones Fiscales</h3>
                                    <p>¿Qué modelos tienes que presentar? Descubre tus obligaciones fiscales según tu perfil, CCAA y actividad.</p>
                                </SpotlightCard>
                            </a>
                        </FadeContent>
                    </div>
                </div>
            </section>

            {/* Creators Section */}
            <section className="creators-promo">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="creators-promo__header">
                            <div className="creators-promo__badge">
                                <AlertTriangle size={14} />
                                <span>DAC7 en vigor — Hacienda ya tiene tus datos</span>
                            </div>
                            <h2 className="creators-promo__title">
                                Creadores de contenido:<br />
                                <span className="creators-promo__title-accent">Hacienda ya sabe cuánto ganas</span>
                            </h2>
                            <p className="creators-promo__subtitle">
                                Desde enero 2026, las plataformas reportan tus ingresos a la AEAT (DAC7).
                                Impuestify te ayuda a declarar correctamente y evitar sanciones.
                            </p>
                        </div>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="creators-promo__grid">
                            {CREATOR_CARDS.map((card, i) => {
                                const Icon = card.icon
                                return (
                                    <div key={i} className="creators-promo__card">
                                        <div className="creators-promo__card-icon">
                                            <Icon size={22} />
                                        </div>
                                        <h3 className="creators-promo__card-title">{card.title}</h3>
                                        <p className="creators-promo__card-desc">{card.description}</p>
                                    </div>
                                )
                            })}
                        </div>
                    </FadeContent>
                    <FadeContent delay={200} duration={500}>
                        <div className="creators-promo__cta-wrap">
                            <Link to="/subscribe" className="btn btn-lg creators-promo__cta">
                                <Video size={20} />
                                Ver Plan Creator — 49 EUR/mes
                                <ArrowRight size={18} />
                            </Link>
                            <p className="creators-promo__cta-note">
                                YouTubers, TikTokers, streamers e influencers. Sin permanencia.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Guía Fiscal Section — internal link for SEO */}
            <section className="guide-promo">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="guide-promo__inner">
                            <div className="guide-promo__icon">
                                <BookOpen size={28} />
                            </div>
                            <div className="guide-promo__content">
                                <h3 className="guide-promo__title">¿Primera vez haciendo la declaración de la renta?</h3>
                                <p className="guide-promo__desc">
                                    Nuestra guía fiscal interactiva te lleva paso a paso por los 7 apartados del IRPF.
                                    Sin jerga fiscal. Sin errores.
                                </p>
                            </div>
                            <Link to="/guia-fiscal" className="guide-promo__link">
                                Ir a la guía fiscal
                                <ArrowRight size={16} />
                            </Link>
                        </div>
                    </FadeContent>
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
                                    <span className="pricing-value pricing-value--creator">49</span>
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

            {/* Footer with legal links — required for Google OAuth verification */}
            <footer className="home-footer">
                <div className="container">
                    <p className="home-footer__desc">
                        Impuestify es un asistente fiscal con inteligencia artificial para particulares, autónomos y creadores de contenido en España.
                        Cubre los 21 territorios fiscales con más de 600 deducciones, simulador IRPF y guía fiscal personalizada.
                    </p>
                    <nav className="home-footer__sectors">
                        <span className="home-footer__sectors-label">Sectores:</span>
                        <Link to="/creadores-de-contenido">Creadores de Contenido</Link>
                        <Link to="/farmacias">Farmacias</Link>
                    </nav>
                    <nav className="home-footer__links">
                        <Link to="/privacy-policy">Política de Privacidad</Link>
                        <Link to="/terms">Términos y Condiciones</Link>
                        <Link to="/politica-cookies">Política de Cookies</Link>
                        <Link to="/security">Seguridad</Link>
                    </nav>
                    <p className="home-footer__copy">
                        © {new Date().getFullYear()} Impuestify — impuestify.com
                    </p>
                </div>
            </footer>
        </div>
    )
}
