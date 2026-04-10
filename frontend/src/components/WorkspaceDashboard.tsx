import { useWorkspaceDashboard, WorkspaceDashboardKPIs, ProveedorData, FacturaReciente, CuentaPGCData } from '../hooks/useWorkspaceDashboard'
import CountUp from './reactbits/CountUp'
import SpotlightCard from './reactbits/SpotlightCard'
import {
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import {
    TrendingUp, TrendingDown, Receipt, Banknote,
    AlertCircle, BarChart3, RefreshCw
} from 'lucide-react'
import './WorkspaceDashboard.css'

const PIE_COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#22c55e', '#ef4444', '#64748b']

const formatEUR = (value: number | null | undefined): string => {
    if (value == null) return '0,00 EUR'
    return new Intl.NumberFormat('es-ES', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value) + ' EUR'
}

const formatEURShort = (value: number): string => {
    if (Math.abs(value) >= 1000) {
        return new Intl.NumberFormat('es-ES', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 1
        }).format(value / 1000) + 'k'
    }
    return new Intl.NumberFormat('es-ES', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value)
}

// -- KPI Cards --

function KPICards({ kpis }: { kpis: WorkspaceDashboardKPIs }) {
    const resultadoPositivo = kpis.resultado_neto >= 0

    return (
        <div className="ws-dashboard-kpis">
            <SpotlightCard className="ws-kpi-card" spotlightColor="rgba(6, 182, 212, 0.15)">
                <div className="ws-kpi-icon ws-kpi-icon--cyan">
                    <TrendingUp size={18} />
                </div>
                <div className="ws-kpi-label">Ingresos</div>
                <div className="ws-kpi-value">
                    <CountUp to={kpis.ingresos_total} separator="." duration={1.5} />
                    <span className="ws-kpi-currency"> EUR</span>
                </div>
                <div className="ws-kpi-detail">{kpis.facturas_count} facturas</div>
            </SpotlightCard>

            <SpotlightCard className="ws-kpi-card" spotlightColor="rgba(239, 68, 68, 0.15)">
                <div className="ws-kpi-icon ws-kpi-icon--red">
                    <TrendingDown size={18} />
                </div>
                <div className="ws-kpi-label">Gastos</div>
                <div className="ws-kpi-value">
                    <CountUp to={kpis.gastos_total} separator="." duration={1.5} />
                    <span className="ws-kpi-currency"> EUR</span>
                </div>
                <div className="ws-kpi-detail">IRPF retenido: {formatEUR(kpis.retencion_irpf_total)}</div>
            </SpotlightCard>

            <SpotlightCard className="ws-kpi-card" spotlightColor="rgba(26, 86, 219, 0.15)">
                <div className="ws-kpi-icon ws-kpi-icon--blue">
                    <Receipt size={18} />
                </div>
                <div className="ws-kpi-label">Balance IVA</div>
                <div className="ws-kpi-value">
                    <CountUp to={kpis.balance_iva} separator="." duration={1.5} />
                    <span className="ws-kpi-currency"> EUR</span>
                </div>
                <div className="ws-kpi-detail">
                    Repercutido: {formatEUR(kpis.iva_repercutido)} | Soportado: {formatEUR(kpis.iva_soportado)}
                </div>
            </SpotlightCard>

            <SpotlightCard
                className="ws-kpi-card"
                spotlightColor={resultadoPositivo ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)'}
            >
                <div className={`ws-kpi-icon ${resultadoPositivo ? 'ws-kpi-icon--green' : 'ws-kpi-icon--negative'}`}>
                    <Banknote size={18} />
                </div>
                <div className="ws-kpi-label">Resultado neto</div>
                <div className="ws-kpi-value">
                    <CountUp to={kpis.resultado_neto} separator="." duration={1.5} />
                    <span className="ws-kpi-currency"> EUR</span>
                </div>
                <div className="ws-kpi-detail">
                    {kpis.facturas_pendientes > 0
                        ? `${kpis.facturas_pendientes} facturas pendientes de confirmar`
                        : 'Todas las facturas confirmadas'}
                </div>
            </SpotlightCard>
        </div>
    )
}

// -- IVA Trimestral Bar Chart --

function IVATrimestralChart({ data }: { data: Array<{ trimestre: string; iva_repercutido: number; iva_soportado: number }> }) {
    if (!data || data.length === 0) return null

    return (
        <div className="ws-chart-card">
            <div className="ws-chart-title">IVA por trimestre</div>
            <ResponsiveContainer width="100%" height={260}>
                <BarChart data={data} barGap={4}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="trimestre" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
                    <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} tickFormatter={formatEURShort} />
                    <Tooltip
                        formatter={(value: number, name: string) => [formatEUR(value), name === 'iva_repercutido' ? 'Repercutido' : 'Soportado']}
                        contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                        labelStyle={{ color: 'rgba(255,255,255,0.8)' }}
                        itemStyle={{ color: 'rgba(255,255,255,0.7)' }}
                    />
                    <Legend
                        formatter={(value: string) => value === 'iva_repercutido' ? 'Repercutido' : 'Soportado'}
                    />
                    <Bar dataKey="iva_repercutido" fill="#06b6d4" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="iva_soportado" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    )
}

// -- Ingresos/Gastos Line Chart --

function IngresosGastosChart({ data }: { data: Array<{ mes: string; ingresos: number; gastos: number }> }) {
    if (!data || data.length === 0) return null

    return (
        <div className="ws-chart-card">
            <div className="ws-chart-title">Ingresos vs Gastos mensual</div>
            <ResponsiveContainer width="100%" height={260}>
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="mes" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }} />
                    <YAxis tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 11 }} tickFormatter={formatEURShort} />
                    <Tooltip
                        formatter={(value: number, name: string) => [formatEUR(value), name === 'ingresos' ? 'Ingresos' : 'Gastos']}
                        contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                        labelStyle={{ color: 'rgba(255,255,255,0.8)' }}
                        itemStyle={{ color: 'rgba(255,255,255,0.7)' }}
                    />
                    <Legend
                        formatter={(value: string) => value === 'ingresos' ? 'Ingresos' : 'Gastos'}
                    />
                    <Line type="monotone" dataKey="ingresos" stroke="#06b6d4" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    <Line type="monotone" dataKey="gastos" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    )
}

// -- PGC Pie Chart --

function PGCPieChart({ data }: { data: CuentaPGCData[] }) {
    if (!data || data.length === 0) return null

    const total = data.reduce((sum, d) => sum + Math.abs(d.total), 0)

    const renderLabel = ({ nombre, percent }: { nombre: string; percent: number }) => {
        if (percent < 0.05) return ''
        const shortName = nombre.length > 15 ? nombre.substring(0, 15) + '...' : nombre
        return `${shortName} (${(percent * 100).toFixed(0)}%)`
    }

    return (
        <div className="ws-chart-card">
            <div className="ws-chart-title">Desglose por cuenta PGC</div>
            <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                    <Pie
                        data={data.map(d => ({ ...d, value: Math.abs(d.total) }))}
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        dataKey="value"
                        nameKey="nombre"
                        label={({ nombre, percent }) => renderLabel({ nombre, percent })}
                        labelLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                    >
                        {data.map((_, index) => (
                            <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value: number) => [
                            `${formatEUR(value)} (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`,
                            'Total'
                        ]}
                        contentStyle={{ background: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                        labelStyle={{ color: 'rgba(255,255,255,0.8)' }}
                        itemStyle={{ color: 'rgba(255,255,255,0.7)' }}
                    />
                </PieChart>
            </ResponsiveContainer>
        </div>
    )
}

// -- Top Proveedores --

function TopProveedores({ data }: { data: ProveedorData[] }) {
    if (!data || data.length === 0) return null

    const maxTotal = Math.max(...data.map(p => p.total))

    return (
        <div className="ws-chart-card">
            <div className="ws-chart-title">Top proveedores</div>
            <div className="ws-proveedores-list">
                {data.map((prov, i) => (
                    <div key={i} className="ws-proveedor-item">
                        <div className="ws-proveedor-header">
                            <span className="ws-proveedor-name">{prov.nombre}</span>
                            <span className="ws-proveedor-total">{formatEUR(prov.total)}</span>
                        </div>
                        <span className="ws-proveedor-meta">{prov.nif} - {prov.facturas} facturas</span>
                        <div className="ws-proveedor-bar-track">
                            <div
                                className="ws-proveedor-bar-fill"
                                style={{ width: maxTotal > 0 ? `${(prov.total / maxTotal) * 100}%` : '0%' }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// -- Facturas Recientes Table --

function FacturasRecientesTable({ data }: { data: FacturaReciente[] }) {
    if (!data || data.length === 0) return null

    const getEstadoBadge = (confianza: string) => {
        switch (confianza) {
            case 'pendiente_confirmacion':
                return <span className="ws-estado-badge ws-estado-badge--pendiente">Pendiente</span>
            case 'confirmada':
                return <span className="ws-estado-badge ws-estado-badge--confirmada">Confirmada</span>
            case 'manual':
                return <span className="ws-estado-badge ws-estado-badge--manual">Manual</span>
            default:
                return <span className="ws-estado-badge ws-estado-badge--pendiente">{confianza || '-'}</span>
        }
    }

    const formatDate = (dateStr: string) => {
        try {
            return new Date(dateStr).toLocaleDateString('es-ES', {
                day: '2-digit',
                month: 'short'
            })
        } catch {
            return dateStr
        }
    }

    return (
        <div className="ws-chart-card ws-dashboard-full">
            <div className="ws-chart-title">Facturas recientes</div>
            <div style={{ overflowX: 'auto' }}>
                <table className="ws-facturas-table">
                    <thead>
                        <tr>
                            <th>Fecha</th>
                            <th>Emisor</th>
                            <th>Concepto</th>
                            <th style={{ textAlign: 'right' }}>Importe</th>
                            <th>Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map(factura => (
                            <tr key={factura.id}>
                                <td>{formatDate(factura.fecha)}</td>
                                <td>{factura.emisor}</td>
                                <td className="ws-factura-concepto">
                                    {factura.concepto.length > 30
                                        ? factura.concepto.substring(0, 30) + '...'
                                        : factura.concepto}
                                </td>
                                <td className="ws-factura-importe">{formatEUR(factura.total)}</td>
                                <td>{getEstadoBadge(factura.clasificacion_confianza)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

// -- Main Dashboard Component --

interface WorkspaceDashboardProps {
    workspaceId: string
}

export default function WorkspaceDashboard({ workspaceId }: WorkspaceDashboardProps) {
    const { data, loading, error, refresh } = useWorkspaceDashboard(workspaceId)

    if (loading) {
        return (
            <div className="ws-dashboard-loading">
                <div className="loading-spinner"></div>
                <p>Cargando dashboard...</p>
            </div>
        )
    }

    if (error) {
        return (
            <div className="ws-dashboard">
                <div className="ws-dashboard-error">
                    <AlertCircle size={18} />
                    <span>{error}</span>
                    <button className="btn btn-ghost btn-sm" onClick={refresh} style={{ marginLeft: 'auto' }}>
                        <RefreshCw size={14} /> Reintentar
                    </button>
                </div>
            </div>
        )
    }

    if (!data) {
        return (
            <div className="ws-dashboard-empty">
                <BarChart3 size={48} />
                <p>Sube facturas al workspace para ver el dashboard financiero</p>
            </div>
        )
    }

    return (
        <div className="ws-dashboard">
            <KPICards kpis={data.kpis} />

            <div className="ws-dashboard-charts">
                <IVATrimestralChart data={data.por_trimestre} />
                <IngresosGastosChart data={data.por_mes} />
            </div>

            <div className="ws-dashboard-bottom">
                <PGCPieChart data={data.por_cuenta_pgc} />
                <TopProveedores data={data.top_proveedores} />
            </div>

            <FacturasRecientesTable data={data.facturas_recientes} />
        </div>
    )
}
