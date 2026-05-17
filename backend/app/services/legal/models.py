"""Pydantic models for the legal norms registry.

These models mirror the YAML schemas in `backend/data/legal/`:
    - `norms.yaml`               → list[LegalNorm]
    - `articles.yaml`            → list[CanonicalArticle]
    - `invoice_templates.yaml`   → list[InvoiceTemplate]

Validation runs at startup. A malformed YAML aborts the app with a clear
error, preventing degraded behaviour from silently shipping.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Norms ────────────────────────────────────────────────────────────────


class LegalNorm(BaseModel):
    """A tax-law norm (Ley/RD/RDLegislativo/Norma Foral)."""

    model_config = ConfigDict(extra="forbid")

    sigla: str = Field(..., min_length=2, description="Sigla oficial: LIVA, LIRPF…")
    full_id: str = Field(..., min_length=3, description='Forma "Tipo Numero/Año"')
    name: str = Field(..., min_length=3, description="Nombre completo")
    norm_type: str = Field(..., description="ley | rd | rd_legislativo | norma_foral | decreto_foral")
    vigent_from: date
    vigent_until: Optional[date] = None
    aliases: List[str] = Field(default_factory=list)
    # BOE identifier (formato oficial BOE-A-NNNN-NNNN). Permite verificar
    # vigencia via API BOE Datos Abiertos y construir link a versión
    # consolidada oficial. Opcional para no romper YAMLs sin migrar.
    boe_id: Optional[str] = Field(
        default=None,
        pattern=r"^BOE-[A-Z]-\d{4}-\d+$",
        description='Identificador BOE oficial, ej "BOE-A-1992-28740"',
    )
    # URL HTML consolidada cacheada desde la API. Si null, se reconstruye
    # con `https://www.boe.es/buscar/act.php?id={boe_id}` cuando se necesite.
    url_html_consolidada: Optional[str] = Field(
        default=None,
        description="URL HTML versión consolidada vigente",
    )
    # Plugin de origen para verificación de vigencia y resolución de URL.
    # Si vacío, default = "boe" (compat con normas estatales existentes).
    # Valores válidos: boe | bopv | static_url | (futuros: bon, boc, …)
    source_id: Optional[str] = Field(
        default=None,
        description="Identificador del plugin LegalSource (boe, bopv, static_url, …)",
    )
    # ID dentro del sistema del source. Para BOE = boe_id; para BOPV =
    # "YYYY/MM/numOrder"; para static_url = la URL completa.
    source_norm_id: Optional[str] = Field(
        default=None,
        description="ID nativo del source. Si null, fallback a boe_id.",
    )

    def effective_source_id(self) -> str:
        """Default = "boe" si no se especifica (compat con YAMLs previos)."""
        return self.source_id or "boe"

    def effective_source_norm_id(self) -> Optional[str]:
        """Resolve which identifier to pass to the source plugin."""
        if self.source_norm_id:
            return self.source_norm_id
        if self.effective_source_id() == "boe":
            return self.boe_id
        if self.effective_source_id() == "static_url":
            return self.url_html_consolidada
        return None

    @field_validator("norm_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        allowed = {"ley", "rd", "real_decreto", "rd_legislativo", "norma_foral", "decreto_foral"}
        if v not in allowed:
            raise ValueError(f"norm_type debe ser uno de {allowed}, recibido '{v}'")
        return v

    def is_vigent_on(self, target: date) -> bool:
        """True if the norm is in force on `target` date."""
        if target < self.vigent_from:
            return False
        if self.vigent_until is not None and target > self.vigent_until:
            return False
        return True


class NormsCatalog(BaseModel):
    """Root document of `norms.yaml`."""

    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    norms: List[LegalNorm]


# ── Canonical Articles ───────────────────────────────────────────────────


class CanonicalArticle(BaseModel):
    """A canonical article referenced by the assistant's templates.

    Only articles the system actively cites should appear in
    `articles.yaml` — this is NOT the full corpus.
    """

    model_config = ConfigDict(extra="forbid")

    law: str = Field(..., description="Sigla of the norm (must exist in norms.yaml)")
    article: str = Field(..., description='Number, e.g. "21", "69", "84"')
    subarticle: Optional[str] = Field(
        default=None,
        description='Apartado/letter, e.g. "Uno.1", "Dos.d", "84.uno.2"; null for whole article',
    )
    topic: str = Field(..., min_length=3, description="Brief topic for human readers")
    vigent_from: date
    vigent_until: Optional[date] = None

    def is_vigent_on(self, target: date) -> bool:
        if target < self.vigent_from:
            return False
        if self.vigent_until is not None and target > self.vigent_until:
            return False
        return True


class ArticlesCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    articles: List[CanonicalArticle]


# ── Invoice Templates ────────────────────────────────────────────────────


class InvoiceTemplate(BaseModel):
    """Copy-paste invoice text for a specific tax scenario."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$", description="Unique identifier")
    scenario: str = Field(..., min_length=5)
    legal_basis: str = Field(..., min_length=3)
    triggers: List[str] = Field(default_factory=list)
    text: str = Field(..., min_length=10)
    notes: Optional[str] = None


class InvoiceTemplatesCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    templates: List[InvoiceTemplate]
