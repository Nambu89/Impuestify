"""
Tests for auto_ingest.py -- RAG auto-ingestion pipeline.

Tests cover:
1. No pending documents -> clean exit
2. One pending file -> processes and moves to log
3. File already ingested (same SHA) -> skip
4. File does not exist -> logged and skipped
5. --dry-run does not modify anything
6. --limit N only processes N documents
7. Malformed _pending_ingest.json -> handles gracefully
8. Unsupported file type -> skip
"""
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend is in path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# We need to mock heavy dependencies before importing auto_ingest
# since it imports from ingest_documents which has Azure/OpenAI deps


@pytest.fixture
def tmp_docs(tmp_path):
    """Create a temporary docs directory with test files."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()

    # Create a small test PDF-like file
    pdf_file = docs_dir / "Madrid" / "test_doc.pdf"
    pdf_file.parent.mkdir(parents=True, exist_ok=True)
    pdf_file.write_bytes(b"%PDF-1.4 test content for hashing purposes " * 10)

    # Create a markdown file
    md_file = docs_dir / "Estatal" / "test_doc.md"
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text("# Test Document\n\nThis is test content for the markdown ingestion pipeline." * 5, encoding="utf-8")

    return docs_dir


@pytest.fixture
def pending_json(tmp_docs):
    """Create a _pending_ingest.json with test entries."""
    data = {
        "generated_at": "2026-03-27T10:00:00+00:00",
        "count": 1,
        "files": [
            {
                "path": "Madrid/test_doc.pdf",
                "status": "new",
                "url": "https://example.com/test.pdf",
                "size": 1234,
            }
        ],
    }
    pending_file = tmp_docs / "_pending_ingest.json"
    with open(pending_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return pending_file


def _compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Mock DB helper ──────────────────────────────────────────────

def _make_mock_db(existing_hashes=None):
    """Create a mock TursoClient."""
    mock_db = AsyncMock()

    # connect/disconnect
    mock_db.connect = AsyncMock()
    mock_db.disconnect = AsyncMock()

    # execute returns different results depending on query
    async def mock_execute(query, params=None):
        result = MagicMock()
        if "SELECT hash FROM documents" in query:
            if existing_hashes:
                result.rows = [{"hash": h} for h in existing_hashes]
            else:
                result.rows = []
        elif "SELECT COUNT" in query:
            result.rows = [{"cnt": 42}]
        else:
            result.rows = []
        return result

    mock_db.execute = AsyncMock(side_effect=mock_execute)
    return mock_db


# ── Mock chunker/extractor/embedder ────────────────────────────

class MockChunk:
    def __init__(self, content, chunk_index=0, page_number=1):
        self.content = content
        self.chunk_index = chunk_index
        self.page_number = page_number


def _mock_chunker():
    chunker = MagicMock()
    chunker.chunk_document.return_value = [
        MockChunk("Test chunk content number one", chunk_index=0),
        MockChunk("Test chunk content number two", chunk_index=1),
    ]
    return chunker


def _mock_extractor():
    extractor = MagicMock()
    extractor.extract.return_value = {
        "content": "Extracted PDF content " * 20,
        "pages": [{"page_number": 1, "content": "Extracted PDF content " * 20}],
        "total_pages": 1,
        "tables_count": 0,
        "file_hash": "abc123",
    }
    return extractor


def _mock_embedder():
    embedder = MagicMock()
    embedder.generate.return_value = [[0.1] * 1536, [0.2] * 1536]
    embedder.MODEL = "text-embedding-3-large"
    embedder.DIMENSIONS = 1536
    return embedder


# ── Patch helper ────────────────────────────────────────────────

def _patch_auto_ingest(tmp_docs, mock_db=None, mock_extractor_inst=None, mock_embedder_inst=None, mock_chunker_inst=None):
    """Return a dict of patches for auto_ingest module."""
    if mock_db is None:
        mock_db = _make_mock_db()
    if mock_extractor_inst is None:
        mock_extractor_inst = _mock_extractor()
    if mock_embedder_inst is None:
        mock_embedder_inst = _mock_embedder()
    if mock_chunker_inst is None:
        mock_chunker_inst = _mock_chunker()

    patches = {
        "DOCS_DIR": tmp_docs,
        "PENDING_INGEST": tmp_docs / "_pending_ingest.json",
        "INGESTED_LOG": tmp_docs / "_ingested_log.json",
        "TursoClient": MagicMock(return_value=mock_db),
        "AzureDocumentExtractor": MagicMock(return_value=mock_extractor_inst),
        "OpenAIEmbeddingGenerator": MagicMock(return_value=mock_embedder_inst),
        "DocumentLayoutChunker": MagicMock(return_value=mock_chunker_inst),
    }
    return patches


# ═══════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════

class TestAutoIngestNoPending:
    """Test 1: No pending documents -> exit clean."""

    def test_no_pending_file(self, tmp_docs):
        """No _pending_ingest.json at all."""
        from scripts.auto_ingest import load_pending, PENDING_INGEST

        # Temporarily override module-level constant
        import scripts.auto_ingest as mod
        original = mod.PENDING_INGEST
        mod.PENDING_INGEST = tmp_docs / "_pending_ingest.json"
        # Remove file if it exists
        if mod.PENDING_INGEST.exists():
            mod.PENDING_INGEST.unlink()

        try:
            result = load_pending()
            assert result == []
        finally:
            mod.PENDING_INGEST = original

    def test_empty_pending_file(self, tmp_docs):
        """_pending_ingest.json exists but with empty files list."""
        import scripts.auto_ingest as mod
        from scripts.auto_ingest import load_pending
        original = mod.PENDING_INGEST

        pending_file = tmp_docs / "_pending_ingest.json"
        with open(pending_file, "w") as f:
            json.dump({"generated_at": "2026-01-01", "count": 0, "files": []}, f)

        mod.PENDING_INGEST = pending_file
        try:
            result = load_pending()
            assert result == []
        finally:
            mod.PENDING_INGEST = original

    def test_no_pending_returns_zero(self, tmp_docs):
        """auto_ingest() returns 0 when no pending docs."""
        import scripts.auto_ingest as mod
        original_pending = mod.PENDING_INGEST
        # Point to non-existent file
        mod.PENDING_INGEST = tmp_docs / "_nonexistent.json"
        try:
            exit_code = asyncio.run(mod.auto_ingest(dry_run=True))
            assert exit_code == 0
        finally:
            mod.PENDING_INGEST = original_pending


class TestAutoIngestProcessFile:
    """Test 2: One pending file -> processes and moves to log."""

    def test_process_one_file(self, tmp_docs, pending_json):
        """A single pending PDF is processed and logged."""
        import scripts.auto_ingest as mod

        mock_db = _make_mock_db()
        patches = _patch_auto_ingest(tmp_docs, mock_db=mock_db)

        original_vals = {}
        for key, val in patches.items():
            original_vals[key] = getattr(mod, key)
            setattr(mod, key, val)

        try:
            exit_code = asyncio.run(mod.auto_ingest(dry_run=False))
            assert exit_code == 0

            # Check ingested log was written
            log_file = tmp_docs / "_ingested_log.json"
            assert log_file.exists()
            with open(log_file, "r") as f:
                log_entries = json.load(f)
            assert len(log_entries) >= 1
            assert log_entries[0]["status"] == "ingested"
            assert log_entries[0]["path"] == "Madrid/test_doc.pdf"

            # Check pending was cleared (or file removed)
            pending_file = tmp_docs / "_pending_ingest.json"
            if pending_file.exists():
                with open(pending_file, "r") as f:
                    data = json.load(f)
                assert data.get("count", 0) == 0 or len(data.get("files", [])) == 0
        finally:
            for key, val in original_vals.items():
                setattr(mod, key, val)


class TestAutoIngestDuplicateHash:
    """Test 3: File already ingested (same SHA-256) -> skip."""

    def test_skip_duplicate_hash(self, tmp_docs, pending_json):
        """Document with matching hash in DB is skipped."""
        import scripts.auto_ingest as mod

        # Compute the real hash of the test file
        test_file = tmp_docs / "Madrid" / "test_doc.pdf"
        real_hash = _compute_sha256(test_file)

        mock_db = _make_mock_db(existing_hashes={real_hash})
        patches = _patch_auto_ingest(tmp_docs, mock_db=mock_db)

        original_vals = {}
        for key, val in patches.items():
            original_vals[key] = getattr(mod, key)
            setattr(mod, key, val)

        try:
            exit_code = asyncio.run(mod.auto_ingest(dry_run=False))
            assert exit_code == 0

            # Check it was logged as skipped
            log_file = tmp_docs / "_ingested_log.json"
            assert log_file.exists()
            with open(log_file, "r") as f:
                log_entries = json.load(f)
            assert len(log_entries) >= 1
            assert log_entries[0]["status"] == "skipped_duplicate"

            # DB should NOT have received any INSERT INTO documents
            insert_calls = [
                call for call in mock_db.execute.call_args_list
                if call.args and "INSERT INTO documents" in str(call.args[0])
            ]
            assert len(insert_calls) == 0
        finally:
            for key, val in original_vals.items():
                setattr(mod, key, val)


class TestAutoIngestFileMissing:
    """Test 4: File does not exist -> error logged, skip."""

    def test_missing_file_skip(self, tmp_docs):
        """Entry pointing to non-existent file is skipped gracefully."""
        import scripts.auto_ingest as mod

        # Create pending with non-existent file
        data = {
            "generated_at": "2026-03-27T10:00:00+00:00",
            "count": 1,
            "files": [
                {
                    "path": "NoExiste/phantom.pdf",
                    "status": "new",
                    "url": "https://example.com/phantom.pdf",
                    "size": 999,
                }
            ],
        }
        pending_file = tmp_docs / "_pending_ingest.json"
        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        patches = _patch_auto_ingest(tmp_docs)
        original_vals = {}
        for key, val in patches.items():
            original_vals[key] = getattr(mod, key)
            setattr(mod, key, val)

        try:
            exit_code = asyncio.run(mod.auto_ingest(dry_run=False))
            # Should not crash, no errors (skipped != error)
            assert exit_code == 0
        finally:
            for key, val in original_vals.items():
                setattr(mod, key, val)


class TestAutoIngestDryRun:
    """Test 5: --dry-run does not modify anything."""

    def test_dry_run_no_writes(self, tmp_docs, pending_json):
        """Dry run does not write to DB or modify pending/log files."""
        import scripts.auto_ingest as mod

        original_pending = mod.PENDING_INGEST
        original_log = mod.INGESTED_LOG
        original_docs = mod.DOCS_DIR

        mod.PENDING_INGEST = pending_json
        mod.INGESTED_LOG = tmp_docs / "_ingested_log.json"
        mod.DOCS_DIR = tmp_docs

        try:
            # Capture pending content before
            with open(pending_json, "r") as f:
                before = f.read()

            exit_code = asyncio.run(mod.auto_ingest(dry_run=True))
            assert exit_code == 0

            # Pending file should be unchanged
            with open(pending_json, "r") as f:
                after = f.read()
            assert before == after

            # No ingested log should be created
            log_file = tmp_docs / "_ingested_log.json"
            assert not log_file.exists()
        finally:
            mod.PENDING_INGEST = original_pending
            mod.INGESTED_LOG = original_log
            mod.DOCS_DIR = original_docs


class TestAutoIngestLimit:
    """Test 6: --limit N only processes N documents."""

    def test_limit_one(self, tmp_docs):
        """With 2 pending files and --limit 1, only 1 is processed."""
        import scripts.auto_ingest as mod

        # Create 2 test files
        file1 = tmp_docs / "Madrid" / "doc1.pdf"
        file1.parent.mkdir(parents=True, exist_ok=True)
        file1.write_bytes(b"%PDF-1.4 document one content " * 10)

        file2 = tmp_docs / "Estatal" / "doc2.pdf"
        file2.parent.mkdir(parents=True, exist_ok=True)
        file2.write_bytes(b"%PDF-1.4 document two content " * 10)

        # Create pending with 2 entries
        data = {
            "generated_at": "2026-03-27T10:00:00+00:00",
            "count": 2,
            "files": [
                {"path": "Madrid/doc1.pdf", "status": "new", "url": "https://example.com/1.pdf", "size": 100},
                {"path": "Estatal/doc2.pdf", "status": "new", "url": "https://example.com/2.pdf", "size": 200},
            ],
        }
        pending_file = tmp_docs / "_pending_ingest.json"
        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        mock_db = _make_mock_db()
        patches = _patch_auto_ingest(tmp_docs, mock_db=mock_db)

        original_vals = {}
        for key, val in patches.items():
            original_vals[key] = getattr(mod, key)
            setattr(mod, key, val)

        try:
            exit_code = asyncio.run(mod.auto_ingest(dry_run=False, limit=1))
            assert exit_code == 0

            # Check that only 1 was ingested
            log_file = tmp_docs / "_ingested_log.json"
            assert log_file.exists()
            with open(log_file, "r") as f:
                log_entries = json.load(f)
            ingested = [e for e in log_entries if e["status"] == "ingested"]
            assert len(ingested) == 1
            assert ingested[0]["path"] == "Madrid/doc1.pdf"

            # Check remaining pending has 1 entry
            if pending_file.exists():
                with open(pending_file, "r") as f:
                    remaining = json.load(f)
                assert len(remaining.get("files", [])) == 1
                assert remaining["files"][0]["path"] == "Estatal/doc2.pdf"
        finally:
            for key, val in original_vals.items():
                setattr(mod, key, val)


class TestAutoIngestMalformedJson:
    """Test 7: Malformed _pending_ingest.json is handled."""

    def test_malformed_json(self, tmp_docs):
        """Corrupted JSON file does not crash the pipeline."""
        import scripts.auto_ingest as mod

        pending_file = tmp_docs / "_pending_ingest.json"
        pending_file.write_text("{broken json!!!", encoding="utf-8")

        original = mod.PENDING_INGEST
        mod.PENDING_INGEST = pending_file

        try:
            result = mod.load_pending()
            assert result == []
        finally:
            mod.PENDING_INGEST = original


class TestAutoIngestUnsupportedType:
    """Test 8: Unsupported file type is skipped."""

    def test_unsupported_extension(self, tmp_docs):
        """A .docx file in the pending list is skipped."""
        import scripts.auto_ingest as mod

        # Create a .docx file
        docx_file = tmp_docs / "test.docx"
        docx_file.write_bytes(b"PK fake docx content " * 10)

        data = {
            "generated_at": "2026-03-27T10:00:00+00:00",
            "count": 1,
            "files": [
                {"path": "test.docx", "status": "new", "url": "https://example.com/test.docx", "size": 100},
            ],
        }
        pending_file = tmp_docs / "_pending_ingest.json"
        with open(pending_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        patches = _patch_auto_ingest(tmp_docs)
        original_vals = {}
        for key, val in patches.items():
            original_vals[key] = getattr(mod, key)
            setattr(mod, key, val)

        try:
            exit_code = asyncio.run(mod.auto_ingest(dry_run=False))
            assert exit_code == 0
        finally:
            for key, val in original_vals.items():
                setattr(mod, key, val)


class TestSavePending:
    """Test save_pending helper."""

    def test_save_empty_removes_file(self, tmp_docs):
        """Saving empty list removes the pending file."""
        import scripts.auto_ingest as mod

        pending_file = tmp_docs / "_pending_ingest.json"
        pending_file.write_text("{}", encoding="utf-8")

        original = mod.PENDING_INGEST
        mod.PENDING_INGEST = pending_file

        try:
            mod.save_pending([])
            assert not pending_file.exists()
        finally:
            mod.PENDING_INGEST = original

    def test_save_preserves_remaining(self, tmp_docs):
        """Saving non-empty list writes correct JSON."""
        import scripts.auto_ingest as mod

        pending_file = tmp_docs / "_pending_ingest.json"
        original = mod.PENDING_INGEST
        mod.PENDING_INGEST = pending_file

        try:
            remaining = [{"path": "test.pdf", "status": "new", "url": "", "size": 0}]
            mod.save_pending(remaining)
            assert pending_file.exists()
            with open(pending_file, "r") as f:
                data = json.load(f)
            assert data["count"] == 1
            assert len(data["files"]) == 1
        finally:
            mod.PENDING_INGEST = original


class TestAppendIngestedLog:
    """Test append_ingested_log helper."""

    def test_append_creates_file(self, tmp_docs):
        """First append creates the log file."""
        import scripts.auto_ingest as mod

        log_file = tmp_docs / "_ingested_log.json"
        original = mod.INGESTED_LOG
        mod.INGESTED_LOG = log_file

        try:
            mod.append_ingested_log({"path": "test.pdf", "status": "ingested"})
            assert log_file.exists()
            with open(log_file, "r") as f:
                entries = json.load(f)
            assert len(entries) == 1
        finally:
            mod.INGESTED_LOG = original

    def test_append_accumulates(self, tmp_docs):
        """Multiple appends accumulate entries."""
        import scripts.auto_ingest as mod

        log_file = tmp_docs / "_ingested_log.json"
        original = mod.INGESTED_LOG
        mod.INGESTED_LOG = log_file

        try:
            mod.append_ingested_log({"path": "a.pdf", "status": "ingested"})
            mod.append_ingested_log({"path": "b.pdf", "status": "ingested"})
            with open(log_file, "r") as f:
                entries = json.load(f)
            assert len(entries) == 2
        finally:
            mod.INGESTED_LOG = original
