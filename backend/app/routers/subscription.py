"""
Subscription Router for TaxIA/Impuestify

Handles Stripe Checkout, Customer Portal, subscription status, and webhooks.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import Optional

from app.auth.jwt_handler import get_current_user, TokenData
from app.services.subscription_service import get_subscription_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription", tags=["subscription"])


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------


class CheckoutRequest(BaseModel):
    success_url: str
    cancel_url: str
    plan_type: str = "particular"  # "particular" | "autonomo" | "creator"


class CheckoutResponse(BaseModel):
    checkout_url: Optional[str] = None


class PortalRequest(BaseModel):
    return_url: str


class PortalResponse(BaseModel):
    portal_url: Optional[str] = None


class SubscriptionStatusResponse(BaseModel):
    has_access: bool
    is_owner: bool = False
    plan_type: Optional[str] = None
    status: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Create a Stripe Checkout Session for the Particular plan (5 EUR/month).

    Returns the checkout URL to redirect the user to Stripe's hosted payment page.
    """
    if not settings.is_stripe_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe no esta configurado.",
        )

    service = await get_subscription_service()

    try:
        url = await service.create_checkout_session(
            user_id=current_user.user_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            plan_type=request.plan_type,
        )
        return CheckoutResponse(checkout_url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error creating checkout session", exc_info=True)
        raise HTTPException(status_code=500, detail="Error al crear la sesion de pago.")


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_status(
    current_user: TokenData = Depends(get_current_user),
):
    """
    Get the current subscription status for the authenticated user.
    """
    service = await get_subscription_service()
    access = await service.check_access(user_id=current_user.user_id, email=current_user.email)

    sub = await service.get_subscription(current_user.user_id)

    return SubscriptionStatusResponse(
        has_access=access.has_access,
        is_owner=access.is_owner,
        plan_type=access.plan_type,
        status=access.status,
        current_period_end=sub.get("current_period_end") if sub else None,
        cancel_at_period_end=bool(sub.get("cancel_at_period_end")) if sub else False,
    )


@router.post("/create-portal", response_model=PortalResponse)
async def create_portal(
    request: PortalRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Create a Stripe Customer Portal session for subscription management.

    Returns the portal URL to redirect the user.
    """
    if not settings.is_stripe_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe no esta configurado.",
        )

    service = await get_subscription_service()
    url = await service.create_portal_session(
        user_id=current_user.user_id,
        return_url=request.return_url,
    )

    if not url:
        raise HTTPException(status_code=404, detail="No se encontro la suscripcion.")

    return PortalResponse(portal_url=url)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.

    Signature verification IS the auth mechanism (no JWT). Returns:
      - 200: event accepted (success or swallowed permanent error)
      - 400: invalid signature (Stripe should not retry)
      - 503: webhook not configured (missing secret)

    Never returns 500: handler-level exceptions are caught and logged inside
    handle_webhook_event so Stripe stops the retry storm.
    """
    if not settings.is_stripe_configured or not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhooks no configurados.",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    service = await get_subscription_service()

    try:
        return await service.handle_webhook_event(payload, sig_header)
    except ValueError as e:
        logger.warning(f"Webhook signature/payload rejected: {e}")
        raise HTTPException(status_code=400, detail="Firma de webhook invalida.")
    except Exception as e:
        # Last-resort guard. Should not normally trigger because
        # handle_webhook_event swallows handler-level errors. If we end up
        # here, it's something around the dispatcher itself (db pool exhausted,
        # etc.) — return 200 anyway to avoid Stripe deactivating our endpoint.
        logger.error(
            "Unexpected error in webhook dispatcher — acknowledging anyway "
            "to keep Stripe endpoint healthy. Error: %s",
            e,
            exc_info=True,
        )
        return {"status": "error_acknowledged", "error": str(e)[:200]}


@router.get("/webhook/health")
async def webhook_health():
    """Lightweight readiness check for the Stripe webhook endpoint."""
    return {
        "configured": bool(getattr(settings, "STRIPE_WEBHOOK_SECRET", "")),
        "stripe_ready": bool(settings.is_stripe_configured),
    }
