import { useEffect, useRef, useCallback } from 'react'

interface TurnstileWidgetProps {
    onVerify: (token: string) => void
    onExpire?: () => void
    onError?: () => void
}

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || ''

declare global {
    interface Window {
        turnstile?: {
            render: (container: string | HTMLElement, options: Record<string, unknown>) => string
            reset: (widgetId: string) => void
            remove: (widgetId: string) => void
        }
        onTurnstileLoad?: () => void
    }
}

export default function TurnstileWidget({ onVerify, onExpire, onError }: TurnstileWidgetProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const widgetIdRef = useRef<string | null>(null)

    const renderWidget = useCallback(() => {
        if (!containerRef.current || !window.turnstile || !SITE_KEY) return
        if (widgetIdRef.current) return // already rendered

        widgetIdRef.current = window.turnstile.render(containerRef.current, {
            sitekey: SITE_KEY,
            callback: (token: string) => onVerify(token),
            'expired-callback': () => onExpire?.(),
            'error-callback': () => onError?.(),
            theme: 'dark',
            language: 'es',
        })
    }, [onVerify, onExpire, onError])

    useEffect(() => {
        // If turnstile script already loaded
        if (window.turnstile) {
            renderWidget()
            return
        }

        // Load script if not present
        const existingScript = document.querySelector('script[src*="turnstile"]')
        if (!existingScript) {
            const script = document.createElement('script')
            script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad'
            script.async = true
            script.defer = true
            document.head.appendChild(script)
        }

        // Callback when script loads
        window.onTurnstileLoad = () => renderWidget()

        return () => {
            if (widgetIdRef.current && window.turnstile) {
                window.turnstile.remove(widgetIdRef.current)
                widgetIdRef.current = null
            }
        }
    }, [renderWidget])

    if (!SITE_KEY) return null

    return <div ref={containerRef} style={{ margin: '12px 0' }} />
}
