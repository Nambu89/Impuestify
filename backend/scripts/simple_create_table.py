import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from app.database.turso_client import TursoClient

async def simple_create():
    db = TursoClient()
    await db.connect()
    
    try:
        # Very simple version
        sql = """
CREATE TABLE IF NOT EXISTS notification_analyses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    notification_type TEXT,
    region TEXT,
    is_foral INTEGER DEFAULT 0,
    summary TEXT,
    deadlines TEXT,
   references TEXT,
    severity TEXT,
    notification_date TEXT,
    created_at TEXT
)
"""
        print("Executing SQL...")
        await db.execute(sql)
        print("✅ Table created!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    await db.disconnect()

asyncio.run(simple_create())
