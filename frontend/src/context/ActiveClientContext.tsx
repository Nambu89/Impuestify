import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import { useApi } from '../hooks/useApi'
import type { GestoriaClient, GestoriaClientInput } from '../hooks/useGestoriaClients'

interface ActiveClientCtx {
    activeClient: GestoriaClient | null
    setActiveClient: (c: GestoriaClient | null) => void
    clients: GestoriaClient[]
    loading: boolean
    error: string | null
    fetchClients: () => Promise<GestoriaClient[] | undefined>
    createClient: (input: GestoriaClientInput) => Promise<GestoriaClient>
    updateClient: (id: string, input: Partial<GestoriaClientInput>) => Promise<GestoriaClient>
    deleteClient: (id: string) => Promise<void>
}

const Ctx = createContext<ActiveClientCtx | undefined>(undefined)
const KEY = 'gestoria_active_client'

export function ActiveClientProvider({ children }: { children: React.ReactNode }) {
    const { user } = useAuth()
    const { apiRequest } = useApi()
    const isGestoria = user?.account_type === 'gestoria'

    const [activeClient, setActiveClientState] = useState<GestoriaClient | null>(() => {
        try {
            const raw = localStorage.getItem(KEY)
            return raw ? (JSON.parse(raw) as GestoriaClient) : null
        } catch {
            return null
        }
    })
    const [clients, setClients] = useState<GestoriaClient[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const setActiveClient = (c: GestoriaClient | null) => {
        setActiveClientState(c)
        if (c) localStorage.setItem(KEY, JSON.stringify(c))
        else localStorage.removeItem(KEY)
    }

    const fetchClients = useCallback(async () => {
        if (!isGestoria) return undefined
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<GestoriaClient[]>('/gestoria/clients', {
                method: 'GET',
            })
            setClients(data || [])
            return data
        } catch (err: any) {
            setError(err.message || 'Error al cargar los clientes')
        } finally {
            setLoading(false)
        }
    }, [isGestoria, apiRequest])

    const createClient = useCallback(
        async (input: GestoriaClientInput) => {
            setLoading(true)
            setError(null)
            try {
                const created = await apiRequest<GestoriaClient>('/gestoria/clients', {
                    method: 'POST',
                    body: JSON.stringify(input),
                })
                setClients((prev) => [created, ...prev])
                return created
            } catch (err: any) {
                setError(err.message || 'Error al crear el cliente')
                throw err
            } finally {
                setLoading(false)
            }
        },
        [apiRequest],
    )

    const updateClient = useCallback(
        async (id: string, input: Partial<GestoriaClientInput>) => {
            setLoading(true)
            setError(null)
            try {
                const updated = await apiRequest<GestoriaClient>(`/api/gestoria/clients/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify(input),
                })
                setClients((prev) => prev.map((c) => (c.id === id ? updated : c)))
                setActiveClientState((prev) => {
                    if (prev?.id === id) {
                        localStorage.setItem(KEY, JSON.stringify(updated))
                        return updated
                    }
                    return prev
                })
                return updated
            } catch (err: any) {
                setError(err.message || 'Error al actualizar el cliente')
                throw err
            } finally {
                setLoading(false)
            }
        },
        [apiRequest],
    )

    const deleteClient = useCallback(
        async (id: string) => {
            setLoading(true)
            setError(null)
            try {
                await apiRequest(`/api/gestoria/clients/${id}`, { method: 'DELETE' })
                setClients((prev) => prev.filter((c) => c.id !== id))
                setActiveClientState((prev) => {
                    if (prev?.id === id) {
                        localStorage.removeItem(KEY)
                        return null
                    }
                    return prev
                })
            } catch (err: any) {
                setError(err.message || 'Error al eliminar el cliente')
                throw err
            } finally {
                setLoading(false)
            }
        },
        [apiRequest],
    )

    useEffect(() => {
        if (isGestoria) {
            void fetchClients()
        }
    }, [isGestoria, fetchClients])

    return (
        <Ctx.Provider
            value={{
                activeClient,
                setActiveClient,
                clients,
                loading,
                error,
                fetchClients,
                createClient,
                updateClient,
                deleteClient,
            }}
        >
            {children}
        </Ctx.Provider>
    )
}

export function useActiveClient() {
    const ctx = useContext(Ctx)
    if (!ctx) throw new Error('useActiveClient must be used within ActiveClientProvider')
    return ctx
}
