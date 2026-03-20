"""
Auth Router for TaxIA

Provides authentication endpoints: register, login, refresh, logout.
Cloudflare Turnstile verification on login/register.
"""
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from app.auth.jwt_handler import (
    create_tokens_for_user,
    create_mfa_token,
    create_reset_token,
    verify_token,
    TokenResponse,
    get_current_user_required,
    TokenData
)
from app.auth.password import hash_password
from app.services.email_service import get_email_service
from app.config import settings
from app.services.user_service import user_service
from app.services.subscription_service import get_subscription_service
from app.database.models import UserCreate, User
from app.database.turso_client import get_db_client
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

# Cloudflare's official always-passing test token (safe to hardcode — it's public documentation)
TURNSTILE_TEST_TOKEN = "1x00000000000000000000AA"


async def verify_turnstile(token: str, remote_ip: Optional[str] = None) -> bool:
    """Verify a Cloudflare Turnstile token. Returns True if valid.

    In test mode (TURNSTILE_TEST_MODE=True), accepts Cloudflare's official
    test token '1x00000000000000000000AA' without making a network call.
    This allows E2E / automated QA tests to bypass the captcha challenge.
    """
    secret = settings.TURNSTILE_SECRET_KEY
    if not secret:
        logger.warning("TURNSTILE_SECRET_KEY not configured — skipping verification")
        return True

    # Accept Cloudflare's official test token when test mode is explicitly enabled
    if settings.TURNSTILE_TEST_MODE and token == TURNSTILE_TEST_TOKEN:
        logger.info("Turnstile test token accepted (TURNSTILE_TEST_MODE=True)")
        return True

    payload = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            result = resp.json()
            if result.get("success"):
                return True
            logger.warning(f"Turnstile verification failed: {result.get('error-codes', [])}")
            return False
    except Exception as e:
        logger.error(f"Turnstile verification error: {e}")
        # Fail open — don't block legitimate users if Cloudflare is down
        return True

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response models
class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")
    name: Optional[str] = None
    ccaa_residencia: Optional[str] = None
    turnstile_token: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str
    turnstile_token: Optional[str] = None


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request"""
    token: str
    new_password: str = Field(..., min_length=8, description="Minimo 8 caracteres")


class UserResponse(BaseModel):
    """User info response"""
    id: str
    email: str
    name: Optional[str]
    is_active: bool
    is_admin: bool = False
    is_owner: bool = False
    subscription_status: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response with tokens"""
    user: UserResponse
    tokens: TokenResponse


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, data: RegisterRequest):
    """
    Register a new user.

    Creates a new account and returns authentication tokens.
    """
    # Turnstile verification
    if data.turnstile_token:
        remote_ip = request.client.host if request.client else None
        if not await verify_turnstile(data.turnstile_token, remote_ip):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verificación de seguridad fallida. Inténtalo de nuevo."
            )
    elif settings.TURNSTILE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verificación de seguridad requerida."
        )

    try:
        user = await user_service.create_user(
            UserCreate(
                email=data.email,
                password=data.password,
                name=data.name
            )
        )

        # Save CCAA to user_profiles if provided
        if data.ccaa_residencia:
            try:
                db = await get_db_client()
                import uuid as _uuid
                await db.execute(
                    """INSERT INTO user_profiles (id, user_id, ccaa_residencia, created_at, updated_at)
                       VALUES (?, ?, ?, datetime('now'), datetime('now'))
                       ON CONFLICT(user_id) DO UPDATE SET ccaa_residencia = ?, updated_at = datetime('now')""",
                    [str(_uuid.uuid4()), user.id, data.ccaa_residencia, data.ccaa_residencia],
                )
            except Exception as e:
                logger.warning(f"Failed to save ccaa_residencia (non-blocking): {e}")

        # Create Stripe customer for the new user
        sub_service = await get_subscription_service()
        try:
            await sub_service.create_stripe_customer(
                user_id=user.id, email=user.email, name=user.name
            )
        except Exception as e:
            logger.warning(f"Stripe customer creation failed (non-blocking): {e}")

        # Check subscription status
        access = await sub_service.check_access(user_id=user.id, email=user.email)

        tokens = create_tokens_for_user(user.id, user.email)

        return AuthResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                is_active=user.is_active,
                is_admin=user.is_admin,
                is_owner=access.is_owner,
                subscription_status=access.status
            ),
            tokens=tokens
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear la cuenta"
        )


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest):
    """
    Login with email and password.

    Returns authentication tokens if credentials are valid.
    """
    # Turnstile verification
    if data.turnstile_token:
        remote_ip = request.client.host if request.client else None
        if not await verify_turnstile(data.turnstile_token, remote_ip):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verificación de seguridad fallida. Inténtalo de nuevo."
            )
    elif settings.TURNSTILE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verificación de seguridad requerida."
        )

    user = await user_service.authenticate_user(data.email, data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    # Check if MFA is enabled for this user
    try:
        db = await get_db_client()
        mfa_result = await db.execute(
            "SELECT is_enabled FROM user_mfa WHERE user_id = ? AND is_enabled = 1",
            [user.id],
        )
        if mfa_result.rows:
            # MFA is enabled — return a short-lived mfa_token instead of full JWT
            mfa_token = create_mfa_token(user.id, user.email)
            return {"mfa_required": True, "mfa_token": mfa_token}
    except Exception as e:
        # If MFA check fails (e.g. table not yet created), proceed without MFA
        logger.warning(f"MFA check failed (non-blocking): {e}")

    # Check subscription status
    sub_service = await get_subscription_service()
    access = await sub_service.check_access(user_id=user.id, email=user.email)

    tokens = create_tokens_for_user(user.id, user.email)

    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            is_owner=access.is_owner,
            subscription_status=access.status
        ),
        tokens=tokens
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshRequest):
    """
    Refresh access token using refresh token.
    
    Returns new access and refresh tokens.
    """
    token_data = verify_token(data.refresh_token, token_type="refresh")
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco inválido o expirado"
        )
    
    # Get user to ensure they still exist and are active
    user = await user_service.get_user_by_id(token_data.user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo"
        )
    
    return create_tokens_for_user(user.id, user.email)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user_required)):
    """
    Get current authenticated user info.
    
    Requires valid access token.
    """
    user = await user_service.get_user_by_id(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Check subscription status
    sub_service = await get_subscription_service()
    access = await sub_service.check_access(user_id=user.id, email=user.email)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        is_owner=access.is_owner,
        subscription_status=access.status
    )


@router.post("/logout")
async def logout(current_user: TokenData = Depends(get_current_user_required)):
    """
    Logout current user.

    Note: With JWT, actual token invalidation requires a blacklist.
    For now, client should discard tokens.
    """
    # In a production system, you would add the token to a blacklist
    # stored in Redis/Upstash
    logger.info(f"User logged out: {current_user.user_id}")

    return {"message": "Sesión cerrada correctamente"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    """
    Request a password reset link.

    Generates a short-lived JWT reset token and sends it to the user's email.
    Always returns 200 with a generic message to avoid user enumeration.
    """
    GENERIC_RESPONSE = {"message": "Si el email existe, recibirás un enlace para restablecer tu contraseña"}

    try:
        user = await user_service.get_user_by_email(data.email)
        if not user or not user.is_active:
            # Return generic response — do not reveal whether the email exists
            return GENERIC_RESPONSE

        reset_token = create_reset_token(user.id, user.email)
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

        html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: #1a56db; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 20px;">Impuestify</h1>
        <p style="margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;">Recuperacion de contrasena</p>
    </div>
    <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px;">
        <p>Hola,</p>
        <p>Has solicitado restablecer tu contrasena en Impuestify.</p>
        <div style="text-align: center; margin: 25px 0;">
            <a href="{reset_link}" style="background: #1a56db; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600;">Restablecer contrasena</a>
        </div>
        <p style="color: #666; font-size: 13px;">Este enlace expira en 1 hora. Si no solicitaste este cambio, ignora este email.</p>
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;">
        <p style="color: #999; font-size: 11px;">Impuestify - Asistente fiscal inteligente</p>
    </div>
</div>
"""

        email_service = get_email_service()
        result = await email_service.send_email(
            to=user.email,
            subject="Restablece tu contrasena en Impuestify",
            html=html,
        )
        if not result.get("success"):
            logger.error(f"Failed to send reset email for user {user.id}: {result.get('error')}")

    except Exception as e:
        # Log but never expose details externally
        logger.error(f"forgot_password error: {e}")

    return GENERIC_RESPONSE


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordRequest):
    """
    Reset password using a valid reset token.

    Verifies the JWT reset token, then updates the user's password.
    """
    token_data = verify_token(data.token, token_type="reset")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de recuperacion no es valido o ha expirado"
        )

    user = await user_service.get_user_by_id(token_data.user_id)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El enlace de recuperacion no es valido o ha expirado"
        )

    new_hash = hash_password(data.new_password)
    await user_service.update_password(user.id, new_hash)

    logger.info(f"Password reset completed for user: {user.id}")

    return {"message": "Contrasena actualizada correctamente. Ya puedes iniciar sesion."}
