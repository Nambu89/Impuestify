import { useState, useCallback, useRef } from 'react'
import { useApi } from './useApi'
import type { ISEstimateInput, ISEstimateResult } from '../types/is'

const DEBOUNCE_MS = 600

export function useIsEstimator() {
    const { apiRequest } = useApi()
    const [result, setResult] = useState<ISEstimateResult | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const abortRef = useRef<AbortController | null>(null)

    const estimate = useCallback((input: ISEstimateInput) => {
        // Must have territorio to estimate
        if (!input.territorio) {
            setResult(null)
            return
        }

        // Must have resultado_contable or ingresos defined
        const hasFinancials =
            (input.resultado_contable !== undefined && input.resultado_contable !== null) ||
            (input.ingresos_explotacion !== undefined && (input.ingresos_explotacion || 0) > 0)
        if (!hasFinancials) {
            setResult(null)
            return
        }

        // Debounce
        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()

        timerRef.current = setTimeout(async () => {
            setLoading(true)
            setError(null)

            const controller = new AbortController()
            abortRef.current = controller

            try {
                const data = await apiRequest<ISEstimateResult>(
                    '/irpf/is-estimate',
                    {
                        method: 'POST',
                        body: JSON.stringify(input),
                        signal: controller.signal,
                    }
                )
                if (!controller.signal.aborted) {
                    setResult(data)
                }
            } catch (err: any) {
                if (err.name !== 'AbortError' && !controller.signal.aborted) {
                    setError(err.message)
                }
            } finally {
                if (!controller.signal.aborted) setLoading(false)
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

    return { result, loading, error, estimate, reset }
}
