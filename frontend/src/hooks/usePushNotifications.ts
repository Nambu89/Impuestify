import { useState, useEffect, useCallback } from 'react'
import { useApi } from './useApi'

// Convert VAPID public key from base64url to Uint8Array
function urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
    const rawData = window.atob(base64)
    const outputArray = new Uint8Array(rawData.length)
    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i)
    }
    return outputArray
}

interface UsePushNotificationsReturn {
    isSupported: boolean
    permission: NotificationPermission
    isSubscribed: boolean
    subscribe: (alertDays?: number[]) => Promise<void>
    unsubscribe: () => Promise<void>
    loading: boolean
    error: string | null
}

export function usePushNotifications(): UsePushNotificationsReturn {
    const { apiRequest } = useApi()

    const isSupported =
        typeof window !== 'undefined' &&
        'PushManager' in window &&
        'serviceWorker' in navigator

    const [permission, setPermission] = useState<NotificationPermission>(
        isSupported ? Notification.permission : 'denied'
    )
    const [isSubscribed, setIsSubscribed] = useState(false)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Check current subscription state on mount
    useEffect(() => {
        if (!isSupported) return

        navigator.serviceWorker.ready
            .then((registration) => registration.pushManager.getSubscription())
            .then((sub) => setIsSubscribed(sub !== null))
            .catch(() => setIsSubscribed(false))
    }, [isSupported])

    const subscribe = useCallback(
        async (alertDays: number[] = [15, 5, 1]) => {
            if (!isSupported) {
                setError('Tu navegador no soporta notificaciones push')
                return
            }

            setLoading(true)
            setError(null)

            try {
                // 1. Request notification permission
                const perm = await Notification.requestPermission()
                setPermission(perm)

                if (perm !== 'granted') {
                    setError('Permiso de notificaciones denegado')
                    return
                }

                // 2. Get VAPID public key from backend (no auth required)
                const apiUrl = import.meta.env.VITE_API_URL || '/api'
                const vapidResponse = await fetch(`${apiUrl}/api/push/vapid-key`)
                if (!vapidResponse.ok) {
                    throw new Error(`VAPID fetch failed: HTTP ${vapidResponse.status}`)
                }
                const vapidData = await vapidResponse.json()
                const vapidKey = vapidData.public_key || vapidData.publicKey
                if (!vapidKey) {
                    throw new Error('Clave VAPID no configurada en el servidor')
                }

                // 3. Register push subscription via Service Worker
                const registration = await navigator.serviceWorker.ready
                console.log('[Push] SW ready, scope:', registration.scope)
                console.log('[Push] SW state:', registration.active?.state)

                // Clear any stale subscription (VAPID key mismatch causes "push service error")
                const existingSub = await registration.pushManager.getSubscription()
                if (existingSub) {
                    console.log('[Push] Clearing stale subscription')
                    await existingSub.unsubscribe()
                }

                // Convert VAPID key and subscribe
                const appServerKey = urlBase64ToUint8Array(vapidKey)
                console.log('[Push] applicationServerKey length:', appServerKey.length, 'bytes')

                const subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: appServerKey,
                })
                console.log('[Push] Subscribed successfully:', subscription.endpoint)

                // 4. Send subscription to backend
                const subJson = subscription.toJSON()
                await apiRequest('/api/push/subscribe', {
                    method: 'POST',
                    body: JSON.stringify({
                        endpoint: subJson.endpoint,
                        p256dh: subJson.keys?.p256dh,
                        auth: subJson.keys?.auth,
                        alert_days: alertDays.join(','),
                    }),
                })

                setIsSubscribed(true)
            } catch (err: any) {
                console.error('[Push] Error completo:', err)
                console.error('[Push] name:', err.name, 'message:', err.message)

                const raw = err.message || String(err)
                let userMessage = raw // Mostrar error real para diagnostico
                if (raw.includes('permission') || raw.includes('denied')) {
                    userMessage = 'Permiso de notificaciones denegado'
                }
                setError(userMessage)
            } finally {
                setLoading(false)
            }
        },
        [isSupported, apiRequest]
    )

    const unsubscribe = useCallback(async () => {
        if (!isSupported) return

        setLoading(true)
        setError(null)

        try {
            const registration = await navigator.serviceWorker.ready
            const subscription = await registration.pushManager.getSubscription()

            if (!subscription) {
                setIsSubscribed(false)
                return
            }

            const endpoint = subscription.endpoint

            // Unsubscribe from browser push manager
            await subscription.unsubscribe()

            // Remove from backend
            await apiRequest('/api/push/unsubscribe', {
                method: 'DELETE',
                body: JSON.stringify({ endpoint }),
            })

            setIsSubscribed(false)
        } catch (err: any) {
            setError(err.message || 'Error al desactivar notificaciones')
        } finally {
            setLoading(false)
        }
    }, [isSupported, apiRequest])

    return {
        isSupported,
        permission,
        isSubscribed,
        subscribe,
        unsubscribe,
        loading,
        error,
    }
}
