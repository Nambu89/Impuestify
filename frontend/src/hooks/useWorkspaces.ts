import { useState, useCallback } from 'react'
import { useApi } from './useApi'

export interface Workspace {
    id: string
    user_id: string
    name: string
    description: string | null
    icon: string
    is_default: boolean
    max_files: number
    max_size_mb: number
    file_count: number
    created_at: string
    updated_at: string
}

export interface WorkspaceFile {
    id: string
    workspace_id: string
    filename: string
    file_type: 'nomina' | 'factura' | 'declaracion' | 'otro'
    mime_type: string
    file_size: number
    processing_status: 'pending' | 'processing' | 'completed' | 'error'
    error_message: string | null
    extracted_data: Record<string, any> | null
    created_at: string
}

export interface CreateWorkspaceData {
    name: string
    description?: string
    icon?: string
}

export function useWorkspaces() {
    const { apiRequest } = useApi()
    const [workspaces, setWorkspaces] = useState<Workspace[]>([])
    const [activeWorkspace, setActiveWorkspace] = useState<Workspace | null>(null)
    const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFile[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const fetchWorkspaces = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const data = await apiRequest<Workspace[]>('/api/workspaces', {
                method: 'GET'
            })
            setWorkspaces(data || [])

            // Auto-select default workspace if none selected
            // Using functional update to avoid dependency on activeWorkspace
            setActiveWorkspace(current => {
                if (!current && data && data.length > 0) {
                    return data.find(w => w.is_default) || data[0]
                }
                return current
            })

            return data
        } catch (err: any) {
            setError(err.message || 'Error al cargar workspaces')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])  // Removed activeWorkspace to prevent infinite loop

    const createWorkspace = useCallback(async (data: CreateWorkspaceData) => {
        setLoading(true)
        setError(null)
        try {
            const workspace = await apiRequest<Workspace>('/api/workspaces', {
                method: 'POST',
                body: JSON.stringify(data)
            })
            setWorkspaces(prev => [workspace, ...prev])
            return workspace
        } catch (err: any) {
            setError(err.message || 'Error al crear workspace')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const deleteWorkspace = useCallback(async (workspaceId: string) => {
        setLoading(true)
        setError(null)
        try {
            await apiRequest(`/api/workspaces/${workspaceId}`, {
                method: 'DELETE'
            })
            setWorkspaces(prev => prev.filter(w => w.id !== workspaceId))

            if (activeWorkspace?.id === workspaceId) {
                setActiveWorkspace(null)
                setWorkspaceFiles([])
            }
        } catch (err: any) {
            setError(err.message || 'Error al eliminar workspace')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest, activeWorkspace])

    const selectWorkspace = useCallback((workspace: Workspace | null) => {
        setActiveWorkspace(workspace)
        if (!workspace) {
            setWorkspaceFiles([])
        }
    }, [])

    const fetchWorkspaceFiles = useCallback(async (workspaceId: string) => {
        setLoading(true)
        try {
            const data = await apiRequest<WorkspaceFile[]>(`/api/workspaces/${workspaceId}/files`, {
                method: 'GET'
            })
            setWorkspaceFiles(data || [])
            return data
        } catch (err: any) {
            setWorkspaceFiles([])
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    const uploadFile = useCallback(async (workspaceId: string, file: File, fileType?: string) => {
        setLoading(true)
        setError(null)
        try {
            const formData = new FormData()
            formData.append('file', file)
            if (fileType) {
                formData.append('file_type', fileType)
            }

            const token = localStorage.getItem('access_token')
            const API_URL = import.meta.env.VITE_API_URL || '/api'

            const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/files`, {
                method: 'POST',
                headers: {
                    ...(token && { Authorization: `Bearer ${token}` })
                },
                body: formData
            })

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}))
                throw new Error(errorData.detail || 'Error al subir archivo')
            }

            const uploadedFile = await response.json()
            setWorkspaceFiles(prev => [uploadedFile, ...prev])

            // Update workspace file count
            setWorkspaces(prev => prev.map(w =>
                w.id === workspaceId
                    ? { ...w, file_count: w.file_count + 1 }
                    : w
            ))

            return uploadedFile
        } catch (err: any) {
            setError(err.message || 'Error al subir archivo')
            throw err
        } finally {
            setLoading(false)
        }
    }, [])

    const deleteFile = useCallback(async (workspaceId: string, fileId: string) => {
        setLoading(true)
        setError(null)
        try {
            await apiRequest(`/api/workspaces/${workspaceId}/files/${fileId}`, {
                method: 'DELETE'
            })
            setWorkspaceFiles(prev => prev.filter(f => f.id !== fileId))

            // Update workspace file count
            setWorkspaces(prev => prev.map(w =>
                w.id === workspaceId
                    ? { ...w, file_count: Math.max(0, w.file_count - 1) }
                    : w
            ))
        } catch (err: any) {
            setError(err.message || 'Error al eliminar archivo')
            throw err
        } finally {
            setLoading(false)
        }
    }, [apiRequest])

    return {
        workspaces,
        activeWorkspace,
        workspaceFiles,
        loading,
        error,
        fetchWorkspaces,
        createWorkspace,
        deleteWorkspace,
        selectWorkspace,
        fetchWorkspaceFiles,
        uploadFile,
        deleteFile
    }
}
