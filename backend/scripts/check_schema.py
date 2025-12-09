"""Check document_chunks table schema"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

from app.database.turso_client import TursoClient

async def check_schema():
    db = TursoClient(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
    await db.connect()
    
    print("document_chunks table schema:")
    result = await db.execute('PRAGMA table_info(document_chunks)')
    for row in result.rows:
        print(f"  {row}")
    
    print("\nForeign keys:")
    result = await db.execute('PRAGMA foreign_key_list(document_chunks)')
    for row in result.rows:
        print(f"  {row}")
    
    await db.disconnect()

asyncio.run(check_schema())
