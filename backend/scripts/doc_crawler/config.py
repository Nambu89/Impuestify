"""
Global configuration for the document crawler.
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # TaxIA/
DOCS_DIR = PROJECT_ROOT / "docs"
INVENTORY_INDEX = DOCS_DIR / "_crawler_index.json"
CRAWLER_REPORT = DOCS_DIR / "_crawler_report.md"
CRAWLER_LOG = DOCS_DIR / "_crawler_log.json"
PENDING_INGEST = DOCS_DIR / "_pending_ingest.json"

# ── Rate Limiting ──────────────────────────────────────────────
INTER_REQUEST_DELAY_S = 4           # Seconds between requests to same domain
MAX_DOWNLOADS_PER_DOMAIN = 50       # Hard cap per execution
BACKOFF_SCHEDULE_S = [10, 30, 60]   # Exponential backoff on error (4th fail = STOP)
REQUEST_TIMEOUT_S = 120

# ── HTTP Headers ───────────────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
    "Accept-Language": "es-ES,es;q=0.9",
}

# ── Validation ─────────────────────────────────────────────────
MIN_FILE_SIZE_BYTES = 10_240   # 10 KB minimum for a real document
PDF_MAGIC = b"%PDF"
XLSX_MAGIC = b"PK"             # ZIP-based (Office Open XML)
XLS_MAGIC = b"\xd0\xcf\x11\xe0"  # OLE2 compound document

# ── Logging ────────────────────────────────────────────────────
MAX_LOG_ENTRIES = 100
