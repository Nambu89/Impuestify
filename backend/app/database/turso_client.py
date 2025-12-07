"""
Turso Database Client for TaxIA

Uses the new libsql SDK (June 2025) for connecting to Turso.
Replaces deprecated libsql-client package.
"""
import os
import logging
from typing import Optional, List, Any
from contextlib import asynccontextmanager

# New Turso SDK (libsql)
try:
    import libsql
    LIBSQL_AVAILABLE = True
except ImportError:
    LIBSQL_AVAILABLE = False
    libsql = None

logger = logging.getLogger(__name__)


class TursoClient:
    """
    Client for interacting with Turso database.
    
    Turso is a SQLite-compatible edge database that provides
    low-latency access from anywhere.
    
    Now uses the official libsql SDK (June 2025+).
    """
    
    def __init__(self, url: Optional[str] = None, auth_token: Optional[str] = None):
        """
        Initialize Turso client.
        
        Args:
            url: Turso database URL (libsql://...)
            auth_token: Authentication token
        """
        self.url = url or os.environ.get("TURSO_DATABASE_URL")
        self.auth_token = auth_token or os.environ.get("TURSO_AUTH_TOKEN")
        self._conn = None
        
        if not self.url:
            logger.warning("TURSO_DATABASE_URL not configured")
        
        if not LIBSQL_AVAILABLE:
            logger.warning("libsql package not installed. Run: pip install libsql")
    
    async def connect(self):
        """Establish connection to Turso database."""
        if not LIBSQL_AVAILABLE:
            raise RuntimeError("libsql package is not installed")
        
        if not self.url:
            raise ValueError("TURSO_DATABASE_URL is required")
        
        try:
            # New libsql SDK API
            self._conn = libsql.connect(
                self.url,
                auth_token=self.auth_token
            )
            logger.info("Connected to Turso database")
        except Exception as e:
            logger.error(f"Failed to connect to Turso: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Disconnected from Turso database")
    
    async def execute(self, sql: str, params: Optional[List[Any]] = None) -> Any:
        """
        Execute a SQL query.
        
        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)
            
        Returns:
            Query result with rows attribute
        """
        if not self._conn:
            await self.connect()
        
        try:
            if params:
                result = self._conn.execute(sql, params)
            else:
                result = self._conn.execute(sql)
            
            # Wrap result to have consistent interface
            return QueryResult(result)
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise
    
    async def execute_many(self, sql: str, params_list: List[List[Any]]) -> None:
        """
        Execute a SQL statement with multiple parameter sets.
        
        Args:
            sql: SQL query string
            params_list: List of parameter sets
        """
        if not self._conn:
            await self.connect()
        
        try:
            for params in params_list:
                self._conn.execute(sql, params)
            self._conn.commit()
        except Exception as e:
            logger.error(f"Execute many failed: {e}")
            raise
    
    async def init_schema(self):
        """
        Initialize database schema.
        
        Creates all required tables if they don't exist.
        """
        schema_statements = [
            # Users table
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """,
            
            # Sessions table (for refresh tokens)
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            
            # Conversations table
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """,
            
            # Messages table
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
            """,
            
            # Usage metrics table
            """
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                endpoint TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                processing_time REAL,
                cached BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """,
            
            # Create indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)",
        ]
        
        try:
            for sql in schema_statements:
                await self.execute(sql)
            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise


class QueryResult:
    """Wrapper for query results to provide consistent interface."""
    
    def __init__(self, cursor):
        self._cursor = cursor
        self._rows = None
    
    @property
    def rows(self) -> List[dict]:
        """Get rows as list of dictionaries."""
        if self._rows is None:
            try:
                # Try to fetch all rows and convert to dicts
                rows = self._cursor.fetchall()
                if rows and hasattr(self._cursor, 'description') and self._cursor.description:
                    columns = [desc[0] for desc in self._cursor.description]
                    self._rows = [dict(zip(columns, row)) for row in rows]
                else:
                    self._rows = []
            except Exception:
                self._rows = []
        return self._rows
    
    @property
    def rowcount(self) -> int:
        """Get number of affected rows."""
        try:
            return self._cursor.rowcount
        except Exception:
            return 0


# Global client instance
_db_client: Optional[TursoClient] = None


async def get_db_client() -> TursoClient:
    """
    Get the global database client instance.
    
    Returns:
        TursoClient instance
    """
    global _db_client
    
    if _db_client is None:
        _db_client = TursoClient()
        await _db_client.connect()
    
    return _db_client


@asynccontextmanager
async def get_db_connection():
    """
    Context manager for database connections.
    
    Yields:
        TursoClient instance
    """
    client = await get_db_client()
    try:
        yield client
    finally:
        # Connection remains open (connection pooling)
        pass
