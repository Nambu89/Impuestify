"""Get full feedback text from Gabriel + look up Stripe customer for any payment."""
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
env_path = backend_dir.parent / ".env"
load_dotenv(env_path)

from app.database.turso_client import TursoClient


async def main():
    client = TursoClient()
    await client.connect()

    res = await client.execute(
        "SELECT * FROM feedback WHERE user_id = ? ORDER BY created_at DESC",
        ["969e2925-26fd-4465-9036-2b02d1f90212"],
    )
    for r in res.rows:
        print("=" * 70)
        print(f"id: {r['id']}")
        print(f"type/status/priority: {r['type']}/{r['status']}/{r['priority']}")
        print(f"created_at: {r['created_at']}")
        print(f"page_url: {r.get('page_url')}")
        print(f"title: {r['title']}")
        print(f"description:\n{r['description']}")
        print(f"has screenshot: {bool(r.get('screenshot_data'))}")


if __name__ == "__main__":
    asyncio.run(main())
