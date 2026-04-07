"""
Feedback Router — User-facing endpoints for feedback and chat ratings.

Provides:
- POST /api/feedback                — Submit a bug report / feature request / general feedback
- GET  /api/feedback/my             — List caller's own feedback items
- POST /api/chat-rating             — Rate an individual chat response (thumbs up/down)

Rate limiting for feedback: 10 submissions per user per day (COUNT query, not slowapi).
Screenshot validation: max 2 MB, must be PNG or JPEG (magic bytes check).
"""
import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.auth.jwt_handler import get_current_user, TokenData
from app.database.turso_client import get_db_client, TursoClient

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
