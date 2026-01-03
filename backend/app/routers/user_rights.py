"""
GDPR User Rights Endpoints

Implements user rights according to GDPR/RGPD:
- Art. 15: Right to Access (Data Export)
- Art. 16: Right to Rectification (Profile Update)
- Art. 17: Right to Erasure (Account Deletion)
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from app.auth.security import get_current_user
from app.database.turso_client import get_db_client, TursoClient

router = APIRouter(prefix="/api/users/me", tags=["user-rights"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class UserUpdateRequest(BaseModel):
    """Request model for updating user profile"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserDataExport(BaseModel):
    """Complete user data export (GDPR Art. 15)"""
    export_date: str
    user: Dict[str, Any]
    conversations: List[Dict[str, Any]]
    total_conversations: int
    total_messages: int
    account_created: str


class DeleteAccountResponse(BaseModel):
    """Response after account deletion"""
    message: str
    user_id: str
    deleted_at: str
    data_purged: Dict[str, int]


# ============================================
# GDPR ART. 15: RIGHT TO ACCESS (DATA EXPORT)
# ============================================

@router.get("/data", response_model=UserDataExport)
async def export_user_data(
    current_user: dict = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client)
):
    """
    Export all user data in JSON format.
    
    **GDPR Art. 15 - Right to Access**
    
    Returns:
    - User account information
    - All conversations with messages
    - Metadata and statistics
    
    Status code 200: Export successful
    """
    user_id = current_user["id"]
    
    # 1. Get user account data
    user_result = await db.execute(
        "SELECT id, email, name, is_admin, created_at, updated_at FROM users WHERE id = ?",
        [user_id]
    )
    
    if not user_result.rows:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user_result.rows[0]
    
    # 2. Get all conversations
    conversations_result = await db.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at, 
               COUNT(m.id) as message_count
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.created_at DESC
        """,
        [user_id]
    )
    
    conversations_list = []
    total_messages = 0
    
    for conv in conversations_result.rows:
        # Get messages for this conversation
        messages_result = await db.execute(
            """
            SELECT id, role, content, created_at, metadata
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            [conv["id"]]
        )
        
        messages = [
            {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "metadata": json.loads(msg["metadata"]) if msg.get("metadata") else None,
                "created_at": msg["created_at"]
            }
            for msg in messages_result.rows
        ]
        
        conversations_list.append({
            "id": conv["id"],
            "title": conv["title"],
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"],
            "message_count": conv["message_count"] or 0,
            "messages": messages
        })
        
        total_messages += len(messages)
    
    # 3. Build export
    export = UserDataExport(
        export_date=datetime.utcnow().isoformat() + "Z",
        user={
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "is_admin": bool(user_data["is_admin"]),
            "created_at": user_data["created_at"],
            "updated_at": user_data["updated_at"]
        },
        conversations=conversations_list,
        total_conversations=len(conversations_list),
        total_messages=total_messages,
        account_created=user_data["created_at"]
    )
    
    return export


# ============================================
# GDPR ART. 16: RIGHT TO RECTIFICATION
# ============================================

@router.patch("", response_model=dict)
async def update_user_profile(
    updates: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client)
):
    """
    Update user profile information.
    
    **GDPR Art. 16 - Right to Rectification**
    
    Allows updating:
    - name (optional)
    - email (must be unique)
    
    Returns: Updated user data
    Status code 200: Update successful
    Status code 409: Email already in use
    """
    user_id = current_user["id"]
    
    # Check if there's anything to update
    if not updates.name and not updates.email:
        raise HTTPException(
            status_code=400, 
            detail="No data provided for update"
        )
    
    # Check email uniqueness if email is being updated
    if updates.email:
        existing_user = await db.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?",
            [updates.email, user_id]
        )
        
        if existing_user.rows:
            raise HTTPException(
                status_code=409, 
                detail="Email already in use"
            )
    
    # Build UPDATE query dynamically
    update_fields = []
    params = []
    
    if updates.name is not None:
        update_fields.append("name = ?")
        params.append(updates.name)
    
    if updates.email is not None:
        update_fields.append("email = ?")
        params.append(updates.email)
    
    # Always update updated_at
    update_fields.append("updated_at = datetime('now')")
    
    # Execute update
    params.append(user_id)
    
    await db.execute(
        f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?",
        params
    )
    
    # Fetch updated user
    updated_user = await db.execute(
        "SELECT id, email, name, is_admin, created_at, updated_at FROM users WHERE id = ?",
        [user_id]
    )
    
    if not updated_user.rows:
        raise HTTPException(status_code=404, detail="User not found after update")
    
    user_data = updated_user.rows[0]
    
    return {
        "message": "Profile updated successfully",
        "user": {
            "id": user_data["id"],
            "email": user_data["email"],
            "name": user_data["name"],
            "is_admin": bool(user_data["is_admin"]),
            "created_at": user_data["created_at"],
            "updated_at": user_data["updated_at"]
        }
    }


# ============================================
# GDPR ART. 17: RIGHT TO ERASURE
# ============================================

@router.delete("", response_model=DeleteAccountResponse)
async def delete_user_account(
    current_user: dict = Depends(get_current_user),
    db: TursoClient = Depends(get_db_client)
):
    """
    Permanently delete user account and all associated data.
    
    **GDPR Art. 17 - Right to Erasure ("Right to be Forgotten")**
    
    Deletes:
    - User account
    - All conversations and messages (CASCADE)
    - All sessions/tokens (CASCADE)
    
    ⚠️ **WARNING**: This action is IRREVERSIBLE.
    
    Returns: Confirmation of deletion with counts
    Status code 200: Account deleted successfully
    """
    user_id = current_user["id"]
    
    # Count data before deletion (for confirmation)
    conversations_count_result = await db.execute(
        "SELECT COUNT(*) as count FROM conversations WHERE user_id = ?",
        [user_id]
    )
    conversations_count = conversations_count_result.rows[0]["count"]
    
    messages_count_result = await db.execute(
        """
        SELECT COUNT(m.id) as count 
        FROM messages m
        JOIN conversations c ON m.conversation_id = c.id
        WHERE c.user_id = ?
        """,
        [user_id]
    )
    messages_count = messages_count_result.rows[0]["count"]
    
    sessions_count_result = await db.execute(
        "SELECT COUNT(*) as count FROM sessions WHERE user_id = ?",
        [user_id]
    )
    sessions_count = sessions_count_result.rows[0]["count"]
    
    # Delete user (CASCADE will handle related data)
    # Order matters due to foreign keys:
    # 1. Messages (CASCADE from conversations)
    # 2. Conversations
    # 3. Sessions
    # 4. User
    
    await db.execute(
        "DELETE FROM conversations WHERE user_id = ?",
        [user_id]
    )
    
    await db.execute(
        "DELETE FROM sessions WHERE user_id = ?",
        [user_id]
    )
    
    await db.execute(
        "DELETE FROM users WHERE id = ?",
        [user_id]
    )
    
    # Return confirmation
    return DeleteAccountResponse(
        message="Account deleted successfully. All data has been permanently removed.",
        user_id=user_id,
        deleted_at=datetime.utcnow().isoformat() + "Z",
        data_purged={
            "conversations": conversations_count,
            "messages": messages_count,
            "sessions": sessions_count,
            "user_account": 1
        }
    )
