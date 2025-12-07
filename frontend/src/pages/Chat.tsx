import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, FileText, AlertCircle } from 'lucide-react'
import Header from '../components/Header'
import { useApi } from '../hooks/useApi'
import './Chat.css'

interface Message {
    id: string
    role: 'user' | 'assistant'
    content: string
    sources?: Array<{
        source: string
        page: number
        title: string
    }>
    loading?: boolean
}

export default function Chat() {
    const { askQuestion } = useApi()
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim()
        }

        const loadingMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: '',
            loading: true
        }

        setMessages(prev => [...prev, userMessage, loadingMessage])
        setInput('')
        setIsLoading(true)

        try {
            const response = await askQuestion(userMessage.content)

            setMessages(prev => prev.map(msg =>
                msg.loading ? {
                    ...msg,
                    content: response.answer,
                    sources: response.sources,
                    loading: false
                } : msg
            ))
        } catch (error: any) {
            setMessages(prev => prev.map(msg =>
                msg.loading ? {
                    ...msg,
                    content: `Error: ${error.message || 'No se pudo obtener respuesta'}`,
                    loading: false
                } : msg
            ))
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="chat-page">
            <Header />

            <main className="chat-main">
                <div className="chat-container">
                    {messages.length === 0 ? (
                        <div className="chat-empty">
                            <FileText size={48} />
                            <h2>¡Hola! Soy TaxIA</h2>
                            <p>Tu asistente fiscal inteligente. Pregúntame sobre impuestos, IRPF, IVA, modelos tributarios y más.</p>

                            <div className="example-questions">
                                <p className="example-title">Prueba a preguntar:</p>
                                <button
                                    className="example-btn"
                                    onClick={() => setInput('¿Cuándo debo presentar el modelo 303 de IVA?')}
                                >
                                    ¿Cuándo debo presentar el modelo 303 de IVA?
                                </button>
                                <button
                                    className="example-btn"
                                    onClick={() => setInput('¿Qué deducciones puedo aplicar en el IRPF?')}
                                >
                                    ¿Qué deducciones puedo aplicar en el IRPF?
                                </button>
                                <button
                                    className="example-btn"
                                    onClick={() => setInput('¿Cómo funciona el régimen de estimación directa?')}
                                >
                                    ¿Cómo funciona el régimen de estimación directa?
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="chat-messages">
                            {messages.map(message => (
                                <div
                                    key={message.id}
                                    className={`message ${message.role}`}
                                >
                                    <div className="message-content">
                                        {message.loading ? (
                                            <div className="message-loading">
                                                <Loader2 size={20} className="animate-spin" />
                                                <span>Analizando tu consulta...</span>
                                            </div>
                                        ) : (
                                            <>
                                                <p>{message.content}</p>
                                                {message.sources && message.sources.length > 0 && (
                                                    <div className="message-sources">
                                                        <p className="sources-title">
                                                            <FileText size={14} />
                                                            Fuentes:
                                                        </p>
                                                        <ul>
                                                            {message.sources.map((source, idx) => (
                                                                <li key={idx}>
                                                                    {source.title} (pág. {source.page})
                                                                </li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </>
                                        )}
                                    </div>
                                </div>
                            ))}
                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>
            </main>

            <footer className="chat-footer">
                <form onSubmit={handleSubmit} className="chat-form">
                    <input
                        type="text"
                        className="chat-input"
                        placeholder="Escribe tu pregunta fiscal..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary chat-submit"
                        disabled={isLoading || !input.trim()}
                    >
                        {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                    </button>
                </form>
                <p className="chat-disclaimer">
                    <AlertCircle size={14} />
                    Información orientativa. Consulta con un asesor fiscal para tu caso particular.
                </p>
            </footer>
        </div>
    )
}
