import './WorkspaceCards.css'

interface WorkspaceCardsProps {
  workspaces: Array<{ id: string; name: string; icon: string; file_count: number; description?: string }>
  onSelectWorkspace: (workspace: { id: string; name: string; icon: string; file_count: number; description?: string }) => void
}

export function WorkspaceCards({ workspaces, onSelectWorkspace }: WorkspaceCardsProps) {
  if (!workspaces || workspaces.length === 0) return null

  return (
    <div className="workspace-cards-strip">
      <div className="workspace-cards-header">
        <span className="workspace-cards-title">Tus escritorios</span>
      </div>
      <div className="workspace-cards-scroll">
        {workspaces.map(ws => (
          <button
            key={ws.id}
            className="workspace-card-mini"
            onClick={() => onSelectWorkspace(ws)}
          >
            <span className="workspace-card-icon">{ws.icon}</span>
            <span className="workspace-card-name">{ws.name}</span>
            <span className="workspace-card-count">{ws.file_count} {ws.file_count === 1 ? 'archivo' : 'archivos'}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
