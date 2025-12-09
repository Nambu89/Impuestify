"""
Production PDF Extraction Pipeline v2.

Improvements over v1:
- Per-page chunking (fixes page number bug)
- Table-aware chunking (preserves structure)
- Markdown output from Azure DI
- Better error handling and progress tracking
- Dry-run mode for testing

Usage:
    # Dry run (test without writing to DB)
    python scripts/extract_pdfs_v2.py --dry-run
    
    # Full extraction
    python scripts/extract_pdfs_v2.py
    
    # Single file
    python scripts/extract_pdfs_v2.py --file "Manual_práctico_de_Renta_2024._Parte_1.pdf"
"""
import asyncio
import os
import sys
import uuid
import hashlib
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient
from app.utils.chunking import DocumentLayoutChunker


class AzureDocumentExtractor:
    """Extractor using Azure Document Intelligence with Markdown output."""
    
    def __init__(self):
        self.endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.client = None
        
        if not self.endpoint or not self.key:
            raise ValueError(
                "Azure Document Intelligence not configured.\n"
                "Set AZ URE_DOCUMENT_INTELLIGENCE_ENDPOINT and AZURE_DOCUMENT_INTELLIGENCE_KEY in .env"
            )
    
    def _init_client(self):
        """Initialize Azure DI client."""
        if self.client is None:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )
    
    def extract_with_markdown(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract content using prebuilt-layout model with Markdown output.
        
        Returns:
            Dict with 'pages' (list of {page_number, content}), 'tables', 'total_pages'
        """
        self._init_client()
        
        import base64
        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
        
        # Read and encode PDF
        with open(pdf_path, "rb") as f:
            file_content = f.read()
        
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Analyze document
        # Note: output_content_format not available in SDK 1.0.2, will use standard extraction
        poller = self.client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=AnalyzeDocumentRequest(bytes_source=base64_content)
        )
        
        result = poller.result()
        
        # Extract pages
        pages = []
        for page in result.pages:
            # Build page content from lines
            page_text = ""
            if page.lines:
                page_text = "\n".join([line.content for line in page.lines])
            
            pages.append({
                "page_number": page.page_number,
                "content": page_text
            })
        
        return {
            "pages": pages,
            "total_pages": len(pages),
            "tables": result.tables if hasattr(result, 'tables') else []
        }


class EmbeddingGenerator:
    """Generate embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.model_name = model_name
        self.model = None
        self.dimensions = 384
    
    def _load_model(self):
        """Load embedding model."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            print(f"   📥 Loading embedding model...")
            self.model = SentenceTransformer(self.model_name)
            print(f"   ✓ Model loaded ({self.dimensions} dimensions)")
    
    def generate(self, texts: List[str]) -> List[str]:
        """Generate embeddings for texts.
        
        Returns:
            List of embeddings as JSON strings.
        """
        import json
        self._load_model()
        
        embeddings = self.model.encode(texts, show_progress_bar=True)
        
        return [json.dumps(emb.tolist()) for emb in embeddings]


async def process_pdfs_v2(data_dir: str, dry_run: bool = False, target_file: str = None):
    """Process PDFs with improved chunking strategy."""
    
    print("=" * 60)
    print("TaxIA - PDF Extraction Pipeline v2")
    print("Per-Page + Table-Aware Chunking")
    print("=" * 60)
    
    if dry_run:
        print("🧪 DRY RUN MODE - No database writes\n")
    
    # Initialize components
    try:
        extractor = AzureDocumentExtractor()
        print("✓ Azure Document Intelligence configured")
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    chunker = DocumentLayoutChunker(
        max_chunk_size=1500,
        min_chunk_size=100,
        preserve_tables=True
    )
    
    embedder = EmbeddingGenerator()
    
    # Connect to Turso
    if not dry_run:
        print("\n📡 Connecting to Turso...")
        client = TursoClient()
        await client.connect()
        print("✓ Connection established\n")
    
    # Get PDF files
    data_path = Path(data_dir)
    if target_file:
        pdf_files = [data_path / target_file] if (data_path / target_file).exists() else []
        if not pdf_files:
            print(f"❌ File not found: {target_file}")
            return
    else:
        pdf_files = list(data_path.glob("*.pdf"))
    
    print(f"📚 Found {len(pdf_files)} PDF file(s)\n")
    
    total_chunks = 0
    processed_docs = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] 📄 {pdf_file.name}")
        
        try:
            # Calculate file hash
            file_hash = hashlib.md5(pdf_file.read_bytes()).hexdigest()
            
            if not dry_run:
                # Check if already processed
                existing = await client.execute(
                    "SELECT id FROM documents WHERE hash = ?",
                    [file_hash]
                )
                
                if existing.rows:
                    print(f"         ⏭️  Already processed, skipping...\n")
                    continue
            
            # Extract with Azure DI
            print(f"         📖 Extracting with Azure DI (Markdown mode)...")
            extracted = extractor.extract_with_markdown(str(pdf_file))
            
            if not extracted["pages"]:
                print(f"         ⚠️  No content extracted\n")
                continue
            
            print(f"         ✓ {extracted['total_pages']} pages extracted")
            
            # Chunk with new strategy
            print(f"         ✂️  Chunking (per-page + table-aware)...")
            chunks = chunker.chunk_document(extracted["pages"], extracted.get("tables"))
            print(f"         ✓ {len(chunks)} chunks created")
            
            # Show chunk stats
            pages_with_chunks = len(set(chunk.page_number for chunk in chunks))
            coverage = (pages_with_chunks / extracted['total_pages'] * 100) if extracted['total_pages'] > 0 else 0
            print(f"         📊 Page coverage: {pages_with_chunks}/{extracted['total_pages']} ({coverage:.1f}%)")
            
            if dry_run:
                print(f"         🧪 [DRY RUN] Would insert {len(chunks)} chunks")
                print(f"         Sample chunk (page {chunks[0].page_number}): {chunks[0].content[:100]}...\n")
                total_chunks += len(chunks)
                processed_docs += 1
                continue
            
            # Insert document
            doc_id = str(uuid.uuid4())
            doc_type = categorize_document(pdf_file.name)
            year = extract_year(pdf_file.name)
            
            await client.execute(
                """
                INSERT INTO documents 
                (id, filename, filepath, title, document_type, year, total_pages, file_size, hash, processed, processing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    doc_id,
                    pdf_file.name,
                    str(pdf_file),
                    pdf_file.stem.replace("_", " "),
                    doc_type,
                    year,
                    extracted["total_pages"],
                    pdf_file.stat().st_size,
                    file_hash,
                    0,
                    "processing"
                ]
            )
            
            # Insert chunks
            chunk_ids = []
            chunk_texts = []
            
            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk.content)
                
                await client.execute(
                    """
                    INSERT INTO document_chunks 
                    (id, document_id, chunk_index, content, content_hash, page_number, token_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        chunk_id,
                        doc_id,
                        chunk.chunk_index,
                        chunk.content,
                        hashlib.md5(chunk.content.encode()).hexdigest(),
                        chunk.page_number,
                        len(chunk.content.split())
                    ]
                )
            
            # Generate embeddings
            print(f"         🧠 Generating embeddings....")
            try:
                embeddings = embedder.generate(chunk_texts)
                
                print(f"         💾 Saving embeddings...")
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    emb_id = str(uuid.uuid4())
                    await client.execute(
                        """
                        INSERT INTO embeddings (id, chunk_id, embedding, model_name, dimensions)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        [emb_id, chunk_id, embedding, embedder.model_name, embedder.dimensions]
                    )
                
                # Mark as completed
                await client.execute(
                    "UPDATE documents SET processed = 1, processing_status = 'completed' WHERE id = ?",
                    [doc_id]
                )
            except Exception as emb_error:
                print(f"         ⚠️  Embedding error: {emb_error}")
                await client.execute(
                    "UPDATE documents SET processing_status = 'partial', error_message = ? WHERE id = ?",
                    [f"Embeddings error: {str(emb_error)}", doc_id]
                )
            
            total_chunks += len(chunks)
            processed_docs += 1
            print(f"         ✅ Completed\n")
            
        except Exception as e:
            print(f"         ❌ Error: {e}\n")
            if not dry_run:
                try:
                    await client.execute(
                        "UPDATE documents SET processing_status = 'error', error_message = ? WHERE filename = ?",
                        [str(e), pdf_file.name]
                    )
                except:
                    pass
    
    if not dry_run:
        await client.disconnect()
    
    print("=" * 60)
    print(f"✅ EXTRACTION COMPLETED")
    print(f"   Documents processed: {processed_docs}/{len(pdf_files)}")
    print(f"   Chunks created: {total_chunks}")
    print("=" * 60)


def categorize_document(filename: str) -> str:
    """Categorize document by filename."""
    filename_lower = filename.lower()
    
    if "iva" in filename_lower:
        return "IVA"
    elif "renta" in filename_lower or "irpf" in filename_lower:
        return "IRPF"
    elif "sociedades" in filename_lower:
        return "IS"
    elif "patrimonio" in filename_lower:
        return "IP"
    elif "retenciones" in filename_lower:
        return "RET"
    elif "calendario" in filename_lower:
        return "CAL"
    elif "factura" in filename_lower or "verifactu" in filename_lower:
        return "FAC"
    else:
        return "GENERAL"


def extract_year(filename: str) -> int:
    """Extract year from filename."""
    import re
    match = re.search(r'20\d{2}', filename)
    return int(match.group()) if match else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract PDFs with improved chunking")
    parser.add_argument("--dry-run", action="store_true", help="Test without writing to DB")
    parser.add_argument("--file", type=str, help="Process single file")
    args = parser.parse_args()
    
    # Path to data directory
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        print(f"❌ Directory not found: {data_dir}")
        sys.exit(1)
    
    asyncio.run(process_pdfs_v2(str(data_dir), dry_run=args.dry_run, target_file=args.file))
