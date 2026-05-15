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
