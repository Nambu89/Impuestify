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
    Create a Stripe Checkout Session for the Particular plan (15 EUR/month).

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
    access = await service.check_access(
        user_id=current_user.user_id, email=current_user.email
    )

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

    This endpoint is called by Stripe and verifies the event signature.
    No JWT auth required — signature verification is the auth mechanism.
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
        result = await service.handle_webhook_event(payload, sig_header)
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Firma de webhook invalida.")
    except Exception as e:
        logger.error("Webhook processing error", exc_info=True)
        raise HTTPException(status_code=500, detail="Error procesando webhook.")
