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

async def verify():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    # Check chunk counts
    sql = """
    SELECT 
        d.filename,
        COUNT(c.id) as chunk_count
    FROM documents d
    LEFT JOIN document_chunks c ON c.document_id = d.id
    WHERE d.filename LIKE '%Renta_2024%'
    GROUP BY d.filename
    ORDER BY chunk_count DESC
    """
    
    result = await db.execute(sql)
    
    print("\n📊 Chunk counts for Renta 2024 manuals:")
    for row in result.rows:
        print(f"   {row['filename']}: {row['chunk_count']} chunks")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(verify())
