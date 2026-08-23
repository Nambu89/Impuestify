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
import { useM131, type M131Input, type M131Result } from '../hooks/useM131'
import { useModeloPDF } from '../hooks/useModeloPDF'
import { formatOptionalNumber, parseOptionalNumber, withOptionalField } from '../utils/numberField'
import './M130CalculatorPage.css'

const TERRITORIOS = [
    { value: 'comun', label: 'Régimen común' },
    { value: 'ceuta_melilla', label: 'Ceuta / Melilla' },
    { value: 'araba', label: 'Araba/Álava (foral)' },
    { value: 'bizkaia', label: 'Bizkaia (foral)' },
    { value: 'gipuzkoa', label: 'Gipuzkoa (foral)' },
    { value: 'navarra', label: 'Navarra (foral)' },
]

const APARTADOS = [
    { value: 'empresarial', label: 'Apartado I — Actividad empresarial (módulos)' },
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

/**
 * Fila del desglose, ya traducida a la numeracion OFICIAL del modelo.
 *
 * Las claves del dict que devuelve el backend (`09_retenciones_trimestre`,
 * `12_resultado_final`...) llevan un prefijo propio que NO es el numero de
 * casilla del Modelo 131. La equivalencia esta en el docstring de
 * `Modelo131Calculator` y sale del diseno de registro DR131_2026 de la AEAT.
 * `num` vacio = ese importe no tiene casilla numerada en el modelo.
 */
interface CasillaRow {
    num: string
    label: string
    value: number
    unit: 'EUR' | '%'
}

function buildCasillaRows(result: M131Result): CasillaRow[] {
    const c = result.casillas
    const d = result.desglose ?? {}
    const rows: CasillaRow[] = []

    if (result.apartado === 'I') {
        rows.push(
            {
                num: '01',
                label: 'Suma de rendimientos netos',
                value: c['01_rendimiento_neto_modulos'] ?? 0,
                unit: 'EUR',
            },
            {
                num: '',
                label: 'Porcentaje aplicable',
                value: c['02_tipo_aplicable'] ?? 0,
                unit: '%',
            },
            {
                num: '02',
                label: 'Pago fraccionado previo: suma de resultados',
                value: c['03_resultado_empresarial'] ?? 0,
                unit: 'EUR',
            },
        )
    } else if (result.apartado === 'III') {
        rows.push(
            {
                num: '05',
                label: 'Volumen de ingresos del trimestre',
                value: c['04_volumen_ingresos_agrario'] ?? 0,
                unit: 'EUR',
            },
            {
                num: '06',
                label: 'Pago fraccionado previo del trimestre (2%)',
                value: c['05_cuota_agraria'] ?? 0,
                unit: 'EUR',
            },
        )
    } else {
        rows.push(
            {
                num: '03',
                label: 'Volumen de ventas o ingresos',
                value: c['01_rendimiento_neto_modulos'] ?? 0,
                unit: 'EUR',
            },
            {
                num: '',
                label: 'Porcentaje aplicable',
                value: c['02_tipo_aplicable'] ?? 0,
                unit: '%',
            },
            {
                num: '04',
                label: 'Pago fraccionado previo',
                value: c['03_resultado_empresarial'] ?? 0,
                unit: 'EUR',
            },
        )
    }

    rows.push({
        num: '07',
        label: 'Suma de los pagos fraccionados previos del trimestre',
        value: c['06_total_cuotas'] ?? 0,
        unit: 'EUR',
    })

    // Las reducciones territoriales no tienen casilla propia: la AEAT las
    // incorpora al porcentaje aplicable de cada actividad.
    if ((c['07_reducciones'] ?? 0) > 0) {
        rows.push(
            {
                num: '',
                label: `Reducciones ${d.reduccion_concepto ?? 'territoriales'}`,
                value: c['07_reducciones'],
                unit: 'EUR',
            },
            {
                num: '',
                label: 'Resultado tras reducciones',
                value: c['08_resultado_tras_reducciones'] ?? 0,
                unit: 'EUR',
            },
        )
    }

    if ((c['09_retenciones_trimestre'] ?? 0) > 0) {
        rows.push({
            num: '08',
            label: 'A deducir: retenciones e ingresos a cuenta',
            value: c['09_retenciones_trimestre'],
            unit: 'EUR',
        })
    }

    const minoracion = Number(d.minoracion_rendimientos_bajos ?? 0)
    if (result.apartado === 'I' && minoracion > 0) {
        rows.push({
            num: '09',
            label: 'Minoración por aplicación de la deducción del art. 110.3.c) RIRPF',
            value: minoracion,
            unit: 'EUR',
        })
    }

    // `pagos_anteriores` no tiene casilla en el 131: el modelo no es
    // acumulativo, a diferencia del 130.
    if ((c['10_pagos_anteriores'] ?? 0) > 0) {
        rows.push({
            num: '',
            label: 'Pagos fraccionados de trimestres anteriores',
            value: c['10_pagos_anteriores'],
            unit: 'EUR',
        })
    }

    if ((c['11_complementaria'] ?? 0) > 0) {
        rows.push({
            num: '14',
            label: 'A deducir: resultado a ingresar de las anteriores declaraciones',
            value: c['11_complementaria'],
            unit: 'EUR',
        })
    }

    rows.push({
        num: '15',
        label: 'Resultado de la declaración',
        value: c['12_resultado_final'] ?? result.resultado_final,
        unit: 'EUR',
    })

    return rows
}

export default function M131CalculatorPage() {
    const [trimestre, setTrimestre] = useState(1)
    const [territorio, setTerritorio] = useState('comun')
    const [apartado, setApartado] = useState<M131Input['actividad_tipo']>('empresarial')
    const [rendimientoNeto, setRendimientoNeto] = useState(0)
    const [numAsalariados, setNumAsalariados] = useState(0)
    const [volumenIngresos, setVolumenIngresos] = useState(0)
    const [retenciones, setRetenciones] = useState(0)
    const [pagosAnteriores, setPagosAnteriores] = useState(0)
    // `undefined` NO es lo mismo que 0: son dos de los tres estados que el
    // backend distingue. Vacío = "no facilito el dato" (la clave se omite del
    // payload y no hay minoración); 0 = "gané 0 EUR" (sí da derecho a los
    // 100 EUR del primer tramo del art. 110.3.c RIRPF). El parseo va por
    // `parseOptionalNumber` justamente para no colapsarlos.
    const [rendAnterior, setRendAnterior] = useState<number | undefined>(undefined)

    const { result, loading, error, calculate } = useM131()
    const { downloadPDF, isLoading: pdfLoading, error: pdfError } = useModeloPDF()

    const trimestreInfo = TRIMESTRES.find((t) => t.value === trimestre)!
    const esCeutaMelilla = territorio === 'ceuta_melilla'

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault()
        const payload: M131Input = {
            trimestre,
            actividad_tipo: apartado,
            territorio,
            rendimiento_neto_modulos_anual: rendimientoNeto,
            num_asalariados: numAsalariados,
            volumen_ingresos_trimestre: volumenIngresos,
            retenciones_trimestre: retenciones,
            // En el 1T no hay trimestres anteriores. El control se deshabilita,
            // pero deshabilitar no vacia: sin este 0 un importe tecleado en el
            // 3T seguia restandose al volver al 1T.
            pagos_anteriores: trimestre === 1 ? 0 : pagosAnteriores,
            ceuta_melilla: esCeutaMelilla,
            la_palma: false,
            year: currentYear,
        }
        // Solo el apartado I aplica hoy la minoración de la casilla [09]. Si el
        // campo va vacío, `withOptionalField` BORRA la clave: no viaja como
        // `null` ni como 0.
        await calculate(
            withOptionalField(
                payload,
                'rendimiento_neto_anterior',
                apartado === 'empresarial' ? rendAnterior : undefined,
            ),
        )
    }

    return (
        <div className="m130-page">
            <Header />
            <main className="m130-main">
                <div className="m130-hero">
                    <div className="m130-hero-badge">
                        <Calculator size={14} />
                        <span>Estimación objetiva — Módulos</span>
                    </div>
                    <h1 className="m130-title">
                        Calculadora <span className="m130-title-highlight">Modelo 131</span>
                    </h1>
                    <p className="m130-subtitle">
                        Pago fraccionado de IRPF para autónomos en estimación objetiva (módulos).
                        Aplicable a los 4 trimestres del ejercicio.
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
                                    Fecha límite: <strong>{trimestreInfo.fechaLimite}</strong>
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
                                <h2 className="m130-fields-title">Datos del cálculo</h2>

                                {apartado === 'empresarial' && (
                                    <>
                                        <div className="m130-field">
                                            <label className="m130-label" htmlFor="rendimiento">
                                                Rendimiento neto de módulos anual (EUR)
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
                                                Rendimiento neto calculado por módulos para el
                                                conjunto del año.
                                            </p>
                                        </div>

                                        <div className="m130-field">
                                            <label className="m130-label" htmlFor="asalariados">
                                                Número de asalariados
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

                                        <div className="m130-field">
                                            <label className="m130-label" htmlFor="rend-anterior">
                                                Rendimiento neto del ejercicio anterior (EUR) —
                                                opcional
                                            </label>
                                            <div className="m130-input-row">
                                                <Euro size={16} className="m130-input-icon" />
                                                {/* `step="any"`: con un step de 100 el
                                                    navegador marca inválido cualquier
                                                    importe que no sea múltiplo y bloquea
                                                    el envío del formulario entero. Sin
                                                    `min`: un ejercicio anterior en
                                                    pérdidas es un dato válido y entra en
                                                    el primer tramo. */}
                                                <input
                                                    id="rend-anterior"
                                                    type="number"
                                                    className="m130-input"
                                                    step="any"
                                                    placeholder="Déjalo vacío si no lo facilitas"
                                                    value={formatOptionalNumber(rendAnterior)}
                                                    onChange={(e) =>
                                                        setRendAnterior(
                                                            parseOptionalNumber(e.target.value),
                                                        )
                                                    }
                                                />
                                                <span className="m130-input-suffix">EUR</span>
                                            </div>
                                            <p className="m130-field-hint">
                                                Es el dato de partida de la casilla [09], no la
                                                casilla en sí. Si el ejercicio anterior fue igual o
                                                inferior a 12.000 EUR, se resta una minoración de
                                                100, 75, 50 o 25 EUR por trimestre (art. 110.3.c)
                                                del Reglamento del IRPF).{' '}
                                                <strong>
                                                    Déjalo vacío si no facilitas el dato: sin él no
                                                    se aplica minoración alguna.
                                                </strong>{' '}
                                                Si de verdad ganaste 0 EUR, escribe un 0 — sí da
                                                derecho a los 100 EUR.
                                            </p>
                                            {rendAnterior === 0 && (
                                                <p className="m130-field-hint">
                                                    Has escrito un 0: se aplicará la minoración
                                                    máxima de 100 EUR en el trimestre.
                                                </p>
                                            )}
                                        </div>
                                    </>
                                )}

                                {apartado !== 'empresarial' && (
                                    <div className="m130-field">
                                        <label className="m130-label" htmlFor="volumen">
                                            {apartado === 'agraria'
                                                ? 'Volumen de ingresos del trimestre (EUR)'
                                                : 'Volumen de ventas o ingresos del trimestre (EUR)'}
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
                                            {apartado === 'agraria'
                                                ? 'Ingresos brutos de la actividad agraria del trimestre, sin contar las subvenciones de capital. Casilla [05].'
                                                : 'Ingresos brutos de la actividad del trimestre. Es la base del apartado II, casilla [03]: sin este dato el resultado sale a cero.'}
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
                                        Pagos fraccionados anteriores del año (EUR)
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
                                        Suma de modelos 131 presentados anteriormente este año.
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
                                {loading ? 'Calculando…' : 'Calcular Modelo 131'}
                            </button>

                            <div className="m130-disclaimer">
                                <Info size={14} />
                                <span>
                                    Esta calculadora es informativa. Presentación oficial en{' '}
                                    <a
                                        className="m130-link"
                                        href="https://sede.agenciatributaria.gob.es"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        Sede Electrónica de la AEAT
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
                                    {/* `tipo_aplicado` YA viene en porcentaje desde el
                                        backend (2.0 / 3.0 / 4.0): multiplicarlo por 100
                                        mostraba 200%, 300% y 400%. */}
                                    Apartado: {result.apartado} — Tipo:{' '}
                                    {result.tipo_aplicado.toFixed(0)}%
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
                                            {buildCasillaRows(result).map((row, i) => (
                                                <tr
                                                    key={`${row.num}-${i}`}
                                                    className="m130-casilla-row"
                                                >
                                                    <td className="m130-casilla-num">
                                                        {row.num || '—'}
                                                    </td>
                                                    <td className="m130-casilla-label">
                                                        {row.label}
                                                    </td>
                                                    <td className="m130-casilla-value">
                                                        {row.unit === '%'
                                                            ? `${row.value.toFixed(0)}%`
                                                            : `${formatEur(row.value)} EUR`}
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
                                            // El trimestre del CALCULO, no el que
                                            // este marcado ahora: cambiarlo sin
                                            // recalcular sacaba un PDF con las
                                            // casillas de un trimestre y la
                                            // cabecera de otro.
                                            String(result.trimestre) + 'T',
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
                                    {pdfLoading ? 'Generando…' : 'Descargar PDF'}
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
