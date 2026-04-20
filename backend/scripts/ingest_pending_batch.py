"""Ingest all pending PDFs that are in docs/ but not in the DB.

Usage: cd backend && python scripts/ingest_pending_batch.py
"""
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Setup
BACKEND_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DOCS_DIR = PROJECT_ROOT / "docs"

sys.path.insert(0, str(BACKEND_DIR))
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


async def get_ingested_filenames() -> set[str]:
    from app.database.turso_client import TursoClient
    db = TursoClient()
    await db.connect()
    r = await db.execute("SELECT filename FROM documents")
    return {dict(row)["filename"] for row in (r.rows or [])}


def find_pending_pdfs(ingested: set[str]) -> list[Path]:
    pending = []
    for p in sorted(DOCS_DIR.rglob("*.pdf")):
        if p.name not in ingested:
            pending.append(p)
    return pending


async def main():
    ingested = await get_ingested_filenames()
    pending = find_pending_pdfs(ingested)

    print(f"Ingested: {len(ingested)} | Pending: {len(pending)}")
    if not pending:
        print("Nothing to ingest.")
        return

    for i, pdf in enumerate(pending, 1):
        size_kb = pdf.stat().st_size // 1024
        print(f"\n[{i}/{len(pending)}] {pdf.name} ({size_kb} KB)")
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(BACKEND_DIR / "scripts" / "ingest_documents.py"),
                    "--file",
                    str(pdf),
                ],
                cwd=str(BACKEND_DIR),
                capture_output=True,
                text=True,
                timeout=1800,  # 30 min per doc (large PDFs via Azure DI)
                env={**os.environ, "PYTHONUTF8": "1"},
            )
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT (30 min) — skipping")
            continue
        # Show last 5 lines of output
        lines = (result.stdout + result.stderr).strip().splitlines()
        for line in lines[-5:]:
            print(f"  {line}")
        if result.returncode != 0:
            print(f"  WARNING: exit code {result.returncode}")

    # Final count
    ingested_after = await get_ingested_filenames()
    new = len(ingested_after) - len(ingested)
    print(f"\nDone. Ingested {new} new documents. Total: {len(ingested_after)}")


if __name__ == "__main__":
    asyncio.run(main())
