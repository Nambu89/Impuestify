import { createContext, useContext, useState } from 'react'
import type { GestoriaClient } from '../hooks/useGestoriaClients'

interface ActiveClientCtx {
    activeClient: GestoriaClient | null
    setActiveClient: (c: GestoriaClient | null) => void
}

const Ctx = createContext<ActiveClientCtx | undefined>(undefined)
const KEY = 'gestoria_active_client'

export function ActiveClientProvider({ children }: { children: React.ReactNode }) {
    const [activeClient, setActiveClientState] = useState<GestoriaClient | null>(() => {
        try {
            const raw = localStorage.getItem(KEY)
            return raw ? (JSON.parse(raw) as GestoriaClient) : null
        } catch {
            return null
        }
    })

    const setActiveClient = (c: GestoriaClient | null) => {
        setActiveClientState(c)
        if (c) localStorage.setItem(KEY, JSON.stringify(c))
        else localStorage.removeItem(KEY)
    }

    return <Ctx.Provider value={{ activeClient, setActiveClient }}>{children}</Ctx.Provider>
}

export function useActiveClient() {
    const ctx = useContext(Ctx)
    if (!ctx) throw new Error('useActiveClient must be used within ActiveClientProvider')
    return ctx
}
