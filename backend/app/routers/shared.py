"""
Shared Conversations — Public share links for chat conversations.

Endpoints:
- POST /api/conversations/{id}/share  — Create share link (auth required)
- GET  /api/shared/{token}            — View shared conversation (public)
- DELETE /api/conversations/{id}/share — Revoke share link (auth required)
"""
import json
import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.auth.jwt_handler import get_current_user, TokenData
from app.database.turso_client import get_db_client, TursoClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["shared"])


class ShareRequest(BaseModel):
    anonymize: bool = True


class ShareResponse(BaseModel):
    share_url: str
    share_token: str
    anonymized: bool
    message_count: int


# =====================================================================
# PII Anonymization for shared conversations
# =====================================================================

_PII_PATTERNS = [
    # DNI/NIE
    (re.compile(r'\b[0-9]{8}[A-Z]\b'), '[DNI]'),
    (re.compile(r'\b[XYZ][0-9]{7}[A-Z]\b'), '[NIE]'),
    # Phone numbers (Spanish)
    (re.compile(r'\b(?:\+34|0034)?[6789]\d{8}\b'), '[TELEFONO]'),
    # Email addresses
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
    # IBAN
    (re.compile(r'\b[A-Z]{2}\d{2}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '[IBAN]'),
    # Credit card numbers
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '[TARJETA]'),
    # Specific salary amounts (>1000 with EUR/euros)
    (re.compile(r'\b(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:EUR|euros?|€)\b', re.IGNORECASE), '[IMPORTE] EUR'),
]

# Names are harder — we anonymize common patterns like "Sr./Sra. Nombre"
_NAME_PATTERNS = [
    (re.compile(r'\b(?:Sr\.|Sra\.|Don|Doña)\s+[A-Z][a-záéíóú]+(?:\s+[A-Z][a-záéíóú]+){0,2}\b'), '[NOMBRE]'),
]


def _anonymize_text(text: str) -> str:
    """Remove PII from text for safe sharing."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in _NAME_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _anonymize_messages(messages: list) -> list:
    """Anonymize all messages in a conversation."""
    anonymized = []
    for msg in messages:
        new_msg = dict(msg)
        if new_msg.get("content"):
            new_msg["content"] = _anonymize_text(new_msg["content"])
        anonymized.append(new_msg)
    return anonymized


# =====================================================================
# POST /api/conversations/{id}/share — Create share link
# =====================================================================

@router.post("/api/conversations/{conversation_id}/share", response_model=ShareResponse)
async def create_share_link(
    conversation_id: str,
    body: ShareRequest,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """Create a public share link for a conversation."""

    # Verify conversation belongs to user
    conv = await db.execute(
        "SELECT id, title FROM conversations WHERE id = ? AND user_id = ?",
        [conversation_id, current_user.user_id],
    )
    if not conv.rows:
        raise HTTPException(status_code=404, detail="Conversacion no encontrada")

    title = conv.rows[0].get("title", "Conversacion compartida")

    # Get messages
    msgs = await db.execute(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        [conversation_id],
    )
    if not msgs.rows:
        raise HTTPException(status_code=400, detail="La conversacion no tiene mensajes")

    messages = [
        {"role": row["role"], "content": row["content"], "created_at": row.get("created_at", "")}
        for row in msgs.rows
    ]

    # Anonymize if requested
    if body.anonymize:
        messages = _anonymize_messages(messages)

    # Check if share already exists
    existing = await db.execute(
        "SELECT share_token, anonymized FROM shared_conversations WHERE conversation_id = ? AND user_id = ?",
        [conversation_id, current_user.user_id],
    )

    if existing.rows:
        # Update existing share
        share_token = existing.rows[0]["share_token"]
        await db.execute(
            "UPDATE shared_conversations SET messages = ?, anonymized = ?, title = ? WHERE share_token = ?",
            [json.dumps(messages, ensure_ascii=False), body.anonymize, title, share_token],
        )
    else:
        # Create new share
        share_id = str(uuid.uuid4())
        share_token = uuid.uuid4().hex[:12]  # Short token for URL
        await db.execute(
            """INSERT INTO shared_conversations (id, share_token, user_id, conversation_id, title, messages, anonymized)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [share_id, share_token, current_user.user_id, conversation_id, title,
             json.dumps(messages, ensure_ascii=False), body.anonymize],
        )

    return ShareResponse(
        share_url=f"/shared/{share_token}",
        share_token=share_token,
        anonymized=body.anonymize,
        message_count=len(messages),
    )


# =====================================================================
# GET /api/shared/{token} — View shared conversation (PUBLIC)
# =====================================================================

@router.get("/api/shared/{token}")
async def get_shared_conversation(
    token: str,
    db: TursoClient = Depends(get_db_client),
):
    """View a shared conversation. Public endpoint, no auth required."""

    result = await db.execute(
        "SELECT title, messages, anonymized, created_at, view_count FROM shared_conversations WHERE share_token = ?",
        [token],
    )

    if not result.rows:
        raise HTTPException(status_code=404, detail="Enlace no encontrado o expirado")

    row = result.rows[0]

    # Increment view count
    await db.execute(
        "UPDATE shared_conversations SET view_count = view_count + 1 WHERE share_token = ?",
        [token],
    )

    try:
        messages = json.loads(row["messages"])
    except (json.JSONDecodeError, TypeError):
        messages = []

    return {
        "title": row.get("title", "Conversacion"),
        "messages": messages,
        "anonymized": bool(row.get("anonymized", True)),
        "created_at": row.get("created_at", ""),
        "view_count": (row.get("view_count", 0) or 0) + 1,
    }


# =====================================================================
# DELETE /api/conversations/{id}/share — Revoke share link
# =====================================================================

@router.delete("/api/conversations/{conversation_id}/share")
async def revoke_share_link(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client),
):
    """Revoke (delete) a share link for a conversation."""

    result = await db.execute(
        "DELETE FROM shared_conversations WHERE conversation_id = ? AND user_id = ?",
        [conversation_id, current_user.user_id],
    )

    return {"status": "deleted", "conversation_id": conversation_id}
