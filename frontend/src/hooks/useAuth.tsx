import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import axios from 'axios'
import { logger } from '../utils/logger'

interface User {
    id: string
    email: string
    name?: string
    is_admin?: boolean | number
}

interface AuthContextType {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean
    login: (email: string, password: string) => Promise<void>
    register: (email: string, password: string, name?: string) => Promise<void>
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
        } catch (error) {
            logger.error('Failed to fetch user:', error)
            localStorage.removeItem(TOKEN_KEY)
            localStorage.removeItem(REFRESH_TOKEN_KEY)
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

    const login = async (email: string, password: string) => {
        logger.debug('Logging in:', email)
        try {
            const response = await authApi.post('/auth/login', {
                email,
                password
            })

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

    const register = async (email: string, password: string, name?: string) => {
        logger.debug('Registering:', email)
        try {
            const response = await authApi.post('/auth/register', {
                email,
                password,
                name
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