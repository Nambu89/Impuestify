import { useState, useCallback } from 'react'
import { useApi } from './useApi'
import { logger } from '../utils/logger'

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
        logger.debug('fetchConversations called')
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<Conversation[]>('/api/conversations', {
                method: 'GET'
            })
            logger.debug('Conversations fetched:', data.length)
            setConversations(data)
            return data
        } catch (err: any) {
            logger.error('Error fetching conversations:', err)
            setError(err.message || 'Failed to fetch conversations')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const createConversation = useCallback(async (title?: string) => {
        logger.debug('Creating conversation:', title)
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<Conversation>('/api/conversations', {
                method: 'POST',
                body: JSON.stringify({ title })
            })
            logger.debug('Conversation created:', data.id)
            setConversations(prev => [data, ...prev])
            return data
        } catch (err: any) {
            logger.error('Error creating conversation:', err)
            setError(err.message || 'Failed to create conversation')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const getConversation = useCallback(async (conversationId: string) => {
        logger.debug('Getting conversation:', conversationId)
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<ConversationWithMessages>(`/api/conversations/${conversationId}`, {
                method: 'GET'
            })
            logger.debug('Conversation loaded with', data.messages.length, 'messages')
            return data
        } catch (err: any) {
            logger.error('Error getting conversation:', err)
            setError(err.message || 'Failed to fetch conversation')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const updateConversationTitle = useCallback(async (conversationId: string, title: string) => {
        logger.debug('Updating conversation title:', conversationId)
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<Conversation>(`/api/conversations/${conversationId}`, {
                method: 'PATCH',
                body: JSON.stringify({ title })
            })
            logger.debug('Conversation title updated')
            setConversations(prev => prev.map(conv =>
                conv.id === conversationId ? data : conv
            ))
            return data
        } catch (err: any) {
            logger.error('Error updating conversation:', err)
            setError(err.message || 'Failed to update conversation')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const warmupChat = useCallback(async (): Promise<{ greeting: string; rag_preloaded: boolean } | null> => {
        try {
            const response = await apiRequest<{ greeting: string; rag_preloaded: boolean }>('/api/chat/warmup', { method: 'POST' })
            logger.debug('Warmup response:', response)
            return response
        } catch (e) {
            console.warn('Chat warmup failed:', e)
            return null
        }
    }, [apiRequest])

    const deleteConversation = useCallback(async (conversationId: string) => {
        logger.debug('Deleting conversation:', conversationId)
        setLoading(true)
        setError(null)
        try {
            await apiRequest(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            })
            logger.debug('Conversation deleted')
            setConversations(prev => prev.filter(conv => conv.id !== conversationId))
        } catch (err: any) {
            logger.error('Error deleting conversation:', err)
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
        deleteConversation,
        warmupChat
    }
}