"""
Inspect documents table schema
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

async def inspect_documents():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    print("📊 Inspecting documents table schema...")
    
    # Get table schema
    schema_sql = "PRAGMA table_info(documents)"
    result = await db.execute(schema_sql)
    
    print("\nColumns in documents:")
    for row in result.rows:
        print(f"  - {row['name']}: {row['type']}")
    
    # Sample row
    print("\n📝 Sample row:")
    sample_sql = "SELECT * FROM documents LIMIT 1"
    result = await db.execute(sample_sql)
    
    if result.rows:
        row = result.rows[0]
        for key in row.keys():
            value = row[key]
            if isinstance(value, str) and len(value) > 100:
                value = value[:100] + "..."
            print(f"  {key}: {value}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(inspect_documents())
