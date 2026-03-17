"""
Migration: Add Integrity Columns

Adds document integrity scanning columns to workspace_files and documents tables:
- workspace_files: integrity_score (REAL), integrity_findings (TEXT)
- documents: integrity_score (REAL DEFAULT 1.0), integrity_findings (TEXT)

SQLite does not support ALTER TABLE ... ADD COLUMN IF NOT EXISTS, so this
script uses try/except to catch "duplicate column name" errors (idempotent).

Usage:
    python -m backend.scripts.migrate_integrity_columns [--dry-run]

Safe to run multiple times. Already-existing columns produce a WARNING, not an error.
"""
import sys
import os
import asyncio
import argparse
import logging

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, ".."))
sys.path.insert(0, BACKEND_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app.database.turso_client import TursoClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# Columns to add: (table, column_name, column_definition)
MIGRATIONS = [
    (
        "workspace_files",
        "integrity_score",
        "ALTER TABLE workspace_files ADD COLUMN integrity_score REAL DEFAULT NULL",
    ),
    (
        "workspace_files",
        "integrity_findings",
        "ALTER TABLE workspace_files ADD COLUMN integrity_findings TEXT DEFAULT NULL",
    ),
    (
        "documents",
        "integrity_score",
        "ALTER TABLE documents ADD COLUMN integrity_score REAL DEFAULT 1.0",
    ),
    (
        "documents",
        "integrity_findings",
        "ALTER TABLE documents ADD COLUMN integrity_findings TEXT DEFAULT NULL",
    ),
]


async def add_column(db: TursoClient, table: str, column: str, sql: str, dry_run: bool) -> bool:
    """
    Execute a single ALTER TABLE statement.

    Returns True if the column was added, False if it already existed.
    Raises on unexpected errors.
    """
    if dry_run:
        logger.info(f"[DRY-RUN] Would execute: {sql}")
        return True

    try:
        await db.execute(sql)
        logger.info(f"Added column '{column}' to table '{table}'")
        return True
    except Exception as exc:
        msg = str(exc).lower()
        if "duplicate column name" in msg or "already exists" in msg:
            logger.warning(f"Column '{column}' already exists in '{table}' — skipping")
            return False
        # Re-raise anything unexpected
        raise


async def verify_columns(db: TursoClient) -> None:
    """
    Run a lightweight verification: PRAGMA table_info on both tables and log
    which integrity columns are present.
    """
    for table in ("workspace_files", "documents"):
        result = await db.execute(f"PRAGMA table_info({table})")
        columns = {row["name"] for row in (result.rows or [])}
        for col in ("integrity_score", "integrity_findings"):
            if col in columns:
                logger.info(f"[VERIFY] {table}.{col} — PRESENT")
            else:
                logger.warning(f"[VERIFY] {table}.{col} — MISSING (unexpected)")


async def main(dry_run: bool) -> None:
    """Main entry point for the integrity columns migration."""
    logger.info("Starting integrity columns migration")
    if dry_run:
        logger.info("[DRY-RUN] No database writes will be performed")

    added = 0
    skipped = 0

    if dry_run:
        for table, column, sql in MIGRATIONS:
            logger.info(f"[DRY-RUN] {table}.{column} — would execute: {sql}")
            added += 1
        logger.info(f"[DRY-RUN] {added} columns would be added. Run without --dry-run to apply.")
        return

    db = TursoClient()
    try:
        await db.connect()

        for table, column, sql in MIGRATIONS:
            was_added = await add_column(db, table, column, sql, dry_run=False)
            if was_added:
                added += 1
            else:
                skipped += 1

        logger.info(f"Migration complete — {added} added, {skipped} already existed")

        logger.info("Verifying columns...")
        await verify_columns(db)

    finally:
        await db.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add integrity_score and integrity_findings columns to workspace_files and documents"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ALTER TABLE statements without executing them",
    )
    args = parser.parse_args()

    asyncio.run(main(args.dry_run))
