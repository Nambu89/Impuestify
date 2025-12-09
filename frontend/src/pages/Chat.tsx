import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, FileText, AlertCircle, Upload } from 'lucide-react'
import Header from '../components/Header'
import { useApi } from '../hooks/useApi'
import { NotificationUpload } from '../components/NotificationUpload'
import { NotificationAnalysisDisplay } from '../components/NotificationAnalysisDisplay'
import { ConversationSidebar } from '../components/ConversationSidebar'
import { useConversations } from '../hooks/useConversations'
import ReactMarkdown from 'react-markdown'
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
    const { getConversation } = useConversations()
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [showNotificationModal, setShowNotificationModal] = useState(false)
    const [notificationAnalysis, setNotificationAnalysis] = useState<any>(null)
    const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
    const [sidebarOpen, setSidebarOpen] = useState(false) // ✅ NUEVO: Estado del sidebar
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSelectConversation = async (conversationId: string) => {
        try {
            const data = await getConversation(conversationId)
            const formattedMessages: Message[] = data.messages.map(msg => ({
                id: msg.id,
                role: msg.role as 'user' | 'assistant',
                content: msg.content,
                sources: msg.metadata?.sources
            }))
            setMessages(formattedMessages)
            setActiveConversationId(conversationId)
            setNotificationAnalysis(null)
            setSidebarOpen(false) // ✅ NUEVO: Cerrar sidebar al seleccionar
        } catch (error) {
            console.error('Error loading conversation:', error)
        }
    }

    const handleNewConversation = () => {
        setMessages([])
        setActiveConversationId(null)
        setNotificationAnalysis(null)
        setSidebarOpen(false) // ✅ NUEVO: Cerrar sidebar al crear nuevo
    }

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
            const response = await askQuestion(
                userMessage.content,
                activeConversationId || undefined
            )

            setMessages(prev => prev.map(msg =>
                msg.loading ? {
                    ...msg,
                    content: response.answer,
                    sources: response.sources,
                    loading: false
                } : msg
            ))

            // ✅ FIX: Solo actualizar el conversation_id
            // El useEffect del ConversationSidebar se encargará del refresh
            if (response.conversation_id) {
                console.log('📝 Conversation ID received:', response.conversation_id)
                setActiveConversationId(response.conversation_id)
            } else {
                console.warn('⚠️ No conversation_id in response')
            }
        } catch (error: any) {
            console.error('❌ Error in handleSubmit:', error)
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
            {/* ✅ NUEVO: Pasar función toggle al Header */}
            <Header onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />

            {/* ✅ NUEVO: Pasar props de sidebar open/close */}
            <ConversationSidebar
                activeConversationId={activeConversationId}
                onSelectConversation={handleSelectConversation}
                onNewConversation={handleNewConversation}
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
            />

            {/* ✅ NUEVO: Overlay para cerrar sidebar en móvil */}
            {sidebarOpen && (
                <div
                    className="sidebar-overlay active"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

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
                                    className="example-question"
                                    onClick={() => setInput('¿Cuándo debo presentar el modelo 303 de IVA?')}
                                >
                                    ¿Cuándo debo presentar el modelo 303 de IVA?
                                </button>
                                <button
                                    className="example-question"
                                    onClick={() => setInput('¿Qué deducciones puedo aplicar en el IRPF?')}
                                >
                                    ¿Qué deducciones puedo aplicar en el IRPF?
                                </button>
                                <button
                                    className="example-question"
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
                                                <div className="message-text">
                                                    <ReactMarkdown>
                                                        {message.content}
                                                    </ReactMarkdown>
                                                </div>
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
                        type="button"
                        className="btn btn-success"
                        onClick={() => setShowNotificationModal(true)}
                        title="Analizar notificación AEAT"
                    >
                        <Upload size={20} />
                    </button>
                    <button
                        type="submit"
                        className="btn btn-primary chat-submit"
                        disabled={isLoading || !input.trim()}
                    >
                        {isLoading ? <Loader2 className="animate-spin" /> : <Send />}
                    </button>
                </form>
                <p className="chat-disclaimer">
                    <AlertCircle size={14} />
                    Información orientativa. Consulta con un asesor fiscal para tu caso particular.
                </p>
            </footer>

            {showNotificationModal && (
                <div className="modal-overlay" onClick={() => setShowNotificationModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>📎 Analizar Notificación AEAT</h3>
                            <button
                                className="modal-close"
                                onClick={() => setShowNotificationModal(false)}
                            >
                                ✕
                            </button>
                        </div>
                        <NotificationUpload
                            onAnalysisComplete={(analysis) => {
                                const analysisMessage: Message = {
                                    id: Date.now().toString(),
                                    role: 'assistant',
                                    content: `📋 **Análisis de Notificación: ${analysis.type}**\n\n${analysis.summary}\n\n---\n\n💡 Puedes hacerme preguntas sobre esta notificación y te ayudaré con toda la información de la AEAT.`
                                }

                                setMessages(prev => [...prev, analysisMessage])
                                setNotificationAnalysis(analysis)
                                setShowNotificationModal(false)

                                if (analysis.conversation_id) {
                                    console.log('📋 Notification conversation ID:', analysis.conversation_id)
                                    setActiveConversationId(analysis.conversation_id)
                                }
                            }}
                        />
                    </div>
                </div>
            )}

            {notificationAnalysis && !messages.some(m => m.content.includes('Análisis de Notificación')) && (
                <div style={{
                    position: 'fixed',
                    top: '80px',
                    right: '20px',
                    maxWidth: '500px',
                    zIndex: 1000,
                    maxHeight: 'calc(100vh - 100px)',
                    overflowY: 'auto'
                }}>
                    <button
                        onClick={() => setNotificationAnalysis(null)}
                        style={{
                            position: 'absolute',
                            right: '10px',
                            top: '10px',
                            background: '#fc8181',
                            color: 'white',
                            border: 'none',
                            borderRadius: '50%',
                            width: '30px',
                            height: '30px',
                            cursor: 'pointer',
                            fontSize: '18px',
                            zIndex: 10
                        }}
                    >
                        ✕
                    </button>
                    <NotificationAnalysisDisplay analysis={notificationAnalysis} />
                </div>
            )}
        </div>
    )
}