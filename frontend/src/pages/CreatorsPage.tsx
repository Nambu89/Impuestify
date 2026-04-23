import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useSEO } from '../hooks/useSEO'
import {
    ArrowRight, CheckCircle, X, Video, ChevronLeft, Zap,
    FileText, Globe, Calculator, Bell, Shield, ChevronDown, Map, MapPin
} from 'lucide-react'
import FadeContent from '../components/reactbits/FadeContent'
import SpotlightCard from '../components/reactbits/SpotlightCard'
import GradientText from '../components/reactbits/GradientText'
import './CreatorsPage.css'

const FEATURES = [
    {
        icon: Calculator,
        title: 'Simulador IRPF con royalties',
        description:
            'Calcula el IRPF con derechos de autor y royalties de plataformas digitales. Aplica la retención del 24% sobre ingresos de YouTube, Twitch o Patreon.',
    },
    {
        icon: Globe,
        title: 'IVA por plataforma',
        description:
            'Calcula el IVA según la plataforma: YouTube/Google (IVA 0% intracomunitario), TikTok UK (sin IVA peninsular), Twitch (régimen especial de servicios digitales).',
    },
    {
        icon: FileText,
        title: 'Epígrafe IAE para creadores',
        description:
            'Te ayuda a elegir el epígrafe IAE correcto para tu actividad. La DGT lo aclara en la consulta vinculante V0773-22. Un epígrafe mal puesto puede costarte una sanción.',
    },
    {
        icon: FileText,
        title: 'Modelo 349 automático',
        description:
            'Gestiona las operaciones intracomunitarias con Google Ireland, Meta Platforms Ireland y TikTok Technology. Declaración informativa trimestral sin errores.',
    },
    {
        icon: Zap,
        title: 'Asistente con IA',
        description:
            'IA entrenada con la normativa que afecta a creadores digitales: DAC7, Modelo 238, Plan Tributario AEAT 2026 y consultas DGT sobre plataformas.',
    },
    {
        icon: Globe,
        title: 'Cobertura en 21 territorios',
        description:
            'País Vasco, Navarra, Canarias (IGIC), Ceuta y Melilla incluidos. Deducciones autonómicas de cada territorio calculadas a partir de fuentes oficiales.',
    },
    {
        icon: Bell,
        title: 'Avisos de plazos',
        description:
            'Avisos de los modelos 303, 130, 349 y Renta. Se acabó pagar multas por presentar tarde. Calendario fiscal ajustado a tu caso.',
    },
    {
        icon: Shield,
        title: 'Análisis de documentos AEAT',
        description:
            'Sube notificaciones de la AEAT y nóminas y la IA las lee por ti. Detecta importes incorrectos y obligaciones que quizá no tenías en el radar.',
    },
]

const COMPARISON_ROWS = [
    {
        feature: 'Precio mensual',
        gestoria: '80-150 EUR/mes',
        onlytax: '84,70 EUR/mes',
        impuestify: '49 EUR/mes',
        highlight: true,
    },
    {
        feature: 'IA fiscal especializada',
        gestoria: false,
        onlytax: false,
        impuestify: true,
    },
    {
        feature: 'Cobertura foral (P. Vasco, Navarra)',
        gestoria: 'variable',
        onlytax: false,
        impuestify: true,
    },
    {
        feature: 'IVA por plataforma digital',
        gestoria: 'manual',
        onlytax: 'manual',
        impuestify: true,
    },
    {
        feature: 'Modelo 349 automático',
        gestoria: 'manual',
        onlytax: false,
        impuestify: true,
    },
    {
        feature: 'Disponibilidad',
        gestoria: 'Horario de oficina',
        onlytax: 'Horario de oficina',
        impuestify: '24/7',
    },
]

const FAQS = [
    {
        q: '¿Qué epígrafe IAE necesito como creador de contenido?',
        a: 'La Dirección General de Tributos aclaró en la consulta vinculante V0773-22 que los creadores de contenido digital tributan en el epígrafe 961.1 (producción de películas cinematográficas) o 961.2 (distribución de películas cinematográficas), según si produces y distribuyes tú mismo. Si tus ingresos principales vienen de patrocinios, en muchos casos aplica el 843 (servicios de publicidad, relaciones públicas y similares). El asistente revisa tu caso y te dice cuál te toca.',
    },
    {
        q: '¿Tengo que facturar a YouTube/Google?',
        a: 'Sí. YouTube paga a través de Google Ireland Limited, una entidad comunitaria. Si estás de alta como autónomo con NIF-IVA, emites factura con IVA 0% (operación intracomunitaria, Modelo 349 trimestral). Si no tienes NIF-IVA, Google puede practicar retención en origen. Para evitar retenciones que no te tocan, configura bien tu cuenta de AdSense con el formulario W-8BEN-E.',
    },
    {
        q: '¿Cómo declaro los ingresos de TikTok si pagan desde UK?',
        a: 'TikTok Technology Limited opera desde Irlanda y Reino Unido. Tras el Brexit, los pagos desde UK ya no son operaciones intracomunitarias: se tratan como servicios prestados a entidad no comunitaria, con IVA al tipo cero y reglas de localización inversa. El importe bruto va a IRPF como rendimiento de actividad económica. Si TikTok te aplica retención en origen, puedes deducirla como crédito fiscal por el Convenio de Doble Imposición España-UK.',
    },
    {
        q: '¿Necesito darme de alta como autónomo?',
        a: 'Si tus ingresos por creación de contenido superan el Salario Mínimo Interprofesional de forma habitual (o incluso de forma esporádica si la TGSS te lo requiere), tienes que darte de alta en el RETA. El Tribunal Supremo dice que lo que obliga es la habitualidad, no el importe. Si son ingresos puntuales por debajo del SMI, puede bastar con tributarlos como rendimiento de capital mobiliario o de trabajo, según el tipo de contrato.',
    },
    {
        q: '¿Qué pasa si no he declarado mis ingresos de plataformas?',
        a: 'Desde 2023, las plataformas digitales (YouTube, TikTok, Twitch, Airbnb, etc.) tienen que reportar a Hacienda los ingresos de sus creadores en España con el Modelo 238 (DAC7). La AEAT ya tiene esos datos. Presentar una complementaria antes de que te llegue el requerimiento baja la sanción del 50-150% al 10-20% si regularizas voluntariamente. El asistente te ayuda a calcular el importe exacto.',
    },
]

export default function CreatorsPage() {
    const [openFaq, setOpenFaq] = useState<number | null>(null)

    useSEO({
        title: 'Fiscalidad para creadores de contenido — Impuestify',
        description: 'Guía fiscal para creadores en España: IVA según plataforma (YouTube, Twitch, TikTok, Patreon), Modelo 349, reporte DAC7 y alta CNAE 60.39.',
        canonical: '/creadores-de-contenido',
        keywords: 'impuestos creadores contenido, YouTubers impuestos, TikTok fiscal, streamers IVA, influencer autónomo',
        schema: [
            {
                '@context': 'https://schema.org',
                '@type': 'WebApplication',
                name: 'Impuestify para Creadores',
                url: 'https://impuestify.com/creadores-de-contenido',
                applicationCategory: 'FinanceApplication',
                operatingSystem: 'Web',
                offers: { '@type': 'Offer', price: '49', priceCurrency: 'EUR' },
                author: { '@type': 'Organization', name: 'Impuestify', url: 'https://impuestify.com' }
            },
            {
                '@context': 'https://schema.org',
                '@type': 'BreadcrumbList',
                itemListElement: [
                    { '@type': 'ListItem', position: 1, name: 'Inicio', item: 'https://impuestify.com' },
                    { '@type': 'ListItem', position: 2, name: 'Creadores de Contenido', item: 'https://impuestify.com/creadores-de-contenido' }
                ]
            }
        ]
    })

    return (
        <div className="creators-page">
            {/* Back link */}
            <div className="creators-back">
                <div className="container">
                    <Link to="/" className="creators-back__link">
                        <ChevronLeft size={16} />
                        Volver al inicio
                    </Link>
                </div>
            </div>

            {/* ==================== HERO ==================== */}
            <section className="creators-hero">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="creators-hero__badges">
                            <span className="creators-hero__badge creators-hero__badge--new">
                                NUEVO
                            </span>
                            <span className="creators-hero__badge creators-hero__badge--plan">
                                <Video size={14} />
                                Plan Creator
                            </span>
                        </div>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <h1 className="creators-hero__title">
                            Fiscalidad para{' '}
                            <GradientText
                                colors={['#1a56db', '#06b6d4', '#3b82f6', '#1a56db']}
                                animationSpeed={6}
                                className="creators-hero__gradient"
                            >
                                creadores de contenido
                            </GradientText>
                            {' '}en España
                        </h1>
                        <p className="creators-hero__subtitle">
                            Asistente fiscal con IA pensado para{' '}
                            <strong>YouTube, TikTok, Twitch e Instagram</strong>.
                            IRPF, IVA por plataforma, IAE para influencers y DAC7.
                            Cubre los 21 territorios: régimen común, foral y Canarias.
                        </p>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <div className="creators-hero__actions">
                            <Link to="/subscribe?highlight=creator" className="btn btn-primary btn-lg">
                                Empieza por 49 EUR/mes
                                <ArrowRight size={20} />
                            </Link>
                            <a href="#features" className="btn btn-secondary btn-lg">
                                Ver qué incluye
                            </a>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== ALERTA DAC7 ==================== */}
            <section className="creators-alert">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="creators-alert__grid">
                            <div className="creators-alert__item creators-alert__item--danger">
                                <div className="creators-alert__icon">
                                    <Shield size={24} />
                                </div>
                                <div>
                                    <h3>Hacienda ya sabe cuánto ganas</h3>
                                    <p>
                                        Desde 2023, la directiva DAC7 obliga a YouTube, TikTok y Twitch a pasarle
                                        tus ingresos a la AEAT mediante el <strong>Modelo 238</strong>. No declararlos
                                        supone sanciones del 50-150% del importe omitido.
                                    </p>
                                </div>
                            </div>
                            <div className="creators-alert__item creators-alert__item--warning">
                                <div className="creators-alert__icon">
                                    <FileText size={24} />
                                </div>
                                <div>
                                    <h3>En el punto de mira del Plan Tributario AEAT 2026</h3>
                                    <p>
                                        El Plan Anual de Control Tributario 2026 de la AEAT cita de forma
                                        expresa a los <strong>creadores de contenido digital</strong> por el
                                        desfase entre lo que declaran y lo que reportan las plataformas.
                                    </p>
                                </div>
                            </div>
                            <div className="creators-alert__item creators-alert__item--info">
                                <div className="creators-alert__icon">
                                    <FileText size={24} />
                                </div>
                                <div>
                                    <h3>Un IAE mal puesto te puede costar caro</h3>
                                    <p>
                                        La consulta DGT <strong>V0773-22</strong> aclara el régimen fiscal de los
                                        creadores. Un epígrafe equivocado puede tumbarte deducciones y abrirte una
                                        inspección. Impuestify elige el que te toca según tu caso.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== FEATURES ==================== */}
            <section className="creators-features" id="features">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Qué incluye el Plan Creator</h2>
                        <p className="section-subtitle">
                            49 EUR/mes. IVA por plataforma, IAE para influencers, Modelo 349 y DAC7. Lo que hace falta para declarar bien como creador digital.
                        </p>
                    </FadeContent>
                    <div className="creators-features__grid">
                        {FEATURES.map((f, i) => {
                            const Icon = f.icon
                            return (
                                <FadeContent key={f.title} delay={i * 80} duration={500}>
                                    <SpotlightCard
                                        className="creators-feature__card"
                                        spotlightColor="rgba(26, 86, 219, 0.08)"
                                    >
                                        <div className="creators-feature__icon">
                                            <Icon size={22} />
                                        </div>
                                        <h3 className="creators-feature__title">{f.title}</h3>
                                        <p className="creators-feature__desc">{f.description}</p>
                                    </SpotlightCard>
                                </FadeContent>
                            )
                        })}
                    </div>
                </div>
            </section>

            {/* ==================== TABLA COMPARATIVA ==================== */}
            <section className="creators-comparison">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Comparativa de opciones</h2>
                        <p className="section-subtitle">
                            Lo que pagas y lo que recibes frente a una gestoría tradicional y a OnlyTax
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="creators-comparison__table-wrap">
                            <table className="creators-comparison__table">
                                <thead>
                                    <tr>
                                        <th>Característica</th>
                                        <th>Gestoría tradicional</th>
                                        <th>OnlyTax</th>
                                        <th className="creators-comparison__th--highlight">
                                            <Zap size={14} className="creators-comparison__th-icon" />
                                            Impuestify Creator
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {COMPARISON_ROWS.map((row) => (
                                        <tr
                                            key={row.feature}
                                            className={row.highlight ? 'creators-comparison__row--price' : ''}
                                        >
                                            <td className="creators-comparison__feature">{row.feature}</td>
                                            <td>
                                                {typeof row.gestoria === 'boolean' ? (
                                                    row.gestoria ? (
                                                        <CheckCircle size={18} className="creators-comparison__icon-yes" />
                                                    ) : (
                                                        <X size={18} className="creators-comparison__icon-no" />
                                                    )
                                                ) : (
                                                    <span className="creators-comparison__text">{row.gestoria}</span>
                                                )}
                                            </td>
                                            <td>
                                                {typeof row.onlytax === 'boolean' ? (
                                                    row.onlytax ? (
                                                        <CheckCircle size={18} className="creators-comparison__icon-yes" />
                                                    ) : (
                                                        <X size={18} className="creators-comparison__icon-no" />
                                                    )
                                                ) : (
                                                    <span className="creators-comparison__text">{row.onlytax}</span>
                                                )}
                                            </td>
                                            <td className="creators-comparison__td--highlight">
                                                {typeof row.impuestify === 'boolean' ? (
                                                    row.impuestify ? (
                                                        <CheckCircle size={18} className="creators-comparison__icon-yes" />
                                                    ) : (
                                                        <X size={18} className="creators-comparison__icon-no" />
                                                    )
                                                ) : (
                                                    <span className="creators-comparison__text creators-comparison__text--highlight">{row.impuestify}</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <p className="creators-comparison__note">
                            Precios de competidores a marzo de 2026. Impuestify no tiene permanencia: cancelas cuando quieras.
                        </p>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== FAQ ==================== */}
            <section className="creators-faq">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Preguntas frecuentes</h2>
                        <p className="section-subtitle">
                            Las dudas que suelen tener los creadores cuando aparece Hacienda
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="creators-faq__list">
                            {FAQS.map((faq, i) => (
                                <div
                                    key={i}
                                    className={`creators-faq__item${openFaq === i ? ' creators-faq__item--open' : ''}`}
                                >
                                    <button
                                        className="creators-faq__question"
                                        onClick={() => setOpenFaq(openFaq === i ? null : i)}
                                        aria-expanded={openFaq === i}
                                    >
                                        <span>{faq.q}</span>
                                        <ChevronDown
                                            size={18}
                                            className={`creators-faq__chevron${openFaq === i ? ' creators-faq__chevron--open' : ''}`}
                                        />
                                    </button>
                                    {openFaq === i && (
                                        <div className="creators-faq__answer">
                                            <p>{faq.a}</p>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== VENTAJAS TERRITORIALES (GEO SEO) ==================== */}
            <section className="creators-territories">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Ventajas fiscales por territorio</h2>
                        <p className="section-subtitle">
                            Según dónde residas, la factura fiscal puede bajar bastante
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="creators-territories__grid">
                            <Link to="/canarias" className="creators-territories__card creators-territories__card--canarias">
                                <div className="creators-territories__card-header">
                                    <Globe size={20} />
                                    <span className="creators-territories__badge">IGIC 7%</span>
                                </div>
                                <h3>Canarias</h3>
                                <ul className="creators-territories__list">
                                    <li>IGIC al 7% en lugar de IVA al 21%</li>
                                    <li>ZEC: Impuesto de Sociedades al 4%</li>
                                    <li>RIC: reduce hasta un 90% de la base imponible</li>
                                    <li>Streamers en Canarias: tipo específico de IGIC</li>
                                </ul>
                                <span className="creators-territories__link">
                                    Ver fiscalidad en Canarias <ArrowRight size={14} />
                                </span>
                            </Link>

                            <Link to="/ceuta-melilla" className="creators-territories__card creators-territories__card--ceuta">
                                <div className="creators-territories__card-header">
                                    <MapPin size={20} />
                                    <span className="creators-territories__badge">IPSI 4%</span>
                                </div>
                                <h3>Ceuta y Melilla</h3>
                                <ul className="creators-territories__list">
                                    <li>IPSI al 4% en lugar de IVA al 21%</li>
                                    <li>Deducción del 60% en IRPF por rentas obtenidas allí</li>
                                    <li>Sin IVA en operaciones locales</li>
                                    <li>De los regímenes más favorables de Europa</li>
                                </ul>
                                <span className="creators-territories__link">
                                    Ver fiscalidad en Ceuta y Melilla <ArrowRight size={14} />
                                </span>
                            </Link>

                            <Link to="/territorios-forales" className="creators-territories__card creators-territories__card--foral">
                                <div className="creators-territories__card-header">
                                    <Map size={20} />
                                    <span className="creators-territories__badge">Régimen foral</span>
                                </div>
                                <h3>País Vasco y Navarra</h3>
                                <ul className="creators-territories__list">
                                    <li>IRPF influencer en Madrid vs País Vasco: hasta 5 puntos menos</li>
                                    <li>7 tramos en País Vasco frente a 6 en régimen común</li>
                                    <li>Deducciones propias que no existen en el resto del Estado</li>
                                    <li>Gestión directa con la Hacienda Foral</li>
                                </ul>
                                <span className="creators-territories__link">
                                    Ver territorios forales <ArrowRight size={14} />
                                </span>
                            </Link>

                            <div className="creators-territories__card creators-territories__card--madrid">
                                <div className="creators-territories__card-header">
                                    <MapPin size={20} />
                                    <span className="creators-territories__badge">Deflactación</span>
                                </div>
                                <h3>Madrid</h3>
                                <ul className="creators-territories__list">
                                    <li>Deflactación de la tarifa autonómica del IRPF</li>
                                    <li>Bonificación del 100% en sucesiones y donaciones</li>
                                    <li>Deducción por alquiler de vivienda habitual</li>
                                    <li>Concentra buena parte de los creadores con fiscalidad atractiva</li>
                                </ul>
                                <span className="creators-territories__link creators-territories__link--disabled">
                                    Pregunta tu caso al asistente
                                </span>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== LINKS INTERNOS SEO ==================== */}
            <section className="creators-internal-links">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="creators-internal-links__grid">
                            <Link to="/territorios-forales" className="creators-internal-links__card">
                                <Map size={20} />
                                <div>
                                    <strong>País Vasco y Navarra</strong>
                                    <span>Régimen foral: deducciones que no existen en el régimen común</span>
                                </div>
                                <ArrowRight size={16} />
                            </Link>
                            <Link to="/canarias" className="creators-internal-links__card">
                                <Globe size={20} />
                                <div>
                                    <strong>Canarias — IGIC</strong>
                                    <span>Impuesto General Indirecto Canario: cómo facturar desde las islas</span>
                                </div>
                                <ArrowRight size={16} />
                            </Link>
                            <Link to="/ceuta-melilla" className="creators-internal-links__card">
                                <MapPin size={20} />
                                <div>
                                    <strong>Ceuta y Melilla — IPSI</strong>
                                    <span>IPSI al 4% y deducción del 60% en IRPF</span>
                                </div>
                                <ArrowRight size={16} />
                            </Link>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== CTA FINAL ==================== */}
            <section className="creators-cta">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="creators-cta__card">
                            <div className="creators-cta__icon">
                                <Video size={36} />
                            </div>
                            <h2>Empieza a declarar bien por 49 EUR/mes</h2>
                            <p>
                                Sin permanencia ni letra pequeña. Un asistente fiscal que conoce
                                tu trabajo como creador digital y habla tu idioma.
                            </p>
                            <Link to="/subscribe?highlight=creator" className="btn btn-primary btn-lg">
                                Empieza por 49 EUR/mes
                                <ArrowRight size={20} />
                            </Link>
                            <p className="creators-cta__note">
                                49 EUR/mes. Sin permanencia. Cancelas cuando quieras.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
