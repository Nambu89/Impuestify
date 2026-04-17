import { useState, useCallback } from 'react'
import { useApi } from './useApi'
import type { ISPrefillData } from '../types/is'

export function useIsPrefill() {
    const { apiRequest } = useApi()
    const [data, setData] = useState<ISPrefillData | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const prefill = useCallback(async (workspaceId: string, ejercicio: number) => {
        if (!workspaceId) {
            setData(null)
            setLoading(false)
            return
        }

        setLoading(true)
        setError(null)

        try {
            const result = await apiRequest<ISPrefillData>(
                `/workspaces/${workspaceId}/is-prefill?ejercicio=${ejercicio}`
            )
            setData(result)
        } catch (err: any) {
            setError(err.message)
            setData(null)
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const reset = useCallback(() => {
        setData(null)
        setError(null)
        setLoading(false)
    }, [])

    return { data, loading, error, prefill, reset }
}
