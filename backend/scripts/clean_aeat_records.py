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

async def delete_incomplete_docs():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    # Files to delete
    files = [
        "Manual_práctico_de_Renta_2024._Parte_1.pdf",
        "Manual_práctico_de_Renta_2024._Parte_2._Deducciones_autonómicas.pdf"
    ]
    
    for filename in files:
        print(f"🗑️ Deleting incomplete records for: {filename}")
        # Get ID
        res = await db.execute("SELECT id FROM documents WHERE filename = ?", [filename])
        if res.rows:
            doc_id = res.rows[0]['id']
            # Delete chunks
            await db.execute("DELETE FROM document_chunks WHERE document_id = ?", [doc_id])
            # Delete embeddings if any
            # await db.execute("DELETE FROM embeddings WHERE chunk_id IN (SELECT id FROM document_chunks WHERE document_id = ?)", [doc_id]) # Complex query, maybe skip
            
            # Delete doc
            await db.execute("DELETE FROM documents WHERE id = ?", [doc_id])
            print("   ✅ Deleted")
        else:
            print("   ⚠️ Not found")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(delete_incomplete_docs())
