import { useState, useCallback, useEffect } from 'react'
import {
    Upload,
    FileText,
    CheckCircle,
    AlertTriangle,
    XCircle,
    Loader2,
    Trash2,
    Eye,
    ChevronDown,
    ChevronUp,
    RefreshCw,
    Search,
    ArrowLeft,
    FolderOpen,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { useWorkspaces } from '../hooks/useWorkspaces'
import './ClasificadorFacturasPage.css'

// ─── Types ────────────────────────────────────────────────────────────────────

interface InvoiceLine {
    concepto: string
    cantidad: number
    precio_unitario: number
    base: number
}

interface InvoiceExtraction {
    emisor_nombre: string
    emisor_nif: string
    receptor_nombre: string
    receptor_nif: string
    fecha: string
    numero_factura: string
    lineas: InvoiceLine[]
    base_imponible: number
    tipo_iva: number
    cuota_iva: number
    retenciones: number
    total: number
    confianza: 'alta' | 'media' | 'baja'
    errores_validacion: string[]
}

interface PGCClassification {
    cuenta_pgc: string
    cuenta_pgc_nombre: string
    confianza: 'alta' | 'media' | 'baja'
    alternativas: Array<{ cuenta_pgc: string; cuenta_pgc_nombre: string }>
}

interface InvoiceResult {
    id: string
    extraccion: InvoiceExtraction
    clasificacion: PGCClassification
    confirmada: boolean
}

interface InvoiceListItem {
    id: string
    fecha: string
    fecha_factura?: string
    numero_factura: string
    emisor_nombre: string
    receptor_nombre: string
    base_imponible: number
    cuota_iva: number
    total: number
    cuenta_pgc: string
    cuenta_pgc_nombre: string
    confianza: 'alta' | 'media' | 'baja' | 'manual'
    clasificacion_confianza?: 'alta' | 'media' | 'baja' | 'manual'
    confirmada: boolean
    tipo?: string
}

type UploadStep = 'idle' | 'extracting' | 'classifying' | 'done' | 'error'

type QueueItemStatus = 'pending' | 'processing' | 'success' | 'error'

interface QueueItem {
    id: string
    filename: string
    size: number
    status: QueueItemStatus
    error?: string
    invoiceId?: string
}

const MAX_BATCH = 10

// ─── Helpers ──────────────────────────────────────────────────────────────────

function ConfianzaBadge({ nivel }: { nivel: 'alta' | 'media' | 'baja' | 'manual' }) {
    const map = {
        alta: { label: 'Alta confianza', cls: 'badge--green' },
        media: { label: 'Media confianza', cls: 'badge--yellow' },
        baja: { label: 'Baja confianza', cls: 'badge--red' },
    }
    const { label, cls } = map[nivel]
    return <span className={`cf-badge ${cls}`}>{label}</span>
}

function formatEUR(n: number | null | undefined) {
    return (n ?? 0).toLocaleString('es-ES', { style: 'currency', currency: 'EUR' })
}

function formatDate(dateStr: string) {
    if (!dateStr) return '—'
    try {
        return new Date(dateStr).toLocaleDateString('es-ES')
    } catch {
        return dateStr
    }
}

// ─── Upload Zone ──────────────────────────────────────────────────────────────

function UploadZone({
    onFiles,
    disabled,
}: {
    onFiles: (files: File[]) => void
    disabled?: boolean
}) {
    const [dragging, setDragging] = useState(false)
    const inputId = 'cf-file-upload'

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault()
            setDragging(false)
            if (disabled) return
            const files = Array.from(e.dataTransfer.files)
            if (files.length) onFiles(files)
        },
        [onFiles, disabled],
    )

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || [])
        if (files.length) onFiles(files)
        e.target.value = ''
    }

    return (
        <label
            htmlFor={inputId}
            className={`cf-upload-zone${dragging ? ' cf-upload-zone--dragging' : ''}${disabled ? ' cf-upload-zone--disabled' : ''}`}
            onDragOver={(e) => {
                e.preventDefault()
                if (!disabled) setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            tabIndex={0}
            onKeyDown={(e) => {
                if (e.key === 'Enter')
                    (e.currentTarget.querySelector('input') as HTMLInputElement)?.click()
            }}
            aria-label="Zona de carga de facturas"
        >
            <input
                id={inputId}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,image/*"
                onChange={handleChange}
                className="cf-upload-input"
                multiple
                disabled={disabled}
            />
            <Upload size={40} className="cf-upload-icon" />
            <p className="cf-upload-title">Arrastra tus facturas aquí</p>
            <p className="cf-upload-subtitle">
                PDF, JPG o PNG · hasta {MAX_BATCH} a la vez · máximo 10 MB cada una
            </p>
            <span className="cf-upload-btn" role="button">
                Seleccionar facturas
            </span>
        </label>
    )
}

function BatchQueue({ items }: { items: QueueItem[] }) {
    if (!items.length) return null
    return (
        <div className="cf-queue">
            <div className="cf-queue__header">
                <span className="cf-queue__title">
                    Procesando {items.length} factura{items.length === 1 ? '' : 's'}
                </span>
            </div>
            <ul className="cf-queue__list">
                {items.map((item) => (
                    <li key={item.id} className={`cf-queue__item cf-queue__item--${item.status}`}>
                        <span className="cf-queue__icon">
                            {item.status === 'pending' && <FileText size={16} />}
                            {item.status === 'processing' && (
                                <Loader2 size={16} className="cf-progress__spinner" />
                            )}
                            {item.status === 'success' && <CheckCircle size={16} />}
                            {item.status === 'error' && <XCircle size={16} />}
                        </span>
                        <div className="cf-queue__body">
                            <span className="cf-queue__name">{item.filename}</span>
                            {item.status === 'pending' && (
                                <span className="cf-queue__status">En cola</span>
                            )}
                            {item.status === 'processing' && (
                                <span className="cf-queue__status">Leyendo y clasificando...</span>
                            )}
                            {item.status === 'success' && (
                                <span className="cf-queue__status cf-queue__status--ok">
                                    Clasificada
                                </span>
                            )}
                            {item.status === 'error' && (
                                <span className="cf-queue__status cf-queue__status--err">
                                    {item.error || 'Error'}
                                </span>
                            )}
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    )
}

// ─── Upload Progress ───────────────────────────────────────────────────────────

function UploadProgress({ step }: { step: UploadStep }) {
    const steps: Array<{ key: UploadStep; label: string }> = [
        { key: 'extracting', label: 'Leyendo la factura...' },
        { key: 'classifying', label: 'Buscando la cuenta PGC...' },
        { key: 'done', label: 'Montando el asiento...' },
    ]
    return (
        <div className="cf-progress">
            <Loader2 size={32} className="cf-progress__spinner" />
            <div className="cf-progress__steps">
                {steps.map((s) => (
                    <span
                        key={s.key}
                        className={`cf-progress__step${step === s.key ? ' cf-progress__step--active' : ''}`}
                    >
                        {s.label}
                    </span>
                ))}
            </div>
        </div>
    )
}

// ─── Extraction Card ──────────────────────────────────────────────────────────

function ExtractionCard({ data }: { data: InvoiceExtraction }) {
    const [linesOpen, setLinesOpen] = useState(false)

    return (
        <div className="cf-card">
            <div className="cf-card__header">
                <h3 className="cf-card__title">Datos extraídos</h3>
                <ConfianzaBadge nivel={data.confianza} />
            </div>

            {data.errores_validacion.length > 0 && (
                <div className="cf-alert cf-alert--warning">
                    <AlertTriangle size={16} />
                    <div>
                        <strong>Revisa esto antes de guardar:</strong>
                        <ul className="cf-alert__list">
                            {data.errores_validacion.map((e, i) => (
                                <li key={i}>{e}</li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

            <div className="cf-grid cf-grid--2">
                <div className="cf-field">
                    <span className="cf-field__label">Emisor</span>
                    <span className="cf-field__value">{data.emisor_nombre || '—'}</span>
                    {data.emisor_nif && (
                        <span className="cf-field__sub">NIF: {data.emisor_nif}</span>
                    )}
                </div>
                <div className="cf-field">
                    <span className="cf-field__label">Receptor</span>
                    <span className="cf-field__value">{data.receptor_nombre || '—'}</span>
                    {data.receptor_nif && (
                        <span className="cf-field__sub">NIF: {data.receptor_nif}</span>
                    )}
                </div>
                <div className="cf-field">
                    <span className="cf-field__label">Número de factura</span>
                    <span className="cf-field__value">{data.numero_factura || '—'}</span>
                </div>
                <div className="cf-field">
                    <span className="cf-field__label">Fecha</span>
                    <span className="cf-field__value">{formatDate(data.fecha)}</span>
                </div>
            </div>

            {/* Lines toggle */}
            {data.lineas?.length > 0 && (
                <div className="cf-lines">
                    <button
                        className="cf-lines__toggle"
                        onClick={() => setLinesOpen((v) => !v)}
                        aria-expanded={linesOpen}
                    >
                        {linesOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        {linesOpen
                            ? 'Ocultar líneas'
                            : `Ver ${data.lineas.length === 1 ? 'la línea' : `las ${data.lineas.length} líneas`} de detalle`}
                    </button>
                    {linesOpen && (
                        <div className="cf-table-wrap">
                            <table className="cf-table">
                                <thead>
                                    <tr>
                                        <th>Concepto</th>
                                        <th className="cf-table__num">Cant.</th>
                                        <th className="cf-table__num">Precio</th>
                                        <th className="cf-table__num">Base</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.lineas.map((l, i) => (
                                        <tr key={i}>
                                            <td>{l.concepto}</td>
                                            <td className="cf-table__num">{l.cantidad}</td>
                                            <td className="cf-table__num">
                                                {formatEUR(l.precio_unitario)}
                                            </td>
                                            <td className="cf-table__num">{formatEUR(l.base)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}

            {/* Totals */}
            <div className="cf-totals">
                <div className="cf-totals__row">
                    <span>Base imponible</span>
                    <span>{formatEUR(data.base_imponible)}</span>
                </div>
                <div className="cf-totals__row">
                    <span>IVA ({data.tipo_iva}%)</span>
                    <span>{formatEUR(data.cuota_iva)}</span>
                </div>
                {data.retenciones > 0 && (
                    <div className="cf-totals__row cf-totals__row--negative">
                        <span>Retenciones</span>
                        <span>-{formatEUR(data.retenciones)}</span>
                    </div>
                )}
                <div className="cf-totals__row cf-totals__row--total">
                    <span>Total</span>
                    <span>{formatEUR(data.total)}</span>
                </div>
            </div>
        </div>
    )
}

// ─── Classification Card ──────────────────────────────────────────────────────

interface ClassificationCardProps {
    data: PGCClassification
    invoiceId: string
    onReclassify: (id: string, cuenta: string, nombre: string) => Promise<void>
    onConfirm: () => void
}

function ClassificationCard({ data, invoiceId, onReclassify, onConfirm }: ClassificationCardProps) {
    const [editing, setEditing] = useState(false)
    const [searchVal, setSearchVal] = useState('')
    const [saving, setSaving] = useState(false)
    const [confirmed, setConfirmed] = useState(false)

    const handleAlternative = async (cuenta: string, nombre: string) => {
        setSaving(true)
        await onReclassify(invoiceId, cuenta, nombre)
        setSaving(false)
        setEditing(false)
    }

    const handleManualSave = async () => {
        const trimmed = searchVal.trim()
        if (!trimmed) return
        // Parse "629 Otros servicios" or just "629"
        const match = trimmed.match(/^(\d{3,4})\s*(.*)$/)
        if (match) {
            await handleAlternative(match[1], match[2] || `Cuenta ${match[1]}`)
        } else {
            await handleAlternative(trimmed, trimmed)
        }
        setSearchVal('')
    }

    const handleConfirm = () => {
        setConfirmed(true)
        onConfirm()
    }

    return (
        <div className="cf-card">
            <div className="cf-card__header">
                <h3 className="cf-card__title">Clasificación PGC</h3>
                <ConfianzaBadge nivel={data.confianza} />
            </div>

            <div className="cf-pgc-main">
                <span className="cf-pgc-code">{data.cuenta_pgc}</span>
                <span className="cf-pgc-name">{data.cuenta_pgc_nombre}</span>
            </div>

            {data.confianza !== 'alta' && data.alternativas?.length > 0 && !editing && (
                <div className="cf-pgc-alternatives">
                    <p className="cf-pgc-alternatives__label">¿Encaja mejor otra cuenta?</p>
                    <div className="cf-pgc-alternatives__list">
                        {data.alternativas.map((alt) => (
                            <button
                                key={alt.cuenta_pgc}
                                className="cf-pgc-alt-btn"
                                onClick={() =>
                                    handleAlternative(alt.cuenta_pgc, alt.cuenta_pgc_nombre)
                                }
                                disabled={saving}
                            >
                                <span className="cf-pgc-alt-btn__code">{alt.cuenta_pgc}</span>
                                <span className="cf-pgc-alt-btn__name">
                                    {alt.cuenta_pgc_nombre}
                                </span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {editing && (
                <div className="cf-pgc-search">
                    <div className="cf-pgc-search__input-wrap">
                        <Search size={15} />
                        <input
                            type="text"
                            placeholder="Código o nombre de la cuenta..."
                            value={searchVal}
                            onChange={(e) => setSearchVal(e.target.value)}
                            className="cf-pgc-search__input"
                            autoFocus
                        />
                    </div>
                    <p className="cf-pgc-search__hint">Ej: 629 Otros servicios</p>
                    <div className="cf-pgc-search__actions">
                        <button
                            className="cf-btn cf-btn--primary"
                            onClick={handleManualSave}
                            disabled={saving || !searchVal.trim()}
                        >
                            <CheckCircle size={16} /> Aplicar
                        </button>
                        <button className="cf-btn cf-btn--ghost" onClick={() => setEditing(false)}>
                            Cancelar
                        </button>
                    </div>
                </div>
            )}

            <div className="cf-pgc-actions">
                {!confirmed ? (
                    <>
                        <button
                            className="cf-btn cf-btn--primary"
                            onClick={handleConfirm}
                            disabled={saving}
                        >
                            <CheckCircle size={16} /> Confirmar
                        </button>
                        <button
                            className="cf-btn cf-btn--ghost"
                            onClick={() => setEditing((v) => !v)}
                            disabled={saving}
                        >
                            <RefreshCw size={16} /> Corregir
                        </button>
                    </>
                ) : (
                    <div className="cf-pgc-confirmed">
                        <CheckCircle size={18} className="cf-pgc-confirmed__icon" />
                        <span>Listo, clasificada</span>
                    </div>
                )}
            </div>
        </div>
    )
}

// ─── Invoice List ──────────────────────────────────────────────────────────────

interface InvoiceListProps {
    invoices: InvoiceListItem[]
    onDelete: (id: string) => void
    onView: (id: string) => void
}

function InvoiceList({ invoices, onDelete, onView }: InvoiceListProps) {
    const [year, setYear] = useState(new Date().getFullYear().toString())
    const [trimestre, setTrimestre] = useState('todos')
    const [tipo, setTipo] = useState('todos')

    const years = Array.from(
        new Set(invoices.map((inv) => new Date(inv.fecha).getFullYear().toString())),
    ).sort((a, b) => Number(b) - Number(a))

    if (years.length === 0) years.push(new Date().getFullYear().toString())

    const filtered = invoices.filter((inv) => {
        const d = new Date(inv.fecha)
        const q = Math.ceil((d.getMonth() + 1) / 3)
        const yearMatch = d.getFullYear().toString() === year
        const qMatch = trimestre === 'todos' || q === Number(trimestre)
        const tipoMatch = tipo === 'todos' || inv.tipo === tipo
        return yearMatch && qMatch && tipoMatch
    })

    return (
        <div className="cf-list-section">
            <div className="cf-list-header">
                <h3 className="cf-section-title">Tus facturas</h3>
                <div className="cf-list-filters">
                    <select
                        value={year}
                        onChange={(e) => setYear(e.target.value)}
                        className="cf-select"
                        aria-label="Filtrar por año"
                    >
                        {years.map((y) => (
                            <option key={y} value={y}>
                                {y}
                            </option>
                        ))}
                    </select>
                    <select
                        value={trimestre}
                        onChange={(e) => setTrimestre(e.target.value)}
                        className="cf-select"
                        aria-label="Filtrar por trimestre"
                    >
                        <option value="todos">Todos los trimestres</option>
                        <option value="1">1T (ene-mar)</option>
                        <option value="2">2T (abr-jun)</option>
                        <option value="3">3T (jul-sep)</option>
                        <option value="4">4T (oct-dic)</option>
                    </select>
                    <select
                        value={tipo}
                        onChange={(e) => setTipo(e.target.value)}
                        className="cf-select"
                        aria-label="Filtrar por tipo"
                    >
                        <option value="todos">Todos los tipos</option>
                        <option value="emitida">Emitidas</option>
                        <option value="recibida">Recibidas</option>
                    </select>
                </div>
            </div>

            {filtered.length === 0 ? (
                <div className="cf-empty">
                    <FileText size={40} />
                    <p>No hay facturas con estos filtros.</p>
                </div>
            ) : (
                <>
                    {/* Desktop table */}
                    <div className="cf-table-wrap cf-table-wrap--desktop">
                        <table className="cf-table cf-table--list">
                            <thead>
                                <tr>
                                    <th>Fecha</th>
                                    <th>Número</th>
                                    <th>Emisor / Receptor</th>
                                    <th className="cf-table__num">Base</th>
                                    <th className="cf-table__num">IVA</th>
                                    <th className="cf-table__num">Total</th>
                                    <th>Cuenta PGC</th>
                                    <th>Confianza</th>
                                    <th>Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((inv) => (
                                    <tr key={inv.id}>
                                        <td>{formatDate(inv.fecha)}</td>
                                        <td>{inv.numero_factura}</td>
                                        <td>{inv.emisor_nombre || inv.receptor_nombre}</td>
                                        <td className="cf-table__num">
                                            {formatEUR(inv.base_imponible)}
                                        </td>
                                        <td className="cf-table__num">
                                            {formatEUR(inv.cuota_iva)}
                                        </td>
                                        <td className="cf-table__num">{formatEUR(inv.total)}</td>
                                        <td>
                                            <span className="cf-pgc-tag">{inv.cuenta_pgc}</span>
                                            <span className="cf-pgc-tag-name">
                                                {inv.cuenta_pgc_nombre}
                                            </span>
                                        </td>
                                        <td>
                                            <ConfianzaBadge nivel={inv.confianza} />
                                        </td>
                                        <td>
                                            <div className="cf-row-actions">
                                                <button
                                                    className="cf-icon-btn"
                                                    title="Ver detalle"
                                                    onClick={() => onView(inv.id)}
                                                >
                                                    <Eye size={16} />
                                                </button>
                                                <button
                                                    className="cf-icon-btn cf-icon-btn--danger"
                                                    title="Eliminar"
                                                    onClick={() => onDelete(inv.id)}
                                                >
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Mobile cards */}
                    <div className="cf-mobile-cards">
                        {filtered.map((inv) => (
                            <div key={inv.id} className="cf-mobile-card">
                                <div className="cf-mobile-card__row">
                                    <span className="cf-mobile-card__label">Fecha</span>
                                    <span>{formatDate(inv.fecha)}</span>
                                </div>
                                <div className="cf-mobile-card__row">
                                    <span className="cf-mobile-card__label">Número</span>
                                    <span>{inv.numero_factura}</span>
                                </div>
                                <div className="cf-mobile-card__row">
                                    <span className="cf-mobile-card__label">Emisor/Receptor</span>
                                    <span>{inv.emisor_nombre || inv.receptor_nombre}</span>
                                </div>
                                <div className="cf-mobile-card__row">
                                    <span className="cf-mobile-card__label">Total</span>
                                    <strong>{formatEUR(inv.total)}</strong>
                                </div>
                                <div className="cf-mobile-card__row">
                                    <span className="cf-mobile-card__label">Cuenta PGC</span>
                                    <span>
                                        {inv.cuenta_pgc} — {inv.cuenta_pgc_nombre}
                                    </span>
                                </div>
                                <div className="cf-mobile-card__row">
                                    <span className="cf-mobile-card__label">Confianza</span>
                                    <ConfianzaBadge nivel={inv.confianza} />
                                </div>
                                <div className="cf-mobile-card__actions">
                                    <button
                                        className="cf-btn cf-btn--ghost cf-btn--sm"
                                        onClick={() => onView(inv.id)}
                                    >
                                        <Eye size={15} /> Ver
                                    </button>
                                    <button
                                        className="cf-btn cf-btn--danger cf-btn--sm"
                                        onClick={() => onDelete(inv.id)}
                                    >
                                        <Trash2 size={15} /> Eliminar
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ClasificadorFacturasPage() {
    const { apiRequest } = useApi()
    const { workspaces, fetchWorkspaces } = useWorkspaces()
    const [searchParams] = useSearchParams()
    const [uploadStep, setUploadStep] = useState<UploadStep>('idle')
    const [uploadError, setUploadError] = useState<string | null>(null)
    const [result, setResult] = useState<InvoiceResult | null>(null)
    const [invoices, setInvoices] = useState<InvoiceListItem[]>([])
    const [loadingList, setLoadingList] = useState(true)
    const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>('')
    const [queue, setQueue] = useState<QueueItem[]>([])
    const [batchSummary, setBatchSummary] = useState<{ success: number; error: number } | null>(
        null,
    )

    // Load invoice list + workspaces on mount
    useEffect(() => {
        loadInvoices()
        fetchWorkspaces()
    }, [fetchWorkspaces])

    // Initialize selected workspace once workspaces load (URL param > default > first)
    useEffect(() => {
        if (selectedWorkspaceId || !workspaces.length) return
        const fromUrl = searchParams.get('workspace_id')
        if (fromUrl && workspaces.some((w) => w.id === fromUrl)) {
            setSelectedWorkspaceId(fromUrl)
            return
        }
        const def = workspaces.find((w) => w.is_default) || workspaces[0]
        if (def) setSelectedWorkspaceId(def.id)
    }, [workspaces, searchParams, selectedWorkspaceId])

    async function loadInvoices() {
        setLoadingList(true)
        try {
            const year = new Date().getFullYear()
            const data = await apiRequest(`/api/invoices?year=${year}`)
            const list = (data?.invoices ?? []).map((inv: any) => ({
                ...inv,
                fecha: inv.fecha || inv.fecha_factura || '',
                confianza: inv.confianza || inv.clasificacion_confianza || 'media',
            }))
            setInvoices(list)
        } catch {
            // Silently fail — backend may not be implemented yet
            setInvoices([])
        } finally {
            setLoadingList(false)
        }
    }

    function mapUploadResultToInvoiceResult(uploadResult: any): InvoiceResult {
        const factura = uploadResult.factura
        const clasificacion = uploadResult.clasificacion
        return {
            id: uploadResult.id,
            extraccion: {
                emisor_nombre: factura?.emisor?.nombre || '',
                emisor_nif: factura?.emisor?.nif_cif || '',
                receptor_nombre: factura?.receptor?.nombre || '',
                receptor_nif: factura?.receptor?.nif_cif || '',
                fecha: factura?.fecha_factura || '',
                numero_factura: factura?.numero_factura || '',
                lineas: (factura?.lineas || []).map((l: any) => ({
                    concepto: l.concepto || '',
                    cantidad: l.cantidad || 0,
                    precio_unitario: l.precio_unitario || 0,
                    base: l.base_imponible || 0,
                })),
                base_imponible: factura?.base_imponible_total || 0,
                tipo_iva: factura?.tipo_iva_pct || 0,
                cuota_iva: factura?.cuota_iva || 0,
                retenciones: factura?.retencion_irpf || 0,
                total: factura?.total || 0,
                confianza: uploadResult.validacion?.confianza_extraccion || 'media',
                errores_validacion: uploadResult.validacion?.errores_validacion || [],
            },
            clasificacion: {
                cuenta_pgc: clasificacion?.cuenta_code || '',
                cuenta_pgc_nombre: clasificacion?.cuenta_nombre || '',
                confianza: clasificacion?.confianza || 'media',
                alternativas: (clasificacion?.alternativas || []).map((a: any) => ({
                    cuenta_pgc: a.code || '',
                    cuenta_pgc_nombre: a.nombre || '',
                })),
            },
            confirmada: false,
        }
    }

    async function handleFiles(files: File[]) {
        if (!files.length) return

        if (files.length > MAX_BATCH) {
            setUploadError(
                `Máximo ${MAX_BATCH} facturas a la vez. Has seleccionado ${files.length}.`,
            )
            setUploadStep('error')
            return
        }

        // Validate sizes
        const oversized = files.filter((f) => f.size > 10 * 1024 * 1024)
        if (oversized.length) {
            setUploadError(
                `Estas facturas pesan más de 10 MB: ${oversized.map((f) => f.name).join(', ')}`,
            )
            setUploadStep('error')
            return
        }

        setUploadError(null)
        setResult(null)
        setBatchSummary(null)

        // Single file: keep classic UX (extracting/classifying steps)
        if (files.length === 1) {
            await handleSingleFile(files[0])
            return
        }

        // Batch flow
        const initial: QueueItem[] = files.map((f, i) => ({
            id: `${Date.now()}-${i}`,
            filename: f.name,
            size: f.size,
            status: 'pending',
        }))
        setQueue(initial)
        setUploadStep('extracting')

        try {
            const formData = new FormData()
            files.forEach((f) => formData.append('files', f))
            if (selectedWorkspaceId) formData.append('workspace_id', selectedWorkspaceId)

            // Mark all as processing while server runs (server processes sequentially; we don't get per-file progress)
            setQueue((prev) => prev.map((it) => ({ ...it, status: 'processing' })))

            const batchResult = await apiRequest('/api/invoices/upload-batch', {
                method: 'POST',
                body: formData,
                timeout: 600000,
            })

            // Map results back to queue items by filename order (server preserves order)
            const serverResults: any[] = batchResult?.results || []
            setQueue((prev) =>
                prev.map((it, idx) => {
                    const r = serverResults[idx]
                    if (!r) return { ...it, status: 'error', error: 'Sin respuesta del servidor' }
                    if (r.success) {
                        return { ...it, status: 'success', invoiceId: r.data?.id }
                    }
                    return {
                        ...it,
                        status: 'error',
                        error: typeof r.error === 'string' ? r.error : 'Error procesando',
                    }
                }),
            )

            setBatchSummary({
                success: batchResult?.success_count || 0,
                error: batchResult?.error_count || 0,
            })
            setUploadStep('done')
            await loadInvoices()
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'No hemos podido procesar el lote.'
            setQueue((prev) =>
                prev.map((it) =>
                    it.status === 'processing' ? { ...it, status: 'error', error: msg } : it,
                ),
            )
            setUploadError(msg)
            setUploadStep('error')
        }
    }

    async function handleSingleFile(file: File) {
        setUploadStep('extracting')

        try {
            const formData = new FormData()
            formData.append('file', file)
            if (selectedWorkspaceId) formData.append('workspace_id', selectedWorkspaceId)

            // Step 1: Upload + extract (Gemini OCR can take 30-60s)
            const uploadResult = await apiRequest('/api/invoices/upload', {
                method: 'POST',
                body: formData,
                timeout: 120000,
            })

            setUploadStep('classifying')

            const mapped = mapUploadResultToInvoiceResult(uploadResult)

            setUploadStep('done')
            setResult(mapped)

            await loadInvoices()
        } catch (err: unknown) {
            setUploadStep('error')
            const msg = err instanceof Error ? err.message : 'No hemos podido procesar la factura.'
            setUploadError(msg)
        }
    }

    async function handleReclassify(id: string, cuenta_pgc: string, cuenta_pgc_nombre: string) {
        await apiRequest(`/api/invoices/${id}/reclassify`, {
            method: 'PUT',
            body: JSON.stringify({ cuenta_pgc, cuenta_pgc_nombre }),
        })
    }

    async function handleDelete(id: string) {
        if (!window.confirm('¿Eliminar esta factura? No se puede deshacer.')) return
        try {
            await apiRequest(`/api/invoices/${id}`, { method: 'DELETE' })
            setInvoices((prev) => prev.filter((inv) => inv.id !== id))
            if (result?.id === id) setResult(null)
        } catch {
            alert('No hemos podido eliminar la factura.')
        }
    }

    async function handleView(id: string) {
        try {
            const data = await apiRequest(`/api/invoices/${id}`)
            const inv = data?.invoice
            if (!inv) return

            // Parse raw_extraction if available
            let rawExtraction: any = null
            if (inv.raw_extraction) {
                try {
                    rawExtraction =
                        typeof inv.raw_extraction === 'string'
                            ? JSON.parse(inv.raw_extraction)
                            : inv.raw_extraction
                } catch {
                    /* ignore parse errors */
                }
            }

            const mapped: InvoiceResult = {
                id: inv.id,
                extraccion: {
                    emisor_nombre: rawExtraction?.emisor?.nombre || inv.emisor_nombre || '',
                    emisor_nif: rawExtraction?.emisor?.nif_cif || inv.emisor_nif || '',
                    receptor_nombre: rawExtraction?.receptor?.nombre || inv.receptor_nombre || '',
                    receptor_nif: rawExtraction?.receptor?.nif_cif || inv.receptor_nif || '',
                    fecha: inv.fecha_factura || '',
                    numero_factura: inv.numero_factura || '',
                    lineas: (rawExtraction?.lineas || []).map((l: any) => ({
                        concepto: l.concepto || '',
                        cantidad: l.cantidad || 0,
                        precio_unitario: l.precio_unitario || 0,
                        base: l.base_imponible || l.base || 0,
                    })),
                    base_imponible: inv.base_imponible || 0,
                    tipo_iva: inv.tipo_iva || 0,
                    cuota_iva: inv.cuota_iva || 0,
                    retenciones: inv.retencion_irpf || 0,
                    total: inv.total || 0,
                    confianza: inv.clasificacion_confianza || 'media',
                    errores_validacion: [],
                },
                clasificacion: {
                    cuenta_pgc: inv.cuenta_pgc || '',
                    cuenta_pgc_nombre: inv.cuenta_pgc_nombre || '',
                    confianza: inv.clasificacion_confianza || 'media',
                    alternativas: [],
                },
                confirmada: inv.clasificacion_confianza === 'manual',
            }

            setResult(mapped)
            setUploadStep('done')
            window.scrollTo({ top: 0, behavior: 'smooth' })
        } catch {
            alert('No hemos podido cargar el detalle de la factura.')
        }
    }

    const isProcessing = uploadStep === 'extracting' || uploadStep === 'classifying'
    const isBatchMode = queue.length > 0
    const selectedWorkspace = workspaces.find((w) => w.id === selectedWorkspaceId)

    function resetUpload() {
        setUploadStep('idle')
        setResult(null)
        setUploadError(null)
        setQueue([])
        setBatchSummary(null)
    }

    return (
        <div className="cf-page">
            <div className="cf-page__inner">
                <Link to="/" className="cf-back-link">
                    <ArrowLeft size={16} /> Volver a inicio
                </Link>

                {/* Page header */}
                <div className="cf-page-header">
                    <div className="cf-page-header__icon">
                        <FileText size={28} />
                    </div>
                    <div>
                        <h1 className="cf-page-header__title">Clasificador de facturas</h1>
                        <p className="cf-page-header__subtitle">
                            Sube una factura: leemos los datos, buscamos la cuenta del PGC y dejamos
                            el asiento hecho.
                        </p>
                    </div>
                </div>

                {/* Workspace selector */}
                {workspaces.length > 0 && (
                    <section className="cf-section cf-workspace-picker">
                        <label htmlFor="cf-workspace-select" className="cf-workspace-picker__label">
                            <FolderOpen size={16} />
                            Guardar facturas en
                        </label>
                        <select
                            id="cf-workspace-select"
                            className="cf-workspace-picker__select"
                            value={selectedWorkspaceId}
                            onChange={(e) => setSelectedWorkspaceId(e.target.value)}
                            disabled={
                                isProcessing ||
                                (isBatchMode && uploadStep !== 'done' && uploadStep !== 'error')
                            }
                        >
                            {workspaces.map((w) => (
                                <option key={w.id} value={w.id}>
                                    {w.icon} {w.name}
                                    {w.is_default ? ' (Principal)' : ''}
                                </option>
                            ))}
                        </select>
                        {selectedWorkspace && (
                            <span className="cf-workspace-picker__hint">
                                Las facturas aparecerán también en este workspace.
                            </span>
                        )}
                    </section>
                )}

                {/* Upload section */}
                <section className="cf-section">
                    {!isProcessing && !isBatchMode && uploadStep !== 'done' ? (
                        <UploadZone onFiles={handleFiles} />
                    ) : isProcessing && !isBatchMode ? (
                        <UploadProgress step={uploadStep} />
                    ) : null}

                    {/* Batch queue (multi-file) */}
                    {isBatchMode && <BatchQueue items={queue} />}

                    {uploadStep === 'error' && uploadError && (
                        <div className="cf-alert cf-alert--error">
                            <XCircle size={18} />
                            <span>{uploadError}</span>
                            <button
                                className="cf-btn cf-btn--ghost cf-btn--sm"
                                onClick={resetUpload}
                            >
                                Reintentar
                            </button>
                        </div>
                    )}

                    {uploadStep === 'done' && !isBatchMode && (
                        <div className="cf-upload-done-bar">
                            <CheckCircle size={18} className="cf-upload-done-bar__icon" />
                            <span>Factura guardada</span>
                            <button
                                className="cf-btn cf-btn--ghost cf-btn--sm"
                                onClick={resetUpload}
                            >
                                Subir otra factura
                            </button>
                        </div>
                    )}

                    {uploadStep === 'done' && isBatchMode && batchSummary && (
                        <div className="cf-upload-done-bar">
                            <CheckCircle size={18} className="cf-upload-done-bar__icon" />
                            <span>
                                {batchSummary.success} factura
                                {batchSummary.success === 1 ? '' : 's'} guardada
                                {batchSummary.success === 1 ? '' : 's'}
                                {batchSummary.error > 0 && ` · ${batchSummary.error} con error`}
                            </span>
                            <button
                                className="cf-btn cf-btn--ghost cf-btn--sm"
                                onClick={resetUpload}
                            >
                                Subir más facturas
                            </button>
                        </div>
                    )}
                </section>

                {/* Extraction + Classification results */}
                {result && (
                    <section className="cf-section cf-section--results">
                        <ExtractionCard data={result.extraccion} />
                        <ClassificationCard
                            data={result.clasificacion}
                            invoiceId={result.id}
                            onReclassify={handleReclassify}
                            onConfirm={() => loadInvoices()}
                        />
                    </section>
                )}

                {/* Invoice list */}
                <section className="cf-section">
                    {loadingList ? (
                        <div className="cf-loading">
                            <Loader2 size={24} className="cf-progress__spinner" />
                            <span>Cargando facturas...</span>
                        </div>
                    ) : (
                        <InvoiceList
                            invoices={invoices}
                            onDelete={handleDelete}
                            onView={handleView}
                        />
                    )}
                </section>

                {/* Legal disclaimer */}
                <p className="cf-disclaimer">
                    Información orientativa. No sustituye el asesoramiento de un profesional
                    contable.
                </p>
            </div>
        </div>
    )
}
