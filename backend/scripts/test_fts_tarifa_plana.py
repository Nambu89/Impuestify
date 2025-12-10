"""
Test FTS5 search for tarifa plana content.
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

async def test_fts_search():
    db = TursoClient(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
    await db.connect()
    
    print("=" * 60)
    print("Test de búsqueda FTS5 - Tarifa Plana")
    print("=" * 60)
    
    # Search for "tarifa plana"
    query = "tarifa plana autónomos"
    print(f"\n🔍 Buscando: '{query}'")
    
    search_sql = """
    SELECT 
        dc.id,
        dc.content,
        d.filename,
        d.title,
        fts.rank
    FROM document_chunks_fts fts
    JOIN document_chunks dc ON fts.chunk_id = dc.id
    JOIN documents d ON dc.document_id = d.id
    WHERE document_chunks_fts MATCH ?
    ORDER BY fts.rank
    LIMIT 5
    """
    
    result = await db.execute(search_sql, [query])
    
    if not result.rows:
        print("\n❌ No se encontraron resultados")
    else:
        print(f"\n✅ Encontrados {len(result.rows)} resultados:")
        for i, row in enumerate(result.rows, 1):
            print(f"\n{i}. {row['filename']} (Rank: {row['rank']})")
            print(f"   Contenido: {row['content'][:200]}...")
    
    # Check if tarifa_plana_80_euros.md is in documents
    print("\n" + "=" * 60)
    print("Verificando documento tarifa_plana_80_euros.md")
    print("=" * 60)
    
    result = await db.execute("""
        SELECT id, filename, title, document_type 
        FROM documents 
        WHERE filename LIKE '%tarifa_plana%'
    """)
    
    if not result.rows:
        print("\n❌ Documento NO encontrado en tabla documents")
    else:
        print(f"\n✅ Documento encontrado:")
        for row in result.rows:
            doc_id = row['id']
            print(f"   ID: {doc_id}")
            print(f"   Filename: {row['filename']}")
            print(f"   Type: {row['document_type']}")
            
            # Check chunks
            chunk_result = await db.execute("""
                SELECT COUNT(*) as count 
                FROM document_chunks 
                WHERE document_id = ?
            """, [doc_id])
            chunk_count = chunk_result.rows[0]['count']
            print(f"   Chunks: {chunk_count}")
            
            # Check if chunks are in FTS
            fts_result = await db.execute("""
                SELECT COUNT(*) as count
                FROM document_chunks_fts fts
                JOIN document_chunks dc ON fts.chunk_id = dc.id
                WHERE dc.document_id = ?
            """, [doc_id])
            fts_count = fts_result.rows[0]['count']
            print(f"   Chunks en FTS5: {fts_count}")
    
    await db.disconnect()
    print("\n" + "=" * 60)

asyncio.run(test_fts_search())
