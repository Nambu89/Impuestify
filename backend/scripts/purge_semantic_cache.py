"""
Purge semantic cache (Upstash Vector) to force fresh LLM responses.

Usage:
    python backend/scripts/purge_semantic_cache.py          # Reset entire cache
    python backend/scripts/purge_semantic_cache.py --stats   # Just show stats
"""
import os
import sys
import argparse
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
project_root = backend_dir.parent

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

try:
    from upstash_vector import Index
except ImportError:
    print("❌ upstash_vector not installed")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", action="store_true", help="Only show stats")
    args = parser.parse_args()

    url = os.getenv("UPSTASH_VECTOR_REST_URL")
    token = os.getenv("UPSTASH_VECTOR_REST_TOKEN")

    if not url or not token:
        print("❌ UPSTASH_VECTOR_REST_URL / TOKEN not set")
        sys.exit(1)

    index = Index(url=url, token=token)

    try:
        info = index.info()
        print(f"📊 Semantic Cache stats:")
        print(f"   Vectors: {info.vector_count}")
        print(f"   Dimensions: {info.dimension}")
        print(f"   Similarity: {info.similarity_function}")
    except Exception as e:
        print(f"⚠️ Could not get info: {e}")

    if args.stats:
        return

    print("\n🗑️  Resetting semantic cache (deleting all cached responses)...")
    try:
        index.reset()
        print("✅ Semantic cache purged!")
        info = index.info()
        print(f"   Vectors after reset: {info.vector_count}")
    except Exception as e:
        print(f"❌ Reset failed: {e}")


if __name__ == "__main__":
    main()
