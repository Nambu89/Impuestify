# app/config.py
import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices, field_validator

# === Raíz del proyecto y .env ===
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_DATA = os.path.join(PROJECT_ROOT, "data")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def _abs_path(path: str) -> str:
    """Convierte a ruta absoluta respetando relativas al proyecto."""
    if not path:
        return path
    return path if os.path.isabs(path) else os.path.abspath(os.path.join(PROJECT_ROOT, path))


class Settings(BaseSettings):
    """Configuración centralizada de TaxIA (robusta + retrocompatible)."""

    # ---------------------------
    # 🔐 OpenAI
    # ---------------------------
    OPENAI_API_KEY: str = Field(validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"))
    OPENAI_MODEL: str = Field(default="gpt-4o-mini",
                              validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"))

    # ---------------------------
    # 📁 Rutas y artefactos (por defecto bajo ./data)
    # ---------------------------
    BASE_DIR: str = Field(default=DEFAULT_DATA,
                          validation_alias=AliasChoices("BASE_DIR", "base_dir"))

    INDEX_DIR: str = Field(default=DEFAULT_DATA,
                           validation_alias=AliasChoices("INDEX_DIR", "PDF_DIR", "pdf_dir"))

    PARQUET_PATH: str = Field(default=os.path.join(DEFAULT_DATA, "aeat_corpus.parquet"),
                              validation_alias=AliasChoices("PARQUET_PATH", "parquet_path"))

    META_PATH: str = Field(default=os.path.join(DEFAULT_DATA, "aeat_meta.parquet"),
                           validation_alias=AliasChoices("META_PATH", "meta_path"))

    INDEX_PATH: str = Field(default=os.path.join(DEFAULT_DATA, "aeat_faiss.index"),
                            validation_alias=AliasChoices("INDEX_PATH", "index_path"))

    CACHE_DIR: str = Field(default=os.path.join(DEFAULT_DATA, "cache"),
                           validation_alias=AliasChoices("CACHE_DIR", "cache_dir"))

    # ---------------------------
    # 🧠 Modelos
    # ---------------------------
    EMB_MODEL_NAME: str = Field(
        default="mixedbread-ai/mxbai-embed-large-v1",
        validation_alias=AliasChoices("EMB_MODEL_NAME", "EMBEDDING_MODEL", "embedding_model")
    )
    RERANKING_MODEL: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias=AliasChoices("RERANKING_MODEL", "reranking_model")
    )

    # ---------------------------
    # 🔍 Parámetros RAG
    # ---------------------------
    CHUNK_SIZE: int = Field(default=1500, validation_alias=AliasChoices("CHUNK_SIZE", "chunk_size"))
    CHUNK_OVERLAP: int = Field(default=150, validation_alias=AliasChoices("CHUNK_OVERLAP", "chunk_overlap"))
    RETRIEVAL_K: int = Field(default=6, validation_alias=AliasChoices("RETRIEVAL_K", "retrieval_k"))
    RERANK_K: int = Field(default=3, validation_alias=AliasChoices("RERANK_K", "rerank_k"))

    # ---------------------------
    # ✍️ Generación
    # ---------------------------
    TEMPERATURE: float = Field(default=0.2, validation_alias=AliasChoices("TEMPERATURE", "temperature"))
    MAX_TOKENS: int = Field(default=1200, validation_alias=AliasChoices("MAX_TOKENS", "max_tokens"))

    # ---------------------------
    # 🛡️ Guardrails
    # ---------------------------
    ENABLE_GUARDRAILS: bool = Field(default=True, validation_alias=AliasChoices("ENABLE_GUARDRAILS", "enable_guardrails"))
    TOXICITY_THRESHOLD: float = Field(default=0.8, validation_alias=AliasChoices("TOXICITY_THRESHOLD", "toxicity_threshold"))
    HALLUCINATION_THRESHOLD: float = Field(default=0.85, validation_alias=AliasChoices("HALLUCINATION_THRESHOLD", "hallucination_threshold"))

    # ---------------------------
    # 🧰 Cache externa (opcional)
    # ---------------------------
    REDIS_URL: Optional[str] = Field(default=None, validation_alias=AliasChoices("REDIS_URL", "redis_url"))
    ENABLE_CACHE: bool = Field(default=False, validation_alias=AliasChoices("ENABLE_CACHE", "enable_cache"))

    # ---------------------------
    # 🧹 Logging / Admin
    # ---------------------------
    LOG_LEVEL: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "log_level"))
    ADMIN_API_KEY: str = Field(default="admin123", validation_alias=AliasChoices("ADMIN_API_KEY", "admin_api_key"))

    # ---------------------------
    # 🧾 Listas desde .env (se aceptan coma-separadas)
    # ---------------------------
    COMPETITORS: Union[List[str], str] = Field(
        default="Tax Advisor,Gestoría Martinez,Asesor Fiscal López,TurboTax,H&R Block,TaxAct,FreeTaxUSA",
        validation_alias=AliasChoices("COMPETITORS", "competitors")
    )
    VALID_TOPICS: Union[List[str], str] = Field(
        default="fiscalidad española,AEAT,impuestos,tributación,Hacienda,declaración,IVA,IRPF,Sociedades,Patrimonio,modelo,formulario,deducción",
        validation_alias=AliasChoices("VALID_TOPICS", "valid_topics")
    )
    INVALID_TOPICS: Union[List[str], str] = Field(
        default="inversiones bursátiles,préstamos,seguros de vida,criptomonedas trading,forex,opciones financieras",
        validation_alias=AliasChoices("INVALID_TOPICS", "invalid_topics")
    )

    # ---------------------------
    # ⚙️ Config del loader
    # ---------------------------
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",           # IGNORA variables desconocidas (evita ValidationError)
    )

    # ---------------------------
    # 🧹 Validadores / Normalizadores
    # ---------------------------
    @field_validator(
        "OPENAI_API_KEY", "ADMIN_API_KEY",
        mode="before"
    )
    @classmethod
    def _strip_quotes(cls, v):
        return v.strip().strip('"').strip("'") if isinstance(v, str) else v

    @field_validator(
        "PARQUET_PATH", "META_PATH", "INDEX_PATH", "CACHE_DIR", "INDEX_DIR", "BASE_DIR",
        mode="after"
    )
    @classmethod
    def _make_abs_paths(cls, v):
        return _abs_path(v)

    @field_validator("COMPETITORS", "VALID_TOPICS", "INVALID_TOPICS", mode="before")
    @classmethod
    def _csv_to_list(cls, v):
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    # ---------------------------
    # 🔁 Propiedades de compatibilidad
    # (para que rag_engine/app.main puedan usar nombres antiguos)
    # ---------------------------
    @property
    def openai_api_key(self) -> str: return self.OPENAI_API_KEY
    @property
    def openai_model(self) -> str: return self.OPENAI_MODEL
    @property
    def embedding_model(self) -> str: return self.EMB_MODEL_NAME
    @property
    def reranking_model(self) -> str: return self.RERANKING_MODEL

    @property
    def pdf_dir(self) -> str: return self.INDEX_DIR
    @property
    def parquet_path(self) -> str: return self.PARQUET_PATH
    @property
    def meta_path(self) -> str: return self.META_PATH
    @property
    def index_path(self) -> str: return self.INDEX_PATH
    @property
    def cache_dir(self) -> str: return self.CACHE_DIR

    @property
    def chunk_size(self) -> int: return self.CHUNK_SIZE
    @property
    def chunk_overlap(self) -> int: return self.CHUNK_OVERLAP
    @property
    def retrieval_k(self) -> int: return self.RETRIEVAL_K
    @property
    def rerank_k(self) -> int: return self.RERANK_K

    @property
    def enable_guardrails(self) -> bool: return self.ENABLE_GUARDRAILS
    @property
    def toxicity_threshold(self) -> float: return self.TOXICITY_THRESHOLD
    @property
    def hallucination_threshold(self) -> float: return self.HALLUCINATION_THRESHOLD

    @property
    def competitors(self) -> List[str]:
        return self.COMPETITORS if isinstance(self.COMPETITORS, list) else []
    @property
    def valid_topics(self) -> List[str]:
        return self.VALID_TOPICS if isinstance(self.VALID_TOPICS, list) else []
    @property
    def invalid_topics(self) -> List[str]:
        return self.INVALID_TOPICS if isinstance(self.INVALID_TOPICS, list) else []


# === Instancia global y creación de carpetas ===
settings = Settings()

os.makedirs(settings.BASE_DIR, exist_ok=True)
os.makedirs(settings.CACHE_DIR, exist_ok=True)
# Asegura carpeta de los artefactos (por si apuntan fuera de BASE_DIR)
for path in (settings.PARQUET_PATH, settings.META_PATH, settings.INDEX_PATH):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)