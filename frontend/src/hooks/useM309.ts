import { useState, useCallback } from 'react'

export interface M309Input {
    periodo: string
    year?: number
    base_intracomunitarias_21: number
    base_intracomunitarias_10: number
    base_intracomunitarias_4: number
    base_intracomunitarias_tabaco: number
    base_isp_21: number
    base_isp_10: number
    base_isp_4: number
    aplica_re: boolean
}

export interface M309Result {
    success: boolean
    periodo: string
    year: number
    aplica_re: boolean
    desglose: Record<string, any>
    total_iva: number
    total_re: number
    resultado: number
    plazo: string
    formatted_response: string
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useM309() {
    const [result, setResult] = useState<M309Result | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const calculate = useCallback(async (input: M309Input) => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`${API_BASE}/api/modelo-309/calculate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(input),
            })
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || `Error ${res.status}`)
            }
            const data: M309Result = await res.json()
            setResult(data)
        } catch (err: any) {
            setError(err.message || 'Error al calcular Modelo 309')
        } finally {
            setLoading(false)
        }
    }, [])

    const reset = useCallback(() => {
        setResult(null)
        setError(null)
    }, [])

    return { result, loading, error, calculate, reset }
}
