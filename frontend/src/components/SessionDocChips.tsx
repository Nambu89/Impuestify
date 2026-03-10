/**
 * SessionDocChips — Shows uploaded session documents as removable chips
 * above the chat input, similar to Claude's document display.
 */
import { X, FileText, Receipt, FileWarning, File } from 'lucide-react'
import type { SessionDoc } from '../hooks/useSessionDocs'

interface Props {
    docs: SessionDoc[]
    onRemove: (docId: string) => void
}

const typeIcons: Record<string, typeof FileText> = {
    nomina: FileText,
    factura: Receipt,
    notificacion: FileWarning,
    declaracion: File,
    otro: File,
}

const typeColors: Record<string, string> = {
    nomina: '#3b82f6',
    factura: '#10b981',
    notificacion: '#f59e0b',
    declaracion: '#8b5cf6',
    otro: '#6b7280',
}

export function SessionDocChips({ docs, onRemove }: Props) {
    if (docs.length === 0) return null

    return (
        <div className="session-doc-chips">
            {docs.map(doc => {
                const Icon = typeIcons[doc.file_type] || File
                const color = typeColors[doc.file_type] || '#6b7280'

                return (
                    <div
                        key={doc.doc_id}
                        className="session-doc-chip"
                        title={doc.summary}
                    >
                        <Icon size={14} style={{ color, flexShrink: 0 }} />
                        <span className="session-doc-chip__name">
                            {doc.filename.length > 25
                                ? doc.filename.slice(0, 22) + '...'
                                : doc.filename}
                        </span>
                        <button
                            className="session-doc-chip__remove"
                            onClick={() => onRemove(doc.doc_id)}
                            title="Quitar documento"
                        >
                            <X size={12} />
                        </button>
                    </div>
                )
            })}
        </div>
    )
}
