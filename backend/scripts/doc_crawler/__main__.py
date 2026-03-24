"""
CLI entry point for the document crawler.

Usage:
    cd backend && python -m scripts.doc_crawler [options]

Or from project root:
    python -m backend.scripts.doc_crawler [options]

Features:
    - Scrapling-based downloads (anti-bot fingerprinting)
    - Multi-cycle retry: failed URLs are retried in subsequent cycles (up to --max-cycles)
    - URL verification: --verify-urls checks all URLs are reachable before downloading
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.scripts.doc_crawler.config import DOCS_DIR
from backend.scripts.doc_crawler.crawler import (
    check_url_exists,
    download_document,
    get_scan_summary,
    reset_session_state,
)
from backend.scripts.doc_crawler.inventory import (
    generate_report,
    get_relative_path,
    load_inventory,
    save_inventory,
    update_document,
)
from backend.scripts.doc_crawler.notifier import append_log, write_pending_ingest
from backend.scripts.doc_crawler.watchlist import get_items, get_stats, get_territories

# Delay between retry cycles (seconds)
INTER_CYCLE_DELAY_S = 30


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


STATUS_ICONS = {
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
    "quarantined": "Q",
    "url_invalid": "!",
}


def cmd_verify(args: argparse.Namespace) -> None:
    """Verify all URLs in the watchlist are reachable."""
    items = get_items(
        territory=args.territory,
        include_future=True,
    )

    # Skip html_only
    items = [i for i in items if i.status not in ("html_only", "deprecated")]

    print(f"Verificando {len(items)} URLs...\n")

    reachable = []
    unreachable = []

    for item in items:
        result = check_url_exists(item.url)
        icon = "OK" if result["reachable"] else "FAIL"
        print(f"  [{icon}] {result['status_code']:>3d}  {item.dest}")

        if result["reachable"]:
            reachable.append(item)
        else:
            unreachable.append((item, result))

    print(f"\n--- Resultado ---")
    print(f"Accesibles: {len(reachable)}/{len(items)}")
    print(f"No accesibles: {len(unreachable)}/{len(items)}")

    if unreachable:
        print(f"\nURLs fallidas:")
        for item, result in unreachable:
            print(f"  [{result['status_code']:>3d}] {item.territory:15s} {item.dest}")
            print(f"        URL: {item.url}")
            if item.notes:
                print(f"        Nota: {item.notes}")


def cmd_run(args: argparse.Namespace) -> None:
    """Main crawl execution with multi-cycle retry for failed URLs."""
    items = get_items(
        territory=args.territory,
        include_future=args.check_new,
    )

    if not items:
        print(f"No items found for territory: {args.territory}")
        return

    # Filter out html_only and (optionally) future items
    downloadable = []
    for item in items:
        if item.status in ("html_only", "deprecated"):
            continue
        if item.status == "future" and not args.check_new:
            continue
        downloadable.append(item)

    max_cycles = args.max_cycles
    print(f"Checking {len(downloadable)} documents (max {max_cycles} cycles)...")
    if args.dry_run:
        print("[DRY RUN MODE — no downloads will be performed]")
    print()

    inventory = load_inventory()
    all_results = []  # Accumulate results across all cycles
    pending_items = list(downloadable)  # Items pending download

    for cycle in range(1, max_cycles + 1):
        if not pending_items:
            break

        if cycle > 1:
            print(f"\n{'='*60}")
            print(f"CICLO {cycle}/{max_cycles} — Reintentando {len(pending_items)} URLs fallidas")
            print(f"{'='*60}")
            print(f"Esperando {INTER_CYCLE_DELAY_S}s entre ciclos...")
            time.sleep(INTER_CYCLE_DELAY_S)
            # Reset blocked domains for retry cycles
            reset_session_state()
        else:
            print(f"--- Ciclo {cycle}/{max_cycles} ---")

        cycle_failed = []

        for item in pending_items:
            dest_path = DOCS_DIR / item.dest

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
            result["cycle"] = cycle

            icon = STATUS_ICONS.get(result.get("status", ""), "?")
            print(f"  [{icon}] {item.dest} — {result.get('message', '')}")

            # Track failed items for retry in next cycle
            if result.get("status") in ("failed", "invalid", "rate_limited"):
                cycle_failed.append(item)
            else:
                # Only add successful/unchanged results to final list
                all_results.append(result)

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

        # Summary for this cycle
        cycle_ok = len(pending_items) - len(cycle_failed)
        print(f"\n  Ciclo {cycle}: {cycle_ok} OK, {len(cycle_failed)} fallidos")

        if not cycle_failed:
            print(f"  Todos los documentos descargados correctamente.")
            break

        # Prepare next cycle with only the failed items
        pending_items = cycle_failed

    # After all cycles, add remaining failures to results
    if pending_items:
        print(f"\n--- {len(pending_items)} URLs fallidas tras {max_cycles} ciclos (fallo definitivo) ---")
        for item in pending_items:
            all_results.append({
                "dest": item.dest,
                "url": item.url,
                "territory": item.territory,
                "success": False,
                "status": "failed",
                "message": f"Failed after {max_cycles} cycles",
                "cycle": max_cycles,
            })
            print(f"  [X] {item.dest}")
            print(f"      URL: {item.url}")

    # Save results
    if not args.dry_run:
        save_inventory(inventory)
        write_pending_ingest(all_results)

    # Always generate report and log
    generate_report(all_results)
    append_log(all_results)

    # Print final summary
    new = sum(1 for r in all_results if r.get("status") == "new")
    updated = sum(1 for r in all_results if r.get("status") == "updated")
    unchanged = sum(1 for r in all_results if r.get("status") == "unchanged")
    failed = sum(1 for r in all_results if r.get("status") in ("failed", "invalid", "rate_limited"))
    quarantined = sum(1 for r in all_results if r.get("status") == "quarantined")

    print()
    print(f"=== RESUMEN FINAL ===")
    print(f"Nuevos: {new} | Actualizados: {updated} | Sin cambios: {unchanged} | Fallidos: {failed}")
    if quarantined:
        print(f"En cuarentena: {quarantined} documentos en docs/_quarantine/ (revisar manualmente)")
    if new + updated > 0:
        print(f"Pendientes de ingesta RAG: {new + updated} archivos")

    scan = get_scan_summary()
    if scan["scanned"] > 0:
        print(
            f"Integrity scan: {scan['scanned']} docs escaneados — "
            f"{scan['clean']} limpios, {scan['quarantined']} en cuarentena"
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
        elif item.status in ("html_only", "deprecated"):
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
        description="TaxIA Document Crawler — Scrapling-based fiscal document monitoring with multi-cycle retry",
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
        "--max-cycles", "-c",
        type=int,
        default=3,
        help="Max retry cycles for failed URLs (default: 3)",
    )
    parser.add_argument(
        "--verify-urls",
        action="store_true",
        help="Only verify URLs are reachable (no downloads)",
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

    if args.verify_urls:
        cmd_verify(args)
    elif args.pending:
        cmd_pending(args)
    elif args.stats:
        cmd_stats(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
