"""
WebAuthn / Passkey handler for Impuestify (NIST SP 800-63-4 phishing-resistant 2FA).

Endpoints (registered in routers/auth.py):
  POST /auth/webauthn/register/begin     -> options for navigator.credentials.create()
  POST /auth/webauthn/register/complete  -> verify + persist credential
  POST /auth/webauthn/login/begin        -> options for navigator.credentials.get()
  POST /auth/webauthn/login/complete     -> verify + issue JWT (same as /auth/login)

Server side challenges are kept in Upstash Redis with a 5-minute TTL keyed by
session/user, so we don't add yet another DB table for one-shot state.

TOTP remains available; passkeys are an ADDITIONAL strong factor users can
enable. Login flow accepts either passkey OR password+TOTP.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


CHALLENGE_TTL_SECONDS = 300  # 5 minutes


# ── Helpers ─────────────────────────────────────────────────────────────────


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _rp_settings() -> tuple[str, str, list[str]]:
    """Resolve RP id, name, and accepted origins from app config + env."""
    from app.config import settings

    frontend_url = getattr(settings, "FRONTEND_URL", "https://impuestify.com")
    parsed = urlparse(frontend_url)
    rp_id = parsed.hostname or "impuestify.com"
    rp_name = "Impuestify"
    allowed = [frontend_url.rstrip("/")]
    extra = os.getenv("WEBAUTHN_EXTRA_ORIGINS", "")
    for o in [s.strip() for s in extra.split(",") if s.strip()]:
        allowed.append(o.rstrip("/"))
    return rp_id, rp_name, allowed


# ── Challenge store (Upstash) ───────────────────────────────────────────────


def _challenge_key(scope: str, ident: str) -> str:
    return f"webauthn:{scope}:{ident}"


def _store_challenge(
    redis, scope: str, ident: str, challenge: bytes, payload: Optional[dict] = None
) -> None:
    if redis is None:
        return
    payload = payload or {}
    payload["challenge"] = _b64url_encode(challenge)
    raw = json.dumps(payload)
    try:
        if hasattr(redis, "setex"):
            redis.setex(_challenge_key(scope, ident), CHALLENGE_TTL_SECONDS, raw)
        else:
            redis.set(_challenge_key(scope, ident), raw, ex=CHALLENGE_TTL_SECONDS)
    except Exception as e:
        logger.warning(f"Could not store webauthn challenge: {e}")


def _pop_challenge(redis, scope: str, ident: str) -> Optional[dict]:
    if redis is None:
        return None
    try:
        raw = redis.get(_challenge_key(scope, ident))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="ignore")
        try:
            redis.delete(_challenge_key(scope, ident))
        except Exception:
            pass
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Could not pop webauthn challenge: {e}")
        return None


# ── Public API ──────────────────────────────────────────────────────────────


@dataclass
class RegistrationOptions:
    rp_id: str
    rp_name: str
    user_id_b64: str
    user_name: str
    challenge_b64: str
    exclude_credentials: List[dict]


@dataclass
class AuthenticationOptions:
    rp_id: str
    challenge_b64: str
    allow_credentials: List[dict]


class WebAuthnService:
    """Thin wrapper around the `webauthn` python lib."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self.redis = redis

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client

        self._db = await get_db_client()
        return self._db

    # ── Registration ───────────────────────────────────────────────────────

    async def begin_registration(self, user_id: str, user_email: str) -> RegistrationOptions:
        from webauthn import generate_registration_options
        from webauthn.helpers.structs import (
            AuthenticatorSelectionCriteria,
            UserVerificationRequirement,
            ResidentKeyRequirement,
        )

        rp_id, rp_name, _ = _rp_settings()
        db = await self._get_db()

        # Avoid registering the same authenticator twice
        existing = await db.execute(
            "SELECT credential_id FROM webauthn_credentials WHERE user_id = ?",
            [user_id],
        )
        exclude = [
            {"id": row["credential_id"], "type": "public-key"} for row in existing.rows or []
        ]

        opts = generate_registration_options(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id=user_id.encode("utf-8"),
            user_name=user_email,
            user_display_name=user_email,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        # Persist challenge so /complete can verify it
        _store_challenge(
            self.redis,
            scope="register",
            ident=user_id,
            challenge=opts.challenge,
            payload={"user_id": user_id, "user_email": user_email},
        )

        return RegistrationOptions(
            rp_id=rp_id,
            rp_name=rp_name,
            user_id_b64=_b64url_encode(user_id.encode("utf-8")),
            user_name=user_email,
            challenge_b64=_b64url_encode(opts.challenge),
            exclude_credentials=exclude,
        )

    async def complete_registration(
        self, user_id: str, credential_response: dict, label: Optional[str] = None
    ) -> str:
        from webauthn import verify_registration_response

        rp_id, _, allowed_origins = _rp_settings()
        challenge_data = _pop_challenge(self.redis, scope="register", ident=user_id)
        if not challenge_data:
            raise ValueError("No hay desafío activo. Reinicia el registro de la passkey.")
        challenge = _b64url_decode(challenge_data["challenge"])

        verification = verify_registration_response(
            credential=credential_response,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=allowed_origins,
            require_user_verification=False,
        )

        cred_id = _b64url_encode(verification.credential_id)
        public_key = _b64url_encode(verification.credential_public_key)

        db = await self._get_db()
        row_id = str(uuid.uuid4())
        await db.execute(
            """
            INSERT INTO webauthn_credentials
                (id, user_id, credential_id, public_key, sign_count, transports, label, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                row_id,
                user_id,
                cred_id,
                public_key,
                int(verification.sign_count),
                json.dumps(credential_response.get("response", {}).get("transports") or []),
                label or "Passkey",
                datetime.now(timezone.utc).isoformat(),
            ],
        )
        return row_id

    # ── Authentication ─────────────────────────────────────────────────────

    async def begin_login(self, user_email: str) -> AuthenticationOptions:
        from webauthn import generate_authentication_options
        from webauthn.helpers.structs import UserVerificationRequirement

        rp_id, _, _ = _rp_settings()
        db = await self._get_db()

        user_row = await db.execute(
            "SELECT id FROM users WHERE email = ? LIMIT 1",
            [user_email.lower()],
        )
        if not user_row.rows:
            # Don't leak whether the email exists. Generate a random challenge
            # the client can complete with no credentials — verify will fail.
            challenge = secrets.token_bytes(32)
            return AuthenticationOptions(
                rp_id=rp_id, challenge_b64=_b64url_encode(challenge), allow_credentials=[]
            )

        user_id = user_row.rows[0]["id"]
        creds = await db.execute(
            "SELECT credential_id FROM webauthn_credentials WHERE user_id = ?",
            [user_id],
        )
        allow = [{"id": row["credential_id"], "type": "public-key"} for row in creds.rows or []]

        opts = generate_authentication_options(
            rp_id=rp_id,
            allow_credentials=[],  # we send our own list to the client; server uses cred lookup
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        _store_challenge(
            self.redis,
            scope="login",
            ident=user_email.lower(),
            challenge=opts.challenge,
            payload={"user_id": user_id, "user_email": user_email.lower()},
        )

        return AuthenticationOptions(
            rp_id=rp_id,
            challenge_b64=_b64url_encode(opts.challenge),
            allow_credentials=allow,
        )

    async def complete_login(self, user_email: str, credential_response: dict) -> str:
        """Verify the assertion. Returns the user_id on success. Raises ValueError on failure."""
        from webauthn import verify_authentication_response

        rp_id, _, allowed_origins = _rp_settings()
        challenge_data = _pop_challenge(self.redis, scope="login", ident=user_email.lower())
        if not challenge_data:
            raise ValueError("No hay desafío de inicio de sesión activo.")
        challenge = _b64url_decode(challenge_data["challenge"])
        user_id = challenge_data.get("user_id")

        cred_id_b64 = credential_response.get("id") or credential_response.get("rawId")
        if not cred_id_b64:
            raise ValueError("Respuesta de credencial inválida.")

        db = await self._get_db()
        cred_row = await db.execute(
            "SELECT id, user_id, credential_id, public_key, sign_count "
            "FROM webauthn_credentials WHERE credential_id = ? LIMIT 1",
            [cred_id_b64],
        )
        if not cred_row.rows:
            raise ValueError("Credencial no encontrada.")
        cred = dict(cred_row.rows[0])
        if user_id and cred["user_id"] != user_id:
            raise ValueError("Credencial no pertenece a este usuario.")

        verification = verify_authentication_response(
            credential=credential_response,
            expected_challenge=challenge,
            expected_rp_id=rp_id,
            expected_origin=allowed_origins,
            credential_public_key=_b64url_decode(cred["public_key"]),
            credential_current_sign_count=int(cred["sign_count"]),
            require_user_verification=False,
        )

        # Update sign_count + last_used_at
        await db.execute(
            "UPDATE webauthn_credentials SET sign_count = ?, last_used_at = ? WHERE id = ?",
            [
                int(verification.new_sign_count),
                datetime.now(timezone.utc).isoformat(),
                cred["id"],
            ],
        )
        return cred["user_id"]

    # ── Management ─────────────────────────────────────────────────────────

    async def list_credentials(self, user_id: str) -> List[dict]:
        db = await self._get_db()
        result = await db.execute(
            "SELECT id, label, created_at, last_used_at "
            "FROM webauthn_credentials WHERE user_id = ? ORDER BY created_at DESC",
            [user_id],
        )
        return [dict(row) for row in result.rows or []]

    async def delete_credential(self, user_id: str, cred_row_id: str) -> bool:
        db = await self._get_db()
        await db.execute(
            "DELETE FROM webauthn_credentials WHERE id = ? AND user_id = ?",
            [cred_row_id, user_id],
        )
        return True
