import { useState, useCallback } from 'react'
import { ClipboardList, Calendar, ExternalLink, AlertTriangle, FileText } from 'lucide-react'
import Header from '../components/Header'
import { CCAA_OPTIONS_WITH_PLACEHOLDER } from '../constants/ccaa'
import './ModelObligationsPage.css'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface DeadlineItem {
    description: string
    date: string
    period: string
}

interface ModelItem {
    modelo: string
    nombre: string
    descripcion: string
    periodicidad: string
    aplica_si: string
    obligatorio: boolean
    organismo: string
    notas: string | null
    deadlines: DeadlineItem[]
}

interface ObligationsResponse {
    success: boolean
    ccaa: string
    situacion_laboral: string
    total_modelos: number
    modelos: ModelItem[]
}

const SEDE_LINKS: Record<string, string> = {
    AEAT: 'https://sede.agenciatributaria.gob.es/',
    ATC: 'https://sede.gobiernodecanarias.org/tributos/',
    DFG: 'https://egoitza.gipuzkoa.eus/',
    DFB: 'https://www.bizkaia.eus/ogasuna/',
    DFA: 'https://web.araba.eus/es/hacienda',
    HTN: 'https://hacienda.navarra.es/',
}

function daysUntil(dateStr: string): number {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const target = new Date(dateStr)
    target.setHours(0, 0, 0, 0)
    return Math.ceil((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function formatDate(dateStr: string): string {
    const d = new Date(dateStr)
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function ModelObligationsPage() {
    const [ccaa, setCcaa] = useState('')
    const [situacion, setSituacion] = useState('autonomo')
    const [empleados, setEmpleados] = useState(false)
    const [alquileres, setAlquileres] = useState(false)
    const [opsIntra, setOpsIntra] = useState(false)
    const [opsTerceros, setOpsTerceros] = useState(false)
    const [estimacion, setEstimacion] = useState('directa_simplificada')
    const [dividendos, setDividendos] = useState(false)

    const [result, setResult] = useState<ObligationsResponse | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    const consultar = useCallback(async () => {
        if (!ccaa) {
            setError('Selecciona tu comunidad autonoma')
            return
        }
        setLoading(true)
        setError('')
        try {
            const resp = await fetch(`${API_BASE}/api/irpf/model-obligations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ccaa,
                    situacion_laboral: situacion,
                    tiene_empleados: empleados,
                    tiene_alquileres: alquileres,
                    estimacion,
                    tiene_ops_intracomunitarias: opsIntra,
                    tiene_ops_terceros_3005: opsTerceros,
                    paga_dividendos: dividendos,
                }),
            })
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: 'Error del servidor' }))
                throw new Error(err.detail || `Error ${resp.status}`)
            }
            const data: ObligationsResponse = await resp.json()
            setResult(data)
        } catch (e: any) {
            setError(e.message || 'Error al consultar obligaciones')
            setResult(null)
        } finally {
            setLoading(false)
        }
    }, [ccaa, situacion, empleados, alquileres, estimacion, opsIntra, opsTerceros, dividendos])

    return (
        <div className="mo-page">
            <Header />

            {/* Hero */}
            <section className="mo-hero">
                <div className="mo-container">
                    <div className="mo-hero-badge">
                        <ClipboardList size={14} />
                        <span>Asesor de obligaciones fiscales</span>
                    </div>
                    <h1 className="mo-hero-title">
                        ¿Qué modelos fiscales tienes que presentar?
                    </h1>
                    <p className="mo-hero-subtitle">
                        Introduce tu perfil fiscal y descubre todos los modelos que debes presentar
                        ante Hacienda, con fechas límite y enlaces a la sede electrónica.
                    </p>
                </div>
            </section>

            {/* Form */}
            <section className="mo-form-section">
                <div className="mo-container">
                    <div className="mo-form-card">
                        <div className="mo-form-grid">
                            {/* CCAA */}
                            <div className="mo-form-group">
                                <label className="mo-form-label">Comunidad autónoma</label>
                                <select
                                    className="mo-form-select"
                                    value={ccaa}
                                    onChange={e => setCcaa(e.target.value)}
                                >
                                    {CCAA_OPTIONS_WITH_PLACEHOLDER.map(opt => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Situacion laboral */}
                            <div className="mo-form-group">
                                <label className="mo-form-label">Situación laboral</label>
                                <select
                                    className="mo-form-select"
                                    value={situacion}
                                    onChange={e => setSituacion(e.target.value)}
                                >
                                    <option value="particular">Particular (asalariado/pensionista)</option>
                                    <option value="autonomo">Autónomo</option>
                                    <option value="sociedad">Sociedad (SL/SA)</option>
                                </select>
                            </div>

                            {/* Estimacion (only for autonomo) */}
                            {situacion === 'autonomo' && (
                                <div className="mo-form-group">
                                    <label className="mo-form-label">Régimen de estimación</label>
                                    <select
                                        className="mo-form-select"
                                        value={estimacion}
                                        onChange={e => setEstimacion(e.target.value)}
                                    >
                                        <option value="directa_simplificada">Estimación directa simplificada</option>
                                        <option value="directa_normal">Estimación directa normal</option>
                                        <option value="objetiva">Estimación objetiva (módulos)</option>
                                    </select>
                                </div>
                            )}

                            {/* Checkboxes */}
                            {situacion !== 'particular' && (
                                <div className="mo-form-group mo-form-group--full">
                                    <label className="mo-form-label">Situación adicional</label>
                                    <div className="mo-checkboxes">
                                        <label className="mo-checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={empleados}
                                                onChange={e => setEmpleados(e.target.checked)}
                                            />
                                            Tiene empleados
                                        </label>
                                        <label className="mo-checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={alquileres}
                                                onChange={e => setAlquileres(e.target.checked)}
                                            />
                                            Alquila inmuebles
                                        </label>
                                        <label className="mo-checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={opsIntra}
                                                onChange={e => setOpsIntra(e.target.checked)}
                                            />
                                            Operaciones intracomunitarias
                                        </label>
                                        <label className="mo-checkbox-label">
                                            <input
                                                type="checkbox"
                                                checked={opsTerceros}
                                                onChange={e => setOpsTerceros(e.target.checked)}
                                            />
                                            Operaciones con terceros &gt;3.005 EUR
                                        </label>
                                        {situacion === 'sociedad' && (
                                            <label className="mo-checkbox-label">
                                                <input
                                                    type="checkbox"
                                                    checked={dividendos}
                                                    onChange={e => setDividendos(e.target.checked)}
                                                />
                                                Paga dividendos
                                            </label>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        <button
                            onClick={consultar}
                            disabled={loading || !ccaa}
                            style={{
                                marginTop: '24px',
                                width: '100%',
                                padding: '12px',
                                borderRadius: 'var(--radius-md)',
                                background: 'var(--color-primary)',
                                color: '#fff',
                                border: 'none',
                                fontSize: '1rem',
                                fontWeight: 600,
                                cursor: loading || !ccaa ? 'not-allowed' : 'pointer',
                                opacity: loading || !ccaa ? 0.5 : 1,
                            }}
                        >
                            {loading ? 'Consultando...' : 'Ver mis obligaciones fiscales'}
                        </button>

                        {error && (
                            <p style={{ color: '#f87171', marginTop: '12px', fontSize: '0.9rem', textAlign: 'center' }}>
                                <AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                                {error}
                            </p>
                        )}
                    </div>
                </div>
            </section>

            {/* Results */}
            {result && result.modelos.length > 0 && (
                <section className="mo-results">
                    <div className="mo-results-header">
                        <h2 className="mo-results-title">
                            Tus obligaciones fiscales
                        </h2>
                        <p className="mo-results-count">
                            {result.total_modelos} modelo{result.total_modelos !== 1 ? 's' : ''} identificado{result.total_modelos !== 1 ? 's' : ''}
                        </p>
                    </div>

                    <div className="mo-results-grid">
                        {result.modelos.map((m, i) => {
                            const sedeLink = SEDE_LINKS[m.organismo] || SEDE_LINKS.AEAT
                            return (
                                <div key={`${m.modelo}-${i}`} className="mo-card">
                                    <div className="mo-card-header">
                                        <span className="mo-card-modelo">{m.modelo}</span>
                                        <span className={`mo-card-periodicidad mo-card-periodicidad--${m.periodicidad}`}>
                                            <Calendar size={12} />
                                            {m.periodicidad}
                                        </span>
                                    </div>
                                    <h3 className="mo-card-nombre">{m.nombre}</h3>
                                    <p className="mo-card-descripcion">{m.descripcion}</p>

                                    {m.deadlines.length > 0 && (
                                        <div className="mo-card-deadlines">
                                            {m.deadlines.map((d, di) => {
                                                const days = daysUntil(d.date)
                                                const urgent = days >= 0 && days <= 15
                                                return (
                                                    <span
                                                        key={di}
                                                        className={`mo-deadline-chip${urgent ? ' mo-deadline-chip--urgent' : ''}`}
                                                    >
                                                        <Calendar size={10} />
                                                        {formatDate(d.date)}
                                                        {urgent && days >= 0 && ` (${days}d)`}
                                                    </span>
                                                )
                                            })}
                                        </div>
                                    )}

                                    {m.notas && (
                                        <p className="mo-card-notas">{m.notas}</p>
                                    )}

                                    <div className="mo-card-footer">
                                        <span className="mo-card-organismo">
                                            <FileText size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} />
                                            {m.organismo}
                                        </span>
                                        <a
                                            href={sedeLink}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="mo-card-link"
                                        >
                                            Sede electrónica <ExternalLink size={12} />
                                        </a>
                                    </div>
                                </div>
                            )
                        })}
                    </div>

                    <div className="mo-disclaimer">
                        <AlertTriangle size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                        Esta herramienta es orientativa. Consulta con un asesor fiscal para confirmar tus
                        obligaciones concretas. Las fechas límite pueden variar si caen en día inhábil.
                        Datos actualizados para el ejercicio fiscal 2025 (presentación 2026).
                    </div>
                </section>
            )}

            {result && result.modelos.length === 0 && (
                <div className="mo-empty">
                    <div className="mo-empty-icon">
                        <ClipboardList size={48} />
                    </div>
                    <p>No se han encontrado obligaciones para este perfil.</p>
                </div>
            )}
        </div>
    )
}
