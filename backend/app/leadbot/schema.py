"""Esquema de tablas del leadbot — idempotente, sólo en DEMO_MODE.

Se invoca desde ``main.py`` en el lifespan, gateado por ``settings.DEMO_MODE``,
de modo que estas tablas NUNCA se crean en la base de datos de Impuestify
principal. No tocamos ``turso_client.init_schema()`` para mantener el core
intacto y evitar conflictos de merge con ``main``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_STATEMENTS: list[str] = [
    # Leads cualificados por el chatbot
    """
    CREATE TABLE IF NOT EXISTS leadbot_leads (
        id TEXT PRIMARY KEY,
        conversation_id TEXT,
        status TEXT NOT NULL DEFAULT 'new',  -- new|qualified|booked|lost|spam
        name TEXT,
        email TEXT,
        phone TEXT,
        company TEXT,
        sector TEXT,
        need TEXT,
        decision_maker INTEGER,              -- 0|1|NULL
        timeline TEXT,                       -- now|1-3m|3-6m|6m+
        budget_range TEXT,                   -- <1k|1-5k|5-15k|15k+
        source TEXT NOT NULL DEFAULT 'chat_widget',
        calendar_event_id TEXT,
        booking_slot TEXT,                   -- ISO8601 del hueco reservado
        transcript_summary TEXT,
        gdpr_consent_at TEXT,
        ip_hash TEXT,                        -- SHA256(ip+salt), NO PII en claro
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_leadbot_leads_status ON leadbot_leads(status)",
    "CREATE INDEX IF NOT EXISTS idx_leadbot_leads_email ON leadbot_leads(email)",
    "CREATE INDEX IF NOT EXISTS idx_leadbot_leads_conv ON leadbot_leads(conversation_id)",
    # Mensajes de la conversación del leadbot (público, sin tabla messages global)
    """
    CREATE TABLE IF NOT EXISTS leadbot_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,                  -- user|assistant
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_leadbot_messages_conv ON leadbot_messages(conversation_id)",
    # Refresh token de Google Calendar cifrado (Fernet)
    """
    CREATE TABLE IF NOT EXISTS leadbot_oauth_credentials (
        provider TEXT NOT NULL,             -- 'google_calendar'
        account_email TEXT NOT NULL,
        refresh_token_encrypted TEXT NOT NULL,
        scopes TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY (provider, account_email)
    )
    """,
    # Consumo diario por IP (anti-abuso / cost cap)
    """
    CREATE TABLE IF NOT EXISTS leadbot_daily_usage (
        ip_hash TEXT NOT NULL,
        date TEXT NOT NULL,
        tokens_in INTEGER DEFAULT 0,
        tokens_out INTEGER DEFAULT 0,
        conversations_count INTEGER DEFAULT 0,
        PRIMARY KEY (ip_hash, date)
    )
    """,
    # Magic-links para confirmar email antes de reservar cita
    """
    CREATE TABLE IF NOT EXISTS leadbot_email_verifications (
        token TEXT PRIMARY KEY,
        lead_id TEXT NOT NULL,
        slot_iso TEXT,
        attendee_email TEXT,
        attendee_name TEXT,
        expires_at TEXT NOT NULL,
        consumed_at TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_leadbot_verif_lead ON leadbot_email_verifications(lead_id)",
]


async def ensure_leadbot_schema(db) -> None:
    """Crea las tablas del leadbot si no existen. Idempotente, best-effort.

    Args:
        db: cliente Turso (``TursoClient``) ya conectado.
    """
    for stmt in _STATEMENTS:
        try:
            await db.execute(stmt)
        except Exception as exc:  # noqa: BLE001 — no abortar arranque del demo
            logger.error("leadbot schema stmt failed (non-fatal): %s", exc)
    logger.info("Leadbot schema verificado/creado")
