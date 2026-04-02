import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
    ArrowRight, CheckCircle, X, ChevronLeft, Zap,
    FileText, Calculator, Shield, ChevronDown, Heart,
    Building2, Award, Calendar, BookOpen
} from 'lucide-react'
import FadeContent from '../components/reactbits/FadeContent'
import SpotlightCard from '../components/reactbits/SpotlightCard'
import GradientText from '../components/reactbits/GradientText'
import './FarmaciasPage.css'

const PAIN_POINTS = [
    {
        icon: FileText,
        title: 'Recargo de Equivalencia confuso',
        description:
            'No necesitas presentar el Modelo 303. Nuestro sistema lo sabe autom\u00e1ticamente y te evita errores con la AEAT.',
    },
    {
        icon: Building2,
        title: 'Fondo de comercio',
        description:
            'Amortiza la compra de tu farmacia al 5% anual durante 20 a\u00f1os. Te lo calculamos con las reglas del IRPF.',
    },
    {
        icon: Award,
        title: 'Cuotas colegiales y RC profesional',
        description:
            'Deducciones espec\u00edficas que tu asesor general puede pasar por alto. El colegio de farmac\u00e9uticos y el seguro de responsabilidad civil son 100% deducibles.',
    },
]

const FEATURES = [
    {
        icon: Calculator,
        title: 'Simulador IRPF adaptado a farmacias',
        description:
            'Motor de c\u00e1lculo que conoce las particularidades fiscales de las oficinas de farmacia: amortizaciones, gastos de personal, suministros y formaci\u00f3n continua.',
    },
    {
        icon: FileText,
        title: 'Recargo de Equivalencia autom\u00e1tico',
        description:
            'Sin Modelo 303. El sistema detecta tu actividad farmac\u00e9utica (IAE 652.1 / CNAE 47.73) y aplica el r\u00e9gimen especial de Recargo de Equivalencia autom\u00e1ticamente.',
    },
    {
        icon: Award,
        title: 'Deducciones espec\u00edficas',
        description:
            'Colegio de farmac\u00e9uticos, seguro RC profesional, formaci\u00f3n continua, congresos y fondo de comercio. Todas las deducciones que te corresponden como farmac\u00e9utico.',
    },
    {
        icon: Calendar,
        title: 'Calendario fiscal personalizado',
        description:
            'Alertas para el Modelo 130/131, Renta y pagos fraccionados. Nunca m\u00e1s una multa por presentaci\u00f3n fuera de plazo.',
    },
]

const FAQS = [
    {
        q: '\u00bfPuedo constituir mi farmacia como Sociedad Limitada?',
        a: 'No. La Ley 16/1997 de Regulaci\u00f3n de Servicios de las Oficinas de Farmacia establece que la propiedad y titularidad de las oficinas de farmacia est\u00e1 reservada exclusivamente a farmac\u00e9uticos licenciados. No es posible constituir la farmacia como SL, SA ni ninguna otra forma societaria. Siempre tributa como actividad econ\u00f3mica en el IRPF del farmac\u00e9utico titular.',
    },
    {
        q: '\u00bfTengo que presentar el Modelo 303 de IVA?',
        a: 'No, si eres farmac\u00e9utico titular y vendes exclusivamente a consumidores finales. Las farmacias est\u00e1n sujetas al R\u00e9gimen Especial de Recargo de Equivalencia (art\u00edculos 154-163 LIVA). Tus proveedores te cobran el IVA m\u00e1s el recargo correspondiente (0,5% para medicamentos al 4%, 1,4% para productos sanitarios al 10%, 5,2% para parafarmacia al 21%), y t\u00fa no presentas liquidaci\u00f3n de IVA trimestral.',
    },
    {
        q: '\u00bfPuedo deducir el fondo de comercio de la farmacia?',
        a: 'S\u00ed. El fondo de comercio de la farmacia (la diferencia entre el precio de compra y el valor contable de los activos) es amortizable al 5% anual durante un m\u00e1ximo de 20 a\u00f1os, seg\u00fan el art\u00edculo 12.6 de la Ley del Impuesto sobre Sociedades, aplicable por remisi\u00f3n a actividades econ\u00f3micas en IRPF. Es una deducci\u00f3n relevante: una farmacia comprada por 600.000 EUR con activos por 200.000 EUR permite deducir 20.000 EUR anuales.',
    },
    {
        q: '\u00bfQu\u00e9 IVA aplica a los productos de mi farmacia?',
        a: 'Los medicamentos de uso humano tributan al tipo superreducido del 4% de IVA. Los productos sanitarios, compresas, tampones y pa\u00f1ales tributan al tipo reducido del 10%. Los productos de parafarmacia (cosm\u00e9ticos, diet\u00e9ticos, higiene no sanitaria) tributan al tipo general del 21%. Recuerda que con el Recargo de Equivalencia, t\u00fa no repercutes IVA al consumidor: lo absorbe el precio final.',
    },
    {
        q: '\u00bfQu\u00e9 gastos puedo deducir como farmac\u00e9utico?',
        a: 'Adem\u00e1s de los gastos generales de actividad econ\u00f3mica (suministros, alquiler, personal), puedes deducir: cuota del Colegio Oficial de Farmac\u00e9uticos (obligatoria), seguro de responsabilidad civil profesional, formaci\u00f3n continua y congresos farmac\u00e9uticos relacionados con tu actividad, amortizaci\u00f3n del fondo de comercio (5% anual) y amortizaci\u00f3n del local comercial si es de tu propiedad.',
    },
]

export default function FarmaciasPage() {
    const [openFaq, setOpenFaq] = useState<number | null>(null)

    useEffect(() => {
        document.title = 'Impuestos Farmacia | Recargo Equivalencia | IRPF Farmac\u00e9uticos | Impuestify'

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
            'Herramienta fiscal con IA para farmac\u00e9uticos. Recargo de Equivalencia autom\u00e1tico, deducciones espec\u00edficas, simulador IRPF. Plan Aut\u00f3nomo desde 39 EUR/mes.'
        )
        setMeta(
            'keywords',
            'impuestos farmacia, IRPF farmac\u00e9utico, recargo equivalencia farmacia, deducciones farmacia, fondo comercio farmacia, IVA medicamentos, IAE 652.1, fiscal farmac\u00e9utico, asesor fiscal farmacia, modelo 130 farmacia'
        )
        setMeta('geo.region', 'ES')
        setMeta('geo.placename', 'Espa\u00f1a')
        setOg('og:title', 'Impuestos Farmacia | Recargo Equivalencia | IRPF Farmac\u00e9uticos | Impuestify')
        setOg(
            'og:description',
            'Herramienta fiscal con IA para farmac\u00e9uticos. Recargo de Equivalencia autom\u00e1tico, deducciones espec\u00edficas, simulador IRPF adaptado a farmacias. 39 EUR/mes.'
        )
        setOg('og:type', 'website')
        setOg('og:url', 'https://impuestify.com/farmacias')

        // Schema.org structured data
        const existingScript = document.querySelector('#farmacias-schema-org')
        if (!existingScript) {
            const script = document.createElement('script')
            script.id = 'farmacias-schema-org'
            script.type = 'application/ld+json'
            script.text = JSON.stringify({
                '@context': 'https://schema.org',
                '@type': 'SoftwareApplication',
                name: 'Impuestify para Farmacias',
                description:
                    'Herramienta fiscal con IA para farmac\u00e9uticos en Espa\u00f1a. Recargo de Equivalencia, deducciones espec\u00edficas, simulador IRPF adaptado a oficinas de farmacia.',
                applicationCategory: 'FinanceApplication',
                operatingSystem: 'Web',
                url: 'https://impuestify.com/farmacias',
                offers: {
                    '@type': 'Offer',
                    price: '39',
                    priceCurrency: 'EUR',
                    priceSpecification: {
                        '@type': 'UnitPriceSpecification',
                        price: '39',
                        priceCurrency: 'EUR',
                        unitCode: 'MON',
                    },
                },
                breadcrumb: {
                    '@type': 'BreadcrumbList',
                    itemListElement: [
                        { '@type': 'ListItem', position: 1, name: 'Inicio', item: 'https://impuestify.com' },
                        {
                            '@type': 'ListItem',
                            position: 2,
                            name: 'Farmacias',
                            item: 'https://impuestify.com/farmacias',
                        },
                    ],
                },
                mainEntity: {
                    '@type': 'FAQPage',
                    mainEntity: FAQS.map((f) => ({
                        '@type': 'Question',
                        name: f.q,
                        acceptedAnswer: { '@type': 'Answer', text: f.a },
                    })),
                },
            })
            document.head.appendChild(script)
        }

        return () => {
            document.title = 'Impuestify \u2014 Asistente Fiscal con IA'
            const schema = document.querySelector('#farmacias-schema-org')
            if (schema) schema.remove()
        }
    }, [])

    return (
        <div className="farmacias-page">
            {/* Back link */}
            <div className="farmacias-back">
                <div className="container">
                    <Link to="/" className="farmacias-back__link">
                        <ChevronLeft size={16} />
                        Volver al inicio
                    </Link>
                </div>
            </div>

            {/* ==================== HERO ==================== */}
            <section className="farmacias-hero">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="farmacias-hero__badges">
                            <span className="farmacias-hero__badge farmacias-hero__badge--new">
                                NUEVO
                            </span>
                            <span className="farmacias-hero__badge farmacias-hero__badge--sector">
                                <Heart size={14} />
                                Sector Farmac\u00e9utico
                            </span>
                        </div>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <h1 className="farmacias-hero__title">
                            La fiscalidad de tu farmacia,{' '}
                            <GradientText
                                colors={['#059669', '#10b981', '#34d399', '#059669']}
                                animationSpeed={6}
                                className="farmacias-hero__gradient"
                            >
                                resuelta con IA
                            </GradientText>
                        </h1>
                        <p className="farmacias-hero__subtitle">
                            Recargo de Equivalencia, IRPF, deducciones espec\u00edficas y m\u00e1s.
                            Todo en una herramienta pensada para farmac\u00e9uticos.
                        </p>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <div className="farmacias-hero__actions">
                            <Link to="/register" className="btn btn-primary btn-lg farmacias-hero__cta">
                                Empieza gratis
                                <ArrowRight size={20} />
                            </Link>
                            <a href="#features" className="btn btn-secondary btn-lg">
                                Ver qu\u00e9 incluye
                            </a>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== PAIN POINTS ==================== */}
            <section className="farmacias-pain">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Problemas que resolvemos</h2>
                        <p className="section-subtitle">
                            La fiscalidad farmac\u00e9utica tiene particularidades que los asesores generalistas suelen desconocer
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="farmacias-pain__grid">
                            {PAIN_POINTS.map((item, i) => {
                                const Icon = item.icon
                                return (
                                    <div key={i} className="farmacias-pain__card">
                                        <div className="farmacias-pain__icon">
                                            <Icon size={24} />
                                        </div>
                                        <div>
                                            <h3>{item.title}</h3>
                                            <p>{item.description}</p>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== FEATURES ==================== */}
            <section className="farmacias-features" id="features">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Qu\u00e9 incluye Impuestify para farmacias</h2>
                        <p className="section-subtitle">
                            Plan Aut\u00f3nomo \u2014 39 EUR/mes IVA incluido. Todas las herramientas que necesitas como farmac\u00e9utico titular.
                        </p>
                    </FadeContent>
                    <div className="farmacias-features__grid">
                        {FEATURES.map((f, i) => {
                            const Icon = f.icon
                            return (
                                <FadeContent key={f.title} delay={i * 80} duration={500}>
                                    <SpotlightCard
                                        className="farmacias-feature__card"
                                        spotlightColor="rgba(5, 150, 105, 0.1)"
                                    >
                                        <div className="farmacias-feature__icon">
                                            <Icon size={22} />
                                        </div>
                                        <h3 className="farmacias-feature__title">{f.title}</h3>
                                        <p className="farmacias-feature__desc">{f.description}</p>
                                    </SpotlightCard>
                                </FadeContent>
                            )
                        })}
                    </div>
                </div>
            </section>

            {/* ==================== PRICING COMPARISON ==================== */}
            <section className="farmacias-pricing">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Ahorra con respecto a una asesor\u00eda especializada</h2>
                        <p className="section-subtitle">
                            Las asesor\u00edas especializadas en farmacias cobran entre 200 y 400 EUR/mes
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="farmacias-pricing__grid">
                            {/* Asesor\u00eda tradicional */}
                            <div className="farmacias-pricing__card farmacias-pricing__card--traditional">
                                <div className="farmacias-pricing__card-header">
                                    <Building2 size={24} />
                                    <h3>Asesor\u00eda especializada</h3>
                                </div>
                                <div className="farmacias-pricing__amount">
                                    <span className="farmacias-pricing__range">200 \u2013 400</span>
                                    <span className="farmacias-pricing__currency">EUR/mes</span>
                                </div>
                                <ul className="farmacias-pricing__list">
                                    <li><X size={16} className="farmacias-pricing__icon-no" /><span>Horario de oficina</span></li>
                                    <li><X size={16} className="farmacias-pricing__icon-no" /><span>Sin IA ni respuestas inmediatas</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-yes" /><span>Conocimiento fiscal farmac\u00e9utico</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-yes" /><span>Presentaci\u00f3n de modelos</span></li>
                                </ul>
                            </div>

                            {/* Impuestify */}
                            <SpotlightCard className="farmacias-pricing__card farmacias-pricing__card--impuestify" spotlightColor="rgba(5, 150, 105, 0.12)">
                                <div className="farmacias-pricing__badge">
                                    <Zap size={13} />
                                    Recomendado
                                </div>
                                <div className="farmacias-pricing__card-header">
                                    <Shield size={24} />
                                    <h3>Impuestify Plan Aut\u00f3nomo</h3>
                                </div>
                                <div className="farmacias-pricing__amount">
                                    <span className="farmacias-pricing__value">39</span>
                                    <span className="farmacias-pricing__currency">EUR/mes <small>IVA incl.</small></span>
                                </div>
                                <ul className="farmacias-pricing__list">
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Disponible 24/7</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>IA especializada en farmacias</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Recargo de Equivalencia autom\u00e1tico</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Deducciones espec\u00edficas farmac\u00e9uticas</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Simulador IRPF con fondo de comercio</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Calendario fiscal personalizado</span></li>
                                </ul>
                                <Link to="/register" className="btn btn-lg farmacias-pricing__cta">
                                    Empieza por 39 EUR/mes
                                    <ArrowRight size={18} />
                                </Link>
                            </SpotlightCard>
                        </div>
                        <p className="farmacias-pricing__savings">
                            <strong>Ahorra hasta 4.300 EUR al a\u00f1o</strong> con respecto a una asesor\u00eda especializada en farmacias.
                        </p>
                        <p className="farmacias-pricing__note">
                            Sin permanencia. Cancela cuando quieras. Pago seguro con Stripe.
                        </p>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== FAQ ==================== */}
            <section className="farmacias-faq">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Preguntas frecuentes</h2>
                        <p className="section-subtitle">
                            Las dudas m\u00e1s habituales sobre la fiscalidad de las oficinas de farmacia
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="farmacias-faq__list">
                            {FAQS.map((faq, i) => (
                                <div
                                    key={i}
                                    className={`farmacias-faq__item${openFaq === i ? ' farmacias-faq__item--open' : ''}`}
                                >
                                    <button
                                        className="farmacias-faq__question"
                                        onClick={() => setOpenFaq(openFaq === i ? null : i)}
                                        aria-expanded={openFaq === i}
                                    >
                                        <span>{faq.q}</span>
                                        <ChevronDown
                                            size={18}
                                            className={`farmacias-faq__chevron${openFaq === i ? ' farmacias-faq__chevron--open' : ''}`}
                                        />
                                    </button>
                                    {openFaq === i && (
                                        <div className="farmacias-faq__answer">
                                            <p>{faq.a}</p>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== RE INFO ==================== */}
            <section className="farmacias-re-info">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <div className="farmacias-re-info__inner">
                            <div className="farmacias-re-info__icon">
                                <BookOpen size={28} />
                            </div>
                            <div className="farmacias-re-info__content">
                                <h3 className="farmacias-re-info__title">Recargo de Equivalencia: lo que debes saber</h3>
                                <p className="farmacias-re-info__desc">
                                    Art\u00edculos 154-163 LIVA. Tu proveedor te cobra IVA + RE (0,5% al 4%, 1,4% al 10%, 5,2% al 21%).
                                    T\u00fa no presentas el 303 ni llevas libros registro de IVA. S\u00ed presentas el Modelo 130/131 de IRPF.
                                </p>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ==================== CTA FINAL ==================== */}
            <section className="farmacias-cta">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="farmacias-cta__card">
                            <div className="farmacias-cta__icon">
                                <Heart size={36} />
                            </div>
                            <h2>Prueba Impuestify para tu farmacia</h2>
                            <p>
                                El asistente fiscal con IA que entiende el Recargo de Equivalencia,
                                el fondo de comercio y todas las deducciones espec\u00edficas de tu profesi\u00f3n.
                            </p>
                            <Link to="/register" className="btn btn-lg farmacias-cta__btn">
                                Empieza gratis
                                <ArrowRight size={20} />
                            </Link>
                            <p className="farmacias-cta__note">
                                39 EUR/mes IVA incluido. Sin permanencia. Cancela cuando quieras.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
