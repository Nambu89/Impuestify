import { useState, useEffect, useCallback, useRef } from 'react'
import {
    FolderOpen,
    Plus,
    Trash2,
    FileText,
    Clock,
    Star,
    X,
    AlertCircle,
    Upload,
    File,
    FileSpreadsheet,
    Receipt
} from 'lucide-react'
import Header from '../components/Header'
import { useApi } from '../hooks/useApi'
import './WorkspacesPage.css'

interface Workspace {
    id: string
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

interface WorkspaceFile {
    id: string
    filename: string
    file_type: string
    file_size: number
    processing_status: string
    created_at: string
}

interface CreateWorkspaceData {
    name: string
    description: string
    icon: string
}

const ICON_OPTIONS = ['📁', '📂', '💼', '📊', '📈', '💰', '🏦', '📋', '🗂️', '📑']

const FILE_TYPE_ICONS: Record<string, React.ReactNode> = {
    nomina: <FileText size={20} />,
    factura: <Receipt size={20} />,
    declaracion: <FileSpreadsheet size={20} />,
    otro: <File size={20} />
}

export default function WorkspacesPage() {
    const { apiRequest } = useApi()
    const [workspaces, setWorkspaces] = useState<Workspace[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Selected workspace for file view
    const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null)
    const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFile[]>([])
    const [filesLoading, setFilesLoading] = useState(false)

    // Modal states
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [showDeleteModal, setShowDeleteModal] = useState(false)
    const [workspaceToDelete, setWorkspaceToDelete] = useState<Workspace | null>(null)

    // Form state
    const [formData, setFormData] = useState<CreateWorkspaceData>({
        name: '',
        description: '',
        icon: '📁'
    })
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [formError, setFormError] = useState<string | null>(null)
    const [uploading, setUploading] = useState(false)

    // Refs
    const fileInputRef = useRef<HTMLInputElement>(null)
    const hasFetched = useRef(false)

    const fetchWorkspaces = useCallback(async () => {
        try {
            setIsLoading(true)
            setError(null)
            const data = await apiRequest<Workspace[]>('/api/workspaces')
            setWorkspaces(data || [])
        } catch (err: any) {
            setError(err.message || 'Error al cargar los workspaces')
        } finally {
            setIsLoading(false)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])  // Empty deps - apiRequest is stable enough

    const fetchWorkspaceFiles = useCallback(async (workspaceId: string) => {
        try {
            setFilesLoading(true)
            const data = await apiRequest<WorkspaceFile[]>(`/api/workspaces/${workspaceId}/files`)
            setWorkspaceFiles(data || [])
        } catch (err: any) {
            setWorkspaceFiles([])
        } finally {
            setFilesLoading(false)
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])  // Empty deps - apiRequest is stable enough

    // Fetch workspaces only once on mount
    useEffect(() => {
        if (!hasFetched.current) {
            hasFetched.current = true
            fetchWorkspaces()
        }
    }, [fetchWorkspaces])

    // Fetch files when workspace is selected
    useEffect(() => {
        if (selectedWorkspace) {
            fetchWorkspaceFiles(selectedWorkspace.id)
        }
    }, [selectedWorkspace?.id, fetchWorkspaceFiles])

    const handleCreateWorkspace = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!formData.name.trim()) {
            setFormError('El nombre es obligatorio')
            return
        }

        try {
            setIsSubmitting(true)
            setFormError(null)

            await apiRequest<Workspace>('/api/workspaces', {
                method: 'POST',
                body: JSON.stringify({
                    name: formData.name.trim(),
                    description: formData.description.trim() || null,
                    icon: formData.icon
                })
            })

            setShowCreateModal(false)
            setFormData({ name: '', description: '', icon: '📁' })
            fetchWorkspaces()
        } catch (err: any) {
            setFormError(err.message || 'Error al crear el workspace')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleDeleteWorkspace = async () => {
        if (!workspaceToDelete) return

        try {
            setIsSubmitting(true)
            await apiRequest(`/api/workspaces/${workspaceToDelete.id}`, {
                method: 'DELETE'
            })

            setShowDeleteModal(false)
            setWorkspaceToDelete(null)
            if (selectedWorkspace?.id === workspaceToDelete.id) {
                setSelectedWorkspace(null)
                setWorkspaceFiles([])
            }
            fetchWorkspaces()
        } catch (err: any) {
            setFormError(err.message || 'Error al eliminar el workspace')
        } finally {
            setIsSubmitting(false)
        }
    }

    const openDeleteModal = (workspace: Workspace, e: React.MouseEvent) => {
        e.stopPropagation()
        setWorkspaceToDelete(workspace)
        setShowDeleteModal(true)
        setFormError(null)
    }

    const selectWorkspace = (workspace: Workspace) => {
        setSelectedWorkspace(workspace)
    }

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (!file || !selectedWorkspace) return

        setUploading(true)
        try {
            const formData = new FormData()
            formData.append('file', file)

            const token = localStorage.getItem('access_token')
            const API_URL = import.meta.env.VITE_API_URL || '/api'

            const response = await fetch(`${API_URL}/api/workspaces/${selectedWorkspace.id}/files`, {
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

            // Refresh files list
            fetchWorkspaceFiles(selectedWorkspace.id)
            // Update workspace file count
            fetchWorkspaces()
        } catch (err: any) {
            setError(err.message || 'Error al subir archivo')
        } finally {
            setUploading(false)
            // Reset input so same file can be uploaded again
            if (fileInputRef.current) {
                fileInputRef.current.value = ''
            }
        }
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'short',
            year: 'numeric'
        })
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    const getStatusBadge = (status: string) => {
        const statusConfig: Record<string, { label: string; className: string }> = {
            completed: { label: 'Procesado', className: 'status-success' },
            processing: { label: 'Procesando', className: 'status-warning' },
            pending: { label: 'Pendiente', className: 'status-pending' },
            error: { label: 'Error', className: 'status-error' }
        }
        const config = statusConfig[status] || statusConfig.pending
        return <span className={`status-badge ${config.className}`}>{config.label}</span>
    }

    return (
        <div className="workspaces-page">
            <Header />

            <main className="workspaces-main">
                <div className="container">
                    {/* Page Header */}
                    <div className="workspaces-header">
                        <div className="workspaces-header-content">
                            <h1>Mis Workspaces</h1>
                            <p>Organiza tus documentos fiscales en espacios de trabajo</p>
                        </div>
                        <button
                            className="btn btn-primary"
                            onClick={() => setShowCreateModal(true)}
                        >
                            <Plus size={20} />
                            <span>Nuevo Workspace</span>
                        </button>
                    </div>

                    {/* Error State */}
                    {error && (
                        <div className="workspaces-error">
                            <AlertCircle size={20} />
                            <span>{error}</span>
                            <button onClick={fetchWorkspaces}>Reintentar</button>
                        </div>
                    )}

                    {/* Loading State */}
                    {isLoading ? (
                        <div className="workspaces-loading">
                            <div className="loading-spinner"></div>
                            <p>Cargando workspaces...</p>
                        </div>
                    ) : workspaces.length === 0 ? (
                        /* Empty State */
                        <div className="workspaces-empty">
                            <div className="empty-icon">
                                <FolderOpen size={64} />
                            </div>
                            <h2>No tienes workspaces</h2>
                            <p>Crea tu primer workspace para organizar tus documentos fiscales</p>
                            <button
                                className="btn btn-primary btn-lg"
                                onClick={() => setShowCreateModal(true)}
                            >
                                <Plus size={20} />
                                Crear mi primer workspace
                            </button>
                        </div>
                    ) : (
                        /* Main Content: Workspaces + Files */
                        <div className="workspaces-layout">
                            {/* Workspaces List */}
                            <div className="workspaces-list">
                                <h2 className="section-title">Espacios de trabajo</h2>
                                <div className="workspaces-grid">
                                    {workspaces.map((workspace) => (
                                        <div
                                            key={workspace.id}
                                            className={`workspace-card ${workspace.is_default ? 'is-default' : ''} ${selectedWorkspace?.id === workspace.id ? 'is-selected' : ''}`}
                                            onClick={() => selectWorkspace(workspace)}
                                        >
                                            {workspace.is_default && (
                                                <div className="workspace-badge">
                                                    <Star size={12} />
                                                    <span>Principal</span>
                                                </div>
                                            )}

                                            <div className="workspace-icon">
                                                {workspace.icon}
                                            </div>

                                            <div className="workspace-content">
                                                <h3>{workspace.name}</h3>
                                                {workspace.description && (
                                                    <p className="workspace-description">
                                                        {workspace.description}
                                                    </p>
                                                )}

                                                <div className="workspace-stats">
                                                    <div className="stat">
                                                        <FileText size={14} />
                                                        <span>{workspace.file_count} archivos</span>
                                                    </div>
                                                    <div className="stat">
                                                        <Clock size={14} />
                                                        <span>{formatDate(workspace.created_at)}</span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="workspace-actions">
                                                <button
                                                    className="btn btn-ghost workspace-action-btn"
                                                    onClick={(e) => openDeleteModal(workspace, e)}
                                                    title="Eliminar workspace"
                                                >
                                                    <Trash2 size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Files Panel */}
                            <div className="files-panel">
                                {/* Hidden file input */}
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileUpload}
                                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx"
                                    style={{ display: 'none' }}
                                />

                                {selectedWorkspace ? (
                                    <>
                                        <div className="files-header">
                                            <div className="files-header-content">
                                                <span className="files-workspace-icon">{selectedWorkspace.icon}</span>
                                                <h2>{selectedWorkspace.name}</h2>
                                            </div>
                                            <button
                                                className="btn btn-primary btn-sm"
                                                onClick={() => fileInputRef.current?.click()}
                                                disabled={uploading}
                                            >
                                                <Upload size={16} />
                                                <span>{uploading ? 'Subiendo...' : 'Subir archivo'}</span>
                                            </button>
                                        </div>

                                        {filesLoading ? (
                                            <div className="files-loading">
                                                <div className="loading-spinner"></div>
                                                <p>Cargando archivos...</p>
                                            </div>
                                        ) : workspaceFiles.length === 0 ? (
                                            <div className="files-empty">
                                                <Upload size={48} />
                                                <p>No hay archivos en este workspace</p>
                                                <span>Sube nominas, facturas o declaraciones</span>
                                            </div>
                                        ) : (
                                            <div className="files-list">
                                                {workspaceFiles.map((file) => (
                                                    <div key={file.id} className="file-item">
                                                        <div className="file-icon">
                                                            {FILE_TYPE_ICONS[file.file_type] || FILE_TYPE_ICONS.otro}
                                                        </div>
                                                        <div className="file-info">
                                                            <span className="file-name">{file.filename}</span>
                                                            <span className="file-meta">
                                                                {formatFileSize(file.file_size)} • {formatDate(file.created_at)}
                                                            </span>
                                                        </div>
                                                        <div className="file-status">
                                                            {getStatusBadge(file.processing_status)}
                                                        </div>
                                                        <button className="btn btn-ghost file-delete-btn">
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <div className="files-placeholder">
                                        <FolderOpen size={48} />
                                        <p>Selecciona un workspace para ver sus archivos</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </main>

            {/* Create Workspace Modal */}
            {showCreateModal && (
                <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
                    <div className="modal" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Crear Workspace</h2>
                            <button
                                className="modal-close"
                                onClick={() => setShowCreateModal(false)}
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <form onSubmit={handleCreateWorkspace}>
                            <div className="modal-body">
                                {formError && (
                                    <div className="form-error">
                                        <AlertCircle size={16} />
                                        <span>{formError}</span>
                                    </div>
                                )}

                                <div className="form-group">
                                    <label className="label">Icono</label>
                                    <div className="icon-picker">
                                        {ICON_OPTIONS.map((icon) => (
                                            <button
                                                key={icon}
                                                type="button"
                                                className={`icon-option ${formData.icon === icon ? 'selected' : ''}`}
                                                onClick={() => setFormData({ ...formData, icon })}
                                            >
                                                {icon}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="form-group">
                                    <label className="label" htmlFor="name">Nombre *</label>
                                    <input
                                        type="text"
                                        id="name"
                                        className="input"
                                        placeholder="Ej: Declaraciones 2024"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        maxLength={50}
                                        autoFocus
                                    />
                                </div>

                                <div className="form-group">
                                    <label className="label" htmlFor="description">Descripcion</label>
                                    <textarea
                                        id="description"
                                        className="input textarea"
                                        placeholder="Descripcion opcional del workspace"
                                        value={formData.description}
                                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                        rows={3}
                                        maxLength={200}
                                    />
                                </div>
                            </div>

                            <div className="modal-footer">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={() => setShowCreateModal(false)}
                                    disabled={isSubmitting}
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                    disabled={isSubmitting || !formData.name.trim()}
                                >
                                    {isSubmitting ? 'Creando...' : 'Crear Workspace'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {showDeleteModal && workspaceToDelete && (
                <div className="modal-overlay" onClick={() => setShowDeleteModal(false)}>
                    <div className="modal modal-sm" onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>Eliminar Workspace</h2>
                            <button
                                className="modal-close"
                                onClick={() => setShowDeleteModal(false)}
                            >
                                <X size={20} />
                            </button>
                        </div>

                        <div className="modal-body">
                            {formError && (
                                <div className="form-error">
                                    <AlertCircle size={16} />
                                    <span>{formError}</span>
                                </div>
                            )}

                            <p className="delete-warning">
                                ¿Estas seguro de que deseas eliminar el workspace
                                <strong> "{workspaceToDelete.name}"</strong>?
                            </p>
                            <p className="delete-info">
                                Esta accion eliminara {workspaceToDelete.file_count} archivo(s)
                                y no se puede deshacer.
                            </p>
                        </div>

                        <div className="modal-footer">
                            <button
                                type="button"
                                className="btn btn-secondary"
                                onClick={() => setShowDeleteModal(false)}
                                disabled={isSubmitting}
                            >
                                Cancelar
                            </button>
                            <button
                                type="button"
                                className="btn btn-danger"
                                onClick={handleDeleteWorkspace}
                                disabled={isSubmitting}
                            >
                                {isSubmitting ? 'Eliminando...' : 'Eliminar'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
