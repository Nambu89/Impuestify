"""
Workspace Service for TaxIA

Handles workspace management operations with Turso database.
"""
import uuid
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database.turso_client import get_db_client
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Workspace(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    icon: str = '📁'
    is_default: bool = False
    max_files: int = 50
    max_size_mb: int = 100
    created_at: datetime
    updated_at: datetime
    file_count: Optional[int] = 0

class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = '📁'

class WorkspaceService:
    """Service for workspace management operations."""
    
    async def create_workspace(self, user_id: str, workspace_data: WorkspaceCreate) -> Workspace:
        """
        Create a new workspace for a user.
        
        Args:
            user_id: ID of the user creating the workspace
            workspace_data: Workspace creation data
            
        Returns:
            Created Workspace object
        """
        db = await get_db_client()
        
        workspace_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Check if this is the first workspace for the user (to make it default)
        workspaces = await self.get_user_workspaces(user_id)
        is_default = len(workspaces) == 0
        
        await db.execute(
            """
            INSERT INTO workspaces (
                id, user_id, name, description, icon, is_default, 
                max_files, max_size_mb, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                workspace_id, 
                user_id, 
                workspace_data.name, 
                workspace_data.description, 
                workspace_data.icon or '📁',
                is_default,
                50,  # Default limits
                100, # Default limits
                now, 
                now
            ]
        )
        
        logger.info(f"Created workspace '{workspace_data.name}' for user {user_id}")
        
        return Workspace(
            id=workspace_id,
            user_id=user_id,
            name=workspace_data.name,
            description=workspace_data.description,
            icon=workspace_data.icon or '📁',
            is_default=is_default,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now)
        )
    
    async def get_user_workspaces(self, user_id: str) -> List[Workspace]:
        """
        Get all workspaces for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of Workspace objects
        """
        db = await get_db_client()
        
        # Query to get workspaces with file count
        query = """
            SELECT w.*, COUNT(wf.id) as file_count 
            FROM workspaces w
            LEFT JOIN workspace_files wf ON w.id = wf.workspace_id
            WHERE w.user_id = ?
            GROUP BY w.id
            ORDER BY w.is_default DESC, w.created_at DESC
        """
        
        result = await db.execute(query, [user_id])
        
        workspaces = []
        for row in result.rows:
            workspaces.append(Workspace(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row["description"],
                icon=row["icon"],
                is_default=bool(row["is_default"]),
                max_files=row["max_files"],
                max_size_mb=row["max_size_mb"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                file_count=row["file_count"]
            ))
            
        return workspaces
    
    async def get_workspace(self, workspace_id: str, user_id: str) -> Optional[Workspace]:
        """
        Get a specific workspace by ID, ensuring ownership.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID (for security verification)
            
        Returns:
            Workspace object if found and owned by user, None otherwise
        """
        db = await get_db_client()
        
        query = """
            SELECT w.*, COUNT(wf.id) as file_count 
            FROM workspaces w
            LEFT JOIN workspace_files wf ON w.id = wf.workspace_id
            WHERE w.id = ? AND w.user_id = ?
            GROUP BY w.id
        """
        
        result = await db.execute(query, [workspace_id, user_id])
        
        if result.rows:
            row = result.rows[0]
            return Workspace(
                id=row["id"],
                user_id=row["user_id"],
                name=row["name"],
                description=row["description"],
                icon=row["icon"],
                is_default=bool(row["is_default"]),
                max_files=row["max_files"],
                max_size_mb=row["max_size_mb"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                file_count=row["file_count"]
            )
            
        return None
    
    async def delete_workspace(self, workspace_id: str, user_id: str) -> bool:
        """
        Delete a workspace and all its files.
        
        Args:
            workspace_id: Workspace ID
            user_id: User ID (for security)
            
        Returns:
            True if deleted, False if not found or not owned by user
        """
        # First verify ownership
        workspace = await self.get_workspace(workspace_id, user_id)
        if not workspace:
            return False
            
        db = await get_db_client()
        
        # Foreign key CASCADE will handle deleting files
        await db.execute(
            "DELETE FROM workspaces WHERE id = ?",
            [workspace_id]
        )
        
        logger.info(f"Deleted workspace {workspace_id} for user {user_id}")
        return True

    async def get_fiscal_summary_from_workspace(self, user_id: str) -> Dict[str, Any]:
        """
        Extract fiscal totals from processed workspace files for this user.

        Reads extracted_data JSON from workspace_files (processing_status='completed')
        and aggregates: ingresos_actividad, gastos_actividad, iva_repercutido, iva_soportado.

        NOTE: This method does NOT overwrite the user's fiscal profile.
        It returns a dict with suggested values + metadata so the frontend
        can show a "use data from documents" prompt. The user decides.

        Returns:
            {
                "has_data": bool,
                "ingresos_actividad": float,
                "gastos_actividad": float,
                "iva_repercutido": float,
                "iva_soportado": float,
                "file_count": int,
                "files": [{"filename": str, "period": str, "tipo": str}]
            }
        """
        import json as _json

        db = await get_db_client()

        result = await db.execute(
            """
            SELECT wf.filename, wf.extracted_data, wf.file_type
            FROM workspace_files wf
            JOIN workspaces w ON wf.workspace_id = w.id
            WHERE w.user_id = ? AND wf.processing_status = 'completed'
              AND wf.extracted_data IS NOT NULL
            ORDER BY wf.created_at DESC
            """,
            [user_id],
        )

        summary = {
            "has_data": False,
            "ingresos_actividad": 0.0,
            "gastos_actividad": 0.0,
            "iva_repercutido": 0.0,
            "iva_soportado": 0.0,
            "file_count": 0,
            "files": [],
        }

        for row in result.rows:
            raw = row.get("extracted_data")
            if not raw:
                continue
            try:
                data = _json.loads(raw) if isinstance(raw, str) else raw
            except (TypeError, ValueError):
                continue

            if not isinstance(data, dict):
                continue

            # Aggregate numeric fields
            summary["ingresos_actividad"] += float(data.get("ingresos_actividad") or data.get("total_ingresos") or 0)
            summary["gastos_actividad"] += float(data.get("gastos_actividad") or data.get("total_gastos") or 0)
            summary["iva_repercutido"] += float(data.get("iva_repercutido") or data.get("iva_cobrado") or 0)
            summary["iva_soportado"] += float(data.get("iva_soportado") or data.get("iva_pagado") or 0)

            summary["files"].append({
                "filename": row.get("filename", ""),
                "tipo": row.get("file_type", ""),
                "period": data.get("periodo") or data.get("period") or "",
            })
            summary["file_count"] += 1

        if summary["file_count"] > 0:
            summary["has_data"] = True
            # Round to 2 decimals
            for k in ("ingresos_actividad", "gastos_actividad", "iva_repercutido", "iva_soportado"):
                summary[k] = round(summary[k], 2)

        return summary


# Global instance
workspace_service = WorkspaceService()
