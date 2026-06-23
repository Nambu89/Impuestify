"""Router Modo Gestoría — cartera de clientes (cada cliente = workspace con perfil fiscal)."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth.gestoria_guard import require_gestoria
from app.auth.jwt_handler import TokenData
from app.services.gestoria_service import (
    ClientLimitError,
    GestoriaClient,
    GestoriaClientCreate,
    GestoriaClientService,
    GestoriaClientUpdate,
)

router = APIRouter(prefix="/api/gestoria", tags=["gestoria"])


def get_service() -> GestoriaClientService:
    return GestoriaClientService()


@router.get("/clients", response_model=list[GestoriaClient])
async def list_clients(current_user: TokenData = Depends(require_gestoria)):
    return await get_service().list_clients(current_user.user_id)


@router.post("/clients", response_model=GestoriaClient)
async def create_client(
    body: GestoriaClientCreate,
    current_user: TokenData = Depends(require_gestoria),
):
    # Cheap, gestoria-gated, capped at 3 clients → no per-route rate limit needed
    # (global SlowAPI middleware still applies to /api/*).
    try:
        return await get_service().create_client(current_user.user_id, body)
    except ClientLimitError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/clients/{workspace_id}", response_model=GestoriaClient)
async def get_client(workspace_id: str, current_user: TokenData = Depends(require_gestoria)):
    client = await get_service().get_client(current_user.user_id, workspace_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.put("/clients/{workspace_id}", response_model=GestoriaClient)
async def update_client(
    workspace_id: str,
    body: GestoriaClientUpdate,
    current_user: TokenData = Depends(require_gestoria),
):
    client = await get_service().update_client(current_user.user_id, workspace_id, body)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.delete("/clients/{workspace_id}", response_model=dict[str, bool], status_code=200)
async def delete_client(workspace_id: str, current_user: TokenData = Depends(require_gestoria)):
    deleted = await get_service().delete_client(current_user.user_id, workspace_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return {"deleted": True}
