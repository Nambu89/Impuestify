"""
Ingest markdown knowledge files into Turso database.
Simplified version - only processes markdown files.
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import List

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

MD_DIR = backend_dir / "data" / "knowledge_updates"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at paragraph or sentence boundary
        if end < text_len:
            last_para = chunk.rfind('\n\n')
            if last_para > chunk_size * 0.5:
                end = start + last_para + 2
                chunk = text[start:end]
            else:
                last_period = max(chunk.rfind('. '), chunk.rfind('.\n'))
                if last_period > chunk_size * 0.5:
                    end = start + last_period + 2
                    chunk = text[start:end]
        
        chunks.append(chunk.strip())
        start += (chunk_size - overlap)
    
    return chunks


async def ingest_markdown(db: TursoClient, md_path: Path) -> int:
    """Ingest a markdown file."""
    print(f"\n📝 Processing: {md_path.name}")
    
    # Read file
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"  📖 Read {len(text)} characters")
    
    # Check if already exists
    check_sql = "SELECT id FROM documents WHERE filename = ?"
    result = await db.execute(check_sql, [md_path.name])
    
    if result.rows and result.rows[0].get('id'):
        doc_id = result.rows[0]['id']
        print(f"  ⚠️  Document exists (ID: {doc_id}), deleting old chunks...")
        await db.execute("DELETE FROM document_chunks WHERE document_id = ?", [doc_id])
        await db.execute("DELETE FROM documents WHERE id = ?", [doc_id])
    
    # Insert document
    import uuid
    doc_id = str(uuid.uuid4())
    title = md_path.name.replace("_", " ").replace(".md", "")
    
    insert_doc_sql = """
    INSERT INTO documents (id, filename, title, document_type, source)
    VALUES (?, ?, ?, ?, ?)
    """
    
    await db.execute(insert_doc_sql, [doc_id, md_path.name, title, 'markdown', 'knowledge_base'])
    print(f"  ✅ Document inserted (ID: {doc_id})")
    
    # Chunk text
    chunks = chunk_text(text)
    print(f"  📦 Created {len(chunks)} chunks")
    
    # Insert chunks in batches (parameterized)
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]

        for chunk_idx, chunk_content in enumerate(batch):
            chunk_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO document_chunks (id, document_id, content, page_number, chunk_index) VALUES (?, ?, ?, 0, ?)",
                [chunk_id, doc_id, chunk_content, i + chunk_idx]
            )
    
    print(f"  ✅ Inserted {len(chunks)} chunks")
    return doc_id


async def main():
    """Main ingestion process."""
    print("🚀 Starting markdown ingestion...\n")
    
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN")
        return
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    print("✅ Connected to Turso\n")
    
    if not MD_DIR.exists():
        print(f"❌ Markdown directory not found: {MD_DIR}")
        await db.disconnect()
        return
    
    md_files = list(MD_DIR.glob("*.md"))
    print(f"📂 Found {len(md_files)} markdown files\n")
    
    total_docs = 0
    for md_path in md_files:
        try:
            await ingest_markdown(db, md_path)
            total_docs += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    await db.disconnect()
    
    print(f"\n✅ Ingestion complete! Processed {total_docs} documents.")
    print("\n🔄 Next step: Run 'python scripts/rebuild_fts5.py' to update the search index.")


if __name__ == "__main__":
    asyncio.run(main())
