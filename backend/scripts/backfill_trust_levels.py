"""
Backfill `documents.trust_level` for existing rows.

Heuristic by filepath / source / filename:
- Filepath under docs/aeat/ or source mentions AEAT  -> 'official_aeat'
- Filepath under docs/boe/ or source mentions BOE    -> 'official_boe'
- Filepath under docs/foral|forales/, foral/Bizkaia, etc -> 'official_foral'
- Filepath under docs/ccaa/                          -> 'official_ccaa'
- Filepath under docs/manuales/ official guides      -> 'official_aeat'
- Otherwise                                          -> 'crawled_third_party'

Run once after adding the column. Safe to re-run (idempotent).
"""
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def classify_trust(filepath: str, source: str, filename: str) -> str:
    fp = (filepath or "").lower().replace("\\", "/")
    src = (source or "").lower()
    fn = (filename or "").lower()

    haystack = " ".join([fp, src, fn])

    if any(tok in haystack for tok in ("/aeat/", "aeat", "agencia tributaria", "manual_renta", "manual renta")):
        return "official_aeat"
    if any(tok in haystack for tok in ("/boe/", "boe", "boletin oficial", "boletín oficial")):
        return "official_boe"
    if any(tok in haystack for tok in ("/foral", "foral", "bizkaia", "gipuzkoa", "araba", "navarra", "diputacion", "diputación")):
        return "official_foral"
    if any(tok in haystack for tok in ("/ccaa/", "comunidad autonom", "comunidad autónom", "boja", "bocm", "boc", "bocl", "boa", "dogc")):
        return "official_ccaa"
    return "crawled_third_party"


async def main():
    from app.database.turso_client import get_db_client

    db = await get_db_client()

    result = await db.execute(
        "SELECT id, filename, filepath, source, trust_level FROM documents"
    )
    rows = result.rows or []
    logger.info(f"Found {len(rows)} documents")

    counts = {"official_aeat": 0, "official_boe": 0, "official_foral": 0,
              "official_ccaa": 0, "crawled_third_party": 0, "skipped": 0}

    for row in rows:
        current = (row.get("trust_level") or "").strip()
        if current and current != "unknown":
            counts["skipped"] += 1
            continue
        new_level = classify_trust(
            row.get("filepath", ""),
            row.get("source", ""),
            row.get("filename", ""),
        )
        await db.execute(
            "UPDATE documents SET trust_level = ? WHERE id = ?",
            [new_level, row["id"]],
        )
        counts[new_level] = counts.get(new_level, 0) + 1

    logger.info("Backfill complete:")
    for k, v in counts.items():
        logger.info(f"  {k}: {v}")


if __name__ == "__main__":
    asyncio.run(main())
