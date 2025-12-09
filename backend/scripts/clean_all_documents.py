"""
Clean ALL document data from database.

WARNING: This will delete:
- All documents
- All document chunks
- All embeddings
- FTS5 index

Usage:
    python scripts/clean_all_documents.py --confirm
"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

async def clean_all():
    print("=" * 60)
    print("⚠️  DATABASE CLEANUP - DELETING ALL DOCUMENTS")
    print("=" * 60)
    print()
    print("This will delete:")
    print("  - All documents")
    print("  - All document chunks")
    print("  - All embeddings")
    print("  - FTS5 search index")
    print()
    
    # Safety check
    if len(sys.argv) < 2 or sys.argv[1] != "--confirm":
        print("❌ Safety check failed!")
        print()
        print("To proceed, run:")
        print("    python scripts/clean_all_documents.py --confirm")
        return
    
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    try:
        # Get count before deletion
        doc_count = await db.execute("SELECT COUNT(*) as cnt FROM documents")
        chunk_count = await db.execute("SELECT COUNT(*) as cnt FROM document_chunks")
        emb_count = await db.execute("SELECT COUNT(*) as cnt FROM embeddings")
        
        print(f"Current database state:")
        print(f"  📄 Documents: {doc_count.rows[0]['cnt']}")
        print(f"  📦 Chunks: {chunk_count.rows[0]['cnt']}")
        print(f"  🧠 Embeddings: {emb_count.rows[0]['cnt']}")
        print()
        
        # Delete in correct order (foreign key constraints)
        print("🗑️  Deleting message_sources...")
        await db.execute("DELETE FROM message_sources")
        
        print("🗑️  Deleting embeddings...")
        await db.execute("DELETE FROM embeddings")
        
        print("🗑️  Deleting document_chunks...")
        await db.execute("DELETE FROM document_chunks")
        
        print("🗑️  Deleting documents...")
        await db.execute("DELETE FROM documents")
        
        # Drop and recreate FTS5
        print("🗑️  Dropping FTS5 table...")
        await db.execute("DROP TABLE IF EXISTS document_chunks_fts")
        
        print("📝 Creating new FTS5 table...")
        await db.execute("""
            CREATE VIRTUAL TABLE document_chunks_fts USING fts5(
                chunk_id UNINDEXED,
                content
            )
        """)
        
        print()
        print("=" * 60)
        print("✅ DATABASE CLEANED SUCCESSFULLY")
        print("=" * 60)
        print()
        print("All document-related data has been deleted.")
        print("You can now run:")
        print("  python scripts/extract_pdfs_v2.py")
        
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        raise
    finally:
        await db.disconnect()

if __name__ == "__main__":
    asyncio.run(clean_all())
