import { useState, useCallback } from 'react'
import { useApi } from './useApi'

export interface Conversation {
    id: string
    user_id: string
    title: string
    created_at: string
    updated_at: string
}

export interface Message {
    id: string
    conversation_id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    metadata: {
        sources?: Array<{
            id: string
            source: string
            page: number
            title: string
            score: number
        }>
        notification_id?: string
    }
    created_at: string
}

export interface ConversationWithMessages {
    conversation: Conversation
    messages: Message[]
}

export function useConversations() {
    const { apiRequest } = useApi()
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const fetchConversations = useCallback(async () => {
        console.log('🔄 fetchConversations called')
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<Conversation[]>('/api/conversations', {
                method: 'GET'
            })
            console.log('✅ Conversations fetched:', data.length)
            setConversations(data)
            return data
        } catch (err: any) {
            console.error('❌ Error fetching conversations:', err)
            setError(err.message || 'Failed to fetch conversations')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const createConversation = useCallback(async (title?: string) => {
        console.log('➕ Creating conversation:', title)
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<Conversation>('/api/conversations', {
                method: 'POST',
                body: JSON.stringify({ title })
            })
            console.log('✅ Conversation created:', data.id)
            setConversations(prev => [data, ...prev])
            return data
        } catch (err: any) {
            console.error('❌ Error creating conversation:', err)
            setError(err.message || 'Failed to create conversation')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const getConversation = useCallback(async (conversationId: string) => {
        console.log('📖 Getting conversation:', conversationId)
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<ConversationWithMessages>(`/api/conversations/${conversationId}`, {
                method: 'GET'
            })
            console.log('✅ Conversation loaded with', data.messages.length, 'messages')
            return data
        } catch (err: any) {
            console.error('❌ Error getting conversation:', err)
            setError(err.message || 'Failed to fetch conversation')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const updateConversationTitle = useCallback(async (conversationId: string, title: string) => {
        console.log('✏️ Updating conversation title:', conversationId, title)
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<Conversation>(`/api/conversations/${conversationId}`, {
                method: 'PATCH',
                body: JSON.stringify({ title })
            })
            console.log('✅ Conversation title updated')
            setConversations(prev => prev.map(conv =>
                conv.id === conversationId ? data : conv
            ))
            return data
        } catch (err: any) {
            console.error('❌ Error updating conversation:', err)
            setError(err.message || 'Failed to update conversation')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const deleteConversation = useCallback(async (conversationId: string) => {
        console.log('🗑️ Deleting conversation:', conversationId)
        setLoading(true)
        setError(null)
        try {
            await apiRequest(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            })
            console.log('✅ Conversation deleted')
            setConversations(prev => prev.filter(conv => conv.id !== conversationId))
        } catch (err: any) {
            console.error('❌ Error deleting conversation:', err)
            setError(err.message || 'Failed to delete conversation')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    return {
        conversations,
        loading,
        error,
        fetchConversations,
        createConversation,
        getConversation,
        updateConversationTitle,
        deleteConversation
    }
}