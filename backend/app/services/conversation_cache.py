"""
Conversation Cache Service for TaxIA

Manages Redis caching of conversation context to improve performance.
Stores notification content + recent messages with 1-hour TTL.

Cached context fields:
- recent_messages: Last 20 conversation messages
- notification_content: AEAT notification text (if any)
- last_rag_chunks: RAG chunks from previous turn (for follow-up optimization)
- last_rag_query: Query string used for last RAG search
- cached_at: ISO timestamp of cache write
"""
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConversationCache:
    """Service for caching conversation context in Redis."""
    
    def __init__(self, redis_client):
        """
        Initialize cache service.
        
        Args:
            redis_client: Upstash Redis async client (or None if disabled)
        """
        self.redis = redis_client
        self.ttl = 3600  # 1 hour in seconds
        self.enabled = redis_client is not None
    
    def _get_key(self, conversation_id: str) -> str:
        """Generate Redis key for conversation context."""
        return f"conversation:{conversation_id}:context"
    
    async def get_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation context from cache.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Cached context dict or None if not found/disabled
        """
        if not self.enabled:
            return None
        
        try:
            key = self._get_key(conversation_id)
            cached_data = await self.redis.get(key)
            
            if cached_data:
                logger.info("Cache HIT for conversation %s", conversation_id)
                # Parse JSON string to dict
                context = json.loads(cached_data)
                return context
            else:
                logger.info("Cache MISS for conversation %s", conversation_id)
                return None
                
        except Exception as e:
            logger.warning("Cache get error for %s: %s", conversation_id, e)
            return None
    
    async def set_context(
        self,
        conversation_id: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Save conversation context to cache with TTL.
        
        Args:
            conversation_id: Conversation ID
            context: Context dict to cache
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            key = self._get_key(conversation_id)
            
            # Add timestamp
            context["cached_at"] = datetime.now(timezone.utc).isoformat()
            
            # Serialize to JSON
            context_json = json.dumps(context, ensure_ascii=False)
            
            # Save with TTL (EX = seconds)
            await self.redis.set(key, context_json, ex=self.ttl)
            
            logger.info("Cache SET for conversation %s (TTL: %ds)", conversation_id, self.ttl)
            return True
            
        except Exception as e:
            logger.warning("Cache set error for %s: %s", conversation_id, e)
            return False
    
    async def refresh_ttl(self, conversation_id: str) -> bool:
        """
        Refresh TTL for cached conversation context.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            key = self._get_key(conversation_id)
            
            # Renew expiration
            result = await self.redis.expire(key, self.ttl)
            
            if result:
                logger.info("Cache TTL renewed for conversation %s", conversation_id)
                return True
            else:
                logger.debug(f"Cache key not found for TTL refresh: {conversation_id}")
                return False
                
        except Exception as e:
            logger.warning("Cache TTL refresh error for %s: %s", conversation_id, e)
            return False
    
    async def invalidate(self, conversation_id: str) -> bool:
        """
        Invalidate (delete) cached conversation context.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            key = self._get_key(conversation_id)
            
            # Delete key
            result = await self.redis.delete(key)
            
            if result:
                logger.info("Cache invalidated for conversation %s", conversation_id)
                return True
            else:
                logger.debug(f"Cache key not found for invalidation: {conversation_id}")
                return False
                
        except Exception as e:
            logger.warning("Cache invalidation error for %s: %s", conversation_id, e)
            return False
