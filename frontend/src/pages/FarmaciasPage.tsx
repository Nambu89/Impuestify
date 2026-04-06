import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useSEO } from '../hooks/useSEO'
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
            'No necesitas presentar el Modelo 303. Nuestro sistema lo sabe automáticamente y te evita errores con la AEAT.',
    },
    {
        icon: Building2,
        title: 'Fondo de comercio',
        description:
            'Amortiza la compra de tu farmacia al 5% anual durante 20 años. Te lo calculamos con las reglas del IRPF.',
    },
    {
        icon: Award,
        title: 'Cuotas colegiales y RC profesional',
        description:
            'Deducciones específicas que tu asesor general puede pasar por alto. El colegio de farmacéuticos y el seguro de responsabilidad civil son 100% deducibles.',
    },
]

const FEATURES = [
    {
        icon: Calculator,
        title: 'Simulador IRPF adaptado a farmacias',
        description:
            'Motor de cálculo que conoce las particularidades fiscales de las oficinas de farmacia: amortizaciones, gastos de personal, suministros y formación continua.',
    },
    {
        icon: FileText,
        title: 'Recargo de Equivalencia automático',
        description:
            'Sin Modelo 303. El sistema detecta tu actividad farmacéutica (IAE 652.1 / CNAE 47.73) y aplica el régimen especial de Recargo de Equivalencia automáticamente.',
    },
    {
        icon: Award,
        title: 'Deducciones específicas',
        description:
            'Colegio de farmacéuticos, seguro RC profesional, formación continua, congresos y fondo de comercio. Todas las deducciones que te corresponden como farmacéutico.',
    },
    {
        icon: Calendar,
        title: 'Calendario fiscal personalizado',
        description:
            'Alertas para el Modelo 130/131, Renta y pagos fraccionados. Nunca más una multa por presentación fuera de plazo.',
    },
]

const FAQS = [
    {
        q: '¿Puedo constituir mi farmacia como Sociedad Limitada?',
        a: 'No. La Ley 16/1997 de Regulación de Servicios de las Oficinas de Farmacia establece que la propiedad y titularidad de las oficinas de farmacia está reservada exclusivamente a farmacéuticos licenciados. No es posible constituir la farmacia como SL, SA ni ninguna otra forma societaria. Siempre tributa como actividad económica en el IRPF del farmacéutico titular.',
    },
    {
        q: '¿Tengo que presentar el Modelo 303 de IVA?',
        a: 'No, si eres farmacéutico titular y vendes exclusivamente a consumidores finales. Las farmacias están sujetas al Régimen Especial de Recargo de Equivalencia (artículos 154-163 LIVA). Tus proveedores te cobran el IVA más el recargo correspondiente (0,5% para medicamentos al 4%, 1,4% para productos sanitarios al 10%, 5,2% para parafarmacia al 21%), y tú no presentas liquidación de IVA trimestral.',
    },
    {
        q: '¿Puedo deducir el fondo de comercio de la farmacia?',
        a: 'Sí. El fondo de comercio de la farmacia (la diferencia entre el precio de compra y el valor contable de los activos) es amortizable al 5% anual durante un máximo de 20 años, según el artículo 12.6 de la Ley del Impuesto sobre Sociedades, aplicable por remisión a actividades económicas en IRPF. Es una deducción relevante: una farmacia comprada por 600.000 EUR con activos por 200.000 EUR permite deducir 20.000 EUR anuales.',
    },
    {
        q: '¿Qué IVA aplica a los productos de mi farmacia?',
        a: 'Los medicamentos de uso humano tributan al tipo superreducido del 4% de IVA. Los productos sanitarios, compresas, tampones y pañales tributan al tipo reducido del 10%. Los productos de parafarmacia (cosméticos, dietéticos, higiene no sanitaria) tributan al tipo general del 21%. Recuerda que con el Recargo de Equivalencia, tú no repercutes IVA al consumidor: lo absorbe el precio final.',
    },
    {
        q: '¿Qué gastos puedo deducir como farmacéutico?',
        a: 'Además de los gastos generales de actividad económica (suministros, alquiler, personal), puedes deducir: cuota del Colegio Oficial de Farmacéuticos (obligatoria), seguro de responsabilidad civil profesional, formación continua y congresos farmacéuticos relacionados con tu actividad, amortización del fondo de comercio (5% anual) y amortización del local comercial si es de tu propiedad.',
    },
]

export default function FarmaciasPage() {
    const [openFaq, setOpenFaq] = useState<number | null>(null)

    useSEO({
        title: 'Impuestos Farmacia | Recargo Equivalencia | IRPF Farmacéuticos | Impuestify',
        description: 'Herramienta fiscal con IA para farmacéuticos. Recargo de Equivalencia automático, IRPF, deducciones específicas farmacia.',
        canonical: '/farmacias',
        keywords: 'impuestos farmacia, recargo equivalencia farmacia, IRPF farmacéutico, deducciones farmacia, IVA medicamentos',
        schema: {
            '@context': 'https://schema.org',
            '@type': 'SoftwareApplication',
            name: 'Impuestify para Farmacias',
            url: 'https://impuestify.com/farmacias',
            applicationCategory: 'FinanceApplication',
            operatingSystem: 'Web',
            offers: { '@type': 'Offer', price: '39', priceCurrency: 'EUR' },
            author: { '@type': 'Organization', name: 'Impuestify', url: 'https://impuestify.com' }
        }
    })

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
                                Sector Farmacéutico
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
                            Recargo de Equivalencia, IRPF, deducciones específicas y más.
                            Todo en una herramienta pensada para farmacéuticos.
                        </p>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <div className="farmacias-hero__actions">
                            <Link to="/register" className="btn btn-primary btn-lg farmacias-hero__cta">
                                Empieza gratis
                                <ArrowRight size={20} />
                            </Link>
                            <a href="#features" className="btn btn-secondary btn-lg">
                                Ver qué incluye
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
                            La fiscalidad farmacéutica tiene particularidades que los asesores generalistas suelen desconocer
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
                        <h2 className="section-title">Qué incluye Impuestify para farmacias</h2>
                        <p className="section-subtitle">
                            Plan Autónomo — 39 EUR/mes IVA incluido. Todas las herramientas que necesitas como farmacéutico titular.
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
                        <h2 className="section-title">Ahorra con respecto a una asesoría especializada</h2>
                        <p className="section-subtitle">
                            Las asesorías especializadas en farmacias cobran entre 200 y 400 EUR/mes
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="farmacias-pricing__grid">
                            {/* Asesoría tradicional */}
                            <div className="farmacias-pricing__card farmacias-pricing__card--traditional">
                                <div className="farmacias-pricing__card-header">
                                    <Building2 size={24} />
                                    <h3>Asesoría especializada</h3>
                                </div>
                                <div className="farmacias-pricing__amount">
                                    <span className="farmacias-pricing__range">200 – 400</span>
                                    <span className="farmacias-pricing__currency">EUR/mes</span>
                                </div>
                                <ul className="farmacias-pricing__list">
                                    <li><X size={16} className="farmacias-pricing__icon-no" /><span>Horario de oficina</span></li>
                                    <li><X size={16} className="farmacias-pricing__icon-no" /><span>Sin IA ni respuestas inmediatas</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-yes" /><span>Conocimiento fiscal farmacéutico</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-yes" /><span>Presentación de modelos</span></li>
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
                                    <h3>Impuestify Plan Autónomo</h3>
                                </div>
                                <div className="farmacias-pricing__amount">
                                    <span className="farmacias-pricing__value">39</span>
                                    <span className="farmacias-pricing__currency">EUR/mes <small>IVA incl.</small></span>
                                </div>
                                <ul className="farmacias-pricing__list">
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Disponible 24/7</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>IA especializada en farmacias</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Recargo de Equivalencia automático</span></li>
                                    <li><CheckCircle size={16} className="farmacias-pricing__icon-highlight" /><span>Deducciones específicas farmacéuticas</span></li>
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
                            <strong>Ahorra hasta 4.300 EUR al año</strong> con respecto a una asesoría especializada en farmacias.
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
                            Las dudas más habituales sobre la fiscalidad de las oficinas de farmacia
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
                                    Artículos 154-163 LIVA. Tu proveedor te cobra IVA + RE (0,5% al 4%, 1,4% al 10%, 5,2% al 21%).
                                    Tú no presentas el 303 ni llevas libros registro de IVA. Sí presentas el Modelo 130/131 de IRPF.
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
                                el fondo de comercio y todas las deducciones específicas de tu profesión.
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
