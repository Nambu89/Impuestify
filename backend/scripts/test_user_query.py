"""
Test specific user query about IRPF calculation
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
from app.routers.chat import fts_search
from app.agents.tax_agent import get_tax_agent

async def test_user_query():
    # User's exact query
    query = "Vivo en Zaragoza, cobro 35000€ al año en 12 pagas, ¿cuánto tendré que pagar de IRPF?"
    
    print(f"\n{'='*60}")
    print(f"Testing: {query}")
    print(f"{'='*60}\n")
    
    # Connect to DB
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    # Step 1: FTS5 Search
    print("Step 1: 🔍 FTS5 Search")
    print("-" * 60)
    chunks = await fts_search(db, query, k=5)
    
    if chunks:
        print(f"✅ Found {len(chunks)} chunks:\n")
        for i, chunk in enumerate(chunks, 1):
            print(f"{i}. 📄 {chunk['source']}")
            print(f"   Page: {chunk['page']}")
            print(f"   Score: {chunk['similarity']:.2f}")
            print(f"   Preview: {chunk['text'][:100]}...")
            print()
    else:
        print("❌ No chunks found!")
        await db.disconnect()
        return
    
    # Step 2: Build Context
    print("\nStep 2: 📝 Building Context")
    print("-" * 60)
    context = "\n\n".join([
        f"[Fuente: {chunk['source']}, Página {chunk['page']}]\n{chunk['text']}"
        for chunk in chunks
    ])
    print(f"Context length: {len(context)} characters\n")
    
    # Step 3: Generate Answer
    print("Step 3: 🤖 Generating Answer with TaxAgent")
    print("-" * 60)
    
    tax_agent = get_tax_agent()
    
    sources = [
        {
            "source": chunk['source'],
            "page": chunk['page'],
            "title": chunk.get('title', chunk['source'])
        }
        for chunk in chunks
    ]
    
    response = await tax_agent.run(query, context=context, sources=sources)
    
    print(f"\n{'='*60}")
    print("RESPUESTA DEL AGENTE:")
    print(f"{'='*60}")
    print(response.content)
    print(f"\n{'='*60}")
    print(f"Framework: {response.metadata.get('framework')}")
    print(f"Sources: {len(response.sources)}")
    print(f"{'='*60}\n")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(test_user_query())
