"""
TaxIA — Pipeline Unificado de Ingesta Documental.

Extrae contenido de PDFs y Markdown usando Azure Document Intelligence,
crea chunks semánticos y genera embeddings con OpenAI text-embedding-3-large
para almacenar en Turso DB.

Reemplaza:
- extract_pdfs.py (v1)
- extract_pdfs_v2.py (v2)
- ingest_ceuta_melilla_autonomos_azure.py

Uso:
    # Procesar todos los PDFs de data/ y docs/
    python scripts/ingest_documents.py

    # Solo una carpeta
    python scripts/ingest_documents.py --dir docs/Bizkaia

    # Solo un archivo
    python scripts/ingest_documents.py --file "docs/Gipuzkoa/IRPF/NormaForal.pdf"

    # Dry run (sin escribir a DB)
    python scripts/ingest_documents.py --dry-run

    # Re-generar embeddings para docs existentes (nuevo modelo)
    python scripts/ingest_documents.py --reembed

    # Solo Markdown files
    python scripts/ingest_documents.py --dir backend/data/knowledge_updates --type md
"""
import asyncio
import argparse
import hashlib
import json
import logging
import os
import re
import struct
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

# Setup paths
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
project_root = backend_dir.parent

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import TursoClient directly (bypass app.database.__init__ which
# imports pydantic models requiring email_validator).
import importlib.util
_turso_spec = importlib.util.spec_from_file_location(
    "turso_client",
    backend_dir / "app" / "database" / "turso_client.py",
)
_turso_mod = importlib.util.module_from_spec(_turso_spec)
_turso_spec.loader.exec_module(_turso_mod)
TursoClient = _turso_mod.TursoClient

# Import DocumentLayoutChunker directly
_chunk_spec = importlib.util.spec_from_file_location(
    "chunking",
    backend_dir / "app" / "utils" / "chunking.py",
)
_chunk_mod = importlib.util.module_from_spec(_chunk_spec)
_chunk_spec.loader.exec_module(_chunk_mod)
DocumentLayoutChunker = _chunk_mod.DocumentLayoutChunker
ExtractedChunk = _chunk_mod.ExtractedChunk

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")


# ─────────────────────────────────────────────
# Azure Document Intelligence Extractor
# ─────────────────────────────────────────────

class AzureDocumentExtractor:
    """
    Extract PDF content using Azure Document Intelligence (prebuilt-layout).

    Outputs Markdown format for optimal downstream chunking & LLM compatibility.
    Uses API v4.0+ with output_content_format="markdown".
    """

    def __init__(self):
        self.endpoint = os.environ.get(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
            os.environ.get("DOCUMENTINTELLIGENCE_ENDPOINT"),
        )
        self.key = os.environ.get(
            "DOCUMENT_INTELLIGENCE_API_KEY",
            os.environ.get(
                "AZURE_DOCUMENT_INTELLIGENCE_KEY",
                os.environ.get("DOCUMENTINTELLIGENCE_API_KEY"),
            ),
        )
        self._client = None

        if not self.endpoint or not self.key:
            raise ValueError(
                "Azure Document Intelligence not configured.\n"
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT and DOCUMENT_INTELLIGENCE_API_KEY in .env"
            )

    def _get_client(self):
        """Lazy-init the Azure DI client."""
        if self._client is None:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential

            self._client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key),
            )
        return self._client

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract content from a PDF file.

        Returns:
            Dict with:
                content: str       — full Markdown text
                pages: list        — per-page content dicts
                total_pages: int
                tables_count: int
                file_hash: str     — SHA256 of the file
        """
        from azure.ai.documentintelligence.models import (
            AnalyzeDocumentRequest,
            DocumentContentFormat,
        )
        import base64

        client = self._get_client()

        # Read file and compute hash
        file_bytes = Path(file_path).read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Analyze with markdown output
        base64_content = base64.b64encode(file_bytes).decode("utf-8")

        try:
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=AnalyzeDocumentRequest(bytes_source=base64_content),
                output_content_format=DocumentContentFormat.MARKDOWN,
            )
        except TypeError:
            # Fallback: older SDK versions may not support output_content_format
            logger.warning("Markdown output not supported in this SDK version, falling back to standard extraction")
            poller = client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=AnalyzeDocumentRequest(bytes_source=base64_content),
            )

        result = poller.result()

        # Try to get markdown content directly (SDK v1.0+ with API v4.0+)
        full_content = getattr(result, "content", None)

        # Build per-page content
        pages = []
        if result.pages:
            for page in result.pages:
                page_text = ""
                if hasattr(page, "lines") and page.lines:
                    page_text = "\n".join(line.content for line in page.lines)
                pages.append({
                    "page_number": page.page_number,
                    "content": page_text,
                })

        # If we didn't get markdown content, build from pages
        if not full_content:
            full_content = "\n\n".join(p["content"] for p in pages if p["content"])

            # Append tables as markdown
            if hasattr(result, "tables") and result.tables:
                for table in result.tables:
                    full_content += "\n\n"
                    rows: Dict[int, Dict[int, str]] = {}
                    for cell in table.cells:
                        rows.setdefault(cell.row_index, {})[cell.column_index] = cell.content

                    if 0 in rows:
                        header = " | ".join(rows[0].get(i, "") for i in range(table.column_count))
                        full_content += f"| {header} |\n"
                        full_content += "|" + " --- |" * table.column_count + "\n"

                    for row_idx in sorted(rows.keys())[1:]:
                        row_data = " | ".join(rows[row_idx].get(i, "") for i in range(table.column_count))
                        full_content += f"| {row_data} |\n"

        tables_count = len(result.tables) if hasattr(result, "tables") and result.tables else 0

        return {
            "content": full_content.strip(),
            "pages": pages,
            "total_pages": len(pages),
            "tables_count": tables_count,
            "file_hash": file_hash,
        }


# ─────────────────────────────────────────────
# OpenAI Embedding Generator
# ─────────────────────────────────────────────

class OpenAIEmbeddingGenerator:
    """
    Generate embeddings using OpenAI text-embedding-3-large (3072 dims).

    Supports batch processing for efficiency (up to 2048 texts per request).
    """

    MODEL = "text-embedding-3-large"
    DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", 1536))  # 1536 = existing data, 3072 = max
    BATCH_SIZE = 20  # texts per API call

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured in .env")

        from openai import OpenAI
        self._client = OpenAI(api_key=self.api_key)

    def generate(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Returns:
            List of float vectors (each 3072 dimensions).
        """
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]

            # Truncate texts that are too long (~8191 token limit ≈ 30k chars)
            batch = [t[:30000] if len(t) > 30000 else t for t in batch]

            response = self._client.embeddings.create(
                model=self.MODEL,
                input=batch,
                encoding_format="float",
                dimensions=self.DIMENSIONS,
            )

            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    @staticmethod
    def to_blob(embedding: List[float]) -> bytes:
        """Convert embedding vector to bytes for BLOB storage in Turso."""
        return struct.pack(f"{len(embedding)}f", *embedding)

    @staticmethod
    def to_json(embedding: List[float]) -> str:
        """Convert embedding vector to JSON string."""
        return json.dumps(embedding)


# ─────────────────────────────────────────────
# Document Categorization
# ─────────────────────────────────────────────

# Territory detection from file path
TERRITORY_MAP = {
    "bizkaia": "Bizkaia", "gipuzkoa": "Gipuzkoa", "araba": "Araba",
    "alava": "Araba", "álava": "Araba", "navarra": "Navarra",
    "aeat": "AEAT", "madrid": "Madrid", "cataluña": "Cataluña",
    "cataluna": "Cataluña", "andalucia": "Andalucía", "andalucía": "Andalucía",
    "valencia": "Valencia", "aragon": "Aragón", "aragón": "Aragón",
    "galicia": "Galicia", "asturias": "Asturias", "baleares": "Baleares",
    "canarias": "Canarias", "cantabria": "Cantabria", "extremadura": "Extremadura",
    "murcia": "Murcia", "rioja": "La Rioja", "larioja": "La Rioja",
    "castillalamancha": "Castilla-La Mancha", "castillayleon": "Castilla y León",
    "castillayleon": "Castilla y León", "ceuta": "Ceuta", "melilla": "Melilla",
    "estatal": "Estatal", "boe": "Estatal",
}

# Tax type detection from filename
TAX_TYPE_MAP = {
    "irpf": "IRPF", "renta": "IRPF", "iva": "IVA", "igic": "IGIC",
    "sociedades": "IS", "patrimonio": "IP", "sucesiones": "ISD",
    "donaciones": "ISD", "isd": "ISD", "itp": "ITP-AJD", "ajd": "ITP-AJD",
    "retenciones": "RET", "calendario": "CAL", "factura": "FAC",
    "verifactu": "FAC", "batuz": "BATUZ", "ticketbai": "BATUZ",
    "lroe": "BATUZ", "autonomo": "AUTONOMOS", "autónomo": "AUTONOMOS",
    "reta": "AUTONOMOS", "modulo": "MODULOS", "estimacion": "MODULOS",
}


def detect_territory(filepath: str) -> str:
    """Detect territory from file path components."""
    path_lower = filepath.lower().replace("\\", "/")
    for key, territory in TERRITORY_MAP.items():
        if key in path_lower:
            return territory
    return "Estatal"


def detect_tax_type(filename: str) -> str:
    """Detect tax type from filename."""
    name_lower = filename.lower()
    for key, tax_type in TAX_TYPE_MAP.items():
        if key in name_lower:
            return tax_type
    return "GENERAL"


def extract_year(filename: str) -> Optional[int]:
    """Extract year from filename."""
    match = re.search(r"20\d{2}", filename)
    return int(match.group()) if match else None


# ─────────────────────────────────────────────
# Main Ingestion Pipeline
# ─────────────────────────────────────────────

async def ingest(
    directories: List[Path],
    file_types: List[str],
    dry_run: bool = False,
    target_file: Optional[str] = None,
    reembed: bool = False,
    force: bool = False,
):
    """
    Main ingestion pipeline.

    1. Discover files (PDF / Markdown)
    2. Extract content (Azure DI for PDFs, raw read for Markdown)
    3. Chunk content (DocumentLayoutChunker)
    4. Generate embeddings (OpenAI text-embedding-3-large)
    5. Store in Turso DB (with deduplication)
    """
    print("=" * 60)
    print("TaxIA — Pipeline Unificado de Ingesta Documental")
    print(f"Modelo embeddings: OpenAI {OpenAIEmbeddingGenerator.MODEL}")
    print(f"Dimensiones: {OpenAIEmbeddingGenerator.DIMENSIONS}")
    print("=" * 60)

    if dry_run:
        print("🧪 DRY RUN — no se escribirá en la base de datos\n")

    if reembed:
        print("🔄 REEMBED — regenerando embeddings para docs existentes\n")
        await _reembed_existing(dry_run)
        return

    # ── Initialize components ──
    extractor = None
    if "pdf" in file_types:
        try:
            extractor = AzureDocumentExtractor()
            logger.info("✓ Azure Document Intelligence configurado")
        except ValueError as e:
            logger.warning(f"⚠️ {e}")
            logger.warning("Los PDFs se omitirán. Solo se procesarán archivos Markdown.")

    try:
        embedder = OpenAIEmbeddingGenerator()
        logger.info("✓ OpenAI Embeddings configurado")
    except ValueError as e:
        if not dry_run:
            logger.error(f"❌ {e}")
            return
        logger.warning(f"⚠️ {e} (ignorado en dry-run)")
        embedder = None

    chunker = DocumentLayoutChunker(
        max_chunk_size=1500,
        min_chunk_size=200,
        overlap_size=150,
        preserve_tables=True,
    )

    # ── Connect to Turso ──
    db = None
    if not dry_run:
        db = TursoClient()
        await db.connect()
        logger.info("✓ Conectado a Turso DB")

    # ── Force mode: delete all existing data first ──
    if force and db and not dry_run:
        print("\n🗑️  FORCE MODE — eliminando todos los datos existentes...")
        await db.execute("DELETE FROM embeddings")
        await db.execute("DELETE FROM document_chunks")
        await db.execute("DELETE FROM documents")
        print("   ✓ Tablas limpiadas (documents, document_chunks, embeddings)")

    # ── Discover files ──
    files = _discover_files(directories, file_types, target_file)
    print(f"\n📚 {len(files)} archivos encontrados")

    if not files:
        print("No hay archivos por procesar.")
        return

    # ── Pre-scan: load existing docs from DB to skip duplicates ──
    existing_hashes = set()
    existing_filenames = set()

    if not dry_run and db and not force:
        result = await db.execute(
            "SELECT hash, filename FROM documents WHERE processed = 1"
        )
        for row in result.rows:
            if row.get("hash"):
                existing_hashes.add(row["hash"])
            if row.get("filename"):
                existing_filenames.add(row["filename"])
        if existing_hashes:
            print(f"📊 {len(existing_hashes)} documentos ya indexados en Turso — se saltarán\n")
        else:
            print()
    else:
        print()

    # ── Process each file ──
    stats = {"processed": 0, "skipped": 0, "errors": 0, "chunks": 0}

    for i, filepath in enumerate(files, 1):
        suffix = filepath.suffix.lower()
        print(f"[{i}/{len(files)}] 📄 {filepath.relative_to(project_root)}")

        try:
            # Calculate hash
            file_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()

            # Check deduplication (hash OR filename) — skip if --force
            if not dry_run and not force:
                if file_hash in existing_hashes:
                    print(f"         ⏭️  Ya indexado (mismo contenido), saltando...\n")
                    stats["skipped"] += 1
                    continue
                if filepath.name in existing_filenames:
                    print(f"         ⏭️  Ya indexado (mismo nombre), saltando...\n")
                    stats["skipped"] += 1
                    continue

            # ── Extract content ──
            if suffix == ".pdf":
                if extractor is None:
                    print(f"         ⚠️  Saltando PDF (Azure DI no configurado)\n")
                    stats["skipped"] += 1
                    continue

                print(f"         📖 Extrayendo con Azure DI...")
                extracted = extractor.extract(str(filepath))
                content = extracted["content"]
                pages = extracted["pages"]
                total_pages = extracted["total_pages"]
                tables_count = extracted["tables_count"]
                print(f"         ✓ {total_pages} págs, {tables_count} tablas")

            elif suffix == ".md":
                content = filepath.read_text(encoding="utf-8")
                pages = [{"page_number": 1, "content": content}]
                total_pages = 1
                tables_count = 0
                print(f"         ✓ {len(content)} caracteres")

            else:
                print(f"         ⚠️  Tipo no soportado: {suffix}\n")
                stats["skipped"] += 1
                continue

            if not content or len(content.strip()) < 50:
                print(f"         ⚠️  Sin contenido útil\n")
                stats["skipped"] += 1
                continue

            # ── Chunk ──
            print(f"         ✂️  Chunking...")
            chunks = chunker.chunk_document(pages)
            print(f"         ✓ {len(chunks)} chunks")

            if dry_run:
                print(f"         🧪 [DRY RUN] Insertaría {len(chunks)} chunks")
                if chunks:
                    print(f"         Ejemplo: {chunks[0].content[:80]}...\n")
                stats["processed"] += 1
                stats["chunks"] += len(chunks)
                continue

            # ── Insert document ──
            doc_id = str(uuid.uuid4())
            territory = detect_territory(str(filepath))
            tax_type = detect_tax_type(filepath.name)
            year = extract_year(filepath.name)

            await db.execute(
                """
                INSERT INTO documents
                (id, filename, filepath, title, document_type, year, source,
                 total_pages, file_size, hash, processed, processing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'processing')
                """,
                [
                    doc_id,
                    filepath.name,
                    str(filepath),
                    filepath.stem.replace("_", " "),
                    tax_type,
                    year,
                    territory,
                    total_pages,
                    filepath.stat().st_size,
                    file_hash,
                ],
            )

            # ── Insert chunks ──
            chunk_ids = []
            chunk_texts = []

            for chunk in chunks:
                chunk_id = str(uuid.uuid4())
                chunk_ids.append(chunk_id)
                chunk_texts.append(chunk.content)

                await db.execute(
                    """
                    INSERT INTO document_chunks
                    (id, document_id, chunk_index, content, content_hash,
                     page_number, token_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        chunk_id,
                        doc_id,
                        chunk.chunk_index,
                        chunk.content,
                        hashlib.md5(chunk.content.encode()).hexdigest(),
                        chunk.page_number,
                        len(chunk.content.split()),
                    ],
                )

            # ── Generate & store embeddings ──
            print(f"         🧠 Generando embeddings ({len(chunk_texts)} chunks)...")
            try:
                embeddings = embedder.generate(chunk_texts)

                print(f"         💾 Guardando embeddings...")
                for chunk_id, embedding in zip(chunk_ids, embeddings):
                    emb_id = str(uuid.uuid4())
                    embedding_blob = OpenAIEmbeddingGenerator.to_blob(embedding)

                    await db.execute(
                        """
                        INSERT INTO embeddings
                        (id, chunk_id, embedding, model_name, dimensions)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        [
                            emb_id,
                            chunk_id,
                            embedding_blob,
                            OpenAIEmbeddingGenerator.MODEL,
                            OpenAIEmbeddingGenerator.DIMENSIONS,
                        ],
                    )

                # Mark as completed
                await db.execute(
                    "UPDATE documents SET processed = 1, processing_status = 'completed' WHERE id = ?",
                    [doc_id],
                )

            except Exception as emb_error:
                logger.error(f"         ⚠️ Error embeddings: {emb_error}")
                await db.execute(
                    "UPDATE documents SET processing_status = 'partial', error_message = ? WHERE id = ?",
                    [f"Embedding error: {str(emb_error)}", doc_id],
                )

            stats["processed"] += 1
            stats["chunks"] += len(chunks)
            print(f"         ✅ Completado\n")

        except Exception as e:
            logger.error(f"         ❌ Error: {e}")
            stats["errors"] += 1
            if not dry_run and db:
                try:
                    await db.execute(
                        "UPDATE documents SET processing_status = 'error', error_message = ? WHERE filename = ?",
                        [str(e), filepath.name],
                    )
                except Exception:
                    pass
            print()

    # ── Cleanup ──
    if not dry_run and db:
        await db.disconnect()

    # ── Summary ──
    print("=" * 60)
    print("INGESTA COMPLETADA")
    print(f"   Procesados:  {stats['processed']}")
    print(f"   Saltados:    {stats['skipped']}")
    print(f"   Errores:     {stats['errors']}")
    print(f"   Chunks:      {stats['chunks']}")
    print(f"   Modelo:      {OpenAIEmbeddingGenerator.MODEL} ({OpenAIEmbeddingGenerator.DIMENSIONS}d)")
    print("=" * 60)

    # ── Auto-rebuild FTS5 if new chunks were added ──
    if stats['chunks'] > 0 and not dry_run:
        print("\nReconstruyendo indice FTS5...")
        try:
            db2 = TursoClient()
            await db2.connect()
            await db2.execute("DROP TABLE IF EXISTS document_chunks_fts")
            await db2.execute("""
                CREATE VIRTUAL TABLE document_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    content
                )
            """)
            await db2.execute("""
                INSERT INTO document_chunks_fts(chunk_id, content)
                SELECT id, content FROM document_chunks
            """)
            r = await db2.execute("SELECT COUNT(*) as cnt FROM document_chunks")
            count = r.rows[0]['cnt']
            print(f"FTS5 reconstruido: {count} chunks indexados")
            await db2.disconnect()
        except Exception as e:
            print(f"Error reconstruyendo FTS5: {e}")


async def _reembed_existing(dry_run: bool = False):
    """Re-generate embeddings for all existing chunks using the new model."""
    print("🔄 Reconectando a Turso para re-generar embeddings...")

    db = TursoClient()
    await db.connect()

    embedder = OpenAIEmbeddingGenerator()

    # Get all chunks that have old embeddings
    result = await db.execute(
        """
        SELECT dc.id, dc.content, e.id as emb_id, e.model_name
        FROM document_chunks dc
        LEFT JOIN embeddings e ON e.chunk_id = dc.id
        WHERE e.model_name != ? OR e.model_name IS NULL
        ORDER BY dc.document_id
        """,
        [OpenAIEmbeddingGenerator.MODEL],
    )

    chunks = result.rows
    print(f"📊 {len(chunks)} chunks necesitan re-embedding\n")

    if dry_run:
        print(f"🧪 [DRY RUN] Re-generaría embeddings para {len(chunks)} chunks")
        await db.disconnect()
        return

    batch_size = 20
    updated = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]

        print(f"   [{i + 1}-{i + len(batch)}/{len(chunks)}] Generando embeddings...")
        embeddings = embedder.generate(texts)

        for chunk_row, embedding in zip(batch, embeddings):
            embedding_blob = OpenAIEmbeddingGenerator.to_blob(embedding)

            if chunk_row.get("emb_id"):
                # Update existing
                await db.execute(
                    "UPDATE embeddings SET embedding = ?, model_name = ?, dimensions = ? WHERE id = ?",
                    [embedding_blob, OpenAIEmbeddingGenerator.MODEL, OpenAIEmbeddingGenerator.DIMENSIONS, chunk_row["emb_id"]],
                )
            else:
                # Insert new
                emb_id = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO embeddings (id, chunk_id, embedding, model_name, dimensions) VALUES (?, ?, ?, ?, ?)",
                    [emb_id, chunk_row["id"], embedding_blob, OpenAIEmbeddingGenerator.MODEL, OpenAIEmbeddingGenerator.DIMENSIONS],
                )

            updated += 1

    await db.disconnect()
    print(f"\n✅ Re-embedding completado: {updated} chunks actualizados al modelo {OpenAIEmbeddingGenerator.MODEL}")


def _discover_files(
    directories: List[Path],
    file_types: List[str],
    target_file: Optional[str] = None,
) -> List[Path]:
    """Discover files to process."""
    if target_file:
        target = Path(target_file)
        if not target.is_absolute():
            target = project_root / target_file
        if target.exists():
            return [target]
        logger.error(f"Archivo no encontrado: {target}")
        return []

    files = []
    extensions = []
    if "pdf" in file_types:
        extensions.append(".pdf")
    if "md" in file_types:
        extensions.append(".md")

    for directory in directories:
        if not directory.exists():
            logger.warning(f"Directorio no encontrado: {directory}")
            continue

        for ext in extensions:
            found = list(directory.rglob(f"*{ext}"))
            # Filter out files starting with underscore (like _inventario.md)
            found = [f for f in found if not f.name.startswith("_")]
            files.extend(found)

    # Sort for consistent processing order
    files.sort(key=lambda f: str(f))
    return files


# ─────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TaxIA — Pipeline Unificado de Ingesta Documental",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/ingest_documents.py                           # Procesa data/ y docs/
  python scripts/ingest_documents.py --dir docs/Bizkaia        # Solo una carpeta
  python scripts/ingest_documents.py --file "doc.pdf"          # Solo un archivo
  python scripts/ingest_documents.py --dry-run                 # Sin escribir a DB
  python scripts/ingest_documents.py --reembed                 # Re-generar embeddings
  python scripts/ingest_documents.py --type md                 # Solo Markdown
        """,
    )
    parser.add_argument("--dir", type=str, help="Directorio específico a procesar")
    parser.add_argument("--file", type=str, help="Archivo específico a procesar")
    parser.add_argument("--dry-run", action="store_true", help="Test sin escribir a DB")
    parser.add_argument("--reembed", action="store_true", help="Re-generar embeddings con nuevo modelo")
    parser.add_argument("--force", action="store_true", help="Eliminar todos los datos existentes y re-procesar desde cero")
    parser.add_argument(
        "--type",
        type=str,
        default="all",
        choices=["all", "pdf", "md"],
        help="Tipo de archivos a procesar (default: all)",
    )

    args = parser.parse_args()

    # Determine directories
    if args.dir:
        dir_path = Path(args.dir)
        if not dir_path.is_absolute():
            dir_path = project_root / args.dir
        directories = [dir_path]
    else:
        # Default: process both data/ and docs/
        directories = [
            project_root / "data",
            project_root / "docs",
        ]

    # Determine file types
    if args.type == "all":
        file_types = ["pdf", "md"]
    else:
        file_types = [args.type]

    asyncio.run(
        ingest(
            directories=directories,
            file_types=file_types,
            dry_run=args.dry_run,
            target_file=args.file,
            reembed=args.reembed,
            force=args.force,
        )
    )
