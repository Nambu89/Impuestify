"""
Admin Endpoints — Owner-only user management and dashboard.

Provides:
- GET  /api/admin/users                      — List all users with plan info
- PUT  /api/admin/users/{id}/plan            — Change a user's plan_type
- PUT  /api/admin/users/{id}/grant-beta      — Grant free beta access until 31/12/2026
- PUT  /api/admin/users/{id}/revoke-beta     — Revoke beta access
- GET  /api/admin/dashboard                  — Aggregated metrics
- GET  /api/admin/feedback                   — List all feedback (no screenshot)
- GET  /api/admin/feedback/stats             — Feedback counters by type/status/priority
- GET  /api/admin/feedback/{id}              — Feedback detail (includes screenshot)
- PUT  /api/admin/feedback/{id}              — Update feedback status/priority/notes
- GET  /api/admin/contact-requests           — List contact requests
- PUT  /api/admin/contact-requests/{id}      — Mark contact request as responded
- GET  /api/admin/chat-ratings               — List chat ratings
- GET  /api/admin/chat-ratings/stats         — Rating stats (% positive, trend)
"""
import logging
import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


@router.put("/users/{user_id}/grant-beta")
async def grant_beta_access(
    user_id: str,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Grant free beta access to a user (active until 31/12/2026, no Stripe)."""
    user_result = await db.execute(
        "SELECT id, email FROM users WHERE id = ?", [user_id]
    )
    if not user_result.rows:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_email = user_result.rows[0]["email"]
    now = datetime.utcnow().isoformat()
    beta_end = "2026-12-31T23:59:59"

    sub_result = await db.execute(
        "SELECT id FROM subscriptions WHERE user_id = ?", [user_id]
    )
    if sub_result.rows:
        await db.execute(
            """UPDATE subscriptions
               SET status = 'active', current_period_start = ?, current_period_end = ?, updated_at = ?
               WHERE user_id = ?""",
            [now, beta_end, now, user_id],
        )
    else:
        await db.execute(
            """INSERT INTO subscriptions
               (id, user_id, stripe_customer_id, plan_type, status,
                current_period_start, current_period_end, created_at, updated_at)
               VALUES (?, ?, ?, 'particular', 'active', ?, ?, ?, ?)""",
            [str(uuid.uuid4()), user_id, f"beta_{user_id[:8]}",
             now, beta_end, now, now],
        )

    logger.info(
        "Admin grant beta: user=%s email=%s until=%s by=%s",
        user_id, user_email, beta_end, owner.email,
    )

    return {
        "message": f"Acceso beta activado para {user_email} hasta 31/12/2026",
        "user_id": user_id,
        "subscription_status": "active",
    }


@router.put("/users/{user_id}/revoke-beta")
async def revoke_beta_access(
    user_id: str,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Revoke beta access (set subscription to inactive)."""
    user_result = await db.execute(
        "SELECT id, email FROM users WHERE id = ?", [user_id]
    )
    if not user_result.rows:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_email = user_result.rows[0]["email"]
    now = datetime.utcnow().isoformat()

    await db.execute(
        "UPDATE subscriptions SET status = 'inactive', updated_at = ? WHERE user_id = ?",
        [now, user_id],
    )

    logger.info(
        "Admin revoke beta: user=%s email=%s by=%s",
        user_id, user_email, owner.email,
    )

    return {
        "message": f"Acceso beta revocado para {user_email}",
        "user_id": user_id,
        "subscription_status": "inactive",
    }


# ============================================================
# DASHBOARD METRICS
# ============================================================

@router.get("/dashboard")
async def get_dashboard(
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Return aggregated metrics for the admin dashboard (owner-only)."""

    # Users
    total_users_result = await db.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = total_users_result.rows[0]["cnt"] if total_users_result.rows else 0

    active_week_result = await db.execute(
        "SELECT COUNT(DISTINCT user_id) as cnt FROM conversations WHERE updated_at > date('now', '-7 days')"
    )
    active_this_week = active_week_result.rows[0]["cnt"] if active_week_result.rows else 0

    subscribers_result = await db.execute(
        "SELECT COUNT(*) as cnt FROM subscriptions WHERE status = 'active'"
    )
    subscribers_paid = subscribers_result.rows[0]["cnt"] if subscribers_result.rows else 0

    plan_result = await db.execute(
        "SELECT plan_type, COUNT(*) as cnt FROM subscriptions WHERE status = 'active' GROUP BY plan_type"
    )
    by_plan = {}
    for row in plan_result.rows:
        by_plan[row["plan_type"]] = row["cnt"]

    new_month_result = await db.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE created_at > date('now', '-30 days')"
    )
    new_this_month = new_month_result.rows[0]["cnt"] if new_month_result.rows else 0

    # Feedback
    bugs_open_result = await db.execute(
        "SELECT COUNT(*) as cnt FROM feedback WHERE type = 'bug' AND status NOT IN ('done', 'wont_fix')"
    )
    bugs_open = bugs_open_result.rows[0]["cnt"] if bugs_open_result.rows else 0

    features_pending_result = await db.execute(
        "SELECT COUNT(*) as cnt FROM feedback WHERE type = 'feature' AND status NOT IN ('done', 'wont_fix')"
    )
    features_pending = features_pending_result.rows[0]["cnt"] if features_pending_result.rows else 0

    feedback_total_result = await db.execute("SELECT COUNT(*) as cnt FROM feedback")
    feedback_total = feedback_total_result.rows[0]["cnt"] if feedback_total_result.rows else 0

    # Chat ratings
    ratings_total_result = await db.execute("SELECT COUNT(*) as cnt FROM chat_ratings")
    ratings_total = ratings_total_result.rows[0]["cnt"] if ratings_total_result.rows else 0

    positive_count_result = await db.execute(
        "SELECT COUNT(*) as cnt FROM chat_ratings WHERE rating = 1"
    )
    positive_count = positive_count_result.rows[0]["cnt"] if positive_count_result.rows else 0

    positive_pct = round((positive_count / ratings_total * 100), 1) if ratings_total > 0 else 0.0
    negative_pct = round(100.0 - positive_pct, 1) if ratings_total > 0 else 0.0

    # Trend: compare last 30 days vs previous 30 days
    trend_str = "N/A"
    if ratings_total > 0:
        recent_result = await db.execute(
            "SELECT COUNT(*) as cnt FROM chat_ratings WHERE rating = 1 AND created_at > date('now', '-30 days')"
        )
        recent_positive = recent_result.rows[0]["cnt"] if recent_result.rows else 0
        recent_total_result = await db.execute(
            "SELECT COUNT(*) as cnt FROM chat_ratings WHERE created_at > date('now', '-30 days')"
        )
        recent_total = recent_total_result.rows[0]["cnt"] if recent_total_result.rows else 0

        prev_result = await db.execute(
            """SELECT COUNT(*) as cnt FROM chat_ratings
               WHERE rating = 1
                 AND created_at <= date('now', '-30 days')
                 AND created_at > date('now', '-60 days')"""
        )
        prev_positive = prev_result.rows[0]["cnt"] if prev_result.rows else 0
        prev_total_result = await db.execute(
            """SELECT COUNT(*) as cnt FROM chat_ratings
               WHERE created_at <= date('now', '-30 days')
                 AND created_at > date('now', '-60 days')"""
        )
        prev_total = prev_total_result.rows[0]["cnt"] if prev_total_result.rows else 0

        if recent_total > 0 and prev_total > 0:
            recent_pct = recent_positive / recent_total * 100
            prev_pct = prev_positive / prev_total * 100
            diff = recent_pct - prev_pct
            sign = "+" if diff >= 0 else ""
            trend_str = f"{sign}{diff:.1f}%"

    # Contact requests
    contact_pending_result = await db.execute(
        "SELECT COUNT(*) as cnt FROM contact_requests WHERE status = 'pending'"
    )
    contact_pending = contact_pending_result.rows[0]["cnt"] if contact_pending_result.rows else 0

    contact_total_result = await db.execute("SELECT COUNT(*) as cnt FROM contact_requests")
    contact_total = contact_total_result.rows[0]["cnt"] if contact_total_result.rows else 0

    return {
        "users": {
            "total": total_users,
            "active_this_week": active_this_week,
            "subscribers_paid": subscribers_paid,
            "by_plan": by_plan,
            "new_this_month": new_this_month,
        },
        "feedback": {
            "bugs_open": bugs_open,
            "features_pending": features_pending,
            "total": feedback_total,
        },
        "ratings": {
            "total": ratings_total,
            "positive_pct": positive_pct,
            "negative_pct": negative_pct,
            "trend_30d": trend_str,
        },
        "contact_requests": {
            "pending": contact_pending,
            "total": contact_total,
        },
    }


# ============================================================
# FEEDBACK MANAGEMENT
# IMPORTANT: /feedback/stats MUST come before /feedback/{id}
# so FastAPI does not interpret "stats" as an ID.
# ============================================================

class FeedbackUpdateRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    admin_notes: Optional[str] = None


VALID_FEEDBACK_STATUSES = {"new", "reviewed", "planned", "in_progress", "done", "wont_fix"}
VALID_PRIORITIES = {"low", "normal", "high", "critical"}


@router.get("/feedback/stats")
async def get_feedback_stats(
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Return feedback counters grouped by type, status and priority (owner-only)."""
    by_type_result = await db.execute(
        "SELECT type, COUNT(*) as cnt FROM feedback GROUP BY type"
    )
    by_status_result = await db.execute(
        "SELECT status, COUNT(*) as cnt FROM feedback GROUP BY status"
    )
    by_priority_result = await db.execute(
        "SELECT priority, COUNT(*) as cnt FROM feedback GROUP BY priority"
    )

    def rows_to_dict(rows):
        return {row[list(row.keys())[0]]: row["cnt"] for row in rows}

    return {
        "by_type": {row["type"]: row["cnt"] for row in by_type_result.rows},
        "by_status": {row["status"]: row["cnt"] for row in by_status_result.rows},
        "by_priority": {row["priority"]: row["cnt"] for row in by_priority_result.rows},
    }


@router.get("/feedback")
async def list_feedback(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """
    List all feedback items with optional filters (owner-only).

    screenshot_data is intentionally excluded to keep responses fast.
    Retrieve it via GET /api/admin/feedback/{id}.
    """
    conditions = []
    params = []

    if type is not None:
        conditions.append("type = ?")
        params.append(type)
    if status is not None:
        conditions.append("status = ?")
        params.append(status)
    if priority is not None:
        conditions.append("priority = ?")
        params.append(priority)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    result = await db.execute(
        f"""
        SELECT f.id, f.type, f.title, f.description, f.page_url,
               f.status, f.priority, f.admin_notes,
               f.created_at, f.updated_at,
               u.email AS user_email
        FROM feedback f
        LEFT JOIN users u ON u.id = f.user_id
        {where_clause}
        ORDER BY f.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )

    items = []
    for row in result.rows:
        items.append({
            "id": row["id"],
            "type": row["type"],
            "title": row["title"],
            "description": row["description"],
            "page_url": row.get("page_url"),
            "status": row["status"],
            "priority": row["priority"],
            "admin_notes": row.get("admin_notes"),
            "user_email": row.get("user_email"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
    return items


@router.get("/feedback/{feedback_id}")
async def get_feedback_detail(
    feedback_id: str,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Return full feedback detail including screenshot_data (owner-only)."""
    result = await db.execute(
        """
        SELECT f.*, u.email AS user_email
        FROM feedback f
        LEFT JOIN users u ON u.id = f.user_id
        WHERE f.id = ?
        """,
        [feedback_id],
    )
    if not result.rows:
        raise HTTPException(status_code=404, detail="Feedback no encontrado")

    row = result.rows[0]
    return {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "page_url": row.get("page_url"),
        "screenshot_data": row.get("screenshot_data"),
        "status": row["status"],
        "priority": row["priority"],
        "admin_notes": row.get("admin_notes"),
        "user_email": row.get("user_email"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@router.put("/feedback/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    body: FeedbackUpdateRequest,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Update a feedback item's status, priority and/or admin notes (owner-only)."""
    existing = await db.execute(
        "SELECT id FROM feedback WHERE id = ?", [feedback_id]
    )
    if not existing.rows:
        raise HTTPException(status_code=404, detail="Feedback no encontrado")

    if body.status is not None and body.status not in VALID_FEEDBACK_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status invalido. Valores permitidos: {', '.join(sorted(VALID_FEEDBACK_STATUSES))}",
        )
    if body.priority is not None and body.priority not in VALID_PRIORITIES:
        raise HTTPException(
            status_code=400,
            detail=f"priority invalida. Valores permitidos: {', '.join(sorted(VALID_PRIORITIES))}",
        )

    update_fields = []
    params = []
    if body.status is not None:
        update_fields.append("status = ?")
        params.append(body.status)
    if body.priority is not None:
        update_fields.append("priority = ?")
        params.append(body.priority)
    if body.admin_notes is not None:
        update_fields.append("admin_notes = ?")
        params.append(body.admin_notes)

    if not update_fields:
        raise HTTPException(status_code=400, detail="No se proporcionaron campos a actualizar")

    now = datetime.utcnow().isoformat()
    update_fields.append("updated_at = ?")
    params.append(now)
    params.append(feedback_id)

    await db.execute(
        f"UPDATE feedback SET {', '.join(update_fields)} WHERE id = ?",
        params,
    )

    logger.info("Admin updated feedback %s by %s", feedback_id, owner.email)
    return {"message": "Feedback actualizado correctamente", "id": feedback_id}


# ============================================================
# CONTACT REQUESTS MANAGEMENT
# ============================================================

@router.get("/contact-requests")
async def list_contact_requests(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """List contact form submissions with optional status filter (owner-only)."""
    conditions = []
    params = []

    if status is not None:
        conditions.append("status = ?")
        params.append(status)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    result = await db.execute(
        f"""
        SELECT id, user_id, email, name, message, request_type, status, created_at
        FROM contact_requests
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )

    items = []
    for row in result.rows:
        items.append({
            "id": row["id"],
            "user_id": row.get("user_id"),
            "email": row["email"],
            "name": row.get("name"),
            "message": row.get("message"),
            "request_type": row.get("request_type"),
            "status": row["status"],
            "created_at": row["created_at"],
        })
    return items


class ContactRequestUpdateBody(BaseModel):
    status: str  # "pending" | "responded"


VALID_CONTACT_STATUSES = {"pending", "responded"}


@router.put("/contact-requests/{request_id}")
async def update_contact_request(
    request_id: str,
    body: ContactRequestUpdateBody,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Mark a contact request as responded (or revert to pending) (owner-only)."""
    if body.status not in VALID_CONTACT_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status invalido. Valores permitidos: {', '.join(sorted(VALID_CONTACT_STATUSES))}",
        )

    existing = await db.execute(
        "SELECT id FROM contact_requests WHERE id = ?", [request_id]
    )
    if not existing.rows:
        raise HTTPException(status_code=404, detail="Solicitud de contacto no encontrada")

    await db.execute(
        "UPDATE contact_requests SET status = ? WHERE id = ?",
        [body.status, request_id],
    )

    logger.info("Admin updated contact request %s to %s by %s", request_id, body.status, owner.email)
    return {"message": f"Solicitud marcada como '{body.status}'", "id": request_id}


# ============================================================
# CHAT RATINGS MANAGEMENT
# IMPORTANT: /chat-ratings/stats MUST come before /chat-ratings
# ============================================================

@router.get("/chat-ratings/stats")
async def get_chat_ratings_stats(
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Return chat rating statistics: % positive, % negative, 30-day trend (owner-only)."""
    total_result = await db.execute("SELECT COUNT(*) as cnt FROM chat_ratings")
    total = total_result.rows[0]["cnt"] if total_result.rows else 0

    positive_result = await db.execute(
        "SELECT COUNT(*) as cnt FROM chat_ratings WHERE rating = 1"
    )
    positive = positive_result.rows[0]["cnt"] if positive_result.rows else 0

    positive_pct = round(positive / total * 100, 1) if total > 0 else 0.0
    negative_pct = round(100.0 - positive_pct, 1) if total > 0 else 0.0

    trend_str = "N/A"
    if total > 0:
        r_pos_result = await db.execute(
            "SELECT COUNT(*) as cnt FROM chat_ratings WHERE rating = 1 AND created_at > date('now', '-30 days')"
        )
        r_pos = r_pos_result.rows[0]["cnt"] if r_pos_result.rows else 0
        r_tot_result = await db.execute(
            "SELECT COUNT(*) as cnt FROM chat_ratings WHERE created_at > date('now', '-30 days')"
        )
        r_tot = r_tot_result.rows[0]["cnt"] if r_tot_result.rows else 0

        p_pos_result = await db.execute(
            """SELECT COUNT(*) as cnt FROM chat_ratings
               WHERE rating = 1
                 AND created_at <= date('now', '-30 days')
                 AND created_at > date('now', '-60 days')"""
        )
        p_pos = p_pos_result.rows[0]["cnt"] if p_pos_result.rows else 0
        p_tot_result = await db.execute(
            """SELECT COUNT(*) as cnt FROM chat_ratings
               WHERE created_at <= date('now', '-30 days')
                 AND created_at > date('now', '-60 days')"""
        )
        p_tot = p_tot_result.rows[0]["cnt"] if p_tot_result.rows else 0

        if r_tot > 0 and p_tot > 0:
            diff = (r_pos / r_tot * 100) - (p_pos / p_tot * 100)
            sign = "+" if diff >= 0 else ""
            trend_str = f"{sign}{diff:.1f}%"

    return {
        "total": total,
        "positive_pct": positive_pct,
        "negative_pct": negative_pct,
        "trend_30d": trend_str,
    }


@router.get("/chat-ratings")
async def list_chat_ratings(
    rating: Optional[int] = Query(None, description="-1 or 1"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """List chat ratings with optional filter by rating value (owner-only)."""
    conditions = []
    params = []

    if rating is not None:
        if rating not in (-1, 1):
            raise HTTPException(status_code=400, detail="rating debe ser -1 o 1")
        conditions.append("cr.rating = ?")
        params.append(rating)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * limit

    result = await db.execute(
        f"""
        SELECT cr.id, cr.user_id, cr.message_id, cr.conversation_id,
               cr.rating, cr.comment, cr.created_at,
               u.email AS user_email
        FROM chat_ratings cr
        LEFT JOIN users u ON u.id = cr.user_id
        {where_clause}
        ORDER BY cr.created_at DESC
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    )

    items = []
    for row in result.rows:
        items.append({
            "id": row["id"],
            "user_id": row.get("user_id"),
            "user_email": row.get("user_email"),
            "message_id": row["message_id"],
            "conversation_id": row.get("conversation_id"),
            "rating": row["rating"],
            "comment": row.get("comment"),
            "created_at": row["created_at"],
        })
    return items
