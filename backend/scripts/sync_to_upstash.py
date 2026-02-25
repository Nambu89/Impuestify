"""
Sync Turso embeddings → Upstash Vector

Reads all chunks + embeddings from Turso DB and upserts them into
Upstash Vector for fast semantic search in the RAG pipeline.

Usage:
    python backend/scripts/sync_to_upstash.py [--batch-size 100] [--namespace rag]
"""
import sys
import struct
import asyncio
import argparse
import logging
from pathlib import Path

# ── Path setup ──
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
project_root = backend_dir.parent

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import TursoClient directly (bypass pydantic email_validator issue)
import importlib.util
_turso_spec = importlib.util.spec_from_file_location(
    "turso_client",
    backend_dir / "app" / "database" / "turso_client.py",
)
_turso_mod = importlib.util.module_from_spec(_turso_spec)
_turso_spec.loader.exec_module(_turso_mod)
TursoClient = _turso_mod.TursoClient

try:
    from upstash_vector import Index, Vector
    print("✅ upstash_vector imported successfully")
except ImportError:
    print("❌ upstash_vector not installed. Run: pip install upstash-vector")
    sys.exit(1)

import os

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def blob_to_floats(blob: bytes) -> list:
    """Convert packed float32 BLOB back to list of floats."""
    n = len(blob) // 4  # 4 bytes per float32
    return list(struct.unpack(f"{n}f", blob))


async def sync(batch_size: int = 100, namespace: str = "rag"):
    """Main sync pipeline."""
    # ── Validate env vars ──
    rag_url = os.getenv("UPSTASH_VECTOR_RAG_URL")
    rag_token = os.getenv("UPSTASH_VECTOR_RAG_TOKEN")

    if not rag_url or not rag_token:
        print("❌ UPSTASH_VECTOR_RAG_URL and UPSTASH_VECTOR_RAG_TOKEN must be set in .env")
        sys.exit(1)

    # ── Connect to Turso ──
    print("📦 Connecting to Turso DB...")
    db = TursoClient()
    await db.connect()
    print("✅ Connected to Turso")

    # ── Connect to Upstash Vector ──
    print(f"🔗 Connecting to Upstash Vector...")
    index = Index(url=rag_url, token=rag_token)

    # Check current state
    try:
        info = index.info()
        print(f"   Current vectors in index: {info.vector_count}")
        print(f"   Dimensions: {info.dimension}")
        print(f"   Similarity: {info.similarity_function}")
    except Exception as e:
        print(f"⚠️ Could not get index info: {e}")

    # ── Count chunks with embeddings ──
    count_result = await db.execute("""
        SELECT COUNT(*) as total
        FROM document_chunks dc
        JOIN embeddings e ON e.chunk_id = dc.id
    """)
    total_chunks = count_result.rows[0]["total"] if count_result.rows else 0
    print(f"\n📊 Total chunks with embeddings: {total_chunks}")

    if total_chunks == 0:
        print("❌ No chunks with embeddings found in Turso. Run ingestion first.")
        return

    # ── Fetch all chunks with embeddings and document metadata ──
    print(f"📥 Fetching chunks in batches of {batch_size}...")
    
    offset = 0
    synced = 0
    errors = 0

    while offset < total_chunks:
        result = await db.execute(
            """
            SELECT 
                dc.id as chunk_id,
                dc.content,
                dc.page_number,
                dc.chunk_index,
                d.filename as source,
                d.title,
                d.source as territory,
                d.document_type as tax_type,
                d.year,
                e.embedding
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            JOIN embeddings e ON e.chunk_id = dc.id
            ORDER BY dc.id
            LIMIT ? OFFSET ?
            """,
            [batch_size, offset],
        )

        if not result.rows:
            break

        # ── Prepare vectors for upsert ──
        vectors = []
        for row in result.rows:
            try:
                embedding_blob = row["embedding"]
                if embedding_blob is None:
                    errors += 1
                    continue

                # Convert BLOB to float list
                embedding_floats = blob_to_floats(embedding_blob)

                vectors.append(
                    Vector(
                        id=row["chunk_id"],
                        vector=embedding_floats,
                        metadata={
                            "content": row["content"][:3800] if row["content"] else "",  # Upstash metadata limit
                            "page": row["page_number"] or 0,
                            "source": row["source"] or "",
                            "title": row["title"] or "",
                            "territory": row["territory"] or "",
                            "tax_type": row["tax_type"] or "",
                            "year": str(row["year"]) if row["year"] else "",
                            "chunk_index": row["chunk_index"] or 0,
                        },
                    )
                )
            except Exception as e:
                errors += 1
                logger.warning(f"⚠️ Error processing chunk {row.get('chunk_id', '?')}: {e}")

        # ── Upsert batch to Upstash ──
        if vectors:
            try:
                index.upsert(vectors=vectors)
                synced += len(vectors)
                pct = (synced / total_chunks) * 100
                print(f"   ✅ Synced {synced}/{total_chunks} ({pct:.1f}%) — batch of {len(vectors)}")
            except Exception as e:
                errors += len(vectors)
                print(f"   ❌ Upsert error: {e}")

        offset += batch_size

    # ── Final report ──
    print(f"\n{'='*50}")
    print(f"📊 Sync Complete!")
    print(f"   ✅ Synced: {synced}")
    print(f"   ❌ Errors: {errors}")
    print(f"   📦 Total in DB: {total_chunks}")

    # Verify
    try:
        info = index.info()
        print(f"   🔢 Vectors in Upstash: {info.vector_count}")
    except Exception as e:
        print(f"   ⚠️ Could not verify: {e}")

    print(f"\n🧪 Testing search...")
    try:
        # Generate a test query embedding
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input="tramos del IRPF estatal",
            dimensions=1536,
        )
        test_embedding = response.data[0].embedding

        results = index.query(
            vector=test_embedding,
            top_k=3,
            include_metadata=True,
        )
        print(f"   ✅ Found {len(results)} results for 'tramos del IRPF estatal':")
        for i, r in enumerate(results, 1):
            source = r.metadata.get("source", "?") if r.metadata else "?"
            score = r.score
            print(f"      {i}. {source} (score: {score:.4f})")
    except Exception as e:
        print(f"   ⚠️ Test search failed: {e}")

    if hasattr(db, 'close'):
        await db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Turso embeddings to Upstash Vector")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for upsert")
    parser.add_argument("--namespace", type=str, default="rag", help="Namespace in Upstash Vector")
    args = parser.parse_args()

    asyncio.run(sync(batch_size=args.batch_size, namespace=args.namespace))
