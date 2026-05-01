"""
Subscription Service for TaxIA/Impuestify

Handles Stripe integration, subscription lifecycle, and access control.
"""
import uuid
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Lazy Stripe import (only when configured)
stripe = None


def _get_stripe():
    """Lazy-load and configure Stripe SDK."""
    global stripe
    if stripe is None:
        import stripe as _stripe
        _stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe = _stripe
    return stripe


@dataclass
class SubscriptionAccess:
    """Result of a subscription access check."""
    has_access: bool
    is_owner: bool
    plan_type: Optional[str] = None
    status: Optional[str] = None
    reason: str = "no_subscription"
    # For frontend: where to redirect if no access
    checkout_url: Optional[str] = None


class SubscriptionService:
    """Manages Stripe subscriptions and access control."""

    def __init__(self, db=None):
        self.db = db

    async def _get_db(self):
        if self.db:
            return self.db
        from app.database.turso_client import get_db_client
        return await get_db_client()

    # ------------------------------------------------------------------
    # Stripe Customer Management
    # ------------------------------------------------------------------

    async def create_stripe_customer(
        self, user_id: str, email: str, name: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a Stripe customer and insert a subscription record (inactive).

        Returns the stripe_customer_id or None if Stripe is not configured.
        """
        if not settings.is_stripe_configured:
            logger.warning("Stripe not configured, skipping customer creation")
            return None

        s = _get_stripe()
        db = await self._get_db()

        # Check if subscription record already exists with a valid customer ID
        existing = await db.execute(
            "SELECT id, stripe_customer_id FROM subscriptions WHERE user_id = ?",
            [user_id],
        )
        if existing.rows and existing.rows[0]["stripe_customer_id"]:
            return existing.rows[0]["stripe_customer_id"]

        # Create Stripe customer
        customer = s.Customer.create(
            email=email,
            name=name,
            metadata={"user_id": user_id},
        )
        logger.info("Stripe customer created", extra={"user_id": user_id, "customer_id": customer.id})

        if existing.rows:
            # Row exists but stripe_customer_id was NULL (grace_period/beta users)
            await db.execute(
                """
                UPDATE subscriptions
                SET stripe_customer_id = ?, updated_at = datetime('now')
                WHERE user_id = ?
                """,
                [customer.id, user_id],
            )
        else:
            # No subscription record yet — create one
            sub_id = str(uuid.uuid4())
            await db.execute(
                """
                INSERT INTO subscriptions (id, user_id, stripe_customer_id, plan_type, status)
                VALUES (?, ?, ?, 'particular', 'inactive')
                """,
                [sub_id, user_id, customer.id],
            )

        return customer.id

    # ------------------------------------------------------------------
    # Stripe Checkout & Portal
    # ------------------------------------------------------------------

    async def create_checkout_session(
        self, user_id: str, success_url: str, cancel_url: str,
        plan_type: str = "particular"
    ) -> Optional[str]:
        """
        Create a Stripe Checkout Session.

        Returns the checkout session URL.
        plan_type is stored as metadata so the webhook can update it in Turso.
        """
        if not settings.is_stripe_configured or not settings.STRIPE_PRICE_ID:
            raise ValueError("Stripe no está configurado. Contacta con soporte.")

        s = _get_stripe()
        db = await self._get_db()

        # Get or create Stripe customer ID
        result = await db.execute(
            "SELECT stripe_customer_id FROM subscriptions WHERE user_id = ?",
            [user_id],
        )

        customer_id = result.rows[0]["stripe_customer_id"] if result.rows else None

        # If no customer ID yet (grace_period/beta users), create one now
        if not customer_id:
            user_result = await db.execute(
                "SELECT email, name FROM users WHERE id = ?", [user_id]
            )
            if not user_result.rows:
                raise ValueError("Usuario no encontrado.")

            email = user_result.rows[0]["email"]
            name = user_result.rows[0].get("name")
            customer_id = await self.create_stripe_customer(user_id, email, name)

            if not customer_id:
                raise ValueError("No se pudo crear el cliente en Stripe.")

        # Select the correct Stripe price based on plan_type
        if plan_type == "autonomo":
            if not settings.STRIPE_PRICE_ID_AUTONOMO:
                raise ValueError("El plan Autónomo no está configurado. Contacta con soporte.")
            price_id = settings.STRIPE_PRICE_ID_AUTONOMO
        elif plan_type == "creator":
            if not settings.STRIPE_PRICE_ID_CREATOR:
                raise ValueError("El plan Creator no está configurado. Contacta con soporte.")
            price_id = settings.STRIPE_PRICE_ID_CREATOR
        else:
            price_id = settings.STRIPE_PRICE_ID

        session = s.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user_id, "plan_type": plan_type},
        )

        logger.info("Checkout session created", extra={"user_id": user_id})
        return session.url

    async def create_portal_session(self, user_id: str, return_url: str) -> Optional[str]:
        """
        Create a Stripe Customer Portal session for subscription management.

        Returns the portal session URL.
        """
        if not settings.is_stripe_configured:
            return None

        s = _get_stripe()
        db = await self._get_db()

        result = await db.execute(
            "SELECT stripe_customer_id FROM subscriptions WHERE user_id = ?",
            [user_id],
        )
        if not result.rows:
            return None

        customer_id = result.rows[0]["stripe_customer_id"]

        session = s.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        return session.url

    # ------------------------------------------------------------------
    # Stripe Webhook Handling
    # ------------------------------------------------------------------

    async def handle_webhook_event(self, payload: bytes, sig_header: str) -> dict:
        """
        Process a Stripe webhook event.

        Returns a dict with the processing result.
        """
        s = _get_stripe()

        # Verify webhook signature
        try:
            event = s.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except s.error.SignatureVerificationError:
            logger.warning("Webhook signature verification failed")
            raise ValueError("Invalid signature")

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"Webhook received: {event_type}")

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data)
        elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
            await self._handle_subscription_upserted(data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(data)
        elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
            await self._handle_invoice_paid(data)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(data)
        else:
            logger.info(f"Unhandled webhook event: {event_type}")

        return {"status": "ok", "event_type": event_type}

    async def _handle_checkout_completed(self, session: dict):
        """Handle successful checkout: activate subscription and update plan_type."""
        db = await self._get_db()
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        metadata = session.get("metadata", {})
        plan_type = metadata.get("plan_type", "particular")

        if not customer_id:
            return

        await db.execute(
            """
            UPDATE subscriptions
            SET stripe_subscription_id = ?,
                plan_type = ?,
                status = 'active',
                current_period_start = datetime('now'),
                updated_at = datetime('now')
            WHERE stripe_customer_id = ?
            """,
            [subscription_id, plan_type, customer_id],
        )
        logger.info(
            f"Subscription activated (plan={plan_type})",
            extra={"customer_id": customer_id, "plan_type": plan_type},
        )

    def _plan_type_from_price_id(self, price_id: Optional[str]) -> Optional[str]:
        """Map a Stripe price id to our plan_type. Returns None if unknown."""
        if not price_id:
            return None
        if price_id == settings.STRIPE_PRICE_ID_AUTONOMO:
            return "autonomo"
        if price_id == settings.STRIPE_PRICE_ID_CREATOR:
            return "creator"
        if price_id == settings.STRIPE_PRICE_ID:
            return "particular"
        return None

    @staticmethod
    def _ts_to_iso(ts: Optional[int]) -> Optional[str]:
        if not ts:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

    async def _handle_subscription_upserted(self, subscription: dict):
        """Handle customer.subscription.created or .updated.

        Persist the latest Stripe state: status, plan_type (derived from price id),
        period start/end, cancellation flag, and the stripe_subscription_id itself.
        """
        db = await self._get_db()
        customer_id = subscription.get("customer")
        sub_id = subscription.get("id")
        status = subscription.get("status")
        cancel_at_period_end = subscription.get("cancel_at_period_end", False)

        status_map = {
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "incomplete": "inactive",
            "incomplete_expired": "inactive",
            "trialing": "active",
            "unpaid": "past_due",
        }
        our_status = status_map.get(status, status)

        # In recent Stripe API versions, current_period_start/end live on items[0],
        # not on the root subscription object. Fall back to root for older payloads.
        items = (subscription.get("items") or {}).get("data") or []
        first_item = items[0] if items else {}
        period_start_ts = (
            first_item.get("current_period_start")
            or subscription.get("current_period_start")
        )
        period_end_ts = (
            first_item.get("current_period_end")
            or subscription.get("current_period_end")
        )
        period_start_str = self._ts_to_iso(period_start_ts)
        period_end_str = self._ts_to_iso(period_end_ts)

        price_id = first_item.get("price", {}).get("id") if first_item else None
        plan_type = self._plan_type_from_price_id(price_id)

        # Build dynamic update so we never overwrite plan_type with NULL when the price
        # is unknown (defensive: avoids losing data on an unrecognized price).
        sets = [
            "stripe_subscription_id = ?",
            "status = ?",
            "cancel_at_period_end = ?",
            "current_period_start = COALESCE(?, current_period_start)",
            "current_period_end = ?",
            "updated_at = datetime('now')",
        ]
        params = [
            sub_id,
            our_status,
            int(cancel_at_period_end),
            period_start_str,
            period_end_str,
        ]
        if plan_type:
            sets.append("plan_type = ?")
            params.append(plan_type)
        params.append(customer_id)

        await db.execute(
            f"UPDATE subscriptions SET {', '.join(sets)} WHERE stripe_customer_id = ?",
            params,
        )
        logger.info(
            f"Subscription upserted to {our_status} (plan={plan_type})",
            extra={"customer_id": customer_id, "subscription_id": sub_id},
        )

    # Backwards-compat alias (older code/tests may reference this name).
    async def _handle_subscription_updated(self, subscription: dict):
        await self._handle_subscription_upserted(subscription)

    async def _handle_invoice_paid(self, invoice: dict):
        """Handle invoice.paid / invoice.payment_succeeded.

        Acts as a safety net: if checkout.session.completed or
        customer.subscription.created were missed, this still activates the
        subscription on first successful payment and extends the period on renewals.
        """
        db = await self._get_db()
        customer_id = invoice.get("customer")
        subscription_id = invoice.get("subscription")
        period_end = invoice.get("period_end") or invoice.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
        period_end_str = self._ts_to_iso(period_end)

        if not customer_id:
            return

        sets = ["status = 'active'", "updated_at = datetime('now')"]
        params: list = []
        if subscription_id:
            sets.append("stripe_subscription_id = COALESCE(stripe_subscription_id, ?)")
            params.append(subscription_id)
        if period_end_str:
            sets.append("current_period_end = ?")
            params.append(period_end_str)
        params.append(customer_id)

        await db.execute(
            f"UPDATE subscriptions SET {', '.join(sets)} WHERE stripe_customer_id = ?",
            params,
        )
        logger.info(
            "Invoice paid → subscription activated",
            extra={"customer_id": customer_id, "subscription_id": subscription_id},
        )

    async def _handle_subscription_deleted(self, subscription: dict):
        """Handle subscription cancellation.

        If the customer still has another active subscription in Stripe (e.g. they
        had two subscriptions and only one was canceled), re-sync so the DB reflects
        the surviving one instead of forcing 'canceled'.
        """
        db = await self._get_db()
        customer_id = subscription.get("customer")
        deleted_sub_id = subscription.get("id")

        # Only act if this customer's row references the canceled subscription
        # (or has no subscription_id at all, which is the legacy case).
        await db.execute(
            """
            UPDATE subscriptions
            SET status = 'canceled',
                updated_at = datetime('now')
            WHERE stripe_customer_id = ?
              AND (stripe_subscription_id = ? OR stripe_subscription_id IS NULL)
            """,
            [customer_id, deleted_sub_id],
        )
        logger.info(
            "Subscription canceled",
            extra={"customer_id": customer_id, "subscription_id": deleted_sub_id},
        )

        # Look up the user_id for this customer and try to recover from any other
        # active subscription they may still have.
        user_row = await db.execute(
            "SELECT user_id FROM subscriptions WHERE stripe_customer_id = ? LIMIT 1",
            [customer_id],
        )
        if user_row.rows:
            try:
                await self.sync_from_stripe(user_row.rows[0]["user_id"])
            except Exception as e:
                logger.warning(
                    "Re-sync after subscription delete failed",
                    extra={"customer_id": customer_id, "error": str(e)},
                )

    async def _handle_payment_failed(self, invoice: dict):
        """Handle failed payment."""
        db = await self._get_db()
        customer_id = invoice.get("customer")

        await db.execute(
            """
            UPDATE subscriptions
            SET status = 'past_due',
                updated_at = datetime('now')
            WHERE stripe_customer_id = ?
            """,
            [customer_id],
        )
        logger.warning("Payment failed", extra={"customer_id": customer_id})

    # ------------------------------------------------------------------
    # Access Control
    # ------------------------------------------------------------------

    async def check_access(self, user_id: str, email: Optional[str] = None) -> SubscriptionAccess:
        """
        Check if a user has access to the application.

        Priority:
        1. Owner email → full access
        2. is_owner flag in DB → full access
        3. Active subscription → access
        4. Grace period (not expired) → access
        5. Otherwise → no access
        """
        db = await self._get_db()

        # 1. Check owner by email
        if email and email.lower() == settings.OWNER_EMAIL.lower():
            return SubscriptionAccess(
                has_access=True,
                is_owner=True,
                plan_type="owner",
                status="active",
                reason="owner",
            )

        # 2. Check is_owner flag and subscription status
        result = await db.execute(
            """
            SELECT u.is_owner, s.plan_type, s.status, s.current_period_end
            FROM users u
            LEFT JOIN subscriptions s ON s.user_id = u.id
            WHERE u.id = ?
            """,
            [user_id],
        )

        if not result.rows:
            return SubscriptionAccess(
                has_access=False, is_owner=False, reason="user_not_found"
            )

        row = result.rows[0]

        # Owner flag in DB
        if row.get("is_owner"):
            return SubscriptionAccess(
                has_access=True,
                is_owner=True,
                plan_type="owner",
                status="active",
                reason="owner",
            )

        sub_status = row.get("status")
        plan_type = row.get("plan_type")
        period_end = row.get("current_period_end")

        # 3. Active subscription
        if sub_status == "active":
            return SubscriptionAccess(
                has_access=True,
                is_owner=False,
                plan_type=plan_type,
                status="active",
                reason="active_subscription",
            )

        # 4. Grace period
        if sub_status == "grace_period" and period_end:
            try:
                end_date = datetime.fromisoformat(period_end)
                if end_date >= datetime.now(timezone.utc):
                    return SubscriptionAccess(
                        has_access=True,
                        is_owner=False,
                        plan_type=plan_type,
                        status="grace_period",
                        reason="grace_period",
                    )
            except (ValueError, TypeError):
                pass

        # 5. No access
        return SubscriptionAccess(
            has_access=False,
            is_owner=False,
            plan_type=plan_type,
            status=sub_status or "inactive",
            reason="no_active_subscription",
        )

    async def get_subscription(self, user_id: str) -> Optional[dict]:
        """Get subscription record for a user."""
        db = await self._get_db()
        result = await db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", [user_id]
        )
        return result.rows[0] if result.rows else None

    async def sync_from_stripe(self, user_id: str) -> dict:
        """Reconcile our DB state for `user_id` with Stripe (recover from missed webhooks).

        Steps:
        1. Look up the user's Stripe customer id.
        2. List subscriptions for that customer.
        3. Pick the most relevant one (active/trialing > past_due > canceled).
        4. Persist its current state via `_handle_subscription_upserted`.

        Returns a summary dict for the caller to log/show.
        """
        if not settings.is_stripe_configured:
            return {"synced": False, "reason": "stripe_not_configured"}

        db = await self._get_db()
        result = await db.execute(
            "SELECT stripe_customer_id FROM subscriptions WHERE user_id = ?",
            [user_id],
        )
        if not result.rows or not result.rows[0]["stripe_customer_id"]:
            return {"synced": False, "reason": "no_stripe_customer"}

        customer_id = result.rows[0]["stripe_customer_id"]
        s = _get_stripe()

        subs = s.Subscription.list(customer=customer_id, status="all", limit=10)
        items = list(subs.auto_paging_iter()) if hasattr(subs, "auto_paging_iter") else (subs.data or [])

        if not items:
            return {
                "synced": False,
                "reason": "no_subscriptions_in_stripe",
                "customer_id": customer_id,
            }

        priority = {"active": 0, "trialing": 1, "past_due": 2, "unpaid": 3,
                    "incomplete": 4, "canceled": 5, "incomplete_expired": 6}
        items.sort(key=lambda sub: priority.get(getattr(sub, "status", "incomplete"), 99))
        chosen = items[0]
        chosen_dict = chosen.to_dict() if hasattr(chosen, "to_dict") else dict(chosen)

        # Stripe SDK objects can also expose .id / .customer at top level — ensure shape.
        chosen_dict.setdefault("customer", customer_id)
        chosen_dict.setdefault("id", getattr(chosen, "id", None))

        await self._handle_subscription_upserted(chosen_dict)

        return {
            "synced": True,
            "customer_id": customer_id,
            "subscription_id": chosen_dict.get("id"),
            "stripe_status": chosen_dict.get("status"),
            "subscriptions_total": len(items),
        }

    async def grant_grace_period(self, user_id: str, end_date: str = "2026-12-31T23:59:59"):
        """Grant grace period to an existing user."""
        db = await self._get_db()
        await db.execute(
            """
            UPDATE subscriptions
            SET status = 'grace_period',
                current_period_end = ?,
                updated_at = datetime('now')
            WHERE user_id = ?
            """,
            [end_date, user_id],
        )
        logger.info(f"Grace period granted until {end_date}", extra={"user_id": user_id})


def validate_plan_role_compatibility(
    plan_type: Optional[str],
    situacion_laboral: str,
    is_owner: bool = False,
) -> Optional[dict]:
    """
    Validate if a subscription plan allows a given fiscal role.

    Returns None if compatible, or a dict with upgrade info if incompatible.
    Plans hierarchy: autonomo > creator > particular.
    """
    if is_owner:
        return None

    effective_plan = plan_type or "particular"
    situacion_lower = (situacion_laboral or "").lower().strip()

    # Roles allowed per plan (cumulative)
    PARTICULAR_ROLES: set = {"asalariado", "pensionista", "desempleado", ""}
    CREATOR_ROLES: set = PARTICULAR_ROLES | {"creador", "influencer", "youtuber", "streamer"}
    # autonomo allows everything (None = unrestricted, includes 'farmaceutico')

    PLAN_ALLOWED: dict = {
        "particular": PARTICULAR_ROLES,
        "creator": CREATOR_ROLES,
        "autonomo": None,  # None = all allowed
    }

    allowed = PLAN_ALLOWED.get(effective_plan, PARTICULAR_ROLES)
    if allowed is None:  # autonomo plan
        return None
    if situacion_lower in allowed:
        return None

    # Determine minimum required plan
    if situacion_lower in CREATOR_ROLES:
        required = "creator"
    else:
        required = "autonomo"

    return {
        "required_plan": required,
        "current_plan": effective_plan,
    }


# Global singleton
_subscription_service: Optional[SubscriptionService] = None


async def get_subscription_service() -> SubscriptionService:
    """Get global SubscriptionService instance."""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
