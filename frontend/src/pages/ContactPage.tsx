import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Send, ArrowLeft, CheckCircle, AlertCircle, Loader, Building2, Mail, UserCircle, MessageSquare } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useApi } from '../hooks/useApi'
import Header from '../components/Header'
import './ContactPage.css'

export default function ContactPage() {
    const { user } = useAuth()
    const { apiRequest } = useApi()
    const [searchParams] = useSearchParams()
    const contactType = searchParams.get('type') || 'general'

    const [form, setForm] = useState({
        name: user?.name || '',
        email: user?.email || '',
        subject: contactType === 'autonomo'
            ? 'Información sobre plan para autónomos'
            : '',
        message: contactType === 'autonomo'
            ? 'Me gustaría recibir información sobre el plan especializado para autónomos y profesionales por cuenta propia.'
            : '',
    })

    const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
    const [errorMsg, setErrorMsg] = useState('')

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        setForm(prev => ({ ...prev, [e.target.name]: e.target.value }))
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setStatus('sending')
        setErrorMsg('')

        try {
            await apiRequest('/api/contact', {
                method: 'POST',
                body: JSON.stringify({
                    name: form.name,
                    email: form.email,
                    subject: form.subject,
                    message: form.message,
                    contact_type: contactType,
                }),
            })
            setStatus('sent')
        } catch (err: any) {
            setErrorMsg(err.message || 'Error al enviar el mensaje')
            setStatus('error')
        }
    }

    if (status === 'sent') {
        return (
            <div className="contact-page">
                <Header />
                <div className="contact-container">
                    <div className="contact-success">
                        <CheckCircle size={48} />
                        <h2>Mensaje enviado</h2>
                        <p>
                            Hemos recibido tu solicitud. Te responderemos lo antes posible
                            a <strong>{form.email}</strong>.
                        </p>
                        <Link to="/" className="btn btn-primary">
                            Volver al inicio
                        </Link>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="contact-page">
            <Header />

            <div className="contact-container">
                <Link to="/" className="back-link">
                    <ArrowLeft size={16} />
                    Volver al inicio
                </Link>

                <div className="contact-header">
                    {contactType === 'autonomo' ? (
                        <>
                            <div className="contact-badge">
                                <Building2 size={16} />
                                <span>Plan Autonomos</span>
                            </div>
                            <h1>Plan para autonomos y profesionales</h1>
                            <p>
                                Estamos preparando un plan especializado con herramientas adaptadas
                                a las necesidades de autonomos y profesionales por cuenta propia.
                                Dejanos tus datos y te informaremos en cuanto este disponible.
                            </p>
                        </>
                    ) : (
                        <>
                            <div className="contact-badge">
                                <Mail size={16} />
                                <span>Contacto</span>
                            </div>
                            <h1>Contacta con nosotros</h1>
                            <p>
                                ¿Tienes alguna duda o sugerencia? Rellena el formulario
                                y te responderemos lo antes posible.
                            </p>
                        </>
                    )}
                </div>

                {status === 'error' && (
                    <div className="contact-alert">
                        <AlertCircle size={20} />
                        <span>{errorMsg}</span>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="contact-form">
                    <div className="form-row">
                        <div className="form-group">
                            <label htmlFor="name">
                                <UserCircle size={16} />
                                Nombre
                            </label>
                            <input
                                type="text"
                                id="name"
                                name="name"
                                value={form.name}
                                onChange={handleChange}
                                placeholder="Tu nombre"
                                className="form-input"
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="email">
                                <Mail size={16} />
                                Email
                            </label>
                            <input
                                type="email"
                                id="email"
                                name="email"
                                value={form.email}
                                onChange={handleChange}
                                placeholder="tu@email.com"
                                className="form-input"
                                required
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label htmlFor="subject">
                            <MessageSquare size={16} />
                            Asunto
                        </label>
                        <input
                            type="text"
                            id="subject"
                            name="subject"
                            value={form.subject}
                            onChange={handleChange}
                            placeholder="Asunto del mensaje"
                            className="form-input"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="message">Mensaje</label>
                        <textarea
                            id="message"
                            name="message"
                            value={form.message}
                            onChange={handleChange}
                            placeholder="Escribe tu mensaje..."
                            className="form-input form-textarea"
                            rows={6}
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-lg contact-submit"
                        disabled={status === 'sending'}
                    >
                        {status === 'sending' ? (
                            <>
                                <Loader size={20} className="animate-spin" />
                                Enviando...
                            </>
                        ) : (
                            <>
                                <Send size={20} />
                                Enviar mensaje
                            </>
                        )}
                    </button>
                </form>
            </div>
        </div>
    )
}
