import { useCallback, useState } from 'react'
import { useApi } from './useApi'

export type ClientTipo = 'particular' | 'autonomo' | 'sociedad'

export interface GestoriaClient {
    id: string
    nombre_cliente: string
    tipo: ClientTipo
    nif?: string | null
    ccaa?: string | null
    situacion_laboral?: string | null
    epigrafe_iae?: string | null
    regimen_iva?: string | null
    fecha_alta?: string | null
    datos_fiscales?: Record<string, unknown>
    file_count?: number
    declaration_count?: number
    ingresos_total?: number
    iva_balance?: number
    created_at?: string | null
    updated_at?: string | null
}

export interface GestoriaClientInput {
    nombre_cliente: string
    tipo: ClientTipo
    nif?: string
    ccaa?: string
    situacion_laboral?: string
    epigrafe_iae?: string
    regimen_iva?: string
    fecha_alta?: string
    datos_fiscales?: Record<string, unknown>
}

export function useGestoriaClients() {
    const { apiRequest } = useApi()
    const [clients, setClients] = useState<GestoriaClient[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const fetchClients = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<GestoriaClient[]>('/api/gestoria/clients', {
                method: 'GET',
            })
            setClients(data || [])
            return data
        } catch (err: any) {
            setError(err.message || 'Error al cargar los clientes')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const createClient = useCallback(
        async (input: GestoriaClientInput) => {
            setLoading(true)
            setError(null)
            try {
                const created = await apiRequest<GestoriaClient>('/api/gestoria/clients', {
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
            } catch (err: any) {
                setError(err.message || 'Error al eliminar el cliente')
                throw err
            } finally {
                setLoading(false)
            }
        },
        [apiRequest],
    )

    return { clients, loading, error, fetchClients, createClient, updateClient, deleteClient }
}
