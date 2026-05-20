"""
TaxIA Configuration

Unified settings using Pydantic with Open AI services support.
"""

import os

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -------------------------------
    # 🤖 OpenAI API (Primary LLM)
    # -------------------------------
    OPENAI_API_KEY: str | None = Field(default=None, description="OpenAI API key")
    OPENAI_MODEL: str | None = Field(
        default="gpt-5-mini",
        description="OpenAI model to use (gpt-5-mini, gpt-5, gpt-5.1, gpt-5.2)",
    )

    # -------------------------------
    # 🔐 Open AI Foundry (Optional Fallback)
    # -------------------------------
    AZURE_OPENAI_API_KEY: str | None = Field(
        default=None, validation_alias=AliasChoices("AZURE_OPENAI_API_KEY")
    )
    AZURE_OPENAI_ENDPOINT: str | None = Field(
        default=None, validation_alias=AliasChoices("AZURE_OPENAI_ENDPOINT")
    )
    AZURE_OPENAI_DEPLOYMENT: str | None = Field(
        default=None, validation_alias=AliasChoices("AZURE_OPENAI_DEPLOYMENT")
    )
    AZURE_OPENAI_API_VERSION: str | None = Field(
        default=None, validation_alias=AliasChoices("AZURE_OPENAI_API_VERSION")
    )

    # -------------------------------
    # 📄 Azure Document Intelligence
    # -------------------------------
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str | None = Field(default=None)
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str | None = Field(default=None)

    # -------------------------------
    # 🔮 Google Gemini (Invoice OCR)
    # -------------------------------
    GOOGLE_GEMINI_API_KEY: str | None = Field(default=None)
    GEMINI_MODEL: str = Field(
        default="gemini-3-flash-preview", description="Gemini model for invoice OCR"
    )

    # -------------------------------
    # 🗄️ Turso Database
    # -------------------------------
    TURSO_DATABASE_URL: str | None = Field(default=None)
    TURSO_AUTH_TOKEN: str | None = Field(default=None)

    # -------------------------------
    # 📦 Upstash Redis
    # -------------------------------
    UPSTASH_REDIS_REST_URL: str | None = Field(default=None)
    UPSTASH_REDIS_REST_TOKEN: str | None = Field(default=None)

    # -------------------------------
    # 🔒 JWT Authentication
    # -------------------------------
    JWT_SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production",
        validation_alias=AliasChoices("JWT_SECRET_KEY"),
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # -------------------------------
    # 📁 Paths de datos e índices
    # -------------------------------
    BASE_DIR: str = Field(default="./data")
    PDF_DIR: str = Field(default="./data")
    INDEX_DIR: str = Field(default="./data")
    PARQUET_PATH: str = Field(default="./data/aeat_corpus.parquet")
    META_PATH: str = Field(default="./data/aeat_meta.parquet")
    INDEX_PATH: str = Field(default="./data/aeat_faiss.index")
    CACHE_DIR: str = Field(default="./cache")

    # -------------------------------
    # 🧠 Modelos de Embeddings
    # -------------------------------
    EMBEDDING_MODEL: str = Field(
        default="mixedbread-ai/mxbai-embed-large-v1",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "EMB_MODEL_NAME"),
    )
    RERANKING_MODEL: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")

    # -------------------------------
    # ⚙️ Parámetros de inferencia
    # -------------------------------
    TEMPERATURE: float = Field(default=1.0)
    MAX_TOKENS: int = Field(default=1200)

    # -------------------------------
    # 🔍 Parámetros RAG
    # -------------------------------
    CHUNK_SIZE: int = Field(default=1200)
    CHUNK_OVERLAP: int = Field(default=150)
    RETRIEVAL_K: int = Field(default=6)
    RERANK_K: int = Field(default=3)

    # -------------------------------
    # 🛡️ Guardrails
    # -------------------------------
    ENABLE_GUARDRAILS: bool = Field(default=True)
    TOXICITY_THRESHOLD: float = Field(default=0.8)
    HALLUCINATION_THRESHOLD: float = Field(default=0.85)

    # -------------------------------
    # 🚦 Rate Limiting
    # -------------------------------
    RATE_LIMIT_PER_MINUTE: int = Field(default=10)

    # -------------------------------
    # 🛡️ Content Moderation (Llama Guard via Groq)
    # -------------------------------
    GROQ_API_KEY: str | None = Field(default=None)
    GROQ_MODEL: str = Field(default="openai/gpt-oss-safeguard-20b")

    # Specialized Groq Models (v2.8 Security Upgrade)
    GROQ_MODEL_ROUTER: str = Field(default="llama-3.1-8b-instant")
    GROQ_MODEL_PROMPT_GUARD: str = Field(default="meta-llama/llama-prompt-guard-2-86m")
    GROQ_MODEL_SAFETY: str = Field(
        default="openai/gpt-oss-safeguard-20b"
    )  # For SQLi (S14) & PII (S7)

    ENABLE_CONTENT_MODERATION: bool = Field(default=True)

    # -------------------------------
    # 🧠 Semantic Cache (Upstash Vector)
    # -------------------------------
    UPSTASH_VECTOR_REST_URL: str | None = Field(default=None)
    UPSTASH_VECTOR_REST_TOKEN: str | None = Field(default=None)
    ENABLE_SEMANTIC_CACHE: bool = Field(default=True)
    SEMANTIC_CACHE_THRESHOLD: float = Field(default=0.93)

    # -------------------------------
    # 🔍 RAG Vector Search (Upstash Vector - separate index)
    # -------------------------------
    UPSTASH_VECTOR_RAG_URL: str | None = Field(default=None)
    UPSTASH_VECTOR_RAG_TOKEN: str | None = Field(default=None)

    # -------------------------------
    # 📋 Topics & Competitors
    # -------------------------------
    VALID_TOPICS: str = Field(
        default="fiscalidad española,AEAT,impuestos,tributación,Hacienda,declaración,IVA,IRPF,Sociedades,Patrimonio,modelo,formulario,deducción"
    )
    INVALID_TOPICS: str = Field(
        default="inversiones bursátiles,préstamos,seguros de vida,criptomonedas trading,forex,opciones financieras"
    )
    COMPETITORS: str = Field(
        default="Tax Advisor,Gestoría Martinez,Asesor Fiscal López,TurboTax,H&R Block,TaxAct,FreeTaxUSA"
    )

    # -------------------------------
    # 📊 Logging
    # -------------------------------
    LOG_LEVEL: str = Field(default="INFO")

    # -------------------------------
    # 💳 Stripe (Payments)
    # -------------------------------
    STRIPE_SECRET_KEY: str | None = Field(default=None)
    STRIPE_WEBHOOK_SECRET: str | None = Field(default=None)
    STRIPE_PRICE_ID: str | None = Field(default=None)
    STRIPE_PRICE_ID_AUTONOMO: str | None = Field(default=None)
    STRIPE_PRICE_ID_CREATOR: str | None = Field(default=None)
    STRIPE_PRODUCT_ID: str = Field(default="prod_U4lJ9l8NhKvFHZ")

    # -------------------------------
    # 📧 Email (Resend)
    # -------------------------------
    RESEND_API_KEY: str | None = Field(default=None)
    RESEND_FROM_EMAIL: str = Field(default="noreply@impuestify.com")

    # -------------------------------
    # 🔔 Web Push (VAPID)
    # -------------------------------
    VAPID_PUBLIC_KEY: str | None = Field(default=None)
    VAPID_PRIVATE_KEY: str | None = Field(default=None)
    VAPID_CLAIMS_EMAIL: str = Field(default="mailto:soporte@impuestify.com")

    # -------------------------------
    # 🛡️ Cloudflare Turnstile
    # -------------------------------
    TURNSTILE_SECRET_KEY: str | None = Field(default=None)
    TURNSTILE_TEST_MODE: bool = Field(
        default=False,
        description="Set True in QA/staging to accept Cloudflare's official test token",
    )

    # -------------------------------
    # 🔑 Google OAuth (SSO)
    # -------------------------------
    GOOGLE_CLIENT_ID: str | None = Field(
        default=None, description="Google OAuth Client ID for SSO login/register"
    )

    # -------------------------------
    # 🌐 Frontend
    # -------------------------------
    FRONTEND_URL: str = Field(default="https://impuestify.com")

    # -------------------------------
    # 👤 Owner & Contact
    # -------------------------------
    OWNER_EMAIL: str = Field(default="fernando.prada@proton.me")
    CONTACT_EMAIL: str = Field(default="fernando.prada@proton.me")

    # -------------------------------
    # 🔑 Admin
    # -------------------------------
    ADMIN_API_KEY: str = Field(default="your-secure-admin-key-here")

    # -------------------------------
    # Demo Mode (white-label deploys)
    # -------------------------------
    DEMO_MODE: bool = Field(
        default=False,
        description="When True, app runs as anonymous white-label demo (Melilla focus).",
    )
    BRAND_NAME: str = Field(
        default="Impuestify",
        description="Brand displayed in emails, PDFs, system prompts. Override per deploy.",
    )
    BRAND_DOMAIN: str = Field(
        default="impuestify.com",
        description="Public domain for emails/links. NEVER hardcode '.es' (Bug 52).",
    )
    SUBSCRIPTIONS_ENABLED: bool = Field(
        default=True,
        description="Toggle Stripe checkout/portal routes. False = demo free access.",
    )
    RAG_TERRITORY_LOCK: str | None = Field(
        default=None,
        description="If set (e.g. 'Melilla'), force territory_filter in all RAG queries.",
    )
    DEMO_USER_EMAIL: str | None = Field(
        default=None,
        description="If DEMO_MODE=True, seed this user at startup.",
    )
    DEMO_USER_PASSWORD: str | None = Field(
        default=None,
        description="Plaintext password for demo user seed (hashed at insert).",
    )

    # -------------------------------
    # Configuracion de entorno
    # -------------------------------
    model_config = SettingsConfigDict(
        env_file="../.env",  # .env is in project root, parent of backend
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -------------------------------
    # 🧹 Validadores
    # -------------------------------
    @field_validator(
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "JWT_SECRET_KEY",
        "ADMIN_API_KEY",
        "TURSO_AUTH_TOKEN",
        "UPSTASH_REDIS_REST_TOKEN",
        "GROQ_API_KEY",
        "UPSTASH_VECTOR_REST_TOKEN",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "RESEND_API_KEY",
        mode="before",
    )
    @classmethod
    def strip_quotes(cls, v):
        """Elimina comillas accidentales en las claves del .env"""
        return v.strip().strip('"').strip("'") if isinstance(v, str) else v

    # -------------------------------
    # 🔧 Helper properties
    # -------------------------------
    @property
    def valid_topics_list(self) -> list[str]:
        """Get valid topics as list"""
        return [t.strip() for t in self.VALID_TOPICS.split(",")]

    @property
    def invalid_topics_list(self) -> list[str]:
        """Get invalid topics as list"""
        return [t.strip() for t in self.INVALID_TOPICS.split(",")]

    @property
    def competitors_list(self) -> list[str]:
        """Get competitors as list"""
        return [c.strip() for c in self.COMPETITORS.split(",")]

    @property
    def is_llm_configured(self) -> bool:
        """Check if LLM (OpenAI or Azure) is configured"""
        return bool(
            self.OPENAI_API_KEY or (self.AZURE_OPENAI_API_KEY and self.AZURE_OPENAI_ENDPOINT)
        )

    @property
    def is_azure_configured(self) -> bool:
        """Check if Azure OpenAI is configured"""
        return bool(self.AZURE_OPENAI_API_KEY and self.AZURE_OPENAI_ENDPOINT)

    @property
    def is_turso_configured(self) -> bool:
        """Check if Turso is configured"""
        return bool(self.TURSO_DATABASE_URL and self.TURSO_AUTH_TOKEN)

    @property
    def is_upstash_configured(self) -> bool:
        """Check if Upstash Redis is configured"""
        return bool(self.UPSTASH_REDIS_REST_URL and self.UPSTASH_REDIS_REST_TOKEN)

    @property
    def is_groq_configured(self) -> bool:
        """Check if Groq (Llama Guard) is configured"""
        return bool(self.GROQ_API_KEY)

    @property
    def is_upstash_vector_configured(self) -> bool:
        """Check if Upstash Vector (Semantic Cache) is configured"""
        return bool(self.UPSTASH_VECTOR_REST_URL and self.UPSTASH_VECTOR_REST_TOKEN)

    @property
    def is_upstash_rag_configured(self) -> bool:
        """Check if Upstash Vector RAG index is configured"""
        return bool(self.UPSTASH_VECTOR_RAG_URL and self.UPSTASH_VECTOR_RAG_TOKEN)

    @property
    def is_stripe_configured(self) -> bool:
        """Check if Stripe payments are configured"""
        return bool(self.STRIPE_SECRET_KEY)

    @property
    def is_resend_configured(self) -> bool:
        """Check if Resend email service is configured"""
        return bool(self.RESEND_API_KEY)


# Initialize global settings
settings = Settings()

# Ensure directories exist
os.makedirs(settings.BASE_DIR, exist_ok=True)
os.makedirs(settings.CACHE_DIR, exist_ok=True)
