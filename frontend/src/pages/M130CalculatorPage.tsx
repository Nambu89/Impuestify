import { useState, useMemo } from 'react'
import {
    Calculator,
    Info,
    AlertTriangle,
    CheckCircle2,
    ChevronDown,
    ChevronUp,
    Euro,
    ArrowRight,
    Calendar,
    Download,
    Loader2,
} from 'lucide-react'
import Header from '../components/Header'
import { useModeloPDF } from '../hooks/useModeloPDF'
import './M130CalculatorPage.css'

// -------------------------------------------------------
// Tipos
// -------------------------------------------------------

type Trimestre = 'Q1' | 'Q2' | 'Q3' | 'Q4'

interface M130Input {
    ingresos: number
    gastos: number
    retenciones: number
    pagosAnteriores: number
    esCeutaMelilla: boolean
    // Opcionales colapsados
    minoraRentas: boolean   // casilla 13 auto
    deduccionVivienda: number  // casilla 16
    resultadosNegativos: number  // casilla 15
}

interface M130Result {
    casilla01: number
    casilla02: number
    casilla03: number
    casilla04: number
    casilla05: number
    casilla06: number
    casilla07: number
    casilla13: number
    casilla15: number
    casilla16: number
    casilla17: number
    casilla19: number
    porcentaje: number
}

// -------------------------------------------------------
// Constantes
// -------------------------------------------------------

const TRIMESTRES: { key: Trimestre; label: string; periodo: string; fechaLimite: string }[] = [
    { key: 'Q1', label: '1T', periodo: 'Ene — Mar', fechaLimite: '20 de abril de 2026' },
    { key: 'Q2', label: '2T', periodo: 'Ene — Jun', fechaLimite: '20 de julio de 2026' },
    { key: 'Q3', label: '3T', periodo: 'Ene — Sep', fechaLimite: '20 de octubre de 2026' },
    { key: 'Q4', label: '4T', periodo: 'Ene — Dic', fechaLimite: '30 de enero de 2027' },
]

const DEFAULT_INPUT: M130Input = {
    ingresos: 0,
    gastos: 0,
    retenciones: 0,
    pagosAnteriores: 0,
    esCeutaMelilla: false,
    minoraRentas: false,
    deduccionVivienda: 0,
    resultadosNegativos: 0,
}

// Minoración casilla 13: según rendimiento neto anual estimado
function calcularMinoracion(rendimientoNeto: number, trimestre: Trimestre): number {
    // El rendimiento neto en la casilla 03 es el acumulado del año.
    // La escala de la casilla 13 se basa en la estimación anual (se anualiza si no es Q4).
    // Aproximación: multiplicamos el acumulado por (4 / numero_trimestre) para anualizar
    const factorAnualizacion: Record<Trimestre, number> = { Q1: 4, Q2: 2, Q3: 4 / 3, Q4: 1 }
    const neto_anual_estimado = rendimientoNeto * factorAnualizacion[trimestre]

    let minoracion_anual = 0
    if (neto_anual_estimado <= 9000) minoracion_anual = 100
    else if (neto_anual_estimado <= 10000) minoracion_anual = 75
    else if (neto_anual_estimado <= 11000) minoracion_anual = 50
    else if (neto_anual_estimado <= 12000) minoracion_anual = 25

    // El valor de la casilla 13 es el trimestral (la minoración es por trimestre)
    return minoracion_anual
}

// -------------------------------------------------------
// Cálculo principal
// -------------------------------------------------------

function calcularM130(input: M130Input, trimestre: Trimestre): M130Result {
    const casilla01 = Math.max(input.ingresos, 0)
    const casilla02 = Math.max(input.gastos, 0)
    const casilla03 = Math.max(casilla01 - casilla02, 0)

    const porcentaje = input.esCeutaMelilla ? 0.08 : 0.20
    const casilla04 = casilla03 * porcentaje

    // Casilla 05 = pagos fraccionados de trimestres anteriores
    const casilla05 = Math.max(input.pagosAnteriores, 0)
    // Casilla 06 = retenciones acumuladas
    const casilla06 = Math.max(input.retenciones, 0)

    // Casilla 07 = 04 - 05 - 06 (mínimo 0)
    const casilla07 = Math.max(casilla04 - casilla05 - casilla06, 0)

    // Sección III — Liquidación
    // Casilla 12 = 07 (no tenemos actividades agrícolas en esta calculadora)
    const casilla12 = casilla07

    // Casilla 13 — Minoración rentas < 12.000 EUR (auto si activada)
    const casilla13 = input.minoraRentas ? calcularMinoracion(casilla03, trimestre) : 0

    // Casilla 14 = 12 - 13
    const casilla14 = Math.max(casilla12 - casilla13, 0)

    // Casilla 15 = resultados negativos de trimestres anteriores
    const casilla15 = Math.max(input.resultadosNegativos, 0)

    // Casilla 16 = deducción vivienda (max 660,14 por trimestre)
    const casilla16 = Math.min(Math.max(input.deduccionVivienda, 0), 660.14)

    // Casilla 17 = 14 - 15 - 16
    const casilla17 = Math.max(casilla14 - casilla15 - casilla16, 0)

    // Casilla 19 = resultado final (= casilla 17 en nuestro caso, sin autoliquidaciones previas)
    const casilla19 = casilla17

    return {
        casilla01,
        casilla02,
        casilla03,
        casilla04,
        casilla05,
        casilla06,
        casilla07,
        casilla13,
        casilla15,
        casilla16,
        casilla17,
        casilla19,
        porcentaje,
    }
}

// -------------------------------------------------------
// Helpers UI
// -------------------------------------------------------

function formatEur(value: number): string {
    return value.toLocaleString('es-ES', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })
}

function formatPct(value: number): string {
    return (value * 100).toLocaleString('es-ES', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    })
}

// -------------------------------------------------------
// Sub-componentes
// -------------------------------------------------------

interface NumberInputProps {
    id: string
    label: string
    hint: string
    value: number
    onChange: (v: number) => void
    disabled?: boolean
    step?: number
}

function NumberInput({ id, label, hint, value, onChange, disabled = false, step = 100 }: NumberInputProps) {
    return (
        <div className={`m130-field ${disabled ? 'm130-field--disabled' : ''}`}>
            <label className="m130-label" htmlFor={id}>{label}</label>
            <div className="m130-input-row">
                <Euro size={16} className="m130-input-icon" />
                <input
                    id={id}
                    type="number"
                    className="m130-input"
                    min={0}
                    step={step}
                    value={value || ''}
                    placeholder="0"
                    disabled={disabled}
                    onChange={e => onChange(parseFloat(e.target.value.replace(',', '.')) || 0)}
                />
                <span className="m130-input-suffix">EUR</span>
            </div>
            <p className="m130-field-hint">{hint}</p>
        </div>
    )
}

interface CasillaRowProps {
    numero: string
    label: string
    value: number
    highlight?: 'primary' | 'result' | 'zero' | 'deduction'
}

function CasillaRow({ numero, label, value, highlight }: CasillaRowProps) {
    return (
        <tr className={`m130-casilla-row ${highlight ? `m130-casilla-row--${highlight}` : ''}`}>
            <td className="m130-casilla-num">{numero}</td>
            <td className="m130-casilla-label">{label}</td>
            <td className="m130-casilla-value">{formatEur(value)} EUR</td>
        </tr>
    )
}

// -------------------------------------------------------
// Página principal
// -------------------------------------------------------

export default function M130CalculatorPage() {
    const [trimestre, setTrimestre] = useState<Trimestre>('Q1')
    const [input, setInput] = useState<M130Input>(DEFAULT_INPUT)
    const [advancedOpen, setAdvancedOpen] = useState(false)
    const { downloadPDF, isLoading: pdfLoading, error: pdfError } = useModeloPDF()

    const trimestreInfo = TRIMESTRES.find(t => t.key === trimestre)!

    const result = useMemo(() => calcularM130(input, trimestre), [input, trimestre])

    const hasData = input.ingresos > 0 || input.gastos > 0 || input.retenciones > 0
    const esCero = result.casilla19 === 0

    function setField<K extends keyof M130Input>(key: K, value: M130Input[K]) {
        setInput(prev => ({ ...prev, [key]: value }))
    }

    function handleTrimestre(t: Trimestre) {
        setTrimestre(t)
        // Si cambiamos a Q1, pagos anteriores no aplica
        if (t === 'Q1') {
            setInput(prev => ({ ...prev, pagosAnteriores: 0 }))
        }
    }

    return (
        <div className="m130-page">
            <Header />

            <main className="m130-main">

                {/* ---- Hero ---- */}
                <div className="m130-hero">
                    <div className="m130-hero-badge">
                        <Calculator size={14} />
                        <span>Estimación directa normal y simplificada</span>
                    </div>
                    <h1 className="m130-title">
                        Calculadora{' '}
                        <span className="m130-title-highlight">Modelo 130</span>
                    </h1>
                    <p className="m130-subtitle">
                        Calcula tu pago fraccionado de IRPF trimestral como autónomo.
                        Fórmula oficial Art. 101 LIRPF — cálculo 100% en tu dispositivo.
                    </p>
                </div>

                {/* ---- Aviso importante ---- */}
                <div className="m130-alert">
                    <AlertTriangle size={16} />
                    <div>
                        <strong>Importante:</strong> todos los importes son <strong>acumulados desde el 1 de enero</strong>,
                        no solo del trimestre. Si pones solo los datos del trimestre, el resultado será incorrecto.
                    </div>
                </div>

                {/* ---- Layout ---- */}
                <div className={`m130-layout ${hasData ? 'm130-layout--split' : ''}`}>

                    {/* ========== Panel izquierdo: inputs ========== */}
                    <section className="m130-inputs-panel">

                        {/* Selector trimestre */}
                        <div className="m130-trim-card">
                            <p className="m130-trim-label">
                                <Calendar size={14} />
                                Trimestre que presentas
                            </p>
                            <div className="m130-trim-buttons">
                                {TRIMESTRES.map(t => (
                                    <button
                                        key={t.key}
                                        className={`m130-trim-btn ${trimestre === t.key ? 'm130-trim-btn--active' : ''}`}
                                        onClick={() => handleTrimestre(t.key)}
                                    >
                                        <span className="m130-trim-btn-label">{t.label}</span>
                                        <span className="m130-trim-btn-periodo">{t.periodo}</span>
                                    </button>
                                ))}
                            </div>
                            <p className="m130-trim-deadline">
                                <Calendar size={12} />
                                Fecha límite: <strong>{trimestreInfo.fechaLimite}</strong>
                            </p>
                        </div>

                        {/* Toggle Ceuta/Melilla */}
                        <div className="m130-ceuta-row">
                            <label className="m130-toggle-label" htmlFor="ceuta">
                                <input
                                    id="ceuta"
                                    type="checkbox"
                                    className="m130-toggle-input"
                                    checked={input.esCeutaMelilla}
                                    onChange={e => setField('esCeutaMelilla', e.target.checked)}
                                />
                                <span className="m130-toggle-track" />
                                <span className="m130-toggle-text">
                                    Actividad en Ceuta o Melilla (tipo reducido 8%)
                                </span>
                            </label>
                        </div>

                        {/* Inputs principales */}
                        <div className="m130-fields-card">
                            <h2 className="m130-fields-title">
                                Datos acumulados — 1 enero a fin de {trimestreInfo.periodo.split('—')[1].trim()}
                            </h2>

                            <NumberInput
                                id="ingresos"
                                label="Casilla 01 — Ingresos acumulados"
                                hint="Total facturado sin IVA desde el 1 de enero. No incluyas el IVA repercutido."
                                value={input.ingresos}
                                onChange={v => setField('ingresos', v)}
                            />

                            <NumberInput
                                id="gastos"
                                label="Casilla 02 — Gastos deducibles acumulados"
                                hint="Cuota de autónomos, suministros, material, formación, alquiler local, vehículo... sin IVA."
                                value={input.gastos}
                                onChange={v => setField('gastos', v)}
                            />

                            <NumberInput
                                id="retenciones"
                                label="Casilla 06 — Retenciones soportadas acumuladas"
                                hint="Retenciones de IRPF que tus clientes te han practicado en facturas este año."
                                value={input.retenciones}
                                onChange={v => setField('retenciones', v)}
                            />

                            <NumberInput
                                id="pagos"
                                label="Casilla 05 — Pagos fraccionados anteriores"
                                hint="Suma de los importes positivos pagados en los M130 anteriores de este año."
                                value={input.pagosAnteriores}
                                onChange={v => setField('pagosAnteriores', v)}
                                disabled={trimestre === 'Q1'}
                            />
                            {trimestre === 'Q1' && (
                                <p className="m130-q1-note">
                                    En el primer trimestre no hay pagos anteriores.
                                </p>
                            )}
                        </div>

                        {/* Opciones avanzadas */}
                        <div className="m130-advanced">
                            <button
                                className="m130-advanced-toggle"
                                onClick={() => setAdvancedOpen(o => !o)}
                                aria-expanded={advancedOpen}
                            >
                                <span>Opciones avanzadas (casillas 13, 15, 16)</span>
                                {advancedOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                            </button>

                            {advancedOpen && (
                                <div className="m130-advanced-body">

                                    {/* Casilla 13 — Minoración */}
                                    <div className="m130-advanced-field">
                                        <label className="m130-toggle-label" htmlFor="minora">
                                            <input
                                                id="minora"
                                                type="checkbox"
                                                className="m130-toggle-input"
                                                checked={input.minoraRentas}
                                                onChange={e => setField('minoraRentas', e.target.checked)}
                                            />
                                            <span className="m130-toggle-track" />
                                            <span className="m130-toggle-text">
                                                Aplicar minoración Casilla 13 (rendimiento neto &lt; 12.000 EUR anuales)
                                            </span>
                                        </label>
                                        {input.minoraRentas && result.casilla13 > 0 && (
                                            <p className="m130-advanced-calc">
                                                Minoración aplicada: {formatEur(result.casilla13)} EUR
                                                (estimación anual {formatEur(result.casilla03 * { Q1: 4, Q2: 2, Q3: 4 / 3, Q4: 1 }[trimestre])} EUR)
                                            </p>
                                        )}
                                        {input.minoraRentas && result.casilla13 === 0 && (
                                            <p className="m130-advanced-calc m130-advanced-calc--none">
                                                Rendimiento neto estimado &gt;= 12.000 EUR anuales — no aplica minoración.
                                            </p>
                                        )}
                                    </div>

                                    {/* Casilla 15 — Resultados negativos */}
                                    <NumberInput
                                        id="negativos"
                                        label="Casilla 15 — Resultados negativos de trimestres anteriores"
                                        hint="Si en un trimestre anterior el resultado fue negativo (Casilla 07 < 0), puedes compensarlo aquí."
                                        value={input.resultadosNegativos}
                                        onChange={v => setField('resultadosNegativos', v)}
                                        step={10}
                                    />

                                    {/* Casilla 16 — Deducción vivienda */}
                                    <NumberInput
                                        id="vivienda"
                                        label="Casilla 16 — Deducción vivienda habitual (pre-2013)"
                                        hint="Solo si compraste la vivienda habitual antes del 1 de enero de 2013. Máximo 660,14 EUR por trimestre."
                                        value={input.deduccionVivienda}
                                        onChange={v => setField('deduccionVivienda', v)}
                                        step={10}
                                    />
                                    {input.deduccionVivienda > 660.14 && (
                                        <p className="m130-advanced-calc m130-advanced-calc--warn">
                                            Limitado al máximo legal: 660,14 EUR por trimestre.
                                        </p>
                                    )}

                                </div>
                            )}
                        </div>

                        {/* Disclaimer */}
                        <div className="m130-disclaimer">
                            <Info size={14} />
                            <span>
                                Cálculo orientativo. Para declaraciones reales usa el formulario oficial de
                                la <a className="m130-link" href="https://sede.agenciatributaria.gob.es" target="_blank" rel="noopener noreferrer">AEAT</a>.
                                No incluye actividades agrícolas (casillas 08-11).
                            </span>
                        </div>
                    </section>

                    {/* ========== Panel derecho: resultado ========== */}
                    {hasData && (
                        <section className="m130-result-panel" aria-live="polite">

                            {/* Tarjeta resultado principal */}
                            <div className={`m130-result-card ${esCero ? 'm130-result-card--zero' : 'm130-result-card--pagar'}`}>
                                <div className="m130-result-label">
                                    {esCero ? (
                                        <><CheckCircle2 size={18} /> Sin ingreso este trimestre</>
                                    ) : (
                                        <><Euro size={18} /> A ingresar en Hacienda</>
                                    )}
                                </div>
                                <div className="m130-result-amount">
                                    {formatEur(result.casilla19)}
                                    <span className="m130-result-currency">EUR</span>
                                </div>
                                <div className="m130-result-sub">
                                    Tipo aplicado: {formatPct(result.porcentaje)}%
                                    {input.esCeutaMelilla ? ' (Ceuta/Melilla)' : ' (tipo general)'}
                                </div>
                                <div className="m130-result-deadline">
                                    <Calendar size={13} />
                                    Plazo: {trimestreInfo.fechaLimite}
                                </div>
                            </div>

                            {/* Tabla casillas */}
                            <div className="m130-casillas-card">
                                <h3 className="m130-casillas-title">Desglose por casillas oficiales</h3>
                                <table className="m130-casillas-table">
                                    <thead>
                                        <tr>
                                            <th className="m130-th-num">Cas.</th>
                                            <th className="m130-th-label">Concepto</th>
                                            <th className="m130-th-value">Importe</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr className="m130-section-header">
                                            <td colSpan={3}>Sección I — Estimación Directa</td>
                                        </tr>
                                        <CasillaRow numero="01" label="Ingresos acumulados (sin IVA)" value={result.casilla01} />
                                        <CasillaRow numero="02" label="Gastos deducibles acumulados" value={result.casilla02} highlight="deduction" />
                                        <CasillaRow numero="03" label="Rendimiento neto (01 - 02)" value={result.casilla03} highlight="primary" />
                                        <CasillaRow numero="04" label={`${formatPct(result.porcentaje)}% de casilla 03`} value={result.casilla04} highlight="primary" />
                                        <CasillaRow numero="05" label="Pagos fraccionados anteriores" value={result.casilla05} highlight="deduction" />
                                        <CasillaRow numero="06" label="Retenciones soportadas" value={result.casilla06} highlight="deduction" />
                                        <CasillaRow numero="07" label="Resultado (04 - 05 - 06)" value={result.casilla07} highlight="primary" />

                                        <tr className="m130-section-header">
                                            <td colSpan={3}>Sección III — Liquidación</td>
                                        </tr>
                                        <CasillaRow numero="12" label="Base liquidacion (= casilla 07)" value={result.casilla07} />
                                        {result.casilla13 > 0 && (
                                            <CasillaRow numero="13" label="Minoración rentas bajas" value={result.casilla13} highlight="deduction" />
                                        )}
                                        {result.casilla15 > 0 && (
                                            <CasillaRow numero="15" label="Resultados negativos anteriores" value={result.casilla15} highlight="deduction" />
                                        )}
                                        {result.casilla16 > 0 && (
                                            <CasillaRow numero="16" label="Deducción vivienda pre-2013" value={result.casilla16} highlight="deduction" />
                                        )}
                                        <CasillaRow
                                            numero="19"
                                            label="RESULTADO FINAL A INGRESAR"
                                            value={result.casilla19}
                                            highlight={esCero ? 'zero' : 'result'}
                                        />
                                    </tbody>
                                </table>
                            </div>

                            {/* Info: si resultado cero */}
                            {esCero && input.ingresos > 0 && (
                                <div className="m130-info-card m130-info-card--ok">
                                    <CheckCircle2 size={16} />
                                    <div>
                                        <p>
                                            Tu resultado es <strong>0 EUR</strong>. Las retenciones y pagos anteriores cubren
                                            el 20% sobre tu rendimiento neto.
                                        </p>
                                        <p>
                                            Aunque el resultado sea cero, <strong>debes presentar el modelo igualmente</strong> antes
                                            del {trimestreInfo.fechaLimite}.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Info: porcentaje efectivo */}
                            {!esCero && result.casilla01 > 0 && (
                                <div className="m130-info-card m130-info-card--info">
                                    <Info size={16} />
                                    <div>
                                        <p>
                                            Pagas <strong>{formatEur(result.casilla19)} EUR</strong> ahora, lo que representa
                                            un <strong>{((result.casilla19 / result.casilla01) * 100).toLocaleString('es-ES', { maximumFractionDigits: 1 })}%</strong> de tus ingresos brutos acumulados.
                                        </p>
                                        <p>
                                            Este pago reduce tu deuda de IRPF en la declaración anual de la renta.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* Descargar PDF */}
                            <div className="m130-cta-card">
                                <button
                                    className="m130-cta-btn"
                                    style={{ width: '100%', justifyContent: 'center', border: 'none', cursor: pdfLoading ? 'wait' : 'pointer' }}
                                    onClick={() => {
                                        const trimestreLabel = trimestre.replace('Q', '') + 'T'
                                        const ejercicio = new Date().getFullYear()
                                        downloadPDF('130', { ...input, ...result }, trimestreLabel, ejercicio)
                                    }}
                                    disabled={pdfLoading}
                                >
                                    {pdfLoading ? <Loader2 size={16} className="spin" /> : <Download size={16} />}
                                    {pdfLoading ? 'Generando...' : 'Descargar PDF'}
                                </button>
                                {pdfError && <p className="m130-advanced-calc m130-advanced-calc--warn">{pdfError}</p>}
                            </div>

                            {/* CTA */}
                            <div className="m130-cta-card">
                                <p className="m130-cta-text">
                                    ¿Quieres un cálculo más completo con todas tus deducciones autonómicas?
                                </p>
                                <a href="/guia-fiscal" className="m130-cta-btn">
                                    Ir a la Guía Fiscal
                                    <ArrowRight size={16} />
                                </a>
                            </div>

                        </section>
                    )}
                </div>

                {/* ---- Pain points — Solo cuando no hay datos ---- */}
                {!hasData && (
                    <div className="m130-tips">
                        <h3 className="m130-tips-title">Errores frecuentes al rellenar el M130</h3>
                        <div className="m130-tips-grid">
                            {[
                                {
                                    icon: '01',
                                    titulo: 'Importes no acumulados',
                                    desc: 'Los importes son desde el 1 de enero, no solo del trimestre actual. Es el error más común.',
                                },
                                {
                                    icon: '02',
                                    titulo: 'Incluir el IVA',
                                    desc: 'Los ingresos y gastos van sin IVA. El IVA se declara en el Modelo 303, no en el 130.',
                                },
                                {
                                    icon: '03',
                                    titulo: 'Olvidar retenciones',
                                    desc: 'Si tus clientes te retienen el 15% en facturas, esas retenciones reducen lo que pagas ahora.',
                                },
                                {
                                    icon: '04',
                                    titulo: 'No presentar en trimestres sin actividad',
                                    desc: 'Aunque no hayas facturado, debes presentar el M130 con resultado cero.',
                                },
                            ].map(tip => (
                                <div key={tip.icon} className="m130-tip-card">
                                    <div className="m130-tip-num">{tip.icon}</div>
                                    <div>
                                        <p className="m130-tip-title">{tip.titulo}</p>
                                        <p className="m130-tip-desc">{tip.desc}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

            </main>
        </div>
    )
}
