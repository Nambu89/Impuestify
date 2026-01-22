import { useEffect } from 'react'
import { MessageSquare, Plus, Trash2, X } from 'lucide-react'
import { useConversations } from '../hooks/useConversations'
import { logger } from '../utils/logger'
import './ConversationSidebar.css'

interface ConversationSidebarProps {
    activeConversationId: string | null
    onSelectConversation: (conversationId: string) => void
    onNewConversation: () => void
    isOpen?: boolean
    onClose?: () => void
}

export function ConversationSidebar({
    activeConversationId,
    onSelectConversation,
    onNewConversation,
    isOpen = false,
    onClose
}: ConversationSidebarProps) {
    const {
        conversations,
        loading,
        fetchConversations,
        deleteConversation
    } = useConversations()

    // Fetch conversations when sidebar opens or active conversation changes
    useEffect(() => {
        logger.debug('ConversationSidebar: Triggering fetch')
        fetchConversations()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeConversationId, isOpen])

    const handleDelete = async (e: React.MouseEvent, conversationId: string) => {
        e.stopPropagation()
        if (confirm('¿Eliminar esta conversación?')) {
            await deleteConversation(conversationId)
            if (activeConversationId === conversationId) {
                onNewConversation()
            }
        }
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMs / 3600000)
        const diffDays = Math.floor(diffMs / 86400000)

        if (diffMins < 1) return 'Ahora'
        if (diffMins < 60) return `Hace ${diffMins}m`
        if (diffHours < 24) return `Hace ${diffHours}h`
        if (diffDays < 7) return `Hace ${diffDays}d`
        return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
    }

    return (
        <>
            <div className={`conversation-sidebar ${isOpen ? 'mobile-open' : ''}`}>
                <div className="sidebar-header">
                    <h2>Conversaciones</h2>
                    <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button
                            className="new-chat-btn"
                            onClick={onNewConversation}
                            title="Nueva conversación"
                        >
                            <Plus size={20} />
                        </button>
                        {onClose && (
                            <button
                                className="close-sidebar-btn"
                                onClick={onClose}
                                title="Cerrar"
                                style={{
                                    background: 'none',
                                    border: 'none',
                                    padding: '8px',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: '#666',
                                    borderRadius: '8px'
                                }}
                            >
                                <X size={20} />
                            </button>
                        )}
                    </div>
                </div>

                <div className="conversations-list">
                    {loading && conversations.length === 0 ? (
                        <div className="loading-state">Cargando...</div>
                    ) : conversations.length === 0 ? (
                        <div className="empty-state">
                            <MessageSquare size={48} opacity={0.3} />
                            <p>No hay conversaciones</p>
                            <p className="hint">Haz una pregunta para empezar</p>
                        </div>
                    ) : (
                        conversations.map((conv) => (
                            <div
                                key={conv.id}
                                className={`conversation-item ${activeConversationId === conv.id ? 'active' : ''}`}
                                onClick={() => {
                                    onSelectConversation(conv.id)
                                    if (onClose) onClose() // Cerrar sidebar en móvil
                                }}
                            >
                                <div className="conversation-content">
                                    <MessageSquare size={16} />
                                    <div className="conversation-info">
                                        <div className="conversation-title">{conv.title}</div>
                                        <div className="conversation-date">{formatDate(conv.updated_at)}</div>
                                    </div>
                                </div>
                                <button
                                    className="delete-btn"
                                    onClick={(e) => handleDelete(e, conv.id)}
                                    title="Eliminar conversación"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </>
    )
}