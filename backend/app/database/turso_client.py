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
            
            # Enable foreign key constraints (disabled by default in SQLite/libSQL)
            self._conn.execute("PRAGMA foreign_keys = ON")
            
            logger.info("Connected to Turso database (foreign keys enabled)")
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
        
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                if params:
                    result = self._conn.execute(sql, params)
                else:
                    result = self._conn.execute(sql)
                
                # Auto-commit for write operations
                if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')):
                    self._conn.commit()
                
                # Wrap result to have consistent interface
                return QueryResult(result)
            except Exception as e:
                error_msg = str(e).lower()
                if 'stream not found' in error_msg or 'connection' in error_msg:
                    if attempt < max_retries:
                        logger.warning(f"Connection issue, reconnecting... (attempt {attempt + 1})")
                        await self.disconnect()
                        await self.connect()
                        continue
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
            # =============================================
            # USER & AUTH TABLES
            # =============================================
            
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
            
            # =============================================
            # USER PROFILES TABLE (Long-term Memory)
            # =============================================
            
            # User profiles table - stores persistent user information
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT UNIQUE NOT NULL,
                ccaa_residencia TEXT,
                situacion_laboral TEXT,
                tiene_vivienda BOOLEAN,
                primera_vivienda BOOLEAN,
                fecha_nacimiento TEXT,
                datos_fiscales TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            
            # =============================================
            # DOCUMENT & RAG TABLES
            # =============================================
            
            # Documents table - stores PDF metadata
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT,
                title TEXT,
                document_type TEXT,
                year INTEGER,
                source TEXT DEFAULT 'AEAT',
                total_pages INTEGER,
                file_size INTEGER,
                hash TEXT UNIQUE,
                processed BOOLEAN DEFAULT 0,
                processing_status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """,
            
            # Document sections - hierarchical structure
            """
            CREATE TABLE IF NOT EXISTS document_sections (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                parent_section_id TEXT,
                title TEXT,
                section_number TEXT,
                level INTEGER DEFAULT 0,
                start_page INTEGER,
                end_page INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (parent_section_id) REFERENCES document_sections(id) ON DELETE SET NULL
            )
            """,
            
            # Document chunks - text segments for RAG
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                section_id TEXT,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT,
                page_number INTEGER,
                start_char INTEGER,
                end_char INTEGER,
                token_count INTEGER,
                metadata TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (section_id) REFERENCES document_sections(id) ON DELETE SET NULL
            )
            """,
            
            # Embeddings table - vector storage for semantic search
            # Note: Turso supports F32_BLOB for vector embeddings
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL UNIQUE,
                embedding BLOB NOT NULL,
                model_name TEXT DEFAULT 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
                dimensions INTEGER DEFAULT 384,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE CASCADE
            )
            """,
            
            # Tax categories for document classification
            """
            CREATE TABLE IF NOT EXISTS tax_categories (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                parent_id TEXT,
                FOREIGN KEY (parent_id) REFERENCES tax_categories(id) ON DELETE SET NULL
            )
            """,
            
            # Document-category mapping
            """
            CREATE TABLE IF NOT EXISTS document_categories (
                document_id TEXT NOT NULL,
                category_id TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0,
                PRIMARY KEY (document_id, category_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES tax_categories(id) ON DELETE CASCADE
            )
            """,
            
            # =============================================
            # CONVERSATION & CHAT TABLES
            # =============================================
            
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
            
            # Message sources - links messages to source chunks
            """
            CREATE TABLE IF NOT EXISTS message_sources (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                relevance_score REAL,
                rank INTEGER,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE CASCADE
            )
            """,
            
            # =============================================
            # ANALYTICS & METRICS TABLES
            # =============================================
            
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
            
            # Search analytics
            """
            CREATE TABLE IF NOT EXISTS search_analytics (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                query TEXT NOT NULL,
                query_embedding_id TEXT,
                results_count INTEGER,
                top_result_score REAL,
                response_time_ms INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """,
            
            # =============================================
            # INDEXES FOR PERFORMANCE
            # =============================================
            
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_user ON user_profiles(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type)",
            "CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year)",
            "CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(hash)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_chunks_section ON document_chunks(section_id)",
            "CREATE INDEX IF NOT EXISTS idx_embeddings_chunk ON embeddings(chunk_id)",
            "CREATE INDEX IF NOT EXISTS idx_sections_document ON document_sections(document_id)",
            "CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)",
            "CREATE INDEX IF NOT EXISTS idx_sources_message ON message_sources(message_id)",
            
            # =============================================
            # WORKSPACE TABLES
            # =============================================
            
            # Workspaces table
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT DEFAULT '📁',
                is_default BOOLEAN DEFAULT 0,
                max_files INTEGER DEFAULT 50,
                max_size_mb INTEGER DEFAULT 100,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,
            
            # Workspace files table
            """
            CREATE TABLE IF NOT EXISTS workspace_files (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                mime_type TEXT,
                file_size INTEGER,
                original_path TEXT,
                extracted_text TEXT,
                extracted_data TEXT,
                processing_status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
            )
            """,
            
            # Workspace indexes
            "CREATE INDEX IF NOT EXISTS idx_workspaces_user ON workspaces(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_workspace_files_workspace ON workspace_files(workspace_id)",
            "CREATE INDEX IF NOT EXISTS idx_workspace_files_type ON workspace_files(file_type)",

            # =============================================
            # WORKSPACE EMBEDDINGS TABLE
            # =============================================

            # Workspace file embeddings - vector storage for semantic search
            """
            CREATE TABLE IF NOT EXISTS workspace_file_embeddings (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT,
                embedding BLOB NOT NULL,
                model_name TEXT DEFAULT 'text-embedding-3-large',
                dimensions INTEGER DEFAULT 3072,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                FOREIGN KEY (file_id) REFERENCES workspace_files(id) ON DELETE CASCADE
            )
            """,

            # Workspace embedding indexes
            "CREATE INDEX IF NOT EXISTS idx_ws_embeddings_workspace ON workspace_file_embeddings(workspace_id)",
            "CREATE INDEX IF NOT EXISTS idx_ws_embeddings_file ON workspace_file_embeddings(file_id)",
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
