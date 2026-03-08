import { useState, useCallback, useRef } from 'react'
import { useApi } from './useApi'

export interface FiscalField {
    key: string
    label: string
    type: 'bool' | 'number' | 'select' | 'date' | 'text'
    options?: string[]
    required?: boolean
    foral_only?: boolean
    help_text?: string
    deductions_count?: number
}

export interface FiscalSection {
    id: string
    title: string
    fields: FiscalField[]
    collapsible?: boolean
    expanded_default?: boolean
}

export type FiscalRegime = 'comun' | 'foral_vasco' | 'foral_navarra' | 'ceuta_melilla' | 'canarias'

export interface FiscalFieldsResponse {
    regime: FiscalRegime
    sections: FiscalSection[]
}

interface UseFiscalFieldsResult {
    sections: FiscalSection[]
    regime: FiscalRegime | null
    loading: boolean
    error: string | null
}

/**
 * Fetches dynamic fiscal form fields for a given CCAA.
 * Caches results per CCAA to avoid redundant requests.
 * Degrades gracefully if the endpoint returns 404 (returns empty sections).
 */
export function useFiscalFields(ccaa: string | null): UseFiscalFieldsResult {
    const { apiRequest } = useApi()
    const [sections, setSections] = useState<FiscalSection[]>([])
    const [regime, setRegime] = useState<FiscalRegime | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Cache per CCAA value to avoid repeated fetches
    const cache = useRef<Map<string, FiscalFieldsResponse>>(new Map())
    const lastCcaa = useRef<string | null>(null)

    const fetchFields = useCallback(async (target: string) => {
        // Return from cache if available
        if (cache.current.has(target)) {
            const cached = cache.current.get(target)!
            setSections(cached.sections)
            setRegime(cached.regime)
            return
        }

        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<FiscalFieldsResponse>(
                `/api/fiscal-profile/fields?ccaa=${encodeURIComponent(target)}`
            )
            // Normalize field types from backend (float/int/str → number/number/text)
            for (const section of data.sections) {
                for (const field of section.fields) {
                    if (field.type === 'float' as any || field.type === 'int' as any) {
                        (field as any).type = 'number'
                    } else if (field.type === 'str' as any) {
                        (field as any).type = 'text'
                    } else if (field.type === 'list_int' as any) {
                        (field as any).type = 'text'  // comma-separated input
                    }
                }
            }
            cache.current.set(target, data)
            setSections(data.sections)
            setRegime(data.regime)
        } catch (err: any) {
            // 404 = endpoint not yet available → degrade gracefully
            if (err.message && (err.message.includes('404') || err.message.includes('HTTP 404'))) {
                setSections([])
                setRegime(null)
            } else {
                setError(err.message || 'Error cargando campos fiscales')
            }
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    // Trigger fetch when ccaa changes
    if (ccaa && ccaa !== lastCcaa.current) {
        lastCcaa.current = ccaa
        fetchFields(ccaa)
    } else if (!ccaa && lastCcaa.current !== null) {
        lastCcaa.current = null
        setSections([])
        setRegime(null)
    }

    return { sections, regime, loading, error }
}
