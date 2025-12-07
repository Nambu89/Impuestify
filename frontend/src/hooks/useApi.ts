import axios, { AxiosError } from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

// Create axios instance with interceptors
const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json'
    }
})

// Request interceptor - add auth token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Response interceptor - handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as any

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true

            try {
                const refreshToken = localStorage.getItem('refresh_token')
                if (refreshToken) {
                    const response = await axios.post(`${API_URL}/auth/refresh`, {
                        refresh_token: refreshToken
                    })

                    const { access_token, refresh_token } = response.data
                    localStorage.setItem('access_token', access_token)
                    localStorage.setItem('refresh_token', refresh_token)

                    originalRequest.headers.Authorization = `Bearer ${access_token}`
                    return api(originalRequest)
                }
            } catch (refreshError) {
                // Refresh failed, clear tokens
                localStorage.removeItem('access_token')
                localStorage.removeItem('refresh_token')
                window.location.href = '/login'
            }
        }

        return Promise.reject(error)
    }
)

export interface AskResponse {
    answer: string
    sources: Array<{
        id: string
        source: string
        page: number
        title: string
        text_preview: string
    }>
    metadata: Record<string, any>
    processing_time: number
    cached: boolean
}

export interface StatsResponse {
    total_chunks: number
    total_documents: number
    embedding_model: string
    cache_stats?: {
        hits: number
        misses: number
    }
}

export function useApi() {
    const askQuestion = async (question: string, k?: number): Promise<AskResponse> => {
        try {
            const response = await api.post('/ask', {
                question,
                k,
                enable_cache: true
            })
            return response.data
        } catch (error: any) {
            const message = error.response?.data?.detail || error.message || 'Error de conexión'
            throw new Error(message)
        }
    }

    const getStats = async (): Promise<StatsResponse> => {
        try {
            const response = await api.get('/stats')
            return response.data
        } catch (error: any) {
            const message = error.response?.data?.detail || error.message
            throw new Error(message)
        }
    }

    const getHealth = async () => {
        try {
            const response = await api.get('/health')
            return response.data
        } catch (error: any) {
            throw new Error('El servidor no está disponible')
        }
    }

    return {
        askQuestion,
        getStats,
        getHealth
    }
}
