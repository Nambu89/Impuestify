"""
Refresh-token rotation + reuse-detection store.

Implements OWASP ASVS 5.0 Verification 4.2.5:
  - Each refresh token is single-use.
  - When the SAME refresh token is presented twice, every refresh token for
    the user is revoked AND the security team is alerted.
  - On normal rotation, the old token's `used_at` is set and a new token is
    issued with a new jti.

Storage: existing `sessions` table (extended with used_at, revoked_at,
rotated_to columns via init_schema).

Hashing: we store SHA-256 of the JWT compact form so the database never
holds the raw token. The `jti` claim is also stored as the row primary key
for fast lookups.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RotationResult:
    ok: bool
    user_id: str | None = None
    reason: str | None = None  # 'reuse_detected', 'unknown', 'revoked', 'expired', 'ok'
    revoked_count: int = 0


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RefreshTokenStore:
    def __init__(self, db=None):
        self._db = db

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client

        self._db = await get_db_client()
        return self._db

    async def register(self, jti: str, user_id: str, raw_token: str, ttl_days: int) -> None:
        """Persist a freshly-issued refresh token."""
        db = await self._get_db()
        expires = (datetime.now(UTC) + timedelta(days=ttl_days)).isoformat()
        await db.execute(
            """
            INSERT INTO sessions
                (id, user_id, refresh_token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            """,
            [jti, user_id, _hash(raw_token), expires],
        )

    async def validate_and_consume(self, jti: str, raw_token: str, user_id: str) -> RotationResult:
        """
        Validate a presented refresh token.

        On reuse (used_at not null) we revoke ALL of the user's sessions and
        return ok=False with reason='reuse_detected'.

        On success we mark used_at and return ok=True. The caller must then
        call register() with the new jti returned by create_refresh_token().
        """
        db = await self._get_db()

        result = await db.execute(
            "SELECT id, user_id, refresh_token_hash, expires_at, used_at, revoked_at "
            "FROM sessions WHERE id = ? LIMIT 1",
            [jti],
        )
        if not result.rows:
            # Unknown jti — could be revoked already (we delete on logout) or
            # a forged token. Either way, refuse and revoke everything for this
            # user as a precaution.
            revoked = await self.revoke_all_for_user(user_id, reason="unknown_jti")
            logger.warning(
                f"Refresh token unknown jti={jti} for user={user_id}, revoked {revoked} sessions"
            )
            return RotationResult(
                ok=False, user_id=user_id, reason="unknown", revoked_count=revoked
            )

        row = dict(result.rows[0])

        if row["user_id"] != user_id:
            logger.error(
                f"Refresh token jti={jti} user mismatch (claim={user_id}, db={row['user_id']})"
            )
            revoked = await self.revoke_all_for_user(user_id, reason="user_mismatch")
            return RotationResult(
                ok=False, user_id=user_id, reason="user_mismatch", revoked_count=revoked
            )

        if _hash(raw_token) != row["refresh_token_hash"]:
            logger.error(f"Refresh token jti={jti} hash mismatch")
            revoked = await self.revoke_all_for_user(user_id, reason="hash_mismatch")
            return RotationResult(
                ok=False, user_id=user_id, reason="hash_mismatch", revoked_count=revoked
            )

        if row.get("revoked_at"):
            logger.warning(f"Refresh token jti={jti} already revoked at {row['revoked_at']}")
            return RotationResult(ok=False, user_id=user_id, reason="revoked")

        # Expiry check
        try:
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            if expires_at <= datetime.now(UTC):
                return RotationResult(ok=False, user_id=user_id, reason="expired")
        except Exception:
            pass

        if row.get("used_at"):
            # === REUSE DETECTED ===
            # The same refresh token presented twice. Revoke all sessions for
            # this user and notify the user via email.
            revoked = await self.revoke_all_for_user(user_id, reason="refresh_token_reuse")
            logger.error(
                f"REFRESH TOKEN REUSE DETECTED for user={user_id} jti={jti}. "
                f"Revoked {revoked} sessions."
            )
            try:
                await self._notify_reuse(user_id)
            except Exception as e:
                logger.warning(f"Could not send reuse-detection email: {e}")
            return RotationResult(
                ok=False,
                user_id=user_id,
                reason="reuse_detected",
                revoked_count=revoked,
            )

        # Mark this token used; the caller will register the new one.
        await db.execute(
            "UPDATE sessions SET used_at = datetime('now') WHERE id = ?",
            [jti],
        )
        return RotationResult(ok=True, user_id=user_id, reason="ok")

    async def link_rotation(self, old_jti: str, new_jti: str) -> None:
        """Record the old->new chain so we can audit."""
        db = await self._get_db()
        try:
            await db.execute(
                "UPDATE sessions SET rotated_to = ? WHERE id = ?",
                [new_jti, old_jti],
            )
        except Exception as e:
            logger.warning(f"Could not link rotation {old_jti}->{new_jti}: {e}")

    async def revoke_all_for_user(self, user_id: str, reason: str = "logout") -> int:
        """Revoke every active session/refresh token for this user."""
        db = await self._get_db()
        try:
            count_result = await db.execute(
                "SELECT COUNT(*) AS c FROM sessions WHERE user_id = ? AND revoked_at IS NULL",
                [user_id],
            )
            count = (count_result.rows[0]["c"] if count_result.rows else 0) or 0
            await db.execute(
                "UPDATE sessions SET revoked_at = datetime('now') "
                "WHERE user_id = ? AND revoked_at IS NULL",
                [user_id],
            )
            logger.info(f"Revoked {count} sessions for user={user_id} reason={reason}")
            return int(count)
        except Exception as e:
            logger.error(f"revoke_all_for_user failed: {e}")
            return 0

    async def _notify_reuse(self, user_id: str) -> None:
        """Email the user that we detected token reuse and forced a logout."""
        from app.services.email_service import EmailService

        db = await self._get_db()
        u = await db.execute("SELECT email, name FROM users WHERE id = ?", [user_id])
        if not u.rows:
            return
        email = u.rows[0]["email"]
        name = u.rows[0].get("name") or ""

        body = (
            f"<h2>Hemos cerrado tu sesión por seguridad</h2>"
            f"<p>Hola {name or ''},</p>"
            f"<p>Detectamos que un token de sesión de tu cuenta de Impuestify "
            f"se ha intentado usar dos veces. Esto puede indicar que alguien "
            f"intentó copiar tu sesión.</p>"
            f"<p>Por seguridad hemos cerrado todas tus sesiones. Por favor, "
            f"vuelve a iniciar sesión y considera cambiar tu contraseña si "
            f"no fuiste tú.</p>"
            f"<p>Si tienes dudas, responde a este email.</p>"
            f"<p>— Equipo Impuestify</p>"
        )
        try:
            svc = EmailService()
            await svc.send_email(
                to=email,
                subject="[Impuestify] Hemos cerrado tu sesión por seguridad",
                html=body,
            )
        except Exception as e:
            logger.warning(f"Reuse-detection email send failed: {e}")

        # Also alert the owner
        owner_email = os.getenv("OWNER_EMAIL")
        if owner_email and owner_email != email:
            try:
                svc = EmailService()
                await svc.send_email(
                    to=owner_email,
                    subject=f"[Impuestify] Token reuse detectado para {email}",
                    html=(
                        f"<p>Token reuse detectado y todas las sesiones revocadas.</p>"
                        f"<ul><li>user_id: {user_id}</li><li>email: {email}</li></ul>"
                    ),
                )
            except Exception:
                pass


# Module-level singleton for FastAPI to use
refresh_token_store = RefreshTokenStore()
