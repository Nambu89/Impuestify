import { useState, useCallback } from 'react'

export interface M131Input {
    trimestre: number
    actividad_tipo: 'empresarial' | 'sin_datos_base' | 'agraria'
    territorio: string
    rendimiento_neto_modulos_anual: number
    num_asalariados: number
    volumen_ingresos_trimestre: number
    /**
     * Rendimiento neto del ejercicio ANTERIOR. Es el dato de partida de la
     * minoracion de la casilla [09] (art. 110.3.c RIRPF), no la casilla en si.
     *
     * Campo OPCIONAL de tres estados. La clave se OMITE cuando el usuario no
     * facilita el dato: asi el backend aplica su defecto (`None`) y no calcula
     * minoracion alguna. Un 0 explicito SI la aplica (100 EUR/trimestre), asi
     * que nunca se envia 0 como relleno. Construyelo con `withOptionalField`
     * de `utils/numberField` para no colapsar los tres estados.
     */
    rendimiento_neto_anterior?: number
    retenciones_trimestre: number
    /*
     * NO hay `pagos_anteriores`. El 131 no es acumulativo: cada trimestre se
     * calcula sobre los datos-base del primer dia del año (art. 110.1.b
     * RIRPF), no sobre lo acumulado, asi que no hay nada que descontar y el
     * diseño de registro DR131 no tiene casilla para ello. Restarlo hacia
     * ingresar de MENOS. Es el 130 (estimacion directa, art. 110.1.a) el que
     * si lo deduce, en su casilla [05].
     */
    ceuta_melilla: boolean
    la_palma: boolean
    year: number
}

export interface M131Result {
    success: boolean
    trimestre: number
    apartado: string
    actividad_tipo: string
    territory: string
    tipo_aplicado: number
    casillas: Record<string, number>
    desglose: Record<string, any>
    resultado_final: number
    plazo: string
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useM131() {
    const [result, setResult] = useState<M131Result | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const calculate = useCallback(async (input: M131Input) => {
        setLoading(true)
        setError(null)
        try {
            const token = localStorage.getItem('access_token')
            const res = await fetch(`${API_BASE}/api/modelo-131/calculate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify(input),
            })
            if (!res.ok) {
                const err = await res.json().catch(() => ({}))
                throw new Error(err.detail || `Error ${res.status}`)
            }
            const data: M131Result = await res.json()
            setResult(data)
        } catch (err: any) {
            setError(err.message || 'Error al calcular Modelo 131')
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
