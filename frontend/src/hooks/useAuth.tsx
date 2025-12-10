import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import axios from 'axios'

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
        console.log('🔑 useAuth: Token attached')
    }
    return config
})

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    const fetchCurrentUser = useCallback(async () => {
        console.log('👤 useAuth: Fetching current user...')
        try {
            const response = await authApi.get('/auth/me')
            console.log('✅ useAuth: User fetched:', response.data.email)
            setUser(response.data)
        } catch (error) {
            console.error('❌ useAuth: Failed to fetch user:', error)
            localStorage.removeItem(TOKEN_KEY)
            localStorage.removeItem(REFRESH_TOKEN_KEY)
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        const token = localStorage.getItem(TOKEN_KEY)
        console.log('🔍 useAuth: Checking for token on mount:', !!token)
        if (token) {
            fetchCurrentUser()  // ← Sin parámetro
        } else {
            setIsLoading(false)
        }
    }, [fetchCurrentUser])

    const login = async (email: string, password: string) => {
        console.log('🔐 useAuth: Logging in:', email)
        try {
            const response = await authApi.post('/auth/login', {
                email,
                password
            })

            const { user, tokens } = response.data

            console.log('✅ useAuth: Login successful, storing tokens')
            localStorage.setItem(TOKEN_KEY, tokens.access_token)
            localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
            setUser(user)
        } catch (error) {
            console.error('❌ useAuth: Login failed:', error)
            throw error
        }
    }

    const register = async (email: string, password: string, name?: string) => {
        console.log('📝 useAuth: Registering:', email)
        try {
            const response = await authApi.post('/auth/register', {
                email,
                password,
                name
            })

            const { user, tokens } = response.data

            console.log('✅ useAuth: Registration successful, storing tokens')
            localStorage.setItem(TOKEN_KEY, tokens.access_token)
            localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
            setUser(user)
        } catch (error) {
            console.error('❌ useAuth: Registration failed:', error)
            throw error
        }
    }

    const logout = () => {
        console.log('👋 useAuth: Logging out')
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