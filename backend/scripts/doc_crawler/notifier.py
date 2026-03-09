"""
Logging and notifications — crawler log + pending ingest flag.
"""
import json
import logging
from datetime import datetime, timezone

from .config import CRAWLER_LOG, MAX_LOG_ENTRIES, PENDING_INGEST

logger = logging.getLogger(__name__)


def append_log(results: list[dict]) -> None:
    """Append execution summary to the crawler log (keeps last N entries)."""
    # Load existing log
    entries = []
    if CRAWLER_LOG.exists():
        try:
            with open(CRAWLER_LOG, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, ValueError):
            entries = []

    now = datetime.now(timezone.utc).isoformat()
    new_docs = [r for r in results if r.get("status") == "new"]
    updated = [r for r in results if r.get("status") == "updated"]
    failed = [r for r in results if r.get("status") in ("failed", "invalid", "rate_limited")]

    entry = {
        "timestamp": now,
        "total_checked": len(results),
        "new": len(new_docs),
        "updated": len(updated),
        "unchanged": len([r for r in results if r.get("status") == "unchanged"]),
        "failed": len(failed),
        "new_files": [r["dest"] for r in new_docs],
        "updated_files": [r["dest"] for r in updated],
        "failed_files": [{"dest": r["dest"], "error": r.get("message", "")} for r in failed],
    }

    entries.append(entry)

    # Keep only last N entries
    if len(entries) > MAX_LOG_ENTRIES:
        entries = entries[-MAX_LOG_ENTRIES:]

    with open(CRAWLER_LOG, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    logger.info(f"Log updated: {len(entries)} total entries")


def write_pending_ingest(results: list[dict]) -> None:
    """
    Write list of new/updated files to _pending_ingest.json.
    This serves as a flag for the RAG ingestion pipeline.
    """
    actionable = [
        r for r in results
        if r.get("status") in ("new", "updated") and r.get("success")
    ]

    if not actionable:
        # Remove stale pending file if no new docs
        if PENDING_INGEST.exists():
            PENDING_INGEST.unlink()
        return

    now = datetime.now(timezone.utc).isoformat()
    data = {
        "generated_at": now,
        "count": len(actionable),
        "files": [
            {
                "path": r["dest"],
                "status": r["status"],
                "url": r.get("url", ""),
                "size": r.get("size", 0),
            }
            for r in actionable
        ],
    }

    with open(PENDING_INGEST, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Pending ingest: {len(actionable)} files flagged for RAG ingestion")
