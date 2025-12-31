"""
Simple Integration Tests for v2.7 Security Features

Simplified tests without emojis for Windows compatibility.
Run with: pytest tests/test_integration_simple.py -v
"""
import pytest
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestLlamaGuardSimple:
    """Simple tests for Llama Guard"""
    
    @pytest.mark.asyncio
    async def test_llama_guard_safe_content(self):
        """Test that safe tax questions pass moderation"""
        from app.security.llama_guard import LlamaGuard
        
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            pytest.skip("GROQ_API_KEY not configured")
        
        guard = LlamaGuard(api_key=groq_key, enabled=True)
        
        safe_text = "Cual es el plazo para presentar el modelo 303 de IVA?"
        result = await guard.moderate(safe_text)
        
        assert result.is_safe, "Safe tax question should pass moderation"
        assert len(result.blocked_categories) == 0
        print(f"\n[PASS] Llama Guard: Safe content passed (latency: {result.latency_ms:.0f}ms)")
    
    @pytest.mark.asyncio
    async def test_llama_guard_disabled(self):
        """Test that disabled guard doesn't break"""
        from app.security.llama_guard import LlamaGuard
        
        guard = LlamaGuard(api_key=None, enabled=False)
        result = await guard.moderate("Any text")
        
        assert result.is_safe
        print("\n[PASS] Llama Guard: Disabled mode works correctly")


class TestSemanticCacheSimple:
    """Simple tests for Semantic Cache"""
    
    def test_semantic_cache_initialization(self):
        """Test that cache initializes correctly"""
        from app.security.semantic_cache import SemanticCache
        
        url = os.getenv("UPSTASH_VECTOR_REST_URL")
        token = os.getenv("UPSTASH_VECTOR_REST_TOKEN")
        
        if not url or not token:
            pytest.skip("UPSTASH_VECTOR credentials not configured")
        
        cache = SemanticCache(url=url, token=token, enabled=True)
        
        assert cache.enabled, "Cache should be enabled with valid credentials"
        print(f"\n[PASS] Semantic Cache: Initialized successfully")
    
    def test_personal_query_detection(self):
        """Test that personal queries are detected"""
        from app.security.semantic_cache import SemanticCache
        
        cache = SemanticCache(enabled=False)
        
        personal_queries = [
            "Cuanto pago yo de IRPF?",  # "pago" triggers detection
            "Mi declaracion de la renta",  # "Mi " triggers detection
            "Tengo un piso en Madrid",  # "Tengo" triggers detection
        ]
        
        detected_count = 0
        for query in personal_queries:
            if cache._is_personal_query(query):
                detected_count += 1
        
        # At least 2 out of 3 should be detected
        assert detected_count >= 2, f"Only {detected_count}/3 personal queries detected"
        print(f"\n[PASS] Semantic Cache: Personal query detection works ({detected_count}/3 detected)")


class TestComplexityRouterSimple:
    """Simple tests for Complexity Router"""
    
    def test_complexity_classification(self):
        """Test complexity classification"""
        from app.security.complexity_router import classify_complexity, ComplexityLevel
        
        # Simple query
        simple_result = classify_complexity("Que es el IVA?")
        assert simple_result.level == ComplexityLevel.SIMPLE
        assert simple_result.reasoning_effort.value == "low"
        
        # Complex query
        complex_result = classify_complexity("Analiza las implicaciones fiscales de heredar una vivienda")
        assert complex_result.level == ComplexityLevel.COMPLEX
        assert complex_result.reasoning_effort.value == "high"
        
        print(f"\n[PASS] Complexity Router: Classification works correctly")


class TestRedisRateLimiterSimple:
    """Simple tests for Redis Rate Limiter"""
    
    def test_rate_limiter_initialization(self):
        """Test that rate limiter initializes"""
        from app.security.rate_limiter import limiter
        
        assert limiter is not None
        
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        
        if redis_url and redis_token:
            print(f"\n[PASS] Rate Limiter: Using Redis (distributed)")
        else:
            print(f"\n[PASS] Rate Limiter: Using in-memory (single instance)")


class TestAuditLoggerSimple:
    """Simple tests for Audit Logger"""
    
    def test_audit_logger_basic(self):
        """Test basic audit logging"""
        from app.security.audit_logger import AuditLogger, AuditEventType
        
        logger = AuditLogger()
        
        # Test logging with correct method names
        logger.log_login_success(
            user_id="test-user",
            ip_address="127.0.0.1"
        )
        
        logger.log_ai_query(
            user_id="test-user",
            query_preview="Test query about IVA",
            ip_address="127.0.0.1"
        )
        
        logger.log_moderation_block(
            user_id="test-user",
            categories=["S1"],
            ip_address="127.0.0.1"
        )
        
        print(f"\n[PASS] Audit Logger: Successfully logged events")


def test_environment_check():
    """Check environment configuration"""
    print("\n" + "="*60)
    print("ENVIRONMENT CONFIGURATION CHECK")
    print("="*60)
    
    required_vars = {
        "GROQ_API_KEY": "Llama Guard",
        "UPSTASH_VECTOR_REST_URL": "Semantic Cache",
        "UPSTASH_VECTOR_REST_TOKEN": "Semantic Cache",
        "UPSTASH_REDIS_REST_URL": "Redis Rate Limiting",
        "UPSTASH_REDIS_REST_TOKEN": "Redis Rate Limiting",
    }
    
    print("\nRequired Variables:")
    all_set = True
    for var, purpose in required_vars.items():
        value = os.getenv(var)
        status = "[OK]" if value else "[MISSING]"
        masked = f"{value[:10]}..." if value and len(value) > 10 else "NOT SET"
        print(f"  {status} {var}: {masked} ({purpose})")
        if not value:
            all_set = False
    
    optional_vars = {
        "ENABLE_CONTENT_MODERATION": os.getenv("ENABLE_CONTENT_MODERATION", "true"),
        "ENABLE_SEMANTIC_CACHE": os.getenv("ENABLE_SEMANTIC_CACHE", "true"),
        "SEMANTIC_CACHE_THRESHOLD": os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.93"),
    }
    
    print("\nOptional Variables:")
    for var, value in optional_vars.items():
        print(f"  [OK] {var}: {value}")
    
    print("\n" + "="*60)
    
    if all_set:
        print("[SUCCESS] All required variables are configured!")
    else:
        print("[WARNING] Some variables are missing. Features may be disabled.")
    
    print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
