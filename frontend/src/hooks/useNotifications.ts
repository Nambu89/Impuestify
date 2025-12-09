import { useState } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

interface NotificationAnalysis {
    id: string
    summary: string
    type: string
    deadlines: Deadline[]
    region: {
        region: string
        is_foral: boolean
    }
    severity: 'low' | 'medium' | 'high'
    reference_links: Reference[]
    notification_date: string
}

interface Deadline {
    description: string
    date: string
    days_remaining: number
    is_urgent: boolean
}

interface Reference {
    title: string
    url: string
}

export function useNotifications() {
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const uploadNotification = async (
        file: File,
        notificationDate?: string
    ): Promise<NotificationAnalysis> => {
        setUploading(true)
        setError(null)

        try {
            const formData = new FormData()
            formData.append('file', file)
            if (notificationDate) {
                formData.append('notification_date', notificationDate)
            }

            const token = localStorage.getItem('token')
            const response = await axios.post<NotificationAnalysis>(
                `${API_URL}/notifications/analyze`,
                formData,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'multipart/form-data'
                    }
                }
            )

            return response.data
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || 'Error al analizar la notificación'
            setError(errorMessage)
            throw new Error(errorMessage)
        } finally {
            setUploading(false)
        }
    }

    const getHistory = async (limit: number = 10) => {
        try {
            const token = localStorage.getItem('token')
            const response = await axios.get(
                `${API_URL}/notifications/history?limit=${limit}`,
                {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                }
            )
            return response.data
        } catch (err: any) {
            throw new Error(err.response?.data?.detail || 'Error al obtener historial')
        }
    }

    return {
        uploadNotification,
        getHistory,
        uploading,
        error
    }
}