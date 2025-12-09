"""
Conversation Service for TaxIA

Manages chat conversations and message history in Turso database.
Provides Claude/ChatGPT-style persistent conversations per user.
"""
import uuid
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.database.turso_client import TursoClient

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for managing chat conversations and messages."""
    
    def __init__(self, db: TursoClient):
        self.db = db
    
    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation for a user.
        
        Args:
            user_id: User ID
            title: Optional conversation title (auto-generated if None)
            
        Returns:
            Created conversation dict
        """
        conversation_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        if not title:
            title = f"Nueva conversación"
        
        sql = """
        INSERT INTO conversations (id, user_id, title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
        
        await self.db.execute(sql, [conversation_id, user_id, title, now, now])
        
        logger.info(f"Created conversation {conversation_id} for user {user_id}")
        
        return {
            "id": conversation_id,
            "user_id": user_id,
            "title": title,
            "created_at": now,
            "updated_at": now
        }
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user, ordered by most recent.
        
        Args:
            user_id: User ID
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dicts
        """
        sql = """
        SELECT id, user_id, title, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """
        
        result = await self.db.execute(sql, [user_id, limit])
        
        return [dict(row) for row in result.rows]
    
    async def get_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific conversation.
        
        Args:
            conversation_id: Conversation ID
            user_id: Optional user ID for authorization check
            
        Returns:
            Conversation dict or None if not found
        """
        if user_id:
            sql = """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE id = ? AND user_id = ?
            """
            result = await self.db.execute(sql, [conversation_id, user_id])
        else:
            sql = """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversations
            WHERE id = ?
            """
            result = await self.db.execute(sql, [conversation_id])
        
        if result.rows:
            return dict(result.rows[0])
        return None
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation, ordered chronologically.
        
        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to return (most recent)
            
        Returns:
            List of message dicts with metadata parsed
        """
        sql = """
        SELECT id, conversation_id, role, content, metadata, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
        LIMIT ?
        """
        
        result = await self.db.execute(sql, [conversation_id, limit])
        
        messages = []
        for row in result.rows:
            msg = dict(row)
            # Parse JSON metadata if present
            if msg.get('metadata'):
                try:
                    msg['metadata'] = json.loads(msg['metadata'])
                except json.JSONDecodeError:
                    msg['metadata'] = {}
            else:
                msg['metadata'] = {}
            messages.append(msg)
        
        return messages
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: Message role ('user' | 'assistant' | 'system')
            content: Message content
            metadata: Optional metadata (sources, notification_id, etc.)
            
        Returns:
            Created message dict
        """
        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Serialize metadata to JSON
        metadata_json = json.dumps(metadata) if metadata else None
        
        sql = """
        INSERT INTO messages (id, conversation_id, role, content, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        await self.db.execute(sql, [
            message_id,
            conversation_id,
            role,
            content,
            metadata_json,
            now
        ])
        
        # Update conversation's updated_at timestamp
        await self.db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            [now, conversation_id]
        )
        
        logger.info(f"Added {role} message to conversation {conversation_id}")
        
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": now
        }
    
    async def add_message_sources(
        self,
        message_id: str,
        sources: List[Dict[str, Any]]
    ) -> None:
        """
        Link source chunks to a message.
        
        Args:
            message_id: Message ID
            sources: List of source dicts with chunk_id, relevance_score, rank
        """
        if not sources:
            return
        
        sql = """
        INSERT INTO message_sources (id, message_id, chunk_id, relevance_score, rank)
        VALUES (?, ?, ?, ?, ?)
        """
        
        params_list = []
        for idx, source in enumerate(sources):
            source_id = str(uuid.uuid4())
            params_list.append([
                source_id,
                message_id,
                source.get('id'),  # chunk_id
                source.get('score'),
                idx
            ])
        
        await self.db.execute_many(sql, params_list)
        logger.info(f"Added {len(sources)} sources to message {message_id}")
    
    async def update_conversation_title(
        self,
        conversation_id: str,
        title: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Update conversation title.
        
        Args:
            conversation_id: Conversation ID
            title: New title
            user_id: Optional user ID for authorization
            
        Returns:
            True if updated, False if not found
        """
        now = datetime.utcnow().isoformat()
        
        if user_id:
            sql = """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
            """
            result = await self.db.execute(sql, [title, now, conversation_id, user_id])
        else:
            sql = """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
            """
            result = await self.db.execute(sql, [title, now, conversation_id])
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Updated conversation {conversation_id} title to: {title}")
        
        return success
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Delete a conversation and all its messages (cascade).
        
        Args:
            conversation_id: Conversation ID
            user_id: Optional user ID for authorization
            
        Returns:
            True if deleted, False if not found
        """
        if user_id:
            sql = "DELETE FROM conversations WHERE id = ? AND user_id = ?"
            result = await self.db.execute(sql, [conversation_id, user_id])
        else:
            sql = "DELETE FROM conversations WHERE id = ?"
            result = await self.db.execute(sql, [conversation_id])
        
        success = result.rowcount > 0
        if success:
            logger.info(f"Deleted conversation {conversation_id}")
        
        return success
    
    async def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent messages formatted for LLM context.
        
        Args:
            conversation_id: Conversation ID
            limit: Number of recent messages to retrieve
            
        Returns:
            List of message dicts with 'role', 'content', and 'metadata' keys
        """
        messages = await self.get_conversation_messages(conversation_id, limit=limit)
        
        # Return full message dict including metadata
        return messages
