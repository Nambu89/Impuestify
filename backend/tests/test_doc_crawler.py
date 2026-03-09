"""
Tests for the automated document crawler.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.scripts.doc_crawler.config import MIN_FILE_SIZE_BYTES
from backend.scripts.doc_crawler.crawler import (
    compute_hash,
    download_document,
    reset_session_state,
    validate_file,
)
from backend.scripts.doc_crawler.inventory import (
    generate_report,
    load_inventory,
    save_inventory,
    update_document,
)
from backend.scripts.doc_crawler.notifier import append_log, write_pending_ingest
from backend.scripts.doc_crawler.watchlist import (
    ALL_ITEMS,
    get_items,
    get_stats,
    get_territories,
)


# ── Validate File Tests ─────────────────────────────────────────


class TestValidateFile:
    def test_valid_pdf(self, tmp_path):
        p = tmp_path / "test.pdf"
        p.write_bytes(b"%PDF-1.7" + b"\x00" * (MIN_FILE_SIZE_BYTES + 100))
        assert validate_file(p, "pdf") is True

    def test_invalid_pdf_magic(self, tmp_path):
        p = tmp_path / "test.pdf"
        p.write_bytes(b"NOT A PDF" + b"\x00" * (MIN_FILE_SIZE_BYTES + 100))
        assert validate_file(p, "pdf") is False

    def test_pdf_too_small(self, tmp_path):
        p = tmp_path / "test.pdf"
        p.write_bytes(b"%PDF-1.7" + b"\x00" * 100)
        assert validate_file(p, "pdf") is False

    def test_valid_xlsx(self, tmp_path):
        p = tmp_path / "test.xlsx"
        p.write_bytes(b"PK\x03\x04" + b"\x00" * (MIN_FILE_SIZE_BYTES + 100))
        assert validate_file(p, "xlsx") is True

    def test_invalid_xlsx(self, tmp_path):
        p = tmp_path / "test.xlsx"
        p.write_bytes(b"NOT XLSX" + b"\x00" * (MIN_FILE_SIZE_BYTES + 100))
        assert validate_file(p, "xlsx") is False

    def test_valid_xls(self, tmp_path):
        p = tmp_path / "test.xls"
        p.write_bytes(b"\xd0\xcf\x11\xe0" + b"\x00" * (MIN_FILE_SIZE_BYTES + 100))
        assert validate_file(p, "xls") is True

    def test_nonexistent_file(self, tmp_path):
        p = tmp_path / "ghost.pdf"
        assert validate_file(p, "pdf") is False


# ── Hash Tests ───────────────────────────────────────────────────


class TestComputeHash:
    def test_deterministic(self, tmp_path):
        p = tmp_path / "test.pdf"
        p.write_bytes(b"%PDF-1.7 test content")
        h1 = compute_hash(p)
        h2 = compute_hash(p)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_content(self, tmp_path):
        p1 = tmp_path / "a.pdf"
        p2 = tmp_path / "b.pdf"
        p1.write_bytes(b"%PDF content A")
        p2.write_bytes(b"%PDF content B")
        assert compute_hash(p1) != compute_hash(p2)


# ── Watchlist Tests ──────────────────────────────────────────────


class TestWatchlist:
    def test_all_items_not_empty(self):
        assert len(ALL_ITEMS) > 0

    def test_minimum_high_priority(self):
        high = get_items(priority="high")
        assert len(high) >= 10, f"Expected >= 10 high priority items, got {len(high)}"

    def test_total_items(self):
        assert len(ALL_ITEMS) >= 40, f"Expected >= 40 total items, got {len(ALL_ITEMS)}"

    def test_filter_by_territory(self):
        aeat = get_items(territory="AEAT")
        assert len(aeat) > 0
        assert all(i.territory == "AEAT" for i in aeat)

    def test_filter_by_priority(self):
        medium = get_items(priority="medium")
        assert all(i.priority == "medium" for i in medium)

    def test_territories_list(self):
        territories = get_territories()
        assert "AEAT" in territories
        assert "Estatal" in territories
        assert len(territories) >= 5

    def test_stats(self):
        stats = get_stats()
        assert stats["total"] == len(ALL_ITEMS)
        assert "high" in stats["by_priority"]
        assert sum(stats["by_priority"].values()) == stats["total"]

    def test_all_items_have_required_fields(self):
        for item in ALL_ITEMS:
            assert item.url, f"Missing URL: {item.dest}"
            assert item.dest, f"Missing dest: {item.url}"
            assert item.territory, f"Missing territory: {item.dest}"
            assert item.file_type in ("pdf", "xlsx", "xls"), f"Bad file_type: {item.file_type}"
            assert item.priority in ("high", "medium", "low"), f"Bad priority: {item.priority}"
            assert item.status in ("active", "future", "html_only"), f"Bad status: {item.status}"

    def test_no_duplicate_destinations(self):
        dests = [item.dest for item in ALL_ITEMS]
        assert len(dests) == len(set(dests)), "Duplicate destinations found"


# ── Inventory Tests ──────────────────────────────────────────────


class TestInventory:
    def test_load_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.scripts.doc_crawler.inventory.INVENTORY_INDEX",
            tmp_path / "nonexistent.json",
        )
        inv = load_inventory()
        assert inv["version"] == 1
        assert inv["documents"] == {}

    def test_save_and_load(self, tmp_path, monkeypatch):
        idx_path = tmp_path / "index.json"
        monkeypatch.setattr(
            "backend.scripts.doc_crawler.inventory.INVENTORY_INDEX", idx_path
        )
        inv = {"version": 1, "last_run": None, "documents": {"test.pdf": {"hash": "abc"}}}
        save_inventory(inv)
        loaded = load_inventory()
        assert loaded["documents"]["test.pdf"]["hash"] == "abc"
        assert loaded["last_run"] is not None

    def test_update_document_new(self):
        inv = {"documents": {}}
        update_document(inv, "test.pdf", "http://example.com", "abc123", 1000, "new")
        assert "test.pdf" in inv["documents"]
        assert inv["documents"]["test.pdf"]["hash"] == "abc123"
        assert inv["documents"]["test.pdf"]["source_url"] == "http://example.com"

    def test_update_document_existing(self):
        inv = {"documents": {"test.pdf": {"hash": "old", "size": 500, "download_date": "2026-01-01"}}}
        update_document(inv, "test.pdf", "http://example.com", "newhash", 2000, "updated")
        assert inv["documents"]["test.pdf"]["hash"] == "newhash"
        assert inv["documents"]["test.pdf"]["size"] == 2000

    def test_generate_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.scripts.doc_crawler.inventory.CRAWLER_REPORT",
            tmp_path / "report.md",
        )
        results = [
            {"status": "new", "dest": "test1.pdf", "url": "http://a.com", "size": 50000, "success": True},
            {"status": "unchanged", "dest": "test2.pdf", "url": "http://b.com", "success": True},
            {"status": "failed", "dest": "test3.pdf", "message": "timeout", "success": False},
        ]
        text = generate_report(results)
        assert "New Documents" in text
        assert "test1.pdf" in text
        assert "Failed" in text
        assert (tmp_path / "report.md").exists()


# ── Notifier Tests ───────────────────────────────────────────────


class TestNotifier:
    def test_append_log(self, tmp_path, monkeypatch):
        log_path = tmp_path / "log.json"
        monkeypatch.setattr("backend.scripts.doc_crawler.notifier.CRAWLER_LOG", log_path)
        results = [
            {"status": "new", "dest": "a.pdf", "success": True},
            {"status": "failed", "dest": "b.pdf", "message": "err", "success": False},
        ]
        append_log(results)
        data = json.loads(log_path.read_text())
        assert len(data) == 1
        assert data[0]["new"] == 1
        assert data[0]["failed"] == 1

    def test_write_pending_ingest_creates_file(self, tmp_path, monkeypatch):
        pi_path = tmp_path / "pending.json"
        monkeypatch.setattr("backend.scripts.doc_crawler.notifier.PENDING_INGEST", pi_path)
        results = [
            {"status": "new", "dest": "a.pdf", "url": "http://a.com", "size": 1000, "success": True},
        ]
        write_pending_ingest(results)
        assert pi_path.exists()
        data = json.loads(pi_path.read_text())
        assert data["count"] == 1
        assert data["files"][0]["path"] == "a.pdf"

    def test_write_pending_ingest_no_new(self, tmp_path, monkeypatch):
        pi_path = tmp_path / "pending.json"
        pi_path.write_text("{}")
        monkeypatch.setattr("backend.scripts.doc_crawler.notifier.PENDING_INGEST", pi_path)
        results = [
            {"status": "unchanged", "dest": "a.pdf", "success": True},
        ]
        write_pending_ingest(results)
        assert not pi_path.exists()  # Stale file removed


# ── Robots Tests ─────────────────────────────────────────────────


class TestRobots:
    def test_can_fetch_no_robots(self):
        from backend.scripts.doc_crawler.robots import can_fetch, clear_cache
        clear_cache()
        # For a domain with no robots.txt, should allow (fail open)
        with patch("backend.scripts.doc_crawler.robots.RobotFileParser") as mock_rp:
            instance = MagicMock()
            instance.read.side_effect = Exception("No robots.txt")
            mock_rp.return_value = instance
            assert can_fetch("http://example-no-robots.test/doc.pdf") is True


# ── Download Tests (mocked HTTP) ────────────────────────────────


class TestDownload:
    def setup_method(self):
        reset_session_state()

    def test_dry_run_new(self, tmp_path):
        dest = tmp_path / "new.pdf"
        result = download_document("http://example.com/doc.pdf", dest, dry_run=True)
        assert result["status"] == "would_download"
        assert not dest.exists()

    def test_dry_run_existing(self, tmp_path):
        dest = tmp_path / "existing.pdf"
        dest.write_bytes(b"%PDF-1.7" + b"\x00" * (MIN_FILE_SIZE_BYTES + 100))
        result = download_document("http://example.com/doc.pdf", dest, dry_run=True)
        assert result["status"] == "would_skip"

    @patch("backend.scripts.doc_crawler.crawler.can_fetch", return_value=False)
    def test_robots_blocked(self, mock_robots, tmp_path):
        dest = tmp_path / "blocked.pdf"
        result = download_document("http://example.com/doc.pdf", dest)
        assert result["status"] == "robots_blocked"

    @patch("backend.scripts.doc_crawler.crawler.can_fetch", return_value=True)
    @patch("backend.scripts.doc_crawler.crawler.requests.get")
    def test_successful_download(self, mock_get, mock_robots, tmp_path):
        content = b"%PDF-1.7 test document content" + b"\x00" * MIN_FILE_SIZE_BYTES
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = content
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        dest = tmp_path / "subdir" / "new.pdf"
        result = download_document("http://example.com/doc.pdf", dest)
        assert result["success"] is True
        assert result["status"] == "new"
        assert dest.exists()
        assert "hash" in result

    @patch("backend.scripts.doc_crawler.crawler.can_fetch", return_value=True)
    @patch("backend.scripts.doc_crawler.crawler.requests.get")
    def test_rate_limited_429(self, mock_get, mock_robots, tmp_path):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        dest = tmp_path / "limited.pdf"
        result = download_document("http://ratelimited.com/doc.pdf", dest)
        assert result["status"] == "rate_limited"
        assert result["success"] is False

        # Second request to same domain should be blocked
        result2 = download_document("http://ratelimited.com/other.pdf", tmp_path / "other.pdf")
        assert result2["status"] == "blocked"
