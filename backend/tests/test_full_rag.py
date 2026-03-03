"""
Test full RAG pipeline: FTS5 Search + OpenAI Generation
"""
import asyncio
import os
import sys
import logging
import pytest
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient
from app.agents.tax_agent import TaxAgent
from app.routers.chat import fts_search

async def _run_full_rag_test(question):
    print(f"\n🧪 Testing Question: {question}")
    
    # 1. Setup Database
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ Missing Turso credentials")
        return

    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    # 2. Search
    print("🔍 Searching...")
    chunks = await fts_search(db, question, k=3)
    
    if not chunks:
        print("❌ No chunks found")
        await db.disconnect()
        return

    print(f"✅ Found {len(chunks)} chunks")
    for i, c in enumerate(chunks, 1):
        print(f"   {i}. {c['title']} (Score: {c['similarity']})")
        
    # 3. Generate
    print("\n🤖 Generating Answer...")
    
    # Prepare context
    context = "\n\n".join([
        f"Fuente: {c['title']} (Página {c['page']})\n{c['text']}"
        for c in chunks
    ])
    
    try:
        tax_agent = TaxAgent()
        answer = await tax_agent.ask(question, context)
        
        print("\n📝 Answer:")
        print("-" * 50)
        print(answer)
        print("-" * 50)
        
        if not answer:
            print("❌ Empty answer received!")
            
    except Exception as e:
        print(f"❌ Error generating answer: {e}")
        
    await db.disconnect()

@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("TURSO_DATABASE_URL"),
    reason="Requires TURSO_DATABASE_URL (integration test)"
)
async def test_full_rag():
    """Integration test: FTS5 search + LLM generation (needs Turso + OpenAI)."""
    question = "¿Cómo funciona el régimen de estimación directa?"
    await _run_full_rag_test(question)


if __name__ == "__main__":
    question = "¿Cómo funciona el régimen de estimación directa?"
    asyncio.run(_run_full_rag_test(question))
