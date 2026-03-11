import { useState, useCallback } from 'react'
import { useApi } from './useApi'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CryptoTransaction {
    id: string
    user_id: string
    exchange: string
    date: string
    type: string          // buy | sell | trade | transfer | staking | mining | fee
    asset: string
    quantity: number
    price_eur: number
    total_eur: number
    fee_eur: number
    notes?: string
    created_at: string
}

export interface CryptoHolding {
    asset: string
    total_units: number
    avg_cost_eur: number
    total_invested_eur: number
    exchange?: string
}

export interface CryptoGain {
    asset: string
    buy_date: string
    sell_date: string
    quantity: number
    acquisition_value_eur: number
    transmission_value_eur: number
    gain_loss_eur: number
    clave_contraprestacion: string  // F | N | O | B
}

export interface CryptoGainsSummary {
    tax_year: number
    total_gains_eur: number      // Casilla 1814
    total_losses_eur: number     // Casilla 1813 (positive value)
    net_eur: number
    gains: CryptoGain[]
    modelo_721_required: boolean
}

export interface CryptoTransactionsPage {
    items: CryptoTransaction[]
    total: number
    page: number
    page_size: number
}

export interface UploadResult {
    success: boolean
    imported: number
    exchange: string
    errors?: string[]
    message?: string
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseCryptoResult {
    transactions: CryptoTransaction[]
    totalTransactions: number
    currentPage: number
    holdings: CryptoHolding[]
    gainsSummary: CryptoGainsSummary | null

    loadingTransactions: boolean
    loadingHoldings: boolean
    loadingGains: boolean
    uploading: boolean

    errorTransactions: string | null
    errorHoldings: string | null
    errorGains: string | null
    errorUpload: string | null

    fetchTransactions: (page?: number) => Promise<void>
    fetchHoldings: () => Promise<void>
    fetchGains: (taxYear: number) => Promise<void>
    uploadFile: (file: File) => Promise<UploadResult | null>
    deleteTransaction: (id: string) => Promise<boolean>
}

const PAGE_SIZE = 20

export function useCrypto(): UseCryptoResult {
    const { apiRequest } = useApi()

    // Transactions state
    const [transactions, setTransactions] = useState<CryptoTransaction[]>([])
    const [totalTransactions, setTotalTransactions] = useState(0)
    const [currentPage, setCurrentPage] = useState(1)
    const [loadingTransactions, setLoadingTransactions] = useState(false)
    const [errorTransactions, setErrorTransactions] = useState<string | null>(null)

    // Holdings state
    const [holdings, setHoldings] = useState<CryptoHolding[]>([])
    const [loadingHoldings, setLoadingHoldings] = useState(false)
    const [errorHoldings, setErrorHoldings] = useState<string | null>(null)

    // Gains state
    const [gainsSummary, setGainsSummary] = useState<CryptoGainsSummary | null>(null)
    const [loadingGains, setLoadingGains] = useState(false)
    const [errorGains, setErrorGains] = useState<string | null>(null)

    // Upload state
    const [uploading, setUploading] = useState(false)
    const [errorUpload, setErrorUpload] = useState<string | null>(null)

    // -----------------------------------------------------------------------

    const fetchTransactions = useCallback(async (page = 1) => {
        setLoadingTransactions(true)
        setErrorTransactions(null)
        try {
            const data = await apiRequest<CryptoTransactionsPage>(
                `/api/crypto/transactions?page=${page}&page_size=${PAGE_SIZE}`
            )
            setTransactions(data.items)
            setTotalTransactions(data.total)
            setCurrentPage(data.page)
        } catch (err: any) {
            setErrorTransactions(err.message || 'Error cargando transacciones')
        } finally {
            setLoadingTransactions(false)
        }
    }, [apiRequest])

    const fetchHoldings = useCallback(async () => {
        setLoadingHoldings(true)
        setErrorHoldings(null)
        try {
            const data = await apiRequest<CryptoHolding[]>('/api/crypto/holdings')
            setHoldings(data)
        } catch (err: any) {
            setErrorHoldings(err.message || 'Error cargando portfolio')
        } finally {
            setLoadingHoldings(false)
        }
    }, [apiRequest])

    const fetchGains = useCallback(async (taxYear: number) => {
        setLoadingGains(true)
        setErrorGains(null)
        try {
            const data = await apiRequest<CryptoGainsSummary>(
                `/api/crypto/gains?tax_year=${taxYear}`
            )
            setGainsSummary(data)
        } catch (err: any) {
            setErrorGains(err.message || 'Error cargando ganancias fiscales')
        } finally {
            setLoadingGains(false)
        }
    }, [apiRequest])

    const uploadFile = useCallback(async (file: File): Promise<UploadResult | null> => {
        setUploading(true)
        setErrorUpload(null)
        try {
            const TOKEN_KEY = 'access_token'
            const token = localStorage.getItem(TOKEN_KEY)
            const API_URL = import.meta.env.VITE_API_URL || '/api'

            const formData = new FormData()
            formData.append('file', file)

            const response = await fetch(`${API_URL}/api/crypto/upload`, {
                method: 'POST',
                headers: {
                    ...(token && { Authorization: `Bearer ${token}` }),
                },
                body: formData,
            })

            if (!response.ok) {
                if (response.status === 401) {
                    localStorage.removeItem(TOKEN_KEY)
                    window.location.href = '/login?expired=true'
                    throw new Error('Sesión expirada')
                }
                const err = await response.json().catch(() => ({}))
                throw new Error(err.detail || `Error ${response.status}`)
            }

            const result = await response.json() as UploadResult
            return result
        } catch (err: any) {
            setErrorUpload(err.message || 'Error subiendo archivo')
            return null
        } finally {
            setUploading(false)
        }
    }, [])

    const deleteTransaction = useCallback(async (id: string): Promise<boolean> => {
        try {
            await apiRequest(`/api/crypto/transactions/${id}`, { method: 'DELETE' })
            setTransactions((prev) => prev.filter((t) => t.id !== id))
            setTotalTransactions((prev) => Math.max(0, prev - 1))
            return true
        } catch (err: any) {
            setErrorTransactions(err.message || 'Error eliminando transacción')
            return false
        }
    }, [apiRequest])

    return {
        transactions,
        totalTransactions,
        currentPage,
        holdings,
        gainsSummary,

        loadingTransactions,
        loadingHoldings,
        loadingGains,
        uploading,

        errorTransactions,
        errorHoldings,
        errorGains,
        errorUpload,

        fetchTransactions,
        fetchHoldings,
        fetchGains,
        uploadFile,
        deleteTransaction,
    }
}
