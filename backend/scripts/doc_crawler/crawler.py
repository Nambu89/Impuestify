"""
Core download engine — download, validate, deduplicate documents.
"""
import hashlib
import logging
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import requests

from .config import (
    BACKOFF_SCHEDULE_S,
    DOCS_DIR,
    HEADERS,
    INTER_REQUEST_DELAY_S,
    MAX_DOWNLOADS_PER_DOMAIN,
    MIN_FILE_SIZE_BYTES,
    PDF_MAGIC,
    PROJECT_ROOT,
    REQUEST_TIMEOUT_S,
    XLS_MAGIC,
    XLSX_MAGIC,
)
from .robots import can_fetch

# ── Document Integrity Scanner ─────────────────────────────────────────────────
# Ensure backend/ is in sys.path so app.security imports resolve when the
# crawler is executed as a standalone script (not via FastAPI).
_BACKEND_ROOT = str(PROJECT_ROOT / "backend")
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

try:
    from app.security.document_integrity import document_integrity_scanner as _dis
    _DIS_AVAILABLE = True
except Exception as _dis_import_err:  # pragma: no cover
    logger_pre = logging.getLogger(__name__)
    logger_pre.warning("Document integrity scanner unavailable: %s", _dis_import_err)
    _DIS_AVAILABLE = False
    _dis = None  # type: ignore

logger = logging.getLogger(__name__)


# Track downloads per domain and last request time
_domain_counts: dict[str, int] = defaultdict(int)
_domain_last_request: dict[str, float] = {}
_blocked_domains: set[str] = set()

# Track integrity scan totals across this session
_scan_total: int = 0
_scan_clean: int = 0
_scan_quarantined: int = 0


def extract_text_for_scan(filepath: Path) -> str:
    """
    Lightweight text extraction from a PDF for integrity scanning.
    Not intended for RAG — just enough text to detect injected instructions.
    Returns empty string for non-PDFs or on any extraction error.
    """
    try:
        import fitz  # PyMuPDF — already in requirements
        doc = fitz.open(str(filepath))
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception:
        return ""


def get_scan_summary() -> dict:
    """Return cumulative integrity scan counters for this session."""
    return {
        "scanned": _scan_total,
        "clean": _scan_clean,
        "quarantined": _scan_quarantined,
    }


def _get_domain(url: str) -> str:
    return urlparse(url).netloc


def _wait_for_rate_limit(domain: str) -> None:
    """Enforce minimum delay between requests to same domain."""
    last = _domain_last_request.get(domain, 0)
    elapsed = time.time() - last
    if elapsed < INTER_REQUEST_DELAY_S:
        wait = INTER_REQUEST_DELAY_S - elapsed
        logger.debug(f"Rate limit: waiting {wait:.1f}s for {domain}")
        time.sleep(wait)


def validate_file(path: Path, file_type: str = "pdf") -> bool:
    """
    Validate downloaded file by magic bytes and minimum size.

    Args:
        path: Path to the file
        file_type: "pdf", "xlsx", or "xls"

    Returns:
        True if valid
    """
    if not path.exists():
        return False

    size = path.stat().st_size
    if size < MIN_FILE_SIZE_BYTES:
        logger.warning(f"File too small ({size} bytes): {path.name}")
        return False

    with open(path, "rb") as f:
        header = f.read(8)

    if file_type == "pdf":
        if not header.startswith(PDF_MAGIC):
            logger.warning(f"Not a valid PDF (bad magic bytes): {path.name}")
            return False
    elif file_type == "xlsx":
        if not header.startswith(XLSX_MAGIC):
            logger.warning(f"Not a valid XLSX (bad magic bytes): {path.name}")
            return False
    elif file_type == "xls":
        if not header.startswith(XLS_MAGIC):
            logger.warning(f"Not a valid XLS (bad magic bytes): {path.name}")
            return False

    return True


def compute_hash(path: Path) -> str:
    """Compute SHA-256 hash of file for deduplication."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download_document(
    url: str,
    dest_path: Path,
    file_type: str = "pdf",
    dry_run: bool = False,
) -> dict:
    """
    Download a document with rate limiting and validation.

    Returns:
        dict with keys: success, status, message, hash, size
    """
    domain = _get_domain(url)

    # Check if domain is blocked (rate limited in this session)
    if domain in _blocked_domains:
        return {
            "success": False,
            "status": "blocked",
            "message": f"Domain {domain} blocked this session (rate limited)",
        }

    # Check domain download limit
    if _domain_counts[domain] >= MAX_DOWNLOADS_PER_DOMAIN:
        return {
            "success": False,
            "status": "limit_reached",
            "message": f"Max {MAX_DOWNLOADS_PER_DOMAIN} downloads reached for {domain}",
        }

    # Check robots.txt
    if not can_fetch(url):
        return {
            "success": False,
            "status": "robots_blocked",
            "message": f"Blocked by robots.txt: {url}",
        }

    # Check if file already exists and hasn't changed
    if dest_path.exists():
        existing_hash = compute_hash(dest_path)
        # File exists — we'll compare hash after download to detect updates
    else:
        existing_hash = None

    if dry_run:
        status = "would_skip" if dest_path.exists() else "would_download"
        return {
            "success": True,
            "status": status,
            "message": f"[DRY RUN] {status}: {dest_path.name}",
        }

    # Ensure parent directory exists
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Rate limit
    _wait_for_rate_limit(domain)

    # Download with retry and backoff
    last_error = None
    for attempt, backoff in enumerate(BACKOFF_SCHEDULE_S + [None]):
        try:
            logger.info(f"Downloading: {url}")
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT_S,
                allow_redirects=True,
            )
            _domain_last_request[domain] = time.time()

            if response.status_code == 429:
                logger.warning(f"Rate limited (429) by {domain} — blocking domain")
                _blocked_domains.add(domain)
                return {
                    "success": False,
                    "status": "rate_limited",
                    "message": f"HTTP 429 from {domain} — domain blocked for this session",
                }

            response.raise_for_status()

            # Write to temp file, then validate
            temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
            with open(temp_path, "wb") as f:
                f.write(response.content)

            if not validate_file(temp_path, file_type):
                temp_path.unlink(missing_ok=True)
                return {
                    "success": False,
                    "status": "invalid",
                    "message": f"Downloaded file failed validation: {dest_path.name}",
                }

            new_hash = compute_hash(temp_path)

            # Check if file is identical to existing
            if existing_hash and new_hash == existing_hash:
                temp_path.unlink(missing_ok=True)
                return {
                    "success": True,
                    "status": "unchanged",
                    "message": f"No changes: {dest_path.name}",
                    "hash": new_hash,
                    "size": dest_path.stat().st_size,
                }

            # Move temp to final
            temp_path.replace(dest_path)
            _domain_counts[domain] += 1

            status = "updated" if existing_hash else "new"
            size = dest_path.stat().st_size
            logger.info(f"[{status.upper()}] {dest_path.name} ({size / 1024:.0f} KB)")

            # ── Integrity scan (PDFs only) ──────────────────────────────────
            integrity_score: float | None = None
            integrity_findings: list[str] = []

            if _DIS_AVAILABLE and file_type == "pdf":
                try:
                    global _scan_total, _scan_clean, _scan_quarantined
                    text = extract_text_for_scan(dest_path)
                    if text:
                        _scan_total += 1
                        scan_result = _dis.scan(text, source="crawler")
                        integrity_score = scan_result.risk_score
                        integrity_findings = [f.pattern_id for f in scan_result.findings]

                        if scan_result.risk_score > 0.6:
                            # Derive territory from dest_path relative to DOCS_DIR
                            try:
                                rel_parts = dest_path.relative_to(DOCS_DIR).parts
                                territory_dir = rel_parts[0] if len(rel_parts) > 1 else "_unknown"
                            except ValueError:
                                territory_dir = "_unknown"

                            quarantine_dir = DOCS_DIR / "_quarantine" / territory_dir
                            quarantine_dir.mkdir(parents=True, exist_ok=True)
                            quarantine_path = quarantine_dir / dest_path.name
                            shutil.move(str(dest_path), str(quarantine_path))
                            _scan_quarantined += 1

                            logger.warning(
                                "Document quarantined: %s (risk=%.2f, findings=%s)",
                                dest_path.name,
                                scan_result.risk_score,
                                integrity_findings,
                            )

                            return {
                                "success": True,
                                "status": "quarantined",
                                "message": (
                                    f"Quarantined: {dest_path.name} "
                                    f"(risk={scan_result.risk_score:.2f}, "
                                    f"findings={len(scan_result.findings)})"
                                ),
                                "hash": new_hash,
                                "size": size,
                                "integrity_score": integrity_score,
                                "integrity_findings": integrity_findings,
                            }
                        else:
                            _scan_clean += 1
                except Exception as _scan_err:
                    # Fail open — log and continue without quarantine
                    logger.warning("Integrity scan failed for %s: %s", dest_path.name, _scan_err)
            # ───────────────────────────────────────────────────────────────

            result_dict: dict = {
                "success": True,
                "status": status,
                "message": f"{status.capitalize()}: {dest_path.name} ({size / 1024:.0f} KB)",
                "hash": new_hash,
                "size": size,
            }
            if integrity_score is not None:
                result_dict["integrity_score"] = integrity_score
                result_dict["integrity_findings"] = integrity_findings
            return result_dict

        except requests.exceptions.RequestException as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if backoff is not None:
                logger.info(f"Backing off {backoff}s...")
                time.sleep(backoff)
            else:
                # All retries exhausted
                break

    return {
        "success": False,
        "status": "failed",
        "message": f"Failed after {len(BACKOFF_SCHEDULE_S) + 1} attempts: {last_error}",
    }


def reset_session_state() -> None:
    """Reset per-session counters (for testing)."""
    _domain_counts.clear()
    _domain_last_request.clear()
    _blocked_domains.clear()
