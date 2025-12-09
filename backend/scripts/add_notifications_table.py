"""
Database migration: Add notification_analyses table.

Run with:
    python scripts/add_notifications_table.py
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


async def add_notifications_table():
    print("📝 Adding notification_analyses table...")
    
    db = TursoClient()
    await db.connect()
    
    try:
        # Create table
        await db.execute("""
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
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("✅ Table created")
        
        # Create indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notif_user 
            ON notification_analyses(user_id, created_at DESC)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notif_hash 
            ON notification_analyses(file_hash)
        """)
        
        print("✅ Indexes created")
        print("\n✅ Migration complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(add_notifications_table())
