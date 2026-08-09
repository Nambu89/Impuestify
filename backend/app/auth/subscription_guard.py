"""
Subscription Guard for TaxIA/Impuestify

FastAPI dependencies for subscription-based access control.
"""

import logging

from fastapi import Depends, HTTPException, status

from app.auth.jwt_handler import TokenData, get_current_user
from app.config import settings
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

    Bypass: when SUBSCRIPTIONS_ENABLED=False (demo deploys), this guard
    grants access unconditionally — the entire subscription system is
    off, so blocking on it would brick every protected endpoint.
    """
    if not settings.SUBSCRIPTIONS_ENABLED:
        # plan_type="autonomo" para que el content_restriction guard
        # de chat_stream NO bloquee preguntas de autónomos (que es lo
        # que queremos demostrar en una demo white-label completa).
        # Sin esto, plan_type=None y `None not in ("autonomo","creator")`
        # bloquea cualquier consulta sobre autónomos / modelos AEAT.
        return SubscriptionAccess(
            has_access=True,
            is_owner=False,
            plan_type="autonomo",
            status="demo",
            reason="subscriptions_disabled",
        )

    service = await get_subscription_service()
    access = await service.check_access(user_id=current_user.user_id, email=current_user.email)

    if not access.has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "subscription_required",
                "message": f"Se requiere una suscripcion activa para usar {settings.BRAND_NAME}.",
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

    Bypass: when SUBSCRIPTIONS_ENABLED=False, returns "demo" access.
    """
    if not settings.SUBSCRIPTIONS_ENABLED:
        # plan_type="autonomo" para que el content_restriction guard
        # de chat_stream NO bloquee preguntas de autónomos (que es lo
        # que queremos demostrar en una demo white-label completa).
        # Sin esto, plan_type=None y `None not in ("autonomo","creator")`
        # bloquea cualquier consulta sobre autónomos / modelos AEAT.
        return SubscriptionAccess(
            has_access=True,
            is_owner=False,
            plan_type="autonomo",
            status="demo",
            reason="subscriptions_disabled",
        )

    service = await get_subscription_service()
    return await service.check_access(user_id=current_user.user_id, email=current_user.email)
