"""
Semantic Window -- intelligent message selection for LLM context.

Instead of sending the last N messages to the LLM, selects the most
semantically relevant messages based on the current query.
Always includes the most recent messages for immediate context.
"""
import logging
import math
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticWindow:
    """Select the most relevant messages for LLM context.

    Parameters:
        max_messages: Maximum number of messages to return.
        recent_guaranteed: Number of most-recent messages that are always
            included regardless of similarity score.
    """

    def __init__(self, max_messages: int = 15, recent_guaranteed: int = 5):
        self.max_messages = max_messages
        self.recent_guaranteed = recent_guaranteed
        self._client: Optional[AsyncOpenAI] = None
        self._embedding_cache: Dict[str, List[float]] = {}

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def _get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Load all messages for a conversation from the database."""
        from app.database.turso_client import get_db_client
        db = await get_db_client()
        result = await db.execute(
            """SELECT id, role, content, created_at
               FROM messages
               WHERE conversation_id = ?
               ORDER BY created_at""",
            [conversation_id],
        )
        return [dict(row) for row in result.rows or []]

    async def _embed(self, text: str) -> List[float]:
        """Get embedding for a text string using text-embedding-3-large (256 dims)."""
        client = self._get_client()
        response = await client.embeddings.create(
            model="text-embedding-3-large",
            input=text[:8000],  # truncate to avoid token limits
            dimensions=256,  # smaller dims for fast similarity
        )
        return response.data[0].embedding

    async def _get_or_create_embedding(
        self, msg_id: str, content: str
    ) -> List[float]:
        """Get cached embedding or create a new one.

        Messages are immutable, so embeddings can be cached indefinitely
        for the lifetime of this instance.
        """
        if msg_id in self._embedding_cache:
            return self._embedding_cache[msg_id]
        embedding = await self._embed(content)
        self._embedding_cache[msg_id] = embedding
        return embedding

    async def select(
        self, conversation_id: str, current_query: str
    ) -> List[Dict[str, Any]]:
        """
        Select the most relevant messages for the current query.

        Returns up to max_messages messages:
        - Last recent_guaranteed messages always included
        - Remaining slots filled by most semantically similar messages
        - Result sorted chronologically
        """
        all_messages = await self._get_messages(conversation_id)

        if len(all_messages) <= self.max_messages:
            return all_messages

        # Always include the last N messages
        recent = all_messages[-self.recent_guaranteed:]
        candidates = all_messages[:-self.recent_guaranteed]

        # Embed the current query
        query_embedding = await self._embed(current_query)

        # Score each candidate by semantic similarity
        scored = []
        for msg in candidates:
            msg_embedding = await self._get_or_create_embedding(
                msg["id"], msg["content"]
            )
            score = cosine_similarity(query_embedding, msg_embedding)
            scored.append((score, msg))

        # Select top candidates to fill remaining slots
        scored.sort(key=lambda x: x[0], reverse=True)
        slots = self.max_messages - self.recent_guaranteed
        selected = [msg for _, msg in scored[:slots]]

        # Sort selected (non-recent) messages chronologically
        selected.sort(key=lambda m: m["created_at"])

        return selected + recent
