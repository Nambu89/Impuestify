"""
Script to re-ingest AEAT manuals correctly.
Focuses on:
1. Manual_práctico_de_Renta_2024._Parte_1.pdf
2. Manual_práctico_de_Renta_2024._Parte_2._Deducciones_autonómicas.pdf
"""
import asyncio
import os
import sys
import logging
from pathlib import Path
from pypdf import PdfReader  # Assuming pypdf is installed or we use azure-ai-documentintelligence

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = project_root / "data"

TARGET_FILES = [
    "Manual_práctico_de_Renta_2024._Parte_1.pdf",
    "Manual_práctico_de_Renta_2024._Parte_2._Deducciones_autonómicas.pdf"
]

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
        
    return chunks

async def reingest():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        logger.error("Missing Database Credentials")
        return

    db = TursoClient(turso_url, turso_token)
    await db.connect()
    print("✅ Connected to Turso")

    for filename in TARGET_FILES:
        filepath = DATA_DIR / filename
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            continue
            
        print(f"\n📄 Processing: {filename}")
        
        # 1. Clean existing data
        print("   🧹 Cleaning old data...")
        # Get doc ID first
        find_sql = "SELECT id FROM documents WHERE filename = ?"
        result = await db.execute(find_sql, [filename])
        
        if result.rows:
            doc_id = result.rows[0]['id']
            # Delete chunks
            await db.execute("DELETE FROM document_chunks WHERE document_id = ?", [doc_id])
            # Delete document entry
            await db.execute("DELETE FROM documents WHERE id = ?", [doc_id])
            print("   ✅ Old data removed")
        
        # 2. Insert Document Entry
        print("   📝 Creating new document entry...")
        # Simple title extraction from filename
        title = filename.replace("_", " ").replace(".pdf", "")
        insert_doc_sql = "INSERT INTO documents (filename, title, content_type, upload_date) VALUES (?, ?, 'application/pdf', CURRENT_TIMESTAMP) RETURNING id"
        
        try:
            result = await db.execute(insert_doc_sql, [filename, title])
            doc_id = result.rows[0]['id']
            print(f"   ✅ Document ID: {doc_id}")
            
            # 3. Read and Chunk PDF
            print("   📖 Reading PDF (this may take a while)...")
            try:
                reader = PdfReader(filepath)
                total_pages = len(reader.pages)
                print(f"   📊 Total Pages: {total_pages}")
                
                total_chunks = 0
                batch_chunks = []
                
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if not text.strip():
                        continue
                        
                    page_chunks = chunk_text(text)
                    
                    for chunk_text_content in page_chunks:
                        # Prepare chunk record
                        batch_chunks.append({
                            "document_id": doc_id,
                            "content": chunk_text_content,
                            "page_number": i + 1,
                            "chunk_index": total_chunks
                        })
                        total_chunks += 1
                        
                    # Insert in batches of 50 to avoid huge queries
                    if len(batch_chunks) >= 50:
                        values_list = []
                        for c in batch_chunks:
                            escaped_content = c['content'].replace("'", "''")
                            values_list.append(f"({c['document_id']}, '{escaped_content}', {c['page_number']}, {c['chunk_index']})")
                        
                        values = ", ".join(values_list)
                        sql = f"INSERT INTO document_chunks (document_id, content, page_number, chunk_index) VALUES {values}"
                        await db.execute(sql)
                        batch_chunks = []
                        print(f"   ...processed page {i+1}/{total_pages}", end='\r')

                # Insert remaining
                if batch_chunks:
                     values_list = []
                     for c in batch_chunks:
                        escaped_content = c['content'].replace("'", "''")
                        values_list.append(f"({c['document_id']}, '{escaped_content}', {c['page_number']}, {c['chunk_index']})")
                     
                     values = ", ".join(values_list)
                     sql = f"INSERT INTO document_chunks (document_id, content, page_number, chunk_index) VALUES {values}"
                     await db.execute(sql)
                     
                print(f"\n   ✅ Ingested {total_chunks} chunks.")
                
            except Exception as e:
                print(f"   ❌ PDF Error: {e}")
                
        except Exception as e:
             print(f"   ❌ Database Error: {e}")

    # Rebuild FTS
    print("\n🔄 Rebuilding FTS Index...")
    try:
        # We need to manually sync the new chunks to FTS
        # Or just rerun rebuild_fts5 script. 
        # Ideally, we insert into FTS as we go, but running the rebuild script is safer.
        pass
    except Exception:
        pass
        
    await db.disconnect()
    print("\n👋 Done. Please run 'python scripts/rebuild_fts5.py' to update the search index.")

if __name__ == "__main__":
    asyncio.run(reingest())
