import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
    ArrowRight, CheckCircle, X, Map, Calculator,
    FileText, Shield, Zap, ChevronLeft
} from 'lucide-react'
import TerritoryCard from '../components/TerritoryCard'
import FadeContent from '../components/reactbits/FadeContent'
import SpotlightCard from '../components/reactbits/SpotlightCard'
import GradientText from '../components/reactbits/GradientText'
import './ForalPage.css'

const FORAL_TERRITORIES = [
    {
        name: 'Araba',
        fullName: 'Territorio Histórico de Álava',
        hacienda: 'Diputación Foral de Álava',
        deductionCount: 8,
        description:
            'IRPF propio regulado por la Norma Foral 33/2013. Tramos y tipos distintos al régimen común. Deducciones exclusivas para inversión empresarial, vivienda habitual y conciliación familiar.',
        slug: 'araba',
    },
    {
        name: 'Bizkaia',
        fullName: 'Territorio Histórico de Bizkaia',
        hacienda: 'Diputación Foral de Bizkaia',
        deductionCount: 6,
        description:
            'IRPF regulado por la Norma Foral 13/2013. Sistema fiscal independiente con gestión y recaudación propia. Deducciones especiales por emprendimiento, eficiencia energética y familia.',
        slug: 'bizkaia',
    },
    {
        name: 'Gipuzkoa',
        fullName: 'Territorio Histórico de Gipuzkoa',
        hacienda: 'Diputación Foral de Gipuzkoa',
        deductionCount: 6,
        description:
            'IRPF regulado por la Norma Foral 3/2014. Tramos propios y deducciones exclusivas por inversión en I+D, alquiler de vivienda y participación en empresas de nueva creación.',
        slug: 'gipuzkoa',
    },
    {
        name: 'Navarra',
        fullName: 'Comunidad Foral de Navarra',
        hacienda: 'Hacienda Foral de Navarra',
        deductionCount: 7,
        description:
            'IRPF propio regulado por el Decreto Foral Legislativo 4/2008. Sistema de convenio económico con el Estado. Deducciones únicas por natalidad, actividad empresarial y vivienda protegida.',
        slug: 'navarra',
    },
]

const IRPF_TRAMOS = [
    {
        territory: 'Régimen Común',
        tramos: [
            { desde: 0, hasta: 12_450, tipo: '19%' },
            { desde: 12_450, hasta: 20_200, tipo: '24%' },
            { desde: 20_200, hasta: 35_200, tipo: '30%' },
            { desde: 35_200, hasta: 60_000, tipo: '37%' },
            { desde: 60_000, hasta: 300_000, tipo: '45%' },
            { desde: 300_000, hasta: null, tipo: '47%' },
        ],
    },
    {
        territory: 'País Vasco (referencia)',
        tramos: [
            { desde: 0, hasta: 15_040, tipo: '23%' },
            { desde: 15_040, hasta: 30_080, tipo: '28%' },
            { desde: 30_080, hasta: 50_000, tipo: '35%' },
            { desde: 50_000, hasta: 180_000, tipo: '46%' },
            { desde: 180_000, hasta: null, tipo: '49%' },
        ],
    },
]

export default function ForalPage() {
    useEffect(() => {
        document.title =
            'Declaración de la Renta en Territorios Forales | Impuestify'

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
            'Calcula tu IRPF foral en Araba, Bizkaia, Gipuzkoa y Navarra. La única herramienta fiscal con IA que cubre todos los territorios forales de España. Deducciones propias, tramos específicos y haciendas forales.'
        )
        setMeta(
            'keywords',
            'IRPF foral, declaración renta País Vasco, IRPF Navarra, Hacienda Foral, Araba, Bizkaia, Gipuzkoa, deducciones forales, régimen foral'
        )
        setOg(
            'og:title',
            'Declaración de la Renta en Territorios Forales | Impuestify'
        )
        setOg(
            'og:description',
            'La única IA fiscal que cubre el IRPF foral del País Vasco (Araba, Bizkaia, Gipuzkoa) y Navarra con sus normativas propias.'
        )
        setOg('og:type', 'website')

        return () => {
            document.title = 'Impuestify — Asistente Fiscal con IA'
        }
    }, [])

    return (
        <div className="foral-page">
            {/* Back link */}
            <div className="foral-back">
                <div className="container">
                    <Link to="/" className="foral-back__link">
                        <ChevronLeft size={16} />
                        Volver al inicio
                    </Link>
                </div>
            </div>

            {/* Hero */}
            <section className="foral-hero">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="foral-hero__badge">
                            <Map size={16} />
                            <span>Cobertura Foral Completa</span>
                        </div>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <h1 className="foral-hero__title">
                            Declaración de la renta en{' '}
                            <GradientText
                                colors={['#1a56db', '#06b6d4', '#3b82f6', '#1a56db']}
                                animationSpeed={6}
                                className="foral-hero__gradient"
                            >
                                territorios forales
                            </GradientText>
                        </h1>
                        <p className="foral-hero__subtitle">
                            País Vasco y Navarra tienen un sistema fiscal propio,
                            completamente distinto al régimen común. Impuestify es la{' '}
                            <strong>única herramienta digital con IA</strong> que
                            integra las normativas forales de Araba, Bizkaia, Gipuzkoa
                            y Navarra con sus deducciones y tramos específicos.
                        </p>
                    </FadeContent>
                    <FadeContent delay={200} duration={600}>
                        <div className="foral-hero__actions">
                            <Link to="/register" className="btn btn-primary btn-lg">
                                Empieza gratis
                                <ArrowRight size={20} />
                            </Link>
                            <a href="#territorios" className="btn btn-secondary btn-lg">
                                Ver territorios
                            </a>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Why foral matters */}
            <section className="foral-why">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            ¿Por qué el régimen foral es diferente?
                        </h2>
                        <p className="section-subtitle">
                            Los territorios forales no aplican la LIRPF estatal.
                            Tienen su propia normativa, sus propias haciendas y sus
                            propias deducciones.
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={500}>
                        <div className="foral-why__grid">
                            <SpotlightCard
                                className="foral-why__card"
                                spotlightColor="rgba(26, 86, 219, 0.1)"
                            >
                                <div className="foral-why__card-icon">
                                    <FileText size={28} />
                                </div>
                                <h3>Normativa propia</h3>
                                <p>
                                    Normas forales propias (no la LIRPF). Araba, Bizkaia
                                    y Gipuzkoa tienen normas distintas entre sí. Navarra
                                    tiene su propio Decreto Foral Legislativo.
                                </p>
                            </SpotlightCard>
                            <SpotlightCard
                                className="foral-why__card"
                                spotlightColor="rgba(6, 182, 212, 0.1)"
                            >
                                <div className="foral-why__card-icon">
                                    <Calculator size={28} />
                                </div>
                                <h3>Tramos y tipos distintos</h3>
                                <p>
                                    Los tramos del IRPF foral no coinciden con los del
                                    régimen común. Tipos marginales, mínimos personales
                                    y reducciones con valores diferentes.
                                </p>
                            </SpotlightCard>
                            <SpotlightCard
                                className="foral-why__card"
                                spotlightColor="rgba(16, 185, 129, 0.1)"
                            >
                                <div className="foral-why__card-icon">
                                    <Shield size={28} />
                                </div>
                                <h3>Haciendas forales propias</h3>
                                <p>
                                    La gestión, liquidación y recaudación la realizan
                                    las Diputaciones Forales y Hacienda Foral de
                                    Navarra. No la AEAT.
                                </p>
                            </SpotlightCard>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* Territory cards */}
            <section className="foral-territories" id="territorios">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Los cuatro territorios forales</h2>
                        <p className="section-subtitle">
                            Cada uno con su propia normativa, deducciones y hacienda
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="foral-territories__grid">
                            {FORAL_TERRITORIES.map((t) => (
                                <TerritoryCard key={t.slug} {...t} isForal />
                            ))}
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* IRPF Tramos comparison */}
            <section className="foral-tramos">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            Comparativa de tramos IRPF
                        </h2>
                        <p className="section-subtitle">
                            Régimen común vs. País Vasco (valores orientativos, consultar
                            normativa vigente de cada territorio)
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="foral-tramos__tables">
                            {IRPF_TRAMOS.map((t) => (
                                <div key={t.territory} className="foral-tramos__table-wrap">
                                    <h3 className="foral-tramos__table-title">{t.territory}</h3>
                                    <table className="legal-table foral-table">
                                        <thead>
                                            <tr>
                                                <th>Desde (€)</th>
                                                <th>Hasta (€)</th>
                                                <th>Tipo</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {t.tramos.map((tr, i) => (
                                                <tr key={i}>
                                                    <td>{tr.desde.toLocaleString('es-ES')}</td>
                                                    <td>
                                                        {tr.hasta
                                                            ? tr.hasta.toLocaleString('es-ES')
                                                            : 'En adelante'}
                                                    </td>
                                                    <td>
                                                        <strong>{tr.tipo}</strong>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            ))}
                        </div>
                        <p className="foral-tramos__note">
                            Los tipos indicados son la suma del tramo estatal y autonómico/foral
                            orientativos. Consulta siempre la normativa vigente o usa nuestro
                            asistente para el cálculo personalizado.
                        </p>
                    </FadeContent>
                </div>
            </section>

            {/* Tool comparison */}
            <section className="foral-comparison">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">
                            ¿Qué herramientas cubren tu territorio?
                        </h2>
                        <p className="section-subtitle">
                            TaxDown, Taxfix y otros asistentes NO cubren los territorios forales
                        </p>
                    </FadeContent>
                    <FadeContent delay={100} duration={500}>
                        <div className="foral-comparison__table-wrap">
                            <table className="foral-comparison__table">
                                <thead>
                                    <tr>
                                        <th>Herramienta</th>
                                        <th>Régimen común</th>
                                        <th>País Vasco (forales)</th>
                                        <th>Navarra</th>
                                        <th>IA con RAG</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr className="foral-comparison__row--highlight">
                                        <td>
                                            <Zap size={16} className="foral-comparison__icon-brand" />
                                            <strong>Impuestify</strong>
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>TaxDown</td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>Taxfix</td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>ChatGPT / IA genérica</td>
                                        <td>
                                            <span className="foral-comparison__partial">Parcial</span>
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                    </tr>
                                    <tr>
                                        <td>Asesor tradicional</td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <CheckCircle size={18} className="foral-comparison__icon-yes" />
                                        </td>
                                        <td>
                                            <X size={18} className="foral-comparison__icon-no" />
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* FAQ */}
            <section className="foral-faq">
                <div className="container">
                    <FadeContent delay={0} duration={500}>
                        <h2 className="section-title">Preguntas frecuentes</h2>
                    </FadeContent>
                    <FadeContent delay={100} duration={600}>
                        <div className="foral-faq__grid">
                            <div className="foral-faq__item">
                                <h3>
                                    ¿Los residentes en el País Vasco hacen la declaración
                                    en la AEAT?
                                </h3>
                                <p>
                                    No. Los contribuyentes del País Vasco presentan su
                                    declaración ante la Diputación Foral correspondiente
                                    (Araba, Bizkaia o Gipuzkoa), no ante la AEAT. La
                                    normativa aplicable es la foral, no la LIRPF estatal.
                                </p>
                            </div>
                            <div className="foral-faq__item">
                                <h3>
                                    ¿Puedo aplicar las deducciones estatales si soy
                                    residente foral?
                                </h3>
                                <p>
                                    No directamente. Los territorios forales tienen su
                                    propio catálogo de deducciones. Algunas son similares
                                    a las estatales, pero otras son exclusivas del régimen
                                    foral y no existen en el régimen común.
                                </p>
                            </div>
                            <div className="foral-faq__item">
                                <h3>¿Qué es el Concierto Económico?</h3>
                                <p>
                                    El Concierto Económico es el acuerdo que permite al
                                    País Vasco recaudar y gestionar sus propios impuestos.
                                    En Navarra existe el Convenio Económico. Ambos son
                                    derechos históricos reconocidos por la Constitución.
                                </p>
                            </div>
                            <div className="foral-faq__item">
                                <h3>
                                    ¿Cómo me ayuda Impuestify con el IRPF foral?
                                </h3>
                                <p>
                                    Nuestro motor de IA tiene acceso a 37+ documentos de
                                    las diputaciones forales, incluyendo normas forales,
                                    instrucciones oficiales y modelos de declaración.
                                    Puede calcular tu IRPF aplicando las deducciones y
                                    tramos correctos de tu territorio.
                                </p>
                            </div>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* CTA */}
            <section className="foral-cta">
                <div className="container">
                    <FadeContent delay={0} duration={600}>
                        <div className="foral-cta__card">
                            <div className="foral-cta__icon">
                                <Map size={40} />
                            </div>
                            <h2>Calcula tu IRPF foral ahora</h2>
                            <p>
                                La única IA fiscal que entiende tu normativa foral.
                                Resultados personalizados con citas a la norma oficial.
                            </p>
                            <Link to="/register" className="btn btn-primary btn-lg">
                                Empieza gratis
                                <ArrowRight size={20} />
                            </Link>
                            <p className="foral-cta__note">
                                Sin tarjeta de crédito en el periodo de prueba.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>
        </div>
    )
}
