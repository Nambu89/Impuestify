"""DefensIA router — stub con health check.

Los endpoints REST completos se implementan en Parte 2 del plan.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/defensia", tags=["defensia"])


@router.get("/_health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "defensia"}
