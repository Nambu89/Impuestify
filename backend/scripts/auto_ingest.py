"""
TaxIA -- Auto-Ingesta RAG Pipeline.

Reads pending documents from docs/_pending_ingest.json (written by the crawler)
and processes them through the existing ingestion pipeline (Azure DI + chunking +
OpenAI embeddings + Turso DB).

Usage:
    # Process all pending documents
    python -m backend.scripts.auto_ingest

    # Dry run -- show what would be processed
    python -m backend.scripts.auto_ingest --dry-run

    # Limit to N documents per run
    python -m backend.scripts.auto_ingest --limit 5

    # Combine
    python -m backend.scripts.auto_ingest --dry-run --limit 3
"""
import argparse
import asyncio
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Path setup ──────────────────────────────────────────────────
backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Re-use classes from the existing ingest_documents pipeline
from scripts.ingest_documents import (
    AzureDocumentExtractor,
    DocumentLayoutChunker,
    OpenAIEmbeddingGenerator,
    TursoClient,
    detect_tax_type,
    detect_territory,
    extract_year,
)
import uuid
import struct

# ── Config ──────────────────────────────────────────────────────
DOCS_DIR = project_root / "docs"
PENDING_INGEST = DOCS_DIR / "_pending_ingest.json"
INGESTED_LOG = DOCS_DIR / "_ingested_log.json"

# Logging -- use print(flush=True) for Railway compatibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("auto_ingest")


# ── Helpers ─────────────────────────────────────────────────────

def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_pending() -> list[dict]:
    """Load pending ingest entries from _pending_ingest.json."""
    if not PENDING_INGEST.exists():
        return []
    try:
        with open(PENDING_INGEST, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("files", [])
    except (json.JSONDecodeError, ValueError):
        logger.warning("Could not parse _pending_ingest.json")
        return []


def save_pending(files: list[dict]) -> None:
    """Write remaining pending files back to _pending_ingest.json."""
    if not files:
        # Remove file when queue is empty
        if PENDING_INGEST.exists():
            PENDING_INGEST.unlink()
        return

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(files),
        "files": files,
    }
    with open(PENDING_INGEST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_ingested_log(entry: dict) -> None:
    """Append a successfully ingested entry to _ingested_log.json."""
    entries = []
    if INGESTED_LOG.exists():
        try:
            with open(INGESTED_LOG, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, ValueError):
            entries = []

    entries.append(entry)

    # Keep last 500 entries
    if len(entries) > 500:
        entries = entries[-500:]

    with open(INGESTED_LOG, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


# ── Main pipeline ───────────────────────────────────────────────

async def auto_ingest(
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> int:
    """
    Process pending documents from the crawler queue.

    Returns:
        Exit code: 0 if OK, 1 if errors occurred.
    """
    print("=" * 60, flush=True)
    print("TaxIA -- Auto-Ingesta RAG Pipeline", flush=True)
    print("=" * 60, flush=True)

    # 1. Load pending queue
    pending = load_pending()
    if not pending:
        print("No hay documentos pendientes de ingesta.", flush=True)
        return 0

    print(f"Pendientes: {len(pending)} documentos", flush=True)

    if dry_run:
        print("[DRY RUN -- no se modificara la base de datos]", flush=True)

    if limit is not None:
        pending_to_process = pending[:limit]
        print(f"Limite: procesando {len(pending_to_process)} de {len(pending)}", flush=True)
    else:
        pending_to_process = list(pending)

    print(flush=True)

    # 2. Initialize components
    extractor = None
    try:
        extractor = AzureDocumentExtractor()
        print("Azure Document Intelligence: OK", flush=True)
    except ValueError as e:
        print(f"Azure DI no configurado: {e}", flush=True)
        print("Solo se procesaran archivos Markdown.", flush=True)

    embedder = None
    if not dry_run:
        try:
            embedder = OpenAIEmbeddingGenerator()
            print("OpenAI Embeddings: OK", flush=True)
        except ValueError as e:
            print(f"ERROR: {e}", flush=True)
            return 1

    chunker = DocumentLayoutChunker(
        max_chunk_size=1500,
        min_chunk_size=200,
        overlap_size=150,
        preserve_tables=True,
    )

    # 3. Connect to Turso (for hash dedup check + writes)
    db = None
    existing_hashes: set[str] = set()

    if not dry_run:
        db = TursoClient()
        await db.connect()
        print("Turso DB: conectado", flush=True)

        # Load existing hashes for deduplication
        result = await db.execute(
            "SELECT hash FROM documents WHERE processed = 1 AND hash IS NOT NULL"
        )
        existing_hashes = {row["hash"] for row in (result.rows or [])}
        print(f"Documentos ya indexados: {len(existing_hashes)}", flush=True)

    print(flush=True)

    # 4. Process each pending file
    stats = {"processed": 0, "skipped_hash": 0, "skipped_missing": 0, "errors": 0, "chunks": 0}
    processed_entries = []  # entries to move to ingested log
    remaining_pending = []  # entries that were NOT processed (due to limit)

    for i, entry in enumerate(pending):
        # If this entry is beyond the limit, keep it in pending
        if entry not in pending_to_process:
            remaining_pending.append(entry)
            continue

        rel_path = entry.get("path", "")
        filepath = DOCS_DIR / rel_path

        print(f"[{i + 1}/{len(pending_to_process)}] {rel_path}", flush=True)

        # 4a. Check file exists
        if not filepath.exists():
            print(f"  SKIP: archivo no encontrado", flush=True)
            logger.warning("File not found: %s", filepath)
            stats["skipped_missing"] += 1
            # Don't keep it in pending -- it's a dead entry
            continue

        # 4b. Compute hash and check dedup
        file_hash = compute_sha256(filepath)

        if file_hash in existing_hashes:
            print(f"  SKIP: ya indexado (mismo hash SHA-256)", flush=True)
            stats["skipped_hash"] += 1
            processed_entries.append({
                "path": rel_path,
                "hash": file_hash,
                "status": "skipped_duplicate",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            continue

        if dry_run:
            suffix = filepath.suffix.lower()
            size_kb = filepath.stat().st_size / 1024
            print(f"  [DRY RUN] Procesaria: {suffix} ({size_kb:.0f} KB)", flush=True)
            stats["processed"] += 1
            continue

        # 4c. Extract content
        suffix = filepath.suffix.lower()
        try:
            if suffix == ".pdf":
                if extractor is None:
                    print(f"  SKIP: PDF sin Azure DI configurado", flush=True)
                    stats["skipped_missing"] += 1
                    remaining_pending.append(entry)
                    continue

                print(f"  Extrayendo con Azure DI...", flush=True)
                extracted = extractor.extract(str(filepath))
                content = extracted["content"]
                pages = extracted["pages"]
                total_pages = extracted["total_pages"]

            elif suffix == ".md":
                content = filepath.read_text(encoding="utf-8")
                pages = [{"page_number": 1, "content": content}]
                total_pages = 1

            else:
                print(f"  SKIP: tipo no soportado ({suffix})", flush=True)
                stats["skipped_missing"] += 1
                continue

            if not content or len(content.strip()) < 50:
                print(f"  SKIP: contenido insuficiente", flush=True)
                stats["skipped_missing"] += 1
                continue

        except Exception as e:
            print(f"  ERROR extraccion: {e}", flush=True)
            logger.error("Extraction error for %s: %s", rel_path, e)
            stats["errors"] += 1
            remaining_pending.append(entry)
            continue

        # 4d. Chunk
        try:
            chunks = chunker.chunk_document(pages)
            print(f"  Chunks: {len(chunks)}", flush=True)
        except Exception as e:
            print(f"  ERROR chunking: {e}", flush=True)
            stats["errors"] += 1
            remaining_pending.append(entry)
            continue

        # 4e. Insert document record
        try:
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

            # 4f. Insert chunks
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

            # 4g. Generate & store embeddings
            print(f"  Generando embeddings ({len(chunk_texts)} chunks)...", flush=True)
            embeddings = embedder.generate(chunk_texts)

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

            # Mark document as completed
            await db.execute(
                "UPDATE documents SET processed = 1, processing_status = 'completed' WHERE id = ?",
                [doc_id],
            )

            existing_hashes.add(file_hash)
            stats["processed"] += 1
            stats["chunks"] += len(chunks)

            processed_entries.append({
                "path": rel_path,
                "hash": file_hash,
                "doc_id": doc_id,
                "chunks": len(chunks),
                "territory": territory,
                "status": "ingested",
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })

            print(f"  OK: {len(chunks)} chunks indexados", flush=True)

        except Exception as e:
            print(f"  ERROR DB/embeddings: {e}", flush=True)
            logger.error("DB/embedding error for %s: %s", rel_path, e)
            stats["errors"] += 1
            remaining_pending.append(entry)
            # Try to mark the doc as errored
            try:
                await db.execute(
                    "UPDATE documents SET processing_status = 'error', error_message = ? WHERE id = ?",
                    [str(e), doc_id],
                )
            except Exception:
                pass

    # 5. Update files
    if not dry_run:
        # Write processed entries to ingested log
        for entry in processed_entries:
            append_ingested_log(entry)

        # Update pending file with remaining items
        save_pending(remaining_pending)

        # Rebuild FTS5 if new chunks were added
        if stats["chunks"] > 0:
            print("\nReconstruyendo indice FTS5...", flush=True)
            try:
                await db.execute("DROP TABLE IF EXISTS document_chunks_fts")
                await db.execute("""
                    CREATE VIRTUAL TABLE document_chunks_fts USING fts5(
                        chunk_id UNINDEXED,
                        content
                    )
                """)
                await db.execute("""
                    INSERT INTO document_chunks_fts(chunk_id, content)
                    SELECT id, content FROM document_chunks
                """)
                r = await db.execute("SELECT COUNT(*) as cnt FROM document_chunks")
                count = r.rows[0]["cnt"]
                print(f"FTS5 reconstruido: {count} chunks indexados", flush=True)
            except Exception as e:
                print(f"Error reconstruyendo FTS5: {e}", flush=True)

        await db.disconnect()

    # 6. Summary
    print(flush=True)
    print("=" * 60, flush=True)
    print("AUTO-INGESTA COMPLETADA", flush=True)
    print(f"  Procesados:       {stats['processed']}", flush=True)
    print(f"  Saltados (hash):  {stats['skipped_hash']}", flush=True)
    print(f"  Saltados (otros): {stats['skipped_missing']}", flush=True)
    print(f"  Errores:          {stats['errors']}", flush=True)
    print(f"  Chunks totales:   {stats['chunks']}", flush=True)
    if remaining_pending:
        print(f"  Pendientes rest.: {len(remaining_pending)}", flush=True)
    print("=" * 60, flush=True)

    return 1 if stats["errors"] > 0 else 0


# ── CLI ─────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="TaxIA -- Auto-Ingesta RAG: procesa documentos pendientes del crawler",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Mostrar que se procesaria sin modificar la DB",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=None,
        help="Maximo N documentos por ejecucion",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(auto_ingest(dry_run=args.dry_run, limit=args.limit))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
