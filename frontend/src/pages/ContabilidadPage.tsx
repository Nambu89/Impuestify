import { useState, useEffect, useRef } from 'react'
import { BookOpen, Download, ChevronDown, Loader2, TrendingUp, TrendingDown, Scale } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import './ContabilidadPage.css'

// ─── Types ────────────────────────────────────────────────────────────────────

interface DiarioEntry {
    fecha: string
    n_asiento: number
    cuenta: string
    nombre_cuenta: string
    debe: number
    haber: number
    concepto: string
}

interface MayorAccount {
    cuenta: string
    nombre: string
    total_debe: number
    total_haber: number
    saldo: number
}

interface BalanceAccount {
    cuenta: string
    nombre: string
    total_debe: number
    total_haber: number
    saldo: number
}

interface BalanceData {
    accounts: BalanceAccount[]
    total_debe: number
    total_haber: number
    diferencia: number
}

interface PYGItem {
    cuenta: string
    nombre: string
    importe: number
}

interface PYGData {
    ingresos: PYGItem[]
    gastos: PYGItem[]
    total_ingresos: number
    total_gastos: number
    resultado: number
}

type TabKey = 'diario' | 'mayor' | 'balance' | 'pyg'
type ExportFormat = 'csv' | 'excel'
type ExportLib = 'diario' | 'mayor' | 'balance' | 'pyg'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatEUR(n: number) {
    return n.toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

function formatDate(dateStr: string) {
    if (!dateStr) return '—'
    try {
        return new Date(dateStr).toLocaleDateString('es-ES')
    } catch {
        return dateStr
    }
}

// ─── Year / Quarter selectors ─────────────────────────────────────────────────

function YearSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    const current = new Date().getFullYear()
    const years = [current, current - 1, current - 2, current - 3].map(String)
    return (
        <select
            className="cont-select"
            value={value}
            onChange={e => onChange(e.target.value)}
            aria-label="Año"
        >
            {years.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
    )
}

function QuarterSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
    return (
        <select
            className="cont-select"
            value={value}
            onChange={e => onChange(e.target.value)}
            aria-label="Trimestre"
        >
            <option value="todos">Todos los trimestres</option>
            <option value="1">1T (ene–mar)</option>
            <option value="2">2T (abr–jun)</option>
            <option value="3">3T (jul–sep)</option>
            <option value="4">4T (oct–dic)</option>
        </select>
    )
}

// ─── Export button with dropdown ──────────────────────────────────────────────

function ExportButton({ lib, year, trimestre }: { lib: ExportLib; year: string; trimestre?: string }) {
    const [open, setOpen] = useState(false)
    const ref = useRef<HTMLDivElement>(null)
    const { apiRequest } = useApi()

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    async function handleExport(format: ExportFormat) {
        setOpen(false)
        try {
            const token = localStorage.getItem('access_token') || ''
            const apiBase = import.meta.env.VITE_API_URL || ''
            const qs = new URLSearchParams({ year, format })
            if (trimestre && trimestre !== 'todos') qs.set('trimestre', trimestre)
            const url = `${apiBase}/api/contabilidad/export/${lib}?${qs}`
            const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
            if (!res.ok) throw new Error('Error al exportar')
            const blob = await res.blob()
            const href = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = href
            a.download = `${lib}_${year}.${format === 'excel' ? 'xlsx' : 'csv'}`
            a.click()
            URL.revokeObjectURL(href)
        } catch {
            alert('No se pudo exportar el archivo. Inténtalo de nuevo.')
        }
    }

    return (
        <div className="cont-export" ref={ref}>
            <button
                className="cont-export__btn"
                onClick={() => setOpen(v => !v)}
                aria-expanded={open}
                aria-haspopup="true"
            >
                <Download size={15} />
                <span className="cont-export__label">Exportar</span>
                <ChevronDown size={13} className={open ? 'cont-export__chevron--up' : ''} />
            </button>
            {open && (
                <div className="cont-export__menu" role="menu">
                    <button className="cont-export__item" onClick={() => handleExport('csv')}>
                        Exportar CSV
                    </button>
                    <button className="cont-export__item" onClick={() => handleExport('excel')}>
                        Exportar Excel
                    </button>
                </div>
            )}
        </div>
    )
}

// ─── Libro Diario ─────────────────────────────────────────────────────────────

function LibroDiario({ year, trimestre }: { year: string; trimestre: string }) {
    const { apiRequest } = useApi()
    const [entries, setEntries] = useState<DiarioEntry[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        const qs = new URLSearchParams({ year })
        if (trimestre && trimestre !== 'todos') qs.set('trimestre', trimestre)
        apiRequest(`/api/contabilidad/libro-diario?${qs}`)
            .then((data: any) => {
                const raw = data?.entries || data?.asientos || []
                setEntries(raw.map((e: any) => ({
                    fecha: e.fecha || '',
                    n_asiento: e.n_asiento ?? e.numero_asiento ?? 0,
                    cuenta: e.cuenta || e.cuenta_code || '',
                    nombre_cuenta: e.nombre_cuenta || e.cuenta_nombre || '',
                    debe: e.debe || 0,
                    haber: e.haber || 0,
                    concepto: e.concepto || '',
                })))
            })
            .catch(() => setEntries([]))
            .finally(() => setLoading(false))
    }, [year, trimestre])

    const totalDebe = entries.reduce((s, e) => s + e.debe, 0)
    const totalHaber = entries.reduce((s, e) => s + e.haber, 0)

    if (loading) return <LoadingRow />

    if (entries.length === 0) return <EmptyState mensaje="No hay asientos para los filtros seleccionados." />

    return (
        <div className="cont-table-section">
            {/* Desktop table */}
            <div className="cont-table-wrap cont-table-wrap--desktop">
                <table className="cont-table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th className="cont-table__num">N.º Asiento</th>
                            <th>Cuenta</th>
                            <th>Nombre</th>
                            <th className="cont-table__num">Debe</th>
                            <th className="cont-table__num">Haber</th>
                            <th>Concepto</th>
                        </tr>
                    </thead>
                    <tbody>
                        {entries.map((e, i) => (
                            <tr key={i}>
                                <td>{formatDate(e.fecha)}</td>
                                <td className="cont-table__num">{e.n_asiento}</td>
                                <td><code className="cont-account-code">{e.cuenta}</code></td>
                                <td>{e.nombre_cuenta}</td>
                                <td className="cont-table__num">{e.debe > 0 ? formatEUR(e.debe) : '—'}</td>
                                <td className="cont-table__num">{e.haber > 0 ? formatEUR(e.haber) : '—'}</td>
                                <td className="cont-table__concepto">{e.concepto}</td>
                            </tr>
                        ))}
                    </tbody>
                    <tfoot>
                        <tr className="cont-table__totals">
                            <td colSpan={4}><strong>Totales</strong></td>
                            <td className="cont-table__num"><strong>{formatEUR(totalDebe)}</strong></td>
                            <td className="cont-table__num"><strong>{formatEUR(totalHaber)}</strong></td>
                            <td />
                        </tr>
                    </tfoot>
                </table>
            </div>

            {/* Mobile cards */}
            <div className="cont-mobile-cards">
                {entries.map((e, i) => (
                    <div key={i} className="cont-mobile-card">
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Fecha / Asiento</span>
                            <span>{formatDate(e.fecha)} · #{e.n_asiento}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Cuenta</span>
                            <code className="cont-account-code">{e.cuenta}</code>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Nombre</span>
                            <span>{e.nombre_cuenta}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Debe</span>
                            <span className="cont-debit">{e.debe > 0 ? formatEUR(e.debe) : '—'}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Haber</span>
                            <span className="cont-credit">{e.haber > 0 ? formatEUR(e.haber) : '—'}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Concepto</span>
                            <span>{e.concepto}</span>
                        </div>
                    </div>
                ))}
                <div className="cont-mobile-totals">
                    <span>Total Debe: <strong>{formatEUR(totalDebe)}</strong></span>
                    <span>Total Haber: <strong>{formatEUR(totalHaber)}</strong></span>
                </div>
            </div>
        </div>
    )
}

// ─── Libro Mayor ──────────────────────────────────────────────────────────────

function LibroMayor({ year }: { year: string }) {
    const { apiRequest } = useApi()
    const [accounts, setAccounts] = useState<MayorAccount[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        apiRequest(`/api/contabilidad/libro-mayor?year=${year}`)
            .then((data: any) => {
                const raw = data?.accounts || data?.cuentas || []
                setAccounts(raw.map((acc: any) => ({
                    cuenta: acc.cuenta || acc.cuenta_code || '',
                    nombre: acc.nombre || acc.cuenta_nombre || '',
                    total_debe: acc.total_debe || 0,
                    total_haber: acc.total_haber || 0,
                    saldo: acc.saldo || 0,
                })))
            })
            .catch(() => setAccounts([]))
            .finally(() => setLoading(false))
    }, [year])

    if (loading) return <LoadingRow />
    if (accounts.length === 0) return <EmptyState mensaje="No hay datos de mayor para el año seleccionado." />

    return (
        <div className="cont-table-section">
            <div className="cont-table-wrap cont-table-wrap--desktop">
                <table className="cont-table">
                    <thead>
                        <tr>
                            <th>Cuenta</th>
                            <th>Nombre</th>
                            <th className="cont-table__num">Total Debe</th>
                            <th className="cont-table__num">Total Haber</th>
                            <th className="cont-table__num">Saldo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {accounts.map((acc, i) => (
                            <tr key={i}>
                                <td><code className="cont-account-code">{acc.cuenta}</code></td>
                                <td>{acc.nombre}</td>
                                <td className="cont-table__num">{formatEUR(acc.total_debe)}</td>
                                <td className="cont-table__num">{formatEUR(acc.total_haber)}</td>
                                <td className={`cont-table__num cont-saldo${acc.saldo >= 0 ? '--pos' : '--neg'}`}>
                                    {formatEUR(acc.saldo)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <div className="cont-mobile-cards">
                {accounts.map((acc, i) => (
                    <div key={i} className="cont-mobile-card">
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Cuenta</span>
                            <code className="cont-account-code">{acc.cuenta}</code>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Nombre</span>
                            <span>{acc.nombre}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Total Debe</span>
                            <span>{formatEUR(acc.total_debe)}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Total Haber</span>
                            <span>{formatEUR(acc.total_haber)}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Saldo</span>
                            <strong className={acc.saldo >= 0 ? 'cont-saldo--pos' : 'cont-saldo--neg'}>
                                {formatEUR(acc.saldo)}
                            </strong>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// ─── Balance ──────────────────────────────────────────────────────────────────

function Balance({ year }: { year: string }) {
    const { apiRequest } = useApi()
    const [data, setData] = useState<BalanceData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        apiRequest(`/api/contabilidad/balance?year=${year}`)
            .then((d: any) => {
                // Map backend response (cuentas/cuenta_code/cuenta_nombre) to frontend shape
                const raw = d?.cuentas || d?.accounts || []
                const accounts = raw.map((acc: any) => ({
                    cuenta: acc.cuenta || acc.cuenta_code || '',
                    nombre: acc.nombre || acc.cuenta_nombre || '',
                    total_debe: acc.total_debe || 0,
                    total_haber: acc.total_haber || 0,
                    saldo: acc.saldo || 0,
                }))
                const total_debe = d.total_debe ?? accounts.reduce((s: number, a: any) => s + a.total_debe, 0)
                const total_haber = d.total_haber ?? accounts.reduce((s: number, a: any) => s + a.total_haber, 0)
                setData({
                    accounts,
                    total_debe,
                    total_haber,
                    diferencia: d.diferencia ?? (total_debe - total_haber),
                })
            })
            .catch(() => setData(null))
            .finally(() => setLoading(false))
    }, [year])

    if (loading) return <LoadingRow />
    if (!data || data.accounts.length === 0) return <EmptyState mensaje="No hay datos de balance para el año seleccionado." />

    const cuadra = Math.abs(data.diferencia) < 0.01

    return (
        <div className="cont-table-section">
            <div className="cont-table-wrap cont-table-wrap--desktop">
                <table className="cont-table">
                    <thead>
                        <tr>
                            <th>Cuenta</th>
                            <th>Nombre</th>
                            <th className="cont-table__num">Total Debe</th>
                            <th className="cont-table__num">Total Haber</th>
                            <th className="cont-table__num">Saldo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.accounts.map((acc, i) => (
                            <tr key={i}>
                                <td><code className="cont-account-code">{acc.cuenta}</code></td>
                                <td>{acc.nombre}</td>
                                <td className="cont-table__num">{formatEUR(acc.total_debe)}</td>
                                <td className="cont-table__num">{formatEUR(acc.total_haber)}</td>
                                <td className={`cont-table__num cont-saldo${acc.saldo >= 0 ? '--pos' : '--neg'}`}>
                                    {formatEUR(acc.saldo)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                    <tfoot>
                        <tr className="cont-table__totals">
                            <td colSpan={2}><strong>Totales</strong></td>
                            <td className="cont-table__num"><strong>{formatEUR(data.total_debe)}</strong></td>
                            <td className="cont-table__num"><strong>{formatEUR(data.total_haber)}</strong></td>
                            <td />
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div className="cont-mobile-cards">
                {data.accounts.map((acc, i) => (
                    <div key={i} className="cont-mobile-card">
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Cuenta</span>
                            <code className="cont-account-code">{acc.cuenta}</code>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Nombre</span>
                            <span>{acc.nombre}</span>
                        </div>
                        <div className="cont-mobile-card__row">
                            <span className="cont-mobile-card__label">Saldo</span>
                            <strong className={acc.saldo >= 0 ? 'cont-saldo--pos' : 'cont-saldo--neg'}>
                                {formatEUR(acc.saldo)}
                            </strong>
                        </div>
                    </div>
                ))}
            </div>

            <div className={`cont-balance-check${cuadra ? ' cont-balance-check--ok' : ' cont-balance-check--err'}`}>
                <Scale size={18} />
                {cuadra
                    ? 'El balance cuadra correctamente (Debe = Haber).'
                    : `El balance no cuadra: diferencia de ${formatEUR(Math.abs(data.diferencia))}.`
                }
            </div>
        </div>
    )
}

// ─── Pérdidas y Ganancias ─────────────────────────────────────────────────────

function PyG({ year }: { year: string }) {
    const { apiRequest } = useApi()
    const [data, setData] = useState<PYGData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        setLoading(true)
        apiRequest(`/api/contabilidad/pyg?year=${year}`)
            .then((d: any) => {
                const mapItems = (items: any[]) => (items || []).map((item: any) => ({
                    cuenta: item.cuenta || item.cuenta_code || '',
                    nombre: item.nombre || item.cuenta_nombre || '',
                    importe: item.importe ?? Math.abs(item.saldo ?? item.total_haber ?? item.total_debe ?? 0),
                }))
                setData({
                    ingresos: mapItems(d?.ingresos),
                    gastos: mapItems(d?.gastos),
                    total_ingresos: d?.total_ingresos ?? 0,
                    total_gastos: d?.total_gastos ?? 0,
                    resultado: d?.resultado ?? 0,
                })
            })
            .catch(() => setData(null))
            .finally(() => setLoading(false))
    }, [year])

    if (loading) return <LoadingRow />
    if (!data) return <EmptyState mensaje="No hay datos de pérdidas y ganancias para el año seleccionado." />

    const esPositivo = data.resultado >= 0

    return (
        <div className="cont-pyg">
            {/* Ingresos */}
            <div className="cont-pyg__block cont-pyg__block--ingresos">
                <div className="cont-pyg__block-header">
                    <TrendingUp size={18} />
                    <h4>Ingresos</h4>
                    <span className="cont-pyg__total cont-pyg__total--ingresos">
                        {formatEUR(data.total_ingresos)}
                    </span>
                </div>
                <div className="cont-table-wrap">
                    <table className="cont-table cont-pyg__table">
                        <thead>
                            <tr>
                                <th>Cuenta</th>
                                <th>Descripción</th>
                                <th className="cont-table__num">Importe</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.ingresos.map((item, i) => (
                                <tr key={i}>
                                    <td><code className="cont-account-code">{item.cuenta}</code></td>
                                    <td>{item.nombre}</td>
                                    <td className="cont-table__num cont-pyg__ingreso">{formatEUR(item.importe)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Gastos */}
            <div className="cont-pyg__block cont-pyg__block--gastos">
                <div className="cont-pyg__block-header">
                    <TrendingDown size={18} />
                    <h4>Gastos</h4>
                    <span className="cont-pyg__total cont-pyg__total--gastos">
                        {formatEUR(data.total_gastos)}
                    </span>
                </div>
                <div className="cont-table-wrap">
                    <table className="cont-table cont-pyg__table">
                        <thead>
                            <tr>
                                <th>Cuenta</th>
                                <th>Descripción</th>
                                <th className="cont-table__num">Importe</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.gastos.map((item, i) => (
                                <tr key={i}>
                                    <td><code className="cont-account-code">{item.cuenta}</code></td>
                                    <td>{item.nombre}</td>
                                    <td className="cont-table__num cont-pyg__gasto">{formatEUR(item.importe)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Resultado */}
            <div className={`cont-pyg__resultado${esPositivo ? ' cont-pyg__resultado--pos' : ' cont-pyg__resultado--neg'}`}>
                <span className="cont-pyg__resultado-label">
                    {esPositivo ? 'Beneficio del ejercicio' : 'Pérdida del ejercicio'}
                </span>
                <span className="cont-pyg__resultado-value">{formatEUR(Math.abs(data.resultado))}</span>
            </div>

            <p className="cont-disclaimer">
                Información orientativa. No sustituye el asesoramiento de un profesional contable.
            </p>
        </div>
    )
}

// ─── Shared sub-components ────────────────────────────────────────────────────

function LoadingRow() {
    return (
        <div className="cont-loading">
            <Loader2 size={22} className="cont-spinner" />
            <span>Cargando datos...</span>
        </div>
    )
}

function EmptyState({ mensaje }: { mensaje: string }) {
    return (
        <div className="cont-empty">
            <BookOpen size={36} />
            <p>{mensaje}</p>
        </div>
    )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const TABS: Array<{ key: TabKey; label: string }> = [
    { key: 'diario',  label: 'Libro Diario' },
    { key: 'mayor',   label: 'Libro Mayor'  },
    { key: 'balance', label: 'Balance'      },
    { key: 'pyg',     label: 'Pérd. y Gan.' },
]

export default function ContabilidadPage() {
    const [activeTab, setActiveTab] = useState<TabKey>('diario')
    const [year, setYear] = useState(new Date().getFullYear().toString())
    const [trimestre, setTrimestre] = useState('todos')

    return (
        <div className="cont-page">
            <div className="cont-page__inner">
                {/* Page header */}
                <div className="cont-page-header">
                    <div className="cont-page-header__icon">
                        <BookOpen size={28} />
                    </div>
                    <div>
                        <h1 className="cont-page-header__title">Contabilidad</h1>
                        <p className="cont-page-header__subtitle">
                            Libro diario, mayor, balance y resultado del ejercicio.
                        </p>
                    </div>
                </div>

                {/* Filters row */}
                <div className="cont-filters">
                    <YearSelect value={year} onChange={setYear} />
                    {activeTab === 'diario' && (
                        <QuarterSelect value={trimestre} onChange={setTrimestre} />
                    )}
                    <div className="cont-filters__spacer" />
                    <ExportButton
                        lib={activeTab}
                        year={year}
                        trimestre={activeTab === 'diario' ? trimestre : undefined}
                    />
                </div>

                {/* Tabs */}
                <div className="cont-tabs" role="tablist">
                    {TABS.map(tab => (
                        <button
                            key={tab.key}
                            role="tab"
                            aria-selected={activeTab === tab.key}
                            className={`cont-tab${activeTab === tab.key ? ' cont-tab--active' : ''}`}
                            onClick={() => setActiveTab(tab.key)}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab panels */}
                <div className="cont-panel" role="tabpanel">
                    {activeTab === 'diario'  && <LibroDiario year={year} trimestre={trimestre} />}
                    {activeTab === 'mayor'   && <LibroMayor year={year} />}
                    {activeTab === 'balance' && <Balance year={year} />}
                    {activeTab === 'pyg'     && <PyG year={year} />}
                </div>

                {/* Disclaimer (global) */}
                {activeTab !== 'pyg' && (
                    <p className="cont-disclaimer">
                        Información orientativa. No sustituye el asesoramiento de un profesional contable.
                    </p>
                )}
            </div>
        </div>
    )
}
