import { Suspense, lazy, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Footer from './components/Footer'
import CookieConsentBanner from './components/CookieConsent'
import FeedbackWidget from './components/FeedbackWidget'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { useSubscription } from './hooks/useSubscription'

const ForgotPassword = lazy(() => import('./pages/ForgotPassword'))
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const WorkspacesPage = lazy(() => import('./pages/WorkspacesPage'))
const SubscribePage = lazy(() => import('./pages/SubscribePage'))
const AdminUsersPage = lazy(() => import('./pages/AdminUsersPage'))
const AdminFeedbackPage = lazy(() => import('./pages/AdminFeedbackPage'))
const AdminContactPage = lazy(() => import('./pages/AdminContactPage'))
const AdminDashboardPage = lazy(() => import('./pages/AdminDashboardPage'))
const ContactPage = lazy(() => import('./pages/ContactPage'))
const PrivacyPolicyPage = lazy(() => import('./pages/PrivacyPolicyPage'))
const AITransparencyPage = lazy(() => import('./pages/AITransparencyPage'))
const CookiePolicyPage = lazy(() => import('./pages/CookiePolicyPage'))
const TermsPage = lazy(() => import('./pages/TermsPage'))
const DataRetentionPage = lazy(() => import('./pages/DataRetentionPage'))
const ForalPage = lazy(() => import('./pages/ForalPage'))
const CeutaMelillaPage = lazy(() => import('./pages/CeutaMelillaPage'))
const CanariasPage = lazy(() => import('./pages/CanariasPage'))
const TaxGuidePage = lazy(() => import('./pages/TaxGuidePage'))
const DeclarationsPage = lazy(() => import('./pages/DeclarationsPage'))
const CalendarPage = lazy(() => import('./pages/CalendarPage'))
const CryptoPage = lazy(() => import('./pages/CryptoPage'))
const CreatorsPage = lazy(() => import('./pages/CreatorsPage'))
const NetSalaryPage = lazy(() => import('./pages/NetSalaryPage'))

function ScrollToTop() {
    const { pathname } = useLocation()
    useEffect(() => {
        window.scrollTo(0, 0)
    }, [pathname])
    return null
}

function AppFooter() {
    const { pathname } = useLocation()
    const hideFooter = ['/chat', '/workspaces'].includes(pathname)
    if (hideFooter) return null
    return <Footer />
}

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
            <ScrollToTop />
            <div className="app">
                <Suspense fallback={<div className="loading-screen">Cargando...</div>}>
                <Routes>
                    <Route path="/" element={<Home />} />
                    <Route path="/login" element={<Login />} />
                    <Route path="/register" element={<Register />} />
                    <Route path="/forgot-password" element={<ForgotPassword />} />
                    <Route path="/reset-password" element={<ResetPassword />} />
                    <Route path="/subscribe" element={<SubscribePage />} />
                    <Route path="/contact" element={<ContactPage />} />

                    {/* Legal Pages - Publicly Accessible */}
                    <Route path="/privacy-policy" element={<PrivacyPolicyPage />} />
                    <Route path="/ai-transparency" element={<AITransparencyPage />} />
                    <Route path="/politica-cookies" element={<CookiePolicyPage />} />
                    <Route path="/terms" element={<TermsPage />} />
                    <Route path="/data-retention" element={<DataRetentionPage />} />

                    {/* SEO Landing Pages - Publicly Accessible */}
                    <Route path="/territorios-forales" element={<ForalPage />} />
                    <Route path="/ceuta-melilla" element={<CeutaMelillaPage />} />
                    <Route path="/canarias" element={<CanariasPage />} />
                    <Route path="/creadores-de-contenido" element={<CreatorsPage />} />

                    {/* Protected Routes (require auth + subscription) */}
                    <Route
                        path="/guia-fiscal"
                        element={
                            <ProtectedRoute>
                                <TaxGuidePage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/modelos-trimestrales"
                        element={
                            <ProtectedRoute>
                                <DeclarationsPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/calendario"
                        element={
                            <ProtectedRoute>
                                <CalendarPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/calculadora-neto"
                        element={
                            <ProtectedRoute>
                                <NetSalaryPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/crypto"
                        element={
                            <ProtectedRoute>
                                <CryptoPage />
                            </ProtectedRoute>
                        }
                    />
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
                        path="/admin"
                        element={
                            <ProtectedRoute requireSubscription={false}>
                                <AdminDashboardPage />
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
                    <Route
                        path="/admin/feedback"
                        element={
                            <ProtectedRoute requireSubscription={false}>
                                <AdminFeedbackPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/admin/contact"
                        element={
                            <ProtectedRoute requireSubscription={false}>
                                <AdminContactPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
                </Suspense>

                {/* Cookie consent banner (LSSI-CE + RGPD) */}
                <CookieConsentBanner />

                {/* Feedback widget — authenticated users only, hidden on public pages */}
                <FeedbackWidget />

                {/* Footer — hidden on full-screen app pages */}
                <AppFooter />
            </div>
        </AuthProvider>
    )
}

export default App
