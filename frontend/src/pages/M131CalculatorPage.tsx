import { useState } from 'react'
import {
    Calculator,
    Info,
    AlertTriangle,
    CheckCircle2,
    Euro,
    Calendar,
    Download,
    Loader2,
} from 'lucide-react'
import Header from '../components/Header'
import { useM131, type M131Input } from '../hooks/useM131'
import { useModeloPDF } from '../hooks/useModeloPDF'
import './M130CalculatorPage.css'

const TERRITORIOS = [
    { value: 'comun', label: 'Regimen Comun' },
    { value: 'ceuta_melilla', label: 'Ceuta / Melilla' },
    { value: 'araba', label: 'Araba (foral)' },
    { value: 'bizkaia', label: 'Bizkaia (foral)' },
    { value: 'gipuzkoa', label: 'Gipuzkoa (foral)' },
    { value: 'navarra', label: 'Navarra (foral)' },
]

const APARTADOS = [
    { value: 'empresarial', label: 'Apartado I — Actividad empresarial (modulos)' },
    { value: 'sin_datos_base', label: 'Apartado II — Sin datos para calcular la base' },
    { value: 'agraria', label: 'Apartado III — Actividad agraria' },
]

const TRIMESTRES = [
    { value: 1, label: '1T', periodo: 'Ene – Mar', fechaLimite: '20 de abril de 2026' },
    { value: 2, label: '2T', periodo: 'Abr – Jun', fechaLimite: '20 de julio de 2026' },
    { value: 3, label: '3T', periodo: 'Jul – Sep', fechaLimite: '20 de octubre de 2026' },
    { value: 4, label: '4T', periodo: 'Oct – Dic', fechaLimite: '30 de enero de 2027' },
]

function formatEur(v: number) {
    return v.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const currentYear = new Date().getFullYear()

export default function M131CalculatorPage() {
    const [trimestre, setTrimestre] = useState(1)
    const [territorio, setTerritorio] = useState('comun')
    const [apartado, setApartado] = useState<M131Input['actividad_tipo']>('empresarial')
    const [rendimientoNeto, setRendimientoNeto] = useState(0)
    const [numAsalariados, setNumAsalariados] = useState(0)
    const [volumenIngresos, setVolumenIngresos] = useState(0)
    const [retenciones, setRetenciones] = useState(0)
    const [pagosAnteriores, setPagosAnteriores] = useState(0)

    const { result, loading, error, calculate } = useM131()
    const { downloadPDF, isLoading: pdfLoading, error: pdfError } = useModeloPDF()

    const trimestreInfo = TRIMESTRES.find((t) => t.value === trimestre)!
    const esCeutaMelilla = territorio === 'ceuta_melilla'

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        await calculate({
            trimestre,
            actividad_tipo: apartado,
            territorio,
            rendimiento_neto_modulos_anual: rendimientoNeto,
            num_asalariados: numAsalariados,
            volumen_ingresos_trimestre: volumenIngresos,
            // Esta pantalla aun no pide el rendimiento del ejercicio anterior:
            // se envia null (dato no facilitado). Enviar 0 activaria la
            // minoracion del art. 110.3.c RIRPF para todo el mundo.
            rendimiento_neto_anterior: null,
            retenciones_trimestre: retenciones,
            pagos_anteriores: pagosAnteriores,
            ceuta_melilla: esCeutaMelilla,
            la_palma: false,
            year: currentYear,
        })
    }

    return (
        <div className="m130-page">
            <Header />
            <main className="m130-main">
                <div className="m130-hero">
                    <div className="m130-hero-badge">
                        <Calculator size={14} />
                        <span>Estimacion objetiva — Modulos</span>
                    </div>
                    <h1 className="m130-title">
                        Calculadora <span className="m130-title-highlight">Modelo 131</span>
                    </h1>
                    <p className="m130-subtitle">
                        Pago fraccionado de IRPF para autonomos en estimacion objetiva (modulos).
                        Applicable a los 4 trimestres del ejercicio.
                    </p>
                </div>

                <div className={`m130-layout ${result ? 'm130-layout--split' : ''}`}>
                    <section className="m130-inputs-panel">
                        <form onSubmit={handleSubmit}>
                            {/* Trimestre */}
                            <div className="m130-trim-card">
                                <p className="m130-trim-label">
                                    <Calendar size={14} />
                                    Trimestre que presentas
                                </p>
                                <div className="m130-trim-buttons">
                                    {TRIMESTRES.map((t) => (
                                        <button
                                            type="button"
                                            key={t.value}
                                            className={`m130-trim-btn ${trimestre === t.value ? 'm130-trim-btn--active' : ''}`}
                                            onClick={() => setTrimestre(t.value)}
                                        >
                                            <span className="m130-trim-btn-label">{t.label}</span>
                                            <span className="m130-trim-btn-periodo">
                                                {t.periodo}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                                <p className="m130-trim-deadline">
                                    <Calendar size={12} />
                                    Fecha limite: <strong>{trimestreInfo.fechaLimite}</strong>
                                </p>
                            </div>

                            {/* Territorio */}
                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">
                                    Territorio y tipo de actividad
                                </h2>
                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="territorio">
                                        Territorio fiscal
                                    </label>
                                    <select
                                        id="territorio"
                                        className="m130-input"
                                        value={territorio}
                                        onChange={(e) => setTerritorio(e.target.value)}
                                    >
                                        {TERRITORIOS.map((t) => (
                                            <option key={t.value} value={t.value}>
                                                {t.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="apartado">
                                        Apartado
                                    </label>
                                    <select
                                        id="apartado"
                                        className="m130-input"
                                        value={apartado}
                                        onChange={(e) =>
                                            setApartado(
                                                e.target.value as M131Input['actividad_tipo'],
                                            )
                                        }
                                    >
                                        {APARTADOS.map((a) => (
                                            <option key={a.value} value={a.value}>
                                                {a.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            {/* Datos principales */}
                            <div className="m130-fields-card">
                                <h2 className="m130-fields-title">Datos del calculo</h2>

                                {apartado === 'empresarial' && (
                                    <>
                                        <div className="m130-field">
                                            <label className="m130-label" htmlFor="rendimiento">
                                                Rendimiento neto de modulos anual (EUR)
                                            </label>
                                            <div className="m130-input-row">
                                                <Euro size={16} className="m130-input-icon" />
                                                <input
                                                    id="rendimiento"
                                                    type="number"
                                                    className="m130-input"
                                                    min={0}
                                                    step={100}
                                                    placeholder="0"
                                                    value={rendimientoNeto || ''}
                                                    onChange={(e) =>
                                                        setRendimientoNeto(
                                                            parseFloat(e.target.value) || 0,
                                                        )
                                                    }
                                                />
                                                <span className="m130-input-suffix">EUR</span>
                                            </div>
                                            <p className="m130-field-hint">
                                                Rendimiento neto calculado por modulos para el
                                                conjunto del ano.
                                            </p>
                                        </div>

                                        <div className="m130-field">
                                            <label className="m130-label" htmlFor="asalariados">
                                                Numero de asalariados
                                            </label>
                                            <input
                                                id="asalariados"
                                                type="number"
                                                className="m130-input"
                                                min={0}
                                                step={1}
                                                placeholder="0"
                                                value={numAsalariados || ''}
                                                onChange={(e) =>
                                                    setNumAsalariados(parseInt(e.target.value) || 0)
                                                }
                                            />
                                            <p className="m130-field-hint">
                                                Afecta al porcentaje a ingresar (2%, 3% o 4%).
                                            </p>
                                        </div>
                                    </>
                                )}

                                {apartado === 'agraria' && (
                                    <div className="m130-field">
                                        <label className="m130-label" htmlFor="volumen">
                                            Volumen de ingresos del trimestre (EUR)
                                        </label>
                                        <div className="m130-input-row">
                                            <Euro size={16} className="m130-input-icon" />
                                            <input
                                                id="volumen"
                                                type="number"
                                                className="m130-input"
                                                min={0}
                                                step={100}
                                                placeholder="0"
                                                value={volumenIngresos || ''}
                                                onChange={(e) =>
                                                    setVolumenIngresos(
                                                        parseFloat(e.target.value) || 0,
                                                    )
                                                }
                                            />
                                            <span className="m130-input-suffix">EUR</span>
                                        </div>
                                        <p className="m130-field-hint">
                                            Ingresos brutos de la actividad agraria del trimestre.
                                        </p>
                                    </div>
                                )}

                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="retenciones">
                                        Retenciones soportadas del trimestre (EUR)
                                    </label>
                                    <div className="m130-input-row">
                                        <Euro size={16} className="m130-input-icon" />
                                        <input
                                            id="retenciones"
                                            type="number"
                                            className="m130-input"
                                            min={0}
                                            step={10}
                                            placeholder="0"
                                            value={retenciones || ''}
                                            onChange={(e) =>
                                                setRetenciones(parseFloat(e.target.value) || 0)
                                            }
                                        />
                                        <span className="m130-input-suffix">EUR</span>
                                    </div>
                                    <p className="m130-field-hint">
                                        Retenciones de IRPF practicadas por clientes en facturas de
                                        este trimestre.
                                    </p>
                                </div>

                                <div className="m130-field">
                                    <label className="m130-label" htmlFor="pagos">
                                        Pagos fraccionados anteriores del ano (EUR)
                                    </label>
                                    <div className="m130-input-row">
                                        <Euro size={16} className="m130-input-icon" />
                                        <input
                                            id="pagos"
                                            type="number"
                                            className="m130-input"
                                            min={0}
                                            step={10}
                                            placeholder="0"
                                            disabled={trimestre === 1}
                                            value={pagosAnteriores || ''}
                                            onChange={(e) =>
                                                setPagosAnteriores(parseFloat(e.target.value) || 0)
                                            }
                                        />
                                        <span className="m130-input-suffix">EUR</span>
                                    </div>
                                    <p className="m130-field-hint">
                                        Suma de M131 presentados anteriormente este ano.
                                    </p>
                                </div>
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
                                style={{
                                    width: '100%',
                                    justifyContent: 'center',
                                    border: 'none',
                                    marginTop: '1rem',
                                    cursor: loading ? 'wait' : 'pointer',
                                }}
                                disabled={loading}
                            >
                                {loading ? (
                                    <Loader2 size={16} className="spin" />
                                ) : (
                                    <Calculator size={16} />
                                )}
                                {loading ? 'Calculando...' : 'Calcular Modelo 131'}
                            </button>

                            <div className="m130-disclaimer">
                                <Info size={14} />
                                <span>
                                    Esta calculadora es informativa. Presentacion oficial en{' '}
                                    <a
                                        className="m130-link"
                                        href="https://sede.agenciatributaria.gob.es"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        Sede Electronica AEAT
                                    </a>
                                    .
                                </span>
                            </div>
                        </form>
                    </section>

                    {result && result.success && (
                        <section className="m130-result-panel" aria-live="polite">
                            <div
                                className={`m130-result-card ${result.resultado_final === 0 ? 'm130-result-card--zero' : 'm130-result-card--pagar'}`}
                            >
                                <div className="m130-result-label">
                                    {result.resultado_final === 0 ? (
                                        <>
                                            <CheckCircle2 size={18} /> Resultado cero
                                        </>
                                    ) : (
                                        <>
                                            <Euro size={18} /> A ingresar en Hacienda
                                        </>
                                    )}
                                </div>
                                <div className="m130-result-amount">
                                    {formatEur(result.resultado_final)}
                                    <span className="m130-result-currency">EUR</span>
                                </div>
                                <div className="m130-result-sub">
                                    Apartado: {result.apartado} — Tipo:{' '}
                                    {(result.tipo_aplicado * 100).toFixed(0)}%
                                </div>
                                <div className="m130-result-deadline">
                                    <Calendar size={13} />
                                    Plazo: {result.plazo}
                                </div>
                            </div>

                            {Object.keys(result.casillas).length > 0 && (
                                <div className="m130-casillas-card">
                                    <h3 className="m130-casillas-title">Desglose por casillas</h3>
                                    <table className="m130-casillas-table">
                                        <thead>
                                            <tr>
                                                <th className="m130-th-num">Cas.</th>
                                                <th className="m130-th-label">Concepto</th>
                                                <th className="m130-th-value">Importe</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Object.entries(result.casillas).map(([cas, val]) => (
                                                <tr key={cas} className="m130-casilla-row">
                                                    <td className="m130-casilla-num">{cas}</td>
                                                    <td className="m130-casilla-label">{cas}</td>
                                                    <td className="m130-casilla-value">
                                                        {formatEur(val as number)} EUR
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}

                            <div className="m130-cta-card">
                                <button
                                    className="m130-cta-btn"
                                    style={{
                                        width: '100%',
                                        justifyContent: 'center',
                                        border: 'none',
                                        cursor: pdfLoading ? 'wait' : 'pointer',
                                    }}
                                    onClick={() =>
                                        downloadPDF(
                                            '131',
                                            { ...result },
                                            String(trimestre) + 'T',
                                            currentYear,
                                        )
                                    }
                                    disabled={pdfLoading}
                                >
                                    {pdfLoading ? (
                                        <Loader2 size={16} className="spin" />
                                    ) : (
                                        <Download size={16} />
                                    )}
                                    {pdfLoading ? 'Generando...' : 'Descargar PDF'}
                                </button>
                                {pdfError && (
                                    <p className="m130-advanced-calc m130-advanced-calc--warn">
                                        {pdfError}
                                    </p>
                                )}
                            </div>
                        </section>
                    )}
                </div>
            </main>
        </div>
    )
}
