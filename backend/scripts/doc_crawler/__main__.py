"""
CLI entry point for the document crawler.

Usage:
    cd backend && python -m scripts.doc_crawler [options]

Or from project root:
    python -m backend.scripts.doc_crawler [options]
"""
import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.scripts.doc_crawler.config import DOCS_DIR
from backend.scripts.doc_crawler.crawler import download_document, get_scan_summary, reset_session_state
from backend.scripts.doc_crawler.inventory import (
    generate_report,
    get_relative_path,
    load_inventory,
    save_inventory,
    update_document,
)
from backend.scripts.doc_crawler.notifier import append_log, write_pending_ingest
from backend.scripts.doc_crawler.watchlist import get_items, get_stats, get_territories


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Main crawl execution."""
    items = get_items(
        territory=args.territory,
        include_future=args.check_new,
    )

    if not items:
        print(f"No items found for territory: {args.territory}")
        return

    print(f"Checking {len(items)} documents...")
    if args.dry_run:
        print("[DRY RUN MODE — no downloads will be performed]")
    print()

    inventory = load_inventory()
    results = []

    for item in items:
        dest_path = DOCS_DIR / item.dest

        # Skip future items unless --check-new
        if item.status == "future" and not args.check_new:
            continue

        # Skip html_only items
        if item.status == "html_only":
            continue

        result = download_document(
            url=item.url,
            dest_path=dest_path,
            file_type=item.file_type,
            dry_run=args.dry_run,
        )

        # Enrich result with metadata
        result["dest"] = item.dest
        result["url"] = item.url
        result["territory"] = item.territory
        results.append(result)

        status_icon = {
            "new": "+",
            "updated": "~",
            "unchanged": "=",
            "would_download": "?",
            "would_skip": "-",
            "failed": "X",
            "rate_limited": "!",
            "blocked": "!",
            "robots_blocked": "R",
            "limit_reached": "L",
            "invalid": "X",
        }.get(result.get("status", ""), "?")

        print(f"  [{status_icon}] {item.dest} — {result.get('message', '')}")

        # Update inventory for successful operations
        if not args.dry_run and result.get("success") and result.get("hash"):
            rel = get_relative_path(dest_path)
            update_document(
                inventory,
                rel_path=rel,
                source_url=item.url,
                file_hash=result["hash"],
                size=result.get("size", 0),
                status=result["status"],
            )

    # Save results
    if not args.dry_run:
        save_inventory(inventory)
        write_pending_ingest(results)

    # Always generate report and log
    report = generate_report(results)
    append_log(results)

    # Print summary
    new = sum(1 for r in results if r.get("status") == "new")
    updated = sum(1 for r in results if r.get("status") == "updated")
    unchanged = sum(1 for r in results if r.get("status") == "unchanged")
    failed = sum(1 for r in results if r.get("status") in ("failed", "invalid", "rate_limited"))

    quarantined = sum(1 for r in results if r.get("status") == "quarantined")

    print()
    print(f"Done: {new} new, {updated} updated, {unchanged} unchanged, {failed} failed")
    if quarantined:
        print(f"Quarantined: {quarantined} documents moved to docs/_quarantine/ (review manually)")
    if new + updated > 0:
        print(f"Pending ingest: {new + updated} files flagged for RAG")

    scan = get_scan_summary()
    if scan["scanned"] > 0:
        print(
            f"Integrity scan: {scan['scanned']} docs scanned — "
            f"{scan['clean']} clean, {scan['quarantined']} quarantined"
        )


def cmd_pending(args: argparse.Namespace) -> None:
    """List all monitored URLs and their status."""
    items = get_items(territory=args.territory)
    inventory = load_inventory()
    docs = inventory.get("documents", {})

    print(f"Monitored URLs: {len(items)}")
    print()

    for item in items:
        rel = item.dest
        doc_info = docs.get(rel)

        if doc_info:
            status = f"[OK] last: {doc_info.get('last_checked', 'unknown')[:10]}"
        elif item.status == "future":
            status = "[FUTURE] not yet available"
        elif item.status == "html_only":
            status = "[HTML] no PDF available"
        else:
            status = "[PENDING] not downloaded"

        priority_mark = {"high": "***", "medium": "**", "low": "*"}.get(item.priority, "")

        print(f"  {priority_mark:3s} {status:40s} {item.dest}")

    print()
    stats = get_stats()
    print(f"By priority: {stats['by_priority']}")
    print(f"By territory: {stats['by_territory']}")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show summary statistics."""
    stats = get_stats()
    inventory = load_inventory()
    docs = inventory.get("documents", {})

    print(f"Watchlist: {stats['total']} URLs monitored")
    print(f"Inventory: {len(docs)} documents indexed")
    print()
    print("By priority:")
    for p, c in sorted(stats["by_priority"].items()):
        print(f"  {p}: {c}")
    print()
    print("By territory:")
    for t, c in sorted(stats["by_territory"].items()):
        print(f"  {t}: {c}")
    print()
    print("By status:")
    for s, c in sorted(stats["by_status"].items()):
        print(f"  {s}: {c}")
    print()
    print(f"Territories: {', '.join(get_territories())}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="doc_crawler",
        description="TaxIA Document Crawler — automated fiscal document monitoring",
    )
    parser.add_argument(
        "--territory", "-t",
        help="Filter by territory (e.g., AEAT, Navarra, Estatal)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview without downloading",
    )
    parser.add_argument(
        "--check-new",
        action="store_true",
        help="Include future/pending documents",
    )
    parser.add_argument(
        "--pending", "-p",
        action="store_true",
        help="List monitored URLs and their status",
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show summary statistics",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Reset session state
    reset_session_state()

    if args.pending:
        cmd_pending(args)
    elif args.stats:
        cmd_stats(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
