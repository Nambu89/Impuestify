"""
Create notification_analyses table in Turso database.

This script creates the table needed for storing notification analysis results.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.database.turso_client import TursoClient
import asyncio


async def create_notification_table():
    """Create notification_analyses table."""
    
    db = TursoClient()
    await db.connect()
    
    try:
        print("Creating notification_analyses table...")
        
        # Create table (Turso doesn't support FOREIGN KEY in CREATE TABLE)
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
        
        print("✅ Table created successfully")
        
        # Create index
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_notif_user 
            ON notification_analyses(user_id, created_at DESC)
        """)
        
        print("✅ Index created successfully")
        
        # Verify
        result = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='notification_analyses'
        """)
        
        if result.rows:
            print(f"\n✅ Verification successful: {result.rows[0]['name']}")
        else:
            print("\n❌ Table not found after creation")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(create_notification_table())
