import { Link } from 'react-router-dom'
import { useSEO } from '../hooks/useSEO'
import {
    ArrowRight, CheckCircle, Calculator, Shield,
    FileText, TrendingDown, Users, ChevronLeft, Info
} from 'lucide-react'
import FadeContent from '../components/reactbits/FadeContent'
import SpotlightCard from '../components/reactbits/SpotlightCard'
import GradientText from '../components/reactbits/GradientText'
import CountUp from '../components/reactbits/CountUp'
import './CeutaMelillaPage.css'

const VENTAJAS = [
    {
        icon: TrendingDown,
        title: 'Deducción 60% cuota íntegra IRPF',
        article: 'Art. 68.4 LIRPF',
        description:
            'Los residentes en Ceuta y Melilla tienen derecho a una deducción del 60% de la parte de la cuota íntegra estatal y autonómica correspondiente a las rentas obtenidas en dichas ciudades.',
        example:
            'Si tu cuota íntegra es de 5.000 €, podrías deducirte hasta 3.000 € — pagando solo 2.000 €.',
    },
    {
        icon: Shield,
        title: 'IPSI en lugar de IVA',
        article: 'Ley 8/1991',
        description:
            'Ceuta y Melilla no están sujetas al IVA. En su lugar aplica el Impuesto sobre la Producción, los Servicios y la Importación (IPSI), con tipos generalmente inferiores al IVA peninsular.',
        example:
            'Tipo general IPSI: 4% frente al 21% del IVA ordinario. Un ahorro significativo en consumo e inversión.',
    },
    {
        icon: Users,
        title: '50% bonificación SS autónomos',
        article: 'Disp. Adic. 3ª Ley 20/2007',
        description:
            'Los trabajadores por cuenta propia con residencia en Ceuta o Melilla disfrutan de una bonificación del 50% en sus cuotas a la Seguridad Social cuando operen principalmente en estas ciudades.',
        example:
            'Si tu cuota mensual es de 300 €, la bonificación reduce el coste a 150 € al mes — 1.800 € al año.',
    },
    {
        icon: FileText,
        title: 'Sin impuesto sobre sucesiones y donaciones',
        article: 'Régimen especial CC.AA.',
        description:
            'Las bonificaciones sobre el Impuesto de Sucesiones y Donaciones varían según la legislación aplicable, con condiciones especialmente favorables en estas ciudades autónomas.',
        example:
            'Las herencias de padres a hijos pueden tener bonificaciones de hasta el 99% de la cuota.',
    },
]

export default function CeutaMelillaPage() {
    useSEO({
        title: 'Ventajas Fiscales en Ceuta y Melilla | Impuestify',
        description: 'Descubre las ventajas fiscales exclusivas de Ceuta y Melilla: deducción 60% cuota IRPF, IPSI en lugar de IVA, bonificaciones IS.',
        canonical: '/ceuta-melilla',
        keywords: 'fiscalidad Ceuta Melilla, IPSI, deducción 60% IRPF, ventajas fiscales Ceuta, impuestos Melilla',
        schema: [
            {
                '@context': 'https://schema.org',
                '@type': 'FAQPage',
                mainEntity: [
                    {
                        '@type': 'Question',
                        name: '¿Me afecta la deducción si trabajo en Ceuta pero vivo en la Península?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'La deducción del 60% aplica a residentes fiscales en Ceuta o Melilla. Si resides en la Península pero obtienes rentas en Ceuta, el tratamiento puede variar según tu situación concreta.',
                        },
                    },
                    {
                        '@type': 'Question',
                        name: '¿El IPSI equivale exactamente al IVA?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'No son exactamente equivalentes. El IPSI tiene sus propios tipos y reglas. No hay derecho a deducción del IVA soportado como en el régimen general. Es un impuesto local con lógica propia.',
                        },
                    },
                    {
                        '@type': 'Question',
                        name: '¿La bonificación del 50% en la Seguridad Social aplica a todos los autónomos en Ceuta?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'Aplica a autónomos que residan y ejerzan su actividad principalmente en Ceuta o Melilla. Existen restricciones para actividades de comercio exterior o cuya clientela esté principalmente fuera de estas ciudades.',
                        },
                    },
                    {
                        '@type': 'Question',
                        name: '¿Cómo puede ayudarme Impuestify con Ceuta y Melilla?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'El motor de IA de Impuestify tiene acceso a la normativa específica de Ceuta y Melilla: el Art. 68.4 LIRPF, la Ley del IPSI y la normativa de Seguridad Social para autónomos. Puede calcular tu IRPF aplicando la deducción correcta y descubrir todas las ventajas aplicables a tu caso.',
                        },
                    },
                ],
            },
            {
                '@context': 'https://schema.org',
                '@type': 'BreadcrumbList',
                itemListElement: [
                    { '@type': 'ListItem', position: 1, name: 'Inicio', item: 'https://impuestify.com' },
                    { '@type': 'ListItem', position: 2, name: 'Ceuta y Melilla', item: 'https://impuestify.com/ceuta-melilla' },
                ],
            },
        ],
    })

    return (
        <div className="ceuta-page">
            {/* Back link */}
            <div className="ceuta-back">
                <div className="container">
                    <Link to="/" className="ceuta-back__link">
                        <ChevronLeft size={16} />
                        Volver al inicio
                    </Link>
                </div>
            </div>

            {/* Hero */}
            <section className="ceuta-hero">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="ceuta-hero__badge">
                            <Shield size={16} />
                            <span>Régimen Fiscal Especial</span>
                        </div>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <h1 className="ceuta-hero__title">
                            Ventajas fiscales en{' '}
                            <GradientText
                                colors={['#1a56db', '#06b6d4', '#3b82f6', '#1a56db']}
                                animationSpeed={6}
                                className="ceuta-hero__gradient"
                            >
                                Ceuta y Melilla
                            </GradientText>
                        </h1>
                        <p className="ceuta-hero__subtitle">
                            Las ciudades autónomas de Ceuta y Melilla tienen un{' '}
                            <strong>régimen fiscal especial</strong> con ventajas únicas
                            en IRPF, IVA y Seguridad Social. Impuestify calcula tu ahorro
                            real con IA y fuentes oficiales.
                        </p>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <div className="ceuta-hero__stats">
                            <div className="ceuta-hero__stat">
                                <span className="ceuta-hero__stat-value">
                                    <CountUp to={60} duration={2} />
                                    <span>%</span>
                                </span>
                                <span className="ceuta-hero__stat-label">
                                    Deducción IRPF
                                </span>
                            </div>
                            <div className="ceuta-hero__stat">
                                <span className="ceuta-hero__stat-value">
                                    <CountUp to={4} duration={1.5} />
                                    <span>%</span>
                                </span>
                                <span className="ceuta-hero__stat-label">
                                    Tipo IPSI general
                                </span>
                            </div>
                            <div className="ceuta-hero__stat">
                                <span className="ceuta-hero__stat-value">
                                    <CountUp to={50} duration={2} />
                                    <span>%</span>
                                </span>
                                <span className="ceuta-hero__stat-label">
                                    Bonificación SS autónomos
                                </span>
                            </div>
                        </div>
                    </FadeContent>
                    <FadeContent delay={300} duration={600}>
                        <div className="ceuta-hero__actions">
                            <Link to="/register" className="btn btn-primary btn-lg">
                                Calcula tu ahorro fiscal
                                <ArrowRight size={20} />
                            </Link>
                            <a href="#ventajas" className="btn btn-secondary btn-lg">
                                Ver ventajas
                            </a>
                        </div>
                    </FadeContent>
                    <FadeContent delay={400} duration={800}>
                        <img
                            src="/images/hero-ceuta-melilla.webp"
                            alt="Ilustración isométrica de Ceuta y Melilla con el 60% de deducción IRPF"
                            className="ceuta-hero__image"
                            loading="lazy"
                            width={1376}
                            height={768}
                        />
                    </FadeContent>
                </div>
            </section>

            {/* Ventajas principales */}
            <section className="ceuta-ventajas" id="ventajas">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            Principales ventajas fiscales
                        </h2>
                        <p className="section-subtitle">
                            Un régimen especial diseñado para compensar el alejamiento
                            geográfico y potenciar la economía local
                        </p>
                    </FadeContent>
                    <div className="ceuta-ventajas__grid">
                        {VENTAJAS.map((v, i) => {
                            const Icon = v.icon
                            return (
                                <FadeContent key={v.title} delay={i * 100} duration={500}>
                                    <SpotlightCard
                                        className="ceuta-ventaja__card"
                                        spotlightColor="rgba(26, 86, 219, 0.08)"
                                    >
                                        <div className="ceuta-ventaja__header">
                                            <div className="ceuta-ventaja__icon">
                                                <Icon size={24} />
                                            </div>
                                            <span className="ceuta-ventaja__article">
                                                {v.article}
                                            </span>
                                        </div>
                                        <h3 className="ceuta-ventaja__title">{v.title}</h3>
                                        <p className="ceuta-ventaja__desc">{v.description}</p>
                                        <div className="ceuta-ventaja__example">
                                            <Info size={14} />
                                            <span>{v.example}</span>
                                        </div>
                                    </SpotlightCard>
                                </FadeContent>
                            )
                        })}
                    </div>
                </div>
            </section>

            {/* IRPF Detail */}
            <section className="ceuta-irpf">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            Cómo funciona la deducción del 60% en el IRPF
                        </h2>
                        <p className="section-subtitle">
                            Art. 68.4 de la Ley 35/2006 del IRPF — Deducción por rentas
                            obtenidas en Ceuta o Melilla
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="ceuta-irpf__grid">
                            <div className="ceuta-irpf__step">
                                <div className="ceuta-irpf__step-num">1</div>
                                <div className="ceuta-irpf__step-content">
                                    <h3>Calcula tu cuota íntegra total</h3>
                                    <p>
                                        La cuota íntegra es el resultado de aplicar los
                                        tipos de la escala del IRPF a tu base liquidable.
                                        Incluye la parte estatal y la parte autonómica.
                                    </p>
                                </div>
                            </div>
                            <div className="ceuta-irpf__step">
                                <div className="ceuta-irpf__step-num">2</div>
                                <div className="ceuta-irpf__step-content">
                                    <h3>Identifica las rentas de Ceuta/Melilla</h3>
                                    <p>
                                        La deducción aplica a la parte de la cuota
                                        correspondiente a rentas obtenidas y computadas
                                        en Ceuta o Melilla (trabajo, actividad
                                        económica, etc.).
                                    </p>
                                </div>
                            </div>
                            <div className="ceuta-irpf__step">
                                <div className="ceuta-irpf__step-num">3</div>
                                <div className="ceuta-irpf__step-content">
                                    <h3>Aplica el 60% de deducción</h3>
                                    <p>
                                        Sobre la parte proporcional de cuota íntegra que
                                        corresponda a esas rentas, se aplica una deducción
                                        del 60%. El resultado se resta de tu cuota líquida
                                        final.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="ceuta-irpf__example-box">
                            <h3>
                                <Calculator size={20} />
                                Ejemplo práctico
                            </h3>
                            <div className="ceuta-irpf__example-table">
                                <div className="ceuta-irpf__example-row">
                                    <span>Ingresos anuales en Ceuta</span>
                                    <span>40.000 €</span>
                                </div>
                                <div className="ceuta-irpf__example-row">
                                    <span>Cuota íntegra estimada</span>
                                    <span>8.200 €</span>
                                </div>
                                <div className="ceuta-irpf__example-row ceuta-irpf__example-row--deduction">
                                    <span>Deducción Art. 68.4 (60%)</span>
                                    <span>— 4.920 €</span>
                                </div>
                                <div className="ceuta-irpf__example-row ceuta-irpf__example-row--total">
                                    <span>
                                        <strong>Cuota líquida final</strong>
                                    </span>
                                    <span>
                                        <strong>3.280 €</strong>
                                    </span>
                                </div>
                            </div>
                            <p className="ceuta-irpf__example-note">
                                Valores orientativos. El cálculo exacto depende de
                                reducciones, mínimos personales y familiares, y otros
                                factores. Usa nuestro asistente para tu cálculo
                                personalizado.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Requisitos */}
            <section className="ceuta-requisitos">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Requisitos para aplicar las ventajas</h2>
                        <p className="section-subtitle">
                            La normativa establece condiciones específicas de residencia
                            y actividad para beneficiarse del régimen especial
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="ceuta-requisitos__grid">
                            <div className="ceuta-requisitos__card ceuta-requisitos__card--ok">
                                <h3>
                                    <CheckCircle size={20} />
                                    Requisitos para la deducción IRPF
                                </h3>
                                <ul>
                                    <li>
                                        <CheckCircle size={14} />
                                        Residencia fiscal en Ceuta o Melilla durante parte
                                        del año (o todo el año)
                                    </li>
                                    <li>
                                        <CheckCircle size={14} />
                                        Rentas obtenidas y computadas en Ceuta o Melilla
                                    </li>
                                    <li>
                                        <CheckCircle size={14} />
                                        La proporción de la deducción depende del tiempo
                                        de residencia en el ejercicio
                                    </li>
                                </ul>
                            </div>
                            <div className="ceuta-requisitos__card ceuta-requisitos__card--ok">
                                <h3>
                                    <CheckCircle size={20} />
                                    Requisitos para bonificación autónomos
                                </h3>
                                <ul>
                                    <li>
                                        <CheckCircle size={14} />
                                        Alta como autónomo con domicilio fiscal en Ceuta
                                        o Melilla
                                    </li>
                                    <li>
                                        <CheckCircle size={14} />
                                        Actividad económica desarrollada principalmente
                                        en Ceuta o Melilla
                                    </li>
                                    <li>
                                        <CheckCircle size={14} />
                                        Cumplimiento de estar al corriente con la
                                        Seguridad Social y la AEAT
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* FAQ */}
            <section className="ceuta-faq">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Preguntas frecuentes</h2>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="ceuta-faq__grid">
                            <div className="ceuta-faq__item">
                                <h3>
                                    ¿Me afecta la deducción si trabajo en Ceuta pero
                                    vivo en la Península?
                                </h3>
                                <p>
                                    La deducción del 60% aplica a residentes fiscales en
                                    Ceuta o Melilla. Si resides en la Península pero
                                    obtienes rentas en Ceuta, el tratamiento puede
                                    variar. Nuestro asistente analiza tu situación
                                    concreta.
                                </p>
                            </div>
                            <div className="ceuta-faq__item">
                                <h3>
                                    ¿El IPSI equivale exactamente al IVA?
                                </h3>
                                <p>
                                    No son exactamente equivalentes. El IPSI tiene sus
                                    propios tipos y reglas. No hay derecho a deducción
                                    del IVA soportado como en el régimen general. Es
                                    un impuesto local con lógica propia.
                                </p>
                            </div>
                            <div className="ceuta-faq__item">
                                <h3>
                                    ¿La bonificación del 50% SS aplica a todos
                                    los autónomos en Ceuta?
                                </h3>
                                <p>
                                    Aplica a autónomos que residan y ejerzan su actividad
                                    principalmente en Ceuta o Melilla. Existen
                                    restricciones para actividades de comercio exterior
                                    o cuya clientela esté principalmente fuera de estas
                                    ciudades.
                                </p>
                            </div>
                            <div className="ceuta-faq__item">
                                <h3>
                                    ¿Cómo puede ayudarme Impuestify con Ceuta/Melilla?
                                </h3>
                                <p>
                                    Nuestro motor tiene acceso a la normativa específica
                                    de Ceuta y Melilla: el Art. 68.4 LIRPF, la Ley del
                                    IPSI y la normativa de SS para autónomos. Puede
                                    calcular tu IRPF aplicando la deducción correcta y
                                    descubrir todas las ventajas aplicables a tu caso.
                                </p>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* CTA */}
            <section className="ceuta-cta">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="ceuta-cta__card">
                            <div className="ceuta-cta__icon">
                                <Calculator size={40} />
                            </div>
                            <h2>Calcula tu ahorro fiscal</h2>
                            <p>
                                Descubre cuánto puedes ahorrar gracias al régimen
                                especial de Ceuta y Melilla. Resultados personalizados
                                con citas al artículo de ley correspondiente.
                            </p>
                            <Link to="/register" className="btn btn-primary btn-lg">
                                Empezar ahora — desde 5 €/mes
                                <ArrowRight size={20} />
                            </Link>
                            <p className="ceuta-cta__note">
                                También accesible desde el plan Particular (5 €/mes).
                                Sin permanencia.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
