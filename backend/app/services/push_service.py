"""
Web Push Notification Service

Sends Web Push notifications (RFC 8292 / VAPID) to users' subscribed devices.
Uses pywebpush for VAPID-signed push delivery.

Designed for:
- Fiscal deadline alerts (15d, 5d, 1d before end_date)
- Idempotency via notification_log UNIQUE(user_id, deadline_id, alert_type)
- Auto-cleanup of expired subscriptions (HTTP 410)
"""
import json
import uuid
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from app.config import settings
from app.database.turso_client import TursoClient, get_db_client

logger = logging.getLogger(__name__)

# Maximum notifications per user per day (rate guard)
MAX_NOTIFICATIONS_PER_DAY = 3

# Alert thresholds in days
ALERT_DAY_OPTIONS = {15, 5, 1}


def _pywebpush_available() -> bool:
    try:
        import pywebpush  # noqa: F401
        return True
    except ImportError:
        return False


def _build_payload(title: str, body: str, url: str = "/calendario", tag: str = "fiscal-deadline") -> str:
    """Build JSON payload string for Web Push (max 4KB)."""
    payload = {
        "title": title,
        "body": body,
        "icon": "/icon-192.png",
        "badge": "/icon-192.png",
        "url": url,
        "tag": tag,
    }
    return json.dumps(payload, ensure_ascii=False)


async def send_push(
    user_id: str,
    title: str,
    body: str,
    url: str = "/calendario",
    tag: str = "fiscal-deadline",
    db: Optional[TursoClient] = None,
) -> dict:
    """
    Send a Web Push notification to all subscriptions for a user.

    Args:
        user_id: Target user ID
        title: Notification title
        body: Notification body text
        url: URL to open on click
        tag: Notification tag (collapses duplicate notifications)
        db: Optional TursoClient (creates one if not provided)

    Returns:
        dict with keys: sent (int), failed (int), expired_cleaned (int)
    """
    if not _pywebpush_available():
        logger.warning("pywebpush not installed — push notifications disabled")
        return {"sent": 0, "failed": 0, "expired_cleaned": 0}

    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("VAPID keys not configured — push notifications disabled")
        return {"sent": 0, "failed": 0, "expired_cleaned": 0}

    from pywebpush import webpush, WebPushException

    own_db = db is None
    if own_db:
        db = await get_db_client()

    try:
        result = await db.execute(
            "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
            [user_id],
        )
        subscriptions = result.rows or []
    except Exception as exc:
        logger.error(f"Failed to fetch subscriptions for user {user_id}: {exc}")
        return {"sent": 0, "failed": 0, "expired_cleaned": 0}

    payload = _build_payload(title, body, url, tag)
    sent = 0
    failed = 0
    expired_cleaned = 0

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": {
                        "p256dh": sub["p256dh"],
                        "auth": sub["auth"],
                    },
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
            )
            sent += 1
        except WebPushException as exc:
            status_code = exc.response.status_code if exc.response else None
            if status_code == 410:
                # Subscription expired — remove from DB
                logger.info(f"Removing expired subscription {sub['id']} for user {user_id}")
                try:
                    await db.execute(
                        "DELETE FROM push_subscriptions WHERE id = ?",
                        [sub["id"]],
                    )
                    expired_cleaned += 1
                except Exception as del_exc:
                    logger.error(f"Failed to delete expired subscription: {del_exc}")
            else:
                logger.error(f"WebPush failed for sub {sub['id']}: {exc}")
                failed += 1
        except Exception as exc:
            logger.error(f"Unexpected error sending push to {sub.get('id')}: {exc}")
            failed += 1

    logger.info(
        f"Push to user {user_id}: sent={sent}, failed={failed}, expired_cleaned={expired_cleaned}"
    )
    return {"sent": sent, "failed": failed, "expired_cleaned": expired_cleaned}


async def send_deadline_alerts(db: Optional[TursoClient] = None) -> dict:
    """
    Cron job: send deadline alerts for all users.

    Logic:
    1. For each active deadline with end_date in the future, compute days_remaining.
    2. For each push_subscription, parse alert_days preferences.
    3. If days_remaining in alert_days AND notification not already sent -> send push.
    4. Insert into notification_log after successful send.
    5. Limit max 3 notifications per user per day.

    Returns:
        dict with summary stats
    """
    own_db = db is None
    if own_db:
        db = await get_db_client()

    today = date.today()
    today_str = today.isoformat()

    stats = {
        "deadlines_checked": 0,
        "users_checked": 0,
        "notifications_sent": 0,
        "notifications_skipped_duplicate": 0,
        "notifications_skipped_rate_limit": 0,
        "errors": 0,
    }

    try:
        # Fetch all active future deadlines
        deadlines_result = await db.execute(
            """
            SELECT id, model, model_name, territory, period, tax_year, end_date, applies_to
            FROM fiscal_deadlines
            WHERE is_active = 1 AND end_date >= ?
            ORDER BY end_date ASC
            """,
            [today_str],
        )
        deadlines = deadlines_result.rows or []
        stats["deadlines_checked"] = len(deadlines)

        # Fetch all push subscriptions
        subs_result = await db.execute(
            "SELECT user_id, alert_days FROM push_subscriptions GROUP BY user_id",
            [],
        )
        subscriptions = subs_result.rows or []
        stats["users_checked"] = len(subscriptions)

        # Daily notification count per user (rate limiting)
        daily_counts: dict[str, int] = {}

        for sub in subscriptions:
            user_id = sub["user_id"]
            alert_days_str = sub.get("alert_days") or "15,5,1"
            try:
                user_alert_days = {int(d.strip()) for d in alert_days_str.split(",") if d.strip().isdigit()}
            except Exception:
                user_alert_days = {15, 5, 1}

            daily_counts.setdefault(user_id, 0)

            for deadline in deadlines:
                if daily_counts[user_id] >= MAX_NOTIFICATIONS_PER_DAY:
                    stats["notifications_skipped_rate_limit"] += 1
                    continue

                end_date = date.fromisoformat(deadline["end_date"])
                days_remaining = (end_date - today).days

                if days_remaining not in user_alert_days:
                    continue

                # Determine alert_type label
                if days_remaining >= 15:
                    alert_type = "15d"
                elif days_remaining >= 5:
                    alert_type = "5d"
                else:
                    alert_type = "1d"

                # Check notification_log for duplicates
                dup_result = await db.execute(
                    """
                    SELECT id FROM notification_log
                    WHERE user_id = ? AND deadline_id = ? AND alert_type = ?
                    """,
                    [user_id, deadline["id"], alert_type],
                )
                if dup_result.rows:
                    stats["notifications_skipped_duplicate"] += 1
                    continue

                # Build message
                try:
                    end_date_str = f"{end_date.day} de {end_date.strftime('%B').lower()}"
                except Exception:
                    end_date_str = str(end_date)
                model_info = f"{deadline['model_name']} ({deadline['territory']})"

                if days_remaining >= 15:
                    title = "Recordatorio fiscal"
                    body = f"Recuerda: {model_info} vence el {end_date_str}"
                elif days_remaining >= 5:
                    title = "Plazo fiscal proximo"
                    body = f"Quedan {days_remaining} dias para presentar {model_info}"
                else:
                    title = "ULTIMO DIA — Plazo fiscal"
                    body = f"ULTIMO DIA: {model_info} vence manana"

                # Send push
                push_result = await send_push(
                    user_id=user_id,
                    title=title,
                    body=body,
                    url="/calendario",
                    tag=f"deadline-{deadline['id']}",
                    db=db,
                )

                if push_result["sent"] > 0:
                    # Log the notification (idempotent via UNIQUE constraint)
                    try:
                        await db.execute(
                            """
                            INSERT OR IGNORE INTO notification_log (id, user_id, deadline_id, alert_type)
                            VALUES (?, ?, ?, ?)
                            """,
                            [str(uuid.uuid4()), user_id, deadline["id"], alert_type],
                        )
                        daily_counts[user_id] += 1
                        stats["notifications_sent"] += 1
                    except Exception as log_exc:
                        logger.error(f"Failed to log notification: {log_exc}")
                        stats["errors"] += 1
                else:
                    if push_result["failed"] > 0:
                        stats["errors"] += 1

    except Exception as exc:
        logger.error(f"send_deadline_alerts failed: {exc}")
        stats["errors"] += 1

    logger.info(f"send_deadline_alerts completed: {stats}")
    return stats
