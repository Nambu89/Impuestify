import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { GoogleOAuthProvider } from '@react-oauth/google'
import App from './App'
import './styles/global.css'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <BrowserRouter>
                <App />
            </BrowserRouter>
        </GoogleOAuthProvider>
    </React.StrictMode>,
)

// Register Service Worker (production only)
if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((reg) => {
                console.log('[SW] Registered:', reg.scope)
                reg.addEventListener('updatefound', () => {
                    console.log('[SW] Update found, installing...')
                })
            })
            .catch((err) => {
                console.warn('[SW] Registration failed:', err)
            })
    })
}
