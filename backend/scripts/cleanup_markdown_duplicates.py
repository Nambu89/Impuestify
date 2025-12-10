"""
Clean up duplicate tarifa plana documents and re-ingest.
"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

from app.database.turso_client import TursoClient

async def cleanup_and_reingest():
    db = TursoClient(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
    await db.connect()
    
    print("=" * 60)
    print("Cleanup and Re-ingestion")
    print("=" * 60)
    
    # Delete all tarifa plana documents
    print("\n🗑️  Deleting all tarifa_plana documents...")
    result = await db.execute("""
        SELECT id FROM documents WHERE filename LIKE '%tarifa_plana%'
    """)
    
    for row in result.rows:
        doc_id = row['id']
        if doc_id:
            await db.execute("DELETE FROM document_chunks WHERE document_id = ?", [doc_id])
            await db.execute("DELETE FROM documents WHERE id = ?", [doc_id])
    
    print(f"✅ Deleted {len(result.rows)} documents")
    
    # Also delete other markdown duplicates
    print("\n🗑️  Deleting other markdown duplicates...")
    result = await db.execute("""
        SELECT id, filename FROM documents 
        WHERE filename IN ('cuota_autonomos_2025_infoautonomos.md', 'ipsi_sage_completo.md')
    """)
    
    for row in result.rows:
        doc_id = row['id']
        if doc_id:
            await db.execute("DELETE FROM document_chunks WHERE document_id = ?", [doc_id])
            await db.execute("DELETE FROM documents WHERE id = ?", [doc_id])
    
    print(f"✅ Deleted {len(result.rows)} documents")
    
    await db.disconnect()
    
    print("\n" + "=" * 60)
    print("✅ Cleanup complete")
    print("=" * 60)
    print("\n🔄 Now run: python scripts/ingest_markdown_only.py")
    print("🔄 Then run: python scripts/rebuild_fts5.py")

asyncio.run(cleanup_and_reingest())
