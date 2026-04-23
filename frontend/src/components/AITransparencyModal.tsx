import { useEffect, useState } from 'react'
import { X, Bot, Shield, AlertCircle, CheckCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import './AITransparencyModal.css'

interface AITransparencyModalProps {
    onAccept: () => void
}

export default function AITransparencyModal({ onAccept }: AITransparencyModalProps) {
    const [isVisible, setIsVisible] = useState(false)

    useEffect(() => {
        // Check if user has already accepted
        const hasAccepted = localStorage.getItem('ai_transparency_accepted')

        if (!hasAccepted) {
            // Small delay for smooth animation
            setTimeout(() => setIsVisible(true), 300)
        } else {
            onAccept() // Immediately call onAccept if already accepted
        }
    }, [onAccept])

    const handleAccept = () => {
        // Store acceptance in localStorage
        localStorage.setItem('ai_transparency_accepted', 'true')
        localStorage.setItem('ai_transparency_accepted_date', new Date().toISOString())

        // Trigger callback
        onAccept()

        // Close modal with animation
        setIsVisible(false)
    }

    if (!isVisible) return null

    return (
        <div className="ai-modal-overlay" onClick={handleAccept}>
            <div className="ai-modal-content" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="ai-modal-header">
                    <div className="ai-modal-title">
                        <Bot size={28} className="ai-icon" />
                        <h2>Sistema de Inteligencia Artificial</h2>
                    </div>
                    <button
                        className="ai-modal-close"
                        onClick={handleAccept}
                        aria-label="Cerrar"
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Body */}
                <div className="ai-modal-body">
                    <div className="ai-notice">
                        <Shield size={20} />
                        <p>
                            <strong>Impuestify funciona con IA</strong> (modelos de lenguaje de última generación) para
                            responder tus consultas fiscales.
                        </p>
                    </div>

                    <div className="ai-features">
                        <h3>Antes de empezar:</h3>

                        <div className="ai-feature-item">
                            <AlertCircle size={18} className="feature-icon warning" />
                            <div className="feature-text">
                                <strong>La IA se equivoca</strong>
                                <p>A veces inventa datos. Revisa siempre las cifras antes de usarlas.</p>
                            </div>
                        </div>

                        <div className="ai-feature-item">
                            <CheckCircle size={18} className="feature-icon success" />
                            <div className="feature-text">
                                <strong>Esto no sustituye a un asesor</strong>
                                <p>Para decisiones importantes, contrasta con un fiscalista colegiado.</p>
                            </div>
                        </div>

                        <div className="ai-feature-item">
                            <Shield size={18} className="feature-icon primary" />
                            <div className="feature-text">
                                <strong>Tus datos, bajo RGPD</strong>
                                <p>Tratamiento seguro, servidores en la UE y borrado a petición.</p>
                            </div>
                        </div>
                    </div>

                    <div className="ai-legal-links">
                        <p className="legal-text">
                            Más detalle en la{' '}
                            <Link to="/ai-transparency" target="_blank">
                                Política de Transparencia IA
                            </Link>
                            {' y la '}
                            <Link to="/privacy-policy" target="_blank">
                                Política de Privacidad
                            </Link>
                            .
                        </p>
                    </div>
                </div>

                {/* Footer */}
                <div className="ai-modal-footer">
                    <button
                        className="btn btn-primary-ai"
                        onClick={handleAccept}
                    >
                        <CheckCircle size={18} />
                        Entendido
                    </button>
                </div>
            </div>
        </div>
    )
}
