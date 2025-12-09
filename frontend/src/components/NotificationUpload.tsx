import { useState, useCallback } from 'react'

interface NotificationAnalysis {
    id: string
    conversation_id?: string  // NEW: conversation ID from backend
    summary: string
    type: string
    deadlines: Array<{
        description: string
        date: string
        days_remaining: number
        is_urgent: boolean
    }>
    region: {
        region: string
        is_foral: boolean
    }
    severity: 'low' | 'medium' | 'high'
    reference_links: Array<{
        title: string
        url: string
    }>
}

interface NotificationUploadProps {
    onAnalysisComplete?: (analysis: NotificationAnalysis) => void
}

export function NotificationUpload({ onAnalysisComplete }: NotificationUploadProps) {
    const [file, setFile] = useState<File | null>(null)
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [dragActive, setDragActive] = useState(false)

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true)
        } else if (e.type === "dragleave") {
            setDragActive(false)
        }
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setDragActive(false)

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0]
            if (droppedFile.type === 'application/pdf') {
                setFile(droppedFile)
                setError(null)
            } else {
                setError('Solo se permiten archivos PDF')
            }
        }
    }, [])

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0]
            if (selectedFile.type === 'application/pdf') {
                setFile(selectedFile)
                setError(null)
            } else {
                setError('Solo se permiten archivos PDF')
            }
        }
    }

    const handleUpload = async () => {
        if (!file) return

        setUploading(true)
        setError(null)

        try {
            const token = localStorage.getItem('access_token')

            // Validate token exists
            if (!token) {
                setError('No estás autenticado. Redirigiendo al login...')
                setTimeout(() => {
                    window.location.href = '/login'
                }, 2000)
                return
            }

            const formData = new FormData()
            formData.append('file', file)

            const response = await fetch('http://localhost:8000/api/notifications/analyze', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            })

            if (!response.ok) {
                // Auto-logout on 401
                if (response.status === 401) {
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    setError('Tu sesión ha expirado. Redirigiendo al login...')
                    setTimeout(() => {
                        window.location.href = '/login?expired=true'
                    }, 2000)
                    return
                }

                const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
                throw new Error(errorData.detail || 'Error al analizar')
            }

            const analysis: NotificationAnalysis = await response.json()

            if (onAnalysisComplete) {
                onAnalysisComplete(analysis)
            }

            // Reset
            setFile(null)
        } catch (err: any) {
            setError(err.message || 'Error al analizar la notificación')
        } finally {
            setUploading(false)
        }
    }

    return (
        <div className="notification-upload">
            <div
                className={`drop-zone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
            >
                {file ? (
                    <div className="file-info">
                        <span className="file-icon">📄</span>
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">{(file.size / 1024).toFixed(2)} KB</span>
                        <button
                            className="remove-btn"
                            onClick={() => setFile(null)}
                            disabled={uploading}
                        >
                            ✕
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="upload-icon">📎</div>
                        <p className="upload-text">
                            Arrastra aquí tu notificación PDF<br />
                            o haz clic para seleccionar
                        </p>
                        <input
                            type="file"
                            accept="application/pdf"
                            onChange={handleFileChange}
                            disabled={uploading}
                            className="file-input"
                        />
                    </>
                )}
            </div>

            {error && (
                <div className="error-message">
                    ⚠️ {error}
                </div>
            )}

            {file && !uploading && (
                <button
                    className="upload-btn"
                    onClick={handleUpload}
                >
                    Analizar Notificación
                </button>
            )}

            {uploading && (
                <div className="uploading-state">
                    <div className="spinner"></div>
                    <p>Analizando notificación...</p>
                    <p className="sub-text">Esto puede tardar 15-20 segundos</p>
                </div>
            )}

            <style>{`
                .notification-upload {
                    margin: 20px 0;
                }

                .drop-zone {
                    border: 2px dashed #cbd5e0;
                    border-radius: 12px;
                    padding: 40px 20px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s;
                    position: relative;
                    background: #f7fafc;
                }

                .drop-zone:hover {
                    border-color: #4299e1;
                    background: #ebf8ff;
                }

                .drop-zone.drag-active {
                    border-color: #3182ce;
                    background: #bee3f8;
                }

                .drop-zone.has-file {
                    cursor: default;
                    border-color: #48bb78;
                    background: #f0fff4;
                }

                .upload-icon {
                    font-size: 48px;
                    margin-bottom: 16px;
                }

                .upload-text {
                    color: #4a5568;
                    line-height: 1.6;
                }

                .file-input {
                    position: absolute;
                    width: 100%;
                    height: 100%;
                    top: 0;
                    left: 0;
                    opacity: 0;
                    cursor: pointer;
                }

                .file-info {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    justify-content: center;
                    flex-wrap: wrap;
                }

                .file-icon {
                    font-size: 32px;
                }

                .file-name {
                    font-weight: 600;
                    color: #2d3748;
                }

                .file-size {
                    color: #718096;
                    font-size: 14px;
                }

                .remove-btn {
                    background: #fc8181;
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    cursor: pointer;
                    font-size: 16px;
                    transition: background 0.2s;
                }

                .remove-btn:hover {
                    background: #f56565;
                }

                .error-message {
                    margin-top: 12px;
                    padding: 12px;
                    background: #fff5f5;
                    border: 1px solid #feb2b2;
                    border-radius: 8px;
                    color: #c53030;
                }

                .upload-btn {
                    width: 100%;
                    margin-top: 16px;
                    padding: 14px;
                    background: #4299e1;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: background 0.2s;
                }

                .upload-btn:hover {
                    background: #3182ce;
                }

                .uploading-state {
                    text-align: center;
                    padding: 30px;
                }

                .spinner {
                    border: 3px solid #e2e8f0;
                    border-top: 3px solid #4299e1;
                    border-radius: 50%;
                    width: 40px;
                    height: 40px;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 16px;
                }

                .sub-text {
                    color: #718096;
                    font-size: 14px;
                    margin-top: 8px;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    )
}
