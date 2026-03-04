import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <BrowserRouter>
            <App />
        </BrowserRouter>
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
