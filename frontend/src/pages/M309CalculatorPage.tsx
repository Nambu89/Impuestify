import { useState } from 'react'
import {
    Calculator,
    Info,
    AlertTriangle,
    Euro,
    Calendar,
    Download,
    Loader2,
} from 'lucide-react'
import Header from '../components/Header'
import { useM309 } from '../hooks/useM309'
import { useModeloPDF } from '../hooks/useModeloPDF'
import './M130CalculatorPage.css'

const TRIMESTRES = [
    { value: '1T', label: '1T', periodo: 'Ene – Mar', fechaLimite: '20 de abril de 2026' },
    { value: '2T', label: '2T', periodo: 'Abr – Jun', fechaLimite: '20 de julio de 2026' },
    { value: '3T', label: '3T', periodo: 'Jul – Sep', fechaLimite: '20 de octubre de 2026' },
    { value: '4T', label: '4T', periodo: 'Oct – Dic', fechaLimite: '30 de enero de 2027' },
]

function formatEur(v: number) {
    return v.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const currentYear = new Date().getFullYear()

interface NumberFieldProps {
    id: string
    label: string
    hint: string
    value: number
    onChange: (v: number) => void
}

function NumberField({ id, label, hint, value, onChange }: NumberFieldProps) {
    return (
        <div className="m130-field">
            <label className="m130-label" htmlFor={id}>{label}</label>
            <div className="m130-input-row">
                <Euro size={16} className="m130-input-icon" />
                <input
                    id={id}
                    type="number"
                    className="m130-input"
                    min={0}
                    step={10}
                    placeholder="0"
                    value={value || ''}
                    onChange={e => onChange(parseFloat(e.target.value) || 0)}
                />
                <span className="m130-input-suffix">EUR</span>
            </div>
            {hint && <p className="m130-field-hint">{hint}</p>}
        </div>
    )
}

export default function M309CalculatorPage() {
    const [trimestre, setTrimestre] = useState('1T')
    const [year, setYear] = useState(currentYear)
    const [aplicaRE, setAplicaRE] = useState(true)

    // Adquisiciones intracomunitarias
    const [baseIntra21, setBaseIntra21] = useState(0)
    const [baseIntra10, setBaseIntra10] = useState(0)
    const [baseIntra4, setBaseIntra4] = useState(0)
    const [baseIntraTabaco, setBaseIntraTabaco] = useState(0)

    // Inversion del sujeto pasivo
    const [baseISP21, setBaseISP21] = useState(0)
    const [baseISP10, setBaseISP10] = useState(0)
    const [baseISP4, setBaseISP4] = useState(0)

    const { result, loading, error, calculate } = useM309()
    const { downloadPDF, isLoading: pdfLoading, error: pdfError } = useModeloPDF()

    const trimestreInfo = TRIMESTRES.find(t => t.value === trimestre)!

    const hasData = baseIntra21 > 0 || baseIntra10 > 0 || baseIntra4 > 0 || baseIntraTabaco > 0
        || baseISP21 > 0 || baseISP10 > 0 || baseISP4 > 0

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        await calculate({
            periodo: trimestre,
            year,
            base_intracomunitarias_21: baseIntra21,
            base_intracomunitarias_10: baseIntra10,
            base_intracomunitarias_4: baseIntra4,
            base_intracomunitarias_tabaco: baseIntraTabaco,
            base_isp_21: baseISP21,
            base_isp_10: baseISP10,
            base_isp_4: baseISP4,
            aplica_re: aplicaRE,
        })
    }

    const hasResult = result && result.success

    return (
        <div className="m130-page">
            <Header />
            <main className="m130-main">
                <div className="m130-hero">
                    <div className="m130-hero-badge">
                        <Calculator size={14} />
                        <span>Autoliquidacion no periodica — Recargo de Equivalencia</span>
                    </div>
                    <h1 className="m130-title">
                        Calculadora <span className="m130-title-highlight">Modelo 309</span>
                    </h1>
                    <p className="m130-subtitle">
                        Declaracion-liquidacion no periodica del IVA para comerciantes minoristas en
                        Recargo de Equivalencia que realizan adquisiciones intracomunitarias o con
                        inversion del sujeto pasivo.
                    </p>
                </div>

                <div className="m130-alert">
                    <AlertTriangle size={16} />
                    <div>
                        <strong>Cuando usar el Modelo 309:</strong> Si eres comerciante en Recargo de Equivalencia
                        y compras mercancias a un proveedor de la Union Europea, o aplicas inversion del sujeto pasivo.
                        <strong> No confundir con el Modelo 308</strong> (devoluciones a viajeros tax-free).
                    </div>
                </div>

                <div className={`m130-layout ${hasResult ? 'm130-layout--split' : ''}`}>
                    <section className="m130-inputs-panel">
                        <form onSubmit={handleSubmit}>
                            {/* Trimestre */}
                            <div className="m130-trim-card">
                                <p className="m130-trim-label">
                                    <Calendar size={14} />
                                    Trimestre de la operacion
                                </p>
                                <div className="m130-trim-buttons">
                                    {TRIMESTRES.map(t => (
                                        <button
                                            type="button"
                                            key={t.value}
                                            className={`m130-trim-btn ${trimestre === t.value ? 'm130-trim-btn--active' : ''}`}
                                            onClick={() => setTrimestre(t.value)}
                                        >
                                            <span className="m130-trim-btn-label">{t.label}</span>
                                            <span className="m130-trim-btn-periodo">{t.periodo}</span>
                                        </button>
                                    ))}
                                </div>
                                <p className="m130-trim-deadline">
                                    <Calendar size={12} />
                                    Fecha limite: <strong>{trimestreInfo.fechaLimite}</strong>
                                </p>
                            </div>

                            {/* Ejercicio + RE */}
                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">Configuracion</h2>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="year">Ejercicio fiscal</label>
                                    <input
                                        id="year"
                                        type="number"
                                        className="m130-input"
                                        min={2020}
                                        max={2030}
                                        value={year}
                                        onChange={e => setYear(parseInt(e.target.value) || currentYear)}
                                    />
                                </div>
                                <div className="m130-ceuta-row">
                                    <label className="m130-toggle-label" htmlFor="aplica-re">
                                        <input
                                            id="aplica-re"
                                            type="checkbox"
                                            className="m130-toggle-input"
                                            checked={aplicaRE}
                                            onChange={e => setAplicaRE(e.target.checked)}
                                        />
                                        <span className="m130-toggle-track" />
                                        <span className="m130-toggle-text">
                                            Aplicar Recargo de Equivalencia (comerciante minorista)
                                        </span>
                                    </label>
                                </div>
                            </div>

                            {/* Adquisiciones intracomunitarias */}
                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">
                                    Adquisiciones intracomunitarias (Art. 30 bis RIVA)
                                </h2>
                                <NumberField
                                    id="intra21"
                                    label="Base tipo general (21% IVA + 5,2% RE)"
                                    hint="Mercancias de la UE sujetas al tipo general."
                                    value={baseIntra21}
                                    onChange={setBaseIntra21}
                                />
                                <NumberField
                                    id="intra10"
                                    label="Base tipo reducido (10% IVA + 1,4% RE)"
                                    hint="Mercancias de la UE sujetas al tipo reducido."
                                    value={baseIntra10}
                                    onChange={setBaseIntra10}
                                />
                                <NumberField
                                    id="intra4"
                                    label="Base tipo superreducido (4% IVA + 0,5% RE)"
                                    hint="Mercancias de la UE sujetas al tipo superreducido."
                                    value={baseIntra4}
                                    onChange={setBaseIntra4}
                                />
                                <NumberField
                                    id="intraTabaco"
                                    label="Base labores del tabaco (21% IVA + 1,75% RE)"
                                    hint="Adquisiciones intracomunitarias de labores del tabaco."
                                    value={baseIntraTabaco}
                                    onChange={setBaseIntraTabaco}
                                />
                            </div>

                            {/* ISP */}
                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">
                                    Inversion del sujeto pasivo (Art. 84.uno.2.o LIVA)
                                </h2>
                                <NumberField
                                    id="isp21"
                                    label="Base tipo general (21%)"
                                    hint="Operaciones con ISP al tipo general."
                                    value={baseISP21}
                                    onChange={setBaseISP21}
                                />
                                <NumberField
                                    id="isp10"
                                    label="Base tipo reducido (10%)"
                                    hint="Operaciones con ISP al tipo reducido."
                                    value={baseISP10}
                                    onChange={setBaseISP10}
                                />
                                <NumberField
                                    id="isp4"
                                    label="Base tipo superreducido (4%)"
                                    hint="Operaciones con ISP al tipo superreducido."
                                    value={baseISP4}
                                    onChange={setBaseISP4}
                                />
                            </div>

                            {error && (
                                <div className="m130-alert">
                                    <AlertTriangle size={16} />
                                    <span>{error}</span>
                                </div>
                            )}

                            <button
                                type="submit"
                                className="m130-cta-btn"
                                style={{ width: '100%', justifyContent: 'center', border: 'none', marginTop: '1rem', cursor: loading ? 'wait' : 'pointer' }}
                                disabled={loading || !hasData}
                            >
                                {loading ? <Loader2 size={16} className="spin" /> : <Calculator size={16} />}
                                {loading ? 'Calculando...' : 'Calcular Modelo 309'}
                            </button>

                            {!hasData && (
                                <p className="m130-q1-note">
                                    Introduce al menos una base imponible para calcular.
                                </p>
                            )}

                            <div className="m130-disclaimer">
                                <Info size={14} />
                                <span>
                                    Esta calculadora es informativa. Presentacion oficial en{' '}
                                    <a className="m130-link" href="https://sede.agenciatributaria.gob.es" target="_blank" rel="noopener noreferrer">
                                        Sede Electronica AEAT
                                    </a>.
                                </span>
                            </div>
                        </form>
                    </section>

                    {hasResult && (
                        <section className="m130-result-panel" aria-live="polite">
                            <div className={`m130-result-card ${result.resultado === 0 ? 'm130-result-card--zero' : 'm130-result-card--pagar'}`}>
                                <div className="m130-result-label">
                                    <Euro size={18} /> A ingresar — IVA + RE
                                </div>
                                <div className="m130-result-amount">
                                    {formatEur(result.resultado)}
                                    <span className="m130-result-currency">EUR</span>
                                </div>
                                <div className="m130-result-sub">
                                    IVA: {formatEur(result.total_iva)} EUR
                                    {result.aplica_re && ` | RE: ${formatEur(result.total_re)} EUR`}
                                </div>
                                <div className="m130-result-deadline">
                                    <Calendar size={13} />
                                    Plazo: {result.plazo}
                                </div>
                            </div>

                            {result.desglose && Object.keys(result.desglose).length > 0 && (
                                <div className="m130-casillas-card">
                                    <h3 className="m130-casillas-title">Desglose por tipo</h3>
                                    <table className="m130-casillas-table">
                                        <thead>
                                            <tr>
                                                <th className="m130-th-label">Tipo</th>
                                                <th className="m130-th-value">IVA</th>
                                                {result.aplica_re && <th className="m130-th-value">RE</th>}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(result.desglose).map(([tipo, vals]: [string, any]) => (
                                                <tr key={tipo} className="m130-casilla-row">
                                                    <td className="m130-casilla-label">{tipo}</td>
                                                    <td className="m130-casilla-value">
                                                        {typeof vals?.cuota_iva === 'number' ? formatEur(vals.cuota_iva) + ' EUR' : '-'}
                                                    </td>
                                                    {result.aplica_re && (
                                                        <td className="m130-casilla-value">
                                                            {typeof vals?.cuota_re === 'number' ? formatEur(vals.cuota_re) + ' EUR' : '-'}
                                                        </td>
                                                    )}
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            <div className="m130-info-card m130-info-card--info">
                                <Info size={16} />
                                <div>
                                    <p>El Modelo 309 no tiene compensacion de periodos anteriores ni regimen de devolucion mensual.</p>
                                    <p style={{ marginTop: '0.5rem' }}>Presenta un modelo separado por cada hecho imponible no periodico que genere autoliquidacion.</p>
                                </div>
                            </div>

                            <div className="m130-cta-card">
                                <button
                                    className="m130-cta-btn"
                                    style={{ width: '100%', justifyContent: 'center', border: 'none', cursor: pdfLoading ? 'wait' : 'pointer' }}
                                    onClick={() => downloadPDF('309', { ...result }, trimestre, year)}
                                    disabled={pdfLoading}
                                >
                                    {pdfLoading ? <Loader2 size={16} className="spin" /> : <Download size={16} />}
                                    {pdfLoading ? 'Generando...' : 'Descargar PDF'}
                                </button>
                                {pdfError && <p className="m130-advanced-calc m130-advanced-calc--warn">{pdfError}</p>}
                            </div>
                        </section>
                    )}
                </div>
            </main>
        </div>
    )
}
