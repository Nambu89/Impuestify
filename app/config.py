import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices, field_validator


class Settings(BaseSettings):
    # -------------------------------
    # 🔐 Claves API
    # -------------------------------
    OPENAI_API_KEY: str = Field(validation_alias=AliasChoices("OPENAI_API_KEY"))
    SERVICE_API_KEY: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("SERVICE_API_KEY", "service_api_key")
    )

    # -------------------------------
    # 📁 Paths de datos e índices
    # -------------------------------
    BASE_DIR: str = Field(default="./data", validation_alias=AliasChoices("BASE_DIR", "base_dir"))

    INDEX_DIR: str = Field(default="./data", validation_alias=AliasChoices("INDEX_DIR", "pdf_dir"))
    PARQUET_PATH: str = Field(default="./data/aeat_corpus.parquet", validation_alias=AliasChoices("PARQUET_PATH", "parquet_path"))
    META_PATH: str = Field(default="./data/aeat_meta.parquet", validation_alias=AliasChoices("META_PATH", "meta_path"))
    INDEX_PATH: str = Field(default="./data/aeat_faiss.index", validation_alias=AliasChoices("INDEX_PATH", "index_path"))

    # Carpeta para cachés de embeddings/respuestas
    CACHE_DIR: str = Field(default="./data/cache", validation_alias=AliasChoices("CACHE_DIR", "cache_dir"))

    # -------------------------------
    # 🧠 Modelos y parámetros
    # -------------------------------
    EMB_MODEL_NAME: str = Field(
        default="mixedbread-ai/mxbai-embed-large-v1",
        validation_alias=AliasChoices("EMB_MODEL_NAME", "embedding_model")
    )
    RERANKING_MODEL: Optional[str] = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias=AliasChoices("RERANKING_MODEL", "reranking_model")
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_MODEL", "openai_model")
    )

    # -------------------------------
    # ⚙️ Parámetros de inferencia
    # -------------------------------
    TEMPERATURE: float = Field(default=0.2, validation_alias=AliasChoices("TEMPERATURE", "temperature"))
    MAX_TOKENS: int = Field(default=1200, validation_alias=AliasChoices("MAX_TOKENS", "max_tokens"))

    # -------------------------------
    # 🔍 Parámetros RAG
    # -------------------------------
    RETRIEVAL_K: int = Field(default=6, validation_alias=AliasChoices("RETRIEVAL_K", "retrieval_k"))
    RERANK_K: int = Field(default=3, validation_alias=AliasChoices("RERANK_K", "rerank_k"))

    CHUNK_SIZE: int = Field(default=1500, validation_alias=AliasChoices("CHUNK_SIZE", "chunk_size"))
    CHUNK_OVERLAP: int = Field(default=150, validation_alias=AliasChoices("CHUNK_OVERLAP", "chunk_overlap"))

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
    @field_validator("OPENAI_API_KEY", "SERVICE_API_KEY", mode="before")
    @classmethod
    def strip_quotes(cls, v):
        """Elimina comillas accidentales en las claves del .env"""
        return v.strip().strip('"').strip("'") if isinstance(v, str) else v


# Inicializa settings global
settings = Settings()

# Asegura existencia de directorios básicos
os.makedirs(settings.BASE_DIR, exist_ok=True)
os.makedirs(settings.CACHE_DIR, exist_ok=True)