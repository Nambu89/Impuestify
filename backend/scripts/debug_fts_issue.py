"""
Check why tarifa plana chunks are not in FTS5.
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

async def debug_fts():
    db = TursoClient(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
    await db.connect()
    
    print("=" * 60)
    print("Debug FTS5 - Tarifa Plana")
    print("=" * 60)
    
    # Get all tarifa plana documents
    result = await db.execute("""
        SELECT id, filename, title, document_type 
        FROM documents 
        WHERE filename LIKE '%tarifa_plana%'
        ORDER BY id
    """)
    
    print(f"\n📋 Documentos tarifa_plana: {len(result.rows)}")
    for row in result.rows:
        doc_id = row['id']
        print(f"\n  Document ID: {doc_id}")
        print(f"  Filename: {row['filename']}")
        
        # Check chunks for this document
        chunk_result = await db.execute("""
            SELECT id, content 
            FROM document_chunks 
            WHERE document_id = ?
            LIMIT 2
        """, [doc_id])
        
        print(f"  Chunks: {len(chunk_result.rows)}")
        
        if chunk_result.rows:
            # Check if first chunk is in FTS5
            chunk_id = chunk_result.rows[0]['id']
            print(f"  First chunk ID: {chunk_id}")
            
            fts_result = await db.execute("""
                SELECT chunk_id 
                FROM document_chunks_fts 
                WHERE chunk_id = ?
            """, [chunk_id])
            
            print(f"  First chunk in FTS5: {len(fts_result.rows) > 0}")
            
            # Show chunk content preview
            print(f"  Content preview: {chunk_result.rows[0]['content'][:100]}...")
    
    # Check total FTS5 count
    result = await db.execute("SELECT COUNT(*) as count FROM document_chunks_fts")
    fts_total = result.rows[0]['count']
    print(f"\n📊 Total chunks en FTS5: {fts_total}")
    
    # Check total document_chunks count
    result = await db.execute("SELECT COUNT(*) as count FROM document_chunks")
    chunks_total = result.rows[0]['count']
    print(f"📊 Total chunks en document_chunks: {chunks_total}")
    
    await db.disconnect()
    print("\n" + "=" * 60)

asyncio.run(debug_fts())
