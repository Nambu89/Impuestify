"""
Fiscal Deadlines & Push Subscriptions API

Endpoints:
- GET /api/deadlines            — list deadlines (auth, filterable)
- GET /api/deadlines/upcoming   — next N days filtered by fiscal profile (auth)
- GET /api/deadlines/public     — generic Estatal/todos deadlines (no auth, rate limited)
- POST /api/push/subscribe      — register push subscription (auth)
- DELETE /api/push/unsubscribe  — remove push subscription (auth)
- GET /api/push/vapid-key       — return VAPID public key (no auth)
"""
import uuid
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.auth.jwt_handler import get_current_user, TokenData
from app.config import settings
from app.database.turso_client import TursoClient, get_db_client
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["deadlines"])


# ---- Pydantic models ---- #

class FiscalDeadlineOut(BaseModel):
    id: str
    model: str
    model_name: str
    territory: str
    period: str
    tax_year: int
    start_date: str
    end_date: str
    domiciliation_date: Optional[str] = None
    applies_to: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    is_active: bool = True


class PushSubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=10)
    p256dh: str = Field(..., min_length=10)
    auth: str = Field(..., min_length=4)
    alert_days: Optional[str] = Field(default="15,5,1", description="Comma-separated days, e.g. '15,5,1'")
    user_agent: Optional[str] = None


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=10)


# ---- Helper functions ---- #

FORAL_TERRITORIES = {"Gipuzkoa", "Bizkaia", "Araba", "Navarra"}
CCAA_TO_FORAL: dict[str, str] = {
    "Gipuzkoa": "Gipuzkoa",
    "Bizkaia": "Bizkaia",
    "Araba": "Araba",
    "Navarra": "Navarra",
    "Pais Vasco": "Gipuzkoa",  # fallback to Gipuzkoa if no specific territory
}

SITUACION_TO_APPLIES: dict[str, list[str]] = {
    "autonomo": ["autonomos", "todos", "particulares"],
    "autónomo": ["autonomos", "todos", "particulares"],
    "asalariado": ["todos", "particulares"],
    "empleado": ["todos", "particulares"],
    "particular": ["todos", "particulares"],
    "desempleado": ["todos", "particulares"],
    "pensionista": ["todos", "particulares"],
    "jubilado": ["todos", "particulares"],
}


def _row_to_deadline(row: dict) -> FiscalDeadlineOut:
    return FiscalDeadlineOut(
        id=row["id"],
        model=row["model"],
        model_name=row["model_name"],
        territory=row["territory"],
        period=row["period"],
        tax_year=row["tax_year"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        domiciliation_date=row.get("domiciliation_date"),
        applies_to=row["applies_to"],
        description=row.get("description"),
        source_url=row.get("source_url"),
        is_active=bool(row.get("is_active", 1)),
    )


async def _get_user_territory(user_id: str, db: TursoClient) -> tuple[str, list[str]]:
    """
    Get territory and applies_to filter for a user based on their fiscal profile.
    Considers roles_adicionales (non-exclusive roles) from datos_fiscales JSON.

    Returns:
        (territory, applies_to_list)
    """
    profile_result = await db.execute(
        "SELECT ccaa_residencia, situacion_laboral, datos_fiscales FROM user_profiles WHERE user_id = ?",
        [user_id],
    )
    profile_rows = profile_result.rows or []
    if not profile_rows:
        return "Estatal", ["todos", "autonomos", "particulares"]

    profile = profile_rows[0]
    ccaa = profile.get("ccaa_residencia") or "Estatal"
    situacion = profile.get("situacion_laboral") or "particular"

    # Map CCAA to territory
    territory = CCAA_TO_FORAL.get(ccaa, "Estatal")
    applies_to = SITUACION_TO_APPLIES.get(situacion, ["todos", "particulares"])

    # Check roles_adicionales — if user has creator/pluriactividad role, include autonomos deadlines
    datos_fiscales = profile.get("datos_fiscales")
    if datos_fiscales:
        import json as _json
        try:
            datos = _json.loads(datos_fiscales) if isinstance(datos_fiscales, str) else datos_fiscales
            roles = datos.get("roles_adicionales", [])
            if isinstance(roles, str):
                roles = _json.loads(roles)
            if any(r in roles for r in ("creador_contenido", "pluriactividad", "autonomo")):
                if "autonomos" not in applies_to:
                    applies_to = list(set(applies_to + ["autonomos"]))
        except Exception as e:
            logger.warning("Failed to parse fiscal profile roles: %s", e)

    return territory, applies_to


# ---- Endpoints ---- #

@router.get("/api/deadlines", response_model=List[FiscalDeadlineOut])
async def list_deadlines(
    territory: Optional[str] = Query(None, description="Filter by territory (e.g. Madrid, Gipuzkoa)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by end_date month"),
    year: Optional[int] = Query(None, ge=2024, le=2030, description="Filter by tax_year"),
    applies_to: Optional[str] = Query(None, description="Filter: 'todos', 'autonomos', 'particulares'"),
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> List[FiscalDeadlineOut]:
    """
    List fiscal deadlines with optional filters.

    Query params:
    - territory: territory name (foral or Estatal)
    - month: month number of end_date
    - year: tax year
    - applies_to: 'todos', 'autonomos', 'particulares'
    """
    conditions = ["is_active = 1"]
    params: list = []

    if territory:
        # Foral territory -> filter by territory; else use Estatal
        if territory in FORAL_TERRITORIES:
            conditions.append("territory = ?")
            params.append(territory)
        else:
            conditions.append("territory = 'Estatal'")

    if year:
        conditions.append("tax_year = ?")
        params.append(year)

    if month:
        conditions.append("CAST(strftime('%m', end_date) AS INTEGER) = ?")
        params.append(month)

    if applies_to:
        conditions.append("applies_to IN ('todos', ?)")
        params.append(applies_to)

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM fiscal_deadlines WHERE {where} ORDER BY end_date ASC"

    result = await db.execute(sql, params if params else None)
    rows = result.rows or []
    return [_row_to_deadline(r) for r in rows]


@router.get("/api/deadlines/upcoming", response_model=List[FiscalDeadlineOut])
async def get_upcoming_deadlines(
    days: int = Query(default=30, ge=1, le=365, description="Window in days from today"),
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> List[FiscalDeadlineOut]:
    """
    Return deadlines in the next N days, filtered by user's fiscal profile.

    The territory and applies_to are determined automatically from the user's
    stored fiscal profile (ccaa_residencia + situacion_laboral).
    """
    territory, applies_to_filter = await _get_user_territory(current_user.user_id, db)

    today = date.today().isoformat()
    future = (date.today() + timedelta(days=days)).isoformat()

    # Build applies_to placeholders
    placeholders = ",".join("?" * len(applies_to_filter))

    result = await db.execute(
        f"""
        SELECT * FROM fiscal_deadlines
        WHERE is_active = 1
          AND territory = ?
          AND end_date BETWEEN ? AND ?
          AND applies_to IN ({placeholders})
        ORDER BY end_date ASC
        """,
        [territory, today, future, *applies_to_filter],
    )
    rows = result.rows or []
    return [_row_to_deadline(r) for r in rows]


@router.get("/api/deadlines/public", response_model=List[FiscalDeadlineOut])
@limiter.limit("30/minute")
async def get_public_deadlines(
    request: Request,
    days: int = Query(default=60, ge=1, le=365, description="Window in days from today"),
    db: TursoClient = Depends(get_db_client),
) -> List[FiscalDeadlineOut]:
    """
    Public endpoint: returns generic Estatal deadlines for the landing page.

    No authentication required. Rate limited to 30 requests/minute.
    Only returns applies_to='todos' deadlines for territory='Estatal'.
    """
    today = date.today().isoformat()
    future = (date.today() + timedelta(days=days)).isoformat()

    result = await db.execute(
        """
        SELECT * FROM fiscal_deadlines
        WHERE is_active = 1
          AND territory = 'Estatal'
          AND applies_to = 'todos'
          AND end_date BETWEEN ? AND ?
        ORDER BY end_date ASC
        """,
        [today, future],
    )
    rows = result.rows or []
    return [_row_to_deadline(r) for r in rows]


@router.post("/api/push/subscribe", status_code=201)
async def subscribe_push(
    body: PushSubscribeRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> dict:
    """
    Register or update a Web Push subscription for the current user.

    Upserts by (user_id, endpoint) — updates alert_days and keys if already exists.
    """
    # Validate alert_days format
    alert_days = body.alert_days or "15,5,1"
    try:
        parts = [d.strip() for d in alert_days.split(",")]
        for part in parts:
            if not part.isdigit() or int(part) < 1:
                raise ValueError(f"Invalid day: {part}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid alert_days format: {exc}")

    sub_id = str(uuid.uuid4())
    try:
        await db.execute(
            """
            INSERT INTO push_subscriptions (id, user_id, endpoint, p256dh, auth, alert_days, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, endpoint) DO UPDATE SET
                p256dh = excluded.p256dh,
                auth = excluded.auth,
                alert_days = excluded.alert_days,
                user_agent = excluded.user_agent
            """,
            [
                sub_id,
                current_user.user_id,
                body.endpoint,
                body.p256dh,
                body.auth,
                alert_days,
                body.user_agent,
            ],
        )
    except Exception as exc:
        logger.error(f"Failed to upsert push subscription: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save subscription")

    return {"status": "subscribed", "alert_days": alert_days}


@router.delete("/api/push/unsubscribe", status_code=200)
async def unsubscribe_push(
    body: PushUnsubscribeRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> dict:
    """
    Remove a push subscription for the current user.

    Only deletes the subscription matching (user_id, endpoint).
    """
    result = await db.execute(
        "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
        [current_user.user_id, body.endpoint],
    )
    return {"status": "unsubscribed"}


@router.post("/api/deadlines/email-alerts/toggle")
async def toggle_email_alerts(
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> dict:
    """
    Toggle deadline email alerts for the current user.

    Flips deadline_email_alerts between 0 and 1 in user_profiles.
    Creates a profile row with the column enabled if none exists yet.

    Returns:
        {"enabled": bool} with the new state after toggling
    """
    user_id = current_user.user_id

    # Read current value (create profile row if absent)
    result = await db.execute(
        "SELECT deadline_email_alerts FROM user_profiles WHERE user_id = ?",
        [user_id],
    )
    rows = result.rows or []

    if not rows:
        # No profile yet — create a minimal one with email alerts enabled
        import uuid as _uuid
        await db.execute(
            """
            INSERT INTO user_profiles (id, user_id, deadline_email_alerts)
            VALUES (?, ?, 1)
            """,
            [str(_uuid.uuid4()), user_id],
        )
        new_value = True
    else:
        current_value = bool(rows[0].get("deadline_email_alerts", 0))
        new_value = not current_value
        await db.execute(
            "UPDATE user_profiles SET deadline_email_alerts = ? WHERE user_id = ?",
            [1 if new_value else 0, user_id],
        )

    logger.info(f"User {user_id} toggled deadline email alerts to {new_value}")
    return {"enabled": new_value}


@router.get("/api/deadlines/email-alerts/status")
async def get_email_alerts_status(
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
) -> dict:
    """
    Return the current deadline email alert preference for the logged-in user.

    Returns:
        {"enabled": bool}
    """
    result = await db.execute(
        "SELECT deadline_email_alerts FROM user_profiles WHERE user_id = ?",
        [current_user.user_id],
    )
    rows = result.rows or []

    if not rows:
        return {"enabled": False}

    enabled = bool(rows[0].get("deadline_email_alerts", 0))
    return {"enabled": enabled}


@router.get("/api/push/vapid-key")
async def get_vapid_key() -> dict:
    """
    Return the VAPID public key for client-side push subscription.

    No authentication required — this is a public key.
    """
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=503,
            detail="Push notifications not configured on this server",
        )
    return {"publicKey": settings.VAPID_PUBLIC_KEY}
