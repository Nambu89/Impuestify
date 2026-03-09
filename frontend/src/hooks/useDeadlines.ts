import { useState, useEffect, useCallback } from 'react'
import { useApi } from './useApi'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FiscalDeadlineRaw {
    id: string
    model: string
    model_name: string
    territory: string
    period: string
    tax_year: number
    start_date: string
    end_date: string
    domiciliation_date?: string
    applies_to: 'todos' | 'autonomos' | 'particulares'
    description?: string
    source_url?: string
    is_active: boolean
}

export type UrgencyLevel = 'past' | 'urgent' | 'soon' | 'normal'

export interface FiscalDeadline extends FiscalDeadlineRaw {
    daysRemaining: number
    urgency: UrgencyLevel
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function calcDaysRemaining(endDate: string): number {
    const now = new Date()
    now.setHours(0, 0, 0, 0)
    const end = new Date(endDate)
    end.setHours(0, 0, 0, 0)
    return Math.round((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
}

function calcUrgency(daysRemaining: number): UrgencyLevel {
    if (daysRemaining < 0) return 'past'
    if (daysRemaining < 5) return 'urgent'
    if (daysRemaining < 15) return 'soon'
    return 'normal'
}

function enrichDeadlines(raw: FiscalDeadlineRaw[]): FiscalDeadline[] {
    return raw.map((d) => {
        const days = calcDaysRemaining(d.end_date)
        return {
            ...d,
            daysRemaining: days,
            urgency: calcUrgency(days),
        }
    })
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseDeadlinesOptions {
    days?: number
    isPublic?: boolean
}

interface UseDeadlinesReturn {
    deadlines: FiscalDeadline[]
    loading: boolean
    error: string | null
    refresh: () => void
}

export function useDeadlines(options: UseDeadlinesOptions = {}): UseDeadlinesReturn {
    const { days = 60, isPublic = false } = options
    const { apiRequest } = useApi()

    const [deadlines, setDeadlines] = useState<FiscalDeadline[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchDeadlines = useCallback(async () => {
        setLoading(true)
        setError(null)

        try {
            if (isPublic) {
                // Public endpoint — no auth required
                const apiUrl = import.meta.env.VITE_API_URL || '/api'
                const res = await fetch(`${apiUrl}/deadlines/public?days=${days}`)
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                const data: FiscalDeadlineRaw[] = await res.json()
                setDeadlines(enrichDeadlines(data))
            } else {
                // Authenticated endpoint
                const data = await apiRequest<FiscalDeadlineRaw[]>(
                    `/deadlines/upcoming?days=${days}`
                )
                setDeadlines(enrichDeadlines(data || []))
            }
        } catch (err: any) {
            setError(err.message || 'Error al cargar plazos fiscales')
            setDeadlines([])
        } finally {
            setLoading(false)
        }
    }, [days, isPublic, apiRequest])

    useEffect(() => {
        fetchDeadlines()
    }, [fetchDeadlines])

    return {
        deadlines,
        loading,
        error,
        refresh: fetchDeadlines,
    }
}
