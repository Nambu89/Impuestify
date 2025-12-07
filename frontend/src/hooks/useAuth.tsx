import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

interface User {
    id: string
    email: string
    name?: string
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

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        // Check for existing token on mount
        const token = localStorage.getItem('access_token')
        if (token) {
            fetchCurrentUser(token)
        } else {
            setIsLoading(false)
        }
    }, [])

    const fetchCurrentUser = async (token: string) => {
        try {
            const response = await axios.get(`${API_URL}/auth/me`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            setUser(response.data)
        } catch (error) {
            // Token invalid or expired
            localStorage.removeItem('access_token')
            localStorage.removeItem('refresh_token')
        } finally {
            setIsLoading(false)
        }
    }

    const login = async (email: string, password: string) => {
        const response = await axios.post(`${API_URL}/auth/login`, {
            email,
            password
        })

        const { user, tokens } = response.data

        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        setUser(user)
    }

    const register = async (email: string, password: string, name?: string) => {
        const response = await axios.post(`${API_URL}/auth/register`, {
            email,
            password,
            name
        })

        const { user, tokens } = response.data

        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        setUser(user)
    }

    const logout = () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
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
