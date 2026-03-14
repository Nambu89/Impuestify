"""
HTTP Client Manager for TaxIA

Manages a shared httpx.AsyncClient instance with connection pooling
for optimal performance with concurrent users.

Based on httpx best practices:
- Single AsyncClient instance reused across requests
- Connection pooling reduces latency and resource usage
- Proper lifecycle management (startup/shutdown)
"""
import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """
    Manages a shared httpx.AsyncClient with connection pooling.
    
    This client is used by:
    - Azure OpenAI API calls
    - Turso database (libsql uses HTTP under the hood)
    - Upstash Redis REST API
    - Any other HTTP-based services
    """
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._is_initialized = False
        # Store config for stats
        self._max_connections = 0
        self._max_keepalive = 0
        self._timeout = 0.0
    
    async def initialize(self) -> None:
        """
        Initialize the HTTP client with connection pooling.
        
        Configuration from environment:
        - HTTPX_MAX_CONNECTIONS: Maximum number of concurrent connections
        - HTTPX_MAX_KEEPALIVE_CONNECTIONS: Max keep-alive connections in pool  
        - HTTPX_TIMEOUT: Request timeout in seconds
        """
        if self._is_initialized:
            logger.warning("HTTP client already initialized")
            return
        
        # Get configuration from environment
        self._max_connections = int(os.environ.get("HTTPX_MAX_CONNECTIONS", "250"))
        self._max_keepalive = int(os.environ.get("HTTPX_MAX_KEEPALIVE_CONNECTIONS", "50"))
        self._timeout = float(os.environ.get("HTTPX_TIMEOUT", "30.0"))
        
        # Create connection limits
        limits = httpx.Limits(
            max_connections=self._max_connections,
            max_keepalive_connections=self._max_keepalive,
            keepalive_expiry=5.0  # Keep connections alive for 5 seconds
        )
        
        # Create timeout configuration
        timeout_config = httpx.Timeout(self._timeout, connect=10.0)
        
        # Initialize the async client (try HTTP/2, fall back to HTTP/1.1)
        try:
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout_config,
                follow_redirects=True,
                http2=True  # Enable HTTP/2 for better performance
            )
        except ImportError:
            logger.warning("h2 package not installed, falling back to HTTP/1.1")
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout_config,
                follow_redirects=True,
                http2=False
            )
        
        self._is_initialized = True
        
        logger.info(
            "✅ HTTP Client Pool initialized",
            max_connections=self._max_connections,
            max_keepalive=self._max_keepalive,
            timeout=self._timeout
        )
    
    async def close(self) -> None:
        """Close the HTTP client and clean up connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._is_initialized = False
            logger.info("🔌 HTTP Client Pool closed")
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client instance."""
        if not self._is_initialized or not self._client:
            raise RuntimeError(
                "HTTP client not initialized. Call initialize() first."
            )
        return self._client
    
    def get_pool_stats(self) -> dict:
        """Get current connection pool statistics."""
        if not self._client:
            return {"status": "not_initialized"}
        
        # Return stored config values
        return {
            "status": "initialized",
            "max_connections": self._max_connections,
            "max_keepalive_connections": self._max_keepalive,
            "timeout": self._timeout
        }


# Global HTTP client manager instance
http_client_manager = HTTPClientManager()


def get_http_client() -> httpx.AsyncClient:
    """
    Dependency function to get the HTTP client.
    
    Usage in FastAPI routes:
    ```python
    @app.get("/")
    async def route(client: httpx.AsyncClient = Depends(get_http_client)):
        response = await client.get("https://api.example.com")
        return response.json()
    ```
    """
    return http_client_manager.client
