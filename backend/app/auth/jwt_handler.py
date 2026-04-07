"""
JWT Token Handler for Impuestify

Implements JWT-based authentication with access and refresh tokens.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = 7

class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    email: Optional[str] = None
    exp: Optional[datetime] = None


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new access token.
    
    Args:
        data: Payload data to encode in the token
        expires_delta: Custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a new refresh token.
    
    Refresh tokens have a longer expiration and are used to obtain new access tokens.
    
    Args:
        data: Payload data to encode in the token
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(f"Invalid token type: expected {token_type}, got {payload.get('type')}")
            return None
        
        user_id: str = payload.get("sub") or payload.get("user_id")
        if user_id is None:
            logger.warning("Token missing user_id")
            return None
        
        return TokenData(
            user_id=user_id,
            email=payload.get("email"),
            exp=datetime.fromtimestamp(payload.get("exp", 0))
        )
        
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
) -> TokenData:
    """
    FastAPI dependency to get the current authenticated user (REQUIRED).
    
    Args:
        credentials: HTTP Bearer credentials from the Authorization header
        
    Returns:
        TokenData if authenticated
        
    Raises:
        HTTPException 401: If token is missing, invalid or expired
    """
    token = credentials.credentials
    token_data = verify_token(token, token_type="access")
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data


# Alias kept for backward compatibility — identical to get_current_user.
get_current_user_required = get_current_user


def create_mfa_token(user_id: str, email: str) -> str:
    """
    Create a short-lived MFA pending token.

    This token is issued after successful password verification when
    the user has MFA enabled.  It must be exchanged for a full
    access/refresh token pair by providing a valid TOTP code.

    Args:
        user_id: User's unique identifier
        email: User's email address

    Returns:
        Encoded JWT token string (5 min TTL, type=mfa_pending)
    """
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "type": "mfa_pending",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "iat": datetime.now(timezone.utc),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_reset_token(user_id: str, email: str) -> str:
    """
    Create a password reset token.

    The token is a short-lived JWT (1 hour) with type="reset".
    It is used exclusively by the forgot-password / reset-password flow.

    Args:
        user_id: User's unique identifier
        email: User's email address

    Returns:
        Encoded JWT reset token string
    """
    return jwt.encode(
        {
            "sub": user_id,
            "email": email,
            "type": "reset",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_tokens_for_user(user_id: str, email: str) -> TokenResponse:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        
    Returns:
        TokenResponse with both tokens
    """
    token_data = {"sub": user_id, "email": email}
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
