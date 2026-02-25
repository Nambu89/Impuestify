"""
Hybrid Retriever for TaxIA RAG Pipeline

Combines two search strategies with Reciprocal Rank Fusion (RRF):
1. Semantic search via Upstash Vector (cosine similarity on embeddings)
2. Keyword search via FTS5 (BM25) in Turso DB

Falls back to FTS5-only if Upstash Vector is unavailable.
"""
import struct
import logging
import asyncio
from typing import List, Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import upstash-vector
try:
    from upstash_vector import Index
    UPSTASH_VECTOR_AVAILABLE = True
except ImportError:
    UPSTASH_VECTOR_AVAILABLE = False
    logger.warning("upstash-vector not installed. Falling back to FTS5-only.")


class HybridRetriever:
    """
    Two-stage retriever with RRF fusion.

    Stage 1: Retrieve candidates from both FTS5 and Upstash Vector
    Stage 2: Fuse results using Reciprocal Rank Fusion (RRF, k=60)

    Args:
        db_client: TursoClient instance for FTS5 queries
        vector_url: Upstash Vector REST URL (optional, uses config)
        vector_token: Upstash Vector REST token (optional, uses config)
    """

    RRF_K = 60  # RRF constant (standard value)
    CANDIDATE_MULTIPLIER = 6  # Fetch N*k candidates from each source

    def __init__(
        self,
        db_client=None,
        vector_url: Optional[str] = None,
        vector_token: Optional[str] = None,
    ):
        self.db = db_client
        self._vector_index: Optional[Index] = None

        # Initialize Upstash Vector
        url = vector_url or settings.UPSTASH_VECTOR_RAG_URL
        token = vector_token or settings.UPSTASH_VECTOR_RAG_TOKEN

        if UPSTASH_VECTOR_AVAILABLE and url and token:
            try:
                self._vector_index = Index(url=url, token=token)
                logger.info("🔍 HybridRetriever initialized (FTS5 + Upstash Vector)")
            except Exception as e:
                logger.error(f"❌ Failed to init Upstash Vector: {e}")
        else:
            logger.info("🔍 HybridRetriever initialized (FTS5-only mode)")

    @property
    def has_vector_search(self) -> bool:
        return self._vector_index is not None

    # ============================================================
    # PUBLIC API
    # ============================================================

    async def search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        k: int = 5,
        territory_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: FTS5 + Vector → RRF fusion.

        Args:
            query: User's question text
            query_embedding: Pre-computed embedding vector (1536d)
            k: Number of final results to return
            territory_filter: Optional territory filter (e.g., "AEAT", "Bizkaia")

        Returns:
            List of dicts with: id, text, page, source, title, similarity, territory
        """
        candidates_k = k * self.CANDIDATE_MULTIPLIER

        # Run both searches in parallel
        if self.has_vector_search and query_embedding:
            fts_task = self._fts_search(query, k=candidates_k, territory=territory_filter)
            vector_task = self._vector_search(query_embedding, k=candidates_k, territory=territory_filter)

            fts_results, vector_results = await asyncio.gather(
                fts_task, vector_task, return_exceptions=True
            )

            # Handle exceptions gracefully
            if isinstance(fts_results, Exception):
                logger.warning(f"⚠️ FTS5 search failed: {fts_results}")
                fts_results = []
            if isinstance(vector_results, Exception):
                logger.warning(f"⚠️ Vector search failed: {vector_results}")
                vector_results = []

            # Fuse with RRF
            if fts_results and vector_results:
                fused = self._rrf_fusion(fts_results, vector_results, k=k)
                logger.info(
                    f"🔀 Hybrid: {len(fts_results)} FTS5 + {len(vector_results)} Vector → {len(fused)} fused"
                )
                return fused
            elif vector_results:
                return vector_results[:k]
            elif fts_results:
                return fts_results[:k]
            else:
                return []
        else:
            # Fallback: FTS5 only
            results = await self._fts_search(query, k=k, territory=territory_filter)
            logger.info(f"🔍 FTS5-only: {len(results)} results")
            return results

    # ============================================================
    # VECTOR SEARCH (Upstash)
    # ============================================================

    async def _vector_search(
        self,
        embedding: List[float],
        k: int = 30,
        territory: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query Upstash Vector for semantically similar chunks."""
        if not self._vector_index:
            return []

        try:
            # Build filter string for metadata
            filter_str = None
            if territory:
                filter_str = f"territory = '{territory}'"

            results = self._vector_index.query(
                vector=embedding,
                top_k=k,
                include_metadata=True,
                filter=filter_str,
            )

            chunks = []
            for r in results:
                meta = r.metadata or {}
                chunks.append({
                    "id": r.id,
                    "text": meta.get("content", ""),
                    "page": meta.get("page", 0),
                    "source": meta.get("source", ""),
                    "title": meta.get("title", ""),
                    "territory": meta.get("territory", ""),
                    "tax_type": meta.get("tax_type", ""),
                    "similarity": r.score,
                    "_search_type": "vector",
                })

            return chunks

        except Exception as e:
            logger.error(f"❌ Upstash Vector search error: {e}")
            return []

    # ============================================================
    # FTS5 SEARCH (Turso)
    # ============================================================

    async def _fts_search(
        self,
        query: str,
        k: int = 30,
        territory: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Full-text search using FTS5 (BM25) in Turso."""
        if not self.db:
            return []

        try:
            # Clean query for FTS5
            fts_query = self._clean_fts_query(query)

            if territory:
                result = await self.db.execute(
                    """
                    SELECT
                        dc.id, dc.content, dc.page_number,
                        d.filename, d.title, d.territory, d.tax_type,
                        rank
                    FROM chunks_fts
                    JOIN document_chunks dc ON dc.id = chunks_fts.chunk_id
                    JOIN documents d ON d.id = dc.document_id
                    WHERE chunks_fts MATCH ?
                      AND d.territory = ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    [fts_query, territory, k],
                )
            else:
                result = await self.db.execute(
                    """
                    SELECT
                        dc.id, dc.content, dc.page_number,
                        d.filename, d.title, d.territory, d.tax_type,
                        rank
                    FROM chunks_fts
                    JOIN document_chunks dc ON dc.id = chunks_fts.chunk_id
                    JOIN documents d ON d.id = dc.document_id
                    WHERE chunks_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    [fts_query, k],
                )

            chunks = []
            for row in result.rows:
                chunks.append({
                    "id": row["id"],
                    "text": row["content"],
                    "page": row["page_number"] or 0,
                    "source": row["filename"] or "",
                    "title": row["title"] or "",
                    "territory": row["territory"] or "",
                    "tax_type": row["tax_type"] or "",
                    "similarity": abs(row["rank"]) if row["rank"] else 0,
                    "_search_type": "fts5",
                })

            return chunks

        except Exception as e:
            logger.error(f"❌ FTS5 search error: {e}")
            # Try LIKE fallback
            return await self._like_fallback(query, k, territory)

    async def _like_fallback(
        self, query: str, k: int = 5, territory: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fallback to LIKE search if FTS5 fails."""
        if not self.db:
            return []

        try:
            words = query.split()[:3]
            conditions = " AND ".join([f"dc.content LIKE '%' || ? || '%'" for _ in words])

            if territory:
                sql = f"""
                    SELECT dc.id, dc.content, dc.page_number,
                           d.filename, d.title, d.territory, d.tax_type
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE {conditions} AND d.territory = ?
                    LIMIT ?
                """
                params = words + [territory, k]
            else:
                sql = f"""
                    SELECT dc.id, dc.content, dc.page_number,
                           d.filename, d.title, d.territory, d.tax_type
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE {conditions}
                    LIMIT ?
                """
                params = words + [k]

            result = await self.db.execute(sql, params)

            return [
                {
                    "id": row["id"],
                    "text": row["content"],
                    "page": row["page_number"] or 0,
                    "source": row["filename"] or "",
                    "title": row["title"] or "",
                    "territory": row["territory"] or "",
                    "tax_type": row["tax_type"] or "",
                    "similarity": 0.5,
                    "_search_type": "like",
                }
                for row in result.rows
            ]
        except Exception as e:
            logger.error(f"❌ LIKE fallback also failed: {e}")
            return []

    # ============================================================
    # RRF FUSION
    # ============================================================

    def _rrf_fusion(
        self,
        fts_results: List[Dict],
        vector_results: List[Dict],
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) to merge two ranked lists.

        Score = Σ  1 / (rank_i + K)

        where K=60 (standard) prevents overweighting top results.
        """
        scores: Dict[str, float] = {}
        chunks_by_id: Dict[str, Dict] = {}

        # Score FTS5 results
        for rank, chunk in enumerate(fts_results, start=1):
            chunk_id = chunk["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (rank + self.RRF_K)
            chunks_by_id[chunk_id] = chunk

        # Score Vector results
        for rank, chunk in enumerate(vector_results, start=1):
            chunk_id = chunk["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (rank + self.RRF_K)
            # Prefer vector result metadata (more complete)
            if chunk_id not in chunks_by_id:
                chunks_by_id[chunk_id] = chunk

        # Sort by fused score (descending)
        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)

        results = []
        for chunk_id in sorted_ids[:k]:
            chunk = chunks_by_id[chunk_id].copy()
            chunk["similarity"] = scores[chunk_id]
            chunk["_search_type"] = "hybrid"
            results.append(chunk)

        return results

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _clean_fts_query(query: str) -> str:
        """
        Clean a user query for FTS5 MATCH syntax.
        Removes special chars and joins words with spaces (implicit AND).
        """
        # Remove FTS5 special operators
        stop_words = {"OR", "AND", "NOT", "NEAR"}
        words = []
        for word in query.split():
            clean = "".join(c for c in word if c.isalnum())
            if clean and clean.upper() not in stop_words and len(clean) > 1:
                words.append(clean)
        return " ".join(words) if words else query


# ============================================================
# EMBEDDING GENERATION HELPER
# ============================================================

async def get_query_embedding(query: str) -> Optional[List[float]]:
    """
    Generate embedding for a search query using OpenAI.

    Returns:
        List of 1536 floats, or None if generation fails.
    """
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            model="text-embedding-3-large",
            input=query,
            dimensions=1536,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"⚠️ Failed to generate query embedding: {e}")
        return None
