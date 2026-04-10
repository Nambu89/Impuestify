import { useState, useCallback, useEffect, useRef } from 'react'
import { useApi } from './useApi'

export interface WorkspaceDashboardKPIs {
    ingresos_total: number
    gastos_total: number
    iva_repercutido: number
    iva_soportado: number
    balance_iva: number
    retencion_irpf_total: number
    resultado_neto: number
    facturas_count: number
    facturas_pendientes: number
}

export interface TrimestreData {
    trimestre: string
    ingresos: number
    gastos: number
    iva_repercutido: number
    iva_soportado: number
}

export interface MesData {
    mes: string
    ingresos: number
    gastos: number
}

export interface CuentaPGCData {
    cuenta: string
    nombre: string
    total: number
    tipo: string
}

export interface ProveedorData {
    nombre: string
    nif: string
    total: number
    facturas: number
}

export interface FacturaReciente {
    id: string
    fecha: string
    emisor: string
    concepto: string
    total: number
    tipo: string
    cuenta_pgc: string
    clasificacion_confianza: string
}

export interface WorkspaceDashboardData {
    kpis: WorkspaceDashboardKPIs
    por_trimestre: TrimestreData[]
    por_mes: MesData[]
    por_cuenta_pgc: CuentaPGCData[]
    top_proveedores: ProveedorData[]
    facturas_recientes: FacturaReciente[]
}

export function useWorkspaceDashboard(workspaceId: string | null, year?: number) {
    const { apiRequest } = useApi()
    const [data, setData] = useState<WorkspaceDashboardData | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const requestIdRef = useRef<number>(0)

    const fetchDashboard = useCallback(async (wsId: string) => {
        const requestId = ++requestIdRef.current
        setLoading(true)
        setError(null)
        try {
            const yearParam = year || new Date().getFullYear()
            const result = await apiRequest<WorkspaceDashboardData>(
                `/api/workspaces/${wsId}/dashboard?year=${yearParam}`
            )
            if (requestId === requestIdRef.current) {
                setData(result)
            }
        } catch (err: any) {
            if (requestId === requestIdRef.current) {
                setError(err.message || 'Error al cargar el dashboard')
                setData(null)
            }
        } finally {
            if (requestId === requestIdRef.current) {
                setLoading(false)
            }
        }
    }, [apiRequest, year])

    useEffect(() => {
        if (workspaceId) {
            fetchDashboard(workspaceId)
        } else {
            setData(null)
            setError(null)
            setLoading(false)
        }
    }, [workspaceId, fetchDashboard])

    const refresh = useCallback(() => {
        if (workspaceId) {
            fetchDashboard(workspaceId)
        }
    }, [workspaceId, fetchDashboard])

    return { data, loading, error, refresh }
}
