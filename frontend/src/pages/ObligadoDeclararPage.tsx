import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
    CheckCircle, AlertCircle, ChevronDown, ChevronUp,
    ArrowRight, Calculator, Users, Briefcase, Info
} from 'lucide-react'
import Header from '../components/Header'
import FadeContent from '../components/reactbits/FadeContent'
import { useSEO } from '../hooks/useSEO'
import './ObligadoDeclararPage.css'

// ─── Tipos ───────────────────────────────────────────────────────────────────

type Pagadores = '1' | '2+'
type EsAutonomo = 'si' | 'no' | ''
type CheckerResult = 'obligado' | 'no_obligado' | 'revisar' | null

interface CheckerState {
    pagadores: Pagadores | ''
    ingresos: string
    autonomo: EsAutonomo
}

// ─── Lógica del checker ───────────────────────────────────────────────────────

function calcularResultado(state: CheckerState): CheckerResult {
    const { pagadores, ingresos, autonomo } = state
    if (!pagadores || !ingresos || !autonomo) return null

    const ingresosNum = parseFloat(ingresos.replace(/\./g, '').replace(',', '.'))
    if (isNaN(ingresosNum) || ingresosNum < 0) return null

    // Autónomos siempre obligados
    if (autonomo === 'si') return 'obligado'

    if (pagadores === '1') {
        if (ingresosNum > 22000) return 'obligado'
        return 'no_obligado'
    }

    if (pagadores === '2+') {
        if (ingresosNum > 15876) return 'obligado'
        if (ingresosNum > 0 && ingresosNum <= 15876) return 'revisar'
        return 'no_obligado'
    }

    return null
}

// ─── Datos de la tabla ────────────────────────────────────────────────────────

const LIMITES = [
    {
        situacion: '1 pagador (asalariado estándar)',
        limite: '22.000 EUR',
        nota: 'Sin cambios respecto a 2024',
    },
    {
        situacion: '2 o más pagadores (2.º pagador > 1.500 EUR)',
        limite: '15.876 EUR',
        nota: 'Novedad 2025: sube de 15.000 a 15.876 EUR (alineado con el SMI)',
    },
    {
        situacion: '2 o más pagadores (2.º pagador ≤ 1.500 EUR)',
        limite: '22.000 EUR',
        nota: 'Mismo límite que 1 solo pagador',
    },
    {
        situacion: 'Capital mobiliario o ganancias patrimoniales',
        limite: '1.600 EUR',
        nota: 'Dividendos, intereses, fondos de inversión sujetos a retención',
    },
    {
        situacion: 'Rentas imputadas + Letras del Tesoro + subvenciones',
        limite: '1.000 EUR',
        nota: 'Importe combinado de todas estas fuentes',
    },
    {
        situacion: 'Autónomos (RETA)',
        limite: 'Siempre obligados',
        nota: 'Sin límite de ingresos desde 2023. Independientemente de cuánto factures.',
    },
    {
        situacion: 'Perceptores del Ingreso Mínimo Vital (IMV)',
        limite: 'Siempre obligados',
        nota: 'Obligación expresa para poder continuar percibiendo la prestación',
    },
]

const CONVIENE_DECLARAR = [
    {
        icono: <Calculator size={20} />,
        titulo: 'Te practicaron retenciones en nómina',
        desc: 'Si tu empresa retuvo IRPF de tu salario y tus ingresos reales son bajos, declarar te devuelve lo retenido de más.',
    },
    {
        icono: <CheckCircle size={20} />,
        titulo: 'Tienes deducción por maternidad',
        desc: 'Hasta 1.200 EUR anuales por hijo menor de 3 años si la madre trabaja fuera del hogar. Solo se cobran declarando.',
    },
    {
        icono: <CheckCircle size={20} />,
        titulo: 'Hiciste donativos a ONG o partidos',
        desc: 'Deducción del 80 % sobre los primeros 250 EUR donados y 40 % sobre el resto. Hacienda te lo devuelve.',
    },
    {
        icono: <CheckCircle size={20} />,
        titulo: 'Pagas alquiler de vivienda habitual',
        desc: 'Muchas CCAA mantienen la deducción autonómica por alquiler: hasta 1.237 EUR en Madrid, hasta 600 EUR en Cataluña.',
    },
    {
        icono: <CheckCircle size={20} />,
        titulo: 'Aportaste a plan de pensiones',
        desc: 'Las aportaciones reducen la base imponible. Si no declaras, pierdes esa reducción que puede ser de miles de euros.',
    },
]

const NOVEDADES = [
    {
        titulo: 'Límite 2+ pagadores sube a 15.876 EUR',
        desc: 'Antes era 15.000 EUR. El incremento se debe a la actualización del Salario Mínimo Interprofesional (SMI). Beneficia a contribuyentes con cambio de empleo, ERTE o pluriempleo.',
    },
    {
        titulo: 'Desempleo SEPE ya no obliga automáticamente',
        desc: 'El RDL 16/2025 elimina la obligación de declarar para quienes solo percibieron prestación por desempleo del SEPE. Aplica si el importe no supera los límites generales.',
    },
    {
        titulo: 'Autónomos: sin cambios — siguen obligados siempre',
        desc: 'Desde 2023, cualquier autónomo dado de alta en el RETA está obligado a presentar la declaración, independientemente de sus ingresos anuales.',
    },
]

const FAQS = [
    {
        pregunta: '¿Qué pasa si no declaro estando obligado?',
        respuesta:
            'Hacienda puede imponerte una sanción mínima de 200 EUR por presentación voluntaria fuera de plazo (sin requerimiento previo). Si hay requerimiento de la AEAT, la sanción va del 50 % al 150 % de la cuota no ingresada, más recargos e intereses de demora. En casos graves puede derivar en delito fiscal si supera los 120.000 EUR defraudados.',
    },
    {
        pregunta: '¿Puedo declarar si no estoy obligado?',
        respuesta:
            'Sí, siempre puedes declarar voluntariamente aunque no estés obligado. De hecho, en muchos casos te conviene porque puede salirte a devolver: si te practicaron retenciones en exceso, si tienes deducciones por maternidad, donativos o alquiler de vivienda habitual.',
    },
    {
        pregunta: '¿Los autónomos siempre están obligados a hacer la renta?',
        respuesta:
            'Sí. Desde la reforma fiscal de 2023, cualquier autónomo dado de alta en el Régimen Especial de Trabajadores Autónomos (RETA) está obligado a presentar la declaración de la renta, sin importar cuánto haya facturado. Aunque hayas ganado 0 EUR, debes declarar.',
    },
    {
        pregunta: '¿Cómo afecta tener dos pagadores al límite?',
        respuesta:
            'Si has tenido dos o más pagadores y el segundo (o los siguientes) te pagaron más de 1.500 EUR en total, tu límite baja de 22.000 EUR a 15.876 EUR. Casos habituales: cambio de empresa durante el año, ERTE con prestación del SEPE, pluriempleo o percibir pensión de jubilación y seguir trabajando.',
    },
]

// ─── Componente FAQ individual ────────────────────────────────────────────────

function FaqItem({ pregunta, respuesta }: { pregunta: string; respuesta: string }) {
    const [open, setOpen] = useState(false)

    return (
        <div className={`od-faq-item ${open ? 'od-faq-item--open' : ''}`}>
            <button
                className="od-faq-trigger"
                onClick={() => setOpen(!open)}
                aria-expanded={open}
            >
                <span>{pregunta}</span>
                {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </button>
            {open && (
                <div className="od-faq-answer">
                    <p>{respuesta}</p>
                </div>
            )}
        </div>
    )
}

// ─── Componente principal ─────────────────────────────────────────────────────

export default function ObligadoDeclararPage() {
    const [checker, setChecker] = useState<CheckerState>({
        pagadores: '',
        ingresos: '',
        autonomo: '',
    })
    const [resultado, setResultado] = useState<CheckerResult>(null)
    const [checked, setChecked] = useState(false)

    useSEO({
        title: '¿Estás obligado a declarar la renta 2026? — Impuestify',
        description: 'Comprueba si tienes que presentar declaración en 2026 según ingresos, tipo de rendimientos, número de pagadores y situación como autónomo.',
        canonical: '/obligado-declarar',
        keywords: 'obligado declarar renta 2026, umbrales declaración, límite rentas IRPF, dos pagadores renta, exento declaración',
        schema: [
            {
                '@context': 'https://schema.org',
                '@type': 'FAQPage',
                mainEntity: [
                    {
                        '@type': 'Question',
                        name: '¿Qué pasa si no declaro estando obligado?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'Hacienda puede imponerte una sanción mínima de 200 EUR por presentación voluntaria fuera de plazo (sin requerimiento previo). Si hay requerimiento de la AEAT, la sanción va del 50 % al 150 % de la cuota no ingresada, más recargos e intereses de demora. En casos graves puede derivar en delito fiscal si supera los 120.000 EUR defraudados.',
                        },
                    },
                    {
                        '@type': 'Question',
                        name: '¿Puedo declarar si no estoy obligado?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'Sí, siempre puedes declarar voluntariamente aunque no estés obligado. De hecho, en muchos casos te conviene porque puede salirte a devolver: si te practicaron retenciones en exceso, si tienes deducciones por maternidad, donativos o alquiler de vivienda habitual.',
                        },
                    },
                    {
                        '@type': 'Question',
                        name: '¿Los autónomos siempre están obligados a hacer la renta?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'Sí. Desde la reforma fiscal de 2023, cualquier autónomo dado de alta en el Régimen Especial de Trabajadores Autónomos (RETA) está obligado a presentar la declaración de la renta, sin importar cuánto haya facturado. Aunque hayas ganado 0 EUR, debes declarar.',
                        },
                    },
                    {
                        '@type': 'Question',
                        name: '¿Cómo afecta tener dos pagadores al límite?',
                        acceptedAnswer: {
                            '@type': 'Answer',
                            text: 'Si has tenido dos o más pagadores y el segundo (o los siguientes) te pagaron más de 1.500 EUR en total, tu límite baja de 22.000 EUR a 15.876 EUR. Casos habituales: cambio de empresa durante el año, ERTE con prestación del SEPE, pluriempleo o percibir pensión de jubilación y seguir trabajando.',
                        },
                    },
                ],
            },
            {
                '@context': 'https://schema.org',
                '@type': 'BreadcrumbList',
                itemListElement: [
                    { '@type': 'ListItem', position: 1, name: 'Inicio', item: 'https://impuestify.com' },
                    { '@type': 'ListItem', position: 2, name: '¿Obligado a declarar?', item: 'https://impuestify.com/obligado-declarar' },
                ],
            },
        ],
    })

    const handleComprobar = () => {
        const res = calcularResultado(checker)
        setResultado(res)
        setChecked(true)
    }

    const handleReset = () => {
        setChecker({ pagadores: '', ingresos: '', autonomo: '' })
        setResultado(null)
        setChecked(false)
    }

    const checkerCompleto =
        checker.pagadores !== '' &&
        checker.ingresos !== '' &&
        checker.autonomo !== ''

    return (
        <div className="od-page">
            <Header />

            {/* ── Hero ─────────────────────────────────────────────────── */}
            <section className="od-hero">
                <div className="od-container">
                    <FadeContent direction="up" duration={600}>
                        <div className="od-hero-badge">
                            <Calculator size={14} />
                            <span>Renta 2025 — Campaña 2026</span>
                        </div>
                        <h1 className="od-hero-title">
                            ¿Estás obligado a declarar<br />
                            la renta en 2026?
                        </h1>
                        <p className="od-hero-subtitle">
                            Tres preguntas y lo sabes. Con los umbrales de la campaña 2025/2026, incluido
                            el nuevo tope de 15.876 EUR para dos pagadores.
                        </p>
                    </FadeContent>
                </div>
            </section>

            {/* ── Mini-checker ─────────────────────────────────────────── */}
            <section className="od-checker-section">
                <div className="od-container od-container--narrow">
                    <FadeContent direction="up" duration={700} delay={100}>
                        <div className="od-checker-card">
                            <h2 className="od-checker-title">Comprobador rápido</h2>
                            <p className="od-checker-desc">
                                Tres preguntas, resultado al instante.
                            </p>

                            {/* Pregunta 1 */}
                            <div className="od-question">
                                <label className="od-question-label">
                                    <Users size={16} />
                                    <span>1. ¿Cuántos pagadores has tenido en 2025?</span>
                                </label>
                                <div className="od-btn-group">
                                    <button
                                        className={`od-option-btn ${checker.pagadores === '1' ? 'od-option-btn--active' : ''}`}
                                        onClick={() => setChecker(p => ({ ...p, pagadores: '1' }))}
                                    >
                                        Solo 1 pagador
                                    </button>
                                    <button
                                        className={`od-option-btn ${checker.pagadores === '2+' ? 'od-option-btn--active' : ''}`}
                                        onClick={() => setChecker(p => ({ ...p, pagadores: '2+' }))}
                                    >
                                        2 o más pagadores
                                    </button>
                                </div>
                                {checker.pagadores === '2+' && (
                                    <p className="od-question-hint">
                                        <Info size={13} />
                                        Incluye cambios de empresa, ERTE, prestación del SEPE,
                                        pensión + trabajo, pluriempleo.
                                    </p>
                                )}
                            </div>

                            {/* Pregunta 2 */}
                            <div className="od-question">
                                <label className="od-question-label" htmlFor="od-ingresos">
                                    <Calculator size={16} />
                                    <span>2. ¿Cuánto has ganado en total (bruto anual)?</span>
                                </label>
                                <div className="od-input-wrap">
                                    <input
                                        id="od-ingresos"
                                        type="number"
                                        className="od-input"
                                        placeholder="Ej: 21500"
                                        value={checker.ingresos}
                                        min={0}
                                        onChange={e =>
                                            setChecker(p => ({ ...p, ingresos: e.target.value }))
                                        }
                                    />
                                    <span className="od-input-suffix">EUR brutos</span>
                                </div>
                            </div>

                            {/* Pregunta 3 */}
                            <div className="od-question">
                                <label className="od-question-label">
                                    <Briefcase size={16} />
                                    <span>3. ¿Eres autónomo (dado de alta en el RETA)?</span>
                                </label>
                                <div className="od-btn-group">
                                    <button
                                        className={`od-option-btn ${checker.autonomo === 'si' ? 'od-option-btn--active' : ''}`}
                                        onClick={() => setChecker(p => ({ ...p, autonomo: 'si' }))}
                                    >
                                        Sí, soy autónomo
                                    </button>
                                    <button
                                        className={`od-option-btn ${checker.autonomo === 'no' ? 'od-option-btn--active' : ''}`}
                                        onClick={() => setChecker(p => ({ ...p, autonomo: 'no' }))}
                                    >
                                        No, soy asalariado
                                    </button>
                                </div>
                            </div>

                            {/* Botón comprobar */}
                            {!checked && (
                                <button
                                    className="od-check-btn"
                                    onClick={handleComprobar}
                                    disabled={!checkerCompleto}
                                >
                                    Comprobar ahora
                                    <ArrowRight size={16} />
                                </button>
                            )}

                            {/* Resultado */}
                            {checked && resultado && (
                                <div
                                    className={`od-result od-result--${resultado}`}
                                    role="alert"
                                    aria-live="polite"
                                >
                                    {resultado === 'obligado' && (
                                        <>
                                            <div className="od-result-icon">
                                                <AlertCircle size={28} />
                                            </div>
                                            <div className="od-result-body">
                                                <strong>Sí, estás obligado a declarar</strong>
                                                <p>
                                                    {checker.autonomo === 'si'
                                                        ? 'Los autónomos dados de alta en el RETA están obligados a presentar la declaración de la renta sin excepción, independientemente de sus ingresos.'
                                                        : `Tus ingresos de ${parseFloat(checker.ingresos).toLocaleString('es-ES')} EUR superan el límite aplicable a tu situación. Debes presentar la declaración antes del 30 de junio de 2026.`}
                                                </p>
                                                <Link to="/guia-fiscal" className="od-result-cta">
                                                    Calcular mi resultado ahora
                                                    <ArrowRight size={14} />
                                                </Link>
                                            </div>
                                        </>
                                    )}
                                    {resultado === 'no_obligado' && (
                                        <>
                                            <div className="od-result-icon">
                                                <CheckCircle size={28} />
                                            </div>
                                            <div className="od-result-body">
                                                <strong>No, no estás obligado a declarar</strong>
                                                <p>
                                                    Tus ingresos no llegan al umbral. Puede aun así compensarte
                                                    presentarla si te retuvieron en nómina o tienes deducciones
                                                    sin aplicar.
                                                </p>
                                                <Link to="/guia-fiscal" className="od-result-cta">
                                                    Mira si te sale a devolver
                                                    <ArrowRight size={14} />
                                                </Link>
                                            </div>
                                        </>
                                    )}
                                    {resultado === 'revisar' && (
                                        <>
                                            <div className="od-result-icon">
                                                <Info size={28} />
                                            </div>
                                            <div className="od-result-body">
                                                <strong>Depende del importe del segundo pagador</strong>
                                                <p>
                                                    Con 2 o más pagadores, el límite es 15.876 EUR solo si el
                                                    segundo pagador te pagó más de 1.500 EUR. Si el segundo
                                                    pagador no supera esa cifra, el límite es 22.000 EUR.
                                                    Revisa tu situación exacta más abajo.
                                                </p>
                                                <Link to="/guia-fiscal" className="od-result-cta">
                                                    Hacer simulación completa
                                                    <ArrowRight size={14} />
                                                </Link>
                                            </div>
                                        </>
                                    )}
                                    <button
                                        className="od-reset-btn"
                                        onClick={handleReset}
                                        aria-label="Volver a empezar"
                                    >
                                        Volver a empezar
                                    </button>
                                </div>
                            )}

                            <p className="od-checker-disclaimer">
                                Resultado orientativo. Para inmuebles, cripto o herencias, tira de la guía
                                fiscal completa o pregunta a un asesor.
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ── Tabla de límites ──────────────────────────────────────── */}
            <section className="od-section">
                <div className="od-container">
                    <FadeContent direction="up" duration={600}>
                        <h2 className="od-section-title">
                            Límites de obligación de declarar — Renta 2025/2026
                        </h2>
                        <p className="od-section-desc">
                            Ejercicio fiscal 2025. Campaña de declaración: del 2 de abril al 30 de junio de 2026.
                        </p>

                        <div className="od-table-wrap">
                            <table className="od-table">
                                <thead>
                                    <tr>
                                        <th>Situación</th>
                                        <th>Límite</th>
                                        <th>Nota</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {LIMITES.map((row, i) => (
                                        <tr key={i}>
                                            <td>{row.situacion}</td>
                                            <td>
                                                <span
                                                    className={`od-badge ${
                                                        row.limite === 'Siempre obligados'
                                                            ? 'od-badge--warning'
                                                            : 'od-badge--info'
                                                    }`}
                                                >
                                                    {row.limite}
                                                </span>
                                            </td>
                                            <td>{row.nota}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ── Novedades 2025 ────────────────────────────────────────── */}
            <section className="od-section od-section--alt">
                <div className="od-container">
                    <FadeContent direction="up" duration={600}>
                        <h2 className="od-section-title">Novedades 2025: ¿qué ha cambiado?</h2>
                        <p className="od-section-desc">
                            Cambios que afectan a la obligación de declarar en la campaña de 2026 respecto
                            al ejercicio anterior.
                        </p>

                        <div className="od-novedades-grid">
                            {NOVEDADES.map((n, i) => (
                                <FadeContent key={i} direction="up" duration={500} delay={i * 80}>
                                    <div className="od-novedad-card">
                                        <h3 className="od-novedad-title">{n.titulo}</h3>
                                        <p className="od-novedad-desc">{n.desc}</p>
                                    </div>
                                </FadeContent>
                            ))}
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ── Aunque no estés obligado ─────────────────────────────── */}
            <section className="od-section">
                <div className="od-container">
                    <FadeContent direction="up" duration={600}>
                        <h2 className="od-section-title">
                            Aunque no estés obligado, te conviene declarar si...
                        </h2>
                        <p className="od-section-desc">
                            No estar obligado no siempre es la mejor noticia. En estos casos, declarar
                            voluntariamente puede suponer una devolución significativa de Hacienda.
                        </p>

                        <div className="od-conviene-grid">
                            {CONVIENE_DECLARAR.map((item, i) => (
                                <FadeContent key={i} direction="up" duration={500} delay={i * 70}>
                                    <div className="od-conviene-card">
                                        <div className="od-conviene-icon">{item.icono}</div>
                                        <div className="od-conviene-body">
                                            <strong>{item.titulo}</strong>
                                            <p>{item.desc}</p>
                                        </div>
                                    </div>
                                </FadeContent>
                            ))}
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ── CTA central ──────────────────────────────────────────── */}
            <section className="od-cta-section">
                <div className="od-container od-container--narrow">
                    <FadeContent direction="up" duration={600}>
                        <div className="od-cta-card">
                            <h2 className="od-cta-title">Calcula tu resultado en 2 minutos</h2>
                            <p className="od-cta-desc">
                                La guía fiscal de Impuestify te muestra en tiempo real si tu declaración
                                sale a devolver o a pagar. Sin registro. Sin esperas. Simulador IRPF
                                basado en normativa oficial 2025.
                            </p>
                            <Link to="/guia-fiscal" className="od-cta-btn">
                                Ir a la guía fiscal
                                <ArrowRight size={18} />
                            </Link>
                            <p className="od-cta-note">
                                Cubre las 17 comunidades autónomas + País Vasco + Navarra + Canarias +
                                Ceuta y Melilla
                            </p>
                        </div>
                    </FadeContent>
                </div>
            </section>

            {/* ── FAQ ──────────────────────────────────────────────────── */}
            <section className="od-section od-section--alt">
                <div className="od-container od-container--narrow">
                    <FadeContent direction="up" duration={600}>
                        <h2 className="od-section-title">Preguntas frecuentes</h2>
                        <div className="od-faq-list">
                            {FAQS.map((faq, i) => (
                                <FaqItem key={i} pregunta={faq.pregunta} respuesta={faq.respuesta} />
                            ))}
                        </div>
                    </FadeContent>
                </div>
            </section>

        </div>
    )
}
