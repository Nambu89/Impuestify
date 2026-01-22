import { useState, useRef, useCallback } from 'react'
import { Upload, File, FileText, Receipt, FileSpreadsheet, X, AlertCircle, CheckCircle, Loader2 } from 'lucide-react'
import './FileUploader.css'

interface FileUploaderProps {
    onUpload: (file: File, fileType?: string) => Promise<void>
    accept?: string
    maxSizeMB?: number
    disabled?: boolean
}

type FileType = 'nomina' | 'factura' | 'declaracion' | 'otro'

const FILE_TYPES: { value: FileType; label: string; icon: React.ReactNode }[] = [
    { value: 'nomina', label: 'Nomina', icon: <FileText size={16} /> },
    { value: 'factura', label: 'Factura', icon: <Receipt size={16} /> },
    { value: 'declaracion', label: 'Declaracion', icon: <FileSpreadsheet size={16} /> },
    { value: 'otro', label: 'Otro', icon: <File size={16} /> }
]

export function FileUploader({
    onUpload,
    accept = '.pdf,.xlsx,.xls,.csv',
    maxSizeMB = 10,
    disabled = false
}: FileUploaderProps) {
    const [isDragging, setIsDragging] = useState(false)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [selectedType, setSelectedType] = useState<FileType>('otro')
    const [isUploading, setIsUploading] = useState(false)
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle')
    const [errorMessage, setErrorMessage] = useState<string | null>(null)

    const fileInputRef = useRef<HTMLInputElement>(null)

    const validateFile = useCallback((file: File): string | null => {
        // Check file size
        const maxSize = maxSizeMB * 1024 * 1024
        if (file.size > maxSize) {
            return `El archivo excede el tamaño maximo de ${maxSizeMB}MB`
        }

        // Check file type
        const allowedTypes = accept.split(',').map(t => t.trim().toLowerCase())
        const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
        const mimeType = file.type.toLowerCase()

        const isValidExtension = allowedTypes.some(type =>
            type === fileExtension ||
            (type === '.pdf' && mimeType === 'application/pdf') ||
            (type === '.xlsx' && mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') ||
            (type === '.xls' && mimeType === 'application/vnd.ms-excel') ||
            (type === '.csv' && (mimeType === 'text/csv' || mimeType === 'application/csv'))
        )

        if (!isValidExtension) {
            return `Tipo de archivo no permitido. Tipos aceptados: ${accept}`
        }

        return null
    }, [accept, maxSizeMB])

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        if (!disabled) {
            setIsDragging(true)
        }
    }, [disabled])

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)

        if (disabled) return

        const files = e.dataTransfer.files
        if (files.length > 0) {
            const file = files[0]
            const error = validateFile(file)
            if (error) {
                setErrorMessage(error)
                setUploadStatus('error')
            } else {
                setSelectedFile(file)
                setErrorMessage(null)
                setUploadStatus('idle')
                autoDetectType(file)
            }
        }
    }, [disabled, validateFile])

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files
        if (files && files.length > 0) {
            const file = files[0]
            const error = validateFile(file)
            if (error) {
                setErrorMessage(error)
                setUploadStatus('error')
            } else {
                setSelectedFile(file)
                setErrorMessage(null)
                setUploadStatus('idle')
                autoDetectType(file)
            }
        }
    }, [validateFile])

    const autoDetectType = (file: File) => {
        const name = file.name.toLowerCase()
        if (name.includes('nomina') || name.includes('payslip') || name.includes('salario')) {
            setSelectedType('nomina')
        } else if (name.includes('factura') || name.includes('invoice')) {
            setSelectedType('factura')
        } else if (name.includes('modelo') || name.includes('declaracion') || name.includes('303') || name.includes('390')) {
            setSelectedType('declaracion')
        } else {
            setSelectedType('otro')
        }
    }

    const handleUpload = async () => {
        if (!selectedFile || isUploading) return

        setIsUploading(true)
        setErrorMessage(null)

        try {
            await onUpload(selectedFile, selectedType)
            setUploadStatus('success')
            setTimeout(() => {
                setSelectedFile(null)
                setUploadStatus('idle')
            }, 2000)
        } catch (err: any) {
            setErrorMessage(err.message || 'Error al subir el archivo')
            setUploadStatus('error')
        } finally {
            setIsUploading(false)
        }
    }

    const clearSelection = () => {
        setSelectedFile(null)
        setErrorMessage(null)
        setUploadStatus('idle')
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    return (
        <div className="file-uploader">
            {/* Drop Zone */}
            <div
                className={`drop-zone ${isDragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''} ${selectedFile ? 'has-file' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !disabled && !selectedFile && fileInputRef.current?.click()}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    accept={accept}
                    onChange={handleFileSelect}
                    disabled={disabled}
                    hidden
                />

                {!selectedFile ? (
                    <div className="drop-zone-content">
                        <div className="drop-zone-icon">
                            <Upload size={32} />
                        </div>
                        <p className="drop-zone-text">
                            Arrastra un archivo aqui o <span>haz clic para seleccionar</span>
                        </p>
                        <p className="drop-zone-hint">
                            PDF, Excel o CSV (max. {maxSizeMB}MB)
                        </p>
                    </div>
                ) : (
                    <div className="selected-file">
                        <div className="selected-file-info">
                            <File size={24} />
                            <div className="file-details">
                                <span className="file-name">{selectedFile.name}</span>
                                <span className="file-size">{formatFileSize(selectedFile.size)}</span>
                            </div>
                            <button
                                type="button"
                                className="clear-file-btn"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    clearSelection()
                                }}
                                disabled={isUploading}
                            >
                                <X size={18} />
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {/* File Type Selector */}
            {selectedFile && uploadStatus !== 'success' && (
                <div className="file-type-selector">
                    <label className="type-label">Tipo de documento:</label>
                    <div className="type-options">
                        {FILE_TYPES.map((type) => (
                            <button
                                key={type.value}
                                type="button"
                                className={`type-option ${selectedType === type.value ? 'selected' : ''}`}
                                onClick={() => setSelectedType(type.value)}
                                disabled={isUploading}
                            >
                                {type.icon}
                                <span>{type.label}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Error Message */}
            {errorMessage && (
                <div className="upload-error">
                    <AlertCircle size={16} />
                    <span>{errorMessage}</span>
                </div>
            )}

            {/* Success Message */}
            {uploadStatus === 'success' && (
                <div className="upload-success">
                    <CheckCircle size={16} />
                    <span>Archivo subido correctamente</span>
                </div>
            )}

            {/* Upload Button */}
            {selectedFile && uploadStatus !== 'success' && (
                <button
                    type="button"
                    className="btn btn-primary upload-btn"
                    onClick={handleUpload}
                    disabled={isUploading}
                >
                    {isUploading ? (
                        <>
                            <Loader2 size={18} className="animate-spin" />
                            <span>Subiendo...</span>
                        </>
                    ) : (
                        <>
                            <Upload size={18} />
                            <span>Subir archivo</span>
                        </>
                    )}
                </button>
            )}
        </div>
    )
}
