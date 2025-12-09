"""
Test to verify Aragón table can be found with specific search.
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

async def test():
    db = TursoClient()
    await db.connect()
    
    # Direct search for "Aragón" + "escala" in Chapter 15 pages
    print("🔍 Searching for: Aragón + escala + IRPF\n")
    
    fts_query = '"Aragón" OR "escala" OR "IRPF"'
    
    sql = """
    SELECT 
        c.page_number,
        c.content,
        d.filename,
        fts.rank
    FROM document_chunks_fts fts
    JOIN document_chunks c ON c.id = fts.chunk_id
    JOIN documents d ON d.id = c.document_id
    WHERE document_chunks_fts MATCH ?
    AND d.filename LIKE '%Renta_2024._Parte_1%'
    AND c.page_number BETWEEN 1230 AND 1240
    ORDER BY rank
    LIMIT 10
    """
    
    result = await db.execute(sql, [fts_query])
    
    if result.rows:
        print(f"✅ Found {len(result.rows)} results\n")
        for i, row in enumerate(result.rows, 1):
            content = row['content']
            has_aragon = 'aragón' in content.lower()
            has_table = '13.072,50' in content or '9,50' in content
            
            print(f"{i}. Page {row['page_number']} (Rank: {row['rank']})")
            print(f"   Aragón: {'✅' if has_aragon else '❌'}")
            print(f"   Tax table: {'✅' if has_table else '❌'}")
            print(f"   Preview: {content[:150]}...")
            print()
    else:
        print("❌ NO results found")
    
    await db.disconnect()

asyncio.run(test())
