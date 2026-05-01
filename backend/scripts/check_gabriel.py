"""Quick diagnostic: check gabriel.demacedo1@gmail.com user + subscription + activity + bug count."""
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

    target_email = "gabriel.demacedo1@gmail.com"

    print(f"\n=== USER: {target_email} ===")
    user_res = await client.execute(
        "SELECT * FROM users WHERE email = ?",
        [target_email],
    )
    if not user_res.rows:
        print("USER NOT FOUND in users table")
        return

    user = user_res.rows[0]
    user_id = user["id"]
    for k, v in user.items():
        print(f"  {k}: {v}")

    print("\n=== SUBSCRIPTIONS ROW ===")
    sub_res = await client.execute(
        "SELECT * FROM subscriptions WHERE user_id = ?", [user_id]
    )
    if not sub_res.rows:
        print("  NO subscriptions row for this user_id")
    else:
        for row in sub_res.rows:
            for k, v in row.items():
                print(f"  {k}: {v}")
            print("  ---")

    print("\n=== CONVERSATIONS (recent activity) ===")
    convs = await client.execute(
        "SELECT id, title, created_at, updated_at FROM conversations "
        "WHERE user_id = ? ORDER BY updated_at DESC LIMIT 10",
        [user_id],
    )
    print(f"  Total recientes: {len(convs.rows)}")
    for r in convs.rows:
        print(f"  {r['updated_at']} | {r['id'][:8]} | {r.get('title') or '(no title)'}")

    print("\n=== MESSAGE COUNT (last 30 days) ===")
    msg_res = await client.execute(
        "SELECT COUNT(*) AS cnt FROM messages m "
        "JOIN conversations c ON c.id = m.conversation_id "
        "WHERE c.user_id = ? AND m.created_at > date('now', '-30 days')",
        [user_id],
    )
    print(f"  Mensajes ultimos 30 dias: {msg_res.rows[0]['cnt']}")

    print("\n=== USAGE METRICS ===")
    usage = await client.execute(
        "SELECT endpoint, COUNT(*) AS cnt, MAX(created_at) AS last_use "
        "FROM usage_metrics WHERE user_id = ? GROUP BY endpoint "
        "ORDER BY cnt DESC LIMIT 20",
        [user_id],
    )
    for r in usage.rows:
        print(f"  {r['endpoint']:<40} | {r['cnt']:>5} | {r['last_use']}")

    print("\n=== ALL FEEDBACK ROWS (entire table) ===")
    fb_all = await client.execute(
        "SELECT id, type, status, priority, title, user_id, created_at "
        "FROM feedback ORDER BY created_at DESC"
    )
    print(f"  Total rows en feedback: {len(fb_all.rows)}")
    for r in fb_all.rows:
        print(f"  [{r['type']}/{r['status']}/{r['priority']}] {r['created_at']} | "
              f"user={r['user_id']} | {r['title'][:60] if r['title'] else ''}")

    print("\n=== DASHBOARD COUNTERS (same query as backend) ===")
    bugs_open = await client.execute(
        "SELECT COUNT(*) AS cnt FROM feedback "
        "WHERE type = 'bug' AND status NOT IN ('done', 'wont_fix')"
    )
    print(f"  bugs_open (dashboard count): {bugs_open.rows[0]['cnt']}")

    bugs_open_with_user = await client.execute(
        "SELECT COUNT(*) AS cnt FROM feedback f "
        "LEFT JOIN users u ON u.id = f.user_id "
        "WHERE f.type = 'bug' AND f.status NOT IN ('done', 'wont_fix')"
    )
    print(f"  bugs_open via LEFT JOIN users: {bugs_open_with_user.rows[0]['cnt']}")


if __name__ == "__main__":
    asyncio.run(main())
