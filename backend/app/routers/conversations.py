"""
Conversations Router for TaxIA

Provides REST API endpoints for managing chat conversations.
Supports Claude/ChatGPT-style persistent conversations per user.
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.database.turso_client import TursoClient
from app.services.conversation_service import ConversationService
from app.auth.jwt_handler import get_current_user, TokenData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# === Models ===

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation"""
    title: Optional[str] = Field(None, max_length=200, description="Conversation title")


class UpdateConversationRequest(BaseModel):
    """Request to update conversation"""
    title: str = Field(..., min_length=1, max_length=200, description="New title")


class ConversationResponse(BaseModel):
    """Conversation metadata"""
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    """Chat message"""
    id: str
    conversation_id: str
    role: str
    content: str
    metadata: Dict[str, Any]
    created_at: str


class ConversationWithMessagesResponse(BaseModel):
    """Conversation with full message history"""
    conversation: ConversationResponse
    messages: List[MessageResponse]


# === Dependencies ===

async def get_db(request: Request) -> TursoClient:
    """Get database client from app state"""
    if hasattr(request.app.state, 'db_client') and request.app.state.db_client:
        return request.app.state.db_client
    raise HTTPException(
        status_code=503,
        detail="Database not connected"
    )


async def get_conversation_service(db: TursoClient = Depends(get_db)) -> ConversationService:
    """Get conversation service instance"""
    return ConversationService(db)


# === Routes ===

@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: TokenData = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Create a new conversation for the current user.
    
    - **title**: Optional conversation title (auto-generated if not provided)
    """
    try:
        conversation = await service.create_conversation(
            user_id=current_user.user_id,
            title=request.title
        )
        return ConversationResponse(**conversation)
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100, description="Maximum conversations to return"),
    current_user: TokenData = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Get all conversations for the current user, ordered by most recent.
    
    - **limit**: Maximum number of conversations to return (default: 50, max: 100)
    """
    try:
        conversations = await service.get_user_conversations(
            user_id=current_user.user_id,
            limit=limit
        )
        return [ConversationResponse(**conv) for conv in conversations]
    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationWithMessagesResponse)
async def get_conversation(
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Get a specific conversation with all its messages.
    
    - **conversation_id**: Conversation ID
    """
    try:
        # Get conversation metadata
        conversation = await service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user.user_id
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get messages
        messages = await service.get_conversation_messages(conversation_id)
        
        return ConversationWithMessagesResponse(
            conversation=ConversationResponse(**conversation),
            messages=[MessageResponse(**msg) for msg in messages]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: TokenData = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Update conversation title.
    
    - **conversation_id**: Conversation ID
    - **title**: New conversation title
    """
    try:
        success = await service.update_conversation_title(
            conversation_id=conversation_id,
            title=request.title,
            user_id=current_user.user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Return updated conversation
        conversation = await service.get_conversation(conversation_id, current_user.user_id)
        return ConversationResponse(**conversation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update conversation: {str(e)}")


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    req: Request,
    conversation_id: str,
    current_user: TokenData = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Delete a conversation and all its messages.
    
    - **conversation_id**: Conversation ID
    """
    try:
        success = await service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.user_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Invalidate cache for deleted conversation
        upstash_client = getattr(req.app.state, 'upstash_client', None)
        from app.services.conversation_cache import ConversationCache
        cache = ConversationCache(upstash_client)
        await cache.invalidate(conversation_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
