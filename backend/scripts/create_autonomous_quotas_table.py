"""
Create autonomous_quotas table in Turso database.
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

async def create_table():
    """Create the autonomous_quotas table."""
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN")
        return
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    print("✅ Connected to Turso")
    
    # Read SQL file
    sql_file = Path(__file__).parent / "autonomous_quotas_table.sql"
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by semicolon and execute each statement
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    print(f"\n📝 Executing {len(statements)} SQL statements...")
    
    for i, statement in enumerate(statements, 1):
        if statement:
            print(f"  {i}. {statement[:50]}...")
            await db.execute(statement)
    
    print("\n✅ Table created successfully!")
    
    # Verify
    result = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='autonomous_quotas'")
    if result.rows:
        print("✅ Verified: autonomous_quotas table exists")
    else:
        print("❌ Error: Table not found after creation")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(create_table())
