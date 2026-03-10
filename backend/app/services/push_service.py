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


def _build_deadline_email_html(deadlines: list[dict], frontend_url: str) -> str:
    """
    Build a branded HTML email body listing upcoming fiscal deadlines.

    Args:
        deadlines: List of deadline dicts from fiscal_deadlines table
        frontend_url: Base URL for the unsubscribe/profile link

    Returns:
        HTML string
    """
    rows_html = ""
    for dl in deadlines:
        rows_html += f"""
        <tr>
            <td style="padding: 10px 12px; border-bottom: 1px solid #e8ecf0;">
                <strong>{dl['model_name']}</strong>
            </td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #e8ecf0; color: #555;">
                {dl.get('period', '')}
            </td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #e8ecf0; color: #c0392b; font-weight: 600;">
                {dl['end_date']}
            </td>
        </tr>"""

    profile_url = f"{frontend_url}/perfil"

    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
                max-width: 600px; margin: 0 auto; background: #ffffff;">

        <!-- Header -->
        <div style="background: linear-gradient(135deg, #1a56db 0%, #1e3a8a 100%);
                    color: white; padding: 28px 32px; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.3px;">
                Impuestify
            </h1>
            <p style="margin: 6px 0 0 0; opacity: 0.85; font-size: 14px;">
                Recordatorio de plazos fiscales — 30 dias
            </p>
        </div>

        <!-- Body -->
        <div style="padding: 28px 32px; background: #f8fafc;">
            <p style="margin: 0 0 20px 0; color: #1a202c; font-size: 15px; line-height: 1.6;">
                Tienes los siguientes plazos fiscales que vencen en los proximos <strong>30 dias</strong>.
                Recuerda presentarlos a tiempo para evitar recargos.
            </p>

            <!-- Deadlines table -->
            <div style="background: white; border-radius: 8px; overflow: hidden;
                        border: 1px solid #e2e8f0; margin-bottom: 24px;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background: #f1f5f9;">
                            <th style="padding: 10px 12px; text-align: left; color: #374151;
                                       font-weight: 600; border-bottom: 2px solid #e2e8f0;">
                                Modelo
                            </th>
                            <th style="padding: 10px 12px; text-align: left; color: #374151;
                                       font-weight: 600; border-bottom: 2px solid #e2e8f0;">
                                Periodo
                            </th>
                            <th style="padding: 10px 12px; text-align: left; color: #374151;
                                       font-weight: 600; border-bottom: 2px solid #e2e8f0;">
                                Fecha limite
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>

            <!-- CTA -->
            <div style="text-align: center; margin-bottom: 24px;">
                <a href="{frontend_url}/calendario"
                   style="display: inline-block; background: #1a56db; color: white;
                          text-decoration: none; padding: 12px 28px; border-radius: 6px;
                          font-size: 15px; font-weight: 600;">
                    Ver calendario fiscal
                </a>
            </div>

            <!-- Divider -->
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">

            <!-- Footer disclaimer -->
            <p style="color: #6b7280; font-size: 12px; margin: 0; line-height: 1.5;">
                Este recordatorio es meramente informativo y no constituye asesoramiento fiscal
                profesional. Consulta con un gestor o asesor fiscal antes de presentar tus
                declaraciones.<br><br>
                Puedes desactivar estos recordatorios en cualquier momento desde tu
                <a href="{profile_url}" style="color: #1a56db; text-decoration: underline;">
                    perfil en Impuestify</a>.
            </p>
        </div>

    </div>
    """


async def send_deadline_email_alerts(db: Optional[TursoClient] = None) -> dict:
    """
    Cron job: send email reminders 30 days before fiscal deadlines.

    Logic:
    1. Find all autonomo users with deadline_email_alerts = 1.
    2. For each user, look up deadlines with end_date exactly 30 days from today.
    3. Skip if a notification_log entry with alert_type='email_30d' already exists
       (idempotency — one email per user per deadline).
    4. Send a single batched HTML email listing all qualifying deadlines.
    5. Log each deadline individually to notification_log.

    Returns:
        dict with summary stats
    """
    from app.services.email_service import get_email_service
    from app.config import settings as _settings

    own_db = db is None
    if own_db:
        db = await get_db_client()

    today = date.today()
    target_date = today + timedelta(days=30)
    target_str = target_date.isoformat()

    stats = {
        "users_checked": 0,
        "emails_sent": 0,
        "emails_skipped_duplicate": 0,
        "emails_skipped_no_deadlines": 0,
        "errors": 0,
    }

    try:
        # Fetch autonomo users who opted in to email alerts
        opted_in_result = await db.execute(
            """
            SELECT up.user_id, u.email
            FROM user_profiles up
            JOIN users u ON u.id = up.user_id
            WHERE up.situacion_laboral = 'autonomo'
              AND up.deadline_email_alerts = 1
              AND u.is_active = 1
            """,
            [],
        )
        opted_in_users = opted_in_result.rows or []
        stats["users_checked"] = len(opted_in_users)

        if not opted_in_users:
            logger.info("send_deadline_email_alerts: no opted-in autonomo users found")
            return stats

        # Fetch all active deadlines ending exactly 30 days from today
        deadlines_result = await db.execute(
            """
            SELECT id, model, model_name, territory, period, tax_year, end_date, applies_to
            FROM fiscal_deadlines
            WHERE is_active = 1
              AND end_date = ?
              AND applies_to IN ('todos', 'autonomos')
            ORDER BY end_date ASC
            """,
            [target_str],
        )
        all_deadlines = deadlines_result.rows or []

        if not all_deadlines:
            logger.info(
                f"send_deadline_email_alerts: no deadlines on {target_str} — nothing to send"
            )
            stats["emails_skipped_no_deadlines"] = len(opted_in_users)
            return stats

        email_service = get_email_service()
        frontend_url = _settings.FRONTEND_URL.rstrip("/")

        for user in opted_in_users:
            user_id = user["user_id"]
            user_email = user["email"]

            # Filter out deadlines already logged for this user
            new_deadlines = []
            for dl in all_deadlines:
                dup_result = await db.execute(
                    """
                    SELECT id FROM notification_log
                    WHERE user_id = ? AND deadline_id = ? AND alert_type = 'email_30d'
                    """,
                    [user_id, dl["id"]],
                )
                if dup_result.rows:
                    stats["emails_skipped_duplicate"] += 1
                else:
                    new_deadlines.append(dl)

            if not new_deadlines:
                logger.debug(f"All deadlines already emailed to user {user_id}")
                continue

            # Build and send a single email listing all new deadlines
            # Use the first model name for a concise subject; list all in body
            if len(new_deadlines) == 1:
                subject = (
                    f"Recordatorio: {new_deadlines[0]['model_name']} "
                    f"vence el {new_deadlines[0]['end_date']}"
                )
            else:
                subject = (
                    f"Recordatorio: {len(new_deadlines)} plazos fiscales "
                    f"vencen el {target_str}"
                )

            html = _build_deadline_email_html(new_deadlines, frontend_url)

            try:
                send_result = await email_service.send_email(
                    to=user_email,
                    subject=subject,
                    html=html,
                )
            except Exception as send_exc:
                logger.error(
                    f"send_deadline_email_alerts: failed to send email to {user_email}: {send_exc}"
                )
                stats["errors"] += 1
                continue

            if not send_result.get("success"):
                logger.error(
                    f"send_deadline_email_alerts: Resend error for {user_email}: "
                    f"{send_result.get('error')}"
                )
                stats["errors"] += 1
                continue

            # Log each deadline individually for idempotency
            for dl in new_deadlines:
                try:
                    await db.execute(
                        """
                        INSERT OR IGNORE INTO notification_log (id, user_id, deadline_id, alert_type)
                        VALUES (?, ?, ?, 'email_30d')
                        """,
                        [str(uuid.uuid4()), user_id, dl["id"]],
                    )
                except Exception as log_exc:
                    logger.error(
                        f"send_deadline_email_alerts: failed to log notification "
                        f"for user {user_id} / deadline {dl['id']}: {log_exc}"
                    )
                    stats["errors"] += 1

            stats["emails_sent"] += 1
            logger.info(
                f"Email reminder sent to {user_email} for {len(new_deadlines)} deadline(s)"
            )

    except Exception as exc:
        logger.error(f"send_deadline_email_alerts failed: {exc}")
        stats["errors"] += 1

    logger.info(f"send_deadline_email_alerts completed: {stats}")
    return stats
