"""
Test FTS5 search logic standalone
"""
import asyncio
import os
import sys
from pathlib import Path

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

async def test_search():
    # User query from the issue
    query = "Vivo en Zaragoza, gano 35000€ al año, cuanto tendré que pagar de IRPF?"
    print(f"\n🔍 Testing Search with User Query: '{query}'")
    
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    db = TursoClient(turso_url, turso_token)
    await db.connect()

    # 1. Simulate Clean & OR logic used in chat.py
    clean_query = ''.join(c for c in query if c.isalnum() or c.isspace())
    keywords = clean_query.split()
    # Basic stop words filter (simulation)
    stop_words = {'en', 'de', 'que', 'a', 'y', 'el', 'la', 'los', 'las', 'un', 'una', 'al'} 
    keywords = [kw for kw in keywords if kw.lower() not in stop_words and len(kw) > 2]
    
    fts_query = ' OR '.join([f'"{kw}"' for kw in keywords])
    print(f"👉 Formatted FTS5 Query: {fts_query}")

    sql = """
    SELECT 
        c.id,
        d.filename,
        d.title,
        fts.rank,
        snippet(document_chunks_fts, 1, '<b>', '</b>', '...', 32) as snippet
    FROM document_chunks_fts fts
    JOIN document_chunks c ON c.id = fts.chunk_id
    JOIN documents d ON d.id = c.document_id
    WHERE document_chunks_fts MATCH ? 
    ORDER BY rank 
    LIMIT 5
    """

    try:
        results = await db.execute(sql, [fts_query])
        
        print(f"\n✅ Found {len(results.rows)} results:")
        for i, res in enumerate(results.rows, 1):
            print(f"\n📄 {i}. Document: {res['filename']}")
            print(f"   Title: {res['title']}")
            print(f"   Rank: {res['rank']}")
            print(f"   Snippet: {res['snippet'][:200]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")

    # Check for AEAT docs presence
    print("\n🔍 Checking for AEAT Manuals in DB...")
    check_sql = "SELECT filename, COUNT(*) as chunks FROM documents WHERE filename LIKE '%Manual_práctico_de_Renta%' GROUP BY filename"
    aeat_check = await db.execute(check_sql)
    if aeat_check.rows:
        for row in aeat_check.rows:
            print(f"   Found: {row['filename']} ({row['chunks']} chunks)")
            
            # Check content sample
            sample_sql = "SELECT content FROM document_chunks WHERE document_id = (SELECT id FROM documents WHERE filename = ?) LIMIT 1"
            sample = await db.execute(sample_sql, [row['filename']])
            if sample.rows:
                print(f"   Sample content: {sample.rows[0]['content'][:100]}...")
    else:
        print("❌ 'Manual_práctico_de_Renta' NOT found in documents table.")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_search())
