"""
Admin Endpoints — Owner-only user management.

Provides:
- GET  /api/admin/users            — List all users with plan info
- PUT  /api/admin/users/{id}/plan  — Change a user's plan_type
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.jwt_handler import get_current_user, TokenData
from app.database.turso_client import get_db_client, TursoClient
from app.services.subscription_service import get_subscription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

VALID_PLAN_TYPES = {"particular", "autonomo"}


# ---- Models ----

class ChangePlanRequest(BaseModel):
    plan_type: str  # "particular" | "autonomo"


class UserListItem(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    is_owner: bool = False
    plan_type: Optional[str] = None
    subscription_status: Optional[str] = None
    created_at: Optional[str] = None


# ---- Helpers ----

async def _require_owner(
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


# ---- Endpoints ----

@router.get("/users", response_model=list[UserListItem])
async def list_users(
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """List all users with their plan type and subscription status (owner-only)."""
    result = await db.execute(
        """
        SELECT u.id, u.email, u.name, u.is_owner, u.created_at,
               s.plan_type, s.status AS subscription_status
        FROM users u
        LEFT JOIN subscriptions s ON s.user_id = u.id
        ORDER BY u.created_at DESC
        """
    )

    users = []
    for row in result.rows:
        users.append(UserListItem(
            id=row["id"],
            email=row["email"],
            name=row.get("name"),
            is_owner=bool(row.get("is_owner")),
            plan_type=row.get("plan_type"),
            subscription_status=row.get("subscription_status"),
            created_at=row.get("created_at"),
        ))
    return users


@router.put("/users/{user_id}/plan")
async def change_user_plan(
    user_id: str,
    request: ChangePlanRequest,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """
    Change a user's plan type (owner-only).

    For upgrading to 'autonomo': also sets situacion_laboral in user_profiles.
    """
    if request.plan_type not in VALID_PLAN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"plan_type inválido. Valores permitidos: {', '.join(VALID_PLAN_TYPES)}",
        )

    # Verify user exists
    user_result = await db.execute(
        "SELECT id, email FROM users WHERE id = ?", [user_id]
    )
    if not user_result.rows:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_email = user_result.rows[0]["email"]
    now = datetime.utcnow().isoformat()

    # Update or create subscription row
    sub_result = await db.execute(
        "SELECT id FROM subscriptions WHERE user_id = ?", [user_id]
    )
    if sub_result.rows:
        await db.execute(
            "UPDATE subscriptions SET plan_type = ?, updated_at = ? WHERE user_id = ?",
            [request.plan_type, now, user_id],
        )
    else:
        # Create a minimal subscription entry (admin-granted, no Stripe)
        await db.execute(
            """INSERT INTO subscriptions
               (id, user_id, stripe_customer_id, plan_type, status,
                current_period_end, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'active', ?, ?, ?)""",
            [
                str(uuid.uuid4()),
                user_id,
                f"admin_granted_{user_id[:8]}",
                request.plan_type,
                "2099-12-31T23:59:59",
                now,
                now,
            ],
        )

    # If upgrading to autonomo, also update user_profiles.situacion_laboral
    if request.plan_type == "autonomo":
        profile_result = await db.execute(
            "SELECT id FROM user_profiles WHERE user_id = ?", [user_id]
        )
        if profile_result.rows:
            await db.execute(
                "UPDATE user_profiles SET situacion_laboral = 'autonomo', updated_at = ? WHERE user_id = ?",
                [now, user_id],
            )
        else:
            await db.execute(
                """INSERT INTO user_profiles
                   (id, user_id, situacion_laboral, datos_fiscales, created_at, updated_at)
                   VALUES (?, ?, 'autonomo', '{}', ?, ?)""",
                [str(uuid.uuid4()), user_id, now, now],
            )

    logger.info(
        "Admin plan change: user=%s email=%s plan=%s by=%s",
        user_id, user_email, request.plan_type, owner.email,
    )

    return {
        "message": f"Plan actualizado a '{request.plan_type}' para {user_email}",
        "user_id": user_id,
        "plan_type": request.plan_type,
    }
