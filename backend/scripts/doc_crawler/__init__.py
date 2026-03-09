"""
TaxIA Document Crawler — Automated fiscal document monitoring and download.

Usage:
    python -m doc_crawler                    # Check all watchlist
    python -m doc_crawler --territory AEAT   # Single territory
    python -m doc_crawler --dry-run          # Preview without downloading
    python -m doc_crawler --pending          # List monitored URLs + status
    python -m doc_crawler --stats            # Summary statistics
"""

__version__ = "1.0.0"
