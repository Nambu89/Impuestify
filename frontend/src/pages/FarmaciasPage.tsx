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
        title: 'Recargo de Equivalencia',
        description:
            'Con la farmacia no tocas el Modelo 303. La plataforma detecta tu régimen y deja fuera el IVA trimestral.',
    },
    {
        icon: Building2,
        title: 'Fondo de comercio',
        description:
            'La compra de la farmacia se amortiza al 5 % anual durante 20 años. Aplicamos el cálculo dentro de tu IRPF.',
    },
    {
        icon: Award,
        title: 'Cuotas colegiales y RC profesional',
        description:
            'Deducciones que un asesor generalista deja fuera: cuota del colegio de farmacéuticos y seguro de responsabilidad civil, ambas al 100 %.',
    },
]

const FEATURES = [
    {
        icon: Calculator,
        title: 'Simulador IRPF para farmacias',
        description:
            'Un motor de cálculo que ya conoce las particularidades de la oficina de farmacia: amortizaciones, personal, suministros y formación continua.',
    },
    {
        icon: FileText,
        title: 'Recargo de Equivalencia, sin líos',
        description:
            'Sin Modelo 303. Al detectar el IAE 652.1 / CNAE 47.73 se activa el régimen especial automáticamente.',
    },
    {
        icon: Award,
        title: 'Deducciones específicas',
        description:
            'Colegio, RC profesional, formación, congresos y fondo de comercio. Lo que te toca como farmacéutico, ya contemplado.',
    },
    {
        icon: Calendar,
        title: 'Calendario fiscal personalizado',
        description:
            'Avisos del 130/131, de la Renta y de los pagos fraccionados. Para no volver a llegar tarde a la AEAT.',
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
        title: 'Fiscalidad para farmacias y farmacéuticos — Impuestify',
        description: 'Cómo gestionar los impuestos de una farmacia: recargo de equivalencia, IRPF por estimación directa, amortización del fondo de comercio y gastos propios.',
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
                            Recargo de Equivalencia, IRPF y deducciones específicas de la oficina de farmacia
                            en una sola herramienta.
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
                        <h2 className="section-title">Lo que te ahorras</h2>
                        <p className="section-subtitle">
                            La fiscalidad de la farmacia tiene matices que los asesores generalistas suelen pasar por alto.
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
                        <h2 className="section-title">Qué incluye</h2>
                        <p className="section-subtitle">
                            Plan Autónomo, 39 EUR/mes con IVA. Lo que necesitas como titular de la oficina de farmacia.
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
                        <h2 className="section-title">Lo que cuesta una asesoría especializada</h2>
                        <p className="section-subtitle">
                            Las asesorías especializadas en farmacia cobran entre 200 y 400 EUR al mes.
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
                            <strong>Ahorro de hasta 4.300 EUR al año</strong> frente a una asesoría especializada en farmacia.
                        </p>
                        <p className="farmacias-pricing__note">
                            Sin permanencia. Cancelas cuando quieras. Pago con Stripe.
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
                            Dudas que nos repite la gente cuando abre o compra una farmacia.
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
                                <h3 className="farmacias-re-info__title">Recargo de Equivalencia en breve</h3>
                                <p className="farmacias-re-info__desc">
                                    Artículos 154-163 de la LIVA. El proveedor te cobra IVA más RE (0,5 % al 4 %, 1,4 % al 10 %, 5,2 % al 21 %).
                                    Tú no presentas el 303 ni llevas libros registro de IVA. Sí presentas el 130/131 por IRPF.
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
                            <h2>Prueba Impuestify en tu farmacia</h2>
                            <p>
                                Asistente fiscal con IA que entiende el Recargo de Equivalencia, el fondo de comercio
                                y las deducciones propias del sector farmacéutico.
                            </p>
                            <Link to="/register" className="btn btn-lg farmacias-cta__btn">
                                Empieza gratis
                                <ArrowRight size={20} />
                            </Link>
                            <p className="farmacias-cta__note">
                                39 EUR/mes con IVA. Sin permanencia, cancelas cuando quieras.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
