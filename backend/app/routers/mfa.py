"""
MFA (Multi-Factor Authentication) Router for Impuestify

Provides TOTP-based 2FA: setup, verify, disable, status, and login validation.
Uses pyotp for TOTP generation/verification and qrcode for QR code generation.
"""
import io
import json
import base64
import logging
import secrets
from typing import List, Optional

import bcrypt
import pyotp
import qrcode
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field

from app.auth.jwt_handler import (
    create_tokens_for_user,
    create_mfa_token,
    verify_token,
    get_current_user_required,
    TokenData,
    TokenResponse,
)
from app.database.turso_client import get_db_client
from app.security.rate_limiter import limiter
from app.services.user_service import user_service
from app.services.subscription_service import get_subscription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/mfa", tags=["MFA"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class MFASetupResponse(BaseModel):
    """Response for MFA setup — contains QR code and backup codes."""
    qr_code_base64: str
    secret: str
    backup_codes: List[str]
    uri: str


class MFAVerifyRequest(BaseModel):
    """Request to verify a TOTP code and enable MFA."""
    code: str = Field(..., min_length=6, max_length=6)


class MFAVerifyResponse(BaseModel):
    """Response after MFA verification succeeds."""
    success: bool
    backup_codes: List[str]


class MFADisableRequest(BaseModel):
    """Request to disable MFA."""
    code: str = Field(..., min_length=6, max_length=10)


class MFAStatusResponse(BaseModel):
    """Current MFA status for the authenticated user."""
    enabled: bool


class MFAValidateRequest(BaseModel):
    """Request to validate MFA during login flow."""
    mfa_token: str
    code: str = Field(..., min_length=6, max_length=10)


class MFALoginResponse(BaseModel):
    """Response after successful MFA login validation."""
    user: dict
    tokens: TokenResponse


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _generate_backup_codes(count: int = 10) -> List[str]:
    """Generate a list of random backup codes."""
    return [secrets.token_hex(4) for _ in range(count)]


def _hash_backup_codes(codes: List[str]) -> str:
    """Hash each backup code with bcrypt and return a JSON array."""
    hashed = []
    for code in codes:
        h = bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt(rounds=10))
        hashed.append(h.decode("utf-8"))
    return json.dumps(hashed)


def _verify_backup_code(plain_code: str, hashed_codes_json: Optional[str]) -> Optional[int]:
    """Check plain_code against hashed backup codes.

    Returns the index of the matching code if found, else None.
    """
    if not hashed_codes_json:
        return None
    try:
        hashed_list = json.loads(hashed_codes_json)
    except (json.JSONDecodeError, TypeError):
        return None
    for idx, hashed in enumerate(hashed_list):
        if hashed and bcrypt.checkpw(plain_code.encode("utf-8"), hashed.encode("utf-8")):
            return idx
    return None


def _remove_backup_code_at_index(hashed_codes_json: str, index: int) -> str:
    """Mark a used backup code as None (consumed)."""
    hashed_list = json.loads(hashed_codes_json)
    hashed_list[index] = None
    return json.dumps(hashed_list)


def _generate_qr_base64(uri: str) -> str:
    """Generate a QR code PNG as a base64-encoded string."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(current_user: TokenData = Depends(get_current_user_required)):
    """
    Begin MFA setup for the authenticated user.

    Generates a TOTP secret, QR code, and backup codes.
    MFA is NOT enabled until the user confirms with /verify.
    """
    db = await get_db_client()
    user = await user_service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Check if MFA is already enabled
    result = await db.execute(
        "SELECT is_enabled FROM user_mfa WHERE user_id = ?",
        [current_user.user_id],
    )
    if result.rows and result.rows[0]["is_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA ya está activado. Desactívalo primero para reconfigurarlo.",
        )

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name="Impuestify")
    qr_b64 = _generate_qr_base64(uri)
    backup_codes = _generate_backup_codes(10)
    hashed_codes = _hash_backup_codes(backup_codes)

    # Upsert — replace any previous incomplete setup
    await db.execute(
        """INSERT INTO user_mfa (user_id, totp_secret, is_enabled, backup_codes, created_at, updated_at)
           VALUES (?, ?, 0, ?, datetime('now'), datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET
               totp_secret = excluded.totp_secret,
               is_enabled = 0,
               backup_codes = excluded.backup_codes,
               updated_at = datetime('now')""",
        [current_user.user_id, secret, hashed_codes],
    )

    logger.info("MFA setup initiated for user %s", current_user.user_id)

    return MFASetupResponse(
        qr_code_base64=qr_b64,
        secret=secret,
        backup_codes=backup_codes,
        uri=uri,
    )


@router.post("/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    body: MFAVerifyRequest,
    current_user: TokenData = Depends(get_current_user_required),
):
    """
    Verify a TOTP code to complete MFA setup.

    After successful verification, MFA is enabled for the user.
    Returns the backup codes one final time (they should be stored securely by the user).
    """
    db = await get_db_client()

    result = await db.execute(
        "SELECT totp_secret, is_enabled, backup_codes FROM user_mfa WHERE user_id = ?",
        [current_user.user_id],
    )
    if not result.rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primero debes iniciar la configuración de MFA con /setup.",
        )

    row = result.rows[0]
    if row["is_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA ya está activado.",
        )

    totp = pyotp.TOTP(row["totp_secret"])
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código TOTP inválido. Inténtalo de nuevo.",
        )

    # Enable MFA
    await db.execute(
        "UPDATE user_mfa SET is_enabled = 1, updated_at = datetime('now') WHERE user_id = ?",
        [current_user.user_id],
    )

    logger.info("MFA enabled for user %s", current_user.user_id)

    # Return backup codes — the plain-text versions were generated in /setup.
    # We cannot return them again since we only store hashed versions.
    # The frontend should have stored them from the /setup response.
    # We return an empty list here to signal success; the setup response was the
    # only time plain backup codes were available.
    return MFAVerifyResponse(success=True, backup_codes=[])


@router.post("/disable")
async def disable_mfa(
    body: MFADisableRequest,
    current_user: TokenData = Depends(get_current_user_required),
):
    """
    Disable MFA for the authenticated user.

    Requires a valid TOTP code or backup code.
    """
    db = await get_db_client()

    result = await db.execute(
        "SELECT totp_secret, is_enabled, backup_codes FROM user_mfa WHERE user_id = ?",
        [current_user.user_id],
    )
    if not result.rows or not result.rows[0]["is_enabled"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA no está activado.",
        )

    row = result.rows[0]
    totp = pyotp.TOTP(row["totp_secret"])
    code_valid = totp.verify(body.code, valid_window=1)

    if not code_valid:
        # Try backup code
        idx = _verify_backup_code(body.code, row["backup_codes"])
        if idx is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código inválido. Usa un código TOTP o un código de respaldo.",
            )

    # Remove MFA record entirely
    await db.execute("DELETE FROM user_mfa WHERE user_id = ?", [current_user.user_id])

    logger.info("MFA disabled for user %s", current_user.user_id)

    return {"success": True}


@router.get("/status", response_model=MFAStatusResponse)
async def mfa_status(current_user: TokenData = Depends(get_current_user_required)):
    """
    Check whether MFA is enabled for the authenticated user.
    """
    db = await get_db_client()

    result = await db.execute(
        "SELECT is_enabled FROM user_mfa WHERE user_id = ?",
        [current_user.user_id],
    )
    enabled = bool(result.rows and result.rows[0]["is_enabled"])

    return MFAStatusResponse(enabled=enabled)


@router.post("/validate")
@limiter.limit("5/minute")
async def validate_mfa(request: Request, body: MFAValidateRequest):
    """
    Validate a TOTP/backup code during the login flow.

    Receives the short-lived mfa_token (issued at login when MFA is required)
    and a TOTP or backup code.  On success, returns full access + refresh tokens.
    """
    # Verify mfa_token
    token_data = verify_token(body.mfa_token, token_type="mfa_pending")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token MFA inválido o expirado. Inicia sesión de nuevo.",
        )

    db = await get_db_client()

    result = await db.execute(
        "SELECT totp_secret, is_enabled, backup_codes FROM user_mfa WHERE user_id = ? AND is_enabled = 1",
        [token_data.user_id],
    )
    if not result.rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA no está activado para este usuario.",
        )

    row = result.rows[0]
    totp = pyotp.TOTP(row["totp_secret"])
    code_valid = totp.verify(body.code, valid_window=1)

    if not code_valid:
        # Try backup code
        idx = _verify_backup_code(body.code, row["backup_codes"])
        if idx is not None:
            # Mark backup code as used
            new_codes = _remove_backup_code_at_index(row["backup_codes"], idx)
            await db.execute(
                "UPDATE user_mfa SET backup_codes = ?, updated_at = datetime('now') WHERE user_id = ?",
                [new_codes, token_data.user_id],
            )
            code_valid = True

    if not code_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código MFA inválido.",
        )

    # MFA validated — issue full tokens
    user = await user_service.get_user_by_id(token_data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
        )

    sub_service = await get_subscription_service()
    access = await sub_service.check_access(user_id=user.id, email=user.email)

    tokens = create_tokens_for_user(user.id, user.email)

    logger.info("MFA validated for user %s", user.id)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "is_owner": getattr(access, "is_owner", False),
            "subscription_status": getattr(access, "status", None),
        },
        "tokens": tokens.model_dump(),
    }
