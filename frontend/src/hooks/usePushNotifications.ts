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

                // Clear any stale subscription
                const existingSub = await registration.pushManager.getSubscription()
                if (existingSub) {
                    await existingSub.unsubscribe()
                }

                // Check push permission state before attempting subscribe
                const pushPermState = await registration.pushManager.permissionState({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(vapidKey),
                })

                if (pushPermState === 'denied') {
                    setError('Las notificaciones push están bloqueadas en tu navegador. Revisa Configuración → Privacidad → Notificaciones.')
                    return
                }

                // Attempt subscription with retry (some browsers need a second attempt)
                const appServerKey = urlBase64ToUint8Array(vapidKey)
                let subscription: PushSubscription
                try {
                    subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: appServerKey,
                    })
                } catch (firstErr: any) {
                    // Retry once after a brief pause — FCM can be flaky on first attempt
                    await new Promise(r => setTimeout(r, 1500))
                    subscription = await registration.pushManager.subscribe({
                        userVisibleOnly: true,
                        applicationServerKey: appServerKey,
                    })
                }

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
                const raw = err.message || String(err)

                let userMessage: string
                if (raw.includes('permission') || raw.includes('denied')) {
                    userMessage = 'Permiso de notificaciones denegado'
                } else if (raw.includes('push service error') || raw.includes('Registration failed')) {
                    userMessage = (
                        'No se pudo conectar con el servicio de notificaciones (FCM). ' +
                        'Prueba a: 1) Desactivar extensiones del navegador (MetaMask, ad blockers), ' +
                        '2) Comprobar que las notificaciones de Chrome están activadas en Windows (Configuración → Sistema → Notificaciones), ' +
                        '3) Intentarlo en una ventana sin extensiones.'
                    )
                } else {
                    userMessage = raw
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
