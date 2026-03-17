"""
Scan existing RAG documents for integrity issues.

Reads each document from the `documents` table, locates its PDF in the docs/
directory, extracts text with PyMuPDF (fitz), and runs DocumentIntegrityScanner.
Updates integrity_score and integrity_findings in the documents table.

Results:
  integrity_score  — 0.0-1.0 composite risk (lower = worse). NULL means not scanned.
  integrity_findings — JSON array of Finding dicts, or a JSON status string.

Usage:
    python -m backend.scripts.scan_existing_docs [--dry-run] [--limit N]

Options:
    --dry-run   Scan and print results without writing to the DB.
    --limit N   Process at most N documents (useful for testing).

Notes:
- Idempotent: re-running updates previously scanned documents.
- Fail-open: if a PDF cannot be found or read, integrity_score is set to NULL
  and integrity_findings is set to {"status": "not_found"} or {"status": "read_error"}.
  The document is NOT excluded from RAG searches (trust defaults to 1.0).
- PyMuPDF (fitz) must be installed: pip install PyMuPDF
"""
import sys
import os
import asyncio
import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))
sys.path.insert(0, BACKEND_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.database.turso_client import TursoClient
from app.security.document_integrity import DocumentIntegrityScanner

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Root of RAG document store
DOCS_ROOT = Path(PROJECT_ROOT) / "docs"

# Scanner singleton
scanner = DocumentIntegrityScanner()


def _find_pdf(filename: str, filepath: str | None) -> Path | None:
    """
    Attempt to locate a PDF file on disk given its filename and optional
    filepath hint stored in the database.

    Search order:
    1. filepath column (if not empty)
    2. Recursive glob under DOCS_ROOT for the exact filename
    3. Case-insensitive fallback glob
    """
    # 1. Explicit filepath from DB
    if filepath:
        candidate = Path(filepath)
        if candidate.is_file():
            return candidate
        # Try relative to PROJECT_ROOT
        candidate2 = Path(PROJECT_ROOT) / filepath
        if candidate2.is_file():
            return candidate2

    if not filename:
        return None

    # 2. Exact match under docs/
    for match in DOCS_ROOT.rglob(filename):
        return match

    # 3. Case-insensitive fallback
    lower_name = filename.lower()
    for match in DOCS_ROOT.rglob("*"):
        if match.name.lower() == lower_name:
            return match

    return None


def _extract_text(pdf_path: Path) -> str:
    """Extract plain text from a PDF using PyMuPDF. Returns empty string on error."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        pages_text = []
        for page in doc:
            pages_text.append(page.get_text())
        doc.close()
        return "\n".join(pages_text)
    except Exception as exc:
        logger.debug("fitz extraction failed for %s: %s", pdf_path, exc)
        return ""


async def scan_documents(dry_run: bool = False, limit: int | None = None) -> None:
    """Main scanning loop. Connects to Turso, iterates documents, updates scores."""
    db = TursoClient()
    await db.connect()

    try:
        # Fetch all documents (or limited batch)
        query = "SELECT id, filename, filepath FROM documents ORDER BY id"
        if limit:
            query += f" LIMIT {limit}"
        result = await db.execute(query, [])
        docs = result.rows or []

        total = len(docs)
        logger.info("Found %d documents to scan%s.", total, f" (limit={limit})" if limit else "")

        stats = {"clean": 0, "warn": 0, "blocked": 0, "not_found": 0, "read_error": 0}

        for idx, row in enumerate(docs, start=1):
            doc_id = row["id"]
            filename = row.get("filename") or ""
            filepath = row.get("filepath") or ""

            logger.info("[%d/%d] %s — %s", idx, total, doc_id, filename)

            # Locate PDF on disk
            pdf_path = _find_pdf(filename, filepath)
            if pdf_path is None:
                logger.warning("  PDF not found: %s (filepath=%r)", filename, filepath)
                integrity_score = None  # NULL = not scanned (trust defaults to 1.0)
                integrity_findings = json.dumps({"status": "not_found", "filename": filename})
                stats["not_found"] += 1
            else:
                # Extract text
                text = _extract_text(pdf_path)
                if not text:
                    logger.warning("  Could not extract text from %s", pdf_path)
                    integrity_score = None
                    integrity_findings = json.dumps({"status": "read_error", "path": str(pdf_path)})
                    stats["read_error"] += 1
                else:
                    # Scan
                    scan_result = scanner.scan(text, source="crawler")
                    integrity_score = scan_result.risk_score
                    integrity_findings = json.dumps([asdict(f) for f in scan_result.findings])

                    if scan_result.risk_score >= 0.8:
                        stats["blocked"] += 1
                        logger.warning(
                            "  BLOCKED risk=%.2f findings=%d — %s",
                            scan_result.risk_score, len(scan_result.findings), filename,
                        )
                    elif scan_result.risk_score >= 0.3:
                        stats["warn"] += 1
                        logger.warning(
                            "  WARN    risk=%.2f findings=%d — %s",
                            scan_result.risk_score, len(scan_result.findings), filename,
                        )
                    else:
                        stats["clean"] += 1
                        logger.info(
                            "  clean   risk=%.2f — %s",
                            scan_result.risk_score, filename,
                        )

            # Write results to DB (unless dry-run)
            if not dry_run:
                await db.execute(
                    """
                    UPDATE documents
                    SET integrity_score = ?,
                        integrity_findings = ?
                    WHERE id = ?
                    """,
                    [integrity_score, integrity_findings, doc_id],
                )

        # Summary
        logger.info(
            "\nScan complete (%d docs%s): %d clean, %d warnings, %d blocked, "
            "%d not_found, %d read_error%s",
            total,
            f" of {limit} max" if limit else "",
            stats["clean"],
            stats["warn"],
            stats["blocked"],
            stats["not_found"],
            stats["read_error"],
            " [DRY RUN — no DB changes]" if dry_run else "",
        )

    finally:
        await db.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan existing RAG documents for integrity issues."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and print results without writing to the DB.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Process at most N documents (useful for testing).",
    )
    args = parser.parse_args()

    asyncio.run(scan_documents(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
