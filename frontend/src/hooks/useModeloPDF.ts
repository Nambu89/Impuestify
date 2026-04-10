import { useState, useCallback } from 'react'
import { useApi } from './useApi'

interface UseModeloPDFReturn {
    downloadPDF: (
        modelo: string,
        data: Record<string, any>,
        trimestre: string,
        ejercicio: number,
        contribuyente?: { nombre?: string; nif?: string },
    ) => Promise<void>
    isLoading: boolean
    error: string | null
}

const API_URL = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'access_token'

export function useModeloPDF(): UseModeloPDFReturn {
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const downloadPDF = useCallback(async (
        modelo: string,
        data: Record<string, any>,
        trimestre: string,
        ejercicio: number,
        contribuyente?: { nombre?: string; nif?: string },
    ) => {
        setIsLoading(true)
        setError(null)

        try {
            const token = localStorage.getItem(TOKEN_KEY)
            if (!token) {
                window.location.href = '/login?expired=true'
                setIsLoading(false)
                return
            }

            const response = await fetch(`${API_URL}/export/modelo-pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    modelo,
                    data,
                    trimestre,
                    ejercicio,
                    ...(contribuyente && { contribuyente }),
                }),
            })

            if (response.status === 401) {
                localStorage.removeItem(TOKEN_KEY)
                localStorage.removeItem('refresh_token')
                window.location.href = '/login?expired=true'
                return
            }

            if (!response.ok) {
                const contentType = response.headers.get('content-type')
                if (contentType && contentType.includes('application/json')) {
                    const err = await response.json()
                    throw new Error(err.detail || `Error ${response.status}`)
                }
                throw new Error(`Error ${response.status} al generar el PDF`)
            }

            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.download = `Modelo_${modelo}_${trimestre}_${ejercicio}.pdf`
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            window.URL.revokeObjectURL(url)
        } catch (err: any) {
            setError(err.message || 'Error al descargar el PDF')
        } finally {
            setIsLoading(false)
        }
    }, [])

    return { downloadPDF, isLoading, error }
}
