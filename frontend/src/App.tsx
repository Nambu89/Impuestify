import { Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import SettingsPage from './pages/SettingsPage'
import WorkspacesPage from './pages/WorkspacesPage'
import PrivacyPolicyPage from './pages/PrivacyPolicyPage'
import AITransparencyPage from './pages/AITransparencyPage'
import Footer from './components/Footer'
import { AuthProvider, useAuth } from './hooks/useAuth'

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuth()

    if (isLoading) {
        return <div className="loading-screen">Cargando...</div>
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    return <>{children}</>
}

function App() {
    return (
        <AuthProvider>
            <div className="app">
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />

                    {/* Legal Pages - Publicly Accessible */}
                    <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
                    <Route path="/ai-transparency" element={<AITransparencyPage />} />
                    <Route path="/terms" element={<PrivacyPolicyPage />} /> {/* Placeholder */}
                    <Route path="/data-retention" element={<PrivacyPolicyPage />} /> {/* Placeholder */}
                    <Route path="/security" element={<PrivacyPolicyPage />} /> {/* Placeholder */}

                    {/* Protected Routes */}
                    <Route
                        path="/chat"
                        element={
                            <ProtectedRoute>
                                <Chat />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/dashboard"
                        element={
                            <ProtectedRoute>
                                <Dashboard />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/settings"
                        element={
                            <ProtectedRoute>
                                <SettingsPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/workspaces"
                        element={
                            <ProtectedRoute>
                                <WorkspacesPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>

                {/* Footer on all pages */}
                <Footer />
            </div>
        </AuthProvider>
    )
}

export default App
