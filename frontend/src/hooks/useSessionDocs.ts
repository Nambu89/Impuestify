/**
 * Session Documents Hook
 *
 * Manages ephemeral document uploads for chat context.
 * Documents persist in sessionStorage (cleared on browser close, NOT on navigation).
 * Backend stores extracted text in Redis (2h TTL).
 */
import { useState, useEffect, useCallback } from 'react'
import { logger } from '../utils/logger'

const API_URL = import.meta.env.VITE_API_URL || '/api'
const STORAGE_KEY = 'session_docs'
const MAX_DOCS = 5

export interface SessionDoc {
    doc_id: string
    filename: string
    file_type: string
    summary: string
    page_count: number
}

interface UseSessionDocsReturn {
    docs: SessionDoc[]
    docIds: string[]
    isUploading: boolean
    uploadError: string | null
    uploadDoc: (file: File) => Promise<SessionDoc | null>
    removeDoc: (docId: string) => Promise<void>
    clearAll: () => void
}

function loadFromStorage(): SessionDoc[] {
    try {
        const raw = sessionStorage.getItem(STORAGE_KEY)
        return raw ? JSON.parse(raw) : []
    } catch {
        return []
    }
}

function saveToStorage(docs: SessionDoc[]) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(docs))
}

export function useSessionDocs(): UseSessionDocsReturn {
    const [docs, setDocs] = useState<SessionDoc[]>(loadFromStorage)
    const [isUploading, setIsUploading] = useState(false)
    const [uploadError, setUploadError] = useState<string | null>(null)

    // Sync to sessionStorage on changes
    useEffect(() => {
        saveToStorage(docs)
    }, [docs])

    const uploadDoc = useCallback(async (file: File): Promise<SessionDoc | null> => {
        if (docs.length >= MAX_DOCS) {
            setUploadError(`Maximo ${MAX_DOCS} documentos por sesion`)
            return null
        }

        setIsUploading(true)
        setUploadError(null)

        try {
            const token = localStorage.getItem('access_token')
            if (!token) throw new Error('No authentication token')

            const formData = new FormData()
            formData.append('file', file)

            const response = await fetch(`${API_URL}/api/session-docs/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData,
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(errorData.detail || `Error ${response.status}`)
            }

            const doc: SessionDoc = await response.json()
            setDocs(prev => [...prev, doc])
            logger.debug('Session doc uploaded:', doc.doc_id, doc.filename)
            return doc
        } catch (err: any) {
            const msg = err.message || 'Error al subir documento'
            setUploadError(msg)
            logger.error('Session doc upload failed:', err)
            return null
        } finally {
            setIsUploading(false)
        }
    }, [docs.length])

    const removeDoc = useCallback(async (docId: string) => {
        try {
            const token = localStorage.getItem('access_token')
            if (token) {
                await fetch(`${API_URL}/api/session-docs/${docId}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${token}` },
                })
            }
        } catch (err) {
            logger.warn('Failed to delete session doc from server:', err)
        }
        setDocs(prev => prev.filter(d => d.doc_id !== docId))
    }, [])

    const clearAll = useCallback(() => {
        setDocs([])
        sessionStorage.removeItem(STORAGE_KEY)
    }, [])

    return {
        docs,
        docIds: docs.map(d => d.doc_id),
        isUploading,
        uploadError,
        uploadDoc,
        removeDoc,
        clearAll,
    }
}
