import { useCallback } from 'react'
import { useApi } from './useApi'

export interface FeedbackItem {
    id: string
    type: 'bug' | 'feature' | 'general'
    title: string
    description: string
    page_url: string | null
    status: 'new' | 'reviewed' | 'planned' | 'in_progress' | 'done' | 'wont_fix'
    priority: 'low' | 'normal' | 'high' | 'critical'
    admin_notes: string | null
    created_at: string
    updated_at: string
    user_email?: string
}

export interface FeedbackStats {
    bugs_open: number
    features_pending: number
    total: number
    new_count: number
}

export interface ChatRatingItem {
    id: string
    message_id: string
    conversation_id: string | null
    rating: 1 | -1
    comment: string | null
    created_at: string
    user_email?: string
}

export interface ChatRatingStats {
    total: number
    positive_pct: number
    negative_pct: number
    trend_30d: string
}

export interface ContactRequest {
    id: string
    email: string
    name: string | null
    subject: string | null
    message: string
    status: 'pending' | 'responded'
    created_at: string
}

export interface DashboardData {
    users: {
        total: number
        active_this_week: number
        subscribers_paid: number
        by_plan: { particular: number; autonomo: number }
        new_this_month: number
    }
    feedback: {
        bugs_open: number
        features_pending: number
        total: number
    }
    ratings: {
        total: number
        positive_pct: number
        negative_pct: number
        trend_30d: string
    }
    contact_requests: {
        pending: number
        total: number
    }
}

export function useFeedback() {
    const { apiRequest } = useApi()

    // --- Usuario ---

    const submitFeedback = useCallback(async (data: {
        type: 'bug' | 'feature' | 'general'
        title: string
        description: string
        page_url?: string
        screenshot_data?: string
    }): Promise<void> => {
        await apiRequest('/api/feedback', {
            method: 'POST',
            body: JSON.stringify(data),
        })
    }, [apiRequest])

    const getMyFeedback = useCallback(async (): Promise<FeedbackItem[]> => {
        return await apiRequest<FeedbackItem[]>('/api/feedback/my')
    }, [apiRequest])

    const submitChatRating = useCallback(async (data: {
        message_id: string
        conversation_id?: string
        rating: 1 | -1
        comment?: string
    }): Promise<void> => {
        await apiRequest('/api/chat-rating', {
            method: 'POST',
            body: JSON.stringify(data),
        })
    }, [apiRequest])

    // --- Admin ---

    const adminGetFeedback = useCallback(async (params: {
        type?: string
        status?: string
        priority?: string
        page?: number
        limit?: number
    } = {}): Promise<{ items: FeedbackItem[]; total: number }> => {
        const qs = new URLSearchParams()
        if (params.type) qs.set('type', params.type)
        if (params.status) qs.set('status', params.status)
        if (params.priority) qs.set('priority', params.priority)
        if (params.page) qs.set('page', String(params.page))
        if (params.limit) qs.set('limit', String(params.limit))
        const query = qs.toString() ? `?${qs.toString()}` : ''
        return await apiRequest<{ items: FeedbackItem[]; total: number }>(`/api/admin/feedback${query}`)
    }, [apiRequest])

    const adminGetFeedbackStats = useCallback(async (): Promise<FeedbackStats> => {
        return await apiRequest<FeedbackStats>('/api/admin/feedback/stats')
    }, [apiRequest])

    const adminGetFeedbackDetail = useCallback(async (id: string): Promise<FeedbackItem & { screenshot_data?: string }> => {
        return await apiRequest(`/api/admin/feedback/${id}`)
    }, [apiRequest])

    const adminUpdateFeedback = useCallback(async (id: string, data: {
        status?: FeedbackItem['status']
        priority?: FeedbackItem['priority']
        admin_notes?: string
    }): Promise<void> => {
        await apiRequest(`/api/admin/feedback/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data),
        })
    }, [apiRequest])

    const adminGetContactRequests = useCallback(async (params: {
        status?: string
        page?: number
        limit?: number
    } = {}): Promise<{ items: ContactRequest[]; total: number }> => {
        const qs = new URLSearchParams()
        if (params.status) qs.set('status', params.status)
        if (params.page) qs.set('page', String(params.page))
        if (params.limit) qs.set('limit', String(params.limit))
        const query = qs.toString() ? `?${qs.toString()}` : ''
        return await apiRequest<{ items: ContactRequest[]; total: number }>(`/api/admin/contact-requests${query}`)
    }, [apiRequest])

    const adminUpdateContactRequest = useCallback(async (id: string, status: 'pending' | 'responded'): Promise<void> => {
        await apiRequest(`/api/admin/contact-requests/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ status }),
        })
    }, [apiRequest])

    const adminGetChatRatings = useCallback(async (params: {
        rating?: string
        page?: number
        limit?: number
    } = {}): Promise<{ items: ChatRatingItem[]; total: number }> => {
        const qs = new URLSearchParams()
        if (params.rating) qs.set('rating', params.rating)
        if (params.page) qs.set('page', String(params.page))
        if (params.limit) qs.set('limit', String(params.limit))
        const query = qs.toString() ? `?${qs.toString()}` : ''
        return await apiRequest<{ items: ChatRatingItem[]; total: number }>(`/api/admin/chat-ratings${query}`)
    }, [apiRequest])

    const adminGetChatRatingStats = useCallback(async (): Promise<ChatRatingStats> => {
        return await apiRequest<ChatRatingStats>('/api/admin/chat-ratings/stats')
    }, [apiRequest])

    const adminGetDashboard = useCallback(async (): Promise<DashboardData> => {
        return await apiRequest<DashboardData>('/api/admin/dashboard')
    }, [apiRequest])

    return {
        submitFeedback,
        getMyFeedback,
        submitChatRating,
        adminGetFeedback,
        adminGetFeedbackStats,
        adminGetFeedbackDetail,
        adminUpdateFeedback,
        adminGetContactRequests,
        adminUpdateContactRequest,
        adminGetChatRatings,
        adminGetChatRatingStats,
        adminGetDashboard,
    }
}
