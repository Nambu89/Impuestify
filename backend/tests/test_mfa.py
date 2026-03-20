"""
Tests for MFA (Multi-Factor Authentication) — TOTP-based 2FA.

Covers: setup, verify, disable, status, login flow with MFA, backup codes.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pyotp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token_data(user_id="user-mfa-test", email="mfa@test.com"):
    """Build a mock TokenData."""
    from app.auth.jwt_handler import TokenData
    return TokenData(user_id=user_id, email=email)


def _make_user(user_id="user-mfa-test", email="mfa@test.com", name="MFA Tester"):
    """Build a mock User object."""
    mock = MagicMock()
    mock.id = user_id
    mock.email = email
    mock.name = name
    mock.is_active = True
    mock.is_admin = False
    return mock


def _make_db_result(rows=None):
    """Build a mock QueryResult."""
    mock = MagicMock()
    mock.rows = rows or []
    return mock


def _make_access():
    """Build a mock subscription access."""
    mock = MagicMock()
    mock.is_owner = False
    mock.status = "active"
    return mock


# ---------------------------------------------------------------------------
# test_setup_mfa_generates_qr
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_setup_mfa_generates_qr():
    """POST /api/auth/mfa/setup should generate QR code, secret, and backup codes."""
    from app.routers.mfa import setup_mfa

    token_data = _make_token_data()
    user = _make_user()

    with patch("app.routers.mfa.get_db_client") as mock_db, \
         patch("app.routers.mfa.user_service") as mock_us:

        db = AsyncMock()
        # First call: check if MFA already enabled — not found
        db.execute.return_value = _make_db_result([])
        mock_db.return_value = db
        mock_us.get_user_by_id = AsyncMock(return_value=user)

        resp = await setup_mfa(current_user=token_data)

    assert resp.qr_code_base64  # non-empty base64 PNG
    assert resp.secret  # 32-char base32
    assert len(resp.backup_codes) == 10
    assert resp.uri.startswith("otpauth://totp/")
    assert "Impuestify" in resp.uri
    # DB should have been called to upsert
    assert db.execute.call_count == 2  # 1 SELECT + 1 INSERT


# ---------------------------------------------------------------------------
# test_verify_mfa_with_valid_code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_mfa_with_valid_code():
    """POST /api/auth/mfa/verify should enable MFA when given a valid TOTP code."""
    from app.routers.mfa import verify_mfa, MFAVerifyRequest

    token_data = _make_token_data()
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    with patch("app.routers.mfa.get_db_client") as mock_db:
        db = AsyncMock()
        db.execute.return_value = _make_db_result([{
            "totp_secret": secret,
            "is_enabled": 0,
            "backup_codes": "[]",
        }])
        mock_db.return_value = db

        req = MFAVerifyRequest(code=valid_code)
        resp = await verify_mfa(body=req, current_user=token_data)

    assert resp.success is True
    # Second call should be the UPDATE to enable MFA
    update_call = db.execute.call_args_list[1]
    assert "is_enabled = 1" in update_call.args[0]


# ---------------------------------------------------------------------------
# test_verify_mfa_with_invalid_code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_mfa_with_invalid_code():
    """POST /api/auth/mfa/verify should reject an invalid TOTP code."""
    from app.routers.mfa import verify_mfa, MFAVerifyRequest
    from fastapi import HTTPException

    token_data = _make_token_data()
    secret = pyotp.random_base32()

    with patch("app.routers.mfa.get_db_client") as mock_db:
        db = AsyncMock()
        db.execute.return_value = _make_db_result([{
            "totp_secret": secret,
            "is_enabled": 0,
            "backup_codes": "[]",
        }])
        mock_db.return_value = db

        req = MFAVerifyRequest(code="000000")

        with pytest.raises(HTTPException) as exc_info:
            await verify_mfa(body=req, current_user=token_data)

    assert exc_info.value.status_code == 400
    assert "inválido" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# test_login_with_mfa_returns_mfa_required
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_with_mfa_returns_mfa_required():
    """Login should return mfa_required=True when user has MFA enabled."""
    from app.routers.auth import login, LoginRequest
    from fastapi import Request as FRequest

    user = _make_user()

    mock_request = MagicMock(spec=FRequest)
    mock_request.client = MagicMock()
    mock_request.client.host = "127.0.0.1"
    mock_request.url = MagicMock()
    mock_request.url.path = "/api/auth/login"

    with patch("app.routers.auth.user_service") as mock_us, \
         patch("app.routers.auth.get_db_client") as mock_db, \
         patch("app.routers.auth.verify_turnstile", return_value=True), \
         patch("app.routers.auth.settings") as mock_settings:

        mock_settings.TURNSTILE_SECRET_KEY = None
        mock_us.authenticate_user = AsyncMock(return_value=user)

        db = AsyncMock()
        db.execute.return_value = _make_db_result([{"is_enabled": 1}])
        mock_db.return_value = db

        data = LoginRequest(email="mfa@test.com", password="TestPass123!")
        resp = await login(request=mock_request, data=data)

    assert resp["mfa_required"] is True
    assert "mfa_token" in resp
    assert isinstance(resp["mfa_token"], str)


# ---------------------------------------------------------------------------
# test_validate_mfa_with_valid_code_returns_jwt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_mfa_with_valid_code_returns_jwt():
    """POST /api/auth/mfa/validate should return full JWT on valid TOTP code."""
    from app.routers.mfa import validate_mfa, MFAValidateRequest
    from app.auth.jwt_handler import create_mfa_token

    user = _make_user()
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    mfa_token = create_mfa_token(user.id, user.email)

    with patch("app.routers.mfa.get_db_client") as mock_db, \
         patch("app.routers.mfa.user_service") as mock_us, \
         patch("app.routers.mfa.get_subscription_service") as mock_sub:

        db = AsyncMock()
        db.execute.return_value = _make_db_result([{
            "totp_secret": secret,
            "is_enabled": 1,
            "backup_codes": "[]",
        }])
        mock_db.return_value = db
        mock_us.get_user_by_id = AsyncMock(return_value=user)

        sub_service = AsyncMock()
        sub_service.check_access = AsyncMock(return_value=_make_access())
        mock_sub.return_value = sub_service

        # Call the unwrapped function to bypass slowapi rate limiter
        inner = validate_mfa.__wrapped__
        mock_request = MagicMock()
        body = MFAValidateRequest(mfa_token=mfa_token, code=valid_code)
        resp = await inner(request=mock_request, body=body)

    assert "tokens" in resp
    assert "access_token" in resp["tokens"]
    assert "refresh_token" in resp["tokens"]
    assert resp["user"]["id"] == user.id


# ---------------------------------------------------------------------------
# test_validate_mfa_with_backup_code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_mfa_with_backup_code():
    """POST /api/auth/mfa/validate should accept a valid backup code."""
    import bcrypt
    from app.routers.mfa import validate_mfa, MFAValidateRequest
    from app.auth.jwt_handler import create_mfa_token

    user = _make_user()
    secret = pyotp.random_base32()
    backup_code = "abcd1234"
    hashed = bcrypt.hashpw(backup_code.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")
    hashed_codes_json = json.dumps([hashed, None, None])

    mfa_token = create_mfa_token(user.id, user.email)

    with patch("app.routers.mfa.get_db_client") as mock_db, \
         patch("app.routers.mfa.user_service") as mock_us, \
         patch("app.routers.mfa.get_subscription_service") as mock_sub:

        db = AsyncMock()
        db.execute.return_value = _make_db_result([{
            "totp_secret": secret,
            "is_enabled": 1,
            "backup_codes": hashed_codes_json,
        }])
        mock_db.return_value = db
        mock_us.get_user_by_id = AsyncMock(return_value=user)

        sub_service = AsyncMock()
        sub_service.check_access = AsyncMock(return_value=_make_access())
        mock_sub.return_value = sub_service

        # Call the unwrapped function to bypass slowapi rate limiter
        inner = validate_mfa.__wrapped__
        mock_request = MagicMock()
        body = MFAValidateRequest(mfa_token=mfa_token, code=backup_code)
        resp = await inner(request=mock_request, body=body)

    assert "tokens" in resp
    assert resp["user"]["id"] == user.id
    # Verify that the backup code was marked as used (UPDATE call)
    update_calls = [
        c for c in db.execute.call_args_list
        if "UPDATE user_mfa SET backup_codes" in str(c)
    ]
    assert len(update_calls) == 1


# ---------------------------------------------------------------------------
# test_disable_mfa
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_disable_mfa():
    """POST /api/auth/mfa/disable should remove MFA with a valid TOTP code."""
    from app.routers.mfa import disable_mfa, MFADisableRequest

    token_data = _make_token_data()
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    with patch("app.routers.mfa.get_db_client") as mock_db:
        db = AsyncMock()
        db.execute.return_value = _make_db_result([{
            "totp_secret": secret,
            "is_enabled": 1,
            "backup_codes": "[]",
        }])
        mock_db.return_value = db

        req = MFADisableRequest(code=valid_code)
        resp = await disable_mfa(body=req, current_user=token_data)

    assert resp["success"] is True
    # Should have called DELETE
    delete_calls = [c for c in db.execute.call_args_list if "DELETE" in str(c)]
    assert len(delete_calls) == 1


# ---------------------------------------------------------------------------
# test_mfa_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mfa_status_enabled():
    """GET /api/auth/mfa/status should return enabled=True when MFA is on."""
    from app.routers.mfa import mfa_status

    token_data = _make_token_data()

    with patch("app.routers.mfa.get_db_client") as mock_db:
        db = AsyncMock()
        db.execute.return_value = _make_db_result([{"is_enabled": 1}])
        mock_db.return_value = db

        resp = await mfa_status(current_user=token_data)

    assert resp.enabled is True


@pytest.mark.asyncio
async def test_mfa_status_disabled():
    """GET /api/auth/mfa/status should return enabled=False when no MFA."""
    from app.routers.mfa import mfa_status

    token_data = _make_token_data()

    with patch("app.routers.mfa.get_db_client") as mock_db:
        db = AsyncMock()
        db.execute.return_value = _make_db_result([])
        mock_db.return_value = db

        resp = await mfa_status(current_user=token_data)

    assert resp.enabled is False
