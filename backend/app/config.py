"""
TaxIA Configuration

Unified settings using Pydantic with Azure AI services support.
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices, field_validator


class Settings(BaseSettings):
    # -------------------------------
    # 🔐 Azure AI Foundry (LLM)
    # -------------------------------
    AZURE_OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY")
    )
    AZURE_OPENAI_ENDPOINT: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AZURE_OPENAI_ENDPOINT")
    )
    AZURE_OPENAI_DEPLOYMENT: str = Field(
        default="gpt-5-mini",
        validation_alias=AliasChoices("AZURE_OPENAI_DEPLOYMENT", "OPENAI_MODEL")
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        default="2024-10-21",
        validation_alias=AliasChoices("AZURE_OPENAI_API_VERSION")
    )
    
    # Legacy OpenAI support (fallback)
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    
    # -------------------------------
    # 📄 Azure Document Intelligence
    # -------------------------------
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: Optional[str] = Field(default=None)
    AZURE_DOCUMENT_INTELLIGENCE_KEY: Optional[str] = Field(default=None)

    # -------------------------------
    # 🗄️ Turso Database
    # -------------------------------
    TURSO_DATABASE_URL: Optional[str] = Field(default=None)
    TURSO_AUTH_TOKEN: Optional[str] = Field(default=None)

    # -------------------------------
    # 📦 Upstash Redis
    # -------------------------------
    UPSTASH_REDIS_REST_URL: Optional[str] = Field(default=None)
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = Field(default=None)

    # -------------------------------
    # 🔒 JWT Authentication
    # -------------------------------
    JWT_SECRET_KEY: str = Field(
        default="change-this-secret-key-in-production",
        validation_alias=AliasChoices("JWT_SECRET_KEY")
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
        validation_alias=AliasChoices("EMBEDDING_MODEL", "EMB_MODEL_NAME")
    )
    RERANKING_MODEL: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2"
    )

    # -------------------------------
    # ⚙️ Parámetros de inferencia
    # -------------------------------
    TEMPERATURE: float = Field(default=0.2)
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
    # 🔑 Admin
    # -------------------------------
    ADMIN_API_KEY: str = Field(default="your-secure-admin-key-here")

    # -------------------------------
    # ⚙️ Configuración de entorno
    # -------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # -------------------------------
    # 🧹 Validadores
    # -------------------------------
    @field_validator(
        "AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "JWT_SECRET_KEY", 
        "ADMIN_API_KEY", "TURSO_AUTH_TOKEN", "UPSTASH_REDIS_REST_TOKEN",
        mode="before"
    )
    @classmethod
    def strip_quotes(cls, v):
        """Elimina comillas accidentales en las claves del .env"""
        return v.strip().strip('"').strip("'") if isinstance(v, str) else v

    # -------------------------------
    # 🔧 Helper properties
    # -------------------------------
    @property
    def valid_topics_list(self) -> List[str]:
        """Get valid topics as list"""
        return [t.strip() for t in self.VALID_TOPICS.split(",")]
    
    @property
    def invalid_topics_list(self) -> List[str]:
        """Get invalid topics as list"""
        return [t.strip() for t in self.INVALID_TOPICS.split(",")]
    
    @property
    def competitors_list(self) -> List[str]:
        """Get competitors as list"""
        return [c.strip() for c in self.COMPETITORS.split(",")]
    
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


# Initialize global settings
settings = Settings()

# Ensure directories exist
os.makedirs(settings.BASE_DIR, exist_ok=True)
os.makedirs(settings.CACHE_DIR, exist_ok=True)