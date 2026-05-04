import { useState, useEffect, useCallback, useMemo } from 'react'
import { ChevronDown, ChevronUp, TrendingDown, Info, Euro, Percent, Minus, CheckCircle2, AlertTriangle, MapPin } from 'lucide-react'
import Header from '../components/Header'
import { useNetSalary, type NetSalaryInput, type RegimenFiscal } from '../hooks/useNetSalary'
import { useSEO } from '../hooks/useSEO'
import { CCAA_OPTIONS_WITH_PLACEHOLDER } from '../constants/ccaa'
import './NetSalaryPage.css'

const IVA_OPTIONS = [
    { label: '21%', value: 21 },
    { label: '10%', value: 10 },
    { label: '4%', value: 4 },
    { label: '0%', value: 0 },
]

const IGIC_OPTIONS = [
    { label: '7%', value: 7 },
    { label: '3%', value: 3 },
    { label: '0%', value: 0 },
    { label: '9,5%', value: 9.5 },
    { label: '13,5%', value: 13.5 },
]

const IPSI_OPTIONS = [
    { label: '4%', value: 4 },
    { label: '0,5%', value: 0.5 },
    { label: '1%', value: 1 },
    { label: '2,5%', value: 2.5 },
    { label: '5%', value: 5 },
    { label: '10%', value: 10 },
]

const DEFAULT_INPUT: NetSalaryInput = {
    facturacion_bruta_mensual: 0,
    tipo_iva: null,
    retencion_irpf: 15,
    cuota_autonomo_mensual: 293,
    gastos_deducibles_mensual: 0,
    es_nuevo_autonomo: false,
    tarifa_plana: false,
    comunidad_autonoma: '',
}

const FORAL_CCAA = new Set(['Araba', 'Bizkaia', 'Gipuzkoa', 'Navarra'])
const CANARIAS_CCAA = new Set(['Canarias'])
const CEUTA_MELILLA_CCAA = new Set(['Ceuta', 'Melilla'])

function deriveRegime(ccaa: string): RegimenFiscal {
    if (FORAL_CCAA.has(ccaa)) return ccaa === 'Navarra' ? 'foral_navarra' : 'foral_vasco'
    if (CANARIAS_CCAA.has(ccaa)) return 'canarias'
    if (CEUTA_MELILLA_CCAA.has(ccaa)) return 'ceuta_melilla'
    return 'comun'
}

function regimeLabel(r: RegimenFiscal): string {
    switch (r) {
        case 'foral_vasco': return 'Régimen foral vasco'
        case 'foral_navarra': return 'Régimen foral Navarra'
        case 'ceuta_melilla': return 'Ceuta / Melilla (con deducción 60%)'
        case 'canarias': return 'Canarias (IGIC)'
        default: return 'Régimen común'
    }
}

function formatEur(value: number): string {
    return value.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function formatPct(value: number): string {
    return value.toLocaleString('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

interface BreakdownBarProps {
    label: string
    amount: number
    pct: number
    colorClass: string
    isBase?: boolean
}

function BreakdownBar({ label, amount, pct, colorClass, isBase }: BreakdownBarProps) {
    const sign = isBase ? '' : '-'
    return (
        <div className="ns-breakdown-row">
            <div className="ns-breakdown-meta">
                <span className="ns-breakdown-label">{label}</span>
                <span className={`ns-breakdown-amount ${colorClass}`}>
                    {sign}{formatEur(Math.abs(amount))} EUR
                </span>
                <span className="ns-breakdown-pct">{formatPct(pct)}%</span>
            </div>
            <div className="ns-breakdown-track">
                <div
                    className={`ns-breakdown-fill ${colorClass}`}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                />
            </div>
        </div>
    )
}

export default function NetSalaryPage() {
    useSEO({
        title: 'Calculadora de sueldo neto para autónomos — Impuestify',
        description: 'Calcula lo que te queda en la mano tras IRPF, IVA o IGIC y cuota de autónomos. Soporta régimen común, Canarias, Ceuta, Melilla y País Vasco.',
        canonical: '/calculadora-neto',
        keywords: 'calculadora neto autónomo 2026, sueldo neto autónomo, cuota autónomo, IRPF autónomo, IVA autónomo',
        schema: [
            {
                '@context': 'https://schema.org',
                '@type': 'WebApplication',
                name: 'Calculadora Sueldo Neto Autónomo 2026',
                url: 'https://impuestify.com/calculadora-neto',
                applicationCategory: 'FinanceApplication',
                operatingSystem: 'Web',
                offers: { '@type': 'Offer', price: '0', priceCurrency: 'EUR' },
                author: { '@type': 'Organization', name: 'Impuestify', url: 'https://impuestify.com' }
            },
            {
                '@context': 'https://schema.org',
                '@type': 'BreadcrumbList',
                itemListElement: [
                    { '@type': 'ListItem', position: 1, name: 'Inicio', item: 'https://impuestify.com' },
                    { '@type': 'ListItem', position: 2, name: 'Calculadora Sueldo Neto Autónomo', item: 'https://impuestify.com/calculadora-neto' }
                ]
            }
        ]
    })

    const [input, setInput] = useState<NetSalaryInput>(DEFAULT_INPUT)
    const [advancedOpen, setAdvancedOpen] = useState(false)
    const { result, loading, error, calculate } = useNetSalary()

    const ccaa = input.comunidad_autonoma || ''
    const regime = useMemo<RegimenFiscal>(() => deriveRegime(ccaa), [ccaa])
    const indirectOptions = regime === 'canarias' ? IGIC_OPTIONS : regime === 'ceuta_melilla' ? IPSI_OPTIONS : IVA_OPTIONS
    const indirectName = regime === 'canarias' ? 'IGIC' : regime === 'ceuta_melilla' ? 'IPSI' : 'IVA'

    const handleFacChange = useCallback((raw: string) => {
        const val = parseFloat(raw.replace(',', '.')) || 0
        setInput(prev => ({ ...prev, facturacion_bruta_mensual: val }))
    }, [])

    const handleCcaaChange = useCallback((value: string) => {
        const newRegime = deriveRegime(value)
        setInput(prev => ({
            ...prev,
            comunidad_autonoma: value,
            // Reset tipo_iva when switching regime so backend auto-detects the right rate
            tipo_iva: newRegime === deriveRegime(prev.comunidad_autonoma || '') ? prev.tipo_iva : null,
        }))
    }, [])

    const handleNuevoAutonomo = useCallback((checked: boolean) => {
        setInput(prev => ({
            ...prev,
            es_nuevo_autonomo: checked,
            retencion_irpf: checked ? 7 : 15,
        }))
    }, [])

    const handleTarifaPlana = useCallback((checked: boolean) => {
        setInput(prev => ({
            ...prev,
            tarifa_plana: checked,
        }))
    }, [])

    useEffect(() => {
        calculate(input)
    }, [input, calculate])

    const bruto = input.facturacion_bruta_mensual
    const hasResult = result && result.success && bruto > 0
    const showResult = hasResult || (bruto > 0 && loading)

    return (
        <div className="ns-page">
            <Header />

            <main className="ns-main">
                {/* Hero */}
                <div className="ns-hero">
                    <h1 className="ns-title">
                        <span className="ns-title-highlight">¿Cuánto te queda</span> limpio?
                    </h1>
                    <p className="ns-subtitle">
                        Tu sueldo neto real de autónomo, calculado con la cuota que te toca este año.
                    </p>
                </div>

                {/* Layout: columna unica mobile, dos columnas desktop */}
                <div className={`ns-layout ${showResult ? 'ns-layout--split' : ''}`}>

                    {/* Panel izquierdo: inputs */}
                    <section className="ns-inputs-panel">

                        {/* CCAA selector */}
                        <div className="ns-field">
                            <label className="ns-label" htmlFor="ccaa">
                                <MapPin size={14} /> Comunidad autónoma
                            </label>
                            <select
                                id="ccaa"
                                className="ns-input ns-select"
                                value={ccaa}
                                onChange={e => handleCcaaChange(e.target.value)}
                            >
                                {CCAA_OPTIONS_WITH_PLACEHOLDER.map(opt => (
                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                ))}
                            </select>
                            {ccaa && (
                                <p className="ns-field-hint ns-field-hint--info">
                                    {regimeLabel(regime)} · Impuesto indirecto: <strong>{indirectName}</strong>
                                    {regime === 'foral_vasco' && ' · escala foral 7 tramos (marginal 49%)'}
                                    {regime === 'foral_navarra' && ' · escala foral 11 tramos (marginal 52,8%)'}
                                    {regime === 'ceuta_melilla' && ' · deducción 60% sobre cuota IRPF'}
                                </p>
                            )}
                            {!ccaa && (
                                <p className="ns-field-hint">
                                    Selecciona tu CCAA para aplicar el IRPF correcto (común, foral, Canarias o Ceuta/Melilla).
                                </p>
                            )}
                        </div>

                        {/* Input principal */}
                        <div className="ns-main-input-wrap">
                            <label className="ns-main-label" htmlFor="facturacion">
                                Facturación mensual bruta
                            </label>
                            <div className="ns-main-input-row">
                                <Euro size={24} className="ns-euro-icon" />
                                <input
                                    id="facturacion"
                                    type="number"
                                    className="ns-main-input"
                                    placeholder="3.000"
                                    min={0}
                                    step={100}
                                    value={bruto || ''}
                                    onChange={e => handleFacChange(e.target.value)}
                                    autoFocus
                                />
                                <span className="ns-eur-suffix">EUR / mes</span>
                            </div>
                            {bruto > 0 && (
                                <p className="ns-main-hint">
                                    {formatEur(bruto * 12)} EUR al año antes de impuestos
                                </p>
                            )}
                        </div>

                        {/* Opciones avanzadas */}
                        <div className="ns-advanced">
                            <button
                                className="ns-advanced-toggle"
                                onClick={() => setAdvancedOpen(o => !o)}
                                aria-expanded={advancedOpen}
                            >
                                <span>Opciones avanzadas</span>
                                {advancedOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                            </button>

                            {advancedOpen && (
                                <div className="ns-advanced-body">

                                    {/* Tipo impuesto indirecto (IVA / IGIC / IPSI) */}
                                    <div className="ns-field">
                                        <label className="ns-label">Tipo de {indirectName}</label>
                                        <div className="ns-radio-group">
                                            <button
                                                className={`ns-radio-btn ${input.tipo_iva === null ? 'ns-radio-btn--active' : ''}`}
                                                onClick={() => setInput(prev => ({ ...prev, tipo_iva: null }))}
                                                title="Aplicar tipo general según régimen"
                                            >
                                                Auto
                                            </button>
                                            {indirectOptions.map(opt => (
                                                <button
                                                    key={opt.value}
                                                    className={`ns-radio-btn ${input.tipo_iva === opt.value ? 'ns-radio-btn--active' : ''}`}
                                                    onClick={() => setInput(prev => ({ ...prev, tipo_iva: opt.value }))}
                                                >
                                                    {opt.label}
                                                </button>
                                            ))}
                                        </div>
                                        <p className="ns-field-hint">
                                            {indirectName === 'IVA' && 'General 21% | Reducido 10% | Superreducido 4% | Exento 0%'}
                                            {indirectName === 'IGIC' && 'Canarias — General 7% | Reducido 3% | Cero 0% | Incrementado 9,5% | Especial 13,5%'}
                                            {indirectName === 'IPSI' && 'Ceuta/Melilla — Servicios 4% (general) | Bienes 0,5% a 10% según producto'}
                                        </p>
                                    </div>

                                    {/* Retencion IRPF */}
                                    <div className="ns-field">
                                        <div className="ns-label-row">
                                            <label className="ns-label">
                                                <Percent size={14} /> Retención IRPF en facturas
                                            </label>
                                            <label className="ns-toggle-label">
                                                <input
                                                    type="checkbox"
                                                    className="ns-toggle-input"
                                                    checked={input.es_nuevo_autonomo}
                                                    onChange={e => handleNuevoAutonomo(e.target.checked)}
                                                />
                                                <span className="ns-toggle-track" />
                                                <span className="ns-toggle-text">Soy nuevo autónomo (7%)</span>
                                            </label>
                                        </div>
                                        <div className="ns-radio-group">
                                            {[7, 15].map(v => (
                                                <button
                                                    key={v}
                                                    className={`ns-radio-btn ${input.retencion_irpf === v ? 'ns-radio-btn--active' : ''}`}
                                                    onClick={() => setInput(prev => ({ ...prev, retencion_irpf: v, es_nuevo_autonomo: v === 7 }))}
                                                >
                                                    {v}%
                                                </button>
                                            ))}
                                            <button
                                                className={`ns-radio-btn ${![7, 15].includes(input.retencion_irpf) ? 'ns-radio-btn--active' : ''}`}
                                                onClick={() => setInput(prev => ({ ...prev, retencion_irpf: 20, es_nuevo_autonomo: false }))}
                                            >
                                                20%
                                            </button>
                                        </div>
                                    </div>

                                    {/* Tarifa plana */}
                                    <div className="ns-field">
                                        <label className="ns-toggle-label">
                                            <input
                                                type="checkbox"
                                                className="ns-toggle-input"
                                                checked={input.tarifa_plana}
                                                onChange={e => handleTarifaPlana(e.target.checked)}
                                            />
                                            <span className="ns-toggle-track" />
                                            <span className="ns-toggle-text">Tarifa plana de nuevo autónomo (80 EUR/mes)</span>
                                        </label>
                                        {input.tarifa_plana && (
                                            <p className="ns-field-hint ns-field-hint--info">
                                                Cuota fija de 80 EUR/mes durante 12 meses, ampliable a 24 si tus ingresos netos son inferiores al SMI.
                                                Requisitos: no haber sido autónomo en los 2 años anteriores y no ser autónomo societario (RDL 13/2022).
                                            </p>
                                        )}
                                    </div>

                                    {/* Cuota autonomo */}
                                    <div className="ns-field">
                                        <label className="ns-label" htmlFor="cuota">
                                            Cuota de autónomo mensual (EUR)
                                        </label>
                                        <input
                                            id="cuota"
                                            type="number"
                                            className="ns-input"
                                            min={0}
                                            step={10}
                                            value={input.tarifa_plana ? 80 : input.cuota_autonomo_mensual}
                                            disabled={input.tarifa_plana}
                                            onChange={e => setInput(prev => ({ ...prev, cuota_autonomo_mensual: parseFloat(e.target.value) || 0 }))}
                                        />
                                        <p className="ns-field-hint">
                                            {input.tarifa_plana
                                                ? 'Cuota fija por tarifa plana — DA 52ª LGSS'
                                                : 'Base mínima 2025: 230,15 EUR | Base media: 293 EUR'}
                                        </p>
                                    </div>

                                    {/* Gastos deducibles */}
                                    <div className="ns-field">
                                        <label className="ns-label" htmlFor="gastos">
                                            Gastos deducibles mensuales (EUR)
                                        </label>
                                        <input
                                            id="gastos"
                                            type="number"
                                            className="ns-input"
                                            min={0}
                                            step={50}
                                            value={input.gastos_deducibles_mensual}
                                            onChange={e => setInput(prev => ({ ...prev, gastos_deducibles_mensual: parseFloat(e.target.value) || 0 }))}
                                        />
                                        <p className="ns-field-hint">Material, suministros, vehículo, formación, etc.</p>
                                    </div>

                                </div>
                            )}
                        </div>

                        {/* Disclaimer */}
                        <div className="ns-disclaimer">
                            <Info size={14} />
                            <span>
                                Estimación orientativa sobre IRPF general. Para el cálculo exacto con tu CCAA y deducciones,
                                usa la <a href="/guia-fiscal" className="ns-link">Guía Fiscal</a>.
                            </span>
                        </div>
                    </section>

                    {/* Panel derecho: resultado */}
                    {showResult && (
                        <section className="ns-result-panel" aria-live="polite">
                            {loading && !result && (
                                <div className="ns-loading">
                                    <div className="ns-spinner" />
                                    <span>Calculando...</span>
                                </div>
                            )}

                            {error && (
                                <div className="ns-error">
                                    <TrendingDown size={20} />
                                    <span>{error}</span>
                                </div>
                            )}

                            {hasResult && result && (
                                <>
                                    {/* Card principal — neto fiscal real (después de IRPF) */}
                                    <div className="ns-net-card">
                                        <div className="ns-net-label">
                                            <CheckCircle2 size={20} />
                                            Tu neto real al mes
                                        </div>
                                        <div className="ns-net-amount">
                                            {formatEur(result.neto_anual / 12)}
                                            <span className="ns-net-currency">EUR</span>
                                        </div>
                                        <div className="ns-net-annual">
                                            {formatEur(result.neto_anual)} EUR al año (tras IRPF, SS y gastos)
                                        </div>
                                        <div className="ns-net-pct">
                                            {formatPct(result.porcentaje_neto)}% de tu facturación bruta
                                        </div>
                                    </div>

                                    {/* Régimen aplicado + impuesto indirecto + deducción C/M */}
                                    {result.regimen_fiscal && (
                                        <div className="ns-regime-chips">
                                            <span className={`ns-chip ns-chip--regime ns-chip--${result.regimen_fiscal}`}>
                                                <MapPin size={12} />
                                                {regimeLabel(result.regimen_fiscal)}
                                            </span>
                                            {result.impuesto_indirecto && (
                                                <span className="ns-chip ns-chip--indirect">
                                                    {result.impuesto_indirecto} {formatPct(result.tipo_impuesto_indirecto || 0)}%
                                                </span>
                                            )}
                                            {result.deduccion_ceuta_melilla && result.deduccion_ceuta_melilla > 0 && (
                                                <span className="ns-chip ns-chip--deduction">
                                                    Deducción 60%: -{formatEur(result.deduccion_ceuta_melilla)} EUR/año
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {/* Warning: reserva mensual si retenciones no cubren IRPF */}
                                    {result.ahorro_retencion_vs_irpf < 0 && (
                                        <div className="ns-reserve-warning">
                                            <AlertTriangle size={16} />
                                            <span>
                                                Reserva <strong>{formatEur(Math.abs(result.ahorro_retencion_vs_irpf) / 12)} EUR/mes</strong> para
                                                la declaración de la renta — tus retenciones no cubren el IRPF estimado.
                                            </span>
                                        </div>
                                    )}

                                    {/* Desglose */}
                                    <div className="ns-breakdown-card">
                                        <h3 className="ns-breakdown-title">Desglose mensual</h3>

                                        <BreakdownBar
                                            label="Facturación bruta"
                                            amount={result.facturacion_bruta}
                                            pct={100}
                                            colorClass="ns-color-base"
                                            isBase
                                        />
                                        {result.iva_a_pagar_hacienda > 0 && (
                                            <BreakdownBar
                                                label={`${result.impuesto_indirecto || 'IVA'} neto a Hacienda (${formatPct(result.tipo_impuesto_indirecto ?? input.tipo_iva ?? 21)}%)`}
                                                amount={result.iva_a_pagar_hacienda}
                                                pct={(result.iva_a_pagar_hacienda / result.facturacion_bruta) * 100}
                                                colorClass="ns-color-iva"
                                            />
                                        )}
                                        <BreakdownBar
                                            label={`IRPF estimado (~${formatPct(result.tipo_irpf_efectivo)}% efectivo)`}
                                            amount={result.irpf_estimado_anual / 12}
                                            pct={(result.irpf_estimado_anual / 12 / result.facturacion_bruta) * 100}
                                            colorClass="ns-color-irpf"
                                        />
                                        <BreakdownBar
                                            label="Cuota de autónomo (RETA)"
                                            amount={result.cuota_autonomo}
                                            pct={(result.cuota_autonomo / result.facturacion_bruta) * 100}
                                            colorClass="ns-color-cuota"
                                        />
                                        {result.gastos_deducibles > 0 && (
                                            <BreakdownBar
                                                label="Gastos deducibles"
                                                amount={result.gastos_deducibles}
                                                pct={(result.gastos_deducibles / result.facturacion_bruta) * 100}
                                                colorClass="ns-color-gastos"
                                            />
                                        )}

                                        {/* Separador neto */}
                                        <div className="ns-breakdown-divider">
                                            <Minus size={14} />
                                        </div>

                                        <BreakdownBar
                                            label="NETO fiscal real"
                                            amount={result.neto_anual / 12}
                                            pct={result.porcentaje_neto}
                                            colorClass="ns-color-neto"
                                            isBase
                                        />
                                    </div>

                                    {/* Info card retenciones */}
                                    {result.ahorro_retencion_vs_irpf !== 0 && (
                                        <div className={`ns-info-card ${result.ahorro_retencion_vs_irpf > 0 ? 'ns-info-card--devolucion' : 'ns-info-card--pago'}`}>
                                            <Info size={16} />
                                            <div>
                                                <p>
                                                    Hacienda te retiene{' '}
                                                    <strong>{formatEur(result.retencion_irpf_factura * 12)} EUR al año</strong>{' '}
                                                    a través de las retenciones de tus facturas, pero tu IRPF real estimado es{' '}
                                                    <strong>{formatEur(result.irpf_estimado_anual)} EUR</strong>.
                                                </p>
                                                {result.ahorro_retencion_vs_irpf > 0 ? (
                                                    <p className="ns-info-highlight ns-info-highlight--green">
                                                        Te devolverían aprox. {formatEur(result.ahorro_retencion_vs_irpf)} EUR
                                                        en la declaración de la renta.
                                                    </p>
                                                ) : (
                                                    <p className="ns-info-highlight ns-info-highlight--red">
                                                        Tendrías que pagar aprox. {formatEur(Math.abs(result.ahorro_retencion_vs_irpf))} EUR
                                                        adicionales en la declaración de la renta.
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                        </section>
                    )}
                </div>
            </main>
        </div>
    )
}
