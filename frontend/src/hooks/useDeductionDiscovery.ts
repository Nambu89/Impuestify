import { useState, useCallback, useRef } from 'react'
import { useApi } from './useApi'

export interface DeductionItem {
    code: string
    name: string
    category: string
    description: string
    percentage?: number
    max_amount?: number
    fixed_amount?: number
    legal_reference: string
}

export interface MissingQuestion {
    key: string
    text: string
    type: string
    deduction_code: string
    deduction_name: string
}

export interface DeductionDiscoveryResult {
    eligible: DeductionItem[]
    maybe_eligible: DeductionItem[]
    estimated_savings: number
    total_deductions: number
    missing_questions: MissingQuestion[]
}

const DEBOUNCE_MS = 300

export function useDeductionDiscovery() {
    const { apiRequest } = useApi()
    const [result, setResult] = useState<DeductionDiscoveryResult | null>(null)
    const [loading, setLoading] = useState(false)
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const abortRef = useRef<AbortController | null>(null)

    const discover = useCallback((ccaa: string, answers: Record<string, any>, taxYear = 2025) => {
        if (!ccaa) {
            setResult(null)
            return
        }

        if (timerRef.current) clearTimeout(timerRef.current)
        if (abortRef.current) abortRef.current.abort()

        timerRef.current = setTimeout(async () => {
            setLoading(true)
            const controller = new AbortController()
            abortRef.current = controller

            try {
                const data = await apiRequest<DeductionDiscoveryResult>(
                    '/api/irpf/deductions/discover',
                    {
                        method: 'POST',
                        body: JSON.stringify({ ccaa, tax_year: taxYear, answers }),
                        signal: controller.signal,
                    }
                )
                if (!controller.signal.aborted) {
                    setResult(data)
                }
            } catch (err: any) {
                if (err.name !== 'AbortError' && !controller.signal.aborted) {
                    setResult(null)
                }
            } finally {
                if (!controller.signal.aborted) setLoading(false)
            }
        }, DEBOUNCE_MS)
    }, [apiRequest])

    return { result, loading, discover }
}
