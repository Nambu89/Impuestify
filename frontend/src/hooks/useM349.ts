import { useState, useCallback } from 'react'

export interface Operacion349 {
    nif_operador: string
    nombre: string
    clave: string
    importe: number
    periodo_rectificado?: string
    base_anterior_declarada?: number
}

export interface M349Input {
    operaciones: Operacion349[]
    periodo: string
    year?: number
    ccaa?: string
    forzar_anual: boolean
    validar_vies: boolean
}

export interface M349Result {
    success: boolean
    periodo: string
    year: number
    periodicidad: string
    operadores_unicos: number
    total_por_clave: Record<string, number>
    total_general: number
    cuadre_303?: Record<string, any> | null
    avisos: string[]
    plazo: string
    formatted_response: string
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useM349() {
    const [result, setResult] = useState<M349Result | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const calculate = useCallback(async (input: M349Input) => {
        setLoading(true)
        setError(null)
        try {
            const token = localStorage.getItem('access_token')
            if (!token) {
                setError('Debes iniciar sesion para usar esta calculadora')
                setLoading(false)
                return
            }
            const res = await fetch(`${API_BASE}/api/modelo-349/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify(input),
            })
            if (res.status === 401) {
                localStorage.removeItem('access_token')
                window.location.href = '/login?expired=true'
                return
            }
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || `Error ${res.status}`)
            }
            const data: M349Result = await res.json()
            setResult(data)
        } catch (err: any) {
            setError(err.message || 'Error al calcular Modelo 349')
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
