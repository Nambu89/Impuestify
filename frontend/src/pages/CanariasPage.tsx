import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
    ArrowRight, CheckCircle, X, Sun, Receipt,
    Building2, PiggyBank, Calculator, ChevronLeft, Info, Zap
} from 'lucide-react'
import FadeContent from '../components/reactbits/FadeContent'
import SpotlightCard from '../components/reactbits/SpotlightCard'
import GradientText from '../components/reactbits/GradientText'
import CountUp from '../components/reactbits/CountUp'
import './CanariasPage.css'

const VENTAJAS = [
    {
        icon: Receipt,
        title: 'IGIC en lugar de IVA',
        article: 'Ley 20/1991',
        description:
            'Canarias no aplica IVA. El IGIC tiene tipo general del 7% frente al 21% del IVA peninsular. Ahorro directo en consumo e inversión local, tanto para particulares como para empresas.',
        example:
            'Una compra de 10.000 EUR tributa 700 EUR (IGIC) vs 2.100 EUR (IVA) — ahorro de 1.400 EUR.',
    },
    {
        icon: Building2,
        title: 'Zona Especial Canaria (ZEC)',
        article: 'RD-Ley 12/2006',
        description:
            'Empresas inscritas en la ZEC tributan al 4% en el Impuesto de Sociedades frente al 25% general. Requiere creación de empleo real y sede efectiva en Canarias.',
        example:
            'Empresa con 200.000 EUR de beneficio: paga 8.000 EUR (ZEC 4%) vs 50.000 EUR (general 25%).',
    },
    {
        icon: PiggyBank,
        title: 'Reserva para Inversiones en Canarias (RIC)',
        article: 'Art. 27 Ley 19/1994',
        description:
            'Permite reducir hasta un 90% de la base imponible destinando beneficios a inversiones en Canarias. Aplica tanto a empresas como a autónomos con actividad económica.',
        example:
            'Autónomo con 80.000 EUR de beneficio que destina 50.000 EUR a RIC: ahorra hasta 11.250 EUR en IRPF.',
    },
    {
        icon: Calculator,
        title: 'Deducciones autonómicas IRPF',
        article: 'DL 1/2009 Canarias',
        description:
            '6 deducciones propias: familia numerosa, nacimiento o adopción, discapacidad, gastos de estudios, inversiones medioambientales y donaciones a entidades canarias.',
        example:
            'Familia numerosa general: deducción de 500 EUR; especial: 1.000 EUR en cuota autonómica.',
    },
]

const IGIC_TIPOS = [
    { tipo: 'Tipo cero', igic: '0%', iva: '4% (superreducido)', ahorro: '100%' },
    { tipo: 'Reducido', igic: '3%', iva: '10%', ahorro: '70%' },
    { tipo: 'General', igic: '7%', iva: '21%', ahorro: '67%' },
    { tipo: 'Incrementado', igic: '9,5%', iva: '21%', ahorro: '55%' },
    { tipo: 'Esp. incrementado', igic: '13,5% / 15%', iva: '21%', ahorro: '36% / 29%' },
]

export default function CanariasPage() {
    useEffect(() => {
        document.title =
            'Fiscalidad en Canarias — IGIC, ZEC y Deducciones | Impuestify'

        const setMeta = (name: string, content: string) => {
            let el = document.querySelector<HTMLMetaElement>(
                `meta[name="${name}"]`
            )
            if (!el) {
                el = document.createElement('meta')
                el.setAttribute('name', name)
                document.head.appendChild(el)
            }
            el.setAttribute('content', content)
        }

        const setOg = (property: string, content: string) => {
            let el = document.querySelector<HTMLMetaElement>(
                `meta[property="${property}"]`
            )
            if (!el) {
                el = document.createElement('meta')
                el.setAttribute('property', property)
                document.head.appendChild(el)
            }
            el.setAttribute('content', content)
        }

        setMeta(
            'description',
            'Descubre las ventajas fiscales de Canarias: IGIC en lugar de IVA (7% vs 21%), Zona Especial Canaria (ZEC) al 4% IS, y 6 deducciones propias. Calcula tu ahorro con IA.'
        )
        setMeta(
            'keywords',
            'IGIC Canarias, fiscalidad Canarias, ZEC Zona Especial Canaria, IVA Canarias, deducciones Canarias, IRPF Canarias, RIC Reserva Inversiones'
        )
        setOg(
            'og:title',
            'Fiscalidad en Canarias — IGIC, ZEC y Deducciones | Impuestify'
        )
        setOg(
            'og:description',
            'IGIC al 7% en lugar de IVA al 21%, ZEC al 4% en Sociedades, RIC hasta el 90% de reducción y 6 deducciones IRPF propias. La IA fiscal que entiende el régimen canario.'
        )
        setOg('og:type', 'website')

        return () => {
            document.title = 'Impuestify — Asistente Fiscal con IA'
        }
    }, [])

    return (
        <div className="canarias-page">
            {/* Back link */}
            <div className="canarias-back">
                <div className="container">
                    <Link to="/" className="canarias-back__link">
                        <ChevronLeft size={16} />
                        Volver al inicio
                    </Link>
                </div>
            </div>

            {/* Hero */}
            <section className="canarias-hero">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="canarias-hero__badge">
                            <Sun size={16} />
                            <span>Régimen Fiscal Especial</span>
                        </div>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <h1 className="canarias-hero__title">
                            Fiscalidad en{' '}
                            <GradientText
                                colors={['#1a56db', '#06b6d4', '#3b82f6', '#1a56db']}
                                animationSpeed={6}
                                className="canarias-hero__gradient"
                            >
                                Canarias
                            </GradientText>
                        </h1>
                        <p className="canarias-hero__subtitle">
                            Canarias tiene un{' '}
                            <strong>régimen fiscal radicalmente distinto</strong> al
                            peninsular. Sin IVA, con IGIC al 7%, la Zona Especial Canaria
                            al 4% en Sociedades, la RIC para reducir hasta el 90% de la
                            base imponible y deducciones IRPF exclusivas. Impuestify
                            calcula tu ahorro real con IA y fuentes oficiales.
                        </p>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <div className="canarias-hero__stats">
                            <div className="canarias-hero__stat">
                                <span className="canarias-hero__stat-value">
                                    <CountUp to={7} duration={1.5} />
                                    <span>%</span>
                                </span>
                                <span className="canarias-hero__stat-label">
                                    IGIC General
                                </span>
                            </div>
                            <div className="canarias-hero__stat">
                                <span className="canarias-hero__stat-value">
                                    <CountUp to={4} duration={1.2} />
                                    <span>%</span>
                                </span>
                                <span className="canarias-hero__stat-label">
                                    IS en ZEC
                                </span>
                            </div>
                            <div className="canarias-hero__stat">
                                <span className="canarias-hero__stat-value">
                                    <CountUp to={50} duration={2} />
                                    <span>%</span>
                                </span>
                                <span className="canarias-hero__stat-label">
                                    Ahorro vs IVA
                                </span>
                            </div>
                        </div>
                    </FadeContent>
                    <FadeContent delay={300} duration={600}>
                        <img
                            src="/images/hero-canarias.webp"
                            alt="Mapa fiscal de Canarias con régimen IGIC y ZEC"
                            className="canarias-hero__image"
                            loading="lazy"
                        />
                    </FadeContent>
                    <FadeContent delay={350} duration={600}>
                        <div className="canarias-hero__actions">
                            <Link to="/register" className="btn btn-primary btn-lg">
                                Calcula tu ahorro fiscal
                                <ArrowRight size={20} />
                            </Link>
                            <a href="#ventajas" className="btn btn-secondary btn-lg">
                                Ver ventajas
                            </a>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Ventajas principales */}
            <section className="canarias-ventajas" id="ventajas">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            Ventajas del régimen canario
                        </h2>
                        <p className="section-subtitle">
                            Un sistema fiscal diseñado para compensar la insularidad y
                            potenciar la actividad economica del archipielago
                        </p>
                    </FadeContent>
                    <div className="canarias-ventajas__grid">
                        {VENTAJAS.map((v, i) => {
                            const Icon = v.icon
                            return (
                                <FadeContent key={v.title} delay={i * 100} duration={500}>
                                    <SpotlightCard
                                        className="canarias-ventaja__card"
                                        spotlightColor="rgba(26, 86, 219, 0.08)"
                                    >
                                        <div className="canarias-ventaja__header">
                                            <div className="canarias-ventaja__icon">
                                                <Icon size={24} />
                                            </div>
                                            <span className="canarias-ventaja__article">
                                                {v.article}
                                            </span>
                                        </div>
                                        <h3 className="canarias-ventaja__title">{v.title}</h3>
                                        <p className="canarias-ventaja__desc">{v.description}</p>
                                        <div className="canarias-ventaja__example">
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

            {/* IGIC vs IVA comparison table */}
            <section className="canarias-comparacion">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">IGIC vs IVA: comparativa de tipos</h2>
                        <p className="section-subtitle">
                            Los residentes en Canarias NO pagan IVA en compras locales
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="canarias-comparacion__table-wrap">
                            <table className="canarias-comparacion__table">
                                <thead>
                                    <tr>
                                        <th>Tipo</th>
                                        <th>IGIC (Canarias)</th>
                                        <th>IVA (Peninsula)</th>
                                        <th>Ahorro</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {IGIC_TIPOS.map((row) => (
                                        <tr key={row.tipo}>
                                            <td>{row.tipo}</td>
                                            <td>{row.igic}</td>
                                            <td>{row.iva}</td>
                                            <td>
                                                <span className="canarias-comparacion__savings">
                                                    {row.ahorro}
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        <p className="canarias-comparacion__note">
                            El IGIC tiene tipos propios regulados por la Ley 20/1991. Los tipos
                            aplicables pueden variar según el producto o servicio. Consulta la
                            normativa vigente o usa nuestro asistente para tu caso concreto.
                        </p>
                    </FadeContent>
                </div>
            </section>

            {/* ZEC section */}
            <section className="canarias-zec">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            Zona Especial Canaria — 4% en Sociedades
                        </h2>
                        <p className="section-subtitle">
                            Un régimen excepcional para empresas que se establezcan y
                            generen empleo real en el archipiélago
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="canarias-zec__steps">
                            <div className="canarias-zec__step">
                                <div className="canarias-zec__step-num">1</div>
                                <div className="canarias-zec__step-content">
                                    <h3>Constituye tu empresa en la ZEC</h3>
                                    <p>
                                        Registro en el Consorcio de la Zona Especial Canaria,
                                        con domicilio social y sede de dirección efectiva en
                                        Canarias. La inscripcion es previa al inicio de la
                                        actividad.
                                    </p>
                                </div>
                            </div>
                            <div className="canarias-zec__step">
                                <div className="canarias-zec__step-num">2</div>
                                <div className="canarias-zec__step-content">
                                    <h3>Cumple requisitos de empleo e inversion</h3>
                                    <p>
                                        Minimo 5 empleados en Gran Canaria o Tenerife (3 en el
                                        resto de islas), e inversion minima de 100.000 EUR
                                        (50.000 EUR en islas menores) en activos afectos a la
                                        actividad en el primer ano.
                                    </p>
                                </div>
                            </div>
                            <div className="canarias-zec__step">
                                <div className="canarias-zec__step-num">3</div>
                                <div className="canarias-zec__step-content">
                                    <h3>Tributa al 4% en Impuesto de Sociedades</h3>
                                    <p>
                                        Sobre los beneficios hasta los límites establecidos
                                        por empleado (cantidades crecientes según plantilla).
                                        El beneficio que supere el límite tributa al tipo
                                        general del 25%.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="canarias-zec__example-box">
                            <h3>
                                <Calculator size={20} />
                                Ejemplo practico: empresa con 200.000 EUR de beneficio
                            </h3>
                            <div className="canarias-zec__example-table">
                                <div className="canarias-zec__example-row">
                                    <span>Beneficio tributable en ZEC</span>
                                    <span>200.000 EUR</span>
                                </div>
                                <div className="canarias-zec__example-row canarias-zec__example-row--zec">
                                    <span>Cuota ZEC (4%)</span>
                                    <span>8.000 EUR</span>
                                </div>
                                <div className="canarias-zec__example-row canarias-zec__example-row--general">
                                    <span>Cuota régimen general (25%)</span>
                                    <span>50.000 EUR</span>
                                </div>
                                <div className="canarias-zec__example-row canarias-zec__example-row--total">
                                    <span>
                                        <strong>Ahorro fiscal con ZEC</strong>
                                    </span>
                                    <span>
                                        <strong>42.000 EUR</strong>
                                    </span>
                                </div>
                            </div>
                            <p className="canarias-zec__example-note">
                                Valores orientativos sujetos a los límites de base imponible
                                por número de empleados establecidos en la normativa ZEC vigente.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Tool comparison */}
            <section className="canarias-comparison">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            ¿Qué herramientas cubren el régimen canario?
                        </h2>
                        <p className="section-subtitle">
                            TaxDown, Taxfix y otros asistentes no cubren el IGIC ni la ZEC ni
                            la RIC canaria
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={500}>
                        <div className="canarias-comparison__table-wrap">
                            <table className="canarias-comparison__table">
                                <thead>
                                    <tr>
                                        <th>Herramienta</th>
                                        <th>IGIC</th>
                                        <th>ZEC / RIC</th>
                                        <th>Deducciones</th>
                                        <th>IA con RAG</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr className="canarias-comparison__row--highlight">
                                        <td>
                                            <Zap size={16} className="canarias-comparison__icon-brand" />
                                            <strong>Impuestify</strong>
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="canarias-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="canarias-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="canarias-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="canarias-comparison__icon-yes" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>TaxDown</td>
                                        <td>
                                            <span className="canarias-comparison__partial">Parcial</span>
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <span className="canarias-comparison__partial">Parcial</span>
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>Taxfix</td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>ChatGPT / IA generica</td>
                                        <td>
                                            <span className="canarias-comparison__partial">Parcial</span>
                                        </td>
                                        <td>
                                            <span className="canarias-comparison__partial">Parcial</span>
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>Asesor tradicional</td>
                                        <td>
                                            <CheckCircle size={18} className="canarias-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="canarias-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="canarias-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <X size={18} className="canarias-comparison__icon-no" />
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* FAQ */}
            <section className="canarias-faq">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Preguntas frecuentes</h2>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="canarias-faq__grid">
                            <div className="canarias-faq__item">
                                <h3>
                                    Los residentes en Canarias pagan IVA?
                                </h3>
                                <p>
                                    No. Canarias no forma parte del territorio aduanero de la
                                    Union Europea a efectos del IVA. En su lugar aplica el
                                    Impuesto General Indirecto Canario (IGIC), con tipos
                                    significativamente inferiores al IVA peninsular.
                                </p>
                            </div>
                            <div className="canarias-faq__item">
                                <h3>
                                    ¿Qué es la Zona Especial Canaria?
                                </h3>
                                <p>
                                    La ZEC es un régimen especial aprobado por la Unión Europea
                                    que permite a empresas radicadas en Canarias tributar al 4%
                                    en el Impuesto de Sociedades, frente al 25% general, siempre
                                    que cumplan requisitos de creacion de empleo e inversion en
                                    el archipielago.
                                </p>
                            </div>
                            <div className="canarias-faq__item">
                                <h3>
                                    ¿Puedo aplicar la RIC como autónomo?
                                </h3>
                                <p>
                                    Sí. Los autónomos con actividad económica en Canarias pueden
                                    aplicar la Reserva para Inversiones en Canarias (RIC) y
                                    reducir hasta el 90% de su base imponible en IRPF,
                                    destinando beneficios a inversiones productivas en el
                                    archipielago dentro de los plazos establecidos.
                                </p>
                            </div>
                            <div className="canarias-faq__item">
                                <h3>
                                    ¿Cómo ayuda Impuestify con el régimen canario?
                                </h3>
                                <p>
                                    Nuestro motor de IA tiene acceso a la normativa específica
                                    de Canarias: Ley 20/1991 del IGIC, Ley 19/1994 del REF
                                    Canario (RIC y ZEC), y el Decreto Legislativo 1/2009 de
                                    deducciones IRPF. Puede calcular tu IGIC, estimar el ahorro
                                    con la RIC y descubrir todas las deducciones aplicables a
                                    tu situación.
                                </p>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* CTA */}
            <section className="canarias-cta">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="canarias-cta__card">
                            <div className="canarias-cta__icon">
                                <Sun size={40} />
                            </div>
                            <h2>Calcula tu ahorro fiscal en Canarias</h2>
                            <p>
                                La única IA fiscal que entiende el régimen canario: IGIC,
                                ZEC, RIC y deducciones propias. Resultados personalizados
                                con citas a la norma oficial.
                            </p>
                            <Link to="/register" className="btn btn-primary btn-lg">
                                Empezar ahora — desde 5 €/mes
                                <ArrowRight size={20} />
                            </Link>
                            <p className="canarias-cta__note">
                                Plan desde 5 EUR/mes. Sin permanencia.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
