import { useState, useCallback } from 'react'
import { useApi } from './useApi'

// ---------------------------------------------------------------------------
// Types — aligned with backend/app/routers/crypto.py response models
// ---------------------------------------------------------------------------

export interface CryptoTransaction {
    id: string
    exchange: string
    tx_type: string       // buy | sell | trade | transfer | staking | mining | fee
    date_utc: string
    asset: string
    amount: number
    price_eur: number | null
    total_eur: number | null
    fee_eur: number | null
    counterpart_asset?: string | null
    counterpart_amount?: number | null
    notes?: string | null
}

export interface CryptoHolding {
    asset: string
    total_units: number
    avg_cost_eur: number
    total_invested_eur: number
}

export interface CryptoGain {
    asset: string
    tx_type: string
    clave_contraprestacion: string  // F | N | O | B
    date_acquisition: string
    date_transmission: string
    acquisition_value_eur: number
    acquisition_fees_eur: number
    transmission_value_eur: number
    transmission_fees_eur: number
    gain_loss_eur: number
    anti_aplicacion: boolean
}

interface GainsSummaryBackend {
    casilla_1813: number  // perdidas
    casilla_1814: number  // ganancias
    net: number
    total_transactions: number
}

export interface CryptoGainsSummary {
    tax_year: number
    total_gains_eur: number      // Casilla 1814
    total_losses_eur: number     // Casilla 1813 (positive value)
    net_eur: number
    gains: CryptoGain[]
}

// Backend response shapes
interface TransactionsResponse {
    success: boolean
    transactions: CryptoTransaction[]
    total: number
    page: number
    per_page: number
}

interface HoldingsResponse {
    success: boolean
    holdings: CryptoHolding[]
    total_invested_eur: number
}

interface GainsResponse {
    success: boolean
    tax_year: number
    gains: CryptoGain[]
    summary: GainsSummaryBackend
}

export interface UploadResult {
    success: boolean
    imported: number
    duplicates_skipped: number
    exchange_detected: string
    date_range: Record<string, string>
    error?: string | null
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

interface UseCryptoResult {
    transactions: CryptoTransaction[]
    totalTransactions: number
    currentPage: number
    holdings: CryptoHolding[]
    totalInvestedEur: number
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
    const [totalInvestedEur, setTotalInvestedEur] = useState(0)
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
            const data = await apiRequest<TransactionsResponse>(
                `/api/crypto/transactions?page=${page}&per_page=${PAGE_SIZE}`
            )
            setTransactions(data.transactions ?? [])
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
            const data = await apiRequest<HoldingsResponse>('/api/crypto/holdings')
            setHoldings(data.holdings ?? [])
            setTotalInvestedEur(data.total_invested_eur ?? 0)
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
            const data = await apiRequest<GainsResponse>(
                `/api/crypto/gains?tax_year=${taxYear}`
            )
            setGainsSummary({
                tax_year: data.tax_year,
                total_gains_eur: data.summary.casilla_1814,
                total_losses_eur: Math.abs(data.summary.casilla_1813),
                net_eur: data.summary.net,
                gains: data.gains ?? [],
            })
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
            const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/api$/, '')

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
                    throw new Error('Sesion expirada')
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
            setErrorTransactions(err.message || 'Error eliminando transaccion')
            return false
        }
    }, [apiRequest])

    return {
        transactions,
        totalTransactions,
        currentPage,
        holdings,
        totalInvestedEur,
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
