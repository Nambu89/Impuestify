"""
Owner Guard — Shared dependency that ensures the caller is the platform owner.

Used by admin.py, rag_quality.py, and any future owner-only routers.
"""
from fastapi import Depends, HTTPException, status

from app.auth.jwt_handler import get_current_user, TokenData
from app.services.subscription_service import get_subscription_service


async def require_owner(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """Dependency that ensures the caller is the platform owner."""
    sub_service = await get_subscription_service()
    access = await sub_service.check_access(
        user_id=current_user.user_id,
        email=current_user.email,
    )
    if not access.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario puede acceder a esta función.",
        )
    return current_user
