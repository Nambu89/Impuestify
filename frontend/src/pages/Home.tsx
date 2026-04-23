import { Link } from 'react-router-dom'
import { useSEO } from '../hooks/useSEO'
import {
    MessageSquare, Shield, FileText, ArrowRight, Calculator, CreditCard,
    CheckCircle, X, Users, Cpu, Search, Lock, Map, Zap, ExternalLink, CalendarDays, Video,
    Globe, AlertTriangle, BookOpen, Building2, Heart, Briefcase,
    Scale, Receipt, Landmark, ScanLine
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

    useSEO({
        title: 'Impuestify — Asistente Fiscal IA para España | IRPF, Autónomos, Creadores',
        description: 'Asistente fiscal con IA para particulares, autónomos y creadores de contenido en España. Simulador IRPF, +1000 deducciones, 21 territorios.',
        canonical: '/',
        keywords: 'asistente fiscal IA, impuestos España, IRPF, declaración renta, deducciones autónomo, creadores contenido',
        schema: {
            '@context': 'https://schema.org',
            '@type': 'SoftwareApplication',
            name: 'Impuestify',
            url: 'https://impuestify.com',
            applicationCategory: 'FinanceApplication',
            operatingSystem: 'Web',
            offers: [
                { '@type': 'Offer', name: 'Particular', price: '5', priceCurrency: 'EUR', description: 'Para asalariados y pensionistas' },
                { '@type': 'Offer', name: 'Creador', price: '49', priceCurrency: 'EUR', description: 'Para YouTubers, TikTokers, streamers' },
                { '@type': 'Offer', name: 'Autónomo', price: '39', priceCurrency: 'EUR', description: 'Para trabajadores por cuenta propia' }
            ],
            aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.8', reviewCount: '150', bestRating: '5' },
            author: { '@type': 'Organization', name: 'Impuestify', url: 'https://impuestify.com' }
        }
    })

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
                            Haz la renta, lleva la contabilidad de tu actividad como
                            autónomo, calcula el Impuesto sobre Sociedades o contesta un
                                requerimiento de Hacienda. Todo desde la misma web. Funciona
                            con IA, sirve para las 15 comunidades autónomas, las cuatro
                            forales y Ceuta y Melilla, y cada respuesta te enseña el
                            artículo de la ley en el que se apoya.
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

            {/* Qué puedes hacer con Impuestify — explicación clara del producto */}
            <section className="what-it-does">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Qué puedes hacer con Impuestify</h2>
                        <p className="section-subtitle">
                            Sirve para particulares, autónomos, creadores y sociedades.
                            Esto es lo que tienes dentro desde el primer minuto.
                        </p>
                    </FadeContent>

                    <div className="what-it-does-grid">
                        <FadeContent delay={80} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(26, 86, 219, 0.1)">
                                <div className="what-icon"><FileText size={26} /></div>
                                <h3>Haz tu renta</h3>
                                <p>Calcula el IRPF con los tramos de tu comunidad o de tu territorio foral. Te dice si sale a pagar o a devolver y qué deducciones autonómicas puedes meter.</p>
                            </SpotlightCard>
                        </FadeContent>

                        <FadeContent delay={130} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(6, 182, 212, 0.1)">
                                <div className="what-icon"><Building2 size={26} /></div>
                                <h3>Impuesto sobre Sociedades</h3>
                                <p>Modelo 200 para tu SL o tu SA. Régimen común, los cuatro forales, ZEC de Canarias y Ceuta/Melilla. También te calcula los pagos fraccionados del Modelo 202.</p>
                            </SpotlightCard>
                        </FadeContent>

                        <FadeContent delay={180} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(16, 185, 129, 0.1)">
                                <div className="what-icon"><Receipt size={26} /></div>
                                <h3>IVA y modelos trimestrales</h3>
                                <p>303, 130, 131, 308, 349, 720 y 721. En Gipuzkoa usa el 300, en Navarra el F69, en Canarias el 420 (IGIC) y en Ceuta/Melilla el IPSI. Todos con borrador en PDF.</p>
                            </SpotlightCard>
                        </FadeContent>

                        <FadeContent delay={230} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(139, 92, 246, 0.1)">
                                <div className="what-icon"><Landmark size={26} /></div>
                                <h3>Sucesiones y Donaciones</h3>
                                <p>ISD con la normativa de cada comunidad, incluidas las bonificaciones forales y las de Ceuta y Melilla.</p>
                            </SpotlightCard>
                        </FadeContent>

                        <FadeContent delay={280} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(239, 68, 68, 0.1)">
                                <div className="what-icon"><Scale size={26} /></div>
                                <h3>DefensIA: defensa fiscal</h3>
                                <p>Si Hacienda te manda una liquidación, una sanción o un requerimiento, DefensIA lee el documento y te redacta el recurso: reposición, TEAR (abreviado o general) o alegaciones.</p>
                            </SpotlightCard>
                        </FadeContent>

                        <FadeContent delay={330} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(234, 179, 8, 0.1)">
                                <div className="what-icon"><ScanLine size={26} /></div>
                                <h3>Facturas y contabilidad</h3>
                                <p>Subes tus facturas, las clasifica al Plan General Contable y te monta los libros Diario, Mayor, Balance y Pérdidas y Ganancias. Los exportas listos para el Registro Mercantil.</p>
                            </SpotlightCard>
                        </FadeContent>

                        <FadeContent delay={380} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(59, 130, 246, 0.1)">
                                <div className="what-icon"><MessageSquare size={26} /></div>
                                <h3>Chat fiscal</h3>
                                <p>Le preguntas como si hablaras con un asesor. Lo que te contesta viene de más de 460 documentos oficiales (AEAT, BOE, Diputaciones Forales), y siempre te pone la cita al artículo de la ley.</p>
                            </SpotlightCard>
                        </FadeContent>

                        <FadeContent delay={430} duration={400}>
                            <SpotlightCard className="what-card" spotlightColor="rgba(6, 182, 212, 0.1)">
                                <div className="what-icon"><Calculator size={26} /></div>
                                <h3>Calculadoras gratis</h3>
                                <p>Sueldo neto, retenciones de IRPF, umbrales contables, qué modelos tienes que presentar, si estás obligado a declarar y checklist del borrador. Sin registrarte.</p>
                            </SpotlightCard>
                        </FadeContent>
                    </div>

                    <FadeContent delay={500} duration={500}>
                        <div className="what-it-does-footer">
                            <p>
                                <strong>Lo que no hace Impuestify:</strong> no presenta modelos ante la AEAT
                                en tu nombre, no gestiona nóminas, TC1/TC2 ni contratos laborales, y no
                                sustituye a un asesor fiscal o a un abogado colegiado. Antes de presentar un
                                modelo o un escrito oficial, pásaselo a un profesional.
                            </p>
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
                        <h2 className="section-title">Deducciones que no sabías que podías aplicarte</h2>
                        <p className="section-subtitle">Muchos contribuyentes pagan de más porque ni se enteran de que tienen derecho a una deducción autonómica.</p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="savings-grid">
                            <div className="savings-card">
                                <span className="savings-card__amount">
                                    <CountUp to={847} separator="." duration={2.5} /> EUR
                                </span>
                                <span className="savings-card__label">Ahorro medio que aparece por usuario</span>
                                <span className="savings-card__detail">En deducciones autonómicas que no se habían aplicado</span>
                            </div>
                            <div className="savings-card">
                                <span className="savings-card__amount">
                                    <CountUp to={3} duration={1.5} /> min
                                </span>
                                <span className="savings-card__label">Tiempo medio de una consulta</span>
                                <span className="savings-card__detail">Una asesoría tradicional tarda unos 45 minutos</span>
                            </div>
                            <div className="savings-card">
                                <span className="savings-card__amount">
                                    5 EUR<span className="savings-card__period">/mes</span>
                                </span>
                                <span className="savings-card__label">Una asesoría cobra entre 150 y 300 EUR al mes</span>
                                <span className="savings-card__detail">Con Impuestify pagas hasta un 97% menos</span>
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
                                    <CountUp to={463} separator="." duration={2.5} />
                                    <span>+</span>
                                </span>
                                <span className="stat-label">Documentos oficiales</span>
                            </div>
                            <div className="stat-item">
                                <span className="stat-number">
                                    <CountUp to={1000} separator="." duration={2} />
                                    <span>+</span>
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
                        <h2 className="section-title">Todas las comunidades, también las forales</h2>
                        <p className="section-subtitle">Mapa fiscal de España: régimen común, País Vasco, Navarra, Canarias y Ceuta/Melilla</p>
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
                        <h2 className="section-title">Por qué nuestra IA no se inventa las respuestas</h2>
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
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> Agentes distintos para renta, nóminas, AEAT y contabilidad</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> Cada respuesta cita el artículo concreto de la ley</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> 15 CCAA + 4 forales + Ceuta y Melilla</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> Más de mil deducciones autonómicas y forales</li>
                                    <li><CheckCircle size={16} className="comparison-icon-yes" /> Protección frente a inyección de prompts y filtrado de datos personales</li>
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
                        <h2 className="section-title">Cómo funciona por debajo</h2>
                    </FadeContent>
                    <div className="features-grid">
                        <FadeContent delay={100} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(26, 86, 219, 0.1)">
                                <div className="feature-icon">
                                    <Users size={28} />
                                </div>
                                <h3>Varios agentes, cada uno a lo suyo</h3>
                                <p>Un agente se ocupa de lo fiscal, otro de las nóminas, otro de las notificaciones de la AEAT y otro de tus documentos. Así cada pregunta va al que realmente sabe del tema.</p>
                            </SpotlightCard>
                        </FadeContent>
                        <FadeContent delay={200} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(6, 182, 212, 0.1)">
                                <div className="feature-icon">
                                    <Search size={28} />
                                </div>
                                <h3>Más de 460 documentos oficiales indexados</h3>
                                <p>AEAT, BOE, las cuatro Diputaciones Forales y boletines autonómicos. Cuando el asistente te responde, te enseña exactamente de dónde ha sacado la respuesta.</p>
                            </SpotlightCard>
                        </FadeContent>
                        <FadeContent delay={300} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(16, 185, 129, 0.1)">
                                <div className="feature-icon">
                                    <Lock size={28} />
                                </div>
                                <h3>Tus datos no se quedan por ahí</h3>
                                <p>Filtramos DNIs, IBANs, teléfonos y correos antes de que lleguen al modelo. Bloqueamos intentos de manipulación del asistente. Todo bajo RGPD y servidores en la UE.</p>
                            </SpotlightCard>
                        </FadeContent>
                        <FadeContent delay={400} duration={400}>
                            <SpotlightCard className="feature-card" spotlightColor="rgba(234, 179, 8, 0.1)">
                                <div className="feature-icon">
                                    <Calculator size={28} />
                                </div>
                                <h3>Sueldo neto del autónomo</h3>
                                <p>Cuánto te queda limpio al mes. Te enseña el desglose: IRPF, IVA, Seguridad Social y gastos.</p>
                            </SpotlightCard>
                        </FadeContent>
                        <FadeContent delay={500} duration={400}>
                            <a href="/calculadora-retenciones" style={{ textDecoration: 'none' }}>
                                <SpotlightCard className="feature-card" spotlightColor="rgba(16, 185, 129, 0.1)">
                                    <div className="feature-icon">
                                        <Calculator size={28} />
                                    </div>
                                    <h3>Retenciones de tu nómina</h3>
                                    <p>¿Cuánto te están quitando de IRPF cada mes? Te lo calcula con el mismo algoritmo que usa la AEAT.</p>
                                </SpotlightCard>
                            </a>
                        </FadeContent>
                        <FadeContent delay={600} duration={400}>
                            <a href="/calculadora-umbrales" style={{ textDecoration: 'none' }}>
                                <SpotlightCard className="feature-card" spotlightColor="rgba(139, 92, 246, 0.1)">
                                    <div className="feature-icon">
                                        <Building2 size={28} />
                                    </div>
                                    <h3>Umbrales contables</h3>
                                    <p>¿Tu empresa va con PGC Normal o con PYMES? ¿Necesita auditoría? Te lo dice según los umbrales de la Ley de Sociedades de Capital.</p>
                                </SpotlightCard>
                            </a>
                        </FadeContent>
                        <FadeContent delay={700} duration={400}>
                            <a href="/modelos-obligatorios" style={{ textDecoration: 'none' }}>
                                <SpotlightCard className="feature-card" spotlightColor="rgba(6, 182, 212, 0.1)">
                                    <div className="feature-icon">
                                        <FileText size={28} />
                                    </div>
                                    <h3>Qué modelos te tocan</h3>
                                    <p>Según tu perfil, tu comunidad y tu actividad, te decimos qué modelos tienes que presentar y cuándo vencen.</p>
                                </SpotlightCard>
                            </a>
                        </FadeContent>
                        <FadeContent delay={800} duration={400}>
                            <a href="/farmacias" style={{ textDecoration: 'none' }}>
                                <SpotlightCard className="feature-card" spotlightColor="rgba(5, 150, 105, 0.1)">
                                    <div className="feature-icon">
                                        <Heart size={28} />
                                    </div>
                                    <h3>Farmacias</h3>
                                    <p>Recargo de equivalencia aplicado automático, fondo de comercio, deducciones propias de farmacéuticos titulares. Pensado para el día a día de una oficina de farmacia.</p>
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

                            {/* Autónomo */}
                            <div className="pricing-card pricing-card--autonomo">
                                <div className="pricing-header">
                                    <div className="pricing-icon pricing-icon--autonomo">
                                        <Briefcase size={32} />
                                    </div>
                                    <div>
                                        <h3 className="pricing-plan-name">Autónomo</h3>
                                        <p className="pricing-plan-desc">Para profesionales por cuenta propia</p>
                                    </div>
                                </div>
                                <div className="pricing-amount">
                                    <span className="pricing-currency">EUR</span>
                                    <span className="pricing-value pricing-value--autonomo">39</span>
                                    <span className="pricing-period">/mes <small>IVA incl.</small></span>
                                </div>
                                <ul className="pricing-features">
                                    <li><CheckCircle size={18} className="pricing-check--autonomo" /><span>Todo lo del plan Particular</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--autonomo" /><span>Modelos 303, 130, 131, 390</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--autonomo" /><span>Clasificador de facturas con IA</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--autonomo" /><span>Contabilidad PGC y libros oficiales</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--autonomo" /><span>Calculadora sueldo neto autónomo</span></li>
                                    <li><CheckCircle size={18} className="pricing-check--autonomo" /><span>Gastos deducibles por actividad</span></li>
                                </ul>
                                <Link to="/subscribe" className="btn btn-lg pricing-cta pricing-cta--autonomo">
                                    <CreditCard size={20} />
                                    Empezar como Autónomo
                                </Link>
                            </div>
                        </div>
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
