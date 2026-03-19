import { useEffect, useRef, useCallback } from 'react'

interface TurnstileWidgetProps {
    onVerify: (token: string) => void
    onExpire?: () => void
    onError?: () => void
}

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || ''
const TEST_MODE = import.meta.env.VITE_TURNSTILE_TEST_MODE === 'true'
// Cloudflare's official always-passing test token (public documentation)
const TEST_TOKEN = '1x00000000000000000000AA'

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

    // In test mode: skip the widget entirely and fire the callback immediately
    // with Cloudflare's official always-passing test token. This hook must be
    // declared unconditionally (Rules of Hooks) — the TEST_MODE guard is inside.
    useEffect(() => {
        if (TEST_MODE) {
            onVerify(TEST_TOKEN)
        }
    }, [onVerify])

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
        // Skip Cloudflare widget setup entirely in test mode
        if (TEST_MODE) return

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

    // In test mode, render nothing (the onVerify callback was already fired above)
    if (TEST_MODE) return null
    if (!SITE_KEY) return null

    return <div ref={containerRef} style={{ margin: '12px 0' }} />
}
