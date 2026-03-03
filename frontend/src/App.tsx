import { Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import SettingsPage from './pages/SettingsPage'
import WorkspacesPage from './pages/WorkspacesPage'
import SubscribePage from './pages/SubscribePage'
import ContactPage from './pages/ContactPage'
import AdminUsersPage from './pages/AdminUsersPage'
import PrivacyPolicyPage from './pages/PrivacyPolicyPage'
import AITransparencyPage from './pages/AITransparencyPage'
import CookiePolicyPage from './pages/CookiePolicyPage'
import TermsPage from './pages/TermsPage'
import DataRetentionPage from './pages/DataRetentionPage'
import Footer from './components/Footer'
import CookieConsentBanner from './components/CookieConsent'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { useSubscription } from './hooks/useSubscription'

// Protected route wrapper — requires auth + active subscription
function ProtectedRoute({ children, requireSubscription = true }: { children: React.ReactNode; requireSubscription?: boolean }) {
    const { isAuthenticated, isLoading } = useAuth()
    const { hasAccess, loading: subLoading } = useSubscription()

    if (isLoading || (isAuthenticated && subLoading)) {
        return <div className="loading-screen">Cargando...</div>
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    if (requireSubscription && !hasAccess) {
        return <Navigate to="/subscribe" replace />
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
                    <Route path="/subscribe" element={<SubscribePage />} />
                    <Route path="/contact" element={<ContactPage />} />

                    {/* Legal Pages - Publicly Accessible */}
                    <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
                    <Route path="/ai-transparency" element={<AITransparencyPage />} />
                    <Route path="/politica-cookies" element={<CookiePolicyPage />} />
                    <Route path="/terms" element={<TermsPage />} />
                    <Route path="/data-retention" element={<DataRetentionPage />} />

                    {/* Protected Routes (require auth + subscription) */}
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
                            <ProtectedRoute requireSubscription={false}>
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
                    <Route
                        path="/admin/users"
                        element={
                            <ProtectedRoute requireSubscription={false}>
                                <AdminUsersPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>

                {/* Cookie consent banner (LSSI-CE + RGPD) */}
                <CookieConsentBanner />

                {/* Footer on all pages */}
                <Footer />
            </div>
        </AuthProvider>
    )
}

export default App
