"""Purge semantic cache (Upstash Vector) — SAFE VERSION.

After a fix that changes verifier/prompt output, older cached responses
(TTL 24h) still contain the broken behavior and would be served on
similarity matches. This script wipes the cache so the first user gets
the new behavior on a cache miss.

SAFETY:
- The semantic-cache index and the RAG embeddings index may share the
  same Upstash Vector instance (depending on .env config). A blind
  `index.reset()` would wipe 84K+ RAG embeddings and break production.
- This script REFUSES to reset if vector_count > MAX_SAFE_CACHE_SIZE,
  unless --force is passed.
- Default mode: scan entries and delete only those whose metadata has a
  'response' key (semantic-cache shape) — RAG entries have 'content'.
- A previous version of this script wiped the RAG index by accident on
  2026-05-13. Don't repeat history.

Usage:
    python backend/scripts/purge_semantic_cache.py --stats
    python backend/scripts/purge_semantic_cache.py             # selective delete
    python backend/scripts/purge_semantic_cache.py --force     # full reset (dangerous)
"""

import argparse
import os
import sys
from pathlib import Path

# Fix Windows encoding for stdout
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
project_root = backend_dir.parent

from dotenv import load_dotenv

load_dotenv(project_root / ".env")

try:
    from upstash_vector import Index
except ImportError:
    print("ERROR: upstash_vector not installed (pip install upstash-vector)")
    sys.exit(1)


# Cache should typically hold tens-to-hundreds of entries (TTL 24h, 0.93
# similarity threshold, deduped by query hash). >1000 means we're looking
# at the RAG index by mistake.
MAX_SAFE_CACHE_SIZE = 1000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stats", action="store_true", help="Show stats only, no destructive action."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Override the RAG safety check. DANGEROUS — only "
        "use if you're sure the index has no RAG vectors.",
    )
    parser.add_argument(
        "--pattern", default=None, help="Substring match against stored query metadata."
    )
    args = parser.parse_args()

    url = os.getenv("UPSTASH_VECTOR_REST_URL")
    token = os.getenv("UPSTASH_VECTOR_REST_TOKEN")
    rag_url = os.getenv("UPSTASH_VECTOR_RAG_URL")

    if not url or not token:
        print("ERROR: UPSTASH_VECTOR_REST_URL / TOKEN not set in .env")
        sys.exit(1)

    if rag_url and rag_url.strip("'\"") == url.strip("'\""):
        print("⚠️  WARNING: UPSTASH_VECTOR_REST_URL == UPSTASH_VECTOR_RAG_URL.")
        print("   Semantic cache and RAG share the same index — selective")
        print("   metadata-based deletion is the only safe mode.")
        print()

    print(f"Connecting to: {url[:50]}...")
    index = Index(url=url.strip("'\""), token=token.strip("'\""))

    # ── Stats ──
    try:
        info = index.info()
        vector_count = info.vector_count
        print("Index stats:")
        print(f"   Vectors: {vector_count}")
        print(f"   Dimensions: {info.dimension}")
        print(f"   Similarity: {info.similarity_function}")
    except Exception as e:
        print(f"ERROR: Could not get index info: {e}")
        return 1

    if args.stats:
        return 0

    # ── Safety check ──
    if vector_count > MAX_SAFE_CACHE_SIZE and not args.force:
        print()
        print(f"🛑 ABORTING: {vector_count} vectors is > {MAX_SAFE_CACHE_SIZE}.")
        print("   Looks like this index contains RAG embeddings (84K+ typical),")
        print("   not just cache entries. Doing a full reset would destroy RAG.")
        print()
        print("   Options:")
        print("   1. (Recommended) Use selective deletion below — no need to")
        print("      reset the whole index.")
        print("   2. Use --force ONLY if you've verified there is no RAG here.")
        print()
        # Fall through to selective deletion
        _selective_delete(index, args.pattern)
        return 0

    # Small index — safe to reset.
    print()
    if args.pattern:
        _selective_delete(index, args.pattern)
    else:
        print(f"Resetting cache index ({vector_count} vectors)...")
        index.reset()
        info = index.info()
        print(f"OK. Vectors after reset: {info.vector_count}")
    return 0


def _selective_delete(index, pattern: str | None) -> None:
    """Delete only entries whose metadata looks like a cache entry
    (presence of 'response' key). RAG entries have 'content' but no
    'response'."""
    print("Selective deletion mode — scanning for cache entries...")
    print("(cache entries are identified by metadata.response key;")
    print(" RAG entries have metadata.content and are preserved)")
    print()

    deleted = 0
    scanned = 0
    cursor: str | None = None
    page_size = 100
    pattern_lc = (pattern or "").lower()

    while True:
        kwargs = {"limit": page_size, "include_metadata": True}
        if cursor:
            kwargs["cursor"] = cursor
        try:
            page = index.range(**kwargs)
        except Exception as e:
            print(f"ERROR: index.range failed: {e}")
            print("Cannot perform selective delete on this Upstash version.")
            print("Either upgrade upstash-vector SDK or use --force at your own risk.")
            return

        vectors = getattr(page, "vectors", []) or []
        for v in vectors:
            scanned += 1
            md = getattr(v, "metadata", None) or {}
            is_cache_entry = "response" in md
            if not is_cache_entry:
                continue
            if pattern_lc:
                query_text = str(md.get("query", "")).lower()
                if pattern_lc not in query_text:
                    continue
            try:
                index.delete(v.id)
                deleted += 1
            except Exception as e:
                print(f"   delete failed for {getattr(v, 'id', '?')}: {e}")

        cursor = getattr(page, "next_cursor", None) or getattr(page, "nextCursor", None)
        if not cursor:
            break

    print(f"Scanned {scanned} entries. Deleted {deleted} cache entries.")
    print("RAG entries left untouched.")


if __name__ == "__main__":
    raise SystemExit(main())
