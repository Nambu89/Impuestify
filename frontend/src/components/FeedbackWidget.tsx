import { useState, useRef } from 'react'
import { MessageSquarePlus, X, Bug, Lightbulb, MessageCircle, Send, Loader, CheckCircle, Paperclip, AlertCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useLocation } from 'react-router-dom'
import { useFeedback } from '../hooks/useFeedback'
import './FeedbackWidget.css'

type FeedbackType = 'bug' | 'feature' | 'general'

const PUBLIC_PATHS = ['/', '/login', '/register', '/forgot-password', '/reset-password', '/subscribe',
    '/contact', '/privacy-policy', '/ai-transparency', '/politica-cookies', '/terms',
    '/data-retention', '/territorios-forales', '/ceuta-melilla', '/canarias']

export default function FeedbackWidget() {
    const { isAuthenticated } = useAuth()
    const { pathname } = useLocation()
    const { submitFeedback } = useFeedback()

    const [open, setOpen] = useState(false)
    const [type, setType] = useState<FeedbackType>('bug')
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [screenshotData, setScreenshotData] = useState<string | null>(null)
    const [screenshotName, setScreenshotName] = useState<string | null>(null)
    const [sending, setSending] = useState(false)
    const [sent, setSent] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Don't show on public pages or when not authenticated
    if (!isAuthenticated || PUBLIC_PATHS.includes(pathname)) return null

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        if (!['image/png', 'image/jpeg'].includes(file.type)) {
            setError('Solo se aceptan imágenes PNG o JPEG')
            return
        }
        if (file.size > 2 * 1024 * 1024) {
            setError('La imagen no puede superar 2 MB')
            return
        }

        setError(null)
        const reader = new FileReader()
        reader.onload = (ev) => {
            setScreenshotData(ev.target?.result as string)
            setScreenshotName(file.name)
        }
        reader.readAsDataURL(file)
    }

    const removeScreenshot = () => {
        setScreenshotData(null)
        setScreenshotName(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    const handleOpen = () => {
        setOpen(true)
        setSent(false)
        setError(null)
    }

    const handleClose = () => {
        setOpen(false)
        setTitle('')
        setDescription('')
        setType('bug')
        setScreenshotData(null)
        setScreenshotName(null)
        setSent(false)
        setError(null)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!title.trim() || !description.trim() || sending) return

        setError(null)
        setSending(true)

        try {
            await submitFeedback({
                type,
                title: title.trim(),
                description: description.trim(),
                page_url: window.location.href,
                ...(screenshotData ? { screenshot_data: screenshotData } : {}),
            })
            setSent(true)
            setTimeout(() => {
                handleClose()
            }, 2500)
        } catch (err: any) {
            setError(err.message || 'No se pudo enviar el feedback. Inténtalo de nuevo.')
        } finally {
            setSending(false)
        }
    }

    const typeOptions: { value: FeedbackType; label: string; icon: React.ReactNode }[] = [
        { value: 'bug', label: 'Error', icon: <Bug size={14} /> },
        { value: 'feature', label: 'Sugerencia', icon: <Lightbulb size={14} /> },
        { value: 'general', label: 'General', icon: <MessageCircle size={14} /> },
    ]

    return (
        <>
            {/* Floating trigger button */}
            <button
                className="feedback-trigger"
                onClick={handleOpen}
                aria-label="Enviar feedback"
                title="Enviar feedback"
            >
                <MessageSquarePlus size={22} />
            </button>

            {/* Modal overlay */}
            {open && (
                <div className="feedback-overlay" onClick={handleClose}>
                    <div
                        className="feedback-modal"
                        onClick={e => e.stopPropagation()}
                        role="dialog"
                        aria-modal="true"
                        aria-label="Enviar feedback"
                    >
                        <div className="feedback-modal__header">
                            <h2 className="feedback-modal__title">
                                <MessageSquarePlus size={20} />
                                Enviar feedback
                            </h2>
                            <button
                                className="feedback-modal__close"
                                onClick={handleClose}
                                aria-label="Cerrar"
                            >
                                <X size={20} />
                            </button>
                        </div>

                        {sent ? (
                            <div className="feedback-success">
                                <CheckCircle size={40} />
                                <p>Gracias.</p>
                                <span>Lo leemos y te contestamos si hace falta.</span>
                            </div>
                        ) : (
                            <form className="feedback-form" onSubmit={handleSubmit}>
                                {/* Type selector */}
                                <div className="feedback-type-group">
                                    {typeOptions.map(opt => (
                                        <button
                                            key={opt.value}
                                            type="button"
                                            className={`feedback-type-btn ${type === opt.value ? 'active' : ''}`}
                                            onClick={() => setType(opt.value)}
                                        >
                                            {opt.icon}
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>

                                {/* Title */}
                                <div className="feedback-field">
                                    <label htmlFor="fb-title" className="feedback-label">
                                        Título <span className="feedback-required">*</span>
                                    </label>
                                    <input
                                        id="fb-title"
                                        type="text"
                                        className="feedback-input"
                                        placeholder="Resumen breve del problema o sugerencia"
                                        value={title}
                                        onChange={e => setTitle(e.target.value.slice(0, 100))}
                                        maxLength={100}
                                        required
                                    />
                                    <span className="feedback-char-count">{title.length}/100</span>
                                </div>

                                {/* Description */}
                                <div className="feedback-field">
                                    <label htmlFor="fb-desc" className="feedback-label">
                                        Descripción <span className="feedback-required">*</span>
                                    </label>
                                    <textarea
                                        id="fb-desc"
                                        className="feedback-textarea"
                                        placeholder="Describe con detalle lo que ocurrió o lo que necesitas..."
                                        value={description}
                                        onChange={e => setDescription(e.target.value.slice(0, 2000))}
                                        maxLength={2000}
                                        rows={4}
                                        required
                                    />
                                    <span className="feedback-char-count">{description.length}/2000</span>
                                </div>

                                {/* Screenshot */}
                                <div className="feedback-field">
                                    {screenshotData ? (
                                        <div className="feedback-screenshot-preview">
                                            <img src={screenshotData} alt="Captura adjunta" />
                                            <div className="feedback-screenshot-info">
                                                <span>{screenshotName}</span>
                                                <button type="button" onClick={removeScreenshot} aria-label="Eliminar captura">
                                                    <X size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    ) : (
                                        <button
                                            type="button"
                                            className="feedback-attach-btn"
                                            onClick={() => fileInputRef.current?.click()}
                                        >
                                            <Paperclip size={14} />
                                            Adjuntar captura (opcional)
                                        </button>
                                    )}
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept="image/png,image/jpeg"
                                        className="feedback-file-input"
                                        onChange={handleFileChange}
                                        aria-label="Adjuntar captura de pantalla"
                                    />
                                </div>

                                {/* Error banner */}
                                {error && (
                                    <div className="feedback-error">
                                        <AlertCircle size={16} />
                                        {error}
                                    </div>
                                )}

                                {/* Page URL info */}
                                <p className="feedback-page-url">
                                    Página: <code>{window.location.pathname}</code>
                                </p>

                                <button
                                    type="submit"
                                    className="feedback-submit"
                                    disabled={!title.trim() || !description.trim() || sending}
                                >
                                    {sending ? (
                                        <><Loader size={16} className="feedback-spin" /> Enviando...</>
                                    ) : (
                                        <><Send size={16} /> Enviar feedback</>
                                    )}
                                </button>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </>
    )
}
