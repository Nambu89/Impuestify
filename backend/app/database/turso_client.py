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
                updated_at TEXT DEFAULT (datetime('now')),
                integrity_score REAL DEFAULT 1.0,
                integrity_findings TEXT DEFAULT NULL
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
                model_name TEXT DEFAULT 'text-embedding-3-large',
                dimensions INTEGER DEFAULT 1536,
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
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
                model TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                cost_usd REAL DEFAULT 0.0,
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
                integrity_score REAL DEFAULT NULL,
                integrity_findings TEXT DEFAULT NULL,
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

            # =============================================
            # TAX PARAMETERS TABLE (data-driven tax config)
            # =============================================

            """
            CREATE TABLE IF NOT EXISTS tax_parameters (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                param_key TEXT NOT NULL,
                year INTEGER NOT NULL,
                jurisdiction TEXT NOT NULL DEFAULT 'Estatal',
                value REAL NOT NULL,
                description TEXT,
                legal_ref TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(category, param_key, year, jurisdiction)
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_tax_params_lookup ON tax_parameters(category, year, jurisdiction)",

            # =============================================
            # SUBSCRIPTION & PAYMENT TABLES
            # =============================================

            # Subscriptions table - Stripe subscription state per user
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                stripe_customer_id TEXT NOT NULL,
                stripe_subscription_id TEXT,
                plan_type TEXT NOT NULL DEFAULT 'particular',
                status TEXT NOT NULL DEFAULT 'inactive',
                current_period_start TEXT,
                current_period_end TEXT,
                cancel_at_period_end BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,

            # Contact requests table - form submissions (e.g. autonomo interest)
            """
            CREATE TABLE IF NOT EXISTS contact_requests (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                email TEXT NOT NULL,
                name TEXT,
                message TEXT,
                request_type TEXT DEFAULT 'autonomo_interest',
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """,

            # Subscription indexes
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id)",
            "CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status)",
            "CREATE INDEX IF NOT EXISTS idx_contact_requests_user ON contact_requests(user_id)",

            # =============================================
            # DEDUCTIONS REGISTRY
            # =============================================

            """
            CREATE TABLE IF NOT EXISTS deductions (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                tax_year INTEGER NOT NULL,
                territory TEXT NOT NULL DEFAULT 'Estatal',
                name TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'deduccion',
                category TEXT NOT NULL DEFAULT 'general',
                percentage REAL,
                max_amount REAL,
                fixed_amount REAL,
                legal_reference TEXT,
                description TEXT,
                requirements_json TEXT,
                questions_json TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(code, tax_year, territory)
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_deductions_territory_year ON deductions(territory, tax_year)",
            "CREATE INDEX IF NOT EXISTS idx_deductions_type ON deductions(type)",
            "CREATE INDEX IF NOT EXISTS idx_deductions_category ON deductions(category)",

            # =============================================
            # EXPORT REPORTS
            # =============================================

            """
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                report_type TEXT NOT NULL DEFAULT 'irpf',
                title TEXT,
                report_data TEXT,
                pdf_bytes BLOB,
                share_token TEXT UNIQUE,
                shared_with_email TEXT,
                shared_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_reports_user ON reports(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_reports_share_token ON reports(share_token)",

            # =============================================
            # QUARTERLY DECLARATIONS (Modelos 303, 130, 420)
            # =============================================

            # Quarterly declarations (Modelos 303, 130, 420)
            """
            CREATE TABLE IF NOT EXISTS quarterly_declarations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                declaration_type TEXT NOT NULL,
                territory TEXT NOT NULL,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL CHECK(quarter BETWEEN 1 AND 4),
                form_data TEXT NOT NULL,
                calculated_result TEXT NOT NULL,
                total_income REAL,
                total_expenses REAL,
                net_income REAL,
                tax_base REAL,
                tax_due REAL,
                status TEXT DEFAULT 'draft',
                source TEXT DEFAULT 'manual',
                workspace_file_id TEXT,
                presentation_date TEXT,
                confidence_score REAL DEFAULT 1.0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, declaration_type, year, quarter)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_declarations_user_year ON quarterly_declarations(user_id, year, quarter)",
            "CREATE INDEX IF NOT EXISTS idx_declarations_type ON quarterly_declarations(declaration_type, territory)",

            # Annual IRPF projections (cache)
            """
            CREATE TABLE IF NOT EXISTS annual_projections (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                year INTEGER NOT NULL,
                quarters_available INTEGER NOT NULL,
                input_summary TEXT NOT NULL,
                projected_income REAL,
                projected_expenses REAL,
                projected_net_income REAL,
                projected_irpf REAL,
                projected_payments REAL,
                projected_differential REAL,
                effective_rate REAL,
                projection_detail TEXT NOT NULL,
                confidence REAL,
                calculated_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, year, quarters_available)
            )
            """,

            # =============================================
            # IRPF CASILLAS (Model 100 field dictionary)
            # =============================================

            """
            CREATE TABLE IF NOT EXISTS irpf_casillas (
                id TEXT PRIMARY KEY,
                casilla_num TEXT NOT NULL,
                description TEXT NOT NULL,
                xsd_path TEXT,
                section TEXT,
                source TEXT DEFAULT 'xsd',
                year INTEGER DEFAULT 2024
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_casillas_num ON irpf_casillas(casilla_num)",
            "CREATE INDEX IF NOT EXISTS idx_casillas_desc ON irpf_casillas(description)",

            # ML fiscal features (future ML training data)
            """
            CREATE TABLE IF NOT EXISTS ml_fiscal_features (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                revenue REAL,
                expenses REAL,
                net_margin REAL,
                vat_balance REAL,
                irpf_payment REAL,
                ss_contribution REAL,
                retention_rate REAL,
                territory TEXT,
                activity_sector TEXT,
                estimation_method TEXT,
                revenue_yoy_change REAL,
                revenue_qoq_change REAL,
                expense_ratio REAL,
                actual_annual_irpf REAL,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, year, quarter)
            )
            """,

            # =============================================
            # FISCAL CALENDAR TABLES
            # =============================================

            # Fiscal deadlines - tax presentation deadlines by territory
            """
            CREATE TABLE IF NOT EXISTS fiscal_deadlines (
                id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                model_name TEXT NOT NULL,
                territory TEXT NOT NULL,
                period TEXT NOT NULL,
                tax_year INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                domiciliation_date TEXT,
                applies_to TEXT NOT NULL DEFAULT 'todos',
                description TEXT,
                source_url TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_deadlines_territory ON fiscal_deadlines(territory)",
            "CREATE INDEX IF NOT EXISTS idx_deadlines_end_date ON fiscal_deadlines(end_date)",
            "CREATE INDEX IF NOT EXISTS idx_deadlines_model ON fiscal_deadlines(model)",

            # Push subscriptions - Web Push API subscriptions per user device
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                endpoint TEXT NOT NULL,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,
                alert_days TEXT DEFAULT '15,5,1',
                user_agent TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, endpoint)
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id)",

            # Notification log - tracks sent push notifications (idempotency)
            """
            CREATE TABLE IF NOT EXISTS notification_log (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                deadline_id TEXT NOT NULL REFERENCES fiscal_deadlines(id),
                alert_type TEXT NOT NULL,
                sent_at TEXT DEFAULT (datetime('now')),
                UNIQUE(user_id, deadline_id, alert_type)
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_notif_log_user ON notification_log(user_id)",

            # =============================================
            # CRYPTOCURRENCY TABLES
            # =============================================

            # Crypto transactions - raw transaction log per user
            """
            CREATE TABLE IF NOT EXISTS crypto_transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id),
                exchange TEXT,
                tx_type TEXT NOT NULL,
                date_utc TEXT NOT NULL,
                asset TEXT NOT NULL,
                amount REAL NOT NULL,
                price_eur REAL,
                total_eur REAL,
                fee_eur REAL DEFAULT 0,
                counterpart_asset TEXT,
                counterpart_amount REAL,
                notes TEXT,
                source_file TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_crypto_tx_user ON crypto_transactions(user_id, date_utc)",

            # Crypto holdings - aggregated per asset (calculated cache, avg_cost for UI only)
            """
            CREATE TABLE IF NOT EXISTS crypto_holdings (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id),
                asset TEXT NOT NULL,
                total_units REAL NOT NULL,
                avg_cost_eur REAL,
                total_invested_eur REAL,
                current_value_eur REAL,
                unrealized_pnl_eur REAL,
                last_updated TEXT,
                UNIQUE(user_id, asset)
            )
            """,

            # Crypto gains - FIFO-calculated gains/losses per tax year
            """
            CREATE TABLE IF NOT EXISTS crypto_gains (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id),
                tax_year INTEGER NOT NULL,
                asset TEXT NOT NULL,
                tx_type TEXT NOT NULL,
                clave_contraprestacion TEXT,
                date_acquisition TEXT,
                date_transmission TEXT,
                acquisition_value_eur REAL,
                acquisition_fees_eur REAL,
                transmission_value_eur REAL,
                transmission_fees_eur REAL,
                gain_loss_eur REAL,
                anti_aplicacion INTEGER DEFAULT 0,
                source_tx_id TEXT REFERENCES crypto_transactions(id),
                created_at TEXT DEFAULT (datetime('now'))
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_crypto_gains_user_year ON crypto_gains(user_id, tax_year)",

            # =============================================
            # FEEDBACK & CHAT RATINGS TABLES
            # =============================================

            # Feedback table — bug reports, feature requests, general comments
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK(type IN ('bug', 'feature', 'general')),
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                page_url TEXT,
                screenshot_data TEXT,
                status TEXT DEFAULT 'new' CHECK(status IN ('new', 'reviewed', 'planned', 'in_progress', 'done', 'wont_fix')),
                priority TEXT DEFAULT 'normal' CHECK(priority IN ('low', 'normal', 'high', 'critical')),
                admin_notes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(type)",

            # Chat ratings — thumbs up/down per assistant message
            """
            CREATE TABLE IF NOT EXISTS chat_ratings (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                message_id TEXT NOT NULL,
                conversation_id TEXT,
                rating INTEGER NOT NULL CHECK(rating IN (-1, 1)),
                comment TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_ratings_user ON chat_ratings(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ratings_message ON chat_ratings(message_id)",
            "CREATE INDEX IF NOT EXISTS idx_ratings_rating ON chat_ratings(rating)",

            # =============================================
            # MFA / 2FA TABLE
            # =============================================

            """
            CREATE TABLE IF NOT EXISTS user_mfa (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                totp_secret TEXT NOT NULL,
                is_enabled BOOLEAN DEFAULT 0,
                backup_codes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """,

            # Shared conversations (public share links)
            """
            CREATE TABLE IF NOT EXISTS shared_conversations (
                id TEXT PRIMARY KEY,
                share_token TEXT UNIQUE NOT NULL,
                user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
                title TEXT,
                messages TEXT NOT NULL,
                anonymized BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now')),
                view_count INTEGER DEFAULT 0
            )
            """,

            # =============================================
            # --- Phase 3: Contabilidad ---
            # =============================================

            # PGC accounts — Plan General Contable
            """
            CREATE TABLE IF NOT EXISTS pgc_accounts (
                id TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                group_code TEXT NOT NULL,
                group_name TEXT NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                keywords TEXT,
                common_for TEXT,
                is_active BOOLEAN DEFAULT 1
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_pgc_code ON pgc_accounts(code)",

            # Libro registro — Invoice registry (emitidas + recibidas)
            """
            CREATE TABLE IF NOT EXISTS libro_registro (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                workspace_file_id TEXT,
                tipo TEXT NOT NULL,
                numero_factura TEXT,
                fecha_factura TEXT,
                fecha_operacion TEXT,
                emisor_nif TEXT,
                emisor_nombre TEXT,
                receptor_nif TEXT,
                receptor_nombre TEXT,
                concepto TEXT,
                base_imponible REAL NOT NULL,
                tipo_iva REAL,
                cuota_iva REAL,
                tipo_re REAL,
                cuota_re REAL,
                retencion_irpf_pct REAL,
                retencion_irpf REAL,
                total REAL NOT NULL,
                cuenta_pgc TEXT,
                cuenta_pgc_nombre TEXT,
                clasificacion_confianza TEXT,
                trimestre INTEGER,
                year INTEGER NOT NULL,
                raw_extraction TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_libro_user_year ON libro_registro(user_id, year)",

            # Asientos contables — Journal entries (double-entry accounting)
            """
            CREATE TABLE IF NOT EXISTS asientos_contables (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                libro_registro_id TEXT REFERENCES libro_registro(id) ON DELETE CASCADE,
                fecha TEXT NOT NULL,
                numero_asiento INTEGER NOT NULL,
                cuenta_code TEXT NOT NULL,
                cuenta_nombre TEXT NOT NULL,
                debe REAL DEFAULT 0,
                haber REAL DEFAULT 0,
                concepto TEXT,
                year INTEGER NOT NULL,
                trimestre INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """,

            "CREATE INDEX IF NOT EXISTS idx_asientos_user_year ON asientos_contables(user_id, year)",
        ]
        
        try:
            for sql in schema_statements:
                await self.execute(sql)

            # Add is_owner column to users if it doesn't exist
            result = await self.execute("PRAGMA table_info(users)")
            existing_columns = {row["name"] for row in result.rows}
            if "is_owner" not in existing_columns:
                await self.execute("ALTER TABLE users ADD COLUMN is_owner BOOLEAN DEFAULT 0")
                logger.info("Added is_owner column to users table")

            # Add google_id column to users if it doesn't exist (Google SSO)
            if "google_id" not in existing_columns:
                await self.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
                logger.info("Added google_id column to users table")

            # Add deadline_email_alerts column to user_profiles if it doesn't exist
            result = await self.execute("PRAGMA table_info(user_profiles)")
            profile_columns = {row["name"] for row in result.rows}
            if "deadline_email_alerts" not in profile_columns:
                await self.execute(
                    "ALTER TABLE user_profiles ADD COLUMN deadline_email_alerts BOOLEAN DEFAULT 0"
                )
                logger.info("Added deadline_email_alerts column to user_profiles table")

            # Add cost tracking columns to usage_metrics if they don't exist
            result = await self.execute("PRAGMA table_info(usage_metrics)")
            um_columns = {row["name"] for row in result.rows}
            for col, coltype in [("model", "TEXT"), ("input_tokens", "INTEGER DEFAULT 0"),
                                  ("output_tokens", "INTEGER DEFAULT 0"), ("cost_usd", "REAL DEFAULT 0.0")]:
                col_name = col.split()[0]  # just the column name
                if col_name not in um_columns:
                    try:
                        await self.execute(f"ALTER TABLE usage_metrics ADD COLUMN {col} {coltype}")
                        logger.info("Added %s column to usage_metrics table", col_name)
                    except Exception:
                        pass  # column already exists

            # Add workspace_id column to conversations if it doesn't exist
            result = await self.execute("PRAGMA table_info(conversations)")
            conv_columns = {row["name"] for row in result.rows}
            if "workspace_id" not in conv_columns:
                try:
                    await self.execute(
                        "ALTER TABLE conversations ADD COLUMN workspace_id TEXT"
                    )
                    logger.info("Added workspace_id column to conversations table")
                except Exception:
                    pass  # column already exists

            # --- DefensIA tables (spec plans/2026-04-13-defensia-design.md §7.4) ---
            from pathlib import Path as _Path
            _migration_path = _Path(__file__).parent / "migrations" / "20260413_defensia_tables.sql"
            if _migration_path.exists():
                _sql = _migration_path.read_text(encoding="utf-8")
                for _stmt in _sql.split(";"):
                    _stmt = _stmt.strip()
                    if _stmt:
                        await self.execute(_stmt)
                logger.info("DefensIA tables migration applied")
            else:
                logger.warning("DefensIA migration file not found: %s", _migration_path)

            # --- DefensIA storage cifrado (Wave 2B T2B-013a) ---
            # Anade columnas BLOB cifrado a `defensia_documentos`. SQLite no
            # soporta `ADD COLUMN IF NOT EXISTS`, asi que envolvemos cada
            # statement en try/except que ignora "duplicate column name" para
            # mantener la migracion idempotente entre re-arranques. Copilot
            # round 2 #4-#7: cualquier error que NO sea "duplicate/already
            # exists" se re-lanza para abortar el init_schema y evitar que
            # el servicio arranque con un schema incompleto que romperia en
            # runtime.
            await self._apply_defensia_migration(
                _Path(__file__).parent / "migrations" / "20260414_defensia_storage.sql",
                label="storage",
            )

            # --- DefensIA quota en_curso column (Wave 2B T2B-010) ---
            # Anade `en_curso INTEGER DEFAULT 0` a `defensia_cuotas_mensuales`
            # para habilitar el patron reserve-commit-release (H8). Idempotente
            # igual que la migracion de storage: ignoramos "duplicate column"
            # y re-lanzamos cualquier otro error.
            await self._apply_defensia_migration(
                _Path(__file__).parent / "migrations" / "20260414_defensia_quota_encurso.sql",
                label="quota",
            )

            logger.info("Database schema initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    async def _apply_defensia_migration(self, migration_path, label: str) -> None:
        """Aplica un .sql DefensIA con idempotencia + fail-fast.

        Copilot round 2 #4-#7: cualquier error que NO sea "duplicate column" o
        "already exists" se re-lanza inmediatamente para abortar el arranque.
        Asi evitamos que el servicio inicie con un schema incompleto y el
        log ``migration applied`` solo se emite si no hubo errores. La
        idempotencia cubre re-deploys sin tabla ``schema_migrations``.
        """
        if not migration_path.exists():
            logger.warning(
                "DefensIA %s migration file not found: %s", label, migration_path
            )
            return

        sql_text = migration_path.read_text(encoding="utf-8")
        for raw_stmt in sql_text.split(";"):
            # Limpia comentarios SQL linea a linea para evitar que un bloque
            # de comentarios pegado a la primera sentencia anule el statement.
            exec_lines = [
                line
                for line in raw_stmt.splitlines()
                if line.strip() and not line.strip().startswith("--")
            ]
            stmt = "\n".join(exec_lines).strip()
            if not stmt:
                continue
            try:
                await self.execute(stmt)
            except Exception as exc:
                msg = str(exc).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    # Idempotente: el schema ya estaba al dia para este stmt.
                    continue
                logger.exception(
                    "DefensIA %s migration stmt failed; aborting init_schema: %s",
                    label,
                    exc,
                )
                raise
        logger.info("DefensIA %s migration applied", label)


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
