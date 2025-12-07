"""
Password Hashing for TaxIA

Uses bcrypt directly for secure password hashing.
"""
import logging
import bcrypt

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be updated.
    
    This can happen when the hashing algorithm or parameters change.
    For bcrypt, we check if rounds are less than current standard.
    
    Args:
        hashed_password: Stored hashed password
        
    Returns:
        True if password should be rehashed
    """
    try:
        # Extract rounds from hash (format: $2b$rounds$...)
        parts = hashed_password.split('$')
        if len(parts) >= 3:
            rounds = int(parts[2])
            return rounds < 12  # Current standard
        return False
    except Exception:
        return False
