"""
Semantic Cache for TaxIA

Uses Upstash Vector to cache AI responses for semantically similar questions.
Reduces OpenAI API costs by ~30-50% by returning cached responses.

Features:
- Similarity threshold: 0.93
- Skip personal progress queries
- Intelligent vector search with Upstash Vector
"""
import os
import logging
import hashlib
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import time

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import upstash-vector
try:
    from upstash_vector import Index
    UPSTASH_VECTOR_AVAILABLE = True
except ImportError:
    UPSTASH_VECTOR_AVAILABLE = False
    logger.warning("upstash-vector not installed. Semantic cache disabled.")


@dataclass
class CacheResult:
    """Result of cache lookup."""
    hit: bool
    response: Optional[str] = None
    similarity: float = 0.0
    query_id: Optional[str] = None
    latency_ms: float = 0.0


class SemanticCache:
    """
    Semantic-based cache for AI responses using Upstash Vector.
    
    Returns cached responses for queries with similarity >= threshold.
    Reduces OpenAI API costs by avoiding duplicate/similar questions.
    """
    
    SIMILARITY_THRESHOLD = 0.93
    NAMESPACE = "taxia_cache"
    
    # Patterns that indicate personal queries (should NOT be cached)
    PERSONAL_QUERY_PATTERNS = [
        "mi ", "mis ", "tengo", "gano", "cobro",
        "mi declaración", "mi situación", "mi caso",
        "cuánto debo", "cuánto pago", "mi nómina"
    ]
    
    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        enabled: bool = True,
        threshold: float = None
    ):
        """
        Initialize Semantic Cache.
        
        Args:
            url: Upstash Vector REST URL
            token: Upstash Vector REST token
            enabled: Whether caching is enabled
            threshold: Similarity threshold (0.0-1.0)
        """
        from app.config import settings
        
        self.url = url or settings.UPSTASH_VECTOR_REST_URL
        self.token = token or settings.UPSTASH_VECTOR_REST_TOKEN
        self.threshold = threshold if threshold is not None else settings.SEMANTIC_CACHE_THRESHOLD
        
        # Strict enabled check: config enabled + library available + credentials present
        self.enabled = (
            enabled 
            and settings.ENABLE_SEMANTIC_CACHE 
            and UPSTASH_VECTOR_AVAILABLE 
            and bool(self.url) 
            and bool(self.token)
        )
        
        self._index: Optional[Index] = None
        
        if self.enabled:
            try:
                self._index = Index(url=self.url, token=self.token)
                logger.info("🧠 Semantic Cache enabled (Upstash Vector)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Upstash Vector: {e}")
                self.enabled = False
        else:
            if not UPSTASH_VECTOR_AVAILABLE:
                 logger.warning("⚠️ Semantic Cache disabled (library not installed)")
            elif not (self.url and self.token):
                 logger.warning("⚠️ Semantic Cache disabled (UPSTASH_VECTOR_REST_URL/TOKEN missing)")
            elif not settings.ENABLE_SEMANTIC_CACHE:
                 logger.info("⚠️ Semantic Cache disabled (ENABLE_SEMANTIC_CACHE=False)")
    
    def _is_personal_query(self, query: str) -> bool:
        """Check if query is personal and should not be cached."""
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in self.PERSONAL_QUERY_PATTERNS)
    
    def _generate_query_id(self, query: str) -> str:
        """Generate unique ID for a query."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    async def get_similar(self, query: str, embedding: Optional[list] = None) -> CacheResult:
        """
        Find cached response for similar query.
        
        Args:
            query: User's question
            embedding: Pre-computed embedding (optional)
            
        Returns:
            CacheResult with cached response if found
        """
        if not self.enabled:
            return CacheResult(hit=False)
        
        # Skip personal queries
        if self._is_personal_query(query):
            logger.debug("⏭️ Skipping cache for personal query")
            return CacheResult(hit=False)
        
        start_time = datetime.now()
        
        try:
            # Query by text (Upstash Vector will compute embedding ONLY if index is configured with a model)
            # If not configured, we must catch the error to prevent 500s
            try:
                results = self._index.query(
                    data=query,
                    top_k=1,
                    include_metadata=True
                )
            except Exception as query_error:
                error_msg = str(query_error)
                if "embedding" in error_msg.lower() and "not allowed" in error_msg.lower():
                    logger.warning("⚠️ Semantic Cache: Upstash index not configured for automatic embeddings.")
                    # In future: implement local OpenAI embedding generation here
                    return CacheResult(hit=False, latency_ms=(datetime.now() - start_time).total_seconds() * 1000)
                raise query_error
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if results and len(results) > 0:
                top_result = results[0]
                similarity = top_result.score
                
                if similarity >= self.threshold:
                    cached_response = top_result.metadata.get("response", "")
                    logger.info(f"💾 Cache HIT (similarity={similarity:.3f}, latency={latency_ms:.0f}ms)")
                    return CacheResult(
                        hit=True,
                        response=cached_response,
                        similarity=similarity,
                        query_id=top_result.id,
                        latency_ms=latency_ms
                    )
                else:
                    logger.debug(f"📭 Cache MISS (similarity={similarity:.3f} < threshold={self.threshold})")
            
            return CacheResult(hit=False, latency_ms=latency_ms)
            
        except Exception as e:
            logger.error(f"⚠️ Semantic cache lookup error: {e}")
            return CacheResult(hit=False)
    
    async def store(self, query: str, response: str):
        """
        Store query-response pair in vector cache.
        
        Args:
            query: User's question
            response: AI response to cache
        """
        if not self.enabled:
            return
        
        # Skip personal queries
        if self._is_personal_query(query):
            return
        
        try:
            query_id = self._generate_query_id(query)
            
            self._index.upsert(
                vectors=[{
                    "id": query_id,
                    "data": query,
                    "metadata": {
                        "query": query,
                        "response": response,
                        "timestamp": datetime.now().isoformat()
                    }
                }]
            )
            
            logger.debug(f"💾 Cached response for query: {query[:50]}...")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to cache response: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            info = self._index.info()
            return {
                "enabled": True,
                "vector_count": info.vector_count,
                "dimension": info.dimension,
                "threshold": self.threshold
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}


# Global instance
_semantic_cache: Optional[SemanticCache] = None


def get_semantic_cache() -> SemanticCache:
    """Get global Semantic Cache instance."""
    global _semantic_cache
    if _semantic_cache is None:
        from app.config import settings
        _semantic_cache = SemanticCache(
            url=getattr(settings, 'UPSTASH_VECTOR_REST_URL', None),
            token=getattr(settings, 'UPSTASH_VECTOR_REST_TOKEN', None),
            enabled=getattr(settings, 'ENABLE_SEMANTIC_CACHE', True),
            threshold=getattr(settings, 'SEMANTIC_CACHE_THRESHOLD', 0.93)
        )
    return _semantic_cache
