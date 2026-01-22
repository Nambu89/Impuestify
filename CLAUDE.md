# CLAUDE.md - AI Assistant Guide for TaxIA (Impuestify)

> **Last Updated:** 2026-01-19
> **Project Version:** 2.7+
> **Purpose:** Guide for AI assistants working on the TaxIA/Impuestify codebase
>
> **⚠️ CORE INSTRUCTION:** Before starting ANY complex task, you MUST check if `task.md` and `implementation_plan.md` exist in the current context or artifacts directory. If they exist, READ THEM. They contain the definitive source of truth for the current objective and implementation details.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Tech Stack](#tech-stack)
4. [Directory Structure](#directory-structure)
5. [Key Components](#key-components)
6. [Development Workflows](#development-workflows)
7. [Testing Strategy](#testing-strategy)
8. [Deployment Process](#deployment-process)
9. [Conventions and Patterns](#conventions-and-patterns)
10. [Common Tasks](#common-tasks)
11. [Security Considerations](#security-considerations)
12. [Troubleshooting](#troubleshooting)
13. [Active Development Areas](#active-development-areas)

---

## 🎯 Project Overview

**TaxIA (Impuestify)** is an intelligent Spanish tax assistant that uses RAG (Retrieval-Augmented Generation) with a multi-agent architecture to provide accurate, conversational, and contextualized responses about Spanish fiscal regulations.

### Key Features
- **Multi-Agent System**: Coordinator routing to specialized agents (Tax, Payslip, Notification, Workspace)
- **User Workspaces**: Personal document storage for invoices, payslips, and declarations with context-aware analysis
- **RAG Pipeline**: Turso database + FAISS + semantic search for official AEAT documentation
- **Advanced Security**: Llama Guard 4, prompt injection detection, PII filtering, SQL injection prevention
- **Semantic Caching**: Upstash Vector for ~30% cost reduction
- **PDF Processing**: PyMuPDF4LLM for intelligent extraction of payslips and AEAT notifications
- **Real-time Streaming**: SSE (Server-Sent Events) for streaming chat responses
- **GDPR Compliance**: User data export and right to be forgotten

### Target Users
- Spanish taxpayers seeking fiscal information
- Self-employed individuals (autónomos) needing quota calculations
- Employees analyzing payslips and IRPF withholdings

---

## 🏗️ Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + Vite)                  │
│  - Chat interface with SSE streaming                        │
│  - Conversation history sidebar                             │
│  - PDF upload for payslips/notifications                    │
│  - Admin dashboard                                          │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST + SSE
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Python 3.12+)              │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Security Layer (Middleware)                  │   │
│  │  - Rate limiting (SlowAPI + Upstash Redis)          │   │
│  │  - Security headers (CSP, XSS protection)           │   │
│  │  - JWT authentication                               │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     ↓                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Guardrails System                           │   │
│  │  - Llama Guard 4 (Content moderation)              │   │
│  │  - Prompt injection detection (Llama Prompt Guard) │   │
│  │  - PII detection                                    │   │
│  │  - SQL injection prevention                         │   │
│  │  - Complexity router (simple/moderate/complex)      │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     ↓                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Semantic Cache (Upstash Vector)             │   │
│  │  - 0.93 similarity threshold                        │   │
│  │  - 24-hour TTL                                      │   │
│  │  - Skips personal data queries                      │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     ↓                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         CoordinatorAgent (Microsoft Agent Framework) │   │
│  │  - Intelligent query routing                        │   │
│  │  - Chain-of-thought reasoning                       │   │
│  └──────────────────┬───────────────────────────────────┘   │
│            ┌────────┴────────┬────────────────┐             │
│            ↓                 ↓                 ↓             │
│  ┌─────────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │   TaxAgent      │ │ PayslipAgent │ │ NotificationAgent│ │
│  │  - IRPF calc    │ │ - Extraction │ │  - PDF analysis  │ │
│  │  - Autonomous   │ │ - Projections│ │  - Key data      │ │
│  │    quotas       │ │ - Recomm.    │ │    extraction    │ │
│  │  - Tax search   │ │              │ │                  │ │
│  └─────────────────┘ └──────────────┘ └──────────────────┘ │
│            │                 │                 │             │
│            └────────┬────────┴────────┬────────┘             │
│                     ↓                 ↓                      │
│  ┌────────────────────────┐  ┌───────────────────────┐     │
│  │   Tools (Function      │  │   RAG Search          │     │
│  │   Calling)             │  │  - FTS5 full-text     │     │
│  │  - irpf_calculator     │  │  - BM25 ranking       │     │
│  │  - autonomous_quota    │  │  - Web scraping       │     │
│  │  - search_regulations  │  │    fallback (AEAT/BOE)│     │
│  │  - analyze_payslip     │  │                       │     │
│  │  - web_scraper         │  │                       │     │
│  └────────────────────────┘  └───────────────────────┘     │
│                                                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
          ┌──────────┴──────────┬────────────────┬─────────────┐
          ↓                     ↓                ↓             ↓
┌──────────────────┐  ┌─────────────────┐  ┌──────────┐  ┌─────────┐
│  Turso Database  │  │ Upstash Redis   │  │ OpenAI   │  │  Groq   │
│  (SQLite Edge)   │  │ - Session cache │  │ GPT-5    │  │ Llama   │
│  - Users         │  │ - Rate limiting │  │ mini/5   │  │ Guard 4 │
│  - Conversations │  │ - Distributed   │  │          │  │         │
│  - Documents     │  └─────────────────┘  └──────────┘  └─────────┘
│  - Embeddings    │
│  - Payslips      │
└──────────────────┘
```

### Request Flow

1. **User sends question** → Frontend (React)
2. **HTTP POST** → Backend `/api/ask` or `/api/ask/stream`
3. **JWT Validation** → Auth middleware
4. **Rate Limiting** → SlowAPI + Upstash Redis (distributed)
5. **Security Checks** → Llama Guard 4, prompt injection, PII detection
6. **Semantic Cache Lookup** → Upstash Vector (0.93 threshold)
7. **If cache miss** → Route to CoordinatorAgent
8. **Agent Selection** → TaxAgent / PayslipAgent / NotificationAgent
9. **Tool Execution** → IRPF calculator / Search / Payslip analysis
10. **RAG Retrieval** → Turso FTS5 + BM25 ranking + optional web scraping
11. **LLM Generation** → OpenAI GPT-5-mini with context
12. **Response Validation** → Hallucination detection, source verification
13. **Cache Storage** → Store in Upstash Vector for future queries
14. **Response** → JSON (regular) or SSE stream (real-time chunks)

---

## 🛠️ Tech Stack

### Backend (Python 3.12+)

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **API Framework** | FastAPI | 0.104.1+ | REST API with async support |
| **Agent Framework** | Microsoft Agent Framework | 1.0.0b251211 | Multi-agent orchestration |
| **LLM Provider** | OpenAI API | - | GPT-5-mini / GPT-5 |
| **Security AI** | Groq API | - | Llama Guard 4, Llama Prompt Guard |
| **Database** | Turso (libsql) | - | SQLite-compatible edge database |
| **Cache** | Upstash Redis | - | Session cache + rate limiting |
| **Vector Store** | Upstash Vector | - | Semantic similarity cache |
| **PDF Processing** | PyMuPDF4LLM | - | LLM-optimized Markdown extraction |
| **PDF Validation** | pypdf | - | Magic number validation |
| **Embeddings** | FAISS + sentence-transformers | - | Local vector search |
| **Logging** | structlog | - | Structured JSON logs |
| **Metrics** | prometheus-fastapi-instrumentator | - | Prometheus metrics export |
| **Security** | slowapi, python-jose, passlib | - | Rate limiting, JWT, bcrypt |
| **HTTP Client** | httpx | - | Async HTTP with connection pooling |
| **Web Scraping** | BeautifulSoup4 | - | AEAT/BOE scraping |

### Frontend (Node.js 18+)

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Framework** | React | 18.2.0 | UI components |
| **Build Tool** | Vite | 5.0.8 | Fast dev server + bundler |
| **Language** | TypeScript | 5.2.2 | Type safety |
| **Routing** | React Router DOM | 6.21.0 | Client-side routing |
| **HTTP Client** | Axios | 1.6.2 | API requests with interceptors |
| **Markdown** | react-markdown | 10.1.0 | Render AI responses |
| **Icons** | Lucide React | 0.294.0 | Icon library |

### Infrastructure

| Service | Provider | Free Tier | Purpose |
|---------|----------|-----------|---------|
| **Database** | Turso | 500 databases, 9GB storage | SQLite edge database |
| **Cache** | Upstash Redis | 10,000 commands/day | Session cache |
| **Vector Store** | Upstash Vector | 10,000 vectors | Semantic cache |
| **LLM** | OpenAI | Pay-as-you-go | GPT-5-mini/GPT-5 |
| **Security AI** | Groq | 14,400 req/day | Llama Guard 4 (free) |
| **Deployment** | Railway.app | $5/month credit | Monorepo hosting |

---

## 📁 Directory Structure

```
TaxIA/
├── backend/                          # Python FastAPI backend
│   ├── app/
│   │   ├── agents/                   # Multi-agent system (Microsoft Agent Framework)
│   │   │   ├── base_agent.py         # Base agent wrapper
│   │   │   ├── coordinator_agent.py  # Router agent (decides which agent to use)
│   │   │   ├── tax_agent.py          # Tax expert agent (IRPF, quotas, search)
│   │   │   ├── payslip_agent.py      # Payslip analysis specialist
│   │   │   └── notification_agent.py # AEAT notification analyzer
│   │   ├── auth/                     # Authentication
│   │   │   ├── jwt_handler.py        # JWT token generation/validation
│   │   │   └── password.py           # Password hashing (bcrypt)
│   │   ├── core/                     # Core infrastructure
│   │   │   └── http_client.py        # HTTP connection pool manager (httpx)
│   │   ├── database/                 # Database layer
│   │   │   ├── turso_client.py       # Turso SQLite client (libsql)
│   │   │   └── models.py             # Pydantic models for DB entities
│   │   ├── routers/                  # API endpoints (FastAPI routers)
│   │   │   ├── auth.py               # /auth/* - Login, register, refresh
│   │   │   ├── chat.py               # /api/ask - Non-streaming chat
│   │   │   ├── chat_stream.py        # /api/ask/stream - SSE streaming chat
│   │   │   ├── conversations.py      # /api/conversations/* - CRUD
│   │   │   ├── notifications.py      # /api/notifications/* - PDF upload
│   │   │   ├── payslips.py           # /api/payslips/* - Payslip management
│   │   │   ├── security_tests.py     # /test/* - Security testing endpoints
│   │   │   └── user_rights.py        # /api/user-rights/* - GDPR compliance
│   │   ├── security/                 # Security layers (defense-in-depth)
│   │   │   ├── audit_logger.py       # Immutable security event logging
│   │   │   ├── complexity_router.py  # Query complexity classification
│   │   │   ├── guardrails.py         # Input/output validation
│   │   │   ├── llama_guard.py        # Llama Guard 4 content moderation
│   │   │   ├── pii_detector.py       # Personal data detection
│   │   │   ├── prompt_injection.py   # Llama Prompt Guard injection detection
│   │   │   ├── rate_limiter.py       # Distributed rate limiting (Upstash Redis)
│   │   │   ├── semantic_cache.py     # Semantic similarity cache (Upstash Vector)
│   │   │   └── sql_injection.py      # SQL injection prevention
│   │   ├── services/                 # Business logic
│   │   │   ├── rag_service.py        # RAG orchestration (search + rerank)
│   │   │   └── payslip_extractor.py  # PDF text extraction for payslips
│   │   ├── tools/                    # Agent tools (function calling)
│   │   │   ├── irpf_calculator_tool.py      # IRPF tax calculator by CCAA
│   │   │   ├── autonomous_quota_tool.py     # Self-employed quota calculator
│   │   │   ├── search_tool.py               # Tax regulations search (DB + web)
│   │   │   ├── payslip_analysis_tool.py     # Payslip field extraction
│   │   │   └── web_scraper_tool.py          # AEAT/BOE/SS web scraper
│   │   ├── utils/                    # Utilities
│   │   │   ├── pdf_extractor.py      # PyMuPDF4LLM integration
│   │   │   ├── irpf_calculator.py    # IRPF calculation logic
│   │   │   └── text_chunker.py       # Text splitting for RAG
│   │   ├── config.py                 # Pydantic settings (environment variables)
│   │   └── main.py                   # FastAPI app initialization + lifespan
│   ├── data/                         # Data files
│   │   ├── knowledge_updates/        # Recent tax regulations (Markdown)
│   │   │   ├── cuota_autonomos_2025_infoautonomos.md
│   │   │   ├── ipsi_sage_completo.md
│   │   │   └── tarifa_plana_80_euros.md
│   │   └── embeddings/               # FAISS index + metadata
│   ├── scripts/                      # Admin scripts
│   │   └── update_admin.py           # Mark user as admin
│   ├── tests/                        # Unit + integration tests
│   │   ├── conftest.py               # pytest fixtures
│   │   ├── test_agents.py            # Multi-agent system tests
│   │   ├── test_api.py               # API endpoint tests
│   │   ├── test_auth.py              # Authentication tests
│   │   ├── test_coordinator.py       # Router agent tests
│   │   ├── test_ai_security.py       # Guardrails tests
│   │   ├── test_gdpr_endpoints.py    # GDPR compliance tests
│   │   ├── test_integration_simple.py # End-to-end workflows
│   │   ├── test_new_tools.py         # Tool tests (IRPF, quotas)
│   │   ├── test_payslip_analysis.py  # Payslip extraction tests
│   │   ├── test_pdf_extractor.py     # PDF processing tests
│   │   ├── test_redis_rate_limiter.py # Rate limiting tests
│   │   ├── test_search_tool_fallback.py # Search + scraping tests
│   │   └── test_openai_connection.py # LLM connectivity tests
│   ├── requirements.txt              # Python dependencies
│   └── pytest.ini                    # pytest configuration
├── frontend/                         # React + Vite frontend
│   ├── public/                       # Static assets
│   ├── src/
│   │   ├── components/               # React components
│   │   │   ├── AITransparencyModal.tsx  # System transparency info
│   │   │   ├── Chat.tsx                 # Main chat interface
│   │   │   ├── ConversationSidebar.tsx  # Conversation history
│   │   │   ├── Footer.tsx               # App footer
│   │   │   ├── Header.tsx               # App header with navigation
│   │   │   ├── NotificationUpload.tsx   # PDF upload widget
│   │   │   ├── NotificationAnalysisDisplay.tsx # Notification data display
│   │   │   ├── ProtectedRoute.tsx       # Auth-protected routes
│   │   │   └── ThinkingIndicator.tsx    # Loading state for streaming
│   │   ├── hooks/                    # Custom React hooks
│   │   │   ├── useApi.ts             # Axios instance with token refresh
│   │   │   ├── useAuth.tsx           # Authentication context
│   │   │   ├── useConversations.ts   # Conversation CRUD operations
│   │   │   └── useStreamingChat.ts   # SSE streaming handler
│   │   ├── pages/                    # Page components
│   │   │   ├── ChatPage.tsx          # Main chat page
│   │   │   ├── Dashboard.tsx         # Admin dashboard
│   │   │   ├── LoginPage.tsx         # Login form
│   │   │   ├── RegisterPage.tsx      # Registration form
│   │   │   └── SettingsPage.tsx      # User settings
│   │   ├── styles/                   # CSS styles
│   │   │   └── App.css               # Global styles
│   │   ├── App.tsx                   # Main app component with routing
│   │   ├── main.tsx                  # React entry point
│   │   └── vite-env.d.ts             # Vite type declarations
│   ├── .env.example                  # Frontend environment template
│   ├── package.json                  # Node dependencies
│   ├── tsconfig.json                 # TypeScript configuration
│   └── vite.config.ts                # Vite build configuration
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore rules
├── .railwayignore                    # Railway deployment ignore rules
├── .secrets.baseline                 # Detect-secrets baseline
├── railway.toml                      # Railway deployment configuration
├── README.md                         # User-facing documentation
├── CLAUDE.md                         # This file - AI assistant guide
├── SECURITY.md                       # Security policy
├── PRIVACY_POLICY.md                 # Privacy policy
├── TERMS_OF_SERVICE.md               # Terms of service
├── AI_TRANSPARENCY.md                # AI transparency documentation
└── DATA_RETENTION.md                 # Data retention policy
```

---

## 🔑 Key Components

### 1. Multi-Agent System (`backend/app/agents/`)

#### CoordinatorAgent (`coordinator_agent.py`)
- **Purpose**: Intelligent router that decides which specialized agent to invoke
- **Routing Logic**: Analyzes query intent and routes to TaxAgent, PayslipAgent, or NotificationAgent
- **Framework**: Microsoft Agent Framework (structured agent orchestration)
- **Chain-of-Thought**: Uses reasoning traces for transparency
- **Location**: `backend/app/agents/coordinator_agent.py:15`

#### TaxAgent (`tax_agent.py`)
- **Purpose**: Expert on Spanish tax regulations (IRPF, VAT, autonomous quotas)
- **Tools**: `calculate_irpf`, `calculate_autonomous_quota`, `search_tax_regulations`
- **Knowledge Base**: AEAT documentation, BOE regulations, Social Security rules
- **Tone**: Conversational, educational, avoids jargon
- **Location**: `backend/app/agents/tax_agent.py:20`

#### PayslipAgent (`payslip_agent.py`)
- **Purpose**: Specialized in Spanish payslip analysis
- **Capabilities**: Extracts 13 fields (gross salary, IRPF, SS, extras, etc.)
- **Projections**: Calculates annual salary and IRPF withheld
- **Recommendations**: Personalized tax advice based on salary range
- **Location**: `backend/app/agents/payslip_agent.py:18`

#### NotificationAgent (`notification_agent.py`)
- **Purpose**: Analyzes AEAT tax notifications (PDFs)
- **Extraction**: Identifies key amounts, deadlines, concepts
- **Context**: Maintains notification data throughout conversation
- **Location**: `backend/app/agents/notification_agent.py:15`

#### WorkspaceAgent (`workspace_agent.py`)
- **Purpose**: Analyzes user's uploaded workspace documents (payslips, invoices, declarations)
- **Capabilities**:
  - Calculate VAT balance from invoices
  - Project annual IRPF from payslips
  - Remind quarterly declaration deadlines
  - Provide personalized fiscal advice based on user's documents
- **Tools**:
  - `get_workspace_summary` → Summary of all workspace files
  - `calculate_vat_balance` → Quarterly VAT balance (input - output)
  - `project_annual_irpf` → Annual IRPF projection from payslips
  - `get_quarterly_deadlines` → Upcoming tax deadlines
- **Location**: `backend/app/agents/workspace_agent.py:35`

### 2. Security Layers (`backend/app/security/`)

#### Llama Guard 4 (`llama_guard.py`)
- **Provider**: Groq API (free tier: 14,400 req/day)
- **Categories**: 14 risk categories (violence, sexual content, hate speech, etc.)
- **Language**: Spanish responses for each violation category
- **Graceful Degradation**: Fails open if Groq unavailable
- **Latency**: ~200-500ms
- **Location**: `backend/app/security/llama_guard.py:25`

#### Semantic Cache (`semantic_cache.py`)
- **Storage**: Upstash Vector (cosine similarity search)
- **Threshold**: 0.93 similarity (configurable)
- **TTL**: 24 hours
- **Skip Conditions**: Personal data queries, user-specific questions
- **Benefit**: ~30% OpenAI cost reduction
- **Location**: `backend/app/security/semantic_cache.py:30`

#### Rate Limiter (`rate_limiter.py`)
- **Storage**: Upstash Redis (distributed across instances)
- **Fallback**: In-memory rate limiting if Redis unavailable
- **Limits**:
  - `/api/ask`: 10 req/min per IP
  - `/api/ask/stream`: 10 req/min per IP
  - `/api/notifications/analyze-pdf`: 5 req/min per IP
  - `/auth/login`: 5 req/min per IP
- **IP Blocking**: 5 violations → 60-minute block
- **Location**: `backend/app/security/rate_limiter.py:40`

#### Prompt Injection Detection (`prompt_injection.py`)
- **Model**: Llama Prompt Guard 2 (86M parameters) via Groq
- **Detection**: Adversarial prompts, jailbreak attempts, role manipulation
- **Response**: Blocks request before reaching main LLM
- **Location**: `backend/app/security/prompt_injection.py:20`

#### PII Detector (`pii_detector.py`)
- **Detection**: Spanish DNI/NIE, phone numbers, emails, bank accounts
- **Patterns**: Regex-based detection for Spanish formats
- **Action**: Warns user, optionally blocks request
- **Location**: `backend/app/security/pii_detector.py:15`

### 3. Tools (Function Calling) (`backend/app/tools/`)

#### IRPF Calculator (`irpf_calculator_tool.py`)
- **Purpose**: Calculate exact IRPF tax based on income and CCAA
- **Data**: 2024 tax brackets for all 17 autonomous communities
- **Algorithm**: BM25 ranking for CCAA matching
- **Output**: Tax breakdown by bracket (estatal + autonómico)
- **Location**: `backend/app/tools/irpf_calculator_tool.py:30`

#### Autonomous Quota Calculator (`autonomous_quota_tool.py`)
- **Purpose**: Calculate self-employed social security quotas (2025)
- **System**: Variable quota based on net income
- **Thresholds**: Minimum (751.63€) to maximum (1,732.03€)
- **Output**: Monthly and annual quota breakdown
- **Location**: `backend/app/tools/autonomous_quota_tool.py:25`

#### Search Tool (`search_tool.py`)
- **Primary**: Full-text search in Turso database (FTS5)
- **Ranking**: BM25 algorithm for relevance scoring
- **Fallback**: Web scraping AEAT/BOE/Social Security sites
- **Caching**: Results cached in Upstash Redis
- **Location**: `backend/app/tools/search_tool.py:40`

#### Payslip Analysis (`payslip_analysis_tool.py`)
- **Extraction**: 13 regex patterns for Spanish payslip fields
- **Fields**: Period, company, gross/net salary, IRPF, SS, extras
- **Validation**: Cross-checks extracted values for consistency
- **Location**: `backend/app/tools/payslip_analysis_tool.py:35`

#### Web Scraper (`web_scraper_tool.py`)
- **Sites**: AEAT (agenciatributaria.es), BOE (boe.es), SS (seg-social.es)
- **Parser**: BeautifulSoup4 for HTML parsing
- **Normalization**: CCAA name normalization (e.g., "Madrid" → "Comunidad de Madrid")
- **Rate Limiting**: Respects site policies
- **Location**: `backend/app/tools/web_scraper_tool.py:20`

### 3.5 Services (`backend/app/services/`)

#### WorkspaceService (`workspace_service.py`)
- **Purpose**: CRUD operations for user workspaces
- **Methods**:
  - `create_workspace(user_id, data)` → Create new workspace
  - `get_user_workspaces(user_id)` → List user's workspaces with file counts
  - `get_workspace(workspace_id, user_id)` → Get specific workspace (with ownership check)
  - `delete_workspace(workspace_id, user_id)` → Delete workspace and all files
- **Location**: `backend/app/services/workspace_service.py`

#### FileProcessingService (`file_processing_service.py`)
- **Purpose**: Process uploaded files and extract structured data
- **Supported Types**: PDF (nominas, facturas, declaraciones), Excel, CSV
- **Pipeline**:
  1. Validate file (magic number, size)
  2. Extract text (PyMuPDF4LLM for PDF)
  3. Classify file type automatically
  4. Extract structured data (invoice_extractor, payslip_extractor)
  5. Generate embeddings (workspace_embedding_service)
- **Location**: `backend/app/services/file_processing_service.py`

#### InvoiceExtractor (`invoice_extractor.py`)
- **Purpose**: Extract structured data from Spanish invoices
- **Fields Extracted**:
  - Issuer (CIF, name, address)
  - Recipient (CIF, name)
  - Invoice details (number, date, due date)
  - Line items (concept, quantity, unit price)
  - Tax breakdown (base imponible, IVA 21%/10%/4%, IRPF retention)
  - Totals (subtotal, total IVA, total)
- **Patterns**: 30+ regex patterns for Spanish invoice formats
- **Location**: `backend/app/services/invoice_extractor.py`

#### WorkspaceEmbeddingService (`workspace_embedding_service.py`)
- **Purpose**: Generate and store vector embeddings for workspace files
- **Model**: OpenAI text-embedding-3-large (3072 dimensions)
- **Storage**: Turso table `workspace_file_embeddings`
- **Features**:
  - Chunk text into 1000-char segments with 200-char overlap
  - Batch embedding generation
  - Similarity search for RAG context
- **Location**: `backend/app/services/workspace_embedding_service.py`

### 4. Database Schema (Turso SQLite)

#### Core Tables
```sql
-- User authentication
users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT,
  is_admin BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- JWT refresh tokens
sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  refresh_token_hash TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP
)

-- Conversation threads
conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  title TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)

-- Chat messages
messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id),
  role TEXT CHECK(role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  metadata TEXT,  -- JSON string with sources, tool calls, etc.
  created_at TIMESTAMP
)

-- RAG documents
documents (
  id TEXT PRIMARY KEY,
  filename TEXT NOT NULL,
  doc_type TEXT,  -- 'AEAT', 'regulation', 'notification'
  source TEXT,    -- File path or URL
  processed_at TIMESTAMP
)

-- Document chunks for RAG
document_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT REFERENCES documents(id),
  text TEXT NOT NULL,
  chunk_index INTEGER,
  section_id TEXT,
  metadata TEXT  -- JSON string
)

-- Vector embeddings
embeddings (
  id TEXT PRIMARY KEY,
  chunk_id TEXT REFERENCES document_chunks(id),
  vector_hash TEXT,  -- SHA256 of vector for deduplication
  metadata TEXT      -- JSON string
)

-- Payslip data
payslips (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  filename TEXT NOT NULL,
  period_month INTEGER,
  period_year INTEGER,
  company_name TEXT,
  gross_salary REAL,
  net_salary REAL,
  irpf_withholding REAL,
  ss_contribution REAL,
  extraction_status TEXT,  -- 'pending', 'success', 'error'
  extracted_data TEXT,     -- JSON string
  analysis_summary TEXT,
  created_at TIMESTAMP
)

-- Usage metrics
usage_metrics (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  endpoint TEXT,
  tokens_used INTEGER,
  processing_time REAL,
  created_at TIMESTAMP
)

-- Workspaces (user document spaces)
workspaces (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  icon TEXT DEFAULT '📁',
  is_default BOOLEAN DEFAULT 0,
  max_files INTEGER DEFAULT 50,
  max_size_mb INTEGER DEFAULT 100,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
)

-- Workspace files (uploaded documents)
workspace_files (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  file_type TEXT NOT NULL,  -- 'nomina', 'factura', 'declaracion', 'otro'
  mime_type TEXT,
  file_size INTEGER,
  extracted_text TEXT,
  extracted_data TEXT,  -- JSON with structured data
  processing_status TEXT DEFAULT 'pending',  -- pending, processing, completed, error
  error_message TEXT,
  created_at TEXT DEFAULT (datetime('now'))
)

-- Workspace file embeddings (for RAG)
workspace_file_embeddings (
  id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL REFERENCES workspace_files(id) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  chunk_text TEXT NOT NULL,
  embedding_vector TEXT,  -- JSON array of floats
  created_at TEXT DEFAULT (datetime('now'))
)
```

### 5. Frontend Architecture

#### Custom Hooks
- **`useAuth`** (`hooks/useAuth.tsx:10`): Authentication context (login, logout, token management)
- **`useApi`** (`hooks/useApi.ts:15`): Axios instance with automatic token refresh
- **`useConversations`** (`hooks/useConversations.ts:20`): CRUD operations for conversations
- **`useStreamingChat`** (`hooks/useStreamingChat.ts:25`): SSE event parsing and state management
- **`useWorkspaces`** (`hooks/useWorkspaces.ts`): Workspace CRUD, file upload, active workspace state

#### Key Components
- **`Chat.tsx`** (`components/Chat.tsx:50`): Main chat interface with SSE streaming
- **`ConversationSidebar.tsx`** (`components/ConversationSidebar.tsx:30`): Persistent conversation history
- **`NotificationUpload.tsx`** (`components/NotificationUpload.tsx:20`): PDF upload with validation
- **`ProtectedRoute.tsx`** (`components/ProtectedRoute.tsx:10`): Auth-gated routes

#### Workspace Components (NEW)
- **`WorkspacesPage.tsx`** (`pages/WorkspacesPage.tsx`): Workspace management page with file list
- **`WorkspaceSelector.tsx`** (`components/WorkspaceSelector.tsx`): Dropdown to select active workspace
- **`WorkspaceContextIndicator.tsx`** (`components/WorkspaceContextIndicator.tsx`): Shows active workspace context
- **`FileUploader.tsx`** (`components/FileUploader.tsx`): Drag & drop file upload with type detection

#### SSE Event Format
```typescript
// Frontend expects SSE events in this format:
interface SSEEvent {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'content' | 'complete';
  data: string;  // JSON stringified content
  index?: number;  // For chunked content
}

// Example SSE message from backend:
event: content
data: {"type": "content", "data": "La respuesta es...", "index": 0}

// Complete event structure:
event: complete
data: {
  "type": "complete",
  "data": {
    "answer": "Full response text",
    "sources": [...],
    "metadata": {...}
  }
}
```

---

## 🔄 Development Workflows

### Local Development Setup

#### 1. Prerequisites
```bash
# Check versions
python --version  # Should be 3.12+
node --version    # Should be 18+

# Clone repository
git clone https://github.com/Nambu89/TaxIA.git
cd TaxIA
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy .env template
cp ../.env.example ../.env

# Edit .env with your credentials:
# - OPENAI_API_KEY (required)
# - GROQ_API_KEY (required for security)
# - TURSO_DATABASE_URL (required)
# - TURSO_AUTH_TOKEN (required)
# - UPSTASH_REDIS_REST_URL (optional)
# - UPSTASH_REDIS_REST_TOKEN (optional)
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)

# Initialize database (auto-creates schema on first connection)
# Run backend to trigger schema initialization
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env
echo "VITE_API_URL=http://localhost:8000" > .env

# Start dev server
npm run dev  # Runs on http://localhost:5173
```

#### 4. Verify Setup
```bash
# Backend health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": 1234567890.0,
  "version": "1.0.0",
  "rag_initialized": true,
  "statistics": {
    "database": "turso",
    "documents": 10,
    "embeddings": 523,
    "status": "connected"
  }
}
```

### Git Workflow

#### Branch Strategy
- **Current Development Branch**: `claude/claude-md-mk8kksbacnqt6c1c-lcqvS`
- **Convention**: Always work on branches starting with `claude/` for Claude-assisted development
- **Main Branch**: Not specified (check with maintainers)

#### Commit Conventions
```bash
# Format: <type>: <description>
# Types:
#   feat:     New feature
#   fix:      Bug fix
#   docs:     Documentation changes
#   style:    Formatting (no code changes)
#   refactor: Code restructuring
#   test:     Adding tests
#   chore:    Maintenance tasks

# Examples:
git commit -m "feat: Add semantic cache for OpenAI cost reduction"
git commit -m "fix: Handle SSE parsing errors in frontend"
git commit -m "docs: Update CLAUDE.md with security layers"
```

#### Recent Changes Context
```bash
# Latest commits on current branch:
# a4a97c9 - Debug: Add extensive SSE logging to trace execution flow
# 3be69f4 - force frontend rebuild: SSE streaming fix v2.0.1
# b6fd7e1 - Fix: Frontend SSE parsing - handle JSON content and fix onComplete callback
# 3236b4d - Debug: Add print(flush=True) statements for Railway SSE tracing
# 90b5d0a - Fix: Rewrite SSE streaming to use sse-starlette dict format correctly

# Current focus: SSE streaming stability
```

### Making Changes

#### Backend Changes
```bash
# 1. Read the relevant file first
# Example: Modifying a router endpoint
cat backend/app/routers/chat_stream.py

# 2. Make changes using your editor

# 3. Test changes locally
uvicorn app.main:app --reload

# 4. Run tests
cd backend
pytest tests/test_api.py -v

# 5. Commit and push
git add .
git commit -m "feat: Add retry logic to SSE streaming"
git push -u origin claude/claude-md-mk8kksbacnqt6c1c-lcqvS
```

#### Frontend Changes
```bash
# 1. Read the relevant component
cat frontend/src/components/Chat.tsx

# 2. Make changes

# 3. Test in dev mode (hot reload)
npm run dev

# 4. Build to verify no errors
npm run build

# 5. Commit and push
git add .
git commit -m "fix: Handle SSE disconnection gracefully"
git push -u origin claude/claude-md-mk8kksbacnqt6c1c-lcqvS
```

### Database Migrations

**Note**: Turso schema is auto-initialized on first connection. No migration files needed.

To modify schema:
1. Edit `backend/app/database/turso_client.py:init_schema()`
2. Add new table definitions or ALTER TABLE statements
3. Schema changes apply on next connection

---

## 🧪 Testing Strategy

### Test Organization

```
tests/
├── conftest.py                    # Fixtures (DB mocks, auth tokens, OpenAI mocks)
├── test_agents.py                 # Multi-agent orchestration tests
├── test_api.py                    # API endpoint tests (CRUD, errors)
├── test_auth.py                   # JWT, login, registration, refresh
├── test_coordinator.py            # Router agent decision logic
├── test_ai_security.py            # Guardrails, Llama Guard, PII detection
├── test_gdpr_endpoints.py         # Data export, right to be forgotten
├── test_integration_simple.py     # End-to-end workflows
├── test_new_tools.py              # IRPF calculator, autonomous quota
├── test_payslip_analysis.py       # Payslip extraction accuracy
├── test_pdf_extractor.py          # PyMuPDF4LLM integration
├── test_redis_rate_limiter.py     # Rate limiting logic
├── test_search_tool_fallback.py   # RAG search + web scraping fallback
└── test_openai_connection.py      # LLM connectivity
```

### Running Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_auth.py -v

# Run specific test function
pytest tests/test_api.py::test_ask_question -v

# Run tests excluding slow tests
pytest tests/ -m "not slow" -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Test Fixtures (conftest.py)

```python
# Key fixtures available in all tests:

@pytest.fixture
def mock_db():
    """Mock Turso database client"""
    # Returns mock database with sample data

@pytest.fixture
def auth_token():
    """Generate valid JWT token for testing"""
    # Returns Bearer token string

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API responses"""
    # Prevents actual API calls during tests

@pytest.fixture
async def test_user():
    """Create test user in database"""
    # Returns user dict with credentials
```

### Writing Tests

#### Example: Testing an API Endpoint
```python
import pytest
from fastapi.testclient import TestClient

def test_ask_question_authenticated(client, auth_token):
    """Test /api/ask with authenticated user"""
    response = client.post(
        "/api/ask",
        json={"question": "¿Qué es el IRPF?"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)
```

#### Example: Testing a Tool
```python
import pytest
from app.tools.irpf_calculator_tool import calculate_irpf

@pytest.mark.asyncio
async def test_irpf_calculator_madrid():
    """Test IRPF calculation for Madrid"""
    result = await calculate_irpf(
        annual_income=30000,
        ccaa="Madrid"
    )

    assert result["status"] == "success"
    assert result["total_irpf"] > 0
    assert "breakdown" in result
```

---

## 🚀 Deployment Process

### Railway.app Deployment

#### Configuration (`railway.toml`)
```toml
[build]
builder = "NIXPACKS"  # Auto-detects environment

[[services]]
name = "impuestify-backend"
source = "backend"
buildCommand = "pip install -r requirements.txt"
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"

[[services]]
name = "impuestify-frontend"
source = "frontend"
buildCommand = "npm install && npm run build"
startCommand = "npm run preview -- --host 0.0.0.0 --port $PORT"
```

#### Environment Variables (Railway Dashboard)

**Backend Service:**
```bash
# Required
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
TURSO_DATABASE_URL=libsql://...
TURSO_AUTH_TOKEN=...
JWT_SECRET_KEY=...  # Generate: openssl rand -hex 32

# Optional (recommended)
UPSTASH_REDIS_REST_URL=https://...
UPSTASH_REDIS_REST_TOKEN=...
UPSTASH_VECTOR_REST_URL=https://...
UPSTASH_VECTOR_REST_TOKEN=...

# Model settings
OPENAI_MODEL=gpt-5-mini
RATE_LIMIT_PER_MINUTE=10

# CORS (important!)
ALLOWED_ORIGINS=https://your-frontend.railway.app
```

**Frontend Service:**
```bash
VITE_API_URL=https://your-backend.railway.app
```

#### Deployment Steps

1. **Connect GitHub Repository**
   - Go to Railway.app → New Project → Deploy from GitHub
   - Select `TaxIA` repository
   - Railway auto-detects `railway.toml` and creates 2 services

2. **Configure Environment Variables**
   - Add variables for backend service (see above)
   - Add `VITE_API_URL` for frontend service
   - **Important**: Update `ALLOWED_ORIGINS` with frontend URL after deployment

3. **Deploy**
   - Railway auto-deploys on push to main branch
   - Monitor logs: `railway logs -s impuestify-backend`

4. **Verify Deployment**
   ```bash
   # Check backend health
   curl https://your-backend.railway.app/health

   # Test authentication
   curl -X POST https://your-backend.railway.app/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "Test123!"}'
   ```

5. **Update CORS** (Important!)
   - After frontend deploys, copy its URL
   - Add to backend `ALLOWED_ORIGINS` environment variable
   - Redeploy backend service

#### Health Checks
- **Path**: `/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Backend auto-initializes Turso schema on startup**

#### Monitoring
```bash
# View logs
railway logs -s impuestify-backend
railway logs -s impuestify-frontend

# Follow logs in real-time
railway logs -s impuestify-backend --follow
```

---

## 📐 Conventions and Patterns

### Code Style

#### Python (Backend)
- **PEP 8**: Follow standard Python style guide
- **Type Hints**: Use type annotations for function signatures
- **Docstrings**: Google-style docstrings for public functions
- **Async/Await**: All database and HTTP operations must be async
- **Error Handling**: Use HTTPException with appropriate status codes

```python
# Good example
async def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Retrieve user by ID from database.

    Args:
        user_id: Unique user identifier

    Returns:
        User object if found, None otherwise

    Raises:
        HTTPException: If database connection fails
    """
    try:
        result = await db.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        return User(**result.rows[0]) if result.rows else None
    except Exception as e:
        logger.error("Failed to fetch user", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
```

#### TypeScript (Frontend)
- **ESLint**: Follow React/TypeScript best practices
- **Interfaces**: Define interfaces for all API responses
- **Hooks**: Use custom hooks for reusable logic
- **Error Handling**: Always handle promise rejections

```typescript
// Good example
interface ChatResponse {
  answer: string;
  sources: Source[];
  metadata: Record<string, any>;
  processing_time: number;
  cached: boolean;
}

const useChatApi = () => {
  const api = useApi();

  const askQuestion = async (question: string): Promise<ChatResponse> => {
    try {
      const response = await api.post<ChatResponse>('/api/ask', { question });
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.error || 'Request failed');
      }
      throw error;
    }
  };

  return { askQuestion };
};
```

### Naming Conventions

#### Files
- **Python**: `snake_case.py` (e.g., `irpf_calculator_tool.py`)
- **TypeScript**: `PascalCase.tsx` for components (e.g., `ChatPage.tsx`)
- **TypeScript**: `camelCase.ts` for utilities (e.g., `useAuth.ts`)

#### Variables
- **Python**: `snake_case` (e.g., `user_id`, `processing_time`)
- **TypeScript**: `camelCase` (e.g., `userId`, `processingTime`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_TOKENS`, `API_URL`)

#### Functions
- **Python**: `snake_case` (e.g., `calculate_irpf()`, `get_user()`)
- **TypeScript**: `camelCase` (e.g., `fetchConversations()`, `handleSubmit()`)

#### Classes
- **Both**: `PascalCase` (e.g., `TursoClient`, `CoordinatorAgent`)

### Architectural Patterns

#### 1. Dependency Injection (Backend)
```python
# Bad: Direct instantiation
def my_endpoint():
    db = TursoClient()  # Hard to test
    user = db.get_user(123)

# Good: Dependency injection via FastAPI
from fastapi import Depends

def my_endpoint(db: TursoClient = Depends(get_database)):
    user = await db.get_user(123)  # Easy to mock in tests
```

#### 2. Error Handling (Backend)
```python
# Always use HTTPException for API errors
from fastapi import HTTPException

# Bad
def get_user(user_id: str):
    return None  # Silent failure

# Good
async def get_user(user_id: str) -> User:
    user = await db.execute(...)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    return user
```

#### 3. Async/Await Consistency (Backend)
```python
# All I/O operations MUST be async
# Bad
def fetch_data():
    response = requests.get("https://...")  # Blocking
    return response.json()

# Good
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://...")  # Non-blocking
        return response.json()
```

#### 4. React Hooks Pattern (Frontend)
```typescript
// Always extract reusable logic into custom hooks
// Bad: Logic in component
const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (text: string) => {
    setLoading(true);
    // Complex API logic here...
  };

  return <div>...</div>;
};

// Good: Custom hook
const useChat = () => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (text: string) => {
    // Complex API logic here...
  };

  return { messages, loading, sendMessage };
};

const ChatPage = () => {
  const { messages, loading, sendMessage } = useChat();
  return <div>...</div>;
};
```

### Logging Conventions

#### Structured Logging (Backend)
```python
import structlog
logger = structlog.get_logger()

# Always use structured logging with context
# Bad
logger.info(f"User {user_id} logged in")

# Good
logger.info(
    "User logged in",
    user_id=user_id,
    ip_address=request.client.host,
    timestamp=time.time()
)
```

#### Log Levels
- **DEBUG**: Detailed information for debugging (disabled in production)
- **INFO**: General informational messages (cache hits, successful operations)
- **WARNING**: Non-critical issues (cache miss, fallback to default)
- **ERROR**: Errors that need attention (API failures, database errors)
- **CRITICAL**: System-critical failures (startup errors, configuration issues)

#### Log Emoji Conventions
```python
# Cache operations
logger.info("💾 Cache HIT", key=cache_key)
logger.info("🔍 Cache MISS", key=cache_key)

# Security events
logger.warning("🛡️ Guardrail violation", violation_type="prompt_injection")
logger.warning("🚫 Rate limit exceeded", ip=client_ip)

# System events
logger.info("✅ Database connected", docs=doc_count)
logger.error("❌ OpenAI API failed", error=str(e))
```

---

## 🛠️ Common Tasks

### 1. Adding a New API Endpoint

```python
# File: backend/app/routers/my_feature.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.auth.jwt_handler import get_current_user
from app.database.turso_client import get_db_client

router = APIRouter(prefix="/api/my-feature", tags=["my-feature"])

class MyRequest(BaseModel):
    data: str

class MyResponse(BaseModel):
    result: str

@router.post("/", response_model=MyResponse)
async def my_endpoint(
    request: MyRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_db_client)
):
    """
    Description of what this endpoint does.

    Requires authentication.
    """
    try:
        # Your logic here
        return MyResponse(result="Success")
    except Exception as e:
        logger.error("Error in my_endpoint", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

# File: backend/app/main.py
# Add this line:
from app.routers.my_feature import router as my_feature_router
app.include_router(my_feature_router)
```

### 2. Adding a New Agent Tool

```python
# File: backend/app/tools/my_new_tool.py

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()

class MyToolInput(BaseModel):
    """Input schema for tool"""
    param1: str
    param2: int

class MyToolOutput(BaseModel):
    """Output schema for tool"""
    result: str
    confidence: float

async def my_new_tool(params: MyToolInput) -> MyToolOutput:
    """
    Description of what this tool does.

    Args:
        params: Input parameters

    Returns:
        Tool output with results
    """
    logger.info("Executing my_new_tool", param1=params.param1)

    # Your tool logic here
    result = f"Processed: {params.param1}"

    return MyToolOutput(result=result, confidence=0.95)

# File: backend/app/agents/tax_agent.py
# Add to the agent's tools list in the function definitions
```

### 3. Adding a New Frontend Component

```typescript
// File: frontend/src/components/MyComponent.tsx

import React from 'react';

interface MyComponentProps {
  data: string;
  onAction: (value: string) => void;
}

export const MyComponent: React.FC<MyComponentProps> = ({ data, onAction }) => {
  const handleClick = () => {
    onAction(data);
  };

  return (
    <div className="my-component">
      <p>{data}</p>
      <button onClick={handleClick}>Action</button>
    </div>
  );
};

// File: frontend/src/pages/SomePage.tsx
// Import and use:
import { MyComponent } from '../components/MyComponent';

const SomePage = () => {
  const handleAction = (value: string) => {
    console.log('Action:', value);
  };

  return (
    <div>
      <MyComponent data="Hello" onAction={handleAction} />
    </div>
  );
};
```

### 4. Adding a New Database Table

```python
# File: backend/app/database/turso_client.py
# Add to the init_schema() method:

async def init_schema(self):
    """Initialize database schema"""

    # ... existing tables ...

    # Add your new table
    await self.execute("""
        CREATE TABLE IF NOT EXISTS my_new_table (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    await self.execute("""
        CREATE INDEX IF NOT EXISTS idx_my_table_user
        ON my_new_table(user_id)
    """)

    logger.info("✅ my_new_table initialized")
```

### 5. Adding a Security Check

```python
# File: backend/app/security/my_security_check.py

import structlog
from typing import Optional

logger = structlog.get_logger()

class SecurityViolation(Exception):
    """Raised when security check fails"""
    pass

async def my_security_check(input_text: str) -> bool:
    """
    Perform security validation on input.

    Args:
        input_text: Text to validate

    Returns:
        True if safe, raises SecurityViolation otherwise
    """
    # Your validation logic
    if "malicious_pattern" in input_text.lower():
        logger.warning(
            "🛡️ Security check failed",
            check_type="my_security_check",
            reason="Malicious pattern detected"
        )
        raise SecurityViolation("Input contains malicious content")

    return True

# File: backend/app/routers/chat.py
# Add to the security pipeline before LLM call
from app.security.my_security_check import my_security_check

await my_security_check(user_input)
```

### 6. Adding Environment Variables

```python
# File: backend/app/config.py
# Add to the Settings class:

class Settings(BaseSettings):
    # ... existing settings ...

    MY_NEW_SETTING: Optional[str] = Field(
        default=None,
        description="Description of what this setting does"
    )

    @field_validator("MY_NEW_SETTING", mode="before")
    @classmethod
    def strip_quotes(cls, v):
        return v.strip().strip('"').strip("'") if isinstance(v, str) else v

# File: .env.example
# Add to the template:
# My Feature Configuration
MY_NEW_SETTING=default_value
```

### 7. Creating a Database Migration

**Note**: Turso auto-initializes schema, but for major changes:

```python
# File: backend/scripts/migrate_data.py

import asyncio
from app.database.turso_client import TursoClient

async def migrate():
    """Migrate data from old schema to new schema"""
    db = TursoClient()
    await db.connect()

    # 1. Create new table
    await db.execute("""
        CREATE TABLE IF NOT EXISTS new_table (
            id TEXT PRIMARY KEY,
            data TEXT
        )
    """)

    # 2. Migrate data
    old_data = await db.execute("SELECT * FROM old_table")
    for row in old_data.rows:
        await db.execute(
            "INSERT INTO new_table (id, data) VALUES (?, ?)",
            (row['id'], row['data'])
        )

    # 3. Drop old table (optional)
    # await db.execute("DROP TABLE old_table")

    await db.disconnect()
    print("✅ Migration complete")

if __name__ == "__main__":
    asyncio.run(migrate())
```

---

## 🔒 Security Considerations

### Defense-in-Depth Architecture

TaxIA implements multiple security layers:

1. **Input Layer** (before processing)
   - Rate limiting (SlowAPI + Upstash Redis)
   - Prompt injection detection (Llama Prompt Guard)
   - PII detection (regex-based)
   - SQL injection prevention

2. **Processing Layer** (during LLM call)
   - Content moderation (Llama Guard 4)
   - Complexity routing (simple/moderate/complex)
   - Semantic cache (skip personal data)

3. **Output Layer** (after LLM response)
   - Hallucination detection
   - Source verification
   - Guardrails validation

4. **Audit Layer** (continuous)
   - Immutable security event logging
   - Prometheus metrics
   - Structured logging (structlog)

### Security Best Practices

#### 1. Never Log Sensitive Data
```python
# Bad
logger.info(f"User logged in: {email}, password: {password}")

# Good
logger.info("User logged in", user_id=user.id)
```

#### 2. Always Validate JWT Tokens
```python
from app.auth.jwt_handler import get_current_user

@router.post("/protected")
async def protected_endpoint(
    current_user = Depends(get_current_user)  # ✅ Always use this
):
    # User is authenticated here
    pass
```

#### 3. Use Parameterized Queries
```python
# Bad (SQL injection risk)
await db.execute(f"SELECT * FROM users WHERE email = '{email}'")

# Good (safe)
await db.execute("SELECT * FROM users WHERE email = ?", (email,))
```

#### 4. Validate File Uploads
```python
# Always validate magic numbers (file signatures)
def is_valid_pdf(file_bytes: bytes) -> bool:
    return file_bytes.startswith(b'%PDF')

# Limit file size
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

if len(file_bytes) > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail="File too large")
```

#### 5. Rate Limit Expensive Operations
```python
from app.security.rate_limiter import rate_limit_ask

@router.post("/api/ask")
@rate_limit_ask  # 10 requests per minute
async def ask_question(request: QuestionRequest):
    # Expensive LLM operation
    pass
```

### Security Headers

All responses include security headers (see `backend/app/main.py:322`):
- **Content-Security-Policy**: Prevents XSS attacks
- **X-Content-Type-Options**: Prevents MIME type sniffing
- **X-Frame-Options**: Prevents clickjacking
- **X-XSS-Protection**: Legacy XSS protection
- **Referrer-Policy**: Limits referrer information
- **Permissions-Policy**: Restricts browser features

### GDPR Compliance

#### Data Export
```python
# Users can export their data
GET /api/user-rights/export-data
Authorization: Bearer <token>

# Response:
{
  "user": {...},
  "conversations": [...],
  "messages": [...],
  "payslips": [...]
}
```

#### Right to be Forgotten
```python
# Users can delete their account and all data
POST /api/user-rights/delete-account
Authorization: Bearer <token>

# Deletes:
# - User account
# - All conversations
# - All messages
# - All payslips
# - All sessions
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Backend Won't Start

**Symptom**: `uvicorn app.main:app` fails with import errors

**Solution**:
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check Python version
python --version  # Must be 3.12+
```

#### 2. Turso Database Connection Fails

**Symptom**: Health check shows `database: not_connected`

**Solution**:
```bash
# Verify environment variables
echo $TURSO_DATABASE_URL
echo $TURSO_AUTH_TOKEN

# Check .env file
cat .env | grep TURSO

# Test connection with Turso CLI
turso db show <database-name>
```

#### 3. Frontend Can't Connect to Backend

**Symptom**: Network errors in browser console

**Solution**:
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify CORS settings in backend/app/main.py
# ALLOWED_ORIGINS should include http://localhost:5173

# Check frontend .env
cat frontend/.env
# Should contain: VITE_API_URL=http://localhost:8000
```

#### 4. SSE Streaming Not Working

**Symptom**: Chat loads forever, no response chunks

**Recent Fix**: Recent commits (a4a97c9, 3be69f4, b6fd7e1) addressed SSE issues

**Debug Steps**:
```bash
# Backend logs
tail -f backend/logs/taxia.log | grep SSE

# Check SSE event format
curl -N -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question":"Test"}' \
  http://localhost:8000/api/ask/stream

# Expected format:
# event: content
# data: {"type": "content", "data": "chunk", "index": 0}
```

**Solution**:
- Ensure `print(flush=True)` in streaming code (Railway fix)
- Verify SSE events use `dict` format, not string format
- Check frontend parsing in `useStreamingChat.ts:45`

#### 5. OpenAI API Errors

**Symptom**: `OpenAI API failed` in logs

**Solution**:
```bash
# Verify API key is valid
echo $OPENAI_API_KEY

# Check usage limits
# https://platform.openai.com/usage

# Try with fallback model
export OPENAI_MODEL=gpt-4o-mini

# Check for rate limiting
# OpenAI has strict rate limits on free tier
```

#### 6. Rate Limiting Issues

**Symptom**: `429 Too Many Requests`

**Solution**:
```bash
# Check rate limit settings
echo $RATE_LIMIT_PER_MINUTE  # Default: 10

# Increase limit for development
export RATE_LIMIT_PER_MINUTE=100

# Clear Redis rate limit cache
# (if using Upstash Redis)
curl -X POST $UPSTASH_REDIS_REST_URL/flushdb \
  -H "Authorization: Bearer $UPSTASH_REDIS_REST_TOKEN"
```

#### 7. Payslip Extraction Fails

**Symptom**: Uploaded PDF shows `extraction_status: error`

**Solution**:
```bash
# Check PyMuPDF4LLM is installed
pip show pymupdf4llm

# Verify PDF is valid
python -c "import fitz; doc = fitz.open('test.pdf'); print(doc.page_count)"

# Check logs for extraction errors
grep "payslip" backend/logs/taxia.log
```

#### 8. Tests Failing

**Symptom**: `pytest` shows failures

**Solution**:
```bash
# Update test dependencies
pip install -r requirements.txt

# Clear pytest cache
rm -rf .pytest_cache

# Run tests with verbose output
pytest tests/ -v -s

# Check for async test issues
# Ensure conftest.py has:
# pytest_plugins = ['pytest_asyncio']
```

### Debug Mode

Enable detailed logging:

```bash
# Backend
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug

# Frontend
npm run dev -- --debug
```

### Logging Locations

- **Backend**: Console output (structlog JSON format)
- **Frontend**: Browser console
- **Railway**: Railway dashboard logs tab

---

## 🚧 Active Development Areas

### Current Focus (Jan 2026)

Based on recent commits, the active areas are:

#### 1. SSE Streaming Stability
- **Recent Fixes** (commits: a4a97c9, 3be69f4, b6fd7e1, 3236b4d, 90b5d0a)
- **Focus**: Ensuring SSE events stream correctly on Railway.app
- **Key Files**:
  - `backend/app/routers/chat_stream.py`
  - `frontend/src/hooks/useStreamingChat.ts`
  - `frontend/src/components/Chat.tsx`

#### 2. Known Issues
- **SSE Buffering**: Railway may buffer SSE events; using `print(flush=True)` as workaround
- **Frontend Parsing**: SSE event parsing had JSON nesting issues (recently fixed)
- **Callback Timing**: `onComplete` callback timing issues (recently fixed)

#### 3. Upcoming Features (Potential)
- **Conversation Branching**: Allow users to fork conversations
- **Export Conversations**: Export chat history to PDF/Markdown
- **Multi-language Support**: Extend beyond Spanish
- **Advanced Analytics**: Usage dashboards for admins
- **Bulk PDF Upload**: Process multiple payslips at once

### Contributing Guidelines

When making changes:

1. **Always read files before editing**: Use `Read` tool to understand existing code
2. **Follow conventions**: Match existing code style and patterns
3. **Add tests**: Every new feature should have tests
4. **Update documentation**: Update this CLAUDE.md when adding features
5. **Log changes**: Use structured logging with context
6. **Test locally**: Run tests and verify changes before pushing
7. **Use feature branches**: Branch from `claude/` prefix for Claude-assisted work
8. **Write clear commit messages**: Follow conventional commits format

### Code Review Checklist

Before pushing code:

- [ ] Code follows style conventions (PEP 8 / ESLint)
- [ ] All new functions have docstrings
- [ ] Tests pass locally (`pytest tests/`)
- [ ] No sensitive data in logs
- [ ] Error handling is comprehensive
- [ ] Type hints are present (Python) or interfaces defined (TypeScript)
- [ ] Security considerations addressed (especially for user input)
- [ ] Documentation updated (if API changed)
- [ ] Environment variables added to `.env.example`
- [ ] Commit message follows convention

---

## 📚 Additional Resources

### Documentation Files
- **README.md**: User-facing documentation and setup guide
- **SECURITY.md**: Security policy and vulnerability reporting
- **PRIVACY_POLICY.md**: GDPR compliance and data handling
- **TERMS_OF_SERVICE.md**: Legal terms for users
- **AI_TRANSPARENCY.md**: AI system transparency documentation
- **DATA_RETENTION.md**: Data retention policies

### External Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Groq API Docs](https://console.groq.com/docs)
- [Turso Documentation](https://docs.turso.tech/)
- [Upstash Redis](https://docs.upstash.com/redis)
- [Upstash Vector](https://docs.upstash.com/vector)
- [Railway Docs](https://docs.railway.app/)

### Key Contacts
- **Repository Owner**: Nambu89
- **GitHub**: https://github.com/Nambu89/TaxIA
- **Issues**: https://github.com/Nambu89/TaxIA/issues

---

## 🎓 Learning Resources

### Understanding the Codebase

#### For New AI Assistants:
1. **Start with architecture**: Read the "Architecture Overview" section
2. **Understand the flow**: Follow a request from frontend → backend → LLM → response
3. **Explore key files**:
   - `backend/app/main.py` - Entry point
   - `backend/app/config.py` - Configuration
   - `backend/app/agents/coordinator_agent.py` - Core routing logic
   - `frontend/src/App.tsx` - Frontend routing
   - `frontend/src/hooks/useAuth.tsx` - Authentication

#### Common Patterns:
- **Dependency Injection**: FastAPI `Depends()` for testability
- **Async/Await**: All I/O operations are async
- **Structured Logging**: Context-rich JSON logs
- **Defense-in-Depth**: Multiple security layers
- **RAG Pipeline**: Search → Rank → Context → Generate → Validate

---

**Last Updated**: 2026-01-10
**Version**: 1.0
**Maintained by**: Claude Code Assistant
**For**: TaxIA (Impuestify) Development Team
