"""
Test Redis Rate Limiter

Quick test to verify that the UpstashStorage adapter works correctly.
"""
import pytest


def test_upstash_storage_methods():
    """Test that UpstashStorage adapter works with mock Redis"""
    # Import here to avoid circular dependencies
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    from app.security.rate_limiter import UpstashStorage
    
    # Create a mock Redis client
    class MockRedis:
        def __init__(self):
            self.data = {}
            self.ttls = {}
        
        def incr(self, key):
            self.data[key] = self.data.get(key, 0) + 1
            return self.data[key]
        
        def expire(self, key, seconds):
            self.ttls[key] = seconds
            return True
        
        def get(self, key):
            return str(self.data.get(key, 0))
        
        def ttl(self, key):
            return self.ttls.get(key, -1)
    
    # Test UpstashStorage
    storage = UpstashStorage(MockRedis())
    
    # Test incr
    count1 = storage.incr("test_key", 60)
    assert count1 == 1, "First increment should return 1"
    
    count2 = storage.incr("test_key", 60)
    assert count2 == 2, "Second increment should return 2"
    
    # Test get
    value = storage.get("test_key")
    assert value == 2, "Get should return current count"
    
    # Test get_expiry
    ttl = storage.get_expiry("test_key")
    assert ttl == 60, "TTL should be 60 seconds"
    
    print("✅ All UpstashStorage tests passed!")


if __name__ == "__main__":
    test_upstash_storage_methods()
