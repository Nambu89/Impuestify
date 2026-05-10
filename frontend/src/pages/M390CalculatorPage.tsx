import { useState } from 'react'
import {
    Calculator,
    Info,
    AlertTriangle,
    CheckCircle2,
    Euro,
    Download,
    Loader2,
} from 'lucide-react'
import Header from '../components/Header'
import { useM390, type Trimestre303 } from '../hooks/useM390'
import { useModeloPDF } from '../hooks/useModeloPDF'
import './M130CalculatorPage.css'

const REGIMENES = [
    { value: 'general', label: 'Regimen general' },
    { value: 'simplificado', label: 'Simplificado (modulos)' },
    { value: 'recargo_equivalencia', label: 'Recargo de equivalencia' },
    { value: 'otro', label: 'Otro' },
]

const CCAA = [
    'Andalucia', 'Aragon', 'Asturias', 'Baleares', 'Canarias', 'Cantabria',
    'Castilla-La Mancha', 'Castilla y Leon', 'Cataluna', 'Extremadura',
    'Galicia', 'La Rioja', 'Madrid', 'Murcia', 'Navarra', 'Pais Vasco', 'Valencia',
    'Ceuta', 'Melilla',
]

function formatEur(v: number) {
    return v.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function emptyTrimestre(): Trimestre303 {
    return { casilla_27: 0, casilla_45: 0, resultado_liquidacion: 0 }
}

const currentYear = new Date().getFullYear()

export default function M390CalculatorPage() {
    const [year, setYear] = useState(currentYear - 1)
    const [ccaa, setCcaa] = useState('')
    const [volumen, setVolumen] = useState(0)
    const [enRedeme, setEnRedeme] = useState(false)
    const [enGrupoIva, setEnGrupoIva] = useState(false)
    const [siiVoluntario, setSiiVoluntario] = useState(false)
    const [regimen, setRegimen] = useState('general')
    const [incluirTrimestres, setIncluirTrimestres] = useState(false)
    const [trimestres, setTrimestres] = useState<Trimestre303[]>([emptyTrimestre(), emptyTrimestre(), emptyTrimestre(), emptyTrimestre()])

    const { result, loading, error, calculate } = useM390()
    const { downloadPDF, isLoading: pdfLoading, error: pdfError } = useModeloPDF()

    function updateTrimestre(index: number, field: keyof Trimestre303, value: number) {
        setTrimestres(prev => prev.map((t, i) => i === index ? { ...t, [field]: value } : t))
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        await calculate({
            year,
            ccaa: ccaa || undefined,
            volumen_operaciones_ano_anterior: volumen,
            en_redeme: enRedeme,
            en_grupo_iva: enGrupoIva,
            sii_voluntario: siiVoluntario,
            regimen_especial: regimen,
            trimestres_303: incluirTrimestres ? trimestres : undefined,
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
                        <span>Resumen anual IVA</span>
                    </div>
                    <h1 className="m130-title">
                        Calculadora <span className="m130-title-highlight">Modelo 390</span>
                    </h1>
                    <p className="m130-subtitle">
                        Declaracion resumen anual del IVA. Se presenta en enero del ano siguiente
                        junto con el cuarto trimestre del Modelo 303.
                    </p>
                </div>

                <div className={`m130-layout ${hasResult ? 'm130-layout--split' : ''}`}>
                    <section className="m130-inputs-panel">
                        <form onSubmit={handleSubmit}>
                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">Datos del ejercicio</h2>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="year">Ejercicio declarado</label>
                                    <input
                                        id="year"
                                        type="number"
                                        className="m130-input"
                                        min={2020}
                                        max={2030}
                                        value={year}
                                        onChange={e => setYear(parseInt(e.target.value) || currentYear - 1)}
                                    />
                                    <p className="m130-field-hint">El M390 de 2025 se presenta en enero de 2026.</p>
                                </div>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="ccaa">Comunidad Autonoma</label>
                                    <select
                                        id="ccaa"
                                        className="m130-input"
                                        value={ccaa}
                                        onChange={e => setCcaa(e.target.value)}
                                    >
                                        <option value="">-- Selecciona CCAA --</option>
                                        {CCAA.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="volumen">
                                        Volumen de operaciones del ano anterior (EUR)
                                    </label>
                                    <div className="m130-input-row">
                                        <Euro size={16} className="m130-input-icon" />
                                        <input
                                            id="volumen"
                                            type="number"
                                            className="m130-input"
                                            min={0}
                                            step={1000}
                                            placeholder="0"
                                            value={volumen || ''}
                                            onChange={e => setVolumen(parseFloat(e.target.value) || 0)}
                                        />
                                        <span className="m130-input-suffix">EUR</span>
                                    </div>
                                    <p className="m130-field-hint">Determina la periodicidad obligatoria del 303 del ejercicio siguiente.</p>
                                </div>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="regimen">Regimen de IVA</label>
                                    <select
                                        id="regimen"
                                        className="m130-input"
                                        value={regimen}
                                        onChange={e => setRegimen(e.target.value)}
                                    >
                                        {REGIMENES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">Regimenes especiales</h2>
                                <div className="m130-ceuta-row">
                                    <label className="m130-toggle-label" htmlFor="redeme">
                                        <input id="redeme" type="checkbox" className="m130-toggle-input" checked={enRedeme} onChange={e => setEnRedeme(e.target.checked)} />
                                        <span className="m130-toggle-track" />
                                        <span className="m130-toggle-text">Inscrito en REDEME (devolucion mensual)</span>
                                    </label>
                                </div>
                                <div className="m130-ceuta-row">
                                    <label className="m130-toggle-label" htmlFor="grupo">
                                        <input id="grupo" type="checkbox" className="m130-toggle-input" checked={enGrupoIva} onChange={e => setEnGrupoIva(e.target.checked)} />
                                        <span className="m130-toggle-track" />
                                        <span className="m130-toggle-text">Grupo de IVA (Art. 163 quinquies LIVA)</span>
                                    </label>
                                </div>
                                <div className="m130-ceuta-row">
                                    <label className="m130-toggle-label" htmlFor="sii">
                                        <input id="sii" type="checkbox" className="m130-toggle-input" checked={siiVoluntario} onChange={e => setSiiVoluntario(e.target.checked)} />
                                        <span className="m130-toggle-track" />
                                        <span className="m130-toggle-text">SII voluntario (Suministro Inmediato de Informacion)</span>
                                    </label>
                                </div>
                            </div>

                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">Datos de los 4 trimestres (opcional)</h2>
                                <div className="m130-ceuta-row">
                                    <label className="m130-toggle-label" htmlFor="incluirT">
                                        <input id="incluirT" type="checkbox" className="m130-toggle-input" checked={incluirTrimestres} onChange={e => setIncluirTrimestres(e.target.checked)} />
                                        <span className="m130-toggle-track" />
                                        <span className="m130-toggle-text">Incluir resumen de los 4 trimestres</span>
                                    </label>
                                </div>

                                {incluirTrimestres && trimestres.map((t, i) => (
                                    <div key={i} style={{ borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '0.75rem', marginTop: '0.75rem' }}>
                                        <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                                            Trimestre {i + 1}T
                                        </p>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                                            <div>
                                                <label className="m130-label" style={{ fontSize: '0.75rem' }}>IVA devengado (c.27)</label>
                                                <input type="number" className="m130-input" min={0} step={0.01} placeholder="0" value={t.casilla_27 || ''} onChange={e => updateTrimestre(i, 'casilla_27', parseFloat(e.target.value) || 0)} />
                                            </div>
                                            <div>
                                                <label className="m130-label" style={{ fontSize: '0.75rem' }}>IVA deducible (c.45)</label>
                                                <input type="number" className="m130-input" min={0} step={0.01} placeholder="0" value={t.casilla_45 || ''} onChange={e => updateTrimestre(i, 'casilla_45', parseFloat(e.target.value) || 0)} />
                                            </div>
                                            <div>
                                                <label className="m130-label" style={{ fontSize: '0.75rem' }}>Resultado</label>
                                                <input type="number" className="m130-input" step={0.01} placeholder="0" value={t.resultado_liquidacion || ''} onChange={e => updateTrimestre(i, 'resultado_liquidacion', parseFloat(e.target.value) || 0)} />
                                            </div>
                                        </div>
                                    </div>
                                ))}
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
                                disabled={loading}
                            >
                                {loading ? <Loader2 size={16} className="spin" /> : <Calculator size={16} />}
                                {loading ? 'Calculando...' : 'Verificar Modelo 390'}
                            </button>

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
                            <div className={`m130-result-card ${result.obligado ? 'm130-result-card--pagar' : 'm130-result-card--zero'}`}>
                                <div className="m130-result-label">
                                    {result.obligado
                                        ? <><AlertTriangle size={18} /> Obligado a presentar</>
                                        : <><CheckCircle2 size={18} /> Exonerado de presentar</>
                                    }
                                </div>
                                {result.modelo && (
                                    <div className="m130-result-amount" style={{ fontSize: '1.5rem' }}>
                                        {result.modelo}
                                    </div>
                                )}
                                {result.motivo_exoneracion && (
                                    <div className="m130-result-sub">{result.motivo_exoneracion}</div>
                                )}
                                {result.variante_territorial && (
                                    <div className="m130-result-sub">Variante: {result.variante_territorial}</div>
                                )}
                            </div>

                            {result.resumen_anual && Object.keys(result.resumen_anual).length > 0 && (
                                <div className="m130-casillas-card">
                                    <h3 className="m130-casillas-title">Resumen anual</h3>
                                    <table className="m130-casillas-table">
                                        <thead>
                                            <tr>
                                                <th className="m130-th-label">Concepto</th>
                                                <th className="m130-th-value">Importe</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(result.resumen_anual).map(([k, v]) => (
                                                <tr key={k} className="m130-casilla-row">
                                                    <td className="m130-casilla-label">{k}</td>
                                                    <td className="m130-casilla-value">{typeof v === 'number' ? formatEur(v) + ' EUR' : String(v)}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            <div className="m130-info-card m130-info-card--info">
                                <Info size={16} />
                                <p>Plazo: <strong>{result.plazo}</strong></p>
                            </div>

                            <div className="m130-cta-card">
                                <button
                                    className="m130-cta-btn"
                                    style={{ width: '100%', justifyContent: 'center', border: 'none', cursor: pdfLoading ? 'wait' : 'pointer' }}
                                    onClick={() => downloadPDF('390', { ...result }, '0A', year)}
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
