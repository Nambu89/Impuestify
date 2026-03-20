import { useState, useMemo } from 'react'
import {
    Info, Euro, AlertTriangle, CheckCircle2, FileText,
    Globe, ChevronDown, ChevronUp, Calculator, Plus, Trash2
} from 'lucide-react'
import Header from '../components/Header'
import './IvaCreatorsPage.css'

// ── Tipos ────────────────────────────────────────────────────────────────────

interface Platform {
    id: string
    name: string
    company: string
    country: string
    flag: string
    eu: boolean
    vatType: 'intracomunitario' | 'importacion'
    modelo349: boolean
    icon: string
    description: string
}

interface PlatformEntry {
    platformId: string
    ingresosMensuales: number
}

// ── Datos de plataformas ─────────────────────────────────────────────────────

const PLATFORMS: Platform[] = [
    {
        id: 'youtube',
        name: 'YouTube',
        company: 'Google Ireland Ltd.',
        country: 'Irlanda',
        flag: '🇮🇪',
        eu: true,
        vatType: 'intracomunitario',
        modelo349: true,
        icon: '▶',
        description: 'AdSense, membresías, Super Thanks y Super Chats',
    },
    {
        id: 'tiktok',
        name: 'TikTok',
        company: 'TikTok Ltd.',
        country: 'Reino Unido',
        flag: '🇬🇧',
        eu: false,
        vatType: 'importacion',
        modelo349: false,
        icon: '♪',
        description: 'Creator Fund, LIVE Gifts y TikTok Shop',
    },
    {
        id: 'twitch',
        name: 'Twitch',
        company: 'Twitch Interactive (Amazon)',
        country: 'EE. UU.',
        flag: '🇺🇸',
        eu: false,
        vatType: 'importacion',
        modelo349: false,
        icon: '◉',
        description: 'Suscripciones, Bits, publicidad directa',
    },
    {
        id: 'instagram',
        name: 'Instagram / Meta',
        company: 'Meta Platforms Ireland Ltd.',
        country: 'Irlanda',
        flag: '🇮🇪',
        eu: true,
        vatType: 'intracomunitario',
        modelo349: true,
        icon: '◈',
        description: 'Branded content, reels bonus, colaboraciones',
    },
    {
        id: 'onlyfans',
        name: 'OnlyFans',
        company: 'Fenix International Ltd.',
        country: 'Reino Unido',
        flag: '🇬🇧',
        eu: false,
        vatType: 'importacion',
        modelo349: false,
        icon: '◎',
        description: 'Suscripciones, propinas y mensajes de pago',
    },
    {
        id: 'spotify',
        name: 'Spotify',
        company: 'Spotify AB',
        country: 'Suecia',
        flag: '🇸🇪',
        eu: true,
        vatType: 'intracomunitario',
        modelo349: true,
        icon: '♫',
        description: 'Royalties por streams de pódcast y música',
    },
    {
        id: 'patreon',
        name: 'Patreon',
        company: 'Patreon Inc.',
        country: 'EE. UU.',
        flag: '🇺🇸',
        eu: false,
        vatType: 'importacion',
        modelo349: false,
        icon: '♥',
        description: 'Membresías de seguidores y contenido exclusivo',
    },
]

const PLATFORM_MAP = Object.fromEntries(PLATFORMS.map(p => [p.id, p]))

const IVA_RATE = 0.21

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatEur(value: number): string {
    return value.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatEurInt(value: number): string {
    return value.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

// ── Subcomponentes ───────────────────────────────────────────────────────────

interface PlatformCardProps {
    platform: Platform
    selected: boolean
    onClick: () => void
}

function PlatformCard({ platform, selected, onClick }: PlatformCardProps) {
    return (
        <button
            className={`ic-platform-card ${selected ? 'ic-platform-card--selected' : ''}`}
            onClick={onClick}
            aria-pressed={selected}
            type="button"
        >
            <div className="ic-platform-icon">{platform.icon}</div>
            <div className="ic-platform-info">
                <span className="ic-platform-name">{platform.name}</span>
                <span className="ic-platform-country">{platform.flag} {platform.country}</span>
            </div>
            {selected && <CheckCircle2 size={18} className="ic-platform-check" />}
        </button>
    )
}

interface VatDetailProps {
    platform: Platform
    open: boolean
    onToggle: () => void
}

function VatDetail({ platform, open, onToggle }: VatDetailProps) {
    const isIntra = platform.vatType === 'intracomunitario'

    return (
        <div className={`ic-vat-detail ${isIntra ? 'ic-vat-detail--intra' : 'ic-vat-detail--import'}`}>
            <button className="ic-vat-header" onClick={onToggle} type="button">
                <div className="ic-vat-header-left">
                    <span className="ic-vat-platform-flag">{platform.flag}</span>
                    <div>
                        <span className="ic-vat-platform-name">{platform.name}</span>
                        <span className="ic-vat-company">{platform.company}</span>
                    </div>
                </div>
                <div className="ic-vat-header-right">
                    <span className={`ic-vat-badge ${isIntra ? 'ic-vat-badge--intra' : 'ic-vat-badge--import'}`}>
                        {isIntra ? 'Intracomunitario' : 'Importación servicios'}
                    </span>
                    {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
            </button>

            {open && (
                <div className="ic-vat-body">
                    <div className="ic-vat-rule-grid">
                        <div className="ic-vat-rule">
                            <span className="ic-vat-rule-label">Operación</span>
                            <span className="ic-vat-rule-value">
                                {isIntra
                                    ? 'Prestación de servicios intracomunitaria (Art. 69 LIVA)'
                                    : 'Importación de servicios de terceros países (Art. 84.Uno.2º LIVA)'}
                            </span>
                        </div>
                        <div className="ic-vat-rule">
                            <span className="ic-vat-rule-label">IVA en tu factura</span>
                            <span className="ic-vat-rule-value ic-vat-rule-value--highlight">
                                0 % — no repercutes IVA al pagador extranjero
                            </span>
                        </div>
                        <div className="ic-vat-rule">
                            <span className="ic-vat-rule-label">Inversión del sujeto pasivo</span>
                            <span className="ic-vat-rule-value">
                                Tú eres quien declara y deduce el 21 % de IVA en el Modelo 303.
                                El importe se anota tanto en «IVA devengado» como en «IVA soportado», por lo que el
                                impacto neto es 0 € si no tienes IVA soportado adicional.
                            </span>
                        </div>
                        <div className="ic-vat-rule">
                            <span className="ic-vat-rule-label">Modelos obligatorios</span>
                            <span className="ic-vat-rule-value">
                                <strong>Modelo 303</strong> (trimestral){platform.modelo349 ? <> + <strong>Modelo 349</strong> (declaración recapitulativa operaciones intracomunitarias)</> : null}
                            </span>
                        </div>
                        {platform.modelo349 && (
                            <div className="ic-vat-rule">
                                <span className="ic-vat-rule-label">NIF-UE (VIES)</span>
                                <span className="ic-vat-rule-value">
                                    Debes estar dado de alta en el ROI (Registro de Operadores Intracomunitarios)
                                    antes de emitir la primera factura.
                                </span>
                            </div>
                        )}
                        <div className="ic-vat-rule">
                            <span className="ic-vat-rule-label">Retención IRPF</span>
                            <span className="ic-vat-rule-value">
                                Las plataformas extranjeras <strong>NO aplican retención IRPF</strong>.
                                Debes autoliquidar el 20 % de IRPF en el Modelo 130 (estimación directa) o
                                incluirlo en tu declaración anual.
                            </span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

// ── Página principal ─────────────────────────────────────────────────────────

export default function IvaCreatorsPage() {
    const [selectedPlatformId, setSelectedPlatformId] = useState<string | null>(null)
    const [entries, setEntries] = useState<PlatformEntry[]>([
        { platformId: '', ingresosMensuales: 0 },
    ])
    const [openDetails, setOpenDetails] = useState<Record<string, boolean>>({})
    const [showExplanation, setShowExplanation] = useState(false)

    // Toggle plataforma seleccionada para detalle informativo
    const handleSelectPlatform = (id: string) => {
        setSelectedPlatformId(prev => (prev === id ? null : id))
    }

    // Gestión de entradas de la calculadora
    const addEntry = () => {
        setEntries(prev => [...prev, { platformId: '', ingresosMensuales: 0 }])
    }

    const removeEntry = (index: number) => {
        setEntries(prev => prev.filter((_, i) => i !== index))
    }

    const updateEntry = (index: number, field: keyof PlatformEntry, value: string | number) => {
        setEntries(prev => prev.map((e, i) => i === index ? { ...e, [field]: value } : e))
    }

    // Cálculos
    const results = useMemo(() => {
        const valid = entries.filter(e => e.platformId && e.ingresosMensuales > 0)

        const byPlatform = valid.map(e => {
            const platform = PLATFORM_MAP[e.platformId]
            const mensual = e.ingresosMensuales
            const ivaBase = mensual * IVA_RATE
            return {
                platform,
                mensual,
                ivaBase,
                ivaTrimestral: ivaBase * 3,
                // En inversión de sujeto pasivo: IVA repercutido = IVA soportado → neto 0
                // Salvo que tengas más IVA soportado de gastos deducibles
                ivaNetoEfectivo: 0,
            }
        })

        const totalMensual = byPlatform.reduce((s, r) => s + r.mensual, 0)
        const totalIvaBase = byPlatform.reduce((s, r) => s + r.ivaBase, 0)
        const totalIvaTrimestral = totalIvaBase * 3
        const tieneIntracomunitarias = byPlatform.some(r => r.platform.vatType === 'intracomunitario')
        const tieneImportacion = byPlatform.some(r => r.platform.vatType === 'importacion')
        const plataformasConModelo349 = byPlatform.filter(r => r.platform.modelo349).map(r => r.platform.name)

        return {
            byPlatform,
            totalMensual,
            totalIvaBase,
            totalIvaTrimestral,
            tieneIntracomunitarias,
            tieneImportacion,
            plataformasConModelo349,
            hasData: valid.length > 0,
        }
    }, [entries])

    const toggleDetail = (id: string) => {
        setOpenDetails(prev => ({ ...prev, [id]: !prev[id] }))
    }

    const selectedPlatform = selectedPlatformId ? PLATFORM_MAP[selectedPlatformId] : null

    // Plataformas únicas seleccionadas en la calculadora (para mostrar detalles)
    const selectedInCalc = useMemo(() => {
        const ids = new Set(entries.filter(e => e.platformId).map(e => e.platformId))
        return PLATFORMS.filter(p => ids.has(p.id))
    }, [entries])

    return (
        <div className="ic-page">
            <Header />

            <main className="ic-main">

                {/* Hero */}
                <div className="ic-hero">
                    <div className="ic-hero-badge">
                        <Globe size={14} />
                        <span>Fiscalidad internacional para creadores</span>
                    </div>
                    <h1 className="ic-title">
                        IVA de tus <span className="ic-title-highlight">plataformas</span>
                    </h1>
                    <p className="ic-subtitle">
                        YouTube, TikTok, Twitch, OnlyFans... cada plataforma tiene un tratamiento
                        fiscal distinto. Calcula el IVA que debes declarar cada trimestre.
                    </p>
                </div>

                <div className="ic-layout">

                    {/* Columna izquierda: selector + calculadora */}
                    <div className="ic-left">

                        {/* Selector de plataforma (informativo) */}
                        <section className="ic-section">
                            <h2 className="ic-section-title">
                                <Calculator size={18} />
                                ¿Con qué plataformas trabajas?
                            </h2>
                            <p className="ic-section-hint">
                                Pulsa una plataforma para ver su tratamiento fiscal detallado.
                            </p>
                            <div className="ic-platform-grid">
                                {PLATFORMS.map(p => (
                                    <PlatformCard
                                        key={p.id}
                                        platform={p}
                                        selected={selectedPlatformId === p.id}
                                        onClick={() => handleSelectPlatform(p.id)}
                                    />
                                ))}
                            </div>
                        </section>

                        {/* Detalle plataforma seleccionada */}
                        {selectedPlatform && (
                            <section className="ic-detail-section">
                                <h3 className="ic-detail-title">
                                    {selectedPlatform.flag} {selectedPlatform.name}
                                    <span className="ic-detail-company">{selectedPlatform.company}</span>
                                </h3>
                                <p className="ic-detail-description">{selectedPlatform.description}</p>

                                <div className="ic-detail-tags">
                                    <span className={`ic-tag ${selectedPlatform.eu ? 'ic-tag--eu' : 'ic-tag--noneu'}`}>
                                        {selectedPlatform.eu ? '🇪🇺 Unión Europea' : '🌍 Fuera de la UE'}
                                    </span>
                                    <span className={`ic-tag ${selectedPlatform.vatType === 'intracomunitario' ? 'ic-tag--intra' : 'ic-tag--import'}`}>
                                        {selectedPlatform.vatType === 'intracomunitario' ? 'Inversión sujeto pasivo (UE)' : 'Inversión sujeto pasivo (3er país)'}
                                    </span>
                                    {selectedPlatform.modelo349 && (
                                        <span className="ic-tag ic-tag--m349">Modelo 349</span>
                                    )}
                                </div>

                                <div className="ic-detail-rules">
                                    <div className="ic-rule">
                                        <span className="ic-rule-icon ic-rule-icon--ok">✓</span>
                                        <div>
                                            <strong>No repercutes IVA</strong> en tu factura a {selectedPlatform.name}.
                                            El tipo aplicable es el 0 % para el pagador extranjero.
                                        </div>
                                    </div>
                                    <div className="ic-rule">
                                        <span className="ic-rule-icon ic-rule-icon--warn">!</span>
                                        <div>
                                            <strong>Sí declaras IVA</strong> mediante la técnica de
                                            «inversión del sujeto pasivo»: anotas el 21 % como IVA devengado
                                            y el mismo importe como IVA soportado en el Modelo 303. El
                                            resultado neto suele ser 0 €, pero la obligación de declarar
                                            existe igualmente.
                                        </div>
                                    </div>
                                    {selectedPlatform.modelo349 && (
                                        <div className="ic-rule">
                                            <span className="ic-rule-icon ic-rule-icon--info">i</span>
                                            <div>
                                                Al ser empresa de la UE, debes presentar el
                                                <strong> Modelo 349</strong> trimestralmente e inscribirte
                                                en el <strong>ROI (Registro de Operadores Intracomunitarios)</strong>
                                                {' '}antes de la primera factura.
                                            </div>
                                        </div>
                                    )}
                                    <div className="ic-rule">
                                        <span className="ic-rule-icon ic-rule-icon--alert">€</span>
                                        <div>
                                            <strong>IRPF sin retención:</strong> {selectedPlatform.name} no
                                            practica retención en origen. Debes provisionar el IRPF tú mismo
                                            (modelo 130 o renta anual).
                                        </div>
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Calculadora trimestral */}
                        <section className="ic-section">
                            <h2 className="ic-section-title">
                                <Euro size={18} />
                                Calculadora trimestral
                            </h2>
                            <p className="ic-section-hint">
                                Introduce tus ingresos mensuales por plataforma para calcular el IVA
                                que debes declarar en el Modelo 303 cada trimestre.
                            </p>

                            <div className="ic-entries">
                                {entries.map((entry, idx) => (
                                    <div key={idx} className="ic-entry-row">
                                        <select
                                            className="ic-select"
                                            value={entry.platformId}
                                            onChange={e => updateEntry(idx, 'platformId', e.target.value)}
                                            aria-label="Plataforma"
                                        >
                                            <option value="">— Selecciona plataforma —</option>
                                            {PLATFORMS.map(p => (
                                                <option key={p.id} value={p.id}>
                                                    {p.flag} {p.name}
                                                </option>
                                            ))}
                                        </select>

                                        <div className="ic-amount-wrap">
                                            <Euro size={16} className="ic-amount-icon" />
                                            <input
                                                type="number"
                                                className="ic-amount-input"
                                                placeholder="0"
                                                min={0}
                                                step={100}
                                                value={entry.ingresosMensuales || ''}
                                                onChange={e => updateEntry(idx, 'ingresosMensuales', parseFloat(e.target.value) || 0)}
                                                aria-label="Ingresos mensuales"
                                            />
                                            <span className="ic-amount-suffix">€/mes</span>
                                        </div>

                                        {entries.length > 1 && (
                                            <button
                                                className="ic-remove-btn"
                                                onClick={() => removeEntry(idx)}
                                                aria-label="Eliminar plataforma"
                                                type="button"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        )}
                                    </div>
                                ))}
                            </div>

                            <button className="ic-add-btn" onClick={addEntry} type="button">
                                <Plus size={16} /> Añadir plataforma
                            </button>
                        </section>

                        {/* Disclaimer */}
                        <div className="ic-disclaimer">
                            <Info size={14} />
                            <span>
                                Cálculo orientativo. La inversión del sujeto pasivo puede tener
                                matices según tu actividad, régimen de IVA (general, simplificado,
                                recargo de equivalencia) y gastos deducibles. Consulta con un asesor
                                fiscal para tu situación concreta.
                            </span>
                        </div>
                    </div>

                    {/* Columna derecha: resultados */}
                    {results.hasData && (
                        <div className="ic-right" aria-live="polite">

                            {/* Resumen total */}
                            <div className="ic-total-card">
                                <div className="ic-total-label">
                                    <CheckCircle2 size={18} />
                                    Base imponible total al mes
                                </div>
                                <div className="ic-total-amount">
                                    {formatEurInt(results.totalMensual)}
                                    <span className="ic-total-currency">EUR</span>
                                </div>
                                <div className="ic-total-sub">
                                    {formatEurInt(results.totalMensual * 3)} EUR en el trimestre
                                </div>
                            </div>

                            {/* IVA a declarar en 303 */}
                            <div className="ic-iva-card">
                                <h3 className="ic-iva-card-title">IVA — Modelo 303 (trimestral)</h3>

                                <div className="ic-iva-row">
                                    <span className="ic-iva-row-label">IVA devengado (21 % inversión sujeto pasivo)</span>
                                    <span className="ic-iva-row-amount ic-iva-row-amount--devenged">
                                        {formatEur(results.totalIvaTrimestral)} €
                                    </span>
                                </div>
                                <div className="ic-iva-row">
                                    <span className="ic-iva-row-label">IVA soportado (misma inversión, deducible)</span>
                                    <span className="ic-iva-row-amount ic-iva-row-amount--supported">
                                        − {formatEur(results.totalIvaTrimestral)} €
                                    </span>
                                </div>
                                <div className="ic-iva-divider" />
                                <div className="ic-iva-row ic-iva-row--total">
                                    <span className="ic-iva-row-label">
                                        <strong>IVA neto a ingresar (solo por inversión)</strong>
                                    </span>
                                    <span className="ic-iva-row-amount ic-iva-row-amount--zero">
                                        0,00 €
                                    </span>
                                </div>
                                <p className="ic-iva-note">
                                    Si tienes <strong>IVA soportado de gastos</strong> (hosting, equipos,
                                    software...), ese importe adicional <em>sí reduce</em> tu cuota a
                                    ingresar. Inclúyelo en el Modelo 303 casilla de IVA deducible.
                                </p>
                            </div>

                            {/* Desglose por plataforma */}
                            <div className="ic-breakdown-card">
                                <h3 className="ic-breakdown-title">Desglose por plataforma</h3>
                                {results.byPlatform.map((r, i) => (
                                    <div key={i} className="ic-breakdown-row">
                                        <div className="ic-breakdown-row-header">
                                            <span className="ic-breakdown-flag">{r.platform.flag}</span>
                                            <span className="ic-breakdown-platform">{r.platform.name}</span>
                                            <span className={`ic-breakdown-type ${r.platform.vatType === 'intracomunitario' ? 'ic-breakdown-type--intra' : 'ic-breakdown-type--import'}`}>
                                                {r.platform.vatType === 'intracomunitario' ? 'UE' : 'No UE'}
                                            </span>
                                        </div>
                                        <div className="ic-breakdown-row-nums">
                                            <span className="ic-breakdown-num-label">Ingresos mes</span>
                                            <span className="ic-breakdown-num">{formatEur(r.mensual)} €</span>
                                            <span className="ic-breakdown-num-label">Base IVA trimestre</span>
                                            <span className="ic-breakdown-num">{formatEur(r.mensual * 3)} €</span>
                                            <span className="ic-breakdown-num-label">IVA devengado/deducible</span>
                                            <span className="ic-breakdown-num ic-breakdown-neutral">{formatEur(r.ivaTrimestral)} €</span>
                                        </div>
                                        <div className="ic-breakdown-track">
                                            <div
                                                className="ic-breakdown-fill"
                                                style={{ width: `${Math.min((r.mensual / results.totalMensual) * 100, 100)}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Obligaciones adicionales */}
                            <div className="ic-obligations-card">
                                <h3 className="ic-obligations-title">
                                    <FileText size={16} />
                                    Obligaciones adicionales
                                </h3>
                                <ul className="ic-obligations-list">
                                    <li className="ic-obligation ic-obligation--required">
                                        <CheckCircle2 size={15} />
                                        <span>
                                            <strong>Modelo 303</strong> — Trimestral (abril, julio,
                                            octubre, enero). Obligatorio aunque el resultado sea 0 €.
                                        </span>
                                    </li>
                                    {results.plataformasConModelo349.length > 0 && (
                                        <li className="ic-obligation ic-obligation--required">
                                            <CheckCircle2 size={15} />
                                            <span>
                                                <strong>Modelo 349</strong> — Por operaciones con{' '}
                                                {results.plataformasConModelo349.join(', ')}.
                                                Trimestral si superas 50.000 EUR de operaciones
                                                intracomunitarias.
                                            </span>
                                        </li>
                                    )}
                                    {results.plataformasConModelo349.length > 0 && (
                                        <li className="ic-obligation ic-obligation--info">
                                            <Info size={15} />
                                            <span>
                                                <strong>ROI (Registro Operadores Intracomunitarios)</strong> —
                                                Solicita el alta en la AEAT antes de facturar a empresas UE.
                                                Se tramita con el Modelo 036.
                                            </span>
                                        </li>
                                    )}
                                    <li className="ic-obligation ic-obligation--warn">
                                        <AlertTriangle size={15} />
                                        <span>
                                            <strong>Modelo 130</strong> — Pago fraccionado IRPF
                                            trimestral. Las plataformas no retienen: debes ingresarlo tú.
                                        </span>
                                    </li>
                                </ul>
                            </div>

                            {/* Detalle técnico por plataforma (acordeón) */}
                            {selectedInCalc.length > 0 && (
                                <div className="ic-tech-section">
                                    <button
                                        className="ic-tech-toggle"
                                        onClick={() => setShowExplanation(o => !o)}
                                        type="button"
                                    >
                                        <span>Explicación técnica por plataforma</span>
                                        {showExplanation ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                    </button>
                                    {showExplanation && (
                                        <div className="ic-tech-body">
                                            {selectedInCalc.map(p => (
                                                <VatDetail
                                                    key={p.id}
                                                    platform={p}
                                                    open={!!openDetails[p.id]}
                                                    onToggle={() => toggleDetail(p.id)}
                                                />
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Estado vacío */}
                    {!results.hasData && (
                        <div className="ic-empty">
                            <div className="ic-empty-icon">
                                <Calculator size={48} />
                            </div>
                            <p className="ic-empty-title">Selecciona una plataforma e introduce tus ingresos</p>
                            <p className="ic-empty-sub">
                                Verás aquí el IVA a declarar, los modelos obligatorios y
                                una guía paso a paso de lo que debes hacer.
                            </p>
                        </div>
                    )}
                </div>

                {/* Sección educativa — qué es la inversión del sujeto pasivo */}
                <section className="ic-edu-section">
                    <h2 className="ic-edu-title">¿Qué es la inversión del sujeto pasivo?</h2>
                    <div className="ic-edu-grid">
                        <div className="ic-edu-card">
                            <div className="ic-edu-card-num">01</div>
                            <h3>Facturas sin IVA al extranjero</h3>
                            <p>
                                Cuando facturas a YouTube (Irlanda), TikTok (UK) o Twitch (EE. UU.),
                                <strong> no incluyes IVA en la factura</strong>. El tipo aplicado al
                                pagador es 0 %.
                            </p>
                        </div>
                        <div className="ic-edu-card">
                            <div className="ic-edu-card-num">02</div>
                            <h3>Tú asumes el rol de «recaudador»</h3>
                            <p>
                                La AEAT considera que, al recibir el servicio, el pagador extranjero
                                «invierte» la obligación: <strong>tú declaras y deduces</strong> el
                                21 % de IVA como si lo hubieras cobrado y pagado al mismo tiempo.
                            </p>
                        </div>
                        <div className="ic-edu-card">
                            <div className="ic-edu-card-num">03</div>
                            <h3>Resultado neto: 0 €... normalmente</h3>
                            <p>
                                En el Modelo 303 el IVA devengado (lo que «cobras») y el IVA
                                soportado (lo que «pagas») se compensan. El neto es 0 €, pero la
                                <strong> obligación de declarar existe igualmente</strong>.
                            </p>
                        </div>
                        <div className="ic-edu-card">
                            <div className="ic-edu-card-num">04</div>
                            <h3>El IVA de tus gastos sí cuenta</h3>
                            <p>
                                Si tienes IVA soportado de gastos reales (cámara, micrófono, software,
                                hosting...), ese importe <strong>reduce la cuota final</strong> que
                                pagas a Hacienda. Guarda todas las facturas.
                            </p>
                        </div>
                    </div>
                </section>

            </main>
        </div>
    )
}
