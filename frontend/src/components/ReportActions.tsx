import { useState } from 'react'
import { Download, Mail, Loader2, Check } from 'lucide-react'
import { ShareReportModal } from './ShareReportModal'
import { logger } from '../utils/logger'
import './ReportActions.css'

const API_URL = import.meta.env.VITE_API_URL || '/api'

/** Keywords that indicate an IRPF simulation result */
const SIMULATION_KEYWORDS = [
    'cuota íntegra',
    'cuota integra',
    'cuota líquida',
    'cuota liquida',
    'tipo efectivo',
    'base liquidable',
    'simulación irpf',
    'simulacion irpf',
    'simulación del irpf',
    'simulacion del irpf',
]

const CCAA_NAMES: Record<string, string> = {
    'andalucía': 'Andalucía',
    'andalucia': 'Andalucía',
    'aragón': 'Aragón',
    'aragon': 'Aragón',
    'asturias': 'Asturias',
    'baleares': 'Islas Baleares',
    'islas baleares': 'Islas Baleares',
    'canarias': 'Canarias',
    'cantabria': 'Cantabria',
    'castilla-la mancha': 'Castilla-La Mancha',
    'castilla la mancha': 'Castilla-La Mancha',
    'castilla y león': 'Castilla y León',
    'castilla y leon': 'Castilla y León',
    'cataluña': 'Cataluña',
    'catalunya': 'Cataluña',
    'ceuta': 'Ceuta',
    'comunidad valenciana': 'Comunidad Valenciana',
    'valencia': 'Comunidad Valenciana',
    'extremadura': 'Extremadura',
    'galicia': 'Galicia',
    'la rioja': 'La Rioja',
    'madrid': 'Madrid',
    'comunidad de madrid': 'Madrid',
    'melilla': 'Melilla',
    'murcia': 'Murcia',
    'región de murcia': 'Murcia',
    'navarra': 'Navarra',
    'país vasco': 'País Vasco',
    'pais vasco': 'País Vasco',
    'euskadi': 'País Vasco',
}

/**
 * Checks if an assistant message contains IRPF simulation results.
 * Requires at least 2 fiscal keywords to be present.
 */
export function isIRPFSimulation(content: string): boolean {
    const lower = content.toLowerCase()
    const matches = SIMULATION_KEYWORDS.filter(kw => lower.includes(kw))
    return matches.length >= 2
}

/**
 * Extract CCAA from message content by searching for known community names.
 */
function extractCCAA(content: string): string | null {
    const lower = content.toLowerCase()
    // Try longer names first to avoid partial matches
    const sortedKeys = Object.keys(CCAA_NAMES).sort((a, b) => b.length - a.length)
    for (const key of sortedKeys) {
        if (lower.includes(key)) {
            return CCAA_NAMES[key]
        }
    }
    return null
}

/**
 * Extract income amount from message content.
 * Looks for patterns like "30.000 €", "30,000€", "35000 euros", etc.
 */
function extractIncome(content: string): number | null {
    // Pattern: number with dots/commas as thousands separator, near € or euros/EUR
    const patterns = [
        /(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:€|euros?|EUR)/gi,
        /(?:ingresos?|salario|brutos?|anuales?)\s*(?:de\s+)?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)/gi,
        /(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?:€|euros?)?\s*(?:brutos?|anuales?)/gi,
    ]

    for (const pattern of patterns) {
        const matches = [...content.matchAll(pattern)]
        for (const match of matches) {
            const numStr = match[1]
                .replace(/\./g, '')  // Remove thousands dots
                .replace(/,/g, '.')  // Convert decimal comma
            const num = parseFloat(numStr)
            // Income should be a reasonable amount (> 1000 and < 1M)
            if (num > 1000 && num < 1000000) {
                return num
            }
        }
    }
    return null
}

interface FiscalProfileData {
    ccaa_residencia?: string
    situacion_laboral?: string
    edad_contribuyente?: number
    num_descendientes?: number
    num_ascendientes_65?: number
    num_ascendientes_75?: number
    discapacidad_contribuyente?: number
    tributacion_conjunta?: boolean
    tipo_unidad_familiar?: string
    hipoteca_pre2013?: boolean
    capital_amortizado_hipoteca?: number
    intereses_hipoteca?: number
    donativos?: number
    donativo_recurrente?: boolean
    familia_numerosa?: boolean
    tipo_familia_numerosa?: string
    madre_trabajadora_ss?: boolean
    gastos_guarderia_anual?: number
    aportaciones_plan_pensiones?: number
    retenciones_trabajo?: number
    ss_empleado?: number
    ceuta_melilla?: boolean
    ingresos_actividad?: number
    gastos_actividad?: number
    cuota_autonomo_anual?: number
    retenciones_actividad?: number
    pagos_fraccionados_130?: number
    intereses?: number
    dividendos?: number
    ganancias_fondos?: number
    [key: string]: unknown
}

interface ReportActionsProps {
    messageContent: string
    previousUserMessage?: string
    fiscalProfile?: FiscalProfileData
}

export function ReportActions({ messageContent, previousUserMessage, fiscalProfile }: ReportActionsProps) {
    const [downloading, setDownloading] = useState(false)
    const [downloaded, setDownloaded] = useState(false)
    const [reportId, setReportId] = useState<string | null>(null)
    const [showShareModal, setShowShareModal] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleDownloadPDF = async () => {
        setDownloading(true)
        setError(null)

        try {
            // Extract params from message content + user question
            const fullText = `${previousUserMessage || ''} ${messageContent}`
            const ccaa = extractCCAA(fullText) || 'Madrid'
            const income = extractIncome(fullText) || 0
            const currentYear = new Date().getFullYear()

            const token = localStorage.getItem('access_token')
            const fp = fiscalProfile || {}
            const response = await fetch(`${API_URL}/api/export/irpf-report`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token && { 'Authorization': `Bearer ${token}` }),
                },
                body: JSON.stringify({
                    ccaa: fp.ccaa_residencia || ccaa,
                    ingresos_trabajo: income,
                    year: currentYear - 1, // Tax year is previous year
                    retenciones_trabajo: fp.retenciones_trabajo || 0,
                    ss_empleado: fp.ss_empleado || 0,
                    aportaciones_plan_pensiones: fp.aportaciones_plan_pensiones || 0,
                    tributacion_conjunta: fp.tributacion_conjunta || false,
                    tipo_unidad_familiar: fp.tipo_unidad_familiar || 'matrimonio',
                    hipoteca_pre2013: fp.hipoteca_pre2013 || false,
                    capital_amortizado_hipoteca: fp.capital_amortizado_hipoteca || 0,
                    intereses_hipoteca: fp.intereses_hipoteca || 0,
                    donativos: fp.donativos || 0,
                    donativo_recurrente: fp.donativo_recurrente || false,
                    familia_numerosa: fp.familia_numerosa || false,
                    tipo_familia_numerosa: fp.tipo_familia_numerosa || 'general',
                    madre_trabajadora_ss: fp.madre_trabajadora_ss || false,
                    gastos_guarderia_anual: fp.gastos_guarderia_anual || 0,
                    edad_contribuyente: fp.edad_contribuyente || 35,
                    num_descendientes: fp.num_descendientes || 0,
                    num_ascendientes_65: fp.num_ascendientes_65 || 0,
                    num_ascendientes_75: fp.num_ascendientes_75 || 0,
                    discapacidad_contribuyente: fp.discapacidad_contribuyente || 0,
                    ceuta_melilla: fp.ceuta_melilla || false,
                    ingresos_actividad: fp.ingresos_actividad || 0,
                    gastos_actividad: fp.gastos_actividad || 0,
                    cuota_autonomo_anual: fp.cuota_autonomo_anual || 0,
                    retenciones_actividad: fp.retenciones_actividad || 0,
                    pagos_fraccionados_130: fp.pagos_fraccionados_130 || 0,
                    intereses: fp.intereses || 0,
                    dividendos: fp.dividendos || 0,
                    ganancias_fondos: fp.ganancias_fondos || 0,
                    chat_content: messageContent || null,
                }),
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => null)
                throw new Error(errorData?.detail || `Error ${response.status}`)
            }

            // Download the PDF blob
            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.setAttribute('download', `informe_irpf_${currentYear - 1}.pdf`)
            document.body.appendChild(link)
            link.click()
            link.remove()
            window.URL.revokeObjectURL(url)

            // Save report ID for sharing
            const rid = response.headers.get('x-report-id')
            if (rid) setReportId(rid)

            setDownloaded(true)
            logger.debug('PDF downloaded', { reportId: rid })
        } catch (err: any) {
            logger.error('PDF download failed:', err)
            setError(err.message || 'Error al generar el informe')
        } finally {
            setDownloading(false)
        }
    }

    return (
        <div className="report-actions">
            <div className="report-actions-buttons">
                <button
                    className="report-btn report-btn-download"
                    onClick={handleDownloadPDF}
                    disabled={downloading}
                >
                    {downloading ? (
                        <>
                            <Loader2 size={16} className="animate-spin" />
                            <span className="report-btn-text">Generando...</span>
                        </>
                    ) : downloaded ? (
                        <>
                            <Check size={16} />
                            <span className="report-btn-text">Descargado</span>
                        </>
                    ) : (
                        <>
                            <Download size={16} />
                            <span className="report-btn-text">Descargar Informe PDF</span>
                        </>
                    )}
                </button>

                {(downloaded || reportId) && (
                    <button
                        className="report-btn report-btn-share"
                        onClick={() => setShowShareModal(true)}
                    >
                        <Mail size={16} />
                        <span className="report-btn-text">Enviar a mi asesor</span>
                    </button>
                )}
            </div>

            {error && (
                <p className="report-error">{error}</p>
            )}

            {showShareModal && reportId && (
                <ShareReportModal
                    reportId={reportId}
                    onClose={() => setShowShareModal(false)}
                />
            )}
        </div>
    )
}
