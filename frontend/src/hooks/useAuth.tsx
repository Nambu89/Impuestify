import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import axios from 'axios'
import { logger } from '../utils/logger'

interface User {
    id: string
    email: string
    name?: string
    is_admin?: boolean | number
    is_owner?: boolean
    subscription_status?: string | null
}

interface AuthContextType {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean
    login: (email: string, password: string, turnstile_token?: string) => Promise<void>
    googleLogin: (idToken: string) => Promise<void>
    completeMfaLogin: (mfaToken: string, code: string) => Promise<void>
    register: (email: string, password: string, name?: string, ccaa_residencia?: string, turnstile_token?: string) => Promise<void>
    logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const API_URL = import.meta.env.VITE_API_URL || '/api'

const TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

const authApi = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json'
    }
})

authApi.interceptors.request.use((config) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
        logger.debug('Auth token attached')
    }
    return config
})

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    const fetchCurrentUser = useCallback(async () => {
        logger.debug('Fetching current user')
        try {
            const response = await authApi.get('/auth/me')
            logger.debug('User fetched:', response.data.email)
            setUser(response.data)
        } catch (error: any) {
            // If 401, try refreshing the token before giving up
            const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
            if (error?.response?.status === 401 && refreshToken) {
                logger.debug('Access token expired, attempting refresh')
                try {
                    const refreshRes = await authApi.post('/auth/refresh', {
                        refresh_token: refreshToken
                    })
                    const { access_token, refresh_token } = refreshRes.data.tokens || refreshRes.data
                    localStorage.setItem(TOKEN_KEY, access_token)
                    if (refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token)

                    // Retry /auth/me with new token
                    const retryRes = await authApi.get('/auth/me', {
                        headers: { Authorization: `Bearer ${access_token}` }
                    })
                    logger.debug('User fetched after refresh:', retryRes.data.email)
                    setUser(retryRes.data)
                } catch (refreshError) {
                    logger.error('Token refresh failed:', refreshError)
                    localStorage.removeItem(TOKEN_KEY)
                    localStorage.removeItem(REFRESH_TOKEN_KEY)
                }
            } else {
                logger.error('Failed to fetch user:', error)
                localStorage.removeItem(TOKEN_KEY)
                localStorage.removeItem(REFRESH_TOKEN_KEY)
            }
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        const token = localStorage.getItem(TOKEN_KEY)
        logger.debug('Checking for token on mount:', !!token)
        if (token) {
            fetchCurrentUser()
        } else {
            setIsLoading(false)
        }
    }, [fetchCurrentUser])

    const login = async (email: string, password: string, turnstile_token?: string) => {
        logger.debug('Logging in:', email)
        try {
            const response = await authApi.post('/auth/login', {
                email,
                password,
                ...(turnstile_token && { turnstile_token }),
            })

            // MFA required — throw special error with mfa_token
            if (response.data.mfa_required) {
                const mfaError: any = new Error('MFA_REQUIRED')
                mfaError.mfa_token = response.data.mfa_token
                throw mfaError
            }

            const { user, tokens } = response.data

            logger.debug('Login successful')
            localStorage.setItem(TOKEN_KEY, tokens.access_token)
            localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
            setUser(user)
        } catch (error) {
            logger.error('Login failed:', error)
            throw error
        }
    }

    const googleLogin = async (idToken: string) => {
        logger.debug('Google SSO login')
        try {
            const response = await authApi.post('/auth/google', { id_token: idToken })

            // MFA required
            if (response.data.mfa_required) {
                const mfaError: any = new Error('MFA_REQUIRED')
                mfaError.mfa_token = response.data.mfa_token
                throw mfaError
            }

            const { user, tokens } = response.data

            logger.debug('Google login successful')
            localStorage.setItem(TOKEN_KEY, tokens.access_token)
            localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
            setUser(user)
        } catch (error) {
            logger.error('Google login failed:', error)
            throw error
        }
    }

    const completeMfaLogin = async (mfaToken: string, code: string) => {
        const response = await authApi.post('/auth/mfa/validate', {
            mfa_token: mfaToken,
            code,
        })
        const { user, tokens } = response.data
        localStorage.setItem(TOKEN_KEY, tokens.access_token)
        localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
        setUser(user)
    }

    const register = async (email: string, password: string, name?: string, ccaa_residencia?: string, turnstile_token?: string) => {
        logger.debug('Registering:', email)
        try {
            const response = await authApi.post('/auth/register', {
                email,
                password,
                name,
                ...(ccaa_residencia && { ccaa_residencia }),
                ...(turnstile_token && { turnstile_token }),
            })

            const { user, tokens } = response.data

            logger.debug('Registration successful')
            localStorage.setItem(TOKEN_KEY, tokens.access_token)
            localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
            setUser(user)
        } catch (error) {
            logger.error('Registration failed:', error)
            throw error
        }
    }

    const logout = () => {
        logger.debug('Logging out')
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(REFRESH_TOKEN_KEY)
        setUser(null)
    }

    return (
        <AuthContext.Provider value={{
            user,
            isAuthenticated: !!user,
            isLoading,
            login,
            googleLogin,
            completeMfaLogin,
            register,
            logout
        }}>
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}