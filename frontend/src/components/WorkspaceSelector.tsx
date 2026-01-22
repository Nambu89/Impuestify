import { useState, useEffect, useRef } from 'react'
import { ChevronDown, FolderOpen, Check, Plus } from 'lucide-react'
import { Workspace } from '../hooks/useWorkspaces'
import './WorkspaceSelector.css'

interface WorkspaceSelectorProps {
    workspaces: Workspace[]
    activeWorkspace: Workspace | null
    onWorkspaceChange?: (workspace: Workspace | null) => void
    onCreateNew?: () => void
}

export function WorkspaceSelector({
    workspaces,
    activeWorkspace,
    onWorkspaceChange,
    onCreateNew
}: WorkspaceSelectorProps) {
    const [isOpen, setIsOpen] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }

        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleSelect = (workspace: Workspace | null) => {
        onWorkspaceChange?.(workspace)
        setIsOpen(false)
    }

    return (
        <div className="workspace-selector" ref={dropdownRef}>
            <button
                type="button"
                className="workspace-selector-trigger"
                onClick={() => setIsOpen(!isOpen)}
                aria-expanded={isOpen}
                aria-haspopup="listbox"
            >
                {activeWorkspace ? (
                    <>
                        <span className="workspace-selector-icon">{activeWorkspace.icon}</span>
                        <span className="workspace-selector-name">{activeWorkspace.name}</span>
                    </>
                ) : (
                    <>
                        <FolderOpen size={16} />
                        <span className="workspace-selector-placeholder">Sin workspace</span>
                    </>
                )}
                <ChevronDown
                    size={16}
                    className={`workspace-selector-chevron ${isOpen ? 'open' : ''}`}
                />
            </button>

            {isOpen && (
                <div className="workspace-selector-dropdown" role="listbox">
                    {/* Option to clear workspace */}
                    <button
                        type="button"
                        className={`workspace-selector-option ${!activeWorkspace ? 'selected' : ''}`}
                        onClick={() => handleSelect(null)}
                        role="option"
                        aria-selected={!activeWorkspace}
                    >
                        <FolderOpen size={16} />
                        <span>Sin workspace</span>
                        {!activeWorkspace && <Check size={14} className="check-icon" />}
                    </button>

                    {workspaces.length > 0 && <div className="workspace-selector-divider" />}

                    {/* Workspace list */}
                    {workspaces.map((workspace) => (
                        <button
                            key={workspace.id}
                            type="button"
                            className={`workspace-selector-option ${activeWorkspace?.id === workspace.id ? 'selected' : ''}`}
                            onClick={() => handleSelect(workspace)}
                            role="option"
                            aria-selected={activeWorkspace?.id === workspace.id}
                        >
                            <span className="option-icon">{workspace.icon}</span>
                            <span className="option-name">{workspace.name}</span>
                            <span className="option-count">{workspace.file_count}</span>
                            {activeWorkspace?.id === workspace.id && (
                                <Check size={14} className="check-icon" />
                            )}
                        </button>
                    ))}

                    {/* Create new option */}
                    {onCreateNew && (
                        <>
                            <div className="workspace-selector-divider" />
                            <button
                                type="button"
                                className="workspace-selector-option create-new"
                                onClick={() => {
                                    setIsOpen(false)
                                    onCreateNew()
                                }}
                            >
                                <Plus size={16} />
                                <span>Crear workspace</span>
                            </button>
                        </>
                    )}
                </div>
            )}
        </div>
    )
}

