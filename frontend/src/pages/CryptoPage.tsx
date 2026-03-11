import { useState, useEffect, useCallback, useRef } from 'react'
import {
    Bitcoin,
    Upload,
    Wallet,
    TrendingUp,
    TrendingDown,
    Trash2,
    AlertTriangle,
    ChevronLeft,
    ChevronRight,
    Loader2,
    FileText,
    BarChart3,
    Info,
} from 'lucide-react'
import Header from '../components/Header'
import { useCrypto } from '../hooks/useCrypto'
import './CryptoPage.css'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CURRENT_YEAR = new Date().getFullYear()
const TAX_YEARS = [CURRENT_YEAR - 1, CURRENT_YEAR - 2, CURRENT_YEAR - 3]

const TX_TYPE_LABELS: Record<string, string> = {
    buy: 'Compra',
    sell: 'Venta',
    trade: 'Intercambio',
    transfer: 'Transferencia',
    staking: 'Staking',
    mining: 'Mineria',
    fee: 'Comision',
}

const CONTRAPRESTACION_LABELS: Record<string, string> = {
    F: 'Moneda fiat',
    N: 'Cripto a cripto',
    O: 'Activo virtual (NFT)',
    B: 'Bienes/servicios',
}

// ---------------------------------------------------------------------------
// Upload Zone
// ---------------------------------------------------------------------------

interface UploadZoneProps {
    onUpload: (file: File) => Promise<void>
    uploading: boolean
    error: string | null
}

function UploadZone({ onUpload, uploading, error }: UploadZoneProps) {
    const [dragging, setDragging] = useState(false)
    const [lastResult, setLastResult] = useState<{ imported: number; exchange: string } | null>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const handleDrop = useCallback(
        async (e: React.DragEvent) => {
            e.preventDefault()
            setDragging(false)
            const file = e.dataTransfer.files[0]
            if (file) await onUpload(file)
        },
        [onUpload]
    )

    const handleFileInput = useCallback(
        async (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0]
            if (file) await onUpload(file)
            // Reset so same file can be re-uploaded
            e.target.value = ''
        },
        [onUpload]
    )

    return (
        <div className="crypto-upload-section">
            <h2 className="crypto-section-title">
                <Upload size={20} />
                Importar transacciones
            </h2>

            <div
                className={`crypto-dropzone ${dragging ? 'crypto-dropzone--dragging' : ''} ${uploading ? 'crypto-dropzone--loading' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => !uploading && inputRef.current?.click()}
                role="button"
                tabIndex={0}
                aria-label="Zona de arrastre para subir CSV"
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click() }}
            >
                <input
                    ref={inputRef}
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    className="crypto-dropzone__input"
                    onChange={handleFileInput}
                    aria-hidden="true"
                    tabIndex={-1}
                />

                {uploading ? (
                    <div className="crypto-dropzone__content">
                        <Loader2 size={36} className="crypto-dropzone__icon crypto-spin" />
                        <p className="crypto-dropzone__text">Procesando archivo...</p>
                    </div>
                ) : (
                    <div className="crypto-dropzone__content">
                        <Bitcoin size={36} className="crypto-dropzone__icon" />
                        <p className="crypto-dropzone__text">
                            Arrastra tu CSV de Binance, Coinbase, Kraken...
                        </p>
                        <p className="crypto-dropzone__hint">
                            O haz clic para seleccionar un archivo CSV / XLSX
                        </p>
                        <button
                            type="button"
                            className="crypto-btn crypto-btn--primary crypto-dropzone__btn"
                            onClick={(e) => { e.stopPropagation(); inputRef.current?.click() }}
                        >
                            Seleccionar archivo
                        </button>
                    </div>
                )}
            </div>

            {error && (
                <div className="crypto-alert crypto-alert--error">
                    <AlertTriangle size={16} />
                    {error}
                </div>
            )}

            {lastResult && !error && (
                <div className="crypto-alert crypto-alert--success">
                    <Info size={16} />
                    {lastResult.imported} transacciones importadas desde {lastResult.exchange}
                </div>
            )}

            {/* Expose a setter so the parent can update last result */}
            <div style={{ display: 'none' }} data-set-result={JSON.stringify(lastResult)} />
        </div>
    )
}

// ---------------------------------------------------------------------------
// Transactions Tab
// ---------------------------------------------------------------------------

interface TransactionsTabProps {
    transactions: ReturnType<typeof useCrypto>['transactions']
    total: number
    page: number
    loading: boolean
    error: string | null
    onPageChange: (p: number) => void
    onDelete: (id: string) => void
}

function TransactionsTab({ transactions, total, page, loading, error, onPageChange, onDelete }: TransactionsTabProps) {
    const PAGE_SIZE = 20
    const totalPages = Math.ceil(total / PAGE_SIZE)

    if (loading) {
        return (
            <div className="crypto-loading">
                <Loader2 size={24} className="crypto-spin" />
                Cargando transacciones...
            </div>
        )
    }

    if (error) {
        return (
            <div className="crypto-alert crypto-alert--error">
                <AlertTriangle size={16} />
                {error}
            </div>
        )
    }

    if (transactions.length === 0) {
        return (
            <div className="crypto-empty">
                <FileText size={40} className="crypto-empty__icon" />
                <p>No hay transacciones importadas aún.</p>
                <p className="crypto-empty__sub">Sube un CSV de tu exchange para empezar.</p>
            </div>
        )
    }

    return (
        <div className="crypto-transactions">
            <div className="crypto-table-wrap">
                <table className="crypto-table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Tipo</th>
                            <th>Activo</th>
                            <th className="crypto-table__right">Cantidad</th>
                            <th className="crypto-table__right">Precio EUR</th>
                            <th className="crypto-table__right">Total EUR</th>
                            <th>Exchange</th>
                            <th aria-label="Acciones"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {transactions.map((tx) => (
                            <tr key={tx.id} className="crypto-table__row">
                                <td className="crypto-table__date">
                                    {new Date(tx.date_utc).toLocaleDateString('es-ES')}
                                </td>
                                <td>
                                    <span className={`crypto-badge crypto-badge--${tx.tx_type}`}>
                                        {TX_TYPE_LABELS[tx.tx_type] ?? tx.tx_type}
                                    </span>
                                </td>
                                <td className="crypto-table__asset">{tx.asset}</td>
                                <td className="crypto-table__right crypto-table__mono">
                                    {tx.amount.toFixed(8)}
                                </td>
                                <td className="crypto-table__right crypto-table__mono">
                                    {(tx.price_eur ?? 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="crypto-table__right crypto-table__mono">
                                    {(tx.total_eur ?? 0).toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="crypto-table__exchange">{tx.exchange}</td>
                                <td>
                                    <button
                                        type="button"
                                        className="crypto-delete-btn"
                                        onClick={() => onDelete(tx.id)}
                                        aria-label={`Eliminar transacción ${tx.asset}`}
                                    >
                                        <Trash2 size={15} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {totalPages > 1 && (
                <div className="crypto-pagination">
                    <button
                        className="crypto-page-btn"
                        disabled={page <= 1}
                        onClick={() => onPageChange(page - 1)}
                        aria-label="Página anterior"
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <span className="crypto-page-info">
                        {page} / {totalPages}
                    </span>
                    <button
                        className="crypto-page-btn"
                        disabled={page >= totalPages}
                        onClick={() => onPageChange(page + 1)}
                        aria-label="Página siguiente"
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>
            )}

            <p className="crypto-total-count">{total} transacciones en total</p>
        </div>
    )
}

// ---------------------------------------------------------------------------
// Portfolio Tab
// ---------------------------------------------------------------------------

interface PortfolioTabProps {
    holdings: ReturnType<typeof useCrypto>['holdings']
    loading: boolean
    error: string | null
}

function PortfolioTab({ holdings, loading, error }: PortfolioTabProps) {
    if (loading) {
        return (
            <div className="crypto-loading">
                <Loader2 size={24} className="crypto-spin" />
                Cargando portfolio...
            </div>
        )
    }

    if (error) {
        return (
            <div className="crypto-alert crypto-alert--error">
                <AlertTriangle size={16} />
                {error}
            </div>
        )
    }

    if (holdings.length === 0) {
        return (
            <div className="crypto-empty">
                <Wallet size={40} className="crypto-empty__icon" />
                <p>No hay activos en cartera.</p>
                <p className="crypto-empty__sub">Los activos aparecerán cuando importes transacciones.</p>
            </div>
        )
    }

    return (
        <div className="crypto-holdings">
            <div className="crypto-holdings__grid">
                {holdings.map((h) => (
                    <div key={h.asset} className="crypto-holding-card">
                        <div className="crypto-holding-card__header">
                            <span className="crypto-holding-card__asset">{h.asset}</span>
                        </div>
                        <div className="crypto-holding-card__stats">
                            <div className="crypto-holding-card__stat">
                                <span className="crypto-holding-card__stat-label">Unidades</span>
                                <span className="crypto-holding-card__stat-value">
                                    {h.total_units.toFixed(8)}
                                </span>
                            </div>
                            <div className="crypto-holding-card__stat">
                                <span className="crypto-holding-card__stat-label">Coste medio</span>
                                <span className="crypto-holding-card__stat-value">
                                    {h.avg_cost_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR
                                </span>
                            </div>
                            <div className="crypto-holding-card__stat">
                                <span className="crypto-holding-card__stat-label">Total invertido</span>
                                <span className="crypto-holding-card__stat-value crypto-holding-card__stat-value--accent">
                                    {h.total_invested_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR
                                </span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// ---------------------------------------------------------------------------
// Gains Tab
// ---------------------------------------------------------------------------

interface GainsTabProps {
    summary: ReturnType<typeof useCrypto>['gainsSummary']
    selectedYear: number
    loading: boolean
    error: string | null
    onYearChange: (year: number) => void
}

function GainsTab({ summary, selectedYear, loading, error, onYearChange }: GainsTabProps) {
    if (loading) {
        return (
            <div className="crypto-loading">
                <Loader2 size={24} className="crypto-spin" />
                Calculando ganancias fiscales...
            </div>
        )
    }

    if (error) {
        return (
            <>
                <div className="crypto-year-selector">
                    <label htmlFor="gains-year" className="crypto-year-label">Ejercicio fiscal:</label>
                    <select
                        id="gains-year"
                        className="crypto-year-select"
                        value={selectedYear}
                        onChange={(e) => onYearChange(Number(e.target.value))}
                    >
                        {TAX_YEARS.map((y) => (
                            <option key={y} value={y}>{y}</option>
                        ))}
                    </select>
                </div>
                <div className="crypto-alert crypto-alert--error">
                    <AlertTriangle size={16} />
                    {error}
                </div>
            </>
        )
    }

    return (
        <div className="crypto-gains">
            <div className="crypto-year-selector">
                <label htmlFor="gains-year" className="crypto-year-label">Ejercicio fiscal:</label>
                <select
                    id="gains-year"
                    className="crypto-year-select"
                    value={selectedYear}
                    onChange={(e) => onYearChange(Number(e.target.value))}
                >
                    {TAX_YEARS.map((y) => (
                        <option key={y} value={y}>{y}</option>
                    ))}
                </select>
            </div>

            {!summary ? (
                <div className="crypto-empty">
                    <BarChart3 size={40} className="crypto-empty__icon" />
                    <p>Selecciona un año para ver las ganancias fiscales.</p>
                </div>
            ) : (
                <>
                    {/* Summary cards */}
                    <div className="crypto-gains__summary">
                        <div className="crypto-gains__card crypto-gains__card--positive">
                            <TrendingUp size={20} className="crypto-gains__card-icon" />
                            <div>
                                <span className="crypto-gains__card-label">Ganancias — Casilla 1814</span>
                                <span className="crypto-gains__card-amount">
                                    {summary.total_gains_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR
                                </span>
                            </div>
                        </div>
                        <div className="crypto-gains__card crypto-gains__card--negative">
                            <TrendingDown size={20} className="crypto-gains__card-icon" />
                            <div>
                                <span className="crypto-gains__card-label">Pérdidas — Casilla 1813</span>
                                <span className="crypto-gains__card-amount">
                                    {summary.total_losses_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR
                                </span>
                            </div>
                        </div>
                        <div className={`crypto-gains__card ${summary.net_eur >= 0 ? 'crypto-gains__card--net-pos' : 'crypto-gains__card--net-neg'}`}>
                            <BarChart3 size={20} className="crypto-gains__card-icon" />
                            <div>
                                <span className="crypto-gains__card-label">Neto a declarar</span>
                                <span className="crypto-gains__card-amount">
                                    {summary.net_eur >= 0 ? '+' : ''}
                                    {summary.net_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} EUR
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Detail table */}
                    {summary.gains.length > 0 && (
                        <div className="crypto-gains__detail">
                            <h3 className="crypto-gains__detail-title">Detalle de operaciones</h3>
                            <div className="crypto-table-wrap">
                                <table className="crypto-table crypto-table--gains">
                                    <thead>
                                        <tr>
                                            <th>Activo</th>
                                            <th>Fecha compra</th>
                                            <th>Fecha venta</th>
                                            <th>Tipo</th>
                                            <th className="crypto-table__right">Adquisición</th>
                                            <th className="crypto-table__right">Transmisión</th>
                                            <th className="crypto-table__right">Ganancia/Pérdida</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {summary.gains.map((g, idx) => (
                                            <tr
                                                key={idx}
                                                className={`crypto-table__row ${g.gain_loss_eur < 0 ? 'crypto-table__row--loss' : 'crypto-table__row--gain'}`}
                                            >
                                                <td className="crypto-table__asset">{g.asset}</td>
                                                <td>{new Date(g.date_acquisition).toLocaleDateString('es-ES')}</td>
                                                <td>{new Date(g.date_transmission).toLocaleDateString('es-ES')}</td>
                                                <td>
                                                    <span className="crypto-badge crypto-badge--contraprestacion" title={CONTRAPRESTACION_LABELS[g.clave_contraprestacion] ?? g.clave_contraprestacion}>
                                                        {g.clave_contraprestacion}
                                                    </span>
                                                </td>
                                                <td className="crypto-table__right crypto-table__mono">
                                                    {g.acquisition_value_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                </td>
                                                <td className="crypto-table__right crypto-table__mono">
                                                    {g.transmission_value_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                </td>
                                                <td className={`crypto-table__right crypto-table__mono ${g.gain_loss_eur < 0 ? 'crypto-text--loss' : 'crypto-text--gain'}`}>
                                                    {g.gain_loss_eur >= 0 ? '+' : ''}
                                                    {g.gain_loss_eur.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    <p className="crypto-gains__note">
                        Las ganancias patrimoniales por criptomonedas tributan en la base del ahorro
                        (Art. 33 LIRPF). Método FIFO aplicado según criterio AEAT.
                    </p>
                </>
            )}
        </div>
    )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

type Tab = 'transactions' | 'portfolio' | 'gains'

export default function CryptoPage() {
    const [activeTab, setActiveTab] = useState<Tab>('transactions')
    const [selectedGainsYear, setSelectedGainsYear] = useState(CURRENT_YEAR - 1)
    const [uploadSuccess, setUploadSuccess] = useState<{ imported: number; exchange: string } | null>(null)

    const {
        transactions, totalTransactions, currentPage,
        holdings, gainsSummary,
        loadingTransactions, loadingHoldings, loadingGains, uploading,
        errorTransactions, errorHoldings, errorGains, errorUpload,
        fetchTransactions, fetchHoldings, fetchGains,
        uploadFile, deleteTransaction,
    } = useCrypto()

    // Load transactions on first render
    useEffect(() => {
        fetchTransactions(1)
    }, [fetchTransactions])

    const handleTabChange = useCallback((tab: Tab) => {
        setActiveTab(tab)
        if (tab === 'portfolio' && holdings.length === 0 && !loadingHoldings) {
            fetchHoldings()
        }
        if (tab === 'gains' && !gainsSummary && !loadingGains) {
            fetchGains(selectedGainsYear)
        }
    }, [holdings.length, loadingHoldings, gainsSummary, loadingGains, selectedGainsYear, fetchHoldings, fetchGains])

    const handleUpload = useCallback(async (file: File) => {
        const result = await uploadFile(file)
        if (result?.success) {
            setUploadSuccess({ imported: result.imported, exchange: result.exchange_detected })
            // Refresh transactions after successful upload
            fetchTransactions(1)
            if (activeTab === 'portfolio') fetchHoldings()
        }
    }, [uploadFile, fetchTransactions, fetchHoldings, activeTab])

    const handleYearChange = useCallback((year: number) => {
        setSelectedGainsYear(year)
        fetchGains(year)
    }, [fetchGains])

    const handleDelete = useCallback(async (id: string) => {
        if (!window.confirm('¿Eliminar esta transacción?')) return
        await deleteTransaction(id)
    }, [deleteTransaction])

    return (
        <div className="crypto-page">
            <Header />

            <main className="crypto-page__main">
                {/* Page header */}
                <div className="crypto-page__header">
                    <Bitcoin size={28} />
                    <div>
                        <h1>Criptomonedas</h1>
                        <p>Gestión fiscal de monedas virtuales — Casillas 1800-1814 del Modelo 100</p>
                    </div>
                </div>

                {/* Upload zone */}
                <UploadZone
                    onUpload={handleUpload}
                    uploading={uploading}
                    error={errorUpload}
                />

                {uploadSuccess && !errorUpload && (
                    <div className="crypto-alert crypto-alert--success">
                        <Info size={16} />
                        {uploadSuccess.imported} transacciones importadas desde {uploadSuccess.exchange}
                    </div>
                )}

                {/* Tabs */}
                <div className="crypto-tabs">
                    <button
                        className={`crypto-tab ${activeTab === 'transactions' ? 'crypto-tab--active' : ''}`}
                        onClick={() => handleTabChange('transactions')}
                    >
                        <FileText size={16} />
                        Transacciones
                    </button>
                    <button
                        className={`crypto-tab ${activeTab === 'portfolio' ? 'crypto-tab--active' : ''}`}
                        onClick={() => handleTabChange('portfolio')}
                    >
                        <Wallet size={16} />
                        Portfolio
                    </button>
                    <button
                        className={`crypto-tab ${activeTab === 'gains' ? 'crypto-tab--active' : ''}`}
                        onClick={() => handleTabChange('gains')}
                    >
                        <BarChart3 size={16} />
                        Ganancias fiscales
                    </button>
                </div>

                {/* Tab content */}
                <div className="crypto-tab-content">
                    {activeTab === 'transactions' && (
                        <TransactionsTab
                            transactions={transactions}
                            total={totalTransactions}
                            page={currentPage}
                            loading={loadingTransactions}
                            error={errorTransactions}
                            onPageChange={fetchTransactions}
                            onDelete={handleDelete}
                        />
                    )}
                    {activeTab === 'portfolio' && (
                        <PortfolioTab
                            holdings={holdings}
                            loading={loadingHoldings}
                            error={errorHoldings}
                        />
                    )}
                    {activeTab === 'gains' && (
                        <GainsTab
                            summary={gainsSummary}
                            selectedYear={selectedGainsYear}
                            loading={loadingGains}
                            error={errorGains}
                            onYearChange={handleYearChange}
                        />
                    )}
                </div>
            </main>
        </div>
    )
}
