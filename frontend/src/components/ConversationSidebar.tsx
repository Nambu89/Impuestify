import { useEffect } from 'react'
import { MessageSquare, Plus, Trash2 } from 'lucide-react'
import { useConversations } from '../hooks/useConversations'
import './ConversationSidebar.css'

interface ConversationSidebarProps {
    activeConversationId: string | null
    onSelectConversation: (conversationId: string) => void
    onNewConversation: () => void
}

export function ConversationSidebar({
    activeConversationId,
    onSelectConversation,
    onNewConversation
}: ConversationSidebarProps) {
    const {
        conversations,
        loading,
        fetchConversations,
        deleteConversation
    } = useConversations()

    useEffect(() => {
        fetchConversations()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    // Refresh sidebar when active conversation changes (new conversation created)
    useEffect(() => {
        if (activeConversationId) {
            fetchConversations()
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeConversationId])

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
        <div className="conversation-sidebar">
            <div className="sidebar-header">
                <h2>Conversaciones</h2>
                <button
                    className="new-chat-btn"
                    onClick={onNewConversation}
                    title="Nueva conversación"
                >
                    <Plus size={20} />
                </button>
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
                            onClick={() => onSelectConversation(conv.id)}
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
    )
}
