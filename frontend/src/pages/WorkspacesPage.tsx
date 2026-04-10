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
    Receipt,
    Pencil,
    Check,
    RefreshCw
} from 'lucide-react'
import Header from '../components/Header'
import IntegrityBadge from '../components/IntegrityBadge'
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
    integrity_score: number | null
    integrity_findings: string | null
    cuenta_pgc: string | null
    cuenta_pgc_nombre: string | null
    clasificacion_confianza: string | null
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
    const [uploadProgress, setUploadProgress] = useState<string | null>(null)
    const [deletingFileId, setDeletingFileId] = useState<string | null>(null)
    const [isDragOver, setIsDragOver] = useState(false)
    const [renamingId, setRenamingId] = useState<string | null>(null)
    const [renamingValue, setRenamingValue] = useState('')
    const [confirmingFileId, setConfirmingFileId] = useState<string | null>(null)
    const [reclassifyFileId, setReclassifyFileId] = useState<string | null>(null)
    const [reclassifyValue, setReclassifyValue] = useState('')

    // Refs
    const fileInputRef = useRef<HTMLInputElement>(null)
    const dragCounterRef = useRef(0)
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

    const handleDeleteFile = async (fileId: string) => {
        if (!selectedWorkspace) return
        try {
            setDeletingFileId(fileId)
            await apiRequest(`/api/workspaces/${selectedWorkspace.id}/files/${fileId}`, {
                method: 'DELETE'
            })
            setWorkspaceFiles(prev => prev.filter(f => f.id !== fileId))
            fetchWorkspaces()
        } catch (err: any) {
            setError(err.message || 'Error al eliminar el archivo')
        } finally {
            setDeletingFileId(null)
        }
    }

    const startRenaming = (workspace: Workspace, e: React.MouseEvent) => {
        e.stopPropagation()
        setRenamingId(workspace.id)
        setRenamingValue(workspace.name)
    }

    const commitRename = async (workspace: Workspace) => {
        const trimmed = renamingValue.trim()
        setRenamingId(null)
        setRenamingValue('')
        if (!trimmed || trimmed === workspace.name) return
        try {
            await apiRequest(`/api/workspaces/${workspace.id}`, {
                method: 'PATCH',
                body: JSON.stringify({ name: trimmed })
            })
            fetchWorkspaces()
        } catch (err: any) {
            setError(err.message || 'Error al renombrar el workspace')
        }
    }

    const handleRenameKeyDown = (e: React.KeyboardEvent, workspace: Workspace) => {
        if (e.key === 'Enter') {
            e.preventDefault()
            commitRename(workspace)
        } else if (e.key === 'Escape') {
            setRenamingId(null)
            setRenamingValue('')
        }
    }

    const handleConfirmClassification = async (fileId: string) => {
        if (!selectedWorkspace) return
        try {
            setConfirmingFileId(fileId)
            const token = localStorage.getItem('access_token')
            const API_URL = import.meta.env.VITE_API_URL || '/api'
            const response = await fetch(
                `${API_URL}/api/workspaces/${selectedWorkspace.id}/files/${fileId}/confirm-classification`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token && { Authorization: `Bearer ${token}` }),
                    },
                    body: JSON.stringify({}),
                }
            )
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}))
                throw new Error(errData.detail || 'Error al confirmar')
            }
            fetchWorkspaceFiles(selectedWorkspace.id)
        } catch (err: any) {
            setError(err.message || 'Error al confirmar clasificacion')
        } finally {
            setConfirmingFileId(null)
        }
    }

    const handleReclassify = async (fileId: string) => {
        if (!selectedWorkspace || !reclassifyValue.trim()) return
        // Parse "600 — Compras" or "600 Compras" format
        const raw = reclassifyValue.trim()
        const match = raw.match(/^(\d{3,4})\s*[—\-–]?\s*(.+)$/)
        if (!match) {
            setError('Formato: "600 — Compras" (codigo + nombre)')
            return
        }
        const code = match[1]
        const nombre = match[2].trim()

        try {
            setConfirmingFileId(fileId)
            const token = localStorage.getItem('access_token')
            const API_URL = import.meta.env.VITE_API_URL || '/api'
            const response = await fetch(
                `${API_URL}/api/workspaces/${selectedWorkspace.id}/files/${fileId}/confirm-classification`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        ...(token && { Authorization: `Bearer ${token}` }),
                    },
                    body: JSON.stringify({
                        nueva_cuenta_code: code,
                        nueva_cuenta_nombre: nombre,
                    }),
                }
            )
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}))
                throw new Error(errData.detail || 'Error al reclasificar')
            }
            setReclassifyFileId(null)
            setReclassifyValue('')
            fetchWorkspaceFiles(selectedWorkspace.id)
        } catch (err: any) {
            setError(err.message || 'Error al reclasificar')
        } finally {
            setConfirmingFileId(null)
        }
    }

    const uploadSingleFile = async (file: File, workspaceId: string): Promise<void> => {
        const token = localStorage.getItem('access_token')
        const API_URL = import.meta.env.VITE_API_URL || '/api'
        const formDataObj = new FormData()
        formDataObj.append('file', file)
        const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/files`, {
            method: 'POST',
            headers: { ...(token && { Authorization: `Bearer ${token}` }) },
            body: formDataObj
        })
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            throw new Error(errorData.detail || 'Error al subir archivo')
        }
    }

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = event.target.files
        if (!files || files.length === 0 || !selectedWorkspace) return

        if (files.length > 10) {
            setError('Máximo 10 archivos por subida')
            if (fileInputRef.current) fileInputRef.current.value = ''
            return
        }

        setUploading(true)
        const total = files.length
        let succeeded = 0
        const errors: string[] = []

        for (let i = 0; i < total; i++) {
            setUploadProgress(total > 1 ? `Subiendo ${i + 1}/${total} archivos...` : null)
            try {
                await uploadSingleFile(files[i], selectedWorkspace.id)
                succeeded++
            } catch (err: any) {
                errors.push(`${files[i].name}: ${err.message}`)
            }
        }

        setUploadProgress(null)
        if (errors.length > 0) {
            setError(errors.join(' | '))
        }
        if (succeeded > 0) {
            fetchWorkspaceFiles(selectedWorkspace.id)
            fetchWorkspaces()
        }
        setUploading(false)
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    const handleDragEnter = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        dragCounterRef.current++
        if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
            setIsDragOver(true)
        }
    }

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        dragCounterRef.current--
        if (dragCounterRef.current === 0) {
            setIsDragOver(false)
        }
    }

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
    }

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragOver(false)
        dragCounterRef.current = 0

        if (!selectedWorkspace) return

        const droppedFiles = Array.from(e.dataTransfer.files || [])
        if (droppedFiles.length === 0) return

        if (droppedFiles.length > 10) {
            setError('Máximo 10 archivos por subida')
            return
        }

        const accepted = ['.pdf', '.png', '.jpg', '.jpeg', '.doc', '.docx', '.xls', '.xlsx', '.csv']
        const invalid = droppedFiles.filter(f => {
            const ext = '.' + f.name.split('.').pop()?.toLowerCase()
            return !accepted.includes(ext)
        })
        if (invalid.length > 0) {
            setError(`Tipo de archivo no admitido. Formatos permitidos: ${accepted.join(', ')}`)
            return
        }

        setUploading(true)
        const total = droppedFiles.length
        let succeeded = 0
        const errors: string[] = []

        for (let i = 0; i < total; i++) {
            setUploadProgress(total > 1 ? `Subiendo ${i + 1}/${total} archivos...` : null)
            try {
                await uploadSingleFile(droppedFiles[i], selectedWorkspace.id)
                succeeded++
            } catch (err: any) {
                errors.push(`${droppedFiles[i].name}: ${err.message}`)
            }
        }

        setUploadProgress(null)
        if (errors.length > 0) setError(errors.join(' | '))
        if (succeeded > 0) {
            fetchWorkspaceFiles(selectedWorkspace.id)
            fetchWorkspaces()
        }
        setUploading(false)
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
                                                {renamingId === workspace.id ? (
                                                    <input
                                                        className="workspace-rename-input"
                                                        value={renamingValue}
                                                        onChange={(e) => setRenamingValue(e.target.value)}
                                                        onBlur={() => commitRename(workspace)}
                                                        onKeyDown={(e) => handleRenameKeyDown(e, workspace)}
                                                        onClick={(e) => e.stopPropagation()}
                                                        autoFocus
                                                        maxLength={50}
                                                    />
                                                ) : (
                                                    <h3>{workspace.name}</h3>
                                                )}
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
                                                    className="btn btn-ghost workspace-action-btn rename-btn"
                                                    onClick={(e) => startRenaming(workspace, e)}
                                                    title="Renombrar workspace"
                                                >
                                                    <Pencil size={16} />
                                                </button>
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
                            <div
                                className={`files-panel${isDragOver && selectedWorkspace ? ' files-panel--drag-over' : ''}`}
                                onDragEnter={handleDragEnter}
                                onDragLeave={handleDragLeave}
                                onDragOver={handleDragOver}
                                onDrop={handleDrop}
                            >
                                {/* Hidden file input */}
                                <input
                                    id="workspace-file-upload"
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileUpload}
                                    accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.csv,image/*"
                                    multiple
                                    style={{ position: 'absolute', opacity: 0, width: 0, height: 0, overflow: 'hidden' }}
                                />

                                {/* Drag overlay */}
                                {isDragOver && selectedWorkspace && (
                                    <div className="files-drag-overlay">
                                        <Upload size={40} />
                                        <p>Suelta el archivo en {selectedWorkspace.name}</p>
                                    </div>
                                )}

                                {selectedWorkspace ? (
                                    <>
                                        <div className="files-header">
                                            <div className="files-header-content">
                                                <span className="files-workspace-icon">{selectedWorkspace.icon}</span>
                                                <h2>{selectedWorkspace.name}</h2>
                                            </div>
                                            <label
                                                htmlFor="workspace-file-upload"
                                                className="btn btn-primary btn-sm"
                                                style={{ cursor: uploading ? 'not-allowed' : 'pointer', opacity: uploading ? 0.4 : 1 }}
                                            >
                                                <Upload size={16} />
                                                <span>{uploadProgress || (uploading ? 'Subiendo...' : 'Subir archivos')}</span>
                                            </label>
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
                                                <span>Sube nóminas, facturas o declaraciones</span>
                                            </div>
                                        ) : (
                                            <div className="files-list">
                                                {workspaceFiles.map((file) => (
                                                    <div key={file.id} className="file-item">
                                                        <div className="file-icon">
                                                            {FILE_TYPE_ICONS[file.file_type] || FILE_TYPE_ICONS.otro}
                                                        </div>
                                                        <div className="file-info">
                                                            <div className="file-name-row">
                                                                <span className="file-name">{file.filename}</span>
                                                                <IntegrityBadge
                                                                    score={file.integrity_score ?? null}
                                                                    findings={file.integrity_findings ?? undefined}
                                                                    compact
                                                                />
                                                            </div>
                                                            <span className="file-meta">
                                                                {formatFileSize(file.file_size)} • {formatDate(file.created_at)}
                                                            </span>
                                                            {/* PGC Classification badge for invoices */}
                                                            {file.file_type === 'factura' && file.cuenta_pgc && (
                                                                <div className="file-classification">
                                                                    <span className={`classification-badge ${
                                                                        file.clasificacion_confianza === 'confirmada' || file.clasificacion_confianza === 'manual'
                                                                            ? 'classification-confirmed'
                                                                            : 'classification-pending'
                                                                    }`}>
                                                                        {file.cuenta_pgc} — {file.cuenta_pgc_nombre}
                                                                    </span>
                                                                    {file.clasificacion_confianza === 'pendiente_confirmacion' && (
                                                                        <span className="classification-status classification-status--pending">
                                                                            Por confirmar
                                                                        </span>
                                                                    )}
                                                                    {(file.clasificacion_confianza === 'confirmada' || file.clasificacion_confianza === 'manual') && (
                                                                        <span className="classification-status classification-status--confirmed">
                                                                            {file.clasificacion_confianza === 'manual' ? 'Manual' : 'Confirmada'}
                                                                        </span>
                                                                    )}
                                                                    {file.clasificacion_confianza === 'pendiente_confirmacion' && (
                                                                        <div className="classification-actions">
                                                                            <button
                                                                                className="btn btn-ghost classification-action-btn classification-confirm-btn"
                                                                                onClick={(e) => { e.stopPropagation(); handleConfirmClassification(file.id) }}
                                                                                disabled={confirmingFileId === file.id}
                                                                                title="Confirmar clasificacion"
                                                                            >
                                                                                <Check size={14} />
                                                                            </button>
                                                                            <button
                                                                                className="btn btn-ghost classification-action-btn classification-reclassify-btn"
                                                                                onClick={(e) => {
                                                                                    e.stopPropagation()
                                                                                    setReclassifyFileId(reclassifyFileId === file.id ? null : file.id)
                                                                                    setReclassifyValue('')
                                                                                }}
                                                                                title="Reclasificar"
                                                                            >
                                                                                <RefreshCw size={14} />
                                                                            </button>
                                                                        </div>
                                                                    )}
                                                                    {reclassifyFileId === file.id && (
                                                                        <div className="reclassify-input-row">
                                                                            <input
                                                                                className="reclassify-input"
                                                                                type="text"
                                                                                placeholder="600 — Compras"
                                                                                value={reclassifyValue}
                                                                                onChange={(e) => setReclassifyValue(e.target.value)}
                                                                                onKeyDown={(e) => {
                                                                                    if (e.key === 'Enter') { e.preventDefault(); handleReclassify(file.id) }
                                                                                    if (e.key === 'Escape') { setReclassifyFileId(null); setReclassifyValue('') }
                                                                                }}
                                                                                autoFocus
                                                                            />
                                                                            <button
                                                                                className="btn btn-primary btn-xs"
                                                                                onClick={() => handleReclassify(file.id)}
                                                                                disabled={!reclassifyValue.trim() || confirmingFileId === file.id}
                                                                            >
                                                                                Aplicar
                                                                            </button>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <div className="file-status">
                                                            {getStatusBadge(file.processing_status)}
                                                        </div>
                                                        <button
                                                            className="btn btn-ghost file-delete-btn"
                                                            onClick={() => handleDeleteFile(file.id)}
                                                            disabled={deletingFileId === file.id}
                                                        >
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
                                    <label className="label" htmlFor="description">Descripción</label>
                                    <textarea
                                        id="description"
                                        className="input textarea"
                                        placeholder="Descripción opcional del workspace"
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
                                Esta acción eliminará {workspaceToDelete.file_count} archivo(s)
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
