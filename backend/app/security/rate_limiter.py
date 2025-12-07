"""
Rate Limiter for TaxIA

Uses slowapi with Upstash Redis for distributed rate limiting.
Protects against abuse and ensures fair resource allocation.
"""
import os
import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key based on user identity.
    
    Uses JWT user ID if authenticated, otherwise falls back to IP address.
    """
    # Try to get user from JWT token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # If authenticated, could extract user ID from token
        # For now, use a hash of the token
        import hashlib
        token_hash = hashlib.md5(auth_header.encode()).hexdigest()[:16]
        return f"user:{token_hash}"
    
    # Fallback to IP address
    return get_remote_address(request)


def get_storage_uri() -> str:
    """
    Get storage URI for rate limiting.
    
    Uses Upstash Redis if configured, otherwise in-memory.
    """
    upstash_url = os.environ.get("UPSTASH_REDIS_REST_URL")
    upstash_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    
    if upstash_url and upstash_token:
        # Format for Redis: redis://user:password@host:port
        # Upstash REST URL needs to be converted
        logger.info("Using Upstash Redis for rate limiting")
        return f"redis://{upstash_token}@{upstash_url.replace('https://', '').replace('http://', '')}"
    
    logger.info("Using in-memory storage for rate limiting")
    return "memory://"


# Create limiter instance
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["100/hour", "10/minute"],
    storage_uri=get_storage_uri() if os.environ.get("UPSTASH_REDIS_REST_URL") else "memory://",
    strategy="fixed-window"
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns a user-friendly JSON response.
    """
    logger.warning(
        f"Rate limit exceeded for {get_rate_limit_key(request)}: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Has superado el límite de consultas. Por favor, espera un momento antes de intentar de nuevo.",
            "detail": str(exc.detail),
            "retry_after": getattr(exc, "retry_after", 60)
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": "10",
            "X-RateLimit-Remaining": "0"
        }
    )


# Rate limit decorators for different endpoints
def rate_limit_ask() -> Callable:
    """Rate limit for /ask endpoint: 10 requests per minute"""
    return limiter.limit("10/minute")


def rate_limit_auth() -> Callable:
    """Rate limit for auth endpoints: 5 requests per minute (prevent brute force)"""
    return limiter.limit("5/minute")


def rate_limit_admin() -> Callable:
    """Rate limit for admin endpoints: 20 requests per minute"""
    return limiter.limit("20/minute")
