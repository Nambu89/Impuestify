"""
Tests for TaxIA Authentication

Tests JWT token generation, password hashing, and auth endpoints.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
from app.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    TokenData
)
from app.auth.password import hash_password, verify_password, needs_rehash
from app.routers.auth import verify_turnstile, TURNSTILE_TEST_TOKEN


class TestPasswordHashing:
    """Tests for password hashing with bcrypt"""
    
    def test_hash_password_creates_hash(self):
        """Password hashing should create a bcrypt hash"""
        password = "MySecurePassword123"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_verify_correct_password(self):
        """Correct password should verify successfully"""
        password = "MySecurePassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Wrong password should fail verification"""
        password = "MySecurePassword123"
        wrong_password = "WrongPassword456"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Same password should produce different hashes (salt)"""
        password = "MySecurePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestJWTTokens:
    """Tests for JWT token handling"""
    
    def test_create_access_token(self):
        """Access token creation should work"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically long
    
    def test_create_refresh_token(self):
        """Refresh token creation should work"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_refresh_token(data)
        
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_valid_access_token(self):
        """Valid access token should verify correctly"""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        
        result = verify_token(token, token_type="access")
        
        assert result is not None
        assert result.user_id == "user123"
        assert result.email == "test@example.com"
    
    def test_verify_valid_refresh_token(self):
        """Valid refresh token should verify correctly"""
        data = {"sub": "user456", "email": "refresh@example.com"}
        token = create_refresh_token(data)
        
        result = verify_token(token, token_type="refresh")
        
        assert result is not None
        assert result.user_id == "user456"
    
    def test_wrong_token_type_fails(self):
        """Using wrong token type should fail verification"""
        data = {"sub": "user123"}
        access_token = create_access_token(data)
        
        # Try to verify access token as refresh token
        result = verify_token(access_token, token_type="refresh")
        
        assert result is None
    
    def test_invalid_token_fails(self):
        """Invalid token should fail verification"""
        result = verify_token("invalid.token.here")
        
        assert result is None
    
    def test_custom_expiration(self):
        """Custom token expiration should work"""
        data = {"sub": "user123"}
        
        # Create token with very short expiration
        token = create_access_token(data, expires_delta=timedelta(seconds=1))
        
        # Should be valid immediately
        result = verify_token(token)
        assert result is not None
        
        # Note: Testing expiration would require waiting, skipped for speed


class TestTokenData:
    """Tests for TokenData model"""
    
    def test_token_data_creation(self):
        """TokenData should be creatable with required fields"""
        data = TokenData(
            user_id="user123",
            email="test@example.com"
        )
        
        assert data.user_id == "user123"
        assert data.email == "test@example.com"
    
    def test_token_data_optional_email(self):
        """Email should be optional in TokenData"""
        data = TokenData(user_id="user123")

        assert data.user_id == "user123"
        assert data.email is None


class TestVerifyTurnstile:
    """Tests for Turnstile test mode bypass logic."""

    @pytest.mark.asyncio
    async def test_test_mode_accepts_official_test_token(self):
        """With TURNSTILE_TEST_MODE=True, the official CF test token must pass."""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.TURNSTILE_SECRET_KEY = "some-secret"
            mock_settings.TURNSTILE_TEST_MODE = True
            result = await verify_turnstile(TURNSTILE_TEST_TOKEN)
        assert result is True

    @pytest.mark.asyncio
    async def test_test_mode_off_does_not_short_circuit(self):
        """With TURNSTILE_TEST_MODE=False, the test token must NOT bypass Cloudflare."""
        from unittest.mock import MagicMock

        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.TURNSTILE_SECRET_KEY = "some-secret"
            mock_settings.TURNSTILE_TEST_MODE = False

            # Simulate Cloudflare returning failure for the test token.
            # httpx.Response.json() is synchronous, so use MagicMock for it.
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": False, "error-codes": ["invalid-input-response"]}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await verify_turnstile(TURNSTILE_TEST_TOKEN)

        assert result is False

    @pytest.mark.asyncio
    async def test_no_secret_always_skips_verification(self):
        """Without TURNSTILE_SECRET_KEY, verification is skipped (existing behavior)."""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.TURNSTILE_SECRET_KEY = None
            mock_settings.TURNSTILE_TEST_MODE = False
            result = await verify_turnstile("any-token")
        assert result is True

    @pytest.mark.asyncio
    async def test_test_mode_only_accepts_official_token(self):
        """With TURNSTILE_TEST_MODE=True, arbitrary tokens still go to Cloudflare."""
        from unittest.mock import MagicMock

        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.TURNSTILE_SECRET_KEY = "some-secret"
            mock_settings.TURNSTILE_TEST_MODE = True

            mock_response = MagicMock()
            mock_response.json.return_value = {"success": False, "error-codes": ["invalid-input-response"]}

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

                result = await verify_turnstile("not-the-test-token")

        assert result is False
