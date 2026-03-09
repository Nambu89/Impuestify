import { Bell, BellOff, X } from 'lucide-react'
import { useState } from 'react'
import { usePushNotifications } from '../hooks/usePushNotifications'
import './PushPermissionBanner.css'

interface PushPermissionBannerProps {
    /** Called when the user dismisses the banner (not the same as denying permission) */
    onDismiss?: () => void
}

export default function PushPermissionBanner({ onDismiss }: PushPermissionBannerProps) {
    const { isSupported, permission, isSubscribed, subscribe, loading, error } =
        usePushNotifications()

    const [dismissed, setDismissed] = useState(false)

    const handleDismiss = () => {
        setDismissed(true)
        onDismiss?.()
    }

    // Do not render if: unsupported, already subscribed, dismissed, or granted (no need to show)
    if (!isSupported || isSubscribed || dismissed) return null

    // Permission was explicitly denied — show informative message (cannot ask again)
    if (permission === 'denied') {
        return (
            <div className="push-banner push-banner--denied">
                <BellOff size={18} className="push-banner__icon" />
                <p className="push-banner__text">
                    Notificaciones bloqueadas. Activalas en los ajustes de tu navegador para
                    recibir alertas de plazos fiscales.
                </p>
                <button
                    className="push-banner__dismiss"
                    onClick={handleDismiss}
                    aria-label="Cerrar aviso"
                >
                    <X size={16} />
                </button>
            </div>
        )
    }

    // Default / granted but not subscribed — show activation prompt
    return (
        <div className="push-banner push-banner--default">
            <Bell size={18} className="push-banner__icon" />
            <div className="push-banner__content">
                <p className="push-banner__text">
                    Activa las notificaciones para no perderte ningun plazo fiscal
                </p>
                {error && <p className="push-banner__error">{error}</p>}
            </div>
            <button
                className="push-banner__action"
                onClick={() => subscribe()}
                disabled={loading}
            >
                {loading ? 'Activando...' : 'Activar'}
            </button>
            <button
                className="push-banner__dismiss"
                onClick={handleDismiss}
                aria-label="Cerrar banner"
            >
                <X size={16} />
            </button>
        </div>
    )
}
