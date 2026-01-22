"""
Test specific search for Aragón IRPF tax table.
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

async def test_aragon_table():
    print("🔍 Searching for Aragón IRPF tax table in Chapter 15...\n")
    
    db = TursoClient()
    await db.connect()
    
    # Search for Aragón-specific content in pages 1236
    sql = """
    SELECT 
        c.page_number,
        c.content,
        d.filename
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.filename LIKE '%Renta_2024._Parte_1%'
    AND c.page_number = 1236
    ORDER BY c.chunk_index
    """
    
    result = await db.execute(sql)
    
    if result.rows:
        print(f"✅ Found {len(result.rows)} chunk(s) on page 1236\n")
        
        for i, row in enumerate(result.rows, 1):
            content = row['content']
            
            # Check for Aragón
            if 'aragón' in content.lower():
                print(f"📄 Chunk {i} - Contains 'Aragón':")
                print(f"   Preview: {content[:300]}...")
                print()
                
                # Check for the tax table
                if '13.072,50' in content and '9,50' in content:
                    print("   ✅ FOUND: Aragón tax table with rates!")
                    print(f"   Full content:\n{content}\n")
                else:
                    print("   ⚠️  Contains Aragón but table might be in adjacent chunk")
            else:
                print(f"📄 Chunk {i}:")
                print(f"   Preview: {content[:200]}...")
                print()
    else:
        print("❌ NO chunks found on page 1236!")
    
    # Also test FTS5 search
    print("\n" + "="*60)
    print("🔍 Testing FTS5 search for 'Aragón IRPF escala'...\n")
    
    fts_sql = """
    SELECT 
        c.page_number,
        c.content,
        d.filename,
        fts.rank
    FROM document_chunks_fts fts
    JOIN document_chunks c ON c.id = fts.chunk_id
    JOIN documents d ON d.id = c.document_id
    WHERE document_chunks_fts MATCH 'Aragón OR escala OR IRPF'
    AND d.filename LIKE '%Renta_2024._Parte_1%'
    AND c.page_number BETWEEN 1230 AND 1240
    ORDER BY rank
    LIMIT 5
    """
    
    fts_result = await db.execute(fts_sql)
    
    if fts_result.rows:
        print(f"✅ FTS5 found {len(fts_result.rows)} relevant chunks\n")
        for row in fts_result.rows:
            print(f"Page {row['page_number']} (Rank: {row['rank']})")
            if 'aragón' in row['content'].lower():
                print("   ✅ Contains Aragón")
                if '13.072,50' in row['content']:
                    print("   ✅ Contains tax table!")
            print(f"   Preview: {row['content'][:150]}...\n")
    else:
        print("❌ FTS5 search found nothing")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_aragon_table())
