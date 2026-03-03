"""
Subscription Guard for TaxIA/Impuestify

FastAPI dependencies for subscription-based access control.
"""
import logging

from fastapi import Depends, HTTPException, status
from app.auth.jwt_handler import get_current_user, TokenData
from app.services.subscription_service import (
    SubscriptionAccess,
    get_subscription_service,
)

logger = logging.getLogger(__name__)


async def require_active_subscription(
    current_user: TokenData = Depends(get_current_user),
) -> SubscriptionAccess:
    """
    FastAPI dependency that requires an active subscription.

    Raises HTTP 403 if the user has no active subscription.
    Returns SubscriptionAccess with access details.
    """
    service = await get_subscription_service()
    access = await service.check_access(
        user_id=current_user.user_id, email=current_user.email
    )

    if not access.has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "subscription_required",
                "message": "Se requiere una suscripcion activa para usar Impuestify.",
                "status": access.status,
                "reason": access.reason,
            },
        )

    return access


async def get_subscription_access(
    current_user: TokenData = Depends(get_current_user),
) -> SubscriptionAccess:
    """
    FastAPI dependency that returns subscription status WITHOUT blocking.

    Use this for endpoints that need to check subscription status
    but handle the response themselves (e.g., chat endpoints that
    return a specific message instead of a 403).
    """
    service = await get_subscription_service()
    return await service.check_access(
        user_id=current_user.user_id, email=current_user.email
    )
