"""
Inventory management — JSON index + human-readable report.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .config import CRAWLER_REPORT, DOCS_DIR, INVENTORY_INDEX

logger = logging.getLogger(__name__)


def load_inventory() -> dict:
    """Load the crawler index from JSON. Returns empty dict if not found."""
    if INVENTORY_INDEX.exists():
        with open(INVENTORY_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "last_run": None, "documents": {}}


def save_inventory(data: dict) -> None:
    """Save the crawler index to JSON."""
    data["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(INVENTORY_INDEX, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Inventory saved: {len(data.get('documents', {}))} documents")


def update_document(
    inventory: dict,
    rel_path: str,
    source_url: str,
    file_hash: str,
    size: int,
    status: str,
) -> None:
    """Update a single document entry in the inventory."""
    now = datetime.now(timezone.utc).isoformat()
    docs = inventory.setdefault("documents", {})

    if rel_path in docs:
        docs[rel_path]["hash"] = file_hash
        docs[rel_path]["size"] = size
        docs[rel_path]["last_checked"] = now
        docs[rel_path]["last_status"] = status
        if status in ("new", "updated"):
            docs[rel_path]["download_date"] = now
    else:
        docs[rel_path] = {
            "source_url": source_url,
            "hash": file_hash,
            "size": size,
            "download_date": now,
            "last_checked": now,
            "last_status": status,
        }


def generate_report(results: list[dict]) -> str:
    """
    Generate a human-readable report from crawl results.
    Writes to _crawler_report.md and returns the text.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    new = [r for r in results if r.get("status") == "new"]
    updated = [r for r in results if r.get("status") == "updated"]
    unchanged = [r for r in results if r.get("status") == "unchanged"]
    failed = [r for r in results if r.get("status") in ("failed", "invalid", "rate_limited")]
    blocked = [r for r in results if r.get("status") in ("blocked", "robots_blocked", "limit_reached")]
    skipped = [r for r in results if r.get("status") in ("would_download", "would_skip")]

    lines = [
        f"# Crawler Report — {now}",
        "",
        f"**Total checked:** {len(results)}",
        f"**New:** {len(new)} | **Updated:** {len(updated)} | **Unchanged:** {len(unchanged)}",
        f"**Failed:** {len(failed)} | **Blocked:** {len(blocked)}",
        "",
    ]

    if new:
        lines.append("## New Documents")
        for r in new:
            lines.append(f"- `{r['dest']}` ({r.get('size', 0) / 1024:.0f} KB) — {r['url']}")
        lines.append("")

    if updated:
        lines.append("## Updated Documents")
        for r in updated:
            lines.append(f"- `{r['dest']}` ({r.get('size', 0) / 1024:.0f} KB)")
        lines.append("")

    if failed:
        lines.append("## Failed")
        for r in failed:
            lines.append(f"- `{r['dest']}` — {r.get('message', 'unknown error')}")
        lines.append("")

    if blocked:
        lines.append("## Blocked / Skipped")
        for r in blocked:
            lines.append(f"- `{r['dest']}` — {r.get('message', '')}")
        lines.append("")

    if skipped:
        lines.append("## Dry Run Preview")
        for r in skipped:
            lines.append(f"- [{r['status']}] `{r['dest']}`")
        lines.append("")

    text = "\n".join(lines)
    CRAWLER_REPORT.write_text(text, encoding="utf-8")
    logger.info(f"Report written: {CRAWLER_REPORT}")
    return text


def get_relative_path(abs_path: Path) -> str:
    """Get path relative to docs/ directory."""
    try:
        return str(abs_path.relative_to(DOCS_DIR)).replace("\\", "/")
    except ValueError:
        return str(abs_path).replace("\\", "/")
