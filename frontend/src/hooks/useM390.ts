import { useState, useCallback } from 'react'

export interface Trimestre303 {
    casilla_27: number
    casilla_45: number
    resultado_liquidacion: number
}

export interface M390Input {
    year?: number
    ccaa?: string
    volumen_operaciones_ano_anterior: number
    en_redeme: boolean
    en_grupo_iva: boolean
    sii_voluntario: boolean
    regimen_especial: string
    trimestres_303?: Trimestre303[]
}

export interface M390Result {
    success: boolean
    year: number
    obligado: boolean
    modelo?: string | null
    ccaa?: string | null
    motivo_exoneracion?: string | null
    variante_territorial?: string | null
    resumen_anual?: Record<string, any> | null
    plazo: string
    formatted_response: string
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useM390() {
    const [result, setResult] = useState<M390Result | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const calculate = useCallback(async (input: M390Input) => {
        setLoading(true)
        setError(null)
        try {
            const token = localStorage.getItem('access_token')
            if (!token) {
                setError('Debes iniciar sesion para usar esta calculadora')
                setLoading(false)
                return
            }
            const res = await fetch(`${API_BASE}/api/modelo-390/calculate`, {
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
            const data: M390Result = await res.json()
            setResult(data)
        } catch (err: any) {
            setError(err.message || 'Error al calcular Modelo 390')
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
