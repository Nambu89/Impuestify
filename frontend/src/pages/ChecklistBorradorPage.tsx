import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
    CheckCircle2, Circle, ArrowRight, AlertTriangle, User, Users,
    MapPin, Briefcase, Home, Gift, Heart, Baby, Star, School,
    Building2, TrendingUp, FileText, Leaf, History,
    ChevronDown, ChevronUp
} from 'lucide-react'
import Header from '../components/Header'
import FadeContent from '../components/reactbits/FadeContent'
import './ChecklistBorradorPage.css'

interface ChecklistItem {
    id: number
    icon: React.ElementType
    title: string
    description: string
    porQueImporta: string
    importeRiesgo?: string
}

const CHECKLIST_ITEMS: ChecklistItem[] = [
    {
        id: 1,
        icon: User,
        title: 'Datos personales actualizados',
        description: 'Verifica domicilio fiscal, estado civil y fecha de nacimiento. Si te mudaste de comunidad autónoma en 2025, la CCAA correcta es la de tu residencia el 31 de diciembre.',
        porQueImporta: 'El domicilio fiscal determina qué deducciones autonómicas puedes aplicar. Un dato erróneo puede costarte cientos de euros en deducciones perdidas o en liquidaciones de la AEAT.',
        importeRiesgo: 'Afecta al tramo autonómico completo',
    },
    {
        id: 2,
        icon: Users,
        title: 'Situación familiar correcta',
        description: 'Comprueba que aparecen todos los hijos, ascendientes a cargo y situaciones de discapacidad. Los nacimientos y adopciones de 2025 deben estar incluidos.',
        porQueImporta: 'Los mínimos familiares reducen directamente la base imponible. Un hijo no registrado supone perder entre 2.400 y 4.500 EUR de mínimo, dependiendo de su edad y orden.',
        importeRiesgo: 'Hasta 4.500 EUR de mínimo por hijo',
    },
    {
        id: 3,
        icon: MapPin,
        title: 'Comunidad autónoma correcta',
        description: 'Si te mudaste en 2025, asegúrate de que el borrador refleja la comunidad autónoma donde residías el 31 de diciembre de 2025, no donde vives ahora.',
        porQueImporta: 'La CCAA incorrecta genera una cuota autonómica equivocada y puede impedir que apliques deducciones como la de alquiler de vivienda habitual o nacimiento de hijos.',
    },
    {
        id: 4,
        icon: Briefcase,
        title: 'Rendimientos del trabajo completos',
        description: 'Verifica que aparecen todos tus pagadores: empresa principal, segunda empresa, SEPE (desempleo), mutualidades, prestaciones por maternidad o paternidad.',
        porQueImporta: 'Tener dos o más pagadores puede obligarte a declarar aunque los ingresos totales sean inferiores a 22.000 EUR. Omitir un pagador es causa frecuente de requerimientos de la AEAT.',
        importeRiesgo: 'Puede conllevar sanciones del 50-150% de la deuda',
    },
    {
        id: 5,
        icon: Home,
        title: 'Deducciones autonómicas por alquiler y vivienda',
        description: 'Además de la deducción estatal transitoria (contratos anteriores al 1 de enero de 2015, hasta el 15% de lo pagado con límite de 9.040 EUR), comprueba si tu comunidad tiene deducción autonómica por alquiler de vivienda habitual.',
        porQueImporta: 'La AEAT casi nunca pre-rellena las deducciones autonómicas. Esta es la mayor fuente de dinero no reclamado en la declaración de la renta.',
        importeRiesgo: 'Hasta 1.000 EUR anuales perdidos',
    },
    {
        id: 6,
        icon: Gift,
        title: 'Donativos y donaciones a ONG y fundaciones',
        description: 'Incluye donativos a fundaciones, ONG, partidos políticos y sindicatos. Los primeros 250 EUR deducen al 80% y el resto al 40% (o 45% si llevas tres años donando al mismo organismo).',
        porQueImporta: 'Las ONG informan a la AEAT pero no siempre constan en el borrador. Un donativo de 250 EUR puede suponer 200 EUR de ahorro fiscal que pierdes si no lo incluyes.',
        importeRiesgo: 'Hasta 200 EUR por cada 250 EUR donados',
    },
    {
        id: 7,
        icon: Heart,
        title: 'Aportaciones a planes de pensiones',
        description: 'Comprueba que constan tus aportaciones a planes de pensiones individuales o de empleo. El límite general es 1.500 EUR, ampliable hasta 8.500 EUR si el plan es de empresa.',
        porQueImporta: 'Las aportaciones reducen la base imponible general, no la cuota. En los tramos altos, el ahorro puede superar el 45% del importe aportado.',
        importeRiesgo: 'Reducción de hasta 1.500 EUR en base imponible',
    },
    {
        id: 8,
        icon: Baby,
        title: 'Deducción por maternidad',
        description: 'Las madres trabajadoras con hijos menores de tres años tienen derecho a hasta 1.200 EUR por cada hijo. Si el niño estuvo en guardería, puedes añadir hasta 1.000 EUR adicionales por gastos de custodia.',
        porQueImporta: 'Es frecuente que el borrador incluya los 1.200 EUR pero omita los 1.000 EUR de guardería. Muchas madres pierden esta cantidad simplemente por no comprobarlo.',
        importeRiesgo: 'Hasta 1.000 EUR adicionales por guardería',
    },
    {
        id: 9,
        icon: Star,
        title: 'Familia numerosa',
        description: 'Las familias numerosas generales tienen derecho a 1.200 EUR de deducción y las de categoría especial a 2.400 EUR. Verifica también si corresponde la deducción por cónyuge con discapacidad.',
        porQueImporta: 'Este importe se deduce de la cuota líquida, no de la base imponible, por lo que el ahorro es íntegro. La AEAT suele incluirlo si hay certificado vigente, pero conviene confirmarlo.',
        importeRiesgo: 'Hasta 2.400 EUR de deducción directa',
    },
    {
        id: 10,
        icon: School,
        title: 'Cuotas sindicales y colegios profesionales',
        description: 'Las cuotas sindicales y las cuotas de colegiación obligatoria son gasto deducible de los rendimientos del trabajo. El límite para cuotas de colegios es de 500 EUR anuales.',
        porQueImporta: 'El borrador suele omitirlas aunque el pagador las declare. Son gastos que el contribuyente puede añadir manualmente en la casilla correspondiente sin necesidad de justificante adicional.',
        importeRiesgo: 'Hasta 500 EUR de gasto deducible omitido',
    },
    {
        id: 11,
        icon: School,
        title: 'Gastos de guardería',
        description: 'Además de la deducción por maternidad, muchas comunidades autónomas tienen deducciones propias por gastos de escuela infantil (0-3 años). Consulta la tabla de tu CCAA.',
        porQueImporta: 'Madrid, Cataluña, Galicia, Andalucía y otras CCAA tienen deducciones propias de hasta el 30% de los gastos de guardería que no se incluyen en el borrador estatal.',
    },
    {
        id: 12,
        icon: Home,
        title: 'Hipoteca anterior a 2013',
        description: 'Si compraste tu vivienda habitual antes del 1 de enero de 2013 y venías aplicando la deducción, puedes seguir haciéndolo con carácter transitorio. El límite es el 15% de lo pagado hasta 9.040 EUR anuales.',
        porQueImporta: 'El borrador suele incluirla si la aplicaste el año anterior, pero verifica el importe. Si refinanciaste la hipoteca, podría haberse perdido el derecho a la deducción transitoria.',
        importeRiesgo: 'Hasta 1.356 EUR anuales de deducción',
    },
    {
        id: 13,
        icon: Leaf,
        title: 'Inversiones en eficiencia energética y vehículo eléctrico',
        description: 'Las obras de mejora de la eficiencia energética del hogar tienen deducciones del 20%, 40% o 60% según el tipo de reforma. La compra de vehículo eléctrico también puede tener deducción autonómica.',
        porQueImporta: 'Son deducciones temporales creadas en los últimos años. Muchos contribuyentes no las conocen o no saben que deben incluirse en la declaración, no en el borrador automático.',
        importeRiesgo: 'Hasta 5.000 EUR por obras de rehabilitación',
    },
    {
        id: 14,
        icon: TrendingUp,
        title: 'Ganancias y pérdidas patrimoniales',
        description: 'Verifica que constan todas las ventas de fondos de inversión, acciones, criptomonedas, inmuebles o cualquier otro activo. Las pérdidas patrimoniales compensan ganancias y reducen el impuesto.',
        porQueImporta: 'La AEAT tiene datos de entidades financieras españolas pero puede no tener información completa de exchanges de cripto o activos en el extranjero. La omisión genera sanciones graves.',
        importeRiesgo: 'Sanciones del 50-150% de la cuota no declarada',
    },
    {
        id: 15,
        icon: Building2,
        title: 'Rentas imputadas de segundas viviendas',
        description: 'Si tienes una segunda vivienda que no es tu residencia habitual y no está arrendada, debes imputar una renta del 1,1% o 2% del valor catastral. Verifica que la referencia catastral y el importe son correctos.',
        porQueImporta: 'Los errores en referencias catastrales o la omisión de inmuebles heredados son causa frecuente de liquidaciones complementarias. La AEAT cruza datos con el Catastro.',
    },
]

export default function ChecklistBorradorPage() {
    const [checked, setChecked] = useState<Set<number>>(new Set())
    const [expandedId, setExpandedId] = useState<number | null>(null)

    useEffect(() => {
        document.title = 'Checklist borrador renta 2026: 15 puntos antes de confirmar — Impuestify'

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

        setMeta('description', '15 puntos que debes revisar antes de confirmar tu borrador de la renta 2025/2026. 1 de cada 3 borradores tiene errores. No pierdas dinero por no revisar.')
        setMeta('keywords', 'checklist borrador renta, revisar borrador IRPF, borrador renta 2026, errores borrador renta, deducciones IRPF borrador')
        setOg('og:title', 'Checklist borrador renta 2026: 15 puntos antes de confirmar — Impuestify')
        setOg('og:description', '1 de cada 3 borradores tiene errores. Comprueba los 15 puntos clave antes de confirmar tu declaración de la renta 2025/2026.')
        setOg('og:type', 'article')

        return () => {
            document.title = 'Impuestify — Asistente Fiscal IA para España'
        }
    }, [])

    const toggleItem = (id: number) => {
        setChecked(prev => {
            const next = new Set(prev)
            if (next.has(id)) {
                next.delete(id)
            } else {
                next.add(id)
            }
            return next
        })
    }

    const toggleExpand = (id: number, e: React.MouseEvent) => {
        e.stopPropagation()
        setExpandedId(prev => (prev === id ? null : id))
    }

    const total = CHECKLIST_ITEMS.length
    const done = checked.size
    const progress = Math.round((done / total) * 100)
    const allDone = done === total

    return (
        <div className="checklist-page">
            <Header />

            {/* Hero */}
            <section className="checklist-hero">
                <FadeContent direction="up" duration={600}>
                    <div className="checklist-hero-inner">
                        <div className="checklist-hero-badge">
                            <FileText size={14} />
                            Campaña Renta 2025/2026
                        </div>
                        <h1 className="checklist-hero-title">
                            15 puntos que debes revisar antes de confirmar tu borrador
                        </h1>
                        <p className="checklist-hero-subtitle">
                            1 de cada 3 borradores tiene errores. No pierdas dinero.
                        </p>
                        <div className="checklist-hero-stat">
                            <AlertTriangle size={16} />
                            Los españoles pierden 9.000 millones de euros al año por confirmar el borrador sin revisar
                            <span className="checklist-source">Fuente: GESTHA</span>
                        </div>
                    </div>
                </FadeContent>
            </section>

            <div className="checklist-layout">
                {/* Sticky progress sidebar */}
                <aside className="checklist-sidebar">
                    <div className="checklist-progress-card">
                        <div className="checklist-progress-label">
                            {allDone
                                ? 'Revisión completada'
                                : `${done} de ${total} puntos revisados`}
                        </div>
                        <div className="checklist-progress-bar-wrap">
                            <div
                                className={`checklist-progress-bar ${allDone ? 'checklist-progress-bar--full' : ''}`}
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                        <div className="checklist-progress-pct">{progress}%</div>

                        {allDone ? (
                            <div className="checklist-result checklist-result--ok">
                                <CheckCircle2 size={20} />
                                <div>
                                    <strong>Tu borrador está revisado.</strong>
                                    <p>Puedes confirmar con confianza.</p>
                                </div>
                            </div>
                        ) : done > 0 ? (
                            <div className="checklist-result checklist-result--warn">
                                <AlertTriangle size={20} />
                                <div>
                                    <strong>Te faltan {total - done} puntos.</strong>
                                    <p>No confirmes aún.</p>
                                </div>
                            </div>
                        ) : null}

                        <div className="checklist-sidebar-cta">
                            <p>¿Quieres que Impuestify detecte automáticamente tus deducciones?</p>
                            <Link to="/guia-fiscal" className="checklist-btn-primary">
                                Guía fiscal gratuita
                                <ArrowRight size={16} />
                            </Link>
                            <Link to="/register" className="checklist-btn-secondary">
                                Crear cuenta
                            </Link>
                        </div>
                    </div>
                </aside>

                {/* Checklist items */}
                <main className="checklist-main">
                    <ul className="checklist-list">
                        {CHECKLIST_ITEMS.map((item, idx) => {
                            const Icon = item.icon
                            const isChecked = checked.has(item.id)
                            const isExpanded = expandedId === item.id

                            return (
                                <FadeContent key={item.id} direction="up" duration={400} delay={idx * 40}>
                                    <li
                                        className={`checklist-item ${isChecked ? 'checklist-item--checked' : ''}`}
                                        onClick={() => toggleItem(item.id)}
                                        role="checkbox"
                                        aria-checked={isChecked}
                                        tabIndex={0}
                                        onKeyDown={e => {
                                            if (e.key === ' ' || e.key === 'Enter') {
                                                e.preventDefault()
                                                toggleItem(item.id)
                                            }
                                        }}
                                    >
                                        <div className="checklist-item-header">
                                            <div className="checklist-item-check">
                                                {isChecked
                                                    ? <CheckCircle2 size={24} />
                                                    : <Circle size={24} />}
                                            </div>

                                            <div className="checklist-item-icon-wrap">
                                                <Icon size={18} />
                                            </div>

                                            <div className="checklist-item-content">
                                                <div className="checklist-item-num">Punto {item.id}</div>
                                                <h2 className="checklist-item-title">{item.title}</h2>
                                                <p className="checklist-item-desc">{item.description}</p>
                                                {item.importeRiesgo && (
                                                    <span className="checklist-item-badge">{item.importeRiesgo}</span>
                                                )}
                                            </div>

                                            <button
                                                className="checklist-item-expand"
                                                onClick={e => toggleExpand(item.id, e)}
                                                aria-label={isExpanded ? 'Colapsar detalle' : 'Ver por qué importa'}
                                                title={isExpanded ? 'Colapsar' : 'Por qué importa'}
                                            >
                                                {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                                            </button>
                                        </div>

                                        {isExpanded && (
                                            <div
                                                className="checklist-item-detail"
                                                onClick={e => e.stopPropagation()}
                                            >
                                                <div className="checklist-item-detail-label">Por qué importa</div>
                                                <p>{item.porQueImporta}</p>
                                            </div>
                                        )}
                                    </li>
                                </FadeContent>
                            )
                        })}
                    </ul>

                    {/* Mobile progress — shown only below 900px */}
                    <div className="checklist-progress-mobile">
                        <div className="checklist-progress-label">
                            {allDone
                                ? 'Revisión completada'
                                : `${done} de ${total} puntos revisados`}
                        </div>
                        <div className="checklist-progress-bar-wrap">
                            <div
                                className={`checklist-progress-bar ${allDone ? 'checklist-progress-bar--full' : ''}`}
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                        {allDone && (
                            <div className="checklist-result checklist-result--ok">
                                <CheckCircle2 size={18} />
                                <div>
                                    <strong>Tu borrador está revisado.</strong>
                                    <p>Puedes confirmar con confianza.</p>
                                </div>
                            </div>
                        )}
                        {!allDone && done > 0 && (
                            <div className="checklist-result checklist-result--warn">
                                <AlertTriangle size={18} />
                                <div>
                                    <strong>Te faltan {total - done} puntos por revisar.</strong>
                                    <p>No confirmes aún.</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Info box */}
                    <FadeContent direction="up" duration={500} delay={200}>
                        <div className="checklist-infobox">
                            <AlertTriangle size={20} />
                            <div>
                                <strong>¿Sabías que?</strong>
                                <p>
                                    Los españoles pierden aproximadamente 9.000 millones de euros al año por confirmar el borrador de la renta sin revisarlo. La mayoría de las deducciones autonómicas no aparecen en el borrador y deben añadirse manualmente.
                                    <br />
                                    <span className="checklist-infobox-source">Fuente: GESTHA (Sindicato de Técnicos del Ministerio de Hacienda)</span>
                                </p>
                            </div>
                        </div>
                    </FadeContent>

                    {/* CTA bottom */}
                    <FadeContent direction="up" duration={500} delay={300}>
                        <div className="checklist-cta-box">
                            <h2 className="checklist-cta-title">
                                ¿Quieres que Impuestify detecte automáticamente tus deducciones?
                            </h2>
                            <p className="checklist-cta-sub">
                                Nuestro asistente fiscal IA analiza tu situación, detecta las deducciones autonómicas que te corresponden y te guía paso a paso antes de confirmar tu borrador.
                            </p>
                            <div className="checklist-cta-actions">
                                <Link to="/guia-fiscal" className="checklist-btn-primary checklist-btn-lg">
                                    Hacer la guía fiscal
                                    <ArrowRight size={18} />
                                </Link>
                                <Link to="/register" className="checklist-btn-secondary checklist-btn-lg">
                                    Crear cuenta gratis
                                </Link>
                            </div>
                        </div>
                    </FadeContent>
                </main>
            </div>
        </div>
    )
}
