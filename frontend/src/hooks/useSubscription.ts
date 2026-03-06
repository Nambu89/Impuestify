import { useState, useEffect, useCallback } from 'react'
import { useApi } from './useApi'
import { useAuth } from './useAuth'

interface SubscriptionStatus {
    has_access: boolean
    is_owner: boolean
    plan_type: string | null
    status: string | null
    current_period_end: string | null
    cancel_at_period_end: boolean
}

interface UseSubscriptionReturn {
    hasAccess: boolean
    isOwner: boolean
    planType: string | null
    status: string | null
    currentPeriodEnd: string | null
    cancelAtPeriodEnd: boolean
    loading: boolean
    error: string | null
    createCheckout: (planType?: string) => Promise<void>
    openPortal: () => Promise<void>
    refresh: () => Promise<void>
}

export function useSubscription(): UseSubscriptionReturn {
    const { apiRequest } = useApi()
    const { user, isAuthenticated } = useAuth()

    const [data, setData] = useState<SubscriptionStatus | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchStatus = useCallback(async () => {
        if (!isAuthenticated) {
            setLoading(false)
            return
        }

        try {
            setError(null)
            const result = await apiRequest('/subscription/status')
            setData(result)
        } catch (err: any) {
            setError(err.message || 'Error al obtener estado de suscripcion')
        } finally {
            setLoading(false)
        }
    }, [isAuthenticated, apiRequest])

    useEffect(() => {
        fetchStatus()
    }, [fetchStatus])

    const createCheckout = useCallback(async (planType: string = 'particular') => {
        try {
            const result = await apiRequest('/subscription/create-checkout', {
                method: 'POST',
                body: JSON.stringify({
                    success_url: `${window.location.origin}/chat?subscription=success`,
                    cancel_url: `${window.location.origin}/subscribe?canceled=true`,
                    plan_type: planType,
                }),
            })

            if (result.checkout_url) {
                window.location.href = result.checkout_url
            }
        } catch (err: any) {
            setError(err.message || 'Error al crear sesion de pago')
            throw err
        }
    }, [apiRequest])

    const openPortal = useCallback(async () => {
        try {
            const result = await apiRequest('/subscription/create-portal', {
                method: 'POST',
                body: JSON.stringify({
                    return_url: `${window.location.origin}/settings`,
                }),
            })

            if (result.portal_url) {
                window.location.href = result.portal_url
            }
        } catch (err: any) {
            setError(err.message || 'Error al abrir portal de gestion')
            throw err
        }
    }, [apiRequest])

    // Owner has full access regardless
    const isOwner = data?.is_owner || user?.is_owner || false
    const hasAccess = data?.has_access || isOwner

    return {
        hasAccess,
        isOwner,
        planType: data?.plan_type || null,
        status: data?.status || user?.subscription_status || null,
        currentPeriodEnd: data?.current_period_end || null,
        cancelAtPeriodEnd: data?.cancel_at_period_end || false,
        loading,
        error,
        createCheckout,
        openPortal,
        refresh: fetchStatus,
    }
}
