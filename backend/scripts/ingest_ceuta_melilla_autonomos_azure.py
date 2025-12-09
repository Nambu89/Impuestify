"""
Ingest Ceuta/Melilla and Autonomous Quotas knowledge using Azure Document Intelligence.

This script:
1. Extracts PDFs using Azure Document Intelligence (better table recognition).
2. Ingests markdown files from knowledge_updates/.
3. Inserts documents and chunks into Turso database.
4. Rebuilds FTS5 index.

Usage:
    python scripts/ingest_ceuta_melilla_autonomos_azure.py
"""
import asyncio
import os
import sys
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Azure Document Intelligence
try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_DI_AVAILABLE = True
except ImportError:
    AZURE_DI_AVAILABLE = False
    logger.warning("Azure Document Intelligence not available. Install: pip install azure-ai-documentintelligence")

# Directories
PDF_DIR = project_root / "data" / "tabla autonomos y fiscalidad ceuta y melilla"
MD_DIR = backend_dir / "data" / "knowledge_updates"

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum chunk size in characters
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at paragraph or sentence boundary
        if end < text_len:
            # Look for paragraph break
            last_para = chunk.rfind('\n\n')
            if last_para > chunk_size * 0.5:  # At least 50% into chunk
                end = start + last_para + 2
                chunk = text[start:end]
            else:
                # Look for sentence break
                last_period = max(chunk.rfind('. '), chunk.rfind('.\n'))
                if last_period > chunk_size * 0.5:
                    end = start + last_period + 2
                    chunk = text[start:end]
        
        chunks.append(chunk.strip())
        start += (chunk_size - overlap)
    
    return chunks


async def extract_pdf_with_azure_di(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract text and tables from PDF using Azure Document Intelligence.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dict with 'text' (markdown), 'pages', 'tables_count', 'hash'
    """
    if not AZURE_DI_AVAILABLE:
        raise RuntimeError("Azure Document Intelligence SDK not installed")
    
    endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    api_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    if not endpoint or not api_key:
        raise ValueError("Missing AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT or AZURE_DOCUMENT_INTELLIGENCE_KEY")
    
    client = DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key)
    )
    
    logger.info(f"📄 Extracting {pdf_path.name} with Azure Document Intelligence...")
    
    # Calculate file hash for deduplication
    import hashlib
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()
    
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Use base64 encoding for bytes_source
    import base64
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    
    base64_source = base64.b64encode(file_bytes).decode('utf-8')
    
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(bytes_source=base64_source)
    )
    
    result = poller.result()
    
    # Convert to markdown
    markdown_text = ""
    tables_count = 0
    
    for page in result.pages:
        # Extract text from page
        if hasattr(page, 'lines'):
            for line in page.lines:
                markdown_text += line.content + "\n"
        markdown_text += "\n"
    
    # Extract tables as markdown
    if hasattr(result, 'tables'):
        for table in result.tables:
            tables_count += 1
            markdown_text += "\n\n### Tabla\n\n"
            
            # Build markdown table
            rows = {}
            for cell in table.cells:
                row_idx = cell.row_index
                col_idx = cell.column_index
                if row_idx not in rows:
                    rows[row_idx] = {}
                rows[row_idx][col_idx] = cell.content
            
            # Write header
            if 0 in rows:
                header = " | ".join([rows[0].get(i, "") for i in range(table.column_count)])
                markdown_text += f"| {header} |\n"
                markdown_text += "|" + " --- |" * table.column_count + "\n"
            
            # Write data rows
            for row_idx in sorted(rows.keys())[1:]:
                row_data = " | ".join([rows[row_idx].get(i, "") for i in range(table.column_count)])
                markdown_text += f"| {row_data} |\n"
            
            markdown_text += "\n"
    
    logger.info(f"  ✅ Extracted {len(result.pages)} pages, {tables_count} tables")
    
    return {
        "text": markdown_text.strip(),
        "pages": len(result.pages),
        "tables_count": tables_count,
        "hash": file_hash
    }


async def extract_markdown(md_path: Path) -> str:
    """
    Read markdown file.
    
    Args:
        md_path: Path to markdown file
        
    Returns:
        Markdown text
    """
    logger.info(f"📝 Reading {md_path.name}...")
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()
    logger.info(f"  ✅ Read {len(text)} characters")
    return text


async def ingest_document(
    db: TursoClient,
    filename: str,
    text: str,
    source_type: str,
    category: str,
    metadata: Dict[str, Any] = None
) -> int:
    """
    Ingest a document into the database with deduplication.
    
    Args:
        db: Database client
        filename: Document filename
        text: Document text
        source_type: 'pdf' or 'markdown'
        category: Document category
        metadata: Additional metadata (should include 'hash' for PDFs)
        
    Returns:
        Document ID or None if duplicate
    """
    import hashlib
    import uuid
    
    # Calculate content hash for deduplication
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    
    # Check if document with same hash already exists
    check_hash_sql = "SELECT id, filename FROM documents WHERE hash = ?"
    result = await db.execute(check_hash_sql, [content_hash])
    
    if result.rows:
        existing_file = result.rows[0]['filename']
        logger.info(f"  ⚠️  Duplicate content detected (same as {existing_file}), skipping...")
        return None
    
    # Check if document with same filename exists
    check_sql = "SELECT id FROM documents WHERE filename = ?"
    result = await db.execute(check_sql, [filename])
    
    if result.rows and result.rows[0].get('id'):
        doc_id = result.rows[0]['id']
        logger.info(f"  ⚠️  Document exists (ID: {doc_id}), deleting old chunks...")
        await db.execute("DELETE FROM document_chunks WHERE document_id = ?", [doc_id])
        await db.execute("DELETE FROM documents WHERE id = ?", [doc_id])
    
    # Insert document
    doc_id = str(uuid.uuid4())
    title = filename.replace("_", " ").replace(".pdf", "").replace(".md", "")
    
    metadata_dict = metadata or {}
    
    insert_doc_sql = """
    INSERT INTO documents (id, filename, title, document_type, source, hash)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    doc_type = 'pdf' if source_type == 'pdf' else 'markdown'
    await db.execute(insert_doc_sql, [doc_id, filename, title, doc_type, category, content_hash])
    
    logger.info(f"  ✅ Document inserted (ID: {doc_id})")
    
    # Chunk text
    chunks = chunk_text(text)
    logger.info(f"  📦 Created {len(chunks)} chunks")
    
    # Insert chunks in batches
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        
        values_list = []
        for chunk_idx, chunk_content in enumerate(batch):
            escaped_content = chunk_content.replace("'", "''")
            values_list.append(f"('{doc_id}', '{escaped_content}', 0, {i + chunk_idx})")
        
        values = ", ".join(values_list)
        sql = f"INSERT INTO document_chunks (document_id, content, page_number, chunk_index) VALUES {values}"
        await db.execute(sql)
    
    logger.info(f"  ✅ Inserted {len(chunks)} chunks")
    
    return doc_id


async def main():
    """Main ingestion process."""
    logger.info("🚀 Starting ingestion process...")
    
    # Connect to database
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        logger.error("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN")
        return
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    logger.info("✅ Connected to Turso")
    
    total_docs = 0
    
    # Ingest PDFs
    if PDF_DIR.exists() and AZURE_DI_AVAILABLE:
        logger.info(f"\n📂 Processing PDFs from {PDF_DIR}...")
        pdf_files = list(PDF_DIR.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        for pdf_path in pdf_files:
            try:
                # Extract with Azure DI
                extracted = await extract_pdf_with_azure_di(pdf_path)
                
                # Ingest
                await ingest_document(
                    db=db,
                    filename=pdf_path.name,
                    text=extracted['text'],
                    source_type='pdf',
                    category='ceuta_melilla',
                    metadata={
                        'pages': extracted['pages'],
                        'tables_count': extracted['tables_count']
                    }
                )
                
                total_docs += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing {pdf_path.name}: {e}")
    else:
        if not PDF_DIR.exists():
            logger.warning(f"⚠️  PDF directory not found: {PDF_DIR}")
        if not AZURE_DI_AVAILABLE:
            logger.warning("⚠️  Azure Document Intelligence not available, skipping PDFs")
    
    # Ingest Markdown files
    if MD_DIR.exists():
        logger.info(f"\n📂 Processing Markdown files from {MD_DIR}...")
        md_files = list(MD_DIR.glob("*.md"))
        logger.info(f"Found {len(md_files)} Markdown files")
        
        for md_path in md_files:
            try:
                # Read markdown
                text = await extract_markdown(md_path)
                
                # Determine category
                category = 'autonomos_2025' if 'autonomos' in md_path.name.lower() or 'tarifa' in md_path.name.lower() else 'ceuta_melilla'
                
                # Ingest
                await ingest_document(
                    db=db,
                    filename=md_path.name,
                    text=text,
                    source_type='markdown',
                    category=category,
                    metadata={
                        'url': 'https://www.infoautonomos.com' if 'infoautonomos' in md_path.name else 'https://www.sage.com'
                    }
                )
                
                total_docs += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing {md_path.name}: {e}")
    else:
        logger.warning(f"⚠️  Markdown directory not found: {MD_DIR}")
    
    await db.disconnect()
    
    logger.info(f"\n✅ Ingestion complete! Processed {total_docs} documents.")
    logger.info("\n🔄 Next step: Run 'python scripts/rebuild_fts5.py' to update the search index.")


if __name__ == "__main__":
    asyncio.run(main())
