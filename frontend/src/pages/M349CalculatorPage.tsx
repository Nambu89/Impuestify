import { useState } from 'react'
import {
    Calculator,
    Info,
    AlertTriangle,
    Euro,
    Download,
    Loader2,
    Plus,
    Trash2,
} from 'lucide-react'
import Header from '../components/Header'
import { useM349, type Operacion349 } from '../hooks/useM349'
import { useModeloPDF } from '../hooks/useModeloPDF'
import './M130CalculatorPage.css'

const CLAVES = [
    { value: 'E', label: 'E — Entregas' },
    { value: 'A', label: 'A — Adquisiciones' },
    { value: 'T', label: 'T — Triangulares' },
    { value: 'S', label: 'S — Servicios prestados' },
    { value: 'I', label: 'I — Servicios adquiridos' },
    { value: 'M', label: 'M — Entregas con instalacion' },
    { value: 'H', label: 'H — Entregas en consigna' },
    { value: 'R', label: 'R — Rectificaciones' },
    { value: 'N', label: 'N — Rectificaciones sin identificacion de periodo' },
    { value: 'D', label: 'D — Devolucion exportacion por viajeros' },
    { value: 'C', label: 'C — Devoluciones de IVA a no establecidos' },
]

const PERIODOS = [
    { value: '1T', label: '1T — Primer trimestre' },
    { value: '2T', label: '2T — Segundo trimestre' },
    { value: '3T', label: '3T — Tercer trimestre' },
    { value: '4T', label: '4T — Cuarto trimestre' },
    { value: '01', label: 'Enero' },
    { value: '02', label: 'Febrero' },
    { value: '03', label: 'Marzo' },
    { value: '04', label: 'Abril' },
    { value: '05', label: 'Mayo' },
    { value: '06', label: 'Junio' },
    { value: '07', label: 'Julio' },
    { value: '08', label: 'Agosto' },
    { value: '09', label: 'Septiembre' },
    { value: '10', label: 'Octubre' },
    { value: '11', label: 'Noviembre' },
    { value: '12', label: 'Diciembre' },
    { value: '0A', label: '0A — Resumen anual' },
]

function formatEur(v: number) {
    return v.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const currentYear = new Date().getFullYear()

function emptyOp(): Operacion349 {
    return { nif_operador: '', nombre: '', clave: 'E', importe: 0 }
}

export default function M349CalculatorPage() {
    const [periodo, setPeriodo] = useState('1T')
    const [year, setYear] = useState(currentYear)
    const [operaciones, setOperaciones] = useState<Operacion349[]>([emptyOp()])

    const { result, loading, error, calculate } = useM349()
    const { downloadPDF, isLoading: pdfLoading, error: pdfError } = useModeloPDF()

    function updateOp(index: number, field: keyof Operacion349, value: string | number) {
        setOperaciones(prev => prev.map((op, i) => i === index ? { ...op, [field]: value } : op))
    }

    function addOp() {
        setOperaciones(prev => [...prev, emptyOp()])
    }

    function removeOp(index: number) {
        setOperaciones(prev => prev.filter((_, i) => i !== index))
    }

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        const ops = operaciones.filter(op => op.nif_operador.trim() && op.importe > 0)
        if (ops.length === 0) return
        await calculate({ operaciones: ops, periodo, year, forzar_anual: false, validar_vies: false })
    }

    const hasResult = result && result.success

    return (
        <div className="m130-page">
            <Header />
            <main className="m130-main">
                <div className="m130-hero">
                    <div className="m130-hero-badge">
                        <Calculator size={14} />
                        <span>Operaciones intracomunitarias</span>
                    </div>
                    <h1 className="m130-title">
                        Calculadora <span className="m130-title-highlight">Modelo 349</span>
                    </h1>
                    <p className="m130-subtitle">
                        Declaracion recapitulativa de operaciones intracomunitarias.
                        Mensual, trimestral o anual segun volumen.
                    </p>
                </div>

                <div className={`m130-layout ${hasResult ? 'm130-layout--split' : ''}`}>
                    <section className="m130-inputs-panel">
                        <form onSubmit={handleSubmit}>
                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">Periodo y ejercicio</h2>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="periodo">Periodo</label>
                                    <select
                                        id="periodo"
                                        className="m130-input"
                                        value={periodo}
                                        onChange={e => setPeriodo(e.target.value)}
                                    >
                                        {PERIODOS.map(p => (
                                            <option key={p.value} value={p.value}>{p.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="year">Ejercicio</label>
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
                            </div>

                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">Operaciones intracomunitarias</h2>
                                <p className="m130-field-hint" style={{ marginBottom: '1rem' }}>
                                    Introduce una linea por cada operador comunitario con el que hayas operado en el periodo.
                                </p>

                                {operaciones.map((op, i) => (
                                    <div key={i} style={{ borderTop: i > 0 ? '1px solid rgba(255,255,255,0.08)' : 'none', paddingTop: i > 0 ? '1rem' : 0, marginBottom: '1rem' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                            <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.8rem' }}>Operador {i + 1}</span>
                                            {operaciones.length > 1 && (
                                                <button type="button" onClick={() => removeOp(i)} style={{ background: 'none', border: 'none', color: 'rgba(239,68,68,0.8)', cursor: 'pointer', padding: '0.25rem' }}>
                                                    <Trash2 size={14} />
                                                </button>
                                            )}
                                        </div>
                                        <div className="m130-field">
                                            <label className="m130-label" htmlFor={`nif-${i}`}>NIF-IVA del operador</label>
                                            <input
                                                id={`nif-${i}`}
                                                type="text"
                                                className="m130-input"
                                                placeholder="IE6388047V"
                                                value={op.nif_operador}
                                                onChange={e => updateOp(i, 'nif_operador', e.target.value)}
                                            />
                                        </div>
                                        <div className="m130-field">
                                            <label className="m130-label" htmlFor={`nombre-${i}`}>Razon social</label>
                                            <input
                                                id={`nombre-${i}`}
                                                type="text"
                                                className="m130-input"
                                                placeholder="Nombre del operador (opcional)"
                                                value={op.nombre}
                                                onChange={e => updateOp(i, 'nombre', e.target.value)}
                                            />
                                        </div>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                                            <div className="m130-field">
                                                <label className="m130-label" htmlFor={`clave-${i}`}>Clave</label>
                                                <select
                                                    id={`clave-${i}`}
                                                    className="m130-input"
                                                    value={op.clave}
                                                    onChange={e => updateOp(i, 'clave', e.target.value)}
                                                >
                                                    {CLAVES.map(c => (
                                                        <option key={c.value} value={c.value}>{c.value} — {c.label.split(' — ')[1]}</option>
                                                    ))}
                                                </select>
                                            </div>
                                            <div className="m130-field">
                                                <label className="m130-label" htmlFor={`importe-${i}`}>Importe (EUR)</label>
                                                <div className="m130-input-row">
                                                    <Euro size={14} className="m130-input-icon" />
                                                    <input
                                                        id={`importe-${i}`}
                                                        type="number"
                                                        className="m130-input"
                                                        min={0}
                                                        step={0.01}
                                                        placeholder="0"
                                                        value={op.importe || ''}
                                                        onChange={e => updateOp(i, 'importe', parseFloat(e.target.value) || 0)}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                <button
                                    type="button"
                                    onClick={addOp}
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: '0.4rem',
                                        background: 'rgba(26,86,219,0.12)', border: '1px dashed rgba(26,86,219,0.4)',
                                        borderRadius: '8px', color: 'var(--color-primary-light)',
                                        padding: '0.5rem 1rem', cursor: 'pointer', fontSize: '0.85rem',
                                        width: '100%', justifyContent: 'center', marginTop: '0.5rem',
                                    }}
                                >
                                    <Plus size={14} />
                                    Anadir operador
                                </button>
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
                                {loading ? 'Calculando...' : 'Calcular Modelo 349'}
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
                            <div className="m130-result-card m130-result-card--pagar">
                                <div className="m130-result-label">
                                    <Euro size={18} /> Total declarado
                                </div>
                                <div className="m130-result-amount">
                                    {formatEur(result.total_general)}
                                    <span className="m130-result-currency">EUR</span>
                                </div>
                                <div className="m130-result-sub">
                                    {result.operadores_unicos} operador{result.operadores_unicos !== 1 ? 'es' : ''} — {result.periodicidad}
                                </div>
                            </div>

                            {Object.keys(result.total_por_clave).length > 0 && (
                                <div className="m130-casillas-card">
                                    <h3 className="m130-casillas-title">Total por clave</h3>
                                    <table className="m130-casillas-table">
                                        <thead>
                                            <tr>
                                                <th className="m130-th-num">Clave</th>
                                                <th className="m130-th-label">Descripcion</th>
                                                <th className="m130-th-value">Importe</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(result.total_por_clave).map(([clave, total]) => (
                                                <tr key={clave} className="m130-casilla-row">
                                                    <td className="m130-casilla-num">{clave}</td>
                                                    <td className="m130-casilla-label">{CLAVES.find(c => c.value === clave)?.label.split(' — ')[1] || clave}</td>
                                                    <td className="m130-casilla-value">{formatEur(total)} EUR</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            {result.avisos.length > 0 && (
                                <div className="m130-alert">
                                    <AlertTriangle size={16} />
                                    <ul style={{ margin: 0, paddingLeft: '1.2rem' }}>
                                        {result.avisos.map((a, i) => <li key={i}>{a}</li>)}
                                    </ul>
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
                                    onClick={() => downloadPDF('349', { ...result }, periodo, year)}
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
