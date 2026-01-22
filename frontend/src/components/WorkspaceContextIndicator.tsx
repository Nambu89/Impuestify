import { FileText, X } from 'lucide-react'
import { Workspace } from '../hooks/useWorkspaces'
import './WorkspaceContextIndicator.css'

interface WorkspaceContextIndicatorProps {
    workspace: Workspace
    onClear?: () => void
}

export function WorkspaceContextIndicator({ workspace, onClear }: WorkspaceContextIndicatorProps) {
    if (!workspace) return null

    return (
        <div className="workspace-context-indicator">
            <div className="context-icon">{workspace.icon}</div>
            <div className="context-info">
                <span className="context-label">Contexto activo:</span>
                <span className="context-name">{workspace.name}</span>
                <span className="context-files">
                    <FileText size={12} />
                    {workspace.file_count} archivos
                </span>
            </div>
            {onClear && (
                <button
                    type="button"
                    className="context-clear"
                    onClick={onClear}
                    title="Quitar contexto"
                >
                    <X size={14} />
                </button>
            )}
        </div>
    )
}
