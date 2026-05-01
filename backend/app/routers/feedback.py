"""
Feedback Router — User-facing endpoints for feedback and chat ratings.

Provides:
- POST /api/feedback                — Submit a bug report / feature request / general feedback
- GET  /api/feedback/my             — List caller's own feedback items
- POST /api/chat-rating             — Rate an individual chat response (thumbs up/down)

Rate limiting for feedback: 10 submissions per user per day (COUNT query, not slowapi).
Screenshot validation: max 2 MB, must be PNG or JPEG (magic bytes check).
"""
import asyncio
import base64
import html as html_lib
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.auth.jwt_handler import get_current_user, TokenData
from app.config import settings
from app.database.turso_client import get_db_client, TursoClient
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["feedback"])

# ---------------------------------------------------------------
# Constants
# ---------------------------------------------------------------

VALID_FEEDBACK_TYPES = {"bug", "feature", "general"}
VALID_FEEDBACK_STATUSES = {"new", "reviewed", "planned", "in_progress", "done", "wont_fix"}
VALID_RATINGS = {-1, 1}

# Max 2 MB for base64-encoded screenshot (raw bytes limit is ~1.5 MB before encoding)
_MAX_SCREENSHOT_B64_LEN = 2 * 1024 * 1024  # characters (generous; base64 overhead ~33%)

# PNG magic bytes (first 8 bytes)
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
# JPEG magic bytes (first 3 bytes)
_JPEG_MAGIC = b"\xff\xd8\xff"


# ---------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------

class FeedbackCreateRequest(BaseModel):
    type: str = Field(..., description="bug | feature | general")
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=2000)
    page_url: Optional[str] = Field(None, max_length=500)
    screenshot_data: Optional[str] = Field(None, description="Base64-encoded PNG or JPEG, max 2 MB")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_FEEDBACK_TYPES:
            raise ValueError(f"type debe ser uno de: {', '.join(sorted(VALID_FEEDBACK_TYPES))}")
        return v

    @field_validator("screenshot_data")
    @classmethod
    def validate_screenshot(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Size check (base64 string length as proxy for file size)
        if len(v) > _MAX_SCREENSHOT_B64_LEN:
            raise ValueError("El screenshot no puede superar 2 MB")
        # Strip data-URI prefix if present (e.g. "data:image/png;base64,...")
        if v.startswith("data:"):
            try:
                v = v.split(",", 1)[1]
            except IndexError:
                raise ValueError("Formato de screenshot invalido")
        # Decode to validate and check magic bytes
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("El screenshot no es base64 valido")
        if not (raw[:8] == _PNG_MAGIC or raw[:3] == _JPEG_MAGIC):
            raise ValueError("El screenshot debe ser PNG o JPEG")
        return v


class FeedbackItem(BaseModel):
    id: str
    type: str
    title: str
    description: str
    page_url: Optional[str] = None
    status: str
    priority: str
    created_at: str
    updated_at: str


class ChatRatingRequest(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=200)
    conversation_id: Optional[str] = Field(None, max_length=200)
    rating: int = Field(..., description="-1 (dislike) or 1 (like)")
    comment: Optional[str] = Field(None, max_length=500)

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v not in VALID_RATINGS:
            raise ValueError("rating debe ser -1 o 1")
        return v


# ---------------------------------------------------------------
# Helper: enforce daily rate limit (10 feedbacks/user/day)
# ---------------------------------------------------------------

_TYPE_LABELS = {"bug": "Error", "feature": "Sugerencia", "general": "General"}


async def _notify_owner_of_feedback(
    feedback_id: str,
    feedback_type: str,
    title: str,
    description: str,
    page_url: Optional[str],
    user_email: str,
    user_id: str,
) -> None:
    """Send the owner an email summarising a new feedback item.

    Best-effort: never raise. Resend failures are logged so the user-facing
    request always succeeds even if the notification doesn't go out.
    """
    if not settings.is_resend_configured:
        logger.info("Skipping feedback notification: Resend not configured")
        return

    try:
        type_label = _TYPE_LABELS.get(feedback_type, feedback_type)
        subject = f"[Impuestify · {type_label}] {title[:80]}"

        # Plain-text fallback
        text_lines = [
            f"Tipo: {type_label}",
            f"De: {user_email} (id: {user_id})",
        ]
        if page_url:
            text_lines.append(f"Pagina: {page_url}")
        text_lines.append("")
        text_lines.append(f"Titulo: {title}")
        text_lines.append("")
        text_lines.append("Descripcion:")
        text_lines.append(description)
        text_lines.append("")
        text_lines.append(
            f"Abrir en panel: https://impuestify.com/admin/feedback#{feedback_id}"
        )
        text_body = "\n".join(text_lines)

        # HTML body — escape user-controlled fields to prevent injection in the inbox.
        e_title = html_lib.escape(title)
        e_desc = html_lib.escape(description).replace("\n", "<br>")
        e_email = html_lib.escape(user_email)
        e_page = html_lib.escape(page_url) if page_url else None
        page_block = (
            f'<p style="margin:6px 0;"><strong>Pagina:</strong> '
            f'<a href="{e_page}" style="color:#1a56db;">{e_page}</a></p>'
            if e_page
            else ""
        )

        html_body = f"""<!doctype html>
<html lang="es">
<body style="margin:0;padding:0;background:#f5f7fb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#1f2937;">
  <div style="max-width:600px;margin:0 auto;padding:20px 16px;">
    <div style="background:#1a56db;color:#fff;padding:14px 20px;border-radius:8px 8px 0 0;">
      <p style="margin:0;font-size:12px;letter-spacing:1px;opacity:0.85;">FEEDBACK · {html_lib.escape(type_label).upper()}</p>
      <h1 style="margin:6px 0 0 0;font-size:18px;font-weight:600;">{e_title}</h1>
    </div>
    <div style="background:#fff;padding:18px 20px;border-radius:0 0 8px 8px;border:1px solid #e5e7eb;border-top:0;line-height:1.55;">
      <p style="margin:0 0 8px 0;"><strong>De:</strong> {e_email}</p>
      {page_block}
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:14px 0;">
      <p style="margin:0;white-space:pre-wrap;">{e_desc}</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:14px 0;">
      <p style="margin:0;font-size:13px;">
        <a href="https://impuestify.com/admin/feedback#{feedback_id}"
           style="color:#1a56db;text-decoration:none;">Abrir en el panel admin</a>
      </p>
      <p style="margin:8px 0 0 0;color:#9ca3af;font-size:11px;">
        feedback_id: {feedback_id} · user_id: {user_id}
      </p>
    </div>
  </div>
</body>
</html>"""

        service = get_email_service()
        result = await service.send_email(
            to=settings.OWNER_EMAIL,
            subject=subject,
            html=html_body,
        )
        if not result.get("success"):
            logger.warning(
                "Owner feedback notification failed: %s", result.get("error")
            )
    except Exception as exc:  # pragma: no cover - notification must never break submit
        logger.warning("Owner feedback notification raised: %s", exc, exc_info=True)


async def _check_feedback_rate_limit(user_id: str, db: TursoClient) -> None:
    result = await db.execute(
        "SELECT COUNT(*) as cnt FROM feedback WHERE user_id = ? AND created_at > date('now', '-1 day')",
        [user_id],
    )
    count = result.rows[0]["cnt"] if result.rows else 0
    if count >= 10:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Has alcanzado el limite de 10 feedbacks por dia. Intenta de nuevo manana.",
        )


# ---------------------------------------------------------------
# POST /api/feedback
# ---------------------------------------------------------------

@router.post("/api/feedback", status_code=status.HTTP_201_CREATED)
async def create_feedback(
    body: FeedbackCreateRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """
    Submit a feedback item (bug report, feature request or general comment).

    Rate limited to 10 submissions per user per calendar day.
    Screenshots must be base64-encoded PNG or JPEG (max 2 MB).
    """
    await _check_feedback_rate_limit(current_user.user_id, db)

    feedback_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """
        INSERT INTO feedback
          (id, user_id, type, title, description, page_url, screenshot_data,
           status, priority, admin_notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'new', 'normal', NULL, ?, ?)
        """,
        [
            feedback_id,
            current_user.user_id,
            body.type,
            body.title,
            body.description,
            body.page_url,
            body.screenshot_data,
            now,
            now,
        ],
    )

    logger.info(
        "Feedback created: id=%s user=%s type=%s",
        feedback_id,
        current_user.user_id,
        body.type,
    )

    # Notify the owner by email so we react to bugs/suggestions without having
    # to poll the admin panel. Fire-and-forget: any failure is logged but the
    # user's submission already succeeded above.
    asyncio.create_task(
        _notify_owner_of_feedback(
            feedback_id=feedback_id,
            feedback_type=body.type,
            title=body.title,
            description=body.description,
            page_url=body.page_url,
            user_email=current_user.email,
            user_id=current_user.user_id,
        )
    )

    return {
        "id": feedback_id,
        "message": "Gracias por tu feedback. Lo revisaremos pronto.",
    }


# ---------------------------------------------------------------
# GET /api/feedback/my
# ---------------------------------------------------------------

@router.get("/api/feedback/my", response_model=list[FeedbackItem])
async def list_my_feedback(
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """Return the authenticated user's own feedback items (no screenshot data)."""
    result = await db.execute(
        """
        SELECT id, type, title, description, page_url, status, priority, created_at, updated_at
        FROM feedback
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        [current_user.user_id],
    )

    items = []
    for row in result.rows:
        items.append(
            FeedbackItem(
                id=row["id"],
                type=row["type"],
                title=row["title"],
                description=row["description"],
                page_url=row.get("page_url"),
                status=row["status"],
                priority=row["priority"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )
    return items


# ---------------------------------------------------------------
# POST /api/chat-rating
# ---------------------------------------------------------------

@router.post("/api/chat-rating", status_code=status.HTTP_201_CREATED)
async def create_chat_rating(
    body: ChatRatingRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """
    Rate an individual assistant message (thumbs up = 1, thumbs down = -1).

    A user can only rate each message_id once; duplicate submissions return 409.
    """
    # Check for duplicate rating
    existing = await db.execute(
        "SELECT id FROM chat_ratings WHERE user_id = ? AND message_id = ?",
        [current_user.user_id, body.message_id],
    )
    if existing.rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya has valorado este mensaje.",
        )

    rating_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """
        INSERT INTO chat_ratings (id, user_id, message_id, conversation_id, rating, comment, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            rating_id,
            current_user.user_id,
            body.message_id,
            body.conversation_id,
            body.rating,
            body.comment,
            now,
        ],
    )

    logger.info(
        "Chat rating created: id=%s user=%s message=%s rating=%d",
        rating_id,
        current_user.user_id,
        body.message_id,
        body.rating,
    )

    return {"id": rating_id, "message": "Valoracion registrada. Gracias."}
