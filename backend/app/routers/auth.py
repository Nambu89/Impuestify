"""
Auth Router for TaxIA

Provides authentication endpoints: register, login, refresh, logout.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, EmailStr, Field

from app.auth.jwt_handler import (
    create_tokens_for_user,
    verify_token,
    TokenResponse,
    get_current_user_required,
    TokenData
)
from app.services.user_service import user_service
from app.services.subscription_service import get_subscription_service
from app.database.models import UserCreate, User
from app.security.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response models
class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")
    name: Optional[str] = None


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


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
async def register(request: Request, data: RegisterRequest):
    """
    Register a new user.
    
    Creates a new account and returns authentication tokens.
    """
    try:
        user = await user_service.create_user(
            UserCreate(
                email=data.email,
                password=data.password,
                name=data.name
            )
        )

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


@router.post("/login", response_model=AuthResponse)
# TODO: Re-enable rate limiting once CORS is confirmed working
# @limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest):
    """
    Login with email and password.
    
    Returns authentication tokens if credentials are valid.
    """
    user = await user_service.authenticate_user(data.email, data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

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
