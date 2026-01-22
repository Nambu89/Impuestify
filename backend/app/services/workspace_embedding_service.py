"""
Workspace Embedding Service for TaxIA

Generates and manages embeddings for workspace documents using OpenAI Ada 3 Large.
Enables semantic search within user workspaces.
"""
import logging
import hashlib
import uuid
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)

# OpenAI client
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("openai package not installed")


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    success: bool
    embedding: Optional[List[float]] = None
    dimensions: int = 0
    model: str = ""
    error: Optional[str] = None


@dataclass
class SearchResult:
    """Result of semantic search."""
    file_id: str
    filename: str
    chunk_text: str
    similarity: float
    metadata: Dict[str, Any]


class WorkspaceEmbeddingService:
    """
    Service for generating and searching embeddings in workspaces.

    Uses OpenAI text-embedding-3-large for high-quality embeddings.
    Stores embeddings in Turso database for persistence.
    """

    # OpenAI embedding model
    EMBEDDING_MODEL = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS = 3072  # Ada 3 Large dimensions

    # Chunking parameters
    CHUNK_SIZE = 1000  # characters per chunk
    CHUNK_OVERLAP = 200  # overlap between chunks

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key (defaults to settings)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client: Optional[AsyncOpenAI] = None

        if not OPENAI_AVAILABLE:
            logger.error("OpenAI package not available")
        elif not self.api_key:
            logger.warning("OPENAI_API_KEY not configured")

    @property
    def client(self) -> AsyncOpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text using OpenAI Ada 3 Large.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with vector
        """
        if not OPENAI_AVAILABLE or not self.api_key:
            return EmbeddingResult(
                success=False,
                error="OpenAI not configured"
            )

        try:
            # Truncate text if too long (model limit is ~8191 tokens)
            max_chars = 30000  # Conservative limit
            if len(text) > max_chars:
                text = text[:max_chars]
                logger.warning(f"Text truncated to {max_chars} characters")

            response = await self.client.embeddings.create(
                model=self.EMBEDDING_MODEL,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding

            return EmbeddingResult(
                success=True,
                embedding=embedding,
                dimensions=len(embedding),
                model=self.EMBEDDING_MODEL
            )

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return EmbeddingResult(
                success=False,
                error=str(e)
            )

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks for embedding.

        Args:
            text: Full text to chunk

        Returns:
            List of chunk dicts with text and metadata
        """
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.CHUNK_SIZE

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within last 100 chars
                for punct in ['. ', '.\n', '? ', '!\n']:
                    last_punct = text[start:end].rfind(punct)
                    if last_punct > self.CHUNK_SIZE - 150:
                        end = start + last_punct + len(punct)
                        break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'chunk_index': chunk_index,
                    'start_char': start,
                    'end_char': end,
                    'char_count': len(chunk_text)
                })
                chunk_index += 1

            # Move start with overlap
            start = end - self.CHUNK_OVERLAP if end < len(text) else end

        return chunks

    async def embed_workspace_file(
        self,
        db,
        workspace_id: str,
        file_id: str,
        text: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Generate and store embeddings for a workspace file.

        Args:
            db: Database client
            workspace_id: Workspace ID
            file_id: File ID
            text: Extracted text content
            filename: Original filename

        Returns:
            Dict with embedding stats
        """
        try:
            # Chunk the text
            chunks = self.chunk_text(text)
            logger.info(f"Processing {len(chunks)} chunks for {filename}")

            successful = 0
            failed = 0

            for chunk in chunks:
                # Generate embedding
                result = await self.generate_embedding(chunk['text'])

                if not result.success:
                    failed += 1
                    continue

                # Store in database
                embedding_id = str(uuid.uuid4())

                # Convert embedding to bytes for BLOB storage
                import struct
                embedding_blob = struct.pack(f'{len(result.embedding)}f', *result.embedding)

                await db.execute(
                    """
                    INSERT INTO workspace_file_embeddings (
                        id, workspace_id, file_id, chunk_index,
                        chunk_text, embedding, model_name, dimensions,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    [
                        embedding_id,
                        workspace_id,
                        file_id,
                        chunk['chunk_index'],
                        chunk['text'][:2000],  # Store truncated for reference
                        embedding_blob,
                        result.model,
                        result.dimensions
                    ]
                )

                successful += 1

            logger.info(f"Embedded {successful}/{len(chunks)} chunks for {filename}")

            return {
                'success': True,
                'total_chunks': len(chunks),
                'successful': successful,
                'failed': failed,
                'model': self.EMBEDDING_MODEL
            }

        except Exception as e:
            logger.error(f"Failed to embed file {filename}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def search_workspace(
        self,
        db,
        workspace_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Semantic search within a workspace.

        Args:
            db: Database client
            workspace_id: Workspace to search
            query: Search query
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score

        Returns:
            List of SearchResult ordered by similarity
        """
        try:
            # Generate query embedding
            query_result = await self.generate_embedding(query)

            if not query_result.success:
                logger.error(f"Failed to embed query: {query_result.error}")
                return []

            # Get all embeddings for workspace
            result = await db.execute(
                """
                SELECT
                    e.id,
                    e.file_id,
                    e.chunk_text,
                    e.embedding,
                    f.filename
                FROM workspace_file_embeddings e
                JOIN workspace_files f ON e.file_id = f.id
                WHERE e.workspace_id = ?
                """,
                [workspace_id]
            )

            if not result.rows:
                return []

            # Calculate similarities
            import struct
            results = []

            for row in result.rows:
                # Decode embedding from BLOB
                embedding_blob = row['embedding']
                num_floats = len(embedding_blob) // 4
                stored_embedding = list(struct.unpack(f'{num_floats}f', embedding_blob))

                # Calculate cosine similarity
                similarity = self._cosine_similarity(
                    query_result.embedding,
                    stored_embedding
                )

                if similarity >= similarity_threshold:
                    results.append(SearchResult(
                        file_id=row['file_id'],
                        filename=row['filename'],
                        chunk_text=row['chunk_text'],
                        similarity=similarity,
                        metadata={'embedding_id': row['id']}
                    ))

            # Sort by similarity and limit
            results.sort(key=lambda x: x.similarity, reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.error(f"Workspace search failed: {e}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def delete_file_embeddings(self, db, file_id: str) -> bool:
        """
        Delete all embeddings for a file.

        Args:
            db: Database client
            file_id: File ID to delete embeddings for

        Returns:
            True if successful
        """
        try:
            await db.execute(
                "DELETE FROM workspace_file_embeddings WHERE file_id = ?",
                [file_id]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete embeddings for file {file_id}: {e}")
            return False

    async def get_workspace_stats(self, db, workspace_id: str) -> Dict[str, Any]:
        """
        Get embedding statistics for a workspace.

        Args:
            db: Database client
            workspace_id: Workspace ID

        Returns:
            Dict with stats
        """
        try:
            result = await db.execute(
                """
                SELECT
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT file_id) as files_embedded,
                    MAX(created_at) as last_updated
                FROM workspace_file_embeddings
                WHERE workspace_id = ?
                """,
                [workspace_id]
            )

            if result.rows:
                return {
                    'total_embeddings': result.rows[0]['total_embeddings'],
                    'files_embedded': result.rows[0]['files_embedded'],
                    'last_updated': result.rows[0]['last_updated'],
                    'model': self.EMBEDDING_MODEL,
                    'dimensions': self.EMBEDDING_DIMENSIONS
                }

            return {'total_embeddings': 0, 'files_embedded': 0}

        except Exception as e:
            logger.error(f"Failed to get workspace stats: {e}")
            return {'error': str(e)}


# Global instance
_embedding_service: Optional[WorkspaceEmbeddingService] = None


def get_workspace_embedding_service() -> WorkspaceEmbeddingService:
    """Get global workspace embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = WorkspaceEmbeddingService()
    return _embedding_service
