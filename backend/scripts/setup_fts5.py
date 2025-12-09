"""
Script to create FTS5 (Full-Text Search) table for document chunks in Turso.

This enables fast text search without needing to generate embeddings for queries.
Uses SQLite's built-in FTS5 extension with BM25 ranking.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

async def setup_fts5():
    """Create FTS5 virtual table for document_chunks"""
    
    # Get Turso client
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ Error: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set")
        return
    
    db = TursoClient(turso_url, turso_token)
    
    await db.connect()
    print("✅ Connected to Turso")
    
    try:
        # Check if FTS5 table already exists
        check_sql = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='document_chunks_fts'
        """
        
        result = await db.execute(check_sql)
        
        if result.rows:
            print("⚠️  FTS5 table 'document_chunks_fts' already exists")
            print("   To rebuild, drop it first: DROP TABLE document_chunks_fts")
            return
        
        print("📝 Creating FTS5 virtual table...")
        
        # Create FTS5 virtual table
        # Note: FTS5 tables don't store data, they index existing data
        create_fts_sql = """
        CREATE VIRTUAL TABLE document_chunks_fts USING fts5(
            chunk_id UNINDEXED,
            content,
            content='document_chunks',
            content_rowid='rowid'
        )
        """
        
        await db.execute(create_fts_sql)
        print("✅ FTS5 table created")
        
        # Populate FTS5 table with existing data
        print("📥 Populating FTS5 table with existing chunks...")
        
        populate_sql = """
        INSERT INTO document_chunks_fts(chunk_id, content)
        SELECT id, content FROM document_chunks
        """
        
        await db.execute(populate_sql)
        print("✅ FTS5 table populated")
        
        # Count indexed chunks
        count_sql = "SELECT COUNT(*) as count FROM document_chunks_fts"
        result = await db.execute(count_sql)
        count = result.rows[0]['count'] if result.rows else 0
        
        print(f"✅ Indexed {count} chunks")
        
        # Test search
        print("\n🧪 Testing FTS5 search...")
        test_sql = """
        SELECT chunk_id, snippet(document_chunks_fts, 1, '<b>', '</b>', '...', 32) as snippet
        FROM document_chunks_fts 
        WHERE document_chunks_fts MATCH 'IRPF OR impuesto'
        ORDER BY rank
        LIMIT 3
        """
        
        result = await db.execute(test_sql)
        
        print(f"Found {len(result.rows)} results")
        for i, row in enumerate(result.rows[:3], 1):
            print(f"\n{i}. Chunk ID: {row['chunk_id']}")
            print(f"   Snippet: {row['snippet'][:150]}...")
        
        print("\n✅ FTS5 setup complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        await db.disconnect()
        print("👋 Disconnected from Turso")


if __name__ == "__main__":
    asyncio.run(setup_fts5())
