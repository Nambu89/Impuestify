"""Acceso a datos del leadbot — queries parametrizadas sobre Turso.

Todas las tablas viven en la misma DB demo (``demo-fiscal-melilla``) pero con
prefijo ``leadbot_`` para no colisionar con el esquema de Impuestify. NUNCA
f-strings en SQL: siempre placeholders ``?``.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Campos del lead que el agente puede actualizar vía save_lead_info.
LEAD_UPDATABLE = (
    "name",
    "email",
    "phone",
    "company",
    "sector",
    "need",
    "decision_maker",
    "timeline",
    "budget_range",
    "status",
    "transcript_summary",
    "calendar_event_id",
    "booking_slot",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def hash_ip(ip: str | None, salt: str = "leadbot") -> str:
    """SHA256(ip+salt) — guardamos el hash, nunca la IP en claro (RGPD)."""
    raw = f"{salt}:{ip or 'unknown'}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class LeadRepository:
    def __init__(self, db: Any):
        self.db = db

    # ----------------------------------------------------------------- leads
    async def create_lead(
        self,
        conversation_id: str,
        gdpr_consent_at: str | None,
        ip_hash: str | None,
        source: str = "chat_widget",
    ) -> str:
        lead_id = uuid.uuid4().hex
        await self.db.execute(
            """
            INSERT INTO leadbot_leads
                (id, conversation_id, status, source, gdpr_consent_at, ip_hash, created_at, updated_at)
            VALUES (?, ?, 'new', ?, ?, ?, ?, ?)
            """,
            [lead_id, conversation_id, source, gdpr_consent_at, ip_hash, _now_iso(), _now_iso()],
        )
        return lead_id

    async def get_lead(self, lead_id: str) -> dict | None:
        res = await self.db.execute("SELECT * FROM leadbot_leads WHERE id = ?", [lead_id])
        return res.rows[0] if res.rows else None

    async def get_lead_by_conversation(self, conversation_id: str) -> dict | None:
        res = await self.db.execute(
            "SELECT * FROM leadbot_leads WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 1",
            [conversation_id],
        )
        return res.rows[0] if res.rows else None

    async def update_lead(self, lead_id: str, **fields: Any) -> None:
        cols = [(k, v) for k, v in fields.items() if k in LEAD_UPDATABLE and v is not None]
        if not cols:
            return
        set_clause = ", ".join(f"{k} = ?" for k, _ in cols)
        params = [v for _, v in cols]
        params.append(_now_iso())  # updated_at
        params.append(lead_id)
        await self.db.execute(
            f"UPDATE leadbot_leads SET {set_clause}, updated_at = ? WHERE id = ?",
            params,
        )

    async def list_leads(self, status: str | None = None, limit: int = 200) -> list[dict]:
        limit = max(1, min(limit, 1000))
        if status:
            res = await self.db.execute(
                "SELECT * FROM leadbot_leads WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                [status, limit],
            )
        else:
            res = await self.db.execute(
                "SELECT * FROM leadbot_leads ORDER BY created_at DESC LIMIT ?",
                [limit],
            )
        return res.rows or []

    async def delete_by_email(self, email: str) -> int:
        """RGPD Art. 17. Borra leads + sus mensajes. Devuelve nº de leads borrados."""
        res = await self.db.execute(
            "SELECT id, conversation_id FROM leadbot_leads WHERE lower(email) = lower(?)",
            [email],
        )
        rows = res.rows or []
        for row in rows:
            conv = row.get("conversation_id")
            if conv:
                await self.db.execute(
                    "DELETE FROM leadbot_messages WHERE conversation_id = ?", [conv]
                )
            await self.db.execute(
                "DELETE FROM leadbot_email_verifications WHERE lead_id = ?", [row.get("id")]
            )
        await self.db.execute("DELETE FROM leadbot_leads WHERE lower(email) = lower(?)", [email])
        return len(rows)

    # -------------------------------------------------------------- messages
    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        await self.db.execute(
            "INSERT INTO leadbot_messages (id, conversation_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [uuid.uuid4().hex, conversation_id, role, content, _now_iso()],
        )

    async def get_messages(self, conversation_id: str, limit: int = 30) -> list[dict]:
        res = await self.db.execute(
            "SELECT role, content FROM leadbot_messages WHERE conversation_id = ? "
            "ORDER BY created_at ASC LIMIT ?",
            [conversation_id, max(1, min(limit, 100))],
        )
        return res.rows or []

    async def count_messages(self, conversation_id: str) -> int:
        res = await self.db.execute(
            "SELECT COUNT(*) AS cnt FROM leadbot_messages WHERE conversation_id = ?",
            [conversation_id],
        )
        return int(res.rows[0]["cnt"]) if res.rows else 0

    # ------------------------------------------------------------ oauth creds
    async def save_oauth_credential(
        self, account_email: str, refresh_token_encrypted: str, scopes: str
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO leadbot_oauth_credentials
                (provider, account_email, refresh_token_encrypted, scopes, created_at, updated_at)
            VALUES ('google_calendar', ?, ?, ?, ?, ?)
            ON CONFLICT(provider, account_email) DO UPDATE SET
                refresh_token_encrypted = excluded.refresh_token_encrypted,
                scopes = excluded.scopes,
                updated_at = excluded.updated_at
            """,
            [account_email, refresh_token_encrypted, scopes, _now_iso(), _now_iso()],
        )

    async def get_oauth_credential(self, account_email: str) -> dict | None:
        res = await self.db.execute(
            "SELECT * FROM leadbot_oauth_credentials WHERE provider = 'google_calendar' "
            "AND account_email = ?",
            [account_email],
        )
        return res.rows[0] if res.rows else None

    # ------------------------------------------------------------- daily usage
    async def add_usage(
        self, ip_hash: str, tokens_in: int, tokens_out: int, new_conversation: bool = False
    ) -> None:
        date = datetime.now(UTC).date().isoformat()
        await self.db.execute(
            """
            INSERT INTO leadbot_daily_usage (ip_hash, date, tokens_in, tokens_out, conversations_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ip_hash, date) DO UPDATE SET
                tokens_in = tokens_in + excluded.tokens_in,
                tokens_out = tokens_out + excluded.tokens_out,
                conversations_count = conversations_count + excluded.conversations_count
            """,
            [ip_hash, date, tokens_in, tokens_out, 1 if new_conversation else 0],
        )

    async def get_usage_today(self, ip_hash: str) -> dict:
        date = datetime.now(UTC).date().isoformat()
        res = await self.db.execute(
            "SELECT tokens_in, tokens_out, conversations_count FROM leadbot_daily_usage "
            "WHERE ip_hash = ? AND date = ?",
            [ip_hash, date],
        )
        if res.rows:
            return res.rows[0]
        return {"tokens_in": 0, "tokens_out": 0, "conversations_count": 0}

    # ------------------------------------------------- email verification (magic-link)
    async def create_verification(
        self,
        lead_id: str,
        slot_iso: str,
        attendee_email: str,
        attendee_name: str,
        ttl_minutes: int = 30,
    ) -> str:
        token = uuid.uuid4().hex
        expires = (datetime.now(UTC) + timedelta(minutes=ttl_minutes)).isoformat()
        await self.db.execute(
            """
            INSERT INTO leadbot_email_verifications
                (token, lead_id, slot_iso, attendee_email, attendee_name, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [token, lead_id, slot_iso, attendee_email, attendee_name, expires, _now_iso()],
        )
        return token

    async def get_verification(self, token: str) -> dict | None:
        res = await self.db.execute(
            "SELECT * FROM leadbot_email_verifications WHERE token = ?", [token]
        )
        return res.rows[0] if res.rows else None

    async def consume_verification(self, token: str) -> None:
        await self.db.execute(
            "UPDATE leadbot_email_verifications SET consumed_at = ? WHERE token = ?",
            [_now_iso(), token],
        )
