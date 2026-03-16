import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
    ArrowRight, CheckCircle, X, Video, ChevronLeft, Zap,
    FileText, Globe, Calculator, Bell, Shield, ChevronDown, Map
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
            'Calcula tu IRPF incluyendo derechos de autor y royalties de plataformas digitales. Retención del 24% aplicada correctamente sobre ingresos de YouTube, Twitch o Patreon.',
    },
    {
        icon: Globe,
        title: 'IVA por plataforma',
        description:
            'Calcula el IVA aplicable según la plataforma: YouTube/Google (factura con IVA 0% intracomunitario), TikTok UK (sin IVA peninsular), Twitch (régimen especial servicios digitales).',
    },
    {
        icon: FileText,
        title: 'Epígrafe IAE para creadores',
        description:
            'Identifica el epígrafe correcto del IAE para tu actividad como creador. La DGT lo aclara en la consulta vinculante V0773-22. Evita sanciones por epígrafe incorrecto.',
    },
    {
        icon: FileText,
        title: 'Modelo 349 automático',
        description:
            'Gestión de las operaciones intracomunitarias con Google Ireland, Meta Platforms Ireland y TikTok Technology. Declaración informativa trimestral sin errores.',
    },
    {
        icon: Zap,
        title: 'Asistente IA especializado',
        description:
            'Motor de IA entrenado sobre la normativa fiscal específica de creadores digitales: DAC7, Modelo 238, Plan Tributario AEAT 2026, consultas DGT sobre plataformas.',
    },
    {
        icon: Globe,
        title: 'Cobertura 21 territorios',
        description:
            'Incluye País Vasco, Navarra, Canarias (IGIC), Ceuta y Melilla. Deducciones autonómicas propias de cada territorio calculadas con fuentes oficiales.',
    },
    {
        icon: Bell,
        title: 'Alertas de plazos fiscales',
        description:
            'Notificaciones de los modelos 303, 130, 349 y Renta. Nunca más una multa por presentación fuera de plazo. Calendario fiscal personalizado según tu situación.',
    },
    {
        icon: Shield,
        title: 'Análisis de documentos AEAT',
        description:
            'Sube notificaciones de la AEAT y nóminas para que la IA las analice. Detecta importes incorrectos y obligaciones fiscales que quizá desconocías.',
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
        a: 'La Dirección General de Tributos aclaró en la consulta vinculante V0773-22 que los creadores de contenido digital tributan en el epígrafe 961.1 (Producción de películas cinematográficas) o 961.2 (Distribución de películas cinematográficas), dependiendo de si produces y distribuyes tú mismo. En muchos casos también aplica el 843 (Servicios de publicidad, relaciones públicas y similares) si los ingresos principales son patrocinios. Nuestro asistente analiza tu caso concreto y determina el epígrafe correcto.',
    },
    {
        q: '¿Tengo que facturar a YouTube/Google?',
        a: 'Sí. YouTube paga a través de Google Ireland Limited, una entidad comunitaria. Si estás dado de alta como autónomo con NIF-IVA, emites factura con IVA 0% (operación intracomunitaria, Modelo 349 trimestral). Si no tienes NIF-IVA, Google puede aplicar retención en origen. La correcta configuración de tu cuenta de AdSense con el formulario W-8BEN-E es fundamental para evitar retenciones incorrectas.',
    },
    {
        q: '¿Cómo declaro los ingresos de TikTok si pagan desde UK?',
        a: 'TikTok Technology Limited opera desde Irlanda y Reino Unido. Tras el Brexit, los pagos desde UK no son operaciones intracomunitarias. Tributan como servicios prestados a entidad no comunitaria: IVA al tipo cero con reglas de localización inversa. El importe bruto se declara en IRPF como rendimiento de actividad económica. La retención en origen aplicada por TikTok (si la hay) puede deducirse como crédito fiscal según el Convenio de Doble Imposición España-UK.',
    },
    {
        q: '¿Necesito darme de alta como autónomo?',
        a: 'Si tus ingresos por creación de contenido superan el Salario Mínimo Interprofesional de forma habitual (o incluso de forma esporádica si la TGSS te lo requiere), sí estás obligado a darte de alta como autónomo en el RETA. La jurisprudencia del Tribunal Supremo establece que la habitualidad, no el importe, determina la obligación. Si son ingresos ocasionales por debajo del SMI, puede ser suficiente tributar como rendimiento de capital mobiliario o rendimiento de trabajo según el tipo de contrato.',
    },
    {
        q: '¿Qué pasa si no he declarado mis ingresos de plataformas?',
        a: 'Desde 2023, las plataformas digitales (YouTube, TikTok, Twitch, Airbnb, etc.) están obligadas a reportar a Hacienda los ingresos de sus creadores en España mediante el Modelo 238 (DAC7). La AEAT ya tiene esos datos. Presentar una declaración complementaria antes de recibir una notificación reduce las sanciones significativamente: del 50-150% con requerimiento previo, al 10-20% si regularizas voluntariamente. Nuestro asistente te ayuda a calcular el importe exacto a regularizar.',
    },
]

export default function CreatorsPage() {
    const [openFaq, setOpenFaq] = useState<number | null>(null)

    useEffect(() => {
        document.title = 'Impuestos para Creadores de Contenido | YouTubers, TikTokers, Streamers | Impuestify'

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
            'Asistente fiscal IA para creadores de contenido en España. YouTube, TikTok, Twitch, Instagram. Epígrafe IAE, IVA intracomunitario, Modelo 349, royalties. 21 territorios incluyendo País Vasco y Navarra. 49 EUR/mes.'
        )
        setMeta(
            'keywords',
            'impuestos creadores contenido, IRPF influencer, IVA YouTube España, fiscalidad TikTok, Modelo 349 creadores, epígrafe IAE influencer, DAC7 España, tributación streamer, royalties creadores, fiscalidad youtuber, impuestos twitch, hacienda influencer'
        )
        setOg('og:title', 'Impuestos para Creadores de Contenido | YouTubers, TikTokers, Streamers | Impuestify')
        setOg(
            'og:description',
            'El único asistente fiscal con IA que entiende YouTube, TikTok, Twitch e Instagram. IRPF, IVA intracomunitario, Modelo 349, epígrafe IAE y cobertura foral completa. 49 EUR/mes.'
        )
        setOg('og:type', 'website')
        setOg('og:url', 'https://impuestify.com/creadores-de-contenido')

        // Schema.org para CreatorsPage
        const existingScript = document.querySelector('#creators-schema-org')
        if (!existingScript) {
            const script = document.createElement('script')
            script.id = 'creators-schema-org'
            script.type = 'application/ld+json'
            script.text = JSON.stringify({
                '@context': 'https://schema.org',
                '@type': 'WebPage',
                name: 'Impuestos para Creadores de Contenido — Impuestify',
                description:
                    'Asistente fiscal IA especializado en creadores de contenido digitales en España. YouTube, TikTok, Twitch, Patreon. IRPF, IVA intracomunitario, Modelo 349.',
                url: 'https://impuestify.com/creadores-de-contenido',
                breadcrumb: {
                    '@type': 'BreadcrumbList',
                    itemListElement: [
                        { '@type': 'ListItem', position: 1, name: 'Inicio', item: 'https://impuestify.com' },
                        {
                            '@type': 'ListItem',
                            position: 2,
                            name: 'Creadores de Contenido',
                            item: 'https://impuestify.com/creadores-de-contenido',
                        },
                    ],
                },
            })
            document.head.appendChild(script)
        }

        return () => {
            document.title = 'Impuestify — Asistente Fiscal con IA'
            const schema = document.querySelector('#creators-schema-org')
            if (schema) schema.remove()
        }
    }, [])

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
                            Impuestos para{' '}
                            <GradientText
                                colors={['#1a56db', '#06b6d4', '#3b82f6', '#1a56db']}
                                animationSpeed={6}
                                className="creators-hero__gradient"
                            >
                                Creadores de Contenido
                            </GradientText>
                        </h1>
                        <p className="creators-hero__subtitle">
                            El único asistente fiscal con IA que entiende{' '}
                            <strong>YouTube, TikTok, Twitch e Instagram</strong>.
                            Con cobertura foral completa para País Vasco y Navarra.
                        </p>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <div className="creators-hero__actions">
                            <Link to="/subscribe" className="btn btn-primary btn-lg">
                                Empezar por 49 EUR/mes
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
                                        Desde 2023, la directiva DAC7 obliga a YouTube, TikTok y Twitch a reportar
                                        tus ingresos a la AEAT mediante el <strong>Modelo 238</strong>. No declararlo
                                        conlleva sanciones del 50-150% del importe no declarado.
                                    </p>
                                </div>
                            </div>
                            <div className="creators-alert__item creators-alert__item--warning">
                                <div className="creators-alert__icon">
                                    <FileText size={24} />
                                </div>
                                <div>
                                    <h3>Objetivo prioritario del Plan Tributario AEAT 2026</h3>
                                    <p>
                                        El Plan Anual de Control Tributario 2026 de la AEAT señala expresamente
                                        a los <strong>creadores de contenido digital</strong> como colectivo de
                                        especial seguimiento por la brecha entre ingresos declarados y reportados
                                        por plataformas.
                                    </p>
                                </div>
                            </div>
                            <div className="creators-alert__item creators-alert__item--info">
                                <div className="creators-alert__icon">
                                    <FileText size={24} />
                                </div>
                                <div>
                                    <h3>El epígrafe IAE correcto evita sanciones</h3>
                                    <p>
                                        La consulta DGT <strong>V0773-22</strong> aclara el régimen fiscal de los
                                        creadores. Un epígrafe incorrecto puede invalidar tus deducciones y
                                        generar inspecciones. Impuestify identifica el correcto para tu caso.
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
                            49 EUR/mes. Todo lo que necesitas para declarar bien como creador digital.
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
                            Por qué Impuestify Creator es la opción más inteligente para tu bolsillo
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
                            Precios de competidores a marzo 2026. Impuestify no tiene permanencia: cancela cuando quieras.
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
                            Las dudas más habituales de los creadores de contenido con Hacienda
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

            {/* ==================== LINKS INTERNOS SEO ==================== */}
            <section className="creators-internal-links">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="creators-internal-links__grid">
                            <Link to="/territorios-forales" className="creators-internal-links__card">
                                <Map size={20} />
                                <div>
                                    <strong>País Vasco y Navarra</strong>
                                    <span>Régimen foral: deducciones exclusivas que no existen en el régimen común</span>
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
                                Sin permanencia. Sin sorpresas. El asistente fiscal que entiende
                                tu actividad como creador digital mejor que ninguna gestoría tradicional.
                            </p>
                            <Link to="/subscribe" className="btn btn-primary btn-lg">
                                Empezar ahora
                                <ArrowRight size={20} />
                            </Link>
                            <p className="creators-cta__note">
                                49 EUR/mes. Cancela cuando quieras.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
