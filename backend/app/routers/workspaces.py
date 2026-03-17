"""
Workspaces Router for TaxIA

Provides REST API endpoints for managing user workspaces and file uploads.
Workspaces allow users to organize documents (payslips, invoices, tax declarations)
for analysis by the WorkspaceAgent.
"""
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.database.turso_client import TursoClient
from app.services.workspace_service import WorkspaceService, WorkspaceCreate
from app.services.file_processing_service import FileProcessingService
from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.services.subscription_service import SubscriptionAccess

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# === Models ===

class CreateWorkspaceRequest(BaseModel):
    """Request to create a new workspace"""
    name: str = Field(..., min_length=1, max_length=100, description="Workspace name")
    description: Optional[str] = Field(None, max_length=500, description="Workspace description")
    icon: Optional[str] = Field(default="📁", max_length=10, description="Workspace icon emoji")


class UpdateWorkspaceRequest(BaseModel):
    """Request to update a workspace"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=10)


class WorkspaceResponse(BaseModel):
    """Workspace metadata response"""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    icon: str
    is_default: bool
    max_files: int
    max_size_mb: int
    created_at: str
    updated_at: str
    file_count: int = 0


class WorkspaceFileResponse(BaseModel):
    """Workspace file metadata"""
    id: str
    workspace_id: str
    filename: str
    file_type: str
    mime_type: Optional[str]
    file_size: int
    processing_status: str
    created_at: str


class WorkspaceDetailResponse(BaseModel):
    """Workspace with all its files"""
    workspace: WorkspaceResponse
    files: List[WorkspaceFileResponse]


class FileUploadResponse(BaseModel):
    """Response after file upload"""
    id: str
    filename: str
    file_type: str
    status: str
    size: int
    integrity_score: Optional[float] = None
    integrity_findings: Optional[str] = None


# === Dependencies ===

async def get_db(request: Request) -> TursoClient:
    """Get database client from app state"""
    if hasattr(request.app.state, 'db_client') and request.app.state.db_client:
        return request.app.state.db_client
    raise HTTPException(status_code=503, detail="Database not connected")


async def get_workspace_service() -> WorkspaceService:
    """Get workspace service instance"""
    return WorkspaceService()


async def get_file_service() -> FileProcessingService:
    """Get file processing service instance"""
    return FileProcessingService()


# === Workspace CRUD Routes ===

@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    request: CreateWorkspaceRequest,
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Create a new workspace for the current user.

    - **name**: Workspace name (required)
    - **description**: Optional description
    - **icon**: Optional emoji icon (default: 📁)
    """
    try:
        workspace_data = WorkspaceCreate(
            name=request.name,
            description=request.description,
            icon=request.icon
        )

        workspace = await service.create_workspace(
            user_id=current_user.user_id,
            workspace_data=workspace_data
        )

        logger.info(f"Workspace created: {workspace.id} for user {current_user.user_id}")

        return WorkspaceResponse(
            id=workspace.id,
            user_id=workspace.user_id,
            name=workspace.name,
            description=workspace.description,
            icon=workspace.icon,
            is_default=workspace.is_default,
            max_files=workspace.max_files,
            max_size_mb=workspace.max_size_mb,
            created_at=(workspace.created_at or datetime.utcnow()).isoformat(),
            updated_at=(workspace.updated_at or datetime.utcnow()).isoformat(),
            file_count=workspace.file_count or 0
        )
    except Exception as e:
        logger.error(f"Error creating workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create workspace: {str(e)}")


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    current_user: TokenData = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Get all workspaces for the current user.

    Returns workspaces ordered by: default first, then by creation date.
    """
    try:
        workspaces = await service.get_user_workspaces(user_id=current_user.user_id)

        return [
            WorkspaceResponse(
                id=w.id,
                user_id=w.user_id,
                name=w.name,
                description=w.description,
                icon=w.icon,
                is_default=w.is_default,
                max_files=w.max_files,
                max_size_mb=w.max_size_mb,
                created_at=(w.created_at or datetime.utcnow()).isoformat(),
                updated_at=(w.updated_at or datetime.utcnow()).isoformat(),
                file_count=w.file_count or 0
            )
            for w in workspaces
        ]
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list workspaces: {str(e)}")


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
async def get_workspace(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
    db: TursoClient = Depends(get_db)
):
    """
    Get a specific workspace with all its files.

    - **workspace_id**: Workspace ID
    """
    try:
        workspace = await service.get_workspace(
            workspace_id=workspace_id,
            user_id=current_user.user_id
        )

        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Get files for this workspace
        result = await db.execute(
            """
            SELECT id, workspace_id, filename, file_type, mime_type,
                   file_size, processing_status, created_at
            FROM workspace_files
            WHERE workspace_id = ?
            ORDER BY created_at DESC
            """,
            [workspace_id]
        )

        files = [
            WorkspaceFileResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                filename=row["filename"],
                file_type=row["file_type"],
                mime_type=row["mime_type"],
                file_size=row["file_size"] or 0,
                processing_status=row["processing_status"],
                created_at=row["created_at"]
            )
            for row in result.rows
        ]

        return WorkspaceDetailResponse(
            workspace=WorkspaceResponse(
                id=workspace.id,
                user_id=workspace.user_id,
                name=workspace.name,
                description=workspace.description,
                icon=workspace.icon,
                is_default=workspace.is_default,
                max_files=workspace.max_files,
                max_size_mb=workspace.max_size_mb,
                created_at=(workspace.created_at or datetime.utcnow()).isoformat(),
                updated_at=(workspace.updated_at or datetime.utcnow()).isoformat(),
                file_count=workspace.file_count or 0
            ),
            files=files
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get workspace: {str(e)}")


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    request: UpdateWorkspaceRequest,
    current_user: TokenData = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service),
    db: TursoClient = Depends(get_db)
):
    """
    Update workspace metadata.

    - **workspace_id**: Workspace ID
    - **name**: New name (optional)
    - **description**: New description (optional)
    - **icon**: New icon (optional)
    """
    try:
        # Verify ownership
        workspace = await service.get_workspace(workspace_id, current_user.user_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Build update query dynamically
        updates = []
        params = []

        if request.name is not None:
            updates.append("name = ?")
            params.append(request.name)

        if request.description is not None:
            updates.append("description = ?")
            params.append(request.description)

        if request.icon is not None:
            updates.append("icon = ?")
            params.append(request.icon)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append("updated_at = datetime('now')")
        params.append(workspace_id)

        await db.execute(
            f"UPDATE workspaces SET {', '.join(updates)} WHERE id = ?",
            params
        )

        # Return updated workspace
        updated = await service.get_workspace(workspace_id, current_user.user_id)

        return WorkspaceResponse(
            id=updated.id,
            user_id=updated.user_id,
            name=updated.name,
            description=updated.description,
            icon=updated.icon,
            is_default=updated.is_default,
            max_files=updated.max_files,
            max_size_mb=updated.max_size_mb,
            created_at=(updated.created_at or datetime.utcnow()).isoformat(),
            updated_at=(updated.updated_at or datetime.utcnow()).isoformat(),
            file_count=updated.file_count or 0
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update workspace: {str(e)}")


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    service: WorkspaceService = Depends(get_workspace_service)
):
    """
    Delete a workspace and all its files.

    - **workspace_id**: Workspace ID
    """
    try:
        success = await service.delete_workspace(
            workspace_id=workspace_id,
            user_id=current_user.user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Workspace not found")

        logger.info(f"Workspace deleted: {workspace_id}")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workspace: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete workspace: {str(e)}")


# === File Management Routes ===

@router.post("/{workspace_id}/files", response_model=FileUploadResponse, status_code=201)
async def upload_file(
    workspace_id: str,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    file_service: FileProcessingService = Depends(get_file_service)
):
    """
    Upload a file to a workspace.

    Supported file types:
    - PDF documents (invoices, payslips, tax declarations)
    - Images (JPEG, PNG)
    - Excel files (XLSX, XLS)

    - **workspace_id**: Target workspace ID
    - **file**: File to upload
    """
    try:
        # Verify workspace ownership
        workspace = await workspace_service.get_workspace(workspace_id, current_user.user_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Check file limits
        if workspace.file_count >= workspace.max_files:
            raise HTTPException(
                status_code=400,
                detail=f"Workspace has reached maximum file limit ({workspace.max_files})"
            )

        # Process the file
        result = await file_service.process_file_upload(workspace_id, file)

        logger.info(f"File uploaded: {file.filename} to workspace {workspace_id}")

        return FileUploadResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.post("/{workspace_id}/files/batch", response_model=List[FileUploadResponse], status_code=201)
async def upload_files_batch(
    workspace_id: str,
    files: List[UploadFile] = File(...),
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription),
    service: WorkspaceService = Depends(get_workspace_service),
    file_service: FileProcessingService = Depends(get_file_service),
    db: TursoClient = Depends(get_db)
):
    """
    Upload up to 10 files at once to a workspace.

    Supported file types:
    - PDF documents (invoices, payslips, tax declarations)
    - Images (JPEG, PNG)
    - Excel files (XLSX, XLS)

    - **workspace_id**: Target workspace ID
    - **files**: List of files to upload (max 10)

    Each file is processed independently. If a file fails, processing continues
    for the remaining files. The response includes results (and errors) for every
    file in the batch.
    """
    MAX_BATCH_SIZE = 10

    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch upload limit is {MAX_BATCH_SIZE} files. Received {len(files)}."
        )

    # Verify workspace ownership once for the whole batch
    workspace = await service.get_workspace(workspace_id, current_user.user_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Snapshot current file count so we can enforce the per-workspace limit
    # across the entire batch without re-querying after every upload.
    current_count = workspace.file_count or 0
    available_slots = workspace.max_files - current_count

    if available_slots <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"Workspace has reached maximum file limit ({workspace.max_files})"
        )

    results: List[FileUploadResponse] = []

    for index, file in enumerate(files):
        # Stop early if the workspace is now full
        if index >= available_slots:
            logger.warning(
                f"Batch upload stopped at file {index + 1}: workspace {workspace_id} "
                f"has no more slots (max {workspace.max_files})"
            )
            # Append a synthetic error entry for each remaining file
            for remaining in files[index:]:
                results.append(
                    FileUploadResponse(
                        id="",
                        filename=remaining.filename or "unknown",
                        file_type="",
                        status="error: workspace file limit reached",
                        size=0,
                    )
                )
            break

        try:
            result = await file_service.process_file_upload(workspace_id, file)
            results.append(FileUploadResponse(**result))
            logger.info(f"Batch upload — file {file.filename} added to workspace {workspace_id}")
        except ValueError as exc:
            logger.warning(f"Batch upload — validation error for {file.filename}: {exc}")
            results.append(
                FileUploadResponse(
                    id="",
                    filename=file.filename or "unknown",
                    file_type="",
                    status=f"error: {exc}",
                    size=0,
                )
            )
        except Exception as exc:
            logger.error(
                f"Batch upload — unexpected error for {file.filename}: {exc}",
                exc_info=True,
            )
            results.append(
                FileUploadResponse(
                    id="",
                    filename=file.filename or "unknown",
                    file_type="",
                    status=f"error: {exc}",
                    size=0,
                )
            )

    return results


@router.get("/{workspace_id}/files", response_model=List[WorkspaceFileResponse])
async def list_files(
    workspace_id: str,
    current_user: TokenData = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    db: TursoClient = Depends(get_db)
):
    """
    List all files in a workspace.

    - **workspace_id**: Workspace ID
    """
    try:
        # Verify workspace ownership
        workspace = await workspace_service.get_workspace(workspace_id, current_user.user_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        result = await db.execute(
            """
            SELECT id, workspace_id, filename, file_type, mime_type,
                   file_size, processing_status, created_at
            FROM workspace_files
            WHERE workspace_id = ?
            ORDER BY created_at DESC
            """,
            [workspace_id]
        )

        return [
            WorkspaceFileResponse(
                id=row["id"],
                workspace_id=row["workspace_id"],
                filename=row["filename"],
                file_type=row["file_type"],
                mime_type=row["mime_type"],
                file_size=row["file_size"] or 0,
                processing_status=row["processing_status"],
                created_at=row["created_at"]
            )
            for row in result.rows
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.delete("/{workspace_id}/files/{file_id}", status_code=204)
async def delete_file(
    workspace_id: str,
    file_id: str,
    current_user: TokenData = Depends(get_current_user),
    workspace_service: WorkspaceService = Depends(get_workspace_service),
    db: TursoClient = Depends(get_db)
):
    """
    Delete a file from a workspace.

    - **workspace_id**: Workspace ID
    - **file_id**: File ID
    """
    try:
        # Verify workspace ownership
        workspace = await workspace_service.get_workspace(workspace_id, current_user.user_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        # Delete file (verify it belongs to this workspace)
        result = await db.execute(
            "DELETE FROM workspace_files WHERE id = ? AND workspace_id = ?",
            [file_id, workspace_id]
        )

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="File not found")

        logger.info(f"File deleted: {file_id} from workspace {workspace_id}")
        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
