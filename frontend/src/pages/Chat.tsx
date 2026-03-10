import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, FileText, Upload, Zap, Calculator, Search, Shield } from 'lucide-react'
import Header from '../components/Header'
import AITransparencyModal from '../components/AITransparencyModal'
import { useApi } from '../hooks/useApi'
import { NotificationUpload } from '../components/NotificationUpload'
import { NotificationAnalysisDisplay } from '../components/NotificationAnalysisDisplay'
import { ConversationSidebar } from '../components/ConversationSidebar'
import { WorkspaceSelector } from '../components/WorkspaceSelector'
import { WorkspaceContextIndicator } from '../components/WorkspaceContextIndicator'
import { ReportActions, isIRPFSimulation } from '../components/ReportActions'
import { DeductionCards, hasDeductions } from '../components/DeductionCards'
import { SessionDocChips } from '../components/SessionDocChips'
import { SessionDocUploadButton } from '../components/SessionDocUploadButton'
import { useConversations } from '../hooks/useConversations'
import { useWorkspaces, Workspace } from '../hooks/useWorkspaces'
import { useStreamingChat } from '../hooks/useStreamingChat'
import { useSessionDocs } from '../hooks/useSessionDocs'
import { StreamingTimeline } from '../components/StreamingTimeline'
import { logger } from '../utils/logger'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { FormattedMessage } from '../components/FormattedMessage'
import OnboardingModal from '../components/OnboardingModal'
import { useAuth } from '../hooks/useAuth'
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
    const { user } = useAuth()
    const { askQuestion } = useApi()
    const { getConversation } = useConversations()
    const { workspaces, activeWorkspace, selectWorkspace, fetchWorkspaces } = useWorkspaces()
    const { streamState, isStreaming, sendStreamingMessage } = useStreamingChat()
    const { docs: sessionDocs, docIds: sessionDocIds, isUploading: isDocUploading, uploadError: docUploadError, uploadDoc, removeDoc } = useSessionDocs()
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [showNotificationModal, setShowNotificationModal] = useState(false)
    const [notificationAnalysis, setNotificationAnalysis] = useState<any>(null)
    const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [useStreaming] = useState(true)
    const [onboardingDone, setOnboardingDone] = useState(() => !!localStorage.getItem('onboarding_seen'))
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const chatMessagesRef = useRef<HTMLDivElement>(null)
    const userJustSentRef = useRef(false)

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

    const isNearBottom = (): boolean => {
        const container = chatMessagesRef.current
        if (!container) return true
        const threshold = 150
        return container.scrollHeight - container.scrollTop - container.clientHeight < threshold
    }

    // Only auto-scroll if user just sent a message or is already near the bottom
    useEffect(() => {
        const timer = setTimeout(() => {
            if (userJustSentRef.current || isNearBottom()) {
                scrollToBottom()
                userJustSentRef.current = false
            }
        }, 100)

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

    const handleSuggestionClick = (text: string) => {
        setInput(text)
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || isLoading || isStreaming) return

        // Auto-close onboarding + AI transparency modals on first message
        if (!onboardingDone) {
            setOnboardingDone(true)
            localStorage.setItem('onboarding_seen', '1')
        }
        if (!localStorage.getItem('ai_transparency_accepted')) {
            localStorage.setItem('ai_transparency_accepted', 'true')
            localStorage.setItem('ai_transparency_accepted_date', new Date().toISOString())
        }

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input.trim()
        }

        userJustSentRef.current = true
        setMessages(prev => [...prev, userMessage])
        const questionText = input.trim()
        setInput('')

        // ✅ STREAMING MODE
        if (useStreaming) {
            try {
                await sendStreamingMessage(questionText, activeConversationId || undefined, {
                    onComplete: (response, convId) => {
                        const assistantMessage: Message = {
                            id: (Date.now() + 1).toString(),
                            role: 'assistant',
                            content: response
                        }
                        setMessages(prev => [...prev, assistantMessage])

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
                }, activeWorkspace?.id, sessionDocIds.length > 0 ? sessionDocIds : undefined)
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

            {/* Onboarding for new users — show first, AITransparency only after */}
            {!onboardingDone && (
                <OnboardingModal userName={user?.name} onDismiss={() => setOnboardingDone(true)} />
            )}

            {/* AI Act Art. 52: AI Transparency Modal — only after onboarding is done */}
            {onboardingDone && (
                <AITransparencyModal onAccept={() => {
                    logger.debug('AI Transparency accepted')
                }} />
            )}

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
                        <div className="chat-empty-state">
                            <h2 className="chat-empty-state__title">
                                ¿En qué puedo ayudarte?
                            </h2>
                            <div className="chat-empty-state__suggestions">
                                <button
                                    className="chat-suggestion-card"
                                    onClick={() => handleSuggestionClick('Calcula mi IRPF en mi comunidad autonoma')}
                                >
                                    <div className="chat-suggestion-card__icon">
                                        <Calculator size={20} />
                                    </div>
                                    <span className="chat-suggestion-card__text">Calcula mi IRPF</span>
                                </button>
                                <button
                                    className="chat-suggestion-card"
                                    onClick={() => handleSuggestionClick('Analiza mi ultima nomina y dime si las retenciones son correctas')}
                                >
                                    <div className="chat-suggestion-card__icon">
                                        <FileText size={20} />
                                    </div>
                                    <span className="chat-suggestion-card__text">Analiza mi nomina</span>
                                </button>
                                <button
                                    className="chat-suggestion-card"
                                    onClick={() => handleSuggestionClick('Que deducciones fiscales puedo aplicar en mi declaracion?')}
                                >
                                    <div className="chat-suggestion-card__icon">
                                        <Search size={20} />
                                    </div>
                                    <span className="chat-suggestion-card__text">Deducciones disponibles</span>
                                </button>
                                <button
                                    className="chat-suggestion-card"
                                    onClick={() => handleSuggestionClick('He recibido una notificación de la AEAT, ¿qué debo hacer?')}
                                >
                                    <div className="chat-suggestion-card__icon">
                                        <Shield size={20} />
                                    </div>
                                    <span className="chat-suggestion-card__text">Notificación AEAT</span>
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="chat-messages" ref={chatMessagesRef}>
                            {messages.map((message, index) => (
                                <div
                                    key={message.id}
                                    className={`message ${message.role} `}
                                >
                                    {message.role === 'assistant' ? (
                                        <div className="message-avatar">
                                            <Zap size={16} />
                                        </div>
                                    ) : (
                                        <div className="message-avatar message-avatar--user">
                                            {user?.name?.[0]?.toUpperCase() || 'U'}
                                        </div>
                                    )}
                                    <div className="message-content">
                                        {message.loading ? (
                                            <div className="message-loading">
                                                <Loader2 size={20} className="animate-spin" />
                                                <span>Analizando tu consulta...</span>
                                            </div>
                                        ) : (
                                            <>
                                                <div className="message-text">
                                                    {message.role === 'assistant' ? (
                                                        <FormattedMessage content={message.content} />
                                                    ) : (
                                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                            {message.content}
                                                        </ReactMarkdown>
                                                    )}
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
                                                {/* Deduction cards for deduction results */}
                                                {message.role === 'assistant' && hasDeductions(message.content) && (
                                                    <DeductionCards content={message.content} />
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

                            {/* STREAMING: Timeline + live content */}
                            {isStreaming && (
                                <div className="streaming-live">
                                    {/* Workspace context badge while streaming */}
                                    {activeWorkspace && (
                                        <div className="streaming-workspace-badge">
                                            <span className="streaming-workspace-icon">{activeWorkspace.icon}</span>
                                            <span>Consultando {activeWorkspace.file_count} {activeWorkspace.file_count === 1 ? 'documento' : 'documentos'} de <strong>{activeWorkspace.name}</strong></span>
                                        </div>
                                    )}

                                    {/* Chain-of-thought timeline (visible while no content yet) */}
                                    {streamState.steps.length > 0 && !streamState.response && (
                                        <StreamingTimeline steps={streamState.steps} />
                                    )}

                                    {/* Live response being typed */}
                                    {streamState.response && (
                                        <>
                                            {/* Collapsed mini-timeline while writing */}
                                            {streamState.steps.length > 0 && (
                                                <StreamingTimeline steps={streamState.steps} />
                                            )}
                                            <div className="message assistant">
                                                <div className="message-avatar">
                                                    <Zap size={16} />
                                                </div>
                                                <div className="message-content">
                                                    <div className="message-text">
                                                        <FormattedMessage content={streamState.response} />
                                                        <span className="streaming-cursor" />
                                                    </div>
                                                </div>
                                            </div>
                                        </>
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

                {/* Session document chips */}
                <SessionDocChips docs={sessionDocs} onRemove={removeDoc} />
                {docUploadError && (
                    <p className="session-doc-error">{docUploadError}</p>
                )}

                <form onSubmit={handleSubmit} className="chat-form">
                    {/* Workspace Selector */}
                    <WorkspaceSelector
                        workspaces={workspaces}
                        activeWorkspace={activeWorkspace}
                        onWorkspaceChange={handleWorkspaceChange}
                        onCreateNew={() => window.location.href = '/workspaces'}
                    />

                    {/* Session Doc Upload (paperclip) */}
                    <SessionDocUploadButton
                        isUploading={isDocUploading}
                        disabled={isLoading || isStreaming}
                        onFileSelected={(file) => uploadDoc(file)}
                    />

                    <input
                        type="text"
                        className="chat-input"
                        placeholder={sessionDocs.length > 0
                            ? `Pregunta sobre tus ${sessionDocs.length} documento(s)...`
                            : activeWorkspace
                                ? `Pregunta sobre ${activeWorkspace.name}...`
                                : "Escribe tu pregunta fiscal..."}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary chat-submit"
                        disabled={isLoading || !input.trim()}
                    >
                        {isLoading ? <Loader2 className="animate-spin" /> : <Send />}
                    </button>
                </form>
                <p className="chat-disclaimer">
                    Impuestify usa IA. Verifica siempre la información importante con un profesional.
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