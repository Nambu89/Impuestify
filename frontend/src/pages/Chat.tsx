import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, FileText, AlertCircle, Upload } from 'lucide-react'
import Header from '../components/Header'
import AITransparencyModal from '../components/AITransparencyModal'
import { useApi } from '../hooks/useApi'
import { NotificationUpload } from '../components/NotificationUpload'
import { NotificationAnalysisDisplay } from '../components/NotificationAnalysisDisplay'
import { ConversationSidebar } from '../components/ConversationSidebar'
import { WorkspaceSelector } from '../components/WorkspaceSelector'
import { WorkspaceContextIndicator } from '../components/WorkspaceContextIndicator'
import { ReportActions, isIRPFSimulation } from '../components/ReportActions'
import { useConversations } from '../hooks/useConversations'
import { useWorkspaces, Workspace } from '../hooks/useWorkspaces'
import { useStreamingChat } from '../hooks/useStreamingChat'
import { ThinkingIndicator } from '../components/ThinkingIndicator'
import { ToolExecutionStatus } from '../components/ToolExecutionStatus'
import { logger } from '../utils/logger'
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
    const { workspaces, activeWorkspace, selectWorkspace, fetchWorkspaces } = useWorkspaces()
    const { streamState, isStreaming, sendStreamingMessage } = useStreamingChat()
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [showNotificationModal, setShowNotificationModal] = useState(false)
    const [notificationAnalysis, setNotificationAnalysis] = useState<any>(null)
    const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [useStreaming] = useState(true)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Fetch workspaces on mount (only once)
    useEffect(() => {
        fetchWorkspaces()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])  // Empty dependency array = run only once on mount

    // Workspace change handler
    const handleWorkspaceChange = (workspace: Workspace | null) => {
        selectWorkspace(workspace)
    }

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    // ✅ IMPROVED: Wait for DOM to fully render before scrolling
    useEffect(() => {
        const timer = setTimeout(() => {
            scrollToBottom()
        }, 100) // Small delay ensures DOM has completed rendering

        return () => clearTimeout(timer)
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
            logger.error('Error loading conversation:', error)
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
        if (!input.trim() || isLoading || isStreaming) return

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim()
        }

        setMessages(prev => [...prev, userMessage])
        const questionText = input.trim()
        setInput('')

        // ✅ STREAMING MODE
        if (useStreaming) {
            try {
                await sendStreamingMessage(questionText, activeConversationId || undefined, {
                    onComplete: (response, convId) => {
                        // ✅ Callback when stream finishes successfully
                        const assistantMessage: Message = {
                            id: (Date.now() + 1).toString(),
                            role: 'assistant',
                            content: response
                        }
                        setMessages(prev => [...prev, assistantMessage])

                        // Update conversation ID if needed
                        if (convId && convId !== activeConversationId) {
                            setActiveConversationId(convId)
                        }
                    },
                    onError: (error) => {
                        logger.error('Streaming error:', error)
                        setMessages(prev => [...prev, {
                            id: (Date.now() + 1).toString(),
                            role: 'assistant',
                            content: `Error: ${error} `
                        }])
                    }
                })
            } catch (error: any) {
                logger.error('Streaming fatal error:', error)
                setMessages(prev => [...prev, {
                    id: (Date.now() + 1).toString(),
                    role: 'assistant',
                    content: `Error: ${error.message || 'No se pudo obtener respuesta'} `
                }])
            }
            return
        }

        // ⏪ FALLBACK: Non-streaming mode (original code)
        const loadingMessage: Message = {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: '',
            loading: true
        }

        setMessages(prev => [...prev, loadingMessage])
        setIsLoading(true)

        try {
            const response = await askQuestion(
                questionText,
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

            // Update conversation ID if returned
            if (response.conversation_id) {
                logger.debug('Conversation ID received:', response.conversation_id)
                setActiveConversationId(response.conversation_id)
            }
        } catch (error: any) {
            logger.error('Error in handleSubmit:', error)
            setMessages(prev => prev.map(msg =>
                msg.loading ? {
                    ...msg,
                    content: `Error: ${error.message || 'No se pudo obtener respuesta'} `,
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

            {/* AI Act Art. 52: AI Transparency Modal on first access */}
            <AITransparencyModal onAccept={() => {
                logger.debug('AI Transparency accepted')
            }} />

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
                            <h2>¡Hola! Soy Impuestify</h2>
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
                            {messages.map((message, index) => (
                                <div
                                    key={message.id}
                                    className={`message ${message.role} `}
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
                                                {/* Fuentes sin bullets, formato inline */}
                                                {message.sources && message.sources.length > 0 && (
                                                    <div className="message-sources">
                                                        <p className="sources-title">
                                                            <FileText size={14} />
                                                            Fuentes: {message.sources.map((source, idx) => (
                                                                <span key={idx}>
                                                                    {idx > 0 && ', '}
                                                                    {source.title} (pág. {source.page})
                                                                </span>
                                                            ))}
                                                        </p>
                                                    </div>
                                                )}
                                                {/* Report actions for IRPF simulation results */}
                                                {message.role === 'assistant' && isIRPFSimulation(message.content) && (
                                                    <ReportActions
                                                        messageContent={message.content}
                                                        previousUserMessage={
                                                            index > 0 && messages[index - 1]?.role === 'user'
                                                                ? messages[index - 1].content
                                                                : undefined
                                                        }
                                                    />
                                                )}
                                            </>
                                        )}
                                    </div>
                                </div>
                            ))}

                            {/* ✅ STREAMING INDICATORS */}
                            {isStreaming && (
                                <div className="streaming-indicators" style={{ margin: '16px 0' }}>
                                    <ThinkingIndicator message={streamState.thinking} />
                                    <ToolExecutionStatus status={streamState.toolStatus} />
                                    {streamState.response && (
                                        <div className="message assistant">
                                            <div className="message-content">
                                                <div className="message-text">
                                                    <ReactMarkdown>
                                                        {streamState.response}
                                                    </ReactMarkdown>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>
                    )}
                </div>
            </main>

            <footer className="chat-footer">
                {/* Workspace Context Indicator */}
                {activeWorkspace && (
                    <div className="chat-workspace-context">
                        <WorkspaceContextIndicator
                            workspace={activeWorkspace}
                            onClear={() => selectWorkspace(null)}
                        />
                    </div>
                )}

                <form onSubmit={handleSubmit} className="chat-form">
                    {/* Workspace Selector */}
                    <WorkspaceSelector
                        workspaces={workspaces}
                        activeWorkspace={activeWorkspace}
                        onWorkspaceChange={handleWorkspaceChange}
                        onCreateNew={() => window.location.href = '/workspaces'}
                    />

                    <input
                        type="text"
                        className="chat-input"
                        placeholder={activeWorkspace
                            ? `Pregunta sobre ${activeWorkspace.name}...`
                            : "Escribe tu pregunta fiscal..."}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={isLoading}
                    />
                    <button
                        type="button"
                        className="btn btn-success"
                        onClick={() => setShowNotificationModal(true)}
                        title="Analizar notificacion AEAT"
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
                    Informacion orientativa. Consulta con un asesor fiscal para tu caso particular.
                </p>
            </footer>

            {showNotificationModal && (
                <div className="modal-overlay" onClick={() => setShowNotificationModal(false)}>
                    <div className="modal-content" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3>📎 Analizar documento</h3>
                            <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px', lineHeight: '1.5', marginBottom: '12px' }}>
                                Sube un documento nómina o notificación de la AEAT en formato PDF.
                                Analizaré el contenido, identificaré plazos importantes y te ayudaré
                                a entender los pasos a seguir.
                            </p>
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
                                    content: `📋 ** Análisis de Notificación: ${analysis.type}**\n\n${analysis.summary} \n\n-- -\n\n💡 Puedes hacerme preguntas sobre esta notificación y te ayudaré con toda la información de la AEAT.`
                                }

                                setMessages(prev => [...prev, analysisMessage])
                                setNotificationAnalysis(analysis)
                                setShowNotificationModal(false)

                                if (analysis.conversation_id) {
                                    logger.debug('Notification conversation ID:', analysis.conversation_id)
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