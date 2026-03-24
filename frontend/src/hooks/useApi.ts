import axios, { AxiosError } from 'axios'
import { useCallback } from 'react'
import { logger } from '../utils/logger'

const API_URL = import.meta.env.VITE_API_URL || '/api'

// ✅ FIX: Usar nombres consistentes para tokens
const TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

// Create axios instance with interceptors
const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json'
    }
})

// Request interceptor - add auth token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
        logger.debug('Token attached to request')
    }
    return config
})

// Response interceptor - handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as any

        if (error.response?.status === 401 && !originalRequest._retry) {
            logger.debug('401 received, attempting token refresh')
            originalRequest._retry = true

            try {
                const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
                if (refreshToken) {
                    const response = await axios.post(`${API_URL}/auth/refresh`, {
                        refresh_token: refreshToken
                    })

                    const { access_token, refresh_token } = response.data
                    localStorage.setItem(TOKEN_KEY, access_token)
                    localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)

                    logger.debug('Token refreshed successfully')

                    originalRequest.headers.Authorization = `Bearer ${access_token}`
                    return api(originalRequest)
                }
            } catch (refreshError) {
                logger.error('Token refresh failed:', refreshError)
                // Refresh failed, clear tokens
                localStorage.removeItem(TOKEN_KEY)
                localStorage.removeItem(REFRESH_TOKEN_KEY)
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
    conversation_id?: string
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
    const askQuestion = useCallback(async (question: string, conversationId?: string, k?: number): Promise<AskResponse> => {
        logger.debug('Sending question:', { question: question.substring(0, 50), conversationId })
        try {
            const response = await api.post('/api/ask', {
                question,
                conversation_id: conversationId,
                k,
                enable_cache: true
            })
            logger.debug('Question response received:', { conversation_id: response.data.conversation_id })
            return response.data
        } catch (error: any) {
            logger.error('Error in askQuestion:', error)
            // Auto-logout on 401
            if (error.response?.status === 401) {
                localStorage.removeItem(TOKEN_KEY)
                localStorage.removeItem(REFRESH_TOKEN_KEY)
                window.location.href = '/login?expired=true'
                throw new Error('Tu sesión ha expirado. Redirigiendo al login...')
            }

            const message = error.response?.data?.detail || error.message || 'Error de conexión'
            throw new Error(message)
        }
    }, [])

    const getHealth = useCallback(async () => {
        try {
            const response = await api.get('/health')
            return response.data
        } catch (error: any) {
            throw new Error('El servidor no está disponible')
        }
    }, [])

    const apiRequest = useCallback(async <T = any>(url: string, options?: RequestInit & { timeout?: number }): Promise<T> => {
        logger.debug('API Request:', url, options?.method || 'GET')

        const controller = new AbortController()
        const timeoutMs = options?.timeout || 30000
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

        try {
            const token = localStorage.getItem(TOKEN_KEY)

            const headers = {
                'Content-Type': 'application/json',
                ...(token && { Authorization: `Bearer ${token}` }),
                ...options?.headers
            }

            const response = await fetch(`${API_URL}${url}`, {  // ✅ Prefijo con API_URL
                ...options,
                headers,
                signal: controller.signal
            })

            logger.debug('API Response:', url, response.status)

            if (!response.ok) {
                if (response.status === 401) {
                    logger.warn('401 Unauthorized for:', url)
                    localStorage.removeItem(TOKEN_KEY)
                    localStorage.removeItem(REFRESH_TOKEN_KEY)
                    window.location.href = '/login?expired=true'
                    throw new Error('Tu sesión ha expirado')
                }

                const contentType = response.headers.get('content-type')
                if (contentType && contentType.includes('application/json')) {
                    const error = await response.json()
                    throw new Error(error.detail || 'Request failed')
                } else {
                    // HTML error page (probably)
                    const text = await response.text()
                    logger.error('Non-JSON error response:', text.substring(0, 200))
                    throw new Error(`HTTP ${response.status}: Request failed`)
                }
            }

            // Handle 204 No Content
            if (response.status === 204) {
                return null as T
            }

            return await response.json()
        } catch (error: any) {
            if (error.name === 'AbortError') {
                logger.warn('apiRequest timeout:', url)
                throw new Error('La solicitud tardó demasiado. Inténtalo de nuevo.')
            }
            logger.error('apiRequest error:', error)
            throw new Error(error.message || 'Error de conexión')
        } finally {
            clearTimeout(timeoutId)
        }
    }, [])

    return {
        askQuestion,
        getHealth,
        apiRequest
    }
}