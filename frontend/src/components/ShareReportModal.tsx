import { useState } from 'react'
import { X, Send, Loader2, Check, AlertCircle } from 'lucide-react'
import { logger } from '../utils/logger'
import './ShareReportModal.css'

const API_URL = import.meta.env.VITE_API_URL || '/api'

interface ShareReportModalProps {
    reportId: string
    onClose: () => void
}

export function ShareReportModal({ reportId, onClose }: ShareReportModalProps) {
    const [email, setEmail] = useState('')
    const [message, setMessage] = useState('')
    const [sending, setSending] = useState(false)
    const [sent, setSent] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const isValidEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!isValidEmail(email)) return

        setSending(true)
        setError(null)

        try {
            const token = localStorage.getItem('access_token')
            const response = await fetch(`${API_URL}/api/export/share-with-advisor`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token && { 'Authorization': `Bearer ${token}` }),
                },
                body: JSON.stringify({
                    report_id: reportId,
                    advisor_email: email,
                    message: message || undefined,
                }),
            })

            if (response.status === 503) {
                setError('El envio por email no esta disponible en este momento. Puedes descargar el PDF y enviarlo manualmente.')
                return
            }

            if (!response.ok) {
                const data = await response.json().catch(() => null)
                throw new Error(data?.detail || `Error ${response.status}`)
            }

            setSent(true)
            logger.debug('Report shared with advisor', { email })

            // Close after brief delay
            setTimeout(() => onClose(), 2000)
        } catch (err: any) {
            logger.error('Share report failed:', err)
            setError(err.message || 'Error al enviar el informe')
        } finally {
            setSending(false)
        }
    }

    return (
        <div className="share-modal-overlay" onClick={onClose}>
            <div className="share-modal" onClick={(e) => e.stopPropagation()}>
                <div className="share-modal-header">
                    <h3>Enviar informe a tu asesor fiscal</h3>
                    <button className="share-modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                {sent ? (
                    <div className="share-modal-body">
                        <div className="share-success">
                            <Check size={32} />
                            <p>Informe enviado correctamente a <strong>{email}</strong></p>
                        </div>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="share-modal-body">
                        <div className="share-field">
                            <label htmlFor="advisor-email">Email del asesor</label>
                            <input
                                id="advisor-email"
                                type="email"
                                className="share-input"
                                placeholder="asesor@ejemplo.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                required
                                autoFocus
                            />
                        </div>

                        <div className="share-field">
                            <label htmlFor="advisor-message">
                                Mensaje <span className="share-optional">(opcional)</span>
                            </label>
                            <textarea
                                id="advisor-message"
                                className="share-textarea"
                                placeholder="Adjunto mi simulacion IRPF para revision..."
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                maxLength={500}
                                rows={3}
                            />
                            <span className="share-char-count">{message.length}/500</span>
                        </div>

                        {error && (
                            <div className="share-error">
                                <AlertCircle size={16} />
                                <p>{error}</p>
                            </div>
                        )}

                        <div className="share-modal-footer">
                            <button
                                type="button"
                                className="share-btn-cancel"
                                onClick={onClose}
                            >
                                Cancelar
                            </button>
                            <button
                                type="submit"
                                className="share-btn-send"
                                disabled={sending || !isValidEmail(email)}
                            >
                                {sending ? (
                                    <>
                                        <Loader2 size={16} className="animate-spin" />
                                        Enviando...
                                    </>
                                ) : (
                                    <>
                                        <Send size={16} />
                                        Enviar
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    )
}
