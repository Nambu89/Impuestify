"""Debug document insertion"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

from app.database.turso_client import TursoClient

async def debug():
    db = TursoClient(os.getenv('TURSO_DATABASE_URL'), os.getenv('TURSO_AUTH_TOKEN'))
    await db.connect()
    
    # Insert a test document
    print("Inserting test document...")
    await db.execute("INSERT INTO documents (filename, title, document_type, source) VALUES (?, ?, ?, ?)",
                     ['test.md', 'Test', 'markdown', 'test'])
    
    # Get the ID
    result = await db.execute("SELECT last_insert_rowid() as id")
    doc_id = result.rows[0]['id']
    print(f"Inserted document ID: {doc_id} (type: {type(doc_id)})")
    
    # Verify it exists
    result = await db.execute("SELECT id FROM documents WHERE id = ?", [str(doc_id)])
    print(f"Found in documents table: {result.rows}")
    
    # Try to insert a chunk
    print(f"\nInserting chunk with document_id='{doc_id}'...")
    try:
        await db.execute(
            "INSERT INTO document_chunks (document_id, content, page_number, chunk_index) VALUES (?, ?, ?, ?)",
            [str(doc_id), 'Test content', 0, 0]
        )
        print("✅ Chunk inserted successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Cleanup
    await db.execute("DELETE FROM document_chunks WHERE document_id = ?", [str(doc_id)])
    await db.execute("DELETE FROM documents WHERE id = ?", [str(doc_id)])
    
    await db.disconnect()

asyncio.run(debug())
