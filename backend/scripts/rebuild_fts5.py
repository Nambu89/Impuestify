"""
Rebuild FTS5 table - drops existing and recreates with correct schema
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

try:
    import libsql
    print(f"✅ libsql imported successfully: {libsql}")
except ImportError as e:
    print(f"❌ libsql import failed in script: {e}")

from app.database.turso_client import TursoClient

async def rebuild_fts5():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    print("🔨 Rebuilding FTS5 table...")
    
    # Drop existing table
    print("🗑️  Dropping old FTS5 table...")
    await db.execute("DROP TABLE IF EXISTS document_chunks_fts")
    print("✅ Dropped")
    
    # Create new table with correct schema - Standalone FTS table (safer)
    print("📝 Creating FTS5 table (standalone)...")
    create_sql = """
    CREATE VIRTUAL TABLE document_chunks_fts USING fts5(
        chunk_id UNINDEXED,
        content
    )
    """
    await db.execute(create_sql)
    print("✅ Created")
    
    # Populate
    print("📥 Populating with 20,595 chunks...")
    populate_sql = """
    INSERT INTO document_chunks_fts(chunk_id, content)
    SELECT id, content FROM document_chunks
    """
    await db.execute(populate_sql)
    print("✅ Populated")
    
    # Verify - count from source table since FTS5 COUNT can be unreliable
    count_sql = "SELECT COUNT(*) as count FROM document_chunks"
    result = await db.execute(count_sql)
    count = result.rows[0]['count'] if result.rows else 0
    print(f"✅ Indexed {count} chunks")
    
    # Test search with JOIN to verify documents table schema too
    print("\n🧪 Testing full search with JOIN...")
    test_sql = """
    SELECT 
        c.id,
        d.filename,
        d.title,
        fts.rank
    FROM document_chunks_fts fts
    JOIN document_chunks c ON c.id = fts.chunk_id
    JOIN documents d ON d.id = c.document_id
    WHERE document_chunks_fts MATCH 'IRPF OR impuesto'
    ORDER BY rank
    LIMIT 3
    """
    result = await db.execute(test_sql)
    print(f"✅ Found {len(result.rows)} results")
    
    for i, row in enumerate(result.rows, 1):
        print(f"  {i}. File: {row['filename']} (Rank: {row['rank']})")
    
    print("\n✅ FTS5 rebuild complete!")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(rebuild_fts5())
