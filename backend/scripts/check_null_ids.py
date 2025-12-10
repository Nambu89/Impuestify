"""
Check documents with NULL IDs in Turso.
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

async def check_null_ids():
    db = TursoClient(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
    await db.connect()
    
    print("=" * 60)
    print("Verificación de IDs NULL en documents")
    print("=" * 60)
    
    # Count NULL IDs
    result = await db.execute("SELECT COUNT(*) as count FROM documents WHERE id IS NULL")
    null_count = result.rows[0]['count']
    print(f"\n❌ Documentos con ID NULL: {null_count}")
    
    # Count valid IDs
    result = await db.execute("SELECT COUNT(*) as count FROM documents WHERE id IS NOT NULL")
    valid_count = result.rows[0]['count']
    print(f"✅ Documentos con ID válido: {valid_count}")
    
    # Show NULL documents
    if null_count > 0:
        print(f"\n📋 Documentos con ID NULL:")
        result = await db.execute("SELECT filename, title, document_type FROM documents WHERE id IS NULL LIMIT 10")
        for row in result.rows:
            print(f"  - {row['filename']} ({row['document_type']})")
    
    # Check orphaned chunks
    result = await db.execute("""
        SELECT COUNT(*) as count 
        FROM document_chunks 
        WHERE document_id NOT IN (SELECT id FROM documents WHERE id IS NOT NULL)
    """)
    orphaned = result.rows[0]['count']
    print(f"\n⚠️  Chunks huérfanos (sin documento válido): {orphaned}")
    
    await db.disconnect()
    print("\n" + "=" * 60)

asyncio.run(check_null_ids())
