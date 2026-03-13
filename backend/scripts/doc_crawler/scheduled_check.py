"""
Scheduled weekly check — designed to run via Windows Task Scheduler.

Checks all watchlist URLs for new/updated documents, downloads them,
and generates a summary. If new documents are found, creates a flag
file and optionally shows a Windows notification.

Setup (Windows Task Scheduler):
    1. Open Task Scheduler (taskschd.msc)
    2. Create Basic Task > "TaxIA Document Checker"
    3. Trigger: Weekly (e.g., Sunday 10:00)
    4. Action: Start a program
       Program: C:\\...\\TaxIA\\venv\\Scripts\\python.exe
       Arguments: -m backend.scripts.doc_crawler.scheduled_check
       Start in: C:\\...\\TaxIA
    5. Done

Or via schtasks CLI:
    schtasks /create /tn "TaxIA-DocCrawler" /tr "C:\\...\\venv\\Scripts\\python.exe -m backend.scripts.doc_crawler.scheduled_check" /sc weekly /d SUN /st 10:00 /f
"""
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root in path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.scripts.doc_crawler.config import CRAWLER_REPORT, DOCS_DIR, PENDING_INGEST
from backend.scripts.doc_crawler.crawler import download_document, reset_session_state
from backend.scripts.doc_crawler.inventory import (
    generate_report,
    get_relative_path,
    load_inventory,
    save_inventory,
    update_document,
)
from backend.scripts.doc_crawler.notifier import append_log, write_pending_ingest
from backend.scripts.doc_crawler.drift_analyzer import analyze_drift
from backend.scripts.doc_crawler.watchlist import get_items, get_stats

LOG_FILE = DOCS_DIR / "_crawler_scheduled.log"


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def show_windows_notification(title: str, message: str) -> None:
    """Show a Windows toast notification (best effort, no dependency required)."""
    try:
        # Use PowerShell for native Windows toast
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
        $template = '<toast><visual><binding template="ToastText02"><text id="1">{title}</text><text id="2">{message}</text></binding></visual></toast>'
        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("TaxIA").Show($toast)
        """
        subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        # Fallback: just log it
        logging.getLogger(__name__).info(f"Notification: {title} — {message}")


def run_scheduled_check() -> dict:
    """
    Run the weekly automated check.

    Returns summary dict with counts.
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("TaxIA Document Crawler — Scheduled Weekly Check")
    logger.info("=" * 60)

    reset_session_state()

    # Check all active items (not future by default)
    items = get_items(include_future=True)
    stats = get_stats()
    logger.info(f"Checking {len(items)} URLs across {len(stats['by_territory'])} territories")

    inventory = load_inventory()
    results = []

    for item in items:
        # Skip html_only
        if item.status == "html_only":
            continue

        dest_path = DOCS_DIR / item.dest

        result = download_document(
            url=item.url,
            dest_path=dest_path,
            file_type=item.file_type,
        )

        result["dest"] = item.dest
        result["url"] = item.url
        result["territory"] = item.territory
        results.append(result)

        # Log each result
        status = result.get("status", "unknown")
        if status in ("new", "updated"):
            logger.info(f"  [NEW] {item.dest} ({result.get('size', 0) / 1024:.0f} KB)")
        elif status in ("failed", "rate_limited", "invalid"):
            logger.warning(f"  [FAIL] {item.dest} — {result.get('message', '')}")
        else:
            logger.debug(f"  [{status}] {item.dest}")

        # Update inventory
        if result.get("success") and result.get("hash"):
            rel = get_relative_path(dest_path)
            update_document(
                inventory,
                rel_path=rel,
                source_url=item.url,
                file_hash=result["hash"],
                size=result.get("size", 0),
                status=result["status"],
            )

    # Save everything
    save_inventory(inventory)
    write_pending_ingest(results)
    generate_report(results)
    append_log(results)

    # Calculate summary
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_checked": len(results),
        "new": sum(1 for r in results if r.get("status") == "new"),
        "updated": sum(1 for r in results if r.get("status") == "updated"),
        "unchanged": sum(1 for r in results if r.get("status") == "unchanged"),
        "failed": sum(1 for r in results if r.get("status") in ("failed", "invalid", "rate_limited")),
    }

    logger.info("")
    logger.info(f"Results: {summary['new']} new, {summary['updated']} updated, "
                f"{summary['unchanged']} unchanged, {summary['failed']} failed")

    # Notify if there are new documents
    new_count = summary["new"] + summary["updated"]
    if new_count > 0:
        new_files = [r["dest"] for r in results if r.get("status") in ("new", "updated")]
        msg = f"{new_count} nuevo(s): {', '.join(new_files[:3])}"
        if len(new_files) > 3:
            msg += f" (+{len(new_files) - 3} mas)"

        logger.info(f"Notificacion: {msg}")
        show_windows_notification("TaxIA — Documentos nuevos", msg)
        logger.info(f"Pendientes de ingesta RAG: ver {PENDING_INGEST}")
    else:
        logger.info("Sin documentos nuevos esta semana.")

    logger.info(f"Reporte: {CRAWLER_REPORT}")

    # ── Drift Analyzer (Layer 2) — runs if pending changes exist ──
    if new_count > 0 and PENDING_INGEST.exists():
        logger.info("")
        logger.info("Running Fiscal Drift Analyzer...")
        try:
            drift_result = analyze_drift(dry_run=False, skip_llm=False)
            logger.info(f"Drift analysis: {drift_result.get('status', 'unknown')}")
            if drift_result.get("email_sent"):
                logger.info("Drift alert email sent via Resend")
        except Exception as e:
            logger.warning(f"Drift analysis failed (non-blocking): {e}")
    else:
        logger.info("No changes detected — skipping drift analysis.")

    logger.info("=" * 60)

    return summary


if __name__ == "__main__":
    setup_logging()
    try:
        run_scheduled_check()
    except Exception as e:
        logging.getLogger(__name__).error(f"Error en scheduled check: {e}", exc_info=True)
        sys.exit(1)
