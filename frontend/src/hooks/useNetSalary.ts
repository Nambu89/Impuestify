import { useState, useCallback, useRef } from 'react'
import { useApi } from './useApi'

export interface NetSalaryInput {
    facturacion_bruta_mensual: number
    tipo_iva: number
    retencion_irpf: number
    cuota_autonomo_mensual: number
    gastos_deducibles_mensual: number
    es_nuevo_autonomo: boolean
}

export interface NetSalaryResult {
    success: boolean
    facturacion_bruta: number
    iva_repercutido: number
    total_factura: number
    retencion_irpf_factura: number
    cobro_efectivo: number
    cuota_autonomo: number
    gastos_deducibles: number
    iva_a_pagar_hacienda: number
    neto_mensual: number
    facturacion_bruta_anual: number
    irpf_estimado_anual: number
    cuota_autonomo_anual: number
    neto_anual: number
    tipo_irpf_efectivo: number
    porcentaje_neto: number
    ahorro_retencion_vs_irpf: number
    error?: string
}

const DEBOUNCE_MS = 400

export function useNetSalary() {
    const { apiRequest } = useApi()
    const [result, setResult] = useState<NetSalaryResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const abortRef = useRef<AbortController | null>(null)

    const calculate = useCallback((input: NetSalaryInput) => {
        if (!input.facturacion_bruta_mensual || input.facturacion_bruta_mensual <= 0) {
            setResult(null)
            setError(null)
            return
        }

        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()

        timerRef.current = setTimeout(async () => {
            setLoading(true)
            setError(null)

            const controller = new AbortController()
            abortRef.current = controller

            try {
                const data = await apiRequest<NetSalaryResult>(
                    '/api/irpf/net-salary',
                    {
                        method: 'POST',
                        body: JSON.stringify(input),
                        signal: controller.signal,
                    }
                )
                if (!controller.signal.aborted) {
                    setResult(data)
                    if (!data.success) {
                        setError(data.error || 'Error al calcular el sueldo neto')
                    }
                }
            } catch (err: any) {
                if (err.name !== 'AbortError' && !controller.signal.aborted) {
                    setError(err.message || 'Error de conexion')
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false)
                }
            }
        }, DEBOUNCE_MS)
    }, [apiRequest])

    const reset = useCallback(() => {
        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()
        setResult(null)
        setError(null)
        setLoading(false)
    }, [])

    return { result, loading, error, calculate, reset }
}
